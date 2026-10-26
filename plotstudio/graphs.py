"""All graph types the app can draw.

Each graph type declares
  * roles   – the column slots the user fills in (X axis, Y axis, colour by, ...)
  * options – extra settings (bins, kind, colormap, ...)
  * build   – a function that WRITES matplotlib/seaborn code for the choices.

The app runs exactly the code a build function writes and shows that code to
the user, so what you see in the "Python code" tab is what drew the plot.
"""
from __future__ import annotations

import math
import re
import textwrap
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .codegen import OMIT, PlotError, Raw, call, clean_comment, cols_expr, lit
from .data import DATETIME, EMPTY, NUMERIC, Dataset, is_boolish

MAX_PANELS = 36
MAX_GROUPS = 30

CMAPS_SEQ = ["viridis", "plasma", "magma", "cividis", "mako", "rocket", "crest", "flare",
             "Blues", "Greens", "Oranges", "Purples", "YlGnBu", "YlOrRd", "gray_r"]
CMAPS_DIV = ["coolwarm", "RdBu_r", "vlag", "icefire", "Spectral", "RdGy", "PiYG", "BrBG"]
CMAPS_ALL = CMAPS_SEQ + CMAPS_DIV


# --------------------------------------------------------------------------- #
# Declarations
# --------------------------------------------------------------------------- #

@dataclass
class Role:
    key: str
    label: str
    accepts: str              # num | cat | num_cat | num_time | any | binary | all
    required: bool = True
    multi: bool = False
    min_count: int = 1
    hint: str = ""
    prefer: str = ""          # how to auto-suggest a column (see suggest())
    auto: bool = False        # optional role that still gets a suggestion
    max_default: int = 4      # how many columns a multi role pre-selects


@dataclass
class Option:
    key: str
    label: str
    kind: str                 # choice | int | float | bool | text
    default: object
    choices: list = field(default_factory=list)   # [(value, label), ...]
    min: float = 0
    max: float = 100
    step: float = 1
    hint: str = ""
    show_if: Callable | None = None   # show_if(selection) -> bool


@dataclass
class GraphType:
    id: str
    name: str
    category: str
    blurb: str
    roles: list
    options: list
    build: Callable
    book: str = ""
    log_axes: bool = True         # log-scale switches make sense
    dropna: bool = True           # rows with gaps in used columns can be dropped
    heavy: Callable | None = None # heavy(options) -> row count that triggers auto-sampling
    min_rows: int = 1
    limits: bool = True           # the X/Y range sliders can zoom this plot (single 2D axes only)

    def option(self, key):
        return next(o for o in self.options if o.key == key)


def ch(*pairs):
    """Option choices: ch('a', ('b', 'Label B')) -> [('a', 'a'), ('b', 'Label B')]."""
    return [p if isinstance(p, tuple) else (p, p) for p in pairs]


# --------------------------------------------------------------------------- #
# Heatmap layout (worked out before drawing)
# --------------------------------------------------------------------------- #

TICK_PT = 11.0      # seaborn's tick label size in points at the "notebook" text size
ANNOT_PT = 12.0     # ... and the size of the numbers written in the cells


@dataclass
class HeatFit:
    w: float                  # figure size, inches
    h: float
    turn_x: bool = False      # write the column names upright
    every_x: int = 1          # label every n-th column (1 = all of them)
    every_y: int = 1
    annot_pt: float = 0.0     # the size the cell numbers fit at (0 = no numbers asked for)
    title_room: float = 0.0   # inches from the left edge of the cells to the right edge of the figure


def heat_fit(xnames, ynames, w, h, *, square, scale=1.0, annot_chars=0, annot_pt=None, axis_names=False,
             w_max=18.0, h_max=15.0) -> HeatFit:
    """Figure size and tick-label choices for a seaborn heatmap.

    seaborn picks the label direction and how many labels to show *before* the final layout
    shrinks the plot, so names could collide and the numbers in the cells could run into each
    other (most with many columns or the bigger text sizes). The rule used here: each cell is
    at least one line of text tall, column names turn upright when side by side they would
    touch, and the figure grows (up to w_max x h_max) before any label is left out.
    Sizes are estimates for the app's chart font (character width ~0.6 of the text size)."""
    nx, ny = max(1, len(xnames)), max(1, len(ynames))
    f = TICK_PT * scale / 72                                     # label text height, inches
    char = 0.6 * f
    fa = (annot_pt or ANNOT_PT * scale) / 72
    line = 1.35 * f                                              # one line of labels, with air
    annot_w = annot_chars * 0.62 * fa + 0.08 if annot_chars else 0.0
    annot_h = 1.35 * fa if annot_chars else 0.0
    ly = max(len(str(v)) for v in ynames) * char + 0.3 + (1.6 * f if axis_names else 0.0)
    flat_x = max(len(str(v)) for v in xnames) * char + 0.1
    top = 0.15 + 2.6 * f + (1.6 * f if axis_names else 0.0)     # title, x axis name, outer pads

    def bar(W):                                                  # colour bar with its numbers and name
        return min(0.75 + 0.14 * W, 2.3) + 3.5 * f

    def cells(W, H, lx):
        cw, chh = (W - ly - bar(W)) / nx, (H - lx - top) / ny
        return (min(cw, chh),) * 2 if square else (cw, chh)

    def size_for(lx):
        need_w, need_h = max(line, annot_w), max(line, annot_h)
        if square:
            need_w = need_h = max(need_w, need_h)
        W = w
        while W < w_max and (W - ly - bar(W)) / nx < need_w:
            W = round(W + 0.1, 1)
        H = max(h, round(need_h * ny + lx + top + 0.05, 1))
        return W, min(H, max(h, h_max))

    lx = f + 0.12
    W, H = size_for(lx)
    turn = flat_x > cells(W, H, lx)[0]
    if turn:
        lx = max(len(str(v)) for v in xnames) * char + 0.15
        W, H = size_for(lx)
    cw, chh = cells(W, H, lx)
    fit = HeatFit(W, H, turn_x=turn)
    spare = (W - ly - bar(W)) - cw * nx                         # square cells sit in the middle
    fit.title_room = round(W - 0.3 - ly - max(spare, 0.0) / 2, 2)
    if turn and cw < line:
        fit.every_x = math.ceil(line / max(cw, 1e-6))
    if chh < line:
        fit.every_y = math.ceil(line / max(chh, 1e-6))
    if annot_chars:
        size = min((cw - 0.08) / (annot_chars * 0.62), chh / 1.35) * 72
        fit.annot_pt = round(min(fa * 72, max(size, 0.0)), 1)
    return fit


TITLE_EM = 0.6      # width of an average bold title character, in font sizes (DejaVu ~0.6, Plex ~0.5)


def wrap_title(title, width: int):
    """Break a title into lines of at most `width` characters, so a long title (big Text size,
    narrow plot) stays inside the figure. An f-string title (Raw code) is wrapped in its
    template, counting each {...} as 6 characters."""
    if not title or width < 1:
        return title
    if isinstance(title, Raw):
        code = str(title)
        if len(code) < 3 or code[0] != "f" or code[1] not in "'\"" or code[-1] != code[1]:
            return title
        q, body = code[1], code[2:-1]
        words = re.findall(r"(?:\{[^}]*\}|\S)+", body)

        def size(word):
            return len(re.sub(r"\{[^}]*\}", "123456", word))

        if sum(size(w) for w in words) + len(words) - 1 <= width:
            return title
        lines, cur = [], []
        for word in words:
            if cur and sum(size(w) for w in cur) + len(cur) + size(word) > width:
                lines.append(cur)
                cur = []
            cur.append(word)
        lines.append(cur)
        text = "\\n".join(" ".join(w for i, w in enumerate(line) if not (w == "·" and i == len(line) - 1))
                           for line in lines)
        return Raw(f"f{q}{text}{q}")
    out = []
    for line in str(title).split("\n"):
        out += textwrap.wrap(line, width, break_long_words=False) or [""]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Code-writing context passed to every build function
# --------------------------------------------------------------------------- #

class Ctx:
    def __init__(self, graph: GraphType, ds: Dataset, df: pd.DataFrame, sel: dict, opts: dict, labels,
                 text_scale: float = 1.0):
        self.graph, self.ds, self.df, self.sel, self.o, self.labels = graph, ds, df, sel, opts, labels
        self.text_scale = text_scale  # the Text size setting (paper 0.8 ... poster 2.0)
        self.fig_w = None             # figure width in inches, when it is not in a figsize=(...) line
        self.title_room = None        # inches a left-aligned title can use (set by plots with narrow axes)
        self.lines: list = []
        self.limit_lines: list = []   # ax.set_xlim/ylim from the range sliders (run after the plot)
        self.imports: list = []
        self.notes: list = []
        self.mode = "single"          # single | multi | figure | single3d
        self.axes_var = None          # name of the axes array in multi mode
        self.title = ""               # automatic title (may be Raw f-string code)
        self.xlabel = ""              # automatic axis labels (for plain matplotlib plots)
        self.ylabel = ""
        self._as_category = set()
        self.all_columns = list(df.columns)
        self.numeric_columns = list(df.select_dtypes("number").columns)
        self.numeric_used = set()
        for role in graph.roles:
            if role.accepts in ("num", "num_time"):
                value = sel.get(role.key)
                self.numeric_used.update(value if isinstance(value, list) else [value] if value else [])

    # writing --------------------------------------------------------------
    def add(self, code: str, level: int = 0):
        pad = "    " * level
        for line in code.split("\n"):
            self.lines.append(pad + line if line.strip() else "")

    def need(self, import_line: str):
        if import_line not in self.imports:
            self.imports.append(import_line)

    def note(self, text: str):
        if text not in self.notes:
            self.notes.append(text)

    def fail(self, text: str):
        raise PlotError(text)

    def cols(self, cols) -> str:
        return cols_expr(cols, self.all_columns, self.numeric_columns)

    # facts about the data -------------------------------------------------
    def info(self, name):
        return self.ds.columns[name]

    def nunique(self, name) -> int:
        return int(self.df[name].nunique())

    def is_number(self, name) -> bool:
        s = self.df[name]
        return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)

    def is_continuous(self, name) -> bool:
        return self.is_number(name) and self.nunique(name) > 15

    def has_missing(self, cols) -> bool:
        return bool(self.df[list(cols)].isna().any().any())

    def heat_ticks(self, fit: HeatFit, what="column"):
        """Tick-label lines after sns.heatmap, from heat_fit()."""
        self.add("ax.tick_params(axis='y', labelrotation=0)  # row names read left to right")
        if fit.turn_x:
            self.add(f"ax.tick_params(axis='x', labelrotation=90)  # upright: side by side the {what} names would touch")
        if fit.every_x > 1 or fit.every_y > 1:
            k = max(fit.every_x, fit.every_y)
            nth = {2: "second", 3: "third"}.get(k, f"{k}th")
            self.note(f"There is no room to write every {what} name, so only every {nth} one is shown. "
                      "Pick fewer columns or a smaller Text size to see them all.")

    def heat_title(self, fit: HeatFit, auto_title):
        """Set the automatic title, and make the heatmap figure taller when the title has to
        wrap onto more lines (the cells were sized for one line)."""
        self.title = auto_title
        lab = self.labels
        title = (lab.title.strip() or auto_title) if lab.show_title else ""
        if not title:
            return
        per = TITLE_EM * 14.4 * self.text_scale / 72
        wrapped = str(wrap_title(title, max(10, int(fit.title_room / per))))
        extra = wrapped.count("\\n") if isinstance(title, Raw) else wrapped.count("\n")
        if extra:
            fit.h = round(fit.h + extra * 0.27 * self.text_scale, 1)

    def annot_size(self, fit: HeatFit, asked: str, normal_pt: float):
        """The cell number size: None = the normal size, 0 = leave the numbers out (they can't fit)."""
        if fit.annot_pt >= normal_pt - 0.05:
            return None
        if asked == "auto" and fit.annot_pt < 6:
            self.note("The numbers don't fit in cells this small, so they are left out (set 'Numbers in cells' "
                      "to yes to force them).")
            return 0
        return max(round(fit.annot_pt, 1), 5.0)

    # common snippets ------------------------------------------------------
    def fig_ax(self, w=10, h=6, layout="constrained"):
        # 'compressed' (matplotlib 3.6+) is constrained layout for square cells with a colour bar:
        # plain 'constrained' could push the title and axis names past the edge there
        self.add(f"fig, ax = plt.subplots(figsize=({lit(float(w))}, {lit(float(h))}), layout={lit(layout)})")
        self.mode = "single"

    def panels(self, n, w=4.4, h=3.4):
        ncols = n if n <= 3 else 2 if n == 4 else 3 if n <= 9 else 4 if n <= 16 else 5
        nrows = math.ceil(n / ncols)
        fw, fh = min(round(w * ncols, 1), 24.0), min(round(h * nrows, 1), 24.0)
        self.add(f"fig, axes = plt.subplots({nrows}, {ncols}, figsize=({fw}, {fh}), layout='constrained')")
        self.mode, self.axes_var = "multi", "axes"
        return nrows, ncols

    def hide_unused(self, n, nrows, ncols, var="cols"):
        if nrows * ncols > n:
            self.add(f"for ax in axes.flat[len({var}):]:\n    ax.set_visible(False)  # unused panels")

    def group(self, key, limit=MAX_GROUPS, convert=True):
        """Column used for colours/groups; numbers become categories for distinct colours."""
        name = self.sel.get(key)
        if not name:
            return None
        n = self.nunique(name)
        if n > limit:
            self.fail(f"'{name}' has {n:,} different values, which is too many to group or colour by "
                      f"(the limit is {limit}). Pick a column with fewer distinct values.")
        if convert and self.is_number(name) and name not in self.numeric_used and name not in self._as_category:
            self.add(f"df = df.astype({{{lit(name)}: 'category'}})  # numbers used as groups get distinct colours")
            self._as_category.add(name)
        return name

    def limit_categories(self, name, top):
        """Keep only the `top` most common values of a column (adds code if needed)."""
        n = self.nunique(name)
        if n > top:
            self.add(f"df = df[df[{lit(name)}].isin(df[{lit(name)}].value_counts().index[:{top}])]"
                     f"  # keep the {top} most common")
            self.note(f"'{name}' has {n:,} values; showing the {top} most common.")
            self.df = self.df[self.df[name].isin(self.df[name].value_counts().index[:top])]

    def binary_target(self, name, positive_text=""):
        """Code that turns a 2-class column into y_true (0/1). Returns the positive class."""
        values = list(self.df[name].dropna().unique())
        if len(values) != 2:
            self.fail(f"'{name}' needs exactly 2 classes for this plot, but it has {len(values)}.")
        if positive_text.strip() and positive_text.strip().lower() != "auto":
            match = [v for v in values if str(v) == positive_text.strip()]
            if not match:
                self.fail(f"'{positive_text}' is not a class of '{name}'. Its classes are "
                          f"{' and '.join(str(v) for v in sorted(values, key=str))}: type one of them, or auto.")
            positive = match[0]
        else:
            positive = positive_class(values)
        if is_boolish(self.df[name]) and positive is True:
            self.add(f"y_true = df[{lit(name)}].astype(int)  # True -> 1, False -> 0")
        elif set(map(lambda v: v if isinstance(v, str) else float(v), values)) == {0.0, 1.0} and positive == 1:
            self.add(f"y_true = df[{lit(name)}]")
        else:
            self.add(f"y_true = (df[{lit(name)}] == {lit(positive)}).astype(int)  # 1 = {clean_comment(positive)}")
        return positive

    # final touches: title, labels, log scales, legend ------------------------
    def finish(self):
        lab = self.labels
        title = (lab.title.strip() or self.title) if lab.show_title else ""
        xl, yl = lab.xlabel.strip() or self.xlabel, lab.ylabel.strip() or self.ylabel
        if self.mode in ("single", "single3d"):
            kw = {}
            if title:
                kw["title"] = self._fit_title(title)
            if xl:
                kw["xlabel"] = xl
            if yl:
                kw["ylabel"] = yl
            if kw:
                self.add(call("ax.set", **kw))
            if self.mode == "single" and self.graph.log_axes:
                if lab.logx:
                    self.add("ax.set_xscale('log')")
                if lab.logy:
                    self.add("ax.set_yscale('log')")
            self._legend("ax", 0)
            if self.zoomable:
                for axis in ("x", "y"):
                    lim = getattr(lab, f"{axis}lim", None)
                    if lim:
                        self.limit_lines.append(f"ax.set_{axis}lim({limit_lit(lim[0])}, {limit_lit(lim[1])})"
                                                f"  # zoomed with the {axis.upper()} slider")
            return
        if self.mode == "multi" and self.axes_var:
            if self.graph.log_axes and (lab.logx or lab.logy):
                self.add(f"for ax in {self.axes_var}.flat:")
                if lab.logx:
                    self.add("ax.set_xscale('log')", 1)
                if lab.logy:
                    self.add("ax.set_yscale('log')", 1)
            if lab.legend != "auto":
                self.add(f"for ax in {self.axes_var}.flat:")
                self._legend("ax", 1)
        if self.mode == "figure":
            # seaborn figure-level grids manage their own layout: only add what the user typed
            if lab.xlabel.strip() or lab.ylabel.strip():
                if self.graph.id == "pairplot":   # every panel is labelled with its own column
                    self.note("A pair plot labels each panel with its column, so the X / Y labels are not used.")
                else:
                    self.add(call("g.set_axis_labels", xl, yl))
            self._grid_legend()
            if self.graph.id in ("pairplot", "facet"):
                # the first layout ran before the panels were filled, so long tick labels
                # (bigger Text sizes) could push an axis name off the edge
                self.add("g.tight_layout()  # fit the names again now that every panel is drawn")
            if lab.show_title and lab.title.strip():
                text = self._fit_title(lab.title.strip(), centred=True)
                room = round(0.3 + 0.25 * self.text_scale * (str(text).count("\n") + 1), 2)
                self.add(f"fig.suptitle({lit(text)})")
                self.add(f"fig.subplots_adjust(top=1 - {room} / fig.get_size_inches()[1])  # room for the title")
            return
        if title:
            self.add(f"fig.suptitle({lit(self._fit_title(title, centred=True))})")

    def _width(self):
        """The figure width in inches: set by the plot, or read from its figsize=(...) line."""
        if self.fig_w:
            return float(self.fig_w)
        for line in reversed(self.lines):
            m = re.search(r"figsize=\(([\d.]+),", line)
            if m:
                return float(m.group(1))
        return None

    def _fit_title(self, title, centred=False):
        """Wrap a title that would run past the edge of the figure (big Text size, narrow plot)."""
        w = self._width()
        if not title or not w:
            return title
        room = (w - 0.4) if centred else (self.title_room or w - (0.9 + 0.5 * self.text_scale))
        per = TITLE_EM * 14.4 * self.text_scale / 72      # inches per character of a bold title
        return wrap_title(title, max(10, int(room / per)))

    @property
    def zoomable(self) -> bool:
        """One ordinary 2D axes called `ax`: the range sliders can zoom it."""
        return self.mode == "single" and self.graph.limits

    def _grid_legend(self):
        """Legend placement for seaborn grids (pair plot, facet grid, joint plot)."""
        where = self.labels.legend
        if where == "auto":
            return
        if self.graph.id == "joint":
            self._legend("g.ax_joint", 0)
            return
        self.add("if g.legend is not None:")
        if where == "hide":
            self.add("g.legend.remove()", 1)
        elif where == "outside":
            self.add("sns.move_legend(g, 'upper left', bbox_to_anchor=(1.0, 1.0))", 1)
        else:
            self.add(f"sns.move_legend(g, {lit(where)})", 1)

    def _legend(self, ax, level):
        where = self.labels.legend
        if where == "auto":
            return
        self.add(f"if {ax}.get_legend() is not None:", level)
        if where == "hide":
            self.add(f"{ax}.get_legend().remove()", level + 1)
        elif where == "outside":
            self.add(f"sns.move_legend({ax}, 'upper left', bbox_to_anchor=(1.02, 1))", level + 1)
        else:
            self.add(f"sns.move_legend({ax}, {lit(where)})", level + 1)


def limit_lit(value) -> str:
    """An axis limit as code: a number, or a pd.Timestamp for date axes."""
    if isinstance(value, pd.Timestamp):
        if value == value.normalize():
            return f"pd.Timestamp({str(value.date())!r})"
        return f"pd.Timestamp({value.isoformat(sep=' ', timespec='minutes')!r})"
    value = float(value)
    return lit(int(value)) if value.is_integer() and abs(value) < 1e15 else lit(value)


def zero_one(values) -> bool:
    """True for number values that are all 0 or 1 (a yes/no column written as numbers)."""
    try:
        return bool(values) and all(not isinstance(v, str) for v in values) and \
            {float(v) for v in values} <= {0.0, 1.0}
    except (TypeError, ValueError):
        return False


def class_key(value):
    """Compare classes the way pandas does: 1, 1.0 and True are the same class, '1' is not."""
    if isinstance(value, (bool, np.bool_)):
        return float(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    return value


def class_list(values, most=6) -> str:
    names = sorted((str(v) for v in values), key=str)
    return ", ".join(names[:most]) + (f" … ({len(names)} classes)" if len(names) > most else "")


def positive_class(values):
    """Pick the 'positive' class of a 2-class column (1, True, 'yes', ...)."""
    vals = list(values)
    if all(isinstance(v, (bool, np.bool_)) for v in vals):
        return True
    try:
        if set(float(v) for v in vals) == {0.0, 1.0}:
            return next(v for v in vals if float(v) == 1.0)
    except (TypeError, ValueError):
        pass
    lower = {str(v).strip().lower(): v for v in vals}
    for word in ("yes", "true", "satisfied", "positive", "pos", "y", "1", "survived", "transported", "churn", "default"):
        if word in lower:
            return lower[word]
    return sorted(vals, key=str)[-1]


# --------------------------------------------------------------------------- #
# Shared option blocks
# --------------------------------------------------------------------------- #

def _has(key):
    return lambda sel: bool(sel.get(key))


def _many(key):
    return lambda sel: isinstance(sel.get(key), list) and len(sel.get(key)) > 1


LAYOUT = Option("layout", "Several columns", "choice", "panels",
                ch(("panels", "one panel each"), ("overlay", "overlay in one plot")), show_if=_many("cols"))
MARKERS = ch(("", "none"), ("o", "circle  o"), (".", "dot  ."), ("s", "square  s"), ("^", "triangle  ^"),
             ("D", "diamond  D"), ("x", "cross  x"))
LINESTYLES = ch(("-", "solid  -"), ("--", "dashed  --"), (":", "dotted  :"), ("-.", "dash-dot  -."))
ORIENT = Option("orient", "Orientation", "choice", "vertical", ch("vertical", "horizontal"))


# --------------------------------------------------------------------------- #
# BASIC CHARTS
# --------------------------------------------------------------------------- #

def b_line(c: Ctx):
    x, ys = c.sel.get("x"), c.sel["y"]
    o = c.o
    hue = c.group("hue") if c.sel.get("hue") else None
    kw = dict(marker=o["marker"] or OMIT, linestyle=o["linestyle"] if o["linestyle"] != "-" else OMIT,
              linewidth=o["linewidth"])
    win = int(o["rolling"])
    if x and c.info(x).kind == DATETIME:
        c.note("Dates on the X axis are formatted automatically.")
    if hue:
        if not x:
            c.fail("Choose an X column to use 'Colour by' in a line plot.")
        band = ("ci", 95) if o["band"] else None
        c.fig_ax(10, 6)
        if len(ys) > 1:
            c.add(f"long = df.melt(id_vars={lit([x, hue])}, value_vars={c.cols(ys)}, "
                  f"var_name='series', value_name='value')")
            c.add(call("sns.lineplot", data=Raw("long"), x=x, y="value", hue=hue, style="series",
                       errorbar=band, **kw, ax=Raw("ax")))
            if win > 1:
                c.note("Smoothing is skipped when several Y columns are combined with 'Colour by'.")
        else:
            y = ys[0]
            if win > 1:
                smooth = f"{y} (rolling mean {win})"
                c.add(f"df = df.sort_values({lit(x)})")
                c.add(f"df[{lit(smooth)}] = df.groupby({lit(hue)}, observed=True)[{lit(y)}]"
                      f".transform(lambda s: s.rolling({win}, min_periods=1).mean())")
                y = smooth
            c.add(call("sns.lineplot", data=Raw("df"), x=x, y=y, hue=hue, errorbar=band, **kw, ax=Raw("ax")))
        c.title = f"{', '.join(ys)} by {x}"
        return
    sort = bool(x) and o["sort_x"]
    data = "data" if sort else "df"
    if sort:
        c.add(f"data = df.sort_values({lit(x)})")
    xs = f"{data}[{lit(x)}]" if x else f"{data}.index"
    c.fig_ax(10, 6)
    loop = len(ys) > 1
    col = "col" if loop else lit(ys[0])
    lvl = 1 if loop else 0
    if loop:
        c.add(f"for col in {c.cols(ys)}:")
    label = Raw("col") if loop else OMIT
    if win > 1:
        if o["show_raw"]:
            c.add(f"raw = ax.plot({xs}, {data}[{col}], linewidth=0.8, alpha=0.35)[0]  # unsmoothed, faint", lvl)
            color = Raw("raw.get_color()")
        else:
            color = OMIT
        smooth_label = Raw(f"f'{{col}} (rolling mean {win})'") if loop else f"{ys[0]} (rolling mean {win})"
        c.add(call("ax.plot", Raw(xs), Raw(f"{data}[{col}].rolling({win}, min_periods=1).mean()"),
                   color=color, **kw, label=smooth_label), lvl)
        c.add("ax.legend()")
    else:
        c.add(call("ax.plot", Raw(xs), Raw(f"{data}[{col}]"), **kw, label=label), lvl)
        if loop:
            c.add("ax.legend()")
    if x and c.info(x).kind == DATETIME:
        c.add("fig.autofmt_xdate()  # tilt the date labels")
    c.xlabel = x or "row"
    c.ylabel = ys[0] if len(ys) == 1 else "value"
    c.title = f"{', '.join(ys)} over {x}" if x else ", ".join(ys)


def b_scatter(c: Ctx):
    x, y = c.sel["x"], c.sel["y"]
    color, size = c.sel.get("color"), c.sel.get("size")
    o = c.o
    c.title = f"{y} vs {x}"
    if color and c.is_continuous(color):
        # numeric colour: colormap + colorbar (the book's plt.scatter style)
        c.fig_ax(10, 6.5)
        kw = dict(c=Raw(f"df[{lit(color)}]"), cmap=o["cmap"], alpha=o["alpha"])
        if size:
            c.add(f"s_min, s_max = df[{lit(size)}].min(), df[{lit(size)}].max()")
            c.add(f"sizes = 20 + 280 * (df[{lit(size)}] - s_min) / ((s_max - s_min) or 1)"
                  f"  # {clean_comment(size)} -> marker size 20..300")
            kw["s"] = Raw("sizes")
        else:
            kw["s"] = o["size"]
        c.add("points = " + call("ax.scatter", Raw(f"df[{lit(x)}]"), Raw(f"df[{lit(y)}]"), **kw))
        c.add(f"fig.colorbar(points, ax=ax, label={lit(color)})")
        if size:
            c.add("handles, names = points.legend_elements(prop='sizes', num=4, alpha=0.6,\n"
                  "                                        func=lambda s: s_min + (s - 20) * ((s_max - s_min) or 1) / 280)")
            c.add(f"ax.legend(handles, names, title={lit(size)})")
        c.xlabel, c.ylabel = x, y
        return
    hue = c.group("color")
    c.fig_ax(10, 6.5)
    c.add(call("sns.scatterplot", data=Raw("df"), x=x, y=y, hue=hue or OMIT,
               size=size or OMIT, sizes=(20, 300) if size else OMIT,
               s=o["size"] if not size else OMIT, alpha=o["alpha"],
               marker=o["marker"] if o["marker"] not in ("", "o") else OMIT, ax=Raw("ax")))


ERRORBARS = {"none": None, "ci": ("ci", 95), "sd": "sd", "se": "se"}


def _bar_fmt(values) -> str:
    big = float(np.nanmax(np.abs(values))) if len(values) else 0
    return "%.0f" if big >= 1000 else "%.1f" if big >= 10 else "%.2f"


def b_bar(c: Ctx):
    x, y = c.sel["x"], c.sel["y"]
    o = c.o
    hue = c.group("hue")
    est, top, horiz = o["estimator"], int(o["top_n"]), o["orient"] == "horizontal"
    n = c.nunique(x)
    cut = f"[:{top}]" if n > top else ""
    if o["sort"] in ("desc", "asc"):
        c.add(f"order = df.groupby({lit(x)}, observed=True)[{lit(y)}].agg({lit(est)})"
              f".sort_values(ascending={o['sort'] == 'asc'}).index{cut}")
        order = Raw("order")
    elif o["sort"] == "name":
        c.add(f"order = sorted(df[{lit(x)}].dropna().unique()){cut}")
        order = Raw("order")
    elif n > top:
        c.add(f"order = df[{lit(x)}].value_counts().index{cut}  # the {top} most common")
        order = Raw("order")
    else:
        order = OMIT
    if n > top:
        c.note(f"'{x}' has {n:,} values; showing {top} bars (change 'Max bars').")
    c.fig_ax(10, 6 if not horiz else max(4.5, min(14, 0.35 * min(n, top) + 1.5)))
    c.add(call("sns.barplot", data=Raw("df"), x=y if horiz else x, y=x if horiz else y, hue=hue or OMIT,
               estimator=est, errorbar=ERRORBARS[o["errorbar"]], order=order,
               orient="h" if horiz else OMIT, dodge=False if hue == x else OMIT, ax=Raw("ax")))
    if o["values"]:
        agg = c.df.groupby(x, observed=True)[y].agg(est).to_numpy()
        c.add("for container in ax.containers:")
        c.add(f"ax.bar_label(container, fmt={lit(_bar_fmt(agg))}, padding=2, fontsize=9)", 1)
    c.title = f"{est.title()} of {y} by {x}"


def b_area(c: Ctx):
    x, ys = c.sel.get("x"), c.sel["y"]
    o = c.o
    if x and o["sort_x"]:
        c.add(f"data = df.sort_values({lit(x)})")
        data = "data"
    else:
        data = "df"
    xs = f"{data}[{lit(x)}]" if x else f"{data}.index"
    c.add(f"cols = {c.cols(ys)}")
    c.fig_ax(10, 6)
    if o["stacked"]:
        c.add(f"ax.stackplot({xs}, [{data}[col] for col in cols], labels=cols, alpha={lit(o['alpha'])})")
    else:
        c.add("for col in cols:")
        c.add(f"line = ax.plot({xs}, {data}[col], label=col)[0]", 1)
        c.add(f"ax.fill_between({xs}, {data}[col], color=line.get_color(), alpha={lit(round(o['alpha'] * 0.5, 2))})", 1)
    c.add("ax.legend(loc='upper left')")
    if x and c.info(x).kind == DATETIME:
        c.add("fig.autofmt_xdate()")
    c.xlabel, c.ylabel = x or "row", "value" if len(ys) > 1 else ys[0]
    c.title = ("Stacked " if o["stacked"] else "") + f"area of {', '.join(ys)}"


def b_pie(c: Ctx):
    lab, val = c.sel["labels"], c.sel.get("values")
    o = c.o
    top = int(o["top_n"])
    if val:
        if (c.df[val] < 0).any():
            c.fail(f"'{val}' has negative numbers; pie slices can't be negative.")
        if not pd.to_numeric(c.df[val], errors="coerce").sum() > 0:
            c.fail(f"'{val}' adds up to 0, so there are no slices to draw: a pie needs amounts above 0.")
        c.add(f"counts = df.groupby({lit(lab)}, observed=True)[{lit(val)}].sum().sort_values(ascending=False)")
        c.title = f"Share of {val} by {lab}"
    else:
        c.add(f"counts = df[{lit(lab)}].value_counts()")
        c.title = f"Share of rows by {lab}"
    if c.nunique(lab) > top:
        c.add(f"counts = pd.concat([counts.iloc[:{top - 1}], pd.Series({{'Other': counts.iloc[{top - 1}:].sum()}})])"
              "  # small slices -> 'Other'")
    c.fig_ax(8, 7)
    wedge = {"width": 0.45, "edgecolor": "white"} if o["donut"] else {"edgecolor": "white"}
    c.add(call("ax.pie", Raw("counts.to_numpy()"), labels=Raw("counts.index.astype(str)"),
               autopct="%1.1f%%" if o["percent"] else OMIT, startangle=90, counterclock=False,
               wedgeprops=wedge, pctdistance=0.78 if o["donut"] else OMIT))
    c.add("ax.set_aspect('equal')")


def b_errorbar(c: Ctx):
    x, y, err = c.sel["x"], c.sel["y"], c.sel.get("err")
    o = c.o
    numeric_x = c.info(x).kind in (NUMERIC, DATETIME)
    if err:
        if numeric_x:
            c.add(f"data = df.sort_values({lit(x)})")
            d = "data"
        else:
            d = "df"
        xs, ys = f"{d}[{lit(x)}]", f"{d}[{lit(y)}]"
        es = f"{d}[{lit(err)}].abs()" if (c.df[err] < 0).any() else f"{d}[{lit(err)}]"
        c.title = f"{y} ± {err}"
        c.ylabel = y
    else:
        c.add(f"stats = df.groupby({lit(x)}, observed=True)[{lit(y)}].agg(['mean', 'std', 'count']).reset_index()")
        spread = o["spread"]
        if spread == "std":
            c.add("stats['error'] = stats['std']  # 1 standard deviation")
        elif spread == "sem":
            c.add("stats['error'] = stats['std'] / np.sqrt(stats['count'])  # standard error of the mean")
        else:
            c.add("stats['error'] = 1.96 * stats['std'] / np.sqrt(stats['count'])  # ~95% confidence interval")
        xs, ys, es = f"stats[{lit(x)}]", "stats['mean']", "stats['error']"
        if c.df.groupby(x)[y].count().min() < 2:
            c.add("stats['error'] = stats['error'].fillna(0)  # a group with one row has no spread")
        if c.df.groupby(x)[y].count().max() < 2:
            c.note(f"Every '{x}' value appears only once, so there is no spread to show. "
                   "Pick an X with repeated values, or an error column.")
        c.title = f"Mean {y} by {x} (± {dict(std='std', sem='std. error', ci95='95% CI')[spread]})"
        c.ylabel = f"mean {y}"
    c.fig_ax(10, 6)
    band = o["style"] == "band"
    if band and not numeric_x:
        c.note("A shaded band needs a number or date X axis, so error bars are used instead.")
        band = False
    marker = o["marker"]
    if band:
        c.add(call("ax.plot", Raw(xs), Raw(ys), marker=marker or OMIT))
        c.add(f"ax.fill_between({xs}, {ys} - {es}, {ys} + {es}, alpha=0.25)")
    else:
        fmt = (marker or "") + ("-" if o["connect"] else "")
        c.add(call("ax.errorbar", Raw(xs), Raw(ys), yerr=Raw(es), fmt=fmt or "none", capsize=int(o["capsize"]),
                   elinewidth=1, ecolor="gray"))
    c.xlabel = x


# --------------------------------------------------------------------------- #
# DISTRIBUTIONS
# --------------------------------------------------------------------------- #

def _dist_family(c: Ctx, func: str, kw: dict, overlay_kw: dict, word: str):
    cols = list(c.sel["cols"])
    hue = c.group("hue")
    if len(cols) > MAX_PANELS:
        c.note(f"Showing the first {MAX_PANELS} of {len(cols)} columns.")
        cols = cols[:MAX_PANELS]
    layout = c.o.get("layout", "panels")
    if len(cols) == 1:
        c.fig_ax(10, 6)
        c.add(call(func, data=Raw("df"), x=cols[0], hue=hue or OMIT, **kw, ax=Raw("ax")))
        c.title = f"{word} of {cols[0]}" + (f" by {hue}" if hue else "")
        return
    if layout == "overlay" and not hue:
        c.add(f"long = df[{c.cols(cols)}].melt(var_name='column', value_name='value')  # stack the columns")
        c.fig_ax(10, 6)
        c.add(call(func, data=Raw("long"), x="value", hue="column", **{**kw, **overlay_kw}, ax=Raw("ax")))
        c.title = f"{word} of {len(cols)} columns"
        return
    if layout == "overlay":
        c.note("'Overlay' can't be combined with 'Colour by', so each column gets its own panel.")
    c.add(f"cols = {c.cols(cols)}")
    nrows, ncols = c.panels(len(cols))
    c.add("for ax, col in zip(axes.flat, cols):")
    c.add(call(func, data=Raw("df"), x=Raw("col"), hue=hue or OMIT, **kw, ax=Raw("ax")), 1)
    c.add("ax.set_title(col)", 1)
    c.hide_unused(len(cols), nrows, ncols)
    c.title = f"{word}s" + (f" by {hue}" if hue else "")


def b_hist(c: Ctx):
    o = c.o
    kw = {}
    if int(o["bins"]) > 0:
        kw["bins"] = int(o["bins"])
    if o["stat"] != "count":
        kw["stat"] = o["stat"]
    if o["element"] != "bars":
        kw["element"] = o["element"]
    if o["kde"]:
        kw["kde"] = True
    if o["cumulative"]:
        kw["cumulative"] = True
    if c.sel.get("hue") and o["multiple"] != "layer":
        kw["multiple"] = o["multiple"]
    if c.labels.logx:
        kw["log_scale"] = True    # log-spaced bins, so the bars stay even on a log axis
        for col in c.sel["cols"]:
            if (c.df[col] <= 0).any():
                c.add(f"df = df[df[{lit(col)}] > 0]  # a log scale can't show 0 or negative values")
                c.note(f"Log scale: rows where '{col}' is 0 or less are left out.")
    overlay = {"element": "step"} if o["element"] == "bars" else {}
    if o["stat"] != "count":
        overlay["common_norm"] = False
    _dist_family(c, "sns.histplot", kw, overlay, "Distribution")


def b_kde(c: Ctx):
    o = c.o
    kw = {}
    if o["fill"]:
        kw["fill"] = True
    if float(o["bw_adjust"]) != 1.0:
        kw["bw_adjust"] = float(o["bw_adjust"])
    if o["cumulative"]:
        kw["cumulative"] = True
    if c.sel.get("hue"):
        if o["multiple"] != "layer":
            kw["multiple"] = o["multiple"]
        if not o["common_norm"]:
            kw["common_norm"] = False
    _dist_family(c, "sns.kdeplot", kw, {"common_norm": False}, "Density")


def b_ecdf(c: Ctx):
    o = c.o
    kw = {}
    if o["stat"] != "proportion":
        kw["stat"] = o["stat"]
    if o["complementary"]:
        kw["complementary"] = True
    _dist_family(c, "sns.ecdfplot", kw, {}, "ECDF")


def _cat_family(c: Ctx, func: str, kw: dict, word: str):
    """Box / violin / strip plots: values (y) split by a group (x) and colour (hue)."""
    ys = list(c.sel["y"])
    x, horiz, top = c.sel.get("x"), c.o["orient"] == "horizontal", int(c.o["top_n"])
    hue = c.group("hue")
    if x and x == hue:
        hue = None
    if x:
        c.group("x", limit=10_000, convert=False)
        c.limit_categories(x, top)
    if not x and hue and len(ys) == 1:
        x, hue = hue, None   # one value column: colour groups become the axis groups
    if len(ys) > MAX_PANELS:
        c.note(f"Showing the first {MAX_PANELS} of {len(ys)} columns.")
        ys = ys[:MAX_PANELS]

    def plot(data, xv, yv, hv, ax="ax", level=0):
        args = dict(x=yv, y=xv) if horiz else dict(x=xv, y=yv)
        args = {k: v for k, v in args.items() if v is not None}
        c.add(call(func, data=Raw(data), **args, hue=hv or OMIT, **kw,
                   orient="h" if horiz else OMIT, ax=Raw(ax)), level)

    if len(ys) == 1:
        c.fig_ax(10, 6)
        plot("df", x, ys[0], hue)
        c.title = f"{ys[0]}" + (f" by {x}" if x else "") + (f" and {hue}" if hue else "")
        return
    if not x:
        scale = c.o.get("scale", "raw")
        keep = ys + ([hue] if hue else [])
        if scale != "raw":
            c.add(f"data = df[{c.cols(keep)}].copy()")
            c.add(f"cols = {c.cols(ys)}")
            if scale == "z":
                c.add("data[cols] = (data[cols] - data[cols].mean()) / data[cols].std()  # z-scores: one shared scale")
            else:
                c.add("data[cols] = (data[cols] - data[cols].min()) / (data[cols].max() - data[cols].min())  # 0..1")
            src, vv = "data", "cols"
        else:
            src, vv = "df", c.cols(ys)
        ids = f"id_vars={lit([hue])}, " if hue else ""
        c.add(f"long = {src}.melt({ids}value_vars={vv}, var_name='column', value_name='value')")
        c.fig_ax(max(10, min(18, 1.1 * len(ys) + 3)), 6)
        plot("long", "column", "value", hue)
        if horiz:
            c.ylabel = ""
        c.title = f"{word} of {len(ys)} columns" + (" (standardised)" if scale == "z" else
                                                     " (scaled 0-1)" if scale == "minmax" else "")
        return
    c.add(f"cols = {c.cols(ys)}")
    nrows, ncols = c.panels(len(ys), w=5.2, h=3.8)
    c.add("for ax, col in zip(axes.flat, cols):")
    plot("df", x, Raw("col"), hue, level=1)
    c.add("ax.set_title(col)", 1)
    c.hide_unused(len(ys), nrows, ncols)
    c.title = f"{word}s by {x}"


def b_box(c: Ctx):
    o = c.o
    kw = {}
    if not o["outliers"]:
        kw["showfliers"] = False
    if o["notch"]:
        kw["notch"] = True
    _cat_family(c, "sns.boxplot", kw, "Box plot")
    if o["points"]:
        if c.sel.get("hue") or len(c.sel["y"]) > 1:
            c.note("Point overlay works for one value column without 'Colour by'.")
        else:
            x, y, horiz = c.sel.get("x"), c.sel["y"][0], o["orient"] == "horizontal"
            args = dict(x=y, y=x) if horiz else dict(x=x, y=y)
            args = {k: v for k, v in args.items() if v is not None}
            c.add(call("sns.stripplot", data=Raw("df"), **args, color="black", size=2.5, alpha=0.35,
                       orient="h" if horiz else OMIT, ax=Raw("ax")))


def b_violin(c: Ctx):
    o = c.o
    kw = {}
    if o["inner"] != "box":
        kw["inner"] = None if o["inner"] == "none" else o["inner"]
    if o["split"]:
        hue = c.sel.get("hue")
        if hue and c.nunique(hue) == 2 and len(c.sel["y"]) == 1:
            kw["split"] = True
        else:
            c.note("'Split' needs a 'Colour by' column with exactly 2 values.")
    if o["trim"]:
        kw["cut"] = 0
    _cat_family(c, "sns.violinplot", kw, "Violin plot")


def b_strip(c: Ctx):
    o = c.o
    kind = o["kind"]
    kw = {"size": float(o["size"]), "alpha": float(o["alpha"])}
    if kind == "strip" and not o["jitter"]:
        kw["jitter"] = False
    if c.sel.get("hue") and o["dodge"]:
        kw["dodge"] = True
    _cat_family(c, "sns.swarmplot" if kind == "swarm" else "sns.stripplot", kw,
                "Swarm plot" if kind == "swarm" else "Strip plot")


def b_qq(c: Ctx):
    cols = list(c.sel["cols"])[:MAX_PANELS]
    z = c.o["standardize"]
    c.need("from statistics import NormalDist")

    def body(col, level, label):
        c.add(f"values = df[{col}].dropna().to_numpy()", level)
        c.add("m = min(len(values), 1000)  # plot at most 1000 quantiles", level)
        c.add("probs = (np.arange(1, m + 1) - 0.5) / m", level)
        c.add("theory = np.array([NormalDist().inv_cdf(p) for p in probs])  # standard normal quantiles", level)
        c.add("sample = np.quantile(values, probs)", level)
        if z:
            c.add("sample = (sample - values.mean()) / values.std()  # z-scores", level)
        c.add(call("ax.scatter", Raw("theory"), Raw("sample"), s=16, alpha=0.75, label=label), level)
        if z:
            c.add("ax.plot(theory, theory, color='#5c5c68', linestyle='--', linewidth=1,\n"
                  "        label='normal reference (y = x)')", level)
        else:
            c.add("ax.plot(theory, values.mean() + values.std() * theory, color='#5c5c68', linestyle='--',\n"
                  "        linewidth=1, label='normal with the same mean and std')", level)

    if len(cols) == 1:
        c.fig_ax(7.5, 6.5)
        body(lit(cols[0]), 0, cols[0])
        c.add("ax.legend()")
        c.xlabel = "theoretical quantiles (standard normal)"
        c.ylabel = "z-score" if z else f"quantiles of {cols[0]}"
        c.title = f"Normal Q-Q plot of {cols[0]}"
        return
    c.add(f"cols = {c.cols(cols)}")
    nrows, ncols = c.panels(len(cols), w=4.4, h=4.0)
    c.add("for ax, col in zip(axes.flat, cols):")
    body("col", 1, OMIT)
    c.add("ax.set(title=col, xlabel='normal quantiles', ylabel='sample quantiles')", 1)
    c.hide_unused(len(cols), nrows, ncols)
    c.title = "Normal Q-Q plots"


# --------------------------------------------------------------------------- #
# RELATIONSHIPS
# --------------------------------------------------------------------------- #

def b_regression(c: Ctx):
    x, y = c.sel["x"], c.sel["y"]
    o = c.o
    hue = c.group("hue", limit=12, convert=False)
    order = int(o["order"])
    ci = 95 if o["ci"] else None
    scatter_kws = {"alpha": float(o["alpha"]), "s": int(o["size"])}
    show = o["show"]
    if show == "both":
        c.add("fig, (ax, ax2) = plt.subplots(1, 2, figsize=(15.0, 6.0), layout='constrained')")
        c.mode = "multi"
    else:
        c.fig_ax(10, 6.5)
    if show in ("fit", "both"):
        if hue:
            c.add(f"for name, group in df.groupby({lit(hue)}):")
            c.add(call("sns.regplot", data=Raw("group"), x=x, y=y, order=order if order > 1 else OMIT, ci=ci,
                       scatter_kws=scatter_kws, label=Raw("str(name)"), ax=Raw("ax")), 1)
            c.add(f"ax.legend(title={lit(hue)})")
        else:
            c.add(call("sns.regplot", data=Raw("df"), x=x, y=y, order=order if order > 1 else OMIT, ci=ci,
                       scatter_kws=scatter_kws, line_kws={"color": "C1"}, ax=Raw("ax")))
            if o["equation"]:
                d = "df"
                if c.has_missing([x, y]):
                    c.add(f"d = df[{lit([x, y])}].dropna()")
                    d = "d"
                c.add(f"fit = np.polyfit({d}[{lit(x)}], {d}[{lit(y)}], {order})  # least-squares polynomial")
                c.add(f"pred = np.polyval(fit, {d}[{lit(x)}])")
                c.add(f"r2 = 1 - (({d}[{lit(y)}] - pred) ** 2).sum() / (({d}[{lit(y)}] - {d}[{lit(y)}].mean()) ** 2).sum()")
                if order == 1:
                    c.add("sign = '-' if fit[1] < 0 else '+'  # y = 2x - 3, not y = 2x + -3")
                    text = "f'y = {fit[0]:.4g}·x {sign} {abs(fit[1]):.4g}\\nR² = {r2:.3f}'"
                else:
                    text = f"f'degree-{order} polynomial\\nR² = {{r2:.3f}}'"
                c.add(f"ax.text(0.02, 0.97, {text}, transform=ax.transAxes, va='top',\n"
                      "        bbox={'boxstyle': 'round', 'facecolor': 'white', 'alpha': 0.85})")
        c.title = f"{y} vs {x}" + (" with linear fit" if order == 1 else f" with degree-{order} fit")
        if c.labels.logx or c.labels.logy:
            c.note("The line is fitted to the raw values: on log axes it bends, and it is cut off where it falls "
                   "below 0. A scatter shows a curved link on log axes better.")
    if show in ("resid", "both"):
        rax = "ax2" if show == "both" else "ax"
        if hue:
            c.note("Residuals are drawn for all rows together ('Colour by' is ignored there).")
        c.add(call("sns.residplot", data=Raw("df"), x=x, y=y, order=order if order > 1 else OMIT,
                   scatter_kws=scatter_kws, ax=Raw(rax)))
        c.add(f"{rax}.set(ylabel='residual (actual - fitted)')")
        if show == "both":
            c.add("ax2.set_title('Residuals')")
        else:
            c.title = f"Residuals of {y} ~ {x}"


def b_joint(c: Ctx):
    x, y = c.sel["x"], c.sel["y"]
    kind = c.o["kind"]
    hue = c.sel.get("hue")
    if hue and kind in ("hex", "reg", "resid"):
        c.note(f"kind='{kind}' can't use 'Colour by', so it was left out.")
        hue = None
    else:
        hue = c.group("hue")
    extra = {"alpha": 0.6, "s": 20} if kind == "scatter" else {}
    c.add("g = " + call("sns.jointplot", data=Raw("df"), x=x, y=y, hue=hue or OMIT,
                        kind=kind if kind != "scatter" else OMIT, height=float(c.o["height"]), **extra))
    c.add("fig = g.figure")
    c.fig_w = float(c.o["height"])
    c.mode = "figure"
    c.title = f"{y} vs {x}"


def b_hexbin(c: Ctx):
    x, y = c.sel["x"], c.sel["y"]
    o = c.o
    c.fig_ax(9.5, 7)
    xs, ys = Raw(f"df[{lit(x)}]"), Raw(f"df[{lit(y)}]")
    label = "count in bin" + (" (log scale)" if o["log"] else "")
    if o["kind"] == "hex":
        c.add("hb = " + call("ax.hexbin", xs, ys, gridsize=int(o["gridsize"]), cmap=o["cmap"], mincnt=1,
                             bins="log" if o["log"] else OMIT))
        c.add(f"fig.colorbar(hb, ax=ax, label={lit(label)})")
    else:
        c.add("counts, xedges, yedges, image = " + call(
            "ax.hist2d", xs, ys, bins=int(o["gridsize"]), cmap=o["cmap"], cmin=1,
            norm=Raw("mpl.colors.LogNorm()") if o["log"] else OMIT))
        c.add(f"fig.colorbar(image, ax=ax, label={lit(label)})")
    c.xlabel, c.ylabel = x, y
    c.title = f"Where the points are: {y} vs {x}"


def b_kde2d(c: Ctx):
    x, y = c.sel["x"], c.sel["y"]
    o = c.o
    hue = c.group("hue")
    c.fig_ax(9.5, 7)
    fill = bool(o["fill"])
    c.add(call("sns.kdeplot", data=Raw("df"), x=x, y=y, hue=hue or OMIT, fill=fill or OMIT,
               levels=int(o["levels"]), thresh=float(o["thresh"]) if float(o["thresh"]) != 0.05 else OMIT,
               bw_adjust=float(o["bw_adjust"]) if float(o["bw_adjust"]) != 1 else OMIT,
               cmap=o["cmap"] if not hue else OMIT, cbar=True if (fill and not hue) else OMIT, ax=Raw("ax")))
    if o["points"]:
        c.add(call("sns.scatterplot", data=Raw("df"), x=x, y=y, s=6, color="black", alpha=0.25,
                   linewidth=0, ax=Raw("ax")))
    c.title = f"Density of {y} vs {x}"


def b_pairplot(c: Ctx):
    cols = list(c.sel["cols"])
    hue = c.sel.get("hue")
    if hue in cols:
        cols.remove(hue)
        c.note(f"'{hue}' is used for colour, so it was removed from the pair plot columns.")
    if len(cols) < 2:
        c.fail("A pair plot needs at least 2 number columns.")
    if len(cols) > 12:
        c.fail(f"You picked {len(cols)} columns; a pair plot of more than 12 is unreadable. Pick fewer.")
    hue = c.group("hue")
    kind = c.o["kind"]
    c.add("g = " + call("sns.pairplot", Raw("df"), vars=cols, hue=hue or OMIT,
                        kind=kind if kind != "scatter" else OMIT,
                        diag_kind=c.o["diag"] if c.o["diag"] != "auto" else OMIT,
                        corner=True if c.o["corner"] else OMIT, height=float(c.o["height"]),
                        plot_kws={"alpha": 0.6, "s": 18} if kind == "scatter" else
                        {"ci": None, "scatter_kws": {"alpha": 0.5, "s": 12}} if kind == "reg" else OMIT))
    c.add("fig = g.figure")
    c.fig_w = float(c.o["height"]) * len(cols) + (1.0 if hue else 0.0)
    c.mode = "figure"
    c.title = "Pair plot" + (f" coloured by {hue}" if hue else "")


# --------------------------------------------------------------------------- #
# ML & MATRICES
# --------------------------------------------------------------------------- #

def b_corr(c: Ctx):
    cols = list(c.sel["cols"])
    if len(cols) > 60:
        c.note(f"Showing the first 60 of {len(cols)} columns.")
        cols = cols[:60]
    o = c.o
    n = len(cols)
    annot = n <= 15 if o["annot"] == "auto" else o["annot"] == "yes"
    method = o["method"]
    c.add(f"cols = {c.cols(cols)}")
    c.add(f"corr = df[cols].corr(method={lit(method)})")
    if o["triangle"]:
        c.add("mask = np.triu(np.ones_like(corr, dtype=bool))  # hide the mirror-image upper half")
    side = round(min(16.0, 4.5 + 0.42 * n), 1)
    decimals = int(o["decimals"])
    normal_pt = (8 if n > 10 else ANNOT_PT) * c.text_scale     # smaller numbers in a big matrix
    fit = heat_fit(cols, cols, side, round(side * 0.82, 1), square=True, scale=c.text_scale,
                   annot_chars=(decimals + 3 if decimals else 2) if annot else 0, annot_pt=normal_pt)
    size = c.annot_size(fit, o["annot"], normal_pt) if annot else None
    annot = annot and size != 0
    if size is None and annot and n > 10:
        size = round(normal_pt, 1)
    every = max(fit.every_x, fit.every_y)
    c.heat_title(fit, f"{method.title()} correlation between {n} columns")
    c.fig_ax(fit.w, fit.h, layout="compressed")
    c.add(call("sns.heatmap", Raw("corr"), mask=Raw("mask") if o["triangle"] else OMIT,
               annot=True if annot else OMIT, fmt=f".{decimals}f" if annot else OMIT,
               annot_kws={"size": size} if annot and size else OMIT, cmap=o["cmap"], vmin=-1, vmax=1, center=0,
               square=True, linewidths=0.5 if n <= 30 else OMIT,
               xticklabels=every if every > 1 else OMIT, yticklabels=every if every > 1 else OMIT,
               cbar_kws={"shrink": 0.8, "label": f"{method} correlation"}, ax=Raw("ax")))
    c.add("ax.grid(False)")
    c.heat_ticks(fit)
    c.title_room = fit.title_room


def b_target_corr(c: Ctx):
    target = c.sel["target"]
    feats = [f for f in c.sel["features"] if f != target]
    if not feats:
        c.fail("Pick at least one feature column (other than the target).")
    flat = [f for f in feats if not pd.to_numeric(c.df[f], errors="coerce").std() > 0]
    if flat:
        feats = [f for f in feats if f not in flat]
        if not feats:
            c.fail(f"{', '.join(map(repr, flat))} {'has' if len(flat) == 1 else 'have'} the same value in every row, "
                   "so there is no correlation to show. Pick features whose values change.")
        c.note(f"Left out (the same value in every row): {', '.join(flat)}.")
    o = c.o
    top = int(o["top_n"])
    if c.is_number(target) and c.nunique(target) > 2:
        c.add(f"target = df[{lit(target)}]")
    else:
        values = list(c.df[target].dropna().unique())
        if len(values) != 2:
            c.fail(f"The target must be a number column or a 2-class column; '{target}' has {len(values)} classes.")
        pos = positive_class(values)
        if is_boolish(c.df[target]):
            c.add(f"target = df[{lit(target)}].astype(int)  # True -> 1")
        else:
            c.add(f"target = (df[{lit(target)}] == {lit(pos)}).astype(int)  # 1 = {clean_comment(pos)}")
    c.add(f"features = {c.cols(feats)}")
    if o["method"] == "pearson":
        c.add("corr = df[features].corrwith(target)")
    else:
        c.add("corr = df[features].rank().corrwith(target.rank())  # Spearman = Pearson on ranks")
    c.add("corr = corr.dropna()")
    if o["sort"] == "abs":
        c.add(f"corr = corr.reindex(corr.abs().sort_values(ascending=False).index)[:{top}]  # strongest first")
    else:
        c.add(f"corr = corr.sort_values(ascending=False)[:{top}]")
    n = min(top, len(feats))
    c.fig_ax(9, round(max(4.0, 0.36 * n + 1.4), 1))
    c.add("colors = np.where(corr.to_numpy() >= 0, '#2a78d6', '#eb6834')  # blue = positive, orange = negative")
    c.add("ax.barh(corr.index.astype(str), corr.to_numpy(), color=colors)")
    c.add("ax.yaxis.grid(False)  # grid lines only along the values")
    c.add("ax.invert_yaxis()  # first item at the top")
    c.add("ax.axvline(0, color='black', linewidth=0.8)")
    c.add("ax.margins(x=0.15)")
    c.add("for i, v in enumerate(corr.to_numpy()):")
    c.add("ax.text(v, i, f' {v:.2f} ', va='center', ha='left' if v >= 0 else 'right', fontsize=9)", 1)
    c.xlabel = f"{o['method'].title()} correlation with {target}"
    c.title = f"Which features move with {target}?"


def b_pivot(c: Ctx):
    r, col, val = c.sel["rows"], c.sel["cols"], c.sel.get("value")
    o = c.o
    top = int(o["top_n"])
    if r == col:
        c.fail("Rows and columns must be two different columns.")
    if val in (r, col):
        c.fail(f"'{val}' is already used for rows or columns; pick a different Value column.")
    c.limit_categories(r, top)
    c.limit_categories(col, top)
    agg = o["agg"]
    if val and agg != "count":
        c.add(f"table = df.pivot_table(index={lit(r)}, columns={lit(col)}, values={lit(val)}, aggfunc={lit(agg)})")
        label, fmt = f"{agg} of {val}", f".{int(o['decimals'])}f"
        c.title = f"{agg.title()} of {val} by {r} and {col}"
        table = c.df.pivot_table(index=r, columns=col, values=val, aggfunc=agg)
    else:
        if val:
            c.note("'count' counts rows, so the Value column is not needed.")
        c.add(f"table = pd.crosstab(df[{lit(r)}], df[{lit(col)}])  # number of rows for each pair")
        label, fmt = "number of rows", "d"
        c.title = f"Rows per {r} × {col}"
        table = pd.crosstab(c.df[r], c.df[col])
    nr, nc = c.nunique(r), c.nunique(col)
    annot = (nr * nc <= 400) if o["annot"] == "auto" else o["annot"] == "yes"
    values = [v for v in table.to_numpy().ravel() if pd.notna(v)]
    chars = max((len(format(v, fmt)) for v in values), default=1) if annot else 0
    normal_pt = ANNOT_PT * c.text_scale
    fit = heat_fit([str(v) for v in table.columns] or ["?"], [str(v) for v in table.index] or ["?"],
                   round(min(18.0, max(7.5, 3.5 + 0.75 * nc)), 1), round(min(14.0, max(5.5, 2.8 + 0.45 * nr)), 1),
                   square=False, scale=c.text_scale, annot_chars=chars, axis_names=True)
    size = c.annot_size(fit, o["annot"], normal_pt) if annot else None
    annot = annot and size != 0
    c.heat_title(fit, c.title)
    c.fig_ax(fit.w, fit.h)
    c.add(call("sns.heatmap", Raw("table"), annot=True if annot else OMIT, fmt=fmt if annot else OMIT,
               annot_kws={"size": size} if annot and size else OMIT, cmap=o["cmap"], linewidths=0.5,
               xticklabels=fit.every_x if fit.every_x > 1 else OMIT,
               yticklabels=fit.every_y if fit.every_y > 1 else OMIT, cbar_kws={"label": label}, ax=Raw("ax")))
    c.add("ax.grid(False)")
    c.heat_ticks(fit, "category")
    c.title_room = fit.title_room


def b_count(c: Ctx):
    col = c.sel["col"]
    o = c.o
    hue = c.group("hue")
    n, top = c.nunique(col), int(o["top_n"])
    cut = f"[:{top}]" if n > top else ""
    if n > top:
        c.note(f"'{col}' has {n:,} values; showing the {top} most common.")
    if o["order"] == "count":
        c.add(f"order = df[{lit(col)}].value_counts().index{cut}")
    else:
        c.add(f"order = sorted(df[{lit(col)}].dropna().unique()){cut}")
    longest = max((len(str(v)) for v in c.df[col].dropna().unique()[:200]), default=1)
    horiz = o["orient"] == "horizontal" or (o["orient"] == "auto" and (min(n, top) > 8 or longest > 12))
    c.fig_ax(10, round(max(4.5, min(14, 0.36 * min(n, top) + 1.6)), 1) if horiz else 6)
    axis = {"y": col} if horiz else {"x": col}
    c.add(call("sns.countplot", data=Raw("df"), **axis, hue=hue or OMIT, order=Raw("order"),
               dodge=False if hue == col else OMIT, ax=Raw("ax")))
    if o["labels"] != "none":
        size = "bar.get_width()" if horiz else "bar.get_height()"
        text = {"both": "f'{v:,.0f} ({v / total:.0%})'", "count": "f'{v:,.0f}'",
                "percent": "f'{v / total:.1%}'"}[o["labels"]]
        c.add("total = len(df)")
        c.add("for container in ax.containers:")
        c.add(f"values = [{size} for bar in container]", 1)
        c.add(f"ax.bar_label(container, labels=[{text} if v > 0 else '' for v in values], padding=2, fontsize=9)", 1)
    c.title = f"Rows per {col}" + (f" split by {hue}" if hue else "")


def b_missing(c: Ctx):
    cols = list(c.sel["cols"])
    o = c.o
    missing = c.df[cols].isna()
    pct = missing.mean() * 100
    shown = pct[pct > 0] if o["only_missing"] else pct
    if not (pct > 0).any():
        c.fig_ax(9, 3.5)
        c.add("ax.text(0.5, 0.5, 'No missing values in the selected columns', ha='center', va='center',\n"
              "        fontsize=15, transform=ax.transAxes)")
        c.add("ax.axis('off')")
        c.title = "Missing values"
        c.note("There are no missing values in the chosen columns.")
        return
    c.add(f"cols = {c.cols(cols)}")
    c.add("missing = df[cols].isna()  # True where a value is missing")
    c.add("pct = missing.mean() * 100")
    if o["sort"]:
        c.add("pct = pct.sort_values(ascending=False)")
    if o["only_missing"]:
        c.add("pct = pct[pct > 0]  # only columns that have gaps")
    k = len(shown)
    height = round(max(4.0, min(16.0, 0.3 * k + 1.6)), 1)
    view = o["view"]

    def bar(ax):
        c.add(f"{ax}.barh(pct.index.astype(str), pct.to_numpy(), color='#eb6834')")
        c.add(f"{ax}.yaxis.grid(False)")
        c.add(f"{ax}.invert_yaxis()")
        c.add(f"{ax}.set(xlabel='% of rows missing', xlim=(0, pct.max() * 1.2 + 1), title='Missing values per column')")
        c.add("for i, v in enumerate(pct.to_numpy()):")
        c.add(f"{ax}.text(v, i, f' {{v:.1f}}%', va='center', fontsize=9)", 1)

    def matrix(ax):
        c.add(f"{ax}.imshow(missing[pct.index].to_numpy(), aspect='auto', interpolation='nearest', vmin=0, vmax=1,\n"
              "          cmap=mpl.colors.ListedColormap(['#eef0f5', '#eb6834']))")
        c.add(f"{ax}.set_xticks(range(len(pct)), pct.index.astype(str), rotation=90)")
        c.add(f"{ax}.set(ylabel='row', title='Where the gaps are (orange = missing)')")
        c.add(f"{ax}.grid(False)")

    if view == "both":
        c.add(f"fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, {height}), layout='constrained',\n"
              "                               gridspec_kw={'width_ratios': [1, 1.5]})")
        bar("ax1")
        matrix("ax2")
        c.mode = "multi"
    elif view == "bar":
        c.fig_ax(10, height)
        bar("ax")
    else:
        c.fig_ax(12, 7)
        matrix("ax")
    c.title = f"Missing values ({int(missing.to_numpy().sum()):,} cells in {k} column(s))"


def b_confusion(c: Ctx):
    a, p = c.sel["actual"], c.sel["predicted"]
    o = c.o
    if a == p:
        c.fail("Actual and Predicted must be different columns.")
    if c.nunique(a) > MAX_GROUPS:
        c.fail(f"'{a}' has {c.nunique(a)} classes; a confusion matrix needs a class column (at most {MAX_GROUPS}).")
    prob = c.is_continuous(p) and bool(c.df[p].between(0, 1).all())
    if not prob and c.nunique(p) > MAX_GROUPS:
        c.fail(f"'{p}' has {c.nunique(p)} values; it should hold predicted classes (or 0-1 probabilities).")
    a_vals = list(c.df[a].dropna().unique())
    p_vals = [0, 1] if prob else list(c.df[p].dropna().unique())
    a01 = is_boolish(c.df[a]) or zero_one(a_vals)
    p01 = prob or is_boolish(c.df[p]) or zero_one(p_vals)
    true_vals = [int(v) for v in a_vals] if is_boolish(c.df[a]) else a_vals
    pred_vals = [int(v) for v in p_vals] if is_boolish(c.df[p]) else p_vals

    def as01(name, values, other):
        # a 2-class column written as 0/1, to compare it with the 0/1 values of the other column
        pos = positive_class(values)
        c.note(f"'{name}' was turned into 0/1 to match '{other}': 1 = {pos}, 0 = the other class.")
        return f"(df[{lit(name)}] == {lit(pos)}).astype(int)  # 1 = {clean_comment(pos)}"

    true_expr = f"df[{lit(a)}]" + (".astype(int)" if is_boolish(c.df[a]) else "")
    pred_expr = f"df[{lit(p)}]" + (".astype(int)" if is_boolish(c.df[p]) else "")
    if not {class_key(v) for v in a_vals} & {class_key(v) for v in p_vals}:
        # no class in common: every row would count as wrong (e.g. 'yes'/'no' against 0/1)
        if p01 and not a01 and len(a_vals) == 2:
            true_expr, true_vals = as01(a, a_vals, p), [0, 1]
        elif a01 and not p01 and len(p_vals) == 2:
            pred_expr, pred_vals = as01(p, p_vals, a), [0, 1]
        elif len(a_vals) == 2 and len(p_vals) == 2 and not prob:
            true_expr, pred_expr = as01(a, a_vals, p), as01(p, p_vals, a)
            true_vals = pred_vals = [0, 1]
        else:
            what = "yes/no predictions (0 or 1)" if prob else f"the classes {class_list(p_vals)}"
            c.fail(f"'{a}' ({class_list(a_vals)}) and '{p}' ({what}) have no class in common, so every row "
                   "would count as wrong. Pick a predicted column that uses the same classes as the actual column.")
    c.add(f"y_true = {true_expr}")
    if prob:
        thr = float(o["threshold"])
        c.add(f"y_pred = (df[{lit(p)}] >= {lit(thr)}).astype(int)  # probability -> class (threshold {thr})")
        c.note(f"'{p}' looks like a probability, so predictions are '{p} >= {thr}' (change 'Threshold').")
    else:
        c.add(f"y_pred = {pred_expr}")
    c.add("labels = pd.Index(y_true.unique()).union(y_pred.unique())  # every class seen")
    c.add("cm = pd.crosstab(y_true, y_pred).reindex(index=labels, columns=labels, fill_value=0)")
    c.add("accuracy = (y_true == y_pred).mean()")
    norm = o["normalize"]
    fmt, label = "d", "rows"
    if norm == "true":
        c.add("cm = cm.div(cm.sum(axis=1), axis=0)  # each row sums to 1 (recall per class on the diagonal)")
        fmt, label = ".1%", "share of actual class"
    elif norm == "pred":
        c.add("cm = cm.div(cm.sum(axis=0), axis=1)  # each column sums to 1 (precision per class on the diagonal)")
        fmt, label = ".1%", "share of predicted class"
    elif norm == "all":
        c.add("cm = cm / cm.to_numpy().sum()")
        fmt, label = ".1%", "share of all rows"
    names = sorted({str(v) for v in list(true_vals) + list(pred_vals)}) or ["?"]
    side = round(min(14.0, 4.5 + 0.55 * len(names)), 1)
    chars = len(f"{len(c.df):d}") if fmt == "d" else 6          # '1234' or '100.0%'
    normal_pt = ANNOT_PT * c.text_scale
    fit = heat_fit(names, names, side + 1, side, square=True, scale=c.text_scale, annot_chars=chars, axis_names=True)
    size = c.annot_size(fit, "yes", normal_pt)
    c.heat_title(fit, Raw("f'Confusion matrix · accuracy {accuracy:.1%}'"))
    c.fig_ax(fit.w, fit.h, layout="compressed")
    every = max(fit.every_x, fit.every_y)
    c.add(call("sns.heatmap", Raw("cm"), annot=True, fmt=fmt, annot_kws={"size": size} if size else OMIT,
               cmap=o["cmap"], square=True, linewidths=0.5, xticklabels=every if every > 1 else OMIT,
               yticklabels=every if every > 1 else OMIT, cbar_kws={"label": label}, ax=Raw("ax")))
    c.add("ax.grid(False)")
    c.heat_ticks(fit, "class")
    c.title_room = fit.title_room
    c.xlabel, c.ylabel = f"Predicted ({p})", f"Actual ({a})"


def b_roc(c: Ctx):
    a = c.sel["actual"]
    scores = [s for s in c.sel["scores"] if s != a]
    if not scores:
        c.fail("Pick at least one score / probability column.")
    curve = c.o["curve"]
    if curve in ("roc", "both"):
        c.need("from sklearn.metrics import roc_auc_score, roc_curve")
    if curve in ("pr", "both"):
        c.need("from sklearn.metrics import average_precision_score, precision_recall_curve")
    c.binary_target(a, c.o["positive"])
    cols = c.cols(scores)
    if curve == "both":
        c.add("fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14.0, 6.5), layout='constrained')")
        c.mode = "multi"
    else:
        c.fig_ax(7.5, 6.5)
    if curve in ("roc", "both"):
        c.add(f"for col in {cols}:")
        c.add("fpr, tpr, _ = roc_curve(y_true, df[col])", 1)
        c.add("ax.plot(fpr, tpr, label=f'{col}  (AUC = {roc_auc_score(y_true, df[col]):.3f})')", 1)
        c.add("ax.plot([0, 1], [0, 1], linestyle='--', color='gray', linewidth=1, label='random guess')")
        c.add("ax.set(xlabel='False positive rate', ylabel='True positive rate (recall)', xlim=(-0.01, 1.01),\n"
              "       ylim=(-0.01, 1.01))")
        c.add("ax.legend(loc='lower right')")
        if curve == "both":
            c.add("ax.set_title('ROC curve')")
        c.title = "ROC curve"
    if curve in ("pr", "both"):
        pax = "ax2" if curve == "both" else "ax"
        c.add(f"for col in {cols}:")
        c.add("precision, recall, _ = precision_recall_curve(y_true, df[col])", 1)
        c.add(f"{pax}.plot(recall, precision, label=f'{{col}}  (AP = {{average_precision_score(y_true, df[col]):.3f}})')", 1)
        c.add(f"{pax}.axhline(y_true.mean(), linestyle='--', color='gray', linewidth=1, label=f'baseline ({{y_true.mean():.2f}})')")
        c.add(f"{pax}.set(xlabel='Recall', ylabel='Precision', xlim=(-0.01, 1.01), ylim=(-0.01, 1.01))")
        c.add(f"{pax}.legend(loc='lower left')")
        if curve == "both":
            c.add("ax2.set_title('Precision–recall curve')")
            c.title = "ROC and precision–recall curves"
        else:
            c.title = "Precision–recall curve"


def b_images(c: Ctx):
    pix = list(c.sel["pixels"])
    label = c.sel.get("label")
    if label in pix:
        pix.remove(label)
    npix = len(pix)
    if npix < 4:
        c.fail("Pick the pixel columns (at least 4), e.g. pixel0 … pixel783 for 28×28 images.")
    width = int(c.o["width"])
    if width > npix:
        c.fail(f"Image width {width} is larger than the number of pixel columns ({npix}).")
    if width > 0:
        height = npix // width
    else:
        side = math.isqrt(npix)
        if side * side == npix:
            width = height = side
        else:
            d = max(k for k in range(1, side + 1) if npix % k == 0)
            width, height = npix // d, d
    if width * height < npix:
        c.note(f"{npix} pixels don't fill a {width}×{height} image; the extra pixels are ignored.")
    n = min(int(c.o["count"]), len(c.df))
    ncols = max(2, math.ceil(math.sqrt(n)))
    nrows = max(1, math.ceil(n / ncols))
    c.add(f"pixel_cols = {c.cols(pix)}")
    c.add("images = df[pixel_cols].to_numpy(dtype=float)  # one row = one image")
    c.add(f"width, height = {width}, {height}")
    c.add(f"fig, axes = plt.subplots({nrows}, {ncols}, figsize=({round(1.7 * ncols, 1)}, "
          f"{round(1.85 * nrows + 0.4, 1)}), layout='constrained')")
    c.add("for i, ax in enumerate(axes.flat):")
    c.add("ax.axis('off')", 1)
    c.add(f"if i < {n}:", 1)
    c.add(f"ax.imshow(images[i, :width * height].reshape(height, width), cmap={lit(c.o['cmap'])})", 2)
    if label:
        c.add(f"ax.set_title(str(df[{lit(label)}].iloc[i]), fontsize=10)", 2)
    c.mode = "multi"
    c.title = f"First {n} images ({width}×{height} pixels)"


# --------------------------------------------------------------------------- #
# 3D & CONTOURS
# --------------------------------------------------------------------------- #

def _grid_code(c: Ctx, x, y, z) -> bool:
    """If (x, y) form a full grid, write code that builds X, Y, Z matrices."""
    nx, ny = c.nunique(x), c.nunique(y)
    pairs = len(c.df[[x, y]].drop_duplicates())
    if nx >= 2 and ny >= 2 and pairs == nx * ny and nx * ny <= 250_000:
        c.add(f"grid = df.pivot_table(index={lit(y)}, columns={lit(x)}, values={lit(z)})  # rows = y, columns = x")
        c.add("X, Y = np.meshgrid(grid.columns, grid.index)")
        c.add("Z = grid.to_numpy()")
        return True
    return False


def b_contour(c: Ctx):
    x, y, z = c.sel["x"], c.sel["y"], c.sel["z"]
    o = c.o
    style, levels, cmap = o["style"], int(o["levels"]), o["cmap"]
    grid = _grid_code(c, x, y, z)
    if grid:
        X, Y, Z, pre = "X", "Y", "Z", ""
    else:
        X, Y, Z, pre = f"df[{lit(x)}]", f"df[{lit(y)}]", f"df[{lit(z)}]", "tri"
        c.note("The points are not on a regular grid, so matplotlib's triangulated contours (tricontour) are used.")
        if style == "image":
            c.note("'Image' needs grid data; filled contours are used instead.")
            style = "filled"
    c.fig_ax(9.5, 7)
    if style in ("filled", "filled_lines"):
        c.add(f"filled = ax.{pre}contourf({X}, {Y}, {Z}, levels={levels}, cmap={lit(cmap)})")
        c.add(f"fig.colorbar(filled, ax=ax, label={lit(z)})")
    if style == "image":
        # one coloured cell centred on each grid point (also right when the grid is not evenly spaced)
        c.add(f"image = ax.pcolormesh(X, Y, Z, shading='nearest', cmap={lit(cmap)})")
        c.add(f"fig.colorbar(image, ax=ax, label={lit(z)})")
        c.add("ax.grid(False)  # no grid lines over the picture")
    if style in ("lines", "filled_lines", "image"):
        how = f"cmap={lit(cmap)}" if style == "lines" else "colors='black', linewidths=0.6"
        c.add(f"lines = ax.{pre}contour({X}, {Y}, {Z}, levels={levels}, {how})")
        if style == "lines":
            c.add(f"fig.colorbar(lines, ax=ax, label={lit(z)})")
        if o["clabel"]:
            c.add("ax.clabel(lines, inline=True, fontsize=8)  # numbers on the lines")
    elif o["clabel"]:
        c.note("Contour labels need contour lines (style 'lines' or 'filled + lines').")
    if o["points"]:
        c.add(f"ax.plot(df[{lit(x)}], df[{lit(y)}], 'k.', markersize=3, alpha=0.5)  # the data points")
    c.xlabel, c.ylabel = x, y
    c.title = f"{z} over {x} and {y}"


def _ax3d(c: Ctx):
    c.add("fig = plt.figure(figsize=(9.5, 7.5), layout='constrained')")
    c.add("ax = fig.add_subplot(projection='3d')")
    c.mode = "single3d"


def b_scatter3d(c: Ctx):
    x, y, z = c.sel["x"], c.sel["y"], c.sel["z"]
    color = c.sel.get("color")
    o = c.o
    mode = o["mode"]
    _ax3d(c)
    cols = f"df[{lit(x)}], df[{lit(y)}], df[{lit(z)}]"
    if mode in ("points", "both"):
        if color and c.is_continuous(color):
            c.add(f"points = ax.scatter({cols}, c=df[{lit(color)}], cmap={lit(o['cmap'])}, "
                  f"s={int(o['size'])}, alpha={lit(o['alpha'])})")
            c.add(f"fig.colorbar(points, ax=ax, shrink=0.6, pad=0.1, label={lit(color)})")
        elif color:
            c.group("color", convert=False)
            c.add(f"for name, group in df.groupby({lit(color)}):")
            c.add(f"ax.scatter(group[{lit(x)}], group[{lit(y)}], group[{lit(z)}], s={int(o['size'])}, "
                  f"alpha={lit(o['alpha'])}, label=str(name))", 1)
            c.add(f"ax.legend(title={lit(color)})")
        else:
            c.add(f"ax.scatter({cols}, s={int(o['size'])}, alpha={lit(o['alpha'])})")
    if mode in ("line", "both"):
        c.add(f"ax.plot({cols}, color='gray', linewidth=1)  # points joined in row order")
    c.add(f"ax.set(xlabel={lit(x)}, ylabel={lit(y)}, zlabel={lit(z)})")
    c.add(f"ax.view_init(elev={int(o['elev'])}, azim={int(o['azim'])})  # camera angle; drag to rotate")
    c.title = f"{z} vs {x} and {y}"


def b_surface3d(c: Ctx):
    x, y, z = c.sel["x"], c.sel["y"], c.sel["z"]
    o = c.o
    kind, cmap = o["kind"], o["cmap"]
    grid = kind != "trisurf" and _grid_code(c, x, y, z)
    _ax3d(c)
    if grid and kind == "surface":
        c.add(f"surface = ax.plot_surface(X, Y, Z, cmap={lit(cmap)}, edgecolor='none')")
        c.add(f"fig.colorbar(surface, ax=ax, shrink=0.6, pad=0.1, label={lit(z)})")
    elif grid and kind == "wireframe":
        c.add("ax.plot_wireframe(X, Y, Z, color='C0', linewidth=0.6)")
    else:
        if kind != "trisurf":
            c.note("The points are not on a regular grid, so a triangulated surface (plot_trisurf) is drawn.")
        c.add(f"surface = ax.plot_trisurf(df[{lit(x)}], df[{lit(y)}], df[{lit(z)}], cmap={lit(cmap)}, linewidth=0.1)")
        c.add(f"fig.colorbar(surface, ax=ax, shrink=0.6, pad=0.1, label={lit(z)})")
    c.add(f"ax.set(xlabel={lit(x)}, ylabel={lit(y)}, zlabel={lit(z)})")
    c.add(f"ax.view_init(elev={int(o['elev'])}, azim={int(o['azim'])})  # camera angle; drag to rotate")
    c.title = f"Surface of {z}"


# --------------------------------------------------------------------------- #
# MULTI-PANEL
# --------------------------------------------------------------------------- #

def b_facet(c: Ctx):
    x, y = c.sel["x"], c.sel.get("y")
    colf, rowf = c.sel["col"], c.sel.get("row")
    o = c.o
    kind = o["kind"]
    if kind == "auto":
        kind = "scatter" if y else "hist"
    if kind in ("scatter", "line", "reg") and not y:
        c.fail(f"'{kind}' facets need a Y column.")
    if kind in ("hist", "kde", "ecdf") and y:
        c.note(f"'{kind}' facets use only the X column; Y is ignored.")
    if rowf and rowf == colf:
        c.fail("Use different columns for facet columns and facet rows.")
    for f in filter(None, (colf, rowf)):
        c.group("col" if f == colf else "row", limit=10_000, convert=False)
        c.limit_categories(f, 12)
    hue = c.group("hue")
    wrap = int(o["wrap"])
    kw = dict(col=colf, row=rowf or OMIT, hue=hue or OMIT,
              col_wrap=wrap if (not rowf and c.nunique(colf) > wrap) else OMIT,
              height=float(o["height"]), margin_titles=True if rowf else OMIT,
              sharex=OMIT if o["share"] else False, sharey=OMIT if o["share"] else False)
    c.add("g = " + call("sns.FacetGrid", Raw("df"), **kw))
    funcs = {
        "hist": call("g.map_dataframe", Raw("sns.histplot"), x=x, bins=int(o["bins"]) if int(o["bins"]) > 0 else OMIT),
        "kde": call("g.map_dataframe", Raw("sns.kdeplot"), x=x, fill=True),
        "ecdf": call("g.map_dataframe", Raw("sns.ecdfplot"), x=x),
        "scatter": call("g.map_dataframe", Raw("sns.scatterplot"), x=x, y=y, alpha=0.7, s=20),
        "line": call("g.map_dataframe", Raw("sns.lineplot"), x=x, y=y, errorbar=None),
        "reg": call("g.map_dataframe", Raw("sns.regplot"), x=x, y=y, scatter_kws={"alpha": 0.5, "s": 15}),
    }
    c.add(funcs[kind] + "  # draw the same plot in every panel")
    if hue:
        c.add("g.add_legend()")
    c.add("fig = g.figure")
    ncols = c.nunique(colf) if rowf else min(c.nunique(colf), wrap)
    c.fig_w = float(o["height"]) * ncols + (1.0 if hue else 0.0)
    c.mode = "figure"
    c.title = f"{x}" + (f" vs {y}" if y and kind not in ('hist', 'kde', 'ecdf') else "") + f" by {colf}" + (f" and {rowf}" if rowf else "")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def R(*a, **k):
    return Role(*a, **k)


def O(*a, **k):
    return Option(*a, **k)


HUE = lambda auto=False: R("hue", "Colour by", "cat", required=False, auto=auto,
                           hint="optional · split into coloured groups", prefer="target")
CAT_ROLES = [
    R("y", "Values", "num", multi=True, hint="number column(s)", prefer="features", max_default=1),
    R("x", "Group by", "cat", required=False, hint="optional · one box per group", prefer="nontarget", auto=True),
    HUE(),
]
TOP_GROUPS = O("top_n", "Max groups", "int", 20, min=2, max=200, hint="most common groups shown")


def _heavy(n):
    return lambda o: n


GRAPHS = [
    # ---------------- Basic charts ----------------
    GraphType(
        "line", "Line plot", "Basic charts", "Trends over time or order; great for training curves.",
        [R("x", "X axis", "any", required=False, auto=True, hint="optional · empty = row number", prefer="ordered"),
         R("y", "Y axis", "num", multi=True, hint="one or more number columns", prefer="features", max_default=2),
         HUE()],
        [O("marker", "Marker", "choice", "", MARKERS), O("linestyle", "Line style", "choice", "-", LINESTYLES),
         O("linewidth", "Line width", "float", 1.4, min=0.4, max=6, step=0.2),
         O("rolling", "Smooth (rolling mean)", "int", 0, min=0, max=500, hint="0 = off; e.g. 5 averages 5 points"),
         O("show_raw", "Show raw line behind smoothed", "bool", True),
         O("sort_x", "Sort by X", "bool", True),
         O("band", "Show 95% CI band (repeated X)", "bool", False, show_if=_has("hue"))],
        b_line, book="PDSH p.224 · Simple line plots"),
    GraphType(
        "scatter", "Scatter / bubble", "Basic charts", "Two numbers against each other; colour and size add more.",
        [R("x", "X axis", "num", prefer="continuous"), R("y", "Y axis", "num", prefer="continuous"),
         R("color", "Colour by", "num_cat", required=False, hint="optional · numbers get a colormap, categories get colours",
           prefer="target"),
         R("size", "Size by", "num", required=False, hint="optional · bubble size")],
        [O("alpha", "Transparency (alpha)", "float", 0.7, min=0.05, max=1, step=0.05),
         O("size", "Point size", "int", 30, min=1, max=400), O("marker", "Marker", "choice", "o", MARKERS[1:]),
         O("cmap", "Colormap (number colour)", "choice", "viridis", ch(*CMAPS_ALL))],
        b_scatter, book="PDSH p.233 · Scatter plots", heavy=_heavy(200_000)),
    GraphType(
        "bar", "Bar chart", "Basic charts", "Compare an average / total across categories.",
        [R("x", "Category", "cat", prefer="nontarget"), R("y", "Value", "num", prefer="continuous"), HUE()],
        [O("estimator", "Bar height", "choice", "mean", ch("mean", "median", "sum", "min", "max", "std")),
         O("errorbar", "Error bars", "choice", "none",
           ch(("none", "none"), ("ci", "95% confidence interval"), ("sd", "standard deviation"), ("se", "standard error"))),
         ORIENT,
         O("sort", "Order", "choice", "desc", ch(("desc", "largest first"), ("asc", "smallest first"),
                                                 ("name", "by name"), ("data", "as in data"))),
         O("top_n", "Max bars", "int", 30, min=2, max=300),
         O("values", "Write values on bars", "bool", False)],
        b_bar, book="seaborn barplot · PDSH p.319"),
    GraphType(
        "area", "Area / stacked area", "Basic charts", "How parts add up to a total over time.",
        [R("x", "X axis", "any", required=False, auto=True, hint="optional · empty = row number", prefer="ordered"),
         R("y", "Areas", "num", multi=True, hint="one or more number columns", prefer="features", max_default=3)],
        [O("stacked", "Stack areas", "bool", True), O("alpha", "Opacity", "float", 0.75, min=0.1, max=1, step=0.05),
         O("sort_x", "Sort by X", "bool", True)],
        b_area, book="matplotlib stackplot / fill_between"),
    GraphType(
        "pie", "Pie / donut", "Basic charts", "Share of each category in the whole.",
        [R("labels", "Slices", "cat", prefer="target"),
         R("values", "Slice size", "num", required=False, hint="optional · empty = count rows")],
        [O("donut", "Donut (hole in the middle)", "bool", False), O("percent", "Show percentages", "bool", True),
         O("top_n", "Max slices", "int", 8, min=2, max=30, hint="the rest becomes 'Other'")],
        b_pie, log_axes=False, limits=False, book="matplotlib ax.pie"),
    GraphType(
        "errorbar", "Error bars", "Basic charts", "Mean ± spread per group, or values ± your error column.",
        [R("x", "X axis", "any", prefer="nontarget"), R("y", "Y axis", "num", prefer="continuous"),
         R("err", "Error column", "num", required=False, hint="optional · empty = compute from groups")],
        [O("spread", "Spread (computed)", "choice", "std",
           ch(("std", "standard deviation"), ("sem", "standard error"), ("ci95", "95% confidence interval")),
           show_if=lambda s: not s.get("err")),
         O("style", "Style", "choice", "bars", ch(("bars", "error bars"), ("band", "shaded band (fill_between)"))),
         O("marker", "Marker", "choice", "o", MARKERS), O("connect", "Connect points with a line", "bool", True),
         O("capsize", "Cap size", "int", 4, min=0, max=20)],
        b_errorbar, book="PDSH p.237 · Visualizing errors"),
    # ---------------- Distributions ----------------
    GraphType(
        "hist", "Histogram", "Distributions", "How values are spread: skew, outliers, peaks.",
        [R("cols", "Columns", "num", multi=True, hint="one or more number columns", prefer="features", max_default=1),
         HUE()],
        [O("bins", "Bins", "int", 0, min=0, max=500, hint="0 = automatic"),
         O("stat", "Height shows", "choice", "count", ch("count", "density", "probability", "percent")),
         O("element", "Draw as", "choice", "bars", ch(("bars", "bars"), ("step", "step outline"), ("poly", "polygon"))),
         O("kde", "Add KDE curve", "bool", False), O("cumulative", "Cumulative", "bool", False),
         O("multiple", "Groups", "choice", "layer", ch("layer", "stack", "dodge", "fill"), show_if=_has("hue")),
         LAYOUT],
        b_hist, book="PDSH p.245 · Histograms, binnings, density", heavy=_heavy(2_000_000)),
    GraphType(
        "kde", "Density (KDE)", "Distributions", "A smooth version of the histogram.",
        [R("cols", "Columns", "num", multi=True, hint="one or more number columns", prefer="features", max_default=1),
         HUE()],
        [O("fill", "Fill under the curve", "bool", True),
         O("bw_adjust", "Smoothness (bw_adjust)", "float", 1.0, min=0.1, max=5, step=0.1, hint="<1 = bumpier"),
         O("cumulative", "Cumulative", "bool", False),
         O("multiple", "Groups", "choice", "layer", ch("layer", "stack", "fill"), show_if=_has("hue")),
         O("common_norm", "Groups share one total area", "bool", True, show_if=_has("hue")),
         O("layout", "Several columns", "choice", "overlay",
           ch(("overlay", "overlay in one plot"), ("panels", "one panel each")), show_if=_many("cols"))],
        b_kde, book="PDSH p.248 & p.313 · KDE", heavy=_heavy(300_000)),
    GraphType(
        "box", "Box plot", "Distributions", "Median, quartiles and outliers, per group.",
        CAT_ROLES,
        [O("outliers", "Show outliers", "bool", True), O("notch", "Notched boxes", "bool", False),
         O("points", "Overlay the data points", "bool", False), ORIENT, TOP_GROUPS,
         O("scale", "Several columns: scale", "choice", "raw",
           ch(("raw", "raw values"), ("z", "standardise (z-score)"), ("minmax", "min-max 0..1")),
           show_if=lambda s: _many("y")(s) and not s.get("x"))],
        b_box, book="PDSH p.318 · catplot(kind='box')"),
    GraphType(
        "violin", "Violin plot", "Distributions", "Box plot + density shape, per group.",
        CAT_ROLES,
        [O("inner", "Inside", "choice", "box", ch("box", "quartile", "point", "stick", "none")),
         O("split", "Split halves by colour (2 groups)", "bool", False, show_if=_has("hue")),
         O("trim", "Trim to data range", "bool", False), ORIENT, TOP_GROUPS,
         O("scale", "Several columns: scale", "choice", "raw",
           ch(("raw", "raw values"), ("z", "standardise (z-score)"), ("minmax", "min-max 0..1")),
           show_if=lambda s: _many("y")(s) and not s.get("x"))],
        b_violin, book="PDSH p.319 · violinplot",
        heavy=lambda o: 5000 if o.get("inner") in ("stick", "point") else 100_000),
    GraphType(
        "strip", "Strip / swarm", "Distributions", "Every point, spread out by group.",
        CAT_ROLES,
        [O("kind", "Kind", "choice", "strip", ch(("strip", "strip (jittered)"), ("swarm", "swarm (no overlap)"))),
         O("jitter", "Jitter", "bool", True), O("size", "Point size", "float", 4, min=1, max=15, step=0.5),
         O("alpha", "Transparency", "float", 0.7, min=0.05, max=1, step=0.05),
         O("dodge", "Separate colours side by side", "bool", True, show_if=_has("hue")), ORIENT, TOP_GROUPS,
         O("scale", "Several columns: scale", "choice", "raw",
           ch(("raw", "raw values"), ("z", "standardise (z-score)"), ("minmax", "min-max 0..1")),
           show_if=lambda s: _many("y")(s) and not s.get("x"))],
        b_strip, book="PDSH p.318 · catplot(kind='strip'/'swarm')",
        heavy=lambda o: 1500 if o.get("kind") == "swarm" else 20_000),
    GraphType(
        "ecdf", "ECDF (cumulative)", "Distributions", "Share of values at or below x; compares groups without bins.",
        [R("cols", "Columns", "num", multi=True, hint="one or more number columns", prefer="features", max_default=1),
         HUE()],
        [O("stat", "Y axis", "choice", "proportion", ch("proportion", "count")),
         O("complementary", "Complementary (1 - ECDF)", "bool", False),
         O("layout", "Several columns", "choice", "overlay",
           ch(("overlay", "overlay in one plot"), ("panels", "one panel each")), show_if=_many("cols"))],
        b_ecdf, book="Think Stats ch.4 · CDFs"),
    GraphType(
        "qq", "Q-Q plot (normality)", "Distributions", "Is this column normally distributed?",
        [R("cols", "Columns", "num", multi=True, hint="one or more number columns", prefer="features", max_default=1)],
        [O("standardize", "Use z-scores (reference y = x)", "bool", False)],
        b_qq, book="Think Stats ch.5 · normal probability plot"),
    # ---------------- Relationships ----------------
    GraphType(
        "regression", "Regression fit", "Relationships", "Scatter + fitted line, R², residuals.",
        [R("x", "X (feature)", "num", prefer="continuous"), R("y", "Y (target)", "num", prefer="numtarget"),
         R("hue", "Fit per group", "cat", required=False, hint="optional · one line per group")],
        [O("order", "Polynomial degree", "int", 1, min=1, max=6),
         O("ci", "95% confidence band", "bool", True),
         O("show", "Show", "choice", "fit", ch(("fit", "fit"), ("resid", "residuals"), ("both", "fit + residuals"))),
         O("equation", "Write equation and R²", "bool", True, show_if=lambda s: not s.get("hue")),
         O("alpha", "Point transparency", "float", 0.5, min=0.05, max=1, step=0.05),
         O("size", "Point size", "int", 20, min=1, max=200)],
        b_regression, book="PDSH p.319 · regplot / jointplot(kind='reg')",
        heavy=lambda o: 5000 if o.get("ci") else 100_000, min_rows=3),
    GraphType(
        "joint", "Joint plot", "Relationships", "Scatter in the middle, distributions on the edges.",
        [R("x", "X axis", "num", prefer="continuous"), R("y", "Y axis", "num", prefer="continuous"), HUE()],
        [O("kind", "Kind", "choice", "scatter", ch("scatter", "kde", "hist", "hex", "reg", "resid")),
         O("height", "Size (inches)", "float", 7, min=3, max=14, step=0.5)],
        b_joint, book="PDSH p.315 · jointplot", log_axes=False,
        heavy=lambda o: {"kde": 4000, "reg": 5000, "resid": 5000}.get(o.get("kind"), 100_000), min_rows=3),
    GraphType(
        "hexbin", "Hexbin / 2D histogram", "Relationships", "Point density when a scatter is a solid blob.",
        [R("x", "X axis", "num", prefer="continuous"), R("y", "Y axis", "num", prefer="continuous")],
        [O("kind", "Bins", "choice", "hex", ch(("hex", "hexagons (hexbin)"), ("square", "squares (hist2d)"))),
         O("gridsize", "Grid size", "int", 30, min=5, max=200), O("cmap", "Colormap", "choice", "Blues", ch(*CMAPS_SEQ)),
         O("log", "Log colour scale", "bool", False)],
        b_hexbin, book="PDSH p.247 · hist2d & hexbin"),
    GraphType(
        "kde2d", "2D density contours", "Relationships", "Smooth density hills of two numbers.",
        [R("x", "X axis", "num", prefer="continuous"), R("y", "Y axis", "num", prefer="continuous"), HUE()],
        [O("fill", "Filled", "bool", True), O("levels", "Levels", "int", 10, min=2, max=40),
         O("thresh", "Hide lowest density (thresh)", "float", 0.05, min=0, max=0.9, step=0.05),
         O("bw_adjust", "Smoothness (bw_adjust)", "float", 1.0, min=0.1, max=5, step=0.1),
         O("cmap", "Colormap", "choice", "Blues", ch(*CMAPS_SEQ), show_if=lambda s: not s.get("hue")),
         O("points", "Show the points", "bool", False)],
        b_kde2d, book="PDSH p.248 & p.315 · 2D KDE", heavy=_heavy(3000), min_rows=3),
    GraphType(
        "pairplot", "Pair plot", "Relationships", "Every column against every other: the first look at a dataset.",
        [R("cols", "Columns", "num", multi=True, min_count=2, hint="2–12 number columns", prefer="features",
           max_default=5),
         HUE(auto=True)],
        [O("kind", "Off-diagonal", "choice", "scatter", ch("scatter", "kde", "hist", "reg")),
         O("diag", "Diagonal", "choice", "auto", ch("auto", "hist", "kde")),
         O("corner", "Only lower triangle (corner)", "bool", False),
         O("height", "Panel size (inches)", "float", 2.5, min=1.2, max=5, step=0.1)],
        b_pairplot, book="PDSH p.316 · pairplot", log_axes=False,
        heavy=lambda o: {"kde": 600, "reg": 2000, "hist": 100_000}.get(o.get("kind"), 3000), min_rows=3),
    # ---------------- ML & matrices ----------------
    GraphType(
        "corr", "Correlation heatmap", "ML & matrices", "How strongly each pair of numeric columns moves together.",
        [R("cols", "Columns", "num", multi=True, min_count=2, hint="number columns", prefer="all_numeric",
           max_default=30)],
        [O("method", "Method", "choice", "pearson", ch("pearson", "spearman", "kendall")),
         O("annot", "Numbers in cells", "choice", "auto", ch("auto", "yes", "no")),
         O("triangle", "Hide upper triangle", "bool", True),
         O("cmap", "Colormap", "choice", "coolwarm", ch(*CMAPS_DIV)),
         O("decimals", "Decimals", "int", 2, min=0, max=4)],
        b_corr, book="PDSH p.329 extra · sns.heatmap(corr)", log_axes=False, limits=False, min_rows=3),
    GraphType(
        "target_corr", "Correlation with target", "ML & matrices", "Rank features by correlation with what you predict.",
        [R("target", "Target", "any", hint="number column or 2-class column", prefer="numtarget"),
         R("features", "Features", "num", multi=True, hint="number columns", prefer="all_numeric", max_default=60)],
        [O("method", "Method", "choice", "pearson", ch("pearson", "spearman")),
         O("sort", "Order", "choice", "abs", ch(("abs", "strongest (either sign) first"), ("value", "highest to lowest"))),
         O("top_n", "Max features", "int", 20, min=2, max=200)],
        b_target_corr, book="Feature screening for ML", log_axes=False, limits=False, min_rows=3),
    GraphType(
        "count", "Count plot (class balance)", "ML & matrices", "How many rows per category, e.g. per target class.",
        [R("col", "Category", "cat", prefer="target"), HUE()],
        [O("labels", "Labels on bars", "choice", "both",
           ch(("both", "count (percent)"), ("count", "count"), ("percent", "percent"), ("none", "none"))),
         O("order", "Order", "choice", "count", ch(("count", "most common first"), ("name", "by name"))),
         O("orient", "Orientation", "choice", "auto", ch("auto", "vertical", "horizontal")),
         O("top_n", "Max categories", "int", 30, min=2, max=300)],
        b_count, book="PDSH p.319 · countplot", log_axes=False),
    GraphType(
        "missing", "Missing values map", "ML & matrices", "Which columns have gaps, how many, and where.",
        [R("cols", "Columns", "all", multi=True, hint="columns to check", prefer="all", max_default=10_000)],
        [O("view", "Show", "choice", "both", ch(("both", "bar chart + map"), ("bar", "bar chart"), ("map", "map"))),
         O("only_missing", "Only columns with gaps", "bool", True),
         O("sort", "Most missing first", "bool", True)],
        b_missing, log_axes=False, limits=False, dropna=False, book="Data cleaning for ML"),
    GraphType(
        "pivot", "Pivot heatmap", "ML & matrices", "A value (mean, sum, count) for every pair of two categories.",
        [R("rows", "Rows", "cat", prefer="nontarget"), R("cols", "Columns", "cat", prefer="nontarget"),
         R("value", "Value", "num", required=False, hint="optional · empty = count rows")],
        [O("agg", "Aggregate", "choice", "mean", ch("mean", "median", "sum", "min", "max", "count")),
         O("annot", "Numbers in cells", "choice", "auto", ch("auto", "yes", "no")),
         O("cmap", "Colormap", "choice", "YlGnBu", ch(*CMAPS_ALL)),
         O("decimals", "Decimals", "int", 1, min=0, max=4), O("top_n", "Max categories per side", "int", 30, min=2, max=200)],
        b_pivot, book="PDSH p.319 · heatmap of a pivot table", log_axes=False, limits=False),
    GraphType(
        "confusion", "Confusion matrix", "ML & matrices", "Actual vs predicted classes, with accuracy.",
        [R("actual", "Actual (true) class", "cat", prefer="target"),
         R("predicted", "Predicted class or probability", "any", prefer="pred")],
        [O("normalize", "Show", "choice", "none",
           ch(("none", "counts"), ("true", "share of each actual class"), ("pred", "share of each predicted class"),
              ("all", "share of all rows"))),
         O("threshold", "Threshold (for probabilities)", "float", 0.5, min=0.01, max=0.99, step=0.05),
         O("cmap", "Colormap", "choice", "Blues", ch(*CMAPS_SEQ))],
        b_confusion, log_axes=False, limits=False, book="Model evaluation"),
    GraphType(
        "roc", "ROC / PR curve", "ML & matrices", "Ranking quality of predicted probabilities (AUC).",
        [R("actual", "Actual class (2 values)", "binary", prefer="target"),
         R("scores", "Predicted probabilities", "num", multi=True, hint="one column per model", prefer="proba",
           max_default=4)],
        [O("curve", "Curve", "choice", "roc", ch(("roc", "ROC"), ("pr", "precision–recall"), ("both", "both"))),
         O("positive", "Positive class", "text", "auto", hint="'auto' = 1 / True / yes")],
        b_roc, log_axes=False, book="Model evaluation · needs scikit-learn"),
    GraphType(
        "images", "Image grid (pixel rows)", "ML & matrices", "Draw rows of pixel columns as pictures (MNIST style).",
        [R("pixels", "Pixel columns", "num", multi=True, min_count=4, hint="e.g. pixel0 … pixel783", prefer="pixels",
           max_default=100_000),
         R("label", "Title from", "any", required=False, auto=True, hint="optional · e.g. label", prefer="label")],
        [O("count", "Images", "int", 25, min=1, max=100), O("width", "Image width (pixels)", "int", 0, min=0, max=2000,
                                                           hint="0 = automatic (square)"),
         O("cmap", "Colormap", "choice", "gray_r", ch("gray_r", "gray", "binary", "viridis", "magma"))],
        b_images, log_axes=False, dropna=False, book="PDSH ch.5 · digits"),
    # ---------------- 3D & contours ----------------
    GraphType(
        "contour", "Contour plot", "3D & contours", "z over an (x, y) map: filled contours, lines or image.",
        [R("x", "X", "num", prefer="continuous"), R("y", "Y", "num", prefer="continuous"),
         R("z", "Z (height / colour)", "num", prefer="continuous")],
        [O("style", "Style", "choice", "filled",
           ch(("filled", "filled contours"), ("lines", "contour lines"), ("filled_lines", "filled + lines"),
              ("image", "image (imshow, grid data)"))),
         O("levels", "Levels", "int", 15, min=2, max=100), O("cmap", "Colormap", "choice", "viridis", ch(*CMAPS_ALL)),
         O("clabel", "Numbers on lines (clabel)", "bool", False), O("points", "Show data points", "bool", False)],
        b_contour, book="PDSH p.241 · Density and contour plots", min_rows=3),
    GraphType(
        "scatter3d", "3D scatter / line", "3D & contours", "Three numbers at once; drag to rotate.",
        [R("x", "X", "num", prefer="continuous"), R("y", "Y", "num", prefer="continuous"),
         R("z", "Z", "num", prefer="continuous"),
         R("color", "Colour by", "num_cat", required=False, hint="optional", prefer="target")],
        [O("mode", "Draw", "choice", "points", ch(("points", "points"), ("line", "line"), ("both", "points + line"))),
         O("size", "Point size", "int", 20, min=1, max=300), O("alpha", "Transparency", "float", 0.8, min=0.05, max=1, step=0.05),
         O("cmap", "Colormap (number colour)", "choice", "viridis", ch(*CMAPS_ALL)),
         O("elev", "Elevation angle", "int", 25, min=-90, max=90, step=5),
         O("azim", "Azimuth angle", "int", -60, min=-180, max=180, step=5)],
        b_scatter3d, book="PDSH p.290 · 3D plotting", log_axes=False, heavy=_heavy(50_000)),
    GraphType(
        "surface3d", "3D surface", "3D & contours", "A surface z = f(x, y): surface, wireframe or triangles.",
        [R("x", "X", "num", prefer="continuous"), R("y", "Y", "num", prefer="continuous"),
         R("z", "Z (height)", "num", prefer="continuous")],
        [O("kind", "Kind", "choice", "surface", ch(("surface", "surface"), ("wireframe", "wireframe"),
                                                   ("trisurf", "triangulated (any points)"))),
         O("cmap", "Colormap", "choice", "viridis", ch(*CMAPS_ALL)),
         O("elev", "Elevation angle", "int", 30, min=-90, max=90, step=5),
         O("azim", "Azimuth angle", "int", -60, min=-180, max=180, step=5)],
        b_surface3d, book="PDSH p.293 · surface & wireframe", log_axes=False, heavy=_heavy(20_000), min_rows=3),
    # ---------------- Multi-panel ----------------
    GraphType(
        "facet", "Facet grid", "Multi-panel", "The same plot repeated for every group (small multiples).",
        [R("x", "X", "num", prefer="continuous"),
         R("y", "Y", "num", required=False, hint="optional · needed for scatter / line / reg"),
         R("col", "Panels across (columns)", "cat", prefer="nontarget"),
         R("row", "Panels down (rows)", "cat", required=False, hint="optional"), HUE()],
        [O("kind", "Plot in each panel", "choice", "auto",
           ch(("auto", "auto (hist, or scatter if Y)"), ("hist", "histogram"), ("kde", "density"), ("ecdf", "ECDF"),
              ("scatter", "scatter"), ("line", "line"), ("reg", "regression"))),
         O("bins", "Bins (histogram)", "int", 0, min=0, max=200, hint="0 = automatic"),
         O("wrap", "Panels per row", "int", 4, min=1, max=10, show_if=lambda s: not s.get("row")),
         O("height", "Panel size (inches)", "float", 3, min=1.5, max=8, step=0.5),
         O("share", "Share axes", "bool", True)],
        b_facet, book="PDSH p.317 · FacetGrid", log_axes=False,
        heavy=lambda o: 3000 if o.get("kind") == "kde" else 200_000),
]

GRAPH_BY_ID = {g.id: g for g in GRAPHS}
CATEGORIES = ["Basic charts", "Distributions", "Relationships", "ML & matrices", "3D & contours", "Multi-panel"]


# --------------------------------------------------------------------------- #
# Which columns fit which role, and automatic suggestions
# --------------------------------------------------------------------------- #

def fits(role: Role, info) -> bool:
    a = role.accepts
    if getattr(info, "relabelled", "") == "skip":        # Column types: skip (Show all still lists it)
        return False
    if info.kind == EMPTY:
        return a == "all"
    if a == "all" or a == "any":
        return True
    if a == "num":
        return info.kind == NUMERIC
    if a == "cat":
        return info.groupable
    if a == "num_cat":
        return info.kind == NUMERIC or info.groupable
    if a == "num_time":
        return info.kind in (NUMERIC, DATETIME)
    if a == "binary":
        return info.unique == 2
    return True


def compatible(role: Role, ds: Dataset, show_all=False) -> list:
    if show_all:
        return [c for c, i in ds.columns.items() if i.kind != EMPTY or role.accepts == "all"]
    return [c for c, i in ds.columns.items() if fits(role, i)]


def suggest(graph: GraphType, ds: Dataset, previous: dict | None = None, show_all=False) -> dict:
    """Pre-fill the column choices with sensible guesses (keeping valid previous choices)."""
    previous = previous or {}
    target = ds.guess_target()
    numtarget = ds.guess_target(numeric_ok=True)
    taken = set()
    out = {}
    cont = [c for c in ds.numeric() if not ds.info(c).is_discrete]

    for role in graph.roles:
        options = compatible(role, ds, show_all=show_all)
        prev = previous.get(role.key)
        if prev == "" and not role.required:          # the user explicitly chose "(none)"
            out[role.key] = [] if role.multi else None
            continue
        if role.multi:
            enough = max(role.min_count, min(role.max_default, 2))  # 1 column from a histogram is too few for a pair plot
            if isinstance(prev, list) and len(prev) >= enough and all(p in options for p in prev):
                out[role.key] = list(prev)
                taken.update(prev)
                continue
        elif prev and prev in options:
            out[role.key] = prev
            taken.add(prev)
            continue
        if not role.required and not role.auto:
            out[role.key] = [] if role.multi else None
            continue
        pick = _pick(role, ds, options, taken, target, numtarget, cont, out)
        out[role.key] = pick
        if pick:
            taken.update(pick if isinstance(pick, list) else [pick])
    return out


def _pick(role, ds, options, taken, target, numtarget, cont, chosen):
    free = [c for c in options if c not in taken and not ds.info(c).is_id]
    p = role.prefer
    if not role.multi:
        # a column named exactly like the role ("x", "y", "z", "label", ...) wins
        for c in options:
            if c not in taken and c.strip().lower() == role.key.lower():
                return c
    if role.multi:
        if p == "all":
            return list(options)
        if p == "pixels":
            label = chosen.get("label") or target
            return [c for c in options if c != label and not ds.info(c).is_id][: role.max_default]
        if p == "proba":
            probs = [c for c in free if c != target and _is_probability(ds, c)]
            named = [c for c in probs if any(w in c.lower() for w in ("prob", "score", "pred", "pr_"))]
            return (named or probs)[: role.max_default]
        avoid = {target, numtarget} if p in ("features", "all_numeric") else set()
        pool = [c for c in free if c not in avoid]
        if p == "features":
            pool = [c for c in pool if c in cont] or pool
        return pool[: role.max_default]
    if not role.required and role.auto and p == "target":
        return target if target in options and target not in taken else None
    if p == "target":
        if target in options and target not in taken:
            return target
        small = [c for c in free if 2 <= ds.info(c).unique <= 12]
        return (small or free or [None])[0]
    if p == "numtarget":
        if numtarget in options and numtarget not in taken:
            return numtarget
        if target in options and target not in taken:
            return target
        p = "continuous"
    if p == "nontarget":
        small = [c for c in free if c != target and 2 <= ds.info(c).unique <= 12]
        rest = [c for c in free if c != target]
        return (small or rest or free or [None])[0]
    if p == "pred":
        named = [c for c in free if "pred" in c.lower() and c != chosen.get("actual")]
        if named:
            return named[0]
        probs = [c for c in free if _is_probability(ds, c) and c != chosen.get("actual")]
        return (probs or [None])[0]
    if p == "label":
        for c in free:
            if c.lower() in ("label", "labels", "target", "class", "digit", "y"):
                return c
        return target if target in options else None
    if p == "continuous":
        pool = [c for c in free if c in cont and c not in (target, numtarget)]
        pool = pool or [c for c in free if c not in (target,)] or free
        return (pool or [None])[0]
    if p == "ordered":
        unused = [c for c in options if c not in taken]
        dates = [c for c in unused if ds.info(c).kind == DATETIME]
        if dates:
            return dates[0]
        words = ("epoch", "step", "time", "date", "year", "iter", "day", "month", "week")
        named = [c for c in unused if any(w in c.lower() for w in words)]
        return named[0] if named else None
    return (free or [None])[0]


def _is_probability(ds, col) -> bool:
    info = ds.info(col)
    if info.kind != NUMERIC or info.is_discrete:
        return False
    s = ds.df[col]
    return bool(s.min() >= 0 and s.max() <= 1)
