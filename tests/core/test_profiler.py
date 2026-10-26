"""plotstudio.core.profiler: column kinds and quality numbers, on small fake columns."""
import numpy as np
import pandas as pd
import pytest

from plotstudio.core.profiler import SAMPLE_ROWS, profile_column, profile_frame

rng = np.random.default_rng(1)


@pytest.mark.parametrize("values, kind", [
    (rng.normal(size=100), "number"),
    (rng.integers(1, 4, 100), "category"),                      # few numbers: groups (like pclass)
    (np.arange(100), "id"),                                     # a running number
    (rng.choice(list("abc"), 100), "category"),
    ([f"T-{i:05d}" for i in range(100)], "id"),                 # a code in every row
    ([f"a long free text comment number {i}" for i in range(100)], "text"),
    (np.ones(100), "constant"),
    ([np.nan] * 100, "empty"),
    (pd.date_range("2024-01-01", periods=100), "date"),
    (pd.date_range("2024-01-01", periods=100).strftime("%Y-%m-%d"), "date"),   # dates stored as text
    (["1,200", "3,400", "560"] * 34, "category"),               # numbers stored as text, 3 values
])
def test_kinds(values, kind):
    assert profile_column(pd.Series(values, name="c")).kind == kind


def test_number_stats_and_notes():
    s = pd.Series(np.r_[rng.lognormal(0, 1, 95), [np.nan] * 5], name="fare")
    p = profile_column(s)
    assert p.kind == "number" and p.skewed and p.skew > 1
    assert p.missing_pct == pytest.approx(0.05)
    assert any("missing" in n for n in p.notes) and any("skewed" in n for n in p.notes)
    assert p.minimum > 0 and p.positive


def test_overrides_original_api():
    s = pd.Series(rng.integers(1, 4, 50), name="pclass")
    assert profile_column(s, overrides={"pclass": "number"}).kind == "number"
    assert profile_column(s, overrides={"other": "number"}).kind == "category"   # only its own entry counts
    with pytest.raises(ValueError):
        profile_column(s, overrides={"pclass": "colour"})


def test_inf_counted_and_dropped():
    s = pd.Series(np.r_[rng.normal(size=40), [np.inf, -np.inf]], name="x")
    p = profile_column(s)
    assert p.infinite == 2 and np.isfinite(p.skew)


def test_frame_sampling_and_target():
    df = pd.DataFrame({"x": rng.normal(size=SAMPLE_ROWS + 10), "Y": rng.integers(0, 2, SAMPLE_ROWS + 10)})
    prof = profile_frame(df, target="y")
    assert prof.sampled and prof.total_rows == SAMPLE_ROWS + 10 and len(prof.df) == SAMPLE_ROWS
    assert prof.target == "Y" and prof.profiles["Y"].is_target


def test_target_never_skipped():
    df = pd.DataFrame({"price": rng.permutation(np.arange(100, 400)).astype(float)})
    prof = profile_frame(df, target="price")
    assert prof.profiles["price"].kind == "number"            # all different, but it is the target


def test_bad_target_names_the_closest_column():
    with pytest.raises(ValueError, match="Did you mean 'survived'"):
        profile_frame(pd.DataFrame({"survived": [0, 1] * 10}), target="survive")
