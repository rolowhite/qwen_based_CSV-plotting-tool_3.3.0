"""Feature Lab scoring: mutual information, out-of-fold target encoding, leakage and redundancy."""
import numpy as np
import pandas as pd
import pytest

from plotstudio.core.feature_lab import encoding, scoring, suggest_features
from plotstudio.core.feature_lab.base import FeatureSuggestion, LabContext
from plotstudio.core.pipeline import Pipeline, Step
from plotstudio.core.profiler import profile_frame

rng = np.random.default_rng(11)


def target(y, kind="category"):
    return scoring.target_info(pd.DataFrame({"y": y}), "y", kind)


def test_mutual_information_basics():
    n = 4000
    y = rng.integers(0, 2, n)
    t = target(y)
    independent = scoring.mutual_info(scoring.codes(pd.Series(rng.normal(size=n))), t.codes)
    copy = scoring.mutual_info(scoring.codes(pd.Series(y.astype(str))), t.codes)
    assert independent < 0.005
    assert copy == pytest.approx(np.log(2), abs=0.01)                # = H(y) for a fair coin


def test_mi_keeps_ids_and_unique_text_at_zero():
    n = 1000
    y = rng.integers(0, 2, n)
    ids = pd.Series([f"id{i}" for i in range(n)])
    assert scoring.mutual_info(scoring.codes(ids), target(y).codes) < 0.01    # cross-validated: nothing to learn
    assert scoring.column_mi(ids, target(y), "id") == 0.0


def test_out_of_fold_target_encoding_does_not_leak():
    """Shuffled labels: the encoding must carry ~0 information (an in-sample mean would not)."""
    n = 3000
    df = pd.DataFrame({"g": rng.integers(0, 600, n).astype(str), "y": rng.integers(0, 2, n)})
    df["y"] = rng.permutation(df["y"].to_numpy())
    pipe = Pipeline()
    pipe.add(Step("target_enc", ["g"], "te", {"target": "y", "positive": 1, "k": 5, "smoothing": 10}), df)
    out = pipe.transform(df)
    t = target(df["y"])
    mi_oof = scoring.mutual_info(scoring.codes(out["te"], "number"), t.codes)
    naive = df.groupby("g")["y"].transform("mean")                    # each row's own label is in its mean
    mi_naive = scoring.mutual_info(scoring.codes(naive, "number"), t.codes)
    assert mi_oof < 0.01, mi_oof
    assert mi_naive > 0.05, mi_naive                                   # the in-sample version looks informative


def test_leakage_is_flagged_and_blocks_accept():
    n = 800
    y = rng.integers(0, 2, n)
    df = pd.DataFrame({"y": y, "x": rng.normal(size=n), "a": rng.integers(0, 5, n), "b": rng.integers(0, 5, n)})
    df["copy"] = df["y"] * 3.0 + rng.normal(0, 0.01, n)               # made from the target
    lab = suggest_features(df, "y")
    leaks = [s for s in lab.suggestions if s.status == "leak"]
    assert leaks, [(s.name, s.leak_value) for s in lab.suggestions]
    assert all(not s.can_accept and "copy" in s.sources for s in leaks)
    assert leaks[0] is lab.suggestions[0]                              # shown first
    assert "Leakage?" in leaks[0].reason


def test_redundant_feature_is_not_recommended():
    n = 600
    x = rng.normal(size=n)
    df = pd.DataFrame({"x": x, "z": x * 2 + 1 + rng.normal(0, 0.01, n), "w": rng.normal(size=n)})
    df["y"] = (x + rng.normal(0, 0.5, n) > 0).astype(int)
    prof = profile_frame(df, target="y")
    ctx = LabContext(df=df, profiles=prof.profiles, target=scoring.target_info(df, "y", "category"),
                     pipeline=Pipeline(), taken=set(df.columns))
    s = FeatureSuggestion(step=Step("diff", ["w", "w"], "copy_of_x"), generator="test", title="t", sources=["w"])
    s.values = df["x"] * 3 - 2
    from plotstudio.core.feature_lab import score
    score(s, ctx)
    assert s.status == "redundant" and s.redundant_with in ("x", "z") and s.redundant_value > 0.95
    assert "Redundant" in s.reason


def test_encoding_helper_rules():
    n = 500
    df = pd.DataFrame({
        "y": rng.integers(0, 2, n),
        "few": rng.choice(list("abc"), n),                              # 3 groups -> one-hot
        "size": rng.choice(["small", "medium", "large"], n),            # a known order -> ordinal
        "many": rng.choice([f"city{i}" for i in range(25)], n),        # 25 groups -> target encoding
        "pclass": rng.integers(1, 4, n),                                # numbers already in order -> nothing
    })
    prof = profile_frame(df, target="y")
    ctx = LabContext(df=df, profiles=prof.profiles, target=scoring.target_info(df, "y", "category"),
                     pipeline=Pipeline(), taken=set(df.columns))
    ops = {s.sources[0]: s.step.op for s in encoding.suggest_encodings(ctx)}
    assert ops == {"few": "onehot", "size": "ordinal", "many": "target_enc"}
    te = next(s for s in encoding.suggest_encodings(ctx) if s.step.op == "target_enc")
    assert "out-of-fold" in te.warning and te.step.params["positive"] == 1
    order = next(s for s in encoding.suggest_encodings(ctx) if s.step.op == "ordinal").step.params["order"]
    assert order == ["small", "medium", "large"]


def test_big_tables_are_scored_on_a_sample_and_say_so():
    n = 60_000
    df = pd.DataFrame({"a": rng.integers(0, 5, n), "b": rng.integers(0, 5, n), "y": rng.integers(0, 2, n)})
    lab = suggest_features(df, "y")
    assert lab.rows_used == 50_000 and lab.total_rows == n
    assert any("50,000-row sample" in note for note in lab.notes)


def test_describe_link_in_words():
    y = np.r_[np.ones(60), np.zeros(140), np.ones(10), np.zeros(90)]
    x = pd.Series(["Mrs"] * 60 + ["Mrs"] * 0 + ["Mr"] * 140 + ["Miss"] * 10 + ["Miss"] * 90)
    text = scoring.describe_link(x, target(y), "title")
    assert text.startswith("y = 1 is most common for title = Mrs (100% vs 23% overall)")


def test_bins_of_a_column_with_telling_gaps_stay_same_information():
    """Review 2: bins keep the gaps as a group of their own, while the column's own score puts them in its
    median bin, so the bins of a column whose gaps tell the target scored higher than the column and were
    called 'Adds information'. A log or bins of one column can't tell more than the column (data-processing
    inequality): they stay neutral, and the 'was missing' flag is the feature that is recommended."""
    n = 3000
    y = rng.integers(0, 2, n)
    a = rng.normal(50, 10, n)                                  # unrelated to y ...
    a[rng.random(n) < np.where(y == 1, 0.45, 0.10)] = np.nan   # ... but a gap says y = 1 more often
    lab = suggest_features(pd.DataFrame({"a": a, "y": y}), "y")
    by_gen = {s.generator: s for s in lab.suggestions if s.sources == ["a"]}
    assert by_gen["binning"].status == "neutral" and "can't tell more" in by_gen["binning"].why
    assert by_gen["missing_flag"].status == "recommended"
    order = [s.generator for s in lab.suggestions]
    assert order.index("missing_flag") < order.index("binning")


def test_small_table_keeps_formula_context_when_target_has_two_classes():
    result = suggest_features(pd.DataFrame({"x": range(10), "y": [0, 1] * 5}), "y")
    assert result.context is not None
    assert any("too few values" in note for note in result.notes)
