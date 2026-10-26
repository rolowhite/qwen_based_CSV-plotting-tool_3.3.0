"""The feature generators (plugins). Each has suggest(df, profiles, target, ctx) and apply(df, step)."""
from __future__ import annotations

from . import (binning, datetime_parts, log_transform, missing_flag, numeric_pairs, rare_grouping, regex_extract,
               sum_group, text_stats)

GENERATORS = [regex_extract.GENERATOR, sum_group.GENERATOR, numeric_pairs.RATIO, numeric_pairs.DIFF,
              datetime_parts.GENERATOR, text_stats.GENERATOR, missing_flag.GENERATOR, rare_grouping.GENERATOR,
              log_transform.GENERATOR, binning.GENERATOR]
BY_NAME = {g.NAME: g for g in GENERATORS}

__all__ = ["BY_NAME", "GENERATORS"]
