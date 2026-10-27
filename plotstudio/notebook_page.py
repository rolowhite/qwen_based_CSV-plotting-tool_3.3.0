"""Notebook: give it a picture, a PDF page or the typed text of a statistics problem and it writes the worked
solution, like a chat. Left: what you gave it, one bubble per turn. Right: the answers, streamed, with the math
drawn by matplotlib's mathtext (Open in browser draws it with the bundled KaTeX).

Pictures are read by a local vision model in Ollama (core/notebook/reader.py); nothing asks you to check or fix
the reading. The work runs in worker threads that report through a queue.Queue polled with after(). The
solution library is only read.
"""
from __future__ import annotations

import base64
import gc
import queue
import re
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import APP_NAME, settings
from .core.notebook import cache as nb_cache
from .core.notebook import library as nb_library
from .core.notebook import lookup as nb_lookup
from .core.notebook import gemini, ollama, reader, render, session, solver, tex, verify
from .core.notebook import setup as reader_setup
from .log import log_error
from .theme import C
from .widgets import AutoScrollbar, PlaceholderEntry, ScrollFrame, SmoothScroller, Tooltip

IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
GUTTER = 12
THUMB = 240             # px: the long side of the picture in a bubble
STREAM = object()       # marks a streamed event in the job queue (the job isn't finished yet)
LIBRARY_FILES = nb_library.BUILT_IN_FILES    # the solutions every answer comes from (for now); tests swap in their own
OWN_PROGRESS = {"setup", "warm", "verify"}                  # jobs that show their own progress bar, not the header's busy bar
GEMINI_NOTICE = ("Gemini (Google) then solves new problems alongside the model on this computer, and its solution "
                 "is shown. The problem's text and picture are sent to Google for that. With a free key, Google may "
                 "use what you send to improve its products and people at Google may read it, so don't send anything "
                 "private. You must be 18 or older, and the free tier isn't for users in the EU, the UK or "
                 "Switzerland. Without a key everything still works, offline.")
GEMINI_TIP = "Tip: a free Gemini key (in the model menu at the top) gives better solutions to new problems."


def notebook_dir() -> Path:
    """Where the index cache, the answer pages and the history live (next to the settings file)."""
    return settings.PATH.parent / ".csv_plot_studio" / "notebook"


def history_path() -> Path:
    return notebook_dir() / "notebook_history.jsonl"


# =========================================================================================== answers ==
class AnswerView(tk.Frame):
    """The right pane: Markdown answers drawn into a read-only Text, each formula as a picture.

    What it shows is a list of items, so a theme switch draws it all again: ("turn", n), ["answer", markdown,
    finished], ("setup", message) and ("note", text, tag)."""

    def __init__(self, master, page):
        super().__init__(master, background=C["panel"])
        self.page = page
        t, px = page.app.theme, page.app.theme.px
        self.t, self.px = t, px
        # the reading text is one point bigger than the controls, like a document
        self.font = {k: (t.f[k][0], t.f[k][1] + 1) + tuple(t.f[k][2:]) for k in ("base", "bold", "mono")}
        self.text = tk.Text(self, wrap="word", font=self.font["base"], background=C["panel"], foreground=C["text"],
                            relief="flat", borderwidth=0, highlightthickness=0, padx=px(6), pady=px(6),
                            state="disabled", cursor="arrow", selectbackground=C["select"],
                            inactiveselectbackground=C["select"], selectforeground=C["text"])
        bar = AutoScrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.text.smooth = SmoothScroller(self.text)
        try:
            self._md = render._markdown()
        except render.RenderUnavailable as exc:
            log_error("Notebook: answers are shown as plain text", exc)
            self._md = None
        self.items = []
        self._dpi = self.text.winfo_fpixels("1i")     # read here: Tk is only touched on its own thread
        self._images = {}          # (tex, display, ink) -> PhotoImage
        self._failed = set()       # formulas mathtext couldn't draw (logged once each)
        self._windows = []         # embedded buttons and cards, destroyed on a redraw
        self._live = None          # the answer item being streamed
        self._drawn = 0            # how much of its markdown is drawn as Markdown (the rest is plain text)
        self._tables = 0
        self.redraw()

    # ----------------------------------------------------------------------------------------- public --
    def clear(self):
        self.items, self._live = [], None
        self.redraw()

    def add_turn(self, n):
        self._add(("turn", n))

    def begin(self):
        self._live = ["answer", "", False]
        self._drawn = 0
        self._add(self._live)

    def feed(self, piece):
        if self._live is not None:
            self._live[1] += piece
            self._edit(lambda: self._advance(final=False))

    def end(self, markdown):
        if self._live is not None:
            self._live[1], self._live[2] = markdown, True
            self._edit(lambda: self._advance(final=True))
            self._live = None

    def finish(self):
        """End the answer being streamed with what has arrived (after Stop)."""
        if self._live is not None:
            self.end(self._live[1])

    def prerender(self, markdown):
        """Draw an answer's formulas in a background thread, so they are ready when the answer streams in (and stay
        remembered for the next time). Called from the solving thread; never touches Tk."""
        size, dpi, color = self.font["base"][1], self._dpi, C["text"]

        def work():
            try:
                forms = []
                for tok in render._markdown().parse(markdown):
                    if tok.type == "math_block":
                        forms.append((tok.content, True))
                    forms += [(c.content, c.type == "math_inline_double") for c in tok.children or []
                              if c.type in ("math_inline", "math_inline_double")]
                for source, display in forms:
                    try:
                        tex.png_cached(source, size * (1.15 if display else 1.0), dpi, color)
                    except tex.TexError:
                        pass
            except Exception:  # noqa: BLE001 - a head start only: the page draws what is missing itself
                pass
        threading.Thread(target=work, daemon=True).start()

    def add_choice(self, options, on_pick):
        """A picture had several problems: one button for each, the user says which to solve."""
        self._live = None
        self._add(("choice", list(options), on_pick))

    def add_correction(self, markdown):
        """An answer that arrives later (the background re-check found a mistake), as a finished answer."""
        self._live = None
        self._add(["answer", markdown, True])

    def setup(self, message):
        self._live = None
        self._add(("setup", message))

    def note(self, text, tag="muted"):
        self._live = None
        self._add(("note", text, tag))

    def show_turn(self, n):
        if f"turn{n}" in self.text.mark_names():
            self.text.yview(f"turn{n}")

    def plain_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def on_theme(self):
        self._images.clear()
        self.text.configure(background=C["panel"], foreground=C["text"], selectbackground=C["select"],
                            inactiveselectbackground=C["select"], selectforeground=C["text"])
        self.redraw()

    def redraw(self):
        for w in self._windows:
            w.destroy()
        self._windows = []
        self._tags()
        self.text.configure(state="normal")
        try:
            self.text.delete("1.0", "end")
            if not self.items:
                self._insert("\n\n\nThe worked solution appears here.", ("empty",))
            for item in self.items:
                if item is self._live:
                    self._drawn = 0
                    self._advance(final=False)
                else:
                    self._draw_item(item)
        finally:
            self.text.configure(state="disabled")

    # --------------------------------------------------------------------------------------- drawing --
    def _tags(self):
        px, f, r = self.px, self.t.f, self.font
        body, size = r["base"][0], r["base"][1]
        tg = self.text.tag_configure
        tg("p", spacing3=px(8))
        tg("h1", font=f["h2"], spacing1=px(10), spacing3=px(6))
        tg("h2", font=f["h3"], spacing1=px(10), spacing3=px(6))
        tg("h3", font=r["bold"], spacing1=px(8), spacing3=px(4))
        tg("bold", font=r["bold"])
        tg("italic", font=(body, size, "italic"))
        tg("bolditalic", font=(r["bold"][0], size, "bold", "italic"))
        tg("code", font=r["mono"], background=C["raised"])
        tg("codeblock", font=r["mono"], background=C["raised"], lmargin1=px(10), lmargin2=px(10), spacing3=px(8))
        tg("display", justify="center", spacing1=px(4), spacing3=px(10))
        tg("li", lmargin1=px(6), lmargin2=px(26), tabs=(px(26),), spacing3=px(4))
        tg("th", font=r["bold"])
        tg("muted", foreground=C["muted"])
        tg("error", foreground=C["danger"])
        tg("gap", font=(body, 4), spacing1=px(14))
        tg("empty", foreground=C["faint"], justify="center")

    def _edit(self, work):
        at_end = self.text.yview()[1] >= 0.999
        self.text.configure(state="normal")
        try:
            work()
        finally:
            self.text.configure(state="disabled")
        if at_end:
            self.text.see("end")

    def _add(self, item):
        if not self.items:
            self.items.append(item)
            self.redraw()
            return
        self.items.append(item)
        self._edit(lambda: self._draw_item(item))

    def _insert(self, text, tags=()):
        self.text.insert("end-1c", text, tags)

    def _draw_item(self, item):
        kind = item[0]
        if kind == "turn":
            if self.text.index("end-1c") != "1.0":
                self._insert("\n", ("gap",))
            self.text.mark_set(f"turn{item[1]}", "end-1c")
            self.text.mark_gravity(f"turn{item[1]}", "left")
        elif kind == "answer":
            self._markdown(item[1])
            if item[2]:
                self._actions(item[1])
        elif kind == "setup":
            self._setup_card(item[1])
        elif kind == "choice":
            self._choice_card(item[1], item[2])
        else:
            self._insert(item[1] + "\n", (item[2], "p"))

    def _advance(self, final):
        """Draw the streamed answer's finished blocks as Markdown; show the unfinished rest as plain text."""
        md = self._live[1]
        if self.text.tag_ranges("pending"):
            self.text.delete("pending.first", "pending.last")
        cut = len(md) if final else _block_end(md, self._drawn)
        if cut > self._drawn:
            self._markdown(md[self._drawn:cut])
            self._drawn = cut
        if final:
            self._actions(md)
        elif md[self._drawn:].strip():
            self._insert(md[self._drawn:].lstrip("\n"), ("pending", "p"))

    def _markdown(self, md):
        if self._md is None:
            self._insert(md.strip("\n") + "\n", ("p",))
            return
        tokens = self._md.parse(md)
        lists = []          # [ordered, next number] per open list
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            kind = tok.type
            if kind == "heading_open":
                tag = {"h1": "h1", "h2": "h2"}.get(tok.tag, "h3")
                self._inline(tokens[i + 1].children or [], (tag,))
                self._insert("\n", (tag,))
                i += 3
                continue
            if kind == "paragraph_open":
                block = ("li",) if lists else ("p",)
                self._inline(tokens[i + 1].children or [], block)
                self._insert("\n", block)
                i += 3
                continue
            if kind in ("bullet_list_open", "ordered_list_open"):
                lists.append([kind == "ordered_list_open", int(tok.attrGet("start") or 1)])
            elif kind in ("bullet_list_close", "ordered_list_close"):
                lists.pop()
            elif kind == "list_item_open" and lists:
                # shortcut: nested lists share one indent; give each depth its own if solutions need it
                ordered, number = lists[-1]
                lists[-1][1] += 1
                self._insert(f"{number}.\t" if ordered else "•\t", ("li",))
            elif kind == "math_block":
                self._math(tok.content, True)
            elif kind in ("fence", "code_block"):
                self._insert(tok.content.rstrip("\n") + "\n", ("codeblock",))
            elif kind == "table_open":
                end = next((k for k in range(i, len(tokens)) if tokens[k].type == "table_close"), len(tokens) - 1)
                self._table(tokens[i:end])
                i = end
            elif kind == "inline":
                self._inline(tok.children or [], ("p",))
                self._insert("\n", ("p",))
            i += 1

    def _inline(self, children, block):
        bold = italic = False
        for c in children:
            kind = c.type
            if kind == "text":
                style = ("bolditalic",) if bold and italic else ("bold",) if bold else ("italic",) if italic else ()
                self._insert(c.content, block + style)
            elif kind in ("softbreak", "hardbreak"):
                self._insert("\n", block)          # keep the author's lines: "(a) ...\n(b) ..."
            elif kind in ("strong_open", "strong_close"):
                bold = kind == "strong_open"
            elif kind in ("em_open", "em_close"):
                italic = kind == "em_open"
            elif kind == "code_inline":
                self._insert(c.content, block + ("code",))
            elif kind == "math_inline":
                self._math(c.content, False, block)
            elif kind == "math_inline_double":
                self._math(c.content, True, block)
            elif c.content:
                self._insert(c.content, block)

    def _photo(self, source, display):
        """The formula as a PhotoImage (cached), or None when mathtext can't draw it (logged once)."""
        key = (source, display, C["text"])
        if key not in self._images:
            size = self.font["base"][1] * (1.15 if display else 1.0)
            try:
                data = tex.png_cached(source, size, self._dpi, C["text"])
                self._images[key] = tk.PhotoImage(master=self.text, data=base64.b64encode(data))
            except tex.TexError as exc:
                if source not in self._failed:
                    self._failed.add(source)
                    log_error(f"Notebook: mathtext can't draw ${source}$", details=str(exc))
                self._images[key] = None
        return self._images[key]

    def _math(self, source, display, block=()):
        photo = self._photo(source, display)
        if display and self.text.index("end-1c").split(".")[1] != "0":
            self._insert("\n", block)
        tags = block + (("display",) if display else ())
        if photo is None:
            fence = "$$" if display else "$"
            self._insert(f"{fence}{source.strip()}{fence}", tags + ("code",))
        else:
            at = self.text.index("end-1c")
            self.text.image_create(at, image=photo, align="center", padx=self.px(1))
            for tag in tags:
                self.text.tag_add(tag, at)
        if display:
            self._insert("\n", tags)

    def _table(self, tokens):
        rows, row, head = [], None, False
        for tok in tokens:
            if tok.type == "thead_open":
                head = True
            elif tok.type == "thead_close":
                head = False
            elif tok.type == "tr_open":
                row = []
            elif tok.type == "inline" and row is not None:
                row.append(tok.children or [])
            elif tok.type == "tr_close" and row is not None:
                rows.append((row, head))
                row = None
        if not rows:
            return
        fonts = {False: tkfont.Font(root=self.text, font=self.font["base"]),
                 True: tkfont.Font(root=self.text, font=self.font["bold"])}
        mono = tkfont.Font(root=self.text, font=self.font["mono"])

        def width(children, bold):
            w = 0
            for c in children:
                if c.type in ("math_inline", "math_inline_double"):
                    photo = self._photo(c.content, False)
                    w += photo.width() + self.px(2) if photo is not None else mono.measure(f"${c.content}$")
                elif c.type == "code_inline":
                    w += mono.measure(c.content)
                elif c.content:
                    w += fonts[bold].measure(c.content)
            return w

        columns = max(len(r) for r, _ in rows)
        widths = [max((width(r[k], h) for r, h in rows if k < len(r)), default=0) for k in range(columns)]
        gap, x, stops = self.px(18), self.px(6), []
        for w in widths[:-1]:
            x += w + gap
            stops.append(x)
        self._tables += 1
        name = f"table{self._tables}"
        self.text.tag_configure(name, lmargin1=self.px(6), lmargin2=self.px(6), tabs=tuple(stops) or "",
                                spacing1=self.px(2), spacing3=self.px(2))
        for k, (cells, is_head) in enumerate(rows):
            for j, cell in enumerate(cells):
                if j:
                    self._insert("\t", (name,))
                self._inline(cell, (name,) + (("th",) if is_head else ()))
            self._insert("\n", (name,))
        self._insert("\n", ("gap",))

    def _actions(self, md):
        t, px = self.t, self.px
        row = tk.Frame(self.text, background=C["panel"])
        ttk.Button(row, text="Copy", image=t.icon("copy", "muted", 14), compound="left", style="Ghost.TButton",
                   command=lambda: self._copy(md)).pack(side="left")
        ttk.Button(row, text="Open in browser", image=t.icon("external", "muted", 14), compound="left",
                   style="Ghost.TButton", command=lambda: self.page.open_in_browser(md)).pack(side="left",
                                                                                         padx=(px(4), 0))
        if self.page.can_recheck(md):
            ttk.Button(row, text="Check again", style="Ghost.TButton",
                       command=lambda: self.page.recheck(md)).pack(side="left", padx=(px(4), 0))
        self._windows.append(row)
        self.text.window_create("end-1c", window=row)
        self._insert("\n", ("p",))

    def _copy(self, md):
        self.clipboard_clear()
        self.clipboard_append(md)
        self.page.set_status("Copied the answer (Markdown with LaTeX).")

    def _choice_card(self, options, on_pick):
        px = self.px
        card = ttk.Frame(self.text, style="Well.TFrame", padding=(px(16), px(12)))
        ttk.Label(card, text=f"I found {len(options)} problems in this picture. Which one should I solve?",
                  style="Raised.Bold.TLabel", wraplength=px(440), justify="left").pack(anchor="w")
        for n, (label, markdown) in enumerate(options, 1):
            row = ttk.Frame(card, style="Well.TFrame")
            row.pack(fill="x", pady=(px(8), 0))
            ttk.Button(row, text=f"Solve {label}" if label else f"Solve #{n}", style="Small.TButton",
                       command=lambda lb=label, md=markdown: on_pick(lb, md)).pack(side="left", anchor="n")
            preview = " ".join(markdown.split())
            ttk.Label(row, text=preview[:140] + ("…" if len(preview) > 140 else ""), style="Raised.Muted.TLabel",
                      wraplength=px(330), justify="left").pack(side="left", padx=(px(10), 0))
        self._windows.append(card)
        self.text.window_create("end-1c", window=card)
        self._insert("\n", ("p",))

    def _setup_card(self, message):
        t, px = self.t, self.px
        card = ttk.Frame(self.text, style="Well.TFrame", padding=(px(16), px(12)))
        width = px(440)
        automatic = reader_setup.enabled()
        ttk.Label(card, text="The picture reader isn't ready", style="Raised.Bold.TLabel").pack(anchor="w")
        ttk.Label(card, text=message, style="Raised.Muted.TLabel", wraplength=width, justify="left").pack(
            anchor="w", pady=(px(4), px(8)))
        lines = (("Set it up installs Ollama and downloads the reading model (about 6 GB, once), by itself.",)
                 if automatic else
                 ("1.  Install Ollama from ollama.com (free; it runs on this PC, offline).",
                  f"2.  In a terminal: {ollama.PULL_HINT}   (about 5 GB, once)"))
        for line in lines:
            ttk.Label(card, text=line, style="Raised.TLabel", wraplength=width, justify="left").pack(anchor="w")
        ttk.Label(card, text="Typed problems work without it.", style="Raised.Faint.TLabel").pack(
            anchor="w", pady=(px(8), 0))
        ttk.Button(card, text="Set it up" if automatic else "Check again", style="Accent.TButton",
                   command=self.page.start_reader_setup if automatic else self.page.check_models).pack(
            anchor="w", pady=(px(10), 0))
        self._windows.append(card)
        self.text.window_create("end-1c", window=card)
        self._insert("\n", ("p",))


def _block_end(md: str, start: int) -> int:
    """Where the finished Markdown blocks end: after the last blank line past `start` that is not inside $$."""
    for m in reversed(list(re.finditer(r"\n[ \t]*\n", md))):
        if m.start() < start:
            break
        if md.count("$$", 0, m.start()) % 2 == 0:
            return m.end()
    return start


# ============================================================================================== page ==
class NotebookPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        t, px = app.theme, app.theme.px
        g = px(GUTTER)
        self.library = None
        self._warmed = set()
        self.cache = nb_cache.Cache(notebook_dir() / "answers.json")      # verified answers and readings
        self._rechecks = {}        # answer Markdown -> the verify.Pending that can check it again
        self._manual = set()       # ids of the Pending the user asked to check again (they get a reply either way)
        self._checks = []          # answers waiting for their background re-check
        self._checker = None       # the Checker running now, and the answer it is re-checking
        self._checking = None
        self.index = None
        self.pdf = None             # open PdfDoc in the page picker
        self.pdf_index = 0
        self.view = None            # how the PDF page picture was drawn
        self.image = None           # the page picture in the picker
        self.crop = None            # (x0, y0, x1, y1) in picture pixels
        self._shown_scale = 1.0
        self._offset = (0, 0)
        self._photo = None
        self._thumbs = []           # PhotoImages of the bubbles
        self._turn = None           # the running session.Turn
        self._turns = 0
        self._models = None         # [(name, capabilities)] from Ollama, None until checked
        self._jobs = queue.Queue()
        self._pending = 0
        self._spinning = 0          # jobs that show the header's busy bar
        self._setup_state = None    # the picture reader's automatic setup: None, "running", "done" or "failed"
        self._setup_chat = None
        self._gemini_problem = None  # why Gemini didn't help the last turn (shown in the Model menu)
        self._gemini_window = None
        self._tipped = False         # the "add a Gemini key" tip is shown once per session
        self._token = {}
        self._loading = False

        # header -----------------------------------------------------------------------------------------
        head = ttk.Frame(self, style="Card.TFrame", padding=(px(14), px(10)))
        head.pack(fill="x", padx=g, pady=(g, 0))
        inner = tk.Frame(head, background=C["panel"])
        inner.pack(fill="x")
        from .app import back_button, theme_button
        back_button(inner, app).pack(side="left")
        ttk.Label(inner, text="Notebook", style="Panel.H3.TLabel").pack(side="left", padx=(px(14), 0))
        ttk.Label(inner, text="Solve a statistics problem from a photo, a PDF or text",
                  style="Panel.Muted.TLabel").pack(side="left", padx=(px(10), 0))
        theme_button(inner, app).pack(side="right", padx=(px(4), 0))
        self.model_var = tk.StringVar(value=app.cfg.get("notebook_reader_model") or "")
        self.model_button = ttk.Menubutton(inner, text="Model", style="Ghost.TMenubutton")
        self.model_button.pack(side="right", padx=(0, px(4)))
        self.model_menu = t.menu(self.model_button)
        self.model_button["menu"] = self.model_menu
        Tooltip(self.model_button, "The local model (Ollama) that reads pictures")
        self.new_btn = ttk.Button(inner, text="New chat", image=t.icon_states("plus", 16), compound="left",
                                  style="Ghost.TButton", command=self.new_chat)
        self.new_btn.pack(side="right", padx=(0, px(4)))

        body = tk.Frame(self, background=C["bg"])
        body.pack(fill="both", expand=True, padx=g, pady=g)
        body.columnconfigure(0, weight=5, uniform="nb")
        body.columnconfigure(1, weight=7, uniform="nb")
        body.rowconfigure(0, weight=1)
        self._build_problem(body, t, px).grid(row=0, column=0, sticky="nsew", padx=(0, px(6)))
        self._build_answer(body, t, px).grid(row=0, column=1, sticky="nsew", padx=(px(6), 0))
        app.bind_all("<Control-v>", self._ctrl_v, add="+")
        self._fill_model_menu()
        if reader_setup.enabled():
            self.after(1500, self.start_reader_setup)     # first start: Ollama and its model, in the background

    # ------------------------------------------------------------------------------------------- layout --
    def _card(self, parent, px):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(px(18), px(14)))
        inner = tk.Frame(card, background=C["panel"])
        inner.pack(fill="both", expand=True)
        return card, inner

    def _build_problem(self, parent, t, px):
        card, box = self._card(parent, px)
        ttk.Label(box, text="Your problem", style="Panel.H3.TLabel").pack(anchor="w", side="top")

        # composer (bottom) -----------------------------------------------------------------------------
        composer = tk.Frame(box, background=C["panel"])
        composer.pack(side="bottom", fill="x", pady=(px(8), 0))
        row = tk.Frame(composer, background=C["panel"])
        row.pack(fill="x")
        self.entry = PlaceholderEntry(row, placeholder="Or type a problem…", style="Panel.TEntry")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: (self.send_text(), "break")[1])
        self.entry.bind("<<Paste>>", self._entry_paste)
        self.send_btn = ttk.Button(row, image=t.icon("arrow", "on_accent", 16), style="Accent.TButton",
                                   command=self.send_text)
        self.send_btn.pack(side="left", padx=(px(6), 0))
        Tooltip(self.send_btn, "Solve the typed problem (Enter)")
        buttons = tk.Frame(composer, background=C["panel"])
        buttons.pack(fill="x", pady=(px(8), 0))
        self.open_btn = ttk.Button(buttons, text="Open image or PDF…", image=t.icon("folder", "muted", 16),
                                   compound="left", command=self.open_dialog)
        self.open_btn.pack(side="left")
        self.paste_btn = ttk.Button(buttons, text="Paste screenshot", image=t.icon("image", "muted", 16),
                                    compound="left", command=self.paste_image)
        self.paste_btn.pack(side="left", padx=(px(6), 0))
        Tooltip(self.paste_btn, "Solve the screenshot on the clipboard (Ctrl+V)")
        self.note_label = ttk.Label(box, style="Panel.Muted.TLabel", justify="left", wraplength=px(420))
        self.note_label.pack(side="bottom", anchor="w", fill="x")

        # PDF page picker (shown above the composer while a PDF is open) ---------------------------------
        self.picker = ttk.Frame(box, style="Well.TFrame", padding=(px(10), px(8)))
        top = tk.Frame(self.picker, background=C["raised"])
        top.pack(fill="x")
        ttk.Button(top, image=t.icon_states("chevron_left", 16), style="Icon.TButton",
                   command=lambda: self.show_pdf_page(self.pdf_index - 1)).pack(side="left")
        self.page_label = ttk.Label(top, style="Raised.Muted.TLabel")
        self.page_label.pack(side="left", padx=px(4))
        ttk.Button(top, image=t.icon_states("chevron_right", 16), style="Icon.TButton",
                   command=lambda: self.show_pdf_page(self.pdf_index + 1)).pack(side="left")
        close = ttk.Button(top, image=t.icon_states("close", 16), style="Icon.TButton", command=self._close_pdf)
        close.pack(side="right")
        Tooltip(close, "Close the PDF")
        self.canvas = tk.Canvas(self.picker, height=px(260), background=C["field"], highlightthickness=1,
                                highlightbackground=C["border_strong"], borderwidth=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, pady=(px(6), px(6)))
        self.canvas.bind("<Configure>", lambda e: self._draw_image())
        self.canvas.bind("<ButtonPress-1>", self._crop_start)
        self.canvas.bind("<B1-Motion>", self._crop_drag)
        self.canvas.bind("<ButtonRelease-1>", self._crop_end)
        self.canvas.bind("<Double-Button-1>", lambda e: self._clear_crop())
        bottom = tk.Frame(self.picker, background=C["raised"])
        bottom.pack(fill="x")
        self.solve_btn = ttk.Button(bottom, text="Solve this page", style="Accent.TButton", command=self.solve_pdf)
        self.solve_btn.pack(side="right")
        ttk.Label(bottom, text="Drag around one problem to solve only that one.", style="Raised.Faint.TLabel").pack(
            side="left")

        # the turns ---------------------------------------------------------------------------------------
        self.turns = ScrollFrame(box, t, bg=C["panel"])
        self.turns.pack(side="top", fill="both", expand=True, pady=(px(8), 0))
        self.empty = tk.Frame(self.turns.body, background=C["panel"])
        self.empty.pack(fill="x", pady=(px(60), 0))
        tk.Label(self.empty, image=t.icon("image", "faint", 32), background=C["panel"]).pack()
        tk.Label(self.empty, text="Open or paste a picture of a problem", background=C["panel"],
                 foreground=C["text"], font=t.f["bold"]).pack(pady=(px(8), px(2)))
        tk.Label(self.empty, text="A photo, a screenshot (Ctrl+V) or a PDF page.\nThe worked solution appears on "
                                  "the right.", background=C["panel"], foreground=C["muted"], font=t.f["small"],
                 justify="center").pack()
        return card

    def _build_answer(self, parent, t, px):
        card, box = self._card(parent, px)
        top = tk.Frame(box, background=C["panel"])
        top.pack(fill="x")
        ttk.Label(top, text="Solution", style="Panel.H3.TLabel").pack(side="left")
        self.stop_btn = ttk.Button(top, text="Stop", image=t.icon("close", "muted", 14), compound="left",
                                   style="Small.TButton", command=self.stop)
        self.progress = ttk.Progressbar(top, mode="indeterminate", length=px(90))
        self.status = ttk.Label(top, style="Panel.Muted.TLabel")
        self.status.pack(side="right", padx=(px(10), 0))
        # shown while the picture reader sets itself up (first start on Windows), with its own progress bar
        self.setup_box = tk.Frame(box, background=C["panel"])
        self.setup_label = ttk.Label(self.setup_box, style="Panel.Muted.TLabel", justify="left", wraplength=px(560))
        self.setup_label.pack(anchor="w")
        row = tk.Frame(self.setup_box, background=C["panel"])
        row.pack(fill="x", pady=(px(4), 0))
        self.setup_bar = ttk.Progressbar(row, mode="determinate", maximum=1.0)
        self.setup_retry = ttk.Button(row, text="Try again", style="Small.TButton",
                                      command=lambda: self.start_reader_setup())
        self.answers = AnswerView(box, self)
        self.answers.pack(fill="both", expand=True, pady=(px(8), 0))
        return card

    # ---------------------------------------------------------------------------------------- page hooks --
    def on_show(self):
        if self.library is None and not self._loading:
            self.reload_library()
        if self._models is None:
            self.check_models(quiet=True)

    # ---------------------------------------------------------------------------------------- workers --
    def _run(self, kind, work, done, on_event=None):
        """Run `work()` in a thread (`work(emit)` when `on_event` is given: emit(event) calls on_event(event)
        on the Tk thread); `done(result, error)` runs on the Tk thread. A newer job of the same kind makes the
        older one's results be ignored."""
        token = self._token[kind] = self._token.get(kind, 0) + 1

        def emit(event):
            self._jobs.put((kind, token, on_event, event, STREAM))

        def target():
            try:
                self._jobs.put((kind, token, done, work(emit) if on_event else work(), None))
            except BaseException as exc:  # noqa: BLE001 - handed to `done`, which shows it
                self._jobs.put((kind, token, done, None, exc))

        self._pending += 1
        if self._pending == 1:
            self.after(40, self._drain)
        if kind not in OWN_PROGRESS:
            self._spin(1)
        gc.collect()      # free dead Tk objects here: Tk must not delete them from the worker thread
        threading.Thread(target=target, daemon=True).start()

    def _drain(self):
        while True:
            try:
                kind, token, handler, result, error = self._jobs.get_nowait()
            except queue.Empty:
                break
            if error is STREAM:
                if token == self._token.get(kind):
                    handler(result)
                continue
            self._pending -= 1
            if kind not in OWN_PROGRESS:
                self._spin(-1)
            if token == self._token.get(kind):
                handler(result, error)
        if self._pending > 0:
            self.after(40, self._drain)

    def _spin(self, step):
        """The small busy bar in the Solution header, while any job without its own progress runs."""
        self._spinning += step
        if self._spinning == 1 and step > 0:
            self.progress.pack(side="right", padx=(self.app.theme.px(8), 0))
            self.progress.start(12)
        elif self._spinning == 0:
            self.progress.stop()
            self.progress.pack_forget()

    # ------------------------------------------------------------------------------------------ library --
    def reload_library(self):
        """Read the solutions that come with the app in a worker (parsed once, then cached by the file's hash)."""
        files = list(LIBRARY_FILES)
        self._loading = True
        cache = notebook_dir() / "index.json"
        self._run("library", lambda: nb_library.load(files, cache_path=cache), self._library_loaded)

    def _library_loaded(self, lib, error):
        self._loading = False
        if error is None and not lib.exercises:
            error = FileNotFoundError("; ".join(str(p) for p in lib.problems) or "no exercises found")
        if error is not None:
            log_error("Notebook: couldn't read the built-in solutions", error)
            self.answers.note(f"The built-in solutions couldn't be read ({error}). Reinstall the app to restore "
                              f"{nb_library.BUILT_IN.name}.", "error")
            return
        self.library, self.index = lib, nb_lookup.Index(lib)

    # ------------------------------------------------------------------------------------------- models --
    def _url(self):
        return self.app.cfg.get("notebook_ollama_url") or ollama.DEFAULT_URL

    def start_reader_setup(self):
        """Install Ollama and download the reading model in the background, showing progress (Windows)."""
        if self._setup_state == "running":
            return
        self._setup_state = "running"
        url, chat = self._url(), ollama.Chat(self._url(), timeout=600)
        self._setup_chat = chat
        self.setup_retry.pack_forget()
        self._run("setup", lambda emit: reader_setup.ensure(url, lambda text, part: emit((text, part)), chat),
                  self._setup_done, on_event=self._setup_event)

    def _setup_event(self, event):
        text, part = event
        if part == 1.0:
            return                  # finished: _setup_done hides the box
        px = self.app.theme.px
        if not self.setup_box.winfo_manager():
            self.setup_box.pack(fill="x", pady=(px(8), 0), before=self.answers)
        if not self.setup_bar.winfo_manager():
            self.setup_bar.pack(side="left", fill="x", expand=True)
        self.setup_label.configure(text=f"Setting up the picture reader (once): {text}  Typed problems work now.",
                                   style="Panel.Muted.TLabel")
        if part is None:
            if str(self.setup_bar.cget("mode")) != "indeterminate":
                self.setup_bar.configure(mode="indeterminate", maximum=100)
                self.setup_bar.start(12)
        else:
            self.setup_bar.stop()
            self.setup_bar.configure(mode="determinate", maximum=1.0, value=part)

    def _setup_done(self, model, error):
        self.setup_bar.stop()
        if error is None:
            self._setup_state = "done"
            self.setup_box.pack_forget()
            self.check_models(quiet=True)
            return
        self._setup_state = "failed"
        log_error("Notebook: setting up the picture reader failed", error)
        self.setup_bar.pack_forget()
        self.setup_label.configure(text=f"The picture reader couldn't be set up: {error}", style="Error.TLabel")
        self.setup_retry.pack(side="left")
        if not self.setup_box.winfo_manager():
            self.setup_box.pack(fill="x", pady=(self.app.theme.px(8), 0), before=self.answers)

    def check_models(self, quiet=False):
        url = self._url()
        self._run("models", lambda: ollama.models(url), lambda found, error: self._models_found(found, error, quiet))

    def _models_found(self, found, error, quiet):
        if error is not None:
            self._models = []
            if not isinstance(error, ollama.OllamaError):
                log_error("Notebook: couldn't ask Ollama for its models", error)
            if not quiet:
                self.answers.setup(str(error))
        else:
            self._models = found
            if not quiet:
                chosen = ollama.pick(found, "vision", self.model_var.get(), avoid="thinking")
                self.set_status(f"Ready: {chosen}" if chosen else "")
                if chosen is None:
                    self.answers.setup("Ollama is running, but none of its models can read pictures.")
        self._fill_model_menu()
        chosen = ollama.pick(self._models, "vision", self.model_var.get(), avoid="thinking") if self._models else None
        if chosen and chosen not in self._warmed:       # load it now, while the user is still choosing a picture
            self._warmed.add(chosen)
            url = self._url()
            self._run("warm", lambda: ollama.warm(url, chosen), lambda result, err: None)

    def _fill_model_menu(self):
        menu = self.model_menu
        menu.delete(0, "end")
        found = self._models or []
        vision = [n for n, caps in found if "vision" in caps]
        chosen = ollama.pick(found, "vision", self.model_var.get(), avoid="thinking")
        if chosen:
            self.model_var.set(chosen)
        for name in vision:
            menu.add_radiobutton(label=name, value=name, variable=self.model_var, command=self._model_chosen)
        if not vision:
            menu.add_command(label="Looking for models…" if self._models is None else
                             "No picture-reading model found", state="disabled")
        menu.add_separator()
        menu.add_command(label="Check again", command=self.check_models)
        menu.add_separator()
        has_key = bool(self.app.cfg.get("notebook_gemini_key"))
        if has_key:
            model = self.app.cfg.get("notebook_gemini_model") or gemini.MODELS[0]
            state = f"Gemini: {self._gemini_problem}" if self._gemini_problem else f"Gemini: on · {model}"
            menu.add_command(label=state if len(state) < 90 else state[:87] + "…", state="disabled")
            menu.add_command(label="Change the Gemini key…", command=self.gemini_dialog)
            menu.add_command(label="Remove the Gemini key", command=self.remove_gemini_key)
        else:
            menu.add_command(label="Gemini: add a free key for better solutions…", command=self.gemini_dialog)
        self.model_button.configure(text=(chosen or "Model") + (" + Gemini" if has_key else ""))

    def _model_chosen(self):
        self.app.cfg["notebook_reader_model"] = self.model_var.get()
        settings.save(self.app.cfg)
        self._fill_model_menu()

    # ------------------------------------------------------------------------------------------- input --
    def open_dialog(self):
        path = filedialog.askopenfilename(
            parent=self, title="Open a picture or PDF of a problem",
            initialdir=self.app.cfg.get("last_dir") or str(Path.home()),
            filetypes=[("Pictures and PDFs", " ".join(f"*{s}" for s in sorted(IMAGE_TYPES)) + " *.pdf"),
                       ("PDF files", "*.pdf"), ("All files", "*.*")])
        if path:
            self.open_path(path)

    def open_path(self, path, password=None):
        path = Path(path)
        if path.suffix.lower() == ".pdf":
            self._close_pdf()
            from .core.pdf_import.inspect import PasswordNeeded, PdfDoc, PdfError, WrongPassword
            try:
                self.pdf = PdfDoc(path, password=password, max_mb=50)
            except PasswordNeeded as exc:
                prompt = ("That password didn't open it. Try again:" if isinstance(exc, WrongPassword) else
                          f"{path.name} is protected with a password. Enter it:")
                answer = simpledialog.askstring(APP_NAME, prompt, show="•", parent=self)
                if answer:
                    self.open_path(path, answer)
                return
            except (PdfError, OSError) as exc:
                self._note(str(exc) or type(exc).__name__, "Error.TLabel")
                return
            self.picker.pack(side="bottom", fill="both", pady=(self.app.theme.px(8), 0), before=self.note_label)
            self.show_pdf_page(0)
            return
        if path.suffix.lower() not in IMAGE_TYPES:
            self._note("Use a picture (PNG, JPG, WEBP …) or a PDF.", "Error.TLabel")
            return
        try:
            from PIL import Image
            if path.stat().st_size > reader.MAX_IMAGE_BYTES:
                raise ValueError("This image is too large. The maximum supported size is 50 MB.")
            with Image.open(path) as im:
                im.load()
                image = im.convert("RGB")
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self._note(f"Couldn't open {path.name}: {exc}", "Error.TLabel")
            return
        self.submit(session.Source(path.name, image), image)

    def _clipboard_picture(self):
        """What the clipboard holds: a PIL image, a path of a picture or PDF, or None."""
        from PIL import Image, ImageGrab
        grabbed = ImageGrab.grabclipboard()
        if isinstance(grabbed, list):
            return next((Path(p) for p in grabbed if Path(p).suffix.lower() in IMAGE_TYPES | {".pdf"}), None)
        return grabbed.convert("RGB") if isinstance(grabbed, Image.Image) else None

    def paste_image(self):
        try:
            found = self._clipboard_picture()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self._note(f"Couldn't read the clipboard: {exc}", "Error.TLabel")
            return
        if isinstance(found, Path):
            self.open_path(found)
        elif found is not None:
            self.submit(session.Source("Screenshot", found), found)
        else:
            self._note("The clipboard has no picture. Copy a screenshot of the problem, or type it below.",
                       "Warn.TLabel")

    def _entry_paste(self, _e):
        """Ctrl+V in the text box: a picture on the clipboard is solved, text is pasted as usual."""
        try:
            found = self._clipboard_picture()
        except Exception:  # noqa: BLE001 - no picture there: the default paste of text runs
            return None
        if found is None:
            return None
        self.open_path(found) if isinstance(found, Path) else self.submit(session.Source("Screenshot", found), found)
        return "break"

    def _ctrl_v(self, _e):
        if self.app.current != "notebook":
            return
        try:
            focus = self.focus_get()
        except (KeyError, tk.TclError):   # focus inside a combobox drop-down
            return
        if isinstance(focus, (tk.Entry, ttk.Entry)) or (isinstance(focus, tk.Text) and
                                                        str(focus.cget("state")) == "normal"):
            return           # a text box pastes for itself (the composer's: see _entry_paste)
        self.paste_image()

    def send_text(self):
        text = self.entry.value().strip()
        if not text:
            return
        if self.submit(session.Source("Typed", text=text)):
            self.entry.set_value("")

    # ---------------------------------------------------------------------------------------------- PDFs --
    def _close_pdf(self):
        if self.pdf is not None:
            try:
                self.pdf.close()
            except Exception as exc:  # noqa: BLE001 - closing a document we no longer need
                log_error("Notebook: couldn't close the PDF", exc)
        self.pdf, self.view, self.image, self.crop = None, None, None, None
        self.picker.pack_forget()

    def show_pdf_page(self, index):
        if self.pdf is None or not 0 <= index < self.pdf.n_pages:
            return
        self.pdf_index = index
        self.page_label.configure(text=f"{self.pdf.name} · page {index + 1} of {self.pdf.n_pages}")
        doc = self.pdf
        self._run("render", lambda: doc.render(index, dpi=reader.PDF_DPI), self._pdf_drawn)

    def _pdf_drawn(self, result, error):
        if error is not None:
            self._note(f"Couldn't draw the page: {error}", "Error.TLabel")
            return
        self.image, self.view = result
        self.crop = None
        self.solve_btn.configure(text="Solve this page")
        self._draw_image()

    def solve_pdf(self):
        if self.pdf is None or self.image is None:
            return
        doc, index, crop, view = self.pdf, self.pdf_index, self.crop, self.view
        thumb = self.image.crop(tuple(int(v) for v in crop)) if crop else self.image
        name = f"{doc.name}, page {index + 1}" + (" (marked part)" if crop else "")
        load = lambda: (reader.page_image(doc, index, crop, view), reader.text_layer(doc, index, crop, view))  # noqa: E731
        self.submit(session.Source(name, load=load), thumb)

    def _draw_image(self):
        c = self.canvas
        c.delete("all")
        if self.image is None:
            return
        from PIL import ImageTk
        w, h = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        iw, ih = self.image.size
        k = min(w / iw, h / ih, 2.0)
        self._shown_scale = k
        shown = self.image.resize((max(1, int(iw * k)), max(1, int(ih * k))))
        self._photo = ImageTk.PhotoImage(shown, master=self)
        self._offset = ((w - shown.width) / 2, (h - shown.height) / 2)
        c.create_image(*self._offset, image=self._photo, anchor="nw")
        if self.crop:
            self._draw_crop()

    def _to_image(self, x, y):
        ox, oy = self._offset
        k = self._shown_scale or 1.0
        iw, ih = self.image.size
        return min(max((x - ox) / k, 0), iw), min(max((y - oy) / k, 0), ih)

    def _draw_crop(self):
        x0, y0, x1, y1 = self.crop
        ox, oy = self._offset
        k = self._shown_scale
        self.canvas.delete("crop")
        self.canvas.create_rectangle(ox + x0 * k, oy + y0 * k, ox + x1 * k, oy + y1 * k, outline=C["accent"],
                                     width=2, dash=(6, 3), tags="crop")

    def _crop_start(self, e):
        if self.image is not None:
            self._drag = self._to_image(e.x, e.y)

    def _crop_drag(self, e):
        if self.image is None or not getattr(self, "_drag", None):
            return
        (x0, y0), (x1, y1) = self._drag, self._to_image(e.x, e.y)
        self.crop = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        self._draw_crop()

    def _crop_end(self, _e):
        self._drag = None
        if self.crop and (self.crop[2] - self.crop[0] < 8 or self.crop[3] - self.crop[1] < 8):
            self._clear_crop()
        elif self.crop:
            self.solve_btn.configure(text="Solve the marked part")

    def _clear_crop(self):
        self.crop = None
        self.canvas.delete("crop")
        self.solve_btn.configure(text="Solve this page")

    # --------------------------------------------------------------------------------------------- turns --
    def submit(self, source, picture=None) -> bool:
        """Start a turn: a bubble on the left, its answer streamed on the right. False while one is running."""
        if self._turn is not None:
            self._note("Wait for this answer, or press Stop.", "Warn.TLabel")
            return False
        if self._loading:
            self._note("Your solutions are still loading. Try again in a moment.", "Warn.TLabel")
            return False
        if self._setup_state == "running" and (source.image is not None or source.load is not None):
            self._note("The picture reader is still being set up (progress on the right). Typed problems work "
                       "now; pictures will in a moment.", "Warn.TLabel")
            return False
        if self.library is None:
            self._note("The built-in solutions couldn't be read (see the message on the right).", "Error.TLabel")
            return False
        self._note("")
        self._stop_checking()                      # a new problem comes first: the re-checks go on afterwards
        self._turns += 1
        self._bubble(self._turns, source.name, picture, source.text)
        self.answers.add_turn(self._turns)
        self.set_status("Working…")
        self._busy(True)
        cfg = self.app.cfg
        self._turn = session.Turn(source, self.index, self._url(), self.model_var.get(), history_path(),
                                  gemini_key=cfg.get("notebook_gemini_key") or "",
                                  gemini_model=cfg.get("notebook_gemini_model") or "", gemini_base=self._gemini_url(),
                                  cache=self.cache, prerender=self.answers.prerender)
        self._run("turn", self._turn.run, self._turn_done, on_event=self._turn_event)
        return True

    def _turn_event(self, event):
        kind, value = event
        if kind == "status":
            self.set_status(value)
        elif kind == "start":
            self.answers.begin()
        elif kind == "text":
            self.answers.feed(value)
        elif kind == "end":
            self._remember_answer()
            self.answers.end(value)
        elif kind == "choose":
            self.answers.add_choice(value, self._pick)

    def _pick(self, label, markdown):
        """The user chose one of a picture's problems: it is solved as typed text (no second reading)."""
        self.submit(session.Source(f"Problem {label}" if label else "Problem", text=markdown, label=label))

    def _remember_answer(self):
        """The answer just finished can be checked again (the Check again button): keep what that needs."""
        turn = self._turn
        if turn is None or not turn.answers or "solution" not in turn.answers[-1]:
            return
        a = turn.answers[-1]
        self._rechecks[a["answer"]] = verify.Pending(a.get("label", ""), a["problem"], a["solution"],
                                                     a.get("by", "qwen"), turn.source.image, turn._context(a["problem"]))

    def can_recheck(self, markdown):
        return markdown in self._rechecks

    def recheck(self, markdown):
        """Check again: forget the remembered answer, and solve it again independently, now (or when this ends)."""
        pending = self._rechecks.get(markdown)
        if pending is None:
            return
        self.cache.drop(pending.problem)
        self._manual.add(id(pending))
        self._checks.insert(0, pending)
        if self._turn is None and self._checker is None:
            self._check_next()
        else:
            self.set_status("I'll check it again as soon as this is finished.")

    def _turn_done(self, _answers, error):
        turn, self._turn = self._turn, None
        self._busy(False)
        self.set_status("")
        if turn is not None:
            self._gemini_state(turn)
        if error is None:
            if turn is not None:
                self._checks.extend(turn.pending)
                self._check_next()
            return
        self.answers.finish()           # keep what had arrived, drawn
        if isinstance(error, (ollama.Cancelled, gemini.Cancelled)):
            self.answers.note("Stopped.")
        elif isinstance(error, ollama.NotReady):
            self.answers.setup(str(error))
            self.check_models(quiet=True)
        elif isinstance(error, (ollama.OllamaError, gemini.GeminiError, solver.SolverError)):
            log_error("Notebook: the model failed", error)
            self.answers.note(str(error), "error")
        else:
            log_error("Notebook: a turn failed", error)
            self.answers.note(f"Something went wrong: {type(error).__name__}: {error}", "error")

    # --------------------------------------------------------------------------------------- re-checks --
    def _check_next(self):
        """Re-solve the next shown-fast answer in the background, only while nothing else is going on."""
        if self._turn is not None or self._checker is not None or not self._checks:
            return
        cfg, pending = self.app.cfg, self._checks.pop(0)
        self._checker, self._checking = session.Checker(
            self._url(), self.model_var.get(), cfg.get("notebook_gemini_key") or "",
            cfg.get("notebook_gemini_model") or "", self._gemini_url()), pending
        checker = self._checker
        self.set_status("Re-checking an earlier answer…")
        self._run("verify", lambda: checker.check(pending), self._checked)

    def _checked(self, verdict, error):
        pending, self._checker, self._checking = self._checking, None, None
        asked = pending is not None and id(pending) in self._manual
        self._manual.discard(id(pending))
        if error is not None:
            if not isinstance(error, (ollama.Cancelled, gemini.Cancelled)):
                log_error("Notebook: the background re-check failed", error)      # nothing to tell the user
                if asked:
                    self.answers.note(f"I couldn't check it again: {error}", "error")
        elif verdict.correction:
            self.cache.drop(pending.problem)
            self.answers.add_correction(verdict.correction)
        else:
            if verdict.agrees:
                self.cache.verify(pending.problem)          # now it may be shown again straight away
            if asked:
                self.answers.note("Checked again: I get the same answer." if verdict.agrees else
                                  "I checked it again, but the two answers have no final numbers to compare.")
        if self._turn is None:
            self.set_status("A correction was added below." if error is None and verdict.correction else "")
        self._check_next()

    def _stop_checking(self):
        """A re-check never delays a new problem: stop it now and put its answer back first in line."""
        self._token["verify"] = self._token.get("verify", 0) + 1       # its result, if it still comes, is ignored
        if self._checker is not None:
            self._checker.cancel()
            self._checks.insert(0, self._checking)
        self._checker, self._checking = None, None

    def _gemini_state(self, turn):
        """After a turn: what the Model menu says about Gemini, and the one-time tip to add a key."""
        has_key = bool(self.app.cfg.get("notebook_gemini_key"))
        solved = [a for a in turn.answers if str(a.get("from", "")).startswith("solver:")]
        if turn.gemini_problem:
            self._gemini_problem = turn.gemini_problem
        elif any(s.get("solver") == "gemini" for a in solved for s in a.get("solutions", [])):
            self._gemini_problem = None
        self._fill_model_menu()
        if solved and not has_key and not self._tipped:
            self._tipped = True
            self._note(GEMINI_TIP, "Panel.Muted.TLabel")

    # -------------------------------------------------------------------------------------------- Gemini --
    def _gemini_url(self):
        return self.app.cfg.get("notebook_gemini_url") or gemini.BASE_URL

    def gemini_dialog(self):
        """Add (or change) the user's own free Gemini key; it is checked before it is saved."""
        t, px = self.app.theme, self.app.theme.px
        win = tk.Toplevel(self)
        win.title("Gemini key")
        win.transient(self.winfo_toplevel())
        win.configure(background=C["bg"])
        win.resizable(False, False)
        card = ttk.Frame(win, style="Card.TFrame", padding=(px(20), px(16)))
        card.pack(fill="both", expand=True, padx=px(12), pady=px(12))
        box = tk.Frame(card, background=C["panel"])
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Better solutions with Gemini (optional)", style="Panel.H3.TLabel").pack(anchor="w")
        ttk.Label(box, text=GEMINI_NOTICE, style="Panel.Muted.TLabel", wraplength=px(470), justify="left").pack(
            anchor="w", pady=(px(6), px(8)))
        ttk.Button(box, text="Get a free key at aistudio.google.com", style="Link.TButton",
                   command=lambda: webbrowser.open(gemini.KEY_PAGE)).pack(anchor="w")
        win.entry = ttk.Entry(box, show="•", width=52, style="Panel.TEntry")
        win.entry.pack(fill="x", pady=(px(10), px(4)))
        win.message = ttk.Label(box, style="Panel.Muted.TLabel", wraplength=px(470), justify="left")
        win.message.pack(anchor="w", fill="x")
        row = tk.Frame(box, background=C["panel"])
        row.pack(fill="x", pady=(px(12), 0))
        win.save = ttk.Button(row, text="Save", style="Accent.TButton", command=lambda: self._check_key(win))
        win.save.pack(side="right")
        ttk.Button(row, text="Cancel", command=win.destroy).pack(side="right", padx=(0, px(6)))
        win.entry.bind("<Return>", lambda e: self._check_key(win))
        win.entry.focus_set()
        self._gemini_window = win
        return win

    def _check_key(self, win):
        key = win.entry.get().strip()
        if not key:
            win.message.configure(text="Paste the key first.", style="Warn.TLabel")
            return
        win.save.state(["disabled"])
        win.message.configure(text="Checking the key…", style="Panel.Muted.TLabel")
        base = self._gemini_url()
        self._run("gemini_key", lambda: gemini.Gemini(key, base).models(),
                  lambda found, error: self._key_checked(win, key, found, error))

    def _key_checked(self, win, key, found, error):
        if not win.winfo_exists():
            return
        if error is not None:
            if not isinstance(error, gemini.GeminiError):
                log_error("Notebook: checking the Gemini key failed", error)
            win.message.configure(text=str(error), style="Error.TLabel")
            win.save.state(["!disabled"])
            return
        cfg = self.app.cfg
        cfg["notebook_gemini_key"] = key
        cfg["notebook_gemini_model"] = gemini.pick(found, cfg.get("notebook_gemini_model") or "") or gemini.MODELS[0]
        settings.save(cfg)
        self._gemini_problem = None
        self._fill_model_menu()
        self.set_status(f"Gemini is on ({cfg['notebook_gemini_model']}).")
        win.destroy()

    def remove_gemini_key(self):
        self.app.cfg.pop("notebook_gemini_key", None)
        settings.save(self.app.cfg)
        self._gemini_problem = None
        self._fill_model_menu()
        self.set_status("Gemini is off: new problems are solved on this computer only.")

    def stop(self):
        if self._turn is not None:
            self._turn.cancel()
            self.set_status("Stopping…")

    def new_chat(self):
        self.stop()
        self._stop_checking()
        self._checks.clear()
        self._token["turn"] = self._token.get("turn", 0) + 1     # results of a stopped turn are ignored
        self._turn = None
        self._busy(False)
        for child in self.turns.body.winfo_children():
            if child is not self.empty:
                child.destroy()
        self._thumbs = []
        self.empty.pack(fill="x", pady=(self.app.theme.px(60), 0))
        self.answers.clear()
        self._note("")
        self.set_status("")

    def _busy(self, busy):
        for b in (self.send_btn, self.open_btn, self.paste_btn, self.solve_btn):
            b.state(["disabled"] if busy else ["!disabled"])
        if busy:
            self.stop_btn.pack(side="right", padx=(self.app.theme.px(8), 0))
        else:
            self.stop_btn.pack_forget()

    def _bubble(self, n, name, picture, text):
        t, px = self.app.theme, self.app.theme.px
        self.empty.pack_forget()
        bubble = ttk.Frame(self.turns.body, style="Soft.TFrame", padding=(px(12), px(10)))
        bubble.pack(anchor="e", padx=(px(36), px(4)), pady=(px(4), px(6)))
        parts = []
        if picture is not None:
            from PIL import ImageTk
            shown = picture.copy()
            shown.thumbnail((px(THUMB), px(THUMB)))
            photo = ImageTk.PhotoImage(shown, master=self)
            self._thumbs.append(photo)
            parts.append(tk.Label(bubble, image=photo, background=C["accent_soft"], borderwidth=0))
        if text:
            parts.append(tk.Label(bubble, text=text, wraplength=px(320), justify="left", background=C["accent_soft"],
                                  foreground=C["text"], font=t.f["base"]))
        parts.append(tk.Label(bubble, text=f"{name} · {time.strftime('%H:%M')}", background=C["accent_soft"],
                              foreground=C["muted"], font=t.f["small"]))
        for i, part in enumerate(parts):
            part.pack(anchor="e" if part is parts[-1] else "w", pady=(px(6) if i else 0, 0))
        for w in [bubble] + parts:
            w.bind("<Button-1>", lambda e, n=n: self.answers.show_turn(n))
        self.after_idle(lambda: self.turns.canvas.yview_moveto(1.0))

    # ------------------------------------------------------------------------------------------- output --
    def open_in_browser(self, md):
        dark = self.app.theme.dark

        def write():
            folder = notebook_dir() / "answers"
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / "answer.html"
            path.write_text(render.answer_page(md, dark), encoding="utf-8")
            return path

        self._run("open", write, self._opened)

    def _opened(self, path, error):
        if error is not None:
            if not isinstance(error, render.RenderUnavailable):
                log_error("Notebook: couldn't write the answer page", error)
            messagebox.showerror(APP_NAME, str(error) if isinstance(error, render.RenderUnavailable) else
                                 f"Couldn't write the answer page:\n{type(error).__name__}: {error}", parent=self)
            return
        if not webbrowser.open(path.as_uri()):
            messagebox.showinfo(APP_NAME, f"No browser opened. Open this file yourself:\n{path}", parent=self)

    def set_status(self, text):
        self.status.configure(text=text)

    def _note(self, text, style="Panel.Muted.TLabel"):
        self.note_label.configure(text=text, style=style)
