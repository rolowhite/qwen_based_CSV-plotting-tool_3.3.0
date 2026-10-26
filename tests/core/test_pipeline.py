"""The Pipeline: every op runs, learns on train only, undo / redo, and only runs its own code."""
import numpy as np
import pandas as pd
import pytest

from plotstudio.core.pipeline import OPS, Pipeline, PipelineError, Step, run_code


def table(n=60, seed=0):
    rng = np.random.default_rng(seed)
    names = [f"Last{i}, {t}. First" for i, t in enumerate(rng.choice(["Mr", "Mrs", "Miss", "Master", "Dr"], n,
                                                                       p=[.5, .2, .2, .08, .02]))]
    df = pd.DataFrame({
        "name": names, "a": rng.normal(10, 3, n), "b": rng.integers(0, 4, n).astype(float),
        "c": rng.choice(list("xyz"), n), "when": pd.date_range("2024-01-01", periods=n, freq="37h"),
        "y": rng.integers(0, 2, n), "code": [f"C{i % 7}" for i in range(n)]})
    df.loc[[1, 5], "a"] = np.nan
    df.loc[3, "c"] = None
    df.loc[4, "name"] = None
    df.loc[7, "when"] = pd.NaT
    return df


EVERY_OP = [
    Step("ratio", ["a", "b"], "a_per_b"),
    Step("diff", ["a", "b"], "a_minus_b"),
    Step("sum", ["a", "b"], "a_plus_b", {"offset": 1}),
    Step("bin", ["a"], "a_bin", {"k": 4}),
    Step("rare", ["c"], "c_grouped", {"min_share": 0.2}),
    Step("log1p", ["b"], "b_log"),
    Step("missing_flag", ["a"], "a_was_missing"),
    Step("dt_part", ["when"], "when_month", {"part": "month"}),
    Step("dt_part", ["when"], "when_weekend", {"part": "is_weekend"}),
    Step("dt_part", ["when"], "when_hour", {"part": "hour"}),
    Step("text_stat", ["name"], "name_len", {"stat": "length"}),
    Step("text_stat", ["name"], "name_words", {"stat": "words"}),
    Step("text_stat", ["code"], "code_digits", {"stat": "digits"}),
    Step("regex", ["name"], "title", {"pattern": r",\s*([^.]+)\.", "min_share": 0.05, "other": "Other"}),
    Step("onehot", ["c"], "c"),
    Step("ordinal", ["c"], "c_order", {"order": ["x", "y", "z"]}),
    Step("target_enc", ["code"], "code_te", {"target": "y", "positive": 1, "k": 5, "smoothing": 5}),
    Step("expr", ["a", "b"], "my", {"expr": "a / (b + 1)"}),
]


def test_every_op_is_covered():
    assert {s.op for s in EVERY_OP} == set(OPS)


@pytest.mark.parametrize("step", EVERY_OP, ids=lambda s: s.name)
def test_every_op_runs_and_adds_its_columns(step):
    df = table()
    pipe = Pipeline()
    fitted = pipe.add(step, df)
    out = pipe.transform(df)
    assert set(fitted.outputs) <= set(out.columns)
    assert list(out.columns[: len(df.columns)]) == list(df.columns)
    pd.testing.assert_frame_equal(out[df.columns], df)                 # the original columns are untouched
    for c in fitted.outputs:
        assert not np.isinf(pd.to_numeric(out[c], errors="coerce")).any(), c
    assert out.shape[0] == df.shape[0]


def test_divide_by_zero_and_gaps():
    df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 0.0], "b": [0.0, 2.0, 1.0, 0.0]})
    out = Pipeline([Pipeline.fit_step(Step("ratio", ["a", "b"], "r"), df)]).transform(df)
    assert out["r"].isna().tolist() == [True, False, True, True]      # 1/0 and 0/0 -> missing, not inf
    assert out["r"][1] == 1.0


def test_learned_values_come_from_train_only():
    rng = np.random.default_rng(1)
    train = pd.DataFrame({"x": rng.normal(0, 1, 500), "g": ["a"] * 300 + ["b"] * 195 + ["rare"] * 5,
                          "y": rng.integers(0, 2, 500)})
    test = pd.DataFrame({"x": rng.normal(5, 1, 200), "g": ["rare"] * 150 + ["new"] * 50, "y": 0})
    pipe = Pipeline()
    for step in (Step("bin", ["x"], "x_bin", {"k": 4}), Step("rare", ["g"], "g2", {"min_share": 0.05}),
                 Step("onehot", ["g"], "g"), Step("target_enc", ["g"], "g_te", {"target": "y", "positive": 1})):
        pipe.add(step, pipe.transform(train))
    out = pipe.transform(test, train=False)
    edges = pipe.steps[0].state["edges"]
    assert edges == sorted(edges) and max(edges) < 1.5                  # learned on train (around 0), not test
    assert (out["x_bin"] == 3).all()                                    # test values are all above train's edges
    assert set(out["g2"]) == {"Other"}                                  # 'rare' was rare in TRAIN
    assert "g_new" not in out.columns and out[["g_a", "g_b", "g_rare"]].sum().tolist() == [0, 0, 150]
    prior = pipe.steps[3].state["prior"]
    assert np.allclose(out.loc[test.g == "new", "g_te"], prior)        # unseen group -> the training mean
    assert out.loc[test.g == "rare", "g_te"].nunique() == 1


def test_target_encoding_never_sees_its_own_row():
    rng = np.random.default_rng(3)
    n = 2000
    df = pd.DataFrame({"g": rng.integers(0, 400, n).astype(str), "y": rng.permutation(np.r_[np.ones(n // 2),
                                                                                             np.zeros(n // 2)])})
    pipe = Pipeline()
    pipe.add(Step("target_enc", ["g"], "te", {"target": "y", "positive": 1, "smoothing": 1}), df)
    out = pipe.transform(df)
    naive = df.groupby("g")["y"].transform("mean")
    r_oof = abs(np.corrcoef(out["te"], df["y"])[0, 1])
    r_naive = abs(np.corrcoef(naive, df["y"])[0, 1])
    assert r_naive > 0.3 and r_oof < 0.1, (r_naive, r_oof)             # in-sample means leak, OOF doesn't


def test_undo_redo_remove_and_dependents():
    df = table()
    pipe = Pipeline()
    pipe.add(Step("sum", ["a", "b"], "s"), df)
    pipe.add(Step("ratio", ["a", "s"], "a_per_s"), pipe.transform(df))
    pipe.add(Step("log1p", ["b"], "b_log"), pipe.transform(df))
    assert pipe.dependents(0) == [1]
    removed = pipe.remove(0)
    assert [s.name for s in removed] == ["s", "a_per_s"] and [s.name for s in pipe] == ["b_log"]
    assert pipe.undo() and [s.name for s in pipe] == ["s", "a_per_s", "b_log"]
    assert pipe.redo() and [s.name for s in pipe] == ["b_log"]
    assert not pipe.redo()
    pipe.undo()
    pipe.rename(0, "family")
    assert pipe.steps[1].cols == ["a", "family"]
    out = pipe.transform(df)
    assert "family" in out.columns and "s" not in out.columns


def test_signature_tells_when_the_steps_are_the_same_again():
    """An evaluation stays valid after undo + redo (same steps), not after a real change."""
    df = table()
    pipe = Pipeline()
    pipe.add(Step("sum", ["a", "b"], "s"), df)
    before = pipe.signature
    pipe.add(Step("log1p", ["b"], "b_log"), pipe.transform(df))
    assert pipe.signature != before
    after = pipe.signature
    pipe.undo()
    assert pipe.signature == before
    pipe.redo()
    assert pipe.signature == after
    pipe.rename(1, "b_log2")
    assert pipe.signature != after


def test_name_clash_and_bad_steps():
    df = table()
    with pytest.raises(PipelineError, match="already exists"):
        Pipeline().add(Step("log1p", ["b"], "a"), df)
    with pytest.raises(PipelineError, match="not found"):
        Pipeline().add(Step("log1p", ["nope"], "z"), df)
    with pytest.raises(PipelineError, match="exactly one group"):
        Pipeline().add(Step("regex", ["name"], "t", {"pattern": "(a)(b)"}), df)
    with pytest.raises(PipelineError, match="Unknown step"):
        Step("rm -rf", ["a"], "x")


def test_round_trip_and_stored_code_is_checked_again():
    df = table()
    pipe = Pipeline()
    for step in EVERY_OP[:6]:
        pipe.add(step, pipe.transform(df))
    again = Pipeline.from_list(pipe.to_list())
    pd.testing.assert_frame_equal(again.transform(df), pipe.transform(df))
    bad = {"op": "expr", "cols": ["a"], "name": "x", "params": {"expr": "__import__('os')", "code": "1"}}
    with pytest.raises(ValueError):
        Step.from_dict(bad)


def test_step_code_runs_without_python_builtins():
    with pytest.raises(NameError):
        run_code(["df['x'] = __import__('os').getcwd()"], pd.DataFrame({"a": [1]}))
    with pytest.raises(NameError):
        run_code(["df['x'] = open('f')"], pd.DataFrame({"a": [1]}))


@pytest.mark.parametrize("formula", ['a == """x\nb.__class__\n#"""', "(a\n+ b)", "a +\r b", "a\x00 + b"])
def test_a_formula_is_one_line(formula):
    """Review 11.1: a line break inside a formula reached the '# formula' comment and became a line of code."""
    from plotstudio.core.feature_lab.safe_expr import ExprError, compile_expr
    with pytest.raises(ExprError, match="one line"):
        compile_expr(formula, ["a", "b"])
    pipe = Pipeline()
    with pytest.raises((PipelineError, ExprError)):                   # a saved pipeline is checked again
        pipe.add(Step("expr", ["a", "b"], "f", {"expr": formula}), pd.DataFrame({"a": [1.0], "b": [2.0]}))


def test_names_with_line_breaks_stay_inside_comments():
    """Review 11.1: column names (CSV headers) and labels go into the step comments; one with a line break must
    not add lines of code."""
    bad = "c\nx = 1/0  #"
    df = table().rename(columns={"c": bad})
    pipe = Pipeline()
    for step in [Step("missing_flag", [bad], "flag"), Step("onehot", [bad], "hot"),
                 Step("rare", [bad], "rare", {"min_share": 0.2, "other": "Other\nraise SystemExit"})]:
        pipe.add(step, pipe.transform(df) if len(pipe) else df)
    lines = pipe.code()
    assert all("\n" not in ln and "\r" not in ln for ln in lines)
    compile("\n".join(lines), "steps", "exec")
    out = pipe.transform(df)
    assert "flag" in out.columns and out["rare"].notna().any()


@pytest.mark.parametrize("new", ["family_size", "family size"])
def test_rename_keeps_the_formulas_built_on_the_column(new):
    """Review 9.1: a formula step kept the old name in its text and code, so transform() stopped with a
    KeyError and the saved pipeline could not be read back."""
    df = table()
    pipe = Pipeline()
    pipe.add(Step("sum", ["a", "b"], "s"), df)
    pipe.add(Step("expr", ["s", "b", "c"], "per", {"expr": "where(s > 10, s / b, 0) + (c == 's')"}),
             pipe.transform(df))
    before = pipe.transform(df)["per"]
    pipe.rename(0, new)
    assert pipe.steps[1].cols[0] == new and "'s'" in pipe.steps[1].params["expr"]    # text in quotes untouched
    out = pipe.transform(df)
    pd.testing.assert_series_equal(out["per"], before)
    again = Pipeline.from_list(pipe.to_list())
    pd.testing.assert_frame_equal(again.transform(df), out)


def test_rename_a_one_hot_step_points_later_steps_at_the_new_columns():
    """Review 9.1: renaming a step with several columns (one-hot) left later steps on the old column names."""
    df = table()
    pipe = Pipeline()
    pipe.add(Step("onehot", ["c"], "c"), df)
    first = pipe.steps[0].outputs[0]
    pipe.add(Step("ratio", [first, "b"], "per_b"), pipe.transform(df))
    pipe.rename(0, "group")
    assert pipe.steps[1].cols[0] == "group" + first[1:]
    assert "per_b" in pipe.transform(df).columns


def test_rename_refuses_names_that_are_taken_or_not_one_line():
    """Review 9.2: a new name could repeat another step's column or a column of the table (one of them was then
    silently overwritten), or hold a line break."""
    df = table()
    pipe = Pipeline()
    pipe.add(Step("sum", ["a", "b"], "s"), df)
    pipe.add(Step("log1p", ["a"], "a_log"), pipe.transform(df))
    with pytest.raises(PipelineError, match="already exists"):
        pipe.rename(1, "s")
    with pytest.raises(PipelineError, match="already exists"):
        pipe.rename(0, "a", taken=df.columns)
    with pytest.raises(PipelineError, match="one line"):
        pipe.rename(0, "s\nx")
    pipe.rename(0, "s")                                    # its own name is fine
    assert [s.name for s in pipe] == ["s", "a_log"]


def test_target_encoding_follows_a_target_made_by_a_step():
    """Review 9.3: the Target list offers the Lab's own columns (e.g. the log of a price), and target encoding
    then learns from that column. Renaming its step left the encoding on the old name, so transform() stopped
    with "Step 'city_te' needs the column(s) s"; removing the step left the encoding behind the same way."""
    rng = np.random.default_rng(0)
    n = 300
    df = pd.DataFrame({"city": rng.choice([f"c{i}" for i in range(12)], n), "b": rng.normal(size=n),
                       "c": rng.normal(size=n)})
    pipe = Pipeline()
    pipe.add(Step("sum", ["b", "c"], "s"), df)
    pipe.add(Step("target_enc", ["city"], "city_te", {"target": "s", "k": 5, "smoothing": 10, "seed": 0}),
             pipe.transform(df))
    pipe.rename(0, "total", taken=df.columns)
    assert pipe.steps[1].params["target"] == "total"
    assert {"total", "city_te"} <= set(pipe.transform(df).columns)
    again = Pipeline.from_list(pipe.to_list())
    pd.testing.assert_frame_equal(again.transform(df), pipe.transform(df))
    assert pipe.dependents(0) == [1]
    assert [s.name for s in pipe.remove(0)] == ["total", "city_te"] and len(pipe) == 0


def test_rename_column_in_a_formula():
    from plotstudio.core.feature_lab.safe_expr import rename_column
    assert rename_column("s / b + 1e5 + log(s)", "s", "t") == "t / b + 1e5 + log(t)"
    assert rename_column("`my col` * 2 + ss", "my col", "x") == "x * 2 + ss"
    assert rename_column("x + 1", "x", "my col") == "`my col` + 1"
    assert rename_column("x == 'x' and y == \"x\"", "x", "z") == "z == 'x' and y == \"x\""
    assert rename_column("x + 2", "x", "log") == "`log` + 2"                          # a function name: backticks
