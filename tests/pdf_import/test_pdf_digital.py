"""Tables read from the text layer: exact text, two methods compared, merged headers, wrapped cells, rotated pages,
cell boxes that hold exactly their cell's text, passwords, and a marked area with column dividers."""
from pathlib import Path

import pytest

pytest.importorskip("pypdfium2")
pytest.importorskip("camelot")

import pdf_fixtures as fx  # noqa: E402

from plotstudio.core.pdf_import import digital  # noqa: E402
from plotstudio.core.pdf_import import inspect as pi  # noqa: E402


def read(path, password=None, page=0):
    with pi.PdfDoc(path, password=password) as doc:
        return digital.read_page(doc, page)


def test_a_bordered_and_a_borderless_table_import_with_identical_text(pdfs):
    (bordered,), _ = read(pdfs["bordered"])
    (borderless,), _ = read(pdfs["borderless"])
    assert bordered.table.grid() == borderless.table.grid() == fx.TRUTH     # every character, as printed
    assert bordered.trust == "agree" and set(bordered.versions) == {"lattice", "network"}
    assert borderless.trust == "one" and borderless.chosen == "network"     # no lines: one method finds it
    for f in (bordered, borderless):
        t = f.table
        assert {c.source for c in t.cells} == {"pdf_text"} and t.header_rows == 1 and t.source_page == 1
        assert t.column_names() == fx.HEADER
        assert t.to_frame().values.tolist() == fx.ROWS
        assert not [i for i in t.issues if i.severity == "error"]


def test_text_that_looks_like_numbers_is_never_changed(pdfs):
    (found,), _ = read(pdfs["bordered"])
    change = [row[3] for row in found.table.grid()[1:]]
    assert change == ["(1,250)", "4.5%", "−320", "12.3*", "—"]     # brackets, %, Unicode minus, *, dash


def test_two_tables_on_a_page_come_in_reading_order(pdfs):
    found, _ = read(pdfs["both"])
    assert [f.number for f in found] == [1, 2]
    assert [f.trust for f in found] == ["agree", "one"]
    assert found[0].table.bbox[1] > found[1].table.bbox[1]                  # the first is higher on the page
    assert all(f.table.grid() == fx.TRUTH for f in found)


def test_prose_on_a_report_page_is_not_taken_for_a_table(pdfs):
    found, _ = read(pdfs["report"])
    assert [f.table.grid() for f in found] == [fx.TRUTH, fx.STAFF]


def test_merged_headers_become_parent_child_names_and_wrapped_cells_one_line(pdfs):
    (found,), _ = read(pdfs["merged"])
    assert found.trust == "differ" and found.chosen == "lattice"           # the methods split it differently
    t = found.table
    assert t.grid() == fx.MERGED and t.header_rows == 2
    assert t.column_names() == fx.MERGED_COLUMNS
    assert t.to_frame()["Notes"].tolist()[1] == "new store opened in the second half"
    other = found.versions["network"]
    assert other.grid() != t.grid()
    found.choose("network")
    assert found.table is other and found.label.startswith("The two methods differ")
    with pytest.raises(KeyError):
        found.choose("stream")


@pytest.mark.parametrize("name", ["landscape", "rotated", "rot_lscape", "rot_sideways"])
def test_rotated_pages_come_out_upright(pdfs, name):
    (found,), _ = read(pdfs[name])
    for method, table in found.versions.items():
        assert table.grid() == fx.WIDE, method                              # not sideways, not transposed
        assert not [i for i in table.issues if i.severity == "error"]
    sideways = any("printed sideways" in n for n in found.table.notes)
    assert sideways == (name in ("rotated", "rot_sideways"))


def test_a_sideways_table_on_an_upright_page_is_flagged(pdfs):
    found, _ = read(pdfs["minority"])
    assert found, "the small table should still be found"
    assert all(any(i.severity == "error" and "sideways" in i.message for i in f.table.issues) for f in found)


@pytest.mark.parametrize("name", ["bordered", "rotated", "rot_lscape", "rot_sideways", "cropped", "merged"])
def test_each_cell_box_holds_exactly_that_cells_text(pdfs, name):
    """What lights up on the page for a cell is where its text is: pdfium's text inside the box is the text."""
    with pi.PdfDoc(pdfs[name]) as doc:
        (found,), _ = digital.read_page(doc, 0)
        table = found.versions["lattice"]
        with doc.page(0) as page:
            textpage = page.get_textpage()
            try:
                for cell in table.cells:
                    if not cell.text:
                        continue
                    x0, y0, x1, y1 = cell.pdf_bbox
                    inside = " ".join(textpage.get_text_bounded(x0, y0, x1, y1).split())
                    assert inside == cell.text, (cell.row, cell.col)
            finally:
                textpage.close()
        x0, y0, x1, y1 = table.bbox
        assert all(x0 - 1 <= c.pdf_bbox[0] and c.pdf_bbox[2] <= x1 + 1 for c in table.cells)


def test_a_password_protected_pdf_is_read_and_its_unprotected_copy_removed(pdfs):
    with pi.PdfDoc(pdfs["encrypted"], password="secret") as doc:
        (found,), _ = digital.read_page(doc, 0)
        assert found.table.grid() == fx.TRUTH and found.trust == "agree"
        folder = Path(doc._tmpdir)
        assert folder.is_dir() and not list(folder.iterdir())          # each page copy is gone after use
    assert not folder.exists()                                         # and the folder when the PDF closes


def _placed_view(doc, turn=0):
    image, view = doc.render(0, scale=2.0, turn=turn)
    lay = fx.LAYOUT["placed"]
    rect_user = (lay["left"] - 4, lay["bottom"] - 4, lay["right"] + 4, lay["top"] + 4)
    return view, view.box_to_pixels(rect_user), lay


def test_a_marked_area_with_column_dividers(pdfs):
    with pi.PdfDoc(pdfs["placed"]) as doc:
        view, rect, lay = _placed_view(doc)
        middle = (lay["bottom"] + lay["top"]) / 2
        dividers = [view.to_pixels(x, middle)[0] for x in lay["dividers"]]
        found = digital.read_area(doc, 0, view, rect, dividers)
        assert found.trust == "marked" and found.chosen == "stream" and found.label == "Marked by hand"
        assert found.table.grid() == fx.TRUTH
        assert any("3 column dividers" in n for n in found.table.notes)
        auto = digital.read_area(doc, 0, view, rect)                   # no dividers: camelot guesses the columns
        words = [[v for v in row if v] for row in auto.table.grid()]
        assert words == fx.TRUTH                       # every value, whole and in its row; the columns may differ
        assert any("camelot found the columns" in n for n in auto.table.notes)


def test_a_marked_area_on_a_page_shown_upright(pdfs):
    with pi.PdfDoc(pdfs["rot_sideways"]) as doc:
        (found,), _ = digital.read_page(doc, 0)
        turn = doc.upright_turn(0)
        image, view = doc.render(0, scale=1.5, turn=turn)
        rect = view.box_to_pixels(found.table.bbox)
        rect = (rect[0] - 6, rect[1] - 6, rect[2] + 6, rect[3] + 6)
        cells = [found.table.cell(0, c).pdf_bbox for c in range(found.table.n_cols)]
        dividers = [view.box_to_pixels(b)[0] for b in cells[1:]]       # the left edge of every column but one
        marked = digital.read_area(doc, 0, view, rect, dividers)
        assert marked.table.grid() == fx.WIDE
        sideways = doc.render(0, scale=1.5, turn=0)[1]                  # dividers on the page shown sideways
        with pytest.raises(pi.PdfError, match="Turn the page"):
            digital.read_area(doc, 0, sideways, sideways.box_to_pixels(found.table.bbox), [10.0])


def test_an_empty_marked_area_says_so(pdfs):
    with pi.PdfDoc(pdfs["placed"]) as doc:
        image, view = doc.render(0)
        with pytest.raises(pi.PdfError, match="no text inside"):
            digital.read_area(doc, 0, view, (5, 5, 60, 40))


def test_a_method_that_fails_is_reported_and_the_other_still_reads(pdfs, monkeypatch):
    real = digital._camelot

    def broken(path, info, flavor, **options):
        if flavor == "lattice":
            raise RuntimeError("boom")
        return real(path, info, flavor, **options)

    monkeypatch.setattr(digital, "_camelot", broken)
    found, notes = read(pdfs["bordered"])
    assert [f.chosen for f in found] == ["network"] and found[0].table.grid() == fx.TRUTH
    assert any("ruling lines method couldn't read page 1 (RuntimeError: boom)" in n for n in notes)


def test_header_guess_without_lines():
    assert digital.guess_header_rows([["a", "b"], ["1", "2"]]) == 1
    assert digital.guess_header_rows([["", "Revenue", "", ""], ["Region", "2023", "2024", "Notes"],
                                      ["North", "1", "2", "x"]]) == 2
    assert digital.guess_header_rows([["Region", "Revenue", "", "Notes"], ["", "2023", "2024", ""],
                                      ["North", "1", "2", "x"]]) == 2
    assert digital.guess_header_rows([["", "2023", "2024"], ["North", "1", "2"]]) == 1   # an empty corner
    assert digital.guess_header_rows([["only"]]) == 1
