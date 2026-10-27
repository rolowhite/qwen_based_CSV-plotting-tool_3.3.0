"""The real window: a pasted picture is read (a fake Ollama), the answer streams into the right pane with its math
drawn, a stored and an unknown problem look the same, Ollama missing shows how to set it up, Stop and New chat.

Replaces the 3.3 tests of the problem-text box, the match list, the history and Wrong match (all removed)."""
import json
import tkinter as tk

import pytest

import nb_fixtures as fx
from fake_ollama import FakeOllama

pytestmark = pytest.mark.gui

MARBLES = ("A box holds 7 red and 5 blue marbles. Two marbles are drawn without replacement. "
           "Find the probability that both are red.")
VISION = {"vl": ["completion", "vision"]}


def _reply(*problems):
    return json.dumps({"problems": [{"label": l, "markdown": m} for l, m in problems], "unreadable": []})


@pytest.fixture
def app(tmp_path, monkeypatch, request):
    try:
        tk.Tk().destroy()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    import plotstudio.settings as settings
    from plotstudio import notebook_page
    from plotstudio.core.notebook import session
    monkeypatch.setattr(settings, "PATH", tmp_path / ".csv_plot_studio.json")
    monkeypatch.setattr(session, "PACE", 0.0)
    if "built_in" not in request.keywords:      # the small made-up library, unless the test is about the real one
        monkeypatch.setattr(notebook_page, "LIBRARY_FILES", (fx.write_sample(tmp_path / "lib"),))
    settings.PATH.write_text(json.dumps({"notebook_ollama_url": "http://127.0.0.1:9"}), encoding="utf-8")
    from plotstudio.app import App
    window = App()
    errors = []
    window.report_callback_exception = lambda *a: errors.append(a)
    window.errors = errors
    yield window
    window.on_close()


def _wait(app, condition, timeout=20.0):
    import time
    end = time.time() + timeout
    while not condition():
        if time.time() > end:
            raise AssertionError("timed out")
        app.update()
        time.sleep(0.02)


def _ready(app, url):
    app.cfg["notebook_ollama_url"] = url
    app.show("notebook")
    nb = app.notebook
    _wait(app, lambda: nb.index is not None)
    return nb


def _picture():
    from PIL import Image
    return Image.new("RGB", (900, 300), "white")


def _images(nb):
    return [name for kind, name, _ in nb.answers.text.dump("1.0", "end", image=True) if kind == "image"]


def test_a_pasted_picture_is_read_and_answered_in_the_right_pane(app, monkeypatch, tmp_path):
    from PIL import ImageGrab
    from plotstudio import notebook_page
    with FakeOllama(VISION, replies=[_reply(("1.1", MARBLES))]) as fake:
        nb = _ready(app, fake.url)
        statuses = []
        set_status = nb.set_status
        monkeypatch.setattr(nb, "set_status", lambda text: statuses.append(text) or set_status(text))
        monkeypatch.setattr(ImageGrab, "grabclipboard", lambda: _picture())
        nb.paste_image()
        assert nb.stop_btn.winfo_manager() == "pack" and nb.send_btn.instate(["disabled"])
        _wait(app, lambda: nb._turn is None)
    assert "Reading the problem…" in statuses and "Solving…" in statuses
    shown = nb.answers.plain_text()
    assert "Problem 1.1." in shown and "7 red and 5 blue" in shown and "Solution." in shown
    assert _images(nb), "the formulas are drawn as pictures"
    assert nb._thumbs and nb.stop_btn.winfo_manager() == ""
    entry = json.loads(notebook_page.history_path().read_text(encoding="utf-8").splitlines()[-1])
    assert entry["answers"][0]["from"] == "library:sample:1.1" and entry["source"] == "Screenshot"
    assert not app.errors


def test_a_stored_and_an_unknown_problem_look_the_same(app):
    nb = _ready(app, "http://127.0.0.1:9")
    nb.submit(nb_session().Source("Typed", text=MARBLES))
    _wait(app, lambda: nb._turn is None)
    nb.submit(nb_session().Source("Typed", text="A die is rolled 4 times. Find the chance of two sixes."))
    _wait(app, lambda: nb._turn is None)
    shown = nb.answers.plain_text()
    assert nb_session().NOT_YET in shown and "Solution." in shown
    for word in ("library", "score", "match", "verified", "checker"):
        assert word not in shown.lower()
    assert len(nb.answers._windows) == 2            # Copy / Open in browser under each answer, nothing else
    assert all(isinstance(w, tk.Frame) for w in nb.answers._windows)
    assert len(nb.turns.body.winfo_children()) == 3      # the empty hint (hidden) and two bubbles
    nb.new_chat()
    assert nb.answers.items == [] and nb.empty.winfo_manager() == "pack"
    assert not app.errors


def test_no_ollama_shows_how_to_set_it_up_and_typing_still_works(app):
    nb = _ready(app, "http://127.0.0.1:9")
    nb.submit(nb_session().Source("Screenshot", _picture()), _picture())
    _wait(app, lambda: nb._turn is None)
    assert any(item[0] == "setup" for item in nb.answers.items)
    card = nb.answers._windows[-1]
    texts = [w.cget("text") for w in card.winfo_children()]
    assert "Reading pictures needs Ollama" in texts and any("ollama pull" in t for t in texts)
    nb.entry.set_value(MARBLES)
    nb.send_text()
    _wait(app, lambda: nb._turn is None)
    assert "Solution." in nb.answers.plain_text()
    assert not app.errors


@pytest.mark.built_in
def test_the_walpole_solutions_come_with_the_app(app):
    from plotstudio.core.notebook import library
    nb = _ready(app, "http://127.0.0.1:9")                    # empty settings: nothing was ever chosen
    assert len(nb.library.exercises) == 1207 and {e.book for e in nb.library.exercises} == {"walpole"}
    problem = library.load([library.BUILT_IN]).get("3.14").problem_md.replace("**Problem:**", "").strip()
    nb.submit(nb_session().Source("Typed", text=problem))
    _wait(app, lambda: nb._turn is None)
    assert "Solution." in nb.answers.plain_text() and "0.7981" in nb.answers.plain_text()
    assert not hasattr(nb, "lib_button")                     # no library menu, no folder to pick
    assert not app.errors


def test_missing_built_in_solutions_are_said_plainly(app, tmp_path, monkeypatch):
    from plotstudio import notebook_page
    monkeypatch.setattr(notebook_page, "LIBRARY_FILES", (tmp_path / "gone.md",))
    app.show("notebook")
    nb = app.notebook
    _wait(app, lambda: not nb._loading and nb.answers.items)
    assert nb.library is None and "built-in solutions couldn't be read" in nb.answers.plain_text()
    assert nb.submit(nb_session().Source("Typed", text=MARBLES)) is False and nb._turn is None
    assert not app.errors


def test_a_formula_mathtext_cant_draw_shows_its_source(app):
    nb = _ready(app, "http://127.0.0.1:9")
    nb.answers.add_turn(1)
    nb.answers.begin()
    nb.answers.end("Here $\\xrightarrow{x}$ fails and $x^2$ works.")
    shown = nb.answers.plain_text()
    assert "$\\xrightarrow{x}$" in shown and "x^2" not in shown and len(_images(nb)) == 1
    app.toggle_theme()                              # drawn again in the other ink: still one picture, no error
    assert len(_images(nb)) == 1 and "$\\xrightarrow{x}$" in nb.answers.plain_text()
    assert not app.errors


def test_stop_ends_a_slow_reading(app):
    with FakeOllama(VISION, replies=[{"text": _reply(("", MARBLES)), "delay": 0.4}]) as fake:
        nb = _ready(app, fake.url)
        nb.submit(nb_session().Source("Screenshot", _picture()), _picture())
        _wait(app, lambda: fake.requests)
        nb.stop()
        _wait(app, lambda: nb._turn is None, timeout=5)
    assert "Stopped." in nb.answers.plain_text()
    assert not app.errors


def nb_session():
    from plotstudio.core.notebook import session
    return session
