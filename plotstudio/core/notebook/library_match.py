"""When a problem that was read may be answered from the user's solution library: only when it is surely the same
problem with the same numbers. Anything less returns None (never a question to the user)."""
from __future__ import annotations

from collections import Counter
from typing import Optional

from . import lookup
from .library import Exercise


def problem_numbers(text: str) -> Counter:
    """The numbers of a problem text, as a multiset, without a leading exercise label ('3.13 A box ...')."""
    if lookup.leading_label(text):
        text = lookup._LABEL.sub(" ", text, count=1)
    return Counter(lookup.numbers(text))


def match(index: lookup.Index, markdown: str, label: str = "") -> Optional[Exercise]:
    """The library exercise for this problem, or None. All three must hold: the lookup has one clear winner,
    that exercise has its own **Problem:** text, and both texts have exactly the same numbers (so a
    textbook variant with one number changed is not given the stored answer)."""
    result = index.lookup(f"{label} {markdown}" if label else markdown)
    if result.status != "match":
        return None
    exercise = result.best.exercise
    if not exercise.has_problem or problem_numbers(markdown) != problem_numbers(exercise.problem_md):
        return None
    return exercise
