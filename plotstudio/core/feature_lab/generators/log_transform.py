"""log_transform: log(1 + x) of a skewed number column (|skew| > 1, no values below 0)."""
from __future__ import annotations

from ...pipeline import Step
from ..base import Generator


class LogTransform(Generator):
    NAME, TITLE, CAP = "log_transform", "Log of a skewed number", 6

    def suggest(self, df, profiles, target, ctx=None):
        out = []
        for c in df.columns:
            p = profiles.get(c)
            if p is None or not ctx.usable(c) or p.kind != "number" or abs(p.skew) <= 1:
                continue
            if p.minimum is None or p.minimum < 0 or ctx.pipeline.has("log1p", c) or str(c).lower().endswith("log"):
                continue                                  # negative values, or a log is already there
            step = Step("log1p", [c], ctx.new_name(f"{c}_log"))
            out.append(self.make(step, f"log(1 + {c})", [c],
                                 f"{c} is skewed ({p.skew:.1f}): a few huge values. The log keeps the order, so MI "
                                 "stays the same, but linear models and distance-based models fit it much better.",
                                 neutral=True))
        return out


GENERATOR = LogTransform()
