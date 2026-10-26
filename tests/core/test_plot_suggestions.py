"""plotstudio.core.analyses: the plugin registry and the plot_suggestions analysis."""
import numpy as np
import pandas as pd
import pytest

from plotstudio.core import analyses
from plotstudio.core.analyses.base import Result
from plotstudio.core.analyses.plot_suggestions import PlotSuggestions

rng = np.random.default_rng(4)


def frame(n=300):
    df = pd.DataFrame({"x": rng.normal(size=n), "g": rng.choice(list("abc"), n)})
    df["y"] = (df.x + rng.normal(size=n) * 0.5 > 0).astype(int)
    df["copy"] = df.y.map({0: "no", 1: "yes"})
    return df


def test_registry_and_result_type():
    assert "plot_suggestions" in analyses.ANALYSES
    res = analyses.run("plot_suggestions", frame(), target="Y")
    assert isinstance(res, PlotSuggestions) and isinstance(res, Result)
    assert res.target == "y" and res.total_rows == res.rows_used == 300 and res.sample_note == ""
    assert res.suggestions[0].columns == ("y",)
    assert [w.level for w in res.warnings][:1] == ["leak"] and "'copy'" in res.warnings[0].text
    assert res.warnings_at("leak") == res.warnings[:1]


def test_every_suggestion_has_its_numbers():
    res = analyses.run("plot_suggestions", frame(), target="y")
    for s in res.suggestions:
        assert s.reason and s.graph and s.sel
        assert s.stat, f"{s.title}: the number behind the reason is missing"
    for w in res.warnings:
        assert any(ch.isdigit() for ch in w.text), f"warning without a number: {w}"


def test_big_files_say_they_used_a_sample():
    df = pd.DataFrame({"x": rng.normal(size=60_000)})
    df["y"] = df.x * 2 + rng.normal(size=60_000)
    res = analyses.run("plot_suggestions", df, target="y")
    assert res.sampled and res.sample_note == "computed on a 50,000-row sample"


def test_overrides_are_reported():
    res = analyses.run("plot_suggestions", frame(), target="y", overrides={"x": "category"})
    assert res.overrides == {"x": "category"} and res.profiles["x"].kind == "category"


def test_unknown_analysis_and_bad_target():
    with pytest.raises(KeyError):
        analyses.run("nope", frame())
    with pytest.raises(ValueError, match="not a column"):
        analyses.run("plot_suggestions", frame(), target="zz")
