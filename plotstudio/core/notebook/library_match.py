"""When a problem that was read may be answered from the user's solution library: only when it is surely the same
problem with the same numbers. Anything less returns None (never a question to the user)."""
from __future__ import annotations

import functools
from collections import Counter
from typing import Optional

from . import lookup
from .library import Exercise

MIN_NUMBERS = 3      # this many numbers, found in no other exercise, identify a problem whose words are few
# Few numbers say little: "For the marbles of Exercise 1.1, find the chance the first is blue" has the same numbers
# as 1.2 ("... that the two have different colours"). Then the picture's printed exercise number or nearly the same
# words are needed; anything else is solved live instead, which is cheap next to a wrong stored answer.
FEW = 2
SMALL = {"0", "1", "2"}
WORDS_WHEN_FEW = 0.9


def problem_numbers(text: str) -> Counter:
    """The numbers of a problem text, as a multiset, without a leading exercise label ('3.13 A box ...').
    A mention of another exercise ('ex1.28') counts once: saying "as in Exercise 1.28" again isn't new data."""
    if lookup.leading_label(text):
        text = lookup._LABEL.sub(" ", text, count=1)
    found = Counter(lookup.numbers(text))
    return Counter({k: 1 if k.startswith("ex") else v for k, v in found.items()})


def _key(numbers: Counter) -> frozenset:
    return frozenset(numbers.items())


@functools.lru_cache(maxsize=4)
def _sharing(index: lookup.Index) -> Counter:
    """How many exercises (with their own problem text) have each multiset of numbers."""
    return Counter(_key(problem_numbers(e.problem_md)) for e in index.library.exercises if e.has_problem)


def _covers(read: Counter, exercise: Exercise) -> bool:
    """Every number of the stored problem was read, and each other number read is one the stored solution uses:
    the book's page often says more than the library's shorter problem text ($R^2$ and $s^2$ in parts it left
    out), while a value the problem doesn't have ("use 3 draws") is in neither."""
    stored = problem_numbers(exercise.problem_md)
    if stored - read:
        return False
    known = set(lookup.numbers(exercise.solution_md))
    return all(k in known for k in read - stored)


def match(index: lookup.Index, markdown: str, label: str = "") -> Optional[Exercise]:
    """The library exercise for this problem, or None.

    A candidate from the lookup's top 3 may be used only if it has its own **Problem:** text and
      - exactly the same numbers, scoring at least lookup.HIGH, or at least lookup.LOW when no other exercise in
        the library has those numbers (at least MIN_NUMBERS of them: "Find t_0.025 for v = 14 ..." has few words);
      - or, when the picture prints its exercise number and that is this exercise's number, every one of its
        numbers was read and the rest are numbers its solution uses, scoring at least lookup.HIGH (the book's
        page says more than the library's shorter text; without the printed number this would match problems
        that only share 0, 1 and 2).
    It must be the only such candidate. So a textbook variant with a number changed is not given the stored answer
    (its stored value is missing), and two exercises with the same words (7.14 and 7.15) are told apart."""
    result = index.lookup(f"{label} {markdown}" if label else markdown)
    if not result.candidates:
        return None
    numbers = problem_numbers(markdown)
    unique = sum(numbers.values()) >= MIN_NUMBERS and _sharing(index)[_key(numbers)] == 1
    printed = lookup.leading_label(f"{label} {markdown}" if label else markdown)
    few = sum(n for k, n in numbers.items() if not k.startswith("ex") and k not in SMALL) < FEW

    def fits(c):
        if few and printed != c.exercise.number and c.word_score < WORDS_WHEN_FEW:
            return False
        stored = problem_numbers(c.exercise.problem_md)
        if stored == numbers:
            return c.score >= lookup.HIGH or (unique and c.score >= lookup.LOW)
        return printed == c.exercise.number and c.score >= lookup.HIGH and _covers(numbers, c.exercise)

    same = [c.exercise for c in result.candidates if c.exercise.has_problem and fits(c)]
    return same[0] if len(same) == 1 else None
