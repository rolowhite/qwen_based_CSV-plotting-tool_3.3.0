"""Small helpers for writing readable Python code as text.

The app never draws a plot directly. It writes plotting code as text, shows
that text to the user, and runs the very same text. These helpers keep the
generated code tidy: proper quoting, short argument lists, wrapped long lines.
"""
from __future__ import annotations

import keyword
import math
import re

import numpy as np
import pandas as pd

LINE_LIMIT = 88
# everything Python (or str.splitlines) may treat as the end of a line, and NUL (which compile() refuses)
_LINE_BREAKS = re.compile("[\r\n\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029\x00]+")


def clean_comment(text) -> str:
    """Text for a '# comment' in generated code, on one line. Column names, CSV values and formulas end up in
    comments; a line break inside them would turn the rest of the text into code that runs."""
    return _LINE_BREAKS.sub(" ", str(text))


class PlotError(Exception):
    """A problem the user can fix (wrong column type, too few rows, ...)."""


class Raw(str):
    """Code that is inserted as-is instead of being quoted, e.g. Raw('ax')."""


OMIT = object()  # keyword value meaning "leave this argument out"


def lit(value) -> str:
    """Return a Python literal for value (strings quoted, numbers tidy)."""
    if isinstance(value, Raw):
        return str(value)
    if value is None or isinstance(value, (bool, np.bool_)):
        return repr(None if value is None else bool(value))
    if isinstance(value, (int, np.integer)):
        return repr(int(value))
    if isinstance(value, (float, np.floating)):
        value = float(value)
        if math.isnan(value):
            return "float('nan')"
        if value.is_integer() and abs(value) < 1e15:
            return repr(value)
        return repr(round(value, 6)) if abs(value) >= 1e-4 else repr(value)
    if isinstance(value, tuple):
        inner = ", ".join(lit(v) for v in value)
        return f"({inner},)" if len(value) == 1 else f"({inner})"
    if isinstance(value, list):
        return "[" + ", ".join(lit(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{lit(k)}: {lit(v)}" for k, v in value.items()) + "}"
    if isinstance(value, pd.Timestamp):
        return f"pd.Timestamp({str(value)!r})"
    if isinstance(value, str):
        return repr(str(value))
    return repr(value)


def call(func: str, *args, **kwargs) -> str:
    """Write a function call, e.g. call('ax.set', title='Hi') -> "ax.set(title='Hi')".

    Keyword arguments whose value is OMIT are skipped. Calls longer than one
    line are split with one argument per line.
    """
    parts = [lit(a) for a in args]
    parts += [f"{key}={lit(val)}" for key, val in kwargs.items() if val is not OMIT]
    one_line = f"{func}({', '.join(parts)})"
    if len(one_line) <= LINE_LIMIT and "\n" not in one_line:
        return one_line
    body = "\n".join(f"    {p}," for p in parts)
    return f"{func}(\n{body}\n)"


def wrap_list(items) -> str:
    """A list literal, split over several lines when it is long."""
    flat = lit(list(items))
    if len(flat) <= LINE_LIMIT - 12:
        return flat
    lines, current = [], ""
    for item in items:
        piece = lit(item) + ", "
        if current and len(current) + len(piece) > LINE_LIMIT - 8:
            lines.append(current.rstrip())
            current = ""
        current += piece
    if current:
        lines.append(current.rstrip())
    return "[\n" + "\n".join("    " + ln for ln in lines) + "\n]"


def cols_expr(cols, all_columns, numeric_columns) -> str:
    """Code for a list of columns, as short as possible.

    A few columns become a plain list. Long selections such as "every number
    column" or "columns 1 to 784" become df.select_dtypes(...) / df.columns[...]
    so the generated script stays readable.
    """
    cols = list(cols)
    all_columns = list(all_columns)
    numeric_columns = list(numeric_columns)
    if len(cols) <= 8:
        return wrap_list(cols)
    if cols == all_columns:
        return "df.columns.tolist()"
    if cols == numeric_columns:
        return "df.select_dtypes('number').columns.tolist()"
    left_out = [c for c in numeric_columns if c not in set(cols)]
    if 0 < len(left_out) <= 3 and cols == [c for c in numeric_columns if c not in set(left_out)]:
        return f"df.select_dtypes('number').columns.drop({lit(left_out)}).tolist()"
    position = {c: i for i, c in enumerate(all_columns)}
    idx = [position.get(c, -1) for c in cols]
    if idx[0] >= 0 and idx == list(range(idx[0], idx[0] + len(idx))):
        return f"df.columns[{idx[0]}:{idx[-1] + 1}].tolist()"
    return wrap_list(cols)


def commented(code: str, comment: str) -> str:
    """'code  # comment', or the comment on its own line above when that would be too long."""
    comment = clean_comment(comment)
    last = code.split("\n")[-1]
    if len(last) + len(comment) + 4 <= LINE_LIMIT + 12:
        return f"{code}  # {comment}"
    return f"# {comment}\n{code}"


def is_identifier(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def indent(code: str, level: int = 1) -> str:
    pad = "    " * level
    return "\n".join(pad + line if line.strip() else line for line in code.split("\n"))
