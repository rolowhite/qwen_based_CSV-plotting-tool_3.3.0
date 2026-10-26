"""Extract a table from an image with OpenCV layout detection and Tesseract OCR.

Nothing is invented: a cell keeps exactly what OCR read (an empty cell stays empty), and what the reader is
unsure about is said in the frame's attrs, so the review dialog can show it:
  cell_confidence      Tesseract's confidence per body cell (0-100; None for the empty part of a merged cell)
  header_confidence    the same for the header
  method               "grid lines" (cells from the drawn lines) or "word positions" (no lines: columns guessed)
  review_all           True when the columns were guessed: every cell should be checked, whatever its confidence
  notes                what was done that the user should know (a photo straightened, empty columns left out)
"""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import importlib
import os
from pathlib import Path

import pandas as pd

MAX_IMAGE_BYTES = 50 * 1024 * 1024
LOW_CONFIDENCE = 65.0
OCR_WORKERS = max(1, min(8, (os.cpu_count() or 2)))   # each cell is one Tesseract process: run several at once


class ImageTableError(ValueError):
    """A readable image-table import error."""


def _import_cv2():
    """Load OpenCV without leaking its bundled OpenMP path to OCR subprocesses."""
    old_ld_path = os.environ.get("LD_LIBRARY_PATH")
    try:
        return importlib.import_module("cv2")
    finally:
        if old_ld_path is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = old_ld_path


def _sanitize_ld_library_path():
    """Remove OpenCV's bundled libgomp directory before starting Tesseract."""
    value = os.environ.get("LD_LIBRARY_PATH")
    if not value:
        return
    paths = [part for part in value.split(os.pathsep)
             if "cv2" not in part.lower() and "opencv" not in part.lower()]
    if paths:
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(paths)
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)


def extract_table(image_path) -> pd.DataFrame:
    """Preprocess an image and extract one table as a DataFrame of text (see the module docstring for attrs)."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ImageTableError("This image is too large. The maximum supported size is 50 MB.")
    try:
        cv2 = _import_cv2()
    except ImportError as exc:
        raise ImageTableError("Image import needs OpenCV: pip install -r requirements-import.txt") from exc
    try:
        import pytesseract
    except ImportError as exc:
        raise ImageTableError("Image import needs pytesseract and the Tesseract OCR program: "
                              "pip install -r requirements-import.txt, then install Tesseract.") from exc

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ImageTableError("This image could not be opened. Use a PNG, JPG, or WEBP image.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if blur_score < 3.0:
        raise ImageTableError("This image is too blurry to read. Try a sharper or higher-resolution image.")
    return extract_from_gray(gray, cv2, pytesseract)


def extract_from_gray(gray, cv2, pytesseract) -> pd.DataFrame:
    """The table in a grayscale picture (also used for scanned PDF pages)."""
    notes = []
    gray, warped = _straighten_page(gray, cv2)
    if warped:
        notes.append("The photo was straightened: the page edges were found and the perspective corrected.")
    prepared = _preprocess(gray, cv2)
    _sanitize_ld_library_path()

    grid = _extract_grid(prepared, cv2, pytesseract)
    if grid and len(grid[0]) > 1:
        rows, confidence = grid[0], grid[1]
        spans = grid[2] if len(grid) > 2 else set()
        method = "grid lines"
    else:
        rows, confidence = _extract_borderless(prepared, cv2, pytesseract)
        spans, method = set(), "word positions"
    if not rows or len(rows) < 2 or max(map(len, rows)) < 2:
        raise ImageTableError("No table was found in this image. Use an image that clearly shows rows and columns.")

    frame = _rows_to_frame(rows, confidence, spans)
    if _mean_confidence(frame) < 15:
        raise ImageTableError("This image is too blurry or low-quality for reliable OCR. Try a clearer image.")
    frame.attrs["method"] = method
    frame.attrs["review_all"] = method == "word positions"
    if method == "word positions":
        notes.append("No ruling lines were found, so the columns were worked out from where the words sit. "
                     "Check every cell, not only the amber ones.")
    frame.attrs["notes"] = notes + frame.attrs.get("notes", [])
    return frame


def _straighten_page(gray, cv2):
    """A phone photo of a sheet: find the sheet's four corners and correct the perspective. Returns (image,
    changed). Pictures without a clear page edge (screenshots, crops) are returned as they are."""
    import numpy as np

    h, w = gray.shape[:2]
    k = 800 / max(h, w) if max(h, w) > 800 else 1.0
    small = cv2.resize(gray, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k != 1.0 else gray
    blurred = cv2.GaussianBlur(small, (5, 5), 0)
    mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]       # paper = bright
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    found = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = found[0] if len(found) == 2 else found[1]                                 # OpenCV 4/5 vs 3
    if not contours:
        return gray, False
    best = max(contours, key=cv2.contourArea)
    area = small.shape[0] * small.shape[1]
    if not 0.2 * area <= cv2.contourArea(best) <= 0.95 * area:
        return gray, False
    peri = cv2.arcLength(best, True)
    for eps in (0.02, 0.03, 0.05):
        quad = cv2.approxPolyDP(best, eps * peri, True)
        if len(quad) == 4 and cv2.isContourConvex(quad):
            break
    else:
        return gray, False
    pts = quad.reshape(4, 2).astype(np.float32) / k
    s, d = pts.sum(axis=1), np.diff(pts, axis=1).ravel()
    tl, tr, br, bl = pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]
    width = int(round(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))))
    height = int(round(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))))
    if width < 50 or height < 50:
        return gray, False
    target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype=np.float32), target)
    return cv2.warpPerspective(gray, matrix, (width, height), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE), True


def _preprocess(gray, cv2):
    """Upscale small text, denoise, deskew and improve local contrast."""
    height, width = gray.shape[:2]
    scale = min(3.0, max(1.0, 1200 / max(height, width)))
    if scale > 1.05:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if min(gray.shape[:2]) >= 5:
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    points = cv2.findNonZero(threshold)
    if points is not None and len(points) > 50:
        angle = float(cv2.minAreaRect(points)[-1])
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle
        if 0.5 < abs(angle) < 12:
            h, w = gray.shape[:2]
            matrix = cv2.getRotationMatrix2D((w / 2, h / 2), -angle, 1.0)
            gray = cv2.warpAffine(
                gray, matrix, (w, h), flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_CONSTANT, borderValue=255,
            )
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _ocr(image, pytesseract, *, psm=6):
    return pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT,
                                     config=f"--psm {psm}")


def _line_centers(mask, axis, coverage, min_gap):
    scores = (mask > 0).sum(axis=axis)
    indexes = [i for i, score in enumerate(scores) if score >= coverage]
    groups = []
    for index in indexes:
        if not groups or index - groups[-1][-1] > min_gap:
            groups.append([index])
        else:
            groups[-1].append(index)
    return [round(sum(group) / len(group)) for group in groups]


def _extract_grid(image, cv2, pytesseract):
    """(rows, scores, spans) from a table with drawn lines. A cell merged over several columns keeps its text in
    the first of them; the others are "" and listed in `spans` as (row, column), so columns never shift."""
    height, width = image.shape[:2]
    # adaptiveThreshold requires an odd block size greater than one. Keep it
    # safely below small image dimensions so thumbnail-sized images fail cleanly.
    block_size = min(31, min(height, width) if min(height, width) % 2 else min(height, width) - 1)
    if block_size < 3:
        return None
    binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, block_size, 12)
    h_len, v_len = max(50, width // 12), max(50, height // 8)
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                  cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1)))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len)))
    # lines at least half as long as the longest one: a small table on a whole scanned page still counts
    longest = int((horizontal > 0).sum(axis=1).max()) if horizontal.size else 0
    ys = _line_centers(horizontal, axis=1, coverage=max(h_len, longest * 0.5), min_gap=12)
    if len(ys) < 3:
        return None
    table_h = max(1, ys[-1] - ys[0])
    xs = _line_centers(vertical[ys[0]:ys[-1] + 1, :], axis=0,
                       coverage=table_h * 0.55, min_gap=15)
    if len(xs) < 3:
        return None

    layout, crops = [], []                       # per row: [(first column, span)], and every crop to read
    for y0, y1 in zip(ys, ys[1:]):
        if y1 - y0 < 8:
            continue
        groups, start = [], 0
        for boundary in range(1, len(xs) - 1):
            x = xs[boundary]
            segment = vertical[max(0, y0 + 2):min(height, y1 - 2), max(0, x - 2):x + 3]
            # Missing dividers identify horizontally merged cells.
            if segment.size and (segment > 0).mean() >= 0.30:
                groups.append((start, boundary))
                start = boundary
        groups.append((start, len(xs) - 1))
        layout.append(groups)
        for a, b in groups:
            x0, x1 = xs[a], xs[b]
            inset_x, inset_y = max(4, (x1 - x0) // 25), max(4, (y1 - y0) // 15)
            crops.append(image[max(0, y0 + inset_y):min(height, y1 - inset_y),
                               max(0, x0 + inset_x):min(width, x1 - inset_x)])
    with ThreadPoolExecutor(OCR_WORKERS) as pool:
        read = iter(list(pool.map(lambda crop: _ocr_cell(crop, pytesseract, cv2), crops)))

    n_cols = len(xs) - 1
    rows, scores, spans = [], [], set()
    for groups in layout:
        texts, confs, cont = [""] * n_cols, [0.0] * n_cols, []
        for a, b in groups:
            text, score = next(read)
            texts[a], confs[a] = text, score
            for c in range(a + 1, b):
                confs[c] = None
                cont.append(c)
        if sum(bool(value) for value in texts) > 1:
            spans.update((len(rows), c) for c in cont)
            rows.append(texts)
            scores.append(confs)
    return (rows, scores, spans) if len(rows) >= 2 else None


def _ocr_cell(crop, pytesseract, cv2):
    if crop.size == 0:
        return "", 0.0
    gray = crop if crop.ndim == 2 else cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    import numpy as np

    ink = (gray < float(np.median(gray)) - 35).astype("uint8")       # darker than this cell's paper
    if not ink.any():
        return "", 100.0
    # no mark bigger than paper grain: an empty cell (OCR would read the grain as letters); a dash stays
    areas = cv2.connectedComponentsWithStats(ink, connectivity=8)[2][1:, cv2.CC_STAT_AREA]
    if areas.max() < max(12, ink.size * 0.0005):
        return "", 100.0
    text, confidence = _read_ocr_cell(crop, pytesseract)
    if confidence < LOW_CONFIDENCE:
        # Tightly trim surrounding whitespace/noise and add a clean white margin;
        # Tesseract often reads isolated digits better with this presentation.
        gray = crop if crop.ndim == 2 else cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        points = cv2.findNonZero(ink)
        if points is not None:
            x, y, w, h = cv2.boundingRect(points)
            tight = gray[y:y + h, x:x + w]
            pad = max(8, round(max(h, w) * 0.12))
            padded = cv2.copyMakeBorder(tight, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
            retry_text, retry_confidence = _read_ocr_cell(padded, pytesseract)
            if retry_confidence > confidence:
                return retry_text, retry_confidence
    return text, confidence


def _read_ocr_cell(crop, pytesseract):
    data = _ocr(crop, pytesseract, psm=6)
    words, scores = [], []
    for text, confidence in zip(data.get("text", []), data.get("conf", [])):
        text = str(text).strip()
        try:
            score = float(confidence)
        except (ValueError, TypeError):
            continue
        if text and score >= 0:
            words.append(text)
            scores.append(score)
    return " ".join(words), sum(scores) / len(scores) if scores else 0.0


def _extract_borderless(image, cv2, pytesseract):
    """A table without lines: one OCR pass, then columns where no word on any line sits (the gaps in the
    words' horizontal spread). Every word lands in exactly one column, so nothing is overwritten."""
    data = _ocr(image, pytesseract, psm=6)
    lines = defaultdict(list)
    for i, text in enumerate(data.get("text", [])):
        text = str(text).strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][i])
        except (ValueError, TypeError, KeyError):
            continue
        if confidence < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines[key].append((int(data["left"][i]), int(data["top"][i]),
                           int(data.get("width", [0])[i]), int(data.get("height", [0])[i]),
                           text, confidence))
    words = [w for line in lines.values() for w in line]
    if len(lines) < 2 or not words:
        return [], []
    heights = sorted(w[3] for w in words)
    gap = max(6, heights[len(heights) // 2] * 0.6)      # wider than a space between words, narrower than a column gap
    columns = []
    for left, right in sorted((w[0], w[0] + w[2]) for w in words):
        if columns and left <= columns[-1][1] + gap:
            columns[-1][1] = max(columns[-1][1], right)
        else:
            columns.append([left, right])
    if len(columns) < 2:
        return [], []
    rows, scores = [], []
    for line in sorted(lines.values(), key=lambda ws: min(w[1] for w in ws)):
        cells = [[] for _ in columns]
        for w in sorted(line):
            centre = w[0] + w[2] / 2
            index = min(range(len(columns)), key=lambda j: 0 if columns[j][0] <= centre <= columns[j][1]
                        else min(abs(centre - columns[j][0]), abs(centre - columns[j][1])))
            cells[index].append(w)
        values = [" ".join(w[4] for w in cell) for cell in cells]
        if sum(bool(value) for value in values) > 1:
            rows.append(values)
            scores.append([sum(w[5] for w in cell) / len(cell) if cell else 0.0 for cell in cells])
    return (rows, scores) if len(rows) >= 2 else ([], [])


def _header_names(rows, spans):
    """Column names and how many rows they used: a heading merged over several columns (spans in row 0, with
    sub-headings under it) gives 'Parent_Child'; otherwise the first row."""
    first = list(rows[0])
    if not any(r == 0 for r, _ in spans) or len(rows) < 3:
        return first, 1
    parent, names = "", []
    for c, (top, sub) in enumerate(zip(first, rows[1])):
        if (0, c) not in spans:
            parent = top
        names.append("_".join(p for p in (parent if (0, c) in spans or top else "", sub) if p) or top)
    return names, 2


def _rows_to_frame(rows, scores, spans=frozenset()):
    width = max(map(len, rows))
    rows = [[str(value).replace("\n", " ").strip() for value in row] + [""] * (width - len(row))
            for row in rows]
    scores = [list(row) + [0.0] * (width - len(row)) for row in scores]
    names, used = _header_names(rows, spans)
    headers = _unique_headers(names)
    header_scores = scores[0] if scores else [0.0] * width
    body, body_scores = rows[used:], scores[used:]
    keep_rows = [i for i, row in enumerate(body) if any(row)]
    keep_cols = [i for i in range(width) if any(row[i] for row in body)]
    frame = pd.DataFrame([[body[r][c] for c in keep_cols] for r in keep_rows],
                         columns=[headers[c] for c in keep_cols])
    notes = []
    if len(keep_rows) < len(body):
        notes.append(f"{len(body) - len(keep_rows)} empty row(s) left out.")
    if len(keep_cols) < width:
        notes.append("Empty column(s) left out: " + ", ".join(headers[c] for c in range(width)
                                                              if c not in keep_cols) + ".")
    frame.attrs["cell_confidence"] = [[body_scores[r][c] for c in keep_cols] for r in keep_rows]
    frame.attrs["header_confidence"] = [header_scores[c] for c in keep_cols]
    frame.attrs["low_confidence_threshold"] = LOW_CONFIDENCE
    frame.attrs["notes"] = notes
    return frame


def _unique_headers(values):
    result, seen = [], {}
    for index, value in enumerate(values, start=1):
        name = str(value).strip() or f"Column {index}"
        seen[name] = seen.get(name, 0) + 1
        result.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return result


def _mean_confidence(frame):
    values = [score for row in frame.attrs.get("cell_confidence", []) for score in row if score]
    return sum(values) / len(values) if values else 0.0
