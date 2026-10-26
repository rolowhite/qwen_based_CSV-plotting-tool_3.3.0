"""rare_grouping: categories with fewer than 1% of the rows -> "Other" (the list is learned on train)."""
from __future__ import annotations

from ...pipeline import Step
from .. import scoring
from ..base import Generator

MIN_SHARE = 0.01


class RareGrouping(Generator):
    NAME, TITLE, CAP = "rare_grouping", "Rare groups as Other", 6

    def suggest(self, df, profiles, target, ctx=None):
        out = []
        for c in df.columns:
            if not ctx.usable(c) or ctx.kind(c) != "category" or scoring.is_number(df[c]):
                continue
            shares = df[c].value_counts(normalize=True, dropna=True)
            rare = shares[shares < MIN_SHARE]
            if len(shares) < 3 or rare.empty or (shares >= MIN_SHARE).sum() < 2 or ctx.pipeline.has("rare", c):
                continue
            step = Step("rare", [c], ctx.new_name(f"{c}_grouped"), {"min_share": MIN_SHARE, "other": "Other"})
            out.append(self.make(step, f"{c} with rare groups as Other", [c],
                                 f"{len(rare)} of the {len(shares)} groups of {c} have under 1% of the rows each; "
                                 "as one 'Other' group they stop adding noise."))
        return out


GENERATOR = RareGrouping()
