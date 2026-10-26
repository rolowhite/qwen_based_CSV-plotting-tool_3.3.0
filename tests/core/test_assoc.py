"""plotstudio.core.assoc: link measures on a 0..1 scale (no scipy, no warnings)."""
import warnings

import numpy as np
import pandas as pd
import pytest

from plotstudio.core import assoc

rng = np.random.default_rng(2)


def test_eta_finds_real_groups_and_ignores_tiny_random_ones():
    codes = np.repeat(np.arange(3), 100)
    y = codes * 2.0 + rng.normal(size=300)
    assert assoc.eta(codes, 3, y)[0] > 0.8
    tiny = rng.integers(0, 250, 300)                            # ~1 row per group, like a ticket code
    assert assoc.eta(tiny, 250, rng.normal(size=300))[0] < 0.35


def test_eta_on_ranks_resists_one_huge_value():
    codes = np.repeat([0, 1], 100)
    y = np.r_[rng.normal(0, 1, 100), rng.normal(2, 1, 100)]
    y[0] = 1e6                                                  # one extreme value in group 0
    assert assoc.eta(codes, 2, y)[0] > 0.6


def test_cramers_v_extremes():
    a = np.repeat([0, 1, 2], 50)
    table, n = assoc.crosstab(a, 3, a, 3)
    assert n == 150 and assoc.cramers_v(table) == pytest.approx(1.0, abs=1e-6)
    b = rng.integers(0, 3, 150)
    assert assoc.cramers_v(assoc.crosstab(a, 3, b, 3)[0]) < 0.2


def test_determines_needs_enough_rows():
    a = np.repeat([0, 1], 50)
    assert assoc.determines(assoc.crosstab(a, 2, a, 2)[0]) == 1.0
    assert assoc.determines(np.array([[1, 0], [0, 1], [1, 0]])) == 0.0   # groups of 1 row decide nothing


def test_trend_sign_and_auc():
    t = np.arange(200.0)
    assert assoc.trend(t, t + rng.normal(size=200))[0] > 0.9
    assert assoc.trend(t, -t)[0] == pytest.approx(-1.0)
    pos = np.repeat([0, 1], 100)
    assert assoc.auc(pos, pos.astype(float)) == pytest.approx(1.0)


def test_number_matrices_and_dates_without_warnings():
    df = pd.DataFrame({"a": rng.normal(size=50), "b": np.ones(50), "c": [np.nan] * 25 + list(range(25))})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        pear, spear, counts = assoc.number_matrices(df)
        times = assoc.date_values(pd.Series(pd.date_range("2024-01-01", periods=5, tz="UTC")))
    assert np.isnan(pear.at["a", "b"]) and counts.at["a", "c"] == 25
    assert np.all(np.diff(times) == 86400)
