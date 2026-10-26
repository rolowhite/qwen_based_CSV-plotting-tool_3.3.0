"""Loading a CSV file and scanning its columns.

load_csv() detects the delimiter and text encoding, reads the file with
pandas, repairs the usual problems (numbers stored as text, date strings,
empty "Unnamed" columns) and works out what kind of data every column holds.
Every repair is also written down as a line of Python, so the exported script
loads the data exactly the way the app did.
"""
from __future__ import annotations

import csv
import re
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .codegen import lit

NUMERIC, CATEGORY, DATETIME, TEXT, EMPTY = "numeric", "category", "datetime", "text", "empty"

KIND_LABELS = {
    NUMERIC: "number",
    CATEGORY: "category",
    DATETIME: "date/time",
    TEXT: "text",
    EMPTY: "empty",
}

DELIMITERS = {"Auto": None, "Comma  ,": ",", "Semicolon  ;": ";", "Tab": "\t", "Pipe  |": "|"}
ENCODINGS = {"Auto": None, "UTF-8": "utf-8", "Windows-1252": "cp1252", "Latin-1": "latin-1"}

TARGET_NAMES = re.compile(
    r"^(target|label|labels|y|y_true|ytrue|true_label|actual|outcome|survived|transported|satisfaction|"
    r"churn|exited|default|diagnosis|species|is_[a-z_]+|has_[a-z_]+)$",
    re.I,
)
WEAK_TARGET_NAMES = re.compile(r"^(class|result|response|quality|grade|status)$", re.I)
ID_NAMES = re.compile(r"(^|[_\s])(id|idx|index|uuid)$|^unnamed: ?0$|^passengerid$", re.I)
DISCRETE_LIMIT = 15        # a number column with this few values can also act as a category
CATEGORY_LIMIT = 50        # a text column with this few values is a category


@dataclass
class ColumnInfo:
    name: str
    kind: str
    dtype: str
    count: int                 # non-missing values
    missing: int
    unique: int
    is_id: bool = False
    is_discrete: bool = False  # numeric column with few distinct values (e.g. 0/1, ratings)
    summary: str = ""
    converted: str = ""        # "numbers" / "dates" when converted from text
    relabelled: str = ""       # the kind the user chose under Column types ("" = as detected)

    @property
    def rows(self) -> int:
        return self.count + self.missing

    @property
    def missing_pct(self) -> float:
        return 100.0 * self.missing / self.rows if self.rows else 0.0

    @property
    def groupable(self) -> bool:
        """True if the column can split data into groups / colours."""
        return self.kind == CATEGORY or (self.kind == NUMERIC and self.is_discrete)

    @property
    def is_binary(self) -> bool:
        return self.unique == 2

    @property
    def skipped(self) -> bool:
        """Set to 'skip' under Column types: left out of the plot slots, suggestions, ideas and models."""
        return self.relabelled == "skip"

    @property
    def kind_label(self) -> str:
        label = KIND_LABELS[self.kind]
        if self.kind == NUMERIC and self.is_discrete:
            label = "number used as groups" if self.relabelled == "category" else "number (few values)"
        if self.is_id:
            label += " · ID"
        if self.relabelled:
            label += " · set by you" if self.relabelled != "skip" else " · skipped by you"
        return label


@dataclass
class RowSettings:
    """Which rows go into the plot."""
    mode: str = "all"          # all | first | range | sample
    first_n: int = 1000
    start: int = 0
    stop: int = 1000
    sample_n: int = 5000
    seed: int = 42
    query: str = ""
    dropna: bool = True
    auto_sample: bool = True


@dataclass
class Dataset:
    path: Path
    df: pd.DataFrame
    columns: dict
    load_code: list
    notes: list = field(default_factory=list)
    seconds: float = 0.0
    sep: str = ","
    encoding: str = "utf-8"
    header: bool = True
    base_columns: dict = field(default_factory=dict)   # the scan as loaded, kept once columns are relabelled

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def shape_text(self) -> str:
        r, c = self.df.shape
        return f"{r:,} rows × {c:,} columns"

    def info(self, column: str) -> ColumnInfo:
        return self.columns[column]

    def names(self, test=None) -> list:
        return [c for c, info in self.columns.items() if test is None or test(info)]

    def numeric(self, continuous_first=True, include_ids=False) -> list:
        cols = [c for c, i in self.columns.items() if i.kind == NUMERIC and (include_ids or not i.is_id)
                and not i.skipped]
        if continuous_first:
            cols.sort(key=lambda c: self.columns[c].is_discrete)
        return cols

    def groupable(self) -> list:
        return [c for c, i in self.columns.items() if i.groupable and not i.is_id and not i.skipped]

    def guess_target(self, numeric_ok=False):
        """Best guess at the column an ML model would predict."""
        infos = list(self.columns.values())
        def fits(i: ColumnInfo):
            if i.is_id or i.kind == EMPTY or i.skipped:
                return False
            if i.groupable and 2 <= i.unique <= 20:
                return True
            return numeric_ok and i.kind == NUMERIC
        for i in infos:
            if fits(i) and TARGET_NAMES.match(i.name.strip()):
                return i.name
        last = infos[-1] if infos else None   # ML files usually keep the target last
        if last and fits(last) and (last.unique <= 10 or numeric_ok):
            return last.name
        for i in infos:
            if fits(i) and WEAK_TARGET_NAMES.match(i.name.strip()):
                return i.name
        for word in ("target", "label", "price", "satisf", "survived"):
            for i in infos:
                if fits(i) and word in i.name.lower():
                    return i.name
        return None

    def summary_text(self) -> str:
        kinds = {}
        for i in self.columns.values():
            key = "number" if i.kind == NUMERIC else KIND_LABELS[i.kind]
            kinds[key] = kinds.get(key, 0) + 1
        parts = [f"{n} {k}" for k, n in kinds.items()]
        missing_cols = sum(1 for i in self.columns.values() if i.missing)
        total_missing = int(sum(i.missing for i in self.columns.values()))
        text = f"{self.shape_text}  ·  " + ", ".join(parts)
        if total_missing:
            text += f"  ·  {total_missing:,} missing values in {missing_cols} column(s)"
        else:
            text += "  ·  no missing values"
        return text


# --------------------------------------------------------------------------- #
# Detection helpers
# --------------------------------------------------------------------------- #

def detect_encoding(path: Path) -> str:
    raw = path.open("rb").read(2_000_000)
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as err:
        if err.start >= len(raw) - 3 and len(raw) == 2_000_000:
            return "utf-8"  # only a multi-byte character cut in half at the end of the sample
    try:
        raw.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        return "latin-1"


def detect_delimiter(text: str) -> str:
    lines = text.splitlines()
    if len(lines) > 1 and not text.endswith(("\n", "\r")):
        lines = lines[:-1]  # the sample may end in the middle of a line
    lines = [ln for ln in lines[:60] if ln.strip()]
    best, best_score = ",", -1.0
    for delim in (",", ";", "\t", "|"):
        try:
            widths = [len(row) for row in csv.reader(lines, delimiter=delim)]
        except csv.Error:
            continue
        if not widths:
            continue
        mode = max(set(widths), key=widths.count)
        if mode < 2:
            continue
        consistency = widths.count(mode) / len(widths)
        score = (2.0 if widths[0] == mode else 0.0) + consistency + min(mode, 100) / 1000
        if score > best_score:
            best, best_score = delim, score
    return best


def _looks_numeric(text: str) -> bool:
    try:
        float(text.strip().strip('"').replace(",", ""))
        return True
    except ValueError:
        return False


def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    v = float(v)
    if v == 0:
        return "0"
    if abs(v) >= 1e6 or abs(v) < 1e-3:
        return f"{v:.3g}"
    if v.is_integer():
        return f"{int(v):,}"
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def _short(value, width=24) -> str:
    text = str(value)
    return text if len(text) <= width else text[: width - 1] + "…"


def is_boolish(s: pd.Series) -> bool:
    """True for bool columns and text columns holding only True/False (plus gaps)."""
    if pd.api.types.is_bool_dtype(s):
        return True
    if pd.api.types.is_object_dtype(s):
        values = s.dropna()
        return not values.empty and all(isinstance(v, (bool, np.bool_)) for v in values.head(2000))
    return False


THOUSANDS = re.compile(r"^\s*-?\d{1,3}(,\d{3})+(\.\d+)?\s*$")
DECIMAL_COMMA = re.compile(r"^\s*-?\d+,\d+\s*$")
EU_THOUSANDS = re.compile(r"^\s*-?\d{1,3}(\.\d{3})+(,\d+)?\s*$")   # 1.234,56 (German, Danish, Brazilian ...)
EU_DOT = r"\.(?=\d\d\d(?:\D|$))"   # a dot between thousands: 1.234,56 and 12.345.678 but not 2.5 or 12.75
PLAIN_NUMBER = re.compile(r"^\s*-?\d+(\.\d+)?\s*$")


MISSING_MARKERS = {"?", "-", "--", ".", "na", "n/a", "nan", "null", "none", "missing", ""}


def _try_numeric(s: pd.Series, sep: str):
    """Return (converted series, code template) if the text column s really holds numbers."""
    values = s.dropna()
    if values.empty:
        return None
    text = values.astype(str).str.strip()
    real = int((~text.str.lower().isin(MISSING_MARKERS)).sum())   # '?', 'n/a', ... count as gaps
    if real == 0:
        return None
    sample = text.head(5000)
    converted = pd.to_numeric(s, errors="coerce")
    if converted.notna().sum() >= 0.95 * real:
        return converted, "pd.to_numeric({col}, errors='coerce')"
    if (sample.str.match(THOUSANDS) | sample.str.match(PLAIN_NUMBER)).mean() >= 0.9:
        converted = pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")
        if converted.notna().sum() >= 0.95 * real:
            return converted, "pd.to_numeric({col}.str.replace(',', '', regex=False), errors='coerce')"
    if sep != ",":
        # decimal commas with dots between the thousands: 1.234,56 -> 1234.56 (the decimal-comma reading below
        # would make it 1.234.56 and lose it as a gap when most of the column is below 1,000). Only the dots
        # between thousands go, so a cell typed with a point (2.5) stays 2.5 instead of becoming 25.
        eu = sample.str.match(EU_THOUSANDS)
        if (eu.any() or (len(text) > len(sample) and text.iloc[len(sample):].str.match(EU_THOUSANDS).any())) \
                and (eu | sample.str.match(DECIMAL_COMMA) | sample.str.match(PLAIN_NUMBER)).mean() >= 0.9:
            converted = pd.to_numeric(s.astype(str).str.replace(EU_DOT, "", regex=True)
                                      .str.replace(",", ".", regex=False), errors="coerce")
            if converted.notna().sum() >= 0.95 * real:
                return converted, (f"pd.to_numeric({{col}}.str.replace(r'{EU_DOT}', '', regex=True)"
                                   ".str.replace(',', '.', regex=False), errors='coerce')")
    if sep != "," and (sample.str.match(DECIMAL_COMMA) | sample.str.match(PLAIN_NUMBER)).mean() >= 0.9:
        converted = pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")
        if converted.notna().sum() >= 0.95 * real:
            return converted, "pd.to_numeric({col}.str.replace(',', '.', regex=False), errors='coerce')"
    return None


DAY_MONTH = re.compile(r"^\s*(\d{1,2})([./-])(\d{1,2})\2(?:\d{4}|\d{2})(?!\d)")


def _day_first(values: pd.Series):
    """True when the dates themselves say the day comes first (a first number above 12: 31/12/2024), False when
    the month does (a second number above 12: 12/31/2024), None when they can't tell. 'It parsed' is not enough:
    pandas 1.x reads 13/01/2024 as 13 January even when asked for the month first (so both orders parse every
    row), and pandas 2+ with the month first parses the 90% of day-first dates whose day is <= 12, wrongly."""
    parts = values.head(200_000).str.extract(DAY_MONTH).dropna()
    if len(parts) < 0.8 * min(len(values), 200_000):
        return None
    first, second = parts[0].astype(int) > 12, parts[2].astype(int) > 12
    if first.any() and not second.any():
        return True
    if second.any() and not first.any():
        return False
    if not first.any() and not second.any() and (parts[1] == ".").all():
        return True                                # 01.02.2024: dates written with dots are day first
    return None                                    # every date fits both orders (or the column mixes them)


def _try_datetime(s: pd.Series):
    """Return (converted series, dayfirst) if the text column s holds dates."""
    values = s.dropna().astype(str)
    if values.empty:
        return None
    sample = values.head(300)
    if sample.str.contains(r"\d").mean() < 0.9 or sample.str.len().median() < 6:
        return None
    hint = _day_first(values)
    def plausible(t: pd.Series) -> bool:
        """Mostly real calendar years: codes like 'T-00001' parse as year 1 and are not dates."""
        t = t.dropna()
        return not t.empty and t.dt.year.between(1700, 2200).mean() >= 0.9

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if hint is None:
            # the dates can't tell: the order that reads more of them, month first on a tie (as before)
            counts = {d: int(pd.to_datetime(sample, errors="coerce", dayfirst=d).notna().sum()) for d in (False, True)}
            order = (True, False) if counts[True] > counts[False] else (False, True)
        else:
            order = (hint, not hint)
        for dayfirst in order:
            parsed = pd.to_datetime(sample, errors="coerce", dayfirst=dayfirst)
            if parsed.notna().mean() < 0.9 or not plausible(parsed):
                continue
            converted = pd.to_datetime(s, errors="coerce", dayfirst=dayfirst)
            if converted.notna().sum() >= 0.9 * len(values) and plausible(converted):
                return converted, dayfirst
    return None


def scan_column(name: str, s: pd.Series) -> ColumnInfo:
    count = int(s.notna().sum())
    missing = int(len(s) - count)
    unique = int(s.nunique(dropna=True))
    dtype = str(s.dtype)
    info = ColumnInfo(name=name, kind=TEXT, dtype=dtype, count=count, missing=missing, unique=unique)
    if count == 0:
        info.kind = EMPTY
        info.summary = "all values missing"
        return info

    if pd.api.types.is_bool_dtype(s):
        info.kind = CATEGORY
    elif pd.api.types.is_numeric_dtype(s):
        info.kind = NUMERIC
        info.is_discrete = unique <= DISCRETE_LIMIT
    elif pd.api.types.is_datetime64_any_dtype(s):
        info.kind = DATETIME
    elif unique <= CATEGORY_LIMIT or (unique <= 1000 and unique <= 0.05 * count):
        info.kind = CATEGORY
    else:
        info.kind = TEXT

    # ID-like columns (unique for every row) are skipped by automatic suggestions
    if ID_NAMES.search(name.strip()):
        info.is_id = unique >= 0.9 * count
    elif unique == len(s) and len(s) > 20:
        if info.kind == NUMERIC:
            vals = s.to_numpy()
            info.is_id = bool(np.all(np.mod(vals, 1) == 0) and (s.is_monotonic_increasing or s.is_monotonic_decreasing))
        elif info.kind == TEXT:
            info.is_id = True

    if info.kind == NUMERIC:
        info.summary = f"min {_fmt(s.min())}  ·  mean {_fmt(s.mean())}  ·  max {_fmt(s.max())}"
    elif info.kind == DATETIME:
        info.summary = f"{s.min():%Y-%m-%d}  to  {s.max():%Y-%m-%d}"
    else:
        top = s.value_counts().head(3)
        info.summary = ", ".join(f"{_short(k, 16)} ({v:,})" for k, v in top.items())
        if info.kind == TEXT:
            info.summary = f"e.g. {_short(s.dropna().iloc[0], 30)}"
    return info


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_csv(path, sep=None, encoding=None, header=None) -> Dataset:
    """Read and scan a CSV file. sep/encoding/header None means "detect"."""
    started = time.perf_counter()
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    notes = []

    encoding = encoding or detect_encoding(path)
    with path.open("r", encoding=encoding, errors="replace", newline="") as fh:
        sample = fh.read(256_000)
    if not sample.strip():
        raise ValueError("The file is empty.")
    sep = sep or detect_delimiter(sample)

    lines = sample.splitlines()
    lead = 0                         # lines at the top with nothing in them but separators (",,," from Excel)
    for ln in lines:
        try:
            fields = next(csv.reader([ln], delimiter=sep), [])
        except csv.Error:
            break
        if any(f.strip() for f in fields):
            break
        lead += 1
    first_line = lines[lead] if lead < len(lines) else ""
    try:
        header_fields = next(csv.reader([first_line], delimiter=sep))
    except (csv.Error, StopIteration):
        header_fields = [first_line]
    named = [f for f in header_fields if f.strip()]
    if header is None:
        header = not (len(header_fields) > 1 and named and all(_looks_numeric(f) for f in named))
        if not header:
            notes.append("The first row looks like data, not column names, so the columns were "
                         "named col_1, col_2, … (change this under 'Advanced' when loading).")
    skip_space = sum(1 for f in header_fields[1:] if f.startswith(" ")) > len(header_fields[1:]) / 2

    kwargs = {}
    if sep != ",":
        kwargs["sep"] = sep
    if encoding != "utf-8":
        kwargs["encoding"] = encoding
    if not header:
        kwargs["header"] = None
    if skip_space:
        kwargs["skipinitialspace"] = True
    if any(ln.strip() for ln in lines[:lead]):          # blank lines pandas skips by itself; ",,," it does not
        kwargs["skiprows"] = lead
        notes.append(f"Skipped {lead} empty line(s) at the top of the file.")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            df = pd.read_csv(path, **kwargs)
        except pd.errors.ParserError:
            kwargs["on_bad_lines"] = "skip"
            df = pd.read_csv(path, **kwargs)
            notes.append("Some lines had the wrong number of fields and were skipped.")
        except UnicodeDecodeError:
            kwargs["encoding"] = encoding = "latin-1"
            df = pd.read_csv(path, **kwargs)

    args = [lit(path.as_posix())] + [f"{k}={lit(v)}" for k, v in kwargs.items()]
    code = [f"df = pd.read_csv({', '.join(args)})"]

    if not header:
        df.columns = [f"col_{i + 1}" for i in range(df.shape[1])]
        code.append("df.columns = [f'col_{i + 1}' for i in range(df.shape[1])]")
    else:
        df.columns = [str(c) for c in df.columns]

    empty_unnamed = [c for c in df.columns if c.startswith("Unnamed:") and df[c].isna().all()]
    if empty_unnamed:
        df = df.drop(columns=empty_unnamed)
        code.append(f"df = df.drop(columns={lit(empty_unnamed)})  # empty columns")
        notes.append(f"Dropped {len(empty_unnamed)} empty 'Unnamed' column(s).")

    columns = {}
    for name in df.columns:
        s = df[name]
        converted_as = ""
        if not (pd.api.types.is_numeric_dtype(s) or is_boolish(s)
                or pd.api.types.is_datetime64_any_dtype(s)):
            as_number = _try_numeric(s, sep)
            if as_number is not None:
                new, template = as_number
                bad = int(new.isna().sum() - s.isna().sum())
                df[name] = s = new
                converted_as = "numbers"
                expr = template.format(col=f"df[{lit(name)}]")
                code.append(f"df[{lit(name)}] = {expr}  # text -> numbers")
                if bad:
                    notes.append(f"'{name}': read as numbers; {bad:,} value(s) that were not numbers became missing.")
            else:
                as_date = _try_datetime(s)
                if as_date is not None:
                    new, dayfirst = as_date
                    bad = int(new.isna().sum() - s.isna().sum())
                    df[name] = s = new
                    converted_as = "dates"
                    if bad:
                        notes.append(f"'{name}': read as dates; {bad:,} value(s) that were not dates became missing.")
                    extra = ", dayfirst=True" if dayfirst else ""
                    code.append(f"df[{lit(name)}] = pd.to_datetime(df[{lit(name)}], errors='coerce'{extra})"
                                "  # text -> dates")
        info = scan_column(name, s)
        info.converted = converted_as
        columns[name] = info

    return Dataset(path=path, df=df, columns=columns, load_code=code, notes=notes,
                   seconds=time.perf_counter() - started, sep=sep, encoding=encoding, header=header)


def dataset_from_frame(df: pd.DataFrame, name: str = "data.csv") -> Dataset:
    """A Dataset for a DataFrame already in memory (e.g. seaborn.load_dataset): the same column
    scan as load_csv, without reading a file. The exported code starts from `df` as it is."""
    started = time.perf_counter()
    df = df.copy()
    names, seen = [], set()
    for c in df.columns:                   # repeated names (or 1 and "1") get a number, as the profiler does
        name = label = str(c)
        k = 1
        while name in seen:
            k += 1
            name = f"{label} ({k})"
        seen.add(name)
        names.append(name)
    df.columns = names
    columns = {c: scan_column(c, df[c]) for c in df.columns}
    code = ["# df: the DataFrame the data came from (it was not read from a file)"]
    return Dataset(path=Path(name), df=df, columns=columns, load_code=code,
                   seconds=time.perf_counter() - started)


def file_size_text(path) -> str:
    size = Path(path).stat().st_size
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:,.0f} {unit}" if unit == "bytes" else f"{size:,.1f} {unit}"
        size /= 1024
    return ""
