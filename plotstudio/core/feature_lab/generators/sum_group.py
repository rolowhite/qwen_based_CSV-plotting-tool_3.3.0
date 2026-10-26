"""sum_group: the sum of 2+ related number columns (e.g. siblings + parents -> family size).

Related means the same shape of numbers, never the same name pattern: small counts with zeros
(0, 1, 2 ...), or amounts that are 0 in many rows (money spent on several things).
"""
from __future__ import annotations

import itertools

import numpy as np

from ...pipeline import Step
from .. import scoring
from ..base import MIN_GAIN, Generator


def _groups(ctx) -> list:
    counts, amounts = [], []
    for c in ctx.df.columns:
        if not ctx.usable(c) or ctx.kind(c) == "date" or not scoring.is_number(ctx.df[c]):
            continue
        x = ctx.numeric(c).dropna()
        if len(x) < 10 or x.nunique() <= 2 or x.min() < 0:
            continue
        zeros = float((x == 0).mean())
        whole = bool(np.all(np.mod(x.to_numpy(), 1) == 0))
        if whole and x.max() <= 50 and zeros >= 0.05:
            counts.append(c)                       # small counts that include 0
        elif zeros >= 0.3 and x.nunique() > 15:
            amounts.append(c)                      # amounts that are 0 in many rows
    return [g for g in (counts, amounts) if len(g) >= 2]


def sum_name(cols) -> str:
    return "_plus_".join(cols) if len(cols) <= 3 else f"{cols[0]}_plus_{len(cols) - 1}_more"


class SumGroup(Generator):
    NAME, TITLE, CAP = "sum_group", "Sum of related numbers", 3

    def suggest(self, df, profiles, target, ctx=None):
        scored = []
        for group in _groups(ctx):
            sets = [list(p) for p in itertools.combinations(group[:8], 2)]
            if 2 < len(group) <= 12:
                sets.append(list(group))
            for cols in sets:
                if any(s.op == "sum" and set(s.cols) == set(cols) for s in ctx.pipeline):
                    continue
                step = Step("sum", cols, sum_name(cols))
                values = ctx.make(step)
                gain = scoring.mutual_info(scoring.codes(values), ctx.target.codes) - max(ctx.mi(c) for c in cols)
                if gain > MIN_GAIN:
                    scored.append((gain, cols, step, values))
        scored.sort(key=lambda t: (-t[0], t[1]))
        out = []
        for gain, cols, step, values in scored[: self.CAP]:
            step.name = ctx.new_name(step.name)
            s = self.make(step, " + ".join(cols), cols,
                          f"The total of {', '.join(cols)}: together they can say more than each one alone "
                          "(e.g. siblings + parents = family size).")
            s.values = values
            out.append(s)
        return out


GENERATOR = SumGroup()
