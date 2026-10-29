"""What a piece of code changed in a table: rows, columns, and the cells that now differ."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple

import pandas as pd

MAX_ROWS = 5000        # changed rows remembered (the table view shows them first)
SAMPLES = 6


@dataclass
class Diff:
    rows_before: int
    rows_after: int
    cols_added: List[str] = field(default_factory=list)
    cols_removed: List[str] = field(default_factory=list)
    retyped: List[Tuple[str, str, str]] = field(default_factory=list)       # (column, old dtype, new dtype)
    cells: int = 0                                                          # cells that differ, in rows and columns both tables have
    by_column: dict = field(default_factory=dict)
    changed_rows: list = field(default_factory=list)                        # index labels
    samples: List[Tuple[Any, str, Any, Any]] = field(default_factory=list)  # (row label, column, before, after)

    @property
    def nothing(self) -> bool:
        return (self.rows_before == self.rows_after and not self.cols_added and not self.cols_removed
                and not self.retyped and self.cells == 0)

    def summary(self) -> str:
        """One plain sentence on what changed."""
        if self.nothing:
            return "Nothing changed."
        parts = []
        if self.cells:
            where = ", ".join(f"{c} ({n:,})" for c, n in sorted(self.by_column.items(), key=lambda kv: -kv[1])[:4])
            parts.append(f"{self.cells:,} cell{'s' if self.cells != 1 else ''} changed in {where}")
        if self.rows_after < self.rows_before:
            parts.append(f"{self.rows_before - self.rows_after:,} row(s) removed")
        elif self.rows_after > self.rows_before:
            parts.append(f"{self.rows_after - self.rows_before:,} row(s) added")
        if self.cols_added:
            parts.append("new column" + ("s " if len(self.cols_added) > 1 else " ") + ", ".join(self.cols_added[:5]))
        if self.cols_removed:
            parts.append("removed column" + ("s " if len(self.cols_removed) > 1 else " ") + ", ".join(self.cols_removed[:5]))
        if self.retyped:
            parts.append("changed type of " + ", ".join(f"{c} ({a} → {b})" for c, a, b in self.retyped[:4]))
        text = "; ".join(parts)
        return text[0].upper() + text[1:] + "."


def _plain(value):
    """A numpy number as a plain Python one (so it prints as 4.0, not np.float64(4.0))."""
    return value.item() if hasattr(value, "item") and getattr(value, "ndim", 1) == 0 else value


def diff_frames(before: pd.DataFrame, after: pd.DataFrame) -> Diff:
    d = Diff(len(before), len(after))
    d.cols_added = [c for c in after.columns if c not in before.columns]
    d.cols_removed = [c for c in before.columns if c not in after.columns]
    common = [c for c in before.columns if c in after.columns]
    d.retyped = [(c, str(before[c].dtype), str(after[c].dtype)) for c in common
                 if str(before[c].dtype) != str(after[c].dtype)]
    if before.index.is_unique and after.index.is_unique:
        rows = before.index.intersection(after.index)
        a, b = before.loc[rows, common], after.loc[rows, common]
    elif len(before) == len(after):                        # repeated labels: compare row by row
        a, b = before[common].reset_index(drop=True), after[common].reset_index(drop=True)
        rows = a.index
    else:
        return d
    if not common or len(rows) == 0:
        return d
    a, b = a.astype(object), b.astype(object)              # categories that changed, nullable <NA>: plain values
    different = (a.ne(b) & ~(a.isna() & b.isna())).fillna(True).astype(bool)
    d.by_column = {c: int(n) for c, n in different.sum().items() if n}
    d.cells = int(sum(d.by_column.values()))
    any_row = different.any(axis=1)
    d.changed_rows = list(rows[any_row.to_numpy()][:MAX_ROWS])
    for label in d.changed_rows[:SAMPLES * 3]:
        for c in common:
            if different.at[label, c] if not isinstance(different.at[label, c], pd.Series) else False:
                d.samples.append((label, c, _plain(a.at[label, c]), _plain(b.at[label, c])))
                break
        if len(d.samples) >= SAMPLES:
            break
    return d
