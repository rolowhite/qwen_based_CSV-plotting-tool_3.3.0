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
MODELS_VT = {"vl": ["completion", "vision", "tools"]}


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


def test_a_stored_and_a_solved_problem_look_the_same(app):
    # an unknown problem used to get "I can't solve this one yet"; now the local model solves it
    solves = [{"text": "**Given:** 4 rolls. Binomial:", "calls": ["comb(4, 2) * (1/6)**2 * (5/6)**2"]},
              "So $P=25/216$.\n\n**Answer:** $0.1157407407$"]
    with FakeOllama({"vl": ["completion", "vision", "tools"]}, replies=solves) as fake:
        nb = _ready(app, fake.url)
        nb.submit(nb_session().Source("Typed", text=MARBLES))
        _wait(app, lambda: nb._turn is None)
        nb.submit(nb_session().Source("Typed", text="A die is rolled 4 times. Find the chance of two sixes."))
        _wait(app, lambda: nb._turn is None)
    shown = nb.answers.plain_text()
    assert shown.count("Solution.") == 2 and "Answer:" in shown and _images(nb)
    import re
    assert not re.search(r"\b(library|score|match|verified|checker|qwen|gemini|vl)\b", shown.lower())
    assert len(nb.answers._windows) == 2            # Copy / Open in browser under each answer, nothing else
    assert all(isinstance(w, tk.Frame) for w in nb.answers._windows)
    assert len(nb.turns.body.winfo_children()) == 3      # the empty hint (hidden) and two bubbles
    nb.new_chat()
    assert nb.answers.items == [] and nb.empty.winfo_manager() == "pack"
    assert not app.errors


def test_the_picture_reader_sets_itself_up_with_progress(app):
    from plotstudio.core.notebook import ollama
    with FakeOllama({"other": ["completion"]}) as fake:            # Ollama runs, the reading model is missing
        fake.pull_delay = 0.4
        nb = _ready(app, fake.url)
        nb.start_reader_setup()
        _wait(app, lambda: nb.setup_box.winfo_manager() == "pack" and float(nb.setup_bar.cget("value")) > 0)
        assert "Downloading the reading model" in nb.setup_label.cget("text")
        assert nb.progress.winfo_manager() == ""                     # its own bar, not the header's busy bar
        assert nb.submit(nb_session().Source("Screenshot", _picture()), _picture()) is False
        assert "still being set up" in nb.note_label.cget("text")
        assert nb.submit(nb_session().Source("Typed", text=MARBLES)) is True      # typing works meanwhile
        _wait(app, lambda: nb._setup_state == "done" and nb._turn is None)
        assert fake.pulls == [ollama.READER_MODEL] and nb.setup_box.winfo_manager() == ""
        assert "Solution." in nb.answers.plain_text()
    assert not app.errors


def test_a_failed_setup_says_why_and_can_be_tried_again(app):
    nb = _ready(app, "http://127.0.0.1:9")
    from plotstudio.core.notebook import setup
    original = setup.ensure
    setup.ensure = lambda url, progress, chat: (_ for _ in ()).throw(setup.ollama.OllamaError("no internet"))
    try:
        nb.start_reader_setup()
        _wait(app, lambda: nb._setup_state == "failed")
    finally:
        setup.ensure = original
    assert "couldn't be set up: no internet" in nb.setup_label.cget("text")
    assert nb.setup_retry.winfo_manager() == "pack" and nb.setup_bar.winfo_manager() == ""
    assert not app.errors


def _menu_labels(nb):
    menu = nb.model_menu
    return [menu.entrycget(i, "label") for i in range(menu.index("end") + 1) if menu.type(i) != "separator"]


def test_the_gemini_key_is_checked_saved_shown_and_removed(app):
    from fake_gemini import FakeGemini
    with FakeGemini(key="good-key") as gem:
        app.cfg["notebook_gemini_url"] = gem.url
        nb = _ready(app, "http://127.0.0.1:9")
        assert "Gemini: add a free key for better solutions…" in _menu_labels(nb)
        win = nb.gemini_dialog()
        texts = " ".join(w.cget("text") for w in win.winfo_children()[0].winfo_children()[0].winfo_children()
                         if isinstance(w, tk.ttk.Label))
        assert "18 or older" in texts and "EU" in texts and "text and picture are sent" in texts
        win.entry.insert(0, "bad-key")
        nb._check_key(win)
        _wait(app, lambda: "didn't accept the key" in win.message.cget("text"))
        assert "notebook_gemini_key" not in app.cfg or not app.cfg["notebook_gemini_key"]
        win.entry.delete(0, "end")
        win.entry.insert(0, "good-key")
        nb._check_key(win)
        _wait(app, lambda: not win.winfo_exists())
    assert app.cfg["notebook_gemini_key"] == "good-key" and app.cfg["notebook_gemini_model"] == "gemini-3.8-flash"
    assert "Gemini: on · gemini-3.8-flash" in _menu_labels(nb) and nb.model_button.cget("text").endswith("+ Gemini")
    nb.remove_gemini_key()
    assert not app.cfg.get("notebook_gemini_key") and "Gemini: add a free key for better solutions…" in _menu_labels(nb)
    assert not app.errors


def test_the_add_a_key_tip_shows_once_after_a_live_solve(app):
    from plotstudio import notebook_page
    solves = [{"calls": ["comb(4, 2) * (1/6)**2 * (5/6)**2"]}, "**Answer:** $0.1157407407$"] * 2
    with FakeOllama({"vl": ["completion", "vision", "tools"]}, replies=solves) as fake:
        nb = _ready(app, fake.url)
        nb.submit(nb_session().Source("Typed", text="A die is rolled 4 times. Find the chance of two sixes."))
        _wait(app, lambda: nb._turn is None)
        assert nb.note_label.cget("text") == notebook_page.GEMINI_TIP
        nb.submit(nb_session().Source("Typed", text="A die is rolled 4 times. Find the chance of two fives."))
        _wait(app, lambda: nb._turn is None)
        assert nb.note_label.cget("text") == ""                  # cleared by the next turn, not shown again
    assert not app.errors


def test_geminis_problem_shows_in_the_model_menu(app):
    from fake_gemini import FakeGemini
    solves = [{"calls": ["comb(4, 2) * (1/6)**2 * (5/6)**2"]}, "**Answer:** $0.1157407407$"]
    with FakeOllama({"vl": ["completion", "vision", "tools"]}, replies=solves) as fake, \
            FakeGemini(out_of_quota={"gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"}) as gem:
        app.cfg.update(notebook_gemini_url=gem.url, notebook_gemini_key="test-key")
        nb = _ready(app, fake.url)
        nb.submit(nb_session().Source("Typed", text="A die is rolled 4 times. Find the chance of two sixes."))
        _wait(app, lambda: nb._turn is None)
    assert "Answer:" in nb.answers.plain_text()                  # qwen's solution, quietly
    assert any(label.startswith("Gemini: Gemini's free quota for") for label in _menu_labels(nb))
    assert not app.errors


def test_no_ollama_shows_how_to_set_it_up_and_typing_still_works(app):
    nb = _ready(app, "http://127.0.0.1:9")
    nb.submit(nb_session().Source("Screenshot", _picture()), _picture())
    _wait(app, lambda: nb._turn is None)
    assert any(item[0] == "setup" for item in nb.answers.items)
    card = nb.answers._windows[-1]
    texts = [w.cget("text") for w in card.winfo_children()]
    assert "The picture reader isn't ready" in texts and any("ollama pull" in t for t in texts)
    nb.entry.set_value(MARBLES)
    nb.send_text()
    _wait(app, lambda: nb._turn is None)
    assert "Solution." in nb.answers.plain_text()
    assert not app.errors


@pytest.mark.built_in
def test_the_built_in_solutions_come_with_the_app(app):
    from plotstudio.core.notebook import library
    nb = _ready(app, "http://127.0.0.1:9")                    # empty settings: nothing was ever chosen
    assert len(nb.library.exercises) == 1207 + 327 and {e.book for e in nb.library.exercises} == {"walpole", "lind"}
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


def test_a_wrong_fast_answer_is_corrected_later_without_blocking_the_next_problem(app):
    coin = "A fair coin is tossed 10 times. Find the probability of exactly 3 heads."
    wrong = [{"text": "**Given:** n=10.", "calls": ["comb(10, 4) / 2**10"]}, "**Answer:** 0.205078125"]
    right = [{"text": "**Given:** n=10.", "calls": ["comb(10, 3) / 2**10"]}, "**Answer:** 0.1171875"]
    with FakeOllama({"vl": ["completion", "vision", "tools"]}, replies=wrong + right) as fake:
        nb = _ready(app, fake.url)
        nb.submit(nb_session().Source("Typed", text=coin))
        _wait(app, lambda: nb._turn is None)
        assert "0.205078125" in nb.answers.plain_text()                      # shown first, fast
        _wait(app, lambda: "Correction for the problem" in nb.answers.plain_text(), 30)
    text = nb.answers.plain_text()
    assert "sorry" in text and "0.1171875" in text and nb._checks == [] and nb._checker is None
    assert not app.errors


def _buttons(widget):
    out = []
    for child in widget.winfo_children():
        out += [child] if child.winfo_class() == "TButton" else _buttons(child)
    return out


def test_a_picture_with_several_problems_offers_a_button_for_each_and_solves_the_chosen_one(app):
    coin = "A fair coin is tossed 10 times. Find the probability of exactly 3 heads."
    reply = _reply(("1.1", MARBLES), ("", coin))
    with FakeOllama(MODELS_VT, replies=[reply, reply]) as fake:
        nb = _ready(app, fake.url)
        nb.submit(nb_session().Source("Screenshot", _picture()), _picture())
        _wait(app, lambda: nb._turn is None)
        card = nb.answers._windows[-1]
        buttons = {b.cget("text"): b for b in _buttons(card)}
        assert list(buttons) == ["Solve 1.1", "Solve #2"] and "Solution." not in nb.answers.plain_text()
        buttons["Solve 1.1"].invoke()                          # the stored one: answered at once, nothing is read again
        _wait(app, lambda: nb._turn is None and "Solution." in nb.answers.plain_text())
        assert len(fake.requests) == 2                         # the two readings of the picture, nothing else
    assert "Problem 1.1." in nb.answers.plain_text() and not app.errors


def test_check_again_solves_it_again_and_says_so(app):
    coin = "A fair coin is tossed 10 times. Find the probability of exactly 3 heads."
    right = [{"text": "**Given:** n=10.", "calls": ["comb(10, 3) / 2**10"]}, "**Answer:** 0.1171875"]
    with FakeOllama({"vl": ["completion", "vision", "tools"]}, replies=right * 3) as fake:
        nb = _ready(app, fake.url)
        nb.submit(nb_session().Source("Typed", text=coin))
        _wait(app, lambda: nb._turn is None and nb._checker is None and not nb._checks and len(fake.requests) >= 4)
        answer = next(md for md in nb._rechecks)
        assert nb.can_recheck(answer) and nb.cache.answer(coin)         # the background re-check agreed: remembered
        nb.recheck(answer)
        _wait(app, lambda: "Checked again: I get the same answer." in nb.answers.plain_text(), 30)
    assert not app.errors
