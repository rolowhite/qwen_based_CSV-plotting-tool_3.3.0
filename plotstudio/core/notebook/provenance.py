"""Where an answer came from and how far to trust it: one badge per result."""
from __future__ import annotations

from dataclasses import dataclass

from .library import Exercise

FROM_LIBRARY = "From your solutions"


@dataclass(frozen=True)
class Badge:
    kind: str        # "verified" | "caution" | "unchecked"
    label: str
    detail: str = ""


def for_exercise(e: Exercise) -> Badge:
    """The trust label of a stored solution, from its checker lines."""
    if e.caution_note:
        return Badge("caution", f"{FROM_LIBRARY} (checked, with a caution ⚠)", e.caution_note)
    if e.checker_note:
        return Badge("verified", f"{FROM_LIBRARY} (verified ✔)", e.checker_note)
    return Badge("unchecked", f"{FROM_LIBRARY} (no checker note)")
