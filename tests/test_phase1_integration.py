"""Phase 1 (Plot suggestions panel) on real data: seaborn's Titanic and tips.

Done when: on Titanic with target 'survived' the leakage warning for 'alive' comes first, and
every suggestion ("Plot it") draws a correct chart: the right graph, with its columns, not empty.
"""
import matplotlib.pyplot as plt
import pytest

from plotstudio.codegen import lit
from plotstudio.core import analyses, overrides
from plotstudio.data import RowSettings, dataset_from_frame
from plotstudio.engine import LabelSettings, StyleSettings, build_plot, run_plot
from plotstudio.graphs import GRAPH_BY_ID
from plotstudio.ideas import fits_app


def suggestions_for(df, name, target, type_overrides=None):
    ds = dataset_from_frame(df, name)
    active = overrides.apply(ds, type_overrides or {})
    res = analyses.run("plot_suggestions", ds.df, target=target, overrides=active, infos=ds.columns)
    return ds, res


def draw(ds, idea):
    """What the Plot it button does, without the window: the idea's graph, columns and options."""
    graph = GRAPH_BY_ID[idea.graph]
    sel = {r.key: idea.sel.get(r.key, [] if r.multi else None) for r in graph.roles}
    opts = {**{o.key: o.default for o in graph.options}, **idea.opts}
    built = build_plot(graph, ds, sel, opts, RowSettings(), StyleSettings(),
                       LabelSettings(logx=idea.logx, logy=idea.logy))
    fig, _, _ = run_plot(built)
    try:
        drawn = sum(len(ax.lines) + len(ax.patches) + len(ax.collections) + len(ax.images) for ax in fig.axes)
    finally:
        plt.close(fig)
    return built, drawn


def check_all_draw(ds, res):
    assert res.suggestions
    for idea in res.suggestions:
        assert fits_app(idea, ds.columns), f"{idea.title}: a column doesn't fit its slot"
        built, drawn = draw(ds, idea)
        assert drawn > 0, f"{idea.title}: empty chart"
        if idea.kind == "overview":
            continue          # whole-table plots may name their columns as a group (select_dtypes)
        for value in idea.sel.values():
            for col in (value if isinstance(value, list) else [value]):
                assert lit(col) in built.plot_code, f"{idea.title}: '{col}' is not in the plot code"


def test_titanic_leakage_first(titanic):
    _, res = suggestions_for(titanic, "titanic.csv", "survived")
    first = res.warnings[0]
    assert first.level == "leak" and "'alive'" in first.text and "survived" in first.text
    assert [w for w in res.warnings if w.level == "leak"] == [first]          # no other leakage alarm
    assert res.suggestions[0].columns == ("survived",)
    assert all("alive" not in s.columns for s in res.suggestions)


def test_titanic_known_issues_are_flagged(titanic):
    _, res = suggestions_for(titanic, "titanic.csv", "survived")
    text = " ".join(str(w) for w in res.warnings)
    assert "'deck': 77% missing" in text
    assert "'fare': right-skewed (4.8)" in text
    assert "'class'" in text and "'pclass'" in text                         # a near-copy pair


def test_titanic_every_plot_it_draws(titanic):
    ds, res = suggestions_for(titanic, "titanic.csv", "survived")
    check_all_draw(ds, res)


def test_tips_no_false_alarms(tips):
    ds, res = suggestions_for(tips, "tips.csv", "tip")
    assert not res.warnings_at("leak", "warn"), [str(w) for w in res.warnings]
    check_all_draw(ds, res)


@pytest.mark.parametrize("target", [None, "survived", "pclass", "fare"])
def test_titanic_other_targets_draw(titanic, target):
    ds, res = suggestions_for(titanic, "titanic.csv", target)
    check_all_draw(ds, res)


def test_type_override_runs_again_and_draws(titanic):
    ds, res = suggestions_for(titanic, "titanic.csv", "survived", {"pclass": "number", "age": "category"})
    assert res.overrides == {"pclass": "number", "age": "category"}
    assert res.profiles["pclass"].kind == "number" and res.profiles["age"].kind == "category"
    check_all_draw(ds, res)
