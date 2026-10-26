"""Plot suggestions inside the window ("Plot ideas"): the recommender's ranked plots and warnings.

* ``IdeaService``  runs the core analysis 'plot_suggestions' in a background thread (one job at a
                   time, cached per file + target + type overrides) and tells the views when done
* ``IdeasView``    the "Plot ideas" tab: target picker, warnings (most serious first), then the
                   suggestions as a table (rank · columns · plot type · why) with a Plot it button
* ``IdeaCard``     a smaller card for the gallery row
* ``TypesDialog``  "Column types": treat a column as number / category / ID / … and run again

Everything here only renders results; the analysis itself lives in plotstudio.core.
"""
from __future__ import annotations

import copy
import gc
import threading
import tkinter as tk
import traceback
from tkinter import messagebox, ttk

from . import APP_NAME
from .core import analyses
from .core import overrides as type_overrides
from .graphs import GRAPH_BY_ID, fits
from .log import log_error, log_path, logger
from .theme import C
from .widgets import AutoScrollbar, ScrollFrame, Tile, Tooltip

NONE = "(none)"
LEVEL_COLOR = {"leak": "danger", "warn": "sev_warn", "check": "sev_check", "info": "faint"}
LEVEL_WORD = {"leak": "Leakage", "warn": "Important", "check": "Worth checking", "info": "Good to know"}
MAJOR = ("leak", "warn")


def fits_app(idea, columns: dict) -> bool:
    """True if the idea's graph exists and every chosen column fits its slot (columns = the scan)."""
    graph = GRAPH_BY_ID.get(idea.graph)
    if graph is None:
        return False
    roles = {r.key: r for r in graph.roles}
    for key, value in idea.sel.items():
        if key not in roles:
            return False
        for col in (value if isinstance(value, list) else [value]):
            if col not in columns or not fits(roles[key], columns[col]):
                return False
    return True


def short(text, n: int) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def show_error(parent, title: str, exc: BaseException, details: str = "") -> None:
    """A dialog with the short message; the traceback goes to the log file."""
    log_error(title, exc, details)
    try:
        messagebox.showerror(APP_NAME, f"{title}\n\n{type(exc).__name__}: {exc}\n\nDetails were written to "
                                       f"{log_path()}", parent=parent)
    except tk.TclError:
        pass        # the window is closing


# =========================================================================== #
# Background worker
# =========================================================================== #

class IdeaService:
    """Plot suggestions for the loaded file, computed off the window's thread."""

    def __init__(self, app):
        self.app = app
        self.cache: dict = {}           # key -> PlotSuggestions
        self.listeners: list = []
        self.job: dict | None = None
        self.wanted = None              # (ds, target, overrides) asked for last
        self.result = None              # PlotSuggestions for `wanted`, once ready
        self.result_ds = None           # the Dataset `result` belongs to
        self.error: BaseException | None = None
        self.progress = (0.0, "")

    @staticmethod
    def key(ds, target, overrides) -> tuple:
        return id(ds), target, tuple(sorted((overrides or {}).items()))

    def listen(self, fn) -> None:
        self.listeners.append(fn)

    def _emit(self, event: str) -> None:
        for fn in list(self.listeners):
            try:
                fn(event)
            except tk.TclError as exc:          # a view that is being destroyed
                logger().warning("plot ideas: a view could not update (%s)", exc)

    @property
    def busy(self) -> bool:
        return self.job is not None and self.result is None

    def request(self, ds, target, overrides=None) -> None:
        """Ask for the suggestions of ds with this target and these type overrides."""
        if ds is None:
            return
        overrides = dict(overrides or {})
        if self.wanted is None or self.wanted[0] is not ds:
            self.cache = {}                     # a new file: forget the old one
        self.wanted = (ds, target, overrides)
        self.error = None
        key = self.key(ds, target, overrides)
        if key in self.cache:
            self.result, self.result_ds = self.cache[key], ds
            self._emit("done")
            return
        self.result = None
        if self.job is not None:
            if self.job["key"] != key:
                self._emit("start")             # starts as soon as the running job is done
            return
        self._start(ds, target, overrides, key)

    def _start(self, ds, target, overrides, key) -> None:
        columns = {name: copy.copy(info) for name, info in ds.columns.items()}   # a snapshot for the thread
        job = {"key": key, "ds": ds, "progress": (0.0, "Starting"), "result": None, "error": None, "details": ""}
        self.job = job

        def tell(fraction, text):
            job["progress"] = (fraction, text)

        def work():
            try:
                res = analyses.run("plot_suggestions", ds.df, target=target, overrides=overrides,
                                   infos=columns, progress=tell)
                res.suggestions = [s for s in res.suggestions if fits_app(s, columns)]
                for i, s in enumerate(res.suggestions):
                    s.rank = i + 1
                job["result"] = res
            except Exception as exc:  # noqa: BLE001 - reported to the user in _poll
                job["details"] = traceback.format_exc()
                job["error"] = exc

        gc.collect()      # free dead Tk variables HERE: Tk must not delete them from the worker thread
        threading.Thread(target=work, daemon=True).start()
        self._emit("start")
        self.app.after(60, self._poll)

    def _poll(self) -> None:
        job = self.job
        if job is None:
            return
        if job["result"] is None and job["error"] is None:
            self.progress = job["progress"]
            self._emit("progress")
            self.app.after(80, self._poll)
            return
        self.job = None
        wanted_key = self.key(*self.wanted) if self.wanted else None
        if job["error"] is None:
            self.cache[job["key"]] = job["result"]
        if job["key"] == wanted_key:
            if job["error"] is not None:
                self.error = job["error"]
                self._emit("error")
                show_error(self.app, "Couldn't work out the plot suggestions.", job["error"], job["details"])
            else:
                self.result, self.result_ds = job["result"], job["ds"]
                self._emit("done")
        elif job["error"] is not None:
            log_error("Plot suggestions for an earlier request failed.", job["error"], job["details"])
        if self.wanted is not None and self.job is None and wanted_key not in self.cache and job["key"] != wanted_key:
            self.request(*self.wanted)          # the target or the types changed while this ran


class Dot(tk.Canvas):
    """A small round severity mark that follows the light / dark look."""

    def __init__(self, master, token: str, size: int, bg: str = "panel"):
        super().__init__(master, width=size, height=size, highlightthickness=0, borderwidth=0, background=C[bg])
        self.token, self.size = token, size
        self.on_theme()

    def on_theme(self) -> None:
        self.delete("all")
        s = self.size
        self.create_oval(1, 1, s - 1, s - 1, fill=C[self.token], outline="")


# =========================================================================== #
# Gallery card
# =========================================================================== #

class IdeaCard(Tile):
    """One idea in the gallery: the graph preview, what to plot and why (short)."""

    def __init__(self, master, app, idea):
        t, px = app.theme, app.theme.px
        super().__init__(master, command=lambda: app.work.open_idea(idea), padding=px(9))
        self.app, self.idea, self.idea_ds = app, idea, None
        img = app.thumbs.get(idea.graph)
        wrap = (img.width() if img else px(200)) - px(4)
        self.picture = tk.Label(self, image=img, background=C["panel"], borderwidth=0) if img else \
            tk.Label(self, text=idea.plot, width=24, height=6, background=C["accent_soft"], foreground=C["accent"])
        self.picture.pack(anchor="w")
        top = tk.Frame(self, background=C["panel"])
        top.pack(fill="x", padx=px(2), pady=(px(10), 0))
        ttk.Label(top, text=str(idea.rank), style="Badge.TLabel" if idea.rank == 1 else "SoftBadge.TLabel").pack(
            side="left", anchor="n")
        tk.Label(top, text=short(idea.title, 30), background=C["panel"], foreground=C["text"], font=t.f["h3"],
                 anchor="w", justify="left", wraplength=wrap - px(30)).pack(side="left", fill="x", padx=(px(8), 0))
        tk.Label(self, text=idea.plot[:1].upper() + idea.plot[1:], background=C["panel"], foreground=C["accent"],
                 font=t.f["small_bold"], anchor="w").pack(fill="x", padx=px(2), pady=(px(4), 0))
        tk.Label(self, text=short(idea.reason, 120), background=C["panel"], foreground=C["muted"], font=t.f["small"],
                 wraplength=wrap, justify="left", anchor="w").pack(fill="x", padx=px(2), pady=(px(2), px(2)))
        self.wire()
        Tooltip(self, f"{idea.title}: {idea.plot}\n{idea.reason}" + (f"\n{idea.stat}" if idea.stat else "") +
                "\n\nClick to draw it.")

    def on_theme(self) -> None:
        img = self.app.thumbs.get(self.idea.graph)
        if img is not None:
            self.picture.configure(image=img)
        super().on_theme()


# =========================================================================== #
# The "Plot ideas" tab
# =========================================================================== #

class IdeasView(tk.Frame):
    """Target picker, warnings, then every suggestion with a Plot it button."""

    def __init__(self, master, page):
        super().__init__(master, background=C["panel"])
        self.page, self.app = page, page.app
        t, px = self.app.theme, self.app.theme.px
        head = tk.Frame(self, background=C["panel"])
        head.pack(fill="x", padx=px(16), pady=(px(12), px(4)))
        top = tk.Frame(head, background=C["panel"])
        top.pack(fill="x")
        self.title = tk.Label(top, text="Plot ideas", background=C["panel"], foreground=C["text"],
                              font=t.f["h3"], anchor="w")
        self.title.pack(side="left")
        self.types_btn = ttk.Button(top, text="Column types…", style="Small.TButton", command=self.open_types)
        self.types_btn.pack(side="right")
        Tooltip(self.types_btn, "Treat a column as a number, a category, an ID … and work the ideas out again. "
                                "The values don't change.")
        self.target_box = ttk.Combobox(top, textvariable=page.target_var, values=[NONE], state="readonly",
                                       width=22, height=18)
        self.target_box.pack(side="right", padx=(0, px(10)))
        self.target_box.bind("<<ComboboxSelected>>", page._target_changed)
        ttk.Label(top, text="Target", style="Panel.Bold.TLabel").pack(side="right", padx=(0, px(8)))
        Tooltip(self.target_box, "The column you want to predict: it is shown first, then the columns most "
                                 "linked to it. Same setting as Target under Columns.")
        self.subtitle = tk.Label(head, background=C["panel"], foreground=C["muted"], font=t.f["small"],
                                 anchor="w", justify="left")
        self.subtitle.pack(fill="x", pady=(px(4), 0))
        self.status_row = tk.Frame(head, background=C["panel"])
        self.progress = ttk.Progressbar(self.status_row, mode="determinate", maximum=1.0, length=px(220))
        self.progress.pack(side="left")
        self.status = tk.Label(self.status_row, background=C["panel"], foreground=C["muted"], font=t.f["small"])
        self.status.pack(side="left", padx=(px(10), 0))
        tk.Frame(self, background=C["border"], height=max(1, px(1))).pack(fill="x", padx=px(16), pady=(px(6), 0))
        self.scroll = ScrollFrame(self, t, bg=C["panel"])
        self.scroll.pack(fill="both", expand=True, padx=(px(8), px(4)), pady=(0, px(8)))
        self.body = self.scroll.body
        self.wraps: list = []               # (label, margin): wrap length follows the width
        self.show_minor = False
        self.plot_buttons: list = []        # one per suggestion, best first (tests use them too)
        self.scroll.canvas.bind("<Configure>", self._rewrap, add="+")
        self.bind("<Configure>", lambda e: self.subtitle.configure(wraplength=max(200, e.width - px(40))), add="+")
        self.app.ideas.listen(self.on_ideas)
        self.on_ideas("idle")

    def set_target_choices(self, values) -> None:
        self.target_box.configure(values=list(values))

    def open_types(self) -> None:
        if self.page.ds is not None:
            TypesDialog(self.page)

    # ---------------------------------------------------------------- events --
    def on_ideas(self, event: str) -> None:
        t, px = self.app.theme, self.app.theme.px
        svc, ds = self.app.ideas, self.page.ds
        if ds is None:
            self.subtitle.configure(text="Open a CSV file to get plot ideas for it.")
            self.types_btn.state(["disabled"])
            self._clear()
            return
        self.types_btn.state(["!disabled"])
        self.title.configure(text=f"Plot ideas for {ds.name}")
        if event in ("start", "progress") or (event == "idle" and svc.busy):
            fraction, text = svc.progress if event == "progress" else (0.0, "Starting")
            self.subtitle.configure(text="Working them out in the background; the window stays usable.")
            self.status_row.pack(fill="x", pady=(px(8), 0))
            self.progress.configure(value=fraction)
            self.status.configure(text=f"{text}…" if text else "Working…")
            return
        self.status_row.pack_forget()
        if event == "error":
            self._clear()
            tk.Label(self.body, text=f"Couldn't work out plot ideas: {type(svc.error).__name__}: {svc.error}\n"
                                     f"Details are in {log_path()}.",
                     background=C["panel"], foreground=C["danger"], font=t.f["small"], anchor="w",
                     justify="left").pack(fill="x", padx=px(8), pady=px(12))
            return
        res = svc.result
        if res is None or svc.result_ds is not ds:
            return
        parts = ["Best first: press Plot it to draw one (its code is in the Python code tab)."]
        if res.sample_note:
            parts.append(res.sample_note[:1].upper() + res.sample_note[1:] + ".")
        if res.overrides:
            parts.append(f"{len(res.overrides)} column type{'s' if len(res.overrides) > 1 else ''} set by you.")
        if res.seconds >= 0.05:
            parts.append(f"Worked out in {res.seconds:.1f} s.")
        if not res.target:
            parts.append("No target: pick the column you want to predict to rank what predicts it.")
        self.subtitle.configure(text="  ".join(parts))
        self._fill(res)

    # ---------------------------------------------------------------- build --
    def _clear(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()
        self.wraps = []
        self.plot_buttons = []

    def _fill(self, res) -> None:
        px = self.app.theme.px
        self._clear()
        if res.warnings:
            self._warnings(res.warnings)
        self._suggestions(res.suggestions)
        tk.Frame(self.body, background=C["panel"], height=px(16)).pack()
        self._rewrap()
        self.scroll.to_top()

    def _section(self, text: str, extra: str = "") -> tk.Frame:
        t, px = self.app.theme, self.app.theme.px
        head = tk.Frame(self.body, background=C["panel"])
        head.pack(fill="x", padx=px(8), pady=(px(16), px(6)))
        tk.Label(head, text=text, background=C["panel"], foreground=C["text"], font=t.f["bold"]).pack(side="left")
        if extra:
            tk.Label(head, text=extra, background=C["panel"], foreground=C["faint"], font=t.f["small"]).pack(
                side="left", padx=(px(10), 0), pady=(px(2), 0))
        return head

    def _warnings(self, notes) -> None:
        t, px = self.app.theme, self.app.theme.px
        head = self._section("Warnings")
        counts: dict = {}
        for n in notes:
            counts[n.level] = counts.get(n.level, 0) + 1
        for level in ("leak", "warn", "check", "info"):
            if counts.get(level):
                Dot(head, LEVEL_COLOR[level], px(9)).pack(side="left", padx=(px(12), px(4)))
                tk.Label(head, text=f"{LEVEL_WORD[level]} {counts[level]}", background=C["panel"],
                         foreground=C["muted"], font=t.f["small"]).pack(side="left")
        major = [n for n in notes if n.level in MAJOR]
        minor = [n for n in notes if n.level not in MAJOR]
        if not major:
            tk.Label(self.body, text="Nothing serious: no leakage, near-copies or heavy gaps.", background=C["panel"],
                     foreground=C["muted"], font=t.f["small"], anchor="w").pack(fill="x", padx=px(8))
        for n in major:
            self._note_row(n)
        if minor:
            if self.show_minor:
                for n in minor:
                    self._note_row(n)
            text = ("Hide" if self.show_minor else "Show") + f" {len(minor)} smaller note{'s' if len(minor) > 1 else ''}"
            ttk.Button(self.body, text=text, style="Link.TButton", command=self._toggle_minor).pack(
                anchor="w", padx=px(4), pady=(px(4), 0))

    def _note_row(self, note) -> None:
        t, px = self.app.theme, self.app.theme.px
        row = tk.Frame(self.body, background=C["panel"])
        row.pack(fill="x", padx=px(8), pady=(px(6), 0))
        Dot(row, LEVEL_COLOR[note.level], px(10)).pack(side="left", anchor="n", pady=(px(5), 0))
        text = tk.Frame(row, background=C["panel"])
        text.pack(side="left", fill="x", expand=True, padx=(px(10), 0))
        main = tk.Label(text, text=note.text[:1].upper() + note.text[1:], background=C["panel"],
                        foreground=C["text"], font=t.f["medium"] if note.level == "leak" else t.f["base"],
                        anchor="w", justify="left")
        main.pack(fill="x")
        self.wraps.append((main, px(70)))
        if note.action:
            act = tk.Label(text, text="→ " + note.action, background=C["panel"], foreground=C["muted"],
                           font=t.f["small"], anchor="w", justify="left")
            act.pack(fill="x")
            self.wraps.append((act, px(70)))

    def _suggestions(self, ideas) -> None:
        t, px = self.app.theme, self.app.theme.px
        self._section("Suggestions", f"{len(ideas)} · best first" if ideas else "")
        if not ideas:
            tk.Label(self.body, text="No plot suggestions: this file has no number, category or date columns that "
                                     "can be plotted (see the warnings above).", background=C["panel"],
                     foreground=C["muted"], font=t.f["small"], anchor="w", justify="left").pack(fill="x", padx=px(8))
            return
        table = tk.Frame(self.body, background=C["panel"])
        table.pack(fill="x", padx=(px(8), px(10)))
        table.columnconfigure(1, minsize=px(190))
        table.columnconfigure(2, minsize=px(150))
        table.columnconfigure(3, weight=1)
        for col, text in enumerate(("#", "Columns", "Plot type", "Why")):
            tk.Label(table, text=text, background=C["panel"], foreground=C["faint"], font=t.f["small_bold"],
                     anchor="w").grid(row=0, column=col, sticky="w", padx=(0, px(12)), pady=(0, px(4)))
        row = 1
        for idea in ideas:
            tk.Frame(table, background=C["border"], height=max(1, px(1))).grid(
                row=row, column=0, columnspan=5, sticky="ew")
            row += 1
            self._idea_row(table, row, idea)
            row += 1

    def _idea_row(self, table, row, idea) -> None:
        t, px = self.app.theme, self.app.theme.px
        pad = (px(9), px(9))
        ttk.Label(table, text=str(idea.rank), style="Badge.TLabel" if idea.rank == 1 else "SoftBadge.TLabel").grid(
            row=row, column=0, sticky="nw", padx=(0, px(12)), pady=pad)
        cols = f"{len(idea.columns)} columns" if idea.kind == "overview" else idea.title
        name = tk.Label(table, text=cols, background=C["panel"], foreground=C["text"], font=t.f["bold"], anchor="w",
                        justify="left", wraplength=px(180))
        name.grid(row=row, column=1, sticky="nw", padx=(0, px(12)), pady=pad)
        tk.Label(table, text=idea.plot[:1].upper() + idea.plot[1:], background=C["panel"], foreground=C["accent"],
                 font=t.f["small_bold"], anchor="w", justify="left", wraplength=px(140)).grid(
            row=row, column=2, sticky="nw", padx=(0, px(12)), pady=(px(11), px(9)))
        why = tk.Frame(table, background=C["panel"])
        why.grid(row=row, column=3, sticky="new", padx=(0, px(12)), pady=pad)
        reason = tk.Label(why, text=idea.reason, background=C["panel"], foreground=C["muted"], font=t.f["base"],
                          anchor="w", justify="left")
        reason.pack(fill="x")
        self.wraps.append((reason, px(500)))      # the other columns of the row take about this much
        if idea.stat:
            tk.Label(why, text=idea.stat, background=C["panel"], foreground=C["faint"], font=t.f["small"],
                     anchor="w").pack(fill="x", pady=(px(1), 0))
        btn = ttk.Button(table, text="Plot it", style="Small.TButton", command=lambda: self.page.open_idea(idea))
        btn.grid(row=row, column=4, sticky="ne", pady=(px(5), px(5)))
        self.plot_buttons.append(btn)
        graph = GRAPH_BY_ID[idea.graph].name
        Tooltip(btn, f"Draw it: {graph}" + (" with a log scale" if idea.logx or idea.logy else "") +
                (f" ({', '.join(idea.columns)})" if idea.kind != "overview" else ""))
        if idea.kind == "overview":
            Tooltip(name, ", ".join(idea.columns))

    def _toggle_minor(self) -> None:
        self.show_minor = not self.show_minor
        if self.app.ideas.result is not None:
            top = self.scroll.canvas.yview()[0]
            self._fill(self.app.ideas.result)
            self.after_idle(lambda: self.scroll.canvas.yview_moveto(top))

    def _rewrap(self, _event=None) -> None:
        width = self.scroll.canvas.winfo_width()
        if width < 50:
            return
        for label, margin in self.wraps:
            try:
                label.configure(wraplength=max(160, width - margin))
            except tk.TclError:
                pass                            # the label was rebuilt meanwhile


# =========================================================================== #
# Column types
# =========================================================================== #

class TypesDialog(tk.Toplevel):
    """Choose how each column is treated (relabel only: the values never change)."""

    def __init__(self, page):
        app, ds = page.app, page.ds
        super().__init__(app)
        self.page, self.app, self.ds = page, app, ds
        t, px = app.theme, app.theme.px
        self.title("Column types")
        self.configure(background=C["panel"])
        self.transient(app)
        app.theme.dark_title_bar(self)
        self.choice = dict(page.type_overrides)          # column -> kind (only the changed ones)
        base = type_overrides.base(ds)
        outer = tk.Frame(self, background=C["panel"], padx=px(20), pady=px(16))
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text=f"Column types for {ds.name}", background=C["panel"], foreground=C["text"],
                 font=t.f["h3"], anchor="w").pack(fill="x")
        tk.Label(outer, text="How the plot ideas and the column slots treat each column. Only the label changes, "
                             "never the values (converting values comes with the cleaning steps).",
                 background=C["panel"], foreground=C["muted"], font=t.f["small"], anchor="w", justify="left",
                 wraplength=px(560)).pack(fill="x", pady=(px(4), px(10)))
        box = ttk.Frame(outer, style="Inset.TFrame", padding=px(3))
        box.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(box, columns=(0, 1, 2), show="headings", selectmode="browse", height=12)
        ys = AutoScrollbar(box, orient="vertical", command=self.tree.yview, style="Field.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        for i, (head, width) in enumerate((("Column", 200), ("Detected", 190), ("Use as", 200))):
            self.tree.heading(i, text=head, anchor="w")
            self.tree.column(i, width=px(width), anchor="w", stretch=(i == 2))
        self.tree.tag_configure("changed", foreground=C["accent"])
        self.items = {}
        for name, info in base.items():
            self.items[self.tree.insert("", "end", values=(name, info.kind_label, ""))] = name
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        row = tk.Frame(outer, background=C["panel"])
        row.pack(fill="x", pady=(px(12), 0))
        self.which = tk.Label(row, text="Pick a column above", background=C["panel"], foreground=C["text"],
                              font=t.f["bold"], anchor="w")
        self.which.pack(side="left")
        self.kind_var = tk.StringVar(value="")
        self.kind_box = ttk.Combobox(row, textvariable=self.kind_var, state="disabled", width=30, height=10)
        self.kind_box.pack(side="left", padx=(px(10), 0))
        self.kind_box.bind("<<ComboboxSelected>>", self._chosen)
        buttons = tk.Frame(outer, background=C["panel"])
        buttons.pack(fill="x", pady=(px(16), 0))
        ttk.Button(buttons, text="Reset all", style="Ghost.TButton", command=self._reset).pack(side="left")
        ttk.Button(buttons, text="Apply and run again", style="Accent.TButton", command=self._apply).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(0, px(8)))
        self.bind("<Escape>", lambda e: self.destroy())
        self._refresh()
        first = next(iter(self.items), None)
        if first:
            self.tree.selection_set(first)
            self.tree.focus(first)
        self.geometry(f"+{app.winfo_rootx() + px(160)}+{app.winfo_rooty() + px(90)}")
        self.grab_set()
        self.tree.focus_set()

    def _refresh(self) -> None:
        for item, name in self.items.items():
            kind = self.choice.get(name, type_overrides.AUTO)
            self.tree.set(item, 2, type_overrides.LABELS[kind])
            self.tree.item(item, tags=("changed",) if kind != type_overrides.AUTO else ())

    def _selected(self, _e=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        name = self.items[sel[0]]
        kinds = type_overrides.allowed(self.ds, name)
        self.which.configure(text=f"Use '{short(name, 24)}' as")
        self.kind_box.configure(values=[type_overrides.LABELS[k] for k in kinds], state="readonly")
        self.kind_var.set(type_overrides.LABELS[self.choice.get(name, type_overrides.AUTO)])

    def _chosen(self, _e=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        name = self.items[sel[0]]
        kind = next(k for k, label in type_overrides.LABELS.items() if label == self.kind_var.get())
        if kind == type_overrides.AUTO:
            self.choice.pop(name, None)
        else:
            self.choice[name] = kind
        self._refresh()

    def _reset(self) -> None:
        self.choice = {}
        self._refresh()
        self._selected()

    def _apply(self) -> None:
        overrides = dict(self.choice)
        self.grab_release()
        self.destroy()
        self.page.set_type_overrides(overrides)
