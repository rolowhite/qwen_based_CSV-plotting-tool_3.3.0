"""Answers worked out live are remembered, so the same problem later is as fast as a library one.

An answer is only shown again once it is *verified*: two solvers agreed on it, or its background re-check agreed.
A reading (what the vision model made of a picture) is remembered by the picture's digest, but only together with
a verified answer or a library hit, so a misread is never pinned. One small JSON file, at most MAX_ENTRIES of each.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import List, Optional

MAX_ENTRIES = 400


def key(problem: str) -> str:
    """A problem's identity: its words and numbers, not its spacing or the case of its letters."""
    return re.sub(r"\s+", " ", problem.replace("**Problem:**", "")).strip().lower()


class Cache:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self.answers: dict = {}         # key -> {"markdown", "by", "verified", "time"}
        self.readings: dict = {}        # picture digest -> [[label, markdown], ...]
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8")) if self.path else {}
            self.answers, self.readings = saved.get("answers", {}), saved.get("readings", {})
        except (OSError, ValueError, AttributeError):
            pass

    # ---------------------------------------------------------------------------------------- answers --
    def answer(self, problem: str) -> Optional[dict]:
        """The verified answer for this problem, or None."""
        entry = self.answers.get(key(problem))
        return entry if entry and entry.get("verified") else None

    def remember(self, problem: str, markdown: str, by: str, verified: bool):
        with self._lock:
            old = self.answers.get(key(problem))
            if old and old.get("verified") and not verified:
                return                  # a verified answer is not replaced by an unverified one
            self.answers[key(problem)] = {"markdown": markdown, "by": by, "verified": verified,
                                          "time": time.time()}
            self._save()

    def verify(self, problem: str):
        with self._lock:
            if key(problem) in self.answers:
                self.answers[key(problem)]["verified"] = True
                self._save()

    def drop(self, problem: str):
        with self._lock:
            if self.answers.pop(key(problem), None) is not None:
                self._save()

    # --------------------------------------------------------------------------------------- readings --
    def reading(self, digest: str) -> Optional[List[list]]:
        return self.readings.get(digest)

    def remember_reading(self, digest: str, problems: List[list]):
        with self._lock:
            self.readings[digest] = problems
            self._save()

    def _save(self):
        for table in (self.answers, self.readings):
            while len(table) > MAX_ENTRIES:
                table.pop(next(iter(table)))                    # the oldest first
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"answers": self.answers, "readings": self.readings}, ensure_ascii=False),
                                 encoding="utf-8")
        except OSError:
            pass                        # a convenience: never lose an answer over it
