"""The pieces every feature generator shares: a suggestion, the context it works in, the plugin base."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from ..pipeline import Pipeline, Step, run_code, unique_name
from . import scoring

MIN_GAIN = 0.005         # MI gains below this (nats) are within the noise: "no real change"


@dataclass(eq=False)
class FeatureSuggestion:
    """One feature the Lab suggests: the pipeline step that makes it, plus its numbers."""
    step: Step
    generator: str                      # the plugin that suggested it, e.g. "numeric_ratio"
    title: str                          # what it is, e.g. "Fare / family_size"
    sources: list                       # the columns it is made from
    why: str = ""                       # what it does and why it can help, in plain words
    kind: str = "feature"               # "feature" or "encoding"
    neutral: bool = False               # keeps the order of the values: MI can't change (log, bins)
    values: Optional[pd.Series] = field(default=None, repr=False)   # the new column on the sample
    mi_before: float = 0.0              # the best source column's MI with the target
    mi_after: float = 0.0               # the new column's MI with the target
    redundant_with: Optional[str] = None
    redundant_value: float = 0.0
    redundant_how: str = ""             # "r" (correlation) or "shared" (same groups)
    leak_metric: str = ""
    leak_value: float = 0.0
    leak: bool = False
    link: str = ""                      # e.g. "Survived = 1 is most common for title = Mrs (79% vs 38% overall)."
    warning: str = ""                   # e.g. why target encoding is computed out-of-fold
    error: str = ""                     # the step could not be made on the sample
    rank: int = 0

    @property
    def name(self) -> str:
        return self.step.name

    @property
    def gain(self) -> float:
        return self.mi_after - self.mi_before

    @property
    def status(self) -> str:
        """leak · redundant · error · recommended · neutral · weak (less than its source)."""
        if self.error:
            return "error"
        if self.leak:
            return "leak"
        if self.redundant_with:
            return "redundant"
        if self.kind == "encoding":
            return "recommended"
        if self.neutral:
            # a log or bins of ONE column can't tell more than the column itself (data-processing inequality):
            # a measured gain is an estimation effect (fewer groups, or the gaps that the column's own score puts
            # in its median bin; the 'was missing' flag is the feature for those), never new information
            return "neutral"
        if self.gain > MIN_GAIN:
            return "recommended"
        return "weak"

    @property
    def can_accept(self) -> bool:
        """One-click Accept is blocked for leakage (and for steps that failed)."""
        return self.status not in ("leak", "error")

    def mi_text(self) -> str:
        return f"MI {self.mi_before:.3f} → {self.mi_after:.3f} ({self.gain:+.3f})"

    @property
    def reason(self) -> str:
        """The one-line reason shown in the list."""
        if self.kind == "encoding":
            return self.why
        if self.status == "error":
            return f"{self.name}: couldn't be made ({self.error})."
        head = f"{self.name}: {self.mi_text()}."
        if self.status == "leak":
            return (f"{head} Leakage? Alone it predicts the target almost perfectly ({self.leak_metric} "
                    f"{self.leak_value:.3f}): it was probably made from the target.")
        if self.status == "redundant":
            how = f"|r| = {self.redundant_value:.2f}" if self.redundant_how == "r" else \
                f"{self.redundant_value:.0%} the same groups"
            return f"{head} Redundant: it repeats '{self.redundant_with}' ({how})."
        if self.status == "neutral":
            return f"{head} {self.why}"
        return f"{head} {self.link}".strip()


@dataclass
class LabContext:
    """What the generators work on: a sample of at most 50,000 rows of the training table."""
    df: pd.DataFrame                    # the sample, original values (the step code runs on these)
    profiles: dict                      # name -> ColumnProfile (the app's own column types)
    target: scoring.Target
    pipeline: Pipeline
    taken: set = field(default_factory=set)     # column names already used (table + suggestions)
    _mi: dict = field(default_factory=dict)

    def kind(self, name) -> str:
        p = self.profiles.get(name)
        return p.kind if p is not None else scoring.feature_kind(self.df[name])

    def usable(self, name) -> bool:
        return name != self.target.name and self.kind(name) in ("number", "category", "date")

    def mi(self, name) -> float:
        """MI of an existing column with the target (cached)."""
        if name not in self._mi:
            self._mi[name] = scoring.column_mi(self.df[name], self.target, self.kind(name))
        return self._mi[name]

    def new_name(self, name: str) -> str:
        name = unique_name(name, self.taken)
        self.taken.add(name)
        return name

    def numeric(self, name) -> pd.Series:
        return pd.to_numeric(self.df[name], errors="coerce").astype(float)

    def make(self, step: Step) -> pd.Series:
        """The new column on the sample (the step is fitted on the sample here, only to score it)."""
        fitted = Pipeline.fit_step(step, self.df)
        needed = set(step.cols) | ({step.params["target"]} if "target" in step.params else set())
        out = run_code(fitted.code(), self.df[[c for c in self.df.columns if c in needed]])
        return out[fitted.outputs[0]] if fitted.outputs else pd.Series(dtype=float)


class Generator:
    """A feature plugin. suggest() proposes steps; apply() runs one on a table."""
    NAME = ""
    TITLE = ""
    CAP = 5              # at most this many suggestions from this plugin

    def suggest(self, df: pd.DataFrame, profiles: dict, target, ctx: LabContext | None = None) -> list:
        raise NotImplementedError

    def apply(self, df: pd.DataFrame, step: Step) -> pd.DataFrame:
        """Add the step's column(s) to df: fitted on df when it hasn't learned yet (train only!)."""
        fitted = step if step.fitted else Pipeline.fit_step(step, df)
        return run_code(fitted.code(), df)

    def make(self, step: Step, title: str, sources, why: str, neutral: bool = False) -> FeatureSuggestion:
        return FeatureSuggestion(step=step, generator=self.NAME, title=title, sources=list(sources), why=why,
                                 neutral=neutral)
