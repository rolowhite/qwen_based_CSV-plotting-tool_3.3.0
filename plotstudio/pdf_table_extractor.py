"""Extract tables from PDFs: text pages from their text layer, scanned pages by OCR.

A digital page is read with camelot's two methods (ruling lines and text positions) and they are compared
(core/pdf_import/digital.py); its text is never changed and never sent to OCR. A scanned page is drawn at
200 dpi and read by the image OCR. Each DataFrame's attrs say where it came from and what to check:
  page_number, pages   the page(s) it came from (1-based)
  method               e.g. "text layer: two methods agree", "OCR: grid lines"
  notes                things to check about this table
  document_notes       pages that couldn't be read, or were skipped, and why
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .core.pdf_import.inspect import (EmptyPdf, PasswordNeeded, PdfError, WrongPassword,  # noqa: F401 (re-exported)
                                      TooBig)

MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_PAGES = 200            # pages read in one import
SCAN_DPI = 200
PDFTableError = PdfError   # the name the app and older tests use


def extract_tables(pdf_path, password=None, progress=None) -> list[pd.DataFrame]:
    """Every table in the PDF (at most MAX_PAGES pages), tables continued on the next page with the same columns
    joined. Raises PasswordNeeded / WrongPassword (ask for the password and call again) or PdfError."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")
    try:
        from .core.pdf_import import digital
        from .core.pdf_import.inspect import PdfDoc
    except ImportError as exc:                                    # pragma: no cover - import of the module itself
        raise PdfError("PDF import needs extra packages: pip install -r requirements-import.txt") from exc
    try:
        import pypdfium2  # noqa: F401
    except ImportError:
        raise PdfError("PDF import needs pypdfium2 and camelot-py: pip install -r requirements-import.txt") from None

    entries, doc_notes = [], []
    with PdfDoc(path, password=password, max_mb=MAX_PDF_BYTES / 1e6) as doc:
        count = min(doc.n_pages, MAX_PAGES)
        if doc.n_pages > MAX_PAGES:
            doc_notes.append(f"Only the first {MAX_PAGES} of {doc.n_pages} pages were read.")
        for index in range(count):
            if progress is not None:
                progress(index + 1, count)
            number = index + 1
            try:
                kind = doc.page_info(index).kind
                if kind in ("digital", "mixed"):
                    found, notes = digital.read_page(doc, index)
                    doc_notes += [f"Page {number}: {n}" for n in notes]
                    for f in found:
                        entries.append((number, _from_found(f)))
                    if kind == "mixed":
                        doc_notes.append(f"Page {number} also has pictures; tables inside pictures aren't read.")
                elif kind == "scanned":
                    frame = _read_scanned(doc, index)
                    if frame is not None:
                        entries.append((number, frame))
                    else:
                        doc_notes.append(f"Page {number} is a scan, and no table was found on it.")
            except PdfError:
                raise
            except Exception as exc:  # noqa: BLE001 - one bad page must not lose the others; it is reported
                doc_notes.append(f"Page {number} couldn't be read ({type(exc).__name__}: {exc}).")
    if not entries:
        raise PdfError("No tables were found in this PDF." + ("\n" + "\n".join(doc_notes) if doc_notes else ""))
    tables = _merge_repeated_headers(entries)
    for frame in tables:
        frame.attrs["document_notes"] = list(doc_notes)
    return tables


def _from_found(found) -> pd.DataFrame:
    table = found.table
    frame = table.to_frame()
    notes = [i.message for i in table.issues]
    if found.trust == "differ":
        notes.append("The ruling-line and text-position methods read this table differently; the ruling-line "
                     "version is shown. Compare it with the PDF.")
    elif found.trust == "one":
        notes.append(f"Only one method ({found.method_label}) found this table.")
    frame.attrs.update(method=f"text layer: {found.method_label}", notes=notes,
                       header_rows=table.header_rows)
    return frame


def _read_scanned(doc, index):
    """OCR of a scanned page drawn at SCAN_DPI; None when no table is on it. Missing OCR packages raise."""
    import numpy as np

    from .image_table_extractor import ImageTableError, _import_cv2, extract_from_gray
    try:
        cv2 = _import_cv2()
        import pytesseract
    except ImportError as exc:
        raise ImageTableError("Page is a scan: reading it needs OpenCV, pytesseract and Tesseract OCR "
                              "(pip install -r requirements-import.txt).") from exc
    image, _view = doc.render(index, dpi=SCAN_DPI)
    try:
        frame = extract_from_gray(np.asarray(image.convert("L")), cv2, pytesseract)
    except ImageTableError as exc:
        if "No table was found" in str(exc):
            return None
        raise
    frame.attrs["method"] = f"OCR: {frame.attrs.get('method', '')}"
    return frame


def _merge_repeated_headers(entries) -> list[pd.DataFrame]:
    """A table that continues on the next page with the same column names becomes one table."""
    result = []
    for page_number, frame in entries:
        last = result[-1] if result else None
        if (last is not None and page_number == last.attrs["pages"][-1] + 1
                and list(last.columns) == list(frame.columns)):
            combined = pd.concat([last, frame], ignore_index=True)
            combined.attrs.update(last.attrs)
            combined.attrs["pages"] = [*last.attrs["pages"], page_number]
            if "cell_confidence" in last.attrs or "cell_confidence" in frame.attrs:
                combined.attrs["cell_confidence"] = (_scores(last) + _scores(frame))
            result[-1] = combined
        else:
            frame.attrs["page_number"] = page_number
            frame.attrs["pages"] = [page_number]
            result.append(frame)
    return result


def _scores(frame):
    return frame.attrs.get("cell_confidence") or [[None] * frame.shape[1] for _ in range(len(frame))]
