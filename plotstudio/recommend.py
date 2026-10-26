"""Which column to put on which axis: ranked suggestions, each with a short reason.

The scores come from the data itself:

* the link with the target (the column a model would predict), measured exactly like the Plot ideas
  (plotstudio.core.assoc, on the same 50,000-row sample of big files):
      r / ρ = Pearson / Spearman    number vs number     (-1 … +1; the larger of |r| and |ρ| ranks)
      η = correlation ratio         number vs groups     (0 = groups look alike, 1 = fully apart)
      V = Cramér's V                groups vs groups     (0 = unrelated, 1 = one decides the other)
  η and V are bias-corrected, so a column with many tiny groups can't look linked by chance.
* pairs of number columns that move together (|r|), for the second axis of a scatter
* dates and always-increasing columns for the X axis of line plots
* shape (skew, outliers) for distribution plots when there is no target
* missing values for the missing-values map, 0–1 columns for predicted probabilities

Big files are scored on the Plot ideas' random sample of 50,000 rows, so both tabs show the same numbers.
"""
from __future__ import annotations

import math
import re
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .core import assoc
from .core.profiler import SAMPLE_ROWS
from .data import DATETIME, EMPTY, NUMERIC, TARGET_NAMES, TEXT, Dataset
from .graphs import GraphType, Role, compatible, suggest

SAMPLE = SAMPLE_ROWS          # the same sample as the Plot ideas (random_state=0, file order)
TOP = 8
DISTRIBUTIONS = ("hist", "kde", "box", "violin", "strip", "ecdf", "qq")
METRIC_WORDS = ("loss", "acc", "score", "error", "metric", "auc", "f1", "precision", "recall", "rmse", "mae")
ORDER_WORDS = ("epoch", "step", "time", "date", "year", "iter", "day", "month", "week", "hour", "index")
TARGET_WORDS = ("target", "price", "sales", "revenue", "salary", "label")
SYMBOLS = {"eta": "η", "rho": "ρ"}   # the app swaps in "eta" / "rho" if the window font has no Greek letters


@dataclass
class Pick:
    column: str
    score: float
    reason: str          # short: shown next to the column name
    detail: str = ""     # one sentence: shown in the status line


def short(name, n=18) -> str:
    name = str(name)
    return name if len(name) <= n else name[: n - 1] + "…"


# --------------------------------------------------------------------------- #
# Target
# --------------------------------------------------------------------------- #

def target_choices(ds: Dataset) -> list:
    """Columns that can be a target: a few classes (2–20) or a number column (not an ID)."""
    out = []
    for c, i in ds.columns.items():
        if i.is_id or i.skipped or i.kind in (EMPTY, TEXT, DATETIME):
            continue
        if (i.groupable and 2 <= i.unique <= 20) or i.kind == NUMERIC:
            out.append(c)
    return out


def default_target(ds: Dataset):
    """A class column the app recognises, else a number column named like a target, else None."""
    t = ds.guess_target()
    if t:
        return t
    names = {c.strip().lower() for c in ds.columns}
    for c in target_choices(ds):
        low = c.strip().lower()
        if low in ("y", "z") and "x" in names:
            continue   # x / y / z coordinates, not a target
        if TARGET_NAMES.match(c.strip()) or any(w in low for w in TARGET_WORDS):
            return c
    return None


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #

def eta(values: pd.Series, groups: pd.Series) -> float:
    """Correlation ratio: how much of the spread of `values` is explained by the groups (0..1), bias-corrected
    and the larger of the raw and the rank version (core.assoc.eta, as in the Plot ideas). NaN: can't tell."""
    codes, labels = assoc.codes_of(groups)
    y = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    ok = (codes >= 0) & np.isfinite(y)
    if ok.sum() < assoc.MIN_ROWS or len(np.unique(codes[ok])) < 2 or np.nanstd(y[ok]) == 0:
        return float("nan")
    return float(assoc.eta(codes, len(labels), y)[0])


def cramers_v(a: pd.Series, b: pd.Series) -> float:
    """Cramér's V between two group columns (0..1), bias-corrected (core.assoc, as in the Plot ideas).
    NaN: can't tell."""
    ca, la = assoc.codes_of(a)
    cb, lb = assoc.codes_of(b)
    table, n = assoc.crosstab(ca, len(la), cb, len(lb))
    used = table[table.sum(axis=1) > 0][:, table.sum(axis=0) > 0]
    if n < assoc.MIN_ROWS or min(used.shape, default=0) < 2:
        return float("nan")
    return float(assoc.cramers_v(table))


def balance(s: pd.Series) -> float:
    """1 = all groups the same size, near 0 = one group dominates."""
    counts = s.value_counts(dropna=True).to_numpy(dtype=float)
    if len(counts) < 2:
        return 0.0
    p = counts / counts.sum()
    return float(-(p * np.log(p)).sum() / math.log(len(p)))


class Profile:
    """Scores for one dataset and one target, computed when first needed."""

    def __init__(self, ds: Dataset, target=None):
        self.ds = ds
        self.target = target if target in ds.columns else None
        df = ds.df
        self.df = df.sample(SAMPLE, random_state=0).sort_index() if len(df) > SAMPLE else df
        info = ds.columns
        self.nums = [c for c, i in info.items() if i.kind == NUMERIC and not i.is_id and not i.skipped
                     and i.unique > 1]
        self.tkind = None
        if self.target:
            ti = info[self.target]
            if ti.groupable and ti.unique <= 20:
                self.tkind = "class"
            elif ti.kind == NUMERIC:
                self.tkind = "number"
        self._links = {}
        self._corr = None
        self._shape = {}
        self._dominant = {}

    # link with the target ------------------------------------------------
    def link(self, col):
        """(score 0..1, short text, sentence) for the link between col and the target, or None."""
        if col in self._links:
            return self._links[col]
        out = None
        t = self.target
        if t and col != t and col in self.df.columns:
            i = self.ds.info(col)
            try:
                if self.tkind == "class" and i.kind == NUMERIC:
                    v = eta(self.df[col], self.df[t])
                    out = (v, f"{SYMBOLS['eta']} {v:.2f}", f"'{col}' looks different for each '{t}' class: {SYMBOLS['eta']} = {v:.2f}  "
                                           f"(0 = no difference, 1 = the classes are fully apart).")
                elif self.tkind == "class" and i.groupable:
                    v = cramers_v(self.df[col], self.df[t])
                    out = (v, f"V {v:.2f}", f"'{col}' and '{t}' go together: Cramér's V = {v:.2f}  "
                                           f"(0 = unrelated, 1 = one decides the other).")
                elif self.tkind == "number" and i.kind == NUMERIC:
                    r, rho, n = assoc.pearson_pair(pd.to_numeric(self.df[col], errors="coerce").to_numpy(dtype=float),
                                                   pd.to_numeric(self.df[t], errors="coerce").to_numpy(dtype=float))
                    if abs(rho) > abs(r) + 0.1:              # curved but steady: the rank correlation says more
                        s = SYMBOLS["rho"]
                        out = (abs(rho), f"{s} {rho:+.2f}", f"'{col}' moves with '{t}' (not in a straight line): "
                                                           f"Spearman {s} = {rho:+.2f}, r = {r:+.2f}  (-1 … +1).")
                    else:
                        out = (max(abs(r), abs(rho)), f"r {r:+.2f}", f"'{col}' moves with '{t}': r = {r:+.2f}  "
                                                                     f"(-1 … +1, 0 = no straight-line link).")
                elif self.tkind == "number" and i.groupable:
                    v = eta(self.df[t], self.df[col])
                    out = (v, f"{SYMBOLS['eta']} {v:.2f}", f"'{t}' differs between the groups of '{col}': {SYMBOLS['eta']} = {v:.2f}  "
                                           f"(0 = no difference, 1 = fully apart).")
            except Exception:  # noqa: BLE001 - a column that can't be scored is simply not ranked
                out = None
            if out is not None and not math.isfinite(out[0]):
                out = None
        self._links[col] = out
        return out

    # pairs of numbers ------------------------------------------------------
    def corr(self):
        if self._corr is None:
            cols = list(dict.fromkeys(self.nums + ([self.target] if self.tkind == "number" else [])))[:120]
            data = self.df[cols].apply(pd.to_numeric, errors="coerce") if cols else pd.DataFrame()
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore")
                self._corr = data.corr() if cols else pd.DataFrame()
        return self._corr

    def pair(self, a, b) -> float:
        m = self.corr()
        if a in m.index and b in m.columns:
            v = m.at[a, b]
            if pd.notna(v):
                return float(v)
        try:
            with warnings.catch_warnings(), np.errstate(all="ignore"):
                warnings.simplefilter("ignore")
                v = pd.to_numeric(self.df[a], errors="coerce").corr(pd.to_numeric(self.df[b], errors="coerce"))
            return float(v) if pd.notna(v) else 0.0
        except Exception:  # noqa: BLE001
            return 0.0

    def best_partner(self, col, exclude=()):
        """(other column, r) with the strongest straight-line link to col."""
        m = self.corr()
        if col not in m.index:
            return None, 0.0
        row = m.loc[col].drop(labels=[c for c in [col, *exclude] if c in m.columns], errors="ignore").dropna()
        if row.empty:
            return None, 0.0
        other = row.abs().idxmax()
        return other, float(row[other])

    def dominant(self, col) -> float:
        """Share of the most common value (1.0 = the column is nearly constant)."""
        if col not in self._dominant:
            s = self.df[col].dropna()
            self._dominant[col] = float(s.value_counts(normalize=True).iloc[0]) if len(s) else 1.0
        return self._dominant[col]

    # shape of one number column ---------------------------------------------
    def shape(self, col):
        if col not in self._shape:
            s = pd.to_numeric(self.df[col], errors="coerce").dropna()
            skew, out_share = 0.0, 0.0
            if len(s) > 3 and s.std() > 0:
                skew = float(s.skew())
                q1, q3 = s.quantile(0.25), s.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    out_share = float(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).mean())
            self._shape[col] = (skew if math.isfinite(skew) else 0.0, out_share)
        return self._shape[col]


_CACHE = {}


def forget(ds: Dataset) -> None:
    """Drop the cached profiles of ds (its column kinds were relabelled)."""
    for key in [k for k, prof in _CACHE.items() if prof.ds is ds]:
        del _CACHE[key]


def profile(ds: Dataset, target=None) -> Profile:
    key = (id(ds), target)
    prof = _CACHE.get(key)
    if prof is None or prof.ds is not ds:
        if len(_CACHE) > 12:
            _CACHE.clear()
        prof = _CACHE[key] = Profile(ds, target)
    return prof


# --------------------------------------------------------------------------- #
# Ranking for one slot
# --------------------------------------------------------------------------- #

def rank(graph: GraphType, role: Role, ds: Dataset, sel: dict | None = None, target=None,
         show_all=False, limit=TOP) -> list:
    """Suggested columns for one slot of a graph, best first (a list of Pick)."""
    prof = profile(ds, target)
    sel = sel or {}
    keep_ids = show_all or role.prefer in ("ordered", "all")
    pool = [c for c in compatible(role, ds, show_all=show_all)
            if (keep_ids or not ds.info(c).is_id) and (ds.info(c).kind != EMPTY or role.accepts == "all")]
    used = set()
    for r in graph.roles:
        if r.key != role.key:
            v = sel.get(r.key)
            used.update(v if isinstance(v, list) else [v] if v else [])
    pool = [c for c in pool if c not in used]
    if not pool:
        return []
    picks = _dispatch(graph, role, prof, pool, sel)
    if role.accepts in ("num", "num_time", "num_cat", "any") and role.prefer not in ("pixels", "all"):
        picks = _penalise_flat(graph, prof, picks)
    if role.key in ("x", "y", "z") and not role.multi:
        named = [c for c in pool if c.strip().lower() == role.key]
        picks = [Pick(c, 50.0, f"named '{role.key}'", f"The column is called '{c}', just like this axis.")
                 for c in named] + picks
    seen, out = set(), []
    for p in sorted(picks, key=lambda p: -p.score):
        if p.column in pool and p.column not in seen:
            seen.add(p.column)
            out.append(p)
    return out[:limit] if limit else out


def _dispatch(graph, role, prof, pool, sel):
    p, key, gid = role.prefer, role.key, graph.id
    if key == "actual":
        return _actual(prof, pool)
    if p == "pred":
        return _predicted(prof, pool, sel.get("actual"))
    if p == "proba":
        return _probabilities(prof, pool)
    if p == "pixels":
        labels = {sel.get("label"), prof.target}
        return [Pick(c, 1.0 - i * 1e-6, "pixel column", "") for i, c in enumerate(pool)
                if c not in labels and c.strip().lower() not in ("label", "labels", "target", "class", "digit", "y")]
    if p == "label":
        return _label(prof, pool)
    if p == "all":
        return _missing(prof, pool)
    if key == "err":
        return _errors(prof, pool)
    if p == "ordered":
        return _ordered(prof, pool)
    if p == "numtarget":
        return _numtarget(prof, pool, sel)
    if key in ("hue", "color", "labels") or (p == "target" and role.accepts in ("cat", "binary", "num_cat", "any")):
        return _groups(prof, pool)
    if role.accepts == "cat" or p == "nontarget":
        return _groupings(prof, pool, _value_column(graph, sel, prof))
    if role.multi:
        return _features(prof, pool, gid)
    return _numbers(prof, pool, graph, role, sel)


SPREAD_GRAPHS = ("kde2d", "contour", "surface3d", "scatter3d", "hexbin", "joint", "regression", "kde", "qq")


def _penalise_flat(graph, prof, picks):
    """Number columns that are (nearly) one value make poor axes: rank them last, or drop them where a
    plot needs real spread (densities, contours, surfaces)."""
    out = []
    for p in picks:
        info = prof.ds.info(p.column) if p.column in prof.ds.columns else None
        if info is None or info.kind != NUMERIC or p.reason.startswith("your target"):
            out.append(p)
            continue
        share = prof.dominant(p.column)
        if graph.id in SPREAD_GRAPHS and (info.unique < 3 or share > 0.95):
            continue
        if share > 0.9:
            p.score *= 0.05
            p.reason = (p.reason + " · " if p.reason else "") + f"{share:.0%} one value"
            p.detail = (p.detail + "  " if p.detail else "") + f"Most rows ({share:.0%}) hold the same value."
        out.append(p)
    return out


def _value_column(graph, sel, prof):
    """The number column the groups are compared on (e.g. the Values of a box plot)."""
    for key in ("y", "value", "values", "x"):
        v = sel.get(key)
        if isinstance(v, list):
            v = v[0] if v else None
        if v and v in prof.ds.columns and prof.ds.info(v).kind == NUMERIC and not prof.ds.info(v).groupable:
            return v
    return prof.target if prof.tkind == "number" else None


def _link_pick(prof, c, weight=1.0, prefix=""):
    L = prof.link(c)
    if L is None:
        return None
    return Pick(c, L[0] * weight, f"{prefix}{L[1]} · {short(prof.target, 14)}", L[2])


def _groups(prof, pool):
    """Colour / slices / class columns: the target first, then groups linked to it."""
    out, t, ds = [], prof.target, prof.ds
    for c in pool:
        i = ds.info(c)
        if c == t and i.groupable:
            out.append(Pick(c, 10.0, "your target", f"'{c}' is the target: colouring by it shows how "
                                                    f"the classes differ."))
            continue
        if not i.groupable:
            p = _link_pick(prof, c, 0.5)
            out.append(p or Pick(c, 0.02, "number → colour scale", f"'{c}' is a number: it gets a colour scale."))
            continue
        n = i.unique
        size_ok = 1.0 if 2 <= n <= 8 else 0.7 if n <= 15 else 0.4
        bal = balance(prof.df[c])
        p = _link_pick(prof, c, size_ok)
        if p:
            p.reason = f"{n} groups · {p.reason}"
            out.append(p)
        else:
            even = " of similar size" if bal > 0.8 else ""
            out.append(Pick(c, 0.3 * size_ok * (0.5 + 0.5 * bal), f"{n} groups" + (", even" if bal > 0.8 else ""),
                            f"'{c}' has {n} groups{even}: easy to tell apart."))
    return out


def _groupings(prof, pool, value):
    """Group-by / category columns: those that split the value (or the target) the most."""
    out, t, ds = [], prof.target, prof.ds
    for c in pool:
        if c == value:
            continue
        i = ds.info(c)
        n = i.unique
        size_ok = 1.0 if 2 <= n <= 12 else 0.6 if n <= 30 else 0.25
        if not i.groupable:
            out.append(Pick(c, 0.01, "number (many values)", f"'{c}' has {n:,} different values."))
            continue
        if value and value != c:
            v = eta(prof.df[value], prof.df[c])
            if math.isfinite(v):
                mine = c == t   # comparing the classes of the target is the classic first look
                out.append(Pick(c, v * size_ok + (0.5 if mine else 0.0),
                                ("your target · " if mine else "") + f"{SYMBOLS['eta']} {v:.2f} for {short(value, 14)}",
                                f"'{value}' differs between the {n} groups of '{c}': {SYMBOLS['eta']} = {v:.2f}  "
                                f"(0 = no difference, 1 = fully apart)."))
                continue
        if c == t:
            out.append(Pick(c, 2.0, "your target", f"'{c}' is the target: one group per class."))
            continue
        p = _link_pick(prof, c, size_ok)
        out.append(p or Pick(c, 0.2 * size_ok, f"{n} groups", f"'{c}' has {n} groups."))
    return out


def _features(prof, pool, gid):
    """Several number columns (histograms, pair plot, correlation map, line Y, ...)."""
    out, t = [], prof.target
    if t in pool and prof.tkind == "number" and gid in ("corr", "pairplot") + DISTRIBUTIONS:
        why = {"corr": "its row shows every feature's link", "pairplot": "every feature is plotted against it"}
        out.append(Pick(t, 10.0, "your target", f"'{t}' is the target: "
                                               f"{why.get(gid, 'look at its shape first (skew, outliers)')}."))
    for c in pool:
        if c == t:
            if gid in ("line", "area") and prof.tkind == "number":
                out.append(Pick(c, 10.0, "your target", f"'{c}' is the target: see how it changes."))
            continue
        if t and c != t:
            p = _link_pick(prof, c)
            if p:
                out.append(p)
                continue
        low = c.lower()
        if gid in ("line", "area") and any(w in low for w in METRIC_WORDS):
            out.append(Pick(c, 0.9, "training metric", f"'{c}' looks like a training metric (loss, accuracy, …)."))
        elif gid in DISTRIBUTIONS and c in prof.nums:
            skew, outl = prof.shape(c)
            score = min(1.0, abs(skew) / 3) * 0.6 + min(1.0, outl * 10) * 0.4
            if outl >= 0.02 and outl * 10 >= abs(skew) / 3:
                reason, detail = f"{outl:.0%} outliers", f"'{c}' has {outl:.1%} values far from the rest."
            elif abs(skew) >= 0.5:
                reason = f"skew {skew:+.1f}"
                detail = f"'{c}' is lopsided (skew = {skew:+.2f}): a long tail on the " \
                         f"{'right' if skew > 0 else 'left'}."
            else:
                reason, detail = "evenly spread", f"'{c}' is fairly symmetric."
            out.append(Pick(c, score, reason, detail))
        elif c in prof.nums:
            other, r = prof.best_partner(c, exclude=[t] if t else [])
            if other is not None:
                out.append(Pick(c, abs(r) * 0.8, f"r {r:+.2f} with {short(other, 12)}",
                                f"'{c}' moves with '{other}': r = {r:+.2f}."))
            else:
                out.append(Pick(c, 0.05, "number", ""))
        else:
            out.append(Pick(c, 0.01, "", ""))
    return out


def _numbers(prof, pool, graph, role, sel):
    """One number slot: X of a relationship plot, its Y partner, Z, size, value, ..."""
    out, t, ds, key = [], prof.target, prof.ds, role.key
    numeric_pool = [c for c in pool if ds.info(c).kind == NUMERIC]
    if key in ("value", "values") or (graph.id in ("bar", "errorbar") and key == "y"):
        # a value compared between groups: the target, else what is linked to it
        for c in numeric_pool:
            if c == t and prof.tkind == "number":
                out.append(Pick(c, 5.0, "your target", f"'{c}' is the target: compare its average per group."))
                continue
            p = _link_pick(prof, c)
            out.append(p or Pick(c, 0.05, "number", ""))
        return out
    partner = sel.get("x") if key == "y" else None
    if isinstance(partner, list):
        partner = partner[0] if partner else None
    if partner and (partner not in ds.columns or ds.info(partner).kind != NUMERIC):
        partner = None
    if key == "z":
        xs = [c for c in (sel.get("x"), sel.get("y")) if c and c in ds.columns and ds.info(c).kind == NUMERIC]
        grid = False
        if len(xs) == 2:
            nx, ny = prof.df[xs[0]].nunique(), prof.df[xs[1]].nunique()
            pairs = len(prof.df[xs].drop_duplicates())
            grid = nx * ny <= 1.5 * pairs and nx <= len(prof.df) / 2 and ny <= len(prof.df) / 2
        for c in numeric_pool:
            if grid:
                try:
                    functional = int(prof.df.groupby(xs)[c].nunique().max()) <= 1
                except Exception:  # noqa: BLE001
                    functional = False
                if functional:
                    out.append(Pick(c, 2.0, "one value per grid point", f"'{c}' has exactly one value at every "
                                                                       f"(x, y) point of the grid: a surface."))
                    continue
            if c == t:
                out.append(Pick(c, 1.5, "your target", f"'{c}' is the target."))
                continue
            p = _link_pick(prof, c)
            if p:
                out.append(p)
                continue
            rs = [prof.pair(c, x) for x in xs]
            r = max(rs, key=abs) if rs else 0.0
            out.append(Pick(c, abs(r) * 0.5, f"r {r:+.2f} with X/Y" if rs else "number", ""))
        return out
    if key == "y" and partner:
        for c in numeric_pool:
            if c == t and prof.tkind == "class":
                continue   # a class target belongs in 'Colour by'
            if c == t and prof.tkind == "number":
                out.append(Pick(c, 5.0, "your target", f"Plot '{partner}' against the target '{c}' "
                                                       f"to see how well it predicts it."))
                continue
            r = prof.pair(c, partner)
            if prof.tkind == "class":
                # two features that each separate the classes: the classic coloured scatter
                p = _link_pick(prof, c)
                if p:
                    p.detail += f"  With '{partner}': r = {r:+.2f}."
                    out.append(p)
                    continue
            out.append(Pick(c, abs(r), f"r {r:+.2f} with {short(partner, 12)}",
                            f"'{c}' and '{partner}' move together: r = {r:+.2f}  (-1 … +1)."))
        return out
    # the first number slot (X): columns linked to the target, else the strongest pairs
    for c in numeric_pool:
        if c == t:
            if prof.tkind == "number" and key not in ("x",):
                out.append(Pick(c, 0.5, "your target", f"'{c}' is the target."))
            continue
        p = _link_pick(prof, c)
        if p:
            out.append(p)
            continue
        other, r = prof.best_partner(c, exclude=[t] if t else [])
        if other is not None:
            out.append(Pick(c, abs(r) * 0.8, f"r {r:+.2f} with {short(other, 12)}",
                            f"'{c}' moves with '{other}': r = {r:+.2f}."))
        else:
            out.append(Pick(c, 0.05, "number", ""))
    return out


def _numtarget(prof, pool, sel):
    """The column to predict (regression Y, correlation-with-target)."""
    out, t, ds = [], prof.target, prof.ds
    partner = sel.get("x")
    for c in pool:
        i = ds.info(c)
        if c == t:
            out.append(Pick(c, 10.0, "your target", f"'{c}' is the target."))
        elif TARGET_NAMES.match(c.strip()) or any(w in c.lower() for w in TARGET_WORDS):
            out.append(Pick(c, 3.0, "target-like name", f"'{c}' is named like something to predict."))
        elif partner and partner in ds.columns and i.kind == NUMERIC and ds.info(partner).kind == NUMERIC:
            r = prof.pair(c, partner)
            out.append(Pick(c, abs(r), f"r {r:+.2f} with {short(partner, 12)}",
                            f"'{c}' and '{partner}' move together: r = {r:+.2f}."))
        elif i.unique == 2:
            out.append(Pick(c, 0.5, "2 values", f"'{c}' has two values (a yes/no outcome?)."))
        else:
            out.append(Pick(c, 0.05, "", ""))
    return out


def _ordered(prof, pool):
    """X axis of a line / area plot: dates, then columns that only go up."""
    out, ds = [], prof.ds
    for c in pool:
        i = ds.info(c)
        low = c.lower()
        if i.kind == DATETIME:
            out.append(Pick(c, 3.0, "dates", f"'{c}' holds dates: the X axis becomes a time line."))
            continue
        if i.kind == NUMERIC:
            s = ds.df[c].dropna()
            if len(s) > 2 and s.is_monotonic_increasing and s.nunique() == len(s):
                if i.is_id and not any(w in low for w in ORDER_WORDS if w != "index"):
                    out.append(Pick(c, 0.5, "row number", f"'{c}' just numbers the rows (the same as leaving "
                                                          f"the X axis empty)."))
                else:
                    out.append(Pick(c, 2.0, "always increasing", f"'{c}' only goes up (like an epoch, step or "
                                                                 f"time)."))
                continue
        if any(w in low for w in ORDER_WORDS):
            out.append(Pick(c, 1.5, "time-like name", f"'{c}' sounds like time or order."))
        elif i.kind == NUMERIC:
            out.append(Pick(c, 0.1, "number", ""))
        else:
            out.append(Pick(c, 0.05, "", ""))
    return out


def _actual(prof, pool):
    out, t, ds = [], prof.target, prof.ds
    for c in pool:
        n = ds.info(c).unique
        if c == t:
            out.append(Pick(c, 10.0, "your target", f"'{c}' is the target: the true classes."))
        elif TARGET_NAMES.match(c.strip()) or "true" in c.lower() or "actual" in c.lower():
            out.append(Pick(c, 3.0, "target-like name", f"'{c}' is named like the true answer."))
        elif "pred" in c.lower() or "prob" in c.lower():
            out.append(Pick(c, 0.01, "looks like a prediction", ""))
        else:
            out.append(Pick(c, 1.0 / (1 + n), f"{n} classes", f"'{c}' has {n} classes."))
    return out


def _predicted(prof, pool, actual):
    out, ds = [], prof.ds
    truth = set(ds.df[actual].dropna().unique()) if actual and actual in ds.columns else set()
    for c in pool:
        if c == actual:
            continue
        low = c.lower()
        values = set(ds.df[c].dropna().unique()) if ds.info(c).unique <= 50 else set()
        same = bool(truth) and len(values) >= min(2, len(truth)) and values <= truth
        if "pred" in low and same:
            out.append(Pick(c, 3.0, "predicted classes", f"'{c}' is named 'pred' and uses the same classes as "
                                                          f"'{actual}'."))
        elif same:
            exact = len(values) == len(truth)
            out.append(Pick(c, 2.0 if exact else 0.5, "same classes as actual",
                            f"'{c}' uses the same classes as '{actual}'."))
        elif _is_probability(ds, c):
            out.append(Pick(c, 1.5 if any(w in low for w in ("prob", "score", "pred")) else 1.0, "0–1 values",
                            f"'{c}' looks like a probability: it is cut at the threshold option."))
        elif "pred" in low:
            out.append(Pick(c, 1.0, "named 'pred'", ""))
        else:
            out.append(Pick(c, 0.01, "", ""))
    return out


def _probabilities(prof, pool):
    out, ds = [], prof.ds
    for c in pool:
        if c == prof.target:
            continue
        low = c.lower()
        if _is_probability(ds, c):
            named = any(w in low for w in ("prob", "score", "pred", "pr_"))
            out.append(Pick(c, 2.0 if named else 1.0, "0–1 values" + (" · named" if named else ""),
                            f"'{c}' stays between 0 and 1, like a predicted probability."))
        else:
            out.append(Pick(c, 0.01, "", ""))
    return out


def _label(prof, pool):
    out = []
    for c in pool:
        low = c.strip().lower()
        if c == prof.target or low in ("label", "labels", "target", "class", "digit", "y"):
            out.append(Pick(c, 2.0, "label", f"'{c}' looks like the answer for each picture."))
    return out


def _missing(prof, pool):
    out, ds = [], prof.ds
    for c in pool:
        pct = ds.info(c).missing_pct
        if pct > 0:
            out.append(Pick(c, 1.0 + pct, f"{pct:.1f}% missing", f"'{c}' has {ds.info(c).missing:,} missing values."))
        else:
            out.append(Pick(c, 0.0, "complete", ""))
    return out


def _errors(prof, pool):
    out = []
    for c in pool:
        low = c.lower()
        if re.search(r"(^|_|\b)(err|error|std|sd|sem|se|ci|unc|uncertainty|sigma)(_|\b|$)", low):
            out.append(Pick(c, 2.0, "error-like name", f"'{c}' is named like an error / spread column."))
    return out


def _is_probability(ds, col) -> bool:
    i = ds.info(col)
    if i.kind != NUMERIC or i.is_discrete:
        return False
    s = ds.df[col]
    return bool(s.min() >= 0 and s.max() <= 1)


# --------------------------------------------------------------------------- #
# All slots at once
# --------------------------------------------------------------------------- #

def how_many(graph: GraphType, role: Role, available: int) -> int:
    if role.prefer in ("all", "pixels") or (graph.id == "target_corr" and role.key == "features"):
        return available
    n = {"pairplot": 4, "corr": 10}.get(graph.id, role.max_default)
    return max(role.min_count, min(n, available))


def suggest_all(graph: GraphType, ds: Dataset, target=None, show_all=False):
    """Recommended columns for every slot of the graph: (selection dict, list of 'slot = column (why)')."""
    sel, notes, optional = {}, {}, []
    for role in graph.roles:
        picks = rank(graph, role, ds, sel, target, show_all=show_all, limit=0)
        if role.multi:
            if role.prefer == "all":   # missing-values map: the columns with gaps, else all
                gaps = [p.column for p in picks if p.score >= 1.0]
                chosen = gaps if gaps else [p.column for p in picks]
            else:
                good = [p for p in picks if p.score > 0.011] or picks   # skip columns with no reason at all
                if len(good) < role.min_count:
                    good = picks
                chosen = [p.column for p in good[: how_many(graph, role, len(good))]]
            if len(chosen) >= role.min_count:
                sel[role.key] = chosen
                why = f" ({picks[0].reason})" if picks and picks[0].reason and len(chosen) == 1 else ""
                names = ", ".join(chosen[:4]) + ("…" if len(chosen) > 4 else "")
                notes[role.key] = f"{role.label}: {names}{why}"
            continue
        if not picks:
            sel[role.key] = None
            continue
        top = picks[0]
        if role.required and top.score <= 0.011:
            sel[role.key] = None   # nothing really fits: the usual guess below
            continue
        if not role.required:
            if not (top.reason.startswith("your target") or (role.auto and top.score >= 1.0)):
                sel[role.key] = None   # optional slots are only filled when the choice is clearly useful
                continue
            optional.append(role.key)
        sel[role.key] = top.column
        notes[role.key] = f"{role.label} = {top.column}" + (f" ({top.reason})" if top.reason else "")
    base = suggest(graph, ds, show_all=show_all)
    for role in graph.roles:   # anything still empty: the usual pre-filled guess
        value = sel.get(role.key)
        if role.required and (not value or (role.multi and len(value) < role.min_count)):
            sel[role.key] = base.get(role.key)
            notes.pop(role.key, None)
    # an optional extra that the graph can't use here (e.g. colour without an X axis) is left out
    for key in reversed(optional):
        if _builds(graph, ds, sel):
            break
        sel[key] = None
        notes.pop(key, None)
    return sel, [notes[r.key] for r in graph.roles if r.key in notes]


def _builds(graph, ds, sel) -> bool:
    from .engine import LabelSettings, StyleSettings, build_plot
    from .codegen import PlotError
    from .data import RowSettings
    try:
        build_plot(graph, ds, sel, {}, RowSettings(), StyleSettings(), LabelSettings())
        return True
    except PlotError:
        return False
    except Exception:  # noqa: BLE001 - let the normal Plot button report anything else
        return True
