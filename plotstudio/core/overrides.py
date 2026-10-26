"""Column type overrides: "treat this column as a category".

Relabelling only: the values never change (turning text into numbers is a data step, part of the
cleaning pipeline). An override changes how the app treats a column everywhere: which plot slots
accept it, how the suggestions use it, what the Data summary calls it. 'auto' gives the detected
kind back.
"""
from __future__ import annotations

import copy

import pandas as pd

from ..data import CATEGORY, DATETIME, EMPTY, NUMERIC, TEXT, Dataset, is_boolish
from .profiler import KIND_SYNONYMS

AUTO = "auto"
CHOICES = (AUTO, "number", "category", "date", "id", "text", "skip")
LABELS = {
    AUTO: "auto (as detected)",
    "number": "number",
    "category": "category (groups)",
    "date": "date",
    "id": "ID (not plotted)",
    "text": "text (not plotted)",
    "skip": "skip (left out of the analysis)",
}


def normalise(kind: str) -> str:
    """'categorical' -> 'category', 'Auto' -> 'auto' (ValueError for anything else)."""
    key = str(kind).strip().lower()
    if key in (AUTO, "detected", ""):
        return AUTO
    if key not in KIND_SYNONYMS:
        raise ValueError(f"{kind!r} is not a column kind; use one of {', '.join(CHOICES)}")
    return KIND_SYNONYMS[key]


def base(ds: Dataset) -> dict:
    """The column scan as the file was loaded (stored the first time a column is relabelled)."""
    if not ds.base_columns:
        ds.base_columns = {name: copy.copy(info) for name, info in ds.columns.items()}
    return ds.base_columns


def allowed(ds: Dataset, column: str) -> list:
    """The kinds `column` can be relabelled to without changing any value."""
    info = base(ds)[column]
    s = ds.df[column]
    if info.kind == EMPTY:
        return [AUTO, "skip"]
    if pd.api.types.is_bool_dtype(s) or is_boolish(s):
        return [AUTO, "category", "skip"]
    if info.kind == NUMERIC:
        return [AUTO, "number", "category", "id", "skip"]
    if info.kind == DATETIME:
        return [AUTO, "date", "category", "skip"]
    return [AUTO, "category", "id", "text", "skip"]


def apply(ds: Dataset, overrides: dict | None) -> dict:
    """Relabel ds.columns for {column: kind}; columns not listed get their detected kind back.

    Returns the overrides now in effect ('auto' entries dropped). Raises ValueError for an unknown
    column or a kind the column can't take without changing its values."""
    original = base(ds)
    wanted = {}
    for col, kind in (overrides or {}).items():
        if col not in original:
            raise ValueError(f"{col!r} is not a column of {ds.name}")
        kind = normalise(kind)
        if kind != AUTO and kind not in allowed(ds, col):
            raise ValueError(f"'{col}' can't be used as {kind} without changing its values "
                             f"(it can be: {', '.join(allowed(ds, col))})")
        if kind != AUTO:
            wanted[col] = kind
    for col in ds.columns:
        ds.columns[col] = copy.copy(original[col])
    for col, kind in wanted.items():
        info = ds.columns[col]
        info.relabelled = kind
        info.is_id = kind == "id" or (info.is_id and kind == "skip")
        if kind == "number":
            info.is_discrete = False
        elif kind == "category":
            if info.kind == NUMERIC:
                info.is_discrete = True        # a number column that groups rows (like pclass)
            else:
                info.kind = CATEGORY
        elif kind == "text":
            info.kind = TEXT
    return wanted
