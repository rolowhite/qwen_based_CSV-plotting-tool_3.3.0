"""Data changes as steps: the Pipeline behind undo / redo, clean.py, the notebook and submissions.

A step is plain data, for example

    {"op": "ratio", "cols": ["Fare", "family_size"], "name": "fare_per_person"}

Each operation ("op") knows two things:

* ``fit(step, df)``  learn what it needs from the TRAINING rows: bin edges, the categories to
  keep, a target-encoding table ... (most ops learn nothing)
* ``code(step)``     write the pandas lines that make the new column(s), with what was learned
  written in as plain numbers and lists

The Pipeline runs exactly those lines, the same way the app runs the plotting code it shows.
So the table in the app, the exported clean.py and the notebook are always identical, and a
test file is transformed with what was learned on the training file (nothing is refitted).

Nothing here imports tkinter; the window only calls these functions.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..codegen import clean_comment, lit, wrap_list

SAFE_BUILTINS = {"range": range, "len": len, "str": str, "float": float, "int": int, "bool": bool,
                 "abs": abs, "min": min, "max": max, "round": round}   # all the step code needs


class PipelineError(ValueError):
    """A step that can't be added or run (the message says why, in plain words)."""


# --------------------------------------------------------------------------- #
# Steps
# --------------------------------------------------------------------------- #

@dataclass
class Step:
    """One change to the table. `cols` are the columns it reads, `name` the column it makes."""
    op: str
    cols: list
    name: str
    params: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)      # learned on the training rows by fit()

    def __post_init__(self):
        self.cols = [str(c) for c in self.cols]
        self.name = str(self.name)
        if self.op not in OPS:
            raise PipelineError(f"Unknown step '{self.op}'. Known steps: {', '.join(sorted(OPS))}.")

    @property
    def fitted(self) -> bool:
        return not OPS[self.op].learns or bool(self.state)

    @property
    def outputs(self) -> list:
        """The columns this step adds."""
        return OPS[self.op].outputs(self)

    @property
    def label(self) -> str:
        """A short description for people, e.g. "Fare / family_size (divide by 0 -> missing)"."""
        return OPS[self.op].describe(self)

    def code(self) -> list:
        return OPS[self.op].code(self)

    def to_dict(self) -> dict:
        out = {"op": self.op, "cols": list(self.cols), "name": self.name}
        if self.params:
            out["params"] = copy.deepcopy(self.params)
        if self.state:
            out["state"] = copy.deepcopy(self.state)
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "Step":
        step = cls(op=data["op"], cols=list(data.get("cols", [])), name=data.get("name", ""),
                   params=copy.deepcopy(data.get("params", {})), state=copy.deepcopy(data.get("state", {})))
        OPS[step.op].check(step)
        return step


def col(name) -> str:
    return f"df[{lit(str(name))}]"


def rlit(pattern: str) -> str:
    """A regex as a raw string literal when that is possible (easier to read than escapes)."""
    if "'" not in pattern and not pattern.endswith("\\") and "\n" not in pattern and "\r" not in pattern:
        return f"r'{pattern}'"
    return repr(pattern)


def text(src: str) -> str:
    """Code for a column read as text (numbers become text, gaps stay gaps)."""
    return f"{src}.astype(str).where({src}.notna())"


def num_list(values) -> str:
    return "[" + ", ".join(lit(float(v)) for v in values) + "]"


def bins_lit(edges) -> str:
    inner = ", ".join(lit(float(e)) for e in edges)
    return f"[-np.inf, {inner}, np.inf]" if inner else "[-np.inf, np.inf]"


def as_number(s: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(s):
        return s.astype(float)
    return pd.to_numeric(s, errors="coerce").astype(float)


# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #

OPS: dict = {}


def register(cls):
    OPS[cls.key] = cls()
    return cls


class Op:
    key = ""
    title = ""
    learns = False           # fit() learns something from the training rows
    needs_target = False     # fit() reads the target column (target encoding)
    n_cols = 1               # how many input columns (0 = any number >= 1)

    def check(self, step: Step) -> None:
        if self.n_cols and len(step.cols) != self.n_cols:
            raise PipelineError(f"'{step.op}' needs {self.n_cols} column(s), got {len(step.cols)}.")
        if not self.n_cols and not step.cols:
            raise PipelineError(f"'{step.op}' needs at least one column.")
        if not step.name.strip():
            raise PipelineError("The new column needs a name.")

    def outputs(self, step: Step) -> list:
        return [step.name]

    def fit(self, step: Step, df: pd.DataFrame) -> dict:
        return {}

    def code(self, step: Step) -> list:
        raise NotImplementedError

    def describe(self, step: Step) -> str:
        return f"{self.title} of {', '.join(step.cols)}"


@register
class Ratio(Op):
    key, title, n_cols = "ratio", "ratio", 2

    def code(self, step):
        a, b = step.cols
        return [f"{col(step.name)} = ({col(a)} / {col(b)}).replace([np.inf, -np.inf], np.nan)  # divide by 0 -> missing"]

    def describe(self, step):
        return f"{step.cols[0]} / {step.cols[1]}"


@register
class Diff(Op):
    key, title, n_cols = "diff", "difference", 2

    def code(self, step):
        a, b = step.cols
        return [f"{col(step.name)} = {col(a)} - {col(b)}"]

    def describe(self, step):
        return f"{step.cols[0]} - {step.cols[1]}"


@register
class Sum(Op):
    key, title, n_cols = "sum", "sum", 0

    def check(self, step):
        super().check(step)
        if len(step.cols) < 2:
            raise PipelineError("A sum needs at least two columns.")

    def code(self, step):
        expr = " + ".join(col(c) for c in step.cols)
        offset = step.params.get("offset", 0)
        if offset:
            expr += f" + {lit(offset)}"
        return [f"{col(step.name)} = {expr}"]

    def describe(self, step):
        offset = step.params.get("offset", 0)
        return " + ".join(step.cols) + (f" + {lit(offset)}" if offset else "")


@register
class Bin(Op):
    key, title, learns = "bin", "equal-count bins", True

    def fit(self, step, df):
        k = int(step.params.get("k", 5))
        x = as_number(df[step.cols[0]]).to_numpy()
        x = x[np.isfinite(x)]
        if x.size == 0:
            return {"edges": []}
        qs = np.quantile(x, np.linspace(0, 1, k + 1)[1:-1])
        edges = sorted({round(float(q), 6) for q in qs})
        return {"edges": edges}

    def code(self, step):
        edges = step.state.get("edges", [])
        k = len(edges) + 1
        return [f"{col(step.name)} = pd.cut({col(step.cols[0])}, bins={bins_lit(edges)}, labels=False)"
                f"  # {k} bins with about the same number of rows; edges from the training rows"]

    def describe(self, step):
        return f"{step.cols[0]} in {len(step.state.get('edges', [])) + 1 or step.params.get('k', 5)} equal-count bins"


@register
class Rare(Op):
    key, title, learns = "rare", "rare categories grouped", True

    def fit(self, step, df):
        share = float(step.params.get("min_share", 0.01))
        counts = df[step.cols[0]].value_counts(normalize=True, dropna=True)
        keep = [v for v, s in counts.items() if s >= share]
        return {"keep": sorted(keep, key=str)}

    def code(self, step):
        src, other = col(step.cols[0]), step.params.get("other", "Other")
        keep = wrap_list(step.state.get("keep", []))
        share = float(step.params.get("min_share", 0.01))
        return [f"{col(step.name)} = {src}.where({src}.isin({keep}) | {src}.isna(), {lit(other)})"
                f"  # groups under {share:.0%} of the training rows -> {clean_comment(other)}"]

    def describe(self, step):
        return f"{step.cols[0]} with rare groups as '{step.params.get('other', 'Other')}'"


@register
class Log1p(Op):
    key, title = "log1p", "log(1 + x)"

    def code(self, step):
        return [f"{col(step.name)} = np.log1p({col(step.cols[0])})  # squeezes a long right tail"]

    def describe(self, step):
        return f"log(1 + {step.cols[0]})"


@register
class MissingFlag(Op):
    key, title = "missing_flag", "was missing"

    def code(self, step):
        return [f"{col(step.name)} = {col(step.cols[0])}.isna().astype(int)  # 1 = the value was missing"]

    def describe(self, step):
        return f"1 where {step.cols[0]} is missing"


DT_PARTS = {"year": "d.dt.year", "month": "d.dt.month", "day": "d.dt.day", "weekday": "d.dt.weekday",
            "hour": "d.dt.hour", "is_weekend": "(d.dt.weekday >= 5).astype(int).where(d.notna())"}


@register
class DatePart(Op):
    key, title = "dt_part", "part of a date"

    def check(self, step):
        super().check(step)
        if step.params.get("part") not in DT_PARTS:
            raise PipelineError(f"Date part must be one of {', '.join(DT_PARTS)}.")

    def code(self, step):
        part = step.params["part"]
        note = "  # Monday = 0" if part == "weekday" else "  # Saturday or Sunday" if part == "is_weekend" else ""
        return [f"d = pd.to_datetime({col(step.cols[0])}, errors='coerce')",
                f"{col(step.name)} = {DT_PARTS[part]}{note}"]

    def describe(self, step):
        return f"{step.params['part'].replace('_', ' ')} of {step.cols[0]}"


TEXT_STATS = {"length": (".str.len()", "characters"), "words": (".str.split().str.len()", "words"),
              "digits": (".str.count(r'\\d')", "digits")}


@register
class TextStat(Op):
    key, title = "text_stat", "text count"

    def check(self, step):
        super().check(step)
        if step.params.get("stat") not in TEXT_STATS:
            raise PipelineError(f"Text count must be one of {', '.join(TEXT_STATS)}.")

    def code(self, step):
        method, what = TEXT_STATS[step.params["stat"]]
        return [f"{col(step.name)} = {text(col(step.cols[0]))}{method}  # number of {what}"]

    def describe(self, step):
        return f"number of {TEXT_STATS[step.params['stat']][1]} in {step.cols[0]}"


@register
class Regex(Op):
    key, title, learns = "regex", "text pulled out with a pattern", True

    def check(self, step):
        super().check(step)
        pattern = step.params.get("pattern", "")
        try:
            groups = re.compile(pattern).groups
        except re.error as exc:
            raise PipelineError(f"The pattern is not a valid regular expression: {exc}") from None
        if groups != 1:
            raise PipelineError("The pattern needs exactly one group in brackets, e.g. ',\\s*([^.]+)\\.'.")

    def _extract_lines(self, step) -> list:
        new, src = col(step.name), col(step.cols[0])
        lines = [f"{new} = {text(src)}.str.extract({rlit(step.params['pattern'])}, expand=False).str.strip()"]
        mapping = step.params.get("map") or {}
        if mapping:
            lines.append(f"{new} = {new}.replace({lit(mapping)})  # the same word, spelled another way")
        return lines

    def fit(self, step, df):
        share = float(step.params.get("min_share", 0.01))
        values = run_code(self._extract_lines(step), df[[step.cols[0]]])[step.name]   # the very code below
        counts = values.value_counts(normalize=True, dropna=True)
        return {"keep": sorted((v for v, s in counts.items() if s >= share), key=str)}

    def code(self, step):
        new = col(step.name)
        lines = self._extract_lines(step)
        other = step.params.get("other", "Other")
        share = float(step.params.get("min_share", 0.01))
        lines.append(f"{new} = {new}.where({new}.isin({wrap_list(step.state.get('keep', []))}) | {new}.isna(), "
                     f"{lit(other)})  # rare (< {share:.0%}) -> {clean_comment(other)}")
        return lines

    def describe(self, step):
        what = step.params.get("preset_title")
        return f"{what} ({step.cols[0]})" if what else f"pattern {step.params['pattern']} in {step.cols[0]}"


def onehot_columns(step: Step) -> dict:
    """{category: new column name} of a one-hot step (its state must be fitted)."""
    out, used = {}, set()
    for value in step.state.get("categories", []):
        tail = re.sub(r"\s+", "_", str(value).strip())
        name = f"{step.name}_{tail}"
        while name in used:
            name += "_"
        used.add(name)
        out[value] = name
    return out


@register
class OneHot(Op):
    key, title, learns = "onehot", "one-hot", True

    def outputs(self, step):
        return list(onehot_columns(step).values())

    def fit(self, step, df):
        values = df[step.cols[0]].dropna().unique().tolist()
        limit = int(step.params.get("max_categories", 30))
        counts = df[step.cols[0]].value_counts(dropna=True)
        keep = counts.index[:limit].tolist() if len(values) > limit else values
        return {"categories": sorted(keep, key=str)}

    def code(self, step):
        pairs = onehot_columns(step)
        return [f"for value, column in {lit(pairs)}.items():",
                f"    df[column] = ({col(step.cols[0])} == value).astype(int)  # 1 where {clean_comment(step.cols[0])} "
                "is that category"]

    def describe(self, step):
        return f"one 0/1 column per group of {step.cols[0]}"


@register
class Ordinal(Op):
    key, title, learns = "ordinal", "ordinal", True

    def fit(self, step, df):
        order = step.params.get("order")
        if not order:
            order = sorted(df[step.cols[0]].dropna().unique().tolist(), key=str)
        return {"codes": {v: i for i, v in enumerate(order)}}

    def code(self, step):
        return [f"{col(step.name)} = {col(step.cols[0])}.map({lit(step.state.get('codes', {}))})"
                "  # the groups in order: 0, 1, 2, ..."]

    def describe(self, step):
        return f"{step.cols[0]} as ordered numbers"


def reads(step: Step) -> list:
    """The columns a step reads: its own, plus the target for target encoding (it learns from the target, which
    can be a column an earlier step made)."""
    target = step.params.get("target") if step.op == "target_enc" else None
    return list(step.cols) + ([target] if target else [])


def target_values(df: pd.DataFrame, step: Step) -> pd.Series:
    """The target as numbers for target encoding: 1/0 for the positive class, else the value."""
    target, positive = step.params["target"], step.params.get("positive")
    if positive is not None:
        return (df[target] == positive).astype(float).where(df[target].notna())
    return pd.to_numeric(df[target], errors="coerce").astype(float)


@register
class TargetEncode(Op):
    key, title, learns, needs_target = "target_enc", "target encoding (out-of-fold)", True, True

    def check(self, step):
        super().check(step)
        if not step.params.get("target"):
            raise PipelineError("Target encoding needs the target column.")

    def fit(self, step, df):
        if step.params["target"] not in df.columns:
            raise PipelineError(f"The target '{step.params['target']}' is not in the table.")
        y = target_values(df, step)
        m = float(step.params.get("smoothing", 10))
        prior = float(y.mean())
        stats = y.groupby(df[step.cols[0]]).agg(["sum", "count"])
        means = (stats["sum"] + m * prior) / (stats["count"] + m)
        return {"prior": round(prior, 6), "map": {k: round(float(v), 6) for k, v in means.items()}}

    def code(self, step):
        src, new = col(step.cols[0]), col(step.name)
        t, positive = step.params["target"], step.params.get("positive")
        k, m, seed = int(step.params.get("k", 5)), lit(float(step.params.get("smoothing", 10))), int(step.params.get("seed", 0))
        y = (f"(df[{lit(t)}] == {lit(positive)}).astype(float).where(df[{lit(t)}].notna())" if positive is not None
             else f"pd.to_numeric(df[{lit(t)}], errors='coerce')")
        prior = lit(step.state.get("prior", 0.0))
        table = lit(step.state.get("map", {}))
        return [
            "if train:  # out-of-fold: each row gets the mean of the OTHER folds, so it never sees its own target",
            f"    y = {y}",
            f"    fold = np.random.RandomState({seed}).permutation(len(df)) % {k}",
            f"    {new} = np.nan",
            f"    for k in range({k}):",
            "        rest = fold != k",
            "        prior = y[rest].mean()",
            f"        stats = y[rest].groupby({src}[rest]).agg(['sum', 'count'])",
            f"        means = (stats['sum'] + {m} * prior) / (stats['count'] + {m})",
            f"        df.loc[fold == k, {lit(step.name)}] = {src}[fold == k].map(means).fillna(prior).to_numpy()",
            "else:  # new data: the means of all training rows",
            f"    {new} = {src}.map({table}).fillna({prior})",
        ]

    def describe(self, step):
        return f"{step.cols[0]} as the mean of {step.params['target']} (out-of-fold)"


@register
class Expression(Op):
    key, title, n_cols = "expr", "your formula", 0

    def check(self, step):
        super().check(step)
        from .feature_lab.safe_expr import compile_expr   # checks the formula again: never trust stored code
        code, used = compile_expr(step.params.get("expr", ""), step.cols)
        step.params["code"] = code

    def code(self, step):
        return [f"{col(step.name)} = {step.params['code']}  # {clean_comment(step.params['expr'])}",
                f"{col(step.name)} = {col(step.name)}.replace([np.inf, -np.inf], np.nan)  # divide by 0 -> missing"]

    def describe(self, step):
        return step.params.get("expr", "")


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #

def run_code(lines, df: pd.DataFrame, train: bool = True) -> pd.DataFrame:
    """Run step code on df (a copy is changed and returned). Only code written by the ops runs here."""
    ns = {"df": df.copy(), "pd": pd, "np": np, "train": bool(train), "__builtins__": SAFE_BUILTINS}
    with np.errstate(all="ignore"):
        exec(compile("\n".join(lines), "<steps>", "exec"), ns)     # noqa: S102 - generated by the ops
    return ns["df"]


class Pipeline:
    """The accepted steps, in order, with undo / redo."""

    def __init__(self, steps=None):
        self.steps: list = [copy.deepcopy(s) for s in (steps or [])]
        self._undo: list = []
        self._redo: list = []
        self.version = 0

    # -------------------------------------------------------------- facts --
    def __len__(self) -> int:
        return len(self.steps)

    def __iter__(self):
        return iter(self.steps)

    @property
    def outputs(self) -> list:
        return [c for s in self.steps for c in s.outputs]

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def has(self, op: str, column: str) -> bool:
        """True if a step `op` on `column` is already there (e.g. a log already applied)."""
        return any(s.op == op and column in s.cols for s in self.steps)

    def dependents(self, index: int) -> list:
        """Indexes of the steps that use (directly or not) the columns step `index` makes."""
        made = set(self.steps[index].outputs)
        out = []
        for j in range(index + 1, len(self.steps)):
            if made & set(reads(self.steps[j])):
                out.append(j)
                made |= set(self.steps[j].outputs)
        return out

    # ------------------------------------------------------------- running --
    def code(self, numbered: bool = True) -> list:
        """The pandas lines of every step (with a comment line naming each step)."""
        lines = []
        for i, step in enumerate(self.steps, 1):
            head = clean_comment(f"{i}. {step.name}: {step.label}" if numbered else f"{step.name}: {step.label}")
            head = f"# {head}"
            lines += [head] + step.code()
        return lines

    @property
    def signature(self) -> tuple:
        """What the steps do (their code, learned values included): equal signatures give equal tables, so an
        undo followed by a redo is recognised as the same pipeline."""
        return tuple(self.code(numbered=False))

    def transform(self, df: pd.DataFrame, train: bool = True, progress=None) -> pd.DataFrame:
        """Apply every step to df (train=False for new data: nothing is learned again)."""
        out = df
        for i, step in enumerate(self.steps):
            if progress:
                progress(i / max(1, len(self.steps)), f"Step {i + 1} of {len(self.steps)}: {step.name}")
            missing = [c for c in step.cols if c not in out.columns]
            if step.op == "target_enc" and train and step.params["target"] not in out.columns:
                missing.append(step.params["target"])
            if missing:
                raise PipelineError(f"Step '{step.name}' needs the column(s) {', '.join(missing)}, "
                                    "which this table doesn't have.")
            out = run_code(step.code(), out, train=train)
        return out if self.steps else df.copy()

    @staticmethod
    def fit_step(step: Step, df: pd.DataFrame) -> Step:
        """A fitted copy of step: what it learns comes from df (the training rows) only."""
        step = copy.deepcopy(step)
        OPS[step.op].check(step)
        missing = [c for c in step.cols if c not in df.columns]
        if missing:
            raise PipelineError(f"Column(s) not found: {', '.join(missing)}.")
        if OPS[step.op].learns:
            with np.errstate(all="ignore"):
                step.state = OPS[step.op].fit(step, df)
        return step

    # ------------------------------------------------------------- editing --
    def _remember(self) -> None:
        self._undo.append([copy.deepcopy(s) for s in self.steps])
        self._redo.clear()
        self.version += 1

    def add(self, step: Step, df: pd.DataFrame) -> Step:
        """Fit `step` on df (the training table after the earlier steps) and append it."""
        fitted = self.fit_step(step, df)
        clash = [c for c in fitted.outputs if c in df.columns]
        if clash:
            raise PipelineError(f"A column called '{clash[0]}' already exists. Pick another name.")
        if not fitted.outputs:
            raise PipelineError(f"'{fitted.name}' would not add any column (no groups were found).")
        self._remember()
        self.steps.append(fitted)
        return fitted

    def remove(self, index: int) -> list:
        """Remove step `index` and the steps built on it. Returns the removed steps."""
        drop = [index] + self.dependents(index)
        self._remember()
        removed = [self.steps[i] for i in drop]
        self.steps = [s for i, s in enumerate(self.steps) if i not in drop]
        return removed

    def rename(self, index: int, name: str, taken=()) -> None:
        """Rename step `index` (its column, or the stem of its columns) and point the later steps at the new
        name(s), formulas included. `taken`: the table's own columns, which a new name may not repeat."""
        name = str(name).strip()
        if not name:
            raise PipelineError("The new column needs a name.")
        if clean_comment(name) != name:
            raise PipelineError("A column name must be one line.")
        step = self.steps[index]
        trial = copy.deepcopy(step)
        trial.name = name
        others = {c for i, s in enumerate(self.steps) if i != index for c in s.outputs}
        taken = set(taken) - set(step.outputs)
        clash = [c for c in trial.outputs if c in others or c in taken]
        if clash:
            raise PipelineError(f"A column called '{clash[0]}' already exists. Pick another name.")
        mapping = {a: b for a, b in zip(step.outputs, trial.outputs) if a != b}
        later = copy.deepcopy(self.steps[index + 1:])
        for s in later:
            if not any(c in mapping for c in reads(s)):
                continue
            if s.op == "target_enc" and s.params.get("target") in mapping:
                s.params["target"] = mapping[s.params["target"]]
            if s.op == "expr":
                from .feature_lab.safe_expr import rename_column
                for a, b in mapping.items():
                    if a in s.cols:
                        s.params["expr"] = rename_column(s.params["expr"], a, b)
            s.cols = [mapping.get(c, c) for c in s.cols]
            OPS[s.op].check(s)                               # a formula is compiled again from its new text
        self._remember()
        step.name = name
        self.steps[index + 1:] = later

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self.steps)
        self.steps = self._undo.pop()
        self.version += 1
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self.steps)
        self.steps = self._redo.pop()
        self.version += 1
        return True

    def clear(self) -> None:
        if self.steps:
            self._remember()
            self.steps = []

    # ------------------------------------------------------------ storage --
    def to_list(self) -> list:
        return [s.to_dict() for s in self.steps]

    @classmethod
    def from_list(cls, items) -> "Pipeline":
        return cls([Step.from_dict(d) for d in items])


def unique_name(name: str, taken) -> str:
    """name, or name_2, name_3 ... if it is already used."""
    taken = set(taken)
    base = re.sub(r"\s+", "_", str(name).strip()) or "feature"
    if base not in taken:
        return base
    i = 2
    while f"{base}_{i}" in taken:
        i += 1
    return f"{base}_{i}"


__all__ = ["OPS", "Pipeline", "PipelineError", "Step", "run_code", "unique_name"]
