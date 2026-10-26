"""Tables from a page's text layer, read by two camelot methods that work differently and then compared.

  lattice ("ruling lines")    finds the lines drawn around and between cells, and puts each cell's text in it
  network ("text positions")  finds rows and columns from how the words line up, so it works without lines
Both find a table with the same cells: "agree" (high trust). Both find it with different cells: "differ"; both
versions are kept and the user picks one (the ruling-line version comes first: its lines were drawn by the
author). Only one finds it: "one". A marked area (a rectangle the user draws, with optional column dividers) is
read with camelot's stream method inside that rectangle: "marked".

Every cell keeps the PDF's exact text: a line break inside a cell becomes one space (a wrapped cell) and nothing
else changes. Numbers stay text; turning them into numbers is a separate step the user sees. Each cell keeps its
box in PDF user space (Cell.pdf_bbox), so the review grid can light it up on the page at any zoom or turn.

camelot reads a page in its own frame: when most of the text runs sideways, it turns the page a quarter turn
first (its Table.rotation says which way) so the table comes out upright. Boxes are mapped back from that frame,
and `check_upright` flags a result that still reads sideways.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .models import Issue, Table, one_line
from .inspect import (MAX_RENDER_PIXELS, PDFIUM_LOCK, Box, PageInfo, PdfDoc, PdfError, View,
                      from_turned, norm_box, to_turned)

METHODS = {"lattice": "ruling lines", "network": "text positions", "stream": "marked area"}
ORDER = ("lattice", "network")
MATCH = 0.6                 # two methods found the same table when the boxes overlap by this share of the smaller
MAX_HEADER_ROWS = 3
LATTICE_DPI = 300           # camelot's own default; lower on very large pages (MAX_RENDER_PIXELS)
UPRIGHT_AGREE = 0.6         # share of a table's characters that must run one way to judge which way it reads
LOW_ACCURACY = 90.0         # camelot's accuracy (% of the area's text that fitted the cells) below this: a check
TURN = {"clockwise": -90, "anticlockwise": 90}   # camelot's Table.rotation -> the extra turn it read the page in


@dataclass
class Found:
    """One table on a page, as each method read it, and which version is used."""
    page: int                                     # 0-based page index
    versions: Dict[str, Table]                    # method -> table, in ORDER
    frames: Dict[str, int]                        # method -> the turn camelot read the page in
    trust: str                                    # agree | differ | one | marked
    chosen: str                                   # the method whose version is used
    number: int = 0                               # 1-based, in reading order on the page
    ticked: bool = True
    notes: List[str] = field(default_factory=list)

    @property
    def table(self) -> Table:
        return self.versions[self.chosen]

    @property
    def bbox(self) -> Optional[Box]:
        boxes = [t.bbox for t in self.versions.values() if t.bbox]
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes),
                max(b[3] for b in boxes))

    def choose(self, method: str) -> None:
        if method not in self.versions:
            raise KeyError(f"No version read by {method}.")
        self.chosen = method

    @property
    def label(self) -> str:
        if self.trust == "agree":
            return "Both methods agree"
        if self.trust == "differ":
            return "The two methods differ: pick a version"
        if self.trust == "marked":
            return "Marked by hand"
        return f"Read by {METHODS[self.chosen]} only"

    @property
    def method_label(self) -> str:
        """For the sidecar and the provenance note."""
        if self.trust == "agree":
            return "two methods agree"
        if self.trust == "differ":
            return f"{METHODS[self.chosen]}, picked over the other method's version"
        return METHODS[self.chosen]


# ------------------------------------------------------------------------------------------------- camelot ---
def lattice_dpi(info: PageInfo) -> int:
    """camelot draws the page to find its lines; on a huge page it draws at a lower resolution."""
    area = max(info.width * info.height, 1.0)
    return int(max(36, min(LATTICE_DPI, 72 * math.sqrt(MAX_RENDER_PIXELS / area))))


def _camelot(path: str, info: PageInfo, flavor: str, **options):
    """camelot's tables in a one-page copy (PdfDoc.single_page) of a page, and its warnings worth showing."""
    try:
        import camelot
    except ImportError:
        raise PdfError("Reading tables from PDFs needs camelot-py: pip install -r requirements-scanner.txt") from None
    kw = dict(pages="1", flavor=flavor, suppress_stdout=True)
    if flavor == "lattice":                       # draw with pdfium only: never fall back to running Ghostscript
        kw.update(resolution=lattice_dpi(info), backend="pdfium", use_fallback=False)
    kw.update(options)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with PDFIUM_LOCK:
            tables = list(camelot.read_pdf(path, **kw))
    quiet = ("No tables found", "is image-based")
    notes = sorted({str(w.message) for w in caught if not any(q in str(w.message) for q in quiet)})
    return tables, notes


def guess_header_rows(rows: List[List[str]], cells=None) -> int:
    """How many rows at the top are headings: a guess the user can change. With ruling lines (`cells`, camelot's
    lattice cells): a heading cell whose bottom line is missing reaches into the next row, so that row is part of
    the header too. Without lines: a first row with few headings over a fuller second row (a heading spread over
    several columns), or a spread heading followed by a row with no label in the first column."""
    n = len(rows)
    if n < 2:
        return n
    limit = min(MAX_HEADER_ROWS, n - 1)
    h = 1
    if cells is not None:
        while h < limit and h - 1 < len(cells) and any(rows[h - 1]) and any(not c.bottom for c in cells[h - 1]):
            h += 1
        return h
    filled = [sum(1 for v in r if v) for r in rows]
    width = max(len(rows[0]), 1)
    if 0 < filled[0] <= width / 2 and filled[1] > filled[0]:
        h = 2
    elif filled[0] and any(not v for v in rows[0][1:]):
        while h < limit and not rows[h][0] and any(rows[h]) and rows[h + 1][0]:
            h += 1
    return min(h, limit)


def _merged_boxes(cells) -> List[List[Tuple[float, float, float, float]]]:
    """For camelot's lattice cells: each cell's box grown to the merged cell it belongs to (cells with no line
    between them are one cell on the page), so highlighting a merged heading lights up all of it."""
    n_rows = len(cells)
    n_cols = len(cells[0]) if n_rows else 0
    parent = {(r, c): (r, c) for r in range(n_rows) for c in range(n_cols)}

    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for r in range(n_rows):
        for c in range(n_cols):
            cell = cells[r][c]
            if c + 1 < n_cols and not cell.right:
                parent[root((r, c + 1))] = root((r, c))
            if r + 1 < n_rows and not cell.bottom:
                parent[root((r + 1, c))] = root((r, c))
    union: Dict[tuple, list] = {}
    for (r, c) in parent:
        cell = cells[r][c]
        box = (min(cell.x1, cell.x2), min(cell.y1, cell.y2), max(cell.x1, cell.x2), max(cell.y1, cell.y2))
        u = union.setdefault(root((r, c)), list(box))
        u[:] = [min(u[0], box[0]), min(u[1], box[1]), max(u[2], box[2]), max(u[3], box[3])]
    return [[tuple(union[root((r, c))]) for c in range(n_cols)] for r in range(n_rows)]


def to_table(ct, info: PageInfo, method: str) -> Tuple[Table, int]:
    """A camelot table as the scanner's Table (cells source='pdf_text', boxes in user space), and the turn camelot
    read the page in."""
    frame = (info.rotation + TURN.get(getattr(ct, "rotation", "") or "", 0)) % 360
    rows = [[one_line(v) for v in row] for row in ct.df.values.tolist()]
    header = guess_header_rows(rows, ct.cells if method == "lattice" else None)
    table = Table.from_rows(rows, header_rows=header, source="pdf_text", source_page=info.number,
                            engine=f"camelot {method}")
    boxes = _merged_boxes(ct.cells) if method == "lattice" else None
    for cell in table.cells:
        try:
            c = ct.cells[cell.row][cell.col]
        except IndexError:
            continue
        x1, y1, x2, y2 = boxes[cell.row][cell.col] if boxes else (c.x1, c.y1, c.x2, c.y2)
        a = from_turned(x1, y1, frame, info.box)
        b = from_turned(x2, y2, frame, info.box)
        cell.pdf_bbox = norm_box((a[0], a[1], b[0], b[1]))
    corners = getattr(ct, "_bbox", None)
    if corners:
        a = from_turned(corners[0], corners[1], frame, info.box)
        b = from_turned(corners[2], corners[3], frame, info.box)
        table.bbox = norm_box((a[0], a[1], b[0], b[1]))
    else:
        boxes = [c.pdf_bbox for c in table.cells if c.pdf_bbox]
        if boxes:
            table.bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes),
                          max(b[3] for b in boxes))
    table.notes.append(f"Read from the PDF's text layer ({METHODS[method]}): each cell's text is exactly as in "
                       "the PDF.")
    if frame != info.rotation:
        table.notes.append("The table is printed sideways: it was read a quarter turn round, so it comes out "
                           "upright.")
    accuracy = (getattr(ct, "parsing_report", None) or {}).get("accuracy")
    if isinstance(accuracy, (int, float)) and accuracy < LOW_ACCURACY:
        table.issues.append(Issue("check", None, None, f"Only {accuracy:.0f}% of the text in this area fitted the "
                                                       "cells cleanly (camelot's own measure): look for text split "
                                                       "across cells or run together."))
    return table, frame


def _overlap(a: Optional[Box], b: Optional[Box]) -> float:
    """The overlap of two boxes as a share of the smaller one."""
    if not a or not b:
        return 0.0
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return (w * h) / small if w > 0 and h > 0 and small > 0 else 0.0


def combine(page: int, read: Dict[str, List[Tuple[Table, int]]]) -> List[Found]:
    """Pairs the tables the two methods found on a page by where they are, and compares their cells."""
    lattice, network = read.get("lattice", []), read.get("network", [])
    found, used = [], set()
    for t, frame in lattice:
        scores = [(_overlap(t.bbox, u.bbox), j) for j, (u, _) in enumerate(network) if j not in used]
        score, j = max(scores, default=(0.0, None))
        if j is not None and score >= MATCH:
            used.add(j)
            u, uframe = network[j]
            trust = "agree" if t.grid() == u.grid() else "differ"
            found.append(Found(page, {"lattice": t, "network": u}, {"lattice": frame, "network": uframe}, trust,
                               "lattice"))
        else:
            found.append(Found(page, {"lattice": t}, {"lattice": frame}, "one", "lattice"))
    for j, (u, frame) in enumerate(network):
        if j not in used:
            found.append(Found(page, {"network": u}, {"network": frame}, "one", "network"))
    return found


def check_upright(doc: PdfDoc, found: Found) -> None:
    """Flags a version that reads sideways: most characters inside it run another way than the frame camelot
    read it in (camelot turns a page by what most of ITS text does; a sideways table on an upright page can't be
    read upright from the text layer)."""
    for method, table in found.versions.items():
        if not table.bbox:
            continue
        turn, share = doc.upright(found.page, table.bbox)
        if turn is not None and share >= UPRIGHT_AGREE and turn != found.frames[method]:
            table.issues.append(Issue("error", None, None, "This table runs a different way from most of the page, "
                                                           "so it came out sideways. Check it closely, or read the "
                                                           "page as a picture turned upright."))


def reading_order(found: List[Found], info: PageInfo) -> List[Found]:
    """Top to bottom, then left to right, as the page reads; numbered from 1."""
    def key(f: Found):
        box = f.table.bbox or (0.0, 0.0, 0.0, 0.0)
        frame = f.frames[f.chosen]
        a = to_turned(box[0], box[1], frame, info.box)
        b = to_turned(box[2], box[3], frame, info.box)
        return (-round(max(a[1], b[1]), 1), round(min(a[0], b[0]), 1))
    ordered = sorted(found, key=key)
    for n, f in enumerate(ordered, start=1):
        f.number = n
    return ordered


def read_page(doc: PdfDoc, index: int, methods: Sequence[str] = ORDER) -> Tuple[List[Found], List[str]]:
    """The tables on one page (in reading order) and notes worth showing (a method that failed, camelot's
    warnings). Runs in a worker thread; pdfium calls hold PDFIUM_LOCK."""
    info = doc.page_info(index)
    read: Dict[str, List[Tuple[Table, int]]] = {}
    notes: List[str] = []
    unknown = [m for m in methods if m not in ORDER]
    if unknown:
        raise ValueError(f"Unknown method {unknown[0]!r}.")
    with doc.single_page(index) as (path, _box):
        for method in methods:
            try:
                tables, warns = _camelot(path, info, method)
            except PdfError:
                raise
            except Exception as exc:  # noqa: BLE001 - camelot can fail on an odd page: say so, keep the other
                notes.append(f"The {METHODS[method]} method couldn't read page {info.number} "
                             f"({type(exc).__name__}: {exc}).")
                continue
            notes += [f"{METHODS[method].capitalize()}: {w}" for w in warns]
            read[method] = [to_table(ct, info, method) for ct in tables]
    found = combine(index, read)
    for f in found:
        check_upright(doc, f)
    return reading_order(found, info), notes


# ------------------------------------------------------------------------------------------- a marked area ---
def camelot_frame(doc: PdfDoc, index: int) -> int:
    """The turn camelot will read a page in: the page's own, or a quarter turn more when most text on it runs
    sideways (camelot doesn't turn upside-down text)."""
    info = doc.page_info(index)
    turn, share = doc.upright(index)
    if turn is not None and share >= 0.5 and (turn - info.rotation) % 180 == 90:
        return turn
    return info.rotation


def read_area(doc: PdfDoc, index: int, view: View, rect_px: Box, dividers_px: Sequence[float] = ()) -> Found:
    """The table inside a rectangle the user drew on a picture of the page (`view` says how the picture was
    drawn), read with camelot's stream method. `dividers_px`: x positions (pixels) of column dividers the user
    placed; without them camelot finds the columns. Text crossing a divider stays whole, in one column."""
    info = doc.page_info(index)
    rect_px = norm_box(rect_px)
    rect = view.box_to_user(rect_px)
    middle = (rect_px[1] + rect_px[3]) / 2

    def options(frame: int):
        if dividers_px and (view.turn - frame) % 180:
            raise PdfError("Turn the page so the table reads upright, then place the column dividers again.")
        a = to_turned(rect[0], rect[1], frame, info.box)
        b = to_turned(rect[2], rect[3], frame, info.box)
        x1, x2 = sorted((a[0], b[0]))
        y1, y2 = sorted((a[1], b[1]))
        cols = []
        for px in dividers_px:
            X, _ = to_turned(*view.to_user(px, middle), frame, info.box)
            if x1 < X < x2:
                cols.append(X)
        opts = {"table_areas": [f"{x1:.2f},{y2:.2f},{x2:.2f},{y1:.2f}"]}      # left, top, right, bottom
        if cols:
            opts["columns"] = [",".join(f"{c:.2f}" for c in sorted(cols))]
        return opts, len(cols)

    empty = PdfError("There's no text inside the marked area. Draw the rectangle around the table's text.")
    if doc.upright(index, rect)[0] is None:
        raise empty
    frame = camelot_frame(doc, index)
    opts, n_cols = options(frame)
    with doc.single_page(index) as (path, _box):
        try:
            tables, notes = _camelot(path, info, "stream", **opts)
            if tables:
                actual = (info.rotation + TURN.get(getattr(tables[0], "rotation", "") or "", 0)) % 360
                if actual != frame:               # camelot turned the page another way: once more, in its frame
                    opts, n_cols = options(actual)
                    tables, notes = _camelot(path, info, "stream", **opts)
        except PdfError:
            raise
        except Exception as exc:  # noqa: BLE001 - camelot can fail on an odd area: say so, in words
            raise PdfError(f"The marked area couldn't be read ({type(exc).__name__}: {exc}). Try a slightly larger "
                           "rectangle, or other column dividers.") from exc
    tables = [t for t in tables if t.df.size and any(str(v).strip() for v in t.df.values.ravel())]
    if not tables:
        raise empty
    table, used = to_table(tables[0], info, "stream")
    table.notes.append("Marked by hand" + (f", with {n_cols} column divider{'s' if n_cols != 1 else ''}."
                                           if n_cols else "; camelot found the columns."))
    found = Found(index, {"stream": table}, {"stream": used}, "marked", "stream", notes=list(notes))
    check_upright(doc, found)
    return found
