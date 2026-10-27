"""When a problem that was read may be answered from the user's solution library: only when it is surely the same
problem with the same numbers. Anything less returns None (never a question to the user)."""
from __future__ import annotations

import functools
from collections import Counter
from typing import Optional

from . import lookup
from .library import Exercise

MIN_NUMBERS = 3      # this many numbers, found in no other exercise, identify a problem whose words are few


def problem_numbers(text: str) -> Counter:
    """The numbers of a problem text, as a multiset, without a leading exercise label ('3.13 A box ...')."""
    if lookup.leading_label(text):
        text = lookup._LABEL.sub(" ", text, count=1)
    return Counter(lookup.numbers(text))


def _key(numbers: Counter) -> frozenset:
    return frozenset(numbers.items())


@functools.lru_cache(maxsize=4)
def _sharing(index: lookup.Index) -> Counter:
    """How many exercises (with their own problem text) have each multiset of numbers."""
    return Counter(_key(problem_numbers(e.problem_md)) for e in index.library.exercises if e.has_problem)


def match(index: lookup.Index, markdown: str, label: str = "") -> Optional[Exercise]:
    """The library exercise for this problem, or None.

    A candidate from the lookup's top 3 may be used only if it has its own **Problem:** text and exactly the same
    numbers, and either it scores at least lookup.HIGH, or it scores at least lookup.LOW and no other exercise in
    the library has those numbers (at least MIN_NUMBERS of them: "Find t_0.025 for v = 14 ..." has few words).
    It must be the only such candidate. So a textbook variant with one number changed is not given the stored
    answer, and two exercises with the same words (7.14 and 7.15) are told apart by their numbers."""
    result = index.lookup(f"{label} {markdown}" if label else markdown)
    if not result.candidates:
        return None
    numbers = problem_numbers(markdown)
    unique = sum(numbers.values()) >= MIN_NUMBERS and _sharing(index)[_key(numbers)] == 1
    same = [c.exercise for c in result.candidates
            if c.exercise.has_problem and problem_numbers(c.exercise.problem_md) == numbers
            and (c.score >= lookup.HIGH or (unique and c.score >= lookup.LOW))]
    return same[0] if len(same) == 1 else None
