"""The Feature Lab in the real window: the Titanic demo end to end, and a 500,000-row file that must not
freeze the window. Skipped when there is no display."""
import sys
import time

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.gui
pytest.importorskip("sklearn")


@pytest.fixture
def app(tmp_path, monkeypatch):
    tk = pytest.importorskip("tkinter")
    try:
        probe = tk.Tk()
        probe.destroy()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    monkeypatch.setenv("HOME", str(tmp_path))
    import plotstudio.settings as settings
    monkeypatch.setattr(settings, "PATH", tmp_path / ".csv_plot_studio.json")
    unraisable = []
    monkeypatch.setattr(sys, "unraisablehook", lambda info: unraisable.append(info))
    from plotstudio.app import App
    window = App()
    errors = []
    window.report_callback_exception = lambda *a: errors.append(a)
    window.errors, window.unraisable = errors, unraisable
    window.geometry("1400x900+0+0")
    yield window
    window.on_close()


def pump(app, seconds, until=None, steps=None):
    """Run the window for up to `seconds`; return True once until() is true. Records each step's time."""
    end = time.time() + seconds
    while time.time() < end:
        t0 = time.time()
        app.update()
        if steps is not None:
            steps.append(time.time() - t0)
        if until is not None and until():
            return True
        time.sleep(0.01)
    return until is None


def lab_ready(app):
    return app.lab.result is not None and not app.lab.busy


def eval_head(lab):
    """The first line of the evaluation: what was compared, and whether the steps changed since."""
    labels = lab.eval_box.winfo_children()
    return labels[0].cget("text") if labels else ""


def test_titanic_demo_through_the_window(app, kaggle_titanic, tmp_path, monkeypatch):
    from tkinter import filedialog, simpledialog
    from plotstudio.featurelab import SubmissionDialog

    full = pd.read_csv(kaggle_titanic)
    train = full.sample(frac=0.8, random_state=1).sort_index()
    train.to_csv(tmp_path / "train.csv", index=False)
    full.drop(train.index).drop(columns=["Survived"]).to_csv(tmp_path / "test.csv", index=False)
    app.loader.load(str(tmp_path / "train.csv"))
    assert pump(app, 30, lambda: app.dataset is not None)
    work, lab = app.work, app.work.lab_view
    work.show_lab()
    work.target_var.set("Survived")
    work._target_changed()
    assert pump(app, 60, lambda: lab_ready(app) and app.lab.result.target == "Survived")
    res = app.lab.result
    names = [s.name for s in res.suggestions[:8]]
    assert "title" in names and "SibSp_plus_Parch" in names, names
    assert lab.selected is not None and lab.selected.name == res.suggestions[0].name
    assert pump(app, 30, lambda: lab._plot_job is None and lab.preview_canvases)       # drawn one by one
    assert len(lab.preview_canvases) == 2, "the first suggestion is previewed with its distribution and its link"

    lab.accept_buttons["title"].invoke()
    assert pump(app, 60, lambda: "title" in app.dataset.df.columns and lab_ready(app))
    lab.accept_buttons["SibSp_plus_Parch"].invoke()
    assert pump(app, 60, lambda: "SibSp_plus_Parch" in app.dataset.df.columns and lab_ready(app))
    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **k: "family_size")
    lab.rename(1)
    assert pump(app, 60, lambda: "family_size" in app.dataset.df.columns and lab_ready(app))
    assert [s.name for s in app.lab.pipeline] == ["title", "family_size"] and len(lab.chips) == 2

    lab.formula.set_value("Fare / (family_size + 1)")
    lab.formula_name.set_value("fare_per_person")
    lab.check_formula()
    assert pump(app, 30, lambda: app.lab.custom is not None and not app.lab.busy)
    assert app.lab.custom.name == "fare_per_person"
    lab.formula.set_value("__import__('os').getcwd()")
    lab.check_formula()
    pump(app, 5, lambda: not app.lab.busy)
    assert "allowed" in lab.formula_msg.cget("text") or "not" in lab.formula_msg.cget("text")
    assert "os" not in app.dataset.df.columns

    lab.undo_btn.invoke()                                               # undoes the rename
    assert pump(app, 60, lambda: [x.name for x in app.lab.pipeline] == ["title", "SibSp_plus_Parch"] and
                lab_ready(app))
    assert "family_size" not in app.dataset.df.columns
    lab.redo_btn.invoke()
    assert pump(app, 60, lambda: [x.name for x in app.lab.pipeline] == ["title", "family_size"] and lab_ready(app))

    lab.eval_btn.invoke()
    assert pump(app, 120, lambda: app.lab.evaluation is not None and not app.lab.busy)
    for score in app.lab.evaluation.scores:
        assert score.after_mean > score.before_mean, score.text()
    lab.undo_btn.invoke()                                               # back and forth: same steps again
    assert pump(app, 60, lambda: app.lab.pipeline.can_redo and lab_ready(app))
    assert app.lab.current_evaluation is None and "press Evaluate again" in eval_head(lab)
    lab.redo_btn.invoke()
    assert pump(app, 60, lambda: not app.lab.pipeline.can_redo and lab_ready(app))
    assert app.lab.current_evaluation is not None and "press Evaluate again" not in eval_head(lab)

    # exports: clean.py rebuilds exactly the table every tab now uses
    saved = iter([tmp_path / "train_clean.py", tmp_path / "train_features.ipynb"])
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda *a, **k: str(next(saved)))
    lab.save_clean()
    lab.save_notebook()
    ns = {}
    code = (tmp_path / "train_clean.py").read_text(encoding="utf-8")
    exec(compile(code.replace('if __name__ == "__main__":', "if False:"), "clean.py", "exec"), ns)
    pd.testing.assert_frame_equal(ns["add_features"](ns["read"](str(tmp_path / "train.csv")), train=True),
                                  app.dataset.df)
    assert (tmp_path / "train_features.ipynb").stat().st_size > 1000

    dialog = SubmissionDialog(lab)
    dialog.choose(str(tmp_path / "test.csv"))
    assert dialog.id_var.get() == "PassengerId"
    dialog.save(str(tmp_path / "submission.csv"))
    assert pump(app, 120, lambda: (tmp_path / "submission.csv").exists() and not app.lab.busy)
    sub = pd.read_csv(tmp_path / "submission.csv")
    assert list(sub.columns) == ["PassengerId", "Survived"] and len(sub) == len(full) - len(train)

    # the new columns are ordinary columns for the plots, and the plot code includes the steps
    from plotstudio.graphs import GRAPH_BY_ID
    app.graph = GRAPH_BY_ID["count"]
    work.set_graph(app.graph)
    work.roles["col"].apply("title")
    work.plot()
    pump(app, 2)
    assert work.plot_view.fig is not None and "Feature Lab steps" in work.code_view.code
    assert not app.errors, app.errors
    assert not app.unraisable, [str(u.exc_value) for u in app.unraisable]


@pytest.mark.slow
def test_500k_rows_do_not_freeze_the_window(app, tmp_path):
    rng = np.random.default_rng(0)
    n = 500_000
    y = rng.integers(0, 2, n)
    df = pd.DataFrame({"id": np.arange(n), "y": y, "amount": rng.lognormal(3, 1, n).round(2),
                       "visits": rng.integers(0, 6, n) + y, "returns": rng.integers(0, 4, n),
                       "city": rng.choice([f"c{i}" for i in range(30)], n),
                       "note": [f"order {i % 977} ref {i % 13}" for i in range(n)]})
    df.loc[rng.choice(n, 40_000, replace=False), "amount"] = np.nan
    path = tmp_path / "big.csv"
    df.to_csv(path, index=False)
    app.loader.load(str(path))
    assert pump(app, 120, lambda: app.dataset is not None)
    work = app.work
    work.show_lab()
    work.target_var.set("y")
    work._target_changed()
    steps = []
    assert pump(app, 300, lambda: lab_ready(app), steps)
    assert app.lab.result.rows_used == 50_000 and "50,000-row sample" in work.lab_view.subtitle.cget("text")
    assert max(steps) < 1.5, f"the window stopped for {max(steps):.2f} s while finding features"
    pick = next(s for s in app.lab.result.suggestions if s.can_accept)
    steps = []
    work.lab_view.accept_buttons[pick.name].invoke()
    assert pump(app, 300, lambda: pick.name in app.dataset.df.columns and lab_ready(app), steps)
    assert len(app.dataset.df) == n
    assert max(steps) < 1.5, f"the window stopped for {max(steps):.2f} s while applying a step"
    steps = []
    work.lab_view.eval_btn.invoke()
    assert pump(app, 600, lambda: app.lab.evaluation is not None and not app.lab.busy, steps)
    assert max(steps) < 1.5, f"the window stopped for {max(steps):.2f} s while evaluating"
    assert not app.errors and not app.unraisable


def test_column_types_and_plot_follow_feature_lab_changes(app, tmp_path):
    """Review 12.1: with no overrides left, update_dataset() didn't apply them, so undoing every step brought
    back the file's Dataset with the kinds of an earlier Column types choice ('age' skipped although set back
    to auto). And the plot and its code kept showing a column the undo had removed."""
    from plotstudio.core.pipeline import Step
    from plotstudio.graphs import GRAPH_BY_ID, compatible

    rng = np.random.default_rng(0)
    path = tmp_path / "data.csv"
    pd.DataFrame({"age": rng.normal(30, 9, 300).round(1), "fare": rng.lognormal(3, 1, 300).round(2),
                  "y": rng.integers(0, 2, 300)}).to_csv(path, index=False)
    app.loader.load(str(path))
    assert pump(app, 30, lambda: app.dataset is not None)
    work, svc = app.work, app.lab
    app.graph = GRAPH_BY_ID["hist"]
    work.set_graph(app.graph)
    role = next(r for r in app.graph.roles if r.key == "cols")
    work.set_type_overrides({"age": "skip"})
    assert "age" not in compatible(role, work.ds)

    class Suggestion:
        step = Step("log1p", ["fare"], "fare_log")

    svc.accept(Suggestion())
    assert pump(app, 30, lambda: "fare_log" in app.dataset.df.columns and not svc.busy)
    work.set_type_overrides({})                                         # all columns back to auto
    work.roles["cols"].apply(["fare_log"])
    work.plot()
    assert pump(app, 10, lambda: "fare_log" in work.code_view.code)
    svc.undo()
    assert pump(app, 30, lambda: "fare_log" not in app.dataset.df.columns and not svc.busy)
    assert pump(app, 10, lambda: "fare_log" not in work.code_view.code), "the plot follows the table"
    assert "age" in compatible(role, work.ds) and not work.ds.columns["age"].skipped
    assert not app.errors, app.errors
