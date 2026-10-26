"""Every Feature Lab generator on small fake tables: gaps, divide by zero, an empty column, one category."""
import numpy as np
import pandas as pd
import pytest

from plotstudio.core.feature_lab import GENERATORS, suggest_features
from plotstudio.core.feature_lab.base import LabContext
from plotstudio.core.feature_lab.scoring import target_info
from plotstudio.core.pipeline import Pipeline
from plotstudio.core.profiler import profile_frame


def awkward(n=300, seed=0):
    """A table with the usual trouble: gaps, zeros, an empty column, one category, text and dates."""
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    df = pd.DataFrame({
        "y": y,
        "amount": rng.lognormal(3, 1, n) * (1 + y),                      # skewed, no negatives
        "count_a": rng.integers(0, 4, n) + y,                           # small counts with zeros
        "count_b": rng.integers(0, 3, n),
        "zeros": np.where(rng.random(n) < 0.5, 0.0, rng.normal(5, 1, n)),  # half zeros: a divisor with zeros
        "negative": rng.normal(0, 5, n),
        "empty": np.nan,
        "one_group": "same",
        "group": rng.choice(["a", "b", "c", "d"] + [f"r{i}" for i in range(6)], n,
                            p=[.3, .3, .2, .14, .01, .01, .01, .01, .01, .01]),
        "name": [f"Smith{i}, {'Mrs' if (v == 1) == (rng.random() < 0.85) else 'Mr'}. John Paul"
                 for i, v in enumerate(y)],                                # the title tells y (85%)
        "code": [f"{c}{rng.integers(1, 99)}" if rng.random() > 0.3 else None for c in rng.choice(list("ABC"), n)],
        "when": pd.date_range("2023-01-01", periods=n, freq="13h"),
    })
    df.loc[rng.choice(n, 40, replace=False), "amount"] = np.nan
    df.loc[rng.choice(n, 20, replace=False), "name"] = None
    df.loc[rng.choice(n, 10, replace=False), "when"] = pd.NaT
    return df


def context(df, target="y"):
    prof = profile_frame(df, target=target)
    info = target_info(df, target, prof.profiles[target].kind)
    return LabContext(df=df, profiles=prof.profiles, target=info, pipeline=Pipeline(), taken=set(df.columns))


@pytest.mark.parametrize("gen", GENERATORS, ids=lambda g: g.NAME)
def test_generator_survives_awkward_tables(gen):
    df = awkward()
    ctx = context(df)
    found = gen.suggest(df, ctx.profiles, ctx.target, ctx)
    assert len(found) <= max(gen.CAP, 12)
    for s in found:
        assert s.generator == gen.NAME and s.step.name not in df.columns
        assert "empty" not in s.sources and "one_group" not in s.sources and "y" not in s.sources
        out = gen.apply(df, s.step)
        new = out[s.step.outputs[0]] if s.step.fitted else out.iloc[:, -1]
        assert len(new) == len(df)
        assert not np.isinf(pd.to_numeric(new, errors="coerce")).any()


def test_each_generator_finds_what_it_is_for():
    df = awkward()
    lab = suggest_features(df, "y")
    made = {(s.generator, tuple(s.sources)) for s in lab.suggestions}
    gens = {g for g, _ in made}
    assert ("regex_extract", ("name",)) in made                                 # title from name
    assert ("missing_flag", ("amount",)) in made or ("missing_flag", ("code",)) in made
    assert ("log_transform", ("amount",)) in made and ("log_transform", ("negative",)) not in made
    assert "rare_grouping" in gens and "datetime_parts" in gens and "text_stats" in gens
    assert not any("empty" in s.sources or "one_group" in s.sources for s in lab.suggestions)
    assert not lab.errors


def test_ratio_uses_the_divisor_without_zeros_and_gives_gaps_not_inf():
    rng = np.random.default_rng(5)
    n = 400
    size = rng.integers(1, 6, n)
    total = size * rng.normal(20, 2, n)
    df = pd.DataFrame({"total": total, "size": size, "y": (total / size > 20).astype(int),
                       "zeros": np.where(rng.random(n) < 0.4, 0, rng.normal(3, 1, n))})
    lab = suggest_features(df, "y")
    ratios = [s for s in lab.suggestions if s.generator == "numeric_ratio"]
    best = ratios[0]
    assert best.step.cols == ["total", "size"] and best.gain > 0.1, [(s.name, s.gain) for s in ratios]
    for s in ratios:
        assert not np.isinf(s.values).any()


def test_sum_group_finds_counts_that_belong_together():
    rng = np.random.default_rng(2)
    n = 900
    a, b = rng.integers(0, 4, n), rng.integers(0, 4, n)
    df = pd.DataFrame({"siblings": a, "parents": b, "age": rng.normal(30, 9, n),
                       "y": ((a + b >= 1) & (a + b <= 3)).astype(int)})
    lab = suggest_features(df, "y")
    sums = [s for s in lab.suggestions if s.generator == "sum_group"]
    assert sums and set(sums[0].sources) == {"siblings", "parents"} and sums[0].gain > 0.05
    assert all("age" not in s.sources for s in sums)                   # a measurement is not a count


def test_nothing_to_suggest_on_a_tiny_or_constant_table():
    df = pd.DataFrame({"y": [0, 1] * 15, "k": 1.0, "empty": np.nan})
    lab = suggest_features(df, "y")
    assert lab.suggestions == [] and not lab.errors


def test_no_target_no_scores():
    lab = suggest_features(awkward(), None)
    assert lab.suggestions == [] and "Pick the target" in lab.notes[0]


def test_suggestions_are_deterministic():
    df = awkward(seed=4)
    a = suggest_features(df, "y")
    b = suggest_features(df.copy(), "y")
    assert [(s.name, round(s.mi_after, 9), s.status) for s in a.suggestions] == \
        [(s.name, round(s.mi_after, 9), s.status) for s in b.suggestions]


def test_regression_target_and_dates():
    rng = np.random.default_rng(8)
    n = 600
    when = pd.date_range("2024-01-01", periods=n, freq="D")
    sales = 100 + 30 * (when.dayofweek >= 5) + rng.normal(0, 5, n)
    df = pd.DataFrame({"when": when, "sales": sales, "noise": rng.normal(size=n)})
    lab = suggest_features(df, "sales")
    assert lab.task == "regression"
    top = lab.suggestions[0]
    assert top.generator == "datetime_parts" and top.step.params["part"] in ("is_weekend", "weekday"), \
        [(s.name, s.gain) for s in lab.suggestions]
    assert "sales (mean) is highest for" in top.link


def test_pairs_of_numbers_that_are_often_zero():
    """Review 5: differences skipped every column that is 0 in more than half of the rows (its median is 0), so
    'arrival - departure delay' was never offered; and the ratio's divisor was chosen by the share of zeros
    among ALL rows, so gaps made a column look like it had fewer zeros than it has."""
    from plotstudio.core.feature_lab.generators.numeric_pairs import oriented
    rng = np.random.default_rng(0)
    n = 3000
    dep = np.where(rng.random(n) < 0.6, 0, rng.exponential(30, n)).round()
    arr = np.clip(dep + rng.normal(0, 15, n), 0, None).round()
    y = ((arr - dep) + rng.normal(0, 8, n) > 5).astype(int)          # the time lost in the air, with noise
    lab = suggest_features(pd.DataFrame({"dep": dep, "arr": arr, "y": y}), "y")
    diffs = [s for s in lab.suggestions if s.generator == "numeric_diff"]
    assert diffs and set(diffs[0].sources) == {"dep", "arr"} and diffs[0].status == "recommended"
    assert lab.suggestions[0].generator == "numeric_diff", [(s.name, round(s.gain, 3)) for s in lab.suggestions]
    a = np.where(rng.random(n) < 0.15, 0.0, rng.normal(50, 5, n))      # 15% of its values are 0 ...
    a[rng.random(n) < 0.5] = np.nan                                     # ... but half of its rows are gaps
    b = np.where(rng.random(n) < 0.08, 0.0, rng.normal(50, 5, n))      # 8% zeros
    df = pd.DataFrame({"a": a, "b": b, "y": rng.integers(0, 2, n)})
    assert oriented(context(df), "a", "b") == ("a", "b")                # divide by b, the one with fewer zeros


def test_patterns_raise_no_future_warnings():
    """Review 12.6: on pandas 2.2 (2.1 and 3.0 are quiet), found.replace(mapping) on a text column that the title
    pattern never matches (all gaps) warned 'Downcasting behavior in `replace` is deprecated' in every Feature
    Lab run on Titanic (Cabin, Ticket)."""
    import warnings
    rng = np.random.default_rng(0)
    n = 200
    y = rng.integers(0, 2, n)
    df = pd.DataFrame({"y": y, "name": [f"Smith{i}, {'Mrs' if v else 'Mr'}. Ann" for i, v in enumerate(y)],
                       "cabin": [f"C{i}" for i in range(n)]})                  # no ', Title.' in any value
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        lab = suggest_features(df, "y")
    titles = [s.step.cols for s in lab.suggestions if s.step.params.get("preset") == "title_from_name"]
    assert titles == [["name"]], lab.notes
