"""What a table looks like, in numbers: this is what Ceasar tells the user first and tells the model every turn."""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

MAX_COLUMNS_IN_PROMPT = 60
EXAMPLE_CHARS = 28


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    kind: str               # number | text | date | bool
    missing: int
    unique: int
    examples: List[str] = field(default_factory=list)


@dataclass
class Profile:
    rows: int
    columns: List[ColumnProfile]
    duplicates: int
    missing_cells: int
    numeric_text: List[str] = field(default_factory=list)      # text columns that are really numbers
    date_text: List[str] = field(default_factory=list)         # text columns that are really dates
    messy_text: List[str] = field(default_factory=list)        # text columns with stray spaces
    outliers: Dict[str, int] = field(default_factory=dict)     # number column -> values outside the IQR fences

    @property
    def cols(self) -> int:
        return len(self.columns)

    def by_kind(self, kind: str) -> List[ColumnProfile]:
        return [c for c in self.columns if c.kind == kind]

    @property
    def missing_columns(self) -> List[ColumnProfile]:
        return [c for c in self.columns if c.missing]


def _kind(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "bool"
    if pd.api.types.is_numeric_dtype(s):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    return "text"


def _dates(text: pd.Series) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(text, errors="coerce")


def _share(ok: pd.Series, of: pd.Series) -> float:
    return float(ok.sum()) / max(1, int(of.sum()))


def profile(df: pd.DataFrame) -> Profile:
    cols, numeric_text, date_text, messy, outliers = [], [], [], [], {}
    for name in df.columns:
        s = df[name]
        kind = _kind(s)
        present = s.dropna()
        examples = [str(v)[:EXAMPLE_CHARS] for v in present.head(3)]
        cols.append(ColumnProfile(str(name), str(s.dtype), kind, int(s.isna().sum()), int(s.nunique(dropna=True)),
                                  examples))
        if kind == "text" and len(present):
            text = present.astype(str)
            if _share(pd.to_numeric(text.str.replace(r"[,\s$€£%]", "", regex=True), errors="coerce").notna(),
                      text.notna()) >= 0.9:
                numeric_text.append(str(name))
            elif _share(_dates(text.head(500)).notna(), text.head(500).notna()) >= 0.9 \
                    and text.str.contains(r"\d").mean() > 0.9 and text.str.len().median() >= 6:
                date_text.append(str(name))
            if (text != text.str.strip()).any() or text.str.contains(r"\s{2,}").any():
                messy.append(str(name))
        if kind == "number" and len(present) >= 8:
            q1, q3 = present.quantile(0.25), present.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                n = int(((present < q1 - 1.5 * iqr) | (present > q3 + 1.5 * iqr)).sum())
                if n:
                    outliers[str(name)] = n
    return Profile(len(df), cols, int(df.duplicated().sum()), int(df.isna().sum().sum()), numeric_text, date_text,
                   messy, outliers)


def overview(p: Profile, name: str) -> str:
    """The first thing Ceasar says: plain words, no model needed."""
    kinds = {k: len(p.by_kind(k)) for k in ("number", "text", "date", "bool")}
    mix = ", ".join(f"{n} {k}" for k, n in kinds.items() if n)
    lines = [f"I looked at {name}: {p.rows:,} rows and {p.cols} columns ({mix})."]
    if p.missing_cells:
        worst = sorted(p.missing_columns, key=lambda c: -c.missing)[:3]
        lines.append(f"{len(p.missing_columns)} column{'s have' if len(p.missing_columns) != 1 else ' has'} gaps "
                     f"({p.missing_cells:,} cells), most in " + ", ".join(f"{c.name} ({c.missing:,})" for c in worst) + ".")
    else:
        lines.append("No column has missing values.")
    if p.duplicates:
        lines.append(f"{p.duplicates:,} row{'s are' if p.duplicates != 1 else ' is'} an exact copy of an earlier row.")
    if p.numeric_text:
        lines.append("Stored as text but really numbers: " + ", ".join(p.numeric_text[:5]) + ".")
    if p.date_text:
        lines.append("Stored as text but really dates: " + ", ".join(p.date_text[:5]) + ".")
    if p.messy_text:
        lines.append("Stray spaces in: " + ", ".join(p.messy_text[:5]) + ".")
    if p.outliers:
        lines.append("Values far outside the usual range in: " + ", ".join(list(p.outliers)[:5]) + ".")
    return " ".join(lines)


def for_model(p: Profile, name: str) -> str:
    """The briefing for the model: the table's shape and every column, not its rows."""
    out = [f"Table `df` from the file {name}: {p.rows:,} rows, {p.cols} columns, {p.duplicates:,} duplicate rows."]
    for c in p.columns[:MAX_COLUMNS_IN_PROMPT]:
        ex = "; ".join(repr(e) for e in c.examples)
        out.append(f"- {c.name!r} ({c.kind}, dtype {c.dtype}, {c.missing:,} missing, {c.unique:,} distinct) e.g. {ex}")
    if p.cols > MAX_COLUMNS_IN_PROMPT:
        out.append(f"- ... and {p.cols - MAX_COLUMNS_IN_PROMPT} more columns")
    return "\n".join(out)
