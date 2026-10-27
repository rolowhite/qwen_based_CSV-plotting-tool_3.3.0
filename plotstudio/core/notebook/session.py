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
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from . import gemini, library_match, ollama, reader, solver

NOTHING = "I couldn't find a problem in this picture. Try a sharper picture, or mark just the problem."
PACE = 0.03              # seconds between streamed pieces
WORDS = 3                # words per piece
SECOND_READ = 1.5        # the second read sends the picture this much bigger (or smaller, past the size cap)


@dataclass
class Source:
    name: str
    image: object = None     # a PIL image: a picture, a screenshot, a PDF page or the marked part of one
    text: str = ""           # typed text: nothing to read
    hint: str = ""           # a digital PDF page's text layer
    load: Optional[Callable[[], Tuple[object, str]]] = None    # gives (image, hint) in the worker: a PDF page

    def digest(self) -> str:
        data = self.image.tobytes() if self.image is not None else (self.text or self.name).encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:16]


def second_size(first: int) -> int:
    """The long side for the second read: 1.5x the first, or 1/1.5x when that would pass the size cap."""
    bigger = round(first * SECOND_READ)
    return bigger if bigger <= ollama.LONG_SIDE_MAX else max(ollama.LONG_SIDE_MIN, round(first / SECOND_READ))


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
                 gemini_model: str = "", gemini_base: str = gemini.BASE_URL):
        self.source = source
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
        self.gemini_problem = None      # why Gemini didn't help this turn (the page shows it in the Model menu)
        self._backends = []

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
            emit(("status", "Solving…"))
            if not problems:
                self._stream(emit, NOTHING, None, {"from": "none"})
            for problem, exercise in zip(problems, hits):
                if exercise is not None:
                    markdown, info = exercise.solution_md, {"from": f"library:{exercise.key}"}
                else:
                    shown, info = self._solve(emit, problem)
                    markdown = shown.markdown
                self._stream(emit, answer_markdown(problem, markdown, unreadable), problem, info)
            return [a["answer"] for a in self.answers]
        except BaseException as exc:
            error = exc
            raise
        finally:
            self._log(error)

    # ------------------------------------------------------------------------------------------- steps --
    def _match(self, problem: reader.Problem):
        return library_match.match(self.index, problem.markdown, problem.label) if self.index is not None else None

    def _typed(self):
        problem = reader.Problem("", self.source.text.strip())
        return [problem], [self._match(problem)]

    def _pick_model(self):
        found = ollama.models(self.url)
        name = ollama.pick(found, "vision", self.wanted, avoid="thinking")
        if name is None:
            raise ollama.NotReady("None of the models installed in Ollama can read pictures. Run: "
                                  + ollama.PULL_HINT)
        caps = dict(found)[name]
        return name, (False if "thinking" in caps else None)      # thinking only slows plain copying down

    def _read(self, emit):
        self.model, think = self._pick_model()
        image, hint = self.source.image, self.source.hint
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
        emit(("status", "Reading it again more closely…"))
        size = second_size(ollama.sent_size(max(image.size)))
        second = reader.read(self.chat, self.model, image, hint, think, long_side=size)
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
            found = ollama.models(self.url)
        except ollama.OllamaError as exc:
            return None, exc
        name = ollama.pick(found, "tools", self.wanted, avoid="thinking")
        if name is None:
            return None, ollama.NotReady("None of the models installed in Ollama can use tools. Run: "
                                         + ollama.PULL_HINT)
        caps = dict(found)[name]
        return solver.OllamaBackend(self.chat, name, False if "thinking" in caps else None), None

    def _gemini_backend(self):
        key, model, base = self._gemini
        if not key:
            return None
        return solver.GeminiBackend(gemini.Gemini(key, base), model or gemini.MODELS[0], gemini.MODELS)

    def _solve(self, emit, problem: reader.Problem):
        """Solve with qwen and (with a key) Gemini at the same time; returns (the solution shown, log info)."""
        qwen, qwen_problem = self._qwen()
        gem = self._gemini_backend()
        jobs = {name: (backend, image) for name, backend, image in
                (("qwen", qwen, None), ("gemini", gem, self.source.image)) if backend is not None}
        if not jobs:
            raise qwen_problem
        self._backends = [b for b, _ in jobs.values()]
        results, cancelled = {}, (lambda: self.chat.cancelled)

        def work(name, backend, image):
            try:
                results[name] = solver.solve(backend, problem.markdown, image, cancelled)
            except BaseException as exc:  # noqa: BLE001 - kept: the other solver may still answer
                results[name] = exc

        threads = [threading.Thread(target=work, args=(n, b, i), daemon=True) for n, (b, i) in jobs.items()]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if self.chat.cancelled:
            raise ollama.Cancelled()
        errors = {n: f"{type(r).__name__}: {r}" for n, r in results.items() if isinstance(r, BaseException)}
        if qwen is None:
            errors["qwen"] = f"{type(qwen_problem).__name__}: {qwen_problem}"
        if isinstance(results.get("gemini"), gemini.GeminiError):
            self.gemini_problem = str(results["gemini"])
        ok = {n: r for n, r in results.items() if isinstance(r, solver.Solution)}
        if not ok:
            raise results.get("gemini") or results["qwen"]
        agree, rechecked = None, False
        shown = ok.get("gemini") or ok["qwen"]
        if len(ok) == 2:
            emit(("status", "Checking the answer…"))
            agree = solver.agree(ok["gemini"].markdown, ok["qwen"].markdown, problem.markdown)
            if agree is False:
                try:
                    shown = solver.recheck(gem, ok["gemini"], solver.answer_text(ok["qwen"].markdown),
                                           problem.markdown, cancelled)
                    rechecked = True
                except (gemini.GeminiError, solver.SolverError) as exc:
                    errors["recheck"] = f"{type(exc).__name__}: {exc}"
        info = {"from": f"solver:{shown.model}", "agree": agree, "rechecked": rechecked, "errors": errors,
                "solutions": [{"solver": n, "model": s.model, "seconds": s.seconds, "checked": s.checked,
                               "answer": solver.answer_text(s.markdown), "tool_log": s.tool_log,
                               "markdown": s.markdown} for n, s in ok.items()]}
        return shown, info

    def _stream(self, emit, markdown: str, problem, info: dict):
        emit(("start", None))
        pieces = re.findall(r"\s*\S+", markdown)
        for i in range(0, len(pieces), WORDS):
            if self.chat.cancelled:
                raise ollama.Cancelled()
            emit(("text", "".join(pieces[i:i + WORDS])))
            time.sleep(self.pace)
        self.answers.append({"problem": problem.markdown if problem else "", "label": problem.label if problem else "",
                             **info, "answer": markdown})
        emit(("end", markdown))

    def _log(self, error):
        if self.log_path is None:
            return
        entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "source": self.source.name,
                 "hash": self.source.digest(), "typed": self.source.image is None, "model": self.model,
                 "reads": [{"seconds": r.seconds, "raw": r.raw} for r in self.reads], "answers": self.answers,
                 "stopped": isinstance(error, ollama.Cancelled),
                 "error": None if error is None or isinstance(error, ollama.Cancelled) else
                 f"{type(error).__name__}: {error}"}
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:      # the history is a convenience: never lose the answer over it
            logging.getLogger("plotstudio").error("Couldn't write the Notebook history %s: %s", self.log_path, exc)
