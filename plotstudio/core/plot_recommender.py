"""plot_recommender: which plots to draw first, each with a one-line reason.

Algorithm (5 stages):
  1. PROFILE    the kind of every column: number, category, date, id, text, constant or empty
                (profiler.py). Numbers with few values count as categories; ids, free text and
                constant columns are reported, not plotted. The target is never skipped.
  2. SCORE-1D   how much a single column is worth a look: skew, outliers, missing values,
                one dominant value. The target always comes first.
  3. SCORE-2D   how strongly two columns are linked, on one 0..1 scale (assoc.py):
                  number-number   max(|Pearson r|, |Spearman ρ|)
                  group-number    correlation ratio η (bias-corrected, raw or on ranks)
                  group-group     Cramér's V (bias-corrected)
                  date-number     |Spearman ρ| of the value against time
                Near-copies (link ≥ 0.95) become notes and only one column of each set is
                plotted; a near-copy of the target is a leakage warning instead of a plot.
  4. RANK       the target first, then its strongest links (at most 4), then overview plots,
                other pairs and single columns by strength, with penalties for missing values
                and very many groups. No column is used more than twice (the target up to 5x).
  5. RECOMMEND  each pick gets a plot that fits the column kinds and the size of the data,
                a reason in plain words with the numbers behind it, and the exact settings
                for the matching CSV Plot Studio graph.

Only numpy and pandas are needed. UI-agnostic:

    profiles, suggestions, notes = recommend(df, target="survived")
    for s in suggestions: print(s)
    for n in notes: print(n)

Run it on a file:  python -m plotstudio.core data.csv [target]
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd

from . import assoc
from .profiler import CAT, CONSTANT, DATE, EMPTY_KIND, HIGH_CARD, ID, NUMBER, SKIP, TEXT, profile_frame

# ---------------------------------------------------------------- config
TOP_K = 10                  # suggestions returned
MAX_PER_COL = 2             # a column appears in at most this many suggestions ...
MAX_TARGET_PAIRS = 4        # ... except the target: its own plot + this many links
MIN_ASSOC = 0.10            # weaker links are not suggested
COPY_LINK = 0.95            # two columns linked this strongly hold the same information
OVERLAP_V = 0.80            # two groupings this linked mostly repeat each other: a note, not a plot
WEAK_LINK = 0.30            # links below this are called "weak" in the reason
IMBALANCED = 0.4            # a class with less than 0.4 x its fair share (20% of 2 classes) is rare
LEAK_NUMBER = 0.98          # a number linked this strongly to a number target (r and ρ) leaks it
LEAK_GROUPS = 0.95          # Cramér's V (or η) this high with the target: leaks it
LEAK_AUC = 0.99             # one number that splits a 2-class target this perfectly leaks it
SCATTER_LIMIT = 10_000      # more rows than this: hexbin instead of scatter
VIOLIN_MAX_GROUPS = 6       # more groups than this: box plot instead of violin
COUNT_MAX_GROUPS = 8        # grouped bars for up to this many colours, else a heatmap of counts
TOP_GROUPS = 20             # plots of columns with many groups show the 20 most common
MAX_PAIR_COLUMNS = 40       # wide files: pairs are checked among this many columns
PAIRPLOT_MAX_ROWS = 10_000

LEVELS = ("leak", "warn", "check", "info")
ICONS = {"leak": "🔴", "warn": "🟠", "check": "🟡", "info": "⚪"}
LEVEL_NAMES = {"leak": "leakage", "warn": "important", "check": "worth checking", "info": "for your information"}
ORDER_NAMES = re.compile(r"(^|[_\s])(epochs?|steps?|iters?|iterations?|rounds?|time|t|years?|months?|weeks?|"
                         r"days?|hours?|minutes?|seconds?|periods?|generations?|gen|batch(es)?)$", re.I)
PIXEL_NAMES = re.compile(r"^(pixel|pix|px|p)[_\s]?\d+$", re.I)
POSITIVE_WORDS = ("1", "yes", "true", "y", "positive", "pos", "survived", "transported", "churn", "default",
                  "satisfied", "malignant", "spam", "fraud")


# ---------------------------------------------------------------- results
@dataclass
class Suggestion:
    rank: int
    columns: tuple            # the columns the plot shows
    plot: str                 # e.g. "box plot (log y)"
    score: float              # ranking value (the target's own plot scores highest)
    reason: str               # one line in plain words
    stat: str = ""            # the numbers behind the reason, e.g. "V = 0.54 · n = 891"
    graph: str = ""           # CSV Plot Studio graph id (hist, box, count, regression, ...)
    sel: dict = field(default_factory=dict)    # graph role -> column(s)
    opts: dict = field(default_factory=dict)   # graph option -> value
    logx: bool = False
    logy: bool = False
    kind: str = ""            # target | target-pair | pair | single | time | overview
    label: str = ""           # a title of its own (time plots: "loss over epoch")

    @property
    def title(self) -> str:
        if self.label:
            return self.label
        if self.kind == "overview":
            return self.plot[:1].upper() + self.plot[1:]
        if self.kind == "time":
            return f"{self.columns[1]} over time" + (f", per {self.columns[2]}" if len(self.columns) > 2 else "")
        return " vs ".join(str(c) for c in self.columns)

    def __str__(self):
        text = f"{self.rank:>2}. {self.title:<34} → {self.plot:<24} | {self.reason}"
        return text + (f"  ({self.stat})" if self.stat else "")


@dataclass
class Note:
    level: str                # leak | warn | check | info  (most serious first)
    text: str
    action: str = ""
    columns: tuple = ()

    @property
    def icon(self) -> str:
        return ICONS[self.level]

    def __str__(self):
        return f"{self.icon} {self.text}" + (f" → {self.action}" if self.action else "")


@dataclass
class Link:
    a: str
    b: str
    kind: str                 # num-num | cat-num (a = groups) | cat-cat | date-num (a = date)
    s: float                  # strength 0..1
    n: int
    r: float = math.nan       # Pearson (signed)
    rho: float = math.nan     # Spearman (signed)
    eta: float = math.nan
    v: float = math.nan
    auc: float = math.nan
    pure_ab: float = math.nan  # share of rows where a's value fixes b's
    pure_ba: float = math.nan

    def other(self, c):
        return self.b if c == self.a else self.a


# ---------------------------------------------------------------- formatting
def fmt(v) -> str:
    """Numbers for people: 84.2, 5,076, 0.42."""
    if v is None or not np.isfinite(v):
        return "–"
    a = abs(v)
    if a >= 100:
        return f"{v:,.0f}"
    if a >= 10:
        return f"{v:.1f}".rstrip("0").rstrip(".")
    if a >= 1:
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if a == 0:
        return "0"
    return f"{v:.2g}"


def pct(share) -> str:
    if 0 < share < 0.01:
        return f"{share:.1%}"
    if 0.99 < share < 1:
        return ">99%"
    return f"{share:.0%}"


def lab(value, width=16) -> str:
    """A category label, short: 3.0 -> '3', long names cut with …"""
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        value = int(value)
    text = str(value)
    return text if len(text) <= width else text[: width - 1] + "…"


def signed(v) -> str:
    return f"{v:+.2f}".replace("-", "−")


def positive_index(labels) -> int:
    """Which of two classes is the 'positive' one (1, True, yes, ...): its share is reported."""
    words = [str(lab(v)).strip().lower() for v in labels]
    for word in POSITIVE_WORDS:
        if word in words:
            return words.index(word)
    return len(labels) - 1


# ---------------------------------------------------------------- the analysis
class _Analysis:
    def __init__(self, prof, tell):
        self.prof, self.tell = prof, tell
        self.p = prof.profiles
        self.df = prof.df
        self.n = len(prof.df)
        self.target = prof.target
        self.notes: list = []
        self.links: dict = {}         # (a, b) sorted -> Link
        self.hidden: dict = {}        # near-copy column -> the column plotted instead
        self.leaks: dict = {}         # column -> Link with the target
        self.cands: list = []         # (score, order, kind, columns, payload)

    # ------------------------------------------------------------ helpers --
    def note(self, level, text, action="", columns=()):
        self.notes.append(Note(level, text, action, tuple(columns)))

    def get(self, a, b):
        return self.links.get((a, b)) or self.links.get((b, a))

    def kind(self, c):
        return self.p[c].kind

    # ------------------------------------------------------------ stage 1 --
    def prepare(self):
        t = self.target
        if t is not None:
            tp = self.p[t]
            if not tp.usable:
                what = {EMPTY_KIND: "has no values", CONSTANT: f"has only one value ({lab(tp.top_value)})"}.get(
                    tp.kind, f"is set to '{tp.kind}'")
                self.note("leak", f"target '{t}' {what}: there is nothing to predict", "pick another target", (t,))
                self.target = t = None
            elif tp.kind == DATE:
                self.note("info", f"target '{t}' holds dates, so it is treated as time, not as something to predict",
                          "pick a number or category column as target", (t,))
                self.target = t = None
        self.usable = [c for c, p in self.p.items() if p.usable]
        self.nums = [c for c in self.usable if self.kind(c) == NUMBER]
        self.cats = [c for c in self.usable if self.kind(c) == CAT]
        self.dates = [c for c in self.usable if self.kind(c) == DATE]
        self.x = {c: self.df[c].to_numpy(dtype=float) for c in self.nums}
        self.xr = {c: assoc.ranks(self.x[c]) for c in self.nums}
        self.codes = {c: assoc.codes_of(self.df[c]) for c in self.cats}
        self.times = {c: assoc.date_values(self.df[c]) for c in self.dates}
        self.orders = []          # running numbers such as epoch or step: a time axis for line plots
        for c, p in self.p.items():
            if c == self.target or p.kind not in (ID, NUMBER) or not ORDER_NAMES.search(c):
                continue
            s = pd.to_numeric(self.df[c], errors="coerce")
            if s.notna().mean() >= 0.95 and s.nunique() >= 0.9 * s.notna().sum() >= 5 and \
                    (s.dropna().is_monotonic_increasing or s.dropna().is_monotonic_decreasing):
                self.orders.append(c)
                self.times[c] = s.to_numpy(dtype=float)
        pixels = [c for c in self.p if PIXEL_NAMES.match(c)]          # image data such as MNIST
        self.pixels = pixels if len(pixels) >= 16 else []
        if self.nums:
            self.pear, self.spear, self.counts = assoc.number_matrices(self.df[self.nums])

    # ------------------------------------------------------------ stage 3 --
    def pair(self, a, b):
        ka, kb = self.kind(a), self.kind(b)
        if ka == NUMBER and kb == NUMBER:
            r, rho, n = float(self.pear.at[a, b]), float(self.spear.at[a, b]), int(self.counts.at[a, b])
            if not (np.isfinite(r) or np.isfinite(rho)):
                return None
            s = max(abs(np.nan_to_num(r)), abs(np.nan_to_num(rho)))
            return Link(a, b, "num-num", s, n, r=r, rho=rho)
        if {ka, kb} == {CAT, NUMBER}:
            g, y = (a, b) if ka == CAT else (b, a)
            codes, labels = self.codes[g]
            e, n = assoc.eta(codes, len(labels), self.x[y], self.xr[y])
            link = Link(g, y, "cat-num", e, n, eta=e)
            if len(labels) == 2:
                link.auc = assoc.auc(codes, self.x[y])
            return link
        if ka == CAT and kb == CAT:
            (ca, la), (cb, lb) = self.codes[a], self.codes[b]
            table, n = assoc.crosstab(ca, len(la), cb, len(lb))
            v = assoc.cramers_v(table)
            return Link(a, b, "cat-cat", v, n, v=v, pure_ab=assoc.determines(table),
                        pure_ba=assoc.determines(table.T))
        if a in self.orders or b in self.orders:
            d, y = (a, b) if a in self.orders else (b, a)
            if y not in self.x or y in self.orders:
                return None
            rho, n = assoc.trend(self.times[d], self.x[y])
            return Link(d, y, "date-num", abs(rho), n, rho=rho) if np.isfinite(rho) else None
        if {ka, kb} == {DATE, NUMBER}:
            d, y = (a, b) if ka == DATE else (b, a)
            rho, n = assoc.trend(self.times[d], self.x[y])
            if not np.isfinite(rho):
                return None
            return Link(d, y, "date-num", abs(rho), n, rho=rho)
        return None

    def target_links(self):
        t = self.target
        if t is None:
            return
        tk = self.kind(t)
        for c in self.usable + [o for o in self.orders if o not in self.usable]:
            if c == t:
                continue
            link = self.pair(t, c)
            if link is None:
                continue
            self.links[(link.a, link.b)] = link
            leak, how = False, ""
            if link.kind == "num-num":
                low = min(abs(np.nan_to_num(link.r)), abs(np.nan_to_num(link.rho)))
                leak, how = low >= LEAK_NUMBER, f"r = {signed(link.r)}"
                if not leak and low >= COPY_LINK:
                    self.note("warn", f"'{c}' almost equals the target '{t}' ({how})",
                              "fine if you know it before the target; if it is measured after, it leaks the answer",
                              (c, t))
            elif link.kind == "cat-cat":
                pure = link.pure_ab if link.a == c else link.pure_ba
                leak = self.p[c].n_unique <= HIGH_CARD and (link.v >= LEAK_GROUPS or pure >= 0.995)
                how = f"Cramér's V = {link.v:.2f}"
            elif link.kind == "cat-num":
                groups = link.a
                if tk == CAT and np.isfinite(link.auc):
                    split = max(link.auc, 1 - link.auc)
                    leak, how = split >= LEAK_AUC, f"AUC = {split:.3f}"
                else:
                    leak = link.eta >= 0.97 and self.p[groups].n_unique <= HIGH_CARD
                    how = f"η = {link.eta:.2f}"
            if leak:
                self.leaks[c] = link
                self.note("leak", f"LEAKAGE: '{c}' almost perfectly gives away the target '{t}' ({how})",
                          "drop it before training a model; it is not shown in the plots", (c, t))

    def pair_links(self):
        t = self.target
        cols = [c for c in self.usable if c != t and c not in self.leaks and c not in self.orders]
        if len(cols) > MAX_PAIR_COLUMNS:
            if t is not None:
                strength = {c: (self.get(t, c).s if self.get(t, c) else 0.0) for c in cols}
                keep = set(sorted(cols, key=lambda c: -strength[c])[:MAX_PAIR_COLUMNS])
                why = f"the {MAX_PAIR_COLUMNS} most linked to '{t}'"
            else:
                keep = set(cols[:MAX_PAIR_COLUMNS])
                why = f"the first {MAX_PAIR_COLUMNS}"
            self.note("info", f"{len(cols)} usable columns: pairs were checked among {why}",
                      "set a target to choose which columns matter")
            cols = [c for c in cols if c in keep]
        pairs = [(a, b) for a, b in combinations(cols, 2)
                 if not (self.kind(a) == DATE and self.kind(b) == DATE)]
        pairs += [(o, c) for o in self.orders for c in cols if self.kind(c) == NUMBER]
        step = max(1, len(pairs) // 40)
        for i, (a, b) in enumerate(pairs):
            if i % step == 0:
                self.tell(0.25 + 0.6 * i / max(1, len(pairs)), f"Comparing columns ({i:,} of {len(pairs):,} pairs)")
            link = self.pair(a, b)
            if link is not None and link.s >= MIN_ASSOC:
                self.links[(link.a, link.b)] = link

    # ------------------------------------------------------------ near-copies --
    def copies(self):
        t = self.target
        parent = {}

        def find(c):
            while parent.get(c, c) != c:
                c = parent[c]
            return c

        def follows_time(c):
            links = [self.get(o, c) for o in self.orders + self.dates]
            return any(lk is not None and lk.s >= 0.8 for lk in links)

        strong = [lk for lk in self.links.values()
                  if lk.kind in ("num-num", "cat-cat") and lk.s >= COPY_LINK and t not in (lk.a, lk.b)
                  and lk.a not in self.leaks and lk.b not in self.leaks
                  and not (follows_time(lk.a) and follows_time(lk.b))]
        for lk in strong:
            ra, rb = find(lk.a), find(lk.b)
            if ra != rb:
                parent[ra] = rb
        groups = {}
        for c in {c for lk in strong for c in (lk.a, lk.b)}:
            groups.setdefault(find(c), []).append(c)
        order = {c: i for i, c in enumerate(self.p)}
        for members in groups.values():
            def rank_key(c):
                link = self.get(t, c) if t else None
                p = self.p[c]
                return (-round(link.s if link else 0.0, 2), round(p.missing_pct, 2), p.many_groups,
                        -p.n_unique if p.kind == CAT else 0, order[c])
            members.sort(key=rank_key)       # plot the one most linked to the target, then the readable one
            keep, rest = members[0], sorted(members[1:], key=order.get)
            for c in rest:
                self.hidden[c] = keep
            links = [self.get(keep, c) for c in rest]
            links = [lk for lk in links if lk is not None] or [lk for lk in strong if lk.a in members]
            low = min(lk.s for lk in links)
            names = ", ".join(f"'{c}'" for c in rest)
            action = f"plots use '{keep}'; for models keep one" + (" or combine them" if len(rest) > 1 else "")
            if self.kind(keep) == NUMBER:
                stat = f"r ≥ {low:.2f}" if len(rest) > 1 else f"r = {signed(links[0].r)}"
                verb = "move together with" if len(rest) > 1 else "moves together with"
                text = f"{names} {verb} '{keep}' ({stat})"
            else:
                stat = f"V ≥ {low:.2f}" if len(rest) > 1 else f"V = {links[0].v:.2f}"
                text = f"{names} {'hold' if len(rest) > 1 else 'holds'} the same groups as '{keep}' ({stat})"
                if len(rest) == 1:
                    lk = links[0]
                    keep_fixes = lk.pure_ab if lk.a == keep else lk.pure_ba
                    other_fixes = lk.pure_ba if lk.a == keep else lk.pure_ab
                    if keep_fixes >= 0.99 > other_fixes:
                        text = f"{names} can be worked out from '{keep}' ({stat})"
                    elif other_fixes >= 0.99 > keep_fixes:
                        text = f"'{keep}' can be worked out from {names}, which has {self.p[rest[0]].n_unique:,} groups ({stat})"
            self.note("warn", text, action, tuple(rest) + (keep,))

    # ------------------------------------------------------------ column notes --
    def column_notes(self):
        t = self.target
        skewed = []
        skipped = [(c, p) for c, p in self.p.items()
                   if not p.usable and c != self.prof.target and c not in self.orders]
        if skipped:
            words = {ID: "ID-like", TEXT: "text", CONSTANT: "one value", EMPTY_KIND: "empty", SKIP: "skipped"}
            listed = ", ".join(f"'{c}' ({words.get(p.kind, p.kind)})" for c, p in skipped[:8])
            more = f" and {len(skipped) - 8} more" if len(skipped) > 8 else ""
            self.note("info", f"not plotted: {listed}{more}",
                      "IDs, free text and one-value columns don't make useful plots", tuple(c for c, _ in skipped))
        for c, p in self.p.items():
            if p.unreadable:
                self.note("warn", f"'{c}': {p.unreadable:,} value(s) could not be read as "
                          f"{'dates' if (p.requested or p.kind) == DATE else 'numbers'}",
                          "they count as missing; check the type you set", (c,))
            if p.infinite:
                self.note("warn", f"'{c}': {p.infinite:,} infinite value(s)", "they are treated as missing", (c,))
            if p.kind in (EMPTY_KIND, CONSTANT, SKIP) or c in self.leaks:
                continue
            if c == t:
                if p.missing_pct > 0:
                    self.note("warn", f"target '{c}' is missing in {pct(p.missing_pct)} of rows",
                              "drop those rows before training", (c,))
                continue
            if p.missing_pct >= 0.30:
                self.note("warn", f"'{c}': {pct(p.missing_pct)} missing", "drop it, or keep a 'was missing' flag", (c,))
            elif p.missing_pct >= 0.05:
                self.note("check", f"'{c}': {pct(p.missing_pct)} missing", "fill the gaps (impute) or add a flag", (c,))
            if not p.usable:
                continue
            if p.skewed and c not in self.hidden and c not in self.timed and c not in self.pixels:
                skewed.append(c)
            if p.many_groups:
                self.note("check", f"'{c}': {p.n_unique:,} groups", f"plots show the top {TOP_GROUPS}; "
                          "for models group the rare values", (c,))
        if len(skewed) > 5:
            listed = ", ".join(f"'{c}' ({self.p[c].skew:.1f})" for c in skewed[:4])
            self.note("check", f"{len(skewed)} columns are skewed: {listed} and {len(skewed) - 4} more",
                      "use log scales for right-skewed ones (np.log1p for models)", tuple(skewed))
        else:
            for c in skewed:
                p = self.p[c]
                side = "right" if p.skew > 0 else "left"
                act = "use a log scale (np.log1p for models)" if p.skew > 0 and p.minimum is not None and \
                    p.minimum >= 0 else "look at it on a robust scale (quantiles)"
                self.note("check", f"'{c}': {side}-skewed ({p.skew:.1f})", act, (c,))
        if t is not None and self.kind(t) == CAT:
            counts = self.df[t].value_counts(normalize=True)
            if len(counts) >= 2 and counts.iloc[-1] < IMBALANCED / len(counts):
                rare = counts.index[-1]
                self.note("warn", f"target '{t}' is imbalanced: '{lab(rare)}' is only {pct(counts.iloc[-1])} of rows",
                          "split with stratify=y and judge models by F1 / recall, not accuracy", (t,))
        if self.prof.sampled:
            self.note("info", f"analysed a random sample of {self.n:,} of {self.prof.total_rows:,} rows",
                      "plenty for ranking; the plots use all rows")

    # ------------------------------------------------------------ stages 2 + 4 --
    def add(self, score, kind, columns, payload=None):
        self.cands.append((score, len(self.cands), kind, tuple(columns), payload))

    def penalty(self, *cols):
        f = 1 - 0.5 * max(self.p[c].missing_pct for c in cols)
        if any(self.p[c].many_groups for c in cols):
            f *= 0.6
        return f

    def interest(self, p) -> float:
        if p.kind == CAT:
            return 0.3 if p.top_share > 0.9 else 0.0
        score = 0.0
        if abs(p.skew) > 1:
            score += min(abs(p.skew) / 3, 1) * 0.4
        score += min(p.outlier_pct / 0.10, 1) * 0.3 if p.outlier_pct > 0.02 else 0.0
        return score

    def plotted(self, c) -> bool:
        return c in self.p and self.p[c].usable and c not in self.hidden and c not in self.leaks

    def candidates(self):
        t = self.target
        nums = [c for c in self.nums if self.plotted(c) and c != t]
        # the target itself
        if t is not None:
            self.add(3.0, "target", (t,))
        # links with the target
        if t is not None:
            for c in self.usable + self.orders:
                if c == t or not (self.plotted(c) or c in self.orders):
                    continue
                link = self.get(t, c)
                if link is None or link.kind == "date-num" and self.kind(t) != NUMBER:
                    continue
                s = link.s * self.penalty(t, c)
                if link.kind == "date-num":      # a number target with dates: always show it over time
                    if not any(k == "time" for _, _, k, _, _ in self.cands):
                        self.add(1.6 + 0.4 * s, "time", (link.a, link.b), link)
                    continue
                if s < MIN_ASSOC:
                    continue
                self.add(1.0 + s if s >= 0.2 else 2 * s, "target-pair", (t, c), link)
        # overview plots
        if t is not None and len(nums) >= 4 and (self.kind(t) == NUMBER or self.p[t].binary):
            self.add(1.3, "overview", ("target_corr",), nums)
        missing = sorted(((self.p[c].missing_pct, c) for c in self.p if self.p[c].kind != SKIP), reverse=True)
        if missing and missing[0][0] >= 0.05:
            self.add(0.6 + 0.3 * missing[0][0], "overview", ("missing",), missing)
        all_nums = [c for c in self.nums if c not in self.leaks]     # the target too: it belongs in the map
        if len(all_nums) >= 4 and not self.pixels:
            self.add(0.75, "overview", ("corr",), all_nums)
        if (t is not None and self.kind(t) == CAT and 2 <= self.p[t].n_unique <= 6 and 3 <= len(nums)
                and self.n <= PAIRPLOT_MAX_ROWS):
            ranked = sorted(nums, key=lambda c: -(self.get(t, c).s if self.get(t, c) else 0))
            self.add(0.85, "overview", ("pairplot",), ranked[:4])
        # time: the target (or the steadiest numbers) over time / over epochs
        axes = self.dates + self.orders
        if axes and (t is None or self.kind(t) != NUMBER):
            for d in axes[:2]:
                for i, ys in enumerate(self.series(d, nums)[:2]):
                    links = [lk for lk in (self.get(d, c) for c in ys) if lk is not None]
                    best = max(links, key=lambda lk: lk.s, default=None)
                    self.add(max(0.65 - 0.1 * i, best.s if best else 0), "time", (d, *ys), best)
        if self.pixels:
            self.add(2.5, "overview", ("images",), self.pixels)
        # single columns (not series that just follow time like a loss curve, not single pixels)
        for c in self.usable:
            if c == t or not self.plotted(c) or c in self.timed or c in self.pixels:
                continue
            score = self.interest(self.p[c])
            if score >= 0.25:
                self.add(0.8 * score, "single", (c,))
        # other pairs
        weights = {"num-num": 0.9, "cat-num": 0.85, "date-num": 0.9, "cat-cat": 0.6}
        for (a, b), link in self.links.items():
            if t in (a, b) or not (self.plotted(a) and self.plotted(b)) or link.s < MIN_ASSOC:
                continue
            if link.kind in ("num-num", "cat-cat") and link.s >= COPY_LINK:
                continue
            if a in self.pixels and b in self.pixels:
                continue
            if link.kind == "cat-cat" and link.s >= OVERLAP_V:
                self.note("check", f"'{a}' and '{b}' overlap a lot (V = {link.v:.2f})",
                          "one may be derived from the other; models may not need both", (a, b))
                continue
            if link.kind == "date-num" and any(k == "time" and set(cols) == {a, b} for _, _, k, cols, _ in self.cands):
                continue
            score = link.s * weights[link.kind] * self.penalty(a, b)
            self.add(score, "time" if link.kind == "date-num" else "pair", (a, b), link)

    def series(self, axis, nums):
        """Which numbers to draw over time: columns sharing a name ending ('train_loss', 'val_loss')
        go in one plot; otherwise the clearest trend, or the first measure of the file."""
        groups = {}
        for c in nums:
            token = re.split(r"[_\s.]+", c.strip().lower())[-1]
            groups.setdefault(token, []).append(c)
        shared = [g for g in groups.values() if 2 <= len(g) <= 4]
        strength = {c: (self.get(axis, c).s if self.get(axis, c) else 0.0) for c in nums}
        shared.sort(key=lambda g: -max(strength[c] for c in g))
        if shared and axis in self.orders:
            return shared
        best = max(nums, key=lambda c: strength[c], default=None)
        if best is None:
            return []
        if strength[best] < WEAK_LINK:
            best = nums[0]                        # no clear trend: the first measure in the file
        return [[best]]

    def pick(self, top_k, max_per_col, max_target_pairs):
        t = self.target
        used, out, seen = {}, [], set()
        for score, _, kind, cols, payload in sorted(self.cands, key=lambda c: (-c[0], c[1])):
            counted = () if kind == "overview" else cols
            if kind == "time":
                counted = tuple(c for c in cols if c != t)    # the target over time is extra
            limits = {c: (1 + max_target_pairs if c == t else max_per_col) for c in counted}
            if any(used.get(c, 0) >= limits[c] for c in counted):
                continue
            ident = (kind, cols) if kind == "overview" else frozenset(cols)
            if ident in seen:
                continue
            spec = self.describe(kind, cols, payload)
            if spec is None:
                continue
            seen.add(ident)
            for c in counted:
                used[c] = used.get(c, 0) + 1
            out.append(Suggestion(rank=len(out) + 1, score=round(float(score), 3), kind=kind, **spec))
            if len(out) >= top_k:
                break
        return out

    def notes_sorted(self):
        order = {lv: i for i, lv in enumerate(LEVELS)}
        return sorted(self.notes, key=lambda n: order[n.level])

    # ------------------------------------------------------------ stage 5 --
    def describe(self, kind, cols, payload):
        if kind == "target":
            return self.d_target(cols[0])
        if kind == "single":
            return self.d_single(cols[0])
        if kind == "overview":
            return self.d_overview(cols[0], payload)
        if kind == "time":
            return self.d_time(cols[0], cols[1:], payload)
        return self.d_pair(payload, kind == "target-pair")

    # --- pieces of text
    def center(self, c):
        p = self.p[c]
        return ("median", np.nanmedian) if p.skewed else ("average", np.nanmean)

    def group_values(self, g, y):
        """[(label, centre, rows)] for groups with enough rows, in a readable order."""
        codes, labels = self.codes[g]
        vals = self.x[y]
        word, fn = self.center(y)
        m = (codes >= 0) & np.isfinite(vals)
        min_rows = max(5, int(0.01 * m.sum()))
        out = []
        for k, label in enumerate(labels):
            sel = m & (codes == k)
            rows = int(sel.sum())
            if rows >= min_rows:
                out.append((label, float(fn(vals[sel])), rows))
        if not self.p[g].ordered:
            out.sort(key=lambda item: -item[1])
        return word, out

    def spread_text(self, items, column, as_pct=False):
        """'60.3 for pclass = 1, 14.2 for 2, 8.05 for 3'; with many groups the highest and lowest."""
        show = pct if as_pct else fmt
        prep = "of" if as_pct else "for"
        if len(items) > 4:
            hi = max(items, key=lambda i: i[1])
            lo = min(items, key=lambda i: i[1])
            return (f"{show(hi[1])} {prep} {column} = {lab(hi[0])} (highest) to "
                    f"{show(lo[1])} {prep} {lab(lo[0])} (lowest)")
        parts = [f"{show(v)} {prep} " + (f"{column} = {lab(k)}" if i == 0 else lab(k))
                 for i, (k, v, _) in enumerate(items)]
        return ", ".join(parts)

    def direction(self, a, b, link):
        r, rho = np.nan_to_num(link.r), np.nan_to_num(link.rho)
        sign = rho if abs(rho) >= abs(r) else r
        text = f"higher {a} → {'higher' if sign > 0 else 'lower'} {b}"
        if link.s < WEAK_LINK:
            text = f"weak link: higher {a} → slightly {'higher' if sign > 0 else 'lower'} {b}"
        if abs(rho) > abs(r) + 0.1:
            text += f"; a steady but curved link (ρ = {signed(rho)} vs r = {signed(r)})"
        return text

    def rates(self, g, t):
        """Share of the target's positive class in each group of g."""
        (cg, lg), (ct, lt) = self.codes[g], self.codes[t]
        table, _ = assoc.crosstab(cg, len(lg), ct, len(lt))
        pos = positive_index(lt)
        rows = table.sum(axis=1)
        min_rows = max(5, int(0.01 * rows.sum()))
        items = [(lg[i], table[i, pos] / rows[i], int(rows[i])) for i in range(len(lg)) if rows[i] >= min_rows]
        if not self.p[g].ordered:
            items.sort(key=lambda i: -i[1])
        return lt[pos], items

    def majority(self, g, t):
        """'3 for Survived = 0 (68%), 1 for 1 (40%)': the most common class in the biggest groups."""
        (cg, lg), (ct, lt) = self.codes[g], self.codes[t]
        table, _ = assoc.crosstab(cg, len(lg), ct, len(lt))
        rows = table.sum(axis=1)
        order = [i for i in np.argsort(-rows)[:3] if rows[i] > 0]
        if self.p[g].ordered:
            order.sort()
        parts = []
        for k, i in enumerate(order):
            j = int(np.argmax(table[i]))
            where = f"{g} = {lab(lg[i])}" if k == 0 else lab(lg[i])
            parts.append(f"{lab(lt[j])} for {where} ({pct(table[i, j] / rows[i])})")
        return ", ".join(parts)

    def lift(self, a, b):
        """The most over-represented pair of values: '<b>=v is 72% of <a>=w rows vs 15% overall'."""
        (ca, la), (cb, lb) = self.codes[a], self.codes[b]
        table, n = assoc.crosstab(ca, len(la), cb, len(lb))
        rows, overall = table.sum(axis=1), table.sum(axis=0) / max(1, n)
        best, text = 0.0, ""
        for i in range(len(la)):
            if rows[i] < max(10, 0.02 * n):
                continue
            share = table[i] / rows[i]
            j = int(np.argmax(share - overall))
            gain = share[j] - overall[j]
            if gain > best:
                best = gain
                text = f"{b} = {lab(lb[j])}: {pct(share[j])} when {a} = {lab(la[i])}, {pct(overall[j])} overall"
        return text

    # --- plot settings
    def logs_for(self, c):
        p = self.p[c]
        return p.skewed and p.skew > 0 and p.positive

    def groups_plot(self, g, y):
        """Box or violin of number y split by groups g."""
        many = self.p[g].n_unique > VIOLIN_MAX_GROUPS
        log = self.logs_for(y)
        graph = "box" if many or self.p[y].skewed else "violin"
        opts = {"top_n": TOP_GROUPS} if self.p[g].n_unique > TOP_GROUPS else {}
        name = ("box plot" if graph == "box" else "violin plot") + (" (log y)" if log else "")
        if self.p[g].n_unique > TOP_GROUPS:
            name += f", top {TOP_GROUPS}"
        return dict(plot=name, graph=graph, sel={"y": [y], "x": g}, opts=opts, logy=log)

    def counts_plot(self, a, b):
        """Rows per pair of groups: grouped bars (few groups) or a heatmap of counts."""
        na, nb = self.p[a].n_unique, self.p[b].n_unique
        if nb <= COUNT_MAX_GROUPS and na <= TOP_GROUPS:
            opts = {"labels": "count" if na * nb > 12 else "both"}
            if self.p[a].ordered:
                opts["order"] = "name"            # 1, 2, 3 rather than most common first
            return dict(plot="grouped bar chart", graph="count", sel={"col": a, "hue": b}, opts=opts)
        return dict(plot="heatmap of counts", graph="pivot", sel={"rows": a, "cols": b},
                    opts={"agg": "count", "top_n": TOP_GROUPS})

    def numbers_plot(self, a, b, colour=None):
        """Two numbers: scatter coloured by the target, hexbin for big data, else a fitted line."""
        if colour is not None:
            return dict(plot=f"scatter coloured by {colour}", graph="scatter",
                        sel={"x": a, "y": b, "color": colour}, opts={"alpha": 0.6})
        if self.n > SCATTER_LIMIT:
            return dict(plot="hexbin (dense data)", graph="hexbin", sel={"x": a, "y": b}, opts={"log": True})
        return dict(plot="scatter + trend line", graph="regression", sel={"x": a, "y": b},
                    opts={"ci": self.n <= 2000})

    # --- the five kinds of suggestion
    def d_target(self, t):
        p = self.p[t]
        if p.kind == CAT:
            counts = self.df[t].value_counts()
            share = counts / counts.sum()
            if len(counts) == 2:
                _, labels = self.codes[t]
                pos = labels[positive_index(labels)]
                other = [v for v in counts.index if v != pos][0]
                reason = (f"target {t} = {lab(pos)}: {pct(share[pos])} ({counts[pos]:,} rows) · "
                          f"{lab(other)}: {pct(share[other])} ({counts[other]:,})")
            elif len(counts) <= 6:
                items = sorted(share.items()) if p.ordered else list(share.items())
                reason = f"target {t} = " + " · ".join(f"{lab(k)}: {pct(v)}" for k, v in items)
            else:
                reason = (f"target: {len(counts)} classes, from {share.min():.1%} "
                          f"({lab(share.idxmin())}) to {share.max():.1%} ({lab(share.idxmax())})")
            reason += " → imbalanced" if share.min() < IMBALANCED / len(share) else " → balanced enough"
            opts = {"labels": "both"} if len(counts) <= TOP_GROUPS else {"labels": "count", "top_n": TOP_GROUPS}
            if p.ordered:
                opts["order"] = "name"
            return dict(columns=(t,), plot="count plot", reason=reason, stat=f"n = {int(counts.sum()):,}",
                        graph="count", sel={"col": t}, opts=opts)
        log = self.logs_for(t)
        reason = f"target: median {fmt(p.median)}, from {fmt(p.minimum)} to {fmt(p.maximum)}"
        if p.skewed:
            reason += f"; {'right' if p.skew > 0 else 'left'}-skewed ({p.skew:.1f})"
            if p.skew > 0 and p.minimum is not None and p.minimum >= 0:
                reason += " → consider predicting log(1 + target)"
        return dict(columns=(t,), plot="histogram (log x)" if log else "histogram + KDE", reason=reason,
                    stat=f"n = {int((~self.df[t].isna()).sum()):,}", graph="hist", sel={"cols": [t]},
                    opts={"kde": not log}, logx=log)

    def d_single(self, c):
        p = self.p[c]
        if p.kind == NUMBER:
            log = self.logs_for(c)
            parts = []
            if p.skewed:
                side = "right" if p.skew > 0 else "left"
                parts.append(f"{side}-skewed ({p.skew:.1f}): " +
                             ("most values are small, a few are very large" if p.skew > 0 else
                              "most values are large, a few are very small"))
            if p.outlier_pct > 0.02:
                parts.append(f"{pct(p.outlier_pct)} outliers")
            reason = "; ".join(parts) or "distribution"
            if log:
                reason += " → log scale"
            return dict(columns=(c,), plot="histogram (log x)" if log else "histogram + KDE", reason=reason,
                        stat=f"median {fmt(p.median)} · n = {int(round(p.rows * (1 - p.missing_pct))):,}",
                        graph="hist", sel={"cols": [c]}, opts={"kde": not log}, logx=log)
        if p.kind == CAT:
            reason = f"'{lab(p.top_value)}' is {pct(p.top_share)} of rows"
            opts = {"top_n": TOP_GROUPS} if p.n_unique > TOP_GROUPS else {}
            if p.ordered:
                opts["order"] = "name"
            return dict(columns=(c,), plot="bar chart" + (f" (top {TOP_GROUPS})" if p.n_unique > TOP_GROUPS else ""),
                        reason=reason,
                        stat=f"{p.n_unique:,} groups", graph="count", sel={"col": c}, opts=opts)
        return None

    def d_overview(self, which, payload):
        t = self.target
        if which == "target_corr":
            feats = list(payload)
            skewed = sum(self.p[c].skewed for c in feats + [t]) > len(feats) / 3
            best = max(feats, key=lambda c: self.get(t, c).s if self.get(t, c) else 0)
            reason = f"all {len(feats)} number columns ranked by their link with {t}; strongest: {best}"
            return dict(columns=(t, *feats), plot="correlation with target", reason=reason,
                        stat="Spearman" if skewed else "Pearson", graph="target_corr",
                        sel={"target": t, "features": feats},
                        opts={"method": "spearman" if skewed else "pearson"})
        if which == "missing":
            gaps = [(m, c) for m, c in payload if m > 0]
            listed = " · ".join(f"{c} {pct(m)}" for m, c in gaps[:3])
            reason = f"{len(gaps)} column{'s' if len(gaps) != 1 else ''} with gaps: {listed}"
            return dict(columns=tuple(c for _, c in gaps), plot="missing values map", reason=reason,
                        stat=f"{len(gaps)} of {len(self.p)} columns", graph="missing",
                        sel={"cols": [c for _, c in gaps]}, opts={})
        if which == "corr":
            cols = list(payload)[:30]
            pairs = [lk for lk in self.links.values() if lk.kind == "num-num" and lk.a in cols and lk.b in cols]
            reason = f"all {len(cols)} number columns at once"
            if pairs:
                top = max(pairs, key=lambda lk: lk.s)
                reason += f"; strongest pair: {top.a} & {top.b} (r = {signed(top.r)})"
            return dict(columns=tuple(cols), plot="correlation heatmap", reason=reason,
                        stat=f"{len(cols)} columns", graph="corr", sel={"cols": cols}, opts={})
        if which == "images":
            cols = list(payload)
            side = int(round(math.sqrt(len(cols))))
            shape = f"a {side}×{side} picture" if side * side == len(cols) else "a picture"
            reason = f"{len(cols)} pixel columns: every row is {shape}; look at a few before plotting pixels"
            sel = {"pixels": cols}
            if t is not None:
                sel["label"] = t
            return dict(columns=tuple(cols), plot="image grid", reason=reason, stat=f"{len(cols)} pixels",
                        graph="images", sel=sel, opts={"count": 25})
        if which == "pairplot":
            cols = list(payload)
            reason = f"every pair of {', '.join(cols)}, coloured by {t}: see which classes separate"
            return dict(columns=(*cols, t), plot="pair plot", reason=reason, stat=f"{len(cols)} columns",
                        graph="pairplot", sel={"cols": cols, "hue": t}, opts={"corner": True})
        return None

    def d_time(self, d, ys, link):
        ys = list(ys)
        y = ys[0]
        over = "over time" if self.kind(d) == DATE else f"over {d}"
        names = ", ".join(ys)
        rho = link.rho if link is not None else math.nan
        if len(ys) > 1:
            moves = []
            for c in ys:
                lk = self.get(d, c)
                if lk is not None and abs(lk.rho) >= WEAK_LINK:
                    moves.append(f"{c} {'rises' if lk.rho > 0 else 'falls'}")
            reason = (", ".join(moves) if moves else "no steady trend") + f"; compare the {len(ys)} lines"
        elif np.isfinite(rho) and abs(rho) >= WEAK_LINK:
            reason = f"{y} {'rises' if rho > 0 else 'falls'} {over}"
        else:
            reason = f"{y} {over}: no steady trend, look for seasons and spikes"
        stat = (f"ρ = {signed(rho)} · " if np.isfinite(rho) else "") + f"n = {int(self.df[y].notna().sum()):,}"
        label = f"{names} {over}"
        axis = self.df[d].dropna()
        repeats = 1 - axis.nunique() / max(1, len(axis))
        if repeats < 0.05:
            opts = {}
            if len(axis) > 1000:
                opts["rolling"] = int(min(200, max(5, len(axis) // 200)))
                reason += f" (smoothed: rolling mean of {opts['rolling']})"
            return dict(columns=(d, *ys), label=label, plot=f"line {over}", reason=reason, stat=stat,
                        graph="line", sel={"x": d, "y": ys}, opts=opts)
        if len(ys) == 1:
            for g in self.cats:
                if g == y or self.p[g].n_unique > COUNT_MAX_GROUPS:
                    continue
                per = self.df.groupby([d, g], observed=True).size()
                if len(per) and per.mean() <= 1.2:
                    return dict(columns=(d, y, g), label=f"{label}, per {g}", plot=f"line {over}, one per {g}",
                                reason=reason, stat=stat, graph="line", sel={"x": d, "y": [y], "hue": g}, opts={})
        return dict(columns=(d, y), label=label, plot=f"average {over}", reason=reason + " (average per date)",
                    stat=stat, graph="errorbar", sel={"x": d, "y": y},
                    opts={"style": "band", "spread": "sem", "marker": ""})

    def d_pair(self, link, with_target):
        t = self.target
        if link.kind == "num-num":
            if with_target:
                f = link.other(t)
                spec = self.numbers_plot(f, t)
                a, b = f, t
            else:
                a, b = link.a, link.b
                colour = t if (t is not None and self.kind(t) == CAT and self.p[t].n_unique <= COUNT_MAX_GROUPS) else None
                spec = self.numbers_plot(a, b, colour)
            if abs(np.nan_to_num(link.rho)) > abs(np.nan_to_num(link.r)) + 0.1 and spec["graph"] != "hexbin":
                spec["logx"], spec["logy"] = self.logs_for(a), self.logs_for(b)
                if (spec["logx"] or spec["logy"]) and spec["graph"] == "regression":
                    # a straight line fitted to the raw values bends on log axes and drops out of the plot where
                    # it goes below 0: on log axes the points alone show the curved link
                    spec.update(plot="scatter", graph="scatter", sel={"x": a, "y": b}, opts={"alpha": 0.6})
                if spec["logx"] or spec["logy"]:
                    spec["plot"] += " (log)"
            reason = self.direction(a, b, link)
            stat = f"r = {signed(link.r)} · ρ = {signed(link.rho)} · n = {link.n:,}"
            return dict(columns=(a, b), reason=reason, stat=stat, **spec)
        if link.kind == "cat-num":
            g, y = link.a, link.b
            spec = self.groups_plot(g, y)
            if with_target and g == t and self.p[t].binary and np.isfinite(link.auc):
                stat = f"η = {link.eta:.2f} · AUC = {max(link.auc, 1 - link.auc):.2f} · n = {link.n:,}"
            else:
                stat = f"η = {link.eta:.2f} · n = {link.n:,}"
            word, items = self.group_values(g, y)
            if items:
                reason = f"{word} {y}: {self.spread_text(items, g)}"
                if link.eta < WEAK_LINK:
                    reason = "weak link: " + reason
            else:
                reason = f"{y} differs between the groups of {g}"
            return dict(columns=(g, y) if g != t else (y, g), reason=reason, stat=stat, **spec)
        if link.kind == "cat-cat":
            if with_target:
                f = link.other(t)
                spec = self.counts_plot(f, t)
                if self.p[t].n_unique == 2:
                    pos, items = self.rates(f, t)
                    reason = f"{t} = {lab(pos)} in {self.spread_text(items, f, as_pct=True)}" if items else ""
                else:
                    reason = f"most common {t}: {self.majority(f, t)}"
                cols = (f, t)
            else:
                a, b = link.a, link.b
                if self.p[a].n_unique < self.p[b].n_unique:
                    a, b = b, a                    # more groups on the axis, fewer as colours
                spec = self.counts_plot(a, b)
                reason = self.lift(a, b) or f"{a} and {b} are linked"
                cols = (a, b)
            reason = reason or "linked groups"
            if link.v < WEAK_LINK:
                reason = "weak link: " + reason
            return dict(columns=cols, reason=reason, stat=f"V = {link.v:.2f} · n = {link.n:,}", **spec)
        return None

    # ------------------------------------------------------------ run --
    def run(self):
        self.tell(0.05, "Profiling the columns")
        self.prepare()
        self.tell(0.15, "Linking columns with the target")
        self.target_links()
        self.pair_links()
        self.tell(0.88, "Finding near-copies")
        self.timed = {lk.b for lk in self.links.values()      # series that just follow time / epochs
                      if lk.kind == "date-num" and lk.s >= 0.8 and lk.a in self.orders + self.dates}
        self.copies()
        self.column_notes()
        self.candidates()


def recommend(df: pd.DataFrame, target=None, top_k: int = TOP_K, max_per_col: int = MAX_PER_COL,
              overrides: dict | None = None, *, infos=None, max_target_pairs: int = MAX_TARGET_PAIRS,
              progress=None):
    """Rank the plots to draw first.

    Returns (profiles, suggestions, notes):
      profiles     {column: ColumnProfile}  kind and quality numbers of every column
      suggestions  [Suggestion]             best first; str(s) is a one-line summary
      notes        [Note]                   leakage first, then important, worth checking, info

    target     column to predict (shown first; its strongest links follow)
    overrides  {'column': 'category'} forces a kind: number, category, date, id, text or skip
    infos      the app's file scan ({name: ColumnInfo}) so kinds match the rest of the app
    progress   optional callback progress(fraction 0..1, text) for a progress bar
    """
    def tell(fraction, text=""):
        if progress is not None:
            progress(min(1.0, max(0.0, fraction)), text)

    prof = profile_frame(df, target=target, overrides=overrides, infos=infos)
    analysis = _Analysis(prof, tell)
    analysis.run()
    tell(0.95, "Choosing plots")
    suggestions = analysis.pick(top_k, max_per_col, max_target_pairs)
    notes = analysis.notes_sorted()
    labels = list(df.columns)
    # the profiler works on cleaned names; where the only change was the spaces around a name ("Age " -> "Age"),
    # hand back the DataFrame's own name, so the app (which keeps the file's names) can draw the suggestion.
    # Numbers as names and repeated headers keep their unique text names ("0", "a (2)").
    spaces = {new: orig for new, orig in prof.renamed.items()
              if isinstance(orig, str) and orig.strip() == new and labels.count(orig) == 1}
    if spaces:
        back = spaces.get
        profiles = {back(n, n): p for n, p in prof.profiles.items()}
        for s in suggestions:
            s.columns = tuple(back(c, c) for c in s.columns)
            s.sel = {k: [back(c, c) for c in v] if isinstance(v, list) else back(v, v) if isinstance(v, str) else v
                     for k, v in s.sel.items()}
        for n in notes:
            n.columns = tuple(back(c, c) for c in n.columns)
    else:
        profiles = prof.profiles
    tell(1.0, "Done")
    return profiles, suggestions, notes


# ---------------------------------------------------------------- command line
def main(argv=None):
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m plotstudio.core data.csv [target_column]")
        return 0
    try:
        sys.stdout.reconfigure(errors="replace")   # arrows and emoji on old Windows consoles
    except (AttributeError, ValueError):
        pass
    from ..data import load_csv
    ds = load_csv(args[0])
    target = args[1] if len(args) > 1 else None
    try:
        profiles, suggestions, notes = recommend(ds.df, target=target, infos=ds.columns)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    print("\nCOLUMN TYPES")
    for p in profiles.values():
        print(f"  {p.name:<22} {p.label:<22} {', '.join(p.notes)}")
    print("\nPLOT FIRST")
    for s in suggestions:
        print(" ", s)
    if notes:
        print("\nNOTES")
        for n in notes:
            print("  ", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
