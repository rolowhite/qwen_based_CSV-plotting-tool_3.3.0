"""The CSV Plot Studio window: gallery -> load CSV -> columns & plot."""
from __future__ import annotations

import dataclasses
import gc
import io
import keyword
import re
import math
import sys
import threading
import time
import tempfile
import tokenize
import traceback
import types
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import matplotlib

matplotlib.use("Agg")  # pyplot draws off-screen; finished figures are shown through our own Tk canvas

import pandas as pd

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk  # noqa: E402

from . import APP_NAME, fonts, settings  # noqa: E402
from .core import activity  # noqa: E402
from .profile_view import ProfilePage  # noqa: E402
from .notebook_page import NotebookPage  # noqa: E402
from .codegen import PlotError  # noqa: E402
from .data import DELIMITERS, ENCODINGS, RowSettings, file_size_text, load_csv  # noqa: E402
from .pdf_table_extractor import MAX_PDF_BYTES, PasswordNeeded, WrongPassword, extract_tables  # noqa: E402
from .image_table_extractor import MAX_IMAGE_BYTES, extract_table  # noqa: E402
from .table_import import edits_between, save_table, suggested_name  # noqa: E402
from .engine import (CONTEXTS, LEGEND_PLACES, PALETTES, LabelSettings, PlotRunError,  # noqa: E402
                     StyleSettings, build_plot, run_plot, style_choices)
from .graphs import CATEGORIES, GRAPH_BY_ID, GRAPHS, compatible, suggest  # noqa: E402
from .core import overrides as type_overrides  # noqa: E402
from .ideas import IdeaCard, IdeaService, IdeasView  # noqa: E402
from .ceasar import CeasarService, CeasarView  # noqa: E402
from .featurelab import FeatureLabView, LabService  # noqa: E402
from .log import log_error, log_path, logger  # noqa: E402
from . import bootstrap  # noqa: E402
from .limits import fmt_limit, fracs, is_full, limit_values, to_value  # noqa: E402
from .navigate import WHEEL_ZOOM, Navigator, zoom_fracs  # noqa: E402
from . import recommend  # noqa: E402
from .paper import apply_paper  # noqa: E402
from .theme import C, CODE, Theme  # noqa: E402
from .tracker import PointTracker  # noqa: E402
from .widgets import (AutoScrollbar, MultiPicker, PlaceholderEntry, RangeSlider, ScrollFrame, Section,  # noqa: E402
                      SmoothScroller, Tile, Tooltip, install_mousewheel, release_canvas, wheel_pixels)

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
SAMPLES = HERE.parent / "samples"
NONE = "(none)"
SAMPLE_INFO = {
    "airline_demo.csv": "2,500 airline passengers (synthetic): ratings, delays, class and satisfaction.",
    "training_log.csv": "Loss and accuracy per epoch: try a line plot with several Y columns.",
    "store_sales.csv": "Daily sales of 3 stores in 2025: dates, line plots, facets.",
    "model_predictions.csv": "True labels and two models' probabilities: ROC curve, confusion matrix.",
    "digits_8x8.csv": "600 handwritten digits as 64 pixel columns: image grid.",
    "surface_xyz.csv": "The Handbook's f(x, y) on a grid: contour plot, 3D surface.",
}
ACCEPTS_TEXT = {"num": "number columns", "cat": "category columns (few distinct values)",
                "num_cat": "number or category columns", "num_time": "number or date columns",
                "any": "any column", "binary": "columns with exactly 2 values", "all": "any column"}
STRING_TOKENS = {getattr(tokenize, n) for n in ("STRING", "FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END",
                                                "TSTRING_START", "TSTRING_MIDDLE", "TSTRING_END")
                 if hasattr(tokenize, n)}
BUILTINS = {"print", "len", "range", "enumerate", "zip", "sorted", "set", "min", "max", "str", "int", "float",
            "list", "dict", "round", "abs", "sum", "lambda"}
GUTTER = 12      # space between the window edge and the cards, and between cards (px at 100 %)


def short_path(path, limit=56) -> str:
    """A folder path that fits: the end is kept (it is the part that tells folders apart)."""
    text = str(path)
    return text if len(text) <= limit else "…" + text[-(limit - 1):]


# =========================================================================== #
# Application
# =========================================================================== #

class App(tk.Tk):
    def __init__(self, csv_path=None, graph_id=None, autoplot=False):
        fonts.register_for_tk()   # before the window exists: macOS reads its font list once
        super().__init__(className="CSVPlotStudio")
        self.withdraw()
        self.title(APP_NAME)
        self.cfg = settings.load()
        self.theme = Theme(self, mode=self.cfg.get("ui_theme", "dark"), style=self.cfg.get("ui_style", "default"))
        recommend.SYMBOLS["eta"] = self.theme.glyph("η", "eta")   # some Linux Tk fonts have no Greek
        recommend.SYMBOLS["rho"] = self.theme.glyph("ρ", "rho")
        self.dataset = None
        self.graph = None
        self.thumbs = Thumbs(self)
        self._icon = None
        self._set_icon()
        install_mousewheel(self, self.theme)
        self.style_settings = self._saved_style()
        self.ideas = IdeaService(self)        # plot ideas for the loaded file (background thread)
        self.lab = LabService(self)           # Feature Lab: the file's feature steps (background thread)
        self.ceasar = CeasarService(self)     # Ceasar: edits to the file made by tasks and chat

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)
        self.gallery = GalleryPage(self.container, self)
        self.loader = LoadPage(self.container, self)
        self.work = WorkspacePage(self.container, self)
        self.profile = ProfilePage(self.container, self)
        self.notebook = NotebookPage(self.container, self)
        self.pages = {"gallery": self.gallery, "load": self.loader, "work": self.work,
                      "profile": self.profile, "notebook": self.notebook}
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.current = "gallery"
        self.show("gallery")

        px = self.theme.px
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(px(1380), sw - 60), min(px(880), sh - 90)
        geo = self.cfg.get("geometry") or ""
        try:
            gw, gh = (int(v) for v in geo.split("+")[0].split("x"))
            if 400 < gw <= sw and 300 < gh <= sh:
                w, h = gw, gh
        except ValueError:
            pass
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        self.minsize(min(px(1000), sw - 40), min(px(640), sh - 80))
        for seq in ("<Control-Return>", "<F5>"):
            self.bind_all(seq, lambda e: self.work.plot() if self.current == "work" else None)
        self.bind_all("<Control-o>", lambda e: self.open_dialog())
        self.bind_all("<Control-Shift-V>", lambda e: (self.notebook if self.current == "notebook" else
                                                      self.loader).paste_image())

        self.bind_all("<Control-s>", lambda e: self.work.plot_view.save_image() if self.current == "work" else None)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.deiconify()
        self.theme.dark_title_bar(self)
        # first start on Windows: Tesseract (tables from pictures) installs in the background, apart from the rest
        # so a waiting administrator prompt holds nothing up; the Notebook sets up its picture reader itself
        threading.Thread(target=lambda: logger().info(bootstrap.install_tesseract()), daemon=True).start()

        if csv_path:
            if graph_id:
                self.graph = next((g for g in GRAPHS if g.id == graph_id), None)
            self.loader.load(csv_path, then_plot=autoplot)

    # ------------------------------------------------------------------ #
    def _saved_style(self) -> StyleSettings:
        st = self.cfg.get("style") or {}
        valid = {v for v, _ in style_choices()}
        theme = st.get("theme")
        if int(self.cfg.get("style_version", 1)) < 2 and theme in (None, "whitegrid"):
            theme = "studio"   # 2.0: the Studio look replaces the old default (seaborn whitegrid)
        self.cfg["style_version"] = 2
        return StyleSettings(
            theme=theme if theme in valid else "studio",
            palette=st.get("palette") if st.get("palette") in PALETTES else "default",
            context=st.get("context") if st.get("context") in CONTEXTS else "notebook")

    def _set_icon(self):
        try:
            self._icon = tk.PhotoImage(master=self, file=str(ASSETS / "icon.png"))
            self.iconphoto(True, self._icon)
        except tk.TclError:
            pass

    def report_callback_exception(self, exc, val, tb):
        """Unexpected errors inside the window: show them instead of failing silently."""
        traceback.print_exception(exc, val, tb)
        log_error("Unexpected error in the window", details="".join(traceback.format_exception(exc, val, tb)))
        try:
            self.busy(False)
            messagebox.showerror(APP_NAME, f"Something went wrong:\n{exc.__name__}: {val}\n\n"
                                           f"Details were written to {log_path()}", parent=self)
        except tk.TclError:
            pass

    def toggle_theme(self):
        """Switch between the light and the dark look (live, remembered for next time)."""
        mode = "light" if self.theme.dark else "dark"
        self.busy(True)
        try:
            self.work.plot_view.paper_var.set(mode == "dark")   # graph paper follows the look
            self.theme.apply(mode)
        finally:
            self.busy(False)
        self.cfg["ui_theme"] = mode
        settings.save(self.cfg)
        if hasattr(self, "profile"):
            self.profile.on_theme()

    def toggle_style(self):
        """Switch between the default style and the ink style (live, remembered for next time)."""
        style = "default" if self.theme.ink else "ink"
        self.busy(True)
        try:
            self.theme.apply(self.theme.mode, style)
        finally:
            self.busy(False)
        self.cfg["ui_style"] = style
        settings.save(self.cfg)
        if hasattr(self, "profile"):
            self.profile.on_theme()

    def show(self, name):
        if name != self.current:
            self.previous_page = self.current
        self.current = name
        self.pages[name].tkraise()
        self.pages[name].on_show()

    def choose_graph(self, graph):
        self.graph = graph
        if self.dataset is None:
            self.loader.set_graph(graph)
            self.show("load")
            return
        self.work.set_graph(graph)
        self.show("work")
        if self.work.has_plotted and self.work.auto_var.get():
            self.after(60, self.work.plot)

    def set_dataset(self, ds, then_plot=False):
        self.dataset = ds
        activity.record_file(self.cfg, rows=len(ds.df), dataset_name=ds.name, dataset_path=str(ds.path.resolve()))
        settings.add_recent(self.cfg, ds.path)
        self.cfg["last_dir"] = str(ds.path.parent)
        settings.save(self.cfg)
        self.title(f"{APP_NAME} · {ds.name}")
        self.gallery.refresh_data_chip()
        self.loader.refresh_recent()
        self.work.set_dataset(ds)
        self.lab.reset(ds)                    # a new file: no feature steps yet
        self.ideas.request(ds, self.work.current_target(), self.work.type_overrides)
        if self.graph is None:
            self.show("gallery")
            return
        self.work.set_graph(self.graph)
        self.show("work")
        if then_plot:
            self.after(80, self.work.plot)
        else:
            self.work.nb.select(self.work.data_view)

    def use_working(self, ds):
        """The same file with Feature Lab steps added or removed: every tab now uses this table."""
        self.dataset = ds
        self.gallery.refresh_data_chip()
        self.work.update_dataset(ds)

    def open_dialog(self):
        path = filedialog.askopenfilename(
            parent=self, title="Open a data file", initialdir=self.cfg.get("last_dir") or str(Path.home()),
                filetypes=[("Data files", "*.csv *.tsv *.txt *.dat *.pdf *.png *.jpg *.jpeg *.webp"),
                       ("Images", "*.png *.jpg *.jpeg *.webp"),
                       ("CSV files", "*.csv *.tsv *.txt *.dat"), ("PDF files", "*.pdf"),
                       ("All files", "*.*")])
        if path:
            suffix = Path(path).suffix.lower()
            if suffix == ".pdf":
                self.loader.load_pdf(path)
            elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                self.loader.load_image(path)
            else:
                self.loader.load(path)

    def busy(self, on: bool):
        try:
            self.configure(cursor="watch" if on else "")
            self.update_idletasks()
        except tk.TclError:
            pass

    def on_close(self):
        try:
            self.cfg["geometry"] = self.geometry()
            self.cfg["style"] = vars(self.work.collect_style())
            self.cfg["style_version"] = 2
            self.cfg["auto_update"] = bool(self.work.auto_var.get())
            self.cfg["show_values"] = bool(self.work.plot_view.values_var.get())
            self.cfg["range_sliders"] = bool(self.work.plot_view.sliders_var.get())
            self.cfg["mouse_nav"] = bool(self.work.plot_view.mouse_var.get())
            self.cfg["fit_window"] = bool(self.work.plot_view.fit.get())
            settings.save(self.cfg)
        except Exception:  # noqa: BLE001 - never block closing
            pass
        plt.close("all")
        self.quit()
        self.destroy()


class Thumbs:
    """Preview images for the gallery cards (1x and 2x sizes, rounded corners)."""

    def __init__(self, root):
        self.root, self.cache = root, {}
        self.large_default = root.theme.scale >= 1.6

    def get(self, gid, large=None):
        large = self.large_default if large is None else large
        folder = "thumbs_dark" if self.root.theme.dark and (ASSETS / "thumbs_dark").is_dir() else "thumbs"
        recolor = folder == "thumbs_dark" and self.root.theme.ink
        key = (gid, large, folder, recolor)
        if key not in self.cache:
            name = f"{gid}@2x.png" if large else f"{gid}.png"
            try:
                if recolor:     # the dark pictures sit on the default dark card: move them to the ink card
                    self.cache[key] = self._on_ink_card(ASSETS / folder / name)
                else:
                    self.cache[key] = tk.PhotoImage(master=self.root, file=str(ASSETS / folder / name))
            except (tk.TclError, OSError):
                self.cache[key] = None
        return self.cache[key]

    def _on_ink_card(self, path):
        import numpy as np
        from PIL import Image, ImageTk
        from .paper import INK_PAPER, PAPER
        img = np.array(Image.open(path).convert("RGBA"))
        old, new = (np.array(Image.new("RGB", (1, 1), c).getpixel((0, 0))) for c in (PAPER["face"], INK_PAPER["face"]))
        img[(img[..., :3] == old).all(axis=-1), :3] = new
        return ImageTk.PhotoImage(Image.fromarray(img), master=self.root)


def theme_button(parent, app, style="Toggle.TButton"):
    """A small button that switches between the light and the dark look."""
    t = app.theme

    def look():
        return ("Light", t.icon_states("sun", 16)) if t.dark else ("Dark", t.icon_states("moon", 16))

    text, image = look()
    btn = ttk.Button(parent, text=text, image=image, compound="left", style=style, command=app.toggle_theme)
    btn.on_theme = lambda: btn.configure(**dict(zip(("text", "image"), look())))
    Tooltip(btn, "Switch between the light and the dark look. The plot's colours follow the graph paper.")
    # the style switch sits just left of the header's other right-hand buttons, added after them so none moves
    btn.after_idle(lambda: btn.winfo_exists() and _place_style_button(btn, app, style))
    return btn


def _place_style_button(theme_btn, app, style):
    info = {k: v for k, v in theme_btn.pack_info().items() if k != "in"}
    style_button(theme_btn.master, app, style).pack(**info)


def style_button(parent, app, style="Toggle.TButton"):
    """A small button that switches between the default style and the ink style (graph paper)."""
    t = app.theme

    def label():
        return "Default style" if t.ink else "New style"

    btn = ttk.Button(parent, text=label(), style=style, command=app.toggle_style)
    btn.on_theme = lambda: btn.configure(text=label())
    Tooltip(btn, "Switch between the app's default style and the new ink style (ink controls, graph paper "
                 "under the plots). Everything else stays the same.")
    return btn


def profile_button(parent, app, style="Toggle.TButton"):
    """Open the local plotting activity dashboard."""
    from .profile_view import refresh_profile_buttons
    btn = ttk.Button(parent, style=style, compound="left", command=lambda: app.show("profile"))
    app._profile_buttons = getattr(app, "_profile_buttons", []) + [btn]
    refresh_profile_buttons(app)
    Tooltip(btn, "Your profile: plots, streaks and badges")
    return btn


def back_button(parent, app, style="Link.TButton"):
    t = app.theme
    b = ttk.Button(parent, text="All graphs", image=t.icon_states("back", 16, normal="accent", active="accent_hover"),
                   compound="left", style=style, command=lambda: app.show("gallery"))
    Tooltip(b, "Back to the gallery of graph types")
    return b


# =========================================================================== #
# Page 1: gallery of graph types
# =========================================================================== #

class GalleryPage(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        t, px = app.theme, app.theme.px
        g = px(GUTTER)
        head = ttk.Frame(self, style="Card.TFrame", padding=(px(22), px(16), px(22), px(16)))
        head.pack(fill="x", padx=g, pady=(g, 0))
        inner = tk.Frame(head, background=C["panel"])
        inner.pack(fill="x")
        top = tk.Frame(inner, background=C["panel"])
        top.pack(fill="x")
        titles = tk.Frame(top, background=C["panel"])
        titles.pack(side="left")
        ttk.Label(titles, text=APP_NAME, style="Panel.H1.TLabel").pack(anchor="w")
        steps = tk.Frame(titles, background=C["panel"])
        steps.pack(anchor="w", pady=(px(6), 0))
        for i, text in enumerate(("Pick a graph", "Load data", "Choose columns and plot")):
            if i:
                tk.Label(steps, image=t.icon("chevron_right", "faint", 14), background=C["panel"]).pack(
                    side="left", padx=px(8))
            ttk.Label(steps, text=str(i + 1), style="Badge.TLabel" if i == 0 else "MutedBadge.TLabel").pack(side="left")
            tk.Label(steps, text=text, background=C["panel"], foreground=C["text"] if i == 0 else C["muted"],
                     font=t.f["medium"] if i == 0 else t.f["base"]).pack(side="left", padx=(px(6), 0))
        theme_button(top, app).pack(side="right", anchor="n", padx=(px(8), 0))
        profile_button(top, app).pack(side="right", anchor="n", padx=(px(8), 0))
        notebook = ttk.Button(top, text="Notebook", image=t.icon_states("file", 16), compound="left",
                              style="Toggle.TButton", command=lambda: app.show("notebook"))
        notebook.pack(side="right", anchor="n", padx=(px(8), 0))
        Tooltip(notebook, "Solve a statistics problem from a photo, a PDF or typed text")
        self.chip = tk.Frame(top, background=C["panel"])
        self.chip.pack(side="right", anchor="n")

        bar = tk.Frame(inner, background=C["panel"])
        bar.pack(fill="x", pady=(px(16), 0))
        self.search = PlaceholderEntry(bar, placeholder="Search graphs, e.g. heatmap or 3D", width=30,
                                       style="Panel.Search.TEntry")
        self.search.pack(side="left", padx=(0, px(12)))
        self.search.var.trace_add("write", lambda *_: self.refilter())
        self.search.bind("<Return>", self._enter)
        self.search.bind("<Escape>", lambda e: (self.search.set_value(""), self.search.focus_set()))
        Tooltip(self.search, "Type to filter the graphs. Press Enter to open the only match.")
        self.cat = tk.StringVar(value="All")
        for cat in ["All"] + CATEGORIES:
            ttk.Radiobutton(bar, text=cat, value=cat, variable=self.cat, style="Chip.TRadiobutton",
                            command=self.refilter).pack(side="left", padx=(0, px(2)))

        self.scroll = ScrollFrame(self, t, bg=C["bg"])
        self.scroll.pack(fill="both", expand=True, pady=(px(4), 0))
        body = self.scroll.body
        self.headings = {}
        for cat in CATEGORIES:
            n = sum(g_.category == cat for g_ in GRAPHS)
            frame = tk.Frame(body, background=C["bg"])
            tk.Label(frame, text=cat, background=C["bg"], foreground=C["text"], font=t.f["h3"]).pack(side="left")
            tk.Label(frame, text=f"{n}", background=C["bg"], foreground=C["faint"], font=t.f["small"]).pack(
                side="left", padx=(px(8), 0), pady=(px(3), 0))
            self.headings[cat] = frame
        self.cards = {g_.id: GraphCard(body, app, g_) for g_ in GRAPHS}
        # plot ideas for the loaded file: one row of cards above the graph types
        self.idea_head = tk.Frame(body, background=C["bg"])
        self.idea_title = tk.Label(self.idea_head, background=C["bg"], foreground=C["text"], font=t.f["h3"])
        self.idea_title.pack(side="left")
        self.idea_status = tk.Label(self.idea_head, background=C["bg"], foreground=C["faint"], font=t.f["small"])
        self.idea_status.pack(side="left", padx=(px(10), 0), pady=(px(3), 0))
        self.idea_all = ttk.Button(self.idea_head, text="All ideas and notes", style="BgLink.TButton",
                                   command=lambda: app.work.show_ideas())
        self.lab_link = ttk.Button(self.idea_head, text="Feature Lab", style="BgLink.TButton",
                                   image=t.icon_states("flask", 14, normal="accent", active="accent_hover"),
                                   compound="left", command=lambda: app.work.show_lab())
        Tooltip(self.lab_link, "New features for this file (title from a name, family size, ratios ...), "
                               "measured against the target")
        self.idea_cards = []
        self.idea_key = None
        app.ideas.listen(self.on_ideas)
        self.empty = tk.Label(body, background=C["bg"], foreground=C["muted"], justify="left")
        self.spacer = tk.Frame(body, background=C["bg"], height=px(24))
        self._cols = 0
        self._shown = None
        self.scroll.canvas.bind("<Configure>", lambda e: self._layout(), add="+")
        self.refresh_data_chip()

    def on_show(self):
        self.refresh_data_chip()
        for card in list(self.cards.values()) + self.idea_cards:
            card.reset()   # clear a hover highlight left from the last click

    def on_ideas(self, event):
        """Plot ideas arrived (or are being worked out) for the loaded file."""
        ds, svc = self.app.dataset, self.app.ideas
        if ds is None:
            return
        self.idea_title.configure(text=f"Plot ideas for {ds.name}")
        if self.idea_cards and self.idea_cards[0].idea_ds is not ds:     # suggestions of the previous file
            for card in self.idea_cards:
                card.destroy()
            self.idea_cards, self.idea_key = [], None
        if event in ("start", "progress"):
            fraction, text = svc.progress if event == "progress" else (0.0, "")
            self.idea_status.configure(text=f"working them out… {fraction:.0%}")
            self.idea_all.pack_forget()
            self.lab_link.pack_forget()
            if self.idea_key is None:
                self._layout(force=True)
            return
        res = svc.result
        if event == "error" or res is None or svc.result_ds is not ds:
            if event == "error":
                self.idea_status.configure(text="couldn't work them out (see the Plot ideas tab)")
            return
        key = (id(res), len(res.suggestions))
        if key == self.idea_key:
            return
        self.idea_key = key
        for card in self.idea_cards:
            card.destroy()
        target = f"target: {res.target}" if res.target else "no target set"
        sample = f" · {res.sample_note}" if res.sample_note else ""
        self.idea_status.configure(text=f"{len(res.suggestions)} ideas · {target}{sample} · click one to draw it")
        self.idea_all.pack(side="left", padx=(self.app.theme.px(6), 0))
        self.lab_link.pack(side="left", padx=(self.app.theme.px(2), 0))
        self.idea_cards = [IdeaCard(self.scroll.body, self.app, s) for s in res.suggestions[:8]]
        for card in self.idea_cards:
            card.idea_ds = svc.result_ds
        self._layout(force=True)

    def refresh_data_chip(self):
        for w in self.chip.winfo_children():
            w.destroy()
        t, ds = self.app.theme, self.app.dataset
        px = t.px
        box = ttk.Frame(self.chip, style="Well.TFrame", padding=(px(12), px(5), px(5), px(5)))
        box.pack()
        inner = tk.Frame(box, background=C["raised"])
        inner.pack(fill="both", expand=True)
        if ds:
            tk.Label(inner, image=t.icon("file", "muted", 16), background=C["raised"]).pack(side="left")
            name = tk.Label(inner, text=ds.name if len(ds.name) <= 28 else ds.name[:26] + "…",
                            background=C["raised"], foreground=C["text"], font=t.f["bold"])
            name.pack(side="left", padx=(px(6), 0))
            Tooltip(name, str(ds.path))
            tk.Label(inner, text=ds.shape_text, background=C["raised"], foreground=C["muted"],
                     font=t.f["small"]).pack(side="left", padx=(px(8), 0))
            ttk.Button(inner, text="Change…", style="Raised.Small.TButton", command=self.app.open_dialog).pack(
                side="left", padx=(px(10), 0))
        else:
            tk.Label(inner, text="No data loaded yet", background=C["raised"], foreground=C["muted"],
                     font=t.f["small"]).pack(side="left")
            ttk.Button(inner, text="Open data file…", style="Raised.Small.TButton",
                       command=lambda: (self.app.loader.set_graph(None), self.app.show("load"))).pack(
                side="left", padx=(px(10), 0))

    def _visible(self):
        text = self.search.value().strip().lower()
        cat = self.cat.get()
        out = []
        for g in GRAPHS:
            if cat != "All" and g.category != cat:
                continue
            hay = f"{g.name} {g.blurb} {g.category} {g.book} {g.id}".lower()
            if text and not all(word in hay for word in text.split()):
                continue
            out.append(g)
        return out

    def _enter(self, _e=None):
        shown = self._visible()
        if len(shown) == 1:
            self.app.choose_graph(shown[0])

    def refilter(self):
        self._shown = None
        self._layout(force=True)
        self.scroll.to_top()

    def _layout(self, force=False):
        px = self.app.theme.px
        width = self.scroll.canvas.winfo_width()
        if width < 50:
            return
        gap = px(8)
        card_w = max(c.winfo_reqwidth() for c in self.cards.values()) + gap
        cols = max(1, (width - px(32)) // card_w)
        left = max(px(GUTTER), (width - cols * card_w) // 2)   # centre the block of cards
        body = self.scroll.body
        body.columnconfigure(0, minsize=left)                   # column 0: the left margin
        for c in range(1, max(cols, self._cols) + 1):           # equal card columns
            body.columnconfigure(c, uniform="card" if c <= cols else "", minsize=0)
        self._cols = cols
        visible = self._visible()
        ideas = self.app.dataset is not None and not self.search.value().strip() and self.cat.get() == "All"
        key = (cols, left, tuple(g.id for g in visible), ideas, self.idea_key)
        if key == self._shown and not force:
            return
        self._shown = key
        for w in (list(self.headings.values()) + list(self.cards.values()) + self.idea_cards +
                  [self.empty, self.spacer, self.idea_head]):
            w.grid_forget()
        row = 0
        if ideas:
            self.idea_head.grid(row=0, column=1, columnspan=cols, sticky="w", padx=(px(6), 0), pady=(px(14), px(6)))
            row = 1
            for i, card in enumerate(self.idea_cards[:cols]):
                card.grid(row=1, column=i + 1, sticky="nsew", padx=(0, gap), pady=(0, gap))
            if self.idea_cards:
                row = 2
        if not visible:
            text = self.search.value().strip()
            self.empty.configure(text=(f"No graph matches “{text}”." if text else "No graph in this group.") +
                                 "\nTry another word, or pick All.")
            self.empty.grid(row=0, column=1, columnspan=max(1, cols), pady=px(30), sticky="w")
        for cat in CATEGORIES:
            group = [g for g in visible if g.category == cat]
            if not group:
                continue
            self.headings[cat].grid(row=row, column=1, columnspan=cols, sticky="w", padx=(px(6), 0),
                                    pady=(px(22) if row else px(14), px(6)))
            row += 1
            for i, g in enumerate(group):
                r, c = divmod(i, cols)
                self.cards[g.id].grid(row=row + r, column=c + 1, sticky="nsew", padx=(0, gap), pady=(0, gap))
            row += math.ceil(len(group) / cols)
        self.spacer.grid(row=row, column=1)


class GraphCard(Tile):
    """One graph type in the gallery: preview, name, what it is for."""

    def __init__(self, master, app: App, graph):
        t, px = app.theme, app.theme.px
        super().__init__(master, command=lambda: app.choose_graph(graph), padding=px(9))
        self.graph, self.app = graph, app
        img = app.thumbs.get(graph.id)
        wrap = (img.width() if img else px(200)) - px(4)
        if img:
            self.picture = tk.Label(self, image=img, background=C["panel"], borderwidth=0)
        else:
            self.picture = tk.Label(self, text=graph.name, width=24, height=6, background=C["accent_soft"],
                                    foreground=C["accent"])
        self.picture.pack(anchor="w")
        tk.Label(self, text=graph.name, background=C["panel"], foreground=C["text"], font=t.f["h3"],
                 anchor="w").pack(fill="x", padx=px(2), pady=(px(10), 0))
        tk.Label(self, text=graph.blurb, background=C["panel"], foreground=C["muted"], font=t.f["small"],
                 wraplength=wrap, justify="left", anchor="w").pack(fill="x", padx=px(2), pady=(px(2), 0))
        if graph.book:
            tk.Label(self, text=graph.book, background=C["panel"], foreground=C["faint"], font=t.f["tiny"],
                     wraplength=wrap, justify="left", anchor="w").pack(fill="x", padx=px(2), pady=(px(6), px(2)))
        self.wire()

    def on_theme(self):
        img = self.app.thumbs.get(self.graph.id)
        if img is not None:
            self.picture.configure(image=img)
        super().on_theme()


# =========================================================================== #
# Page 2: load a CSV
# =========================================================================== #

class LoadPage(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        t, px = app.theme, app.theme.px
        g = px(GUTTER)
        self._result = None
        self._then_plot = False
        head = ttk.Frame(self, style="Card.TFrame", padding=(px(14), px(10)))
        head.pack(fill="x", padx=g, pady=(g, 0))
        inner = tk.Frame(head, background=C["panel"])
        inner.pack(fill="x")
        back_button(inner, app).pack(side="left")
        ttk.Label(inner, text="Load a data file", style="Panel.H3.TLabel").pack(side="left", padx=(px(14), 0))
        self.for_graph = ttk.Label(inner, style="Panel.Muted.TLabel")
        self.for_graph.pack(side="left", padx=(px(10), 0))
        theme_button(inner, app).pack(side="right")

        scroll = ScrollFrame(self, t, bg=C["bg"])
        scroll.pack(fill="both", expand=True)
        card = ttk.Frame(scroll.body, style="Card.TFrame", padding=(px(32), px(28), px(32), px(24)))
        card.pack(pady=(px(20), px(28)))
        self.card = card
        body = tk.Frame(card, background=C["panel"])
        body.pack(fill="both", expand=True)
        tk.Frame(body, background=C["panel"], width=px(680), height=1).pack()
        ttk.Label(body, text="Choose a data file, PDF, or table image", style="Panel.H2.TLabel").pack(anchor="w")
        ttk.Label(body, text="The delimiter, encoding, column types and missing values are detected for you.",
                  style="Panel.Muted.TLabel").pack(anchor="w", pady=(px(4), px(18)))
        row = tk.Frame(body, background=C["panel"])
        row.pack(fill="x")
        self.open_btn = ttk.Button(row, text="Choose CSV, PDF, or image…", image=t.icon("folder", "on_accent", 18),
                                   compound="left", style="Big.Accent.TButton", command=app.open_dialog)
        self.open_btn.pack(side="left")
        self.paste_btn = ttk.Button(row, text="Paste screenshot", image=t.icon("image", "muted", 18),
                                    compound="left", style="Big.TButton", command=self.paste_image)
        self.paste_btn.pack(side="left", padx=(px(10), 0))
        Tooltip(self.paste_btn, "Read a table from a screenshot on the clipboard (Ctrl+Shift+V)")
        self.shortcut = ttk.Label(row, text="or press Ctrl+O", style="Panel.Faint.TLabel")
        self.shortcut.pack(side="left", padx=(px(12), 0))
        self.progress = ttk.Progressbar(row, mode="indeterminate", length=px(160))
        self.status = ttk.Label(body, style="Panel.Muted.TLabel", wraplength=px(640), justify="left")
        self.status.pack(anchor="w", pady=(px(10), 0))

        ttk.Label(body, text="Recent files", style="Section.TLabel").pack(anchor="w", pady=(px(22), px(8)))
        self.recent = tk.Frame(body, background=C["panel"])
        self.recent.pack(fill="x")

        ttk.Label(body, text="Try a sample", style="Section.TLabel").pack(anchor="w", pady=(px(22), px(8)))
        samples = tk.Frame(body, background=C["panel"])
        samples.pack(fill="x")
        files = sorted(SAMPLES.glob("*.csv")) if SAMPLES.is_dir() else []
        for i, f in enumerate(files):
            b = ttk.Button(samples, text=f.name, style="TButton", command=lambda p=f: self.load(p))
            b.grid(row=i // 3, column=i % 3, sticky="ew", padx=(0, px(4)), pady=(0, px(4)))
            Tooltip(b, SAMPLE_INFO.get(f.name, ""))
        for c in range(3):
            samples.columnconfigure(c, weight=1, uniform="samples")

        adv = Section(body, t, "Advanced reading options", collapsed=True)
        adv.pack(fill="x", pady=(px(10), 0))
        grid = adv.body
        self.sep = tk.StringVar(value="Auto")
        self.enc = tk.StringVar(value="Auto")
        self.header = tk.StringVar(value="Auto")
        for r, (label, var, values) in enumerate((
                ("Delimiter", self.sep, list(DELIMITERS)), ("Encoding", self.enc, list(ENCODINGS)),
                ("First row is column names", self.header, ["Auto", "Yes", "No"]))):
            ttk.Label(grid, text=label, style="Panel.TLabel").grid(row=r, column=0, sticky="w", padx=(t.m, 0),
                                                                   pady=px(2))
            ttk.Combobox(grid, textvariable=var, values=values, state="readonly", width=16).grid(
                row=r, column=1, sticky="w", padx=(px(12), 0), pady=px(2))
        self.refresh_recent()

    def on_show(self):
        for row in self.recent.winfo_children():
            if isinstance(row, Tile):
                row.reset()

    def set_graph(self, graph):
        self.for_graph.configure(text=f"for {graph.name}" if graph else "")

    def refresh_recent(self):
        t, px = self.app.theme, self.app.theme.px
        for w in self.recent.winfo_children():
            w.destroy()
        paths = [Path(p) for p in self.app.cfg.get("recent", []) if Path(p).is_file()][:6]
        if not paths:
            ttk.Label(self.recent, text="Files you open appear here.", style="Panel.Muted.TLabel").pack(anchor="w")
            return
        for p in paths:
            row = Tile(self.recent, command=lambda p=p: self.load(p), style="Panel.Tile.TFrame",
                       padding=(px(12), px(7)))
            row.pack(fill="x", pady=(0, px(2)))
            tk.Label(row, image=t.icon("file", "muted", 18), background=C["panel"]).pack(side="left")
            tk.Label(row, text=p.name, background=C["panel"], foreground=C["text"], font=t.f["bold"]).pack(
                side="left", padx=(px(8), 0))
            tk.Label(row, text=short_path(p.parent, 48), background=C["panel"], foreground=C["faint"],
                     font=t.f["small"]).pack(side="left", padx=(px(10), 0))
            tk.Label(row, text=file_size_text(p), background=C["panel"], foreground=C["muted"],
                     font=t.f["small"]).pack(side="right")
            row.wire()
            Tooltip(row, str(p))

    # ------------------------------------------------------ tables from PDFs and images --
    def paste_image(self):
        """Read a clipboard image into a temporary PNG and start the image import."""
        try:
            from PIL import Image, ImageGrab
            image = ImageGrab.grabclipboard()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            messagebox.showerror(APP_NAME, f"Couldn't read an image from the clipboard:\n{exc}", parent=self)
            return
        if isinstance(image, Image.Image):
            with tempfile.NamedTemporaryFile(prefix="csv_plot_studio_clipboard_", suffix=".png", delete=False) as fh:
                image_path = Path(fh.name)
            try:
                image.save(image_path, format="PNG")
            except Exception as exc:  # noqa: BLE001 - shown to the user
                image_path.unlink(missing_ok=True)
                messagebox.showerror(APP_NAME, f"Couldn't save the clipboard image:\n{exc}", parent=self)
                return
            self.load_image(image_path)
            return
        if isinstance(image, list):
            candidate = next((Path(item) for item in image if Path(item).suffix.lower() in
                              {".png", ".jpg", ".jpeg", ".webp"}), None)
            if candidate is not None:
                self.load_image(candidate)
                return
        messagebox.showinfo(APP_NAME, "The clipboard has no image. Copy a screenshot of a table and try again.",
                            parent=self)

    def _start_import(self, text):
        self.app.show("load")
        self._then_plot = False
        self.open_btn.state(["disabled"])
        self.paste_btn.state(["disabled"])
        self.shortcut.pack_forget()
        self.progress.pack(side="left", padx=(self.app.theme.px(16), 0))
        self.progress.start(12)
        self.status.configure(text=text, style="Panel.Muted.TLabel")
        self._result = None
        self._progress_text = ""
        self._token = token = getattr(self, "_token", 0) + 1
        gc.collect()
        return token

    def load_image(self, path):
        """OCR an image in a worker thread, then open the review dialog."""
        path = Path(path)
        if not path.is_file():
            messagebox.showerror(APP_NAME, f"Image file not found:\n{path}", parent=self)
            return
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            messagebox.showerror(APP_NAME, "Use a PNG, JPG, or WEBP image.", parent=self)
            return
        if path.stat().st_size > MAX_IMAGE_BYTES:
            messagebox.showerror(APP_NAME, "This image is too large. The maximum supported size is 50 MB.",
                                 parent=self)
            return
        token = self._start_import(f"Reading the table in {path.name}…")

        def work():
            try:
                result = ("image", extract_table(path))
            except Exception as exc:  # noqa: BLE001 - shown to the user
                result = ("error", exc)
            if token == self._token:
                self._result = result

        threading.Thread(target=work, daemon=True).start()
        self.after(80, lambda: self._poll(image_path=path))

    def load(self, path, then_plot=False):
        path = Path(path)
        if not path.is_file():
            messagebox.showerror(APP_NAME, f"File not found:\n{path}\n\nIt may have been moved or renamed.",
                                 parent=self)
            return
        self.app.show("load")
        self._then_plot = then_plot
        sep = DELIMITERS[self.sep.get()]
        enc = ENCODINGS[self.enc.get()]
        header = {"Auto": None, "Yes": True, "No": False}[self.header.get()]
        self.open_btn.state(["disabled"])
        self.paste_btn.state(["disabled"])
        self.shortcut.pack_forget()
        self.progress.pack(side="left", padx=(self.app.theme.px(16), 0))
        self.progress.start(12)
        self.status.configure(text=f"Reading {path.name} ({file_size_text(path)})…", style="Panel.Muted.TLabel")
        self._result = None
        self._token = token = getattr(self, "_token", 0) + 1   # only the latest request counts

        def work():
            try:
                result = ("ok", load_csv(path, sep=sep, encoding=enc, header=header))
            except Exception as exc:  # noqa: BLE001 - shown to the user
                result = ("error", exc)
            if token == self._token:
                self._result = result

        gc.collect()      # free dead Tk variables HERE: Tk must not delete them from the reading thread
        threading.Thread(target=work, daemon=True).start()
        self.after(80, self._poll)

    def load_pdf(self, path, password=None):
        """Read the PDF's tables in a worker thread, then open the review dialog."""
        path = Path(path)
        if not path.is_file():
            messagebox.showerror(APP_NAME, f"File not found:\n{path}", parent=self)
            return
        if path.stat().st_size > MAX_PDF_BYTES:
            messagebox.showerror(APP_NAME, "This PDF is too large. The maximum supported size is 50 MB.", parent=self)
            return
        token = self._start_import(f"Looking for tables in {path.name}…")

        def progress(done, total):
            self._progress_text = f"Looking for tables in {path.name}: page {done} of {total}…"

        def work():
            try:
                result = ("pdf", extract_tables(path, password=password, progress=progress))
            except Exception as exc:  # noqa: BLE001 - shown to the user
                result = ("error", exc)
            if token == self._token:
                self._result = result

        threading.Thread(target=work, daemon=True).start()
        self.after(80, lambda: self._poll(pdf_path=path))

    PREVIEW_ROWS = 300      # the review grid shows this many rows; the rest are saved as read

    def render_table_preview(self, parent, frame, *, editable=False):
        """Scrollable table for PDF and image imports. Amber cells: low OCR confidence, or every cell when the
        columns were guessed. Returns the entry widgets so edits can be read back."""
        t, px = self.app.theme, self.app.theme.px
        for child in parent.winfo_children():
            child.destroy()
        outer = tk.Frame(parent, background=C["panel"])
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        canvas = tk.Canvas(outer, background=C["panel"], highlightthickness=0)
        ybar = AutoScrollbar(outer, orient="vertical", command=canvas.yview)
        xbar = AutoScrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        grid = tk.Frame(canvas, background=C["panel"])
        canvas.create_window((0, 0), window=grid, anchor="nw")
        grid.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))

        threshold = float(frame.attrs.get("low_confidence_threshold", 65.0))
        check_all = bool(frame.attrs.get("review_all"))
        header_scores = frame.attrs.get("header_confidence", [])
        cell_scores = frame.attrs.get("cell_confidence", [])
        header_entries, value_entries = [], []
        widths = [max(8, min(28, max([len(str(name))] + [len(str(v)) for v in frame.iloc[:50, j]]) + 2))
                  for j, name in enumerate(frame.columns)]

        def add_cell(value, confidence, row, column, *, header=False):
            value = "" if pd.isna(value) else str(value)
            low = (confidence is not None and confidence < threshold) or (check_all and not header)
            background = C["warn_soft"] if low else C["field"]
            entry = tk.Entry(grid, width=widths[column], relief="flat", bd=0, background=background,
                             foreground=C["text"], insertbackground=C["text"], highlightthickness=1,
                             highlightbackground=C["border"], highlightcolor=C["focus_ring"],
                             font=t.f["bold"] if header else t.f["small"])
            entry.insert(0, value)
            if not editable:
                entry.configure(state="readonly", readonlybackground=background)
            entry.grid(row=row, column=column, sticky="nsew", padx=(0, 1), pady=(0, 1), ipady=px(3))
            (header_entries if header else value_entries).append(entry)
            if confidence is not None:
                Tooltip(entry, f"OCR confidence {confidence:.0f}%" + (": check this cell" if low else ""))
            elif check_all and not header:
                Tooltip(entry, "Columns were guessed from word positions: check this cell")
            return entry

        for column, name in enumerate(frame.columns):
            score = header_scores[column] if column < len(header_scores) else None
            add_cell(name, score, 0, column, header=True)
        for row_index, row in enumerate(frame.head(self.PREVIEW_ROWS).itertuples(index=False, name=None)):
            for column, value in enumerate(row):
                score = (cell_scores[row_index][column] if row_index < len(cell_scores)
                         and column < len(cell_scores[row_index]) else None)
                add_cell(value, score, row_index + 1, column)
        if len(frame) > self.PREVIEW_ROWS:
            tk.Label(grid, text=f"Showing the first {self.PREVIEW_ROWS:,} of {len(frame):,} rows; the rest are "
                                "saved as read.", background=C["panel"], foreground=C["muted"],
                     font=t.f["small"]).grid(row=self.PREVIEW_ROWS + 1, column=0, columnspan=frame.shape[1],
                                             sticky="w", pady=(px(6), 0))
        return {"headers": header_entries, "values": value_entries}

    @staticmethod
    def _read_back(frame, controls):
        """The table with the review grid's edits applied (only the rows the grid showed can change)."""
        headers = [entry.get().strip() or f"Column {i + 1}" for i, entry in enumerate(controls["headers"])]
        seen, names = {}, []
        for header in headers:
            seen[header] = seen.get(header, 0) + 1
            names.append(header if seen[header] == 1 else f"{header} ({seen[header]})")
        edited = frame.copy().astype(object).where(frame.notna(), "")
        edited.columns = names
        width, entries = len(names), controls["values"]
        for k, entry in enumerate(entries):
            edited.iat[k // width, k % width] = entry.get().strip()
        edited.attrs.update(frame.attrs)
        return edited

    def review_tables(self, source, tables, kind):
        """One dialog for PDF and image imports: pick a table (PDFs), read what to check, edit cells, then save
        it as a CSV (with a .source.json note next to it) and open it."""
        t, px = self.app.theme, self.app.theme.px
        win = tk.Toplevel(self)
        win.title(f"Review the table · {source.name}")
        win.transient(self.winfo_toplevel())
        win.configure(background=C["bg"])
        win.geometry(f"{px(1180)}x{px(720)}")
        win.minsize(px(760), px(460))
        t.dark_title_bar(win)
        clipboard = source.name.startswith("csv_plot_studio_clipboard_")
        edited = [None] * len(tables)
        state = {"index": 0, "controls": None}

        card = ttk.Frame(win, style="Card.TFrame", padding=(px(22), px(18)))
        card.pack(fill="both", expand=True, padx=px(12), pady=(px(12), 0))
        body = tk.Frame(card, background=C["panel"])
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Check the table before it opens", style="Panel.H2.TLabel").pack(anchor="w")
        ttk.Label(body, text="Click a cell to change it. Amber cells are the ones to check first.",
                  style="Panel.Muted.TLabel").pack(anchor="w", pady=(px(2), px(12)))
        main = tk.Frame(body, background=C["panel"])
        main.pack(fill="both", expand=True)

        side = None
        if kind == "pdf" and len(tables) > 1:
            side = tk.Frame(main, background=C["panel"])
            side.pack(side="left", fill="y", padx=(0, px(16)))
            ttk.Label(side, text=f"{len(tables)} tables found", style="Section.TLabel").pack(anchor="w",
                                                                                          pady=(0, px(6)))
            listing = tk.Listbox(side, exportselection=False, activestyle="none", width=30, relief="flat", bd=0,
                                 highlightthickness=1, highlightbackground=C["border"],
                                 highlightcolor=C["focus_ring"], background=C["field"], foreground=C["text"],
                                 selectbackground=C["select"], selectforeground=C["text"], font=t.f["small"])
            listing.pack(fill="y", expand=True)
            for i, frame in enumerate(tables):
                pages = frame.attrs.get("pages", [frame.attrs.get("page_number", i + 1)])
                where = f"page {pages[0]}" if len(pages) == 1 else f"pages {pages[0]}–{pages[-1]}"
                listing.insert("end", f"  Table {i + 1}, {where} ({len(frame):,} × {frame.shape[1]})")
            listing.selection_set(0)
        elif kind == "image":
            side = tk.Frame(main, background=C["panel"])
            side.pack(side="left", fill="y", padx=(0, px(16)))
            picture = tk.Label(side, background=C["panel"], anchor="n")
            picture.pack(fill="both", expand=True)
            try:
                from PIL import Image, ImageTk
                original = Image.open(source).convert("RGB")
                original.thumbnail((px(420), px(520)), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(original, master=win)
                picture.configure(image=photo)
                picture.image = photo
            except Exception as exc:  # noqa: BLE001 - the preview is optional; the reason is shown
                picture.configure(text=f"No preview of the image:\n{exc}", foreground=C["muted"], font=t.f["small"])

        right = tk.Frame(main, background=C["panel"])
        right.pack(side="left", fill="both", expand=True)
        info = ttk.Label(right, style="Panel.Muted.TLabel", justify="left", wraplength=px(640))
        info.pack(anchor="w", fill="x")
        notes = ttk.Label(right, style="Warn.TLabel", justify="left", wraplength=px(640))
        notes.pack(anchor="w", fill="x", pady=(px(4), px(8)))
        table_box = tk.Frame(right, background=C["panel"])
        table_box.pack(fill="both", expand=True)

        def commit():
            if state["controls"] is not None:
                i = state["index"]
                edited[i] = self._read_back(tables[i], state["controls"])

        def show(index):
            commit()
            state["index"] = index
            frame = edited[index] if edited[index] is not None else tables[index]
            pages = frame.attrs.get("pages")
            where = (f"Page {pages[0]}" if pages and len(pages) == 1 else
                     f"Pages {pages[0]}–{pages[-1]}" if pages else "Image")
            info.configure(text=f"{where}, read from the {frame.attrs.get('method', 'picture')}: "
                                f"{len(frame):,} rows and {frame.shape[1]} columns")
            todo = list(frame.attrs.get("notes", [])) + list(frame.attrs.get("document_notes", []))
            notes.configure(text="\n".join(f"• {n}" for n in todo))
            state["controls"] = self.render_table_preview(table_box, frame, editable=True)

        if kind == "pdf" and len(tables) > 1:
            listing.bind("<<ListboxSelect>>", lambda _e: listing.curselection() and show(listing.curselection()[0]))
        show(0)

        def close():
            win.destroy()
            if clipboard:
                source.unlink(missing_ok=True)

        def save():
            commit()
            i = state["index"]
            original, table = tables[i], edited[i]
            folder = (self.app.cfg.get("last_dir") or str(Path.home())) if clipboard else str(source.parent)
            name = "clipboard_table.csv" if clipboard else suggested_name(source, i + 1 if len(tables) > 1 else None)
            target = filedialog.asksaveasfilename(parent=win, title="Save the table as", initialdir=folder,
                                                  initialfile=name, defaultextension=".csv",
                                                  filetypes=[("CSV files", "*.csv")])
            if not target:
                return
            note = {"source": "clipboard image" if clipboard else str(source), "kind": kind,
                    "pages": table.attrs.get("pages"), "method": table.attrs.get("method"),
                    "to_check": list(table.attrs.get("notes", [])), "edits": edits_between(original, table)}
            try:
                path = save_table(pd.DataFrame(table), target, note)
            except OSError as exc:
                messagebox.showerror(APP_NAME, f"Couldn't save the table:\n{exc}", parent=win)
                return
            close()
            self.load(path)

        buttons = tk.Frame(win, background=C["bg"])
        buttons.pack(fill="x", padx=px(12), pady=px(12))
        ttk.Button(buttons, text="Save as CSV and open", style="Bg.Accent.TButton", command=save).pack(side="right")
        ttk.Button(buttons, text="Cancel", style="Bg.TButton", command=close).pack(side="right", padx=(0, px(8)))
        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _e: close())
        win.grab_set()
        win.wait_window()

    def _ask_password(self, path, wrong):
        from tkinter import simpledialog
        prompt = ("That password didn't open it. Try again:" if wrong else
                  f"{path.name} is protected with a password. Enter it to read its tables:")
        return simpledialog.askstring(APP_NAME, prompt, show="•", parent=self)

    def _poll(self, pdf_path=None, image_path=None):
        if self._result is None:
            if getattr(self, "_progress_text", ""):
                self.status.configure(text=self._progress_text)
            self.after(80, lambda: self._poll(pdf_path=pdf_path, image_path=image_path))
            return
        self.progress.stop()
        self.progress.pack_forget()
        self.shortcut.pack(side="left", padx=(self.app.theme.px(12), 0))
        self.open_btn.state(["!disabled"])
        self.paste_btn.state(["!disabled"])
        kind, value = self._result
        if kind in ("pdf", "image"):
            self.status.configure(text="")
            self.review_tables(pdf_path or image_path, value if kind == "pdf" else [value], kind)
            return
        if kind == "error":
            if isinstance(value, PasswordNeeded):
                password = self._ask_password(pdf_path, isinstance(value, WrongPassword))
                if password:
                    self.load_pdf(pdf_path, password=password)
                else:
                    self.status.configure(text=str(value), style="Error.TLabel")
                return
            if image_path is not None and image_path.name.startswith("csv_plot_studio_clipboard_"):
                image_path.unlink(missing_ok=True)
            if pdf_path is not None or image_path is not None:
                self.status.configure(text=str(value), style="Error.TLabel")
            else:
                self.status.configure(text=f"Couldn't read this file ({type(value).__name__}: {value}).\n"
                                           "Open 'Advanced reading options' below and set the delimiter or the "
                                           "encoding by hand.", style="Error.TLabel")
            return
        self.status.configure(text=f"Loaded {value.name}: {value.shape_text} in {value.seconds:.1f} s",
                              style="Ok.TLabel")
        self.app.set_dataset(value, then_plot=self._then_plot)


# =========================================================================== #
# Page 3: columns + plot workspace
# =========================================================================== #

class WorkspacePage(ttk.Frame):
    LEFT_WIDTH = 380

    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        t, px = app.theme, app.theme.px
        g = px(GUTTER)
        self.graph = None
        self.ds = None
        self.roles = {}
        self.options = {}
        self.memory = {}        # previous column choices, reused when switching graphs
        self.type_overrides = {}  # column -> kind the user set under Plot ideas > Column types
        self.opt_memory = {}    # (graph id, option) -> value
        self.has_plotted = False
        self.last_built = None
        self.last_signature = None
        self.view_limits = {"x": None, "y": None}   # set with the range sliders around the plot
        self.last_request = None
        self._after = None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        card = ttk.Frame(self, style="Card.TFrame", width=px(self.LEFT_WIDTH))
        card.grid(row=0, column=0, sticky="nsew", padx=(g, px(6)), pady=g)
        card.pack_propagate(False)
        left = tk.Frame(card, background=C["panel"])
        left.pack(fill="both", expand=True)
        side = px(16)

        # header
        head = tk.Frame(left, background=C["panel"], padx=side - px(4), pady=px(10))
        head.pack(side="top", fill="x")
        nav = tk.Frame(head, background=C["panel"])
        nav.pack(fill="x")
        back_button(nav, app).pack(side="left")
        theme_button(nav, app).pack(side="right")
        profile_button(nav, app).pack(side="right", padx=(0, px(8)))
        self.g_name = ttk.Label(head, style="Panel.H2.TLabel")
        self.g_name.pack(anchor="w", padx=px(4), pady=(px(8), 0))
        self.g_book = ttk.Label(head, style="Panel.Faint.TLabel")
        self.g_book.pack(anchor="w", padx=px(4))
        drow = ttk.Frame(head, style="Well.TFrame", padding=(px(10), px(6), px(5), px(6)))
        drow.pack(fill="x", pady=(px(10), 0), padx=px(1))
        dinner = tk.Frame(drow, background=C["raised"])
        dinner.pack(fill="both", expand=True)
        dinner.columnconfigure(1, weight=1)
        tk.Label(dinner, image=t.icon("file", "muted", 18), background=C["raised"]).grid(
            row=0, column=0, rowspan=2, padx=(0, px(8)))
        self.d_name = tk.Label(dinner, background=C["raised"], foreground=C["text"], font=t.f["bold"], anchor="w")
        self.d_name.grid(row=0, column=1, sticky="w")
        self.d_shape = tk.Label(dinner, background=C["raised"], foreground=C["muted"], font=t.f["small"],
                                anchor="w")
        self.d_shape.grid(row=1, column=1, sticky="w")
        self.d_tip = Tooltip(self.d_name, "")
        ttk.Button(dinner, text="Change file…", style="Raised.Small.TButton", command=app.open_dialog).grid(
            row=0, column=2, rowspan=2, sticky="e", padx=(px(8), 0))
        tk.Frame(left, background=C["border"], height=max(1, px(1))).pack(side="top", fill="x", padx=side)

        # footer with the Plot button
        foot = tk.Frame(left, background=C["panel"], padx=side - px(3), pady=px(12))
        foot.pack(side="bottom", fill="x")
        tk.Frame(left, background=C["border"], height=max(1, px(1))).pack(side="bottom", fill="x", padx=side)
        self.plot_btn = ttk.Button(foot, text="Plot", image=t.icon("play", "on_accent", 14), compound="right",
                                   style="Big.Accent.TButton", command=self.plot)
        self.plot_btn.pack(fill="x")
        Tooltip(self.plot_btn, "Draw the graph (Ctrl+Enter or F5)")
        frow = tk.Frame(foot, background=C["panel"])
        frow.pack(fill="x", pady=(px(8), 0))
        self.auto_var = tk.BooleanVar(value=bool(app.cfg.get("auto_update", True)))
        cb = ttk.Checkbutton(frow, text="Redraw after every change", variable=self.auto_var,
                             style="Switch.TCheckbutton")
        cb.pack(side="left")
        Tooltip(cb, "After the first plot, redraw automatically whenever you change a column or an option.")
        ttk.Label(frow, text="Ctrl+Enter", style="Panel.Faint.TLabel").pack(side="right", padx=(0, px(3)))
        self.msg = ttk.Label(foot, style="Panel.Muted.TLabel", wraplength=px(self.LEFT_WIDTH - 44), justify="left")
        self.msg.pack(fill="x", padx=px(3), pady=(px(6), 0))

        # scrolling controls
        self.scroll = ScrollFrame(left, t, bg=C["panel"])
        self.scroll.pack(side="top", fill="both", expand=True, padx=(0, px(2)))
        body = self.scroll.body
        pad = dict(padx=(side - px(7), px(8)))
        self.show_all = tk.BooleanVar(value=False)

        def show_all_switch(parent):
            sw = ttk.Checkbutton(parent, text="Show all", variable=self.show_all, command=self.rebuild_roles,
                                 style="Small.Switch.TCheckbutton")
            Tooltip(sw, "Offer every column in every slot, not only the ones of the right type.")
            return sw

        self.sec_cols = Section(body, t, "Columns", extra=show_all_switch)
        self.sec_cols.pack(fill="x", **pad)
        # the target (what a model would predict) steers the column suggestions
        self.target_var = tk.StringVar(value=NONE)
        trow = tk.Frame(self.sec_cols.body, background=C["panel"])
        trow.pack(fill="x", pady=(0, px(14)))
        ttop = tk.Frame(trow, background=C["panel"])
        ttop.pack(fill="x")
        tl = ttk.Label(ttop, text="Target", style="Panel.Bold.TLabel")
        tl.pack(side="left", padx=(t.m, 0))
        ttk.Label(ttop, text="the column you want to predict", style="Panel.Muted.TLabel").pack(
            side="left", padx=(px(8), 0), pady=(px(1), 0))
        self.target_box = ttk.Combobox(trow, textvariable=self.target_var, values=[NONE], state="readonly",
                                       height=18)
        self.target_box.pack(fill="x", pady=(px(4), 0))
        self.target_box.bind("<<ComboboxSelected>>", self._target_changed)
        sa = ttk.Button(trow, text="Suggest all columns", image=t.icon_states("sparkle", 16, normal="accent",
                                                                             active="accent_hover"),
                        compound="left", style="TButton", command=self.suggest_all)
        sa.pack(fill="x", pady=(px(6), 0))
        for w in (tl, self.target_box):
            Tooltip(w, "The column you want to predict. The suggestions rank the other columns by how strongly "
                       "they are linked to it:\n  r = correlation (numbers; "
                       f"{recommend.SYMBOLS['rho']} when the link is curved but steady)\n  "
                       f"{recommend.SYMBOLS['eta']} = how much the classes differ (number vs groups)\n"
                       "  V = Cramér's V (groups vs groups)\n0 = no link, 1 = perfect link.")
        Tooltip(sa, "Fill every slot with the recommended columns and plot. Each slot also has its own "
                    "Suggest list.")
        self.roles_frame = tk.Frame(self.sec_cols.body, background=C["panel"])
        self.roles_frame.pack(fill="x")
        self.pending_note = None
        self.sec_rows = Section(body, t, "Rows")
        self.sec_rows.pack(fill="x", **pad)
        self._build_rows(self.sec_rows.body)
        self.sec_opts = Section(body, t, "Options")
        self.sec_opts.pack(fill="x", **pad)
        self.sec_style = Section(body, t, "Labels and style", collapsed=not app.cfg.get("style_open", False))
        self.sec_style.pack(fill="x", **pad)
        self._build_style(self.sec_style.body)
        tk.Frame(body, background=C["panel"], height=px(16)).pack()

        # right side tabs
        self.nb = ttk.Notebook(self)
        self.nb.grid(row=0, column=1, sticky="nsew", padx=(px(6), g), pady=g)
        self.plot_view = PlotView(self.nb, self)
        self.code_view = CodeView(self.nb, self)
        self.data_view = DataView(self.nb, self)
        self.ideas_view = IdeasView(self.nb, self)
        self.lab_view = FeatureLabView(self.nb, self)
        self.ceasar_view = CeasarView(self.nb, self)
        for view, text, icon in ((self.plot_view, "Plot", "chart"), (self.code_view, "Python code", "code"),
                                 (self.data_view, "Data summary", "table"), (self.ideas_view, "Plot ideas", "sparkle"),
                                 (self.lab_view, "Feature Lab", "flask"), (self.ceasar_view, "Ceasar", "chat")):
            self.nb.add(view, text=f" {text}", compound="left",
                        image=t.icon_states(icon, 16, normal="muted", active="text", selected="text"))
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed, add="+")

    def on_show(self):
        pass

    # ---------------------------------------------------------------- build --
    def _build_rows(self, parent):
        t, px = self.app.theme, self.app.theme.px
        self.row_mode = tk.StringVar(value="all")
        self.first_n = tk.StringVar(value="1000")
        self.start = tk.StringVar(value="0")
        self.stop = tk.StringVar(value="1000")
        self.sample_n = tk.StringVar(value="5000")
        self.seed = tk.StringVar(value="42")

        def spin(master, var, width=7, lo=0, hi=10_000_000):
            sb = ttk.Spinbox(master, textvariable=var, from_=lo, to=hi, increment=100, width=width,
                             command=self.changed)
            sb.bind("<Return>", self.changed)
            sb.bind("<FocusOut>", self.changed)
            return sb

        def line(value, text_before, *parts):
            row = tk.Frame(parent, background=C["panel"])
            row.pack(fill="x", pady=px(1))
            ttk.Radiobutton(row, text=text_before, value=value, variable=self.row_mode,
                            command=self.changed).pack(side="left")
            for part in parts:
                if isinstance(part, str):
                    tk.Label(row, text=part, background=C["panel"], foreground=C["text"]).pack(side="left",
                                                                                               padx=px(2))
                else:
                    part(row).pack(side="left", padx=px(2))
            return row

        line("all", "All rows")
        line("first", "First", lambda r: spin(r, self.first_n), "rows")
        line("range", "Rows", lambda r: spin(r, self.start, 6), "to", lambda r: spin(r, self.stop, 7))
        self.rows_total = 1000
        self._rows_sync = False
        self.rows_slider = RangeSlider(parent, t, two=True, on_change=self._rows_slid,
                                       on_release=lambda lo, hi: self.changed(delay=60), min_gap=0.0)
        self.rows_slider.pack(fill="x", padx=(px(22), px(4)))
        Tooltip(self.rows_slider, "Drag the balls to pick a range of rows (or drag the bar between them). "
                                  "Double-click: all rows.")
        for var in (self.start, self.stop):
            var.trace_add("write", lambda *_: self._rows_to_slider())
        self._rows_to_slider()
        line("sample", "Random sample of", lambda r: spin(r, self.sample_n), "rows")
        tk.Label(parent, text="Filter rows (pandas query)", background=C["panel"], foreground=C["text"],
                 font=t.f["bold"]).pack(anchor="w", padx=(t.m, 0), pady=(px(12), px(4)))
        self.query = PlaceholderEntry(parent, placeholder="e.g. Age > 30 and Class == 'Eco'")
        self.query.pack(fill="x")
        self.query.bind("<Return>", self.changed)
        self.query.bind("<FocusOut>", self.changed)
        Tooltip(self.query, "Keep only rows matching a condition, e.g.\n  Age > 30\n  Sex == 'female' and Fare < 50\n"
                            "  `Flight Distance` > 1000   (backticks for names with spaces)\nPress Enter to apply.")
        self.dropna = tk.BooleanVar(value=True)
        self.dropna_cb = ttk.Checkbutton(parent, text="Skip rows with missing values",
                                         variable=self.dropna, command=self.changed)
        self.dropna_cb.pack(anchor="w", pady=(px(10), 0))
        Tooltip(self.dropna_cb, "Rows with a gap in any of the chosen columns are left out (df.dropna). "
                                "Most plots need this; the missing values map ignores it.")
        self.auto_sample = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(parent, text="Sample big data for slow plots", variable=self.auto_sample,
                             command=self.changed)
        cb.pack(anchor="w")
        Tooltip(cb, "Pair plots, swarm plots, KDEs and regression bands get slow with many rows. "
                    "When on, those plots use a random sample (the app tells you when it does).")

    def _rows_slid(self, lo, hi):
        n = max(1, self.rows_total)
        a, b = int(round(lo * n)), int(round(hi * n))
        if b <= a:
            b = min(n, a + 1)
            a = b - 1
        self._rows_sync = True
        try:
            self.start.set(str(a))
            self.stop.set(str(b))
        finally:
            self._rows_sync = False
        self.row_mode.set("range")
        self.message(f"Rows {a:,} to {b - 1:,}  ({b - a:,} rows)")
        self.changed()

    def _rows_to_slider(self):
        if self._rows_sync:
            return
        n = max(1, self.rows_total)
        try:
            a, b = float(self.start.get()), float(self.stop.get())
        except (ValueError, tk.TclError):
            return
        self.rows_slider.set(min(1.0, max(0.0, a / n)), min(1.0, max(0.0, b / n)))

    def _build_style(self, parent):
        t, px = self.app.theme, self.app.theme.px
        st = self.app.style_settings
        parent.columnconfigure(1, weight=1)
        title_row = tk.Frame(parent, background=C["panel"])
        self.title_entry = PlaceholderEntry(title_row, placeholder="automatic")
        self.show_title = tk.BooleanVar(value=True)
        self.xlabel = PlaceholderEntry(parent, placeholder="automatic")
        self.ylabel = PlaceholderEntry(parent, placeholder="automatic")
        self.logx, self.logy = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        self.legend = tk.StringVar(value=LEGEND_PLACES[0][1])
        self.styles = style_choices()
        self.style_var = tk.StringVar(value=dict(self.styles).get(st.theme, self.styles[0][1]))
        self.palette_var = tk.StringVar(value=st.palette)
        self.context_var = tk.StringVar(value=st.context)
        r = 0

        def label(text):
            ttk.Label(parent, text=text, style="Panel.TLabel").grid(row=r, column=0, sticky="w", padx=(t.m, 0),
                                                                    pady=px(1))

        label("Title")
        title_row.grid(row=r, column=1, sticky="ew", padx=(px(10), 0))
        self.title_entry.pack(side="left", fill="x", expand=True)
        ttk.Checkbutton(title_row, text="show", variable=self.show_title, command=self.changed).pack(
            side="left", padx=(px(6), 0))
        r += 1
        for text, entry in (("X label", self.xlabel), ("Y label", self.ylabel)):
            label(text)
            entry.grid(row=r, column=1, sticky="ew", padx=(px(10), 0), pady=px(1))
            r += 1
        for entry in (self.title_entry, self.xlabel, self.ylabel):
            entry.bind("<Return>", self.changed)
            entry.bind("<FocusOut>", self.changed)
        label("Log scale")
        lr = tk.Frame(parent, background=C["panel"])
        lr.grid(row=r, column=1, sticky="w", padx=(px(10), 0), pady=px(2))
        self.logx_cb = ttk.Checkbutton(lr, text="X axis", variable=self.logx,
                                       command=lambda: (self.clear_limits("x"), self.changed()))
        self.logx_cb.pack(side="left")
        self.logy_cb = ttk.Checkbutton(lr, text="Y axis", variable=self.logy,
                                       command=lambda: (self.clear_limits("y"), self.changed()))
        self.logy_cb.pack(side="left", padx=(px(10), 0))
        r += 1
        for text, var, values in (("Legend", self.legend, [lbl for _, lbl in LEGEND_PLACES]),
                                  ("Style", self.style_var, [lbl for _, lbl in self.styles]),
                                  ("Palette", self.palette_var, PALETTES),
                                  ("Text size", self.context_var, CONTEXTS)):
            label(text)
            cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", height=16)
            cb.grid(row=r, column=1, sticky="ew", padx=(px(10), 0), pady=px(1))
            cb.bind("<<ComboboxSelected>>", self.changed)
            if text == "Palette":
                Tooltip(cb, "'default' uses the style's own colours. 'studio' is the colour-blind-safe set of "
                            "the Studio style.")
            r += 1
        ttk.Label(parent, text="Style, palette and text size are kept for next time.",
                  style="Panel.Muted.TLabel").grid(row=r, column=0, columnspan=2, sticky="w", padx=(t.m, 0),
                                                   pady=(px(6), 0))

    # --------------------------------------------------- graph / data setup --
    def set_dataset(self, ds):
        self.ds = ds
        self.clear_limits()
        self.rows_total = max(1, len(ds.df))
        self._rows_to_slider()
        self.d_name.configure(text=ds.name if len(ds.name) <= 30 else ds.name[:28] + "…")
        self.d_shape.configure(text=ds.shape_text)
        self.d_tip.text = str(ds.path)
        if self.graph is not None and self.roles:
            self._remember()   # hand-picked columns carry over (e.g. train.csv -> test.csv)
        self.type_overrides = {}
        choices = self._refresh_targets()
        guess = recommend.default_target(ds)
        self.target_var.set(guess if guess in choices else NONE)
        self.data_view.set_dataset(ds, self.current_target())
        if self.graph:
            self.rebuild()

    def set_graph(self, graph):
        if self.graph is not None and self.roles:
            self._remember()
        self.graph = graph
        self.clear_limits()
        self.g_name.configure(text=graph.name)
        self.g_book.configure(text=graph.book)
        for entry in (self.title_entry, self.xlabel, self.ylabel):   # labels belong to one graph
            entry.set_value("")
        self.logx.set(False)
        self.logy.set(False)
        if self.ds is not None:
            self.rebuild()
        self.plot_view.show_placeholder(graph)
        self.code_view.set_code("# Press Plot to write the code for this graph.\n")
        self.nb.select(self.plot_view)
        self.message("")
        self.scroll.to_top()

    def _remember(self):
        """Keep the columns the user picked by hand, so the next graph starts from them."""
        for key, row in self.roles.items():
            if row.touched:
                self.memory[key] = row.get() or ""   # "" = the user chose (none)
        for key, w in self.options.items():
            self.opt_memory[(self.graph.id, key)] = w.get()
        self.roles = {}

    def rebuild(self):
        for w in self.sec_opts.body.winfo_children():
            w.destroy()
        self.options = {}
        self.rebuild_roles()
        self.rebuild_options()
        state = ["!disabled"] if self.graph.dropna else ["disabled"]
        self.dropna_cb.state(state)
        for cb in (self.logx_cb, self.logy_cb):
            cb.state(["!disabled"] if self.graph.log_axes else ["disabled"])

    def rebuild_roles(self):
        if not (self.graph and self.ds):
            return
        previous = {k: (r.get() or "") for k, r in self.roles.items()}   # same graph: keep what is shown
        touched = {k for k, r in self.roles.items() if r.touched}
        memory = {**self.memory, **previous}
        for w in self.roles_frame.winfo_children():
            w.destroy()
        self.roles = {}
        show_all = self.show_all.get()
        chosen = suggest(self.graph, self.ds, memory, show_all=show_all)
        for role in self.graph.roles:
            columns = compatible(role, self.ds, show_all=show_all)
            row = RoleRow(self.roles_frame, self, role, columns, chosen.get(role.key))
            row.touched = role.key in touched
            self.roles[role.key] = row
        self.update_visibility()

    def rebuild_options(self):
        for w in self.sec_opts.body.winfo_children():
            w.destroy()
        self.options = {}
        body = self.sec_opts.body
        body.columnconfigure(1, weight=1)
        if not self.graph.options:
            ttk.Label(body, text="This graph has no extra options.", style="Panel.Muted.TLabel").grid(
                row=0, column=0, sticky="w", padx=(self.app.theme.m, 0))
        for i, opt in enumerate(self.graph.options):
            value = self.opt_memory.get((self.graph.id, opt.key), opt.default)
            self.options[opt.key] = OptionRow(body, self, opt, value, i)
        self.update_visibility()

    def update_visibility(self):
        if not self.graph:
            return
        sel = self.collect_selection()
        current = {o.key: o for o in self.graph.options}
        for key, w in self.options.items():
            opt = current.get(key)
            if opt is not None:
                w.show(opt.show_if is None or bool(opt.show_if(sel)))

    # ------------------------------------------------------------ suggestions --
    def current_target(self):
        value = self.target_var.get()
        return None if value in ("", NONE) or self.ds is None or value not in self.ds.columns else value

    def _refresh_targets(self) -> list:
        """The Target lists (left panel and Plot ideas tab) for the current column kinds."""
        choices = recommend.target_choices(self.ds)
        for box in (self.target_box, self.ideas_view.target_box, self.lab_view.target_box):
            box.configure(values=[NONE] + choices)
        return choices

    def set_type_overrides(self, overrides: dict):
        """Treat columns as another kind (relabel only), then refresh slots and suggestions."""
        if self.ds is None:
            return
        try:
            active = type_overrides.apply(self.ds, overrides)
        except ValueError as exc:
            log_error("Column types could not be applied", exc)
            messagebox.showerror(APP_NAME, f"Couldn't change the column types:\n{exc}", parent=self)
            return
        self.type_overrides = active
        recommend.forget(self.ds)
        choices = self._refresh_targets()
        if self.target_var.get() not in choices:
            self.target_var.set(NONE)
        self.data_view.set_dataset(self.ds, self.current_target())
        if self.graph is not None:
            self.rebuild_roles()
        changed = ", ".join(f"{c} → {k}" for c, k in active.items()) or "all columns back to the detected kinds"
        self.message(f"Column types: {changed}.", "ok")
        self.app.ideas.request(self.ds, self.current_target(), active)

    def _target_changed(self, *_):
        target = self.current_target()
        self.data_view.set_target(target)
        self.app.ideas.request(self.ds, target, self.type_overrides)
        self.lab_view.on_target()
        if target:
            self.message(f"Target: {target}. Each Suggest list now ranks columns by their link with it "
                         f"(the Data summary tab shows every link).", "ok")
        else:
            self.message("No target: the suggestions use pairs of columns, dates and the shape of the data.")

    def suggest_all(self):
        """Fill every slot with the recommended columns and plot."""
        if not (self.graph and self.ds):
            return
        sel, notes = recommend.suggest_all(self.graph, self.ds, self.current_target(), show_all=self.show_all.get())
        for key, row in self.roles.items():
            row.apply(sel.get(key))
        self.clear_limits()
        self.update_visibility()
        self.pending_note = ("Suggested: " + "  ·  ".join(notes)) if notes else None
        if notes:
            self.message("Suggested: " + "  ·  ".join(notes), "ok")
        self.plot()

    def open_idea(self, idea):
        """Draw a plot idea: its graph, columns, options and log scales, then plot."""
        graph = GRAPH_BY_ID.get(idea.graph)
        if graph is None or self.ds is None:
            return
        for opt in graph.options:     # the idea's settings, everything else at its default
            self.opt_memory[(graph.id, opt.key)] = idea.opts.get(opt.key, opt.default)
        self.app.graph = graph
        self.set_graph(graph)
        for key, row in self.roles.items():
            row.apply(idea.sel.get(key))
        self.logx.set(bool(idea.logx))
        self.logy.set(bool(idea.logy))
        self.update_visibility()
        if self.app.current != "work":
            self.app.show("work")
        self.scroll.to_top()
        self.pending_note = f"Idea {idea.rank}: {idea.reason}"
        self.plot()

    def _tab_changed(self, _event=None):
        try:
            if self.nb.select() == str(self.lab_view):
                self.lab_view.on_show()
            elif self.nb.select() == str(self.ceasar_view):
                self.ceasar_view.on_show()
        except tk.TclError:
            pass

    def update_dataset(self, ds):
        """The same file with feature steps added or removed: keep the graph, columns, target and types."""
        self.ds = ds
        overrides = {c: k for c, k in self.type_overrides.items() if c in ds.columns}
        try:
            # also with no overrides: the table may carry the kinds of an earlier choice (undoing every step
            # brings back the file's own Dataset, relabelled when Column types was used before the first step)
            overrides = type_overrides.apply(ds, overrides)
        except ValueError as exc:
            log_error("Column types could not be kept for the new table", exc)
            overrides = {}
        self.type_overrides = overrides
        self.rows_total = max(1, len(ds.df))
        self._rows_to_slider()
        self.d_shape.configure(text=ds.shape_text)
        target = self.target_var.get()
        choices = self._refresh_targets()
        if target not in choices:
            self.target_var.set(NONE)
        recommend.forget(ds)
        self.data_view.set_dataset(ds, self.current_target())
        if self.graph is not None:
            self.rebuild_roles()
        self.app.ideas.request(ds, self.current_target(), self.type_overrides)
        self.changed(delay=10)            # with "Redraw after every change": the plot and its code use the new table

    def show_lab(self):
        """The Feature Lab tab (from the gallery)."""
        if self.graph is None:
            res = self.app.ideas.result
            if res is not None and res.suggestions:
                self.open_idea(res.suggestions[0])
            else:
                self.app.graph = GRAPH_BY_ID["hist"]
                self.set_graph(self.app.graph)
        self.app.show("work")
        self.nb.select(self.lab_view)

    def show_ideas(self):
        """The Plot ideas tab (from the gallery's 'All ideas')."""
        if self.graph is None:
            res = self.app.ideas.result
            if res is not None and res.suggestions:
                self.open_idea(res.suggestions[0])
            else:
                return
        self.app.show("work")
        self.nb.select(self.ideas_view)

    # ------------------------------------------------------------ collect --
    def collect_selection(self) -> dict:
        return {k: r.get() for k, r in self.roles.items()}

    def collect_options(self) -> dict:
        return {k: w.get() for k, w in self.options.items()}

    def collect_rows(self) -> RowSettings:
        def num(var, default):
            try:
                return max(0, int(float(var.get())))
            except (ValueError, tk.TclError):
                return default
        return RowSettings(mode=self.row_mode.get(), first_n=max(1, num(self.first_n, 1000)),
                           start=num(self.start, 0), stop=num(self.stop, 1000),
                           sample_n=max(1, num(self.sample_n, 5000)), seed=num(self.seed, 42),
                           query=self.query.value(), dropna=bool(self.dropna.get()),
                           auto_sample=bool(self.auto_sample.get()))

    def collect_labels(self) -> LabelSettings:
        legend = {lbl: val for val, lbl in LEGEND_PLACES}.get(self.legend.get(), "auto")
        return LabelSettings(title=self.title_entry.value(), show_title=bool(self.show_title.get()),
                             xlabel=self.xlabel.value(), ylabel=self.ylabel.value(),
                             logx=bool(self.logx.get()), logy=bool(self.logy.get()), legend=legend,
                             xlim=self.view_limits.get("x"), ylim=self.view_limits.get("y"))

    def collect_style(self) -> StyleSettings:
        theme = {lbl: val for val, lbl in self.styles}.get(self.style_var.get(), "studio")
        return StyleSettings(theme=theme, palette=self.palette_var.get(), context=self.context_var.get())

    # --------------------------------------------------------------- plot --
    def changed(self, *_, delay=450):
        self.update_visibility()
        if self.has_plotted and self.auto_var.get():
            if self._after:
                self.after_cancel(self._after)
            self._after = self.after(delay, lambda: self.plot(auto=True))

    # ------------------------------------------------------- axis ranges --
    def clear_limits(self, which=None):
        for key in (("x", "y") if which is None else (which,)):
            self.view_limits[key] = None

    def set_view_limit(self, which, values):
        self.set_view_limits({which: values})

    def set_view_limits(self, changes: dict):
        """A slider was let go or the plot was moved / zoomed with the mouse: write
        ax.set_xlim / ax.set_ylim into the code (the plot itself is already showing it)."""
        changes = {k: v for k, v in changes.items() if self.view_limits.get(k) != v}
        if not changes:
            return
        self.view_limits.update(changes)
        last = self.last_request
        if not (self.graph and self.ds and self.has_plotted and last and last[0] == self.graph.id):
            return
        # the plot on screen + the new range (other changes not plotted yet stay out of the code)
        labels = dataclasses.replace(last[5], xlim=self.view_limits.get("x"), ylim=self.view_limits.get("y"))
        request = last[:5] + (labels,)
        try:
            built = build_plot(self.graph, self.ds, *request[1:])
        except PlotError:
            return
        self.last_request = request
        self.code_view.set_code(built.script)
        self.last_built = built
        self.last_signature = (id(self.ds), repr(request))
        parts = []
        for which in ("x", "y"):
            if which not in changes:
                continue
            values = changes[which]
            parts.append(f"{which.upper()}: full range" if values is None else
                         f"{which.upper()}: {fmt_limit(values[0])} to {fmt_limit(values[1])}")
        added = any(v is not None for v in changes.values())
        self.message("  ·  ".join(parts) + ("  ·  range written into the code" if added else
                                            "  ·  range removed from the code"), "ok")

    def redraw(self):
        """Draw the last plot again from its code (after switching the look or the graph paper)."""
        if self.last_built is None or self.plot_view.fig is None:
            return
        self.app.busy(True)
        try:
            fig, warns, seconds = run_plot(self.last_built)
        except PlotRunError:
            return
        finally:
            self.app.busy(False)
        self.plot_view.show_figure(fig, self.last_built, warns, seconds)

    def message(self, text, kind="muted"):
        style = {"muted": "Panel.Muted.TLabel", "error": "Error.TLabel", "ok": "Ok.TLabel"}[kind]
        self.msg.configure(text=text, style=style)

    def plot(self, *_, auto=False):
        if self._after:
            self.after_cancel(self._after)
            self._after = None
        if not (self.graph and self.ds):
            return
        self.app.cfg["style_open"] = not self.sec_style.collapsed
        request = (self.graph.id, self.collect_selection(), self.collect_options(), self.collect_rows(),
                   self.collect_style(), self.collect_labels())
        signature = (id(self.ds), repr(request))
        if auto and signature == self.last_signature:
            return  # nothing changed since the last plot
        self.last_signature = signature
        try:
            built = build_plot(self.graph, self.ds, *request[1:])
        except PlotError as exc:
            text = str(exc)
            empty = [r.role.label for r in self.roles.values() if r.empty and r.role.required]
            if empty and not self.show_all.get():
                text += ("\n\nThis file has no column of the right type for " +
                         ", ".join(f"“{e}”" for e in empty) +
                         ". Turn on 'Show all' (next to Columns) to pick any column, or choose another graph.")
            self.message(text.split("\n")[0], "error")
            self.plot_view.show_problem("Almost there", text)
            self.nb.select(self.plot_view)
            return
        self.code_view.set_code(built.script)
        self.app.busy(True)
        try:
            fig, warns, seconds = run_plot(built)
            if not auto:        # count the plots the user asked for, not every automatic redraw
                activity.record_plot(self.app.cfg, self.graph.id, graph_name=self.graph.name,
                                     dataset_name=self.ds.name, variables=len(self.ds.columns))
                settings.save(self.app.cfg)
        except PlotRunError as exc:
            self.message("The plotting code raised an error. The Plot tab shows where.", "error")
            self.plot_view.show_problem("Couldn't draw this plot", exc.message, exc.line, exc.details)
            self.nb.select(self.plot_view)
            return
        finally:
            self.app.busy(False)
        self.last_built = built
        self.last_request = request
        self.has_plotted = True
        self.message("Drawing…")
        self.plot_view.show_figure(fig, built, warns, seconds)
        self.nb.select(self.plot_view)

    def popout(self):
        if self.last_built is not None:
            PopoutWindow(self.app, self.last_built)


class RoleRow:
    """One column slot (e.g. 'X axis') in the Columns section."""

    def __init__(self, parent, page: WorkspacePage, role, columns, value):
        t, px = page.app.theme, page.app.theme.px
        self.role, self.page = role, page
        frame = tk.Frame(parent, background=C["panel"])
        frame.pack(fill="x", pady=(0, px(14)))
        top = tk.Frame(frame, background=C["panel"])
        top.pack(fill="x")
        tk.Label(top, text=role.label, background=C["panel"], foreground=C["text"], font=t.f["bold"]).pack(
            side="left", padx=(t.m, 0))
        if role.required:
            star = tk.Label(top, text="*", background=C["panel"], foreground=C["accent"], font=t.f["bold"])
            star.pack(side="left", padx=(px(2), 0))
            Tooltip(star, "Required")
        if columns:
            self.suggest_btn = ttk.Button(top, text="Suggest", style="Link.TButton", compound="left",
                                          image=t.icon_states("sparkle", 14, normal="accent", active="accent_hover"),
                                          command=self.open_suggestions)
            self.suggest_btn.pack(side="right")
            Tooltip(self.suggest_btn, f"Recommended columns for “{role.label}”, best first, with the reason.")
        hint = role.hint or ACCEPTS_TEXT.get(role.accepts, "")
        self.empty = not columns
        if self.empty:
            needs = ACCEPTS_TEXT.get(role.accepts, "another type")
            hint = (f"No suitable column in this file (needs {needs}). Turn on 'Show all' to use any column."
                    if role.required else f"optional · this file has no {needs}")
        tk.Label(frame, text=hint, background=C["panel"],
                 foreground=C["danger"] if (self.empty and role.required) else C["muted"],
                 font=t.f["small"], anchor="w", justify="left", wraplength=px(310)).pack(fill="x", padx=(t.m, 0))
        self.touched = False   # True once the user picks something here (remembered across graphs)
        if role.multi:
            self.widget = MultiPicker(frame, t, on_change=self._user_change, height=min(8, max(3, len(columns))))
            self.widget.set_items(columns, value or [])
            self.widget.pack(fill="x", pady=(px(4), 0))
        else:
            values = ([NONE] if not role.required else []) + columns
            self.var = tk.StringVar(value=value if value in columns else (NONE if not role.required else ""))
            self.widget = ttk.Combobox(frame, textvariable=self.var, values=values, state="readonly", height=18)
            self.widget.pack(fill="x", pady=(px(4), 0))
            self.widget.bind("<<ComboboxSelected>>", self._user_change)

    def _user_change(self, *_):
        self.touched = True
        self.page.clear_limits()    # other columns: the zoomed ranges no longer apply
        self.page.changed()

    def get(self):
        if self.role.multi:
            return self.widget.get()
        value = self.var.get()
        return None if value in ("", NONE) else value

    def apply(self, value):
        """Put a suggested choice in (without plotting)."""
        if self.role.multi:
            items = self.widget.items
            self.widget.set_items(items, [v for v in (value or []) if v in items])
        else:
            values = list(self.widget.cget("values"))
            if value in values:
                self.var.set(value)
            elif not self.role.required:
                self.var.set(NONE)
        self.touched = True

    # suggestions menu ----------------------------------------------------
    def open_suggestions(self):
        page = self.page
        if not (page.graph and page.ds):
            return
        t = page.app.theme
        target = page.current_target()
        try:
            picks = recommend.rank(page.graph, self.role, page.ds, page.collect_selection(), target,
                                   show_all=page.show_all.get())
        except Exception as exc:  # noqa: BLE001 - a suggestion must never break the window
            page.message(f"Couldn't rank the columns: {type(exc).__name__}: {exc}", "error")
            return
        old = getattr(self, "_menu", None)
        if old is not None:
            try:
                old.destroy()
            except tk.TclError:
                pass
        menu = self._menu = t.menu(self.suggest_btn)
        head = f"Best for “{self.role.label}”"
        if target:
            head += f"  ·  ranked by link with {recommend.short(target, 22)}"
        menu.add_command(label=head, state="disabled")
        details = {}
        self._menu_vars = []
        if not picks:
            menu.add_command(label="Nothing fits here (turn on 'Show all' for any column)", state="disabled")
        elif self.role.multi:
            n = recommend.how_many(page.graph, self.role, len(picks))
            top = [p.column for p in picks[:n]]
            label = f"Use the top {len(top)}:  " + ", ".join(recommend.short(c, 14) for c in top[:3]) + \
                ("…" if len(top) > 3 else "")
            menu.add_command(label=label if len(top) > 1 else f"Use {top[0]}", command=lambda: self._use(top))
            menu.add_separator()
            current = set(self.get() or [])
            for p in picks:
                var = tk.BooleanVar(master=menu, value=p.column in current)
                self._menu_vars.append(var)
                menu.add_checkbutton(label=p.column, accelerator=p.reason, variable=var,
                                     command=lambda c=p.column, v=var: self._toggle(c, v.get()))
                details[menu.index("end")] = p.detail
        else:
            for p in picks:
                menu.add_radiobutton(label=p.column, accelerator=p.reason, value=p.column, variable=self.var,
                                     command=self._user_change)
                details[menu.index("end")] = p.detail
            if not self.role.required:
                menu.add_separator()
                menu.add_radiobutton(label=NONE, value=NONE, variable=self.var, command=self._user_change)

        def hover(_e=None):
            try:
                idx = menu.index("active")
            except tk.TclError:
                idx = None
            if idx is not None and details.get(idx):
                page.message(details[idx])

        menu.bind("<<MenuSelect>>", hover)
        x = self.suggest_btn.winfo_rootx()
        y = self.suggest_btn.winfo_rooty() + self.suggest_btn.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _use(self, columns):
        self.widget.set_items(self.widget.items, columns)
        self._user_change()

    def _toggle(self, column, on):
        chosen = [c for c in self.get() if c != column]
        if on:
            chosen.append(column)
        self.widget.set_items(self.widget.items, chosen)
        self._user_change()


class OptionRow:
    """One graph option (bins, colormap, ...) in the Options section."""

    def __init__(self, parent, page: WorkspacePage, option, value, row):
        t, px = page.app.theme, page.app.theme.px
        self.option, self.page = option, page
        self.widgets = []
        if option.kind == "bool":
            self.var = tk.BooleanVar(value=bool(value))
            w = ttk.Checkbutton(parent, text=option.label, variable=self.var, command=page.changed)
            w.grid(row=row, column=0, columnspan=2, sticky="w", pady=px(2))
            self.widgets = [w]
            if option.hint:
                Tooltip(w, option.hint)
        else:
            lbl = ttk.Label(parent, text=option.label, style="Panel.TLabel", wraplength=px(140), justify="left")
            lbl.grid(row=row, column=0, sticky="w", padx=(t.m, 0), pady=px(1))
            if option.kind == "choice":
                labels = [lb for _, lb in option.choices]
                self.lookup = {lb: v for v, lb in option.choices}
                current = next((lb for v, lb in option.choices if v == value), labels[0])
                self.var = tk.StringVar(value=current)
                w = ttk.Combobox(parent, textvariable=self.var, values=labels, state="readonly", height=16, width=18)
                if option.key == "orient":   # X and Y swap places: the zoomed ranges no longer apply
                    w.bind("<<ComboboxSelected>>", lambda e: (page.clear_limits(), page.changed()))
                else:
                    w.bind("<<ComboboxSelected>>", page.changed)
            elif option.kind in ("int", "float"):
                self.var = tk.StringVar(value=str(value))
                w = tk.Frame(parent, background=C["panel"])
                spin = ttk.Spinbox(w, textvariable=self.var, from_=option.min, to=option.max, increment=option.step,
                                   width=6, command=page.changed)
                spin.bind("<Return>", page.changed)
                spin.bind("<FocusOut>", page.changed)
                spin.pack(side="right")
                # the same number with a ball slider, for the mouse
                self._syncing = False
                self.slider = RangeSlider(w, t, two=False, on_change=self._slid,
                                          on_release=lambda lo, hi: page.changed(delay=60),
                                          on_reset=self._slider_reset)
                self.slider.pack(side="left", fill="x", expand=True, padx=(0, px(2)))
                self.var.trace_add("write", lambda *_: self._to_slider())
                self._to_slider()
                if option.hint:
                    Tooltip(spin, option.hint)
            else:
                self.var = tk.StringVar(value=str(value))
                w = ttk.Entry(parent, textvariable=self.var, width=18)
                w.bind("<Return>", page.changed)
                w.bind("<FocusOut>", page.changed)
            w.grid(row=row, column=1, sticky="ew", padx=(px(10), 0), pady=px(1))
            self.widgets = [lbl, w]
            if option.hint:
                Tooltip(lbl, option.hint)
                if option.kind not in ("int", "float"):
                    Tooltip(w, option.hint)

    # ball slider <-> number ---------------------------------------------
    def _curve(self):
        o = self.option
        span_steps = (o.max - o.min) / (o.step or 1)
        return 2.0 if o.min >= 0 and span_steps > 150 else 1.0   # finer steps at the low end of big ranges

    def _value_at(self, t):
        o = self.option
        v = o.min + (o.max - o.min) * (t ** self._curve())
        step = max(1, int(round(o.step))) if o.kind == "int" else (o.step or 0.01)
        v = o.min + round((v - o.min) / step) * step
        v = min(max(v, o.min), o.max)
        if o.kind == "int":
            return int(round(v))
        decimals = max(0, -int(math.floor(math.log10(step)))) if step < 1 else 1
        return round(v, decimals + 1)

    def _slid(self, _lo, t):
        value = self._value_at(t)
        text = str(value)
        if text != self.var.get():
            self._syncing = True
            try:
                self.var.set(text)
            finally:
                self._syncing = False
            self.page.message(f"{self.option.label}: {text}")
            self.page.changed()

    def _slider_reset(self):
        self.var.set(str(self.option.default))
        self.page.changed(delay=60)

    def _to_slider(self):
        if self._syncing:
            return
        o = self.option
        try:
            v = float(self.var.get())
        except (ValueError, tk.TclError):
            return
        t = (min(max(v, o.min), o.max) - o.min) / ((o.max - o.min) or 1)
        self.slider.set(hi=t ** (1 / self._curve()))

    def show(self, visible: bool):
        for w in self.widgets:
            w.grid() if visible else w.grid_remove()

    def get(self):
        o = self.option
        if o.kind == "bool":
            return bool(self.var.get())
        if o.kind == "choice":
            return self.lookup.get(self.var.get(), o.default)
        if o.kind in ("int", "float"):
            try:
                v = float(self.var.get())
            except (ValueError, tk.TclError):
                return o.default
            v = min(max(v, o.min), o.max)
            return int(round(v)) if o.kind == "int" else v
        return self.var.get()


# =========================================================================== #
# Right-hand tabs
# =========================================================================== #

class Toolbar(NavigationToolbar2Tk):
    """matplotlib's navigation toolbar, kept out of sight: its Home / Back / Forward / Pan / Zoom
    are driven by our own rounded buttons (NavButtons)."""
    toolitems = [t for t in NavigationToolbar2Tk.toolitems if t[0] in ("Home", "Back", "Forward", "Pan", "Zoom")]

    def __init__(self, canvas, window):
        super().__init__(canvas, window, pack_toolbar=False)
        self.configure(width=1, height=1)   # newer matplotlib sizes the toolbar to the figure width

    def set_message(self, s):   # the coordinates are shown by the value ball instead
        pass


class NavButtons:
    """Reset / back / forward and the Pan and Box-zoom tools, as rounded icon buttons."""

    def __init__(self, parent, theme, get_toolbar, style_prefix=""):
        self.get_toolbar = get_toolbar
        self.buttons = {}
        px = theme.px
        for key, icon, tip in (("home", "home", "Reset the view: show everything (or double-click the plot)"),
                               ("back", "back", "Back to the previous view"),
                               ("forward", "forward", "Forward to the next view")):
            b = ttk.Button(parent, style=f"{style_prefix}Icon.TButton", image=theme.icon_states(icon, 18),
                           command=lambda k=key: self._call(k))
            b.pack(side="left")
            Tooltip(b, tip)
            self.buttons[key] = b
        tk.Frame(parent, background=C["border"], width=max(1, px(1)), height=px(20)).pack(side="left", padx=px(6))
        for key, icon, tip in (("pan", "move", "Pan tool: drag to move the view. Click again to turn it off."),
                               ("zoom", "zoom", "Box zoom tool: drag a rectangle to zoom into it. Click again to "
                                                "turn it off.")):
            b = ttk.Button(parent, style=f"{style_prefix}Icon.TButton",
                           image=theme.icon_states(icon, 18, selected="accent"), command=lambda k=key: self._call(k))
            b.pack(side="left")
            Tooltip(b, tip)
            self.buttons[key] = b
        self.set_enabled(False)

    def _call(self, key):
        tb = self.get_toolbar()
        if tb is None:
            return
        getattr(tb, key)()
        self.sync()

    def sync(self):
        tb = self.get_toolbar()
        mode = str(getattr(tb, "mode", "") or "") if tb is not None else ""
        for key, wanted in (("pan", "pan/zoom"), ("zoom", "zoom rect")):
            try:
                self.buttons[key].state(["selected" if mode == wanted else "!selected"])
            except tk.TclError:
                pass

    def set_enabled(self, on: bool):
        for b in self.buttons.values():
            b.state(["!disabled" if on else "disabled"])
        if not on:
            for key in ("pan", "zoom"):
                self.buttons[key].state(["!selected"])


def tracker_colors():
    return {"box": C["panel"], "border": C["border_strong"], "text": C["text"], "ring": "#ffffff"}


class PlotView(tk.Frame):
    def __init__(self, master, page: WorkspacePage):
        super().__init__(master, background=C["panel"])
        self.page, self.app = page, page.app
        t, px = self.app.theme, self.app.theme.px
        self.fig = None
        self.canvas = None
        self.toolbar = None
        self.tracker = None
        self.zoom = None              # automatic X/Y ranges of the plot (for the range sliders)
        self._sliding = False
        self._ax_cids = []
        self.natural = (800, 600)
        self.placeholder_graph = None

        bar = tk.Frame(self, background=C["panel"])
        bar.pack(fill="x", padx=px(10), pady=(px(8), px(2)))
        self.actions = tk.Frame(bar, background=C["panel"])
        self.actions.pack(side="right")          # packed first so it always keeps its space
        self.nav_holder = tk.Frame(bar, background=C["panel"])
        self.nav_holder.pack(side="left")
        self._hidden = tk.Frame(self)            # parent of matplotlib's own (hidden) toolbar
        self.navbuttons = NavButtons(self.nav_holder, t, lambda: self.toolbar)
        self.fit = tk.BooleanVar(value=bool(self.app.cfg.get("fit_window", True)))
        self.values_var = tk.BooleanVar(value=bool(self.app.cfg.get("show_values", True)))
        self.sliders_var = tk.BooleanVar(value=bool(self.app.cfg.get("range_sliders", True)))
        self.mouse_var = tk.BooleanVar(value=bool(self.app.cfg.get("mouse_nav", True)))
        self.paper_var = tk.BooleanVar(value=self.app.theme.dark)
        self.nav = None
        self._wheel_jobs = {}

        # View ▾ · Save ▾ · Copy code · Pop out
        view = ttk.Menubutton(self.actions, text="View", image=t.icon("sliders", "muted", 16), compound="left",
                              style="Ghost.TMenubutton")
        menu = t.menu(view)
        menu.add_checkbutton(label="Fit the plot to the window", variable=self.fit, command=self._resize)
        menu.add_separator()
        menu.add_checkbutton(label="Move and zoom with the mouse", variable=self.mouse_var,
                             command=lambda: self.page.message(
                                 "Mouse: drag to move, scroll to zoom (Shift: X only, Ctrl: Y only), right-drag "
                                 "for a zoom box, double-click to reset." if self.mouse_var.get() else
                                 "Mouse move and zoom is off. The Pan and Box zoom tools still work."))
        menu.add_command(label="      drag · scroll · right-drag · double-click", state="disabled")
        menu.add_checkbutton(label="Value ball under the mouse", variable=self.values_var,
                             command=self._values_toggled)
        menu.add_checkbutton(label="X / Y range sliders", variable=self.sliders_var, command=self._setup_sliders)
        menu.add_separator()
        menu.add_checkbutton(label="Dark graph paper", variable=self.paper_var, command=self.page.redraw)
        view["menu"] = menu
        view.pack(side="left", padx=(0, px(4)))
        Tooltip(view, "Fit to window, mouse move and zoom, value ball, range sliders, graph paper")

        self.dpi = tk.StringVar(value=self.app.cfg.get("dpi", "150 dpi"))
        save = ttk.Menubutton(self.actions, text="Save", image=t.icon("download", "muted", 16), compound="left",
                              style="TMenubutton")
        smenu = t.menu(save)
        smenu.add_command(label="Save image…", accelerator="Ctrl+S", command=self.save_image)
        smenu.add_separator()
        smenu.add_command(label="Resolution of PNG and JPG files", state="disabled")
        for value, label in (("100 dpi", "100 dpi  (screen)"), ("150 dpi", "150 dpi"), ("200 dpi", "200 dpi"),
                             ("300 dpi", "300 dpi  (print)")):
            smenu.add_radiobutton(label=label, value=value, variable=self.dpi)
        save["menu"] = smenu
        save.pack(side="left", padx=(0, px(4)))
        Tooltip(save, "Save the plot as PNG, SVG, PDF or JPG (Ctrl+S) and pick the resolution")
        self.copy_btn = ttk.Button(self.actions, text="Copy code", image=t.icon_states("copy", 16), compound="left",
                                   style="Small.TButton", command=lambda: page.code_view.copy(self.copy_btn))
        self.copy_btn.pack(side="left", padx=(0, px(4)))
        Tooltip(self.copy_btn, "Copy the code that drew this plot")
        pop = ttk.Button(self.actions, style="Icon.TButton", image=t.icon_states("external", 18), command=page.popout)
        pop.pack(side="left")
        Tooltip(pop, "Open the plot in its own window")

        self.body = tk.Frame(self, background=C["panel"])
        self.body.pack(fill="both", expand=True, padx=px(10))
        self.host_frame = tk.Frame(self.body, background=C["panel"])
        self.host = tk.Canvas(self.host_frame, background=C["panel"], highlightthickness=0, xscrollincrement=1,
                              yscrollincrement=1)
        self.vbar = ttk.Scrollbar(self.host_frame, orient="vertical", command=self.host.yview)
        self.hbar = ttk.Scrollbar(self.host_frame, orient="horizontal", command=self.host.xview)
        self.host.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)
        self.host.smooth = SmoothScroller(self.host)
        # range sliders: Y on the left of the plot, X underneath (lined up with the axes)
        self.ysl = RangeSlider(self.host_frame, t, orient="vertical", two=True,
                               on_change=lambda lo, hi: self._slide("y", lo, hi),
                               on_release=lambda lo, hi: self._commit("y", lo, hi),
                               on_reset=lambda: self._reset_axis("y"))
        self.xsl = RangeSlider(self.host_frame, t, orient="horizontal", two=True,
                               on_change=lambda lo, hi: self._slide("x", lo, hi),
                               on_release=lambda lo, hi: self._commit("x", lo, hi),
                               on_reset=lambda: self._reset_axis("x"))
        self.xsl.wheel_handler = lambda steps: self._slider_wheel("x", steps)   # wheel over a slider zooms it
        self.ysl.wheel_handler = lambda steps: self._slider_wheel("y", steps)
        for sl, axis in ((self.xsl, "X"), (self.ysl, "Y")):
            Tooltip(sl, f"Drag the balls to zoom the {axis} axis, or the bar between them to move. "
                        "Scroll here to zoom, double-click to reset.")
        self.host.grid(row=0, column=1, sticky="nsew")
        self.host_frame.rowconfigure(0, weight=1)
        self.host_frame.columnconfigure(1, weight=1)
        self.host.scroll_target = True
        self.host.xscroll_target = True
        self.host.bind("<Configure>", lambda e: self._resize())
        self.other = None

        self.notes = tk.Label(self, background=C["panel"], foreground=C["muted"], font=t.f["small"], justify="left",
                              anchor="w")
        self.notes.pack(fill="x", padx=px(16), pady=(px(4), px(10)))
        self.bind("<Configure>", lambda e: self.notes.configure(wraplength=max(200, e.width - px(40))), add="+")

    # -------------------------------------------------------------------
    def on_theme(self):
        if self.fig is None and self.placeholder_graph is not None and self.other is not None:
            self.show_placeholder(self.placeholder_graph)
        elif self.fig is not None:
            self.page.redraw()

    def _swap(self, widget):
        for w in self.body.winfo_children():
            w.pack_forget()
        widget.pack(fill="both", expand=True)

    def show_placeholder(self, graph):
        t, px = self.app.theme, self.app.theme.px
        self._drop_figure()
        self.placeholder_graph = graph
        if self.other is not None:
            self.other.destroy()
        frame = tk.Frame(self.body, background=C["panel"])
        self.other = frame
        inner = tk.Frame(frame, background=C["panel"])
        inner.place(relx=0.5, rely=0.42, anchor="center")
        img = self.app.thumbs.get(graph.id, large=True)
        if img:
            tk.Label(inner, image=img, background=C["panel"]).pack()
        tk.Label(inner, text=graph.name, background=C["panel"], foreground=C["text"], font=t.f["h2"]).pack(
            pady=(px(16), px(2)))
        tk.Label(inner, text=graph.blurb, background=C["panel"], foreground=C["muted"]).pack()
        if self.page.ds is None:
            msg = "Load a CSV first."
        else:
            msg = "The columns on the left are filled in with suggestions. Check them, then press Plot."
        tk.Label(inner, text=msg, background=C["panel"], foreground=C["text"], font=t.f["medium"]).pack(
            pady=(px(18), px(8)))
        if self.page.ds is not None:
            ttk.Button(inner, text="Plot", image=t.icon("play", "on_accent", 14), compound="right",
                       style="Accent.TButton", command=self.page.plot).pack()
            tk.Label(inner, text="or press Ctrl+Enter", background=C["panel"], foreground=C["faint"],
                     font=t.f["small"]).pack(pady=(px(6), 0))
        self._swap(frame)
        self.notes.configure(text="")

    def show_problem(self, title, message, line="", details=""):
        t, px = self.app.theme, self.app.theme.px
        self._drop_figure()
        self.placeholder_graph = None
        if self.other is not None:
            self.other.destroy()
        frame = tk.Frame(self.body, background=C["panel"])
        self.other = frame
        bg = C["danger_soft"] if details else C["warn_soft"]
        box = ttk.Frame(frame, style="Danger.TFrame" if details else "Warn.TFrame", padding=(px(20), px(16)))
        box.pack(fill="x", pady=(px(24), 0), padx=px(24))
        inner = tk.Frame(box, background=bg)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, background=bg, foreground=C["danger"] if details else C["warn"],
                 font=t.f["h3"]).pack(anchor="w")
        tk.Label(inner, text=message, background=bg, foreground=C["text"], justify="left", anchor="w",
                 wraplength=px(760)).pack(anchor="w", pady=(px(8), 0))
        if line:
            tk.Label(inner, text="In this line of the generated code:", background=bg, foreground=C["muted"],
                     font=t.f["small"]).pack(anchor="w", pady=(px(12), px(4)))
            well = ttk.Frame(inner, style="Code.TFrame", padding=px(3))
            well.pack(anchor="w", fill="x")
            code = tk.Label(well, text=line, background=CODE["bg"], foreground=CODE["fg"], font=t.f["mono"],
                            anchor="w", justify="left", padx=px(8), pady=px(4), wraplength=px(740))
            code.fixed_colors = True
            code.pack(anchor="w", fill="x")
        if details:
            holder = ttk.Frame(frame, style="Code.TFrame", padding=px(4))
            text = tk.Text(holder, height=14, font=t.f["mono"], background=CODE["bg"], foreground=CODE["fg"],
                           relief="flat", wrap="none", borderwidth=0, highlightthickness=0, padx=px(8), pady=px(6))
            text.fixed_colors = True
            text.insert("1.0", details)
            text.configure(state="disabled")
            smooth_text(text, t)

            def toggle():
                if holder.winfo_ismapped():
                    holder.pack_forget()
                    toggle_btn.configure(text="Show technical details", image=t.icon_states("chevron_down", 16))
                else:
                    holder.pack(fill="both", expand=True, padx=px(24), pady=(px(8), px(12)))
                    text.pack(fill="both", expand=True)
                    toggle_btn.configure(text="Hide technical details", image=t.icon_states("chevron_up", 16))
            toggle_btn = ttk.Button(frame, text="Show technical details", image=t.icon_states("chevron_down", 16),
                                    compound="right", style="Ghost.TButton", command=toggle)
            toggle_btn.pack(anchor="w", padx=px(20), pady=(px(10), 0))
        self._swap(frame)
        self.notes.configure(text="")

    def _drop_figure(self):
        if self.tracker is not None:
            self.tracker.disconnect()
            self.tracker = None
        if self.nav is not None:
            self.nav.disconnect()
            self.nav = None
        self._disconnect_axes()
        if self.canvas is not None:
            release_canvas(self.canvas)
        if self.toolbar is not None:
            self.toolbar.destroy()
        self.host.delete("all")
        self.canvas = self.toolbar = self.fig = None
        self.zoom = None
        self.xsl.grid_remove()
        self.ysl.grid_remove()
        self.navbuttons.set_enabled(False)

    def show_figure(self, fig, built, warns, seconds):
        self._drop_figure()
        self.placeholder_graph = None
        if self.other is not None:
            self.other.destroy()
            self.other = None
        apply_paper(fig, self.paper_var.get(), self.app.theme.ink)
        self.fig = fig
        self.inches = tuple(fig.get_size_inches())
        self.base_dpi = fig.dpi
        self.natural = (int(self.inches[0] * fig.dpi), int(self.inches[1] * fig.dpi))
        # Figures with a layout engine (our own plots) are stretched to fill the window.
        # seaborn grids (pair/joint/facet) keep their layout and are zoomed like a picture instead.
        engine = type(fig.get_layout_engine()).__name__
        self.zoom_mode = engine not in ("ConstrainedLayoutEngine", "TightLayoutEngine")
        canvas = self.canvas = FigureCanvasTkAgg(fig, master=self.host)
        widget = self.canvas.get_tk_widget()
        widget.configure(background=C["panel"], highlightthickness=0)
        # matplotlib re-applies the screen's pixel ratio when the canvas appears; size it again afterwards
        widget.bind("<Map>", lambda e: self.after_idle(self._resize), add="+")
        self.win = self.host.create_window(0, 0, window=widget, anchor="nw")
        self.toolbar = Toolbar(self.canvas, self._hidden)
        self.navbuttons.set_enabled(True)
        self.navbuttons.sync()
        self.tracker = PointTracker(canvas, tracker_colors, enabled=self.values_var.get)
        z = getattr(fig, "_studio_zoom", None)
        self.nav = Navigator(canvas, toolbar=self.toolbar,
                             natural={id(z["ax"]): {"x": z["x"], "y": z["y"]}} if z else None,
                             on_done=self._nav_done, on_reset=self._nav_reset, scroll=self._host_scroll,
                             enabled=self.mouse_var.get, on_status=self.page.message)
        canvas.mpl_connect("draw_event", lambda e: self._align_sliders())
        started = time.perf_counter()
        rows = len(built.df)
        tips = []
        if "3d" in built.plot_code:
            tips.append("drag the plot to rotate it")
        if self.nav.specs and self.mouse_var.get():
            tips.append("drag to move · scroll to zoom · double-click to reset")
        if getattr(fig, "_studio_zoom", None) and self.sliders_var.get():
            tips.append("or use the sliders beside the axes")
        if self.values_var.get():
            tips.append("hover a point to read its value")
        hint = "  ·  ".join(tips) if tips else "use the tools above the plot to move and zoom"
        extra = [f"•  {n}" for n in built.notes] + [f"•  matplotlib/seaborn says: {msg}" for msg in warns]

        def drawn(_event=None):
            canvas.mpl_disconnect(cid)
            if canvas is not self.canvas:
                return
            total = seconds + time.perf_counter() - started
            self.notes.configure(text="\n".join([f"{rows:,} rows  ·  {total:.1f} s  ·  {hint}"] + extra))
            note, self.page.pending_note = self.page.pending_note, None
            self.page.message((note + "  ·  " if note else "") + f"Plotted {rows:,} rows in {total:.1f} s.", "ok")

        cid = canvas.mpl_connect("draw_event", drawn)
        self.notes.configure(text="\n".join([f"{rows:,} rows  ·  drawing…"] + extra))
        self._swap(self.host_frame)
        self._setup_sliders(draw=False)
        self.update_idletasks()
        self._resize()
        self.canvas.draw_idle()

    # ------------------------------------------------------- mouse move / zoom --
    def _nav_done(self, ax):
        """The plot was moved or zoomed with the mouse: the main plot's range goes into the code."""
        z = self.zoom or getattr(self.fig, "_studio_zoom", None)
        if not z or ax is not z["ax"]:
            return
        changes = {}
        for which in ("x", "y"):
            spec = z.get(which)
            if spec:
                lim = ax.get_xlim() if which == "x" else ax.get_ylim()
                changes[which] = limit_values(spec, *fracs(spec, lim))
        self.page.set_view_limits(changes)

    def _nav_reset(self):
        if getattr(self.fig, "_studio_zoom", None):
            self.page.set_view_limits({"x": None, "y": None})

    def _host_scroll(self, step, horizontal, probe=False):
        """Scroll the figure in the window when it is bigger than the window (Fit to window off)."""
        if self.fit.get():
            return False
        first, last = self.host.xview() if horizontal else self.host.yview()
        can = first > 0 or last < 1
        if probe or not can:
            return can
        pixels = -math.copysign(max(1.0, abs(step)), step) * self.app.theme.px(48)
        if horizontal:
            self.host.xview_scroll(int(pixels), "units")
        else:
            self.host.smooth.scroll(pixels)
        return True

    def _slider_wheel(self, which, steps):
        """Mouse wheel over a range slider: zoom that axis around the middle of what is shown."""
        if not self.zoom or not self.zoom.get(which) or self.canvas is None:
            return
        sl = self.xsl if which == "x" else self.ysl
        lo, hi = zoom_fracs(sl.lo, sl.hi, (sl.lo + sl.hi) / 2, WHEEL_ZOOM ** (-steps))
        sl.set(lo, hi)
        self._slide(which, lo, hi)
        job = self._wheel_jobs.pop(which, None)
        if job:
            self.after_cancel(job)
        self._wheel_jobs[which] = self.after(400, lambda: (self._wheel_jobs.pop(which, None),
                                                           self._commit(which, sl.lo, sl.hi)))

    def _values_toggled(self):
        if self.tracker is not None and not self.values_var.get():
            self.tracker.hide()

    # ------------------------------------------------------------- range sliders --
    def _disconnect_axes(self):
        for ax, cid in self._ax_cids:
            try:
                ax.callbacks.disconnect(cid)
            except Exception:  # noqa: BLE001
                pass
        self._ax_cids = []

    def _setup_sliders(self, draw=True):
        self._disconnect_axes()
        z = getattr(self.fig, "_studio_zoom", None) if (self.fig is not None and self.sliders_var.get()) else None
        self.zoom = z
        for which, sl, place in (("x", self.xsl, dict(row=2, column=1, sticky="ew")),
                                 ("y", self.ysl, dict(row=0, column=0, sticky="ns"))):
            spec = z.get(which) if z else None
            if spec is None:
                sl.grid_remove()
                continue
            sl.grid(**place)
            ax = z["ax"]
            sl.set(*fracs(spec, ax.get_xlim() if which == "x" else ax.get_ylim()))
            cid = ax.callbacks.connect(f"{which}lim_changed", lambda _ax, w=which: self._sync_slider(w))
            self._ax_cids.append((ax, cid))
        if draw:
            self.after_idle(self._resize)

    def _sync_slider(self, which):
        """The view changed (toolbar zoom / pan / Home): move the balls to match."""
        if self._sliding or not self.zoom or not self.zoom.get(which):
            return
        ax = self.zoom["ax"]
        lim = ax.get_xlim() if which == "x" else ax.get_ylim()
        (self.xsl if which == "x" else self.ysl).set(*fracs(self.zoom[which], lim))

    def _set_limits(self, which, lo, hi):
        spec, ax = self.zoom[which], self.zoom["ax"]
        if is_full(lo, hi):
            a, b = spec["natural"]
        else:
            a, b = to_value(spec, lo), to_value(spec, hi)
        self._sliding = True
        try:
            (ax.set_xlim if which == "x" else ax.set_ylim)(a, b)
        finally:
            self._sliding = False
        if self.tracker is not None:
            self.tracker.hide()
        self.canvas.draw_idle()

    def _slide(self, which, lo, hi):
        if not self.zoom or not self.zoom.get(which) or self.canvas is None:
            return
        self._set_limits(which, lo, hi)
        values = limit_values(self.zoom[which], lo, hi)
        if values is None:
            self.page.message(f"{which.upper()} axis: everything")
        else:
            self.page.message(f"{which.upper()} axis: {fmt_limit(values[0])} to {fmt_limit(values[1])}")

    def _commit(self, which, lo, hi):
        if not self.zoom or not self.zoom.get(which) or self.canvas is None:
            return
        self._set_limits(which, lo, hi)
        self.page.set_view_limit(which, limit_values(self.zoom[which], lo, hi))

    def _reset_axis(self, which):
        if not self.zoom or not self.zoom.get(which) or self.canvas is None:
            return
        (self.xsl if which == "x" else self.ysl).set(0.0, 1.0)
        self._commit(which, 0.0, 1.0)

    def _align_sliders(self):
        """Line the slider tracks up with the plot's axes (called after every draw)."""
        if not self.zoom or self.canvas is None:
            return
        try:
            ax = self.zoom["ax"]
            bb = ax.get_window_extent()
            fw, fh = self.fig.bbox.width, self.fig.bbox.height
            widget = self.canvas.get_tk_widget()
            ww, wh = widget.winfo_width(), widget.winfo_height()
            x0 = self.host.coords(self.win)[0] - self.host.canvasx(0)
            y0 = -self.host.canvasy(0)
        except (tk.TclError, IndexError, AttributeError):
            return
        if fw <= 0 or fh <= 0 or ww <= 1 or wh <= 1:
            return
        self.xsl.set_span(x0 + bb.x0 / fw * ww, x0 + bb.x1 / fw * ww)
        self.ysl.set_span(y0 + (1 - bb.y1 / fh) * wh, y0 + (1 - bb.y0 / fh) * wh)

    # -------------------------------------------------------------------
    def _resize(self):
        if self.canvas is None or self.host.winfo_width() < 20 or self.host.winfo_height() < 20:
            return   # not on screen yet
        W, H = max(self.host.winfo_width(), 50), max(self.host.winfo_height(), 50)
        fit = self.fit.get()
        ratio = getattr(self.canvas, "device_pixel_ratio", 1.0) or 1.0   # >1 on high-DPI screens
        natural_dpi = self.base_dpi * ratio
        if self.zoom_mode:
            # keep the figure's size in inches and change the resolution: everything scales together
            dpi = min(W / self.inches[0], H / self.inches[1], natural_dpi * 1.5) if fit else natural_dpi
            self.fig.set_dpi(dpi)
            self.fig.set_size_inches(*self.inches, forward=False)
            w, h = int(self.inches[0] * dpi), int(self.inches[1] * dpi)
        elif fit:
            w, h = W, H   # stretch: the layout engine re-arranges the plot for the new size
        else:
            w, h = int(self.inches[0] * natural_dpi), int(self.inches[1] * natural_dpi)
        x0 = max(0, (W - w) // 2) if fit else 0
        if fit:
            self.vbar.grid_remove()
            self.hbar.grid_remove()
            self.host.xview_moveto(0)
            self.host.yview_moveto(0)
        else:
            self.vbar.grid(row=0, column=2, sticky="ns") if h > H else self.vbar.grid_remove()
            self.hbar.grid(row=1, column=1, sticky="ew") if w > W else self.hbar.grid_remove()
        self.host.coords(self.win, x0, 0)
        self.host.itemconfigure(self.win, width=w, height=h)
        self.host.configure(scrollregion=(0, 0, max(w, 1), max(h, 1)))
        try:   # tell matplotlib about the new size right away (no <Configure> comes if the size is unchanged)
            self.canvas.resize(types.SimpleNamespace(width=w, height=h))
        except Exception:  # noqa: BLE001
            pass

    def save_image(self):
        if self.fig is None:
            messagebox.showinfo(APP_NAME, "Make a plot first, then save it.", parent=self)
            return
        page = self.page
        stem = Path(page.ds.name).stem if page.ds else "plot"
        path = filedialog.asksaveasfilename(
            parent=self, title="Save the plot as an image",
            initialdir=self.app.cfg.get("save_dir") or self.app.cfg.get("last_dir") or str(Path.home()),
            initialfile=f"{page.graph.id}_{stem}.png", defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("SVG vector image", "*.svg"), ("PDF document", "*.pdf"),
                       ("JPEG image", "*.jpg")])
        if not path:
            return
        dpi = int(self.dpi.get().split()[0])
        try:
            self.fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=self.fig.get_facecolor())
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_NAME, f"Couldn't save the image:\n{exc}", parent=self)
            return
        finally:
            self._resize()
            self.canvas.draw_idle()   # the screen picture (and the value ball's background) again
        self.app.cfg["save_dir"] = str(Path(path).parent)
        self.app.cfg["dpi"] = self.dpi.get()
        paper = "  (on dark graph paper: turn off View › Dark graph paper for a white background)" \
            if getattr(self.fig, "_studio_paper", "") == "dark" else ""
        page.message(f"Saved {Path(path).name}{paper}", "ok")


class PopoutWindow(tk.Toplevel):
    """The current plot in its own resizable window (re-drawn from the same code)."""

    def __init__(self, app: App, built):
        super().__init__(app)
        self.title(f"{built.graph.name} · {built.dataset.name}")
        t, px = app.theme, app.theme.px
        self.theme = t
        self.configure(background=C["panel"])
        try:
            fig, _w, _s = run_plot(built)
        except PlotRunError as exc:
            self.destroy()
            messagebox.showerror(APP_NAME, exc.message, parent=app)
            return
        view = app.work.plot_view
        apply_paper(fig, view.paper_var.get(), app.theme.ink)
        self.fig = fig
        w, h = (int(v * fig.dpi) for v in fig.get_size_inches())  # open at the figure's natural size
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(w + px(24), sw - 60)}x{min(h + px(64), sh - 100)}")
        bar = tk.Frame(self, background=C["panel"])
        bar.pack(fill="x", padx=px(10), pady=(px(8), px(4)))
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.toolbar = Toolbar(self.canvas, tk.Frame(self))
        nav = NavButtons(bar, t, lambda: self.toolbar)
        nav.set_enabled(True)
        ttk.Button(bar, text="Save image…", image=t.icon_states("download", 16), compound="left",
                   style="Small.TButton", command=self.save).pack(side="right")
        widget = self.canvas.get_tk_widget()
        widget.configure(background=C["panel"], highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=px(10), pady=(0, px(10)))
        self.tracker = PointTracker(self.canvas, tracker_colors, enabled=view.values_var.get)
        z = getattr(fig, "_studio_zoom", None)
        self.nav = Navigator(self.canvas, toolbar=self.toolbar,
                             natural={id(z["ax"]): {"x": z["x"], "y": z["y"]}} if z else None,
                             enabled=view.mouse_var.get)
        self.canvas.draw_idle()
        self.app = app
        app.theme.dark_title_bar(self)

    def save(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".png",
                                            filetypes=[("PNG image", "*.png"), ("SVG vector image", "*.svg"),
                                                       ("PDF document", "*.pdf")])
        if path:
            dpi = int(self.app.work.plot_view.dpi.get().split()[0])
            self.fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=self.fig.get_facecolor())
            self.canvas.draw_idle()


def smooth_text(text: tk.Text, theme):
    """Glide a Text widget on the mouse wheel instead of jumping by lines."""
    text.smooth = SmoothScroller(text)
    step = theme.px(64)

    def wheel(e, pixels=None):
        text.smooth.scroll(wheel_pixels(e, theme) if pixels is None else pixels)
        return "break"

    text.bind("<MouseWheel>", wheel)
    text.bind("<Button-4>", lambda e: wheel(e, -step))
    text.bind("<Button-5>", lambda e: wheel(e, step))
    text.bind("<Shift-MouseWheel>", lambda e: (text.xview_scroll(-int(e.delta / 120) * 4 or
                                                                 (-4 if e.delta > 0 else 4), "units"), "break")[1])


class CodeView(tk.Frame):
    def __init__(self, master, page: WorkspacePage):
        super().__init__(master, background=C["panel"])
        self.page, self.app = page, page.app
        t, px = self.app.theme, self.app.theme.px
        bar = tk.Frame(self, background=C["panel"])
        bar.pack(fill="x", padx=px(14), pady=(px(10), px(8)))
        tk.Label(bar, text="The exact code behind the plot. It runs as it is in Jupyter, Kaggle or a .py file.",
                 background=C["panel"], foreground=C["muted"], font=t.f["small"]).pack(side="left", padx=(px(2), 0))
        ttk.Button(bar, text="Save as .py…", image=t.icon_states("download", 16), compound="left",
                   style="TButton", command=self.save).pack(side="right")
        self.copy_btn = ttk.Button(bar, text="Copy code", image=t.icon("copy", "on_accent", 16), compound="left",
                                   style="Accent.TButton", command=self.copy)
        self.copy_btn.pack(side="right", padx=(0, px(6)))
        box = ttk.Frame(self, style="Code.TFrame", padding=px(4))
        box.pack(fill="both", expand=True, padx=px(14), pady=(0, px(14)))
        # the code keeps its own colours in both looks
        self.text = tk.Text(box, wrap="none", font=t.f["mono"], background=CODE["bg"], foreground=CODE["fg"],
                            relief="flat", borderwidth=0, padx=px(12), pady=px(10), insertwidth=0,
                            selectbackground=CODE["select"], selectforeground=CODE["fg"], spacing1=px(2),
                            spacing3=px(2), highlightthickness=0)
        self.text.fixed_colors = True
        smooth_text(self.text, t)
        ys = AutoScrollbar(box, orient="vertical", command=self.text.yview, style="Code.Vertical.TScrollbar")
        xs = AutoScrollbar(box, orient="horizontal", command=self.text.xview, style="Code.Horizontal.TScrollbar")
        self.text.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.text.tag_configure("comment", foreground=CODE["comment"], font=t.f["mono_italic"])
        self.text.tag_configure("string", foreground=CODE["string"])
        self.text.tag_configure("number", foreground=CODE["number"])
        self.text.tag_configure("keyword", foreground=CODE["keyword"], font=t.f["mono_bold"])
        self.text.tag_configure("module", foreground=CODE["module"], font=t.f["mono_bold"])
        self.text.tag_configure("builtin", foreground=CODE["builtin"])
        self.code = ""
        self._copy_job = None
        self.set_code("# Pick columns and press Plot: the code appears here.\n")

    def set_code(self, code):
        self.code = code
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", code)
        previous = ""
        try:
            for tok in tokenize.generate_tokens(io.StringIO(code).readline):
                tag = None
                if tok.type == tokenize.COMMENT:
                    tag = "comment"
                elif tok.type in STRING_TOKENS:
                    tag = "string"
                elif tok.type == tokenize.NUMBER:
                    tag = "number"
                elif tok.type == tokenize.NAME and previous != ".":
                    if keyword.iskeyword(tok.string):
                        tag = "keyword"
                    elif tok.string in ("plt", "sns", "pd", "np", "mpl"):
                        tag = "module"
                    elif tok.string in BUILTINS:
                        tag = "builtin"
                if tag:
                    self.text.tag_add(tag, f"{tok.start[0]}.{tok.start[1]}", f"{tok.end[0]}.{tok.end[1]}")
                if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT):
                    previous = tok.string
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass
        self.text.configure(state="disabled")

    def copy(self, source=None):
        """Copy the code; the button that was used says "Copied" for a moment."""
        t = self.app.theme
        self.clipboard_clear()
        self.clipboard_append(self.code)
        self.update()
        buttons = [(self.copy_btn, t.icon("check", "on_accent", 16), t.icon("copy", "on_accent", 16))]
        if source is not None:
            buttons.append((source, t.icon_states("check", 16, normal="ok", active="ok"), t.icon_states("copy", 16)))
        for button, done, normal in buttons:
            button.configure(text="Copied", image=done)
        if self._copy_job:
            self.after_cancel(self._copy_job)

        def restore():
            self._copy_job = None
            for button, _done, normal in buttons:
                try:
                    button.configure(text="Copy code", image=normal)
                except tk.TclError:
                    pass
        self._copy_job = self.after(1600, restore)
        self.page.message("Code copied to the clipboard.", "ok")

    def save(self):
        page = self.page
        name = f"{page.graph.id}_plot.py" if page.graph else "plot.py"
        path = filedialog.asksaveasfilename(parent=self, title="Save the code", defaultextension=".py",
                                            initialfile=name, initialdir=self.app.cfg.get("save_dir") or None,
                                            filetypes=[("Python file", "*.py"), ("Text", "*.txt")])
        if path:
            Path(path).write_text(self.code, encoding="utf-8")
            page.message(f"Saved {Path(path).name}", "ok")


class DataView(tk.Frame):
    """The automatic scan of the CSV: column types, missing values, first rows."""

    def __init__(self, master, page: WorkspacePage):
        super().__init__(master, background=C["panel"])
        self.page, self.app = page, page.app
        t, px = self.app.theme, self.app.theme.px
        top = tk.Frame(self, background=C["panel"])
        top.pack(fill="x", padx=px(16), pady=(px(12), px(6)))
        self.title = tk.Label(top, background=C["panel"], foreground=C["text"], font=t.f["h3"], anchor="w")
        self.title.pack(fill="x")
        self.summary = tk.Label(top, background=C["panel"], foreground=C["muted"], anchor="w", justify="left",
                                font=t.f["small"])
        self.summary.pack(fill="x", pady=(px(2), 0))
        self.notes = tk.Label(top, background=C["panel"], foreground=C["warn"], anchor="w", justify="left",
                              font=t.f["small"])
        self.notes.pack(fill="x")
        self.bind("<Configure>", lambda e: (self.notes.configure(wraplength=e.width - px(40)),
                                            self.summary.configure(wraplength=e.width - px(40))), add="+")
        pane = ttk.PanedWindow(self, orient="vertical")
        pane.pack(fill="both", expand=True, padx=px(14), pady=(px(4), px(12)))
        cols_frame = tk.Frame(pane, background=C["panel"])
        rows_frame = tk.Frame(pane, background=C["panel"])
        pane.add(cols_frame, weight=3)
        pane.add(rows_frame, weight=2)
        head = tk.Frame(cols_frame, background=C["panel"])
        head.pack(fill="x", pady=(0, px(6)))
        tk.Label(head, text="Columns", background=C["panel"], foreground=C["text"], font=t.f["bold"]).pack(
            side="left", padx=(px(2), 0))
        tk.Label(head, text="click a heading to sort", background=C["panel"], foreground=C["faint"],
                 font=t.f["small"]).pack(side="left", padx=(px(8), 0))
        self.cols = self._table(cols_frame, ("#", "Column", "Type", "Missing", "Unique", "Link to target", "Summary"),
                                (40, 200, 150, 110, 80, 150, 400), sortable=True)
        self.ds = None
        self.items = {}   # tree item -> column name
        tk.Label(rows_frame, text="First rows", background=C["panel"], foreground=C["text"],
                 font=t.f["bold"]).pack(anchor="w", padx=(px(2), 0), pady=(px(10), px(6)))
        self.rows_holder = rows_frame
        self.rows = None

    def _table(self, parent, headings, widths, sortable=False):
        px = self.app.theme.px
        box = ttk.Frame(parent, style="Inset.TFrame", padding=px(3))
        box.pack(fill="both", expand=True)
        tree = ttk.Treeview(box, columns=list(range(len(headings))), show="headings", selectmode="browse")
        ys = AutoScrollbar(box, orient="vertical", command=tree.yview, style="Field.Vertical.TScrollbar")
        xs = AutoScrollbar(box, orient="horizontal", command=tree.xview, style="Field.Horizontal.TScrollbar")
        tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        for i, (h, w) in enumerate(zip(headings, widths)):
            tree.heading(i, text=h, anchor="w")
            if sortable:
                tree.heading(i, command=lambda i=i, tree=tree: self._sort(tree, i))
            tree.column(i, width=px(w), minwidth=px(40), anchor="w", stretch=(i == len(headings) - 1))
        tree.tag_configure("odd", background=C["stripe"])
        tree.tag_configure("gaps", foreground=C["warn"])
        return tree

    def on_theme(self):
        for tree in (self.cols, self.rows):
            if tree is not None:
                tree.tag_configure("odd", background=C["stripe"])
                tree.tag_configure("gaps", foreground=C["warn"])

    @staticmethod
    def _sort_key(text):
        """Numbers sort as numbers ('1,460 (4.1%)' -> 1460, 'η 0.35' -> 0.35), other text alphabetically."""
        m = re.search(r"[-+]?\d[\d,]*\.?\d*", str(text))
        if m:
            try:
                return (0, float(m.group().replace(",", "")), "")
            except ValueError:
                pass
        return (1, 0.0, str(text).lower())

    def _sort(self, tree, col):
        """Click a heading: sort by that column (click again: the other way round)."""
        reverse = getattr(tree, "_sorted", None) == (col, False)
        rows = [(self._sort_key(tree.set(item, col)), item) for item in tree.get_children("")]
        if col == 5:   # links: the target, then the strongest link (r can be negative), no link ('–') last
            def strength(row):
                text = tree.set(row[1], col)
                if text == "target":
                    return (0, 0.0)
                group, value, _ = row[0]
                return (1, -abs(value)) if group == 0 else (2, 0.0)
            rows.sort(key=strength, reverse=reverse)
        else:
            rows.sort(key=lambda r: r[0], reverse=reverse)
        for n, (_key, item) in enumerate(rows):
            tree.move(item, "", n)
            tags = [tg for tg in tree.item(item, "tags") if tg != "odd"] + (["odd"] if n % 2 else [])
            tree.item(item, tags=tags)
        tree._sorted = (col, reverse)

    def _link_text(self, prof, name):
        if prof.target is None:
            return "–"
        if name == prof.target:
            return "target"
        link = prof.link(name)
        return link[1] if link else "–"

    def set_target(self, target):
        """Fill the 'Link to target' column (r, η or Cramér's V with the chosen target)."""
        if self.ds is None:
            return
        prof = recommend.profile(self.ds, target)
        self.cols.heading(5, text=f"Link to {recommend.short(target, 16)}" if target else "Link to target")
        for item, name in self.items.items():
            self.cols.set(item, 5, self._link_text(prof, name))
        if getattr(self.cols, "_sorted", None) and self.cols._sorted[0] == 5:
            self.cols._sorted = None
            self._sort(self.cols, 5)

    def set_dataset(self, ds, target=None):
        self.ds = ds
        self.title.configure(text=ds.name)
        self.summary.configure(text=f"{ds.summary_text()}   ·   read in {ds.seconds:.1f} s   ·   {ds.path.parent}")
        self.notes.configure(text="\n".join(f"•  {n}" for n in ds.notes) +
                             ("\n" if ds.notes else "") +
                             "\n".join(f"•  '{c}' was stored as text and converted to {i.converted}."
                                       for c, i in ds.columns.items() if i.converted))
        tree = self.cols
        tree.delete(*tree.get_children())
        tree._sorted = None
        self.items = {}
        for n, (name, info) in enumerate(ds.columns.items()):
            missing = f"{info.missing:,} ({info.missing_pct:.1f}%)" if info.missing else "–"
            tags = ["odd"] if n % 2 else []
            if info.missing:
                tags.append("gaps")
            item = tree.insert("", "end", values=(n + 1, name, info.kind_label, missing, f"{info.unique:,}", "",
                                                  info.summary), tags=tags)
            self.items[item] = name
        self.set_target(target)
        # first rows
        if self.rows is not None:
            self.rows.master.destroy()
        names = list(ds.df.columns[:60])
        head = ds.df.iloc[:200, :60]
        t = self.app.theme
        body_font, head_font = tkfont.Font(font=t.f["base"]), tkfont.Font(font=t.f["small_bold"])
        widths = []   # wide enough for the heading and the first values (in 100 % pixels)
        for i, c in enumerate(names):
            sample = {str(v)[:40] for v in head.iloc[:50, i].tolist()}
            longest = sorted(sample, key=len, reverse=True)[:3]      # measuring is slow: only the longest few
            need = max([head_font.measure(str(c))] + [body_font.measure(v) for v in longest])
            widths.append(int(min(260, max(60, need / t.scale + 28))))
        self.rows = self._table(self.rows_holder, names, widths)
        for c in range(len(names)):
            self.rows.column(c, stretch=False)
        for n, row in enumerate(head.itertuples(index=False)):
            values = ["–" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v)[:40] for v in row]
            self.rows.insert("", "end", values=values, tags=["odd"] if n % 2 else [])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    csv_path = graph_id = None
    autoplot = "--plot" in argv
    if "--csv" in argv:
        csv_path = argv[argv.index("--csv") + 1]
    elif argv and not argv[0].startswith("-"):
        csv_path = argv[0]
    if "--graph" in argv:
        graph_id = argv[argv.index("--graph") + 1]
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CSVPlotStudio")
        except Exception:  # noqa: BLE001
            pass
    app = App(csv_path=csv_path, graph_id=graph_id, autoplot=autoplot)
    app.mainloop()


if __name__ == "__main__":
    main()
