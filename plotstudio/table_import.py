"""Saving an imported table (from a PDF or an image) where the user chose, with a note on where it came from."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

SIDECAR_SUFFIX = ".source.json"


def sidecar_path(csv_path) -> Path:
    """table.csv -> table.source.json (next to it)."""
    csv_path = Path(csv_path)
    return csv_path.with_name(csv_path.stem + SIDECAR_SUFFIX)


def save_table(df: pd.DataFrame, path, source: dict) -> Path:
    """Write `df` as a UTF-8 CSV at `path`, and next to it a JSON note of where it came from: the source file,
    page(s), how it was read, what to check, and every cell the user changed (`source` holds these)."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("save_table expects a pandas DataFrame")
    path = Path(path)
    df.to_csv(path, index=False, encoding="utf-8")
    note = {"saved": datetime.now().isoformat(timespec="seconds"), "csv": path.name, "rows": len(df),
            "columns": [str(c) for c in df.columns], **source}
    sidecar_path(path).write_text(json.dumps(note, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def edits_between(before: pd.DataFrame, after: pd.DataFrame) -> list:
    """The cells (and column names) the user changed in the review grid: [{row, column, old, new}]."""
    out = [{"row": "header", "column": i, "old": str(a), "new": str(b)}
           for i, (a, b) in enumerate(zip(before.columns, after.columns)) if str(a) != str(b)]
    for r in range(min(len(before), len(after))):
        for c in range(min(before.shape[1], after.shape[1])):
            a, b = before.iat[r, c], after.iat[r, c]
            a = "" if pd.isna(a) else str(a)
            if a != str(b):
                out.append({"row": r + 1, "column": str(after.columns[c]), "old": a, "new": str(b)})
    return out


def suggested_name(source, index=None) -> str:
    """report.pdf, table 2 -> report_table2.csv; photo.png -> photo_table.csv."""
    stem = Path(source).stem
    return f"{stem}_table{index}.csv" if index else f"{stem}_table.csv"
