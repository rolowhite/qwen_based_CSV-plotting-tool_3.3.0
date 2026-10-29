"""The Ceasar tab: a local assistant for the first hours with a data file.

* ``CeasarService``   the loaded file's edits (with undo / redo), the chat memory, and the background jobs.
                      It works on the file as loaded (what Feature Lab starts from): every edit gives the app a new
                      starting table, so every tab, the plots and the exported code follow.
* ``CeasarView``      the tab: starter tasks and a chat on the left, the live table on the right.

Everything it does to the table is pandas code that is shown, run by core.ceasar.sandbox on a copy, and undoable. The
model (Ollama) only writes that code and phrases things; tasks and reports work without it.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
import traceback
from dataclasses import dataclass
from tkinter import filedialog, ttk
from typing import Any, List, Optional

import pandas as pd

from .core import export as exporter
from .core.ceasar import agent, diff as differ, profile as profiling, sandbox, tasks as task_list
from .core.notebook import ollama
from .data import Dataset, scan_column
from .log import log_error
from .theme import C
from .widgets import AutoScrollbar, PlaceholderEntry, Tooltip

TABLE_ROWS = 300
TABLE_COLUMNS = 60
PLACEHOLDER = "Tell Ceasar what to do, e.g. make Age 18 where Name starts with Master"
OLLAMA_HINT = ("The chat needs Ollama running on this computer (the same one the Notebook uses). The tasks above work "
               "without it.")


@dataclass
class Edit:
    title: str
    code: str
    summary: str = ""
    kind: str = "change"


def make_edited(original: Dataset, df: pd.DataFrame, edits: List[Edit]) -> Dataset:
    """The file as loaded with the edits applied, as a Dataset: columns scanned again, and the code every plot exports
    starts with the edits (so it still runs on the raw file)."""
    columns = {c: scan_column(c, df[c]) for c in df.columns}
    code = list(original.load_code)
    if edits:
        code += ["", "# Ceasar: the edits made in the Ceasar tab", "import math, re"]
        for e in edits:
            code += [f"# {e.title}"] + e.code.strip().split("\n")
    return Dataset(path=original.path, df=df, columns=columns, load_code=code, notes=list(original.notes),
                   seconds=original.seconds, sep=original.sep, encoding=original.encoding, header=original.header)


def replay(original: Dataset, edits: List[Edit]) -> pd.DataFrame:
    df = original.df
    for e in edits:
        df = sandbox.run(df, e.code).df
    return df


def table_text(answer: Any, rows: int = 25, cols: int = 12) -> str:
    """A report's result as text for the chat."""
    if isinstance(answer, pd.Series):
        answer = answer.to_frame()
    if isinstance(answer, pd.DataFrame):
        if answer.empty:
            return "(nothing)"
        shown = answer.iloc[:rows, :cols]
        text = shown.to_string(max_colwidth=26)
        extra = []
        if len(answer) > rows:
            extra.append(f"{len(answer) - rows:,} more rows")
        if answer.shape[1] > cols:
            extra.append(f"{answer.shape[1] - cols} more columns")
        return text + (f"\n… {', '.join(extra)}" if extra else "")
    return str(answer)


# =========================================================================== #
# The service
# =========================================================================== #

class CeasarService:
    def __init__(self, app):
        self.app = app
        self.original: Optional[Dataset] = None
        self.edits: List[Edit] = []
        self.undone: List[Edit] = []
        self.memory: list = []                  # [(instruction, the model's JSON reply)]
        self.listeners: list = []
        self.job: Optional[dict] = None
        self.chat: Optional[ollama.Chat] = None
        self.greeted = False
        self.profile: Optional[profiling.Profile] = None
        self._profile_for = None
        self._models = None
        app.lab.listen(self._lab_event)

    # ------------------------------------------------------------------ events --
    def listen(self, fn) -> None:
        self.listeners.append(fn)

    def emit(self, event: str, **data) -> None:
        for fn in list(self.listeners):
            try:
                fn(event, data)
            except tk.TclError as exc:          # a view that is being destroyed
                log_error("Ceasar: a view could not update", exc)

    def _lab_event(self, event: str) -> None:
        if event == "reset":                    # a newly loaded file: a fresh start
            self.stop()
            self.original = self.app.lab.base
            self.edits, self.undone, self.memory = [], [], []
            self.greeted, self.profile, self._profile_for = False, None, None
            self.emit("reset")
        elif event == "changed":
            self.emit("table")

    @property
    def ready(self) -> bool:
        return self.original is not None and self.app.lab.base is not None

    @property
    def busy(self) -> bool:
        return self.job is not None

    @property
    def source(self) -> Dataset:
        return self.app.lab.base

    @property
    def table(self) -> Optional[Dataset]:
        return self.app.lab.working

    # -------------------------------------------------------------------- jobs --
    def _start(self, text: str, work, done) -> bool:
        if self.job is not None:
            return False
        job = {"text": text, "result": None, "error": None, "trace": "", "ended": False, "done": done,
               "started": time.monotonic()}
        self.job = job

        def target():
            try:
                job["result"] = work()
            except BaseException as exc:  # noqa: BLE001 - handed to the Tk thread
                job["error"], job["trace"] = exc, traceback.format_exc()
            job["ended"] = True
        threading.Thread(target=target, daemon=True).start()
        self.emit("busy", text=text)
        self.app.after(60, self._poll, job)
        return True

    def _poll(self, job) -> None:
        if job is not self.job:                 # stopped, or a new file was opened: the result is dropped
            return
        if not job["ended"] or self.app.lab.busy:     # a Feature Lab job would put the old table back after us
            self.app.after(80, self._poll, job)
            return
        self.job = None
        exc = job["error"]
        if exc is None:
            try:
                job["done"](job["result"])
            except Exception as err:  # noqa: BLE001
                log_error("Ceasar: showing a result failed", err, traceback.format_exc())
                self.emit("problem", text=f"Something went wrong showing that ({type(err).__name__}: {err}).")
        elif isinstance(exc, (ollama.Cancelled,)):
            self.emit("say", text="Stopped.", muted=True)
        elif isinstance(exc, ollama.NotReady):
            self._models = None
            self.emit("problem", text=f"{exc}")
        elif isinstance(exc, ollama.OllamaError):
            self.emit("problem", text=f"{exc} {OLLAMA_HINT}")
        else:
            log_error("Ceasar: a job failed", exc, job["trace"])
            self.emit("problem", text=f"That did not work: {type(exc).__name__}: {exc}")
        self.emit("idle")

    def stop(self) -> None:
        """Stop now: the model is cancelled and whatever the job still returns is dropped (pandas work that is
        already running cannot be interrupted, but it no longer holds up the tab)."""
        if self.chat is not None:
            self.chat.cancel()
        if self.job is not None:
            self.job = None
            self.emit("say", text="Stopped.", muted=True)
            self.emit("idle")

    # ------------------------------------------------------------------ the file --
    def profile_now(self) -> profiling.Profile:
        df = self.source.df
        if self._profile_for is not df:
            self.profile, self._profile_for = profiling.profile(df), df
        return self.profile

    def greet(self) -> None:
        """The first thing Ceasar does with a file: look at it (no model needed) and offer starter tasks."""
        if self.greeted or not self.ready:
            return
        name = self.source.name

        def work():
            return self.profile_now()

        def done(p):
            self.emit("say", text=profiling.overview(p, name))
            self.emit("tasks", items=task_list.suggest(p), title="What would you like to do first?")
            self._narrate(name)
        self.greeted = self._start("Looking at the file", work, done)

    def _narrate(self, name: str) -> None:
        """An extra: the local model's own short read of the table, if Ollama is up (never blocks anything)."""
        df, overview = self.source.df, profiling.overview(self.profile, name)
        token, box = id(self.original), {}

        def go():
            try:
                model, think = self._model()
                box["model"] = model
                chat = ollama.Chat(self.app.cfg.get("notebook_ollama_url") or ollama.DEFAULT_URL)   # not self.chat:
                box["text"] = agent.narrate(chat, model, think, df, name, overview)                # Stop is the user's
            except Exception:  # noqa: BLE001 - optional: no Ollama, no extra
                box["text"] = ""
            box["done"] = True
        threading.Thread(target=go, daemon=True).start()

        def wait(left=240):                   # polled on the Tk thread: a worker must not touch Tk
            if token != id(self.original) or left <= 0:
                return
            if not box.get("done"):
                self.app.after(250, wait, left - 1)
                return
            self.emit("model", name=box.get("model"))
            if box.get("text"):
                self.emit("say", text=box["text"], who="Ceasar (the model's read)")
        self.app.after(250, wait)

    # ---------------------------------------------------------------------- model --
    def _new_chat(self) -> ollama.Chat:
        self.chat = ollama.Chat(self.app.cfg.get("notebook_ollama_url") or ollama.DEFAULT_URL)
        return self.chat

    def _model(self):
        url = self.app.cfg.get("notebook_ollama_url") or ollama.DEFAULT_URL
        cached = self._models                   # read once: the narration thread may reset it meanwhile
        if cached is None or time.monotonic() - cached[0] > 60:
            cached = self._models = (time.monotonic(), ollama.models(url))
        found = cached[1]
        name = ollama.pick(found, "completion", self.app.cfg.get("notebook_reader_model") or "", avoid="thinking")
        if name is None:
            raise ollama.NotReady("None of the models installed in Ollama can write text. Run: " + ollama.PULL_HINT)
        return name, (False if "thinking" in dict(found)[name] else None)

    # --------------------------------------------------------------------- actions --
    def run_task(self, task: task_list.Task) -> None:
        if self.busy or not self.ready:
            return
        self.emit("user", text=task.title)
        p = self.profile_now()
        if task.kind == "engine":
            self.emit("engine", task=task)
            return
        code = task.code(p).strip()
        if not code:
            self.emit("say", text="There is nothing to do for that in this table.")
            return
        self._execute(task.title, code, task.kind)

    def _execute(self, title: str, code: str, kind: str) -> None:
        df, original, edits = self.source.df, self.original, list(self.edits)

        def work():
            run = sandbox.run(df, code)
            if kind == "report":
                return run, None, None
            d = differ.diff_frames(df, run.df)
            return run, d, None if d.nothing else make_edited(original, run.df, edits + [Edit(title, code)])

        def done(res):
            run, d, new = res
            if kind == "report":
                self.emit("result", title=title, answer=run.answer, output=run.output, code=code)
            elif new is None:
                self.emit("say", text="Nothing needed changing, so the table is as it was.")
            else:
                self._apply(Edit(title, code, d.summary()), new, d, code)
        self._start(f"Running: {title}", work, done)

    def _apply(self, edit: Edit, new: Dataset, d: differ.Diff, code: str) -> None:
        self.edits.append(edit)
        self.undone.clear()
        note = self.app.lab.rebase(new)
        self.emit("changed", edit=edit, diff=d, note=note)
        self.emit("table")
        self.emit("history")

    def ask(self, text: str) -> None:
        text = text.strip()
        if not text or self.busy or not self.ready:
            return
        self.emit("user", text=text)
        df, name, original, edits = self.source.df, self.source.name, self.original, list(self.edits)
        chat = self._new_chat()
        memory = list(self.memory)

        def work():
            model, think = self._model()            # asks Ollama over HTTP: never on the window's thread
            out = agent.respond(chat, model, think, df, name, text, memory, cancelled=lambda: chat.cancelled)
            new = None
            if out.kind == "change" and out.run is not None and out.diff is not None and not out.diff.nothing:
                new = make_edited(original, out.run.df, edits + [Edit(text, out.code)])
            return out, new

        def done(res):
            out, new = res
            self.memory.append((text, out.raw or text))
            if new is not None:
                if out.say:
                    self.emit("say", text=out.say)
                self._apply(Edit(text, out.code, out.diff.summary()), new, out.diff, out.code)
            elif out.problem:
                if out.say:
                    self.emit("say", text=out.say)
                self.emit("problem", text=out.problem)
            elif out.kind == "question" and out.run is not None:
                self.emit("say", text=out.say) if out.say else None
                self.emit("result", title="", answer=out.run.answer, output=out.run.output, code=out.code)
            else:
                self.emit("say", text=out.say or "I did not find anything to do for that.")
        self._start("Ceasar is writing the code", work, done)

    # ----------------------------------------------------------------- history --
    @property
    def can_undo(self) -> bool:
        return bool(self.edits) and not self.busy

    @property
    def can_redo(self) -> bool:
        return bool(self.undone) and not self.busy

    def undo(self) -> None:
        if not self.can_undo:
            return
        gone = self.edits[-1]
        keep = self.edits[:-1]
        self._rebuild(keep, f"Undid: {gone.title}", lambda: (self.edits.pop(), self.undone.append(gone)))

    def redo(self) -> None:
        if not self.can_redo:
            return
        again = self.undone[-1]
        self._rebuild(self.edits + [again], f"Did again: {again.title}",
                      lambda: (self.undone.pop(), self.edits.append(again)))

    def restore(self) -> None:
        """Back to the file as it was loaded (the edits stay in redo, one by one)."""
        if self.busy or not self.edits:
            return
        gone = list(self.edits)
        self._rebuild([], "Back to the file as loaded.", lambda: (self.undone.extend(reversed(gone)),
                                                                  self.edits.clear()))

    def _rebuild(self, edits: List[Edit], message: str, commit) -> None:
        original = self.original

        def work():
            return make_edited(original, replay(original, edits), edits)

        def done(new):
            commit()
            self.emit("unmark")                 # the shading belonged to the edit that was just taken back
            note = self.app.lab.rebase(new)
            self.emit("say", text=message + (f" {note}" if note else ""), muted=True)
            self.emit("table")
            self.emit("history")
        self._start("Rebuilding the table", work, done)

    # ----------------------------------------------------------------- exporting --
    def script(self) -> str:
        if self.source is None:
            return ""
        return exporter.clean_script(self.source, self.app.lab.pipeline, self.app.lab.target())

    def save_csv(self, path) -> None:
        self.table.df.to_csv(path, index=False)


# =========================================================================== #
# The tab
# =========================================================================== #

def cell_text(value) -> str:
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)[:80]


class CeasarView(tk.Frame):
    """Starter tasks and a chat on the left, the live table on the right."""

    def __init__(self, master, page):
        super().__init__(master, background=C["panel"])
        self.page, self.app = page, page.app
        self.svc: CeasarService = self.app.ceasar
        t, px = self.app.theme, self.app.theme.px
        self.cards: list = []                  # embedded widgets of the transcript
        self.wraps: list = []                  # labels inside them that wrap with the pane
        self.changed_rows: set = set()
        self.changed_cols: set = set()
        self.table_mode = "changed"            # after an edit: the rows it changed first
        self._waiting_features = False
        self._tick = None

        head = tk.Frame(self, background=C["panel"])
        head.pack(fill="x", padx=px(16), pady=(px(12), px(4)))
        top = tk.Frame(head, background=C["panel"])
        top.pack(fill="x")
        self.title = tk.Label(top, text="Ceasar", background=C["panel"], foreground=C["text"], font=t.f["h3"],
                              anchor="w")
        self.title.pack(side="left")
        # the file and the model, as chips beside the name (the Figma design, page "9 · Ceasar")
        self.file_chip = tk.Label(top, background=C["raised"], foreground=C["muted"], font=t.f["small"],
                                  padx=px(10), pady=px(2))
        self.model_chip = tk.Label(top, background=C["panel"], foreground=C["faint"], font=t.f["small"],
                                   padx=px(10), pady=px(1), highlightthickness=1, highlightbackground=C["border"])
        Tooltip(self.model_chip, "The local model Ceasar writes code with (Ollama, the same one the Notebook uses).")
        self.stop_btn = ttk.Button(top, text="Stop", style="Small.TButton", command=self.svc.stop)
        self.status_row = tk.Frame(top, background=C["panel"])
        self.progress = ttk.Progressbar(self.status_row, mode="indeterminate", length=px(140))
        self.progress.pack(side="left")
        self.status = tk.Label(self.status_row, background=C["panel"], foreground=C["muted"], font=t.f["small"])
        self.status.pack(side="left", padx=(px(10), 0))
        self.subtitle = tk.Label(head, background=C["panel"], foreground=C["muted"], font=t.f["small"], anchor="w",
                                 justify="left")
        self.subtitle.pack(fill="x", pady=(px(4), 0))
        self.bind("<Configure>", lambda e: self.subtitle.configure(wraplength=max(200, e.width - px(40))), add="+")
        tk.Frame(self, background=C["border"], height=max(1, px(1))).pack(fill="x", padx=px(16), pady=(px(6), 0))

        self.split = ttk.PanedWindow(self, orient="horizontal")
        self.split.pack(fill="both", expand=True, padx=(px(8), px(8)), pady=(px(4), px(8)))
        left = tk.Frame(self.split, background=C["panel"])
        right = tk.Frame(self.split, background=C["panel"])
        self.split.add(left, weight=2)
        self.split.add(right, weight=3)
        self._build_chat(left)
        self._build_table(right)
        self.svc.listen(self.on_event)
        self.app.lab.listen(self._lab_event)
        self.bind_all("<Control-z>", lambda e: self._key(self.svc.undo), add="+")
        self.bind_all("<Control-y>", lambda e: self._key(self.svc.redo), add="+")
        self.on_event("reset", {})

    # --------------------------------------------------------------------- build --
    def _build_chat(self, parent) -> None:
        t, px = self.app.theme, self.app.theme.px
        box = tk.Frame(parent, background=C["panel"])
        box.pack(side="bottom", fill="x", padx=px(8), pady=(px(6), px(4)))
        self.chips = tk.Frame(box, background=C["panel"])       # the tasks this table needs most, one click away
        self.chips.pack(fill="x", pady=(0, px(6)))
        self.tasks_btn = ttk.Menubutton(self.chips, text="All tasks", style="TMenubutton")
        menu = t.menu(self.tasks_btn)
        for task in task_list.TASKS:
            menu.add_command(label=f"{task.title}  ·  {task.what}", command=lambda k=task: self.svc.run_task(k))
        self.tasks_btn["menu"] = menu
        self.tasks_btn.pack(side="right")
        self.chip_buttons: list = []
        line = tk.Frame(box, background=C["panel"])
        line.pack(fill="x")
        self.entry = PlaceholderEntry(line, placeholder=PLACEHOLDER)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send)
        self.send_btn = ttk.Button(line, text="Send", style="Accent.TButton", command=self.send)
        self.send_btn.pack(side="left", padx=(px(8), 0))
        Tooltip(self.tasks_btn, "Every starter task, any time.")
        Tooltip(self.entry, "Say what you want done to the table, in your own words. Ceasar writes the pandas code, "
                            "shows it, runs it on a copy and changes the table; Undo takes it back.")
        self.text = tk.Text(parent, wrap="word", font=t.f["base"], background=C["panel"], foreground=C["text"],
                            relief="flat", borderwidth=0, highlightthickness=0, padx=px(10), pady=px(8),
                            state="disabled", cursor="arrow", selectbackground=C["select"],
                            inactiveselectbackground=C["select"], selectforeground=C["text"], spacing3=px(4))
        bar = AutoScrollbar(parent, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.bind("<Configure>", self._rewrap, add="+")
        self._tags()

    def _tags(self) -> None:
        t, px = self.app.theme, self.app.theme.px
        tg = self.text.tag_configure
        tg("who", font=t.f["small"], spacing1=px(10))
        tg("whoname", font=t.f["bold"])
        tg("right", justify="right")
        tg("muted", foreground=C["muted"])
        tg("err", foreground=C["danger"])
        tg("ok", foreground=C["ok"])
        tg("mono", font=t.f["mono"], background=C["raised"], lmargin1=px(8), lmargin2=px(8), spacing3=0)
        tg("monofirst", spacing1=px(4))
        tg("small", font=t.f["small"], foreground=C["muted"])

    def _build_table(self, parent) -> None:
        t, px = self.app.theme, self.app.theme.px
        head = tk.Frame(parent, background=C["panel"])
        head.pack(fill="x", padx=px(6), pady=(px(2), px(6)))
        self.table_title = tk.Label(head, background=C["panel"], foreground=C["text"], font=t.f["bold"], anchor="w")
        self.table_title.pack(side="left")
        self.table_count = tk.Label(head, background=C["panel"], foreground=C["faint"], font=t.f["small"], anchor="w")
        self.table_count.pack(side="left", padx=(px(8), 0))
        self.mode_var = tk.StringVar(value="changed")
        self.mode_row = tk.Frame(head, background=C["panel"])      # shown once something changed
        for value, label in (("first", "All rows"), ("changed", "Changed rows")):
            ttk.Radiobutton(self.mode_row, text=label, value=value, variable=self.mode_var, style="Chip.TRadiobutton",
                            command=self._mode).pack(side="right")
        buttons = tk.Frame(parent, background=C["panel"])
        buttons.pack(fill="x", padx=px(6), pady=(0, px(6)))
        head = buttons
        self.restore_btn = ttk.Button(head, text="Back to loaded file", style="Link.TButton", command=self.svc.restore)
        self.save_btn = ttk.Button(head, text="Save CSV…", image=t.icon("download", "muted", 16), compound="left",
                                   style="Small.TButton", command=self.save_csv)
        self.code_btn = ttk.Button(head, text="Code", image=t.icon("code", "muted", 16), compound="left",
                                   style="Small.TButton", command=self.show_code)
        self.redo_btn = ttk.Button(head, text="Redo", image=t.icon_states("redo", 16), compound="left",
                                   style="Small.TButton", command=self.svc.redo)
        self.undo_btn = ttk.Button(head, text="Undo", image=t.icon_states("undo", 16), compound="left",
                                   style="Small.TButton", command=self.svc.undo)
        for b in (self.undo_btn, self.redo_btn, self.restore_btn):
            b.pack(side="left", padx=(0, px(4)))
        for b in (self.save_btn, self.code_btn):
            b.pack(side="right", padx=(px(4), 0))
        Tooltip(self.undo_btn, "Take back the last change (Ctrl+Z)")
        Tooltip(self.redo_btn, "Do it again (Ctrl+Y)")
        Tooltip(self.restore_btn, "Back to the file as it was loaded. Redo brings the changes back one by one.")
        Tooltip(self.save_btn, "Save the table as you see it to a new CSV file. The file you opened is never changed.")
        Tooltip(self.code_btn, "The code that rebuilds this table from the file (also at the start of every plot's code).")
        self.table_note = tk.Label(parent, background=C["panel"], foreground=C["faint"], font=t.f["small"], anchor="w")
        self.table_note.pack(side="bottom", fill="x", padx=px(6), pady=(px(6), 0))
        box = ttk.Frame(parent, style="Inset.TFrame", padding=px(3))
        box.pack(fill="both", expand=True, padx=px(4))
        self.tree = ttk.Treeview(box, show="headings", selectmode="browse")
        ys = AutoScrollbar(box, orient="vertical", command=self.tree.yview, style="Field.Vertical.TScrollbar")
        xs = AutoScrollbar(box, orient="horizontal", command=self.tree.xview, style="Field.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self._tree_tags()

    def _tree_tags(self) -> None:
        self.tree.tag_configure("odd", background=C["stripe"])
        self.tree.tag_configure("changed", background=C["accent_soft"], foreground=C["text"])

    # ---------------------------------------------------------------------- events --
    def _key(self, action) -> None:
        if self.page.nb.select() != str(self) or isinstance(self.focus_get(), (tk.Entry, ttk.Entry, tk.Text)):
            return
        action()

    def is_showing(self) -> bool:
        try:
            return self.page.nb.select() == str(self)
        except tk.TclError:
            return False

    def on_show(self) -> None:
        if self.svc.ready:
            self.svc.greet()

    def _lab_event(self, event: str) -> None:
        if event == "done" and self._waiting_features:
            self._waiting_features = False
            self._features_list()

    def on_event(self, event: str, data: dict) -> None:
        svc = self.svc
        if event == "reset":
            self._clear()
            self._chips([])
            self.model_chip.configure(text="○ looking for the model…", foreground=C["faint"])
            self.changed_rows, self.changed_cols = set(), set()
            self.table_mode = "changed"
            self.mode_var.set("changed")
            self._state()
            self.refresh_table()
            if self.is_showing():
                svc.greet()
        elif event == "busy":
            self._busy(True, data.get("text", "Working"))
        elif event == "idle":
            self._busy(False)
        elif event == "user":
            self._say(data["text"], who="You", tag="me")
        elif event == "say":
            self._say(data["text"], who=data.get("who", "Ceasar"), tag="muted" if data.get("muted") else "")
        elif event == "problem":
            self._say(data["text"], who="Ceasar", tag="err")
        elif event == "tasks":
            self._task_rows(data["items"], data["title"])
        elif event == "result":
            self._result(data)
        elif event == "changed":
            self._changed(data)
        elif event == "table":
            self.refresh_table()
        elif event == "model":
            name = data.get("name")
            self.model_chip.configure(text=f"● {name} · local" if name else "○ Ollama is not running",
                                      foreground=C["ok"] if name else C["faint"])
        elif event == "unmark":
            self.changed_rows, self.changed_cols = set(), set()
        elif event == "history":
            self._state()
        elif event == "engine":
            (self._plot_ideas if data["task"].id == "plot_ideas" else self._feature_ideas)()

    def _busy(self, busy: bool, text: str = "") -> None:
        px = self.app.theme.px
        if busy:
            self.stop_btn.pack(side="right")
            self.status_row.pack(side="right", padx=(0, px(10)))
            self.progress.start(14)
            self._started = time.monotonic()
            self._label = text
            self._elapsed()
        else:
            if self._tick is not None:
                self.after_cancel(self._tick)
                self._tick = None
            self.progress.stop()
            self.status_row.pack_forget()
            self.stop_btn.pack_forget()
        self._state()

    def _elapsed(self) -> None:
        secs = int(time.monotonic() - self._started)
        self.status.configure(text=f"{self._label}…" + (f" {secs} s" if secs >= 3 else ""))
        self._tick = self.after(500, self._elapsed)

    def _state(self) -> None:
        svc = self.svc
        ready, busy = svc.ready, svc.busy
        self.undo_btn.state(["!disabled"] if svc.can_undo else ["disabled"])
        self.redo_btn.state(["!disabled"] if svc.can_redo else ["disabled"])
        self.restore_btn.state(["!disabled"] if svc.edits and not busy else ["disabled"])
        for b in (self.save_btn, self.code_btn):
            b.state(["!disabled"] if ready else ["disabled"])
        for b in (self.send_btn, self.tasks_btn, *self.chip_buttons):
            b.state(["!disabled"] if ready and not busy else ["disabled"])
        self.entry.configure(state="normal" if ready else "disabled")
        if not ready:
            self.title.configure(text="Ceasar")
            self.subtitle.configure(text="Open a CSV file and Ceasar looks at it, offers the first tasks (missing data, "
                                         "duplicates, types, outliers…) and changes the table when you tell it to.")
        else:
            self.title.configure(text="Ceasar")
            self.subtitle.configure(text="Choose a task, or write what you want done to the table. Every change is "
                                         "pandas code you can see, undo, and export.")
        self.mode_row.pack_forget() if not self.changed_rows else self.mode_row.pack(side="right")
        if ready:
            ds = svc.source
            self.file_chip.configure(text=f"{ds.name}   {ds.shape_text}")
            self.file_chip.pack(side="left", padx=(self.app.theme.px(12), 0))
            self.model_chip.pack(side="left", padx=(self.app.theme.px(8), 0))
        else:
            self.file_chip.pack_forget()
            self.model_chip.pack_forget()

    # ------------------------------------------------------------------ transcript --
    def _clear(self) -> None:
        for w in self.cards:
            try:
                w.destroy()
            except tk.TclError:
                pass
        self.cards = []
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        if not self.svc.ready:
            self._write("Open a CSV file first.", "muted")

    def _write(self, text: str, *tags) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", text, tags)
        self.text.configure(state="disabled")
        self.text.see("end")

    def _say(self, text: str, who: str, tag: str = "") -> None:
        t, px = self.app.theme, self.app.theme.px
        if tag == "me":                         # the user: a bubble on the right
            self._write("\n", "who")
            bubble = tk.Label(self.text, text=text, background=C["select"], foreground=C["text"], font=t.f["base"],
                              justify="left", padx=px(12), pady=px(7), wraplength=self._wrap_width())
            self.wraps.append(bubble)
            self.text.configure(state="normal")
            self.text.window_create("end", window=bubble)
            self.text.tag_add("right", "end-2c", "end-1c")
            self.text.insert("end", "\n", "right")
            self.text.configure(state="disabled")
            self.cards.append(bubble)
            return
        self._write("\n", "who")
        self.text.configure(state="normal")
        mark = tk.Label(self.text, text="C", background=C["accent"], foreground=C["on_accent"], font=t.f["bold"],
                        width=2, padx=0, pady=0)
        self.cards.append(mark)
        self.text.window_create("end", window=mark, align="center", padx=px(0))
        self.text.configure(state="disabled")
        self._write(f"  {who}\n", "whoname")
        if text:
            self._write(text + "\n", *([tag] if tag else []))

    def _embed(self, widget) -> None:
        self.cards.append(widget)
        self.text.configure(state="normal")
        self.text.window_create("end", window=widget)
        self.text.insert("end", "\n")
        self.text.configure(state="disabled")
        self.text.see("end")
        self.text.after_idle(lambda: self.text.see("end"))      # once the card has its size

    def _wrap_width(self, width=None) -> int:
        return max(200, (width or self.text.winfo_width()) - self.app.theme.px(80))

    def _rewrap(self, event=None) -> None:
        width = self._wrap_width(event.width if event else None)
        for label in list(self.wraps):
            try:
                label.configure(wraplength=width // 2 - self.app.theme.px(30) if getattr(label, "half", False)
                                else width)
            except tk.TclError:
                self.wraps.remove(label)

    def _wrapped(self, parent, text: str) -> ttk.Label:
        label = ttk.Label(parent, text=text, style="Raised.Muted.TLabel", justify="left", wraplength=self._wrap_width())
        self.wraps.append(label)
        return label

    def _card(self) -> ttk.Frame:
        px = self.app.theme.px
        return ttk.Frame(self.text, style="Well.TFrame", padding=(px(14), px(10)))

    def _task_rows(self, items, title: str) -> None:
        px = self.app.theme.px
        self._write(title + "\n", "small")
        grid = tk.Frame(self.text, background=C["panel"])
        two = self.text.winfo_width() >= px(600)          # two cards a row when the chat is wide enough
        grid.columnconfigure((0, 1) if two else 0, weight=1, uniform="task")
        for i, (task, why) in enumerate(items):
            cell = ttk.Frame(grid, style="Well.TFrame", padding=(px(12), px(10)))
            cell.grid(row=i // 2 if two else i, column=i % 2 if two else 0, sticky="nsew", padx=(0, px(8)),
                      pady=(0, px(8)))
            ttk.Button(cell, text=task.title, style="Small.TButton",
                       command=lambda k=task: self.svc.run_task(k)).pack(anchor="w")
            label = self._wrapped(cell, why or task.what)
            label.pack(anchor="w", pady=(px(4), 0))
            label.half = two
        self._embed(grid)
        self._chips([task for task, why in items if why][:2])

    def _chips(self, items) -> None:
        for b in self.chip_buttons:
            b.destroy()
        self.chip_buttons = []
        for task in items:
            b = ttk.Button(self.chips, text=task.title, style="Small.TButton", command=lambda k=task: self.svc.run_task(k))
            b.pack(side="left", padx=(0, self.app.theme.px(6)))
            self.chip_buttons.append(b)
        self._state()

    def _code_block(self, code: str) -> None:
        lines = code.strip().split("\n")
        shown = lines if len(lines) <= 14 else lines[:14] + [f"# … {len(lines) - 14} more lines (the Code button has all)"]
        self._write("\n".join(shown) + "\n", "mono", "monofirst")

    def _result(self, data: dict) -> None:
        answer = data.get("answer")
        if data.get("title"):
            self._say("", who=data["title"])
        text = table_text(answer) if answer is not None else (data.get("output") or "Done.")
        if answer is not None and isinstance(answer, pd.DataFrame) and answer.empty:
            self._write("Nothing found.\n", "ok")
        else:
            self._write(text + "\n", "mono", "monofirst")
        if data.get("code"):
            self._write("code\n", "small")
            self._code_block(data["code"])

    def _changed(self, data: dict) -> None:
        t, px = self.app.theme, self.app.theme.px
        edit, d, note = data["edit"], data["diff"], data.get("note", "")
        card = self._card()
        head = tk.Frame(card, background=C["raised"])
        head.pack(fill="x")
        tk.Label(head, text="✔ " + d.summary(), background=C["raised"], foreground=C["ok"], font=t.f["bold"],
                 justify="left", anchor="w").pack(side="left")
        for label, column, before, after in d.samples[:4]:
            tk.Label(card, text=f"row {label}   {column}   {cell_text(before)}  →  {cell_text(after)}",
                     background=C["raised"], foreground=C["muted"], font=t.f["mono"], anchor="w").pack(fill="x")
        if note:
            self._wrapped(card, note).configure(foreground=C["danger"])
            card.winfo_children()[-1].pack(fill="x", pady=(px(4), 0))
        lines = edit.code.strip().split("\n")
        code = tk.Label(card, text="\n".join(lines[:14] + ([f"# … {len(lines) - 14} more lines"] if len(lines) > 14 else [])),
                        background=C["field"], foreground=C["text"], font=t.f["mono"], justify="left", anchor="w",
                        padx=px(8), pady=px(6), wraplength=self._wrap_width())
        self.wraps.append(code)
        acts = tk.Frame(card, background=C["raised"])
        acts.pack(fill="x", pady=(px(8), 0))
        undo = ttk.Button(acts, text="Undo", style="Small.TButton", command=self.svc.undo)
        undo.pack(side="left")
        Tooltip(undo, "Take back the last change")

        def toggle(btn):
            if code.winfo_manager():
                code.pack_forget()
                btn.configure(text="Show code")
            else:
                code.pack(fill="x", pady=(px(8), 0))
                btn.configure(text="Hide code")
        show = ttk.Button(acts, text="Hide code", style="Link.TButton")
        show.configure(command=lambda: toggle(show))
        show.pack(side="left", padx=(px(8), 0))
        code.pack(fill="x", pady=(px(8), 0))         # shown at first: the user sees what ran
        self._embed(card)
        self.changed_rows = set(d.changed_rows) if d.rows_after >= d.rows_before else set()
        self.changed_cols = set(d.by_column) | set(d.cols_added)
        self.table_mode = "changed"
        self.mode_var.set("changed")

    # ------------------------------------------------------------------------ table --
    def _mode(self) -> None:
        self.table_mode = self.mode_var.get()
        self.refresh_table()

    def refresh_table(self) -> None:
        px = self.app.theme.px
        ds = self.svc.table
        self._state()
        for item in self.tree.get_children(""):
            self.tree.delete(item)
        if ds is None:
            self.tree.configure(columns=())
            self.table_title.configure(text="No table yet")
            self.table_note.configure(text="")
            return
        df = ds.df
        edits = len(self.svc.edits)
        self.table_title.configure(text=ds.shape_text)
        self.table_count.configure(text=f"{edits} change{'s' if edits != 1 else ''}" if edits else "")
        names = [str(c) for c in df.columns[:TABLE_COLUMNS]]
        self.tree.configure(columns=["#"] + list(range(len(names))))
        self.tree.heading("#", text="#", anchor="w")
        self.tree.column("#", width=px(56), minwidth=px(40), anchor="w", stretch=False)
        sample = df.iloc[:60, :TABLE_COLUMNS]
        for i, name in enumerate(names):
            self.tree.heading(i, text=("● " if name in self.changed_cols else "") + name, anchor="w")
            longest = max([len(name) + 2] + [len(cell_text(v)) for v in sample.iloc[:, i].tolist()])
            self.tree.column(i, width=px(max(70, min(260, 16 + 8 * longest))), minwidth=px(50), anchor="w",
                             stretch=False)
        show = df
        if self.table_mode == "changed" and self.changed_rows:
            show = df[df.index.isin(self.changed_rows)]
        sub = show.iloc[:TABLE_ROWS, :TABLE_COLUMNS]
        for n, (label, row) in enumerate(sub.iterrows()):
            tags = ("changed",) if label in self.changed_rows else (("odd",) if n % 2 else ())
            self.tree.insert("", "end", values=[label] + [cell_text(v) for v in row.tolist()], tags=tags)
        more = []
        if len(show) > TABLE_ROWS:
            more.append(f"first {TABLE_ROWS:,} of {len(show):,} rows")
        if df.shape[1] > TABLE_COLUMNS:
            more.append(f"first {TABLE_COLUMNS} of {df.shape[1]} columns")
        if self.table_mode == "changed" and self.changed_rows:
            more.append("shaded rows were changed")
        self.table_note.configure(text="  ·  ".join(more))

    # ------------------------------------------------------------------------ actions --
    def send(self, _event=None) -> None:
        text = self.entry.value()
        if not text.strip() or self.svc.busy or not self.svc.ready:
            return
        self.entry.set_value("")
        self.svc.ask(text)

    def save_csv(self) -> None:
        ds = self.svc.table
        if ds is None:
            return
        stem = ds.path.stem + "_ceasar.csv"
        path = filedialog.asksaveasfilename(parent=self, title="Save the table", defaultextension=".csv",
                                            initialfile=stem, initialdir=self.app.cfg.get("save_dir") or None,
                                            filetypes=[("CSV file", "*.csv")])
        if path:
            self.svc.save_csv(path)
            self._done(f"Saved {len(ds.df):,} rows to {path}.")

    def show_code(self) -> None:
        from .featurelab import CodeDialog
        if self.svc.ready:
            CodeDialog(self, self.svc.script(), (self.svc.source.path.stem or "table") + "_ceasar.py",
                       note="Loads the file, then every change made in Ceasar and every accepted feature, as plain pandas.")

    def _done(self, text: str) -> None:
        self._say(text, who="Ceasar", tag="muted")

    # ------------------------------------------------- the rest of the app, as tasks --
    def _plot_ideas(self) -> None:
        px = self.app.theme.px
        res = self.app.ideas.result
        if res is None or not res.suggestions:
            self.app.ideas.request(self.svc.table, self.page.current_target(), self.page.type_overrides)
            self._say("The plot ideas are still being worked out. Press the task again in a moment.", who="Ceasar",
                      tag="muted")
            return
        card = self._card()
        ttk.Label(card, text="Plots worth drawing first", style="Raised.Bold.TLabel").pack(anchor="w")
        for s in res.suggestions[:5]:
            row = ttk.Frame(card, style="Well.TFrame")
            row.pack(fill="x", pady=(px(8), 0))
            ttk.Button(row, text="Plot it", style="Small.TButton", command=lambda s=s: self._open_idea(s)).pack(anchor="w")
            self._wrapped(row, f"{', '.join(map(str, s.columns))} — {s.plot}. {s.reason}").pack(anchor="w", pady=(px(2), 0))
        self._embed(card)

    def _open_idea(self, s) -> None:
        self.page.open_idea(s)
        self.page.nb.select(self.page.plot_view)

    def _feature_ideas(self) -> None:
        lab = self.app.lab
        if self.page.current_target() is None:
            self._say("Feature Lab measures new columns against a target, the column you want to predict. Pick the "
                      "Target in the box on the left, then press this task again.", who="Ceasar", tag="muted")
            return
        if lab.result is not None and lab.result_key == lab.key():
            self._features_list()
            return
        self._waiting_features = True
        self._say("Asking the Feature Lab…", who="Ceasar", tag="muted")
        lab.suggest()

    def _features_list(self) -> None:
        px = self.app.theme.px
        res = self.app.lab.result
        good = [s for s in (res.suggestions if res else []) if s.status == "recommended"][:5]
        if not good:
            self._say("The Feature Lab found no new column that adds information about the target.", who="Ceasar")
            return
        card = self._card()
        ttk.Label(card, text="New columns that tell a model more", style="Raised.Bold.TLabel").pack(anchor="w")
        for s in good:
            row = ttk.Frame(card, style="Well.TFrame")
            row.pack(fill="x", pady=(px(8), 0))
            ttk.Button(row, text=f"Add {s.name}", style="Small.TButton", command=lambda s=s: self.app.lab.accept(s)).pack(
                anchor="w")
            self._wrapped(row, f"{s.title}. {s.link or s.why}").pack(anchor="w", pady=(px(2), 0))
        ttk.Button(card, text="Open the Feature Lab", style="Small.TButton",
                   command=lambda: self.page.nb.select(self.page.lab_view)).pack(anchor="w", pady=(px(8), 0))
        self._embed(card)

    # ------------------------------------------------------------------------- look --
    def on_theme(self) -> None:
        self._tags()
        self._tree_tags()
