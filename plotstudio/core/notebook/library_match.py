"""When a problem that was read may be answered from the user's solution library: only when it is surely the same
problem with the same numbers. Anything less returns None (never a question to the user)."""
from __future__ import annotations

import functools
import re
from collections import Counter
from typing import Optional, Tuple

from . import lookup
from .library import Exercise

MIN_NUMBERS = 3      # this many numbers, found in no other exercise, identify a problem whose words are few
# Few numbers say little: "For the marbles of Exercise 1.1, find the chance the first is blue" has the same numbers
# as 1.2 ("... that the two have different colours"). Then the picture's printed exercise number or nearly the same
# words are needed; anything else is solved live instead, which is cheap next to a wrong stored answer.
FEW = 2
SMALL = {"0", "1", "2"}
WORDS_WHEN_FEW = 0.9
NEAR_WORDS = 0.8     # a printed exercise number plus words this alike allow one number to be misread (a blurred digit)
# Without a printed number: nearly the same words and most of the numbers still name the exercise. The stored answer
# is shown with a note saying which numbers differ, and the problem is solved again with its own numbers in the
# background (a Correction follows if that answer differs), so a textbook variant is never left with the wrong one.
LOOSE_WORDS = 0.8
LOOSE_NUMBERS = 0.3      # share of the read numbers' weight the exercise has (one of two misread still passes)


def problem_numbers(text: str) -> Counter:
    """The numbers of a problem text, as a multiset, without a leading exercise label ('3.13 A box ...').
    A mention of another exercise ('ex1.28') counts once: saying "as in Exercise 1.28" again isn't new data."""
    text = re.sub(r"^\s*\*\*Problem:?\*\*:?", " ", text)       # a stored problem and a read one are cut the same way
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


def _covers(read: Counter, exercise: Exercise, slack: int = 0) -> bool:
    """Every number of the stored problem was read, and each other number read is one the stored solution uses:
    the book's page often says more than the library's shorter problem text ($R^2$ and $s^2$ in parts it left
    out), while a value the problem doesn't have ("use 3 draws") is in neither."""
    stored = problem_numbers(exercise.problem_md)
    missing = sum((stored - read).values())
    known = set(lookup.numbers(exercise.solution_md))
    unknown = sum(n for k, n in (read - stored).items() if k not in known)
    # `slack` allows a misread digit: one number missing (read as another, or lost), never one only added
    return missing <= slack and unknown <= slack and (missing > 0 or unknown == 0)


def near(index: lookup.Index, markdown: str, label: str = "") -> bool:
    """Is this problem probably in the library, even if it isn't sure? (A second, closer reading is worth its time.)"""
    best = index.lookup(f"{label} {markdown}" if label else markdown).best
    return best is not None and best.score >= lookup.LOW


def differences(read: Counter, exercise: Exercise) -> str:
    """'read 0.73, the book has 0.75' for the one number that differs, '' when none does."""
    stored = problem_numbers(exercise.problem_md)
    a, b = sorted((read - stored).elements()), sorted((stored - read).elements())
    short = lambda xs: ", ".join(xs[:4]) + (" …" if len(xs) > 4 else "") or "nothing else"   # noqa: E731
    return f"read {short(a)}, the book has {short(b)}" if a or b else ""


def match_with_note(index: lookup.Index, markdown: str, label: str = "",
                    prefer: str = "") -> Tuple[Optional[Exercise], str]:
    """The library exercise for this problem, or None; the note says which number was read differently (or '').

    A candidate from the lookup's top 3 may be used only if it has its own **Problem:** text and
      - exactly the same numbers, scoring at least lookup.HIGH, or at least lookup.LOW when no other exercise in
        the library has those numbers (at least MIN_NUMBERS of them: "Find t_0.025 for v = 14 ..." has few words);
      - or, when the picture prints its exercise number and that is this exercise's number, every one of its
        numbers was read and the rest are numbers its solution uses, scoring at least lookup.HIGH (the book's
        page says more than the library's shorter text; without the printed number this would match problems
        that only share 0, 1 and 2);
      - or the printed number, nearly the same words (NEAR_WORDS) and all but one number: a blurred digit.
    Exercises of two books can share numbers and datasets (Walpole 1.4 and 10.107): when several fit, the printed
    number picks one, else the best score if it leads by lookup.MARGIN, else None. A textbook variant with a
    number changed and no printed number is not given the stored answer."""
    result = index.lookup(f"{label} {markdown}" if label else markdown)
    if not result.candidates:
        return None, ""
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
        if printed != c.exercise.number:
            return False
        return (c.score >= lookup.HIGH and _covers(numbers, c.exercise)) or \
            (c.word_score >= NEAR_WORDS and _covers(numbers, c.exercise, slack=1))

    same = [c for c in result.candidates if c.exercise.has_problem and fits(c)]
    if len(same) > 1:
        named = [c for c in same if c.exercise.number == printed]
        same = named or same
        liked = [c for c in same if prefer and c.exercise.book == prefer]
        same = liked if len(liked) == 1 else same        # the user's own book breaks a tie between two books
        if len(same) > 1 and same[0].score - same[1].score < lookup.MARGIN:
            return None, ""
    if not same:
        loose = [c for c in result.candidates if c.exercise.has_problem and c.word_score >= LOOSE_WORDS
                 and (c.number_score >= LOOSE_NUMBERS or not numbers)
                 and (printed is None or printed == c.exercise.number)]        # a printed number must agree
        if not loose or (len(loose) > 1 and loose[0].word_score - loose[1].word_score < 0.05):
            return None, ""
        found = loose[0].exercise
        return found, differences(numbers, found) or "the numbers are written differently"
    found = same[0].exercise
    return found, ("" if problem_numbers(found.problem_md) == numbers else differences(numbers, found))


def match(index: lookup.Index, markdown: str, label: str = "", prefer: str = "") -> Optional[Exercise]:
    """The library exercise for this problem, or None (see match_with_note)."""
    return match_with_note(index, markdown, label, prefer)[0]
