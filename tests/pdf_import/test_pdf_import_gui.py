"""The real window: import a PDF table, edit a cell in the review dialog, save it as a CSV next to the PDF
with its .source.json note, and land in the workspace with that file loaded."""
import json
import time
import tkinter as tk

import pytest

pytest.importorskip("pypdfium2")
pytest.importorskip("camelot")
pytestmark = pytest.mark.gui

import pdf_fixtures as fx  # noqa: E402


@pytest.fixture
def app(tmp_path, monkeypatch):
    try:
        tk.Tk().destroy()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    monkeypatch.setenv("HOME", str(tmp_path))
    import plotstudio.settings as settings
    monkeypatch.setattr(settings, "PATH", tmp_path / ".csv_plot_studio.json")
    from plotstudio.app import App
    window = App()
    errors = []
    window.report_callback_exception = lambda *a: errors.append(a)
    window.errors = errors
    yield window
    window.on_close()


def _dialog(app):
    return next((w for w in app.winfo_children() if isinstance(w, tk.Toplevel)), None) or next(
        (w for w in app.loader.winfo_children() if isinstance(w, tk.Toplevel)), None)


def test_pdf_table_is_reviewed_edited_saved_and_opened(app, pdfs, tmp_path, monkeypatch):
    from tkinter import filedialog

    src = tmp_path / "report.pdf"
    src.write_bytes(pdfs["report"].read_bytes())
    target = tmp_path / "report_table1.csv"
    seen = {}
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: seen.update(kw) or str(target))

    def act():
        win = _dialog(app)
        if win is None:
            app.after(100, act)
            return
        grid_entries = []

        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, tk.Entry):
                    grid_entries.append(c)
                walk(c)
        walk(win)
        cell = grid_entries[4 + 1]                            # row 1 ("North"), column 2 (Units)
        cell.delete(0, "end")
        cell.insert(0, "1,205")
        button = next(b for b in _buttons(win) if b.cget("text") == "Save as CSV and open")
        seen["tables"] = sum(1 for _ in grid_entries)
        button.invoke()

    app.after(200, act)
    app.loader.load_pdf(src)
    end = time.time() + 60
    while time.time() < end and app.dataset is None:
        app.update()
        time.sleep(0.02)
    assert not app.errors, app.errors
    assert app.dataset is not None and app.dataset.path == target
    assert seen["initialdir"] == str(tmp_path) and seen["initialfile"] == "report_table1.csv"
    note = json.loads((tmp_path / "report_table1.source.json").read_text(encoding="utf-8"))
    assert note["pages"] == [1] and note["method"].startswith("text layer")
    assert note["edits"] == [{"row": 1, "column": "Units", "old": "1,204", "new": "1,205"}]
    assert list(app.dataset.df.columns) == fx.HEADER


def _buttons(widget):
    from tkinter import ttk
    out = []
    for c in widget.winfo_children():
        if isinstance(c, ttk.Button):
            out.append(c)
        out += _buttons(c)
    return out
