"""regex_extract: a word pulled out of text with a pattern (built-in presets, e.g. title from name)."""
from __future__ import annotations

from ...pipeline import Step
from .. import scoring
from ..base import Generator
from ..presets import PRESETS


class RegexExtract(Generator):
    NAME, TITLE, CAP = "regex_extract", "Pattern in text", 6

    def suggest(self, df, profiles, target, ctx=None):
        out = []
        for c in df.columns:
            if c == target.name or ctx.kind(c) not in ("text", "id", "category") or scoring.is_number(df[c]):
                continue
            filled = df[c].notna()
            if filled.sum() < 10 or df[c][filled].nunique() <= 10:
                continue
            for preset in PRESETS:
                if ctx.kind(c) not in preset.kinds:
                    continue
                step = Step("regex", [c], preset.output.format(col=c),
                            {"pattern": preset.pattern, "map": dict(preset.mapping), "min_share": preset.min_share,
                             "other": "Other", "preset": preset.key, "preset_title": preset.title})
                found = df[c].astype(str).where(filled).str.extract(preset.pattern, expand=False)
                if preset.mapping:      # map, not replace: pandas 2.2 warns when replace() downcasts all gaps
                    found = found.map(lambda v: preset.mapping.get(v, v))
                if found.notna()[filled].mean() < preset.min_match:
                    continue
                shares = found.value_counts(normalize=True)
                groups = int((shares >= preset.min_share).sum()) + int((shares < preset.min_share).any())
                if not 2 <= groups <= preset.max_groups + 1:
                    continue
                step.name = ctx.new_name(step.name)
                out.append(self.make(step, f"{preset.title} ({c})", [c], preset.why))
        return out


GENERATOR = RegexExtract()
