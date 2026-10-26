"""datetime_parts: year, month, day, weekday, weekend and hour of a date column."""
from __future__ import annotations

import pandas as pd

from ...pipeline import Step
from ..base import Generator

WHY = {
    "year": "The year: slow changes over the years (prices, habits) show up as one number.",
    "month": "The month: seasons repeat every year, a plain date can't show that.",
    "day": "The day of the month: paydays and month ends often matter.",
    "weekday": "The day of the week (Monday = 0): weekly rhythms repeat.",
    "is_weekend": "1 on Saturday and Sunday: weekends often behave differently.",
    "hour": "The hour of the day: daily rhythms repeat.",
}


class DatetimeParts(Generator):
    NAME, TITLE, CAP = "datetime_parts", "Parts of a date", 12

    def suggest(self, df, profiles, target, ctx=None):
        out = []
        for c in df.columns:
            if c == target.name or ctx.kind(c) != "date":
                continue
            d = pd.to_datetime(df[c], errors="coerce")
            if d.notna().sum() < 10:
                continue
            values = {"year": d.dt.year, "month": d.dt.month, "day": d.dt.day, "weekday": d.dt.weekday,
                      "is_weekend": d.dt.weekday >= 5, "hour": d.dt.hour}
            for part, v in values.items():
                if v[d.notna()].nunique() < 2:
                    continue                                    # e.g. every date in the same year
                step = Step("dt_part", [c], ctx.new_name(f"{c}_{part}"), {"part": part})
                out.append(self.make(step, f"{part.replace('_', ' ')} of {c}", [c], WHY[part]))
        return out


GENERATOR = DatetimeParts()
