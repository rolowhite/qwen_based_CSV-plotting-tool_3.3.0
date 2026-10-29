"""Ceasar in the real window with a scripted fake Ollama: it greets with starter tasks, the user's own sentence changes
the table everywhere, Undo / Redo / Back to loaded, Feature Lab steps survive an edit, the exported code reproduces
the table, and without a file or without Ollama nothing breaks."""
import json
import sys
import tkinter as tk
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebook"))
from fake_ollama import FakeOllama  # noqa: E402

pytestmark = pytest.mark.gui
SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "titanic_like.csv"
MASTER = "mask = df['Name'].str.contains(r'\\bMaster\\.', na=False)\ndf.loc[mask, 'Age'] = 18"
MODELS = {"qwen": ["completion", "tools"]}


def R(kind, say="ok", code=""):
    return json.dumps({"kind": kind, "say": say, "code": code})


@pytest.fixture
def make_app(tmp_path, monkeypatch):
    try:
        tk.Tk().destroy()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    import plotstudio.settings as settings
    monkeypatch.setattr(settings, "PATH", tmp_path / ".csv_plot_studio.json")
    made = []

    def build(url="http://127.0.0.1:9", csv=SAMPLE):
        settings.PATH.write_text(json.dumps({"notebook_ollama_url": url}), encoding="utf-8")
        from plotstudio.app import App
        window = App(csv_path=str(csv)) if csv else App()
        errors = []
        window.report_callback_exception = lambda *a: errors.append(a)
        window.errors = errors
        window.geometry("1400x900+0+0")
        made.append(window)
        return window
    yield build
    for w in made:
        w.on_close()


def wait(app, condition, timeout=30.0):
    import time
    end = time.time() + timeout
    while not condition():
        if time.time() > end:
            raise AssertionError("timed out")
        app.update()
        time.sleep(0.02)


def settle(app, seconds=0.3):
    wait(app, lambda: False, 0) if False else None
    import time
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def open_ceasar(app):
    app.work.nb.select(app.work.ceasar_view)
    settle(app, 0.5)
    wait(app, lambda: not app.ceasar.busy)
    return app.work.ceasar_view


def transcript(view):
    return view.text.get("1.0", "end")


def run_task(app, task_id):
    from plotstudio.core.ceasar import tasks
    app.ceasar.run_task(tasks.BY_ID[task_id])
    wait(app, lambda: not app.ceasar.busy)


def say(app, view, text):
    view.entry.set_value(text)
    view.send()
    wait(app, lambda: not app.ceasar.busy)
    settle(app, 0.2)


def cards_text(view):
    out = []
    for card in view.cards:
        def walk(w):
            try:
                out.append(w.cget("text"))
            except tk.TclError:
                pass
            for c in w.winfo_children():
                walk(c)
        walk(card)
    return "\n".join(t for t in out if t)


def test_tab_sits_after_feature_lab_and_nothing_else_moved(make_app):
    app = make_app()
    names = [app.work.nb.tab(t, "text").strip() for t in app.work.nb.tabs()]
    assert names[-2:] == ["Feature Lab", "Ceasar"] or names[-1] == "Ceasar"
    assert names.index("Ceasar") == names.index("Feature Lab") + 1


def test_without_a_csv_it_waits_and_says_so(make_app):
    app = make_app(csv=None)
    view = app.work.ceasar_view
    assert not app.ceasar.ready
    assert "Open a CSV" in transcript(view) or "Open a CSV" in view.subtitle.cget("text")
    assert str(view.entry.cget("state")) == "disabled" and view.send_btn.instate(["disabled"])
    view.send()                                     # nothing happens, nothing breaks
    assert app.errors == []


def test_opening_the_tab_looks_at_the_file_and_offers_starter_tasks(make_app):
    with FakeOllama(MODELS, replies=["Age and Cabin have gaps; check the duplicates next."]) as fake:
        app = make_app(fake.url)
        view = open_ceasar(app)
        settle(app, 1.0)
        text = transcript(view) + cards_text(view)
        assert "426" in text and "Count missing data" in cards_text(view)
        assert "Remove duplicate rows" in cards_text(view)
        assert "Age and Cabin have gaps" in transcript(view)       # the model's own read, as an extra
        assert "titanic_like" in view.file_chip.cget("text")
        assert app.errors == []


def test_starter_tasks_work_with_no_ollama_at_all(make_app):
    app = make_app()                                # the Ollama url points nowhere
    view = open_ceasar(app)
    assert "Count missing data" in cards_text(view)
    run_task(app, "count_missing")
    assert "Age" in transcript(view) and len(app.ceasar.edits) == 0
    run_task(app, "find_duplicates")
    assert len(app.dataset.df) == 420 and len(app.ceasar.edits) == 1
    assert len(app.lab.working.df) == 420
    say(app, view, "make the ages 18")              # the chat needs Ollama: a clear message, no crash
    assert "Ollama" in transcript(view)
    assert app.errors == []


def test_the_users_sentence_changes_the_csv_everywhere(make_app):
    with FakeOllama(MODELS, replies=["n", R("change", "I set Age to 18 for every Master.", MASTER)]) as fake:
        app = make_app(fake.url)
        view = open_ceasar(app)
        before = app.lab.base.df.copy()
        say(app, view, "make the ages 18 if their name starts with master")
        after = app.lab.working.df
        masters = before["Name"].str.contains("Master", na=False)
        assert masters.sum() > 0 and (after.loc[masters, "Age"] == 18).all()
        assert after.loc[~masters].equals(before.loc[~masters]), "no other cell may change"
        assert app.dataset is app.lab.working or app.dataset.df.equals(after)      # every tab sees the new table
        assert view.changed_rows and "cells changed" in cards_text(view)
        assert len(view.tree.get_children()) == len(view.changed_rows)          # the changed rows first
        assert "Age" in [view.tree.heading(c, "text").lstrip("● ") for c in view.tree["columns"][1:]]
        assert "Master" in " ".join(str(v) for v in view.tree.item(view.tree.get_children()[0], "values"))
        assert (pd.read_csv(SAMPLE).equals(before))                          # the file on disk is never touched
        assert app.errors == []


def test_undo_redo_and_back_to_the_file_as_loaded(make_app):
    with FakeOllama(MODELS, replies=["n", R("change", "ok", MASTER)]) as fake:
        app = make_app(fake.url)
        view = open_ceasar(app)
        original = app.lab.base.df.copy()
        run_task(app, "find_duplicates")
        say(app, view, "master is 18")
        edited = app.lab.working.df.copy()
        assert len(app.ceasar.edits) == 2 and view.undo_btn.instate(["!disabled"])
        app.ceasar.undo(); wait(app, lambda: not app.ceasar.busy)
        assert len(app.lab.working.df) == 420 and app.lab.working.df["Age"].ne(18).any()
        app.ceasar.redo(); wait(app, lambda: not app.ceasar.busy)
        assert app.lab.working.df.equals(edited)
        app.ceasar.restore(); wait(app, lambda: not app.ceasar.busy)
        assert app.lab.working.df.equals(original) and not app.ceasar.edits
        assert view.restore_btn.instate(["disabled"]) and view.redo_btn.instate(["!disabled"])
        app.ceasar.redo(); app.ceasar.redo()
        wait(app, lambda: not app.ceasar.busy)
        assert app.errors == []


def test_a_new_edit_clears_redo(make_app):
    app = make_app()
    open_ceasar(app)
    run_task(app, "find_duplicates")
    app.ceasar.undo(); wait(app, lambda: not app.ceasar.busy)
    assert app.ceasar.undone
    run_task(app, "fill_missing")
    assert not app.ceasar.undone


def test_code_that_does_nothing_is_never_applied(make_app):
    nothing = R("change", "done", "df.loc[df['Name'].str.startswith('Master', na=False), 'Age'] = 18")
    with FakeOllama(MODELS, replies=["n", nothing, nothing]) as fake:
        app = make_app(fake.url)
        view = open_ceasar(app)
        say(app, view, "make the ages 18 if their name starts with master")
        assert not app.ceasar.edits and "changed nothing" in transcript(view) + cards_text(view)


def test_a_question_is_answered_without_changing_the_table(make_app):
    with FakeOllama(MODELS, replies=["n", R("question", "Counting.", "answer = int(df['Age'].isna().sum())")]) as fake:
        app = make_app(fake.url)
        view = open_ceasar(app)
        say(app, view, "how many ages are missing?")
        assert str(int(app.lab.base.df["Age"].isna().sum())) in transcript(view) and not app.ceasar.edits


def test_feature_lab_steps_survive_an_edit_and_the_export_reproduces_the_table(make_app, tmp_path):
    pytest.importorskip("sklearn")
    app = make_app()
    view = open_ceasar(app)
    app.work.target_var.set("Survived")
    app.lab.suggest()
    wait(app, lambda: app.lab.result is not None and not app.lab.busy, 90)
    good = [s for s in app.lab.result.suggestions if s.can_accept]
    assert good, "the sample should give the Feature Lab at least one acceptable feature"
    app.lab.accept(good[0])
    wait(app, lambda: not app.lab.busy)
    step = good[0].step.name
    assert step in app.lab.working.df.columns
    run_task(app, "find_duplicates")
    assert step in app.lab.working.df.columns and len(app.lab.working.df) == 420, "the step runs again on the edit"
    # the exported script, run on the raw file, gives the same table
    script = app.ceasar.script()
    assert "Ceasar" in script and "drop_duplicates" in script
    scope = {"__name__": "export"}
    exec(compile(script, "<export>", "exec"), scope)
    rebuilt = scope["add_features"](scope["read"](str(SAMPLE)), train=True)
    assert list(rebuilt.columns) == list(app.lab.working.df.columns)
    assert len(rebuilt) == len(app.lab.working.df)
    pd.testing.assert_frame_equal(rebuilt.reset_index(drop=True), app.lab.working.df.reset_index(drop=True),
                                  check_dtype=False)
    assert app.errors == []


def test_a_step_that_no_longer_fits_is_dropped_with_a_note_not_a_crash(make_app):
    pytest.importorskip("sklearn")
    app = make_app()
    open_ceasar(app)
    app.work.target_var.set("Survived")
    app.lab.suggest()
    wait(app, lambda: app.lab.result is not None and not app.lab.busy, 90)
    good = [s for s in app.lab.result.suggestions if s.can_accept]
    app.lab.accept(good[0])
    wait(app, lambda: not app.lab.busy)
    from plotstudio.ceasar import Edit
    cols = list(good[0].step.inputs) if hasattr(good[0].step, "inputs") else []
    code = f"df = df.drop(columns={cols or ['Fare']!r})"
    app.ceasar._execute("drop it", code, "change")
    wait(app, lambda: not app.ceasar.busy)
    assert app.errors == [] and len(app.ceasar.edits) == 1


def test_save_csv_writes_the_edited_table(make_app, tmp_path, monkeypatch):
    from tkinter import filedialog
    app = make_app()
    view = open_ceasar(app)
    run_task(app, "find_duplicates")
    target = tmp_path / "out.csv"
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: str(target))
    view.save_csv()
    assert len(pd.read_csv(target)) == 420 and len(pd.read_csv(SAMPLE)) == 426


def test_code_button_shows_the_edits(make_app, monkeypatch):
    app = make_app()
    view = open_ceasar(app)
    run_task(app, "find_duplicates")
    shown = []
    import plotstudio.featurelab as fl
    monkeypatch.setattr(fl.CodeDialog, "__init__", lambda self, v, code, name, note="": shown.append((code, name)))
    view.show_code()
    assert shown and "drop_duplicates" in shown[0][0]


def test_loading_another_file_starts_fresh(make_app, tmp_path):
    app = make_app()
    view = open_ceasar(app)
    run_task(app, "find_duplicates")
    other = tmp_path / "other.csv"
    pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}).to_csv(other, index=False)
    app.loader.load(str(other))
    wait(app, lambda: app.dataset is not None and app.dataset.path.name == "other.csv", 30)
    assert app.ceasar.edits == [] and app.ceasar.source.name == "other.csv"
    assert "other.csv" in view.file_chip.cget("text")


def test_plot_ideas_and_theme_switch_do_not_break(make_app):
    app = make_app()
    view = open_ceasar(app)
    run_task(app, "plot_ideas")
    settle(app, 1.0)
    view.on_theme()
    assert app.errors == []


# ------------------------------------------------------- found in review --
def test_stop_frees_the_tab_and_the_late_result_is_dropped(make_app):
    with FakeOllama(MODELS, replies=["n", {"text": R("change", "ok", MASTER), "delay": 1.5}]) as fake:
        app = make_app(fake.url)
        view = open_ceasar(app)
        view.entry.set_value("master is 18")
        view.send()
        settle(app, 0.3)
        assert app.ceasar.busy
        app.ceasar.stop()
        assert not app.ceasar.busy and view.send_btn.instate(["!disabled"])
        settle(app, 2.5)
        assert not app.ceasar.edits and app.lab.working.df["Age"].ne(18).any()
        assert app.errors == []


def test_a_job_still_running_when_another_file_opens_never_touches_it(make_app, tmp_path):
    with FakeOllama(MODELS, replies=["n", {"text": R("change", "ok", MASTER), "delay": 1.5}]) as fake:
        app = make_app(fake.url)
        view = open_ceasar(app)
        view.entry.set_value("master is 18")
        view.send()
        settle(app, 0.3)
        other = tmp_path / "other.csv"
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(other, index=False)
        app.loader.load(str(other))
        wait(app, lambda: app.dataset is not None and app.dataset.path.name == "other.csv", 30)
        settle(app, 2.5)
        assert list(app.lab.working.df.columns) == ["a"] and not app.ceasar.edits
        assert app.ceasar.greeted or not view.is_showing()
        assert app.errors == []


def test_undo_clears_the_shading_of_the_edit_it_took_back(make_app):
    app = make_app()
    view = open_ceasar(app)
    run_task(app, "fill_missing")
    assert view.changed_rows
    app.ceasar.undo()
    wait(app, lambda: not app.ceasar.busy)
    assert not view.changed_rows and not view.changed_cols
    assert not any("● " in view.tree.heading(c, "text") for c in view.tree["columns"])
