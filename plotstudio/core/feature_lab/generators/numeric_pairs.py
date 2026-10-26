"""numeric_ratio / numeric_diff: a / b and a - b of two number columns.

Only the columns that tell most about the target are paired (the 8 best), and only the 5 pairs
with the largest MI gain are suggested: never every combination.
"""
from __future__ import annotations

import itertools

import numpy as np

from ...pipeline import Step
from .. import scoring
from ..base import MIN_GAIN, Generator

TOP_COLUMNS = 8


def number_columns(ctx) -> list:
    cols = [c for c in ctx.df.columns if ctx.usable(c) and ctx.kind(c) != "date"
            and scoring.is_number(ctx.df[c]) and ctx.df[c].nunique(dropna=True) > 2]
    cols.sort(key=lambda c: (-ctx.mi(c), str(c)))
    return cols[:TOP_COLUMNS]


def scale(x) -> float:
    """The typical size of a column's values: the median of the values that are not 0 (a column that is 0 in
    most rows, like a delay, still has a size), else 0."""
    x = np.abs(np.asarray(x, dtype=float))
    x = x[np.isfinite(x) & (x != 0)]
    return float(np.median(x)) if x.size else 0.0


def oriented(ctx, a, b) -> tuple:
    """(numerator, denominator): divide by the column with fewer zeros among its values (gaps don't count),
    then by the smaller one."""
    xa, xb = ctx.numeric(a).dropna(), ctx.numeric(b).dropna()
    za = float((xa == 0).mean()) if len(xa) else 1.0
    zb = float((xb == 0).mean()) if len(xb) else 1.0
    if abs(za - zb) > 0.01:
        return (a, b) if zb < za else (b, a)
    return (a, b) if scale(xb) <= scale(xa) else (b, a)


class _Pairs(Generator):
    CAP = 5
    OP = ""

    def candidates(self, ctx, cols):
        raise NotImplementedError

    def suggest(self, df, profiles, target, ctx=None):
        scored = []
        for a, b in self.candidates(ctx, number_columns(ctx)):
            step = Step(self.OP, [a, b], self.name_for(a, b))
            if any(s.op == self.OP and set(s.cols) == {a, b} for s in ctx.pipeline):
                continue                                  # already in the pipeline
            try:
                values = ctx.make(step)
            except Exception:  # noqa: BLE001 - a pair that can't be computed is just not suggested
                continue
            mi = scoring.mutual_info(scoring.codes(values), ctx.target.codes)
            gain = mi - max(ctx.mi(a), ctx.mi(b))
            if gain > MIN_GAIN:
                scored.append((gain, a, b, step, values))
        scored.sort(key=lambda t: (-t[0], t[1], t[2]))
        out = []
        for gain, a, b, step, values in scored[: self.CAP]:
            step.name = ctx.new_name(step.name)
            s = self.make(step, self.title_for(a, b), [a, b], self.why(a, b))
            s.values = values
            out.append(s)
        return out


class NumericRatio(_Pairs):
    NAME, TITLE, OP = "numeric_ratio", "Ratio of two numbers", "ratio"

    def candidates(self, ctx, cols):
        return [oriented(ctx, a, b) for a, b in itertools.combinations(cols, 2)]

    def name_for(self, a, b):
        return f"{a}_per_{b}"

    def title_for(self, a, b):
        return f"{a} / {b}"

    def why(self, a, b):
        return f"{a} per unit of {b} (divide by 0 gives a gap): a rate often says more than the two amounts."


class NumericDiff(_Pairs):
    NAME, TITLE, OP = "numeric_diff", "Difference of two numbers", "diff"

    def candidates(self, ctx, cols):
        pairs = []
        for a, b in itertools.combinations(cols, 2):
            ma, mb = scale(ctx.numeric(a)), scale(ctx.numeric(b))
            if ma > 0 and mb > 0 and 0.1 <= ma / mb <= 10:     # only numbers of a similar size
                pairs.append((a, b) if ma >= mb else (b, a))
        return pairs

    def name_for(self, a, b):
        return f"{a}_minus_{b}"

    def title_for(self, a, b):
        return f"{a} - {b}"

    def why(self, a, b):
        return f"How far {a} is above {b}: a gap between two similar amounts can matter more than either."


RATIO = NumericRatio()
DIFF = NumericDiff()
