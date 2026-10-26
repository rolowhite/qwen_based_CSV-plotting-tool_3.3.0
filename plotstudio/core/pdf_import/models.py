"""The one contract every table reader returns: `Table` made of `Cell`s, plus `Issue`s, pages and jobs.

A cell keeps the text exactly as it was read (only line breaks inside a cell become spaces), where it came from
(`source`) and, when the reader knows it, its box on the page image. Turning text into numbers is a separate,
visible step; nothing here changes a value.
"""
from __future__ import annotations

import copy
import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

SOURCES = ("vlm", "ocr", "both", "user", "pdf_text")
SEVERITIES = ("error", "check")          # shown as red / yellow, always with words
Box = Tuple[float, float, float, float]  # x0, y0, x1, y1 in page-image pixels (origin top left)


def now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def one_line(text) -> str:
    """A cell's text on one line: line breaks inside a cell (a wrapped cell) become single spaces."""
    text = "" if text is None else str(text)
    return re.sub(r"\s*[\r\n]+\s*", " ", text).strip()


@dataclass
class Cell:
    row: int
    col: int
    text: str
    confidence: Optional[float] = None
    bbox_on_image: Optional[Box] = None
    source: str = "vlm"
    pdf_bbox: Optional[Box] = None        # PDF points (x0, y0, x1, y1), origin bottom left: digital pages only

    def to_dict(self) -> dict:
        return {"row": self.row, "col": self.col, "text": self.text, "confidence": self.confidence,
                "bbox": list(self.bbox_on_image) if self.bbox_on_image else None, "source": self.source}


@dataclass
class Issue:
    severity: str                          # "error" (red) or "check" (yellow)
    row: Optional[int]
    col: Optional[int]
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {"severity": self.severity, "row": self.row, "col": self.col, "message": self.message,
                "suggestion": self.suggestion}


FORMULA_START = re.compile(r"^\s*[=@]|^\s*[+\-](?=\S)(?![\d.,\s]*\d[\d.,\s]*%?\s*$)")


def looks_like_formula(text: str) -> bool:
    """True for cell text a spreadsheet program would run as a formula ('=SUM(A1)', '@cmd', '+A1'); numbers like
    -320 or +4.5% are fine."""
    return bool(text) and bool(FORMULA_START.match(text))


@dataclass
class Table:
    cells: List[Cell]
    n_rows: int
    n_cols: int
    header_rows: int = 1
    source_page: int = 0                   # index of the page on the page strip (PDF: its page number, from 1)
    bbox: Optional[Box] = None             # the table's box on the page image (PDF tables: in PDF points, like
                                           # Cell.pdf_bbox)
    engine: str = ""                       # e.g. "ollama/qwen2.5vl:7b", "camelot lattice"
    notes: List[str] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)

    # ---------------------------------------------------------------- build --
    @classmethod
    def from_rows(cls, rows, header_rows: int = 1, source: str = "vlm", boxes=None, **kw) -> "Table":
        """A table from rows of text (each row a list). Short rows are padded with empty cells, and each padded
        cell is a yellow issue: the reader saw fewer cells in that row than in the widest one."""
        rows = [[one_line(v) for v in (r if isinstance(r, (list, tuple)) else [r])] for r in rows]
        n_cols = max((len(r) for r in rows), default=0)
        cells, issues = [], []
        for i, r in enumerate(rows):
            if len(r) < n_cols:
                issues.append(Issue("check", i, len(r), f"Row {i + 1} has {len(r)} of {n_cols} cells: the missing "
                                                        "ones are empty here. Check them against the page."))
            for j in range(n_cols):
                box = None
                if boxes is not None and i < len(boxes) and boxes[i] is not None and j < len(boxes[i]):
                    box = boxes[i][j]
                cells.append(Cell(i, j, r[j] if j < len(r) else "", None, box, source))
        table = cls(cells=cells, n_rows=len(rows), n_cols=n_cols,
                    header_rows=max(0, min(int(header_rows or 0), len(rows))), issues=issues, **kw)
        table.issues += table.formula_issues()
        return table

    def copy(self) -> "Table":
        return copy.deepcopy(self)

    # ------------------------------------------------------------------ read --
    def cell(self, row: int, col: int) -> Cell:
        return self.cells[row * self.n_cols + col]

    def grid(self) -> List[List[str]]:
        return [[self.cell(r, c).text for c in range(self.n_cols)] for r in range(self.n_rows)]

    @property
    def has_cell_boxes(self) -> bool:
        return any(c.bbox_on_image for c in self.cells)

    def column_names(self) -> List[str]:
        return flatten_header(self.grid()[:self.header_rows], self.n_cols)

    def to_frame(self) -> pd.DataFrame:
        """The body as text, with the header rows flattened into column names (Parent_Child)."""
        grid = self.grid()
        body = grid[self.header_rows:]
        return pd.DataFrame(body, columns=self.column_names(), dtype=object) if self.n_cols else pd.DataFrame()

    def frame_position(self, row: int, col: int) -> Optional[Tuple[int, int]]:
        """(DataFrame row, column) of a table cell, or None for a header cell."""
        return None if row < self.header_rows else (row - self.header_rows, col)

    def issues_at(self, row: int, col: int) -> List[Issue]:
        return [i for i in self.issues if (i.row is None or i.row == row) and (i.col is None or i.col == col)
                and not (i.row is None and i.col is None)]

    def formula_issues(self) -> List[Issue]:
        return [Issue("check", c.row, c.col, f"'{c.text[:30]}' starts like a formula: a spreadsheet program may run "
                                             "it instead of showing it. The CSV keeps the text as it is; the XLSX "
                                             "stores it as text.")
                for c in self.cells if looks_like_formula(c.text)]

    def info(self) -> dict:
        return {"page": self.source_page, "rows": self.n_rows, "columns": self.n_cols, "header_rows": self.header_rows,
                "bbox": list(self.bbox) if self.bbox else None, "engine": self.engine,
                "column_names": self.column_names(), "notes": list(self.notes)}


def flatten_header(header_rows, n_cols: Optional[int] = None) -> List[str]:
    """Column names from one or more header rows. A parent cell that spans several columns (read as one text and
    empty cells to its right) gives each child 'Parent_Child'; a name that is empty in every header row becomes
    'column_<n>', and a name used twice gets ' (2)'."""
    n = n_cols if n_cols is not None else max((len(r) for r in header_rows), default=0)
    grid = [[one_line(r[i]) if i < len(r) else "" for i in range(n)] for r in header_rows]
    for k in range(len(grid) - 1):                      # spread parents right over the empty (merged) cells
        last = ""
        for i in range(n):
            if grid[k][i]:
                last = grid[k][i]
            elif last and any(grid[j][i] for j in range(k + 1, len(grid))):
                grid[k][i] = last
            else:
                last = ""
    names, seen = [], set()
    for i in range(n):
        parts = []
        for k in range(len(grid)):
            p = grid[k][i]
            if p and (not parts or parts[-1] != p):
                parts.append(p)
        name = label = "_".join(parts) or f"column_{i + 1}"
        k = 1
        while name in seen:
            k += 1
            name = f"{label} ({k})"
        seen.add(name)
        names.append(name)
    return names


@dataclass
class Edit:
    row: int
    col: int
    old: str
    new: str
    old_source: str
    time: str

    def to_dict(self) -> dict:
        return {"row": self.row, "col": self.col, "old": self.old, "new": self.new, "time": self.time}


class EditLog:
    """Edits made in the review grid: each marks the cell source='user'; undo / redo step through them."""

    def __init__(self, table: Table):
        self.table = table
        self.done: List[Edit] = []
        self.undone: List[Edit] = []
        self.header_changes: List[dict] = []

    def set(self, row: int, col: int, text: str) -> Optional[Edit]:
        cell = self.table.cell(row, col)
        text = one_line(text)
        if text == cell.text:
            return None
        edit = Edit(row, col, cell.text, text, cell.source, now())
        cell.text, cell.source = text, "user"
        self.done.append(edit)
        self.undone.clear()
        return edit

    def undo(self) -> Optional[Edit]:
        if not self.done:
            return None
        edit = self.done.pop()
        cell = self.table.cell(edit.row, edit.col)
        cell.text, cell.source = edit.old, edit.old_source
        self.undone.append(edit)
        return edit

    def redo(self) -> Optional[Edit]:
        if not self.undone:
            return None
        edit = self.undone.pop()
        cell = self.table.cell(edit.row, edit.col)
        cell.text, cell.source = edit.new, "user"
        self.done.append(edit)
        return edit

    def set_header_rows(self, n: int) -> bool:
        n = max(0, min(int(n), self.table.n_rows))
        if n == self.table.header_rows:
            return False
        self.header_changes.append({"header_rows": [self.table.header_rows, n], "time": now()})
        self.table.header_rows = n
        return True

    def history(self) -> List[dict]:
        return [e.to_dict() for e in self.done]


@dataclass
class Page:
    index: int                              # position on the page strip (0-based)
    image_path: Optional[str] = None        # the photo, or the PDF page rendered as an image
    pdf_page: Optional[int] = None          # 1-based page number in the PDF
    kind: str = "photo"                     # photo | digital | scanned | mixed | empty
    kind_override: Optional[str] = None     # the user's choice, when they changed the badge
    width: int = 0
    height: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def effective_kind(self) -> str:
        return self.kind_override or self.kind


@dataclass
class TableRegion:
    page: int
    bbox: Box
    label: str = ""


@dataclass
class ScanJob:
    """One import: where the pages came from, the pages in the order shown, and what was read."""
    id: str
    source: str                             # phone | files | pdf
    pages: List[Page] = field(default_factory=list)
    folder: Optional[str] = None            # the inbox folder of a phone upload
    pdf_path: Optional[str] = None
    pdf_sha256: Optional[str] = None
    created: str = field(default_factory=now)

    def page(self, index: int) -> Page:
        return self.pages[index]
