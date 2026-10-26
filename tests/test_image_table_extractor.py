"""Image table import and shared CSV conversion tests."""
from __future__ import annotations

import csv
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from plotstudio import image_table_extractor as extractor
from plotstudio.image_table_extractor import ImageTableError, extract_table
from plotstudio.table_import import edits_between, save_table, sidecar_path, suggested_name


def _high_contrast_image(path):
    pytest.importorskip("cv2")
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(image)
    for x in (30, 450, 870):
        draw.line((x, 30, x, 470), fill="black", width=3)
    for y in (30, 170, 310, 470):
        draw.line((30, y, 870, y), fill="black", width=3)
    image.save(path)


def _fake_tesseract(monkeypatch):
    fake = SimpleNamespace(Output=SimpleNamespace(DICT="dict"))
    monkeypatch.setitem(sys.modules, "pytesseract", fake)


def _ocr_font(size):
    from PIL import ImageFont

    font_path = Path(__file__).resolve().parents[1] / "plotstudio" / "assets" / "fonts" / "IBMPlexSans-SemiBold.ttf"
    return ImageFont.truetype(str(font_path), size)


def _render_bordered_table(path, *, rotation=0):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1376, 768), "white")
    draw = ImageDraw.Draw(image)
    xs = [32, 360, 688, 1016, 1344]
    ys = [34, 174, 314, 454, 594, 734]
    for x in xs:
        draw.line((x, ys[0], x, ys[-1]), fill="black", width=5)
    for y in ys:
        draw.line((xs[0], y, xs[-1], y), fill="black", width=5)
    rows = [
        ["Month", "Revenue", "Cost", "Profit"],
        ["January", "1,200", "700", "500"],
        ["February", "1,500", "850", "650"],
        ["March", "1,800", "900", "900"],
        ["April", "2,100", "1,200", "900"],
    ]
    font = _ocr_font(38)
    for row_i, row in enumerate(rows):
        for col_i, text in enumerate(row):
            box = draw.textbbox((0, 0), text, font=font)
            x = (xs[col_i] + xs[col_i + 1] - (box[2] - box[0])) / 2
            y = (ys[row_i] + ys[row_i + 1] - (box[3] - box[1])) / 2 - box[1]
            draw.text((x, y), text, font=font, fill="black")
    if rotation:
        image = image.rotate(rotation, resample=Image.Resampling.BICUBIC, fillcolor="white")
    image.save(path)


def _render_borderless_table(path):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1376, 600), "white")
    draw = ImageDraw.Draw(image)
    font = _ocr_font(36)
    rows = [
        ["City", "TempC", "Humidity", "WindKph"],
        ["Oslo", "8", "61", "13"],
        ["Cairo", "27", "33", "18"],
        ["Tokyo", "19", "57", "11"],
        ["Lima", "23", "72", "9"],
    ]
    xs, ys = [45, 380, 710, 1040], [55, 160, 265, 370, 475]
    for y, row in zip(ys, rows):
        for x, text in zip(xs, row):
            draw.text((x, y), text, font=font, fill="black")
    image.save(path)


def test_clean_bordered_image_extracts_table(tmp_path, monkeypatch):
    path = tmp_path / "bordered.png"
    _high_contrast_image(path)
    _fake_tesseract(monkeypatch)
    monkeypatch.setattr(extractor, "_extract_grid", lambda *_: (
        [["Name", "Amount"], ["Ada", "1,250.50"]], [[98, 97], [96, 96]]))

    frame = extract_table(path)

    assert frame.to_dict("records") == [{"Name": "Ada", "Amount": "1,250.50"}]
    assert frame.attrs["cell_confidence"] == [[96, 96]]


def test_borderless_image_uses_alignment_fallback(tmp_path, monkeypatch):
    path = tmp_path / "borderless.jpg"
    _high_contrast_image(path)
    _fake_tesseract(monkeypatch)
    monkeypatch.setattr(extractor, "_extract_grid", lambda *_: None)
    monkeypatch.setattr(extractor, "_extract_borderless", lambda *_: (
        [["Product", "Qty"], ["Notebook", "3"]], [[90, 89], [84, 93]]))

    frame = extract_table(path)

    assert frame.to_dict("records") == [{"Product": "Notebook", "Qty": "3"}]
    assert frame.attrs["cell_confidence"] == [[84, 93]]


def test_low_quality_phone_screenshot_keeps_cell_confidence(tmp_path, monkeypatch):
    path = tmp_path / "phone.webp"
    _high_contrast_image(path)
    _fake_tesseract(monkeypatch)
    monkeypatch.setattr(extractor, "_extract_grid", lambda *_: (
        [["Date", "Total"], ["2024-01-02", "18.40"]], [[58, 62], [41, 55]]))

    frame = extract_table(path)

    assert frame.attrs["cell_confidence"] == [[41, 55]]
    assert frame.attrs["low_confidence_threshold"] == 65


def test_image_without_table_reports_clear_error(tmp_path, monkeypatch):
    path = tmp_path / "no-table.png"
    _high_contrast_image(path)
    _fake_tesseract(monkeypatch)
    monkeypatch.setattr(extractor, "_extract_grid", lambda *_: None)
    monkeypatch.setattr(extractor, "_extract_borderless", lambda *_: ([], []))

    with pytest.raises(ImageTableError, match="No table was found"):
        extract_table(path)


def test_opencv_import_restores_linux_loader_path(monkeypatch):
    import importlib

    monkeypatch.setenv("LD_LIBRARY_PATH", "/system/lib")

    def fake_import(_name):
        os.environ["LD_LIBRARY_PATH"] = "/opencv/wheel/lib64"
        return object()

    monkeypatch.setattr(importlib, "import_module", fake_import)
    extractor._import_cv2()
    assert os.environ["LD_LIBRARY_PATH"] == "/system/lib"


def test_grid_detection_does_not_fragment_large_table_cells(tmp_path, monkeypatch):
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    path = tmp_path / "large_grid.png"
    _render_bordered_table(path)
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    prepared = extractor._preprocess(gray, cv2)
    monkeypatch.setattr(extractor, "_ocr_cell", lambda *_: ("cell", 99.0))

    result = extractor._extract_grid(prepared, cv2, object())

    assert result is not None
    rows, _scores, _spans = result
    assert len(rows) == 5
    assert all(len(row) == 4 for row in rows)


def test_preprocess_normalizes_opencv45_angle_convention(monkeypatch):
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    gray = np.full((240, 480), 255, dtype=np.uint8)
    cv2.rectangle(gray, (25, 25), (455, 215), 0, 4)
    old_min_area_rect = cv2.minAreaRect
    old_rotation = cv2.getRotationMatrix2D
    angles = []

    monkeypatch.setattr(cv2, "minAreaRect", lambda _points: ((0, 0), (100, 50), 87.5))

    def remember_rotation(center, angle, scale):
        angles.append(angle)
        return old_rotation(center, angle, scale)

    monkeypatch.setattr(cv2, "getRotationMatrix2D", remember_rotation)
    extractor._preprocess(gray, cv2)

    assert angles == [-2.5]
    monkeypatch.setattr(cv2, "minAreaRect", old_min_area_rect)


def test_borderless_columns_align_using_cell_midpoints():
    import numpy as np

    texts, lefts, widths, tops, line_nums = [], [], [], [], []
    rows = [
        [("City", 45, 70), ("TempC", 380, 100), ("Humidity", 710, 145), ("WindKph", 1040, 150)],
        [("Oslo", 45, 70), ("8", 420, 20), ("61", 760, 45), ("13", 1095, 40)],
        [("Cairo", 45, 80), ("27", 410, 40), ("33", 760, 45), ("18", 1095, 40)],
        [("Tokyo", 45, 75), ("19", 410, 40), ("57", 760, 45), ("11", 1095, 40)],
    ]
    for line_number, row in enumerate(rows, start=1):
        for text, left, width in row:
            texts.append(text)
            lefts.append(left)
            widths.append(width)
            tops.append(line_number * 100)
            line_nums.append(line_number)
    data = {
        "text": texts, "conf": ["95"] * len(texts), "left": lefts, "width": widths,
        "top": tops, "height": [40] * len(texts), "block_num": [1] * len(texts),
        "par_num": [1] * len(texts), "line_num": line_nums,
    }
    fake = SimpleNamespace(Output=SimpleNamespace(DICT="dict"),
                           image_to_data=lambda *_args, **_kwargs: data)

    extracted, _scores = extractor._extract_borderless(np.zeros((600, 1376), dtype=np.uint8), None, fake)
    frame = extractor._rows_to_frame(extracted, _scores)

    assert frame.shape == (3, 4)
    assert list(frame.columns) == ["City", "TempC", "Humidity", "WindKph"]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract OCR executable is not installed")
def test_real_ocr_high_res_bordered_table_with_large_digits(tmp_path):
    pytest.importorskip("cv2")
    path = tmp_path / "large_digits.png"
    _render_bordered_table(path)

    frame = extract_table(path)

    assert frame.shape == (4, 4)
    assert list(frame.columns) == ["Month", "Revenue", "Cost", "Profit"]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract OCR executable is not installed")
@pytest.mark.xfail(strict=False, reason="Tesseract 5 reads 'TempC' as 'Tempc' in this font (also in 3.2.0); "
                   "borderless tables are marked review_all so the user checks every cell")
def test_real_ocr_borderless_table_preserves_distinct_headers(tmp_path):
    pytest.importorskip("cv2")
    path = tmp_path / "borderless.png"
    _render_borderless_table(path)

    frame = extract_table(path)

    assert frame.shape == (4, 4)
    assert list(frame.columns) == ["City", "TempC", "Humidity", "WindKph"]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract OCR executable is not installed")
def test_deskew_handles_opencv45_angle_convention(tmp_path):
    pytest.importorskip("cv2")
    path = tmp_path / "rotated.png"
    _render_bordered_table(path, rotation=2.5)

    frame = extract_table(path)

    assert frame.shape == (4, 4)
    assert list(frame.columns) == ["Month", "Revenue", "Cost", "Profit"]


def test_saved_table_is_utf8_with_a_note_on_where_it_came_from(tmp_path):
    import json

    before = pd.DataFrame({"City": ["Zürich", "Bern"], "Value": ["1,250.50", "7"]})
    after = before.copy()
    after.iat[1, 1] = "8"
    path = save_table(after, tmp_path / "cities.csv", {"source": "scan.png", "edits": edits_between(before, after)})
    with path.open(encoding="utf-8", newline="") as stream:
        assert list(csv.reader(stream)) == [["City", "Value"], ["Zürich", "1,250.50"], ["Bern", "8"]]
    note = json.loads(sidecar_path(path).read_text(encoding="utf-8"))
    assert note["source"] == "scan.png" and note["rows"] == 2
    assert note["edits"] == [{"row": 2, "column": "Value", "old": "7", "new": "8"}]
    assert suggested_name("report.pdf", 2) == "report_table2.csv" and suggested_name("a.png") == "a_table.csv"


def test_nothing_is_filled_in_and_left_out_parts_are_noted():
    rows = [["Group", "Item", "Value"], ["A", "x", "1"], ["", "y", "2"], ["", "", ""], ["B", "z", ""]]
    scores = [[90] * 3 for _ in rows]
    frame = extractor._rows_to_frame(rows, scores)
    assert frame.values.tolist() == [["A", "x", "1"], ["", "y", "2"], ["B", "z", ""]]   # no carried-down "A"
    assert frame.attrs["notes"] == ["1 empty row(s) left out."]


def test_a_merged_heading_becomes_parent_child_names():
    rows = [["Region", "Revenue", "", "Notes"], ["", "2023", "2024", ""], ["North", "1,000", "1,100", "ok"]]
    scores = [[90, 90, None, 90], [90] * 4, [90] * 4]
    frame = extractor._rows_to_frame(rows, scores, {(0, 2)})
    assert list(frame.columns) == ["Region", "Revenue_2023", "Revenue_2024", "Notes"]
    assert frame.values.tolist() == [["North", "1,000", "1,100", "ok"]]


def test_close_borderless_columns_keep_every_value():
    """3.2.0 merged 'Region Units' into one column and then overwrote Region with Units in every row."""
    import numpy as np

    rows = [[("Region", 40, 110), ("Units", 175, 85), ("Revenue", 420, 140)],
            [("North", 40, 95), ("1,204", 180, 80), ("45,310.50", 400, 160)],
            [("South", 40, 95), ("987", 205, 55), ("38,002.10", 400, 160)]]
    data = {k: [] for k in ("text", "conf", "left", "width", "top", "height", "block_num", "par_num", "line_num")}
    for n, row in enumerate(rows, start=1):
        for text, left, width in row:
            for k, v in (("text", text), ("conf", "92"), ("left", left), ("width", width), ("top", n * 60),
                         ("height", 30), ("block_num", 1), ("par_num", 1), ("line_num", n)):
                data[k].append(v)
    fake = SimpleNamespace(Output=SimpleNamespace(DICT="dict"), image_to_data=lambda *_a, **_k: data)
    got, _ = extractor._extract_borderless(np.zeros((300, 700), dtype=np.uint8), None, fake)
    assert got == [["Region", "Units", "Revenue"], ["North", "1,204", "45,310.50"], ["South", "987", "38,002.10"]]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract OCR executable is not installed")
def test_a_phone_photo_of_the_page_is_straightened_and_read(tmp_path):
    pytest.importorskip("cv2")
    from PIL import Image

    flat = tmp_path / "flat.png"
    _render_bordered_table(flat)
    page = Image.open(flat)
    photo = Image.new("RGB", (1700, 1100), (70, 72, 80))                 # a dark desk around the sheet
    photo.paste(page, (160, 160))
    w, h = photo.size
    # look at the sheet a little from the side: the far edge is narrower
    coeffs = _perspective_coeffs([(0, 0), (w, 0), (w, h), (0, h)], [(60, 30), (w - 40, 0), (w, h), (0, h - 20)])
    photo = photo.transform((w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    path = tmp_path / "photo.jpg"
    photo.save(path, quality=90)

    frame = extract_table(path)

    assert list(frame.columns) == ["Month", "Revenue", "Cost", "Profit"] and frame.shape == (4, 4)
    assert any("straightened" in note for note in frame.attrs["notes"])


def _perspective_coeffs(dst, src):
    import numpy as np

    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(rows, float), np.array([c for p in src for c in p], float)).tolist()
