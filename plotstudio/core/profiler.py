"""Stage 1: what kind of data each column holds, plus its quality numbers.

Every column gets one kind:

    number     measurements and amounts (fare, age, price)
    category   groups and labels, including numbers with few values (pclass 1/2/3, ratings)
    date       dates and times (also date strings such as "2024-03-01")
    id         a different value in (almost) every row: passenger ids, ticket codes
    text       free text such as names and comments
    constant   the same value in every row
    empty      no values at all

Only number, category and date columns are used for plots; the others are reported.
The rules match the app's file scanner (``plotstudio.data``), so a column has the same
kind everywhere in the app.
"""
from __future__ import annotations

import difflib
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..data import (CATEGORY, CATEGORY_LIMIT, DATETIME, DISCRETE_LIMIT, EMPTY, ID_NAMES, NUMERIC,
                    _try_datetime, _try_numeric, is_boolish)
from ..data import TEXT as TEXT_SCAN

NUMBER, CAT, DATE, ID, TEXT, CONSTANT, EMPTY_KIND, SKIP = (
    "number", "category", "date", "id", "text", "constant", "empty", "skip")
USABLE = (NUMBER, CAT, DATE)

SAMPLE_ROWS = 50_000        # bigger files are analysed on a random sample of this many rows
HIGH_CARD = 50              # a category with more groups than this is shown as "top 20" only

KIND_SYNONYMS = {
    "number": NUMBER, "numeric": NUMBER, "num": NUMBER, "continuous": NUMBER, "float": NUMBER,
    "int": NUMBER, "integer": NUMBER, "measure": NUMBER,
    "category": CAT, "categorical": CAT, "cat": CAT, "binary": CAT, "class": CAT, "label": CAT,
    "group": CAT, "bool": CAT, "boolean": CAT, "ordinal": CAT, "discrete": CAT,
    "date": DATE, "datetime": DATE, "time": DATE, "timestamp": DATE,
    "id": ID, "identifier": ID, "key": ID,
    "text": TEXT, "string": TEXT, "str": TEXT,
    "skip": SKIP, "ignore": SKIP, "drop": SKIP, "none": SKIP,
}
KIND_LABELS = {NUMBER: "number", CAT: "category", DATE: "date", ID: "ID-like", TEXT: "text",
               CONSTANT: "constant", EMPTY_KIND: "empty", SKIP: "skipped"}


@dataclass
class ColumnProfile:
    name: str
    kind: str                       # number | category | date | id | text | constant | empty | skip
    rows: int                       # rows looked at (the sample, for big files)
    n_unique: int
    missing_pct: float              # 0..1
    skew: float = 0.0
    outlier_pct: float = 0.0        # share of values outside 1.5 IQR
    top_share: float = 0.0          # share of the most common value (categories)
    top_value: object = None
    minimum: float | None = None
    maximum: float | None = None
    median: float | None = None
    zeros_pct: float = 0.0
    infinite: int = 0               # ±inf values (treated as missing)
    ordered: bool = False           # a category made of numbers (1 < 2 < 3): keeps its order
    converted: str = ""             # "numbers" / "dates" when the values were stored as text
    unreadable: int = 0             # values a type override could not convert (now missing)
    requested: str = ""             # the kind asked for in overrides (kept when the column ends up empty)
    source: str = "auto"            # auto | override | target
    is_target: bool = False
    notes: list = field(default_factory=list)   # short plain-language flags, e.g. "77% missing"

    @property
    def usable(self) -> bool:
        return self.kind in USABLE

    @property
    def binary(self) -> bool:
        return self.kind == CAT and self.n_unique == 2

    @property
    def many_groups(self) -> bool:
        return self.kind == CAT and self.n_unique > HIGH_CARD

    @property
    def skewed(self) -> bool:
        return self.kind == NUMBER and abs(self.skew) > 1

    @property
    def positive(self) -> bool:
        """All values above 0: a log scale can show every value."""
        return self.minimum is not None and self.minimum > 0

    @property
    def label(self) -> str:
        if self.kind == CAT:
            return "category (2 values)" if self.n_unique == 2 else f"category ({self.n_unique} groups)"
        return KIND_LABELS.get(self.kind, self.kind)


@dataclass
class Profiled:
    """The analysed (sampled, cleaned) data and one profile per column."""
    df: pd.DataFrame                # cleaned working copy: numbers float, dates datetime64
    profiles: dict                  # name -> ColumnProfile, in column order
    total_rows: int                 # rows in the whole file
    renamed: dict                   # name used here -> original column label (only if changed)
    target: str | None = None

    @property
    def sampled(self) -> bool:
        return self.total_rows > len(self.df)

    def kind(self, name) -> str:
        return self.profiles[name].kind

    def names(self, *kinds) -> list:
        return [c for c, p in self.profiles.items() if not kinds or p.kind in kinds]


# --------------------------------------------------------------------------- #
# Checking the caller's input
# --------------------------------------------------------------------------- #

def clean_names(columns) -> list:
    """Column labels as unique strings (CSV files can repeat a header; frames can use numbers)."""
    out, seen = [], {}
    for c in columns:
        name = str(c).strip() or "column"
        base, k = name, 1
        while name in seen:
            k += 1
            name = f"{base} ({k})"
        seen[name] = True
        out.append(name)
    return out


def check_column(name, columns, what="column") -> str:
    """Return `name` if it is a column, else raise ValueError with the closest matches."""
    if name in columns:
        return name
    text = str(name)
    lower = {str(c).strip().lower(): c for c in columns}
    if text.strip().lower() in lower:            # 'Survived' for 'survived', 'age ' for 'age'
        return lower[text.strip().lower()]
    close = difflib.get_close_matches(text, [str(c) for c in columns], n=3, cutoff=0.6)
    hint = f" Did you mean {' or '.join(repr(c) for c in close)}?" if close else ""
    raise ValueError(f"{what} {text!r} is not a column of this data.{hint}")


def normalise_overrides(overrides, columns) -> dict:
    """{'Pclass': 'categorical', 'zip': 'text'} -> {'Pclass': 'category', 'zip': 'text'} (validated)."""
    out = {}
    for col, kind in (overrides or {}).items():
        name = check_column(col, columns, "override for")
        key = str(kind).strip().lower()
        if key not in KIND_SYNONYMS:
            allowed = "number, category, date, id, text or skip"
            raise ValueError(f"override {kind!r} for {name!r} is not a kind; use {allowed}.")
        out[name] = KIND_SYNONYMS[key]
    return out


# --------------------------------------------------------------------------- #
# Kind detection
# --------------------------------------------------------------------------- #

def _prose(values: pd.Series) -> bool:
    """Free text (names, comments) rather than codes: long values with spaces."""
    sample = values.dropna().astype(str).head(500)
    if sample.empty:
        return False
    return sample.str.len().mean() > 20 and sample.str.contains(" ").mean() > 0.5


def _integer_valued(x: pd.Series) -> bool:
    values = x.dropna().to_numpy(dtype=float)
    return values.size > 0 and bool(np.all(np.mod(values, 1) == 0))


def _number_kind(name: str, x: pd.Series) -> str:
    nn = x.dropna()
    nu = int(nn.nunique())
    if ID_NAMES.search(name) and nu >= 0.9 * len(nn):
        return ID
    if nu == len(x) > 20 and _integer_valued(nn):
        span = float(nn.max() - nn.min()) + 1
        if x.is_monotonic_increasing or x.is_monotonic_decreasing or span == len(x):
            return ID      # a row number / running id (also when the rows were shuffled)
    return CAT if nu <= DISCRETE_LIMIT else NUMBER


def _text_kind(name: str, s: pd.Series) -> str:
    nn = s.dropna()
    nu = int(nn.nunique())
    if nu <= CATEGORY_LIMIT or (nu <= 1000 and nu <= 0.05 * len(nn)):
        return CAT
    if ID_NAMES.search(name):
        return ID
    return TEXT if _prose(nn) else ID


def detect(name: str, s: pd.Series):
    """-> (kind, cleaned series, how it was converted: '' | 'numbers' | 'dates')."""
    nn = s.dropna()
    if nn.empty:
        return EMPTY_KIND, s, ""
    if pd.api.types.is_bool_dtype(s) or is_boolish(s):
        return CAT, s, ""
    if pd.api.types.is_datetime64_any_dtype(s):
        return DATE, s, ""
    if isinstance(s.dtype, pd.CategoricalDtype):
        return CAT, s, ""
    if pd.api.types.is_numeric_dtype(s):
        return NUMBER, s, ""
    converted = _try_numeric(s, ",")          # numbers stored as text ("1,234", "7.5")
    if converted is not None:
        return NUMBER, converted[0], "numbers"
    converted = _try_datetime(s)              # dates stored as text (works on pandas 1.5 to 3.x)
    if converted is not None:
        return DATE, converted[0], "dates"
    return _text_kind(name, s), s, ""


def kind_from_scan(info, s: pd.Series) -> str:
    """The kind for a column the app's file scanner already looked at (plotstudio.data.ColumnInfo)."""
    if getattr(info, "relabelled", "") == "skip":       # Column types: skip -> left out everywhere
        return SKIP
    if info.kind == EMPTY:
        return EMPTY_KIND
    if info.kind == TEXT_SCAN:
        return TEXT if _prose(s) else ID
    if info.is_id:
        return ID
    if info.kind == NUMERIC:
        return CAT if info.is_discrete else NUMBER
    if info.kind == DATETIME:
        return DATE
    if info.kind == CATEGORY:
        return CAT
    return TEXT if _prose(s) else ID


def _as_number(s: pd.Series):
    x = pd.to_numeric(s, errors="coerce")
    if pd.api.types.is_bool_dtype(x):
        x = x.astype(float)
    return x.astype(float), int(x.isna().sum() - s.isna().sum())


def _as_date(s: pd.Series):
    if pd.api.types.is_datetime64_any_dtype(s):
        return s, 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t = pd.to_datetime(s, errors="coerce")
    return t, int(t.isna().sum() - s.isna().sum())


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #

def _number_stats(p: ColumnProfile, x: pd.Series):
    values = x.to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return
    p.minimum, p.maximum = float(finite.min()), float(finite.max())
    p.median = float(np.median(finite))
    p.zeros_pct = float((finite == 0).mean())
    if finite.size > 2 and finite.std() > 0:
        with np.errstate(all="ignore"):
            skew = pd.Series(finite).skew()
        p.skew = float(skew) if np.isfinite(skew) else 0.0
    q1, q3 = np.percentile(finite, [25, 75])
    iqr = q3 - q1
    if iqr > 0:
        p.outlier_pct = float(((finite < q1 - 1.5 * iqr) | (finite > q3 + 1.5 * iqr)).mean())


def _notes(p: ColumnProfile):
    out = []
    if p.missing_pct >= 0.05:
        out.append(f"{p.missing_pct:.0%} missing")
    if p.converted:
        out.append(f"{p.converted} stored as text")
    if p.unreadable:
        out.append(f"{p.unreadable:,} value(s) could not be read (now missing)")
    if p.infinite:
        out.append(f"{p.infinite:,} infinite value(s) treated as missing")
    if p.skewed:
        side = "right" if p.skew > 0 else "left"
        out.append(f"{side}-skewed ({p.skew:.1f})")
    if p.kind == NUMBER and p.outlier_pct > 0.05:
        out.append(f"{p.outlier_pct:.0%} outliers")
    if p.kind == CAT and p.top_share > 0.9 and p.n_unique > 1:
        out.append(f"one value is {p.top_share:.0%} of rows")
    if p.many_groups:
        out.append(f"{p.n_unique:,} groups")
    p.notes = out


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #

def profile_frame(df: pd.DataFrame, target=None, overrides=None, infos=None,
                  sample_rows: int = SAMPLE_ROWS, seed: int = 0) -> Profiled:
    """Profile every column of df.

    target     the column a model would predict: always kept usable (never skipped as an ID)
    overrides  {'column': 'category'} forces a kind (number, category, date, id, text or skip)
    infos      the app's scan of the file ({name: ColumnInfo}); keeps the kinds identical to
               what the rest of the app shows
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("recommend() needs a pandas DataFrame")
    names = clean_names(df.columns)
    renamed = {new: orig for orig, new in zip(df.columns, names) if orig != new}   # name used -> label
    lookup = {}
    for orig, new in zip(df.columns, names):     # the first of two equal headers keeps the name
        lookup.setdefault(str(orig), new)
        lookup.setdefault(str(orig).strip(), new)
    total = len(df)
    data = df
    if total > sample_rows:
        data = df.sample(sample_rows, random_state=seed).sort_index()   # keep the file's row order
    data = data.copy()
    data.columns = names
    if target is not None:
        target = check_column(lookup.get(str(target), target), names, "target")
    forced = normalise_overrides({lookup.get(str(k), k): v for k, v in (overrides or {}).items()}, names)
    infos = {str(k): v for k, v in (infos or {}).items()}

    profiles = {}
    for name in names:
        s = data[name]
        info = infos.get(name) or infos.get(str(renamed.get(name, name)))   # the scan keeps the file's names
        if info is not None:
            kind, how = kind_from_scan(info, s), ""
        else:
            kind, s, how = detect(name, s)
        source, unreadable, infinite = "auto", 0, 0
        if name in forced:
            kind, source = forced[name], "override"
        if kind == NUMBER or (kind == CAT and pd.api.types.is_numeric_dtype(s)
                              and not pd.api.types.is_bool_dtype(s)):
            if not pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
                s, unreadable = _as_number(s)
            s = s.astype(float)
            infinite = int(np.isinf(s.to_numpy()).sum())
            if infinite:
                s = s.replace([np.inf, -np.inf], np.nan)
        elif kind == DATE:
            s, unreadable = _as_date(s)
        if kind == NUMBER and source == "auto" and info is None:
            kind = _number_kind(name, s)      # few values -> category, running numbers -> id
        if name == target and source == "auto" and kind in (ID, TEXT):
            # the target is never skipped: numbers are predicted as numbers, text as classes
            kind, source = (NUMBER if pd.api.types.is_numeric_dtype(s) else CAT), "target"
        data[name] = s

        nn = s.dropna()
        p = ColumnProfile(name=name, kind=kind, rows=len(s), n_unique=int(nn.nunique()),
                          missing_pct=float(1 - len(nn) / len(s)) if len(s) else 0.0,
                          converted=how, unreadable=unreadable, infinite=infinite, source=source,
                          is_target=name == target, requested=forced.get(name, ""))
        if kind != SKIP and nn.empty:
            p.kind = EMPTY_KIND
        elif kind != SKIP and p.n_unique <= 1:
            p.kind = CONSTANT
            p.top_value, p.top_share = nn.iloc[0], 1.0
        if p.kind == NUMBER:
            _number_stats(p, s)
        elif p.kind == CAT:
            counts = nn.value_counts(normalize=True)
            p.top_value, p.top_share = counts.index[0], float(counts.iloc[0])
            p.ordered = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
            if p.ordered:
                _number_stats(p, s)
        _notes(p)
        profiles[name] = p
    return Profiled(df=data, profiles=profiles, total_rows=total, renamed=renamed, target=target)


def profile_column(s: pd.Series, overrides: dict | None = None) -> ColumnProfile:
    """Profile one column: its kind and quality numbers (the original plot_recommender API).

    overrides  {'column name': 'category', ...}; only the entry for this column is used
    The whole column is profiled (no sampling); the column name comes from s.name.
    """
    name = clean_names([s.name if s.name is not None else "column"])[0]
    forced = {k: v for k, v in (overrides or {}).items() if str(k).strip() == name}
    frame = s.to_frame(name=name)
    return profile_frame(frame, overrides=forced, sample_rows=max(1, len(s))).profiles[name]
