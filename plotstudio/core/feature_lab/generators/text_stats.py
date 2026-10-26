"""text_stats: length, word count and digit count of a text column."""
from __future__ import annotations

from ...pipeline import Step
from .. import scoring
from ..base import Generator

WHY = {
    "length": "How long the text is: long names, tickets or comments often go with a certain kind of row.",
    "words": "How many words: e.g. people with long names often had titles or two family names.",
    "digits": "How many digits: codes with numbers and codes without often mean different groups.",
}


class TextStats(Generator):
    NAME, TITLE, CAP = "text_stats", "Text counts", 6

    def suggest(self, df, profiles, target, ctx=None):
        out = []
        for c in df.columns:
            if c == target.name or ctx.kind(c) not in ("text", "id") or scoring.is_number(df[c]):
                continue
            text = df[c].dropna().astype(str)
            if len(text) < 10:
                continue
            stats = ["length"]
            if text.str.contains(" ").mean() > 0.5:
                stats.append("words")
            if 0.05 < text.str.contains(r"\d").mean():
                stats.append("digits")
            for stat in stats:
                step = Step("text_stat", [c], ctx.new_name(f"{c}_{stat}"), {"stat": stat})
                out.append(self.make(step, f"{stat} of {c}", [c], WHY[stat]))
        return out


GENERATOR = TextStats()
