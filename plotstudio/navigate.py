"""Moving and zooming a plot with the mouse, without picking a toolbar mode first.

    drag                    move the plot (left / right / up / down)
    mouse wheel             zoom in / out around the mouse      Shift: only X   Ctrl: only Y
    over the tick labels    wheel or drag works on that one axis
    right-drag / Ctrl+drag  draw a box and zoom into it
    double-click            show everything again
    arrow keys, + and -     move / zoom after clicking the plot (0 or Home: everything)

Every axis keeps its "automatic" range (what the plot showed before any zooming)
and the view stays inside it, so the data can't get lost off-screen. The
positions are handled as fractions of that range (see limits.py), which makes
log axes and date axes behave like ordinary ones.

When matplotlib's own Pan or Zoom toolbar button is on, the toolbar is in charge
and this class does nothing.
"""
from __future__ import annotations

import sys

from .limits import axis_spec, fracs, set_fracs, to_frac

MIN_SPAN = 1e-5        # smallest visible part of an axis (fraction of its automatic range)
WHEEL_ZOOM = 0.8       # one wheel notch shows 80 % of the current range
KEY_PAN = 0.1          # an arrow key moves the view by 10 %
DRAG_START = 3         # pixels the mouse must move before a press becomes a drag
TICK_ZONE = 48         # pixels outside the axes that count as "over the tick labels"

SHIFT, CONTROL = 0x0001, 0x0004   # Tk event.state bits


def movable(ax) -> bool:
    """Plain 2D axes with something to move (not colour bars, pie charts, pictures or 3D)."""
    if getattr(ax, "name", "") != "rectilinear" or not ax.get_visible() or not ax.get_navigate():
        return False
    if hasattr(ax, "_colorbar") or ax.get_label() == "<colorbar>":
        return False
    if not ax.axison:
        return False
    if not ax.get_frame_on() and not len(ax.get_xticks()) and not len(ax.get_yticks()):
        return False   # e.g. a pie chart
    return True


def _state(event) -> int:
    gui = getattr(event, "guiEvent", None)
    try:
        return int(getattr(gui, "state", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _view(lo, hi):
    return min(lo, hi), max(lo, hi)


def pan_fracs(lo, hi, shift):
    """Move the window lo..hi by `shift` (fractions), staying inside 0..1."""
    shift = max(-lo, min(1.0 - hi, shift))
    return lo + shift, hi + shift


def zoom_fracs(lo, hi, centre, factor):
    """Zoom the window lo..hi around `centre` by `factor` (<1 = in), staying inside 0..1."""
    span = hi - lo
    new = min(1.0, max(MIN_SPAN, span * factor))
    if span <= 0:
        return 0.0, 1.0
    a = centre - (centre - lo) * new / span
    b = a + new
    if a < 0:
        a, b = 0.0, new
    if b > 1:
        a, b = 1.0 - new, 1.0
    return max(0.0, a), min(1.0, b)


class Navigator:
    """Mouse and keyboard move / zoom for every movable axes of one figure canvas."""

    def __init__(self, canvas, toolbar=None, natural=None, on_done=None, on_reset=None, scroll=None,
                 enabled=lambda: True, on_status=None):
        """
        natural   {id(ax): {"x": spec, "y": spec}} automatic ranges known in advance (e.g. before
                  slider limits were applied); other axes use the range they show now
        on_done   on_done(ax) after a move / zoom has finished (to update the code)
        on_reset  on_reset() after a double-click reset
        scroll    scroll(step, horizontal) -> True if the window scrolled instead (figure bigger than the view)
        """
        self.canvas = canvas
        self.fig = canvas.figure
        self.toolbar = toolbar
        self.on_done = on_done
        self.on_reset = on_reset
        self.scroll = scroll
        self.enabled = enabled
        self.on_status = on_status
        self.specs = {}
        natural = natural or {}
        for ax in self.fig.axes:
            if movable(ax):
                known = natural.get(id(ax)) or {}
                self.specs[id(ax)] = {"ax": ax,
                                      "x": known.get("x") or axis_spec(ax, "x"),
                                      "y": known.get("y") or axis_spec(ax, "y")}
        self._drag = None
        self._wheel_job = None
        self._wheel_axes = set()
        self._cursor = None
        self._last_ax = None
        self._pushed_home = False
        self._clipped = set()
        self.cids = [canvas.mpl_connect("button_press_event", self._press),
                     canvas.mpl_connect("motion_notify_event", self._motion),
                     canvas.mpl_connect("button_release_event", self._release),
                     canvas.mpl_connect("scroll_event", self._wheel),
                     canvas.mpl_connect("figure_leave_event", lambda e: self._set_cursor(""))]
        widget = self._widget()
        if widget is not None:
            widget.wheel_zoom = True   # the app's mouse-wheel router leaves this widget to us
            for seq, func in (("<Left>", lambda e: self._key_pan(-1, 0)), ("<Right>", lambda e: self._key_pan(1, 0)),
                              ("<Up>", lambda e: self._key_pan(0, 1)), ("<Down>", lambda e: self._key_pan(0, -1)),
                              ("<plus>", lambda e: self._key_zoom(WHEEL_ZOOM)),
                              ("<equal>", lambda e: self._key_zoom(WHEEL_ZOOM)),
                              ("<KP_Add>", lambda e: self._key_zoom(WHEEL_ZOOM)),
                              ("<minus>", lambda e: self._key_zoom(1 / WHEEL_ZOOM)),
                              ("<KP_Subtract>", lambda e: self._key_zoom(1 / WHEEL_ZOOM)),
                              ("<Key-0>", lambda e: self.reset()), ("<Home>", lambda e: self.reset())):
                widget.bind(seq, lambda e, f=func: (f(e), "break")[1], add="+")

    # ------------------------------------------------------------------ #
    def disconnect(self):
        for cid in self.cids:
            self.canvas.mpl_disconnect(cid)
        self.cids = []
        self._cancel_wheel()

    def _widget(self):
        try:
            return self.canvas.get_tk_widget()
        except AttributeError:
            return None

    def _active(self) -> bool:
        if not self.enabled() or not self.specs:
            return False
        mode = getattr(self.toolbar, "mode", "") if self.toolbar is not None else ""
        return not mode   # matplotlib's Pan / Zoom tool is in charge while it is switched on

    def _status(self, text):
        if self.on_status:
            self.on_status(text)

    # ------------------------------------------------------------------ #
    # where is the mouse?
    # ------------------------------------------------------------------ #
    def target(self, x, y):
        """(spec entry, "xy" | "x" | "y") for the axes under (or next to) the mouse, or (None, "")."""
        best = None
        for entry in self.specs.values():
            bb = entry["ax"].bbox
            if bb.x0 <= x <= bb.x1 and bb.y0 <= y <= bb.y1:
                return entry, "xy"
            zone = TICK_ZONE * self._ratio()
            if bb.x0 <= x <= bb.x1 and bb.y0 - zone <= y < bb.y0 and entry["x"]:
                best = best or (entry, "x")
            elif bb.y0 <= y <= bb.y1 and bb.x0 - zone <= x < bb.x0 and entry["y"]:
                best = best or (entry, "y")
        return best or (None, "")

    def _ratio(self):
        return getattr(self.canvas, "device_pixel_ratio", 1.0) or 1.0

    # ------------------------------------------------------------------ #
    # changing the view
    # ------------------------------------------------------------------ #
    def current(self, entry, which):
        spec = entry[which]
        ax = entry["ax"]
        return fracs(spec, ax.get_xlim() if which == "x" else ax.get_ylim())

    def show(self, entry, which, lo, hi):
        spec = entry[which]
        if spec is None:
            return
        ax = entry["ax"]
        if id(ax) not in self._clipped:
            # numbers printed in heatmap cells etc. would otherwise spill out of a zoomed plot
            self._clipped.add(id(ax))
            for t in ax.texts:
                if t.get_transform() is ax.transData:
                    t.set_clip_on(True)
        lo, hi = _view(lo, hi)
        set_fracs(ax, which, spec, lo, hi)

    def anchor(self, entry, which):
        """Where bars start (value 0) as a fraction, if the axes has bars growing along `which`
        and their base line is in view: zooming then keeps the bars standing on it."""
        spec = entry[which]
        if not spec or spec["scale"] != "linear":
            return None
        want = "vertical" if which == "y" else "horizontal"
        bars = [c for c in getattr(entry["ax"], "containers", [])
                if type(c).__name__ == "BarContainer" and (getattr(c, "orientation", None) or "vertical") == want]
        a, b = spec["natural"]
        if not bars or not min(a, b) <= 0 <= max(a, b):
            return None
        t = to_frac(spec, 0.0)
        lo, hi = self.current(entry, which)
        return t if lo - 1e-9 <= t <= hi + 1e-9 else None

    def _push_home(self):
        """Make sure the toolbar's Back / Home know the view from before our first change."""
        tb = self.toolbar
        if tb is None or self._pushed_home:
            return
        self._pushed_home = True
        try:
            if tb._nav_stack() is None:
                tb.push_current()
        except Exception:  # noqa: BLE001 - private matplotlib API: history is a bonus
            pass

    def _push(self):
        try:
            if self.toolbar is not None:
                self.toolbar.push_current()
        except Exception:  # noqa: BLE001
            pass

    def _redraw(self):
        self.canvas.draw_idle()

    def _finish(self, axes):
        self._push()
        if self.on_done:
            for ax in axes:
                self.on_done(ax)

    # ------------------------------------------------------------------ #
    # mouse
    # ------------------------------------------------------------------ #
    def _press(self, event):
        if not self._active() or event.x is None:
            return
        widget = self._widget()
        if widget is not None:
            try:
                widget.focus_set()   # so the arrow keys and + / - reach the plot
            except Exception:  # noqa: BLE001
                pass
        entry, mask = self.target(event.x, event.y)
        if entry is None:
            return
        self._last_ax = entry
        button = int(getattr(event, "button", 0) or 0)
        if getattr(event, "dblclick", False) and button == 1:
            self._drag = None
            self.reset()
            return
        box = button == 3 or (button == 1 and _state(event) & CONTROL)
        if box and mask != "xy":
            box = False
        if button not in (1, 2, 3):
            return
        if button == 3 and not box:
            return
        self._drag = {"entry": entry, "mask": mask, "x0": event.x, "y0": event.y, "moved": False,
                      "box": box, "start": {w: self.current(entry, w) for w in ("x", "y") if entry[w]}}

    def _motion(self, event):
        if event.x is None:
            return
        d = self._drag
        if d is None:
            if self._active():
                entry, mask = self.target(event.x, event.y)
                self._last_ax = entry or self._last_ax
                self._set_cursor({"xy": "fleur", "x": "sb_h_double_arrow", "y": "sb_v_double_arrow"}.get(mask, ""))
            return
        dx, dy = event.x - d["x0"], event.y - d["y0"]
        if not d["moved"]:
            if abs(dx) < DRAG_START and abs(dy) < DRAG_START:
                return
            d["moved"] = True
            self._push_home()
            self._set_cursor("crosshair" if d["box"] else "fleur")
        if d["box"]:
            try:
                self.toolbar.draw_rubberband(event, d["x0"], d["y0"], event.x, event.y)
            except Exception:  # noqa: BLE001 - the box is only a guide
                pass
            return
        entry, mask = d["entry"], d["mask"]
        bb = entry["ax"].bbox
        for which, delta, size in (("x", dx, bb.width), ("y", dy, bb.height)):
            if which not in mask or which not in d["start"] or size <= 0:
                continue
            lo, hi = d["start"][which]
            self.show(entry, which, *pan_fracs(lo, hi, -delta / size * (hi - lo)))
        self._redraw()

    def _release(self, event):
        d, self._drag = self._drag, None
        if d is None:
            return
        if d["box"]:
            try:
                self.toolbar.remove_rubberband()
            except Exception:  # noqa: BLE001
                pass
            if d["moved"] and event.x is not None:
                self._box_zoom(d, event.x, event.y)
        elif d["moved"]:
            self._finish([d["entry"]["ax"]])
        self._set_cursor("")

    def _box_zoom(self, d, x1, y1):
        entry = d["entry"]
        bb = entry["ax"].bbox
        small = 6 * self._ratio()
        changed = False
        for which, a, b, start, size in (("x", d["x0"], x1, bb.x0, bb.width), ("y", d["y0"], y1, bb.y0, bb.height)):
            if which not in d["start"] or abs(b - a) < small or size <= 0:
                continue   # a thin box zooms only the other direction
            lo, hi = d["start"][which]
            fa = min(1.0, max(0.0, (min(a, b) - start) / size))
            fb = min(1.0, max(0.0, (max(a, b) - start) / size))
            new_lo, new_hi = lo + fa * (hi - lo), lo + fb * (hi - lo)
            if new_hi - new_lo >= MIN_SPAN:
                self.show(entry, which, new_lo, new_hi)
                changed = True
        if changed:
            self._redraw()
            self._finish([entry["ax"]])

    def _wheel(self, event):
        if event.x is None:
            return
        step = float(getattr(event, "step", 0) or 0)
        if sys.platform == "darwin" and step and abs(step) < 1:
            step = 1.0 if step > 0 else -1.0   # macOS sends tiny steps
        if not step:
            return
        state = _state(event)
        shift, ctrl = bool(state & SHIFT), bool(state & CONTROL)
        # A figure bigger than the window (Fit to window off): the wheel scrolls, Ctrl + wheel zooms.
        scrollable = self.scroll is not None and self.scroll(step, shift, probe=True)
        if scrollable and not ctrl:
            self.scroll(step, shift)
            return
        entry, mask = self.target(event.x, event.y) if self._active() else (None, "")
        if entry is None:
            if scrollable:
                self.scroll(step, shift)
            return
        if mask == "xy" and not scrollable:
            if shift and not ctrl:
                mask = "x"
            elif ctrl and not shift:
                mask = "y"
        self._push_home()
        factor = WHEEL_ZOOM ** step
        bb = entry["ax"].bbox
        for which, pos, start, size in (("x", event.x, bb.x0, bb.width), ("y", event.y, bb.y0, bb.height)):
            if which not in mask or not entry[which] or size <= 0:
                continue
            lo, hi = self.current(entry, which)
            centre = self.anchor(entry, which)
            if centre is None:
                centre = lo + min(1.0, max(0.0, (pos - start) / size)) * (hi - lo)
            self.show(entry, which, *zoom_fracs(lo, hi, centre, factor))
        self._redraw()
        self._wheel_axes.add(entry["ax"])
        self._schedule_wheel_end()

    def _schedule_wheel_end(self):
        widget = self._widget()
        if widget is None:
            self._wheel_end()
            return
        self._cancel_wheel()
        self._wheel_job = widget.after(350, self._wheel_end)

    def _cancel_wheel(self):
        widget = self._widget()
        if self._wheel_job is not None and widget is not None:
            try:
                widget.after_cancel(self._wheel_job)
            except Exception:  # noqa: BLE001
                pass
        self._wheel_job = None

    def _wheel_end(self):
        self._wheel_job = None
        axes, self._wheel_axes = list(self._wheel_axes), set()
        if axes:
            self._finish(axes)

    def _set_cursor(self, name):
        if name == self._cursor:
            return
        widget = self._widget()
        if widget is None:
            return
        try:
            widget.configure(cursor=name)
            self._cursor = name
        except Exception:  # noqa: BLE001 - unknown cursor name on this system
            pass

    # ------------------------------------------------------------------ #
    # keyboard and reset
    # ------------------------------------------------------------------ #
    def _key_entry(self):
        if self._last_ax is not None:
            return self._last_ax
        return next(iter(self.specs.values()), None)

    def _key_pan(self, sx, sy):
        entry = self._key_entry()
        if entry is None or not self._active():
            return
        self._push_home()
        for which, s in (("x", sx), ("y", sy)):
            if s and entry[which]:
                lo, hi = self.current(entry, which)
                self.show(entry, which, *pan_fracs(lo, hi, s * KEY_PAN * (hi - lo)))
        self._redraw()
        self._wheel_axes.add(entry["ax"])
        self._schedule_wheel_end()

    def _key_zoom(self, factor):
        entry = self._key_entry()
        if entry is None or not self._active():
            return
        self._push_home()
        for which in ("x", "y"):
            if entry[which]:
                lo, hi = self.current(entry, which)
                centre = self.anchor(entry, which)
                self.show(entry, which, *zoom_fracs(lo, hi, (lo + hi) / 2 if centre is None else centre, factor))
        self._redraw()
        self._wheel_axes.add(entry["ax"])
        self._schedule_wheel_end()

    def reset(self):
        """Show the whole automatic range of every axes again."""
        if not self.specs:
            return
        self._cancel_wheel()
        self._wheel_axes = set()
        for entry in self.specs.values():
            for which in ("x", "y"):
                if entry[which]:
                    self.show(entry, which, 0.0, 1.0)
        self._redraw()
        self._push()
        if self.on_reset:
            self.on_reset()
        self._status("Showing everything again.")
