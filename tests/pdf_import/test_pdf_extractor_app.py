"""The app's PDF import (pdf_table_extractor) on PDFs with known tables: text pages, scans, passwords,
multi-page tables, and the 3.2.0 failures (missed second table, split headers, sideways pages, prose)."""
import shutil

import pandas as pd
import pytest

pytest.importorskip("pypdfium2")
pytest.importorskip("camelot")

import pdf_fixtures as fx  # noqa: E402

from plotstudio import pdf_table_extractor as px  # noqa: E402


def grid(frame):
    return [list(frame.columns)] + frame.astype(object).values.tolist()


@pytest.mark.parametrize("name", ["bordered", "borderless", "cropped", "placed"])
def test_text_tables_come_out_exactly_as_printed(pdfs, name):
    (table,) = px.extract_tables(pdfs[name])
    assert grid(table) == fx.TRUTH and table.attrs["pages"] == [1]
    assert table.attrs["method"].startswith("text layer")


def test_every_table_on_a_page_is_found_and_prose_is_not_a_table(pdfs):
    assert [grid(t) for t in px.extract_tables(pdfs["both"])] == [fx.TRUTH, fx.TRUTH]
    assert [grid(t) for t in px.extract_tables(pdfs["report"])] == [fx.TRUTH, fx.STAFF]
    with pytest.raises(px.PDFTableError, match="No tables"):
        px.extract_tables(pdfs["mixed"])                        # paragraphs and a picture, no table


@pytest.mark.parametrize("name", ["rotated", "rot_lscape", "rot_sideways", "landscape"])
def test_turned_pages_come_out_upright(pdfs, name):
    (table,) = px.extract_tables(pdfs[name])
    assert grid(table) == fx.WIDE


def test_merged_headings_and_wrapped_cells(pdfs):
    (table,) = px.extract_tables(pdfs["merged"])
    assert list(table.columns) == fx.MERGED_COLUMNS
    assert table["Notes"].tolist()[1] == "new store opened in the second half"
    assert any("read this table differently" in n for n in table.attrs["notes"])


def test_a_password_is_asked_for(pdfs):
    with pytest.raises(px.PasswordNeeded):
        px.extract_tables(pdfs["encrypted"])
    with pytest.raises(px.WrongPassword):
        px.extract_tables(pdfs["encrypted"], password="nope")
    assert grid(px.extract_tables(pdfs["encrypted"], password="secret")[0]) == fx.TRUTH


def test_broken_and_empty_files_say_what_is_wrong(pdfs):
    for name, match in (("corrupt", "damaged"), ("nopages", "no pages"), ("empty", "0 bytes"),
                        ("blank", "No tables")):
        with pytest.raises(px.PDFTableError, match=match):
            px.extract_tables(pdfs[name])


def test_a_sideways_table_on_an_upright_page_is_flagged(pdfs):
    (table,) = px.extract_tables(pdfs["minority"])
    assert any("sideways" in n for n in table.attrs["notes"])


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract OCR executable is not installed")
def test_a_scanned_page_is_read_by_ocr(pdfs):
    pytest.importorskip("cv2")
    pytest.importorskip("pytesseract")
    (table,) = px.extract_tables(pdfs["scanned"])
    assert table.attrs["method"] == "OCR: grid lines"
    assert list(table.columns) == fx.HEADER and len(table) == len(fx.ROWS)
    assert table["Region"].tolist() == [r[0] for r in fx.ROWS]


def test_a_failing_page_is_reported_not_hidden(pdfs, monkeypatch):
    from plotstudio.core.pdf_import import digital

    monkeypatch.setattr(digital, "read_page", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(px.PDFTableError, match="Page 1 couldn't be read"):
        px.extract_tables(pdfs["bordered"])


def test_tables_join_only_across_consecutive_pages():
    a = pd.DataFrame({"Name": ["Ada"], "Value": ["1"]})
    b = pd.DataFrame({"Name": ["Lin"], "Value": ["2"]})
    joined = px._merge_repeated_headers([(1, a.copy()), (2, b.copy())])
    assert len(joined) == 1 and joined[0].attrs["pages"] == [1, 2] and joined[0]["Name"].tolist() == ["Ada", "Lin"]
    assert len(px._merge_repeated_headers([(1, a.copy()), (3, b.copy())])) == 2      # a gap: two tables
    assert len(px._merge_repeated_headers([(1, a.copy()), (1, b.copy())])) == 2      # same page: two tables
