"""Feature Engineering Lab: suggest new features, explain each one, and measure it against the target.

    from plotstudio.core.feature_lab import suggest_features
    lab = suggest_features(df, "Survived")                   # -> LabResult
    for s in lab.suggestions:                               # best first
        print(s.reason)                                     # title: MI 0.000 -> 0.231 (+0.231). ...
    pipeline.add(lab.suggestions[0].step, df)               # accepting = adding the step

Every feature is a pipeline step (plotstudio.core.pipeline), so undo / redo, clean.py, the notebook
and Kaggle submissions include it. The plugins live in ``generators/``; each one has
``suggest(df, profiles, target, ctx)`` and ``apply(df, step)``. Scoring (``scoring.py``) runs on a
sample of at most 50,000 rows and is deterministic.
"""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from ..analyses.base import Result
from ..pipeline import Pipeline, Step
from ..profiler import SAMPLE_ROWS, profile_frame
from . import scoring
from .base import MIN_GAIN, FeatureSuggestion, Generator, LabContext
from .encoding import suggest_encodings
from .generators import BY_NAME, GENERATORS
from .safe_expr import ExprError, compile_expr, default_name

MAX_SHOWN = 25
PER_COLUMN = 2           # at most this many ideas made from the same single column
STATUS_ORDER = {"leak": 0, "recommended": 1, "neutral": 2, "weak": 3, "redundant": 4, "error": 5}


@dataclass
class LabResult(Result):
    """The Lab's suggestions for one table and target.

    suggestions  [FeatureSuggestion], leakage first, then by MI gain (recommended, neutral, weak, redundant)
    encodings    [FeatureSuggestion] how a model should read each category column
    notes        short messages for the user (no target, sample used, a plugin that failed ...)
    errors       [(plugin, message, traceback)] for the log: nothing is dropped silently
    """
    target: Optional[str] = None
    task: str = ""
    metric: str = ""
    suggestions: list = field(default_factory=list)
    encodings: list = field(default_factory=list)
    profiles: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    context: Optional[LabContext] = field(default=None, repr=False)

    @property
    def recommended(self) -> list:
        return [s for s in self.suggestions if s.status == "recommended"]

    def find(self, name: str):
        return next((s for s in self.suggestions + self.encodings if s.name == name), None)


def _sample(df: pd.DataFrame, rows: int) -> pd.DataFrame:
    if not df.index.is_unique:
        df = df.reset_index(drop=True)
    if len(df) > rows:
        return df.loc[df.sample(rows, random_state=0).sort_index().index]   # the profiler's own sample
    return df


def score(s: FeatureSuggestion, ctx: LabContext) -> FeatureSuggestion:
    """Fill in a suggestion's numbers: MI before / after, redundancy, leakage and the link in words."""
    target = ctx.target
    try:
        if s.values is None:
            s.values = ctx.make(s.step)
    except Exception as exc:  # noqa: BLE001 - shown on the suggestion itself
        s.error = f"{type(exc).__name__}: {exc}"
        return s
    s.values = s.values.reindex(ctx.df.index)
    s.mi_after = scoring.mutual_info(scoring.codes(s.values), target.codes)
    s.mi_before = max((ctx.mi(c) for c in s.sources if c in ctx.df.columns), default=0.0)
    own = set(s.sources) if s.neutral or s.generator == "rare_grouping" else set()
    kinds = {c: ctx.kind(c) for c in ctx.df.columns}
    s.redundant_with, s.redundant_value, s.redundant_how = scoring.redundancy(
        s.values, ctx.df, kinds, skip={target.name} | own)
    s.leak_metric, s.leak_value = scoring.predictive_power(s.values, target)
    s.leak = scoring.is_leak(s.leak_metric, s.leak_value, target)
    try:
        s.link = scoring.describe_link(s.values, target, s.name)
    except Exception:  # noqa: BLE001 - the sentence is optional
        s.link = ""
    return s


def _same(params: dict) -> str:
    """The parameters that make two steps the same (not the learned state, not the name)."""
    return repr(sorted((k, repr(v)) for k, v in params.items() if k not in ("preset_title",)))


def _rank_key(s: FeatureSuggestion):
    status = s.status
    size = -s.gain if status in ("leak", "recommended", "weak") else -s.mi_after
    return STATUS_ORDER[status], round(size, 6), s.name


def suggest_features(df: pd.DataFrame, target: Optional[str], *, pipeline: Optional[Pipeline] = None,
                     infos: Optional[dict] = None, overrides: Optional[dict] = None,
                     sample_rows: int = SAMPLE_ROWS,
                     progress: Optional[Callable[[float, str], None]] = None) -> LabResult:
    """Suggest features for df (the training table, after the pipeline's steps) and this target."""
    started = time.perf_counter()
    tell = progress or (lambda fraction, text: None)
    pipeline = pipeline or Pipeline()
    result = LabResult(rows_used=min(len(df), sample_rows), total_rows=len(df), target=target)
    if not target:
        result.notes.append("Pick the target (the column you want to predict): the Lab measures every feature "
                            "against it.")
        return result
    tell(0.02, "Reading the column types")
    prof = profile_frame(df, target=target, overrides=overrides, infos=infos, sample_rows=sample_rows)
    profiles = {prof.renamed.get(n, n): p for n, p in prof.profiles.items()}
    target = next((n for n, p in profiles.items() if p.is_target), target)
    result.target, result.profiles = target, profiles
    sample = _sample(df, sample_rows)
    result.rows_used = len(sample)
    tkind = profiles[target].kind
    if tkind not in ("number", "category"):
        result.notes.append(f"'{target}' is {profiles[target].label}: pick a number or a category column as the "
                            "target.")
        return result
    info = scoring.target_info(sample, target, tkind)
    if len(set(info.codes[info.codes >= 0])) < 2:
        result.notes.append(f"'{target}' has too few values to measure anything against.")
        return result
    result.task, result.metric = info.task, info.metric
    ctx = LabContext(df=sample, profiles=profiles, target=info, pipeline=pipeline,
                     taken=set(map(str, df.columns)) | set(pipeline.outputs))
    result.context = ctx
    if (info.codes >= 0).sum() < 20:
        result.notes.append(f"'{target}' has too few values to measure anything against.")
        return result
    if prof.sampled:
        result.notes.append(f"Computed on a {len(sample):,}-row sample of the {len(df):,} rows.")

    found = []
    existing = [(st.op, tuple(st.cols), _same(st.params)) for st in pipeline]
    for i, gen in enumerate(GENERATORS):
        tell(0.05 + 0.45 * i / len(GENERATORS), f"Looking for {gen.TITLE.lower()}")
        try:
            found += gen.suggest(sample, profiles, info, ctx)
        except Exception as exc:  # noqa: BLE001 - reported, the other plugins still run
            result.errors.append((gen.NAME, f"{type(exc).__name__}: {exc}", traceback.format_exc()))
            result.notes.append(f"The '{gen.TITLE}' ideas could not be worked out ({type(exc).__name__}: {exc}).")

    found = [s for s in found if (s.step.op, tuple(s.step.cols), _same(s.step.params)) not in existing]
    for i, s in enumerate(found):
        if i % 4 == 0:
            tell(0.5 + 0.45 * i / max(1, len(found)), f"Measuring {s.name}")
        score(s, ctx)

    kept = []
    for gen in GENERATORS:                       # each plugin keeps its best few
        mine = sorted((s for s in found if s.generator == gen.NAME), key=_rank_key)
        kept += [s for s in mine if s.status == "leak"] + [s for s in mine if s.status != "leak"][: gen.CAP]
    kept.sort(key=_rank_key)
    leaks = [s for s in kept if s.status == "leak"]
    shown, per_column = [], {}
    for s in kept:
        if s.status == "leak":
            continue
        if len(s.sources) == 1:                  # variety: at most 2 ideas made from one column
            per_column[s.sources[0]] = per_column.get(s.sources[0], 0) + 1
            if per_column[s.sources[0]] > PER_COLUMN:
                continue
        shown.append(s)
    result.suggestions = leaks + shown[:MAX_SHOWN]
    for i, s in enumerate(result.suggestions, 1):
        s.rank = i
    tell(0.97, "Encodings")
    try:
        result.encodings = suggest_encodings(ctx)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(("encoding", f"{type(exc).__name__}: {exc}", traceback.format_exc()))
    result.seconds = time.perf_counter() - started
    tell(1.0, "Done")
    return result


def score_formula(result: LabResult, text: str, name: str = "") -> FeatureSuggestion:
    """Your own feature: check the formula (safe_expr), make it on the sample and score it like the others.

    Raises ExprError for a formula outside the allow-list or a name that is taken."""
    ctx = result.context
    if ctx is None:
        raise ExprError("Pick a target first: the formula is measured against it.")
    columns = [c for c in ctx.df.columns]
    code, used = compile_expr(text, columns)
    name = (name or "").strip() or default_name(text, ctx.taken)
    if name in ctx.df.columns or name in ctx.pipeline.outputs:
        raise ExprError(f"A column called '{name}' already exists. Pick another name.")
    step = Step("expr", used, name, {"expr": text.strip(), "code": code})
    s = FeatureSuggestion(step=step, generator="custom", title=text.strip(), sources=used,
                          why="Your formula, checked piece by piece (it never runs with eval).")
    score(s, ctx)
    if s.error:
        raise ExprError(f"The formula can't be computed: {s.error}")
    return s


__all__ = ["BY_NAME", "ExprError", "FeatureSuggestion", "GENERATORS", "Generator", "LabContext", "LabResult",
           "MIN_GAIN", "score", "score_formula", "suggest_features"]
