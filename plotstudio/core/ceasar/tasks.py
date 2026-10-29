"""The starter tasks Ceasar offers. Each one is pandas code (shown to the user, run by the sandbox, undoable), so a
task and an instruction typed in the chat go through exactly the same path.

kind  "report"  asks a question of the table (the result is shown, the table is not changed)
      "change"  edits the table
      "engine"  uses another part of the app (plot ideas, Feature Lab); the window handles those
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from .profile import Profile


@dataclass
class Task:
    id: str
    title: str                       # the button
    what: str                        # one line: what it does
    kind: str
    code: Optional[Callable[[Profile], str]] = None
    why: Callable[[Profile], str] = lambda p: ""         # why it is worth doing here ("" = not needed now)
    always: bool = False                                 # offered even when nothing calls for it
    follows: tuple = ()                                  # task ids worth doing next


def _list(names) -> str:
    return "[" + ", ".join(repr(n) for n in names) + "]"


def _plural(n: int, one: str, many: str) -> str:
    return f"{n:,} {one if n == 1 else many}"


def _names(names, one: str, many: str) -> str:
    """'Fare looks like ...' / 'Fare, Price look like ...'"""
    names = list(names)[:3]
    return f"{', '.join(names)} {one if len(names) == 1 else many}"


COUNT_MISSING = '''missing = df.isna().sum()
answer = pd.DataFrame({"missing": missing, "percent": (missing / len(df) * 100).round(1)})
answer = answer[answer["missing"] > 0].sort_values("missing", ascending=False)
'''
FILL_MISSING = '''for col in df.columns:
    if df[col].isna().any() and df[col].notna().any():
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].median())      # numbers: the middle value
        elif not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].fillna(df[col].mode().iloc[0])  # text: the most common value
'''
DROP_MISSING_COLUMNS = '''df = df.loc[:, df.isna().mean() <= 0.5]    # keep columns with at most half of their cells missing
'''
DROP_DUPLICATES = '''df = df.drop_duplicates()
'''
FIND_OUTLIERS = '''rows = []
for col in df.select_dtypes("number").columns:
    s = df[col].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    n = int(((s < low) | (s > high)).sum())
    if n:
        rows.append({"column": col, "outliers": n, "below": round(low, 3), "above": round(high, 3)})
answer = pd.DataFrame(rows, columns=["column", "outliers", "below", "above"])
'''
CLIP_OUTLIERS = '''for col in df.select_dtypes("number").columns:
    s = df[col].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    if q3 > q1:
        df[col] = df[col].clip(q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1))   # pull far values back to the fence
'''
SUMMARY = '''answer = df.describe(include="all").T
'''
CORRELATIONS = '''corr = df.select_dtypes("number").corr()
pairs = corr.where(np.triu(np.ones(corr.shape, dtype=bool), 1)).stack().reset_index()
pairs.columns = ["column A", "column B", "correlation"]
answer = pairs.reindex(pairs["correlation"].abs().sort_values(ascending=False).index).head(10).round(3)
'''


def _numeric_text(p: Profile) -> str:
    return "\n".join(f'df[{c!r}] = pd.to_numeric(df[{c!r}].astype(str).str.replace(r"[,\\s$€£%]", "", regex=True), '
                     f'errors="coerce")' for c in p.numeric_text) + "\n"


def _dates(p: Profile) -> str:
    return "\n".join(f"df[{c!r}] = pd.to_datetime(df[{c!r}], errors=\"coerce\")" for c in p.date_text) + "\n"


def _trim(p: Profile) -> str:
    return "\n".join(f'df[{c!r}] = df[{c!r}].map(lambda v: re.sub(r"\\s+", " ", v).strip() if isinstance(v, str) '
                     'else v)' for c in p.messy_text) + "\n"


TASKS: List[Task] = [
    Task("count_missing", "Count missing data", "Which columns have gaps, how many, and what share.", "report",
         lambda p: COUNT_MISSING, why=lambda p: (f"{_plural(len(p.missing_columns), 'column has', 'columns have')} "
                                                  f"missing values" if p.missing_cells else ""),
         always=True, follows=("fill_missing", "drop_missing_columns")),
    Task("fill_missing", "Fill the gaps", "Numbers get the median, text gets the most common value.", "change",
         lambda p: FILL_MISSING, why=lambda p: f"{p.missing_cells:,} cells are empty" if p.missing_cells else "",
         follows=("find_duplicates",)),
    Task("drop_missing_columns", "Drop columns that are mostly empty", "Removes columns with more than half missing.",
         "change", lambda p: DROP_MISSING_COLUMNS,
         why=lambda p: (f"{sum(c.missing > p.rows / 2 for c in p.columns)} column(s) are more than half empty"
                        if any(c.missing > p.rows / 2 for c in p.columns) else "")),
    Task("find_duplicates", "Remove duplicate rows", "Keeps the first copy of every identical row.", "change",
         lambda p: DROP_DUPLICATES, why=lambda p: _plural(p.duplicates, "row is a copy", "rows are copies")
         if p.duplicates else ""),
    Task("fix_numbers", "Turn text into numbers", "Columns of numbers stored as text (with commas or $).", "change",
         _numeric_text, why=lambda p: _names(p.numeric_text, "looks like numbers stored as text", "look like numbers stored as text")
         if p.numeric_text else ""),
    Task("fix_dates", "Turn text into dates", "Columns of dates stored as text.", "change", _dates,
         why=lambda p: _names(p.date_text, "looks like dates stored as text", "look like dates stored as text")
         if p.date_text else ""),
    Task("trim_text", "Tidy stray spaces", "Trims text and collapses repeated spaces.", "change", _trim,
         why=lambda p: _names(p.messy_text, "has stray spaces", "have stray spaces") if p.messy_text else ""),
    Task("find_outliers", "Find outliers", "Values far outside the usual range of each number column.", "report",
         lambda p: FIND_OUTLIERS, why=lambda p: _plural(len(p.outliers), "number column has", "number columns have")
         + " far-out values" if p.outliers else "", follows=("clip_outliers",)),
    Task("clip_outliers", "Pull outliers back to the fence", "Clips far-out values to the edge of the usual range.",
         "change", lambda p: CLIP_OUTLIERS),
    Task("summary", "Summarise every column", "Count, mean, spread, most common value.", "report",
         lambda p: SUMMARY, always=True),
    Task("correlations", "Find the strongest links", "The ten pairs of number columns that move together most.",
         "report", lambda p: CORRELATIONS, why=lambda p: "", always=False),
    Task("plot_ideas", "Suggest plots", "The plots worth drawing first, from the app's Plot ideas.", "engine",
         always=True),
    Task("feature_ideas", "Suggest new features", "New columns for a model, from the Feature Lab.", "engine",
         always=True),
]
BY_ID = {t.id: t for t in TASKS}


def suggest(p: Profile) -> List[tuple]:
    """(task, why) in the order worth doing: what the table calls for first, then the always-useful ones."""
    wanted = []
    for t in TASKS:
        if t.kind != "engine" or t.always:
            reason = t.why(p)
            if t.id == "correlations" and len(p.by_kind("number")) >= 2:
                reason = "see which number columns move together"
            if reason or t.always:
                wanted.append((t, reason))
    first = [w for w in wanted if w[1]]
    rest = [w for w in wanted if not w[1]]
    return first + rest
