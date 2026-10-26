"""How much a column tells about the target, and the checks a feature passes before it is recommended.

Mutual information (MI) is measured the way a model would meet the column:

* numbers: gaps filled with the median, then 16 bins with about the same number of rows
  (equal values stay together, so a log or any other order-keeping change gives the same MI)
* categories, yes/no and numbers with few values: one group per value, gaps as their own group
* text and ID columns (a different value in almost every row) count as 0: a model can't use
  them as they are

MI is cross-validated: the target shares of each group are learned on 4/5 of the rows and
scored on the other 1/5 (in nats, like scikit-learn). Groups that are too small to learn
from therefore add nothing, which keeps "name" or "ticket" from looking informative.
Everything is deterministic (fixed folds).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import assoc

N_BINS = 16
LEAK_BINS = 32
FOLDS = 5
LEAK_LIMIT = 0.99
REDUNDANT = 0.95
FEW_VALUES = 15          # numbers with this many values or fewer are treated as groups


@dataclass
class Target:
    """The target column on the scoring sample."""
    name: str
    task: str                # "binary" | "multiclass" | "regression"
    values: pd.Series        # the target, aligned with the sample (gaps possible)
    codes: np.ndarray        # integer classes (or 16 bins of a number target); -1 = gap
    positive: object = None  # the class counted as 1 for a 2-class target
    classes: list = None

    @property
    def metric(self) -> str:
        return {"binary": "AUC", "multiclass": "accuracy", "regression": "R²"}[self.task]

    def word(self) -> str:
        if self.task == "binary":
            return f"{self.name} = {_fmt(self.positive)}"
        return self.name


def fold_ids(n: int, folds: int = FOLDS) -> np.ndarray:
    """Fixed folds: the same rows go together every time (and in every Python)."""
    return np.random.RandomState(0).permutation(n) % folds


def is_number(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def feature_kind(s: pd.Series) -> str:
    """'number' (many values) or 'category' (labels, yes/no, numbers with few values)."""
    if is_number(s) and s.nunique(dropna=True) > FEW_VALUES:
        return "number"
    return "category"


def quantile_codes(x: np.ndarray, bins: int) -> np.ndarray:
    """Codes 0..bins-1 with about the same number of values each (equal values share a bin)."""
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        return np.zeros(len(x), dtype=np.int64)
    edges = np.unique(np.quantile(finite, np.linspace(0, 1, bins + 1)[1:-1]))
    return np.searchsorted(edges, x, side="right").astype(np.int64)


def codes(s: pd.Series, kind: str | None = None, bins: int = N_BINS) -> np.ndarray:
    """Integer codes of a column as a model would see it (see the module notes)."""
    kind = kind or feature_kind(s)
    if kind == "number":
        x = pd.to_numeric(s, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)
        x = x.fillna(x.median() if x.notna().any() else 0.0).to_numpy()
        return quantile_codes(x, bins)
    values = s.astype("object").where(s.notna(), "\x00missing")
    return pd.factorize(values.to_numpy(dtype=object))[0].astype(np.int64)   # codes in order of appearance


def target_info(df: pd.DataFrame, name: str, kind: str) -> Target:
    """kind: the target's profile kind ('category' -> classes, 'number' -> regression)."""
    y = df[name]
    if kind == "number" and is_number(y) and y.nunique(dropna=True) > FEW_VALUES:
        x = pd.to_numeric(y, errors="coerce").astype(float)
        c = quantile_codes(x.to_numpy(), N_BINS)
        c[x.isna().to_numpy()] = -1
        return Target(name, "regression", y, c)
    classes = sorted(y.dropna().unique().tolist(), key=lambda v: (str(type(v)), v))
    c = pd.Series(pd.Categorical(y, categories=classes)).cat.codes.to_numpy().astype(np.int64)
    if len(classes) == 2:
        from ...graphs import positive_class
        positive = positive_class(classes)
        c = np.where(c < 0, -1, (y.to_numpy() == positive).astype(np.int64))
        return Target(name, "binary", y, c, positive=positive, classes=classes)
    return Target(name, "multiclass", y, c, classes=classes)


def mutual_info(x_codes: np.ndarray, y_codes: np.ndarray, m: float = 1.0) -> float:
    """Cross-validated mutual information in nats (>= 0); rows with a target gap are left out."""
    keep = y_codes >= 0
    xc, yc = x_codes[keep], y_codes[keep]
    n = len(yc)
    if n < 20:
        return 0.0
    kx, ky = int(xc.max()) + 1, int(yc.max()) + 1
    if kx < 2 or ky < 2:
        return 0.0
    fold = fold_ids(n)
    total = 0.0
    for f in range(FOLDS):
        tr, te = fold != f, fold == f
        joint = np.bincount(xc[tr] * ky + yc[tr], minlength=kx * ky).reshape(kx, ky).astype(float)
        prior = (joint.sum(axis=0) + 1.0) / (tr.sum() + ky)                 # class shares (Laplace)
        cond = (joint + m * prior) / (joint.sum(axis=1, keepdims=True) + m)  # shrunk toward the prior
        total += float(np.sum(np.log(cond[xc[te], yc[te]]) - np.log(prior[yc[te]])))
    return max(0.0, total / n)


def date_number(s: pd.Series) -> pd.Series:
    """Dates as seconds (a number that keeps their order); gaps stay gaps."""
    t = pd.to_datetime(s, errors="coerce", utc=True)
    return (t - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()


def column_mi(s: pd.Series, target: Target, profile_kind: str | None = None) -> float:
    """MI of one column with the target; text / ID columns count as 0."""
    if profile_kind in ("text", "id", "empty", "constant", "skip"):
        return 0.0
    if profile_kind == "date":
        return mutual_info(codes(date_number(s), "number"), target.codes)
    return mutual_info(codes(s), target.codes)


# --------------------------------------------------------------------------- #
# Leakage
# --------------------------------------------------------------------------- #

def _oof_scores(xc: np.ndarray, yv: np.ndarray, m: float = 2.0) -> np.ndarray:
    """Out-of-fold mean of yv per group of xc (the prediction of a one-column model)."""
    n = len(xc)
    kx = int(xc.max()) + 1 if n else 1
    out = np.empty(n)
    fold = fold_ids(n)
    for f in range(FOLDS):
        tr, te = fold != f, fold == f
        prior = yv[tr].mean() if tr.any() else 0.0
        sums = np.bincount(xc[tr], weights=yv[tr], minlength=kx)
        counts = np.bincount(xc[tr], minlength=kx)
        out[te] = ((sums + m * prior) / (counts + m))[xc[te]]
    return out


def predictive_power(s: pd.Series, target: Target) -> tuple:
    """How well this column ALONE predicts the target, out-of-fold -> (metric, value).

    2 classes: AUC · more classes: accuracy · numbers: R². Above 0.99 = leakage
    (the column was probably made from the target)."""
    keep = target.codes >= 0
    kind = feature_kind(s)
    xc = codes(s[keep], kind, bins=LEAK_BINS)
    if target.task == "binary":
        yv = target.codes[keep].astype(float)
        score = _oof_scores(xc, yv)
        value = assoc.auc(target.codes[keep], score)
        if kind == "number":
            x = pd.to_numeric(s[keep], errors="coerce").to_numpy(float)
            raw = assoc.auc(target.codes[keep], np.where(np.isfinite(x), x, np.nanmedian(x) if np.isfinite(x).any() else 0))
            value = max(value if not math.isnan(value) else 0.0, raw, 1 - raw) if not math.isnan(raw) else value
        return "AUC", (0.5 if value is None or math.isnan(value) else float(value))
    if target.task == "multiclass":
        yc = target.codes[keep]
        k = int(yc.max()) + 1
        n = len(yc)
        fold = fold_ids(n)
        hits = 0
        kx = int(xc.max()) + 1
        for f in range(FOLDS):
            tr, te = fold != f, fold == f
            table = np.bincount(xc[tr] * k + yc[tr], minlength=kx * k).reshape(kx, k)
            fallback = np.bincount(yc[tr], minlength=k).argmax()
            best = np.where(table.sum(axis=1) > 0, table.argmax(axis=1), fallback)
            hits += int((best[xc[te]] == yc[te]).sum())
        return "accuracy", hits / max(1, n)
    y = pd.to_numeric(target.values[keep], errors="coerce").to_numpy(float)
    pred = _oof_scores(xc, y)
    var = float(np.var(y))
    r2 = 1 - float(np.mean((y - pred) ** 2)) / var if var > 0 else 0.0
    if kind == "number":
        x = pd.to_numeric(s[keep], errors="coerce").to_numpy(float)
        ok = np.isfinite(x)
        if ok.sum() > 2 and np.std(x[ok]) > 0:
            r = np.corrcoef(x[ok], y[ok])[0, 1]
            r2 = max(r2, float(r * r) * ok.mean())
    return "R²", float(r2)


def is_leak(metric: str, value: float, target: Target) -> bool:
    if target.task == "multiclass":
        base = np.bincount(target.codes[target.codes >= 0]).max() / max(1, (target.codes >= 0).sum())
        return value > LEAK_LIMIT and base < LEAK_LIMIT
    return value > LEAK_LIMIT


# --------------------------------------------------------------------------- #
# Redundancy
# --------------------------------------------------------------------------- #

def same_information(a: np.ndarray, b: np.ndarray) -> float:
    """0..1: 1 when each group of a matches one group of b and back (MI over the larger entropy)."""
    ka, kb = int(a.max()) + 1, int(b.max()) + 1
    table = np.bincount(a * kb + b, minlength=ka * kb).reshape(ka, kb).astype(float)
    p = table / table.sum()
    pa, pb = p.sum(axis=1), p.sum(axis=0)
    nz = p > 0
    mi = float(np.sum(p[nz] * np.log(p[nz] / np.outer(pa, pb)[nz])))
    ha = -float(np.sum(pa[pa > 0] * np.log(pa[pa > 0])))
    hb = -float(np.sum(pb[pb > 0] * np.log(pb[pb > 0])))
    top = max(ha, hb)
    return mi / top if top > 0 else 1.0


def redundancy(new: pd.Series, table: pd.DataFrame, kinds: dict, skip=()) -> tuple:
    """-> (column, value, how) of the existing column the new one copies (|r| or shared info
    above 0.95), else (None, 0, '')."""
    best = (None, 0.0, "")
    if feature_kind(new) == "number":
        x = pd.to_numeric(new, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)
        for name in table.columns:
            if name in skip or kinds.get(name) not in ("number", "category") or not is_number(table[name]):
                continue
            y = pd.to_numeric(table[name], errors="coerce").astype(float)
            ok = x.notna() & y.notna()
            if ok.sum() < 10 or x[ok].std() == 0 or y[ok].std() == 0:
                continue
            r = abs(float(np.corrcoef(x[ok], y[ok])[0, 1]))
            if r > best[1]:
                best = (name, r, "r")
    else:
        a = codes(new, "category")
        for name in table.columns:
            if name in skip or kinds.get(name) != "category":
                continue
            v = same_information(a, codes(table[name], "category"))
            if v > best[1]:
                best = (name, v, "shared")
    return best if best[1] > REDUNDANT else (None, best[1], "")


# --------------------------------------------------------------------------- #
# Plain-words link to the target
# --------------------------------------------------------------------------- #

def _fmt(v) -> str:
    if isinstance(v, (float, np.floating)):
        if float(v).is_integer():
            return str(int(v))
        return f"{v:.3g}"
    return str(v)


def describe_link(s: pd.Series, target: Target, name: str) -> str:
    """One sentence, e.g. 'Survived = 1 is most common for family_size 2–4 (58% vs 38% overall).'"""
    keep = target.codes >= 0
    s = s[keep]
    if target.task == "regression":
        yv = pd.to_numeric(target.values[keep], errors="coerce").astype(float)
        what, overall = f"{target.name} (mean)", float(yv.mean())
    elif target.task == "binary":
        yv = pd.Series(target.codes[keep].astype(float), index=s.index)
        what, overall = target.word(), float(yv.mean())
    else:
        common = pd.Series(target.codes[keep]).value_counts().idxmax()
        label = target.classes[common]
        yv = pd.Series((target.codes[keep] == common).astype(float), index=s.index)
        what, overall = f"{target.name} = {label}", float(yv.mean())
    n = len(s)
    min_rows = max(10, int(0.02 * n))
    ordered = is_number(s)
    if ordered and s.nunique() > 12:
        groups = pd.qcut(pd.to_numeric(s, errors="coerce"), 5, duplicates="drop")
        stats = yv.groupby(groups, observed=True).agg(["mean", "count"])
        stats = stats[stats["count"] >= min_rows]
        if stats.empty:
            return ""
        top = stats["mean"].idxmax()
        lo, hi = _fmt(top.left), _fmt(top.right)
        place = f"{name} {lo}–{hi}"
        best = stats.loc[top, "mean"]
    else:
        stats = yv.groupby(s.astype("object").where(s.notna(), "missing")).agg(["mean", "count"])
        stats = stats[stats["count"] >= min_rows]
        if len(stats) < 2:
            return ""
        top = stats["mean"].idxmax()
        best = stats.loc[top, "mean"]
        if ordered and top != "missing":
            # widen to the neighbouring values that are also well above the overall level
            values = [v for v in stats.index if v != "missing"]
            values.sort()
            i = values.index(top)
            lo_i = hi_i = i
            limit = overall + 0.5 * (best - overall)
            while lo_i > 0 and stats.loc[values[lo_i - 1], "mean"] >= limit:
                lo_i -= 1
            while hi_i < len(values) - 1 and stats.loc[values[hi_i + 1], "mean"] >= limit:
                hi_i += 1
            if hi_i > lo_i:
                part = stats.loc[values[lo_i:hi_i + 1]]
                best = float((part["mean"] * part["count"]).sum() / part["count"].sum())
                place = f"{name} {_fmt(values[lo_i])}–{_fmt(values[hi_i])}"
            else:
                place = f"{name} = {_fmt(top)}"
        else:
            place = f"{name} = {_fmt(top)}" if top != "missing" else f"{name} missing"
    if target.task == "regression":
        return f"{what} is highest for {place} ({_fmt(best)} vs {_fmt(overall)} overall)."
    return f"{what} is most common for {place} ({best:.0%} vs {overall:.0%} overall)."
