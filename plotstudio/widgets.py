"""Reusable widgets: smooth scrolling, tooltips, tiles, multi-select list, placeholder entry,
foldable sections and the ball slider."""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from .skin import png_data, rgba, shape
from .theme import C

WHEEL_STEP = 64     # pixels per wheel notch (at 100 %)


# --------------------------------------------------------------------------- #
# smooth scrolling
# --------------------------------------------------------------------------- #

class SmoothScroller:
    """Eased scrolling for a Canvas (or a Text): each wheel notch glides instead of jumping.

    The view moves 30 % of the remaining distance every frame (about 60 frames a second),
    so it starts fast and settles softly; new notches add to where it is heading.
    """

    def __init__(self, widget):
        self.w = widget
        self.target = None      # Canvas: wanted top, in pixels
        self.left = 0.0         # Text: pixels still to scroll
        self.job = None

    def _metrics(self):
        w = self.w
        region = str(w.cget("scrollregion")).split()
        total = float(region[3]) - float(region[1]) if len(region) == 4 else 0.0
        return total, float(w.winfo_height())

    def scroll(self, pixels: float):
        if isinstance(self.w, tk.Canvas):
            total, view = self._metrics()
            if total <= view + 1:
                return
            start = self.target if self.job is not None and self.target is not None else self.w.canvasy(0)
            self.target = min(max(0.0, start + pixels), total - view)
        else:
            self.left += pixels
        if self.job is None:
            self.job = self.w.after(8, self._step)

    def _step(self):
        self.job = None
        try:
            if isinstance(self.w, tk.Canvas):
                total, view = self._metrics()
                if total <= 0 or self.target is None:
                    return
                current = self.w.canvasy(0)
                diff = self.target - current
                if abs(diff) < 0.75:
                    self.w.yview_moveto(self.target / total)
                    self.target = None
                    return
                step = diff * 0.3
                if abs(step) < 1:
                    step = 1 if diff > 0 else -1
                self.w.yview_moveto((current + step) / total)
            else:
                if abs(self.left) < 1:
                    self.left = 0.0
                    return
                step = self.left * 0.3
                step = int(step) if abs(step) >= 1 else (1 if self.left > 0 else -1)
                self.left -= step
                self.w.yview_scroll(step, "pixels")
        except tk.TclError:
            return
        self.job = self.w.after(14, self._step)


class AutoScrollbar(ttk.Scrollbar):
    """A slim scrollbar whose thumb disappears while everything fits.

    Its space stays reserved, so nothing next to it moves when it comes and goes.
    """

    def __init__(self, master, orient="vertical", style=None, **kw):
        style = style or ("Vertical.TScrollbar" if orient == "vertical" else "Horizontal.TScrollbar")
        super().__init__(master, orient=orient, style=style, **kw)
        self._base = style
        self._hidden = None

    def set(self, first, last):
        super().set(first, last)
        hidden = float(first) <= 0.0 and float(last) >= 1.0
        if hidden != self._hidden:
            self._hidden = hidden
            try:
                self.configure(style=("Hidden." if hidden else "") + self._base)
            except tk.TclError:
                pass


class ScrollFrame(ttk.Frame):
    """A vertically scrollable area. Put child widgets in `.body`.

    The scrollbar is a slim pill that only shows while there is something to scroll.
    """

    def __init__(self, master, theme, bg=None, **kw):
        bg = bg or C["bg"]
        on_bg = bg == C["bg"]
        super().__init__(master, style="TFrame" if on_bg else "Panel.TFrame", **kw)
        self.theme = theme
        self.canvas = tk.Canvas(self, background=bg, highlightthickness=0, borderwidth=0, yscrollincrement=1)
        self.vbar = AutoScrollbar(self, orient="vertical", command=self.canvas.yview,
                                  style="Bg.Vertical.TScrollbar" if on_bg else "Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.body = tk.Frame(self.canvas, background=bg)
        self._win = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.body.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._fit_width)
        self.canvas.scroll_target = True  # found by the mouse-wheel router
        self.canvas.smooth = SmoothScroller(self.canvas)

    def _update_region(self, _event=None):
        self.canvas.configure(scrollregion=(0, 0, self.body.winfo_reqwidth(), self.body.winfo_reqheight()))

    def _fit_width(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)
        self._update_region()

    def to_top(self):
        self.canvas.smooth.target = None
        self.canvas.yview_moveto(0)


def wheel_pixels(event, theme=None) -> float:
    """Pixels to scroll for one wheel event (positive = down)."""
    step = theme.px(WHEEL_STEP) if theme else WHEEL_STEP
    d = getattr(event, "delta", 0) or 0
    if sys.platform == "darwin":
        return -d * step / 8.0
    return -d / 120.0 * step


def install_mousewheel(root: tk.Misc, theme=None):
    """Scroll whatever scrollable area is under the mouse (Windows, macOS, Linux, Tk 8.6 and 9)."""
    step = theme.px(WHEEL_STEP) if theme else WHEEL_STEP

    def target_for(widget):
        w = widget
        while w is not None:
            if getattr(w, "wheel_zoom", False):
                return None  # a plot: it zooms with the wheel itself (see navigate.py)
            if callable(getattr(w, "wheel_handler", None)):
                return w     # e.g. a range slider: the wheel zooms that axis
            if getattr(w, "scroll_target", False):
                return w
            if isinstance(w, (tk.Listbox, ttk.Treeview)):
                return None  # these scroll themselves
            if isinstance(w, tk.Text):
                return w if getattr(w, "smooth", None) else None
            w = getattr(w, "master", None)
        return None

    def scroll(event, pixels=None):
        try:
            widget = root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        target = target_for(widget)
        if target is None:
            return
        if pixels is None:
            pixels = wheel_pixels(event, theme)
        if not pixels:
            return
        if callable(getattr(target, "wheel_handler", None)):
            target.wheel_handler(1 if pixels > 0 else -1)
            return
        smooth = getattr(target, "smooth", None)
        if smooth is not None:
            smooth.scroll(pixels)
            return "break"
        first, last = target.yview()
        if first > 0 or last < 1:
            target.yview_scroll(int(pixels / max(1, step / 3)) or (1 if pixels > 0 else -1), "units")

    def horizontal(event, steps=None):
        try:
            widget = root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        w = widget
        while w is not None and not getattr(w, "xscroll_target", False):
            if getattr(w, "wheel_zoom", False):
                return   # a plot handles Shift + wheel itself
            w = getattr(w, "master", None)
        if w is not None:
            if steps is None:
                steps = -int(event.delta / 120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
            w.xview_scroll(steps * 2, "units")

    def touchpad(event):
        """Tk 9 sends two-finger scrolling as <TouchpadScroll> with packed x/y pixel deltas."""
        d = int(getattr(event, "delta", 0) or 0)
        dy = d & 0xFFFF
        if dy >= 0x8000:
            dy -= 0x10000
        if dy:
            scroll(event, -dy * 1.5)

    root.bind_all("<MouseWheel>", scroll, add="+")
    root.bind_all("<Shift-MouseWheel>", horizontal, add="+")
    root.bind_all("<Button-4>", lambda e: scroll(e, -step), add="+")
    root.bind_all("<Button-5>", lambda e: scroll(e, step), add="+")
    try:
        root.bind_all("<TouchpadScroll>", touchpad, add="+")
    except tk.TclError:   # Tk 8.6
        pass
    # Comboboxes and spinboxes would otherwise change their value while the user scrolls the panel.
    for cls in ("TCombobox", "TSpinbox"):
        root.bind_class(cls, "<MouseWheel>", lambda e: (scroll(e), "break")[1])
        root.bind_class(cls, "<Button-4>", lambda e: (scroll(e, -step), "break")[1])
        root.bind_class(cls, "<Button-5>", lambda e: (scroll(e, step), "break")[1])


# --------------------------------------------------------------------------- #
# tooltips
# --------------------------------------------------------------------------- #

class Tooltip:
    """A short note under a widget while the mouse rests on it (rounded where the system allows)."""

    KEY = "#010203"   # Windows: this colour becomes see-through (outside the rounded corners)

    def __init__(self, widget, text, delay=500):
        self.widget, self.text, self.delay = widget, text, delay
        self.tip = None
        self._after = None
        self._img = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        self._cancel()
        self._after = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None

    def _pointer_inside(self):
        try:
            x, y = self.widget.winfo_pointerxy()
            w = self.widget.winfo_containing(x, y)
        except (KeyError, tk.TclError):
            return False
        while w is not None:
            if w is self.widget:
                return True
            w = getattr(w, "master", None)
        return False

    def _watch(self):
        """Hide when the mouse has left (e.g. the page changed under a still mouse: no <Leave> comes)."""
        if self.tip is None:
            return
        if not self._pointer_inside():
            self._hide()
            return
        self.widget.after(300, self._watch)

    def _theme(self):
        w = self.widget
        while w is not None:
            t = getattr(w, "theme", None)
            if t is not None and hasattr(t, "px"):
                return t
            w = getattr(w, "master", None)
        return None

    def _show(self):
        if self.tip or not self.text or not self._pointer_inside():
            return
        theme = self._theme()
        px = theme.px if theme else (lambda n: n)
        font = theme.f["small"] if theme else None
        x = self.widget.winfo_rootx() + px(6)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + px(6)
        tip = self.tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        try:
            tip.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        pad_x, pad_y = px(10), px(7)
        rounded = sys.platform in ("win32", "darwin") and theme is not None and theme.skin.ok
        if rounded:
            outside = "systemTransparent" if sys.platform == "darwin" else self.KEY
            try:
                if sys.platform == "darwin":
                    tip.wm_attributes("-transparent", True)
                else:
                    tip.wm_attributes("-transparentcolor", self.KEY)
                tip.configure(background=outside)
            except tk.TclError:
                rounded = False
        if rounded:
            canvas = tk.Canvas(tip, background=outside, highlightthickness=0, borderwidth=0)
            label = tk.Label(canvas, text=self.text, background=C["tip_bg"], foreground=C["tip_fg"], justify="left",
                             wraplength=px(340), font=font, padx=0, pady=0, borderwidth=0)
            w, h = label.winfo_reqwidth() + 2 * pad_x, label.winfo_reqheight() + 2 * pad_y
            img = shape(w, h, px(7), fill=rgba(C["tip_bg"]))
            self._img = tk.PhotoImage(master=tip, data=png_data(img))
            canvas.configure(width=w, height=h)
            canvas.create_image(0, 0, anchor="nw", image=self._img)
            canvas.create_window(pad_x, pad_y, anchor="nw", window=label)
            canvas.pack()
        else:
            tip.configure(background=C["border_dark"])
            tk.Label(tip, text=self.text, background=C["tip_bg"], foreground=C["tip_fg"], justify="left",
                     wraplength=px(340), padx=pad_x, pady=pad_y - 1, font=font).pack(padx=1, pady=1)
        # keep the tip on screen
        tip.update_idletasks()
        sw = tip.winfo_screenwidth()
        if x + tip.winfo_reqwidth() > sw - 8:
            x = max(8, sw - 8 - tip.winfo_reqwidth())
        tip.wm_geometry(f"+{x}+{y}")
        self.widget.after(300, self._watch)

    def _hide(self, _e=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None
            self._img = None


# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #

class PlaceholderEntry(ttk.Entry):
    """ttk.Entry that shows grey hint text while empty."""

    def __init__(self, master, placeholder="", textvariable=None, **kw):
        self.var = textvariable or tk.StringVar()
        super().__init__(master, textvariable=self.var, **kw)
        self.placeholder = placeholder
        self._showing = False
        self.bind("<FocusIn>", self._focus_in, add="+")
        self.bind("<FocusOut>", self._focus_out, add="+")
        self._focus_out()

    def _focus_in(self, _e=None):
        if self._showing:
            self._showing = False
            self.var.set("")
            self.configure(foreground=C["text"])

    def _focus_out(self, _e=None):
        if not self.var.get() and self.placeholder:
            self._showing = True
            self.var.set(self.placeholder)
            self.configure(foreground=C["faint"])

    def on_theme(self):
        self.configure(foreground=C["faint"] if self._showing else C["text"])

    def value(self) -> str:
        return "" if self._showing else self.var.get()

    def set_value(self, text: str):
        self._showing = False
        self.configure(foreground=C["text"])
        self.var.set(text)
        try:
            focused = self.focus_get()
        except (KeyError, tk.TclError):   # focus inside a combobox drop-down
            focused = None
        if not text and focused is not self:
            self._focus_out()


class MultiPicker(tk.Frame):
    """A list of column names where several can be chosen, with All / None and a filter box."""

    def __init__(self, master, theme, on_change=None, height=7):
        super().__init__(master, background=C["panel"])
        self.theme, self.on_change = theme, on_change
        self.items, self.selected, self.visible = [], set(), []
        self.filter = PlaceholderEntry(self, placeholder="Filter columns…", style="Panel.Search.TEntry")
        self.filter.var.trace_add("write", lambda *_: self._refill())
        box = ttk.Frame(self, style="Inset.TFrame", padding=theme.px(3))
        self.lb = tk.Listbox(box, selectmode="multiple", exportselection=False, activestyle="none", height=height,
                             font=theme.f["base"], background=C["field"], foreground=C["text"], borderwidth=0,
                             highlightthickness=0, selectbackground=C["select"], selectforeground=C["text"],
                             selectborderwidth=0)
        sb = AutoScrollbar(box, orient="vertical", command=self.lb.yview, style="Field.Vertical.TScrollbar")
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True, padx=(theme.px(2), 0), pady=theme.px(2))
        sb.pack(side="right", fill="y", pady=theme.px(2))
        self.box = box
        bar = tk.Frame(self, background=C["panel"])
        self.count = ttk.Label(bar, style="Panel.Muted.TLabel")
        self.count.pack(side="left", padx=(theme.m, 0))
        ttk.Button(bar, text="None", style="Link.TButton", command=self.select_none).pack(side="right")
        ttk.Button(bar, text="All", style="Link.TButton", command=self.select_all).pack(side="right")
        self.bar = bar
        self.lb.bind("<<ListboxSelect>>", self._on_select)
        self._layout()

    def _layout(self):
        for w in (self.filter, self.box, self.bar):
            w.pack_forget()
        if len(self.items) > 10:
            self.filter.pack(fill="x", pady=(0, self.theme.px(4)))
        self.box.pack(fill="both", expand=True)
        self.bar.pack(fill="x", pady=(self.theme.px(2), 0))

    def set_items(self, items, selected=()):
        self.items = list(items)
        self.selected = {s for s in selected if s in self.items}
        self.filter.set_value("")
        self._layout()
        self._refill()

    def _refill(self):
        text = self.filter.value().strip().lower()
        self.visible = [i for i in self.items if text in str(i).lower()] if text else list(self.items)
        self.lb.delete(0, "end")
        for i, name in enumerate(self.visible):
            self.lb.insert("end", f"  {name}")
            if name in self.selected:
                self.lb.selection_set(i)
        self._update_count()

    def _on_select(self, _e=None):
        chosen = set(self.lb.curselection())
        for i, name in enumerate(self.visible):
            if i in chosen:
                self.selected.add(name)
            else:
                self.selected.discard(name)
        self._update_count()
        if self.on_change:
            self.on_change()

    def _update_count(self):
        self.count.configure(text=f"{len(self.selected)} of {len(self.items)} selected")

    def select_all(self):
        self.selected.update(self.visible)
        self.lb.selection_set(0, "end")
        self._on_select()

    def select_none(self):
        self.selected.difference_update(self.visible)
        self.lb.selection_clear(0, "end")
        self._on_select()

    def get(self) -> list:
        return [i for i in self.items if i in self.selected]


# --------------------------------------------------------------------------- #
# layout pieces
# --------------------------------------------------------------------------- #

class Section(tk.Frame):
    """A titled block in the left panel; click the title (or press Space on it) to fold it."""

    def __init__(self, master, theme, title, collapsed=False, extra=None, bg=None):
        bg = bg or C["panel"]
        super().__init__(master, background=bg)
        self.theme = theme
        head = tk.Frame(self, background=bg)
        head.pack(fill="x", pady=(theme.px(10), theme.px(4)))
        self.open_img = theme.icon_states("chevron_down", 16, normal="muted", active="text")
        self.closed_img = theme.icon_states("chevron_right", 16, normal="muted", active="text")
        style = "Section.TButton" if bg == C["panel"] else "Bg.Section.TButton"
        self.button = ttk.Button(head, text=title, image=self.open_img, compound="left", style=style,
                                 command=self.toggle)
        self.button.pack(side="left")
        self.title = self.button
        if extra is not None:
            extra(head).pack(side="right")
        self.body = tk.Frame(self, background=bg)
        self.collapsed = False
        self.body.pack(fill="x")
        if collapsed:
            self.toggle()

    def toggle(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.body.pack_forget()
            self.button.configure(image=self.closed_img)
        else:
            self.body.pack(fill="x")
            self.button.configure(image=self.open_img)


class Tile(ttk.Frame):
    """A rounded card you can click: hover tint, a pressed look, Enter/Space and a focus ring."""

    def __init__(self, master, command=None, style="Tile.TFrame", **kw):
        super().__init__(master, style=style, cursor="hand2", takefocus=1, **kw)
        self.command = command
        self._inside = False
        self.bind("<Return>", lambda e: self.invoke())
        self.bind("<space>", lambda e: self.invoke())
        self.bind("<KP_Enter>", lambda e: self.invoke())

    def wire(self):
        """Call after the children are made: hover / press / click on the whole tile."""
        def walk(w):
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")
            w.bind("<ButtonPress-1>", self._press, add="+")
            w.bind("<ButtonRelease-1>", self._release, add="+")
            for child in w.winfo_children():
                walk(child)
        walk(self)

    def _surface(self, hover):
        set_bg(self, C["card_hover"] if hover else C["panel"], skip_ttk=True)

    def _enter(self, _e=None):
        if not self._inside:
            self._inside = True
            self.state(["active"])
            self._surface(True)

    def _leave(self, _e=None):
        try:
            x, y = self.winfo_pointerxy()
            inside = self.winfo_containing(x, y)
        except (KeyError, tk.TclError):
            inside = None
        while inside is not None:
            if inside is self:
                return
            inside = getattr(inside, "master", None)
        self.reset()

    def reset(self):
        self._inside = False
        try:
            self.state(["!active", "!pressed"])
        except tk.TclError:
            return
        self._surface(False)

    def _press(self, _e=None):
        self.state(["pressed"])

    def _release(self, e=None):
        pressed = "pressed" in self.state()
        self.state(["!pressed"])
        if pressed and self._inside:
            self.invoke()

    def invoke(self):
        if self.command:
            self.command()

    def on_theme(self):
        self._surface(self._inside)


def hover_bind(widget, on_enter, on_leave):
    """Enter/leave for a frame and all its children, without flicker between children."""
    def enter(_e):
        on_enter()

    def leave(_e):
        x, y = widget.winfo_pointerxy()
        inside = widget.winfo_containing(x, y)
        while inside is not None:
            if inside is widget:
                return
            inside = getattr(inside, "master", None)
        on_leave()

    def walk(w):
        w.bind("<Enter>", enter, add="+")
        w.bind("<Leave>", leave, add="+")
        for child in w.winfo_children():
            walk(child)
    walk(widget)


def bind_click(widget, func):
    widget.bind("<Button-1>", lambda e: func(), add="+")
    for child in widget.winfo_children():
        bind_click(child, func)


def set_bg(widget, color, skip_ttk=False):
    if not (skip_ttk and isinstance(widget, ttk.Widget)):
        try:
            widget.configure(background=color)
        except tk.TclError:
            pass
    for child in widget.winfo_children():
        if not isinstance(child, ttk.Widget):
            set_bg(child, color)


# --------------------------------------------------------------------------- #
# ball slider
# --------------------------------------------------------------------------- #

class RangeSlider(tk.Canvas):
    """A slider with ball handles: two balls pick a range, one ball picks a value.

    Positions are fractions from 0 to 1 (left -> right, or bottom -> top when vertical).
      on_change(lo, hi)   while a ball is dragged (with one ball, `hi` is the value)
      on_release(lo, hi)  when the mouse button is let go (or after a key press)
      on_reset()          on double-click (or Escape)
    Drag the coloured part between two balls to move the whole range.
    Keyboard: Tab to the slider, arrows move a ball (Shift: bigger steps), Space switches
    between the two balls, Home / End go to the ends, Escape resets.
    """

    def __init__(self, master, theme, orient="horizontal", two=True, on_change=None, on_release=None,
                 on_reset=None, bg=None, min_gap=0.005):
        self.theme = theme
        self.size = theme.px(26)
        horizontal = orient == "horizontal"
        kw = {"height": self.size} if horizontal else {"width": self.size}
        super().__init__(master, highlightthickness=0, borderwidth=0, background=bg or C["panel"],
                         cursor="hand2", takefocus=1, **kw)
        self.horizontal, self.two = horizontal, two
        self.on_change, self.on_release, self.on_reset = on_change, on_release, on_reset
        self.min_gap = min_gap
        self.lo, self.hi = 0.0, 1.0
        self.span = None          # (start, end) pixels along the slider; None = whole length
        self.enabled = True
        self._drag = None         # "lo" | "hi" | "both"
        self._grab = 0.0
        self._hover = None
        self._key_ball = "hi"     # the ball the arrow keys move
        self._focus = False
        self._key_job = None
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Double-Button-1>", self._double)
        self.bind("<Motion>", self._hover_move)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", lambda e: self._set_focus(False))
        for key, d in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1)):
            self.bind(f"<{key}>", lambda e, d=d: self._key_move(d * 0.01))
            self.bind(f"<Shift-{key}>", lambda e, d=d: self._key_move(d * 0.1))
        self.bind("<Home>", lambda e: self._key_move(-2.0))
        self.bind("<End>", lambda e: self._key_move(2.0))
        self.bind("<space>", self._switch_ball)
        self.bind("<Escape>", lambda e: self._double())

    # geometry ------------------------------------------------------------
    def _length(self):
        return max(self.winfo_width() if self.horizontal else self.winfo_height(), 1)

    def _ends(self):
        r = self.size / 2
        if self.span:
            a, b = self.span
            a, b = max(a, r), min(b, self._length() - r)
            if b - a > 20:
                return a, b
        return r, max(r + 1, self._length() - r)

    def _pos(self, t):
        a, b = self._ends()
        return a + t * (b - a) if self.horizontal else b - t * (b - a)

    def _frac(self, p):
        a, b = self._ends()
        t = (p - a) / (b - a) if self.horizontal else (b - p) / (b - a)
        return min(1.0, max(0.0, t))

    def _along(self, event):
        return event.x if self.horizontal else event.y

    def _xy(self, p):
        c = self.size / 2
        return (p, c) if self.horizontal else (c, p)

    # public ---------------------------------------------------------------
    def set(self, lo=None, hi=None):
        if lo is not None:
            self.lo = min(1.0, max(0.0, float(lo)))
        if hi is not None:
            self.hi = min(1.0, max(0.0, float(hi)))
        if self.two and self.lo > self.hi:
            self.lo, self.hi = self.hi, self.lo
        self.redraw()

    def set_span(self, start=None, end=None):
        """Line the track up with something else (e.g. the plot's axis), in pixels along the slider."""
        span = None if start is None or end is None else (float(start), float(end))
        if span != self.span:
            self.span = span
            self.redraw()

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "", takefocus=1 if enabled else 0)
        self.redraw()

    def on_theme(self):
        self.redraw()

    # drawing --------------------------------------------------------------
    def redraw(self):
        self.delete("all")
        a, b = self._ends()
        c = self.size / 2
        width = max(2, self.theme.px(4))
        if self.horizontal:
            self.create_line(a, c, b, c, fill=C["track"], width=width, capstyle="round")
        else:
            self.create_line(c, a, c, b, fill=C["track"], width=width, capstyle="round")
        lo = self.lo if self.two else 0.0
        p0, p1 = self._pos(lo), self._pos(self.hi)
        color = C["accent"] if self.enabled else C["faint"]
        if abs(p1 - p0) > 0.5:
            self.create_line(*self._xy(p0), *self._xy(p1), fill=color, width=width, capstyle="round")
        handles = ("lo", "hi") if self.two else ("hi",)
        photos = self.theme.skin.photos
        for name in handles:
            t = self.lo if name == "lo" else self.hi
            x, y = self._xy(self._pos(t))
            if not self.enabled:
                key = "ball:disabled"
            elif self._focus and name == self._key_ball:
                key = "ball:focus"
            elif name == self._drag or name == self._hover or self._drag == "both":
                key = "ball:active"
            else:
                key = "ball:normal"
            img = photos.get(key)
            if img is not None:
                self.create_image(x, y, image=img)
            else:   # no Pillow: plain circles
                r = self.theme.px(8)
                self.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=C["panel"], width=2)

    # mouse ----------------------------------------------------------------
    def _nearest(self, p):
        """The ball under the mouse (or None)."""
        r = self.theme.px(12)
        best, dist = None, r + 1
        for name in (("lo", "hi") if self.two else ("hi",)):
            d = abs(self._pos(self.lo if name == "lo" else self.hi) - p)
            if d < dist or (d == dist and name == "lo" and self.hi >= 0.999):
                best, dist = name, d
        return best

    def _press(self, event):
        if not self.enabled:
            return
        p = self._along(event)
        t = self._frac(p)
        name = self._nearest(p)
        if name is None:
            if self.two and min(self._pos(self.lo), self._pos(self.hi)) < p < max(self._pos(self.lo), self._pos(self.hi)):
                self._drag, self._grab = "both", t - self.lo
                self.redraw()
                return
            name = "hi" if not self.two or abs(t - self.hi) <= abs(t - self.lo) else "lo"
            self._drag = name
            self._key_ball = name
            self._move(name, t)
            return
        self._drag = name
        self._key_ball = name
        self.redraw()

    def _move(self, name, t):
        if name == "lo":
            self.lo = min(t, self.hi - self.min_gap)
            self.lo = max(0.0, self.lo)
        elif name == "hi":
            self.hi = max(t, self.lo + self.min_gap) if self.two else t
            self.hi = min(1.0, self.hi)
        else:
            width = self.hi - self.lo
            lo = min(max(0.0, t - self._grab), 1.0 - width)
            self.lo, self.hi = lo, lo + width
        self.redraw()
        if self.on_change:
            self.on_change(self.lo if self.two else 0.0, self.hi)

    def _motion(self, event):
        if self._drag:
            self._move(self._drag, self._frac(self._along(event)))

    def _release(self, _event=None):
        if self._drag:
            self._drag = None
            self.redraw()
            if self.on_release:
                self.on_release(self.lo if self.two else 0.0, self.hi)

    def _double(self, _event=None):
        if not self.enabled:
            return
        self._drag = None
        if self.on_reset:
            self.on_reset()
        elif self.two:
            self.set(0.0, 1.0)
            if self.on_release:
                self.on_release(0.0, 1.0)

    def _hover_move(self, event):
        if not self._drag and self.enabled:
            self._set_hover(self._nearest(self._along(event)))

    def _set_hover(self, name):
        if name != self._hover:
            self._hover = name
            if not self._drag:
                self.redraw()

    # keyboard ---------------------------------------------------------------
    def _focus_in(self, _e=None):
        self._set_focus(bool(getattr(self.theme, "_keyboard", True)))

    def _set_focus(self, on):
        if on != self._focus:
            self._focus = on
            self.redraw()

    def _switch_ball(self, _e=None):
        if self.two:
            self._key_ball = "lo" if self._key_ball == "hi" else "hi"
            self._set_focus(True)
            self.redraw()
        return "break"

    def _key_move(self, delta):
        if not self.enabled:
            return "break"
        self._set_focus(True)
        name = self._key_ball if self.two else "hi"
        current = self.lo if name == "lo" else self.hi
        self._move(name, min(1.0, max(0.0, current + delta)))
        if self._key_job:
            self.after_cancel(self._key_job)
        self._key_job = self.after(350, self._key_commit)
        return "break"

    def _key_commit(self):
        self._key_job = None
        if self.on_release:
            self.on_release(self.lo if self.two else 0.0, self.hi)


def release_canvas(canvas) -> None:
    """Destroy a matplotlib FigureCanvasTkAgg and free its picture now, on the window's thread.

    Left to the garbage collector, the picture could be deleted while a background thread runs,
    and Tk only allows that from the thread that made it ("main thread is not in main loop")."""
    photo = getattr(canvas, "_tkphoto", None)
    try:
        canvas.get_tk_widget().destroy()
    except tk.TclError:
        pass
    if photo is not None and getattr(photo, "name", None):
        try:
            photo.tk.call("image", "delete", photo.name)
        except tk.TclError:
            pass
        photo.name = None
