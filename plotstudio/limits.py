"""X/Y range sliders: from slider positions (0..1) to axis limits, and back.

The sliders run from one end of the plot's automatic range ("natural" limits,
recorded before any slider limits are applied) to the other. Log axes move
in log steps, date axes produce pd.Timestamp limits.
"""
from __future__ import annotations

import math

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.axes import Axes

_DATE_FORMATTERS = tuple(getattr(mdates, n) for n in ("AutoDateFormatter", "ConciseDateFormatter", "DateFormatter")
                         if hasattr(mdates, n))
_DATE_CONVERTERS = tuple(getattr(mdates, n) for n in ("DateConverter", "_SwitchableDateConverter",
                                                       "ConciseDateConverter") if hasattr(mdates, n))


def is_date_axis(axis) -> bool:
    if isinstance(axis.get_major_formatter(), _DATE_FORMATTERS):
        return True
    conv = axis.get_converter() if hasattr(axis, "get_converter") else getattr(axis, "converter", None)
    return bool(_DATE_CONVERTERS) and isinstance(conv, _DATE_CONVERTERS)


def axis_spec(ax, which: str) -> dict | None:
    """The current range of one axis as a 'spec': {"natural": (a, b), "scale": ..., "date": ...}."""
    axis = ax.xaxis if which == "x" else ax.yaxis
    lim = ax.get_xlim() if which == "x" else ax.get_ylim()
    a, b = float(lim[0]), float(lim[1])
    if not (math.isfinite(a) and math.isfinite(b)) or a == b:
        return None
    scale = "log" if axis.get_scale() == "log" and min(a, b) > 0 else "linear"
    return {"natural": (a, b), "scale": scale, "date": is_date_axis(axis)}


def zoom_info(ax, fig) -> dict | None:
    """The automatic X and Y ranges of a plain 2D axes, or None if it can't be zoomed."""
    if not isinstance(ax, Axes) or getattr(ax, "name", "") != "rectilinear" or ax not in fig.axes:
        return None
    info = {"ax": ax, "x": axis_spec(ax, "x"), "y": axis_spec(ax, "y")}
    if info["x"] is None and info["y"] is None:
        return None
    return info


def set_fracs(ax, which: str, spec, lo: float, hi: float):
    """Show the part lo..hi (fractions of the automatic range) of one axis."""
    if is_full(lo, hi):
        a, b = spec["natural"]
    else:
        a, b = to_value(spec, lo), to_value(spec, hi)
    (ax.set_xlim if which == "x" else ax.set_ylim)(a, b)


def to_value(spec, t: float) -> float:
    a, b = spec["natural"]
    if spec["scale"] == "log":
        la, lb = math.log10(a), math.log10(b)
        return 10 ** (la + t * (lb - la))
    return a + t * (b - a)


def to_frac(spec, v: float) -> float:
    a, b = spec["natural"]
    try:
        if spec["scale"] == "log":
            la, lb = math.log10(a), math.log10(b)
            t = (math.log10(v) - la) / (lb - la)
        else:
            t = (float(v) - a) / (b - a)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0.0
    return min(1.0, max(0.0, t))


def fracs(spec, lim) -> tuple:
    """Slider positions that show the axis limits `lim`."""
    t0, t1 = to_frac(spec, lim[0]), to_frac(spec, lim[1])
    return (min(t0, t1), max(t0, t1))


def is_full(lo: float, hi: float) -> bool:
    return lo <= 0.001 and hi >= 0.999


def _round_to(v: float, span: float) -> float:
    if span <= 0 or not math.isfinite(span):
        return v
    digits = 3 - int(math.floor(math.log10(span)))
    return round(v, digits)


def _num_to_timestamp(v: float) -> pd.Timestamp:
    ts = pd.Timestamp(mdates.num2date(v))
    return ts.tz_convert(None) if ts.tzinfo is not None else ts


def limit_values(spec, lo: float, hi: float):
    """Tidy limit values for the code (None = the full automatic range)."""
    if is_full(lo, hi):
        return None
    v0, v1 = to_value(spec, lo), to_value(spec, hi)
    if spec["date"]:
        span_days = abs(v1 - v0)
        out = []
        for v in (v0, v1):
            ts = _num_to_timestamp(v)
            out.append(ts.round("D") if span_days > 3 else ts.round("min"))
        if out[0] == out[1]:
            out = [_num_to_timestamp(v0).round("s"), _num_to_timestamp(v1).round("s")]
        return tuple(out)
    if spec["scale"] == "log":
        out = tuple(round(v, 2 - int(math.floor(math.log10(abs(v))))) for v in (v0, v1))
    else:
        span = abs(v1 - v0)
        out = (_round_to(v0, span), _round_to(v1, span))
    if out[0] == out[1]:
        out = (v0, v1)
    return tuple(int(v) if float(v).is_integer() and abs(v) < 1e15 else float(v) for v in out)


def fmt_number(v) -> str:
    """Short, readable number: 1,460  ·  0.734  ·  12.5  ·  3.2e-06."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(v):
        return str(v)
    a = abs(v)
    if a >= 1e15 or (0 < a < 1e-4):
        return f"{v:.3g}"
    if v.is_integer():
        return f"{int(v):,}"
    if a >= 1000:
        return f"{v:,.1f}"
    if a >= 1:
        return f"{v:,.3f}".rstrip("0").rstrip(".")
    return f"{v:.4g}"


def fmt_limit(value) -> str:
    if isinstance(value, pd.Timestamp):
        return str(value.date()) if value == value.normalize() else value.strftime("%Y-%m-%d %H:%M")
    return fmt_number(value)
