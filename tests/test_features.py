"""Checks for the range sliders, the dark graph paper, the value ball, moving / zooming with the
mouse and the column suggestions (no window needed).

    python tests/test_features.py
"""
from __future__ import annotations

import contextlib
import io
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402

from plotstudio.data import RowSettings, load_csv  # noqa: E402
from plotstudio.engine import LabelSettings, StyleSettings, build_plot, run_plot  # noqa: E402
from plotstudio.graphs import GRAPHS, suggest  # noqa: E402
from plotstudio.limits import fmt_number, fracs, limit_values  # noqa: E402
from plotstudio.paper import _step, apply_dark_paper  # noqa: E402
from plotstudio.theme import DARK, LIGHT, WIDGET_BG_KEYS, WIDGET_FG_KEYS  # noqa: E402
from plotstudio.tracker import PointTracker  # noqa: E402
from plotstudio.navigate import Navigator, pan_fracs, zoom_fracs  # noqa: E402
from plotstudio import recommend  # noqa: E402
import types  # noqa: E402

SAMPLES = ROOT / "samples"
SAMPLE_FOR = {"line": "training_log.csv", "area": "training_log.csv", "confusion": "model_predictions.csv",
              "roc": "model_predictions.csv", "images": "digits_8x8.csv", "contour": "surface_xyz.csv",
              "surface3d": "surface_xyz.csv", "scatter3d": "surface_xyz.csv"}
COLORS = lambda: {"box": "#1c1c1f", "border": "#3a3a41", "text": "#ededf0", "ring": "#ffffff"}  # noqa: E731

failures = []


def check(cond, text):
    if not cond:
        failures.append(text)
        print("FAIL", text)


def run_script(script):
    with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
        warnings.simplefilter("ignore")
        exec(compile(script, "<script>", "exec"), {"__name__": "__main__"})
    plt.close("all")


def test_palettes():
    for name, pal in (("light", LIGHT), ("dark", DARK)):
        check(set(pal) == set(LIGHT), f"{name} palette has the same keys as light")
        for keys in (WIDGET_BG_KEYS, WIDGET_FG_KEYS):
            values = [pal[k].lower() for k in keys]
            check(len(set(values)) == len(values), f"{name} palette: widget colours are unique {keys}")


def test_limits_numbers_and_dates():
    ds = load_csv(SAMPLES / "store_sales.csv")
    g = next(x for x in GRAPHS if x.id == "line")
    sel = {**suggest(g, ds), "x": "date", "y": ["sales"]}
    built = build_plot(g, ds, sel, {}, RowSettings(), StyleSettings(), LabelSettings())
    fig, _w, _s = run_plot(built)
    z = fig._studio_zoom
    check(z is not None and z["x"]["date"], "line plot over dates can be zoomed, X is a date axis")
    xl, yl = limit_values(z["x"], 0.2, 0.6), limit_values(z["y"], 0.1, 0.9)
    check(limit_values(z["x"], 0.0, 1.0) is None, "full range means no limit line")
    built = build_plot(g, ds, sel, {}, RowSettings(), StyleSettings(), LabelSettings(xlim=xl, ylim=yl))
    check("ax.set_xlim(pd.Timestamp(" in built.script and "ax.set_ylim(" in built.script,
          "limits are written into the script")
    check("set_xlim" not in built.plot_code and "set_xlim" in built.limit_code,
          "limits run after the plot (so the automatic range can be recorded)")
    fig, _w, _s = run_plot(built)
    ax = fig._studio_zoom["ax"]
    lo, hi = fracs(fig._studio_zoom["x"], ax.get_xlim())
    check(abs(lo - 0.2) < 0.02 and abs(hi - 0.6) < 0.02, f"slider positions come back ({lo:.3f}, {hi:.3f})")
    run_script(built.script)
    plt.close("all")


def test_limits_log_axis():
    ds = load_csv(SAMPLES / "airline_demo.csv")
    g = next(x for x in GRAPHS if x.id == "scatter")
    built = build_plot(g, ds, suggest(g, ds), {}, RowSettings(), StyleSettings(), LabelSettings(logy=True))
    fig, _w, _s = run_plot(built)
    spec = fig._studio_zoom["y"]
    check(spec["scale"] == "log", "log axis slides in log steps")
    a, b = limit_values(spec, 0.25, 0.75)
    check(0 < a < b, "log limits are positive and ordered")
    plt.close("all")


def test_not_zoomable():
    ds = load_csv(SAMPLES / "airline_demo.csv")
    for gid in ("pie", "corr", "pairplot", "facet", "scatter3d"):
        g = next(x for x in GRAPHS if x.id == gid)
        name = SAMPLE_FOR.get(gid, "airline_demo.csv")
        d = ds if name == "airline_demo.csv" else load_csv(SAMPLES / name)
        built = build_plot(g, d, suggest(g, d), {}, RowSettings(), StyleSettings(),
                           LabelSettings(xlim=(0, 1), ylim=(0, 1)))
        check(not built.zoomable and "set_xlim" not in built.script, f"{gid}: no range sliders, no limit lines")


def test_every_graph_paper_and_tracker():
    datasets = {}
    for g in GRAPHS:
        name = SAMPLE_FOR.get(g.id, "airline_demo.csv")
        ds = datasets.get(name) or datasets.setdefault(name, load_csv(SAMPLES / name))
        built = build_plot(g, ds, suggest(g, ds), {}, RowSettings(), StyleSettings(), LabelSettings())
        fig, _w, _s = run_plot(built)
        before = [tuple(map(tuple, ax.collections[0].get_facecolor())) for ax in fig.axes
                  if ax.collections and ax.collections[0].get_array() is None and len(ax.collections[0].get_facecolor())]
        apply_dark_paper(fig)
        after = [tuple(map(tuple, ax.collections[0].get_facecolor())) for ax in fig.axes
                 if ax.collections and ax.collections[0].get_array() is None and len(ax.collections[0].get_facecolor())]
        # coloured data keeps its colour, except the Studio colours, which take their dark-paper step
        coloured = []
        for b, a in zip(before, after):
            if not b or max(b[0][:3]) - min(b[0][:3]) <= 0.1:
                continue
            step = _step(b[0])
            coloured.append(a == b or (step is not None and all(abs(x - y) < 1e-6 for x, y in zip(a[0], step))))
        check(all(coloured), f"{g.id}: data colours kept (or stepped for dark paper)")
        canvas = FigureCanvasAgg(fig)
        tr = PointTracker(canvas, COLORS)
        canvas.draw()
        tr._on_draw()
        hits = 0
        for ax in fig.axes:
            if getattr(ax, "name", "") != "rectilinear" or hasattr(ax, "_colorbar"):
                continue
            bb = ax.bbox
            for fx in (0.1, 0.3, 0.5, 0.7, 0.9):
                for fy in (0.1, 0.3, 0.5, 0.7, 0.9):
                    x, y = bb.x0 + fx * bb.width, bb.y0 + fy * bb.height
                    xd, yd = ax.transData.inverted().transform((x, y))
                    hit = tr.find(ax, x, y, xd, yd)
                    if hit:
                        hits += 1
                        tr._show(*hit)
                        check(isinstance(hit[3], str) and hit[3], f"{g.id}: hover text")
        tr.hide()
        print(f"ok   {g.id:<12} hover hits {hits}")
        plt.close("all")


def _event(**kw):
    return types.SimpleNamespace(**{"button": None, "dblclick": False, "step": 0, "guiEvent": None, **kw})


def test_navigation_math():
    def near(a, b):
        return all(abs(x - y) < 1e-9 for x, y in zip(a, b))
    check(near(pan_fracs(0.2, 0.6, 0.1), (0.3, 0.7)), "pan moves the window")
    check(near(pan_fracs(0.2, 0.6, -0.5), (0.0, 0.4)), "pan stops at the start")
    check(near(pan_fracs(0.2, 0.6, 0.9), (0.6, 1.0)), "pan stops at the end")
    lo, hi = zoom_fracs(0.0, 1.0, 0.5, 0.8)
    check(abs(lo - 0.1) < 1e-9 and abs(hi - 0.9) < 1e-9, "zoom in around the middle")
    check(zoom_fracs(0.1, 0.9, 0.5, 10) == (0.0, 1.0), "zoom out never goes past everything")
    lo, hi = zoom_fracs(0.0, 1.0, 0.0, 0.5)
    check(lo == 0.0 and abs(hi - 0.5) < 1e-9, "zoom keeps the point under the mouse")


def test_navigator_on_plots():
    ds = load_csv(SAMPLES / "airline_demo.csv")
    for gid, lab in (("scatter", {}), ("hist", {}), ("box", {}), ("scatter", {"logy": True})):
        g = next(x for x in GRAPHS if x.id == gid)
        built = build_plot(g, ds, suggest(g, ds), {}, RowSettings(), StyleSettings(), LabelSettings(**lab))
        fig, _w, _s = run_plot(built)
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        z = fig._studio_zoom
        done = []
        nav = Navigator(canvas, natural={id(z["ax"]): {"x": z["x"], "y": z["y"]}}, on_done=done.append)
        entry = nav.specs[id(z["ax"])]
        bb = z["ax"].bbox
        cx, cy = bb.x0 + bb.width / 2, bb.y0 + bb.height / 2
        nav._wheel(_event(x=cx, y=cy, step=2))
        x0, x1 = nav.current(entry, "x")
        check(x1 - x0 < 0.7, f"{gid}: the wheel zooms in")
        nav._press(_event(x=cx, y=cy, button=1))
        nav._motion(_event(x=cx + 5000, y=cy, button=1))
        nav._release(_event(x=cx + 5000, y=cy, button=1))
        check(nav.current(entry, "x")[0] == 0.0, f"{gid}: dragging stops at the start of the range")
        check(done, f"{gid}: a finished move is reported (to update the code)")
        if gid == "hist":
            check(abs(z["ax"].get_ylim()[0]) < 1e-9, "hist: zooming keeps the bars on their base line")
        nav._press(_event(x=cx, y=cy, button=1, dblclick=True))
        check(nav.current(entry, "x") == (0.0, 1.0) and nav.current(entry, "y") == (0.0, 1.0),
              f"{gid}: double-click shows everything again")
        plt.close("all")
    print("ok   navigator")


def test_suggestions():
    for name, target in (("airline_demo.csv", "satisfaction"), ("store_sales.csv", "sales"),
                         ("training_log.csv", None), ("model_predictions.csv", "y_true")):
        ds = load_csv(SAMPLES / name)
        check(recommend.default_target(ds) == target, f"{name}: target guess {recommend.default_target(ds)}")
        for g in GRAPHS:
            sel, notes = recommend.suggest_all(g, ds, target)
            for role in g.roles:
                for pick in recommend.rank(g, role, ds, sel, target):
                    check(pick.column in ds.columns, f"{g.id}/{role.key}: suggested column exists")
    ds = load_csv(SAMPLES / "airline_demo.csv")
    g = next(x for x in GRAPHS if x.id == "scatter")
    sel, notes = recommend.suggest_all(g, ds, "satisfaction")
    check(sel["x"] == "Online boarding", f"scatter X = the feature most linked to the target ({sel['x']})")
    check(sel["color"] == "satisfaction", "scatter colour = the class target")
    prof = recommend.profile(ds, "satisfaction")
    check(prof.link("Online boarding")[0] > prof.link("Age")[0], "eta ranks a strong feature above a weak one")
    check(prof.link("Class")[1].startswith("V "), "groups vs class target use Cramer's V")
    ds = load_csv(SAMPLES / "store_sales.csv")
    g = next(x for x in GRAPHS if x.id == "line")
    sel, _ = recommend.suggest_all(g, ds, "sales")
    check(sel["x"] == "date" and sel["y"][0] == "sales", f"line: dates on X, the target first ({sel})")
    print("ok   suggestions")


def test_suggest_scores_match_the_plot_ideas():
    """Review 1: Suggest and Data summary used their own uncorrected eta / Cramer's V and Pearson only, so a
    column of 45 tiny groups in 90 rows (pure noise) scored V = 0.71 and came first, while the Plot ideas,
    bias-corrected, ranked it last. Both now use core.assoc on the same sample."""
    import numpy as np
    import pandas as pd
    from plotstudio.core import assoc
    from plotstudio.data import dataset_from_frame
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 90)
    df = pd.DataFrame({"noise45": [f"g{i}" for i in rng.permutation(np.repeat(np.arange(45), 2))],
                       "useful": np.where(rng.random(90) < 0.75, y, 1 - y), "x": rng.normal(size=90) + y, "y": y})
    ds = dataset_from_frame(df, "noise.csv")
    prof = recommend.Profile(ds, "y")
    scores = {c: prof.link(c)[0] for c in ("noise45", "useful", "x")}
    check(max(scores, key=scores.get) == "useful" and scores["noise45"] < scores["x"],
          f"noise with many groups is ranked last ({scores})")
    ca, la = assoc.codes_of(df["noise45"])
    cb, lb = assoc.codes_of(df["y"])
    check(abs(scores["noise45"] - assoc.cramers_v(assoc.crosstab(ca, len(la), cb, len(lb))[0])) < 1e-9,
          "Suggest V = the Plot ideas' V")
    # a curved but steady link between two numbers: the rank correlation is shown and ranks it
    x = np.linspace(0, 6, 200)
    curve = dataset_from_frame(pd.DataFrame({"x": x, "noise": rng.normal(size=200), "t": np.exp(x)}), "c.csv")
    link = recommend.Profile(curve, "t").link("x")
    check(link[1].startswith(recommend.SYMBOLS["rho"]) and link[0] > 0.99, f"rho for a curved link ({link})")
    print("ok   suggest scores = plot ideas scores")


def test_number_format():
    check(fmt_number(1460) == "1,460", "fmt 1460")
    check(fmt_number(0.73456) == "0.7346", "fmt 0.73")
    check(fmt_number(12.5) == "12.5", "fmt 12.5")
    check(fmt_number(755000.0) == "755,000", "fmt 755000")


def test_score_formula_works_on_small_extracted_table_under_20_rows():
    import pandas as pd
    from plotstudio.core.feature_lab import score_formula, suggest_features
    from plotstudio.core.pipeline import Pipeline

    df = pd.DataFrame({
        "Quarter": ["Q1", "Q2", "Q3", "Q4"],
        "Revenue": [10000, 12000, 15000, 18000],
        "Expense": [4900, 5350, 9400, 9600],
        "NetMargin": [0.51, 0.55, 0.37, 0.46],
    })
    result = suggest_features(df, "NetMargin")
    suggestion = score_formula(result, "Revenue - Expense", name="Profit")
    pipeline = Pipeline()
    pipeline.add(suggestion.step, df)

    assert pipeline.transform(df)["Profit"].tolist() == [5100.0, 6650.0, 5600.0, 8400.0]


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILURE(S)'}")
    sys.exit(1 if failures else 0)


def test_the_style_switch_keeps_every_control_where_it_is_and_switches_back(tmp_path, monkeypatch):
    import json
    import tkinter as tk
    try:
        tk.Tk().destroy()
    except tk.TclError:
        import pytest
        pytest.skip("no display")
    import plotstudio.settings as settings
    from plotstudio.theme import C, INK_DARK, DARK
    monkeypatch.setattr(settings, "PATH", tmp_path / ".csv_plot_studio.json")
    settings.PATH.write_text(json.dumps({"ui_theme": "dark"}), encoding="utf-8")
    from plotstudio.app import App
    app = App()
    try:
        app.update()
        buttons = [w for w in _walk(app) if w.winfo_class() == "TButton" and w.winfo_ismapped()]
        before = {str(w): (w.winfo_rootx(), w.winfo_rooty()) for w in buttons if w.cget("text") not in ("New style", "Default style")}
        style = next(w for w in _walk(app) if w.winfo_class() == "TButton" and w.cget("text") == "New style")
        style.invoke(); app.update()
        assert app.theme.ink and C["panel"] == INK_DARK["panel"] and style.cget("text") == "Default style"
        after = {str(w): (w.winfo_rootx(), w.winfo_rooty()) for w in buttons if str(w) in before}
        assert after == before                                  # nothing moved
        assert json.loads(settings.PATH.read_text(encoding="utf-8"))["ui_style"] == "ink"
        style.invoke(); app.update()
        assert not app.theme.ink and C["panel"] == DARK["panel"]   # and back to the default style
    finally:
        app.destroy()


def _walk(w):
    yield w
    for child in w.winfo_children():
        yield from _walk(child)
