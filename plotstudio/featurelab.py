"""The Feature Lab tab: new features measured against the target, added as pipeline steps.

* ``LabService``       the loaded file's Pipeline (with undo / redo), the background jobs (find
                       features, apply a change, evaluate, submission) and the working table that
                       every other tab uses (the file + the accepted steps)
* ``FeatureLabView``   the tab: ranked suggestions with Accept / Skip, a preview (first rows,
                       distribution, link to the target), your own formula, the accepted features
                       with undo / redo, Evaluate with model, and Export
* ``CodeDialog``, ``SubmissionDialog``

Everything here only renders and asks; the work itself is done in plotstudio.core.
"""
from __future__ import annotations

import copy
import gc
import textwrap
import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import matplotlib
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import APP_NAME, settings
from .codegen import PlotError
from .core import export as exporter
from .core import activity
from .core import feature_lab
from .core import recommend as recommend_plots
from .core.evaluate import EvaluateError, evaluate
from .core.feature_lab import ExprError, score_formula, scoring
from .core.pipeline import Pipeline, PipelineError
from .data import Dataset, RowSettings, dataset_from_frame, load_csv, scan_column
from .engine import LabelSettings, StyleSettings, build_plot, run_plot
from .graphs import GRAPH_BY_ID
from .ideas import Dot, show_error, short
from .log import log_error
from .paper import apply_dark_paper
from .theme import C, CODE
from .widgets import AutoScrollbar, PlaceholderEntry, ScrollFrame, Tooltip, release_canvas

STATUS_COLOR = {"leak": "danger", "recommended": "ok", "neutral": "muted", "weak": "faint", "redundant": "sev_check",
                "error": "danger"}
STATUS_WORD = {"leak": "Leakage?", "recommended": "Adds information", "neutral": "Same information, new shape",
               "weak": "Less than its source", "redundant": "Redundant", "error": "Couldn't be made"}
PREVIEW_ROWS = 10
PLOT_ROWS = 3000
PLOT_GAP_MS = 40                         # pause between preview plots: the window answers


def make_working(base: Dataset, pipeline: Pipeline, df: pd.DataFrame) -> Dataset:
    """The file + the accepted steps as a Dataset: the new columns are scanned like the others, and
    the code every plot exports starts with the steps (so it runs on the raw file)."""
    if not pipeline.steps:
        return base
    original = base.base_columns or base.columns
    columns = {c: copy.copy(original[c]) if c in original else scan_column(c, df[c]) for c in df.columns}
    code = list(base.load_code)
    if any(s.op == "target_enc" for s in pipeline):
        code.append("train = True  # this is the training file: target encodings are computed out-of-fold")
    code += ["", "# Feature Lab steps (Feature Lab > Export has them as clean.py and a notebook)"] + pipeline.code()
    return Dataset(path=base.path, df=df, columns=columns, load_code=code, notes=list(base.notes),
                   seconds=base.seconds, sep=base.sep, encoding=base.encoding, header=base.header)


# =========================================================================== #
# Background work
# =========================================================================== #

class LabService:
    """The Feature Lab's state for the loaded file and its background jobs (one at a time)."""

    def __init__(self, app):
        self.app = app
        self.base: Dataset | None = None          # the file as loaded
        self.pipeline = Pipeline()
        self.working: Dataset | None = None       # file + steps: what every tab shows
        self.result = None                        # feature_lab.LabResult
        self.result_key = None
        self.evaluation = None
        self.eval_version = None                  # pipeline.signature the evaluation belongs to
        self.custom = None                        # the last checked formula (FeatureSuggestion)
        self.skipped: set = set()
        self.listeners: list = []
        self.job: dict | None = None
        self.queued = False                       # find features again once the running job ends
        self.progress = (0.0, "")
        self.status = ("", "muted")

    # -------------------------------------------------------------- events --
    def listen(self, fn) -> None:
        self.listeners.append(fn)

    def _emit(self, event: str) -> None:
        for fn in list(self.listeners):
            try:
                fn(event)
            except tk.TclError as exc:            # a view that is being destroyed
                log_error("Feature Lab: a view could not update", exc)

    @property
    def busy(self) -> bool:
        return self.job is not None

    def reset(self, ds: Dataset) -> None:
        """A newly loaded file: no steps yet."""
        self.base = self.working = ds
        self.pipeline = Pipeline()
        self.result = self.result_key = self.evaluation = self.eval_version = self.custom = None
        self.skipped = set()
        self.status = ("", "muted")
        self._emit("reset")

    def target(self):
        return self.app.work.current_target()

    @property
    def current_evaluation(self):
        """The last evaluation if it belongs to the steps as they are now (an undo + redo is the same), else None."""
        if self.evaluation is not None and self.eval_version == self.pipeline.signature:
            return self.evaluation
        return None

    def key(self) -> tuple:
        overrides = tuple(sorted(self.app.work.type_overrides.items()))
        return id(self.working), self.target(), self.pipeline.version, overrides

    # ---------------------------------------------------------------- jobs --
    def _start(self, kind: str, work, done, text: str) -> bool:
        if self.job is not None:
            return False
        job = {"kind": kind, "progress": (0.0, text), "result": None, "error": None, "details": "", "ended": False,
               "done": done}
        self.job = job

        def tell(fraction, message):
            job["progress"] = (fraction, message)

        def run():
            try:
                job["result"] = work(tell)
            except Exception as exc:  # noqa: BLE001 - shown in a dialog by _poll
                job["error"], job["details"] = exc, traceback.format_exc()
            job["ended"] = True

        gc.collect()      # free dead Tk variables and pictures HERE: Tk must not delete them from the thread
        threading.Thread(target=run, daemon=True).start()
        self.progress = (0.0, text)
        self._emit("start")
        self.app.after(60, self._poll)
        return True

    def _poll(self) -> None:
        job = self.job
        if job is None:
            return
        if not job["ended"]:
            self.progress = job["progress"]
            self._emit("progress")
            self.app.after(80, self._poll)
            return
        self.job = None
        if job["error"] is not None:
            exc = job["error"]
            friendly = isinstance(exc, (PipelineError, EvaluateError, ExprError, ValueError))
            self.status = (f"{type(exc).__name__}: {exc}" if not friendly else str(exc), "danger")
            if friendly:
                log_error(f"Feature Lab ({job['kind']})", exc, job["details"])
                if job["kind"] != "formula":
                    messagebox.showerror(APP_NAME, str(exc), parent=self.app)
            else:
                show_error(self.app, f"The Feature Lab couldn't finish ({job['kind']}).", exc, job["details"])
            self._emit("error")
        else:
            try:
                job["done"](job["result"])
            except Exception as exc:  # noqa: BLE001
                show_error(self.app, "The Feature Lab couldn't show the result.", exc, traceback.format_exc())
        if self.queued and self.job is None:
            self.queued = False
            self.suggest()
        else:
            self._emit("idle")

    def suggest(self, force: bool = False) -> None:
        """Find features for the working table and the target (cached per table + target + steps)."""
        if self.working is None:
            return
        key = self.key()
        if not force and self.result is not None and self.result_key == key:
            self._emit("done")
            return
        if self.job is not None:
            self.queued = True
            return
        ds, target, pipe = self.working, self.target(), copy.deepcopy(self.pipeline)
        overrides = dict(self.app.work.type_overrides)
        columns = {n: copy.copy(i) for n, i in ds.columns.items()}

        def work(tell):
            return feature_lab.suggest_features(ds.df, target, pipeline=pipe, infos=columns, overrides=overrides,
                                                progress=tell)

        def done(res):
            self.result, self.result_key = res, key
            for plugin, message, details in res.errors:
                log_error(f"Feature Lab: the '{plugin}' ideas failed", details=f"{message}\n{details}")
            self._emit("done")

        self._start("suggest", work, done, "Looking for features")

    def change(self, how, message: str, kind: str = "change", activity_data: dict | None = None) -> bool:
        """Change the pipeline (on a copy, in the background), then rebuild the working table."""
        if self.job is not None or self.base is None:
            return False
        new = copy.deepcopy(self.pipeline)
        base, current = self.base, self.working.df

        def work(tell):
            how(new, current)
            df = new.transform(base.df, train=True, progress=tell) if new.steps else base.df
            return new, make_working(base, new, df)

        def done(res):
            self.pipeline, self.working = res
            self.custom = None
            self.status = (message, "ok")
            if kind == "accept":
                event_data = activity_data or {}
                activity.record_feature(self.app.cfg, event_data.get("name", ""),
                                        event_data.get("mi_gain"),
                                        dataset_name=self.base.name if self.base else "")
                settings.save(self.app.cfg)
            self.app.use_working(self.working)
            self._emit("changed")
            self.queued = True                 # the new columns open new ideas

        return self._start(kind, work, done, "Applying the steps")

    def accept(self, suggestion) -> bool:
        step = suggestion.step
        return self.change(lambda p, df: p.add(step, df), f"Added '{step.name}' ({step.label}).", "accept",
                           {"name": step.name, "mi_gain": getattr(suggestion, "gain", None)})

    def remove(self, index: int) -> bool:
        step = self.pipeline.steps[index]
        later = self.pipeline.dependents(index)
        extra = f" and {len(later)} step(s) built on it" if later else ""
        return self.change(lambda p, df: p.remove(index), f"Removed '{step.name}'{extra}. Undo brings it back.")

    def rename(self, index: int, name: str) -> bool:
        old = self.pipeline.steps[index].name
        return self.change(lambda p, df: p.rename(index, name, taken=df.columns), f"Renamed '{old}' to '{name}'.")

    def undo(self) -> bool:
        return self.pipeline.can_undo and self.change(lambda p, df: p.undo(), "Undone.")

    def redo(self) -> bool:
        return self.pipeline.can_redo and self.change(lambda p, df: p.redo(), "Redone.")

    def check_formula(self, text: str, name: str) -> bool:
        """Score your own formula like the suggestions (in the background)."""
        res = self.result
        if res is None or res.context is None:
            self.status = ("Pick the target and let the Lab find features first: your formula is measured the "
                           "same way.", "danger")
            self._emit("error")
            return False

        def work(tell):
            tell(0.3, "Checking the formula")
            return score_formula(res, text, name)

        def done(s):
            self.custom = s
            self._emit("custom")

        return self._start("formula", work, done, "Checking the formula")

    def evaluate(self) -> bool:
        target = self.target()
        if not target:
            self.status = ("Pick the target first: the models predict it.", "danger")
            self._emit("error")
            return False
        ds, base_cols = self.working, list(self.base.df.columns)
        outputs, version = list(self.pipeline.outputs), self.pipeline.signature
        columns = {n: copy.copy(i) for n, i in ds.columns.items()}

        def work(tell):
            return evaluate(ds.df, target, outputs, base_columns=base_cols, infos=columns, progress=tell)

        def done(ev):
            self.evaluation, self.eval_version = ev, version
            self._emit("evaluated")

        return self._start("evaluate", work, done, "Cross-validating")

    def submission(self, test: pd.DataFrame, id_column: str, model: str, path: Path) -> bool:
        target, train = self.target(), self.working.df
        pipe, base_cols = copy.deepcopy(self.pipeline), list(self.base.df.columns)
        columns = {n: copy.copy(i) for n, i in self.working.columns.items()}

        def work(tell):
            tell(0.2, "Applying the steps to the test file")
            out = exporter.submission(train, test, pipe, target, id_column, base_columns=base_cols, model=model,
                                      infos=columns)
            tell(0.9, "Writing the file")
            out.to_csv(path, index=False)
            return out

        def done(out):
            text = f"Saved {path.name}: {len(out):,} predictions of {target} ({model_label(model)})."
            left = out.attrs.get("left_out") or []
            if left:
                text += f" Not in the test file, so not used: {', '.join(left[:6])}{' …' if len(left) > 6 else ''}."
            self.status = (text, "ok")
            self._emit("exported")

        return self._start("submission", work, done, "Training the model on all rows")


def model_label(model: str) -> str:
    return {"boosting": "gradient boosting", "linear": "linear model"}.get(model, model)


# =========================================================================== #
# Small pieces
# =========================================================================== #

def fit_titles(fig, width_in: float) -> None:
    """Wrap the axes titles of a figure that was made smaller after its code ran (the preview plots), so a long
    title breaks into lines instead of running off the picture."""
    for ax in fig.axes:
        for text in (getattr(ax, "_left_title", None), getattr(ax, "title", None), getattr(ax, "_right_title", None)):
            if text is None or not text.get_text():
                continue
            chars = max(12, int(width_in * 72 / (text.get_fontsize() * 0.62)))
            flat = " ".join(text.get_text().split())
            if len(flat) > chars:
                text.set_text("\n".join(textwrap.wrap(flat, chars)))


class GainBar(tk.Canvas):
    """MI before (grey) and after (green / accent) on one scale: the gain at a glance."""

    def __init__(self, master, before: float, after: float, top: float, width: int, height: int, color: str):
        super().__init__(master, width=width, height=height, highlightthickness=0, borderwidth=0,
                         background=C["panel"])
        self.values, self.top, self.color = (before, after), max(top, 1e-9), color
        self.on_theme()

    def on_theme(self) -> None:
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        before, after = self.values
        r = h / 2
        self.create_rectangle(0, r - 1, w, r + 1, fill=C["border"], outline="")
        xa = max(2.0, w * min(1.0, after / self.top))
        xb = w * min(1.0, before / self.top)
        self.create_rectangle(0, 1, xa, h - 1, fill=C[self.color], outline="")
        if xb > 0:
            self.create_rectangle(0, h * 0.3, xb, h * 0.7, fill=C["border_dark"], outline="")


class FlowFrame(tk.Frame):
    """Children laid out left to right, wrapping to the next line when the width runs out."""

    def __init__(self, master, gap: int, **kw):
        super().__init__(master, **kw)
        self.gap = gap
        self.bind("<Configure>", lambda e: self.after_idle(self.reflow), add="+")

    def reflow(self, retry: int = 3) -> None:
        """Runs at idle time (after the children worked out their sizes), so it never has to force a layout pass
        of the whole window."""
        width = max(self.winfo_width(), 200)
        sizes = [(c, c.winfo_reqwidth(), c.winfo_reqheight()) for c in self.winfo_children()]
        if retry and any(cw <= 1 for _, cw, _ in sizes):
            self.after_idle(lambda: self.reflow(retry - 1))
            return
        x = y = line = 0
        for child, cw, ch in sizes:
            if x and x + cw > width:
                x, y = 0, y + line + self.gap
                line = 0
            child.place(x=x, y=y)
            x += cw + self.gap
            line = max(line, ch)
        self.configure(height=max(1, y + line))


# =========================================================================== #
# The tab
# =========================================================================== #

class FeatureLabView(tk.Frame):
    """Suggestions (Accept / Skip), preview, your own formula, accepted features, Evaluate, Export."""

    def __init__(self, master, page):
        super().__init__(master, background=C["panel"])
        self.page, self.app = page, page.app
        self.svc: LabService = self.app.lab
        t, px = self.app.theme, self.app.theme.px
        self.selected = None                  # the suggestion in the preview
        self.wraps: list = []
        self.accept_buttons: dict = {}        # name -> button (tests use them too)
        self.skip_buttons: dict = {}
        self.chips: list = []
        self.show_skipped = False
        self.preview_canvases: list = []
        self._redraw_pending = False
        self._split_done = False              # the list gets ~57 % of the width once
        self._plot_width = 0                  # width the preview plots were drawn for
        self._resize_job = None
        self._plot_token = None               # the preview the queued plots belong to
        self._plot_job = None

        # header ------------------------------------------------------------
        head = tk.Frame(self, background=C["panel"])
        head.pack(fill="x", padx=px(16), pady=(px(12), px(4)))
        top = tk.Frame(head, background=C["panel"])
        top.pack(fill="x")
        self.title = tk.Label(top, text="Feature Lab", background=C["panel"], foreground=C["text"],
                              font=t.f["h3"], anchor="w")
        self.title.pack(side="left")
        self.find_btn = ttk.Button(top, text="Find features", image=t.icon_states("sparkle", 16, normal="accent",
                                                                                   active="accent_hover"),
                                   compound="left", style="Small.TButton", command=lambda: self.svc.suggest(force=True))
        self.find_btn.pack(side="right")
        Tooltip(self.find_btn, "Work the suggestions out again (they also update by themselves when you accept one "
                               "or change the target).")
        self.target_box = ttk.Combobox(top, textvariable=page.target_var, values=["(none)"], state="readonly",
                                       width=22, height=18)
        self.target_box.pack(side="right", padx=(0, px(10)))
        self.target_box.bind("<<ComboboxSelected>>", page._target_changed)
        ttk.Label(top, text="Target", style="Panel.Bold.TLabel").pack(side="right", padx=(0, px(8)))
        Tooltip(self.target_box, "The column to predict. Every feature is measured against it.")
        self.subtitle = tk.Label(head, background=C["panel"], foreground=C["muted"], font=t.f["small"], anchor="w",
                                 justify="left")
        self.subtitle.pack(fill="x", pady=(px(4), 0))
        self.status_row = tk.Frame(head, background=C["panel"])
        self.progress = ttk.Progressbar(self.status_row, mode="determinate", maximum=1.0, length=px(220))
        self.progress.pack(side="left")
        self.status = tk.Label(self.status_row, background=C["panel"], foreground=C["muted"], font=t.f["small"])
        self.status.pack(side="left", padx=(px(10), 0))
        tk.Frame(self, background=C["border"], height=max(1, px(1))).pack(fill="x", padx=px(16), pady=(px(6), 0))

        # bottom: accepted features, evaluate, export ---------------------------
        self.bottom = tk.Frame(self, background=C["panel"])
        self.bottom.pack(side="bottom", fill="x", padx=px(16), pady=(px(6), px(12)))
        tk.Frame(self, background=C["border"], height=max(1, px(1))).pack(side="bottom", fill="x", padx=px(16))
        self._build_bottom(self.bottom)

        # middle: suggestions | preview ------------------------------------------
        self.split = ttk.PanedWindow(self, orient="horizontal")
        self.split.pack(fill="both", expand=True, padx=(px(8), px(8)))
        left = tk.Frame(self.split, background=C["panel"])
        right = tk.Frame(self.split, background=C["panel"])
        self.split.add(left, weight=3)
        self.split.add(right, weight=2)
        self.scroll = ScrollFrame(left, t, bg=C["panel"])
        self.scroll.pack(fill="both", expand=True)
        self.body = self.scroll.body
        self.scroll.canvas.bind("<Configure>", self._rewrap, add="+")
        self.pscroll = ScrollFrame(right, t, bg=C["panel"])
        self.pscroll.pack(fill="both", expand=True)
        self.preview = self.pscroll.body
        self.pscroll.canvas.bind("<Configure>", self._preview_resized, add="+")
        self.split.bind("<Configure>", self._first_split, add="+")
        self.bind("<Configure>", lambda e: self.subtitle.configure(wraplength=max(200, e.width - px(40))), add="+")
        self.bind_all("<Control-z>", lambda e: self._key(self.svc.undo), add="+")
        self.bind_all("<Control-y>", lambda e: self._key(self.svc.redo), add="+")
        self.bind_all("<Control-Shift-Z>", lambda e: self._key(self.svc.redo), add="+")
        self.svc.listen(self.on_event)
        page.plot_view.paper_var.trace_add("write", lambda *a: self.on_theme())
        self.on_event("reset")

    # ---------------------------------------------------------------- build --
    def _build_bottom(self, parent) -> None:
        t, px = self.app.theme, self.app.theme.px
        row = tk.Frame(parent, background=C["panel"])
        row.pack(fill="x")
        self.acc_title = tk.Label(row, text="Accepted features", background=C["panel"], foreground=C["text"],
                                  font=t.f["bold"], anchor="w")
        self.acc_title.pack(side="left")
        self.export_btn = ttk.Menubutton(row, text="Export", image=t.icon("download", "muted", 16), compound="left",
                                         style="TMenubutton")
        menu = t.menu(self.export_btn)
        menu.add_command(label="Show the code…", command=self.show_code)
        menu.add_command(label="Save clean.py…", command=self.save_clean)
        menu.add_command(label="Save notebook (.ipynb)…", command=self.save_notebook)
        menu.add_separator()
        menu.add_command(label="Kaggle submission…", command=self.submission)
        self.export_btn["menu"] = menu
        self.export_btn.pack(side="right")
        Tooltip(self.export_btn, "The accepted steps as clean.py or a notebook (they rebuild exactly this table from "
                                 "the raw file), or a Kaggle submission for a test file.")
        self.eval_btn = ttk.Button(row, text="Evaluate with model", style="Accent.TButton", command=self.evaluate)
        self.eval_btn.pack(side="right", padx=(0, px(8)))
        Tooltip(self.eval_btn, "5-fold cross-validation of a linear model and gradient boosting, without and with the "
                               "accepted features (same folds). Gains smaller than the spread between folds are "
                               "marked 'not significant'.")
        self.redo_btn = ttk.Button(row, text="Redo", image=t.icon_states("redo", 16), compound="left",
                                   style="Small.TButton", command=self.svc.redo)
        self.redo_btn.pack(side="right", padx=(0, px(8)))
        self.undo_btn = ttk.Button(row, text="Undo", image=t.icon_states("undo", 16), compound="left",
                                   style="Small.TButton", command=self.svc.undo)
        self.undo_btn.pack(side="right", padx=(0, px(6)))
        Tooltip(self.undo_btn, "Undo the last change to the accepted features (Ctrl+Z)")
        Tooltip(self.redo_btn, "Redo (Ctrl+Y)")
        self.flow = FlowFrame(parent, gap=px(6), background=C["panel"], height=1)
        self.flow.pack(fill="x", pady=(px(8), 0))
        self.acc_empty = tk.Label(parent, text="None yet: press Accept on a suggestion. Each one becomes a step, so "
                                               "undo, the code export and submissions include it.",
                                  background=C["panel"], foreground=C["faint"], font=t.f["small"], anchor="w",
                                  justify="left")
        self.eval_box = tk.Frame(parent, background=C["panel"])
        self.eval_box.pack(fill="x", pady=(px(6), 0))
        self.message = tk.Label(parent, background=C["panel"], foreground=C["muted"], font=t.f["small"], anchor="w",
                                justify="left")
        self.message.pack(fill="x", pady=(px(4), 0))
        parent.bind("<Configure>", lambda e: (self.message.configure(wraplength=max(200, e.width - px(10))),
                                              self.acc_empty.configure(wraplength=max(200, e.width - px(10)))),
                    add="+")

    def set_target_choices(self, values) -> None:
        self.target_box.configure(values=list(values))

    def _key(self, action) -> None:
        if self.page.nb.select() != str(self) or isinstance(self.focus_get(), (tk.Entry, ttk.Entry, tk.Text)):
            return
        action()

    # ---------------------------------------------------------------- events --
    def on_event(self, event: str) -> None:
        px = self.app.theme.px
        svc, ds = self.svc, self.svc.working
        busy = svc.busy
        for b in (self.find_btn, self.eval_btn, self.export_btn):
            b.state(["disabled"] if busy or ds is None else ["!disabled"])
        self.undo_btn.state(["!disabled"] if svc.pipeline.can_undo and not busy else ["disabled"])
        self.redo_btn.state(["!disabled"] if svc.pipeline.can_redo and not busy else ["disabled"])
        for btn in self.accept_buttons.values():
            try:
                if getattr(btn, "allowed", True):
                    btn.state(["disabled"] if busy else ["!disabled"])
            except tk.TclError:
                pass
        if ds is None:
            self.title.configure(text="Feature Lab")
            self.subtitle.configure(text="Open a CSV file to find new features for it.")
            self._clear()
            self._fill_accepted()
            return
        self.title.configure(text=f"Feature Lab for {ds.name}")
        if event in ("start", "progress"):
            fraction, text = svc.progress
            self.status_row.pack(fill="x", pady=(px(8), 0))
            self.progress.configure(value=fraction)
            self.status.configure(text=f"{text}…" if text else "Working…")
            return
        self.status_row.pack_forget()
        if event in ("reset", "changed", "idle", "error", "exported", "evaluated", "custom", "done"):
            self._fill_accepted()
            self._fill_evaluation()
            text, role = svc.status
            self.message.configure(text=text, foreground=C[role] if role in C else C["muted"])
        if event == "done":
            self._fill(svc.result)
        elif event == "reset":
            self._clear()
            self._show_intro()
            if self.is_showing():
                svc.suggest()
        elif event == "custom" and svc.custom is not None:
            self._custom_result()
            self.show_preview(svc.custom)
        elif event == "error" and svc.job is None and svc.status[0]:
            if hasattr(self, "formula_msg"):
                self.formula_msg.configure(text=svc.status[0], foreground=C["danger"])

    def is_showing(self) -> bool:
        try:
            return self.page.nb.select() == str(self)
        except tk.TclError:
            return False

    def on_show(self) -> None:
        """The tab was opened: find features if they aren't there yet."""
        if self.svc.working is not None:
            self.svc.suggest()

    def on_target(self) -> None:
        if self.is_showing() and self.svc.working is not None:
            self.svc.suggest()
        else:
            self.svc.result_key = None

    # ------------------------------------------------------------------ list --
    def _clear(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()
        self.wraps = []
        self.accept_buttons, self.skip_buttons = {}, {}

    def _show_intro(self) -> None:
        t, px = self.app.theme, self.app.theme.px
        tk.Label(self.body, text="The Lab suggests new columns (title from a name, family size, ratios, date parts, "
                                 "flags for gaps ...), measures each one against the target and adds the ones you "
                                 "accept as steps.", background=C["panel"], foreground=C["muted"], font=t.f["small"],
                 anchor="w", justify="left", wraplength=px(520)).pack(fill="x", padx=px(8), pady=px(12))

    def _section(self, text: str, extra: str = "") -> tk.Frame:
        t, px = self.app.theme, self.app.theme.px
        head = tk.Frame(self.body, background=C["panel"])
        head.pack(fill="x", padx=px(8), pady=(px(14), px(6)))
        tk.Label(head, text=text, background=C["panel"], foreground=C["text"], font=t.f["bold"]).pack(side="left")
        if extra:
            tk.Label(head, text=extra, background=C["panel"], foreground=C["faint"], font=t.f["small"]).pack(
                side="left", padx=(px(10), 0), pady=(px(2), 0))
        return head

    def _fill(self, res) -> None:
        t, px = self.app.theme, self.app.theme.px
        top = self.scroll.canvas.yview()[0]
        self._clear()
        if res is None:
            return
        parts = []
        if res.target:
            parts.append(f"New columns that tell more about {res.target}, best first. MI = mutual information with "
                         "the target (nats); the gain is over the best column it is made from.")
        parts += res.notes
        if res.seconds >= 0.05:
            parts.append(f"Worked out in {res.seconds:.1f} s.")
        self.subtitle.configure(text="  ".join(parts))
        if not res.target:
            self._show_intro()
            return
        shown = [s for s in res.suggestions if self._key_of(s) not in self.svc.skipped]
        skipped = [s for s in res.suggestions if self._key_of(s) in self.svc.skipped]
        self._section("Suggestions", f"{len(shown)} · by MI gain" if shown else "")
        if not shown:
            tk.Label(self.body, text="No new features found for this table: every idea was already there or added "
                                     "nothing. Try your own formula below.", background=C["panel"],
                     foreground=C["muted"], font=t.f["small"], anchor="w", justify="left").pack(fill="x", padx=px(8))
        top_mi = max((max(s.mi_before, s.mi_after) for s in shown), default=0.0)
        table = tk.Frame(self.body, background=C["panel"])
        table.pack(fill="x", padx=(px(8), px(10)))
        table.columnconfigure(1, weight=1)
        r = 0
        for s in shown:
            tk.Frame(table, background=C["border"], height=max(1, px(1))).grid(row=r, column=0, columnspan=4,
                                                                                 sticky="ew")
            self._row(table, r + 1, s, top_mi)
            r += 2
        if skipped:
            text = ("Hide" if self.show_skipped else "Show") + f" {len(skipped)} skipped"
            ttk.Button(self.body, text=text, style="Link.TButton", command=self._toggle_skipped).pack(
                anchor="w", padx=px(4), pady=(px(6), 0))
            if self.show_skipped:
                box = tk.Frame(self.body, background=C["panel"])
                box.pack(fill="x", padx=(px(8), px(10)))
                for i, s in enumerate(skipped):
                    line = tk.Frame(box, background=C["panel"])
                    line.pack(fill="x", pady=px(2))
                    tk.Label(line, text=s.name, background=C["panel"], foreground=C["faint"], font=t.f["small"]).pack(
                        side="left")
                    ttk.Button(line, text="Bring back", style="Link.TButton",
                               command=lambda s=s: self._unskip(s)).pack(side="left", padx=(px(8), 0))
        if res.encodings:
            self._encodings(res.encodings)
        self._formula_box()
        tk.Frame(self.body, background=C["panel"], height=px(16)).pack()
        self._rewrap()
        self.after_idle(lambda: self.scroll.canvas.yview_moveto(top))
        if self.selected is not None:
            again = res.find(self.selected.name) if self.selected.generator != "custom" else None
            if again is not None:
                self.show_preview(again)
            elif self.selected.generator != "custom":
                self._preview_empty()
        elif shown:
            self.show_preview(shown[0])
        else:
            self._preview_empty()

    @staticmethod
    def _key_of(s) -> tuple:
        return s.step.op, tuple(s.step.cols), s.step.name

    def _row(self, table, row, s, top_mi) -> None:
        t, px = self.app.theme, self.app.theme.px
        status = s.status
        color = STATUS_COLOR[status]
        pad = (px(8), px(8))
        badge = ttk.Label(table, text=str(s.rank), style="Badge.TLabel" if s.rank == 1 and status == "recommended"
                          else "SoftBadge.TLabel" if status != "leak" else "MutedBadge.TLabel")
        badge.grid(row=row, column=0, sticky="nw", padx=(0, px(10)), pady=pad)
        mid = tk.Frame(table, background=C["panel"])
        mid.grid(row=row, column=1, sticky="new", pady=pad, padx=(0, px(10)))
        fits = []                             # labels that wrap to mid's real width (label, room for others)
        mid.bind("<Configure>", lambda e, fits=fits: self._fit_labels(e.width, fits), add="+")
        line = tk.Frame(mid, background=C["panel"])
        line.pack(fill="x")
        if status == "leak":
            Dot(line, "danger", px(10)).pack(side="left", padx=(0, px(6)), pady=(px(3), 0))
        name = tk.Label(line, text=s.name, background=C["panel"], foreground=C["text"], font=t.f["bold"],
                        anchor="w", cursor="hand2")
        name.pack(side="left")
        tk.Label(line, text=s.title if s.title != s.name else s.generator.replace("_", " "), background=C["panel"],
                 foreground=C["faint"], font=t.f["small"], anchor="w").pack(side="left", fill="x", expand=True,
                                                                            padx=(px(8), 0), pady=(px(2), 0))
        meter = tk.Frame(mid, background=C["panel"])
        meter.pack(fill="x", pady=(px(4), 0))
        GainBar(meter, s.mi_before, s.mi_after, top_mi, px(96), px(8),
                "ok" if status == "recommended" else "accent" if status == "neutral" else
                "danger" if status == "leak" else "border_dark").pack(side="left", pady=(px(2), 0))
        mi = tk.Label(meter, text=s.mi_text(), background=C["panel"], anchor="w", justify="left",
                      foreground=C[color] if status in ("recommended", "leak") else C["muted"],
                      font=t.f["small_bold"] if status in ("recommended", "leak") else t.f["small"])
        mi.pack(side="left", fill="x", expand=True, padx=(px(8), 0))
        fits.append((mi, px(96) + px(8)))     # wraps beside the bar instead of being cut off
        detail = s.reason.split(". ", 1)[1] if ". " in s.reason else ""
        if status not in ("recommended", "leak") and not detail.startswith(STATUS_WORD[status]):
            detail = f"{STATUS_WORD[status]}. {detail}"
        if detail:
            why = tk.Label(mid, text=detail, background=C["panel"], foreground=C["muted"], font=t.f["small"],
                           anchor="w", justify="left")
            why.pack(fill="x", pady=(px(3), 0))
            fits.append((why, 0))
        for w in (name, badge):
            w.bind("<Button-1>", lambda e, s=s: self.show_preview(s))
        Tooltip(name, f"{s.title}\n{s.why}\nClick to preview it.")
        buttons = tk.Frame(table, background=C["panel"])
        buttons.grid(row=row, column=2, sticky="ne", pady=(px(5), px(5)))
        primary = status == "recommended"
        acc = ttk.Button(buttons, text="Accept", compound="left",
                         image=t.icon("check", "on_accent", 14) if primary else t.icon_states("check", 14),
                         style="Accent.TButton" if primary else "TButton", command=lambda s=s: self.accept(s))
        acc.pack(side="left")
        acc.allowed = s.can_accept
        if not s.can_accept:
            acc.state(["disabled"])
            Tooltip(acc, "Blocked: alone this feature predicts the target almost perfectly, so it was probably made "
                         "from the target (leakage). Use 'Accept anyway' only if you are sure it isn't.")
        else:
            Tooltip(acc, "Add it as a step: the column appears in every tab, the code export and submissions.")
        skip = ttk.Button(buttons, text="Skip", image=t.icon_states("close", 14), compound="left",
                          style="Small.TButton", command=lambda s=s: self.skip(s))
        skip.pack(side="left", padx=(px(6), 0))
        self.accept_buttons[s.name] = acc
        self.skip_buttons[s.name] = skip
        if status == "leak":
            ttk.Button(mid, text="Accept anyway…", style="Link.TButton",
                       command=lambda s=s: self.accept(s, force=True)).pack(anchor="w")

    def _encodings(self, encodings) -> None:
        t, px = self.app.theme, self.app.theme.px
        self._section("Encodings", "how a model should read each category column")
        box = tk.Frame(self.body, background=C["panel"])
        box.pack(fill="x", padx=(px(8), px(10)))
        box.columnconfigure(0, weight=1)
        for i, s in enumerate(encodings):
            tk.Frame(box, background=C["border"], height=max(1, px(1))).grid(row=2 * i, column=0, columnspan=2,
                                                                               sticky="ew")
            text = tk.Frame(box, background=C["panel"])
            text.grid(row=2 * i + 1, column=0, sticky="new", pady=(px(7), px(7)))
            head, _, rest = s.why.partition(". ")
            tk.Label(text, text=head, background=C["panel"], foreground=C["text"], font=t.f["bold"],
                     anchor="w").pack(fill="x")
            lbl = tk.Label(text, text=rest, background=C["panel"], foreground=C["muted"], font=t.f["small"],
                           anchor="w", justify="left")
            lbl.pack(fill="x")
            self.wraps.append((lbl, px(200)))
            if s.warning:
                warn = tk.Label(text, text="⚠ " + s.warning if self.app.theme.glyph("⚠", "!") == "⚠" else s.warning,
                                background=C["panel"], foreground=C["sev_warn"], font=t.f["small"], anchor="w",
                                justify="left")
                warn.pack(fill="x", pady=(px(3), 0))
                self.wraps.append((warn, px(200)))
            acc = ttk.Button(box, text="Accept", image=t.icon("check", "on_accent", 14), compound="left",
                             style="Accent.TButton", command=lambda s=s: self.accept(s))
            acc.grid(row=2 * i + 1, column=1, sticky="ne", pady=(px(5), px(5)))
            acc.allowed = True
            self.accept_buttons[f"encode {s.sources[0]}"] = acc

    def _formula_box(self) -> None:
        t, px = self.app.theme, self.app.theme.px
        self._section("Your own feature", "a formula of columns")
        box = tk.Frame(self.body, background=C["panel"])
        box.pack(fill="x", padx=(px(8), px(10)))
        box.columnconfigure(0, weight=1)
        old = getattr(self, "formula", None)
        old_text = old.value() if old is not None else ""
        old_name = self.formula_name.value() if old is not None else ""
        self.formula = PlaceholderEntry(box, placeholder="e.g. Fare / (SibSp + Parch + 1)")
        self.formula.grid(row=0, column=0, sticky="ew")
        self.formula_name = PlaceholderEntry(box, placeholder="name (optional)", width=18)
        self.formula_name.grid(row=0, column=1, sticky="ew", padx=(px(6), 0))
        if old_text:
            self.formula.set_value(old_text)
        if old_name:
            self.formula_name.set_value(old_name)
        self.check_btn = ttk.Button(box, text="Check", style="Small.TButton", command=self.check_formula)
        self.check_btn.grid(row=0, column=2, padx=(px(6), 0))
        self.add_formula_btn = ttk.Button(box, text="Accept", image=t.icon("check", "on_accent", 14), compound="left",
                                          style="Accent.TButton", command=self.accept_formula)
        self.add_formula_btn.grid(row=0, column=3, padx=(px(6), 0))
        self.add_formula_btn.state(["disabled"])
        self.add_formula_btn.allowed = False
        self.accept_buttons["(formula)"] = self.add_formula_btn
        self.formula.bind("<Return>", lambda e: self.check_formula())
        Tooltip(self.formula, "Column names, numbers, + - * / // % **, < > == !=, and / or / not and the functions "
                              "log, log1p, sqrt, abs, exp, round, clip, minimum, maximum, where, isna, notna.\n"
                              "Names with spaces go in backticks: `Flight Distance`.\nThe formula is checked piece "
                              "by piece; it never runs with eval.")
        self.formula_msg = tk.Label(box, text="It is measured like the suggestions, then you can accept it.",
                                    background=C["panel"], foreground=C["faint"], font=t.f["small"], anchor="w",
                                    justify="left")
        self.formula_msg.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(px(4), 0))
        self.wraps.append((self.formula_msg, px(40)))
        if self.svc.custom is not None:
            self._custom_result()

    def _custom_result(self) -> None:
        s = self.svc.custom
        if s is None or not hasattr(self, "formula_msg"):
            return
        color = STATUS_COLOR[s.status]
        self.formula_msg.configure(text=f"{STATUS_WORD[s.status]}: {s.reason}",
                                   foreground=C[color] if s.status in ("recommended", "leak") else C["muted"])
        ok = s.can_accept
        self.add_formula_btn.allowed = ok
        self.add_formula_btn.state(["!disabled"] if ok and not self.svc.busy else ["disabled"])

    def _toggle_skipped(self) -> None:
        self.show_skipped = not self.show_skipped
        self._fill(self.svc.result)

    @staticmethod
    def _fit_labels(width: int, fits) -> None:
        """Wrap labels to the width their frame really got (stable: the column's width doesn't depend on them)."""
        for label, others in fits:
            want = max(120, width - others)
            try:
                if int(label.cget("wraplength")) != want:
                    label.configure(wraplength=want)
            except tk.TclError:
                pass

    def _rewrap(self, _event=None) -> None:
        width = self.scroll.canvas.winfo_width()
        if width < 50:
            return
        for label, margin in self.wraps:
            try:
                label.configure(wraplength=max(160, width - margin))
            except tk.TclError:
                pass

    # ---------------------------------------------------------------- actions --
    def accept(self, s, force: bool = False) -> None:
        if self.svc.busy:
            return
        if not s.can_accept:
            if not force:
                return
            if not messagebox.askyesno(APP_NAME, f"'{s.name}' alone predicts the target almost perfectly "
                                                 f"({s.leak_metric} {s.leak_value:.3f}). That usually means it was "
                                                 "made from the target, and a model trained on it fails on new "
                                                 "data.\n\nAdd it anyway?", parent=self, icon="warning"):
                return
        self.svc.accept(s)

    def skip(self, s) -> None:
        self.svc.skipped.add(self._key_of(s))
        if self.selected is s:
            self.selected = None
        self._fill(self.svc.result)

    def _unskip(self, s) -> None:
        self.svc.skipped.discard(self._key_of(s))
        self._fill(self.svc.result)

    def check_formula(self) -> None:
        text = self.formula.value().strip()
        if not text:
            self.formula_msg.configure(text="Type a formula first, e.g. Fare / (SibSp + Parch + 1).",
                                       foreground=C["danger"])
            return
        self.formula_msg.configure(text="Checking…", foreground=C["muted"])
        self.svc.check_formula(text, self.formula_name.value().strip())

    def accept_formula(self) -> None:
        s = self.svc.custom
        if s is not None and s.can_accept and not self.svc.busy:
            self.svc.accept(s)
            self.formula.set_value("")
            self.formula_name.set_value("")

    def evaluate(self) -> None:
        self.svc.evaluate()

    # --------------------------------------------------------- accepted list --
    def _fill_accepted(self) -> None:
        t, px = self.app.theme, self.app.theme.px
        for w in self.flow.winfo_children():
            w.destroy()
        steps = self.svc.pipeline.steps
        self.acc_title.configure(text=f"Accepted features ({len(steps)})" if steps else "Accepted features")
        self.chips = []
        if not steps:
            self.acc_empty.pack(fill="x", after=self.flow)
            self.flow.configure(height=1)
            return
        self.acc_empty.pack_forget()
        for i, step in enumerate(steps):
            chip = tk.Frame(self.flow, background=C["accent_soft"], padx=px(8), pady=px(2))
            label = tk.Label(chip, text=step.name if len(step.outputs) == 1 else f"{step.name} ({len(step.outputs)})",
                             background=C["accent_soft"], foreground=C["text"], font=t.f["small_bold"])
            label.pack(side="left")
            x = ttk.Button(chip, image=t.icon_states("close", 12), style="Icon.TButton",
                           command=lambda i=i: self.remove(i))
            x.pack(side="left", padx=(px(4), 0))
            Tooltip(label, f"{step.label}\n" + "\n".join(step.code()[:6]) + "\n\nDouble-click to rename.")
            Tooltip(x, f"Remove '{step.name}'" + (" and the steps built on it" if self.svc.pipeline.dependents(i)
                                                   else ""))
            label.bind("<Double-Button-1>", lambda e, i=i: self.rename(i))
            self.chips.append(chip)
        self.after_idle(self.flow.reflow)

    def remove(self, index: int) -> None:
        if not self.svc.busy:
            self.svc.remove(index)

    def rename(self, index: int) -> None:
        if self.svc.busy:
            return
        step = self.svc.pipeline.steps[index]
        name = simpledialog.askstring(APP_NAME, f"New name for '{step.name}':", initialvalue=step.name, parent=self)
        if name and name.strip() and name.strip() != step.name:
            if name.strip() in self.svc.working.df.columns:
                messagebox.showerror(APP_NAME, f"A column called '{name.strip()}' already exists.", parent=self)
                return
            self.svc.rename(index, name.strip())

    def _fill_evaluation(self) -> None:
        t, px = self.app.theme, self.app.theme.px
        for w in self.eval_box.winfo_children():
            w.destroy()
        ev = self.svc.evaluation
        if ev is None:
            return
        stale = self.svc.current_evaluation is None
        head = f"5-fold cross-validation of {ev.target} ({ev.metric}), without → with {len(ev.new_columns)} new " \
               f"column(s)" + (f" · {ev.notes[0]}" if ev.notes else "")
        if stale:
            head += " · the features changed since: press Evaluate again"
        tk.Label(self.eval_box, text=head, background=C["panel"], foreground=C["faint"], font=t.f["small"],
                 anchor="w", justify="left").pack(fill="x")
        for score in ev.scores:
            color = "ok" if score.significant and score.gain > 0 else "danger" if score.significant else "muted"
            line = tk.Frame(self.eval_box, background=C["panel"])
            line.pack(fill="x")
            tk.Label(line, text=f"{score.name}:", background=C["panel"], foreground=C["text"], font=t.f["small_bold"],
                     anchor="w").pack(side="left")
            tk.Label(line, text=score.text(), background=C["panel"], foreground=C[color], font=t.f["small"],
                     anchor="w").pack(side="left", padx=(px(6), 0))

    # --------------------------------------------------------------- preview --
    def _preview_clear(self) -> None:
        self._plot_token = None                 # plots still queued for the old preview are dropped
        if self._plot_job is not None:
            self.after_cancel(self._plot_job)
            self._plot_job = None
        for canvas in self.preview_canvases:
            release_canvas(canvas)          # frees the picture on this thread (see widgets.release_canvas)
        self.preview_canvases = []
        for w in self.preview.winfo_children():
            w.destroy()

    def _preview_empty(self) -> None:
        self.selected = None
        self._preview_clear()
        t, px = self.app.theme, self.app.theme.px
        tk.Label(self.preview, text="Click a suggestion to see its first rows, its distribution and how it relates "
                                    "to the target.", background=C["panel"], foreground=C["faint"],
                 font=t.f["small"], anchor="w", justify="left", wraplength=px(320)).pack(fill="x", padx=px(10),
                                                                                       pady=px(14))

    def show_preview(self, s) -> None:
        t, px = self.app.theme, self.app.theme.px
        self.selected = s
        self._preview_clear()
        res = self.svc.result
        ctx = res.context if res is not None else None
        if ctx is None or s.values is None:
            self._preview_empty()
            return
        pad = dict(fill="x", padx=px(10))
        tk.Label(self.preview, text=s.name, background=C["panel"], foreground=C["text"], font=t.f["h3"],
                 anchor="w").pack(**pad, pady=(px(10), 0))
        subtitle = s.title if s.title == s.step.label else f"{s.title} · {s.step.label}"
        tk.Label(self.preview, text=subtitle, background=C["panel"], foreground=C["faint"],
                 font=t.f["small"], anchor="w", justify="left", wraplength=px(340)).pack(**pad)
        status = s.status
        facts = [f"{s.mi_text()} · {STATUS_WORD[status]}"]
        if s.leak_metric:
            facts.append(f"Alone it predicts {ctx.target.name} with {s.leak_metric} {s.leak_value:.3f}"
                         + (" (above 0.99: leakage?)" if s.leak else ""))
        if s.redundant_with:
            facts.append(f"Repeats '{s.redundant_with}' ({'|r|' if s.redundant_how == 'r' else 'same groups'} "
                         f"{s.redundant_value:.2f})")
        if s.link:
            facts.append(s.link)
        facts.append(s.why)
        if s.warning:
            facts.append(s.warning)
        for i, f in enumerate(facts):
            tk.Label(self.preview, text=f, background=C["panel"],
                     foreground=C[STATUS_COLOR[status]] if i == 0 and status in ("recommended", "leak") else
                     C["muted"], font=t.f["small_bold"] if i == 0 else t.f["small"], anchor="w", justify="left",
                     wraplength=px(340)).pack(**pad, pady=(px(4) if i == 0 else px(2), 0))
        # first rows
        cols = [c for c in s.sources if c in ctx.df.columns][:3]
        target = ctx.target.name
        table = ctx.df[cols + ([target] if target not in cols else [])].head(PREVIEW_ROWS).copy()
        table.insert(len(cols), s.name, s.values.head(PREVIEW_ROWS))
        tk.Label(self.preview, text=f"First {len(table)} rows", background=C["panel"], foreground=C["text"],
                 font=t.f["small_bold"], anchor="w").pack(**pad, pady=(px(10), px(2)))
        box = ttk.Frame(self.preview, style="Inset.TFrame", padding=px(2))
        box.pack(**pad)
        tree = ttk.Treeview(box, columns=list(range(len(table.columns))), show="headings", height=len(table),
                            selectmode="none")
        for i, c in enumerate(table.columns):
            tree.heading(i, text=short(c, 16), anchor="w")
            tree.column(i, width=px(110 if c == s.name else 90), anchor="w", stretch=True)
        for _, row in table.iterrows():
            tree.insert("", "end", values=[_cell(v) for v in row.tolist()])
        tree.pack(fill="x")
        # plots
        self._plots(s, ctx)
        self.pscroll.to_top()

    def _plots(self, s, ctx) -> None:
        """The distribution and the link with the target, drawn one plot per step of the event loop (each takes a
        few tenths of a second), so the window keeps answering while the preview fills in."""
        target = ctx.target.name
        frame = ctx.df[[c for c in dict.fromkeys(s.sources + [target]) if c in ctx.df.columns]].copy()
        frame[s.name] = s.values
        if len(frame) > PLOT_ROWS:
            frame = frame.sample(PLOT_ROWS, random_state=0)
        ds = dataset_from_frame(frame[[s.name, target]], "preview.csv")
        if scoring.feature_kind(s.values) == "number":
            first = ("Distribution", "hist", {"cols": [s.name]}, {})
        else:
            first = ("Distribution", "count", {"col": s.name}, {"labels": "count", "top_n": 12})
        style = self.page.collect_style()
        style = StyleSettings(theme=style.theme, palette=style.palette, context="paper")
        token = self._plot_token = object()

        def second():
            try:
                _, ideas, _ = recommend_plots(ds.df, target=target, infos=ds.columns)
                idea = next((i for i in ideas if set(i.columns) == {s.name, target} and i.graph in GRAPH_BY_ID), None)
            except Exception as exc:  # noqa: BLE001 - the preview still shows the distribution
                log_error("Feature Lab preview: no plot idea", exc)
                return None
            return None if idea is None else (f"With {target}", idea.graph, idea.sel, idea.opts)

        def step(todo):
            self._plot_job = None
            if self._plot_token is not token or not todo:
                return
            spec = todo[0]() if callable(todo[0]) else todo[0]
            if spec is not None:
                self._draw_preview_plot(ds, style, *spec)
            if len(todo) > 1:
                self._plot_job = self.after(PLOT_GAP_MS, lambda: step(todo[1:]))

        self._plot_job = self.after(PLOT_GAP_MS, lambda: step([first, second]))

    def _draw_preview_plot(self, ds, style, title, gid, sel, opts) -> None:
        px = self.app.theme.px
        graph = GRAPH_BY_ID[gid]
        full = {r.key: sel.get(r.key, [] if r.multi else None) for r in graph.roles}
        options = {o.key: o.default for o in graph.options}
        options.update({k: v for k, v in opts.items() if k in options})
        if gid == "count" and full.get("col") in ds.df.columns:     # small plot: numbers on a few bars only
            hue = full.get("hue")
            bars = ds.df[full["col"]].nunique() * (ds.df[hue].nunique() if hue in ds.df.columns and hue != full["col"]
                                                   else 1)
            options["labels"] = "count" if bars <= 6 else "none"
        with matplotlib.rc_context():         # the preview's style must not become the main plot's
            try:
                built = build_plot(graph, ds, full, options, RowSettings(), style, LabelSettings(title=title))
                fig, _, _ = run_plot(built)
            except (PlotError, Exception) as exc:  # noqa: BLE001 - one preview plot failing is not fatal
                log_error(f"Feature Lab preview plot ({gid})", exc)
                return
            width_in = min(6.0, max(2.6, self._plot_space() / fig.dpi))
            fig.set_size_inches(width_in, max(2.2, min(3.4, width_in * 0.66)))
            fit_titles(fig, width_in)
            if self.page.plot_view.paper_var.get():
                apply_dark_paper(fig)
            canvas = FigureCanvasTkAgg(fig, master=self.preview)
            # A fixed-size picture: the preview draws it again itself when its width changes, so matplotlib's own
            # resize handler (which would draw every plot a second time as soon as it is shown) is not needed.
            canvas.get_tk_widget().unbind("<Configure>")
            canvas.draw()
        widget = canvas.get_tk_widget()
        widget.configure(highlightthickness=0, borderwidth=0, background=C["panel"])
        widget.pack(anchor="w", padx=px(10), pady=(px(10), 0))
        self.preview_canvases.append(canvas)

    def _plot_space(self) -> int:
        """Pixels the preview plots can use (the preview's width minus its padding)."""
        px = self.app.theme.px
        width = self.pscroll.canvas.winfo_width()
        space = (width if width > 50 else px(470)) - px(26)
        self._plot_width = space
        return max(px(240), space)

    def _preview_resized(self, event) -> None:
        """Redraw the plots when the preview got clearly wider or narrower (the sash or the window moved)."""
        if not self.preview_canvases or self.selected is None:
            return
        if abs((event.width - self.app.theme.px(26)) - self._plot_width) < self.app.theme.px(40):
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(250, self._resize_now)

    def _resize_now(self) -> None:
        self._resize_job = None
        self.on_theme()

    def _first_split(self, event) -> None:
        """Give the list a bit more than half of the width the first time the tab has a real size."""
        if self._split_done or event.width < 400:
            return
        self._split_done = True
        try:
            self.split.sashpos(0, int(event.width * 0.57))
        except tk.TclError:
            pass

    def on_theme(self) -> None:
        """Redraw the preview plots on the new paper (light / dark look, or View > Dark graph paper)."""
        if self.selected is None or self._redraw_pending:
            return
        self._redraw_pending = True

        def redraw():
            self._redraw_pending = False
            if self.selected is not None:
                self.show_preview(self.selected)
        self.after_idle(redraw)

    # ----------------------------------------------------------------- export --
    def _ready(self) -> bool:
        if self.svc.working is None:
            return False
        if self.svc.busy:
            messagebox.showinfo(APP_NAME, "The Lab is still working; try again in a moment.", parent=self)
            return False
        return True

    def show_code(self) -> None:
        if self._ready():
            CodeDialog(self, exporter.clean_script(self.svc.base, self.svc.pipeline, self.svc.target()),
                       f"{self.svc.base.path.stem}_clean.py")

    def save_clean(self) -> None:
        if not self._ready():
            return
        code = exporter.clean_script(self.svc.base, self.svc.pipeline, self.svc.target())
        path = self._ask_save(f"{self.svc.base.path.stem}_clean.py", [("Python file", "*.py")], ".py")
        if path:
            path.write_text(code, encoding="utf-8")
            activity.record_export(self.app.cfg, path.name)
            settings.save(self.app.cfg)
            self._done(f"Saved {path.name}: run it next to the data to rebuild this table.")

    def save_notebook(self) -> None:
        if not self._ready():
            return
        ev = self.svc.current_evaluation
        text = exporter.notebook_json(self.svc.base, self.svc.pipeline, self.svc.target(), ev)
        path = self._ask_save(f"{self.svc.base.path.stem}_features.ipynb", [("Jupyter notebook", "*.ipynb")], ".ipynb")
        if path:
            path.write_text(text, encoding="utf-8")
            activity.record_export(self.app.cfg, path.name)
            settings.save(self.app.cfg)
            self._done(f"Saved {path.name}: open it in Jupyter or upload it to Kaggle.")

    def submission(self) -> None:
        if not self._ready():
            return
        if not self.svc.target():
            messagebox.showinfo(APP_NAME, "Pick the target first: the submission predicts it.", parent=self)
            return
        SubmissionDialog(self)

    def _ask_save(self, name, types, ext):
        path = filedialog.asksaveasfilename(parent=self, title="Save", initialfile=name, defaultextension=ext,
                                            initialdir=str(self.svc.base.path.parent), filetypes=types)
        return Path(path) if path else None

    def _done(self, text: str) -> None:
        self.svc.status = (text, "ok")
        self.message.configure(text=text, foreground=C["ok"])


def _cell(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "–"
    if isinstance(value, float):
        return f"{value:.4g}"
    text = str(value)
    return text if len(text) <= 28 else text[:27] + "…"


# =========================================================================== #
# Dialogs
# =========================================================================== #

class CodeDialog(tk.Toplevel):
    """The pipeline as clean.py: read-only, with Copy and Save."""

    def __init__(self, view, code: str, name: str):
        app = view.app
        super().__init__(app)
        t, px = app.theme, app.theme.px
        self.view, self.code, self.name = view, code, name
        self.title(name)
        self.configure(background=C["panel"])
        self.transient(app)
        t.dark_title_bar(self)
        bar = tk.Frame(self, background=C["panel"])
        bar.pack(fill="x", padx=px(14), pady=(px(12), px(8)))
        tk.Label(bar, text="The accepted steps as plain pandas: it rebuilds the Lab's table from the raw file.",
                 background=C["panel"], foreground=C["muted"], font=t.f["small"]).pack(side="left")
        ttk.Button(bar, text="Save…", style="TButton", command=self.save).pack(side="right")
        self.copy_btn = ttk.Button(bar, text="Copy", style="Accent.TButton", command=self.copy)
        self.copy_btn.pack(side="right", padx=(0, px(6)))
        box = ttk.Frame(self, style="Code.TFrame", padding=px(4))
        box.pack(fill="both", expand=True, padx=px(14), pady=(0, px(14)))
        text = tk.Text(box, wrap="none", font=t.f["mono"], background=CODE["bg"], foreground=CODE["fg"],
                       relief="flat", borderwidth=0, padx=px(12), pady=px(10), highlightthickness=0,
                       width=110, height=32)
        text.fixed_colors = True
        ys = AutoScrollbar(box, orient="vertical", command=text.yview, style="Code.Vertical.TScrollbar")
        xs = AutoScrollbar(box, orient="horizontal", command=text.xview, style="Code.Horizontal.TScrollbar")
        text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        text.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        text.insert("1.0", code)
        text.configure(state="disabled")
        self.bind("<Escape>", lambda e: self.destroy())

    def copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.code)
        self.copy_btn.configure(text="Copied")
        self.after(1500, lambda: self.copy_btn.winfo_exists() and self.copy_btn.configure(text="Copy"))

    def save(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, initialfile=self.name, defaultextension=".py",
                                            filetypes=[("Python file", "*.py")])
        if path:
            Path(path).write_text(self.code, encoding="utf-8")
            self.view._done(f"Saved {Path(path).name}.")


class SubmissionDialog(tk.Toplevel):
    """Kaggle submission: pick the test file, its ID column and the model; the steps are applied to it."""

    def __init__(self, view):
        app = view.app
        super().__init__(app)
        t, px = app.theme, app.theme.px
        self.view, self.svc, self.test = view, view.svc, None
        self.title("Kaggle submission")
        self.configure(background=C["panel"])
        self.transient(app)
        t.dark_title_bar(self)
        outer = tk.Frame(self, background=C["panel"], padx=px(20), pady=px(16))
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="Kaggle submission", background=C["panel"], foreground=C["text"], font=t.f["h3"],
                 anchor="w").pack(fill="x")
        tk.Label(outer, text=f"The accepted steps are applied to the test file with what they learned on "
                             f"{self.svc.base.name} (nothing is learned again), a model is trained on all training "
                             f"rows, and it predicts {self.svc.target()} for each test row.",
                 background=C["panel"], foreground=C["muted"], font=t.f["small"], anchor="w", justify="left",
                 wraplength=px(480)).pack(fill="x", pady=(px(4), px(12)))
        grid = tk.Frame(outer, background=C["panel"])
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        ttk.Label(grid, text="Test file", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=px(4))
        self.file_lbl = tk.Label(grid, text="(none)", background=C["panel"], foreground=C["muted"], anchor="w")
        self.file_lbl.grid(row=0, column=1, sticky="ew", padx=(px(10), px(6)))
        ttk.Button(grid, text="Choose…", style="Small.TButton", command=self.choose).grid(row=0, column=2)
        ttk.Label(grid, text="ID column", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=px(4))
        self.id_var = tk.StringVar()
        self.id_box = ttk.Combobox(grid, textvariable=self.id_var, state="disabled", width=24)
        self.id_box.grid(row=1, column=1, sticky="w", padx=(px(10), 0))
        ttk.Label(grid, text="Model", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=px(4))
        self.model_var = tk.StringVar()
        models = {"Gradient boosting": "boosting", "Linear model": "linear"}
        ev = self.svc.current_evaluation
        best = ev.best() if ev is not None else None
        self.models = models
        self.model_var.set("Linear model" if best is not None and best.model == "linear" else "Gradient boosting")
        ttk.Combobox(grid, textvariable=self.model_var, values=list(models), state="readonly", width=24).grid(
            row=2, column=1, sticky="w", padx=(px(10), 0))
        if best is not None:
            tk.Label(grid, text=f"best in the last evaluation: {best.name}", background=C["panel"],
                     foreground=C["faint"], font=t.f["small"]).grid(row=2, column=2, sticky="w", padx=(px(6), 0))
        self.msg = tk.Label(outer, text="", background=C["panel"], foreground=C["danger"], font=t.f["small"],
                            anchor="w", justify="left", wraplength=px(480))
        self.msg.pack(fill="x", pady=(px(8), 0))
        buttons = tk.Frame(outer, background=C["panel"])
        buttons.pack(fill="x", pady=(px(12), 0))
        self.go = ttk.Button(buttons, text="Save submission…", style="Accent.TButton", command=self.save)
        self.go.pack(side="right")
        self.go.state(["disabled"])
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(0, px(8)))
        self.bind("<Escape>", lambda e: self.destroy())
        self.geometry(f"+{app.winfo_rootx() + px(200)}+{app.winfo_rooty() + px(120)}")

    def choose(self, path=None) -> None:
        path = path or filedialog.askopenfilename(parent=self, title="Test file", initialdir=str(self.svc.base.path.parent),
                                                  filetypes=[("CSV files", "*.csv *.tsv *.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            ds = load_csv(path)
        except Exception as exc:  # noqa: BLE001
            self.msg.configure(text=f"Couldn't read it: {exc}")
            log_error("Submission: the test file could not be read", exc)
            return
        need = sorted({c for s in self.svc.pipeline for c in s.cols} - set(ds.df.columns) -
                      set(self.svc.pipeline.outputs))
        self.test = ds.df
        self.file_lbl.configure(text=f"{Path(path).name} · {ds.shape_text}", foreground=C["text"])
        self.id_box.configure(values=list(ds.df.columns), state="readonly")
        guess = exporter.guess_id_column(ds.df, self.svc.working.df.columns)
        self.id_var.set(guess or ds.df.columns[0])
        if need:
            self.msg.configure(text=f"The test file has no column(s) {', '.join(need)}, which the steps need.")
            self.go.state(["disabled"])
            return
        self.msg.configure(text="", foreground=C["danger"])
        self.go.state(["!disabled"])

    def save(self, path=None) -> None:
        if self.test is None:
            return
        name = f"submission_{self.svc.base.path.stem}.csv"
        path = path or filedialog.asksaveasfilename(parent=self, initialfile=name, defaultextension=".csv",
                                                    initialdir=str(self.svc.base.path.parent),
                                                    filetypes=[("CSV", "*.csv")])
        if not path:
            return
        if self.svc.submission(self.test, self.id_var.get(), self.models[self.model_var.get()], Path(path)):
            self.destroy()
        else:
            self.msg.configure(text="The Lab is busy; try again in a moment.")


__all__ = ["CodeDialog", "FeatureLabView", "LabService", "SubmissionDialog", "make_working"]
