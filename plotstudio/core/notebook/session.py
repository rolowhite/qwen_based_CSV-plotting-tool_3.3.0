"""One Notebook turn: read the picture (or take the typed text), then write an answer for each problem in it.

For now an answer comes only from the user's own solution library, and only when library_match is sure (live
solving is the next phase). The answer is streamed in small pieces, the same way for every problem, so the page
never shows where it came from; that is written only to the local history file (one JSON line per turn).
A picture that doesn't give a sure match is read once more at another size before giving up.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from . import library_match, ollama, reader

NOT_YET = "I can't solve this one yet. Solving new problems is coming in the next update."
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

    def digest(self) -> str:
        data = self.image.tobytes() if self.image is not None else self.text.encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:16]


def second_size(first: int) -> int:
    """The long side for the second read: 1.5x the first, or 1/1.5x when that would pass the size cap."""
    bigger = round(first * SECOND_READ)
    return bigger if bigger <= ollama.LONG_SIDE_MAX else max(ollama.LONG_SIDE_MIN, round(first / SECOND_READ))


def answer_markdown(problem: reader.Problem, exercise, unreadable=()) -> str:
    """What the page shows for one problem: the problem as it was read, then the worked solution."""
    head = f"**Problem {problem.label}.**" if problem.label else "**Problem.**"
    if exercise is None:
        tail = NOT_YET
        if unreadable:
            tail += " Part of the picture couldn't be read: " + "; ".join(u.rstrip(".") for u in unreadable) + "."
        return f"{head}\n\n{problem.markdown}\n\n{tail}"
    return f"{head}\n\n{problem.markdown}\n\n**Solution.**\n\n{exercise.solution_md}"


class Turn:
    """Run with `run(emit)` in a worker thread; `cancel()` (from any thread) stops it with ollama.Cancelled.
    emit gets ("status", text), ("start", None), ("text", piece) and ("end", markdown) for each answer."""

    def __init__(self, source: Source, index=None, url: str = ollama.DEFAULT_URL, wanted_model: str = "",
                 log_path: Optional[Path] = None, pace: float = PACE):
        self.source = source
        self.index = index
        self.chat = ollama.Chat(url)
        self.url = url
        self.wanted = wanted_model
        self.log_path = log_path
        self.pace = pace
        self.model = None
        self.reads: List[reader.Reading] = []
        self.answers: List[dict] = []

    def cancel(self):
        self.chat.cancel()

    def run(self, emit: Callable) -> List[str]:
        error = None
        try:
            problems, hits = self._read(emit) if self.source.image is not None else self._typed()
            unreadable = self.reads[-1].unreadable if self.reads and all(r.unreadable for r in self.reads) else []
            emit(("status", "Solving…"))
            if not problems:
                self._stream(emit, NOTHING, None, None)
            for problem, exercise in zip(problems, hits):
                self._stream(emit, answer_markdown(problem, exercise, unreadable), problem, exercise)
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
        name = ollama.pick(found, "vision", self.wanted)
        if name is None:
            raise ollama.NotReady("None of the models installed in Ollama can read pictures. Run: "
                                  + ollama.PULL_HINT)
        caps = dict(found)[name]
        return name, (False if "thinking" in caps else None)      # thinking only slows plain copying down

    def _read(self, emit):
        self.model, think = self._pick_model()
        image, hint = self.source.image, self.source.hint
        emit(("status", "Reading the problem…"))
        first = reader.read(self.chat, self.model, image, hint, think)
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

    def _stream(self, emit, markdown: str, problem, exercise):
        emit(("start", None))
        pieces = re.findall(r"\s*\S+", markdown)
        for i in range(0, len(pieces), WORDS):
            if self.chat.cancelled:
                raise ollama.Cancelled()
            emit(("text", "".join(pieces[i:i + WORDS])))
            time.sleep(self.pace)
        self.answers.append({"problem": problem.markdown if problem else "", "label": problem.label if problem else "",
                             "from": f"library:{exercise.key}" if exercise is not None else "none",
                             "answer": markdown})
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
