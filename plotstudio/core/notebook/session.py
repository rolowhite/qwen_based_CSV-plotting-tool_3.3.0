"""One Notebook turn: read the picture (or take the typed text), then write an answer for each problem in it.

A problem that library_match is sure about gets the stored solution. Any other problem is solved live: the local
qwen model and, when the user added a key, Gemini solve it at the same time, both taking every number from the
calculator. If both finish, Gemini's solution is shown; when their results disagree, Gemini first re-checks its
work once with qwen's answer in view. If one of them fails, the other's solution is shown.
Every answer is streamed in small pieces, the same way, so the page never shows where it came from; that is
written only to the local history file (one JSON line per turn, never the key).
A picture that doesn't give a sure match is read once more at another size first.
"""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from . import cache as answer_cache
from . import footer, gemini, library_match, lookup, ollama, quick, reader, solver, verify

NOTHING = "I couldn't find a problem in this picture. Try a sharper picture, or mark just the problem."
PACE = 0.03              # seconds between streamed pieces
WORDS = 3                # words per piece
SECOND_READ = 1.5        # the second read sends the picture this much bigger (or smaller, past the size cap)
EXAMPLE_WORDS = 0.5      # a library problem this close in wording is shown to the solver as a worked example
SOLVE_BUDGET = 300       # s each solver may take for one problem (a looping or stalled model is stopped)
GEMINI_GRACE = 90        # s Gemini may go on after the local model has its answer, before that one is used
QWEN_GRACE = 30          # s the local model may go on after Gemini has its answer (usually first), to cross-check it
STREAM_MAX = 1.2         # s at most to show a stored or finished answer: the words are only paced, never waited for


# "9.5", "lind 9.5", "Exercise 9.5 walpole": the user names an exercise instead of showing it
_REFERENCE = re.compile(r"^\s*(?:(?P<b1>lind|walpole)\b[\s:,.-]*)?(?:ex(?:ercise)?\.?\s*)?(?P<n>\d{1,2}\.\d{1,3})"
                        r"\s*(?:(?:in|from|of)?\s*(?P<b2>lind|walpole))?\s*\??\s*$", re.I)


def reference(text: str, need_book: bool = False):
    """(book or '', '9.5') when the text only names an exercise, else None. `need_book`: only 'lind 9.5' counts."""
    m = _REFERENCE.match(text or "")
    if m is None or (need_book and not (m.group("b1") or m.group("b2"))):
        return None
    major, minor = m.group("n").split(".")
    return (m.group("b1") or m.group("b2") or "").lower(), f"{int(major)}.{int(minor)}"


@dataclass
class Source:
    name: str
    image: object = None     # a PIL image: a picture, a screenshot, a PDF page or the marked part of one
    text: str = ""           # typed text: nothing to read
    label: str = ""          # typed text: the exercise number it came with ("4.10", chosen from a picture's problems)
    hint: str = ""           # a digital PDF page's text layer
    load: Optional[Callable[[], Tuple[object, str]]] = None    # gives (image, hint) in the worker: a PDF page

    def digest(self) -> str:
        data = self.image.tobytes() if self.image is not None else (self.text or self.name).encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:16]


def ok_names(results: dict) -> List[str]:
    return [n for n, r in results.items() if isinstance(r, solver.Solution)]


def second_size(first: int) -> int:
    """The long side for the second read: 1.5x the first, up to the size cap; smaller only when it is already
    at the cap (a second look at a bigger picture can't be bigger)."""
    bigger = min(round(first * SECOND_READ), ollama.LONG_SIDE_MAX)
    return bigger if bigger >= first * 1.15 else max(ollama.LONG_SIDE_MIN, round(first / SECOND_READ))


def answer_markdown(problem: reader.Problem, solution_md: str, unreadable=()) -> str:
    """What the page shows for one problem: the problem as it was read, then the worked solution."""
    head = f"**Problem {problem.label}.**" if problem.label else "**Problem.**"
    tail = ""
    if unreadable:
        tail = "\n\n*Part of the picture couldn't be read: " + "; ".join(u.rstrip(".") for u in unreadable) + ".*"
    return f"{head}\n\n{problem.markdown}\n\n**Solution.**\n\n{solution_md}{tail}"


class Turn:
    """Run with `run(emit)` in a worker thread; `cancel()` (from any thread) stops it with ollama.Cancelled.
    emit gets ("status", text), ("start", None), ("text", piece) and ("end", markdown) for each answer."""

    def __init__(self, source: Source, index=None, url: str = ollama.DEFAULT_URL, wanted_model: str = "",
                 log_path: Optional[Path] = None, pace: Optional[float] = None, gemini_key: str = "",
                 gemini_model: str = "", gemini_base: str = gemini.BASE_URL, match: bool = True,
                 cache: Optional[answer_cache.Cache] = None, prerender: Optional[Callable[[str], None]] = None,
                 prefer: str = ""):
        self.source = source
        self.prefer = prefer            # the user's book ("lind"): it breaks a tie between two books
        self._missing = ""              # why no exercise was found, when a typed number named none
        self.cache = cache              # verified live answers and readings, remembered between turns
        self.prerender = prerender      # draws an answer's formulas in the background before it streams in
        self.choices: List[Tuple[str, str]] = []
        self._steps = {}
        self.index = index
        self.chat = ollama.Chat(url)
        self.url = url
        self.wanted = wanted_model
        self.log_path = log_path
        self.pace = PACE if pace is None else pace
        self.model = None
        self.reads: List[reader.Reading] = []
        self.answers: List[dict] = []
        self._gemini = (gemini_key, gemini_model, gemini_base)
        self.match = match              # False: always solve (the live eval), the library still gives context
        self.gemini_problem = None      # why Gemini didn't help this turn (the page shows it in the Model menu)
        self._backends = []
        self.pending: List[verify.Pending] = []     # answers worth re-checking in the background once this turn is done
        self._found = None              # ollama.models(), once per turn
        self._said_reading = False
        self._notes = {}                # problem text -> which number was read differently from the library's

    def cancel(self):
        self.chat.cancel()
        for backend in list(self._backends):
            backend.cancel()

    def run(self, emit: Callable) -> List[str]:
        error = None
        try:
            if self.source.load is not None:
                self.source.image, self.source.hint = self.source.load()
            problems, hits = self._read(emit) if self.source.image is not None else self._typed()
            unreadable = self.reads[-1].unreadable if self.reads and all(r.unreadable for r in self.reads) else []
            if self.source.image is not None and len(problems) > 1:
                # one picture, several problems: the user says which one, then it is solved (the page asks)
                self.choices = [(p.label, p.markdown) for p in problems]
            if self.choices:
                emit(("choose", self.choices))
                return []
            emit(("status", "Solving…"))
            if not problems:
                self._stream(emit, self._missing or NOTHING, None, {"from": "none"})
            trusted = []
            for problem, exercise in zip(problems, hits):
                cached = None
                if exercise is None and self.cache is not None and self.match:
                    cached = self.cache.answer(problem.markdown)
                if cached is not None:
                    markdown, info = cached["markdown"], {"from": "cache", "by": cached["by"]}
                    trusted.append(True)
                elif exercise is not None:
                    markdown, info = exercise.solution_md, {"from": f"library:{exercise.key}", "by": "library",
                                                            "solution": exercise.solution_md}
                    trusted.append(True)
                    note = self._notes.get(problem.markdown)
                    if note:        # a blurred digit may be why a number differs: say so, the page is the judge
                        markdown += f"\n\n*Matched to Exercise {exercise.number} of {exercise.book.title()} by its " \
                                    f"wording, but some numbers differ ({note}). Check them against your page: if " \
                                    "your numbers are different, it is being solved again with them, and a " \
                                    "correction follows here if the answer changes.*"
                        info["note"] = note
                        trusted[-1] = False
                        self.pending.append(verify.Pending(problem.label, problem.markdown, exercise.solution_md,
                                                           "library", self.source.image, self._context(problem.markdown)))
                    if self.index is not None:      # where it is from, what to watch out for, the formulas, what is next
                        markdown += footer.book_footer(exercise, self.index.library)
                else:
                    got = self._quick(problem)
                    if got is not None:
                        markdown, info = got
                    else:
                        shown, info = self._solve(emit, problem)
                        markdown = shown.markdown
                        info["by"] = "gemini" if shown.model.startswith("gemini") else "qwen"
                    trusted.append(info["agree"] is True)
                    if self.cache is not None:       # remembered; shown again only once two solvers or a re-check agree
                        self.cache.remember(problem.markdown, markdown, info["by"], info["agree"] is True)
                    if len(info["solutions"]) == 1:      # nobody cross-checked it: worth a second, independent look
                        self.pending.append(verify.Pending(problem.label, problem.markdown, markdown,
                                                           info["solutions"][0]["solver"], self.source.image,
                                                           self._context(problem.markdown)))
                info.setdefault("solution", markdown)
                self._stream(emit, answer_markdown(problem, markdown, unreadable), problem, info)
            if self.cache is not None and self.source.image is not None and problems and all(trusted):
                self.cache.remember_reading(self.source.digest(), [[p.label, p.markdown] for p in problems])
            return [a["answer"] for a in self.answers]
        except BaseException as exc:
            error = exc
            raise
        finally:
            self._log(error)

    # ------------------------------------------------------------------------------------------- steps --
    def _match(self, problem: reader.Problem):
        if self.index is None or not self.match:
            return None
        exercise, note = library_match.match_with_note(self.index, problem.markdown, problem.label, self.prefer)
        if note:
            self._notes[problem.markdown] = note
        return exercise

    def _near(self, problem: reader.Problem) -> bool:
        return self.index is not None and self.match and library_match.near(self.index, problem.markdown, problem.label)

    def _context(self, text: str) -> str:
        """The problems of the exercises `text` mentions ("the joint density of Exercise 3.40"), from the library.
        Two books number their exercises alike: the book of the closest library problem decides."""
        if self.index is None:
            return ""
        best = self.index.lookup(text).best
        book = best.exercise.book if best is not None and best.score >= lookup.LOW else (self.prefer or None)
        found = []
        for token in dict.fromkeys(t for t in lookup.numbers(text) if t.startswith("ex")):
            exercise = self.index.library.get(token[2:], book)
            if exercise is not None and exercise.has_problem:
                found.append(f"Exercise {exercise.number}: " + exercise.problem_md.replace("**Problem:**", "", 1).strip())
        return "\n\n".join(found)[:6000]

    def _typed(self):
        ref = reference(self.source.text) or reference(self.source.label, need_book=True)
        if ref is not None and self.index is not None:
            return self._named(*ref)
        problem = reader.Problem(self.source.label, self.source.text.strip())
        return [problem], [self._match(problem)]

    def _named(self, book: str, number: str):
        """The user typed an exercise number ("9.5", "lind 9.5"): answer it, or ask which book when two have it."""
        found = self.index.library.all_with_number(number)
        books = sorted({e.book for e in self.index.library.exercises})
        if book:
            found = [e for e in found if e.book == book]
        elif len(found) > 1 and any(e.book == self.prefer for e in found):
            found = [e for e in found if e.book == self.prefer]
        if not found:
            where = book.title() if book else " or ".join(b.title() for b in books)
            self._missing = f"I don't have Exercise {number} of {where} among my solutions."
            return [], []
        texts = [(f"{e.book.title()} {e.number}", e.problem_md.replace("**Problem:**", "", 1).strip() or
                  f"Exercise {e.number}") for e in found]
        if len(found) > 1:
            self.choices = texts
            return [], []
        return [reader.Problem(*texts[0])], found

    def _models(self):
        """Ollama's models, asked once a turn (each one costs a request for its capabilities)."""
        if self._found is None:
            self._found = ollama.models(self.url)
        return self._found

    def _pick_model(self):
        found = self._models()
        name = ollama.pick(found, "vision", self.wanted, avoid="thinking")
        if name is None:
            raise ollama.NotReady("None of the models installed in Ollama can read pictures. Run: "
                                  + ollama.PULL_HINT)
        caps = dict(found)[name]
        return name, (False if "thinking" in caps else None)      # thinking only slows plain copying down

    def _from_text_layer(self, emit):
        """A digital PDF's own text (exact characters), or else Tesseract's quick reading of the picture: when it
        alone is a library problem, no model has to read the picture (the slowest step). Anything less than a sure
        match falls through to the usual reading."""
        if self.index is None or not self.match:
            return None
        text = reader.clean_text(self.source.hint)
        if not text:
            emit(("status", "Reading the problem…"))
            self._said_reading = True
            text = reader.ocr_text(self.source.image)
        if not text:
            return None
        parts = reader.split_labelled(text)         # "4.9 ... 4.10 ... 4.11 ...": several problems on one picture
        if len(parts) > 1:
            hits = [self._match(p) for p in parts]
            return (parts, hits) if all(hits) else None
        problem = reader.Problem("", text)
        exercise = self._match(problem)
        return ([problem], [exercise]) if exercise is not None else None

    def _read(self, emit):
        saved = self.cache.reading(self.source.digest()) if self.cache is not None and self.match else None
        if saved:               # this very picture was read before and its problems answered: no model needed
            problems = [reader.Problem(label, markdown) for label, markdown in saved]
            return problems, [self._match(p) for p in problems]
        quick = self._from_text_layer(emit)
        if quick is not None:
            return quick
        self.model, think = self._pick_model()
        image, hint = self.source.image, self.source.hint
        if not self._said_reading:
            emit(("status", "Reading the problem…"))
        try:
            first = reader.read(self.chat, self.model, image, hint, think)
        except ollama.NotReady:
            raise
        except ollama.OllamaError as exc:       # the reply looped or broke: the read at another size may not
            first = reader.Reading(raw=f"{type(exc).__name__}: {exc}")
        self.reads.append(first)
        problems, hits = first.problems, [self._match(p) for p in first.problems]
        if problems and all(hits):
            return problems, hits
        if problems and not any(self._near(p) for p in problems):
            return problems, hits           # not in the library at all: another reading would only cost its minute
        emit(("status", "Reading it again more closely…"))
        size = second_size(ollama.sent_size(max(image.size)))
        second = reader.read(self.chat, self.model, reader.enhance(image), hint, think, long_side=size)
        self.reads.append(second)
        hits2 = [self._match(p) for p in second.problems]
        if len(second.problems) == len(problems):
            pairs = [(a, h) if h is not None else (b, h2)
                     for a, h, b, h2 in zip(problems, hits, second.problems, hits2)]
            return [p for p, _ in pairs], [h for _, h in pairs]
        if sum(h is not None for h in hits2) > sum(h is not None for h in hits) or not problems:
            return second.problems, hits2
        return problems, hits

    # ------------------------------------------------------------------------------------------ solving --
    def _qwen(self):
        """The local solver, or (None, why not)."""
        try:
            found = self._models()
        except ollama.OllamaError as exc:
            return None, exc
        name = ollama.pick(found, "tools", self.wanted, avoid="thinking")
        if name is None:
            return None, ollama.NotReady("None of the models installed in Ollama can use tools. Run: "
                                         + ollama.PULL_HINT)
        caps = dict(found)[name]
        # its own connection, so its time budget can stop it without stopping the turn
        return solver.OllamaBackend(ollama.Chat(self.url), name, False if "thinking" in caps else None), None

    def _gemini_backend(self):
        key, model, base = self._gemini
        if not key:
            return None
        return solver.GeminiBackend(gemini.Gemini(key, base), model or gemini.MODELS[0], gemini.MODELS)

    def _quick(self, problem: reader.Problem):
        """A confidence interval or a test of one or two means or proportions: the local model only copies the givens
        and Python solves it (seconds). (markdown, info) like a solve, or None for the full solver."""
        if not self.match or not quick.candidate(problem.markdown):
            return None
        backend, _ = self._qwen()
        if backend is None:
            return None
        start = time.perf_counter()
        self._backends = [backend]
        found = quick.solve(backend, problem.markdown)
        if found is None:
            return None
        seconds = round(time.perf_counter() - start, 1)
        answer = solver.answer_text(found.markdown)
        return found.markdown, {"from": f"quick:{found.kind}", "by": "quick", "agree": None, "rechecked": False,
                                "errors": {}, "example": "", "solutions": [
                                    {"solver": "quick", "model": "quick", "seconds": seconds, "checked": True,
                                     "answer": answer, "tool_log": [], "markdown": found.markdown}]}

    def _rules(self, problem: reader.Problem) -> str:
        """The table rules and formulas of the chapter the closest library problem is in (the book's rounding)."""
        if self.index is None or not self.match:
            return ""
        best = self.index.lookup(f"{problem.label} {problem.markdown}").best
        if best is None or best.score < lookup.LOW:
            return ""
        return "\n\n".join(x for x in (best.exercise.tables, best.exercise.conventions) if x)[:2500]

    def _example(self, problem: reader.Problem):
        """A library problem close to this one in wording (but not the same: it didn't match), with its worked
        solution, for the solver to follow the method of. (No example when matching is off: the eval would leak.)"""
        if self.index is None or not self.match:
            return "", ""
        best = self.index.lookup(f"{problem.label} {problem.markdown}").best
        if best is None or not best.exercise.has_problem or best.word_score < EXAMPLE_WORDS:
            return "", ""
        e = best.exercise
        return f"{e.problem_md}\n\n{e.solution_md}"[:5000], e.key

    def _solve(self, emit, problem: reader.Problem):
        """Solve with qwen and (with a key) Gemini at the same time; returns (the solution shown, log info)."""
        qwen, qwen_problem = self._qwen()
        gem = self._gemini_backend()
        jobs = {name: (backend, image) for name, backend, image in
                (("qwen", qwen, None), ("gemini", gem, self.source.image)) if backend is not None}
        if not jobs:
            raise qwen_problem
        self._backends = [b for b, _ in jobs.values()]
        results, used, cancelled = {}, {}, (lambda: self.chat.cancelled)
        finished = queue.Queue()        # who answers first sets the pace; the other gets only a short grace
        context = self._context(problem.markdown)
        example, example_key = self._example(problem)
        rules = self._rules(problem)

        def progress(name):
            def tell(count):
                self._steps[name] = count
                emit(("status", f"Solving… {max(self._steps.values())} calculations so far"))
            return tell

        def work(name, backend, image):
            try:
                used[name] = backend
                try:
                    results[name] = solver.solve(backend, problem.markdown, image, cancelled, context,
                                                 example=example, progress=progress(name), rules=rules)
                except gemini.GeminiError as exc:
                    # out of today's quota mid-solve: once more from the start on the next free model
                    fresh = solver.GeminiBackend(backend.client, backend.model, gemini.MODELS) \
                        if name == "gemini" and exc.kind == "quota" else None
                    if fresh is None or fresh.model == backend.model:
                        raise
                    used[name] = fresh
                    results[name] = solver.solve(fresh, problem.markdown, image, cancelled, context,
                                                 example=example, progress=progress(name), rules=rules)
            except BaseException as exc:  # noqa: BLE001 - kept: the other solver may still answer
                results[name] = exc
            finally:
                finished.put(name)

        threads = {n: threading.Thread(target=work, args=(n, b, i), daemon=True) for n, (b, i) in jobs.items()}
        timers = [threading.Timer(SOLVE_BUDGET, b.cancel) for b, _ in jobs.values()]      # a looping model stops
        for t in list(threads.values()) + timers:
            t.daemon = True
            t.start()
        cut = None
        if "qwen" in threads and "gemini" in threads:
            first = finished.get()
            other = "qwen" if first == "gemini" else "gemini"
            if isinstance(results.get(first), solver.Solution):
                # an answer exists: the other solver only cross-checks it, so it gets a little longer, not minutes
                threads[other].join(QWEN_GRACE if first == "gemini" else GEMINI_GRACE)
                if threads[other].is_alive():
                    cut = other
                    used_backend = qwen if other == "qwen" else gem
                    used_backend.cancel()
        for t in threads.values():
            t.join()
        for t in timers:
            t.cancel()
        if self.chat.cancelled:
            raise ollama.Cancelled()
        stopped = (ollama.Cancelled, gemini.Cancelled, ollama.OllamaError, gemini.GeminiError)
        if cut == "qwen" and isinstance(results.get("qwen"), stopped):
            results["qwen"] = solver.SolverError("stopped: Gemini had already answered")
        elif qwen is not None and qwen.chat.cancelled and isinstance(results.get("qwen"), stopped):
            partial = getattr(results["qwen"], "partial", "")
            if partial and "gemini" not in ok_names(results):     # keep the work done so far: it is still useful
                results["qwen"] = solver.Solution(
                    partial + f"\n\n*Stopped after {SOLVE_BUDGET // 60} minutes, so this solution may be unfinished. "
                    "A free Gemini key (model menu at the top) helps with long problems.*",
                    qwen.model, [], float(SOLVE_BUDGET), checked=False)
            else:
                results["qwen"] = solver.SolverError(
                    f"This problem took the model on this computer more than {SOLVE_BUDGET // 60} minutes, so it was "
                    "stopped. A free Gemini key (model menu at the top) helps with long problems.")
        if gem is not None and gem.client.cancelled and isinstance(results.get("gemini"), stopped):
            results["gemini"] = gemini.GeminiError("Gemini took too long this time.", "busy")
        errors = {n: f"{type(r).__name__}: {r}" for n, r in results.items() if isinstance(r, BaseException)}
        if qwen is None:
            errors["qwen"] = f"{type(qwen_problem).__name__}: {qwen_problem}"
        if isinstance(results.get("gemini"), gemini.GeminiError):
            self.gemini_problem = str(results["gemini"])
        ok = {n: r for n, r in results.items() if isinstance(r, solver.Solution)}
        if not ok:
            raise results.get("qwen") or results["gemini"]       # the local model's reason first: it is always there
        agree, rechecked = None, False
        shown = ok.get("gemini") or ok["qwen"]
        if len(ok) == 2:
            emit(("status", "Checking the answer…"))
            agree = solver.agree(ok["gemini"].markdown, ok["qwen"].markdown, problem.markdown)
            if agree is False:
                try:
                    shown = solver.recheck(used["gemini"], ok["gemini"], solver.answer_text(ok["qwen"].markdown),
                                           problem.markdown, cancelled)
                    rechecked = True
                except (gemini.GeminiError, gemini.Cancelled, solver.SolverError) as exc:
                    errors["recheck"] = f"{type(exc).__name__}: {exc}"
        info = {"from": f"solver:{shown.model}", "agree": agree, "rechecked": rechecked, "errors": errors,
                "example": example_key,
                "solutions": [{"solver": n, "model": s.model, "seconds": s.seconds, "checked": s.checked,
                               "answer": solver.answer_text(s.markdown), "tool_log": s.tool_log,
                               "markdown": s.markdown} for n, s in ok.items()]}
        return shown, info

    def _stream(self, emit, markdown: str, problem, info: dict):
        if self.prerender is not None:
            self.prerender(markdown)
        emit(("start", None))
        pieces = re.findall(r"\s*\S+", markdown)
        pace = min(self.pace, STREAM_MAX / max(1, len(pieces) // WORDS))      # a long answer is not slower to show
        for i in range(0, len(pieces), WORDS):
            if self.chat.cancelled:
                raise ollama.Cancelled()
            emit(("text", "".join(pieces[i:i + WORDS])))
            time.sleep(pace)
        self.answers.append({"problem": problem.markdown if problem else "", "label": problem.label if problem else "",
                             **info, "answer": markdown})
        emit(("end", markdown))

    def _log(self, error):
        if self.log_path is None:
            return
        entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "source": self.source.name,
                 "hash": self.source.digest(), "typed": self.source.image is None, "model": self.model,
                 "reads": [{"seconds": r.seconds, "raw": r.raw} for r in self.reads], "answers": self.answers,
                 "choices": [label for label, _ in self.choices],
                 "stopped": isinstance(error, ollama.Cancelled),
                 "error": None if error is None or isinstance(error, ollama.Cancelled) else
                 f"{type(error).__name__}: {error}"}
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:      # the history is a convenience: never lose the answer over it
            logging.getLogger("plotstudio").error("Couldn't write the Notebook history %s: %s", self.log_path, exc)


class Checker(Turn):
    """Solves a Pending answer again, independently, on the solver that did NOT give it (Gemini when it has a key
    and isn't busy, else the local model). Run with `check(pending)` in a worker; `cancel()` stops it."""

    def __init__(self, url: str = ollama.DEFAULT_URL, wanted_model: str = "", gemini_key: str = "",
                 gemini_model: str = "", gemini_base: str = gemini.BASE_URL):
        super().__init__(Source("re-check"), None, url, wanted_model, gemini_key=gemini_key,
                         gemini_model=gemini_model, gemini_base=gemini_base)

    def _backend(self, by: str):
        gem = self._gemini_backend() if by != "gemini" else None
        if gem is not None and gem.busy_until.get(gem.model, 0) < time.time():
            return gem, True            # Gemini also sees the picture
        qwen, why = self._qwen()
        if qwen is None:
            raise why
        return qwen, False

    def check(self, pending: verify.Pending) -> verify.Verdict:
        backend, with_picture = self._backend(pending.by)
        self._backends = [backend]
        timer = threading.Timer(SOLVE_BUDGET, backend.cancel)       # a looping model is stopped, as in a turn
        timer.daemon = True
        timer.start()
        try:
            solution = solver.solve(backend, pending.problem, pending.image if with_picture else None,
                                    lambda: self.chat.cancelled, pending.context, verify.SYSTEM)
        finally:
            timer.cancel()
        return verify.judge(pending, solution)
