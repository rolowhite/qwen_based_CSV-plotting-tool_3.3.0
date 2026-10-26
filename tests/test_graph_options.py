"""Regression tests from the trial of every graph type and option (v2.2.1).

Each bug the trial found has a check here: pair plot axis names, legend places on seaborn
grids, the regression equation sign, heatmap labels and cell numbers that collided, titles
and axis names cut off at the figure edge, the contour 'image' cells, and confusion matrices
whose actual and predicted columns name their classes differently.
"""
from __future__ import annotations

import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import QuadMesh

from plotstudio.codegen import PlotError, Raw
from plotstudio.data import RowSettings, dataset_from_frame
from plotstudio.engine import LabelSettings, StyleSettings, build_plot, run_plot
from plotstudio.graphs import GRAPH_BY_ID, heat_fit, wrap_title

LONG_TITLE = "A longer title that a user typed for this chart"
rng = np.random.default_rng(11)


# --------------------------------------------------------------------------- data
def _pairs():
    species = rng.choice(["s1", "s2", "s3"], 300)
    shift = pd.Series(species).map({"s1": 0.0, "s2": 2.0, "s3": 4.0}).to_numpy()
    return pd.DataFrame({"a": shift + rng.normal(size=300), "b": 0.5 * shift + rng.normal(size=300),
                         "c": rng.normal(size=300), "d": -shift + rng.normal(size=300), "species": species,
                         "site": rng.choice(["n", "s"], 300)})


PAIRS = _pairs()
WIDE = pd.DataFrame(rng.normal(size=(120, 20)), columns=[f"pixel{i}" for i in range(20)])
LONG_NAMES = pd.DataFrame(rng.normal(size=(120, 12)), columns=[f"measurement_{i:02d}_value" for i in range(12)])
BASIC = pd.DataFrame(rng.normal(size=(200, 9)), columns=["x", "y", "y2", "y3", "size", "pos", "neg", "err", "k"])
SALES = pd.DataFrame({"city": rng.choice([f"City number {i}" for i in range(25)], 3000),
                      "product": rng.choice([f"product_{c}" for c in "abcdefghijklmnopqrst"], 3000),
                      "sales": rng.gamma(2, 50, 3000)})
_classes = [f"class_{w}" for w in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
                                   "india", "juliet", "kilo", "lima")]
_act = rng.choice(_classes, 600)
CLASSES = pd.DataFrame({"actual": _act, "predicted": np.where(rng.random(600) < 0.7, _act, rng.choice(_classes, 600))})
_truth = rng.integers(0, 2, 400)
ML = pd.DataFrame({"y_true": _truth, "answer": np.where(_truth == 1, "yes", "no"),
                   "p_good": np.clip(_truth * 0.55 + rng.uniform(0, 0.45, 400), 0, 1),
                   "pred_good": (rng.random(400) < 0.5).astype(int), "c3": rng.choice(list("abc"), 400),
                   "actual3": rng.choice(list("abc"), 400)})
ML["pred3"] = np.where(rng.random(400) < 0.8, ML["actual3"], rng.choice(list("abc"), 400))
_gx, _gy = np.meshgrid(np.linspace(-3, 3, 25), np.linspace(-2, 2, 18))
GRID = pd.DataFrame({"x": _gx.ravel(), "y": _gy.ravel(), "z": (np.sin(_gx) * np.cos(_gy) + 0.1 * _gx).ravel()})


# --------------------------------------------------------------------------- helpers
def draw(gid, df, sel, opts=None, context="notebook", **labels):
    graph = GRAPH_BY_ID[gid]
    options = {o.key: o.default for o in graph.options}
    options.update(opts or {})
    selection = {r.key: sel.get(r.key, [] if r.multi else None) for r in graph.roles}
    built = build_plot(graph, dataset_from_frame(df, "test.csv"), selection, options, RowSettings(),
                       StyleSettings(context=context), LabelSettings(**labels))
    fig, _, _ = run_plot(built)
    FigureCanvasAgg(fig)
    fig.canvas.draw()
    return built, fig


def plot_axes(fig):
    return [ax for ax in fig.axes if ax.get_label() != "<colorbar>" and ax.get_visible()]


def tick_collisions(fig, ax):
    """Neighbouring tick labels that overlap, per axis."""
    renderer = fig.canvas.get_renderer()
    out = {}
    for axis, labels in (("x", ax.get_xticklabels()), ("y", ax.get_yticklabels())):
        boxes = sorted((t.get_window_extent(renderer) for t in labels if t.get_visible() and t.get_text()),
                       key=lambda b: b.x0 if axis == "x" else b.y0)
        out[axis] = sum(1 for a, b in zip(boxes, boxes[1:]) if a.overlaps(b))
    return out


def cell_number_collisions(fig, ax):
    renderer = fig.canvas.get_renderer()
    rows = {}
    for t in ax.texts:
        if t.get_visible() and t.get_text():
            b = t.get_window_extent(renderer)
            rows.setdefault(round(b.y0 + b.height / 2), []).append(b)
    return sum(1 for row in rows.values() for a, b in zip(sorted(row, key=lambda b: b.x0),
                                                          sorted(row, key=lambda b: b.x0)[1:]) if a.overlaps(b))


def cut_off(fig, tol=2):
    """Titles, axis names, tick labels or legends that run past the edge of the figure."""
    renderer = fig.canvas.get_renderer()
    W, H = fig.bbox.width, fig.bbox.height
    items = [fig._suptitle] if getattr(fig, "_suptitle", None) is not None else []
    items += list(fig.legends)
    for ax in fig.axes:
        if not ax.get_visible() or not ax.axison:
            continue
        items += [ax.title, ax._left_title, ax._right_title, ax.xaxis.label, ax.yaxis.label, ax.get_legend()]
        if ax.name != "3d":
            for axis in (ax.xaxis, ax.yaxis):
                lo, hi = sorted(axis.get_view_interval())
                items += [t.label1 for t in axis.get_major_ticks() if lo - 1e-9 <= t.get_loc() <= hi + 1e-9]
    bad = []
    for item in items:
        if item is None or not item.get_visible() or (hasattr(item, "get_text") and not item.get_text()):
            continue
        b = item.get_window_extent(renderer)
        over = max(-b.x0, b.x1 - W, -b.y0, b.y1 - H)
        if over > tol:
            bad.append(f"{getattr(item, 'get_text', lambda: 'legend')()[:30]!r} by {over:.0f}px")
    return bad


def legends(fig):
    return [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None] + list(fig.legends)


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


# --------------------------------------------------------------------------- seaborn grids
def test_pair_plot_with_typed_axis_names_draws_and_says_why_they_are_unused():
    built, fig = draw("pairplot", PAIRS, {"cols": ["a", "b", "c"]}, xlabel="X label", ylabel="Y label")
    assert any("labels each panel" in n for n in built.notes)
    assert "set_axis_labels" not in built.script


@pytest.mark.parametrize("gid, sel", [
    ("pairplot", {"cols": ["a", "b"], "hue": "species"}),
    ("facet", {"x": "a", "y": "b", "col": "site", "hue": "species"}),
    ("joint", {"x": "a", "y": "b", "hue": "species"}),
])
@pytest.mark.parametrize("where", ["hide", "upper left", "outside"])
def test_legend_place_works_on_seaborn_grids(gid, sel, where):
    built, fig = draw(gid, PAIRS, sel, legend=where)
    if where == "hide":
        assert not legends(fig)
    else:
        assert legends(fig), built.script


def test_pair_plot_axis_names_stay_inside_with_big_text():
    built, fig = draw("pairplot", PAIRS, {"cols": ["a", "b"]}, context="talk")
    assert "g.tight_layout()" in built.script
    assert cut_off(fig) == []


# --------------------------------------------------------------------------- regression line
def test_regression_equation_writes_a_minus_sign():
    # its own generator: the module's rng gave different data whenever another test drew from it first (and the
    # fitted intercept of y = 2x - 3 then printed as '- 2.98' about half the time); an intercept of -3.5 is 7
    # standard errors away from the edges of '- 3.x', so the check below no longer depends on the noise
    rng = np.random.default_rng(11)
    x = rng.uniform(0, 10, 200)
    df = pd.DataFrame({"x": x, "y": 2 * x - 3.5 + rng.normal(0, 0.5, 200)})
    built, fig = draw("regression", df, {"x": "x", "y": "y"}, {"equation": True})
    text = next(t.get_text() for t in plot_axes(fig)[0].texts if t.get_text().startswith("y ="))
    assert "+ -" not in text and re.search(r"·x - 3\.\d", text), text


# --------------------------------------------------------------------------- heatmaps
HEATMAPS = [
    ("corr", WIDE, {"cols": list(WIDE.columns)}, "notebook"),
    ("corr", LONG_NAMES, {"cols": list(LONG_NAMES.columns)}, "poster"),
    ("corr", BASIC, {"cols": list(BASIC.columns)}, "talk"),
    ("pivot", SALES, {"rows": "city", "cols": "product", "value": "sales"}, "notebook"),
    ("pivot", SALES, {"rows": "product", "cols": "city"}, "poster"),
    ("confusion", CLASSES, {"actual": "actual", "predicted": "predicted"}, "notebook"),
    ("confusion", ML, {"actual": "actual3", "predicted": "pred3"}, "poster"),
]


@pytest.mark.parametrize("gid, df, sel, context", HEATMAPS)
def test_heatmap_labels_and_cell_numbers_do_not_collide(gid, df, sel, context):
    built, fig = draw(gid, df, sel, context=context)
    ax = plot_axes(fig)[0]
    assert tick_collisions(fig, ax) == {"x": 0, "y": 0}, built.script
    assert cell_number_collisions(fig, ax) == 0
    assert {round(t.get_rotation()) for t in ax.get_yticklabels() if t.get_text()} == {0}, "row names read flat"
    assert cut_off(fig) == []


def test_huge_matrix_writes_every_second_name_and_says_so():
    df = pd.DataFrame(rng.normal(size=(80, 60)), columns=[f"pixel{i}" for i in range(60)])
    built, fig = draw("corr", df, {"cols": list(df.columns)}, context="poster")
    assert "xticklabels=2" in built.script
    assert any("every second one" in n for n in built.notes)
    assert tick_collisions(fig, plot_axes(fig)[0]) == {"x": 0, "y": 0}


def test_heatmap_grows_before_leaving_names_or_numbers_out():
    built, fig = draw("corr", WIDE, {"cols": list(WIDE.columns)}, context="poster")
    ax = plot_axes(fig)[0]
    assert "xticklabels" not in built.script
    assert len([t for t in ax.get_xticklabels() if t.get_text()]) == 20
    built, fig = draw("corr", BASIC, {"cols": list(BASIC.columns)}, context="poster")
    sizes = {t.get_fontsize() for t in plot_axes(fig)[0].texts if t.get_text()}
    assert sizes == {24.0}, f"cell numbers at the poster size, not shrunk: {sizes}"


def test_heat_fit_never_shrinks_the_figure_and_turns_long_names():
    fit = heat_fit(list("abcd"), list("abcd"), 6.2, 5.1, square=True)
    assert (fit.w, fit.h, fit.turn_x, fit.every_x) == (6.2, 5.1, False, 1)
    fit = heat_fit([f"measurement_{i:02d}" for i in range(12)], list("abcdefghijkl"), 9.5, 7.8, square=True)
    assert fit.turn_x and fit.w >= 9.5 and fit.h >= 7.8


# --------------------------------------------------------------------------- titles
@pytest.mark.parametrize("gid, df, sel", [
    ("pie", PAIRS, {"labels": "species"}),
    ("qq", PAIRS, {"cols": ["a"]}),
    ("roc", ML, {"actual": "y_true", "scores": ["p_good"]}),
    ("confusion", ML, {"actual": "y_true", "predicted": "pred_good"}),
    ("corr", BASIC, {"cols": ["x", "y", "y2", "y3"]}),
])
@pytest.mark.parametrize("context", ["talk", "poster"])
def test_long_titles_wrap_instead_of_running_off_the_figure(gid, df, sel, context):
    built, fig = draw(gid, df, sel, context=context, title=LONG_TITLE)
    assert cut_off(fig) == [], built.script
    shown = [" ".join(ax.get_title(loc=loc).split()) for ax in fig.axes for loc in ("left", "center")]
    assert LONG_TITLE in shown


def test_wrap_title_plain_and_f_string():
    assert wrap_title("short", 20) == "short"
    assert wrap_title(LONG_TITLE, 20).split("\n") == ["A longer title that", "a user typed for", "this chart"]
    raw = Raw("f'Confusion matrix · accuracy {accuracy:.1%}'")
    assert wrap_title(raw, 40) == raw
    assert wrap_title(raw, 20) == "f'Confusion matrix\\naccuracy {accuracy:.1%}'"


# --------------------------------------------------------------------------- contour image
def test_contour_image_cells_sit_on_the_grid_points_without_grid_lines():
    built, fig = draw("contour", GRID, {"x": "x", "y": "y", "z": "z"}, {"style": "image"})
    ax = plot_axes(fig)[0]
    mesh = [m for m in ax.collections if isinstance(m, QuadMesh)]
    assert mesh and "imshow" not in built.script
    corners = mesh[0].get_coordinates()
    centres = (corners[:-1, :-1] + corners[1:, 1:] + corners[:-1, 1:] + corners[1:, :-1]) / 4
    table = GRID.pivot_table(index="y", columns="x", values="z")
    X, Y = np.meshgrid(table.columns.to_numpy(float), table.index.to_numpy(float))
    assert np.allclose(centres[..., 0], X) and np.allclose(centres[..., 1], Y)
    assert np.allclose(np.ma.filled(mesh[0].get_array(), np.nan).ravel(), table.to_numpy().ravel())
    assert not any(line.get_visible() for line in ax.get_xgridlines() + ax.get_ygridlines())


# --------------------------------------------------------------------------- confusion classes
@pytest.mark.parametrize("predicted", ["p_good", "pred_good"])
def test_confusion_matrix_turns_yes_no_into_0_1_to_match_the_predictions(predicted):
    built, fig = draw("confusion", ML, {"actual": "answer", "predicted": predicted})
    assert "== 'yes').astype(int)" in built.script
    assert any("turned into 0/1" in n and "1 = yes" in n for n in built.notes)
    title = plot_axes(fig)[0].get_title(loc="left")
    accuracy = float(re.search(r"accuracy (\d+\.\d)%", " ".join(title.split())).group(1))
    expected = ((ML["answer"] == "yes").astype(int) == ((ML[predicted] >= 0.5).astype(int))).mean() * 100
    assert accuracy == pytest.approx(expected, abs=0.06)


def test_confusion_matrix_with_no_class_in_common_explains_instead_of_drawing():
    with pytest.raises(PlotError, match="no class in common"):
        draw("confusion", ML, {"actual": "c3", "predicted": "pred_good"})


# ------------------------------------------------------------------ 11.2: CSV text is never code
def test_csv_text_never_runs_as_code(tmp_path):
    """Review 11.2: a CSV value or header with a line break inside went into a '# 1 = <value>' comment of the
    plot code, so the text after the line break ran when the plot was drawn. Every graph type is drawn on the
    sample files with a payload after a line break in every header and every text value: nothing may run,
    neither in the app nor in the exported script."""
    import io
    import tokenize
    from pathlib import Path

    from plotstudio.data import load_csv
    from plotstudio.engine import make_plot
    from plotstudio.graphs import GRAPHS, suggest

    flag = tmp_path / "ran"
    payload = f"\n__import__('pathlib').Path({str(flag)!r}).touch()  #"
    samples = Path(__file__).resolve().parents[1] / "samples"
    sample_for = {"line": "training_log.csv", "area": "training_log.csv", "confusion": "model_predictions.csv",
                  "roc": "model_predictions.csv", "images": "digits_8x8.csv", "contour": "surface_xyz.csv",
                  "surface3d": "surface_xyz.csv", "scatter3d": "surface_xyz.csv"}
    hostile = {}
    for name in set(sample_for.values()) | {"airline_demo.csv"}:
        df = pd.read_csv(samples / name).head(400)
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]):          # text (object or pandas 3 str)
                df[c] = df[c].where(df[c].isna(), df[c].astype(str) + payload)
        df.columns = [f"{c}{payload}" for c in df.columns]
        path = tmp_path / name
        df.to_csv(path, index=False)
        hostile[name] = load_csv(path)
    drawn = 0
    for graph in GRAPHS:
        ds = hostile[sample_for.get(graph.id, "airline_demo.csv")]
        try:
            result = make_plot(graph, ds, suggest(graph, ds), {}, RowSettings(), StyleSettings(), LabelSettings())
        except PlotError:
            continue                                          # refused politely is fine; running text is not
        finally:
            plt.close("all")
        drawn += 1
        assert not flag.exists(), f"{graph.id}: text from the CSV ran while drawing"
        names = [t.string for t in tokenize.generate_tokens(io.StringIO(result.script).readline)
                 if t.type == tokenize.NAME]
        assert "__import__" not in names, f"{graph.id}: text from the CSV is code in the exported script"
    assert drawn >= 25, drawn


def test_exported_plot_script_imports_numpy_for_feature_lab_steps(tmp_path):
    """Review 8: the imports were chosen from the plot lines only, so after a Feature Lab step that uses np
    (log1p here) the exported script of a histogram lacked 'import numpy as np' and stopped with a NameError."""
    import os
    import subprocess
    import sys

    pytest.importorskip("tkinter")
    from plotstudio.core.pipeline import Pipeline, Step
    from plotstudio.data import load_csv
    from plotstudio.engine import make_plot
    from plotstudio.featurelab import make_working

    path = tmp_path / "data.csv"
    pd.DataFrame({"fare": rng.lognormal(3, 1, 200).round(2), "y": rng.integers(0, 2, 200)}).to_csv(path, index=False)
    base = load_csv(path)
    pipe = Pipeline()
    pipe.add(Step("log1p", ["fare"], "fare_log"), base.df)
    ds = make_working(base, pipe, pipe.transform(base.df))
    result = make_plot(GRAPH_BY_ID["hist"], ds, {"cols": ["fare_log"], "hue": None}, {}, RowSettings(),
                       StyleSettings(), LabelSettings())
    assert "import numpy as np" in result.script
    script = tmp_path / "plot.py"
    script.write_text(result.script, encoding="utf-8")
    run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=tmp_path, timeout=120,
                         env={**os.environ, "MPLBACKEND": "Agg"})
    assert run.returncode == 0, run.stderr[-600:]


def test_pie_of_zeros_and_correlations_of_constant_columns_explain_themselves():
    """Review 12.2: a pie whose amounts are all 0 stopped inside matplotlib (PlotRunError 'All wedge sizes are
    zero'), and 'Correlation with target' on features with one value drew an empty chart with a divide warning."""
    zeros = pd.DataFrame({"part": ["a", "b", "c"] * 10, "amount": [0.0] * 30})
    with pytest.raises(PlotError, match="adds up to 0"):
        draw("pie", zeros, {"labels": "part", "values": "amount"})
    flat = pd.DataFrame({"f1": [1.0] * 40, "f2": [5.0] * 40, "f3": np.arange(40.0), "y": [0, 1] * 20})
    with pytest.raises(PlotError, match="same value in every row"):
        draw("target_corr", flat, {"target": "y", "features": ["f1", "f2"]})
    built, fig = draw("target_corr", flat, {"target": "y", "features": ["f1", "f3"]})
    assert len(fig.axes[0].patches) == 1 and any("f1" in n for n in built.notes)   # f3 drawn, f1 left out
