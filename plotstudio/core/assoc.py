"""Stage 3: how strongly two columns are linked, on one 0..1 scale.

    number vs number    max(|Pearson r|, |Spearman ρ|)    straight-line or steady curved link
    groups vs number    correlation ratio η               how much of the number the groups explain
    groups vs groups    Cramér's V                        how much one grouping decides the other
    date vs number      |Spearman ρ| of value vs time     steady rise or fall over time

η and V are bias-corrected: with many small groups the plain versions come out high even for
random data (a ticket code with one passenger per value "explains" every fare). η is also
computed on ranks and the larger value is kept, so a few huge values can't hide a clear
difference between the groups (same idea as max(Pearson, Spearman) for two numbers).

Only numpy and pandas are needed (no scipy), and nothing here prints warnings.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

MIN_ROWS = 10        # fewer rows with both values -> no link is reported


def quiet():
    """Silence divide-by-zero noise on degenerate data (thread-safe, unlike warnings filters,
    so the analysis can run in a background thread while the app draws plots)."""
    return np.errstate(all="ignore")


def ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks (ties share a rank); missing stays missing."""
    return pd.Series(values).rank(method="average").to_numpy(dtype=float)


def codes_of(s: pd.Series):
    """Category codes 0..k-1 (-1 = missing) and the labels, numbers in numeric order."""
    try:
        codes, labels = pd.factorize(s, sort=True)
    except TypeError:                        # mixed types (12 and "12") can't be sorted
        codes, labels = pd.factorize(s, sort=False)
    return np.asarray(codes, dtype=np.int64), list(labels)


# --------------------------------------------------------------------------- #
# number vs number (all pairs at once)
# --------------------------------------------------------------------------- #

def number_matrices(num: pd.DataFrame):
    """Pearson and Spearman matrices plus the number of rows behind each pair."""
    with quiet():
        pearson = num.corr(method="pearson", min_periods=MIN_ROWS)
        spearman = num.rank().corr(method="pearson", min_periods=MIN_ROWS)   # Spearman = Pearson on ranks
    present = num.notna().to_numpy(dtype=np.float64)
    counts = pd.DataFrame(present.T @ present, index=num.columns, columns=num.columns)
    return pearson, spearman, counts


def pearson_pair(x: np.ndarray, y: np.ndarray):
    """(r, rho, n) for two float arrays with gaps."""
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    if n < MIN_ROWS:
        return math.nan, math.nan, n
    a, b = x[m], y[m]
    with quiet():
        r = np.corrcoef(a, b)[0, 1]
        rho = np.corrcoef(ranks(a), ranks(b))[0, 1]
    return float(r), float(rho), n


# --------------------------------------------------------------------------- #
# groups vs number
# --------------------------------------------------------------------------- #

def _eta_sq(codes: np.ndarray, k: int, y: np.ndarray):
    """Bias-corrected eta² (epsilon²) of y explained by the groups; codes and y already masked."""
    n = y.size
    counts = np.bincount(codes, minlength=k).astype(float)
    sums = np.bincount(codes, weights=y, minlength=k)
    used = counts > 0
    groups = int(used.sum())
    if groups < 2 or n <= groups:
        return 0.0
    grand = y.mean()
    ss_total = float(((y - grand) ** 2).sum())
    if ss_total <= 0:
        return 0.0
    means = sums[used] / counts[used]
    ss_between = float((counts[used] * (means - grand) ** 2).sum())
    raw = ss_between / ss_total
    adjusted = 1 - (1 - raw) * (n - 1) / (n - groups)
    return min(1.0, max(0.0, adjusted))


def eta(codes: np.ndarray, k: int, y: np.ndarray, y_ranks: np.ndarray | None = None):
    """(η, n): correlation ratio of a number y over groups, the larger of raw and rank version."""
    m = (codes >= 0) & np.isfinite(y)
    n = int(m.sum())
    if n < MIN_ROWS:
        return 0.0, n
    c = codes[m]
    with quiet():
        raw = _eta_sq(c, k, y[m])
        rk = ranks(y[m]) if y_ranks is None else y_ranks[m]
        on_ranks = _eta_sq(c, k, rk)
    return math.sqrt(max(raw, on_ranks)), n


def auc(positive: np.ndarray, y: np.ndarray):
    """Area under the ROC curve of y for a 0/1 array (0.5 = no help, 1 or 0 = perfect split)."""
    m = (positive >= 0) & np.isfinite(y)
    pos = positive[m] == 1
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    rk = ranks(y[m])
    return float((rk[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


# --------------------------------------------------------------------------- #
# groups vs groups
# --------------------------------------------------------------------------- #

def crosstab(ca: np.ndarray, ka: int, cb: np.ndarray, kb: int):
    """Counts table (ka x kb) of two code arrays, rows with a gap left out."""
    m = (ca >= 0) & (cb >= 0)
    flat = np.bincount(ca[m] * kb + cb[m], minlength=ka * kb)
    return flat.reshape(ka, kb), int(m.sum())


def cramers_v(table: np.ndarray):
    """Bias-corrected Cramér's V (Bergsma 2013) of a counts table."""
    table = np.asarray(table, dtype=float)
    table = table[table.sum(axis=1) > 0][:, table.sum(axis=0) > 0]
    r, k = table.shape
    n = table.sum()
    if r < 2 or k < 2 or n < MIN_ROWS:
        return 0.0
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / n
    with quiet():
        chi2 = float(((table - expected) ** 2 / expected).sum())
    phi2 = max(0.0, chi2 / n - (k - 1) * (r - 1) / (n - 1))
    rc = r - (r - 1) ** 2 / (n - 1)
    kc = k - (k - 1) ** 2 / (n - 1)
    denom = min(kc - 1, rc - 1)
    return float(min(1.0, math.sqrt(phi2 / denom))) if denom > 0 else 0.0


def determines(table: np.ndarray, min_rows: int = 5) -> float:
    """Share of rows whose column value (rows of `table`) fixes the other value (purity).

    1.0 means every value of the first column always comes with the same value of the
    second, e.g. 'alive' = yes always comes with survived = 1. Values with fewer than
    `min_rows` rows don't count, so ID-like columns can't look perfect by accident."""
    table = np.asarray(table, dtype=float)
    big = table.sum(axis=1) >= min_rows
    if big.sum() < 2:
        return 0.0
    t = table[big]
    return float(t.max(axis=1).sum() / t.sum())


# --------------------------------------------------------------------------- #
# date vs number
# --------------------------------------------------------------------------- #

def date_values(t: pd.Series) -> np.ndarray:
    """Dates as float seconds (any resolution or time zone), NaN for gaps."""
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert("UTC").dt.tz_localize(None)
    out = np.full(len(t), np.nan)
    ok = t.notna().to_numpy()
    if ok.any():
        out[ok] = (t[ok] - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy(dtype=float)
    return out


def trend(t: np.ndarray, y: np.ndarray):
    """(ρ, n): Spearman correlation of a number with time (signed)."""
    m = np.isfinite(t) & np.isfinite(y)
    n = int(m.sum())
    if n < MIN_ROWS:
        return math.nan, n
    with quiet():
        rho = np.corrcoef(ranks(t[m]), ranks(y[m]))[0, 1]
    return float(rho), n
