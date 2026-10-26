"""plotstudio.core.overrides: relabel columns (never their values) for the whole app."""
import numpy as np
import pandas as pd
import pytest

from plotstudio.core import overrides
from plotstudio.data import dataset_from_frame
from plotstudio.graphs import GRAPH_BY_ID, compatible

rng = np.random.default_rng(3)


@pytest.fixture
def ds():
    df = pd.DataFrame({"age": rng.normal(40, 10, 60).round(), "sex": rng.choice(["m", "f"], 60),
                       "flag": rng.choice([True, False], 60), "when": pd.date_range("2024-01-01", periods=60)})
    return dataset_from_frame(df, "fake.csv")


def group_slots(ds):
    role = next(r for r in GRAPH_BY_ID["box"].roles if r.key == "x")
    return compatible(role, ds)


def test_allowed_kinds(ds):
    assert overrides.allowed(ds, "age") == ["auto", "number", "category", "id", "skip"]
    assert overrides.allowed(ds, "flag") == ["auto", "category", "skip"]
    assert overrides.allowed(ds, "when") == ["auto", "date", "category", "skip"]
    assert "number" not in overrides.allowed(ds, "sex")          # would need converting values


def test_relabel_and_reset(ds):
    before = ds.df.copy()
    assert "age" not in group_slots(ds)
    active = overrides.apply(ds, {"age": "categorical", "sex": "auto"})
    assert active == {"age": "category"}
    assert "age" in group_slots(ds)
    assert ds.columns["age"].kind_label == "number used as groups · set by you"
    pd.testing.assert_frame_equal(ds.df, before)                 # values untouched
    assert overrides.apply(ds, {}) == {}
    assert "age" not in group_slots(ds) and not ds.columns["age"].relabelled


def test_refuses_value_changes(ds):
    with pytest.raises(ValueError, match="without changing its values"):
        overrides.apply(ds, {"sex": "number"})
    with pytest.raises(ValueError, match="not a column"):
        overrides.apply(ds, {"nope": "category"})
    with pytest.raises(ValueError, match="not a column kind"):
        overrides.normalise("colour")
