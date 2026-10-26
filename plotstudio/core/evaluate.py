"""Evaluate with model: does a model score better WITH the accepted features than without them?

The same 5 folds are used for both runs, with two simple models side by side (no tuning):

* a linear model (logistic regression for classes, ridge regression for numbers): numbers are
  filled with the median and scaled, categories one-hot encoded
* gradient boosting (scikit-learn's HistGradientBoosting): gaps are fine, categories as codes

Scores: accuracy for classes, R² for numbers. A gain smaller than the cross-validation standard
deviation is labelled "not significant": the folds disagree more than the features help.
Big tables are evaluated on a 50,000-row sample (and the result says so).
"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .analyses.base import Result
from .profiler import SAMPLE_ROWS, profile_frame

FOLDS = 5
MAX_GROUPS = 50          # categories with more groups are left out of the model (too many columns)
MODELS = ("linear", "boosting")
MODEL_NAMES = {("linear", "class"): "Logistic regression", ("linear", "number"): "Ridge regression",
               ("boosting", "class"): "Gradient boosting", ("boosting", "number"): "Gradient boosting"}


class EvaluateError(ValueError):
    """The evaluation can't run (no scikit-learn, no target, no usable columns ...)."""


@dataclass
class ModelScore:
    model: str                     # "linear" | "boosting"
    name: str                      # e.g. "Logistic regression"
    metric: str                    # "accuracy" | "R²"
    before: list                   # one score per fold, without the new features
    after: list                    # the same folds, with them

    @property
    def before_mean(self) -> float:
        return float(np.mean(self.before))

    @property
    def after_mean(self) -> float:
        return float(np.mean(self.after))

    @property
    def before_std(self) -> float:
        return float(np.std(self.before))

    @property
    def after_std(self) -> float:
        return float(np.std(self.after))

    @property
    def gain(self) -> float:
        return self.after_mean - self.before_mean

    @property
    def cv_std(self) -> float:
        """The cross-validation standard deviation the gain is compared with."""
        return max(self.before_std, self.after_std)

    @property
    def significant(self) -> bool:
        return abs(self.gain) >= self.cv_std and self.gain != 0

    def text(self) -> str:
        verdict = "" if self.significant else ", not significant"
        return (f"{self.metric} {self.before_mean:.3f} ± {self.before_std:.3f} → {self.after_mean:.3f} ± "
                f"{self.after_std:.3f}  ({self.gain:+.3f}{verdict})")


@dataclass
class Evaluation(Result):
    target: str = ""
    task: str = ""                 # "class" | "number"
    metric: str = ""
    base_columns: list = field(default_factory=list)
    new_columns: list = field(default_factory=list)
    left_out: list = field(default_factory=list)     # (column, why)
    scores: list = field(default_factory=list)        # [ModelScore]
    notes: list = field(default_factory=list)

    def best(self) -> Optional[ModelScore]:
        return max(self.scores, key=lambda s: s.after_mean) if self.scores else None


def sklearn_or_error():
    try:
        import sklearn  # noqa: F401
    except ImportError:
        raise EvaluateError("This needs scikit-learn. Install it with:  pip install scikit-learn") from None


def model_columns(df: pd.DataFrame, columns, profiles: dict, linear: bool = False) -> tuple:
    """-> (number columns, category columns, [(column, why left out)]) for a model.

    linear=True: groups written as numbers (bins, Pclass: 3 or more values that the profile reads as groups) are
    one-hot encoded, so a linear model can give each group its own weight (one slope can't follow a U shape).
    Trees keep them as numbers: their order is kept, which the text codes of a category would lose."""
    nums, cats, left = [], [], []
    for c in columns:
        p = profiles.get(c)
        kind = p.kind if p is not None else "category"
        s = df[c]
        if kind in ("id", "text"):
            left.append((c, "an ID or free text"))
        elif kind in ("date", "empty", "constant", "skip"):
            left.append((c, {"date": "a date (use its parts)", "empty": "empty", "constant": "one value only",
                             "skip": "skipped"}[kind]))
        elif linear and kind == "category" and pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) \
                and 2 < s.nunique(dropna=True) <= MAX_GROUPS:
            cats.append(c)
        elif pd.api.types.is_bool_dtype(s) or (pd.api.types.is_numeric_dtype(s)):
            nums.append(c)
        elif s.nunique(dropna=True) > MAX_GROUPS:
            left.append((c, f"more than {MAX_GROUPS} groups"))
        else:
            cats.append(c)
    return nums, cats, left


def build_model(kind: str, task: str, nums: list, cats: list):
    """A scikit-learn pipeline: preprocessing + one of the two baseline models."""
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline as SkPipeline
    from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

    if kind == "linear":
        from sklearn.linear_model import LogisticRegression, Ridge
        parts = []
        if nums:
            parts.append(("num", SkPipeline([("fill", SimpleImputer(strategy="median")),
                                             ("scale", StandardScaler())]), nums))
        if cats:
            parts.append(("cat", SkPipeline([("fill", SimpleImputer(strategy="most_frequent")),
                                             ("onehot", OneHotEncoder(handle_unknown="ignore"))]), cats))
        model = LogisticRegression(max_iter=2000) if task == "class" else Ridge(alpha=1.0)
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
        parts = []
        if nums:
            parts.append(("num", "passthrough", nums))
        if cats:
            parts.append(("cat", SkPipeline([("fill", SimpleImputer(strategy="constant", fill_value="missing")),
                                             ("codes", OrdinalEncoder(handle_unknown="use_encoded_value",
                                                                      unknown_value=-1))]), cats))
        model = (HistGradientBoostingClassifier(random_state=0) if task == "class"
                 else HistGradientBoostingRegressor(random_state=0))
    return SkPipeline([("prep", ColumnTransformer(parts)), ("model", model)])


def prepare(df: pd.DataFrame, nums: list, cats: list) -> pd.DataFrame:
    """Numbers as floats, categories as text (gaps stay gaps): what the models get."""
    X = pd.DataFrame(index=df.index)
    for c in nums:
        X[c] = pd.to_numeric(df[c], errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)
    for c in cats:
        X[c] = df[c].astype(str).where(df[c].notna()).astype(object)
    return X


def target_task(y: pd.Series, profile) -> str:
    kind = profile.kind if profile is not None else ("number" if pd.api.types.is_numeric_dtype(y) else "category")
    if kind == "number" and pd.api.types.is_numeric_dtype(y) and y.nunique() > 15:
        return "number"
    return "class"


def evaluate(df: pd.DataFrame, target: str, new_columns, *, base_columns=None, infos: Optional[dict] = None,
             models=MODELS, sample_rows: int = SAMPLE_ROWS, folds: int = FOLDS,
             progress: Optional[Callable[[float, str], None]] = None) -> Evaluation:
    """Cross-validate the baseline models without and with new_columns.

    df            the training table WITH the new columns (the pipeline already applied)
    new_columns   the accepted features (pipeline outputs)
    base_columns  the columns the model uses without them (default: every other column)
    """
    sklearn_or_error()
    from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score

    started = time.perf_counter()
    tell = progress or (lambda fraction, text: None)
    if not target or target not in df.columns:
        raise EvaluateError("Pick the target (the column to predict) first.")
    new_columns = [c for c in new_columns if c in df.columns and c != target]
    if base_columns is None:
        base_columns = [c for c in df.columns if c not in set(new_columns) and c != target]
    base_columns = [c for c in base_columns if c in df.columns and c != target]
    data = df[df[target].notna()]
    note = []
    if len(data) > sample_rows:
        data = data.sample(sample_rows, random_state=0).sort_index()
        note.append(f"Computed on a {sample_rows:,}-row sample of the {len(df):,} rows.")
    if len(data) < 4 * folds:
        raise EvaluateError(f"Only {len(data)} rows have a target value: too few for {folds}-fold cross-validation.")
    tell(0.03, "Reading the column types")
    prof = profile_frame(data[base_columns + new_columns + [target]], target=target, infos=infos,
                         sample_rows=len(data))
    profiles = {prof.renamed.get(n, n): p for n, p in prof.profiles.items()}
    task = target_task(data[target], profiles.get(target))
    y = data[target]
    if task == "class":
        counts = y.value_counts()
        if len(counts) < 2:
            raise EvaluateError(f"'{target}' has only one value here.")
        if counts.min() < folds:
            raise EvaluateError(f"A class of '{target}' has fewer than {folds} rows: too few for {folds} folds.")
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
        y = y.astype(str) if y.dtype == object else y
        scoring, metric = "accuracy", "accuracy"
    else:
        y = pd.to_numeric(y, errors="coerce").astype(float)
        cv = KFold(n_splits=folds, shuffle=True, random_state=0)
        scoring, metric = "r2", "R²"
    b_nums, b_cats, left = model_columns(data, base_columns, profiles)
    n_nums, n_cats, n_left = model_columns(data, new_columns, profiles)
    if not (b_nums or b_cats) and not (n_nums or n_cats):
        raise EvaluateError("No column a model can use (only IDs, text or dates).")
    result = Evaluation(rows_used=len(data), total_rows=len(df), target=target, task=task, metric=metric,
                        base_columns=b_nums + b_cats, new_columns=n_nums + n_cats, left_out=left + n_left,
                        notes=note)
    runs = [(m, before) for m in models for before in (True, False)]
    scores = {}
    for i, (m, before) in enumerate(runs):
        bn, bc, _ = model_columns(data, base_columns, profiles, linear=(m == "linear"))
        nn, nc, _ = model_columns(data, new_columns, profiles, linear=(m == "linear"))
        nums = bn + ([] if before else nn)
        cats = bc + ([] if before else nc)
        label = MODEL_NAMES[(m, task)]
        tell(0.1 + 0.85 * i / len(runs), f"{label}, {'without' if before else 'with'} the new features")
        if not (nums or cats):
            fold_scores = [float("nan")] * folds          # nothing to learn from: no score
        else:
            X = prepare(data, nums, cats)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fold_scores = cross_val_score(build_model(m, task, nums, cats), X, y, cv=cv, scoring=scoring)
        scores[(m, before)] = [float(v) for v in fold_scores]
    for m in models:
        result.scores.append(ModelScore(model=m, name=MODEL_NAMES[(m, task)], metric=metric,
                                        before=scores[(m, True)], after=scores[(m, False)]))
    if not result.new_columns:
        result.notes.append("No accepted feature a model can use yet: both runs are the same.")
    result.seconds = time.perf_counter() - started
    tell(1.0, "Done")
    return result


def fit_and_predict(train: pd.DataFrame, test: pd.DataFrame, target: str, columns, *, model: str = "boosting",
                    infos: Optional[dict] = None) -> pd.Series:
    """Train one baseline model on all training rows and predict the test rows (for a submission)."""
    sklearn_or_error()
    data = train[train[target].notna()]
    prof = profile_frame(data[list(columns) + [target]], target=target, infos=infos,
                         sample_rows=min(len(data), SAMPLE_ROWS))
    profiles = {prof.renamed.get(n, n): p for n, p in prof.profiles.items()}
    task = target_task(data[target], profiles.get(target))
    nums, cats, _ = model_columns(data, columns, profiles, linear=(model == "linear"))
    if not (nums or cats):
        raise EvaluateError("No column a model can use (only IDs, text or dates).")
    missing = [c for c in nums + cats if c not in test.columns]
    if missing:
        raise EvaluateError(f"The test file has no column(s) {', '.join(missing)}.")
    if task == "class":
        y = data[target]
        y = y.astype(str) if y.dtype == object else y       # as in evaluate(): mixed labels (1 and "no") as text
    else:
        y = pd.to_numeric(data[target], errors="coerce").astype(float)
    pipe = build_model(model, task, nums, cats)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe.fit(prepare(data, nums, cats), y)
        pred = pipe.predict(prepare(test, nums, cats))
    return pd.Series(pred, index=test.index, name=target)
