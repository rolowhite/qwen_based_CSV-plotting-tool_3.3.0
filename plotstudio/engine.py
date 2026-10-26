"""From the user's choices to code, and from code to a matplotlib Figure.

    build_plot()  writes the code (rows -> style -> plot) without drawing
    run_plot()    executes the plotting part and returns the Figure
    make_plot()   both

The full script shown to the user is the same code plus the CSV-loading lines
and plt.show(), so it runs unchanged in Jupyter, Kaggle or a .py file.
"""
from __future__ import annotations

import re
import time
import traceback
import warnings
from dataclasses import dataclass, field

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import APP_NAME, fonts
from .codegen import LINE_LIMIT, PlotError, Raw, call, clean_comment, cols_expr, commented, lit
from .data import Dataset, RowSettings
from .graphs import Ctx, GraphType
from .limits import zoom_info

PLOT_FILE = "<plot code>"

SEABORN_STYLES = ["whitegrid", "darkgrid", "white", "ticks", "dark"]
PALETTES = ["default", "studio", "deep", "muted", "pastel", "bright", "dark", "colorblind", "Set1", "Set2", "Set3",
            "tab10", "Paired", "husl", "viridis", "rocket", "mako", "flare", "crest", "magma", "Spectral", "coolwarm"]
CONTEXTS = ["paper", "notebook", "talk", "poster"]
CONTEXT_SCALE = {"paper": 0.8, "notebook": 1.0, "talk": 1.5, "poster": 2.0}

# The Studio look: 8 categorical colours in a colour-blind-safe order (checked with a CVD
# simulation: every neighbouring pair stays apart), fine lines, a hairline grid, no box,
# left-aligned bold titles, quiet legends. It builds on seaborn's "white" style, which
# already gives white gaps between bars, round line caps and the grid behind the data.
# Neutral greys only, so the dark graph paper (paper.py) can swap them for light ones.
STUDIO_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
STUDIO_INK = {"text": "#1f1f24", "label": "#4a4a55", "tick": "#5c5c68", "grid": "#e6e6eb", "spine": "#c4c4cc"}
STUDIO_LABEL = "Studio (clean, recommended)"

fonts.register_for_matplotlib()   # IBM Plex for the charts drawn in the app


def studio_rc(context: str = "notebook") -> dict:
    """The rcParams of the Studio look (line widths follow the Text size setting)."""
    k = CONTEXT_SCALE.get(context, 1.0)

    def w(v):
        return round(v * k, 2)

    ink = STUDIO_INK
    return {
        "font.sans-serif": list(fonts.CHART_SANS),
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": ink["spine"], "axes.linewidth": w(0.8),
        "axes.grid": True, "grid.color": ink["grid"], "grid.linewidth": w(0.6),
        "axes.titlelocation": "left", "axes.titleweight": "bold", "axes.titlesize": "large",
        "axes.titlepad": w(10), "figure.titleweight": "bold",
        "text.color": ink["text"], "axes.labelcolor": ink["label"],
        "xtick.color": ink["tick"], "ytick.color": ink["tick"],
        "lines.linewidth": w(1.4), "lines.markersize": w(5), "patch.linewidth": w(1.0),
        "legend.edgecolor": ink["grid"],
    }


def rc_code(rc: dict, comment: str = "") -> list:
    """plt.rcParams.update({...}) written over a few short lines."""
    lines = ["plt.rcParams.update({" + (f"  # {clean_comment(comment)}" if comment else "")]
    row = ""
    for key, value in rc.items():
        item = f"{lit(key)}: {lit(value)},"
        if row and len(row) + 1 + len(item) > LINE_LIMIT - 4:
            lines.append("    " + row)
            row = item
        else:
            row = f"{row} {item}".strip()
    if row:
        lines.append("    " + row)
    lines.append("})")
    return lines
LEGEND_PLACES = [("auto", "automatic"), ("upper right", "upper right"), ("upper left", "upper left"),
                 ("lower right", "lower right"), ("lower left", "lower left"), ("center left", "centre left"),
                 ("outside", "outside, right"), ("hide", "hidden")]
PIP_NAMES = {"sklearn": "scikit-learn", "scipy": "scipy", "statsmodels": "statsmodels"}
NOISE = ("non-interactive", "constrained_layout not applied", "Tight layout not applied", "layout has changed",
         "not compatible with tight_layout", "Glyph", "FixedFormatter", "set_ticklabels()",
         "incompatible with subplots_adjust")


def style_choices() -> list:
    """(value, label) pairs for the Style dropdown."""
    out = [("studio", STUDIO_LABEL)] + [(s, f"seaborn · {s}") for s in SEABORN_STYLES]
    for name in sorted(plt.style.available, key=str.lower):
        if not name.startswith(("_", "seaborn")):
            out.append((f"mpl:{name}", f"matplotlib · {name}"))
    return out


@dataclass
class StyleSettings:
    theme: str = "studio"         # "studio", a seaborn style name, or "mpl:<matplotlib style sheet>"
    palette: str = "default"      # "default" = the style's own colours
    context: str = "notebook"     # paper / notebook / talk / poster (font sizes)

    def _palette(self, default):
        """The palette as code: the Studio colours are written out, others by name."""
        name = default if self.palette == "default" else self.palette
        return Raw("studio_colors") if name == "studio" else name

    def code(self) -> list:
        theme = self.theme
        if theme.startswith("mpl:") and theme[4:] not in plt.style.available:
            theme = "studio"
        context = self.context if self.context in CONTEXTS else "notebook"
        lines = []
        uses_studio = (self.palette == "studio") or (self.palette == "default" and theme == "studio")
        if uses_studio:
            half = len(STUDIO_COLORS) // 2
            lines.append(f"studio_colors = [{', '.join(map(lit, STUDIO_COLORS[:half]))},  # colour-blind-safe order")
            lines.append(f"                 {', '.join(map(lit, STUDIO_COLORS[half:]))}]")
        if theme == "studio":
            lines.append(call("sns.set_theme", style="white", context=context, palette=self._palette("studio")))
            lines += rc_code(studio_rc(context), "Studio look: fine lines, hairline grid, no box")
            return lines
        if theme.startswith("mpl:"):
            lines.append(f"plt.style.use({lit(theme[4:])})")
            if context != "notebook":
                lines.append(f"sns.set_context({lit(context)})")
            if self.palette != "default":
                lines.append(f"sns.set_palette({lit(self._palette(self.palette))})")
            return lines
        lines.append(call("sns.set_theme", style=theme, context=context, palette=self._palette("deep")))
        return lines


@dataclass
class LabelSettings:
    title: str = ""
    show_title: bool = True
    xlabel: str = ""
    ylabel: str = ""
    logx: bool = False
    logy: bool = False
    legend: str = "auto"
    xlim: tuple | None = None     # set with the range sliders under / beside the plot
    ylim: tuple | None = None


@dataclass
class BuiltPlot:
    graph: GraphType
    dataset: Dataset
    df: pd.DataFrame            # the rows that go into the plot
    plot_code: str              # what the app executes (imports + style + plot)
    script: str                 # full script for the user
    notes: list = field(default_factory=list)
    limit_code: str = ""        # ax.set_xlim/ylim lines, executed after plot_code
    zoomable: bool = False      # one 2D axes `ax` that the range sliders can zoom


@dataclass
class PlotResult:
    built: BuiltPlot
    figure: object
    warnings: list
    seconds: float

    @property
    def script(self):
        return self.built.script

    @property
    def notes(self):
        return self.built.notes


class PlotRunError(Exception):
    """The generated code raised an exception while drawing."""

    def __init__(self, message: str, details: str = "", line: str = ""):
        super().__init__(message)
        self.message, self.details, self.line = message, details, line

    @classmethod
    def wrap(cls, exc: BaseException, code: str) -> "PlotRunError":
        frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == PLOT_FILE]
        line = ""
        if frames:
            lines = code.split("\n")
            n = frames[-1].lineno
            if 1 <= n <= len(lines):
                line = lines[n - 1].strip()
        if isinstance(exc, ModuleNotFoundError) and exc.name:
            pkg = PIP_NAMES.get(exc.name.split(".")[0], exc.name.split(".")[0])
            message = f"This plot needs the '{pkg}' package.\nInstall it with:   pip install {pkg}"
        elif isinstance(exc, MemoryError):
            message = "Ran out of memory. Use fewer rows (Rows: random sample)."
        else:
            message = f"{type(exc).__name__}: {exc}"
        details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return cls(message, details, line)


# --------------------------------------------------------------------------- #
# Checking the selection
# --------------------------------------------------------------------------- #

def selection_problems(graph: GraphType, ds: Dataset, sel: dict) -> list:
    problems = []
    for role in graph.roles:
        value = sel.get(role.key)
        if role.multi:
            value = value or []
            if role.required and len(value) < role.min_count:
                need = f"at least {role.min_count} columns" if role.min_count > 1 else "a column"
                problems.append(f"Choose {need} for “{role.label}”.")
            missing = [v for v in value if v not in ds.columns]
        else:
            if role.required and not value:
                problems.append(f"Choose a column for “{role.label}”.")
            missing = [value] if value and value not in ds.columns else []
        if missing:
            problems.append(f"Column(s) not in this file: {', '.join(map(str, missing))}")
    return problems


def used_columns(graph: GraphType, sel: dict) -> list:
    used = []
    for role in graph.roles:
        value = sel.get(role.key)
        for col in (value if isinstance(value, list) else [value] if value else []):
            if col not in used:
                used.append(col)
    return used


# --------------------------------------------------------------------------- #
# Rows
# --------------------------------------------------------------------------- #

def prepare_rows(ds: Dataset, rows: RowSettings, used: list, dropna: bool, heavy: int | None):
    """Return (code lines, chosen rows, notes) for the Rows settings."""
    lines, notes = [], []
    ns = {"df": ds.df, "pd": pd, "np": np}

    def run(line, hint=""):
        try:
            exec(line, ns)
        except Exception as exc:
            raise PlotError(f"Row selection failed:\n{type(exc).__name__}: {exc}{hint}") from None
        lines.append(line)

    query = rows.query.strip()
    if query:
        run(f"df = df.query({lit(query)})",
            "\n\nWrite filters like:   Age > 30 and Sex == 'male'\n"
            "Put column names with spaces in `backticks`, e.g.  `Flight Distance` > 1000")
        if ns["df"].empty:
            raise PlotError(f"The filter “{query}” matches no rows.")
    if rows.mode == "first":
        run(f"df = df.head({int(rows.first_n)})")
    elif rows.mode == "range":
        start, stop = int(rows.start), int(rows.stop)
        if stop <= start:
            raise PlotError("In 'Rows from … to …', the end must be larger than the start.")
        run(f"df = df.iloc[{start}:{stop}]  # rows {start} to {stop - 1}")
    if dropna and used:
        present = [c for c in used if c in ns["df"].columns]
        if present and ns["df"][present].isna().any().any():
            before = len(ns["df"])
            subset = "" if present == list(ns["df"].columns) else \
                f"subset={cols_expr(present, ns['df'].columns, ns['df'].select_dtypes('number').columns)}"
            run(commented(f"df = df.dropna({subset})", "drop rows with gaps in the plotted columns"))
            dropped = before - len(ns["df"])
            if dropped:
                notes.append(f"{dropped:,} row(s) with missing values in the chosen columns were left out.")
    if rows.mode == "sample":
        n = int(rows.sample_n)
        if len(ns["df"]) > n:
            run(f"df = df.sample(n={n}, random_state={int(rows.seed)})  # random sample of rows")
        else:
            notes.append(f"The sample size ({n:,}) is not smaller than the rows available "
                         f"({len(ns['df']):,}), so all rows are used.")
    elif rows.auto_sample and heavy and len(ns["df"]) > heavy:
        total = len(ns["df"])
        run(f"df = df.sample(n={heavy}, random_state=42)  # random sample: keeps this plot fast")
        notes.append(f"Plotted a random sample of {heavy:,} of {total:,} rows to keep this plot fast "
                     f"(turn off 'Sample big data for slow plots' under Rows to use all rows).")
    return lines, ns["df"], notes


# --------------------------------------------------------------------------- #
# Build / run
# --------------------------------------------------------------------------- #

def build_plot(graph: GraphType, ds: Dataset, sel: dict, opts: dict, rows: RowSettings,
               style: StyleSettings, labels: LabelSettings) -> BuiltPlot:
    problems = selection_problems(graph, ds, sel)
    if problems:
        raise PlotError("\n".join(problems))
    sel = {k: (list(v) if isinstance(v, list) else v) for k, v in sel.items()}
    opts = {**{o.key: o.default for o in graph.options}, **(opts or {})}
    used = used_columns(graph, sel)
    heavy = graph.heavy(opts) if graph.heavy else None
    row_lines, df, notes = prepare_rows(ds, rows, used, rows.dropna and graph.dropna, heavy)
    if len(df) < graph.min_rows:
        raise PlotError(f"Only {len(df)} row(s) left after choosing rows; this plot needs at least "
                        f"{graph.min_rows}. Check the row filter and missing values.")
    ctx = Ctx(graph, ds, df, sel, opts, labels, text_scale=CONTEXT_SCALE.get(style.context, 1.0))
    graph.build(ctx)
    ctx.finish()

    style_lines = style.code()
    run_lines = list(ctx.imports) + ([""] if ctx.imports else []) + style_lines + [""] + ctx.lines
    plot_code = "\n".join(run_lines)
    script = assemble_script(graph, ds, row_lines, style_lines, ctx)
    return BuiltPlot(graph, ds, df, plot_code, script, notes + ctx.notes,
                     limit_code="\n".join(ctx.limit_lines), zoomable=ctx.zoomable)


def assemble_script(graph, ds, row_lines, style_lines, ctx) -> str:
    # every line of the script decides the imports: Feature Lab steps in the load code use np too
    body = "\n".join(list(ds.load_code) + list(row_lines) + list(style_lines) + ctx.lines + ctx.limit_lines)
    out = [f"# {graph.name}: made with {APP_NAME}", f"# Data: {clean_comment(ds.name)}", ""]
    if re.search(r"\bnp\.", body):
        out.append("import numpy as np")
    out.append("import pandas as pd")
    if re.search(r"\bmpl\.", body):
        out.append("import matplotlib as mpl")
    out += ["import matplotlib.pyplot as plt", "import seaborn as sns"]
    out += ctx.imports
    out += ["", "# 1. Load the CSV"] + ds.load_code
    step = 2
    if row_lines:
        out += ["", f"# {step}. Choose the rows"] + row_lines
        step += 1
    out += ["", f"# {step}. Style"] + style_lines
    out += ["", f"# {step + 1}. Plot"] + ctx.lines + ctx.limit_lines + ["", "plt.show()", ""]
    return "\n".join(out)


def run_plot(built: BuiltPlot):
    """Execute the plotting code; return (figure, warning messages, seconds)."""
    started = time.perf_counter()
    plt.close("all")
    matplotlib.rcdefaults()
    ns = {"df": built.df, "pd": pd, "np": np, "plt": plt, "sns": sns, "mpl": matplotlib, "__name__": "__plot__"}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            exec(compile(built.plot_code, PLOT_FILE, "exec"), ns)
        except Exception as exc:
            plt.close("all")
            raise PlotRunError.wrap(exc, built.plot_code) from None
        fig = ns.get("fig") or plt.gcf()
        # Remember the automatic X/Y ranges before the slider limits are applied:
        # the range sliders go from one end of these to the other.
        fig._studio_zoom = None
        if built.zoomable:
            fig._studio_zoom = zoom_info(ns.get("ax"), fig)
        if built.limit_code:
            try:
                exec(compile(built.limit_code, PLOT_FILE, "exec"), ns)
            except Exception as exc:
                plt.close("all")
                raise PlotRunError.wrap(exc, built.limit_code) from None
    plt.close("all")  # forget pyplot's bookkeeping; the Figure object itself stays usable
    messages = []
    for w in caught:
        text = str(w.message).strip().split("\n")[0]
        if issubclass(w.category, (UserWarning, RuntimeWarning)) and not any(n in text for n in NOISE):
            if text not in messages:
                messages.append(text)
    return fig, messages[:4], time.perf_counter() - started


def make_plot(graph, ds, sel, opts, rows, style, labels) -> PlotResult:
    built = build_plot(graph, ds, sel, opts, rows, style, labels)
    fig, msgs, seconds = run_plot(built)
    return PlotResult(built, fig, msgs, seconds)
