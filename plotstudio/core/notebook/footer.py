"""What a stored answer says about itself: where in the book it is from, that it matches the book, what to watch
out for, the chapter's formulas, and the next exercises of the section (type a number to solve one)."""
from __future__ import annotations

import re

from .library import Exercise, Library

NEXT = 2            # exercises of the same section offered after an answer
MAX_FORMULAS = 8    # bullets of the chapter's formulas shown


def _where(e: Exercise) -> str:
    topic = re.sub(r"^\w+\s+[—-]\s+", "", e.topic) if e.topic else ""        # "Lind — Chapter 9, Section 9.3: ..."
    book = f"{e.book.title()}, {e.edition} edition" if e.edition else e.book.title()
    return f"{book} · {topic} · Exercise {e.number}" if topic else f"{book} · Exercise {e.number}"


def book_footer(e: Exercise, library: Library) -> str:
    """Markdown to put after a stored solution; '' for an exercise with nothing to add."""
    parts = [f"*From {_where(e)}*"]
    if e.checker_note:
        note = e.checker_note
        parts.append(f"**{note}**" if note.startswith("Matches") else f"**Checked:** {note}")      # "Matches Lind Appendix C"
    if e.caution_note:
        parts.append(f"**Watch out.** {e.caution_note}")
    bullets = [line for line in e.conventions.split("\n") if line.startswith("- ")][:MAX_FORMULAS]
    if bullets:
        parts.append("**Formulas for this chapter**\n\n" + "\n".join(bullets))
    following, nxt = [], e
    while len(following) < NEXT:
        nxt = library.neighbour(nxt, +1)
        if nxt is None or nxt.topic != e.topic:
            break
        following.append(nxt.number)
    if following:
        parts.append(f"**Next in this section:** {', '.join(following)}. Type a number to solve it.")
    return "\n\n" + "\n\n".join(parts)
