"""The drawn look of every control: rounded buttons, fields, tabs, cards, scrollbars and icons.

ttk "image" elements are 9-slice pictures: the corners keep their shape and the edges
stretch, so one small picture per state draws a rounded control of any size. The
pictures are drawn with Pillow at 4x and scaled down, which gives smooth corners.

Every interactive picture keeps a thin transparent margin around the shape. It holds
the keyboard focus ring and the short halo that plays after a click, and it keeps
neighbouring controls from touching. Transparent pixels show the style's `background`
option, so each style says which surface it sits on (panel, window, raised ...).

When the look changes, the same PhotoImage objects are redrawn in place, so every
widget that uses them updates at once.
"""
from __future__ import annotations

import base64
import io
import math
import tkinter as tk

S = 4   # supersampling factor

# --------------------------------------------------------------------------- #
# colour + Pillow helpers
# --------------------------------------------------------------------------- #


def rgb(color: str):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def rgba(color, alpha=1.0):
    if color is None:
        return None
    if isinstance(color, tuple):
        return color[:3] + (int(round((color[3] if len(color) > 3 else 255) * alpha)),)
    return rgb(color) + (int(round(255 * alpha)),)


def png_data(image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _pil():
    from PIL import Image, ImageChops, ImageDraw
    return Image, ImageChops, ImageDraw


def _reduce(img):
    if hasattr(img, "reduce"):
        return img.reduce(S)
    Image = _pil()[0]
    return img.resize((img.width // S, img.height // S), getattr(Image, "Resampling", Image).LANCZOS)


def _rr_mask(size, box, radius):
    """An 'L' mask with a filled rounded rectangle (box = x0, y0, x1, y1 inclusive)."""
    Image, _, ImageDraw = _pil()
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    x0, y0, x1, y1 = box
    if x1 < x0 or y1 < y0:
        return mask
    radius = max(0, min(radius, (x1 - x0 + 1) / 2, (y1 - y0 + 1) / 2))
    if hasattr(d, "rounded_rectangle"):
        d.rounded_rectangle(box, radius=radius, fill=255)
    else:   # Pillow < 8.2
        r = int(radius)
        d.rectangle((x0 + r, y0, x1 - r, y1), fill=255)
        d.rectangle((x0, y0 + r, x1, y1 - r), fill=255)
        for cx, cy in ((x0, y0), (x1 - 2 * r, y0), (x0, y1 - 2 * r), (x1 - 2 * r, y1 - 2 * r)):
            d.ellipse((cx, cy, cx + 2 * r, cy + 2 * r), fill=255)
    return mask


def mix(a, b, t):
    """Colour a moved a share t of the way to colour b (hex in, hex out)."""
    ra, rb = rgb(a), rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb))


def _gradient(canvas, top, bottom, mask, y0, y1):
    """Composite a vertical gradient (top colour at row y0 -> bottom colour at row y1, held beyond) through a
    mask."""
    Image = _pil()[0]
    h = canvas.size[1]
    span = max(1, y1 - y0)
    column = Image.new("RGBA", (1, h))
    px = column.load()
    for y in range(h):
        t = min(1.0, max(0.0, (y - y0) / span))
        px[0, y] = tuple(round(a + (b - a) * t) for a, b in zip(top[:3], bottom[:3])) + (255,)
    layer = column.resize(canvas.size)
    layer.putalpha(mask)
    return Image.alpha_composite(canvas, layer)


def _paint(canvas, color, mask):
    """Composite a solid colour through a mask onto the canvas (respects the colour's alpha)."""
    if color is None:
        return canvas
    Image = _pil()[0]
    layer = Image.new("RGBA", canvas.size, color[:3] + (0,))
    alpha = color[3] / 255.0 if len(color) > 3 else 1.0
    layer.putalpha(mask.point(lambda v: int(v * alpha)) if alpha < 1 else mask)
    return Image.alpha_composite(canvas, layer)


def shape(w, h, radius, fill=None, border=None, bw=1, margin=0, inset=0, ring=None, ring_w=2, ring_gap=1,
          top_light=None, bottom_shade=None, fill2=None, sheen=None):
    """An RGBA picture (w x h device pixels) of a rounded rectangle.

    margin   transparent space around the shape (focus ring / click halo live there)
    inset    shrinks the shape (the pressed look)
    ring     a ring around the shape, ring_gap pixels away, ring_w wide
    top_light / bottom_shade   1px inner lines that give a flat button a hint of body
    fill2    a vertical gradient from fill (top) to fill2 (bottom). In a 9-slice picture the stretched middle
             keeps the centre colour, so the light top and darker bottom stay at the edges of any size
    sheen    (colour, depth): the top `depth` pixels blend from colour into fill; the rest is exactly fill,
             so widgets with the fill colour as background sit seamlessly on it (cards)
    """
    Image, ImageChops, _ = _pil()
    size = (w * S, h * S)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    a = (margin + inset) * S
    box = (a, a, w * S - a - 1, h * S - a - 1)
    r = radius * S
    if ring is not None:
        g, rw = ring_gap * S, ring_w * S
        outer = _rr_mask(size, (box[0] - g - rw, box[1] - g - rw, box[2] + g + rw, box[3] + g + rw), r + g + rw)
        inner = _rr_mask(size, (box[0] - g, box[1] - g, box[2] + g, box[3] + g), r + g if g else r)
        img = _paint(img, ring, ImageChops.subtract(outer, inner))
    outer = _rr_mask(size, box, r)
    if fill is not None and fill2 is not None:
        img = _gradient(img, fill, fill2, outer, box[1], box[3])
    elif fill is not None and sheen is not None:
        img = _gradient(img, sheen[0], fill, outer, box[1], box[1] + sheen[1] * S)
    elif fill is not None:
        img = _paint(img, fill, outer)
    if border is not None and bw > 0:
        b = int(round(bw * S))
        inner = _rr_mask(size, (box[0] + b, box[1] + b, box[2] - b, box[3] - b), max(0, r - b))
        img = _paint(img, border, ImageChops.subtract(outer, inner))
    if top_light is not None or bottom_shade is not None:
        b = int(round(bw * S)) if border is not None else 0
        inner = _rr_mask(size, (box[0] + b, box[1] + b, box[2] - b, box[3] - b), max(0, r - b))
        if top_light is not None:
            lower = _rr_mask(size, (box[0] + b, box[1] + b + S, box[2] - b, box[3] - b + S), max(0, r - b))
            img = _paint(img, top_light, ImageChops.subtract(inner, lower))
        if bottom_shade is not None:
            upper = _rr_mask(size, (box[0] + b, box[1] + b - S, box[2] - b, box[3] - b - S), max(0, r - b))
            img = _paint(img, bottom_shade, ImageChops.subtract(inner, upper))
    return _reduce(img)


def grow(img, border, size):
    """Stretch the middle of a 9-slice picture to `size` (w, h); the corners stay as they are.

    ttk fills a control by *tiling* the middle of its picture, and each tile of a picture
    with soft (partly transparent) edges costs a slow blend on X11. A wide middle keeps
    that to a handful of tiles per control.
    """
    Image = _pil()[0]
    left, top, right, bottom = border
    w, h = img.size
    W, H = size
    if (W, H) == (w, h):
        return img
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cols = [(0, left, 0, left), (left, w - right, left, W - right), (w - right, w, W - right, W)]
    rows = [(0, top, 0, top), (top, h - bottom, top, H - bottom), (h - bottom, h, H - bottom, H)]
    nearest = getattr(Image, "Resampling", Image).NEAREST
    for sx0, sx1, dx0, dx1 in cols:
        for sy0, sy1, dy0, dy1 in rows:
            if sx1 <= sx0 or sy1 <= sy0 or dx1 <= dx0 or dy1 <= dy0:
                continue
            piece = img.crop((sx0, sy0, sx1, sy1))
            if piece.size != (dx1 - dx0, dy1 - dy0):
                piece = piece.resize((dx1 - dx0, dy1 - dy0), nearest)
            out.paste(piece, (dx0, dy0))
    return out


# --------------------------------------------------------------------------- #
# icons: simple line drawings on a 24 x 24 grid (in the spirit of the Lucide set)
# --------------------------------------------------------------------------- #

def _arc(cx, cy, r, a0, a1, n=8):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _rounded_path(x0, y0, x1, y1, r):
    pts = []
    pts += _arc(x1 - r, y0 + r, r, -90, 0)
    pts += _arc(x1 - r, y1 - r, r, 0, 90)
    pts += _arc(x0 + r, y1 - r, r, 90, 180)
    pts += _arc(x0 + r, y0 + r, r, 180, 270)
    return pts + [pts[0]]


ICONS = {
    # name: list of ("line", points) | ("fill", points) | ("circle", (cx, cy, r)) | ("dot", (cx, cy, r))
    "home": [("line", [(3, 10.5), (12, 3.5), (21, 10.5)]),
             ("line", [(5, 9), (5, 19.5), (6, 20.5), (18, 20.5), (19, 19.5), (19, 9)]),
             ("line", [(9.5, 20.5), (9.5, 14), (14.5, 14), (14.5, 20.5)])],
    "arrow": [("line", [(5, 12), (19, 12)]), ("line", [(13, 6), (19, 12), (13, 18)])],
    "calendar": [("line", _rounded_path(3, 5, 21, 21, 3)),
                 ("line", [(8, 3), (8, 7)]), ("line", [(16, 3), (16, 7)]),
                 ("line", [(3, 10), (21, 10)])],
    "chart_bars": [("line", [(4, 19), (4, 9)]), ("line", [(10, 19), (10, 5)]),
                   ("line", [(16, 19), (16, 12)]), ("line", [(2, 19), (22, 19)])],
    "code_slash": [("line", [(8, 9), (4, 12), (8, 15)]), ("line", [(16, 9), (20, 12), (16, 15)]),
                   ("line", [(14, 5), (10, 19)])],
    "data": [("line", [(4, 5), (6, 3.4), (9, 2.4), (12, 2), (15, 2.4), (18, 3.4), (20, 5),
                       (18, 6.6), (15, 7.6), (12, 8), (9, 7.6), (6, 6.6), (4, 5)]),
             ("line", [(4, 5), (4, 19)]), ("line", [(20, 5), (20, 19)]),
             ("line", [(4, 12), (6, 13.7), (9, 14.6), (12, 15), (15, 14.6), (18, 13.7), (20, 12)]),
             ("line", [(4, 19), (6, 20.7), (9, 21.6), (12, 22), (15, 21.6), (18, 20.7), (20, 19)])],
    "flame": [("line", [(13, 3), (14, 6), (12, 8), (10, 10), (9, 12), (9, 14), (10, 16),
                         (12, 17), (14, 16), (15, 14), (15, 12), (17, 14), (18, 17), (17, 20),
                         (14, 22), (10, 22), (7, 20), (5, 17), (4, 14), (5, 10), (8, 7), (11, 5), (13, 3)]),
               ("line", [(12, 12), (11, 14), (11, 16), (12, 18), (14, 17), (14, 15), (13, 13), (12, 12)])],
    "chat": [("line", [(5, 4), (19, 4), (20.4, 4.6), (21, 6), (21, 14), (20.4, 15.4), (19, 16), (11, 16), (6.5, 20),
                       (6.5, 16), (5, 16), (3.6, 15.4), (3, 14), (3, 6), (3.6, 4.6), (5, 4)]),
             ("line", [(8, 9), (16, 9)]), ("line", [(8, 12.2), (13, 12.2)])],
    "spark": [("line", [(12, 3), (13.4, 7.6), (18, 9), (13.4, 10.4), (12, 15),
                         (10.6, 10.4), (6, 9), (10.6, 7.6), (12, 3)]),
              ("line", [(19, 15), (19.7, 17.3), (22, 18), (19.7, 18.7), (19, 21),
                         (18.3, 18.7), (16, 18), (18.3, 17.3), (19, 15)])],
    "back": [("line", [(19, 12), (5, 12)]), ("line", [(11, 6), (5, 12), (11, 18)])],
    "forward": [("line", [(5, 12), (19, 12)]), ("line", [(13, 6), (19, 12), (13, 18)])],
    "move": [("line", [(12, 2.5), (12, 21.5)]), ("line", [(2.5, 12), (21.5, 12)]),
             ("line", [(9, 5.5), (12, 2.5), (15, 5.5)]), ("line", [(9, 18.5), (12, 21.5), (15, 18.5)]),
             ("line", [(5.5, 9), (2.5, 12), (5.5, 15)]), ("line", [(18.5, 9), (21.5, 12), (18.5, 15)])],
    "zoom": [("circle", (10.5, 10.5, 7)), ("line", [(20.5, 20.5), (15.6, 15.6)]),
             ("line", [(10.5, 7.5), (10.5, 13.5)]), ("line", [(7.5, 10.5), (13.5, 10.5)])],
    "search": [("circle", (10.5, 10.5, 7)), ("line", [(20.5, 20.5), (15.6, 15.6)])],
    "chevron_down": [("line", [(6, 9), (12, 15), (18, 9)])],
    "chevron_up": [("line", [(6, 15), (12, 9), (18, 15)])],
    "chevron_right": [("line", [(9, 6), (15, 12), (9, 18)])],
    "chevron_left": [("line", [(15, 6), (9, 12), (15, 18)])],
    "copy": [("line", _rounded_path(8.5, 8.5, 21, 21, 2)),
             ("line", [(4.8, 15.5), (3.6, 14.9), (3, 13.7), (3, 4.8), (3.6, 3.6), (4.8, 3), (13.7, 3), (14.9, 3.6),
                       (15.5, 4.8)])],
    "external": [("line", [(15, 3), (21, 3), (21, 9)]), ("line", [(10.5, 13.5), (21, 3)]),
                 ("line", [(18, 13.5), (18, 19), (17.4, 20.4), (16, 21), (5, 21), (3.6, 20.4), (3, 19), (3, 8),
                           (3.6, 6.6), (5, 6), (10.5, 6)])],
    "download": [("line", [(21, 15), (21, 19), (20.4, 20.4), (19, 21), (5, 21), (3.6, 20.4), (3, 19), (3, 15)]),
                 ("line", [(7, 10), (12, 15), (17, 10)]), ("line", [(12, 15), (12, 3)])],
    "sun": [("circle", (12, 12, 4)),
            ("line", [(12, 2), (12, 4)]), ("line", [(12, 20), (12, 22)]), ("line", [(4.93, 4.93), (6.34, 6.34)]),
            ("line", [(17.66, 17.66), (19.07, 19.07)]), ("line", [(2, 12), (4, 12)]), ("line", [(20, 12), (22, 12)]),
            ("line", [(6.34, 17.66), (4.93, 19.07)]), ("line", [(19.07, 4.93), (17.66, 6.34)])],
    "moon": [("moon", None)],
    "sparkle": [("fill", [(12, 2.5), (13.9, 9.4), (20.5, 11.5), (13.9, 13.6), (12, 20.5), (10.1, 13.6), (3.5, 11.5),
                          (10.1, 9.4)]),
                ("fill", [(19, 2.5), (19.7, 4.6), (21.8, 5.3), (19.7, 6), (19, 8.1), (18.3, 6), (16.2, 5.3), (18.3, 4.6)])],
    "play": [("fill", [(7, 4.5), (19.5, 12), (7, 19.5)])],
    "folder": [("line", [(4, 20), (20, 20), (21.4, 19.4), (22, 18), (22, 8.5), (21.4, 7.1), (20, 6.5), (12.2, 6.5),
                         (11.2, 6.1), (10.5, 5.3), (9.7, 4), (8.9, 3.3), (7.9, 3), (4, 3), (2.6, 3.6), (2, 5), (2, 18),
                         (2.6, 19.4), (4, 20)])],
    "file": [("line", [(14.5, 2.5), (6, 2.5), (4.6, 3.1), (4, 4.5), (4, 19.5), (4.6, 20.9), (6, 21.5), (18, 21.5),
                       (19.4, 20.9), (20, 19.5), (20, 8), (14.5, 2.5)]),
             ("line", [(14, 2.8), (14, 8.5), (19.7, 8.5)]), ("line", [(8, 13), (16, 13)]), ("line", [(8, 17), (13, 17)])],
    "sliders": [("line", [(21, 5), (14, 5)]), ("line", [(10, 5), (3, 5)]), ("line", [(21, 12), (12, 12)]),
                ("line", [(8, 12), (3, 12)]), ("line", [(21, 19), (16, 19)]), ("line", [(12, 19), (3, 19)]),
                ("line", [(14, 2.5), (14, 7.5)]), ("line", [(8, 9.5), (8, 14.5)]), ("line", [(16, 16.5), (16, 21.5)])],
    "chart": [("line", [(3, 3), (3, 19), (3.6, 20.4), (5, 21), (21, 21)]),
              ("line", [(7, 16), (10.5, 11.5), (14, 14.5), (19.5, 7.5)])],
    "code": [("line", [(16, 18), (22, 12), (16, 6)]), ("line", [(8, 6), (2, 12), (8, 18)])],
    "table": [("line", _rounded_path(3, 3, 21, 21, 2)), ("line", [(3, 9), (21, 9)]), ("line", [(3, 15), (21, 15)]),
              ("line", [(12, 3), (12, 21)])],
    "check": [("line", [(20, 6.5), (9, 17.5), (4, 12.5)])],
    "close": [("line", [(6, 6), (18, 18)]), ("line", [(18, 6), (6, 18)])],
    "plus": [("line", [(12, 5), (12, 19)]), ("line", [(5, 12), (19, 12)])],
    "image": [("line", _rounded_path(3, 3, 21, 21, 2)), ("circle", (9, 9, 2)),
              ("line", [(21, 15), (16, 10), (5, 21)])],
    # Feature Lab: a conical flask with a liquid line; curved undo / redo arrows
    "flask": [("line", [(8.5, 3), (15.5, 3)]),
              ("line", [(10, 3), (10, 9.2), (4.4, 18.6), (4.5, 20), (5.6, 21), (18.4, 21), (19.5, 20), (19.6, 18.6),
                        (14, 9.2), (14, 3)]),
              ("line", [(7.1, 15), (16.9, 15)])],
    "undo": [("line", [(9, 14), (4, 9), (9, 4)]),
             ("line", [(4, 9), (14.5, 9), (17.2, 9.6), (19.2, 11.3), (20, 13.5), (19.2, 15.7), (17.2, 17.4),
                       (14.5, 18), (11, 18)])],
    "redo": [("line", [(15, 14), (20, 9), (15, 4)]),
             ("line", [(20, 9), (9.5, 9), (6.8, 9.6), (4.8, 11.3), (4, 13.5), (4.8, 15.7), (6.8, 17.4),
                       (9.5, 18), (13, 18)])],
}


def draw_icon(name, size, color, stroke=1.9):
    """An RGBA icon picture, size x size device pixels."""
    Image, ImageChops, ImageDraw = _pil()
    big = size * S
    k = big / 24.0
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    mask = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(mask)
    w = max(1.0, stroke * k)
    half = w / 2.0
    for kind, data in ICONS.get(name, []):
        if kind == "line":
            pts = [(x * k, y * k) for x, y in data]
            d.line(pts, fill=255, width=int(round(w)))
            for x, y in pts:   # round caps and joins
                d.ellipse((x - half, y - half, x + half, y + half), fill=255)
        elif kind == "fill":
            d.polygon([(x * k, y * k) for x, y in data], fill=255)
        elif kind == "circle":
            cx, cy, r = (v * k for v in data)
            d.ellipse((cx - r - half, cy - r - half, cx + r + half, cy + r + half), fill=255)
            d.ellipse((cx - r + half, cy - r + half, cx + r - half, cy + r - half), fill=0)
        elif kind == "dot":
            cx, cy, r = (v * k for v in data)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
        elif kind == "moon":
            full = Image.new("L", (big, big), 0)
            ImageDraw.Draw(full).ellipse((3.2 * k, 3.2 * k, 20.8 * k, 20.8 * k), fill=255)
            bite = Image.new("L", (big, big), 0)
            ImageDraw.Draw(bite).ellipse((9.2 * k, 0.2 * k, 23.6 * k, 14.6 * k), fill=255)
            mask = ImageChops.lighter(mask, ImageChops.subtract(full, bite))
            d = ImageDraw.Draw(mask)
    img = _paint(img, rgba(color), mask)
    return _reduce(img)


# --------------------------------------------------------------------------- #
# the skin: all pictures + ttk elements of one Theme
# --------------------------------------------------------------------------- #

class Skin:
    """Draws the pictures for the current colours and registers the ttk elements once."""

    def __init__(self, theme):
        self.t = theme
        self.photos = {}          # key -> tk.PhotoImage (redrawn in place on a theme change)
        self.icon_specs = {}      # key -> (name, color role, size)
        self.made = set()         # ttk element names already created
        self.ok = True
        try:
            _pil()
        except ImportError:       # Pillow comes with matplotlib; this is only a safety net
            self.ok = False
        px = theme.px
        self.m = px(3)            # margin for the focus ring and the click halo
        self.r = px(8)            # controls
        self.r_card = px(12)      # cards
        self.r_pill = px(14)      # chips
        self.hair = max(1, px(1))

    # photo images ------------------------------------------------------------
    def photo(self, key, pil_image):
        data = png_data(pil_image)
        img = self.photos.get(key)
        if img is None:
            img = self.photos[key] = tk.PhotoImage(master=self.t.root, data=data)
        else:
            img.configure(data=data)
        return img

    def icon(self, name, role="muted", size=18):
        """An icon in a colour role of the palette (redrawn when the look changes)."""
        if not self.ok:
            return ""
        px = self.t.px(size)
        key = f"icon:{name}:{role}:{px}"
        if key not in self.photos:
            self.icon_specs[key] = (name, role, px)
            self.photo(key, draw_icon(name, px, self._color(role)))
        return self.photos[key]

    def icon_states(self, name, size=18, normal="muted", active="text", disabled="faint", selected=None,
                    pressed=None):
        """An image spec for a ttk widget's `image` option: the icon changes colour with the state."""
        if not self.ok:
            return ""
        spec = [self.icon(name, normal, size), "disabled", self.icon(name, disabled, size)]
        if pressed:
            spec += ["pressed", self.icon(name, pressed, size)]
        if selected:
            spec += ["selected", self.icon(name, selected, size)]
        if active and active != normal:
            spec += ["active", self.icon(name, active, size)]
        return tuple(spec)

    def _color(self, role):
        from .theme import C
        return C.get(role, role)

    # --------------------------------------------------------------------------
    def redraw(self, style):
        """(Re)draw every picture for the current colours; create the ttk elements the first time."""
        if not self.ok:
            return
        for key, (name, role, size) in list(self.icon_specs.items()):
            self.photo(key, draw_icon(name, size, self._color(role)))
        self._buttons(style)
        self._fields(style)
        self._tabs(style)
        self._cards(style)
        self._scrollbars(style)
        self._indicators(style)
        self._misc(style)

    def _element(self, style, name, base, states, border, padding=None, sticky="nsew", width=None, height=None):
        if name in self.made:
            return
        kw = {"border": border, "sticky": sticky}
        if padding is not None:
            kw["padding"] = padding
        if width is not None:
            kw["width"] = width
        if height is not None:
            kw["height"] = height
        try:
            style.element_create(name, "image", self.photos[base],
                                 *[tuple(st.split()) + (self.photos[key],) for st, key in states], **kw)
        except tk.TclError:   # already exists (a second Tk interpreter is not expected, but be safe)
            pass
        self.made.add(name)

    # buttons ------------------------------------------------------------------
    def _button_set(self, style, kind, normal, hover, pressed, disabled, radius, selected=None,
                    selected_hover=None):
        """Pictures + element for one button family. Each state is a dict for shape()."""
        from .theme import C
        m, r = self.m, radius
        side = 2 * (m + r) + 4
        ring = rgba(C["focus_ring"])
        halo1, halo2 = rgba(C["accent"], 0.42), rgba(C["accent"], 0.16)
        name = f"btn:{kind}"
        b = m + r + 1
        big = (2 * b + self.t.px(96), 2 * b + self.t.px(24))

        def make(key, spec, **extra):
            img = shape(side, side, r, margin=m, **{**spec, **extra})
            self.photo(f"{name}:{key}", grow(img, (b, b, b, b), big))

        make("normal", normal)
        make("hover", hover)
        make("pressed", pressed, inset=self.hair)
        make("disabled", disabled)
        make("focus", normal, ring=ring)
        make("focus_hover", hover, ring=ring)
        make("flash1", hover, ring=halo1, ring_gap=0, ring_w=m)
        make("flash2", hover, ring=halo2, ring_gap=0, ring_w=m)
        states = [("disabled", "disabled"), ("pressed", "pressed"), ("user1", "flash1"), ("user2", "flash2")]
        if selected:
            make("selected", selected)
            make("selected_hover", selected_hover or selected)
            make("selected_focus", selected, ring=ring)
            states += [("selected user3", "selected_focus"), ("selected active", "selected_hover"),
                       ("selected", "selected")]
        states += [("user3 active", "focus_hover"), ("user3", "focus"), ("active", "hover")]
        self._element(style, f"Studio.{kind}.button", f"{name}:normal",
                      [(st, f"{name}:{key}") for st, key in states], border=b, padding=m, width=2 * b, height=2 * b)

    def _buttons(self, style):
        from .theme import C
        r = self.r
        hair = self.hair
        light = rgba("#ffffff", 0.22 if not self.t.dark else 0.16)
        shade = rgba("#000000", 0.10 if not self.t.dark else 0.18)
        def lit(color, up=0.16, down=0.10):     # the dashboard's look: lighter at the top, deeper at the bottom
            return dict(fill=rgba(mix(color, "#ffffff", up)), fill2=rgba(mix(color, "#000000", down)))

        self._button_set(
            style, "primary",
            normal=dict(**lit(C["accent"]), top_light=light, bottom_shade=shade),
            hover=dict(**lit(C["accent_hover"]), top_light=light, bottom_shade=shade),
            pressed=dict(**lit(C["accent_pressed"], 0.04, 0.04)),
            disabled=dict(fill=rgba(C["accent"], 0.38)), radius=r)
        self._button_set(
            style, "secondary",
            normal=dict(**lit(C["raised"], 0.05 if self.t.dark else 0.6, 0.04 if self.t.dark else 0.015),
                        border=rgba(C["border_strong"]), bw=hair,
                        top_light=rgba("#ffffff", 0.05) if self.t.dark else None),
            hover=dict(**lit(C["hover"], 0.05 if self.t.dark else 0.5, 0.03), border=rgba(C["input_border"]), bw=hair),
            pressed=dict(fill=rgba(C["pressed"]), border=rgba(C["input_border"]), bw=hair),
            disabled=dict(fill=rgba(C["raised"], 0.5), border=rgba(C["border"]), bw=hair), radius=r,
            selected=dict(fill=rgba(C["accent_soft"]), border=rgba(C["accent_line"]), bw=hair),
            selected_hover=dict(fill=rgba(C["accent_soft"]), border=rgba(C["accent"]), bw=hair))
        ghost = dict(normal=dict(), hover=dict(fill=rgba(C["hover"])), pressed=dict(fill=rgba(C["pressed"])),
                     disabled=dict(),
                     selected=dict(fill=rgba(C["accent_soft"]), border=rgba(C["accent_line"]), bw=hair),
                     selected_hover=dict(fill=rgba(C["accent_soft"]), border=rgba(C["accent"]), bw=hair))
        self._button_set(style, "ghost", radius=r, **ghost)
        self._button_set(style, "chip", radius=self.r_pill, **ghost)
        # ghost buttons that sit on the window background (hover tint relative to it)
        self._button_set(style, "bgghost", radius=r,
                         normal=dict(), hover=dict(fill=rgba(C["bg_hover"])), pressed=dict(fill=rgba(C["pressed"])),
                         disabled=dict(),
                         selected=dict(fill=rgba(C["panel"]), border=rgba(C["border"]), bw=hair),
                         selected_hover=dict(fill=rgba(C["panel"]), border=rgba(C["border_strong"]), bw=hair))

    # fields -------------------------------------------------------------------
    def _fields(self, style):
        from .theme import C
        m, r, hair = self.m, self.r, self.hair
        side = 2 * (m + r) + 4
        glow = rgba(C["accent"], 0.28)
        b = m + r + 1
        big = (2 * b + self.t.px(128), 2 * b + self.t.px(24))

        def make(key, **spec):
            self.photo(key, grow(shape(side, side, r, margin=m, bw=hair, **spec), (b, b, b, b), big))

        # typing fields (entry, spinbox): focus shows on click too, the caret is there
        make("field:normal", fill=rgba(C["field"]), border=rgba(C["input_border"]))
        make("field:hover", fill=rgba(C["field"]), border=rgba(C["muted"]))
        make("field:focus", fill=rgba(C["field"]), border=rgba(C["accent"]), ring=glow, ring_gap=0, ring_w=m)
        make("field:disabled", fill=rgba(C["bg"]), border=rgba(C["border"]))
        make("field:invalid", fill=rgba(C["field"]), border=rgba(C["danger"]))
        self._element(style, "Studio.field", "field:normal",
                      [("disabled", "field:disabled"), ("invalid", "field:invalid"), ("focus", "field:focus"),
                       ("hover", "field:hover")], border=b, padding=m, width=2 * b, height=2 * b)
        # drop-down selects (read-only comboboxes): act like buttons
        make("select:normal", fill=rgba(C["field"]), border=rgba(C["input_border"]))
        make("select:hover", fill=rgba(C["hover"]), border=rgba(C["muted"]))
        make("select:pressed", fill=rgba(C["pressed"]), border=rgba(C["muted"]))
        make("select:focus", fill=rgba(C["field"]), border=rgba(C["accent"]), ring=rgba(C["focus_ring"]))
        make("select:disabled", fill=rgba(C["bg"]), border=rgba(C["border"]))
        self._element(style, "Studio.select", "select:normal",
                      [("disabled", "select:disabled"), ("pressed", "select:pressed"), ("user3", "select:focus"),
                       ("hover", "select:hover")], border=b, padding=m, width=2 * b, height=2 * b)
        # chevrons inside fields
        sz = self.t.px(16)
        for key, name, role in (("chev:normal", "chevron_down", "muted"), ("chev:hover", "chevron_down", "text"),
                                ("chev:disabled", "chevron_down", "faint")):
            self.photo(key, self._padded_icon(name, sz, role, pad=(self.t.px(2), 0, self.t.px(8), 0)))
        self._element(style, "Studio.Combo.downarrow", "chev:normal",
                      [("disabled", "chev:disabled"), ("hover", "chev:hover")], border=0, sticky="")
        small = self.t.px(12)
        for key, name, role in (("up:normal", "chevron_up", "muted"), ("up:hover", "chevron_up", "accent"),
                                ("down:normal", "chevron_down", "muted"), ("down:hover", "chevron_down", "accent"),
                                ("up:disabled", "chevron_up", "faint"), ("down:disabled", "chevron_down", "faint")):
            self.photo(key, self._padded_icon(name, small, role, pad=(self.t.px(2), 0, self.t.px(6), 0)))
        self._element(style, "Studio.Spin.uparrow", "up:normal",
                      [("disabled", "up:disabled"), ("pressed", "up:hover"), ("active", "up:hover")],
                      border=0, sticky="")
        self._element(style, "Studio.Spin.downarrow", "down:normal",
                      [("disabled", "down:disabled"), ("pressed", "down:hover"), ("active", "down:hover")],
                      border=0, sticky="")
        self.photo("search:icon", self._padded_icon("search", self.t.px(16), "faint", pad=(self.t.px(8), 0,
                                                                                            self.t.px(2), 0)))
        self._element(style, "Studio.search.icon", "search:icon", [], border=0, sticky="")
        self.photo("menu:chev", self._padded_icon("chevron_down", self.t.px(14), "muted",
                                                  pad=(self.t.px(4), 0, 0, 0)))
        self.photo("menu:chev:on", self._padded_icon("chevron_down", self.t.px(14), "text",
                                                     pad=(self.t.px(4), 0, 0, 0)))
        self._element(style, "Studio.menu.indicator", "menu:chev",
                      [("pressed", "menu:chev:on"), ("active", "menu:chev:on")], border=0, sticky="")

    def _padded_icon(self, name, size, role, pad=(0, 0, 0, 0)):
        Image = _pil()[0]
        icon = draw_icon(name, size, self._color(role), stroke=2.0)
        left, top, right, bottom = pad
        img = Image.new("RGBA", (size + left + right, size + top + bottom), (0, 0, 0, 0))
        img.paste(icon, (left, top), icon)
        return img

    # notebook tabs --------------------------------------------------------------
    def _tabs(self, style):
        from .theme import C
        m, r, hair = self.m, self.r, self.hair
        side = 2 * (m + r) + 4
        ring = rgba(C["focus_ring"])
        b = m + r + 1
        big = (2 * b + self.t.px(64), 2 * b + self.t.px(16))

        def make(key, **spec):
            self.photo(key, grow(shape(side, side, r, margin=m, bw=hair, **spec), (b, b, b, b), big))

        make("tab:normal")
        make("tab:hover", fill=rgba(C["bg_hover"]))
        make("tab:selected", fill=rgba(C["panel"]), border=rgba(C["border"]))
        make("tab:selected_focus", fill=rgba(C["panel"]), border=rgba(C["border"]), ring=ring)
        make("tab:focus", ring=ring)
        self._element(style, "Studio.tab", "tab:normal",
                      [("selected user3", "tab:selected_focus"), ("selected", "tab:selected"),
                       ("active", "tab:hover")], border=b, padding=m, width=2 * b, height=2 * b)

    # cards ----------------------------------------------------------------------
    def _cards(self, style):
        from .theme import C
        m, rc, hair = self.m, self.r_card, self.hair
        ring = rgba(C["focus_ring"])
        # structural cards (left panel, tab content, load card): no margin
        side = 2 * rc + 4
        b = rc + 1
        sheen = (rgba(mix(C["panel"], C["accent"], 0.05 if self.t.dark else 0.025)), rc)
        self.photo("card:panel", grow(shape(side, side, rc, fill=rgba(C["panel"]), border=rgba(C["border"]), bw=hair,
                                            sheen=sheen),
                                      (b, b, b, b), (2 * b + self.t.px(256), 2 * b + self.t.px(256))))
        self._element(style, "Studio.panel", "card:panel", [], border=b, padding=self.t.px(4), width=2 * b,
                      height=2 * b)
        self._element(style, "Studio.nb.client", "card:panel", [], border=b, padding=self.t.px(4), width=2 * b,
                      height=2 * b)
        # clickable cards (gallery cards, recent files): margin for the focus ring
        side = 2 * (m + rc) + 4
        b = m + rc + 1
        big = (2 * b + self.t.px(192), 2 * b + self.t.px(192))
        for key, spec in (("normal", dict(fill=rgba(C["panel"]), border=rgba(C["border"]), sheen=sheen)),
                          ("hover", dict(fill=rgba(C["card_hover"]), border=rgba(C["accent_line"]))),
                          ("pressed", dict(fill=rgba(C["pressed"]), border=rgba(C["accent"]))),
                          ("focus", dict(fill=rgba(C["panel"]), border=rgba(C["border"]), ring=ring)),
                          ("focus_hover", dict(fill=rgba(C["card_hover"]), border=rgba(C["accent_line"]), ring=ring))):
            self.photo(f"card:{key}", grow(shape(side, side, rc, margin=m, bw=hair, **spec), (b, b, b, b), big))
        self._element(style, "Studio.card", "card:normal",
                      [("pressed", "card:pressed"), ("user3 active", "card:focus_hover"), ("user3", "card:focus"),
                       ("active", "card:hover")], border=b, padding=m, width=2 * b, height=2 * b)
        # wells: rounded boxes inside a card (data chip, tables, code)
        from .theme import CODE
        rw = self.r
        side = 2 * rw + 4
        b = rw + 1
        wide = (2 * b + self.t.px(256), 2 * b + self.t.px(160))
        for kind, fill, edge in (("raised", rgba(C["raised"]), rgba(C["border"])),
                                 ("field", rgba(C["field"]), rgba(C["border_strong"])),
                                 ("soft", rgba(C["accent_soft"]), rgba(C["accent_line"])),
                                 ("code", rgba(CODE["bg"]), rgba(C["border_strong"])),
                                 ("danger", rgba(C["danger_soft"]), rgba(C["danger"], 0.35)),
                                 ("warn", rgba(C["warn_soft"]), rgba(C["warn"], 0.35))):
            self.photo(f"well:{kind}", grow(shape(side, side, rw, fill=fill, border=edge, bw=hair), (b, b, b, b), wide))
            self._element(style, f"Studio.well.{kind}", f"well:{kind}", [], border=b, padding=self.t.px(3),
                          width=2 * b, height=2 * b)
        # badges (step numbers) and status pills
        rb = self.t.px(10)
        side = 2 * rb + 4
        b = rb + 1
        small = (2 * b + self.t.px(16), 2 * b + self.t.px(4))
        for kind, spec in (("on", dict(fill=rgba(mix(C["accent"], "#ffffff", 0.14)), fill2=rgba(mix(C["accent"], "#000000", 0.08)))),
                           ("off", dict(fill=rgba(C["accent_soft"]))),
                           ("muted", dict(fill=rgba(C["raised"]), border=rgba(C["border"]), bw=hair))):
            self.photo(f"badge:{kind}", grow(shape(side, side, rb, **spec), (b, b, b, b), small))
            self._element(style, f"Studio.badge.{kind}", f"badge:{kind}", [], border=b, padding=0, width=2 * b,
                          height=2 * b)

    # scrollbars ---------------------------------------------------------------
    def _scrollbars(self, style):
        from .theme import C, LIGHT
        px = self.t.px
        thick, long = px(12), px(192)
        Image = _pil()[0]
        self.photo("sb:v:none", Image.new("RGBA", (thick, long), (0, 0, 0, 0)))
        self.photo("sb:h:none", Image.new("RGBA", (long, thick), (0, 0, 0, 0)))
        for orient in ("v", "h"):
            self._thumbs(style, orient, "", C["scroll"], C["scroll_hover"], C["accent"])
            # the code box keeps its light colours in both looks, and so does its scrollbar
            self._thumbs(style, orient, "code", LIGHT["scroll"], LIGHT["scroll_hover"], LIGHT["accent"])
            self._element(style, f"Studio.{orient}.trough", f"sb:{orient}:none", [], border=0, sticky="nsew",
                          width=thick, height=thick)

    def _thumbs(self, style, orient, name, normal, hover, pressed):
        """Pill-shaped scrollbar thumbs: slim at rest, a little wider under the mouse."""
        px = self.t.px
        thick, length, long = px(12), px(30), px(192)
        Image = _pil()[0]
        end = px(2) + px(4) + 1
        for key, width, color in (("normal", px(6), normal), ("active", px(8), hover), ("pressed", px(8), pressed)):
            gap = (thick - width) // 2
            w, h = (thick, length) if orient == "v" else (length, thick)
            img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
            if orient == "v":
                box = (gap * S, px(2) * S, (gap + width) * S - 1, (length - px(2)) * S - 1)
            else:
                box = (px(2) * S, gap * S, (length - px(2)) * S - 1, (gap + width) * S - 1)
            img = _reduce(_paint(img, rgba(color), _rr_mask(img.size, box, width * S / 2)))
            if orient == "v":
                img = grow(img, (0, end, 0, end), (thick, 2 * end + long))
            else:
                img = grow(img, (end, 0, end, 0), (2 * end + long, thick))
            self.photo(f"sb:{orient}{name}:{key}", img)
        border = (0, end, 0, end) if orient == "v" else (end, 0, end, 0)
        size = dict(width=thick, height=2 * end) if orient == "v" else dict(width=2 * end, height=thick)
        self._element(style, f"Studio.{name}{orient}.thumb", f"sb:{orient}{name}:normal",
                      [("pressed", f"sb:{orient}{name}:pressed"), ("active", f"sb:{orient}{name}:active")],
                      border=border, sticky="nsew", **size)

    # check boxes, radio buttons, switches ----------------------------------------
    def _indicators(self, style):
        from .theme import C
        Image, ImageChops, ImageDraw = _pil()
        px = self.t.px
        box, ring_m, gap = px(16), px(3), px(7)
        W, H = ring_m + box + ring_m + gap - ring_m, ring_m + box + ring_m
        ring = rgba(C["focus_ring"])
        hair = self.hair

        def checkbox(on, state):
            alpha = 0.45 if state == "disabled" else 1.0
            border = C["accent"] if state == "hover" else C["input_border"]
            img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
            a = ring_m * S
            bx = (a, a, a + box * S - 1, a + box * S - 1)
            if state == "focus":
                g = 0
                outer = _rr_mask(img.size, (bx[0] - 2 * S, bx[1] - 2 * S, bx[2] + 2 * S, bx[3] + 2 * S), px(5) * S + 2 * S)
                inner = _rr_mask(img.size, (bx[0] - g, bx[1] - g, bx[2] + g, bx[3] + g), px(5) * S)
                img = _paint(img, ring, ImageChops.subtract(outer, inner))
            mask = _rr_mask(img.size, bx, px(5) * S)
            if on:
                img = _paint(img, rgba(C["accent_hover"] if state == "hover" else C["accent"], alpha), mask)
                mark = Image.new("L", img.size, 0)
                d = ImageDraw.Draw(mark)
                pts = [(a + x * box * S, a + y * box * S) for x, y in ((0.26, 0.52), (0.43, 0.69), (0.75, 0.33))]
                wdt = int(2.0 * S * self.t.scale)
                d.line(pts, fill=255, width=wdt)
                for x, y in pts:
                    d.ellipse((x - wdt / 2, y - wdt / 2, x + wdt / 2, y + wdt / 2), fill=255)
                img = _paint(img, rgba(C["check_mark"], alpha), mark)
            else:
                img = _paint(img, rgba(C["field"], alpha), mask)
                b = hair * S
                inner = _rr_mask(img.size, (bx[0] + b, bx[1] + b, bx[2] - b, bx[3] - b), px(5) * S - b)
                img = _paint(img, rgba(border, alpha), ImageChops.subtract(mask, inner))
            return _reduce(img)

        def radio(on, state):
            alpha = 0.45 if state == "disabled" else 1.0
            img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
            a = ring_m * S
            c = a + box * S / 2
            R = box * S / 2

            def circle(rr):
                m_ = Image.new("L", img.size, 0)
                ImageDraw.Draw(m_).ellipse((c - rr, c - rr, c + rr, c + rr), fill=255)
                return m_
            if state == "focus":
                img = _paint(img, ring, ImageChops.subtract(circle(R + 2 * S), circle(R)))
            if on:
                img = _paint(img, rgba(C["accent_hover"] if state == "hover" else C["accent"], alpha), circle(R))
                img = _paint(img, rgba(C["check_mark"], alpha), circle(R * 0.38))
            else:
                border = C["accent"] if state == "hover" else C["input_border"]
                img = _paint(img, rgba(C["field"], alpha), circle(R))
                img = _paint(img, rgba(border, alpha), ImageChops.subtract(circle(R), circle(R - hair * S)))
            return _reduce(img)

        sw_w, sw_h = px(30), px(18)
        SW, SH = ring_m + sw_w + ring_m + gap - ring_m, ring_m + sw_h + ring_m

        def switch(on, state):
            alpha = 0.45 if state == "disabled" else 1.0
            img = Image.new("RGBA", (SW * S, SH * S), (0, 0, 0, 0))
            a = ring_m * S
            track = (a, a, a + sw_w * S - 1, a + sw_h * S - 1)
            if state == "focus":
                outer = _rr_mask(img.size, (track[0] - 2 * S, track[1] - 2 * S, track[2] + 2 * S, track[3] + 2 * S),
                                 sw_h * S / 2 + 2 * S)
                img = _paint(img, ring, ImageChops.subtract(outer, _rr_mask(img.size, track, sw_h * S / 2)))
            tmask = _rr_mask(img.size, track, sw_h * S / 2)
            if on:
                img = _paint(img, rgba(C["accent_hover"] if state == "hover" else C["accent"], alpha), tmask)
            else:
                img = _paint(img, rgba(C["switch_off"], alpha), tmask)
                if state == "hover":
                    b = hair * S
                    inner = _rr_mask(img.size, (track[0] + b, track[1] + b, track[2] - b, track[3] - b),
                                     sw_h * S / 2 - b)
                    img = _paint(img, rgba(C["muted"], alpha), ImageChops.subtract(tmask, inner))
            knob_r = (sw_h - px(4)) * S / 2
            cy = a + sw_h * S / 2
            cx = a + (sw_w * S - sw_h * S / 2) if on else a + sw_h * S / 2
            knob = Image.new("L", img.size, 0)
            ImageDraw.Draw(knob).ellipse((cx - knob_r, cy - knob_r, cx + knob_r, cy + knob_r), fill=255)
            img = _paint(img, rgba(C["knob"], alpha), knob)
            return _reduce(img)

        for kind, fn in (("check", checkbox), ("radio", radio), ("switch", switch)):
            for on in (True, False):
                for state in ("normal", "hover", "focus", "disabled"):
                    self.photo(f"{kind}:{'on' if on else 'off'}:{state}", fn(on, state))
            self._element(style, f"Studio.{kind}.indicator", f"{kind}:off:normal",
                          [("disabled selected", f"{kind}:on:disabled"), ("disabled", f"{kind}:off:disabled"),
                           ("selected user3", f"{kind}:on:focus"), ("user3", f"{kind}:off:focus"),
                           ("selected active", f"{kind}:on:hover"), ("active", f"{kind}:off:hover"),
                           ("selected", f"{kind}:on:normal")], border=0, sticky="w")

    # progress bar, slider balls --------------------------------------------------
    def _misc(self, style):
        from .theme import C
        Image, _, ImageDraw = _pil()
        px = self.t.px
        h = px(6)
        side = 2 * h + 2
        e = h // 2 + 1
        wide = (2 * e + px(96), h)
        self.photo("pb:trough", grow(shape(side, h, h // 2, fill=rgba(C["accent_soft"])), (e, 0, e, 0), wide))
        self.photo("pb:bar", grow(shape(side, h, h // 2, fill=rgba(C["accent"])), (e, 0, e, 0), wide))
        self._element(style, "Studio.pb.trough", "pb:trough", [], border=(e, 0, e, 0), padding=0, width=2 * e,
                      height=h)
        self._element(style, "Studio.pb.pbar", "pb:bar", [], border=(e, 0, e, 0), padding=0, width=2 * e, height=h)

        from PIL import ImageFilter
        ball, size = px(16), px(26)

        def slider_ball(kind):
            img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
            c = size * S / 2
            accent = rgb(C["faint"] if kind == "disabled" else C["accent"])
            rr = ball * S / 2
            if kind in ("active", "focus"):
                glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow)
                g = size * S * 0.48
                gd.ellipse((c - g, c - g, c + g, c + g), fill=accent + (70 if kind == "active" else 0,))
                img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(S * 1.2)))
            else:
                sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ImageDraw.Draw(sh).ellipse((c - rr, c - rr + S, c + rr, c + rr + S), fill=(0, 0, 0, 60))
                img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(S)))
            d = ImageDraw.Draw(img)
            if kind == "focus":
                fr = rgb(C["focus_ring"])
                g = rr + 3.2 * S * self.t.scale
                d.ellipse((c - g, c - g, c + g, c + g), fill=fr + (255,))
                g2 = rr + 1.4 * S * self.t.scale
                d.ellipse((c - g2, c - g2, c + g2, c + g2), fill=rgb(C["panel"]) + (255,))
            d.ellipse((c - rr, c - rr, c + rr, c + rr), fill=rgb(C["knob"]) + (255,))
            inner = rr - 2.4 * S * self.t.scale
            d.ellipse((c - inner, c - inner, c + inner, c + inner), fill=accent + (255,))
            return _reduce(img)

        for kind in ("normal", "active", "disabled", "focus"):
            self.photo(f"ball:{kind}", slider_ball(kind))
