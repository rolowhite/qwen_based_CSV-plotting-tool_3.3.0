"""binning: a number in k = 4..10 bins with about the same number of rows (edges learned on train)."""
from __future__ import annotations

from ...pipeline import Step
from .. import scoring
from ..base import Generator


class Binning(Generator):
    NAME, TITLE, CAP = "binning", "Equal-count bins", 4

    def suggest(self, df, profiles, target, ctx=None):
        found = []
        for c in df.columns:
            if not ctx.usable(c) or ctx.kind(c) != "number" or ctx.df[c].nunique(dropna=True) <= 20:
                continue
            if ctx.pipeline.has("bin", c):
                continue
            best = None
            for k in range(4, 11):
                step = Step("bin", [c], f"{c}_bin", {"k": k})
                values = ctx.make(step)
                mi = scoring.mutual_info(scoring.codes(values), ctx.target.codes)
                if best is None or mi > best[0] + 1e-4:
                    best = (mi, k, step, values)
            if best:
                found.append((best[0], c) + best[1:])
        found.sort(key=lambda t: (-t[0], t[1]))
        out = []
        for mi, c, k, step, values in found[: self.CAP]:
            step.name = ctx.new_name(step.name)
            s = self.make(step, f"{c} in {k} bins", [c],
                          f"Same order, fewer values ({k} bins with the same number of rows): it can't tell more than "
                          f"{c} itself (a small rise in the score is an estimation effect), but a linear model can "
                          "then treat low, middle and high values differently. Trees don't need it.",
                          neutral=True)
            s.values = values
            out.append(s)
        return out


GENERATOR = Binning()
