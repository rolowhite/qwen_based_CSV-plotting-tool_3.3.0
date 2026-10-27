"""TeX formulas as PNG pictures, drawn by matplotlib's mathtext (no LaTeX install needed).

mathtext knows a subset of LaTeX, so `prepare` first rewrites what it lacks into what it has: \\le -> \\leq,
\\tfrac -> \\frac, \\frac1n -> \\frac{1}{n}, \\boxed{x} -> {x}, \\big( -> ( ... Environments (\\begin{cases}, matrices)
stay unsupported: `png` raises TexError and the caller shows the TeX source instead.
"""
from __future__ import annotations

import io
import re

# command -> replacement; matched only as a whole command (\le, not \left)
REWRITES = {
    "le": r"\leq", "ge": r"\geq", "ne": r"\neq", "tfrac": r"\frac", "tbinom": r"\binom", "dbinom": r"\binom",
    "boxed": "", "fbox": "", "displaystyle": "", "textstyle": "", "lvert": "|", "rvert": "|",
    "lVert": r"\Vert", "rVert": r"\Vert", "textbf": r"\mathbf", "textit": r"\mathit", "textrm": r"\mathrm",
    "dots": r"\ldots", "iff": r"\Leftrightarrow", "underbrace": "", "#": "\\# ",   # mathtext fails on \#H, not \# H
    **{f"{size}{side}": "" for size in ("big", "Big", "bigg", "Bigg") for side in ("", "l", "r", "m")},
}
# commands whose arguments may be written without braces (\frac12, \sqrt x, \mathbf v)
ARGS = {"frac": 2, "dfrac": 2, "binom": 2, "sqrt": 1, "mathbf": 1, "mathrm": 1, "mathit": 1, "mathbb": 1,
        "mathcal": 1, "text": 1, "overline": 1}
_CMD = re.compile(r"\\([A-Za-z]+|#)")


class TexError(ValueError):
    """mathtext can't draw this formula."""


def _rewrite(tex: str) -> str:
    return _CMD.sub(lambda m: REWRITES.get(m.group(1), m.group(0)), tex)


def _group_end(tex: str, i: int) -> int:
    """Index just past the } that closes the { at tex[i] (len(tex) when it is never closed)."""
    depth = 0
    while i < len(tex):
        c = tex[i]
        if c == "\\":
            i += 2
            continue
        depth += {"{": 1, "}": -1}.get(c, 0)
        i += 1
        if depth == 0:
            return i
    return len(tex)


def _token_end(tex: str, i: int) -> int:
    """Index just past one TeX token at tex[i]: a {group}, a \\command or one character."""
    if tex[i] == "{":
        return _group_end(tex, i)
    if tex[i] == "\\":
        m = re.match(r"\\(?:[A-Za-z]+|.)", tex[i:])
        return i + len(m.group(0))
    return i + 1


def _brace(tex: str) -> str:
    out, i = [], 0
    while i < len(tex):
        m = _CMD.match(tex, i) if tex[i] == "\\" else None
        if m is None or m.group(1) not in ARGS:
            end = _token_end(tex, i)
            piece = tex[i:end]
            out.append("{" + _brace(piece[1:-1]) + "}" if piece.startswith("{") and piece.endswith("}") and
                       len(piece) > 1 else piece)
            i = end
            continue
        out.append(m.group(0))
        i = m.end()
        if m.group(1) == "sqrt" and i < len(tex) and tex[i] == "[":
            close = tex.find("]", i)
            if close < 0:
                break
            out.append(tex[i:close + 1])
            i = close + 1
        for _ in range(ARGS[m.group(1)]):
            while i < len(tex) and tex[i] == " ":
                i += 1
            if i >= len(tex):
                break
            end = _token_end(tex, i)
            piece = tex[i:end]
            inner = piece[1:-1] if piece.startswith("{") and piece.endswith("}") and len(piece) > 1 else piece
            out.append("{" + _brace(inner) + "}")
            i = end
    return "".join(out)


def prepare(tex: str) -> str:
    """The formula rewritten into the LaTeX subset mathtext understands."""
    return _brace(_rewrite(tex.replace("\n", " ").strip()))


def png(tex: str, size: float = 11.0, dpi: float = 96.0, color: str = "#000000") -> bytes:
    """The formula as a transparent PNG. `size` is in points; raises TexError if mathtext can't parse it."""
    import matplotlib
    from matplotlib import mathtext
    from matplotlib.font_manager import FontProperties

    buf = io.BytesIO()
    try:
        # transparent so it sits on any card colour; a fixed font set so the app's plot style can't change it
        with matplotlib.rc_context({"savefig.transparent": True, "mathtext.fontset": "dejavusans"}):
            mathtext.math_to_image(f"${prepare(tex)}$", buf, prop=FontProperties(size=size), dpi=dpi, format="png",
                                   color=color)
    except ValueError as exc:       # mathtext's parse errors are ValueErrors with the parser's explanation
        lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
        raise TexError(lines[-1] if lines else "mathtext can't draw this formula") from exc
    return buf.getvalue()
