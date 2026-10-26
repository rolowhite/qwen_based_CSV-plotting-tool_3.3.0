"""Notebook: a picture (or the typed text) of a statistics problem -> the matching exercise in the user's own
solution library -> its stored solution, shown in the browser with the math drawn by the bundled KaTeX.

The work (reading the library, OCR, writing the solution pages) runs in worker threads; results come back
through a queue.Queue that the window polls with after(). The library files are only read.
"""
from __future__ import annotations

import gc
import json
import queue
import re
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import APP_NAME, settings
from .core.notebook import library as nb_library
from .core.notebook import lookup as nb_lookup
from .core.notebook import ocr as nb_ocr
from .core.notebook import provenance, render
from .theme import C
from .widgets import AutoScrollbar, PlaceholderEntry, Tooltip

IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
HISTORY_LIMIT = 30
GUTTER = 12


def notebook_dir() -> Path:
    """Where the index cache, the solution pages and the feedback log live (next to the settings file)."""
    return settings.PATH.parent / ".csv_plot_studio" / "notebook"


def feedback_path() -> Path:
    return notebook_dir() / "notebook_feedback.jsonl"


def plain_problem(e: nb_library.Exercise) -> str:
    """The problem as plain text for the preview (the browser page shows it with the math drawn)."""
    text = e.problem_md or e.solution_md[:600]
    text = re.sub(r"(?m)^\|[-| :]+\|[ \t]*\n?", "", text)          # a Markdown table's |---|---| line
    return text.replace("**Problem:**", "").replace("**", "").replace("$", "").strip()


def log_feedback(text: str, shown, correct: str, candidates) -> dict:
    """One line in notebook_feedback.jsonl: what was read, what was shown, what the user says is right."""
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "text": text,
             "shown": shown.key if shown is not None else None, "correct": correct or None,
             "candidates": [{"exercise": c.exercise.key, "score": c.score} for c in candidates]}
    path = feedback_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


class NotebookPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        t, px = app.theme, app.theme.px
        g = px(GUTTER)
        self.library = None
        self.index = None
        self.result = None          # the last LookupResult
        self.current = None         # the Exercise in the detail panel
        self.listed = []            # what the list shows: exercises, in order
        self.image = None           # PIL image of the problem (a picture, or the PDF page)
        self.pdf = None             # open PdfDoc
        self.pdf_index = 0
        self.view = None            # how the PDF page picture was drawn
        self.crop = None            # (x0, y0, x1, y1) in image pixels
        self._shown_scale = 1.0
        self._photo = None
        self._jobs = queue.Queue()
        self._pending = 0
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
        ttk.Label(inner, text="Find a problem in your own solutions", style="Panel.Muted.TLabel").pack(
            side="left", padx=(px(10), 0))
        theme_button(inner, app).pack(side="right")
        self.lib_button = ttk.Menubutton(inner, text="Library: none", style="Ghost.TMenubutton")
        self.lib_button.pack(side="right", padx=(0, px(8)))
        menu = t.menu(self.lib_button)
        menu.add_command(label="Add a solutions folder…", command=self.add_folder)
        menu.add_command(label="Add a solutions file…", command=self.add_file)
        menu.add_command(label="Reload", command=self.reload_library)
        menu.add_command(label="Show load notes", command=self.show_load_notes)
        menu.add_separator()
        menu.add_command(label="Forget the library list", command=self.forget_library)
        self.lib_button["menu"] = menu
        Tooltip(self.lib_button, "The folders or .md files with your worked solutions (only read, never changed)")

        body = tk.Frame(self, background=C["bg"])
        body.pack(fill="both", expand=True, padx=g, pady=g)
        body.columnconfigure(0, weight=5, uniform="nb")
        body.columnconfigure(1, weight=6, uniform="nb")
        body.rowconfigure(0, weight=1)
        self._build_problem(body, t, px).grid(row=0, column=0, sticky="nsew", padx=(0, px(6)))
        self._build_result(body, t, px).grid(row=0, column=1, sticky="nsew", padx=(px(6), 0))
        self._set_detail(None)

    # ------------------------------------------------------------------------------------------- layout --
    def _card(self, parent, px):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(px(18), px(14)))
        inner = tk.Frame(card, background=C["panel"])
        inner.pack(fill="both", expand=True)
        return card, inner

    def _build_problem(self, parent, t, px):
        card, box = self._card(parent, px)
        ttk.Label(box, text="Problem", style="Panel.H3.TLabel").pack(anchor="w")
        row = tk.Frame(box, background=C["panel"])
        row.pack(fill="x", pady=(px(8), px(6)))
        self.open_btn = ttk.Button(row, text="Open image or PDF…", image=t.icon("folder", "on_accent", 16),
                                   compound="left", style="Accent.TButton", command=self.open_dialog)
        self.open_btn.pack(side="left")
        self.paste_btn = ttk.Button(row, text="Paste screenshot", image=t.icon("image", "muted", 16),
                                    compound="left", command=self.paste_image)
        self.paste_btn.pack(side="left", padx=(px(6), 0))
        Tooltip(self.paste_btn, "Read a problem from a screenshot on the clipboard (Ctrl+Shift+V)")
        self.read_btn = ttk.Button(row, text="Read text", command=self.read_text)
        self.read_btn.pack(side="left", padx=(px(6), 0))
        Tooltip(self.read_btn, "Read the picture (or the marked part of it) into the text box")
        self.page_bar = tk.Frame(row, background=C["panel"])
        ttk.Button(self.page_bar, image=t.icon_states("chevron_left", 16), style="Icon.TButton",
                   command=lambda: self.show_pdf_page(self.pdf_index - 1)).pack(side="left")
        self.page_label = ttk.Label(self.page_bar, style="Panel.Muted.TLabel")
        self.page_label.pack(side="left", padx=px(4))
        ttk.Button(self.page_bar, image=t.icon_states("chevron_right", 16), style="Icon.TButton",
                   command=lambda: self.show_pdf_page(self.pdf_index + 1)).pack(side="left")

        self.canvas = tk.Canvas(box, height=px(250), background=C["field"], highlightthickness=1,
                                highlightbackground=C["border_strong"], borderwidth=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw_image())
        self.canvas.bind("<ButtonPress-1>", self._crop_start)
        self.canvas.bind("<B1-Motion>", self._crop_drag)
        self.canvas.bind("<ButtonRelease-1>", self._crop_end)
        self.canvas.bind("<Double-Button-1>", lambda e: self._clear_crop())
        self.status = ttk.Label(box, style="Panel.Muted.TLabel", justify="left", wraplength=px(460))
        self.status.pack(anchor="w", fill="x", pady=(px(6), 0))

        label_row = tk.Frame(box, background=C["panel"])
        label_row.pack(fill="x", pady=(px(10), px(4)))
        ttk.Label(label_row, text="Problem text", style="Section.TLabel").pack(side="left")
        ttk.Label(label_row, text="Fix what was misread, then Find (Ctrl+Enter). Numbers are highlighted.",
                  style="Panel.Faint.TLabel").pack(side="left", padx=(px(8), 0))
        holder = tk.Frame(box, background=C["panel"])
        holder.pack(fill="both", expand=True)
        self.text = tk.Text(holder, height=8, wrap="word", font=t.f["base"], background=C["field"],
                            foreground=C["text"], insertbackground=C["text"], relief="flat", borderwidth=0,
                            highlightthickness=1, highlightbackground=C["border_strong"],
                            highlightcolor=C["accent"], padx=px(10), pady=px(8), undo=True)
        bar = AutoScrollbar(holder, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        self._tag_numbers()
        self.text.bind("<KeyRelease>", lambda e: self._highlight_later(), add="+")
        self.text.bind("<<Paste>>", lambda e: self.after(10, self._highlight), add="+")
        self.text.bind("<Control-Return>", lambda e: (self.find(), "break")[1])

        actions = tk.Frame(box, background=C["panel"])
        actions.pack(fill="x", pady=(px(8), 0))
        self.find_btn = ttk.Button(actions, text="Find in library", image=t.icon("search", "on_accent", 16),
                                   compound="left", style="Accent.TButton", command=self.find)
        self.find_btn.pack(side="left")
        ttk.Button(actions, text="Clear", command=self.clear).pack(side="left", padx=(px(6), 0))
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=px(120))
        return card

    def _build_result(self, parent, t, px):
        card, box = self._card(parent, px)
        top = tk.Frame(box, background=C["panel"])
        top.pack(fill="x")
        self.list_mode = tk.StringVar(value="matches")
        for value, text in (("matches", "Best matches"), ("search", "Search"), ("history", "History")):
            ttk.Radiobutton(top, text=text, value=value, variable=self.list_mode, style="Chip.TRadiobutton",
                            command=self._mode_changed).pack(side="left", padx=(0, px(2)))
        self.search = PlaceholderEntry(top, placeholder="Search: 3.13 or words", width=26,
                                       style="Panel.Search.TEntry")
        self.search.pack(side="right")
        self.search.var.trace_add("write", lambda *_: self._search_later())
        self.search.bind("<FocusIn>", lambda e: self.list_mode.set("search") or self._mode_changed(), add="+")

        self.banner = ttk.Label(box, style="Panel.Muted.TLabel", justify="left", wraplength=px(560))
        self.banner.pack(anchor="w", fill="x", pady=(px(8), px(4)))
        listbox = tk.Frame(box, background=C["panel"])
        listbox.pack(fill="x")
        self.tree = ttk.Treeview(listbox, columns=("ex", "score", "text"), show="headings", height=5,
                                 selectmode="browse")
        for col, text, width, stretch in (("ex", "Exercise", px(80), False), ("score", "Score", px(64), False),
                                          ("text", "Problem", px(300), True)):
            self.tree.heading(col, text=text, anchor="w")
            self.tree.column(col, width=width, minwidth=width, stretch=stretch, anchor="w")
        bar = AutoScrollbar(listbox, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        listbox.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._picked)

        ttk.Separator(box).pack(fill="x", pady=px(12))
        self.title = ttk.Label(box, style="Panel.H2.TLabel")
        self.title.pack(anchor="w")
        self.meta = ttk.Label(box, style="Panel.Muted.TLabel", justify="left", wraplength=px(560))
        self.meta.pack(anchor="w", fill="x", pady=(px(2), px(6)))
        self.badge = ttk.Label(box, style="Ok.TLabel", justify="left", wraplength=px(560))
        self.badge.pack(anchor="w", fill="x")
        holder = tk.Frame(box, background=C["panel"])
        holder.pack(fill="both", expand=True, pady=(px(8), 0))
        self.preview = tk.Text(holder, height=8, wrap="word", font=t.f["base"], background=C["raised"],
                               foreground=C["text"], relief="flat", borderwidth=0, highlightthickness=0,
                               padx=px(12), pady=px(10), state="disabled", cursor="arrow")
        pbar = AutoScrollbar(holder, orient="vertical", command=self.preview.yview, style="Raised.Vertical.TScrollbar")
        self.preview.configure(yscrollcommand=pbar.set)
        self.preview.grid(row=0, column=0, sticky="nsew")
        pbar.grid(row=0, column=1, sticky="ns")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)

        actions = tk.Frame(box, background=C["panel"])
        actions.pack(fill="x", pady=(px(10), 0))
        self.solution_btn = ttk.Button(actions, text="Open solution", image=t.icon("external", "on_accent", 16),
                                       compound="left", style="Accent.TButton", command=self.open_solution)
        self.solution_btn.pack(side="left")
        Tooltip(self.solution_btn, "Show the stored solution in your browser (offline; the math is drawn there)")
        self.prev_btn = ttk.Button(actions, image=t.icon_states("chevron_left", 16), style="Icon.TButton",
                                   command=lambda: self._step(-1))
        self.prev_btn.pack(side="left", padx=(px(8), 0))
        Tooltip(self.prev_btn, "Previous exercise")
        self.next_btn = ttk.Button(actions, image=t.icon_states("chevron_right", 16), style="Icon.TButton",
                                   command=lambda: self._step(1))
        self.next_btn.pack(side="left")
        Tooltip(self.next_btn, "Next exercise")
        self.wrong_btn = ttk.Button(actions, text="Wrong match", command=self.wrong_match)
        self.wrong_btn.pack(side="right")
        Tooltip(self.wrong_btn, "Tell the Notebook which exercise this really is (saved locally to improve matching)")
        return card

    # ---------------------------------------------------------------------------------------- page hooks --
    def on_show(self):
        if self.library is None and not self._loading:
            self.reload_library()

    def on_theme(self):
        self._tag_numbers()

    def _tag_numbers(self):
        self.text.tag_configure("num", background=C["accent_soft"], foreground=C["accent"])

    # ---------------------------------------------------------------------------------------- workers --
    def _run(self, kind, work, done):
        """Run `work()` in a thread; `done(result, error)` runs on the Tk thread. A newer job of the same kind
        makes the older one's result be ignored."""
        token = self._token[kind] = self._token.get(kind, 0) + 1

        def target():
            try:
                self._jobs.put((kind, token, done, work(), None))
            except Exception as exc:  # noqa: BLE001 - handed to `done`, which shows it
                self._jobs.put((kind, token, done, None, exc))

        self._pending += 1
        if self._pending == 1:
            self.progress.pack(side="left", padx=(self.app.theme.px(12), 0))
            self.progress.start(12)
            self.after(60, self._drain)
        gc.collect()      # free dead Tk objects here: Tk must not delete them from the worker thread
        threading.Thread(target=target, daemon=True).start()

    def _drain(self):
        while True:
            try:
                kind, token, done, result, error = self._jobs.get_nowait()
            except queue.Empty:
                break
            self._pending -= 1
            if token == self._token.get(kind):
                done(result, error)
        if self._pending > 0:
            self.after(60, self._drain)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    # ------------------------------------------------------------------------------------------ library --
    def _folders(self):
        return [p for p in self.app.cfg.get("notebook_library", []) if isinstance(p, str)]

    def add_folder(self):
        path = filedialog.askdirectory(parent=self, title="Folder with your solution files (.md)")
        if path:
            self._add_source(path)

    def add_file(self):
        path = filedialog.askopenfilename(parent=self, title="A solutions file", filetypes=[("Markdown", "*.md")])
        if path:
            self._add_source(path)

    def _add_source(self, path):
        folders = self._folders()
        if path not in folders:
            folders.append(path)
        self.app.cfg["notebook_library"] = folders
        settings.save(self.app.cfg)
        self.reload_library()

    def forget_library(self):
        self.app.cfg["notebook_library"] = []
        settings.save(self.app.cfg)
        self.reload_library()

    def reload_library(self):
        folders = self._folders()
        self._loading = True
        self.lib_button.configure(text="Library: loading…")
        cache = notebook_dir() / "index.json"
        self._run("library", lambda: nb_library.load(folders, cache_path=cache), self._library_loaded)

    def _library_loaded(self, lib, error):
        self._loading = False
        if error is not None:
            self.lib_button.configure(text="Library: error")
            messagebox.showerror(APP_NAME, f"Couldn't read the solutions library:\n{error}", parent=self)
            return
        self.library, self.index = lib, nb_lookup.Index(lib)
        books = sorted({(e.book, e.edition) for e in lib.exercises})
        name = ", ".join(f"{b.title()} {ed}".strip() for b, ed in books) or "empty"
        notes = f" · {len(lib.problems)} notes" if lib.problems else ""
        self.lib_button.configure(text=f"Library: {name} · {len(lib.exercises)} exercises{notes}")
        if not lib.exercises:
            self._set_banner("No solutions loaded yet. Use Library ▾ › Add a solutions folder… (your .md files "
                             "are only read, never changed). Typed text can be searched once a library is loaded.",
                             "Warn.TLabel")
        else:
            self._set_banner("Open or paste a picture of a problem, or type it, then Find.")
        if self.list_mode.get() != "matches":
            self._mode_changed()

    def show_load_notes(self):
        if self.library is None or not self.library.problems:
            messagebox.showinfo(APP_NAME, "The library loaded without problems.", parent=self)
            return
        lines = [str(p) for p in self.library.problems[:40]]
        more = len(self.library.problems) - len(lines)
        messagebox.showinfo(APP_NAME, "\n".join(lines) + (f"\n… and {more} more" if more > 0 else ""), parent=self)

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
        self._close_pdf()
        if path.suffix.lower() == ".pdf":
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
                self._set_status(str(exc) or type(exc).__name__, "Error.TLabel")
                return
            self.show_pdf_page(0)
            return
        if path.suffix.lower() not in IMAGE_TYPES:
            self._set_status("Use a picture (PNG, JPG, WEBP …) or a PDF.", "Error.TLabel")
            return
        try:
            from PIL import Image
            if path.stat().st_size > nb_ocr.MAX_IMAGE_BYTES:
                raise ValueError("This image is too large. The maximum supported size is 50 MB.")
            with Image.open(path) as im:
                im.load()
                image = im.convert("RGB")
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self._set_status(f"Couldn't open {path.name}: {exc}", "Error.TLabel")
            return
        self._set_image(image, f"{path.name}. Drag on it to read only one problem, then Read text.")
        self.read_text()

    def paste_image(self):
        try:
            from PIL import Image, ImageGrab
            grabbed = ImageGrab.grabclipboard()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self._set_status(f"Couldn't read the clipboard: {exc}", "Error.TLabel")
            return
        if isinstance(grabbed, list):
            path = next((Path(p) for p in grabbed if Path(p).suffix.lower() in IMAGE_TYPES | {".pdf"}), None)
            if path is not None:
                self.open_path(path)
                return
        if isinstance(grabbed, Image.Image):
            self._close_pdf()
            self._set_image(grabbed.convert("RGB"), "Screenshot from the clipboard.")
            self.read_text()
            return
        self._set_status("The clipboard has no picture. Copy a screenshot of the problem, or paste its text "
                         "into the box below.", "Warn.TLabel")

    def _close_pdf(self):
        if self.pdf is not None:
            try:
                self.pdf.close()
            except Exception:  # noqa: BLE001 - closing a document we no longer need
                pass
        self.pdf, self.view = None, None
        self.page_bar.pack_forget()

    def show_pdf_page(self, index):
        if self.pdf is None or not 0 <= index < self.pdf.n_pages:
            return
        self.pdf_index = index
        self.page_label.configure(text=f"Page {index + 1} of {self.pdf.n_pages}")
        self.page_bar.pack(side="left", padx=(self.app.theme.px(10), 0))
        doc = self.pdf
        self._run("render", lambda: doc.render(index, dpi=nb_ocr.PDF_DPI), self._pdf_drawn)

    def _pdf_drawn(self, result, error):
        if error is not None:
            self._set_status(f"Couldn't draw the page: {error}", "Error.TLabel")
            return
        image, self.view = result
        self._set_image(image, f"{self.pdf.name}, page {self.pdf_index + 1}. Drag around one problem to read "
                               "only that one, then Read text.")

    def _set_image(self, image, message):
        self.image = image
        self.crop = None
        self._draw_image()
        self._set_status(message)

    def _draw_image(self):
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        if self.image is None:
            c.create_text(w / 2, h / 2, text="Open or paste a picture of the problem,\nor just type it below.",
                          fill=C["faint"], font=self.app.theme.f["base"], justify="center")
            return
        from PIL import ImageTk
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
            self._set_status("Marked part: Read text reads only that part. Double-click the picture to clear it.")

    def _clear_crop(self):
        self.crop = None
        self.canvas.delete("crop")

    def read_text(self):
        if self.image is None:
            self._set_status("Open or paste a picture first, or type the problem into the box.", "Warn.TLabel")
            return
        self._set_status("Reading the text…")
        crop, image, doc, index, view = self.crop, self.image, self.pdf, self.pdf_index, self.view
        if doc is not None:
            work = lambda: nb_ocr.read_pdf_page(doc, index, crop, view)  # noqa: E731
        else:
            work = lambda: nb_ocr.read_image(image, crop)  # noqa: E731
        self._run("ocr", work, self._text_read)

    def _text_read(self, reading, error):
        if error is not None:
            kind = "Warn.TLabel" if isinstance(error, nb_ocr.OcrUnavailable) else "Error.TLabel"
            self._set_status(str(error) or type(error).__name__, kind)
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", reading.text)
        self._highlight()
        self._set_status(" ".join(reading.notes) or "Read.", "Panel.Muted.TLabel")
        if reading.text.strip():
            self.find()

    def clear(self):
        self._close_pdf()
        self.image = None
        self.crop = None
        self._draw_image()
        self.text.delete("1.0", "end")
        self._set_status("")
        self.result = None
        self._fill_list([])
        self._set_detail(None)

    # ------------------------------------------------------------------------------------- highlighting --
    def _highlight_later(self):
        if getattr(self, "_hl_job", None):
            self.after_cancel(self._hl_job)
        self._hl_job = self.after(150, self._highlight)

    def _highlight(self):
        self._hl_job = None
        self.text.tag_remove("num", "1.0", "end")
        for start, end in nb_lookup.number_spans(self.text.get("1.0", "end-1c")):
            self.text.tag_add("num", f"1.0+{start}c", f"1.0+{end}c")

    # --------------------------------------------------------------------------------------------- lookup --
    def problem_text(self) -> str:
        return self.text.get("1.0", "end-1c").strip()

    def find(self):
        text = self.problem_text()
        if self.index is None:
            self._set_banner("The library is still loading, or none is set (Library ▾).", "Warn.TLabel")
            return
        result = self.result = self.index.lookup(text)
        self.list_mode.set("matches")
        self._fill_list([c.exercise for c in result.candidates], scores=[c.score for c in result.candidates])
        if result.status == "empty":
            self._set_banner(result.note, "Warn.TLabel")
            self._set_detail(None)
            return
        if result.status == "match":
            best = result.best
            self._set_banner(f"Found: Exercise {best.exercise.number} (score {best.score:.2f}). "
                             "Not this one? Pick another below." + (f" {result.note}" if result.note else ""),
                             "Ok.TLabel")
            self._select(best.exercise)
        elif result.status == "choose":
            self._set_banner(f"{result.note} Click one to see it.", "Warn.TLabel")
            self._set_detail(None)
        else:
            self._set_banner(f"Not in your library (best score {result.best.score:.2f}, below "
                             f"{nb_lookup.LOW:.2f}). The closest ones are below. Live solving comes in a later "
                             "version.", "Warn.TLabel")
            self._set_detail(None)
        self._remember(text, result)

    def _remember(self, text, result):
        history = [h for h in self.app.cfg.get("notebook_history", []) if isinstance(h, dict)]
        best = result.best.exercise.key if result.status == "match" and result.best else None
        history.insert(0, {"time": time.strftime("%Y-%m-%d %H:%M"), "text": text[:400], "status": result.status,
                           "exercise": best})
        self.app.cfg["notebook_history"] = history[:HISTORY_LIMIT]
        settings.save(self.app.cfg)

    # ------------------------------------------------------------------------------------------- the list --
    def _mode_changed(self):
        mode = self.list_mode.get()
        if mode == "matches":
            cands = self.result.candidates if self.result else []
            self._fill_list([c.exercise for c in cands], scores=[c.score for c in cands])
        elif mode == "search":
            self._run_search()
        else:
            self._fill_history()

    def _search_later(self):
        if getattr(self, "_search_job", None):
            self.after_cancel(self._search_job)
        self._search_job = self.after(200, self._run_search)

    def _run_search(self):
        self._search_job = None
        if self.index is None:
            return
        self.list_mode.set("search")
        self._fill_list(self.index.search(self.search.value()))

    def _fill_history(self):
        self.tree.delete(*self.tree.get_children())
        self.listed = []
        self._history = [h for h in self.app.cfg.get("notebook_history", []) if isinstance(h, dict)]
        for i, h in enumerate(self._history):
            number = (h.get("exercise") or "").split(":")[-1] or {"choose": "picked?", "none": "not found"}.get(
                h.get("status"), "")
            self.tree.insert("", "end", iid=f"h{i}", values=(number, h.get("time", "")[5:],
                                                            " ".join(h.get("text", "").split())[:120]))

    def _fill_list(self, exercises, scores=None):
        self.tree.delete(*self.tree.get_children())
        self.listed = list(exercises)
        self.tree.heading("score", text="Score" if scores else "Chapter")
        for i, e in enumerate(exercises):
            second = f"{scores[i]:.2f}" if scores else str(e.chapter)
            self.tree.insert("", "end", iid=str(i), values=(e.number, second, " ".join(plain_problem(e).split())[:140]))

    def _picked(self, _e=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("h"):
            h = self._history[int(iid[1:])]
            self.text.delete("1.0", "end")
            self.text.insert("1.0", h.get("text", ""))
            self._highlight()
            ex = None
            if h.get("exercise") and self.library is not None:
                book, _, number = h["exercise"].partition(":")
                ex = self.library.get(number, book)
            self._set_detail(ex)
            return
        self._set_detail(self.listed[int(iid)])

    def _select(self, exercise):
        if exercise in self.listed:
            iid = str(self.listed.index(exercise))
            self.tree.selection_set(iid)
            self.tree.see(iid)
        self._set_detail(exercise)

    # ---------------------------------------------------------------------------------------- the detail --
    def _set_detail(self, e):
        self.current = e
        for b in (self.solution_btn, self.prev_btn, self.next_btn):
            b.state(["!disabled"] if e is not None else ["disabled"])
        self.wrong_btn.state(["!disabled"] if self.result is not None else ["disabled"])
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        if e is None:
            self.title.configure(text="No exercise selected")
            self.meta.configure(text="A match from your library appears here.")
            self.badge.configure(text="")
        else:
            self.title.configure(text=f"Exercise {e.number}" + (f" · {e.title}" if e.title else ""))
            self.meta.configure(text=f"{e.book.title()} {e.edition} · Chapter {e.chapter} · {e.topic}"
                                     f"\n{Path(e.source_file).name}, line {e.line}")
            badge = provenance.for_exercise(e)
            style = {"verified": "Ok.TLabel", "caution": "Warn.TLabel"}.get(badge.kind, "Panel.Muted.TLabel")
            detail = f": {badge.detail}" if badge.detail else ""
            tables = f"\n📘 Uses {len(e.table_refs)} table lookup{'s' if len(e.table_refs) > 1 else ''}." \
                if e.table_refs else ""
            self.badge.configure(text=f"{badge.label}{detail}{tables}", style=style)
            self.preview.insert("1.0", plain_problem(e))
        self.preview.configure(state="disabled")

    def _step(self, step):
        if self.current is None or self.library is None:
            return
        other = self.library.neighbour(self.current, step)
        if other is not None:
            self._select(other)

    def open_solution(self):
        e, lib = self.current, self.library
        if e is None or lib is None:
            return
        pages = render.Pages(lib, notebook_dir() / "pages", dark=self.app.theme.dark)
        self._run("open", lambda: pages.opener(e), self._opened)

    def _opened(self, path, error):
        if error is not None:
            kind = render.RenderUnavailable
            messagebox.showerror(APP_NAME, str(error) if isinstance(error, kind) else
                                 f"Couldn't write the solution page:\n{type(error).__name__}: {error}", parent=self)
            return
        if not webbrowser.open(path.as_uri()):
            messagebox.showinfo(APP_NAME, f"No browser opened. Open this file yourself:\n{path}", parent=self)

    def wrong_match(self):
        if self.result is None:
            return
        answer = simpledialog.askstring(
            APP_NAME, "Which exercise is it really? Type its number (for example 3.13).\n"
                      "Leave it empty if it isn't in your library.", parent=self)
        if answer is None:
            return
        number = answer.strip().lower().removeprefix("exercise").strip()
        target = self.library.get(number) if number and self.library is not None else None
        if number and target is None:
            messagebox.showwarning(APP_NAME, f"Exercise {number} isn't in your library.", parent=self)
            return
        try:
            log_feedback(self.problem_text(), self.current, target.key if target else "", self.result.candidates)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Couldn't save the note:\n{exc}", parent=self)
            return
        self._set_banner(f"Saved to {feedback_path().name}. Thanks: it is used to tune the matching.", "Ok.TLabel")
        if target is not None:
            self._select(target)

    # -------------------------------------------------------------------------------------------- messages --
    def _set_status(self, text, style="Panel.Muted.TLabel"):
        self.status.configure(text=text, style=style)

    def _set_banner(self, text, style="Panel.Muted.TLabel"):
        self.banner.configure(text=text, style=style)
