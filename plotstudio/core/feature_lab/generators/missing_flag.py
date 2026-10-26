"""missing_flag: col_was_missing = 1 where a column with more than 5% gaps is empty."""
from __future__ import annotations

from ...pipeline import Step
from ..base import Generator

MIN_MISSING = 0.05


class MissingFlag(Generator):
    NAME, TITLE, CAP = "missing_flag", "Was the value missing?", 6

    def suggest(self, df, profiles, target, ctx=None):
        out = []
        for c in df.columns:
            p = profiles.get(c)
            if p is None or c == target.name or p.kind in ("empty", "constant", "skip"):
                continue
            share = float(df[c].isna().mean())
            if not MIN_MISSING < share < 1 or ctx.pipeline.has("missing_flag", c):
                continue
            step = Step("missing_flag", [c], ctx.new_name(f"{c}_was_missing"))
            out.append(self.make(step, f"{c} was missing", [c],
                                 f"{share:.0%} of {c} is empty. Models usually fill the gaps, which hides that a value "
                                 "was missing; the flag keeps it (gaps are often not random)."))
        return out


GENERATOR = MissingFlag()
