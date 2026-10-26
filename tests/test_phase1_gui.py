"""The real window: Plot ideas tab on Titanic, every Plot it button, column types, target box.
Skipped when there is no display (e.g. a headless CI machine)."""
import os
import time

import pytest

pytestmark = pytest.mark.gui


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
    from plotstudio.app import App
    window = App()
    errors = []
    window.report_callback_exception = lambda *a: errors.append(a)
    window.errors = errors
    yield window
    window.on_close()


def settle(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def wait_for_ideas(app, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        settle(app, 0.1)
        if app.ideas.result is not None and app.ideas.job is None:
            return app.ideas.result
    pytest.fail("plot ideas did not arrive")


def test_plot_it_buttons(app, titanic, tmp_path):
    path = tmp_path / "titanic.csv"
    titanic.to_csv(path, index=False)
    app.loader.load(str(path))
    res = wait_for_ideas(app)
    assert res.target == "survived" and res.warnings[0].level == "leak" and "'alive'" in res.warnings[0].text
    work = app.work
    work.show_ideas()
    settle(app, 0.5)
    assert len(work.ideas_view.plot_buttons) == len(res.suggestions)
    for i, idea in enumerate(res.suggestions):
        work.nb.select(work.ideas_view)
        work.ideas_view.plot_buttons[i].invoke()
        settle(app, 0.3)
        assert work.graph.id == idea.graph and work.plot_view.fig is not None, idea.title
        def same(sel):      # a column list keeps the file's order in the picker
            return {k: sorted(v) if isinstance(v, list) else v for k, v in sel.items() if v}
        assert same(work.collect_selection()) == same(idea.sel), idea.title
    work.set_type_overrides({"age": "category"})
    res = wait_for_ideas(app)
    assert res.overrides == {"age": "category"}
    work.target_var.set("pclass")
    work._target_changed()
    res = wait_for_ideas(app)
    assert res.target == "pclass" and work.ideas_view.target_box.get() == "pclass"
    assert not app.errors
    assert os.environ.get("CSV_PLOT_STUDIO_LOG")
