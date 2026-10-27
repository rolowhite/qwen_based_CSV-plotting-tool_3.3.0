"""Re-checking an answer after it was shown fast.

A stored library answer is already right (it was worked and checked when the library was written), so those are
not re-checked. What can be wrong is an answer from ONE live solver, and a library answer for a problem whose
numbers differed from the stored one (a blurred digit). Those are solved again, independently and in the
background; when the re-check is calculator-backed and its result disagrees, the page prints a Correction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import solver

SYSTEM = solver.SYSTEM + ("\n- This is an independent re-check of someone else's work: solve it from the start with your "
                          "own working. Mind sample versus population, one- versus two-sided, and which table value.")


@dataclass
class Pending:
    label: str
    problem: str            # Markdown
    shown: str              # the solution that was shown
    by: str                 # "qwen", "gemini" or "library"
    image: object = None
    context: str = ""


@dataclass
class Verdict:
    agrees: Optional[bool]              # None: nothing to compare
    solution: Optional[solver.Solution] = None
    correction: str = ""                # Markdown, only when the re-check is sure the shown answer was wrong


def supports(stored: str, other: str, problem: str) -> Optional[bool]:
    """Does a stored solution (most have no **Answer:** line) contain every result number of `other`'s answer?"""
    mine = [v for _, v in solver.result_numbers(other, problem)]
    if not mine:
        return None
    known = [v for _, v in solver._floats(stored)]
    return all(any(solver._close(x, k) for k in known) for x in mine)


def correction(p: Pending, solution: solver.Solution) -> str:
    head = f"Problem {p.label}" if p.label else "the problem"
    quote = " ".join(p.problem.split())[:140]
    return (f"**Correction for {head}.** I'm sorry, the answer I gave to *{quote}…* was wrong. I solved it again in "
            f"the background, and this is the right solution:\n\n{solution.markdown}")


def judge(p: Pending, solution: solver.Solution) -> Verdict:
    agrees = supports(p.shown, solution.markdown, p.problem) if p.by == "library" else \
        solver.agree(p.shown, solution.markdown, p.problem)
    # an unchecked re-check (a number the calculator never gave) is no reason to tell the user they were wrong
    return Verdict(agrees, solution, correction(p, solution) if agrees is False and solution.checked else "")
