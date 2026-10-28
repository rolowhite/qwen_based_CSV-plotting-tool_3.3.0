"""Design tokens (colours, type, spacing), fonts and ttk styles, with a light and a dark look.

`C` always holds the colours of the current look. Widgets read it when they are
created; switching the look (Theme.apply) updates `C` in place, redraws the skin
(skin.py), re-styles all ttk widgets and recolours the plain Tk widgets that exist.

Every text/background pair below meets WCAG 2.1 AA (4.5:1 for text, 3:1 for the
outlines of inputs and the focus ring); tests/test_design.py checks it.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from . import fonts
from .skin import Skin

# --------------------------------------------------------------------------- #
# colour tokens
# --------------------------------------------------------------------------- #

LIGHT = {
    "bg": "#f1f3f8",            # window, behind the cards
    "bg_hover": "#e5e8f0",      # hover tint for things that sit on the window background
    "panel": "#ffffff",         # cards (and the light graph paper)
    "card_hover": "#fafbff",
    "raised": "#f7f8fb",        # secondary buttons, wells
    "hover": "#eef0f6",
    "pressed": "#e3e6ef",
    "field": "#fdfdfe",         # inside of inputs, lists, tables
    "border": "#e2e6ee",        # hairlines
    "border_strong": "#cdd3df",
    "border_dark": "#b4bccb",
    "input_border": "#8a93a6",  # 3:1 against the panel (WCAG 1.4.11)
    "text": "#1a2030",
    "muted": "#535c70",
    "faint": "#646c7f",
    "accent": "#b8461f",
    "accent_hover": "#a03b19",
    "accent_pressed": "#873014",
    "accent_soft": "#fbece6",
    "accent_line": "#efc4b3",
    "accent_disabled": "#e3b09c",
    "accent_disabled_fg": "#fff6f2",
    "on_accent": "#ffffff",     # text on an accent background
    "focus_ring": "#b8461f",
    "select": "#f8ddd2",
    "danger": "#b42318",
    "danger_soft": "#fef3f2",
    "warn": "#8a4b08",
    "sev_warn": "#c2410c",          # severity marks: important (orange) ...
    "sev_check": "#a16207",         # ... and worth checking (yellow); leakage uses danger
    "warn_soft": "#fff8e6",
    "ok": "#067647",
    "ok_soft": "#ecfdf3",
    "stripe": "#f8f9fc",
    "heading": "#f4f5f9",
    "heading_hover": "#eceef5",
    "scroll": "#c3c9d6",
    "scroll_hover": "#9aa3b5",
    "track": "#d9dde6",         # slider track
    "check_mark": "#ffffff",
    "switch_off": "#c6ccd8",
    "knob": "#ffffff",
    "tip_bg": "#1a2030",
    "tip_fg": "#ffffff",
    "btn_fg": "#1a2030",
}

# Charcoal + coral, the same accent as the profile dashboard (one accent for the whole app).
DARK = {
    "bg": "#121214",
    "bg_hover": "#202024",
    "panel": "#1c1c1f",         # must equal paper.PAPER["face"] (the dark graph paper)
    "card_hover": "#212125",
    "raised": "#242428",
    "hover": "#2a2a2f",
    "pressed": "#323238",
    "field": "#161619",
    "border": "#2b2b30",
    "border_strong": "#3a3a41",
    "border_dark": "#4a4a52",
    "input_border": "#6c6c76",
    "text": "#ededf0",
    "muted": "#a6a6b0",
    "faint": "#93939d",
    "accent": "#f2764b",
    "accent_hover": "#f58b66",
    "accent_pressed": "#e0613a",
    "accent_soft": "#35231e",
    "accent_line": "#5b3528",
    "accent_disabled": "#6b3a2b",
    "accent_disabled_fg": "#c9ada3",
    "on_accent": "#1b100c",     # dark ink on coral: 6.6:1 (white would be 2.9:1)
    "focus_ring": "#f39a77",
    "select": "#3d2720",
    "danger": "#ff6b61",
    "danger_soft": "#3a1c1a",
    "warn": "#f6b04a",
    "sev_warn": "#ff8f4d",
    "sev_check": "#f3c94a",
    "warn_soft": "#36290f",
    "ok": "#4ade80",
    "ok_soft": "#13301e",
    "stripe": "#1a1a1d",
    "heading": "#1b1b1e",
    "heading_hover": "#26262b",
    "scroll": "#46464e",
    "scroll_hover": "#62626c",
    "track": "#38383f",
    "check_mark": "#1b100c",
    "switch_off": "#45454d",
    "knob": "#f4f4f6",
    "tip_bg": "#2b2b31",
    "tip_fg": "#f2f2f4",
    "btn_fg": "#ededf0",
}

PALETTES = {"light": LIGHT, "dark": DARK}

# The "Ink on graph paper" style (Figma proposal): every control is one ink, so the coral accent no longer looks
# like the orange of a plot's second series; layered cool surfaces; the same status colours. Same keys as above.
INK_LIGHT = {**LIGHT,
    "bg": "#f3f5f7", "bg_hover": "#e7ebf0", "panel": "#ffffff", "card_hover": "#f9fafb", "raised": "#eef1f4",
    "hover": "#e9edf2", "pressed": "#dde2e9", "field": "#fdfdfe", "border": "#d9dfe7", "border_strong": "#c6ced9",
    "border_dark": "#aab4c2", "input_border": "#7d8798", "text": "#1a2230", "muted": "#4e596a", "faint": "#5f697b",
    "accent": "#17202c", "accent_hover": "#2b3646", "accent_pressed": "#0e151e", "accent_soft": "#e6eaf0",
    "accent_line": "#bcc5d1", "accent_disabled": "#aab2bf", "accent_disabled_fg": "#f3f5f7", "on_accent": "#ffffff",
    "focus_ring": "#17202c", "select": "#e1e7ee", "stripe": "#f8f9fb", "heading": "#f1f3f6",
    "heading_hover": "#e8ebf0", "scroll": "#c2c9d3", "scroll_hover": "#98a2b1", "track": "#d9dfe7",
    "switch_off": "#c4cbd5", "tip_bg": "#17202c", "btn_fg": "#1a2230",
}
INK_DARK = {**DARK,
    "bg": "#14171c", "bg_hover": "#1f242b", "panel": "#1c2026", "card_hover": "#21262d", "raised": "#252a31",
    "hover": "#2a3038", "pressed": "#323943", "field": "#171a1f", "border": "#2e343d", "border_strong": "#3b424c",
    "border_dark": "#4b535e", "input_border": "#6f7885", "text": "#eceff3", "muted": "#a6aeba", "faint": "#8f98a5",
    "accent": "#e6eaf0", "accent_hover": "#ffffff", "accent_pressed": "#cfd5dd", "accent_soft": "#2a313b",
    "accent_line": "#46505c", "accent_disabled": "#4a525d", "accent_disabled_fg": "#9aa2ad", "on_accent": "#14171c",
    "focus_ring": "#e6eaf0", "select": "#313844", "stripe": "#1a1e23", "heading": "#1b1f25",
    "heading_hover": "#262b33", "scroll": "#474e59", "scroll_hover": "#636b77", "track": "#3b424c",
    "check_mark": "#14171c", "switch_off": "#46505c", "knob": "#f4f6f8", "tip_bg": "#2b313a", "tip_fg": "#f2f4f6",
    "btn_fg": "#eceff3",
}
STYLES = {"default": PALETTES, "ink": {"light": INK_LIGHT, "dark": INK_DARK}}
HALO_MS = {"default": (90, 130), "ink": (60, 80)}      # the click halo: strong, then faint (ink: 140 ms in all)
C = dict(LIGHT)

# The "Python code" tab keeps its own colours in both looks.
CODE = {"bg": "#fbfbfe", "fg": "#1d2433", "select": "#e3e6ff", "comment": "#6a7287", "string": "#0b7a43",
        "number": "#b45309", "keyword": "#7c3aed", "module": "#4f46e5", "builtin": "#2563eb"}

# Palette entries that plain Tk widgets use directly. Their values are unique within each
# palette, so a colour found on a widget can be traced back to its role when the look changes.
WIDGET_BG_KEYS = ("bg", "panel", "card_hover", "raised", "field", "border", "border_strong", "border_dark", "accent",
                  "accent_soft", "hover", "select", "danger_soft", "warn_soft", "ok_soft", "stripe")
WIDGET_FG_KEYS = ("text", "muted", "faint", "accent", "danger", "warn", "ok", "on_accent", "sev_warn", "sev_check")
BG_OPTIONS = ("background", "highlightbackground", "selectbackground", "activebackground", "troughcolor",
              "disabledbackground", "readonlybackground", "selectcolor")
FG_OPTIONS = ("foreground", "highlightcolor", "selectforeground", "activeforeground", "disabledforeground",
              "insertbackground")

# fallbacks when the bundled IBM Plex fonts can't be used (e.g. a Tk without Xft on Linux)
UI_FONTS = ("Segoe UI", "Ubuntu", "Noto Sans", "Cantarell", "Inter", "Roboto", "DejaVu Sans", "Liberation Sans",
            "Helvetica Neue", "Helvetica", "Arial")
MONO_FONTS = ("Cascadia Mono", "Consolas", "JetBrains Mono", "Ubuntu Mono", "DejaVu Sans Mono", "Noto Sans Mono",
              "Liberation Mono", "Menlo", "Courier New")

# spacing scale (px at 100 %): 4 8 12 16 20 24 32
SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 20, "xxl": 24, "xxxl": 32}

# Tcl helpers: the short halo after a click (states user1 -> user2 -> normal)
_TCL = r"""
namespace eval ::studio {}
set ::studio::t1 90
set ::studio::t2 130
proc ::studio::flash {w} {
    if {![winfo exists $w] || [$w instate disabled]} { return }
    catch { after cancel [set ::studio::job($w)] }
    $w state {user1 !user2}
    set ::studio::job($w) [after $::studio::t1 [list ::studio::flash2 $w]]
}
proc ::studio::flash2 {w} {
    if {![winfo exists $w]} { return }
    $w state {!user1 user2}
    set ::studio::job($w) [after $::studio::t2 [list ::studio::flash3 $w]]
}
proc ::studio::flash3 {w} {
    catch { unset ::studio::job($w) }
    if {[winfo exists $w]} { $w state {!user1 !user2} }
}
proc ::studio::release {w} {
    if {[winfo exists $w] && [$w instate {pressed !disabled}]} { ::studio::flash $w }
}
"""


def _pick(root, names, fallback):
    available = {f.lower(): f for f in tkfont.families(root)}
    for name in names:
        if name.lower() in available:
            return available[name.lower()]
    return tkfont.nametofont(fallback).actual("family")


class Theme:
    def __init__(self, root: tk.Tk, mode: str = "light", style: str = "default"):
        self.root = root
        self.mode = mode if mode in PALETTES else "light"
        self.style = style if style in STYLES else "default"
        C.clear()
        C.update(STYLES[self.style][self.mode])
        try:
            dpi = root.winfo_fpixels("1i")
        except tk.TclError:
            dpi = 96
        self.scale = max(1.0, dpi / 96.0)
        self._fonts()
        self.skin = Skin(self)
        self.m = self.skin.m          # margin around controls (focus ring / click halo)
        self.images = {}
        self._elements_made = False
        self._rgb_cache = {}
        self._keyboard = False        # was the last input a Tab key? (focus rings only then)
        self._options()
        self._styles()
        self._interaction()

    # ------------------------------------------------------------------ #
    # type
    # ------------------------------------------------------------------ #
    def _fonts(self):
        root = self.root
        fonts.register_for_tk()
        families = tkfont.families(root)
        plex = fonts.pick(families, fonts.SANS) or (fonts.SANS if fonts.resolves(root, fonts.SANS) else None)
        if sys.platform == "darwin":
            body = plex or tkfont.nametofont("TkDefaultFont").actual("family")
        else:
            body = plex or _pick(root, UI_FONTS, "TkDefaultFont")
        mono = (fonts.pick(families, fonts.MONO) or (fonts.MONO if fonts.resolves(root, fonts.MONO) else None)
                or _pick(root, MONO_FONTS, "TkFixedFont"))
        # Plex's medium and semibold faces have their own family names (Windows, Linux)
        def face(name):
            return name if plex and fonts.resolves(root, name) else None
        medium = face(fonts.SANS + " Medm")
        semi = face(fonts.SANS + " SmBld")
        mono_semi = face(fonts.MONO + " SmBld")
        size = 10 if sys.platform != "darwin" else 13
        self.family, self.mono_family, self.plex = body, mono, bool(plex)

        def med(n):
            return (medium, n) if medium else (body, n)

        def semibold(n):
            return (semi, n) if semi else (body, n, "bold")

        self.f = {
            "base": (body, size),
            "small": (body, size - 1),
            "tiny": (body, size - 2),
            "medium": med(size),
            "small_medium": med(size - 1),
            "bold": semibold(size),
            "small_bold": semibold(size - 1),
            "h1": semibold(size + 10),
            "h2": semibold(size + 5),
            "h3": semibold(size + 2),
            "button": med(size),
            "button_small": med(size - 1),
            "button_big": semibold(size + 1),
            "mono": (mono, size),
            "mono_bold": (mono_semi, size) if mono_semi else (mono, size, "bold"),
            "mono_italic": (mono, size, "italic"),
        }
        # the profile dashboard's type scale: the same Plex faces as the rest of the app, larger steps
        self.pf = {
            "hero_h1": semibold(size + 14),
            "stat_value": semibold(size + 10),
            "ring_value": semibold(size + 9),
            "summary_num": semibold(size + 6),
            "panel_h2": semibold(size + 3),
            "insight_h2": semibold(size + 3),
            "identity_name": semibold(size + 3),
            "modal_h2": semibold(size + 5),
            "body_lg": (body, size + 2),
            "card_title": semibold(size),
            "body": (body, size),
            "body_sm": (body, size - 1),
            "label": med(size - 1),
            "tiny": (body, size - 2),
        }
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
                     "TkTooltipFont", "TkSmallCaptionFont", "TkIconFont"):
            try:
                tkfont.nametofont(name).configure(family=body, size=size if name != "TkTooltipFont" else size - 1)
            except tk.TclError:
                pass
        try:
            tkfont.nametofont("TkFixedFont").configure(family=mono, size=size)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ #
    @property
    def dark(self) -> bool:
        return self.mode == "dark"

    @property
    def ink(self) -> bool:
        return self.style == "ink"

    def px(self, n) -> int:
        return int(round(n * self.scale))

    def icon(self, name, role="muted", size=18):
        return self.skin.icon(name, role, size)

    def icon_states(self, name, size=18, **kw):
        return self.skin.icon_states(name, size, **kw)

    def glyph(self, fancy: str, plain: str) -> str:
        """`fancy` if the UI font can draw it, else `plain`.

        Some Linux builds of Tk (e.g. standalone Pythons) only have basic X11 fonts
        without arrows or symbols; those would show up as blanks.
        """
        if not hasattr(self, "_measure_font"):
            self._measure_font = tkfont.Font(root=self.root, font=self.f["base"])
        font = self._measure_font
        try:
            for ch in fancy:
                if ch.isspace() or ord(ch) < 128:
                    continue
                width = font.measure(ch)
                # missing glyphs are drawn as nothing (Tk 9) or as the text "\uXXXX" (Tk 8.6)
                if width == 0 or width == font.measure(f"\\u{ord(ch):04x}"):
                    return plain
        except tk.TclError:
            return plain
        return fancy

    # ------------------------------------------------------------------ #
    # switching the look
    # ------------------------------------------------------------------ #
    def apply(self, mode: str, style: str = None):
        """Switch to the light or dark look (and/or the default or ink style), live."""
        style = self.style if style is None else style
        if mode not in PALETTES or style not in STYLES or (mode, style) == (self.mode, self.style):
            return
        old = dict(C)
        self.mode, self.style = mode, style
        C.clear()
        C.update(STYLES[style][mode])
        self._halo_timing()
        self._options()
        self._styles()
        self._recolor_tree(old)
        self.dark_title_bar(self.root)

    def _norm(self, color):
        color = str(color)
        if not color:
            return None
        rgb = self._rgb_cache.get(color)
        if rgb is None:
            try:
                rgb = tuple(v // 257 for v in self.root.winfo_rgb(color))
            except tk.TclError:
                rgb = ()
            self._rgb_cache[color] = rgb
        return rgb or None

    def _recolor_tree(self, old: dict):
        bg_map = {self._norm(old[k]): C[k] for k in WIDGET_BG_KEYS}
        fg_map = {self._norm(old[k]): C[k] for k in WIDGET_FG_KEYS}

        def recolor(w):
            if getattr(w, "fixed_colors", False):
                return
            for options, mapping in ((BG_OPTIONS, bg_map), (FG_OPTIONS, fg_map)):
                for opt in options:
                    try:
                        value = w.cget(opt)
                    except (tk.TclError, AttributeError, ValueError):
                        continue
                    new = mapping.get(self._norm(value))
                    if new is not None:
                        try:
                            w.configure(**{opt: new})
                        except tk.TclError:
                            pass
            if isinstance(w, ttk.Combobox):
                self.style_combobox_list(w)
            for child in w.winfo_children():
                recolor(child)
            hook = getattr(w, "on_theme", None)
            if callable(hook):
                hook()

        recolor(self.root)

    def style_combobox_list(self, combo):
        """The drop-down list of a ttk.Combobox is a plain Tk listbox; give it the look too."""
        try:
            popdown = combo.tk.call("ttk::combobox::PopdownWindow", combo)
            combo.tk.call(f"{popdown}.f.l", "configure", "-background", C["field"], "-foreground", C["text"],
                          "-selectbackground", C["select"], "-selectforeground", C["text"],
                          "-font", self.f["base"], "-borderwidth", 0, "-highlightthickness", 0,
                          "-activestyle", "none", "-selectborderwidth", 0)
            combo.tk.call(f"{popdown}.f", "configure", "-padding", (self.px(6), self.px(4)))
            combo.tk.call(popdown, "configure", "-background", C["border_strong"])
        except tk.TclError:
            pass

    def dark_title_bar(self, window):
        """Windows 10/11: dark window title bar in the dark look."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1 if self.dark else 0)
            for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (new / old Windows 10 builds)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value),
                                                              ctypes.sizeof(value)) == 0:
                    break
        except Exception:  # noqa: BLE001 - purely cosmetic
            pass

    # ------------------------------------------------------------------ #
    # keyboard focus rings and the click halo
    # ------------------------------------------------------------------ #
    def _interaction(self):
        """Focus rings appear for keyboard users only ("focus-visible"), and a button
        gives a short halo when it is clicked."""
        root = self.root

        def keyboard(_e=None):
            self._keyboard = True

        def pointer(_e=None):
            self._keyboard = False

        root.bind_all("<ButtonPress>", pointer, add="+")
        for seq in ("<Tab>", "<<NextWindow>>", "<<PrevWindow>>"):
            try:
                root.bind_all(seq, keyboard, add="+")
            except tk.TclError:
                pass

        def focus_in(e):
            w = e.widget
            if self._keyboard and hasattr(w, "state"):
                try:
                    w.state(["user3"])
                except tk.TclError:
                    pass

        def focus_out(e):
            w = e.widget
            if hasattr(w, "state"):
                try:
                    w.state(["!user3"])
                except tk.TclError:
                    pass

        for cls in ("TButton", "TCheckbutton", "TRadiobutton", "TMenubutton", "TNotebook", "TCombobox", "TFrame"):
            root.bind_class(cls, "<FocusIn>", focus_in, add="+")
            root.bind_class(cls, "<FocusOut>", focus_out, add="+")
        # read-only comboboxes: no selected-text highlight after picking a value
        def clear_selection(e):
            w = e.widget
            try:
                if "readonly" in w.state():
                    w.after_idle(lambda: w.winfo_exists() and w.selection_clear())
            except (tk.TclError, AttributeError):
                pass
        root.bind_class("TCombobox", "<<ComboboxSelected>>", clear_selection, add="+")
        # the drop-down list is made the first time it opens: style it then
        for seq in ("<ButtonPress-1>", "<KeyPress-Down>"):
            root.bind_class("TCombobox", seq, lambda e: self.style_combobox_list(e.widget), add="+")
        root.bind_class("TCombobox", "<FocusIn>", clear_selection, add="+")
        try:
            root.tk.eval(_TCL)
            self._halo_timing()
            old = root.tk.eval("bind TButton <ButtonRelease-1>")
            if "studio::release" not in old:
                root.tk.eval("bind TButton <ButtonRelease-1> {::studio::release %W\n" + old + "}")
            for seq in ("<Key-space>", "<<Invoke>>"):
                old = root.tk.eval(f"bind TButton {seq}")
                if old and "studio::flash" not in old:
                    root.tk.eval(f"bind TButton {seq} " + "{::studio::flash %W\n" + old + "}")
        except tk.TclError:   # the halo is decoration; never fail because of it
            pass

    def _halo_timing(self):
        try:
            first, second = HALO_MS[self.style]
            self.root.tk.eval(f"set ::studio::t1 {first}; set ::studio::t2 {second}")
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ #
    # option database: defaults for plain Tk widgets made later
    # (Tk file dialogs on Linux, menus, the combobox drop-down)
    # ------------------------------------------------------------------ #
    def _options(self):
        r = self.root
        r.configure(background=C["bg"])
        for pattern, value in (("*Background", C["panel"]), ("*Foreground", C["text"]),
                               ("*activeBackground", C["hover"]), ("*activeForeground", C["text"]),
                               ("*selectBackground", C["select"]), ("*selectForeground", C["text"]),
                               ("*highlightBackground", C["panel"]), ("*insertBackground", C["text"]),
                               ("*troughColor", C["bg"]), ("*selectColor", C["select"]),
                               ("*Entry.background", C["field"]), ("*Listbox.background", C["field"]),
                               ("*Text.background", C["field"]),
                               ("*TCombobox*Listbox.font", self.f["base"]),
                               ("*TCombobox*Listbox.selectBackground", C["select"]),
                               ("*TCombobox*Listbox.selectForeground", C["text"]),
                               ("*TCombobox*Listbox.background", C["field"]),
                               ("*TCombobox*Listbox.foreground", C["text"]),
                               ("*Menu.background", C["panel"]), ("*Menu.foreground", C["text"]),
                               ("*Menu.activeBackground", C["select"]),
                               ("*Menu.activeForeground", C["text"]), ("*Menu.relief", "flat"),
                               ("*Menu.font", self.f["base"])):
            r.option_add(pattern, value)

    def menu(self, master, **kw):
        """A popup menu in the current look (rounded on Windows 11 and macOS by the system)."""
        opts = dict(tearoff=False, background=C["panel"], foreground=C["text"], activebackground=C["select"],
                    activeforeground=C["text"], selectcolor=C["accent"], disabledforeground=C["faint"],
                    borderwidth=1, relief="solid", activeborderwidth=0, font=self.f["base"])
        opts.update(kw)
        return tk.Menu(master, **opts)

    # ------------------------------------------------------------------ #
    # ttk styles
    # ------------------------------------------------------------------ #
    def _styles(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")
        self.skin.redraw(s)
        px, f = self.px, self.f
        s.configure(".", background=C["bg"], foreground=C["text"], font=f["base"], bordercolor=C["border"],
                    lightcolor=C["panel"], darkcolor=C["border"], troughcolor=C["bg"], focuscolor=C["accent_line"],
                    selectbackground=C["select"], selectforeground=C["text"], insertcolor=C["text"],
                    fieldbackground=C["field"])
        # clam maps backgrounds by state (grey when active/disabled); the skin's pictures do that now,
        # and the transparent margins of the pictures must always show the surface
        s.map(".", foreground=[("disabled", C["faint"])], background=[], selectbackground=[], selectforeground=[])
        for name in ("TButton", "TNotebook.Tab", "TCombobox", "TEntry", "TSpinbox", "TMenubutton"):
            s.map(name, background=[], lightcolor=[], darkcolor=[], bordercolor=[])
        surfaces = {"": C["bg"], "Panel.": C["panel"], "Raised.": C["raised"], "Soft.": C["accent_soft"],
                    "Field.": C["field"]}

        # frames and cards ----------------------------------------------------
        s.configure("TFrame", background=C["bg"])
        s.configure("Panel.TFrame", background=C["panel"])
        if self.skin.ok:
            s.layout("Card.TFrame", [("Studio.panel", {"sticky": "nswe"})])
            s.layout("Tile.TFrame", [("Studio.card", {"sticky": "nswe"})])
            for kind, style in (("raised", "Well.TFrame"), ("field", "Inset.TFrame"), ("soft", "Soft.TFrame"),
                                ("code", "Code.TFrame"), ("danger", "Danger.TFrame"), ("warn", "Warn.TFrame")):
                s.layout(style, [(f"Studio.well.{kind}", {"sticky": "nswe"})])
        s.configure("Card.TFrame", background=C["bg"])
        s.configure("Tile.TFrame", background=C["bg"])
        s.configure("Panel.Tile.TFrame", background=C["panel"])
        for style in ("Well.TFrame", "Inset.TFrame", "Soft.TFrame", "Code.TFrame", "Danger.TFrame", "Warn.TFrame"):
            s.configure(style, background=C["panel"])

        # labels ----------------------------------------------------------------
        for prefix, bg in surfaces.items():
            s.configure(f"{prefix}TLabel", background=bg, foreground=C["text"])
            s.configure(f"{prefix}Muted.TLabel", background=bg, foreground=C["muted"], font=f["small"])
            s.configure(f"{prefix}Faint.TLabel", background=bg, foreground=C["faint"], font=f["small"])
            s.configure(f"{prefix}Bold.TLabel", background=bg, foreground=C["text"], font=f["bold"])
            s.configure(f"{prefix}Medium.TLabel", background=bg, foreground=C["text"], font=f["medium"])
            s.configure(f"{prefix}Accent.TLabel", background=bg, foreground=C["accent"], font=f["small_bold"])
            s.configure(f"{prefix}H1.TLabel", background=bg, foreground=C["text"], font=f["h1"])
            s.configure(f"{prefix}H2.TLabel", background=bg, foreground=C["text"], font=f["h2"])
            s.configure(f"{prefix}H3.TLabel", background=bg, foreground=C["text"], font=f["h3"])
        s.configure("Section.TLabel", background=C["panel"], foreground=C["text"], font=f["bold"])
        s.configure("Error.TLabel", background=C["panel"], foreground=C["danger"], font=f["small"])
        s.configure("Ok.TLabel", background=C["panel"], foreground=C["ok"], font=f["small"])
        s.configure("Warn.TLabel", background=C["panel"], foreground=C["warn"], font=f["small"])
        if self.skin.ok:
            for kind, style, fg in (("on", "Badge.TLabel", C["on_accent"]), ("off", "SoftBadge.TLabel", C["accent"]),
                                    ("muted", "MutedBadge.TLabel", C["muted"])):
                s.layout(style, [(f"Studio.badge.{kind}", {"sticky": "nswe", "children": [
                    ("Label.padding", {"sticky": "nswe", "children": [("Label.label", {"sticky": "nswe"})]})]})])
                s.configure(style, background=C["panel"], foreground=fg, font=f["small_bold"],
                            padding=(px(7), px(1)), anchor="center")

        # buttons -----------------------------------------------------------------
        def button_layout(style, element):
            children = [("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]
            s.layout(style, [(f"Studio.{element}.button", {"sticky": "nswe", "children": children})])

        if self.skin.ok:
            for style, element in (("TButton", "secondary"), ("Accent.TButton", "primary"),
                                   ("Link.TButton", "ghost"), ("Ghost.TButton", "ghost"), ("Icon.TButton", "ghost"),
                                   ("Toggle.TButton", "ghost"), ("Section.TButton", "ghost"),
                                   ("Small.TButton", "secondary"), ("Big.TButton", "secondary"),
                                   ("Row.TButton", "ghost"),
                                   ("BgLink.TButton", "bgghost")):
                button_layout(style, element)
        s.configure("TButton", background=C["panel"], foreground=C["text"], padding=(px(12), px(5)),
                    font=f["button"], anchor="center", width=0, relief="flat", borderwidth=0,
                    focuscolor=C["panel"])
        s.map("TButton", foreground=[("disabled", C["faint"])])
        s.configure("Accent.TButton", foreground=C["on_accent"], padding=(px(16), px(7)), font=f["button_big"])
        s.map("Accent.TButton", foreground=[("disabled", C["accent_disabled_fg"] if not self.dark else C["muted"])])
        s.configure("Big.Accent.TButton", padding=(px(20), px(10)), font=f["button_big"])
        s.configure("Big.TButton", padding=(px(18), px(10)), font=f["button_big"])
        s.configure("Small.TButton", padding=(px(10), px(3)), font=f["button_small"])
        s.configure("Link.TButton", foreground=C["accent"], padding=(px(7), px(3)), font=f["small_bold"])
        s.map("Link.TButton", foreground=[("disabled", C["faint"]), ("pressed", C["accent_pressed"] if not self.dark
                                                                      else C["accent_hover"]),
                                          ("active", C["accent_hover"] if not self.dark else C["accent_hover"])])
        s.configure("BgLink.TButton", background=C["bg"], foreground=C["accent"], padding=(px(7), px(3)),
                    font=f["small_bold"])
        s.configure("Ghost.TButton", foreground=C["text"], padding=(px(8), px(4)), font=f["button"])
        s.configure("Icon.TButton", foreground=C["muted"], padding=(px(5), px(5)))
        s.map("Icon.TButton", foreground=[("disabled", C["faint"]), ("selected", C["accent"]), ("active", C["text"])])
        s.configure("Toggle.TButton", foreground=C["muted"], padding=(px(8), px(4)), font=f["button_small"])
        s.map("Toggle.TButton", foreground=[("active", C["text"])])
        s.configure("Section.TButton", foreground=C["text"], padding=(px(4), px(4)), font=f["bold"], anchor="w")
        s.configure("Row.TButton", foreground=C["text"], padding=(px(10), px(6)), anchor="w")
        for prefix, bg in surfaces.items():
            if not prefix:
                prefix = "Bg."
            for style in ("TButton", "Accent.TButton", "Small.TButton", "Link.TButton", "Ghost.TButton",
                          "Icon.TButton", "Toggle.TButton", "Section.TButton"):
                s.configure(f"{prefix}{style}", background=bg)

        # menu buttons (View, Save) ---------------------------------------------------
        if self.skin.ok:
            for style, element in (("TMenubutton", "secondary"), ("Ghost.TMenubutton", "ghost")):
                s.layout(style, [(f"Studio.{element}.button", {"sticky": "nswe", "children": [
                    ("Menubutton.padding", {"sticky": "nswe", "children": [
                        ("Studio.menu.indicator", {"side": "right", "sticky": ""}),
                        ("Menubutton.label", {"side": "left", "sticky": ""})]})]})])
        s.configure("TMenubutton", background=C["panel"], foreground=C["text"], padding=(px(10), px(4), px(8), px(4)),
                    font=f["button_small"], relief="flat", borderwidth=0, width=0)
        s.configure("Ghost.TMenubutton", foreground=C["text"])

        # check boxes, radio buttons, switches ------------------------------------------
        if self.skin.ok:
            for style, kind in (("TCheckbutton", "check"), ("TRadiobutton", "radio"), ("Switch.TCheckbutton", "switch")):
                base = "Checkbutton" if "Check" in style else "Radiobutton"
                s.layout(style, [(f"{base}.padding", {"sticky": "nswe", "children": [
                    (f"Studio.{kind}.indicator", {"side": "left", "sticky": ""}),
                    (f"{base}.label", {"side": "left", "sticky": "nswe"})]})])
        for style in ("TCheckbutton", "TRadiobutton", "Switch.TCheckbutton"):
            s.configure(style, background=C["panel"], foreground=C["text"], padding=(0, px(2)),
                        focuscolor=C["panel"], indicatorbackground=C["field"], indicatorforeground=C["accent"])
            s.map(style, background=[("active", C["panel"])], foreground=[("disabled", C["faint"])])
            for prefix, bg in surfaces.items():
                if prefix:
                    s.configure(f"{prefix}{style}", background=bg)
                    s.map(f"{prefix}{style}", background=[("active", bg)])
            s.configure(f"Bg.{style}", background=C["bg"])
            s.map(f"Bg.{style}", background=[("active", C["bg"])])
        s.configure("Small.Switch.TCheckbutton", font=f["small"])

        # category chips (gallery filter) ---------------------------------------------------
        if self.skin.ok:
            s.layout("Chip.TRadiobutton", [("Studio.chip.button", {"sticky": "nswe", "children": [
                ("Radiobutton.padding", {"sticky": "nswe", "children": [
                    ("Radiobutton.label", {"sticky": "nswe"})]})]})])
        s.configure("Chip.TRadiobutton", background=C["panel"], foreground=C["muted"], padding=(px(12), px(4)),
                    font=f["button_small"], focuscolor=C["panel"])
        s.map("Chip.TRadiobutton", foreground=[("selected", C["accent"]), ("active", C["text"])],
              background=[("active", C["panel"])])

        # inputs -------------------------------------------------------------------------
        if self.skin.ok:
            s.layout("TEntry", [("Studio.field", {"sticky": "nswe", "children": [
                ("Entry.padding", {"sticky": "nswe", "children": [("Entry.textarea", {"sticky": "nswe"})]})]})])
            s.layout("Search.TEntry", [("Studio.field", {"sticky": "nswe", "children": [
                ("Studio.search.icon", {"side": "left", "sticky": ""}),
                ("Entry.padding", {"sticky": "nswe", "children": [("Entry.textarea", {"sticky": "nswe"})]})]})])
            s.layout("TCombobox", [("Studio.select", {"sticky": "nswe", "children": [
                ("Studio.Combo.downarrow", {"side": "right", "sticky": "ns"}),
                ("Combobox.padding", {"expand": "1", "sticky": "nswe", "children": [
                    ("Combobox.textarea", {"sticky": "nswe"})]})]})])
            s.layout("TSpinbox", [("Studio.field", {"sticky": "nswe", "children": [
                ("null", {"side": "right", "sticky": "", "children": [
                    ("Studio.Spin.uparrow", {"side": "top", "sticky": "e"}),
                    ("Studio.Spin.downarrow", {"side": "bottom", "sticky": "e"})]}),
                ("Spinbox.padding", {"sticky": "nswe", "children": [("Spinbox.textarea", {"sticky": "nswe"})]})]})])
        for name in ("TEntry", "TCombobox", "TSpinbox", "Search.TEntry"):
            s.configure(name, background=C["panel"], foreground=C["text"], fieldbackground=C["field"],
                        padding=(px(8), px(5)), insertcolor=C["text"], insertwidth=max(1, px(1)),
                        selectbackground=C["select"], selectforeground=C["text"])
            s.map(name, foreground=[("disabled", C["faint"])],
                  fieldbackground=[("disabled", C["bg"])])
        s.configure("TSpinbox", padding=(px(8), px(4), px(2), px(4)))
        s.configure("ComboboxPopdownFrame", background=C["field"], bordercolor=C["border_strong"],
                    lightcolor=C["border_strong"], darkcolor=C["border_strong"], relief="solid", borderwidth=1)
        s.configure("Search.TEntry", padding=(px(6), px(6)))
        s.configure("TCombobox", padding=(px(8), px(5), px(2), px(5)))
        s.map("TCombobox", foreground=[("disabled", C["faint"]), ("readonly", C["text"])],
              selectbackground=[("pressed", C["pressed"]), ("hover", C["hover"]), ("readonly", C["field"])],
              selectforeground=[("readonly", C["text"])])
        for prefix, bg in surfaces.items():
            if prefix:
                for name in ("TEntry", "TCombobox", "TSpinbox"):
                    s.configure(f"{prefix}{name}", background=bg)
        for name in ("TEntry", "TCombobox", "TSpinbox"):
            s.configure(f"Bg.{name}", background=C["bg"])
        s.configure("Bg.Search.TEntry", background=C["bg"])
        s.configure("Panel.Search.TEntry", background=C["panel"])

        # notebook (Plot / Python code / Data summary) --------------------------------------
        if self.skin.ok:
            s.layout("TNotebook", [("Studio.nb.client", {"sticky": "nswe"})])
            s.layout("TNotebook.Tab", [("Studio.tab", {"sticky": "nswe", "children": [
                ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                    ("Notebook.label", {"side": "top", "sticky": ""})]})]})])
        s.configure("TNotebook", background=C["bg"], borderwidth=0, tabmargins=(0, 0, 0, px(6)),
                    bordercolor=C["bg"], lightcolor=C["bg"], darkcolor=C["bg"])
        s.configure("TNotebook.Tab", background=C["bg"], foreground=C["muted"], padding=(px(12), px(5)),
                    font=f["medium"], focuscolor=C["bg"], borderwidth=0)
        s.map("TNotebook.Tab", foreground=[("selected", C["text"]), ("active", C["text"])],
              expand=[("selected", (0, 0, 0, 0))], padding=[("selected", (px(12), px(5)))])

        # tables ----------------------------------------------------------------------------
        s.configure("Treeview", background=C["field"], fieldbackground=C["field"], foreground=C["text"],
                    rowheight=px(28), bordercolor=C["field"], lightcolor=C["field"], darkcolor=C["field"],
                    borderwidth=0, font=f["base"], focuscolor=C["field"])
        s.map("Treeview", background=[("selected", C["select"])], foreground=[("selected", C["text"])])
        s.layout("Treeview.Item", [("Treeitem.padding", {"sticky": "nswe", "children": [
            ("Treeitem.indicator", {"side": "left", "sticky": ""}),
            ("Treeitem.image", {"side": "left", "sticky": ""}),
            ("Treeitem.text", {"side": "left", "sticky": ""})]})])
        s.configure("Treeview.Item", padding=(px(6), 0))
        s.configure("Treeview.Heading", background=C["heading"], foreground=C["muted"], font=f["small_bold"],
                    relief="flat", bordercolor=C["border"], lightcolor=C["heading"], darkcolor=C["border"],
                    padding=(px(10), px(7)), borderwidth=1)
        s.map("Treeview.Heading", background=[("active", C["heading_hover"])],
              lightcolor=[("active", C["heading_hover"])], foreground=[("active", C["text"])])

        # scrollbars, progress, separators --------------------------------------------------
        if self.skin.ok:
            for orient, o in (("Vertical", "v"), ("Horizontal", "h")):
                s.layout(f"{orient}.TScrollbar", [(f"Studio.{o}.trough", {"sticky": "nswe", "children": [
                    (f"Studio.{o}.thumb", {"expand": "1", "sticky": "nswe"})]})])
                s.layout(f"Code.{orient}.TScrollbar", [(f"Studio.{o}.trough", {"sticky": "nswe", "children": [
                    (f"Studio.code{o}.thumb", {"expand": "1", "sticky": "nswe"})]})])
            s.layout("Horizontal.TProgressbar", [("Studio.pb.trough", {"sticky": "nswe", "children": [
                ("Studio.pb.pbar", {"side": "left", "sticky": "ns"})]})])
        for orient in ("Vertical", "Horizontal"):
            s.configure(f"{orient}.TScrollbar", background=C["panel"], troughcolor=C["panel"],
                        bordercolor=C["panel"], lightcolor=C["panel"], darkcolor=C["panel"], arrowcolor=C["muted"],
                        gripcount=0, arrowsize=px(12))
            s.map(f"{orient}.TScrollbar", background=[])
            for prefix, bg in (("", C["panel"]), ("Bg.", C["bg"]), ("Field.", C["field"]), ("Code.", CODE["bg"]),
                               ("Raised.", C["raised"])):
                s.configure(f"{prefix}{orient}.TScrollbar", background=bg, troughcolor=bg, bordercolor=bg,
                            lightcolor=bg, darkcolor=bg)
                # nothing to scroll: same width, no thumb (ScrollFrame switches to this)
                if self.skin.ok:
                    s.layout(f"Hidden.{prefix}{orient}.TScrollbar",
                             [(f"Studio.{orient[0].lower()}.trough", {"sticky": "nswe"})])
                s.configure(f"Hidden.{prefix}{orient}.TScrollbar", background=bg, troughcolor=bg, bordercolor=bg,
                            lightcolor=bg, darkcolor=bg)
        s.configure("Horizontal.TProgressbar", background=C["panel"], troughcolor=C["accent_soft"],
                    bordercolor=C["accent_soft"], lightcolor=C["accent"], darkcolor=C["accent"],
                    thickness=px(6))
        s.configure("TSeparator", background=C["border"])
        s.configure("TPanedwindow", background=C["panel"])
        s.configure("Sash", sashthickness=px(10), gripcount=0, background=C["panel"], lightcolor=C["panel"],
                    bordercolor=C["panel"], sashpad=0)
