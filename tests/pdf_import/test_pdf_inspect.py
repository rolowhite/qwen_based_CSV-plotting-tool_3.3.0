"""Opening PDFs (passwords, broken and empty files, size limit), page kinds, rendering, the page <-> pixel maths
checked against pdfium's own, and a 500-page file that must stay small in memory."""
import ctypes

import pytest

pdfium = pytest.importorskip("pypdfium2")
import pypdfium2.raw as pdfium_c  # noqa: E402

from plotstudio.core.pdf_import import inspect as pi  # noqa: E402


def test_errors_say_what_happened_and_what_to_do(pdfs, tmp_path):
    with pytest.raises(pi.PasswordNeeded, match="protected with a password"):
        pi.PdfDoc(pdfs["encrypted"])
    with pytest.raises(pi.WrongPassword, match="doesn't open"):
        pi.PdfDoc(pdfs["encrypted"], password="nope")
    with pi.PdfDoc(pdfs["encrypted"], password="secret") as doc:
        assert doc.n_pages == 1 and doc.encrypted and doc.may_copy_text
    with pytest.raises(pi.DamagedPdf, match="damaged"):
        pi.PdfDoc(pdfs["corrupt"])
    with pytest.raises(pi.DamagedPdf):
        pi.PdfDoc(pdfs["text_file"])                       # a text file called .pdf
    with pytest.raises(pi.EmptyPdf, match="0 bytes"):
        pi.PdfDoc(pdfs["empty"])
    with pytest.raises(pi.EmptyPdf, match="no pages"):
        pi.PdfDoc(pdfs["nopages"])
    with pytest.raises(pi.TooBig, match="MB"):
        pi.PdfDoc(pdfs["bordered"], max_mb=0.001)
    with pytest.raises(pi.PdfError, match="can't be opened"):
        pi.PdfDoc(tmp_path / "missing.pdf")


def test_a_pdf_that_forbids_copying_is_refused_unless_its_owner_password_is_given(pdfs):
    with pi.PdfDoc(pdfs["nocopy"]) as doc:                 # opens without a password, but copying is off
        assert not doc.may_copy_text
        with pytest.raises(pi.CopyingNotAllowed, match="owner password"):
            with doc.single_page(0):
                pass
    with pi.PdfDoc(pdfs["nocopy"], password="owner") as doc:
        assert doc.may_copy_text
        with doc.single_page(0) as (path, box):
            assert pdfium.PdfDocument(path).get_page(0) is not None     # the copy opens with no password


@pytest.mark.parametrize("name, kind", [("bordered", "digital"), ("report", "digital"), ("scanned", "scanned"),
                                        ("searchable", "scanned"), ("mixed", "mixed"), ("blank", "blank"),
                                        ("drawn", "scanned"), ("nested", "scanned")])
def test_each_kind_of_page_is_recognised(pdfs, name, kind):
    with pi.PdfDoc(pdfs[name]) as doc:
        info = doc.page_info(0)
        assert info.kind == kind, info.reason
        assert info.reason
    if name == "searchable":
        assert info.hidden_chars > 0 and "hidden text layer" in info.reason
    if name == "nested":                                   # a picture inside a form XObject, scaled into place
        assert info.image_cover > 0.95
    if name == "mixed":
        assert 0.15 < info.image_cover < 0.40


def test_kinds_page_by_page(pdfs):
    with pi.PdfDoc(pdfs["mixed_pages"]) as doc:
        assert [doc.page_info(i).kind for i in range(doc.n_pages)] == ["digital", "scanned"]


def test_the_classification_rules():
    assert pi.classify(500, 0, 0.0)[0] == "digital"
    assert pi.classify(8, 0, 0.0)[0] == "digital"             # a few words and nothing else: still a text layer
    assert pi.classify(500, 0, 0.3)[0] == "mixed"
    assert pi.classify(12, 0, 0.95)[0] == "scanned"           # a scan with a short printed stamp
    assert pi.classify(0, 300, 1.0)[0] == "scanned"
    assert pi.classify(0, 0, 0.0, paths=500)[0] == "scanned"
    assert pi.classify(0, 0, 0.0, paths=20)[0] == "blank"


def test_pages_render_within_the_pixel_cap_and_thumbnails_are_cached(pdfs):
    with pi.PdfDoc(pdfs["bordered"]) as doc:
        image, view = doc.render(0, dpi=72)
        assert abs(image.width - 595) <= 1 and abs(image.height - 842) <= 1 and view.scale == 1.0
        big, view = doc.render(0, dpi=2400, max_pixels=1_000_000)
        assert big.width * big.height <= 1_010_000 and view.scale < 2400 / 72
        thumb = doc.thumbnail(0)
        assert abs(thumb.height - pi.THUMB_HEIGHT) <= 1 and doc.thumbnail(0) is thumb
        with pytest.raises(ValueError):
            doc.render(0, turn=45)
        with pytest.raises(IndexError, match="no page 2"):
            doc.page_info(1)


def _pdfium_device(doc, index, size, turn, x, y):
    dx, dy = ctypes.c_int(), ctypes.c_int()
    with doc.page(index) as page:
        assert pdfium_c.FPDF_PageToDevice(page.raw, 0, 0, size[0], size[1], turn // 90, x, y, ctypes.byref(dx),
                                          ctypes.byref(dy))
    return dx.value, dy.value


@pytest.mark.parametrize("name", ["bordered", "rotated", "rot_lscape", "rot_sideways", "cropped", "landscape"])
@pytest.mark.parametrize("turn", [0, 90, 180, 270])
def test_page_to_pixel_maths_matches_pdfium(pdfs, name, turn):
    with pi.PdfDoc(pdfs[name]) as doc:
        image, view = doc.render(0, scale=1.5, turn=turn)
        x0, y0, x1, y1 = view.box
        points = [(x0 + 30, y0 + 40), (x1 - 20, y0 + 10), ((x0 + x1) / 2, (y0 + y1) / 2), (x1 - 5, y1 - 60)]
        for x, y in points:
            px, py = view.to_pixels(x, y)
            assert abs(px - _pdfium_device(doc, 0, image.size, turn, x, y)[0]) <= 1.0
            assert abs(py - _pdfium_device(doc, 0, image.size, turn, x, y)[1]) <= 1.0
            back = view.to_user(px, py)
            assert abs(back[0] - x) < 1e-6 and abs(back[1] - y) < 1e-6


def test_the_upright_turn_of_each_kind_of_rotated_page(pdfs):
    expected = {"bordered": 0, "rot_lscape": 0, "rotated": 270, "rot_sideways": 90}
    for name, turn in expected.items():
        with pi.PdfDoc(pdfs[name]) as doc:
            assert doc.upright_turn(0) == turn, name


def test_page_ranges():
    assert pi.parse_pages("1-3, 8, 10-", 12) == [0, 1, 2, 7, 9, 10, 11]
    assert pi.parse_pages("", 4) == pi.parse_pages("all", 4) == [0, 1, 2, 3]
    assert pi.parse_pages("-2; 4", 5) == [0, 1, 3]
    for bad, why in [("0", "outside"), ("5-2", "outside"), ("13", "outside"), ("x", "isn't a page")]:
        with pytest.raises(ValueError, match=why):
            pi.parse_pages(bad, 12)


def test_the_pdf_engine_cannot_run_javascript():
    """This app never sets up pdfium's form environment, and camelot's ruling-line method does (init_forms);
    what keeps a PDF's JavaScript from running is that this pdfium build has no JavaScript engine."""
    assert not pi.javascript_engine()


def test_500_pages_open_lazily_and_memory_stays_small(pdfs):
    psutil = pytest.importorskip("psutil")
    proc = psutil.Process()
    before = proc.memory_info().rss
    with pi.PdfDoc(pdfs["pages500"]) as doc:
        assert doc.n_pages == 500 and doc.looked_at() == []            # nothing is read until it is asked for
        kinds = {doc.page_info(i).kind for i in range(doc.n_pages)}
        for i in range(300):
            doc.thumbnail(i)
        assert kinds == {"digital"} and len(doc._thumbs) <= pi.THUMB_CACHE
        grown = proc.memory_info().rss - before
    assert grown < 250 * 1024 * 1024, f"memory grew by {grown / 2**20:.0f} MB"
