"""Evaluate with model, and the exports: clean.py and the notebook rebuild the exact table; submissions."""
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from plotstudio.core import export  # noqa: E402
from plotstudio.core.evaluate import EvaluateError, evaluate  # noqa: E402
from plotstudio.core.pipeline import Pipeline, Step  # noqa: E402
from plotstudio.data import load_csv  # noqa: E402

rng = np.random.default_rng(21)


def test_a_helpful_feature_is_significant_for_the_linear_model():
    n = 1500
    a, b = rng.normal(size=n), rng.normal(size=n)
    df = pd.DataFrame({"a": a, "b": b, "y": (a * b > 0).astype(int)})          # same sign: not linear in a, b
    pipe = Pipeline()
    pipe.add(Step("expr", ["a", "b"], "ab", {"expr": "a * b"}), df)
    data = pipe.transform(df)
    ev = evaluate(data, "y", ["ab"], base_columns=["a", "b"])
    linear = next(s for s in ev.scores if s.model == "linear")
    assert ev.metric == "accuracy" and len(linear.before) == 5
    assert linear.before_mean < 0.65 and linear.after_mean > 0.9 and linear.significant
    assert "not significant" not in linear.text()
    noise = data.assign(noise=rng.normal(size=n))
    ev2 = evaluate(noise, "y", ["noise"], base_columns=["a", "b", "ab"])
    assert all(not s.significant for s in ev2.scores), [s.text() for s in ev2.scores]
    assert all("not significant" in s.text() for s in ev2.scores)


def test_regression_target_uses_r2():
    n = 600
    x = rng.uniform(1, 10, n)
    df = pd.DataFrame({"x": x, "y": np.log(x) * 10 + rng.normal(0, 0.5, n)})
    df["x_log"] = np.log(df["x"])
    ev = evaluate(df, "y", ["x_log"], base_columns=["x"])
    assert ev.metric == "R²" and ev.task == "number"
    linear = next(s for s in ev.scores if s.model == "linear")
    assert linear.after_mean > linear.before_mean


def test_evaluate_explains_what_is_missing():
    df = pd.DataFrame({"x": range(10), "y": [0, 1] * 5})
    with pytest.raises(EvaluateError, match="target"):
        evaluate(df, None, [])
    with pytest.raises(EvaluateError, match="too few"):
        evaluate(df.head(8), "y", [])


def every_op_table(path):
    n = 400
    when = pd.date_range("2023-03-01", periods=n, freq="9h").strftime("%Y-%m-%d %H:%M")
    df = pd.DataFrame({
        "id": np.arange(1, n + 1), "y": rng.integers(0, 2, n),
        "name": [f"Last{i}, {t}. First" for i, t in enumerate(rng.choice(["Mr", "Mrs", "Miss", "Rev"], n,
                                                                           p=[.5, .25, .245, .005]))],
        "a": rng.lognormal(2, 1, n).round(3), "b": rng.integers(0, 4, n), "c": rng.integers(0, 3, n),
        "city": rng.choice([f"town{i}" for i in range(15)], n), "size": rng.choice(["small", "medium", "large"], n),
        "when": when, "code": [f"X{i % 13}" if i % 5 else None for i in range(n)],
    })
    df.loc[rng.choice(n, 30, replace=False), "a"] = np.nan
    df.to_csv(path, index=False)
    return load_csv(path)


def build_every_op(ds):
    pipe = Pipeline()
    steps = [
        Step("regex", ["name"], "title", {"pattern": r",\s*([^.]+)\.", "min_share": 0.01, "other": "Other"}),
        Step("sum", ["b", "c"], "b_plus_c"), Step("ratio", ["a", "b_plus_c"], "a_per"), Step("diff", ["b", "c"], "b_c"),
        Step("bin", ["a"], "a_bin", {"k": 5}), Step("rare", ["city"], "city2", {"min_share": 0.07}),
        Step("log1p", ["a"], "a_log"), Step("missing_flag", ["code"], "code_missing"),
        Step("dt_part", ["when"], "when_hour", {"part": "hour"}), Step("dt_part", ["when"], "when_wknd",
                                                                       {"part": "is_weekend"}),
        Step("text_stat", ["code"], "code_digits", {"stat": "digits"}), Step("onehot", ["title"], "title"),
        Step("ordinal", ["size"], "size_n", {"order": ["small", "medium", "large"]}),
        Step("target_enc", ["city"], "city_te", {"target": "y", "positive": 1}),
        Step("expr", ["a", "b"], "mix", {"expr": "where(isna(a), -1, a) * (b > 1)"}),
    ]
    for step in steps:
        pipe.add(step, pipe.transform(ds.df))
    return pipe


def test_clean_py_and_notebook_rebuild_the_identical_table(tmp_path):
    ds = every_op_table(tmp_path / "train.csv")
    pipe = build_every_op(ds)
    app_table = pipe.transform(ds.df)
    code = export.clean_script(ds, pipe, "y")
    ns = {}
    exec(compile(code.replace('if __name__ == "__main__":', "if False:"), "clean.py", "exec"), ns)
    pd.testing.assert_frame_equal(ns["add_features"](ns["read"](str(tmp_path / "train.csv")), train=True), app_table)
    nb = export.notebook(ds, pipe, "y")
    nb_ns = {}
    exec(compile(export.notebook_code(nb), "notebook", "exec"), nb_ns)
    pd.testing.assert_frame_equal(nb_ns["df"], app_table)
    assert nb["nbformat"] == 4 and sum(c["cell_type"] == "code" for c in nb["cells"]) >= len(pipe) + 2
    script = tmp_path / "train_clean.py"
    script.write_text(code, encoding="utf-8")
    run = subprocess.run([sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-800:]
    written = pd.read_csv(tmp_path / "train_clean.csv")
    assert written.shape == app_table.shape and list(written.columns) == list(app_table.columns)


def test_new_data_is_changed_with_what_train_learned(tmp_path):
    ds = every_op_table(tmp_path / "train.csv")
    pipe = build_every_op(ds)
    test = ds.df.drop(columns=["y"]).sample(80, random_state=1)
    test.loc[test.index[:5], "city"] = "brand_new_town"
    out = pipe.transform(test, train=False)
    te = next(s for s in pipe if s.op == "target_enc")
    assert np.allclose(out.loc[test.index[:5], "city_te"], te.state["prior"])
    known = test.index[5:]
    assert np.allclose(out.loc[known, "city_te"], test.loc[known, "city"].map(te.state["map"]))
    code = export.clean_script(ds, pipe, "y")
    ns = {}
    exec(compile(code.replace('if __name__ == "__main__":', "if False:"), "clean.py", "exec"), ns)
    pd.testing.assert_frame_equal(ns["add_features"](test, train=False), out)


def test_submission(tmp_path):
    ds = every_op_table(tmp_path / "train.csv")
    pipe = build_every_op(ds)
    train = pipe.transform(ds.df)
    test = ds.df.drop(columns=["y"]).iloc[:120]
    assert export.guess_id_column(test, train.columns) == "id"
    for model in ("linear", "boosting"):
        sub = export.submission(train, test, pipe, "y", "id", base_columns=list(ds.df.columns), model=model)
        assert list(sub.columns) == ["id", "y"] and len(sub) == 120
        assert sub["id"].tolist() == test["id"].tolist() and set(sub["y"]) <= {0, 1}
        assert sub["y"].dtype.kind in "iu"


@pytest.mark.parametrize("name", ["bob's_data.csv", 'quote"""end.csv', "back\\slash.csv", "two\nlines.csv"])
def test_clean_py_compiles_whatever_the_file_is_called(tmp_path, name):
    """Review 11.3: a file name with an apostrophe made clean.py a SyntaxError (print('bob's_data_clean.csv:')),
    and quotes or backslashes in the name could end its docstring early or make an invalid escape."""
    import ast
    path = tmp_path / name
    pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "y": [0, 1, 0, 1]}).to_csv(path, index=False)
    ds = load_csv(path)
    pipe = Pipeline()
    pipe.add(Step("log1p", ["a"], "a_log"), ds.df)
    code = export.clean_script(ds, pipe, "y")
    tree = ast.parse(code)                                     # compiles
    kinds = [type(node).__name__ for node in tree.body]
    assert kinds[0] == "Expr" and set(kinds[1:]) <= {"Import", "FunctionDef", "If"}, kinds   # nothing extra runs
    ns = {}
    exec(compile(code.replace('if __name__ == "__main__":', "if False:"), "clean.py", "exec"), ns)
    pd.testing.assert_frame_equal(ns["add_features"](ns["read"](str(path)), train=True), pipe.transform(ds.df))


def test_linear_model_one_hot_encodes_bins_and_other_numeric_groups():
    """Review 3: bins (and numbers read as groups, like Pclass) reached the linear model as one number with one
    slope, so bins of a U-shaped x changed nothing (0.673 -> 0.673). They are one-hot encoded for the linear
    model now; trees keep them as numbers (their order)."""
    from plotstudio.core.evaluate import model_columns
    from plotstudio.core.profiler import profile_frame
    n = 2000
    x = rng.normal(size=n)
    df = pd.DataFrame({"x": x, "flag": (x > 0).astype(int), "y": (x ** 2 > 1).astype(int)})
    pipe = Pipeline()
    pipe.add(Step("bin", ["x"], "x_bin", {"k": 8}), df)
    data = pipe.transform(df)
    prof = profile_frame(data, target="y").profiles
    assert model_columns(data, ["x_bin", "flag"], prof, linear=True)[:2] == (["flag"], ["x_bin"])   # 0/1 stays
    assert model_columns(data, ["x_bin", "flag"], prof, linear=False)[:2] == (["x_bin", "flag"], [])
    result = evaluate(data, "y", ["x_bin"], base_columns=["x"])
    linear = next(s for s in result.scores if s.model == "linear")
    assert linear.before_mean < 0.7 and linear.after_mean > 0.9 and linear.significant, linear.text()


def test_submission_says_what_it_could_not_use_and_explains_failures():
    """Review 12.4: columns that only the training file has were dropped without a word; no usable column ended in
    sklearn's 'Found array with 0 feature(s)'; mixed class labels (1 and 'no') in 'Unknown label type'."""
    n = 200
    train = pd.DataFrame({"id": np.arange(n), "x": rng.normal(size=n), "extra": rng.normal(size=n),
                          "y": rng.integers(0, 2, n)})
    test = train.drop(columns=["y", "extra"]).head(20)
    sub = export.submission(train, test, Pipeline(), "y", "id")
    assert len(sub) == 20 and sub.attrs["left_out"] == ["extra"]
    only_text = pd.DataFrame({"id": np.arange(n), "name": [f"n{i}" for i in range(n)], "y": rng.integers(0, 2, n)})
    with pytest.raises(EvaluateError, match="No column a model can use"):
        export.submission(only_text, only_text.drop(columns=["y"]).head(5), Pipeline(), "y", "id")
    mixed = train.assign(y=pd.Series([1, "no"] * (n // 2), dtype=object))
    sub = export.submission(mixed, test, Pipeline(), "y", "id")
    assert set(sub["y"]) <= {"1", "no"}
