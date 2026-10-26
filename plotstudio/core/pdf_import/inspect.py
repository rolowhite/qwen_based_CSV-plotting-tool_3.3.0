"""Opening a PDF safely and looking at its pages: how many there are, their size and turn, and what each one is.

What a page is (`PageInfo.kind`, a guess from what the page holds; the user can change it):
  digital  it has a text layer: its tables are read straight from it, never by OCR or a model
  scanned  a picture of a page (maybe with a hidden text layer that scanning software added by OCR), or text
           drawn as shapes: either way only a picture of it can be read
  mixed    a text layer plus pictures that cover part of the page
  blank    nothing to read

The file is untrusted data. pdfium (pypdfium2) parses and draws it. This module never sets up pdfium's form
environment, and the pdfium build has no JavaScript engine (`javascript_engine()` checks), so nothing in the file
can run; links, actions, attachments and embedded files are never followed or opened. Memory stays bounded: the
size is checked before opening, a page is loaded only while it is used, a rendered image has at most
MAX_RENDER_PIXELS pixels, objects and characters looked at per page are capped, and thumbnails live in a small
cache.

pdfium is not thread-safe, so every call into it holds PDFIUM_LOCK (digital.py runs camelot under the same lock:
its ruling-line method draws pages with pdfium too).

Coordinates: PDF user space is in points, origin at the bottom left of the page before any turn. A turn is
clockwise in degrees (0, 90, 180, 270): the page's own /Rotate plus any turn the app adds to show it upright.
`View` says how one picture of a page was drawn and converts between user space and its pixels.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
import tempfile
import threading
import warnings
from collections import Counter, OrderedDict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

Box = Tuple[float, float, float, float]            # x0, y0, x1, y1

PDFIUM_LOCK = threading.RLock()

MAX_FILE_MB = 500                 # bigger files are refused (a scanner setting)
LAZY_FROM = 50                    # more pages than this: thumbnails load as they're needed, and a page range is read
MAX_RENDER_PIXELS = 30_000_000    # a rendered page never has more pixels (an A4 page at 300 dpi has 8.7 million)
THUMB_HEIGHT = 150
THUMB_CACHE = 240                 # thumbnails kept in memory
MAX_OBJECTS = 200_000             # page objects looked at per page
MAX_CHARS = 200_000               # characters looked at per page
MIN_TEXT_CHARS = 20               # with pictures on a page, fewer printed characters than this isn't a text layer
MIXED_COVER = 0.10                # pictures covering this share of a page that has text make it "mixed"
DRAWN_PATHS = 200                 # no text but this many shapes: text drawn as outlines, or a drawing
HIDDEN_MODES = (3, 7)             # text render modes that never paint (invisible; clip only)
COPY_PERMISSION = 0x10            # bit 5 of a PDF's permissions: copy or extract text and graphics
COVER_GRID = 64
KINDS = ("digital", "scanned", "mixed", "blank")


class PdfError(Exception):
    """A PDF can't be opened or read; the message says why and what to do."""


class PasswordNeeded(PdfError):
    """The file is protected: ask for its password."""


class WrongPassword(PasswordNeeded):
    """The password given doesn't open the file."""


class DamagedPdf(PdfError):
    """Not a readable PDF."""


class EmptyPdf(PdfError):
    """0 bytes, or no pages."""


class TooBig(PdfError):
    """Over the size limit."""


class CopyingNotAllowed(PdfError):
    """The PDF's own settings don't allow copying its text."""


# --------------------------------------------------------------------------------------------------- geometry --
def norm_box(box) -> Box:
    x0, y0, x1, y1 = (float(v) for v in box)
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def check_turn(turn) -> int:
    t = int(turn) % 360
    if t % 90:
        raise ValueError(f"A page turns in steps of 90 degrees, not {turn}.")
    return t


def turned_size(turn: int, box: Box) -> Tuple[float, float]:
    """Width and height of `box` after a clockwise turn."""
    w, h = box[2] - box[0], box[3] - box[1]
    return (w, h) if check_turn(turn) in (0, 180) else (h, w)


def to_turned(x: float, y: float, turn: int, box: Box) -> Tuple[float, float]:
    """User space -> the page turned clockwise by `turn`, origin at the bottom left of the turned `box`. (camelot
    reads a page in this frame, from its media box.)"""
    x0, y0, x1, y1 = box
    t = check_turn(turn)
    if t == 0:
        return x - x0, y - y0
    if t == 90:
        return y - y0, x1 - x
    if t == 180:
        return x1 - x, y1 - y
    return y1 - y, x - x0


def from_turned(X: float, Y: float, turn: int, box: Box) -> Tuple[float, float]:
    """The turned frame -> user space (undoes to_turned)."""
    x0, y0, x1, y1 = box
    t = check_turn(turn)
    if t == 0:
        return x0 + X, y0 + Y
    if t == 90:
        return x1 - Y, y0 + X
    if t == 180:
        return x1 - X, y1 - Y
    return x0 + Y, y1 - X


@dataclass(frozen=True)
class View:
    """How a picture of a page was drawn: turned `turn` degrees clockwise in all (the page's /Rotate plus any
    extra turn), `scale` pixels per point, showing `box` (user space). Pixels have their origin at the top left."""
    turn: int
    scale: float
    box: Box
    size: Tuple[int, int] = (0, 0)

    def to_pixels(self, x: float, y: float) -> Tuple[float, float]:
        X, Y = to_turned(x, y, self.turn, self.box)
        return X * self.scale, (turned_size(self.turn, self.box)[1] - Y) * self.scale

    def to_user(self, px: float, py: float) -> Tuple[float, float]:
        height = turned_size(self.turn, self.box)[1]
        return from_turned(px / self.scale, height - py / self.scale, self.turn, self.box)

    def box_to_pixels(self, box: Box) -> Box:
        a, b = self.to_pixels(box[0], box[1]), self.to_pixels(box[2], box[3])
        return norm_box((a[0], a[1], b[0], b[1]))

    def box_to_user(self, box_px: Box) -> Box:
        a, b = self.to_user(box_px[0], box_px[1]), self.to_user(box_px[2], box_px[3])
        return norm_box((a[0], a[1], b[0], b[1]))


# ---------------------------------------------------------------------------------------------- what a page is --
@dataclass
class PageInfo:
    index: int                    # 0-based; the page number people see is index + 1
    width: float                  # points, as the page is shown (its /Rotate applied)
    height: float
    rotation: int                 # the page's /Rotate, degrees clockwise
    mediabox: Box                 # user space
    box: Box                      # the part that is shown: the crop box inside the media box (camelot's frames
                                  # start from it: it reads one-page copies whose media box is this box)
    kind: str
    reason: str
    visible_chars: int = 0
    hidden_chars: int = 0
    image_cover: float = 0.0
    paths: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def number(self) -> int:
        return self.index + 1

    def to_dict(self) -> dict:
        return asdict(self)


def classify(visible: int, hidden: int, cover: float, paths: int = 0) -> Tuple[str, str]:
    """(kind, a one-line reason) from what a page holds: printed and hidden characters, the share of the page that
    pictures cover, and the number of drawn shapes."""
    pct = f"{cover:.0%}"
    if visible >= MIN_TEXT_CHARS or (visible and cover < MIXED_COVER):
        if cover >= MIXED_COVER:
            return "mixed", f"Text layer ({visible:,} characters) and pictures covering {pct} of the page."
        return "digital", f"Text layer: {visible:,} characters."
    if cover > 0:
        why = f"A picture of a page (pictures cover {pct} of it)"
        if hidden:
            why += ", with a hidden text layer from the scanning software's OCR"
        if visible:
            why += f", and only {visible} printed characters"
        return "scanned", why + "."
    if hidden:
        return "scanned", f"No printed text, only a hidden text layer ({hidden:,} characters)."
    if paths >= DRAWN_PATHS:
        return "scanned", f"No text layer: the page is drawn as {paths:,} shapes (text turned into outlines?)."
    return "blank", "No text or pictures on this page."


def coverage(rects: Sequence[Box], box: Box, grid: int = COVER_GRID) -> float:
    """Share of `box` that the union of `rects` covers, sampled on a grid x grid lattice of points."""
    x0, y0, x1, y1 = box
    if not rects or x1 <= x0 or y1 <= y0:
        return 0.0
    import numpy as np

    xs = x0 + (np.arange(grid) + 0.5) * (x1 - x0) / grid
    ys = y0 + (np.arange(grid) + 0.5) * (y1 - y0) / grid
    X, Y = np.meshgrid(xs, ys)
    covered = np.zeros(X.shape, dtype=bool)
    for a, b, c, d in rects:
        covered |= (X >= a) & (X <= c) & (Y >= b) & (Y <= d)
    return float(covered.mean())


def _analyse(page, index: int) -> PageInfo:
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_c

    width, height = page.get_size()
    mediabox = norm_box(page.get_mediabox())
    shown = norm_box(page.get_bbox())
    visible = hidden = paths = unsized = 0
    rects: List[Box] = []
    notes: List[str] = []
    forms: list = []                               # matrices of the form XObjects around the current object
    textpage = page.get_textpage()
    try:
        for n, obj in enumerate(page.get_objects(max_depth=8)):
            if n >= MAX_OBJECTS:
                notes.append(f"A very busy page: only its first {MAX_OBJECTS:,} objects were looked at.")
                break
            del forms[getattr(obj, "level", 0):]
            if obj.type == pdfium_c.FPDF_PAGEOBJ_TEXT:
                chars = max(0, pdfium_c.FPDFTextObj_GetText(obj.raw, textpage.raw, None, 0) // 2 - 1)
                if pdfium_c.FPDFTextObj_GetTextRenderMode(obj.raw) in HIDDEN_MODES:
                    hidden += chars
                else:
                    visible += chars
            elif obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
                try:
                    rect = obj.get_bounds()
                except pdfium.PdfiumError:
                    unsized += 1
                    continue
                for matrix in reversed(forms):     # bounds inside a form are in the form's own space
                    rect = matrix.on_rect(*rect)
                rects.append(norm_box(rect))
            elif obj.type == pdfium_c.FPDF_PAGEOBJ_PATH:
                paths += 1
            elif obj.type == pdfium_c.FPDF_PAGEOBJ_FORM:
                forms.append(obj.get_matrix())
    finally:
        textpage.close()
    if unsized:
        notes.append(f"{unsized} picture(s) without a size weren't counted.")
    cover = coverage(rects, shown)
    kind, reason = classify(visible, hidden, cover, paths)
    return PageInfo(index=index, width=float(width), height=float(height), rotation=check_turn(page.get_rotation()),
                    mediabox=mediabox, box=shown, kind=kind, reason=reason, visible_chars=visible,
                    hidden_chars=hidden, image_cover=round(cover, 4), paths=paths, notes=notes)


def _no_pages(path) -> bool:
    """pdfium won't load a PDF whose page tree is empty, and says only 'success'; pypdf tells the two apart."""
    try:
        import pypdf

        return len(pypdf.PdfReader(str(path)).pages) == 0
    except Exception:  # noqa: BLE001 - any failure here just means "not known to be empty"
        return False


def _open_error(exc, name: str, password: Optional[str], path=None) -> PdfError:
    import pypdfium2.raw as pdfium_c

    code = getattr(exc, "err_code", None)
    # pdfium refuses a PDF with an empty page tree without setting an error of its own (the code left over from
    # an earlier failure is reported), so that case is checked first
    if code in (pdfium_c.FPDF_ERR_SUCCESS, pdfium_c.FPDF_ERR_FORMAT) and path is not None and _no_pages(path):
        return EmptyPdf(f"{name} has no pages.")
    if code == pdfium_c.FPDF_ERR_PASSWORD:
        if password:
            return WrongPassword(f"That password doesn't open {name}. Check it (capital letters count) and try "
                                 "again.")
        return PasswordNeeded(f"{name} is protected with a password. Enter it to open the file.")
    if code == pdfium_c.FPDF_ERR_FORMAT:
        return DamagedPdf(f"{name} is damaged or isn't a PDF, so it can't be opened. If a PDF viewer can open it, "
                          "save a new copy from there and import that.")
    if code == pdfium_c.FPDF_ERR_FILE:
        return PdfError(f"{name} can't be read: the file is missing or you don't have permission to open it.")
    if code == pdfium_c.FPDF_ERR_SECURITY:
        return PdfError(f"{name} is protected in a way this app can't open.")
    if code == pdfium_c.FPDF_ERR_SUCCESS:
        return DamagedPdf(f"{name} can't be opened: its structure is broken.")
    return PdfError(f"{name} can't be opened ({exc}).")


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def javascript_engine() -> bool:
    """True if the pdfium build in use has a JavaScript engine (V8). The standard pypdfium2 wheels don't; this
    app relies on that, and a test checks it."""
    import pypdfium2 as pdfium

    return "V8" in tuple(getattr(pdfium.PDFIUM_INFO, "flags", ()) or ())


def parse_pages(text: str, n_pages: int) -> List[int]:
    """0-based page indices from what a person types: '1-5, 8, 12-' (an open end runs to the last page); 'all'
    or nothing: every page. A ValueError says what's wrong."""
    text = re.sub(r"\s*[-–]\s*", "-", (text or "").strip().lower())
    if text in ("", "all"):
        return list(range(n_pages))
    out = set()
    for part in filter(None, re.split(r"[,;\s]+", text)):
        m = re.fullmatch(r"(\d*)-(\d*)|(\d+)", part)
        if not m or part == "-":
            raise ValueError(f"'{part}' isn't a page or a range like 3-7.")
        if m.group(3):
            first = last = int(m.group(3))
        else:
            first = int(m.group(1) or 1)
            last = int(m.group(2) or n_pages)
        if first < 1 or last > n_pages or first > last:
            raise ValueError(f"'{part}' is outside pages 1-{n_pages}.")
        out.update(range(first - 1, last))
    return sorted(out)


# ------------------------------------------------------------------------------------------------- the document --
class PdfDoc:
    """An open PDF (a context manager; or call close()). Page details are looked at when first asked for, and
    kept."""

    def __init__(self, path, password: Optional[str] = None, max_mb: float = MAX_FILE_MB):
        self.path = Path(path)
        self.name = self.path.name
        self._pdf = None
        try:
            self.size = self.path.stat().st_size
        except OSError as exc:
            raise PdfError(f"{self.name} can't be opened: {exc.strerror or exc}.") from None
        if not self.path.is_file():
            raise PdfError(f"{self.name} isn't a file.")
        if self.size == 0:
            raise EmptyPdf(f"{self.name} is empty (0 bytes): there is nothing in it to import.")
        if self.size > max_mb * 1_000_000:
            raise TooBig(f"{self.name} is {self.size / 1e6:,.0f} MB. PDFs up to {max_mb:,.0f} MB can be opened "
                         "(the limit is in the scanner settings).")
        import pypdfium2 as pdfium
        import pypdfium2.raw as pdfium_c

        self._password = password or None
        with PDFIUM_LOCK:
            try:
                self._pdf = pdfium.PdfDocument(str(self.path), password=self._password)  # read from disk as needed
            except pdfium.PdfiumError as exc:
                raise _open_error(exc, self.name, self._password, self.path) from None
            self.n_pages = len(self._pdf)
            self.encrypted = pdfium_c.FPDF_GetSecurityHandlerRevision(self._pdf.raw) != -1
            self.permissions = pdfium_c.FPDF_GetDocPermissions(self._pdf.raw) & 0xFFFFFFFF
        if self.n_pages == 0:
            self.close()
            raise EmptyPdf(f"{self.name} has no pages.")
        self._sha256: Optional[str] = None
        self._info: Dict[int, PageInfo] = {}
        self._chars: Dict[int, List[Tuple[int, float, float]]] = {}
        self._thumbs: "OrderedDict[tuple, object]" = OrderedDict()
        self._tmpdir: Optional[str] = None

    def __enter__(self) -> "PdfDoc":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def closed(self) -> bool:
        return self._pdf is None

    @property
    def sha256(self) -> str:
        if self._sha256 is None:
            self._sha256 = file_sha256(self.path)
        return self._sha256

    @property
    def may_copy_text(self) -> bool:
        return bool(self.permissions & COPY_PERMISSION)

    @contextmanager
    def page(self, index: int) -> Iterator[object]:
        """The pdfium page, under PDFIUM_LOCK; closed afterwards."""
        if not 0 <= index < self.n_pages:
            raise IndexError(f"There is no page {index + 1}: {self.name} has {self.n_pages} pages.")
        with PDFIUM_LOCK:
            if self._pdf is None:
                raise PdfError(f"{self.name} is closed.")
            page = self._pdf[index]
            try:
                yield page
            finally:
                page.close()

    # ------------------------------------------------------------------------------------------- what's on it --
    def page_info(self, index: int) -> PageInfo:
        info = self._info.get(index)
        if info is None:
            with self.page(index) as page:
                info = _analyse(page, index)
            self._info[index] = info
        return info

    def looked_at(self) -> List[int]:
        return sorted(self._info)

    def text_directions(self, index: int) -> List[Tuple[int, float, float]]:
        """(turn, x, y) for each printed character of a page: the turn in all (clockwise, as shown) at which it
        reads left to right, and its centre in user space."""
        if index in self._chars:
            return self._chars[index]
        import ctypes

        import pypdfium2.raw as pdfium_c

        out = []
        with self.page(index) as page:
            textpage = page.get_textpage()
            try:
                tp = textpage.raw
                left, right, bottom, top = (ctypes.c_double() for _ in range(4))
                for i in range(min(pdfium_c.FPDFText_CountChars(tp), MAX_CHARS)):
                    u = pdfium_c.FPDFText_GetUnicode(tp, i)
                    if u <= 32 or u > 0x10FFFF or chr(u).isspace() or pdfium_c.FPDFText_IsGenerated(tp, i) == 1:
                        continue
                    angle = pdfium_c.FPDFText_GetCharAngle(tp, i)         # radians, measured clockwise
                    if angle < 0 or not pdfium_c.FPDFText_GetCharBox(tp, i, ctypes.byref(left), ctypes.byref(right),
                                                                       ctypes.byref(bottom), ctypes.byref(top)):
                        continue
                    turn = int(round(((-math.degrees(angle)) % 360) / 90.0)) % 4 * 90
                    out.append((turn, (left.value + right.value) / 2, (bottom.value + top.value) / 2))
            finally:
                textpage.close()
        self._chars[index] = out
        return out

    def upright(self, index: int, box: Optional[Box] = None) -> Tuple[Optional[int], float]:
        """(the turn in all at which most of the text reads left to right, the share of characters that agree);
        (None, 0.0) without text. `box` (user space) looks only at the characters inside it."""
        chars = self.text_directions(index)
        if box is not None:
            x0, y0, x1, y1 = box
            chars = [c for c in chars if x0 <= c[1] <= x1 and y0 <= c[2] <= y1]
        if not chars:
            return None, 0.0
        turn, n = Counter(c[0] for c in chars).most_common(1)[0]
        return turn, n / len(chars)

    def upright_turn(self, index: int, agree: float = 0.6) -> int:
        """The extra turn (on top of the page's /Rotate) that shows the page with its text reading left to right;
        0 without text, or when its text doesn't clearly run one way."""
        turn, share = self.upright(index)
        if turn is None or share < agree:
            return 0
        return (turn - self.page_info(index).rotation) % 360

    # ----------------------------------------------------------------------------------------------- pictures --
    def render(self, index: int, dpi: Optional[float] = None, scale: Optional[float] = None, turn: int = 0,
               max_pixels: int = MAX_RENDER_PIXELS):
        """(PIL RGB image, View) of a page at `dpi` (or `scale` pixels per point; a point is 1/72 inch), with an
        extra `turn` on top of its /Rotate; drawn smaller when it would have more than `max_pixels` pixels."""
        info = self.page_info(index)
        extra = check_turn(turn)
        s = dpi / 72.0 if dpi else float(scale or 1.0)
        if s <= 0:
            raise ValueError("The scale must be positive.")
        area = max(info.width * info.height, 1.0)
        if area * s * s > max_pixels:
            s = math.sqrt(max_pixels / area)
        with self.page(index) as page:
            bitmap = page.render(scale=s, rotation=extra, may_draw_forms=False)
            try:
                image = bitmap.to_pil().convert("RGB")       # a copy: the bitmap's memory is freed next
            finally:
                bitmap.close()
        return image, View((info.rotation + extra) % 360, s, info.box, image.size)

    def thumbnail(self, index: int, height: int = THUMB_HEIGHT):
        key = (index, int(height))
        image = self._thumbs.get(key)
        if image is not None:
            self._thumbs.move_to_end(key)
            return image
        info = self.page_info(index)
        image, _ = self.render(index, scale=height / max(info.height, 1.0), max_pixels=max(1, 6 * height * height))
        self._thumbs[key] = image
        while len(self._thumbs) > THUMB_CACHE:
            self._thumbs.popitem(last=False)
        return image

    # ------------------------------------------------------------------------------------------- for camelot --
    @contextmanager
    def single_page(self, index: int) -> Iterator[Tuple[str, Box]]:
        """(path, box): a one-page copy of a page for camelot, in a private temporary folder, deleted afterwards,
        and the box that is its media box (camelot's frames start from it).

        Why a copy: camelot opens the file itself (its ruling-line method with pdfium), so it can't be given a
        password; it measures from the media box but draws only the crop box, so on a cropped page its lines and
        its text wouldn't line up; and re-opening a huge PDF for every page is slow. The copy has no password, a
        media box equal to the shown part of the page, and nothing but that page. Refused when the PDF's own
        settings forbid copying its text."""
        if not self.may_copy_text:
            raise CopyingNotAllowed(f"{self.name}'s settings don't allow copying its text. If you have its owner "
                                    "password, open it again with that password.")
        import pypdfium2 as pdfium

        info = self.page_info(index)
        if self._tmpdir is None:
            self._tmpdir = tempfile.mkdtemp(prefix="plotstudio-pdf-")    # readable by this user only
        target = os.path.join(self._tmpdir, f"page-{index + 1}.pdf")
        with PDFIUM_LOCK:
            if self._pdf is None:
                raise PdfError(f"{self.name} is closed.")
            copy = pdfium.PdfDocument.new()
            try:
                copy.import_pages(self._pdf, [index])
                page = copy[0]
                try:
                    page.set_mediabox(*info.box)
                    page.set_cropbox(*info.box)
                finally:
                    page.close()
                copy.save(target)
            finally:
                copy.close()
        try:
            yield target, info.box
        finally:
            try:
                os.remove(target)
            except OSError as exc:
                warnings.warn(f"The temporary copy of page {index + 1} ({target}) couldn't be removed: {exc}")

    def close(self) -> None:
        with PDFIUM_LOCK:
            if self._pdf is not None:
                self._pdf.close()
                self._pdf = None
        self._thumbs.clear()
        if self._tmpdir:
            try:
                shutil.rmtree(self._tmpdir)
            except OSError as exc:
                warnings.warn(f"The temporary folder {self._tmpdir} couldn't be removed: {exc}")
            self._tmpdir = None
