"""The ball that follows the mouse over a plot and shows the value of the nearest point.

Works on any 2D axes: line points, scatter points, bars / histogram bins, pie
wedges, hexbin cells, heatmap cells and image pixels. The ball and its label are
drawn with blitting (only the changed pixels are copied), so moving the mouse
never redraws the plot itself. They are never part of the figure, so saved
images and the generated code don't contain them.
"""
from __future__ import annotations

import math

import matplotlib.dates as mdates
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.transforms import IdentityTransform

from .limits import fmt_number, is_date_axis

MAX_POINTS = 400_000   # per axes; more than this and only the first points are searched


def _clean_label(text) -> str:
    text = str(text or "")
    return "" if text.startswith("_") else text


def _short(text, n=34) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _is_categorical(axis) -> bool:
    fmt = type(axis.get_major_formatter()).__name__
    units = type(getattr(axis, "units", None)).__name__
    return fmt in ("StrCategoryFormatter", "FixedFormatter") or units == "UnitData"


def _tick_text(axis, value):
    """The tick label nearest to value (within half a step), or None."""
    try:
        locs = np.asarray(axis.get_ticklocs(), dtype=float)
        labels = [t.get_text() for t in axis.get_ticklabels()]
    except Exception:  # noqa: BLE001
        return None
    if not len(locs) or len(labels) != len(locs):
        return None
    i = int(np.argmin(np.abs(locs - value)))
    step = np.min(np.diff(np.sort(locs))) if len(locs) > 1 else 1.0
    if abs(locs[i] - value) <= max(step, 1e-9) / 2 + 1e-9 and labels[i]:
        return labels[i]
    return None


def _named_tick(axis, value):
    """Tick label at value if the ticks carry names (not just numbers)."""
    text = _tick_text(axis, value)
    if not text:
        return None
    try:
        float(text.replace(",", "").replace("\u2212", "-"))
        return None
    except ValueError:
        return text


def axis_value(axis, v) -> str:
    """How a data value on this axis reads to a person: a date, a category name or a number."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(v):
        return str(v)
    if is_date_axis(axis):
        try:
            d = mdates.num2date(v)
            return d.strftime("%Y-%m-%d") if (d.hour, d.minute, d.second) == (0, 0, 0) else \
                d.strftime("%Y-%m-%d %H:%M")
        except (ValueError, OverflowError):
            pass
    if _is_categorical(axis):
        text = _tick_text(axis, v)
        if text:
            return text
    return fmt_number(v)


def _axis_name(axis, fallback):
    return _short(axis.get_label().get_text() or fallback, 26)


class PointTracker:
    """Attach to a FigureCanvas: shows a ball + value label for the nearest point."""

    def __init__(self, canvas, colors, enabled=lambda: True):
        self.canvas = canvas
        self.fig = canvas.figure
        self.colors = colors          # callable -> {"box": ..., "border": ..., "text": ..., "ring": ...}
        self.enabled = enabled
        self.bg = None
        self.cache = {}
        self.shown = False
        ident = IdentityTransform()
        # sizes are set in screen pixels in _show(), whatever the figure's dpi
        self.halo = Line2D([0], [0], marker="o", linestyle="none", markeredgewidth=0, color="black",
                           alpha=0.38, transform=ident, animated=True)
        self.ball = Line2D([0], [0], marker="o", linestyle="none", transform=ident, animated=True)
        self.label = Text(0, 0, "", transform=ident, animated=True, linespacing=1.35, multialignment="left",
                          bbox=dict(boxstyle="round,pad=0.5"))
        for a in (self.halo, self.ball, self.label):
            a.set_figure(self.fig)    # drawn by us only: never part of the figure itself
        self._last = None          # where the mouse rests (to put the ball back after a zoom)
        self._reshow_job = None
        self.cids = [canvas.mpl_connect("draw_event", self._on_draw),
                     canvas.mpl_connect("motion_notify_event", self._on_move),
                     canvas.mpl_connect("figure_leave_event", self._on_leave),
                     canvas.mpl_connect("button_press_event", self._on_press)]

    def disconnect(self):
        for cid in self.cids:
            self.canvas.mpl_disconnect(cid)
        self.cids = []
        if self._reshow_job is not None:
            try:
                self.canvas.get_tk_widget().after_cancel(self._reshow_job)
            except Exception:  # noqa: BLE001
                pass
            self._reshow_job = None

    # ------------------------------------------------------------------ #
    def _on_draw(self, _event=None):
        try:
            self.bg = self.canvas.copy_from_bbox(self.fig.bbox)
        except Exception:  # noqa: BLE001 - e.g. a backend without blitting
            self.bg = None
        self.cache.clear()
        self.shown = False
        if self._last is not None and self.enabled():
            # zoomed with the wheel under a still mouse: put the ball back once the new picture is up
            widget = getattr(self.canvas, "get_tk_widget", lambda: None)()
            if widget is not None and self._reshow_job is None:
                self._reshow_job = widget.after_idle(self._reshow)

    def _reshow(self):
        self._reshow_job = None
        if self._last is None or self.bg is None or not self.enabled():
            return
        x, y = self._last
        for ax in self.fig.axes:
            if getattr(ax, "name", "") != "rectilinear" or hasattr(ax, "_colorbar") or not ax.get_visible():
                continue
            if ax.bbox.contains(x, y):
                try:
                    xd, yd = ax.transData.inverted().transform((x, y))
                    hit = self.find(ax, x, y, xd, yd)
                except Exception:  # noqa: BLE001
                    hit = None
                if hit is not None:
                    self._show(*hit)
                return

    def _on_press(self, _event=None):
        self._last = None
        self.hide()

    def _on_leave(self, _event=None):
        self._last = None
        self.hide()

    def _on_move(self, event):
        if not self.enabled() or self.bg is None or event.button is not None:
            self.hide()
            return
        ax = event.inaxes
        self._last = (event.x, event.y) if ax is not None else None
        if ax is None or getattr(ax, "name", "") != "rectilinear" or hasattr(ax, "_colorbar"):
            self.hide()
            return
        try:
            hit = self.find(ax, event.x, event.y, event.xdata, event.ydata)
        except Exception:  # noqa: BLE001 - never let hovering raise
            hit = None
        if hit is None:
            self.hide()
        else:
            self._show(*hit)

    # ------------------------------------------------------------------ #
    # finding the point under the mouse
    # ------------------------------------------------------------------ #
    def find(self, ax, x, y, xdata, ydata):
        """(display x, display y, colour, text) for what is under / nearest to (x, y), or None."""
        hit = self._cell(ax, xdata, ydata)
        if hit is not None:
            return hit
        hit = self._wedge(ax, x, y)
        if hit is not None:
            return hit
        groups = self.cache.get(id(ax))
        if groups is None:
            groups = self.cache[id(ax)] = self._collect(ax)
        radius = max(12.0, 0.3 * self.fig.dpi)
        best, best_d = None, radius
        for g in groups:
            if g["kind"] == "bar":
                x0, x1, y0, y1 = g["box"].T
                dx = np.maximum(np.maximum(x0 - x, 0), x - x1)
                dy = np.maximum(np.maximum(y0 - y, 0), y - y1)
                d = np.hypot(dx, dy)
            else:
                d = np.hypot(g["disp"][:, 0] - x, g["disp"][:, 1] - y)
            if not len(d):
                continue
            d = d + g.get("penalty", 0.0)   # faint background lines give way to the main ones
            i = int(np.argmin(d))
            if d[i] < best_d or (best is not None and d[i] == best_d == 0 and g["kind"] != "bar"):
                best, best_d = (g, i), d[i]
        if best is None:
            return None
        g, i = best
        return self._describe(ax, g, i)

    def _collect(self, ax):
        groups = []
        budget = MAX_POINTS
        categorical = _is_categorical(ax.xaxis) or _is_categorical(ax.yaxis)
        for line in ax.lines:
            if not line.get_visible() or line.get_transform() is not ax.transData:
                continue
            if line.get_linestyle() in ("None", "none", "", " ") and line.get_marker() in ("None", "none", "", None, " "):
                continue
            xy = np.asarray(line.get_xydata(), dtype=float)[:budget]
            ok = np.isfinite(xy).all(axis=1)
            xy = xy[ok]
            if not len(xy):
                continue
            budget -= len(xy)
            alpha = line.get_alpha()
            groups.append({"kind": "line", "artist": line, "data": xy, "disp": ax.transData.transform(xy),
                           "color": to_rgba(line.get_color()), "label": _clean_label(line.get_label()),
                           "penalty": 8.0 * self.fig.dpi / 100 if alpha is not None and alpha < 0.5 else 0.0})
        for coll in ax.collections:
            name = type(coll).__name__
            if not coll.get_visible() or name in ("QuadMesh", "QuadContourSet", "TriContourSet", "ContourSet",
                                                  "LineCollection", "EventCollection"):
                continue
            if hasattr(coll, "levels"):
                continue
            offsets = np.asarray(coll.get_offsets(), dtype=float) if hasattr(coll, "get_offsets") else np.empty((0, 2))
            transform = coll.get_offset_transform() if hasattr(coll, "get_offset_transform") else \
                getattr(coll, "_transOffset", None)
            values = coll.get_array()
            if len(offsets) > 1 or (len(offsets) == 1 and name == "PathCollection"):
                # hexbin keeps its centres in data units behind an AffineDeltaTransform
                if transform is not ax.transData and not (type(transform).__name__ == "AffineDeltaTransform"
                                                          and name == "PolyCollection"):
                    continue
                offsets = offsets[:budget]
                ok = np.isfinite(offsets).all(axis=1)
                idx = np.nonzero(ok)[0]
                if not len(idx):
                    continue
                budget -= len(idx)
                faces = coll.get_facecolor()
                groups.append({"kind": "hex" if name == "PolyCollection" and values is not None else "scatter",
                               "artist": coll, "data": offsets[idx], "disp": ax.transData.transform(offsets[idx]),
                               "index": idx, "faces": faces, "values": values,
                               "label": _clean_label(coll.get_label())})
            elif name in ("PolyCollection", "FillBetweenPolyCollection") and values is None and not categorical:
                # filled areas (KDE, area plots): their top edges are the curves
                if coll.get_transform() is not ax.transData:
                    continue
                pts = [p.vertices for p in coll.get_paths() if len(p.vertices)]
                if not pts:
                    continue
                xy = np.concatenate(pts)
                xy = xy[np.isfinite(xy).all(axis=1) & (xy[:, 1] != 0)][:budget]
                if not len(xy):
                    continue
                budget -= len(xy)
                faces = coll.get_facecolor()
                groups.append({"kind": "line", "artist": coll, "data": xy, "disp": ax.transData.transform(xy),
                               "color": tuple(faces[0]) if len(faces) else (0.5, 0.5, 0.5, 1),
                               "label": _clean_label(coll.get_label())})
        rects = [p for p in ax.patches if type(p).__name__ == "Rectangle" and p.get_visible()
                 and p.get_data_transform() is ax.transData and (p.get_width() != 0 and p.get_height() != 0)]
        if rects:
            names = {}
            legend_colors = _legend_colors(ax)
            for cont in getattr(ax, "containers", []):
                patches = getattr(cont, "patches", []) or []
                name = _clean_label(cont.get_label())
                if not name and patches and legend_colors:
                    name = _match_color(to_rgba(patches[0].get_facecolor()), legend_colors)
                for p in patches:
                    names[id(p)] = name
            xs = np.array([[p.get_x(), p.get_y(), p.get_width(), p.get_height()] for p in rects], dtype=float)
            on_x_axis = np.sum(np.isclose(xs[:, 1], 0))
            on_y_axis = np.sum(np.isclose(xs[:, 0], 0))
            horizontal = on_y_axis > on_x_axis
            corners0 = ax.transData.transform(xs[:, :2])
            corners1 = ax.transData.transform(xs[:, :2] + xs[:, 2:])
            box = np.column_stack([np.minimum(corners0[:, 0], corners1[:, 0]), np.maximum(corners0[:, 0], corners1[:, 0]),
                                   np.minimum(corners0[:, 1], corners1[:, 1]), np.maximum(corners0[:, 1], corners1[:, 1])])
            groups.append({"kind": "bar", "artist": rects, "rects": xs, "box": box, "horizontal": horizontal,
                           "names": [names.get(id(p), "") for p in rects]})
        return groups

    def _describe(self, ax, g, i):
        xa, ya = ax.xaxis, ax.yaxis
        xname, yname = _axis_name(xa, "x"), _axis_name(ya, "y")
        lines = []
        if g["kind"] == "bar":
            x0, y0, w, h = g["rects"][i]
            p = g["artist"][i]
            color = to_rgba(p.get_facecolor())
            if g["names"][i]:
                lines.append(_short(g["names"][i]))
            if g["horizontal"]:
                cx, cy = x0 + w, y0 + h / 2
                cat = _tick_text(ya, cy) if _is_categorical(ya) else None
                lines.append(f"{yname}: {cat}" if cat else
                             f"{yname}: {axis_value(ya, min(y0, y0 + h))} – {axis_value(ya, max(y0, y0 + h))}")
                lines.append(f"{xname}: {fmt_number(w)}")
            else:
                cx, cy = x0 + w / 2, y0 + h
                cat = _tick_text(xa, cx) if _is_categorical(xa) else None
                lines.append(f"{xname}: {cat}" if cat else
                             f"{xname}: {axis_value(xa, min(x0, x0 + w))} – {axis_value(xa, max(x0, x0 + w))}")
                lines.append(f"{yname}: {fmt_number(h)}")
            dx, dy = ax.transData.transform((cx, cy))
            return dx, dy, color, "\n".join(lines)
        dx, dy = g["disp"][i]
        vx, vy = g["data"][i]
        if g["kind"] in ("scatter", "hex"):
            j = int(g["index"][i])
            faces, values = g["faces"], g["values"]
            if values is not None and np.ndim(values) == 1 and j < len(values):
                color = g["artist"].to_rgba(values[j])
            elif len(faces) > j:
                color = tuple(faces[j])
            elif len(faces):
                color = tuple(faces[0])
            else:
                color = (0.3, 0.4, 0.8, 1)
            if g["label"]:
                lines.append(_short(g["label"]))
            lines.append(f"{xname}: {axis_value(xa, vx)}")
            lines.append(f"{yname}: {axis_value(ya, vy)}")
            if g["kind"] == "hex" and values is not None and j < len(values):
                lines.append(f"count: {fmt_number(values[j])}")
        else:
            color = g["color"]
            if g["label"]:
                lines.append(_short(g["label"]))
            lines.append(f"{xname}: {axis_value(xa, vx)}")
            lines.append(f"{yname}: {axis_value(ya, vy)}")
        return dx, dy, color, "\n".join(lines)

    def _cell(self, ax, xdata, ydata):
        """Heatmap cells (pcolormesh / sns.heatmap) and image pixels (imshow)."""
        if xdata is None or ydata is None:
            return None
        for mesh in ax.collections:
            if type(mesh).__name__ != "QuadMesh" or not mesh.get_visible() or not hasattr(mesh, "get_coordinates"):
                continue
            coords = np.asarray(mesh.get_coordinates())
            arr = mesh.get_array()
            if coords.ndim != 3 or arr is None:
                continue
            xs, ys = coords[0, :, 0], coords[:, 0, 1]
            ncol, nrow = len(xs) - 1, len(ys) - 1
            col = _bin(xs, xdata)
            row = _bin(ys, ydata)
            if col is None or row is None:
                continue
            arr2 = np.ma.asarray(arr).reshape(nrow, ncol) if np.size(arr) == nrow * ncol else None
            if arr2 is None or np.ma.is_masked(arr2[row, col]):
                continue
            value = arr2[row, col]
            cx, cy = (xs[col] + xs[col + 1]) / 2, (ys[row] + ys[row + 1]) / 2
            dx, dy = ax.transData.transform((cx, cy))
            rlab = _tick_text(ax.yaxis, cy) or fmt_number(row)
            clab = _tick_text(ax.xaxis, cx) or fmt_number(col)
            text = (f"{_axis_name(ax.yaxis, 'row')}: {rlab}\n{_axis_name(ax.xaxis, 'column')}: {clab}\n"
                    f"value: {fmt_number(value)}")
            return dx, dy, mesh.to_rgba(value), text
        for im in ax.images:
            if not im.get_visible():
                continue
            arr = im.get_array()
            if arr is None or np.ndim(arr) < 2:
                continue
            h, w = arr.shape[:2]
            left, right, bottom, top = im.get_extent()
            if im.origin == "upper":
                fy = (ydata - top) / (bottom - top) if bottom != top else -1
            else:
                fy = (ydata - bottom) / (top - bottom) if bottom != top else -1
            fx = (xdata - left) / (right - left) if right != left else -1
            if not (0 <= fx < 1 and 0 <= fy < 1):
                continue
            col, row = int(fx * w), int(fy * h)
            value = arr[row, col]
            cx = left + (col + 0.5) / w * (right - left)
            if im.origin == "upper":
                cy = top + (row + 0.5) / h * (bottom - top)
            else:
                cy = bottom + (row + 0.5) / h * (top - bottom)
            dx, dy = ax.transData.transform((cx, cy))
            if np.ndim(value):
                vtext, color = "colour pixel", (0.5, 0.5, 0.5, 1)
            else:
                if np.ma.is_masked(value):
                    continue
                vtext, color = fmt_number(value), im.to_rgba(value)
            xl, yl = _named_tick(ax.xaxis, cx), _named_tick(ax.yaxis, cy)
            text = (f"{_axis_name(ax.xaxis, 'x')}: {xl or axis_value(ax.xaxis, cx)}\n"
                    f"{_axis_name(ax.yaxis, 'y')}: {yl or axis_value(ax.yaxis, cy)}\nvalue: {vtext}")
            return dx, dy, color, text
        return None

    def _wedge(self, ax, x, y):
        wedges = [p for p in ax.patches if type(p).__name__ == "Wedge" and p.get_visible()]
        if not wedges:
            return None
        for wdg in wedges:
            if wdg.contains_point((x, y)):
                share = (wdg.theta2 - wdg.theta1) / 360.0
                mid = math.radians((wdg.theta1 + wdg.theta2) / 2)
                inner = (wdg.r - wdg.width) if wdg.width else 0.0
                rr = (wdg.r + inner) / 2 if wdg.width else wdg.r * 0.62
                cx, cy = wdg.center[0] + rr * math.cos(mid), wdg.center[1] + rr * math.sin(mid)
                dx, dy = wdg.get_transform().transform((cx, cy))
                name = _clean_label(wdg.get_label())
                text = (f"{_short(name)}\n" if name else "") + f"share: {share * 100:.1f}%"
                return dx, dy, to_rgba(wdg.get_facecolor()), text
        return None

    # ------------------------------------------------------------------ #
    # drawing
    # ------------------------------------------------------------------ #
    def _show(self, x, y, color, text):
        c = self.colors()
        color = to_rgba(color)
        ratio = getattr(self.canvas, "device_pixel_ratio", 1.0) or 1.0
        k = 72.0 * ratio / self.fig.dpi        # points per screen pixel
        self.halo.set_data([x], [y])
        self.halo.set_markersize(17 * k)      # dark rim: the ball stands out on its own line
        self.ball.set_data([x], [y])
        self.ball.set_markersize(12 * k)
        self.ball.set_markeredgewidth(2.4 * k)
        self.ball.set_markerfacecolor(color[:3] + (1.0,))
        self.ball.set_markeredgecolor(c["ring"])
        self.label.set_fontsize(12.5 * k)
        fw, fh = self.fig.bbox.width, self.fig.bbox.height
        off = 14 * ratio
        right = x > fw * 0.6
        high = y > fh * 0.72
        self.label.set_text(text)
        self.label.set_color(c["text"])
        self.label.set_horizontalalignment("right" if right else "left")
        self.label.set_verticalalignment("top" if high else "bottom")
        self.label.set_position((x - off if right else x + off, y - off if high else y + off))
        patch = self.label.get_bbox_patch()
        if patch is not None:
            patch.set_facecolor(c["box"])
            patch.set_edgecolor(c["border"])
            patch.set_linewidth(1.3 * k)
            patch.set_alpha(0.96)
        try:
            renderer = self.canvas.get_renderer()
            bb = self.label.get_window_extent(renderer)
            pad = 8 * ratio
            sx = max(0.0, pad - bb.x0) - max(0.0, bb.x1 - (fw - pad))
            sy = max(0.0, pad - bb.y0) - max(0.0, bb.y1 - (fh - pad))
            if sx or sy:
                px_, py_ = self.label.get_position()
                self.label.set_position((px_ + sx, py_ + sy))
            self.canvas.restore_region(self.bg)
            for a in (self.halo, self.ball, self.label):
                a.draw(renderer)
            self.canvas.blit(self.fig.bbox)
            self.shown = True
        except Exception:  # noqa: BLE001 - e.g. the window is closing
            pass

    def hide(self):
        if not self.shown or self.bg is None:
            self.shown = False
            return
        try:
            self.canvas.restore_region(self.bg)
            self.canvas.blit(self.fig.bbox)
        except Exception:  # noqa: BLE001
            pass
        self.shown = False


def _legend_colors(ax):
    """[(rgb, text)] from the legend of this axes (or the figure), to name bars by colour."""
    legends = [ax.get_legend()] + list(getattr(ax.figure, "legends", []))
    out = []
    for legend in legends:
        if legend is None:
            continue
        handles = getattr(legend, "legend_handles", None) or getattr(legend, "legendHandles", None) or []
        for h, t in zip(handles, legend.get_texts()):
            try:
                rgb = to_rgba(h.get_facecolor() if hasattr(h, "get_facecolor") else h.get_color())[:3]
            except (ValueError, TypeError):
                continue
            out.append((np.array(rgb), t.get_text()))
    return out


def _match_color(rgba, legend_colors):
    rgb = np.array(rgba[:3])
    best = min(legend_colors, key=lambda item: float(np.abs(item[0] - rgb).sum()))
    return best[1] if float(np.abs(best[0] - rgb).sum()) < 0.06 else ""


def _bin(edges, v):
    """Index of the cell between edges[i] and edges[i+1] that contains v (edges may run either way)."""
    edges = np.asarray(edges, dtype=float)
    if len(edges) < 2:
        return None
    lo, hi = min(edges[0], edges[-1]), max(edges[0], edges[-1])
    if not lo <= v <= hi:
        return None
    if edges[0] > edges[-1]:
        i = len(edges) - 2 - int(np.searchsorted(edges[::-1], v, side="right") - 1)
    else:
        i = int(np.searchsorted(edges, v, side="right") - 1)
    return min(max(i, 0), len(edges) - 2)
