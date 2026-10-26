"""Dark "graph paper" for a finished matplotlib figure.

Only the paper changes: figure and axes background, grid, spines, tick labels,
axis labels, titles and legend boxes. The data keep their colours, with two
exceptions:

* neutral black/grey helper marks (outlines, reference lines, black points) would
  vanish on dark paper: they become light grey, and white separators between bars or
  wedges take the paper colour, the way matplotlib's own dark style does it;
* the Studio colours (engine.STUDIO_COLORS) switch to their dark-paper steps: the
  same eight hues, re-stepped so each keeps 3:1 against the dark paper and stays
  apart from its neighbours for colour-blind readers.

The generated code is not changed; this is only how the app shows the figure.
"""
from __future__ import annotations

from matplotlib.colors import to_rgba, to_rgba_array

PAPER = {
    "face": "#1c1c1f",       # around the plot (same as the dark cards: theme.DARK["panel"])
    "axes": "#1c1c1f",       # inside the axes when the style has no separate axes colour
    "axes_raised": "#232327",  # inside the axes for styles with a grey axes background (darkgrid ...)
    "grid": "#2f2f35",
    "spine": "#4c4c55",
    "text": "#c9c9d1",
    "title": "#f0f0f3",
    "light": "#d4d4da",      # replaces black / dark-grey helper marks
    "legend_face": "#232327",
    "legend_edge": "#3a3a41",
}

# Studio colours (light paper) -> their steps for dark paper
STUDIO_DARK = {
    "#2a78d6": "#3987e5", "#eb6834": "#d95926", "#1baf7a": "#199e70", "#eda100": "#c98500",
    "#e87ba4": "#d55181", "#008300": "#008300", "#6250d6": "#9085e9", "#e34948": "#e66767",
}


def _desaturate(rgb, prop):
    """seaborn's desaturate(): scale the HLS saturation (its bar and box plots use 0.75)."""
    import colorsys
    h, l, s = colorsys.rgb_to_hls(*rgb)
    return colorsys.hls_to_rgb(h, l, s * prop)


_STEPS = []
for _a, _b in STUDIO_DARK.items():
    _la, _lb = to_rgba(_a)[:3], to_rgba(_b)[:3]
    _STEPS.append((_la, _lb))
    _STEPS.append((_desaturate(_la, 0.75), _desaturate(_lb, 0.75)))   # seaborn bars, boxes, violins


def _step(rgba):
    """The dark-paper step of a Studio colour (keeping its alpha), or None."""
    if rgba is None or len(rgba) < 4:
        return None
    r, g, b = rgba[:3]
    for (lr, lg, lb), dark in _STEPS:
        if abs(r - lr) < 0.004 and abs(g - lg) < 0.004 and abs(b - lb) < 0.004:
            return tuple(dark) + (rgba[3],)
    return None


def _is_neutral(rgba) -> bool:
    r, g, b = rgba[:3]
    return max(r, g, b) - min(r, g, b) < 0.07


def _lum(rgba) -> float:
    r, g, b = rgba[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _swap_one(rgba, p, white_to=None):
    """New colour for a neutral dark (or, with white_to, white) colour, or a Studio colour; None = keep."""
    if rgba is None or len(rgba) < 4 or rgba[3] == 0:
        return None
    if not _is_neutral(rgba):
        return _step(rgba)
    lum = _lum(rgba)
    if lum < 0.32:
        return to_rgba(p["light"], rgba[3])
    if white_to is not None and lum > 0.93:
        return to_rgba(white_to, rgba[3])
    return None


def _swap_array(colors, p, white_to=None):
    try:
        arr = to_rgba_array(colors)
    except (ValueError, TypeError):
        return None
    if arr.size == 0:
        return None
    changed = False
    out = arr.copy()
    for i, c in enumerate(arr):
        new = _swap_one(c, p, white_to)
        if new is not None:
            out[i] = new
            changed = True
    return out if changed else None


def _text(t, color):
    if t is None or not t.get_text():
        return
    rgba = to_rgba(t.get_color())
    if _is_neutral(rgba) and _lum(rgba) < 0.5:
        t.set_color(color)


def _line(line, p):
    for get, set_ in (("get_color", "set_color"), ("get_markerfacecolor", "set_markerfacecolor"),
                      ("get_markeredgecolor", "set_markeredgecolor")):
        try:
            value = getattr(line, get)()
            if isinstance(value, str) and value in ("none", "auto"):
                continue
            new = _swap_one(to_rgba(value), p, white_to=p["axes"] if get == "get_markeredgecolor" else None)
        except (ValueError, TypeError):
            continue
        if new is not None:
            getattr(line, set_)(new)


def _collection(coll, p):
    mapped = coll.get_array() is not None   # colours come from a colormap (heatmaps, hexbin): keep the faces
    try:
        edges = _swap_array(coll.get_edgecolor(), p, white_to=p["axes"])
        if edges is not None:
            coll.set_edgecolor(edges)
        if not mapped:
            faces = _swap_array(coll.get_facecolor(), p)
            if faces is not None:
                coll.set_facecolor(faces)
    except (ValueError, TypeError, AttributeError):
        pass


def _patch(patch, p):
    try:
        edge = _swap_one(to_rgba(patch.get_edgecolor()), p, white_to=p["axes"])
        if edge is not None:
            patch.set_edgecolor(edge)
        face = _swap_one(to_rgba(patch.get_facecolor()), p)
        if face is not None:
            patch.set_facecolor(face)
    except (ValueError, TypeError):
        pass


def _legend(legend, p):
    if legend is None:
        return
    frame = legend.get_frame()
    frame.set_facecolor(p["legend_face"])
    frame.set_edgecolor(p["legend_edge"])
    for t in legend.get_texts():
        _text(t, p["text"])
    _text(legend.get_title(), p["text"])
    handles = getattr(legend, "legend_handles", None) or getattr(legend, "legendHandles", None) or []
    for h in handles:
        _artist(h, p)


def _artist(a, p):
    kind = type(a).__name__
    if kind == "Line2D":
        _line(a, p)
    elif hasattr(a, "get_offsets") or kind.endswith("Collection"):
        _collection(a, p)
    elif hasattr(a, "get_facecolor") and hasattr(a, "get_edgecolor"):
        _patch(a, p)


def _axes3d(ax, p):
    ax.set_facecolor(p["face"])
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        try:
            axis.set_pane_color(to_rgba(p["axes"], 1.0))
            axis.line.set_color(p["spine"])
            axis.label.set_color(p["text"])
            info = getattr(axis, "_axinfo", None)
            if isinstance(info, dict) and isinstance(info.get("grid"), dict):
                info["grid"]["color"] = to_rgba(p["grid"])
        except Exception:  # noqa: BLE001 - differs between matplotlib versions
            pass
    for which in ("x", "y", "z"):
        try:
            ax.tick_params(axis=which, colors=p["text"])
        except Exception:  # noqa: BLE001
            pass


def _axes(ax, p, fig_face=None):
    if getattr(ax, "name", "") == "3d":
        _axes3d(ax, p)
    else:
        own = to_rgba(ax.get_facecolor())
        same = fig_face is not None and all(abs(a - b) < 0.01 for a, b in zip(own[:3], fig_face[:3]))
        # a plain white axes melts into the paper; a tinted one (darkgrid ...) stays a shade lighter
        ax.set_facecolor(p["axes"] if same or own[3] == 0 else p["axes_raised"])
        for spine in ax.spines.values():
            spine.set_edgecolor(p["spine"])
        ax.tick_params(axis="both", which="both", colors=p["text"], grid_color=p["grid"])
        for axis in (ax.xaxis, ax.yaxis):
            axis.label.set_color(p["text"])
            axis.offsetText.set_color(p["text"])
    for t in (ax.title, getattr(ax, "_left_title", None), getattr(ax, "_right_title", None)):
        _text(t, p["title"])
    _legend(ax.get_legend(), p)
    for line in ax.lines:
        _line(line, p)
    for coll in ax.collections:
        _collection(coll, p)
    for patch in ax.patches:
        _patch(patch, p)
    # numbers printed inside heatmap cells / images sit on coloured cells: leave them alone
    has_cells = bool(ax.images) or any(type(c).__name__ == "QuadMesh" for c in ax.collections)
    if not has_cells:
        for t in ax.texts:
            box = t.get_bbox_patch()
            if box is None:
                _text(t, p["text"])
                continue
            face = to_rgba(box.get_facecolor())
            if _is_neutral(face) and _lum(face) > 0.85:   # a white note box (e.g. the regression equation)
                box.set_facecolor(p["legend_face"])
                box.set_edgecolor(p["legend_edge"])
                _text(t, p["text"])


def apply_dark_paper(fig, p: dict = PAPER):
    """Recolour a finished figure for dark paper (in place)."""
    fig_face = to_rgba(fig.patch.get_facecolor())
    fig.patch.set_facecolor(p["face"])
    fig.patch.set_edgecolor(p["face"])
    for t in fig.texts:
        _text(t, p["title"])
    for legend in fig.legends:
        _legend(legend, p)
    for ax in fig.axes:
        _axes(ax, p, fig_face)
    fig._studio_paper = "dark"
    return fig
