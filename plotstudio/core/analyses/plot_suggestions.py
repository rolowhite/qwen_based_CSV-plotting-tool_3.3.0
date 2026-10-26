"""Analysis plugin: which plots to draw first (the plot recommender), as one result object."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from ..plot_recommender import TOP_K, recommend
from .base import Result

NAME = "plot_suggestions"
TITLE = "Plot suggestions"


@dataclass
class PlotSuggestions(Result):
    """Ranked plot suggestions plus the warnings found on the way.

    target       the target column used (matched case-insensitively), or None
    suggestions  [Suggestion], best first; each knows its graph, columns, reason and numbers
    warnings     [Note], most serious first: leak > warn > check > info
    profiles     {column: ColumnProfile}: the kind of every column (after overrides)
    overrides    {column: kind} the kinds the user forced
    """
    target: Optional[str] = None
    suggestions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    profiles: dict = field(default_factory=dict)
    overrides: dict = field(default_factory=dict)

    def warnings_at(self, *levels) -> list:
        """The warnings of the given levels, e.g. warnings_at('leak', 'warn')."""
        return [w for w in self.warnings if w.level in levels]


def run(df: pd.DataFrame, target: Optional[str] = None, overrides: Optional[dict] = None, *,
        infos: Optional[dict] = None, top_k: int = TOP_K,
        progress: Optional[Callable[[float, str], None]] = None) -> PlotSuggestions:
    """Rank the plots to draw first for df.

    target     the column to predict (shown first; its strongest links follow)
    overrides  {'column': 'category'} forces a kind: number, category, date, id, text or skip
    infos      the app's scan of the file ({name: ColumnInfo}) so kinds match the rest of the app
    progress   optional callback progress(fraction 0..1, text)
    Raises ValueError for an unknown target / override (the message names the closest columns).
    """
    started = time.perf_counter()
    profiles, suggestions, notes = recommend(df, target=target, top_k=top_k, overrides=overrides,
                                             infos=infos, progress=progress)
    rows_used = next(iter(profiles.values())).rows if profiles else len(df)
    used_target = next((p.name for p in profiles.values() if p.is_target), None)
    forced = {p.name: p.requested for p in profiles.values() if p.requested}
    return PlotSuggestions(rows_used=rows_used, total_rows=len(df), seconds=time.perf_counter() - started,
                           target=used_target, suggestions=suggestions, warnings=notes, profiles=profiles,
                           overrides=forced)
