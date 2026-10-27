"""TeX formulas as PNG pictures, drawn by matplotlib's mathtext (no LaTeX install needed).

mathtext knows a subset of LaTeX, so `prepare` first rewrites what it lacks into what it has: \\le -> \\leq,
\\tfrac -> \\frac, \\frac1n -> \\frac{1}{n}, \\boxed{x} -> {x}, \\big( -> ( ... Environments (\\begin{cases}, matrices)
are drawn cell by cell and laid out as a grid. What mathtext still can't parse raises TexError, and the caller
shows the TeX source instead.
"""
from __future__ import annotations

import io
import re

# command -> replacement; matched only as a whole command (\le, not \left)
REWRITES = {
    "le": r"\leq", "ge": r"\geq", "ne": r"\neq", "tfrac": r"\frac", "tbinom": r"\binom", "dbinom": r"\binom",
    "boxed": "", "fbox": "", "displaystyle": "", "textstyle": "", "lvert": "|", "rvert": "|",
    "lVert": r"\Vert", "rVert": r"\Vert", "textbf": r"\mathbf", "textit": r"\mathit", "textrm": r"\mathrm",
    "dots": r"\ldots", "iff": r"\Leftrightarrow", "underbrace": "", "underline": r"\overline", "#": "\\# ",   # mathtext fails on \#H, not \# H
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
        return i + (len(m.group(0)) if m else 1)       # a formula may end with a lone backslash
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


def _draw(tex: str, size: float, dpi: float, color: str):
    """One prepared formula as a transparent PIL image."""
    import matplotlib
    from matplotlib import mathtext
    from matplotlib.font_manager import FontProperties
    from PIL import Image

    buf = io.BytesIO()
    try:
        # transparent so it sits on any card colour; a fixed font set so the app's plot style can't change it
        with matplotlib.rc_context({"savefig.transparent": True, "mathtext.fontset": "dejavusans"}):
            mathtext.math_to_image(f"${tex}$", buf, prop=FontProperties(size=size), dpi=dpi, format="png",
                                   color=color)
    except ValueError as exc:       # mathtext's parse errors are ValueErrors with the parser's explanation
        lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
        raise TexError(lines[-1] if lines else "mathtext can't draw this formula") from exc
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


# \begin{cases} and matrices: mathtext has no environments, so each cell is drawn alone and laid out in a grid
_ENV = re.compile(r"\\begin\{(cases|aligned|matrix|[pbBvV]matrix|array)\}(?:\{[^{}]*\})?(.*?)\\end\{\1\}", re.S)
DELIMITERS = {"cases": "{", "pmatrix": "()", "bmatrix": "[]", "Bmatrix": "{}", "vmatrix": "||", "Vmatrix": "||"}


def _delimiter(kind: str, height: int, em: float, color: str, right: bool):
    """A stretched (, [, { or | as a picture `height` pixels tall (drawn 4x bigger, then scaled down smoothly)."""
    from PIL import Image, ImageColor, ImageDraw, ImageOps

    s = 4
    w, h, lw = max(3, round(0.45 * em)) * s, max(8, height) * s, max(1, round(em / 14)) * s
    img = Image.new("RGBA", (w + 2 * lw, h + 2 * lw), (0, 0, 0, 0))
    d, ink = ImageDraw.Draw(img), ImageColor.getrgb(color)
    x0, y0, x1, y1 = lw, lw, w + lw, h + lw
    if kind == "(":
        d.arc((x0, y0, x0 + 2 * w, y1), 90, 270, fill=ink, width=lw)
    elif kind == "[":
        d.line([(x1, y0), (x0 + lw, y0), (x0 + lw, y1), (x1, y1)], fill=ink, width=lw)
    elif kind == "|":
        d.line([(x0 + w // 2, y0), (x0 + w // 2, y1)], fill=ink, width=lw)
    else:  # "{": two quarter arcs at each end and a point in the middle
        r, mid, half = min(h / 6, w), (y0 + y1) / 2, w / 2
        xm = x0 + half
        d.arc((xm, y0, xm + w, y0 + 2 * r), 180, 270, fill=ink, width=lw)
        d.line([(xm, y0 + r), (xm, mid - r)], fill=ink, width=lw)
        d.arc((x0 - half, mid - 2 * r, xm, mid), 0, 90, fill=ink, width=lw)
        d.arc((x0 - half, mid, xm, mid + 2 * r), 270, 360, fill=ink, width=lw)
        d.line([(xm, mid + r), (xm, y1 - r)], fill=ink, width=lw)
        d.arc((xm, y1 - 2 * r, xm + w, y1), 90, 180, fill=ink, width=lw)
    img = img.resize((max(1, img.width // s), max(1, img.height // s)), Image.LANCZOS)
    return ImageOps.mirror(img) if right else img


def _grid(env: str, body: str, size: float, dpi: float, color: str):
    """One environment's cells laid out in rows and columns, with its delimiters."""
    from PIL import Image

    em = size * dpi / 72
    rows = [[c.strip() for c in row.split("&")] for row in re.split(r"\\\\", body) if row.strip()]
    if not rows:
        raise TexError(f"\\begin{{{env}}} has no rows")
    cells = [[_draw(c, size, dpi, color) if c else None for c in row] for row in rows]
    n = max(len(r) for r in cells)
    widths = [max((r[k].width for r in cells if k < len(r) and r[k] is not None), default=0) for k in range(n)]
    heights = [max((c.height for c in r if c is not None), default=round(em)) for r in cells]
    gap = 0 if env == "aligned" else round(em)
    row_gap = round(0.35 * em)
    grid = Image.new("RGBA", (sum(widths) + gap * (n - 1), sum(heights) + row_gap * (len(rows) - 1)), (0, 0, 0, 0))
    y = 0
    for row, h in zip(cells, heights):
        x = 0
        for k, cell in enumerate(row):
            if cell is not None:
                # aligned: right, left, right ... (around the &=); matrices centred; cases and arrays left
                dx = (widths[k] - cell.width if k % 2 == 0 else 0) if env == "aligned" else                     (widths[k] - cell.width) // 2 if env.endswith("matrix") else 0
                grid.alpha_composite(cell, (x + dx, y + (h - cell.height) // 2))
            x += widths[k] + gap
        y += h + row_gap
    pair = DELIMITERS.get(env, "")
    left = _delimiter(pair[0], grid.height, em, color, False) if pair else None
    closing = {")": "(", "]": "[", "}": "{"}.get(pair[1:], pair[1:])          # drawn as the opening one, mirrored
    right = _delimiter(closing, grid.height, em, color, True) if closing else None
    return _row([left, grid, right], round(0.15 * em))


def _row(parts, pad: int):
    """Pictures side by side, centred on one line."""
    from PIL import Image

    parts = [p for p in parts if p is not None]
    out = Image.new("RGBA", (sum(p.width for p in parts) + pad * (len(parts) - 1), max(p.height for p in parts)),
                    (0, 0, 0, 0))
    x = 0
    for p in parts:
        out.alpha_composite(p, (x, (out.height - p.height) // 2))
        x += p.width + pad
    return out


def png(tex: str, size: float = 11.0, dpi: float = 96.0, color: str = "#000000") -> bytes:
    """The formula as a transparent PNG. `size` is in points; raises TexError if mathtext can't parse it.
    \\begin{cases}, matrices and aligned (not nested) are laid out as grids of cells."""
    tex = prepare(tex)
    parts, at = [], 0
    for m in _ENV.finditer(tex):
        if "\\begin" in m.group(2):
            raise TexError(f"nested \\begin{{...}} inside \\begin{{{m.group(1)}}}")
        if tex[at:m.start()].strip():
            parts.append(_draw(tex[at:m.start()], size, dpi, color))
        parts.append(_grid(m.group(1), m.group(2), size, dpi, color))
        at = m.end()
    if tex[at:].strip() or not parts:
        parts.append(_draw(tex[at:], size, dpi, color))
    image = parts[0] if len(parts) == 1 else _row(parts, round(0.15 * size * dpi / 72))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
