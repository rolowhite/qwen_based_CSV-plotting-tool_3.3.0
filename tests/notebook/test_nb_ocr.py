"""Problem text from a picture (Tesseract) and from a PDF page (its text layer, or a marked part of it)."""
import pytest

from plotstudio.core.notebook import ocr

PROBLEM = ["3.13 The number of imperfections per 10 meters", "of fabric has the distribution 0.41 0.37 0.16."]


def _picture():
    from PIL import Image, ImageDraw, ImageFont
    from plotstudio.fonts import FONT_DIR
    img = Image.new("RGB", (1300, 260), "white")
    font = ImageFont.truetype(str(FONT_DIR / "IBMPlexSans-Regular.ttf"), 34)
    ImageDraw.Draw(img).multiline_text((24, 30), "\n".join(PROBLEM), fill="black", font=font, spacing=80)
    return img


def test_a_picture_is_read_as_text():
    try:
        reading = ocr.read_image(_picture())
    except ocr.OcrUnavailable as exc:
        pytest.skip(str(exc))
    assert reading.method == "tesseract"
    assert "imperfections" in reading.text and "0.41 0.37 0.16" in reading.text
    assert reading.confidence is not None and reading.confidence > 70


def test_a_marked_part_of_a_picture_is_read_alone():
    try:
        reading = ocr.read_image(_picture(), box=(0, 110, 1300, 260))
    except ocr.OcrUnavailable as exc:
        pytest.skip(str(exc))
    assert "0.41" in reading.text and "imperfections" not in reading.text


def test_a_text_pdf_gives_its_text_and_a_marked_area(tmp_path):
    pytest.importorskip("pypdfium2")
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    from plotstudio.core.pdf_import.inspect import PdfDoc

    path = tmp_path / "problems.pdf"
    c = canvas.Canvas(str(path), pagesize=(600, 400))
    c.setFont("Helvetica", 14)
    c.drawString(40, 340, "4.1 First problem: a fair coin is tossed 3 times.")
    c.drawString(40, 120, "4.2 Second problem: the mean of 2, 4 and 9.")
    c.save()
    with PdfDoc(path) as doc:
        whole = ocr.read_pdf_page(doc, 0)
        assert whole.method == "pdf text" and "First problem" in whole.text and "Second problem" in whole.text
        _image, view = doc.render(0, dpi=ocr.PDF_DPI)
        k = view.scale
        part = ocr.read_pdf_page(doc, 0, box=(0, 250 * k, 600 * k, 400 * k), view=view)   # the lower half
        assert "Second problem" in part.text and "First problem" not in part.text
