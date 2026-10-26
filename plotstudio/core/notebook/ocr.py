"""Problem text from a picture or a PDF page.

A picture is straightened and cleaned the way the table import does it (image_table_extractor), then read
by Tesseract as running text. A PDF page with a text layer gives its text directly (only the marked area,
when one is given); a scanned page is drawn and read like a picture. What was read is only a draft: the
user sees it in an editable box and fixes it before the lookup runs again.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

Box = Tuple[float, float, float, float]      # left, top, right, bottom in image pixels
PDF_DPI = 150                                # the page picture shown in the Notebook
OCR_DPI = 300                                # a scanned page is drawn again this sharp for Tesseract
MAX_IMAGE_BYTES = 50 * 1024 * 1024


class OcrUnavailable(RuntimeError):
    """OpenCV, pytesseract or the Tesseract program is missing."""


@dataclass
class Reading:
    text: str
    method: str                       # "tesseract" | "pdf text"
    confidence: Optional[float] = None    # Tesseract's mean word confidence, 0-100
    notes: List[str] = field(default_factory=list)


def _tools():
    from ... import image_table_extractor as ite
    from ...bootstrap import _add_tesseract_to_path

    try:
        cv2 = ite._import_cv2()
        import pytesseract
    except ImportError as exc:
        raise OcrUnavailable("Reading pictures needs OpenCV and pytesseract: "
                             "pip install -r requirements-import.txt") from exc
    if not _add_tesseract_to_path():
        raise OcrUnavailable("Reading pictures needs the Tesseract OCR program (Windows: winget install "
                             "UB-Mannheim.TesseractOCR, Linux: sudo apt install tesseract-ocr). You can still "
                             "type or paste the problem text.")
    ite._sanitize_ld_library_path()
    return ite, cv2, pytesseract


def read_image(image, box: Optional[Box] = None) -> Reading:
    """Text of a PIL image (or of the `box` part of it)."""
    import numpy as np

    ite, cv2, pytesseract = _tools()
    if box is not None:
        image = image.crop(tuple(int(round(v)) for v in box))
    gray = np.asarray(image.convert("L"))
    notes = []
    gray, warped = ite._straighten_page(gray, cv2)
    if warped:
        notes.append("The photo was straightened (page edges found, perspective corrected).")
    prepared = ite._preprocess(gray, cv2)
    data = pytesseract.image_to_data(prepared, config="--psm 6", output_type=pytesseract.Output.DICT)
    lines, confidences = {}, []
    for word, conf, block, par, line in zip(data["text"], data["conf"], data["block_num"], data["par_num"],
                                            data["line_num"]):
        if word.strip():
            lines.setdefault((block, par, line), []).append(word)
            if float(conf) >= 0:
                confidences.append(float(conf))
    text = "\n".join(" ".join(ws) for _, ws in sorted(lines.items()))
    confidence = sum(confidences) / len(confidences) if confidences else None
    if not text.strip():
        notes.append("No text was found. Try a sharper picture, or crop to the problem.")
    elif confidence is not None and confidence < 70:
        notes.append(f"Tesseract was unsure (mean confidence {confidence:.0f}). Check the numbers.")
    notes.append("Tesseract reads plain text: fractions, symbols and formulas often come out wrong.")
    return Reading(text, "tesseract", confidence, notes)


def read_image_file(path, box: Optional[Box] = None) -> Reading:
    from PIL import Image

    path = Path(path)
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("This image is too large. The maximum supported size is 50 MB.")
    with Image.open(path) as image:
        image.load()
        return read_image(image, box)


def read_pdf_page(doc, index: int, box: Optional[Box] = None, view=None) -> Reading:
    """Text of page `index` of an open PdfDoc. `box` is in the pixels of the picture drawn with `view`."""
    info = doc.page_info(index)
    if info.kind in ("digital", "mixed") and doc.may_copy_text:
        with doc.page(index) as page:
            textpage = page.get_textpage()
            try:
                if box is not None and view is not None:
                    x0, y0, x1, y1 = view.box_to_user(box)
                    text = textpage.get_text_bounded(left=x0, bottom=y0, right=x1, top=y1)
                else:
                    text = textpage.get_text_range()
            finally:
                textpage.close()
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if text:
            return Reading(text, "pdf text", None, [f"Read from the text layer of page {index + 1}."])
    image, ocr_view = doc.render(index, dpi=OCR_DPI)
    if box is not None and view is not None:
        k = ocr_view.scale / view.scale
        box = tuple(v * k for v in box)
    reading = read_image(image, box)
    reading.notes.insert(0, f"Page {index + 1} has no usable text layer, so it was read with OCR.")
    return reading
