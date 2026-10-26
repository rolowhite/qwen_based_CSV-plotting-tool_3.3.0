"""Feature Lab end to end on Kaggle's Titanic (target Survived): suggestions, accepting title and family
size, Evaluate with model, clean.py / notebook rebuilding the identical table, and a Kaggle submission."""
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from plotstudio.core import export  # noqa: E402
from plotstudio.core.evaluate import evaluate  # noqa: E402
from plotstudio.core.feature_lab import suggest_features  # noqa: E402
from plotstudio.core.pipeline import Pipeline  # noqa: E402
from plotstudio.data import load_csv  # noqa: E402


@pytest.fixture
def split(kaggle_titanic, tmp_path):
    full = pd.read_csv(kaggle_titanic)
    train = full.sample(frac=0.8, random_state=1).sort_index()
    test = full.drop(train.index)
    train.to_csv(tmp_path / "train.csv", index=False)
    test.drop(columns=["Survived"]).to_csv(tmp_path / "test.csv", index=False)
    return load_csv(tmp_path / "train.csv"), load_csv(tmp_path / "test.csv"), test.set_index("PassengerId")["Survived"]


def test_titanic_feature_lab(split, tmp_path):
    ds, test_ds, truth = split
    pipe = Pipeline()
    lab = suggest_features(ds.df, "Survived", infos=ds.columns, pipeline=pipe)
    assert lab.task == "binary" and not lab.errors
    top = lab.suggestions[:8]
    title = next((s for s in top if s.name == "title"), None)
    family = next((s for s in top if s.step.op == "sum" and set(s.sources) == {"SibSp", "Parch"}), None)
    assert title is not None and family is not None, [s.name for s in top]
    assert title.rank == 1 and title.gain > 0.1 and family.gain > 0, (title.reason, family.reason)
    assert title.status == family.status == "recommended"
    assert "Mrs" in title.link

    work = ds.df
    pipe.add(title.step, work)
    work = pipe.transform(ds.df)
    pipe.add(family.step, work)
    pipe.rename(1, "family_size")
    work = pipe.transform(ds.df)
    assert work["title"].value_counts().index[:4].tolist() == ["Mr", "Miss", "Mrs", "Master"]
    assert set(work["title"].dropna()) == {"Mr", "Miss", "Mrs", "Master", "Other"}
    assert (work["family_size"] == ds.df["SibSp"] + ds.df["Parch"]).all()

    # Evaluate with model: both baselines score better with the two features (same 5 folds)
    ev = evaluate(work, "Survived", pipe.outputs, base_columns=list(ds.df.columns), infos=ds.columns)
    assert ev.new_columns == ["family_size", "title"] or set(ev.new_columns) == {"title", "family_size"}
    for score in ev.scores:
        assert score.after_mean > score.before_mean, score.text()
    assert {c for c, _ in ev.left_out} >= {"Name", "Ticket", "Cabin", "PassengerId"}

    # the exports rebuild the identical table
    code = export.clean_script(ds, pipe, "Survived")
    ns = {}
    exec(compile(code.replace('if __name__ == "__main__":', "if False:"), "clean.py", "exec"), ns)
    pd.testing.assert_frame_equal(ns["add_features"](ns["read"](str(tmp_path / "train.csv")), train=True), work)
    nb_ns = {}
    exec(compile(export.notebook_code(export.notebook(ds, pipe, "Survived", ev)), "nb", "exec"), nb_ns)
    pd.testing.assert_frame_equal(nb_ns["df"], work)

    # Kaggle submission: the steps applied to test with what they learned on train
    test = test_ds.df
    sub = export.submission(work, test, pipe, "Survived", "PassengerId", base_columns=list(ds.df.columns))
    assert list(sub.columns) == ["PassengerId", "Survived"] and len(sub) == len(test)
    assert sub["Survived"].isin([0, 1]).all()
    accuracy = float(np.mean(sub.set_index("PassengerId")["Survived"] == truth.loc[sub["PassengerId"]].to_numpy()))
    assert accuracy > 0.75, accuracy
    tested = pipe.transform(test, train=False)
    assert tested["title"].notna().all() and set(tested["title"]) <= {"Mr", "Miss", "Mrs", "Master", "Other"}
