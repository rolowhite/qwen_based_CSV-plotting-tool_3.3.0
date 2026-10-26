"""The real window: the Notebook page loads a library, finds a typed problem, steps through exercises, keeps a
history, logs a wrong match and writes the solution page that the browser opens."""
import json
import tkinter as tk

import pytest

import nb_fixtures as fx

pytestmark = pytest.mark.gui


@pytest.fixture
def app(tmp_path, monkeypatch):
    try:
        tk.Tk().destroy()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    import plotstudio.settings as settings
    monkeypatch.setattr(settings, "PATH", tmp_path / ".csv_plot_studio.json")
    lib = fx.write_sample(tmp_path / "lib")
    settings.PATH.write_text(json.dumps({"notebook_library": [str(lib)]}), encoding="utf-8")
    from plotstudio.app import App
    window = App()
    errors = []
    window.report_callback_exception = lambda *a: errors.append(a)
    window.errors = errors
    yield window
    window.on_close()


def _wait(app, condition, timeout=15.0):
    import time
    end = time.time() + timeout
    while not condition():
        if time.time() > end:
            raise AssertionError("timed out")
        app.update()
        time.sleep(0.02)


def test_typed_problem_is_found_shown_logged_and_opened(app, tmp_path, monkeypatch):
    from tkinter import simpledialog
    import webbrowser
    from plotstudio import notebook_page

    app.show("notebook")
    nb = app.notebook
    _wait(app, lambda: nb.index is not None)
    assert "Sample 1st · 6 exercises" in nb.lib_button.cget("text")

    nb.text.insert("1.0", "A box holds 7 red and 5 blue marbles. Two are drawn without replacement. "
                          "Find the probability that both are red.")
    nb._highlight()
    assert len(nb.text.tag_ranges("num")) == 4          # 7 and 5, start and end each
    nb.find()
    assert nb.result.status == "match" and nb.current.number == "1.1"
    assert "verified" in nb.badge.cget("text") and nb.badge.cget("style") == "Ok.TLabel"
    assert app.cfg["notebook_history"][0]["exercise"] == "sample:1.1"

    nb._step(1)
    assert nb.current.number == "1.2" and "caution" in nb.badge.cget("text")

    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **k: "1.3")
    nb.wrong_match()
    entry = json.loads(notebook_page.feedback_path().read_text(encoding="utf-8").splitlines()[-1])
    assert entry["shown"] == "sample:1.2" and entry["correct"] == "sample:1.3"
    assert entry["candidates"][0] == {"exercise": "sample:1.1", "score": nb.result.best.score}
    assert nb.current.number == "1.3"

    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url) or True)
    nb.open_solution()
    _wait(app, lambda: opened)
    assert opened[0].startswith("file:") and opened[0].endswith("/open.html")
    assert not app.errors


def test_ties_ask_and_search_and_history_fill_the_list(app):
    app.show("notebook")
    nb = app.notebook
    _wait(app, lambda: nb.index is not None)
    nb.text.insert("1.0", "The weights of six parcels are given in kg. Find the sample mean.")
    nb.find()
    assert nb.result.status == "choose" and nb.current is None
    assert len(nb.tree.get_children()) == 3
    nb.tree.selection_set("1")
    app.update()
    assert nb.current is not None

    nb.search.set_value("lamp")
    nb._run_search()
    assert nb.listed[0].number == "1.3"
    nb.list_mode.set("history")
    nb._mode_changed()
    assert nb.tree.item("h0", "values")[0] == "picked?"
    assert not app.errors
