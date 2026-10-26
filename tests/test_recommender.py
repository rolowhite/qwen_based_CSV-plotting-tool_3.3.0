"""Checks for the plot recommender (plotstudio/core): every bug found in the first version of
plot_recommender.py has a small fake DataFrame here that reproduces it.

    python tests/test_recommender.py
"""
from __future__ import annotations

import subprocess
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
import pandas as pd  # noqa: E402

from plotstudio.data import RowSettings, load_csv  # noqa: E402
from plotstudio.core import assoc, recommend  # noqa: E402
from plotstudio.engine import LabelSettings, StyleSettings, build_plot, run_plot  # noqa: E402
from plotstudio.graphs import GRAPH_BY_ID, fits  # noqa: E402

SAMPLES = ROOT / "samples"
failures = []
rng = np.random.default_rng(7)


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL", msg)


def run(df, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # the recommender must not print warnings
        return recommend(df, **kw)


def texts(notes):
    return [str(n) for n in notes]


def test_no_scipy_needed():
    code = ("import sys; sys.modules['scipy'] = None; sys.path.insert(0, %r)\n"
            "import pandas as pd, numpy as np\n"
            "from plotstudio.eda import recommend\n"
            "df = pd.DataFrame({'a': np.arange(50.0), 'b': np.arange(50.0) ** 2, 'g': list('xy') * 25})\n"
            "p, s, n = recommend(df, target='b'); print(len(s))" % str(ROOT))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    check(out.returncode == 0, f"runs without scipy (old scipy had no .statistic): {out.stderr[-300:]}")
    print("ok   no scipy")


def test_text_dates():
    n = 120
    for dtype in (object, "string"):
        dates = pd.Series(pd.date_range("2024-01-01", periods=n).strftime("%Y-%m-%d"), dtype=dtype)
        df = pd.DataFrame({"day": dates, "sales": np.arange(n) * 3.0 + rng.normal(size=n) * 20})
        profiles, sugg, _ = run(df)
        check(profiles["day"].kind == "date", f"date strings ({dtype}) are dates, not IDs")
        check(any(s.graph == "line" and s.sel.get("x") == "day" for s in sugg), f"sales over time suggested ({dtype})")
    print("ok   text dates")


def test_strong_feature_is_not_leakage():
    n = 2000
    size = rng.lognormal(0, 0.6, n)
    df = pd.DataFrame({"carat": size, "price": 3000 * size ** 1.7 * rng.lognormal(0, 0.25, n),
                       "depth": rng.normal(60, 2, n)})
    df["copy"] = df["price"] * 1.2 + rng.normal(size=n)          # a real leak: the price with tax
    _, sugg, notes = run(df, target="price")
    leaks = [n_ for n_ in notes if n_.level == "leak"]
    check(len(leaks) == 1 and "'copy'" in leaks[0].text, f"only the copy is leakage: {texts(leaks)}")
    check(any(s.columns == ("carat", "price") for s in sugg), "the strongest real feature is still plotted")
    check(not any("carat" in n_.text and "almost equals" in n_.text for n_ in notes),
          "r 0.9 / rho 0.96 is strong, not 'almost equal'")
    print("ok   leakage vs strong feature")


def test_eta_with_many_small_groups():
    n = 400
    codes = rng.integers(0, 300, n)                  # ~1 row per group, like a ticket code
    y = rng.normal(size=n)
    raw = assoc._eta_sq(codes, 300, y)
    plain = 1 - ((y - pd.Series(y).groupby(codes).transform("mean")) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    e, _ = assoc.eta(codes, 300, y)
    check(plain > 0.5, f"(plain eta² of random groups is high: {plain:.2f})")
    check(e < 0.35 and raw < 0.12, f"bias-corrected eta stays low for random groups ({e:.2f})")
    table = np.bincount(codes * 2 + (y > 0), minlength=600).reshape(300, 2)
    check(assoc.cramers_v(table) < 0.35, "bias-corrected V stays low for random groups")
    check(assoc.determines(table) < 0.9, "groups with < 5 rows can't 'decide' anything")
    print("ok   eta / V bias")


def test_time_trend_is_a_plot_not_a_copy():
    n = 150
    df = pd.DataFrame({"t": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
                       "v": np.arange(n) + rng.normal(size=n)})
    _, sugg, notes = run(df)
    check(sugg and sugg[0].graph == "line", "a clean trend over time is the first plot")
    check(not any("same" in n_.text or "together" in n_.text for n_ in notes), "a trend is not a near-copy")
    print("ok   time trend")


def test_inf_values_and_names():
    n = 120
    df = pd.DataFrame(rng.normal(size=(n, 3)))
    df.iloc[:4, 0] = np.inf
    _, sugg, notes = run(df, target=1)
    check(all(np.isfinite(s.score) for s in sugg), "no NaN scores from inf values")
    check(any("infinite" in n_.text for n_ in notes), "inf values are reported")
    check(all(isinstance(c, str) for s in sugg for c in s.columns), "number column names become strings")
    [str(s) for s in sugg]
    dup = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    dup.columns = ["a", "a"]
    profiles, _, _ = run(dup)
    check(list(profiles) == ["a", "a (2)"], f"repeated headers get unique names: {list(profiles)}")
    print("ok   inf values and odd column names")


def test_overrides_and_target_checks():
    df = pd.DataFrame({"a": rng.normal(size=60), "g": rng.choice(list("xyz"), 60), "k": 1})
    for kind in ("category", "categorical", "cat"):
        profiles, _, _ = run(df, overrides={"a": kind})
        check(profiles["a"].kind == "category", f"override '{kind}' works")
    profiles, _, notes = run(df, overrides={"g": "numeric"})
    check(profiles["g"].kind == "empty" and any("could not be read as numbers" in n_.text for n_ in notes),
          "'numeric' on text: no crash, a note")
    for bad, msg in (({"overrides": {"g": "colour"}}, "not a kind"), ({"overrides": {"zz": "category"}}, "not a column"),
                     ({"target": "G "}, None), ({"target": "aa"}, "Did you mean 'a'")):
        try:
            run(df, **bad)
            ok = msg is None
        except ValueError as exc:
            ok = msg is not None and msg in str(exc)
        check(ok, f"input check {bad}")
    _, _, notes = run(df, target="k")
    check(notes and notes[0].level == "leak" and "only one value" in notes[0].text, "a constant target is reported")
    print("ok   overrides and target checks")


def test_target_rules():
    n = 300
    price = rng.permutation(np.arange(1000, 1000 + n)) * 7          # every value different: not an ID
    df = pd.DataFrame({"price": price.astype(float)})
    for i, r in enumerate((0.9, 0.7, 0.5, 0.3, 0.2, 0.15)):
        df[f"f{i}"] = r * (price - price.mean()) / price.std() + np.sqrt(1 - r * r) * rng.normal(size=n)
    df["other1"] = rng.normal(size=n)
    df["other2"] = df["other1"] + rng.normal(size=n) * 0.5
    _, sugg, _ = run(df, target="price")
    check(sugg[0].columns == ("price",), "the target is shown first even if every value is different")
    pairs = [s for s in sugg if s.kind == "target-pair"]
    check([s.columns[0] for s in pairs] == ["f0", "f1", "f2", "f3"], f"target links in strength order: "
          f"{[s.columns for s in pairs]}")
    uses = {}
    for s in sugg:
        if s.kind != "overview":
            for c in s.columns:
                uses[c] = uses.get(c, 0) + 1
    check(uses.get("price", 0) <= 5 and all(v <= 2 for c, v in uses.items() if c != "price"),
          f"column use limits: {uses}")
    check(all(s.reason and "baseline" not in s.reason for s in sugg), "no empty filler suggestions")
    print("ok   target rules")


def test_near_copies_shown_once():
    n = 400
    cls = rng.integers(1, 4, n)
    df = pd.DataFrame({"pclass": cls, "class": pd.Series(cls).map({1: "First", 2: "Second", 3: "Third"}),
                       "fare": 100.0 / cls + rng.normal(size=n), "survived": (rng.random(n) < 0.7 / cls).astype(int)})
    df["alive"] = df["survived"].map({0: "no", 1: "yes"})
    _, sugg, notes = run(df, target="survived")
    shown = {c for s in sugg for c in s.columns}
    check("class" not in shown and "pclass" in shown, f"one of two copies is plotted: {shown}")
    check("alive" not in shown, "the leaked column is not plotted")
    check(any("'class'" in n_.text and n_.level == "warn" for n_ in notes), "the copy is a note")
    check(notes[0].level == "leak" and "'alive'" in notes[0].text, "leakage is the first note")
    print("ok   near-copies")


def test_progress_and_speed():
    seen = []
    df = pd.DataFrame(rng.normal(size=(800, 120)), columns=[f"c{i}" for i in range(120)])
    df["y"] = rng.integers(0, 3, 800)
    t0 = time.perf_counter()
    run(df, target="y", progress=lambda f, text: seen.append(f))
    took = time.perf_counter() - t0
    check(took < 8, f"120 columns in {took:.1f} s")
    check(seen and seen[-1] == 1.0 and seen == sorted(seen), "progress goes up to 1")
    big = pd.DataFrame({"x": rng.normal(size=200_000), "g": rng.choice(list("abc"), 200_000)})
    big["y"] = big.x + rng.normal(size=200_000)
    profiles, _, notes = run(big, target="y")
    check(profiles["x"].rows == 50_000 and any("sample" in n_.text for n_ in notes), "big files use a sample")
    print(f"ok   progress and speed ({took:.2f} s for 120 columns)")


def test_curved_links_on_log_axes_are_scatters_not_straight_fits():
    """Review 4: two skewed numbers with a curved link were suggested as 'scatter + trend line (log)': a straight
    line fitted to the raw values, drawn on log axes, bent and fell out of the plot where it went below 0
    (y = 555.5x - 9321 with R² of the raw fit). On log axes the idea is now a scatter (the colour of a coloured
    scatter is kept)."""
    n = 600
    size = rng.lognormal(3, 1, n)
    price = 5 * size ** 1.8 * rng.lognormal(0, 1.2, n)
    df = pd.DataFrame({"size": size.round(2), "price": price.round(2), "other": rng.normal(size=n)})
    _, sugg, _ = run(df)
    idea = next(s for s in sugg if set(s.columns) == {"size", "price"})
    check(idea.graph == "scatter" and idea.logx and idea.logy and idea.plot == "scatter (log)",
          f"curved link on log axes: {idea.plot} / {idea.graph}")
    df["kind"] = rng.choice(["a", "b"], n)
    _, sugg, _ = run(df, target="kind")
    idea = next(s for s in sugg if set(s.columns) == {"size", "price"})
    check(idea.graph == "scatter" and idea.sel.get("color") == "kind", f"coloured scatter kept: {idea.sel}")
    g = GRAPH_BY_ID["regression"]
    sel = {r.key: None for r in g.roles}
    sel.update(x="size", y="price")
    from plotstudio.data import dataset_from_frame
    built = build_plot(g, dataset_from_frame(df, "c.csv"), sel, {o.key: o.default for o in g.options},
                       RowSettings(), StyleSettings(), LabelSettings(logx=True, logy=True))
    check(any("fitted to the raw values" in note for note in built.notes), "a fit drawn on log axes says so")
    print("ok   curved links on log axes")


def test_names_with_spaces_keep_their_ideas_and_column_types(tmp_path):
    """Review 7.1 / 7.3: the profiler strips spaces from names ("Age " -> "Age"). The Plot ideas came back with
    the stripped names, so the app (which keeps the file's names) dropped every idea that used them (1 of 3
    kept), and the app's own scan was not found for those columns (a Column types choice was ignored)."""
    pytest.importorskip("tkinter")
    from plotstudio.core import overrides
    from plotstudio.core.analyses import run as run_analysis
    from plotstudio.core.profiler import profile_frame
    from plotstudio.ideas import fits_app
    n = 400
    y = rng.integers(0, 2, n)
    path = tmp_path / "spaces.csv"
    pd.DataFrame({"Age ": rng.normal(30, 9, n).round(1) + 8 * y, " Fare": rng.lognormal(3, 1, n).round(2),
                  "Pclass ": rng.integers(1, 4, n), "Survived": y}).to_csv(path, index=False)
    ds = load_csv(path)
    res = run_analysis("plot_suggestions", ds.df, target="Survived", infos=ds.columns)
    check(res.suggestions and all(fits_app(s, ds.columns) for s in res.suggestions),
          f"every idea fits the app's columns ({[s.columns for s in res.suggestions]})")
    check({"Age ", " Fare"} <= {c for s in res.suggestions for c in s.columns}, "ideas use the file's names")
    overrides.apply(ds, {"Pclass ": "number"})
    kinds = profile_frame(ds.df, target="Survived", infos=ds.columns).profiles
    check(kinds["Pclass"].kind == "number", f"the scan's 'number' is used ({kinds['Pclass'].kind})")
    print("ok   names with spaces")


def test_skipped_columns_are_left_out_everywhere(tmp_path):
    """Review 7.2 / 7.4 / 7.5: 'skip' under Column types only set info.relabelled, so the column still filled
    plot slots, Suggest / Suggest all, the target list, the Feature Lab and the models (Evaluate, submissions)."""
    import copy
    from plotstudio import recommend as rec
    from plotstudio.core import overrides
    from plotstudio.core.feature_lab import suggest_features
    from plotstudio.graphs import compatible
    n = 300
    y = rng.integers(0, 2, n)
    path = tmp_path / "skip.csv"
    pd.DataFrame({"age": rng.normal(30, 9, n).round(1) + 9 * y, "fare": rng.lognormal(3, 1, n).round(2),
                  "kids": rng.integers(0, 4, n), "y": y}).to_csv(path, index=False)
    ds = load_csv(path)
    overrides.apply(ds, {"age": "skip"})
    for g in (GRAPH_BY_ID["hist"], GRAPH_BY_ID["scatter"], GRAPH_BY_ID["box"]):
        for role in g.roles:
            check("age" not in compatible(role, ds), f"{g.id}/{role.key}: no skipped column in the list")
            check("age" in compatible(role, ds, show_all=True) or role.accepts == "binary", "Show all still has it")
            check("age" not in [p.column for p in rec.rank(g, role, ds, {}, "y")], f"{g.id}/{role.key}: Suggest")
        sel, _ = rec.suggest_all(g, ds, "y")
        check("age" not in [c for v in sel.values() for c in (v if isinstance(v, list) else [v])],
              f"{g.id}: Suggest all ({sel})")
    check("age" not in rec.target_choices(ds), "not offered as the target")
    infos = {k: copy.copy(v) for k, v in ds.columns.items()}
    lab = suggest_features(ds.df, "y", infos=infos)
    check(not any("age" in s.sources for s in lab.suggestions + lab.encodings), "Feature Lab leaves it out")
    pytest.importorskip("sklearn")
    from plotstudio.core.evaluate import evaluate
    ev = evaluate(ds.df, "y", [], base_columns=list(ds.df.columns), infos=infos)
    check("age" not in ev.base_columns and ("age", "skipped") in ev.left_out, f"models leave it out ({ev.left_out})")
    print("ok   skipped columns")


def test_suggestions_draw_in_the_app():
    """Every suggestion for every sample file opens a real graph that draws without errors."""
    cases = [("airline_demo.csv", "satisfaction"), ("airline_demo.csv", None), ("store_sales.csv", "sales"),
             ("store_sales.csv", None), ("training_log.csv", None), ("digits_8x8.csv", "label"),
             ("model_predictions.csv", "y_true"), ("surface_xyz.csv", "z")]
    total = 0
    for name, target in cases:
        ds = load_csv(SAMPLES / name)
        _, sugg, _ = run(ds.df, target=target, infos=ds.columns)
        check(sugg, f"{name}: has suggestions")
        for s in sugg:
            g = GRAPH_BY_ID.get(s.graph)
            if g is None:
                check(False, f"{name}: unknown graph {s.graph}")
                continue
            roles = {r.key: r for r in g.roles}
            for key, value in s.sel.items():
                check(key in roles, f"{name}/{s.graph}: role {key}")
                for col in (value if isinstance(value, list) else [value]):
                    check(key in roles and fits(roles[key], ds.columns[col]), f"{name}/{s.graph}: {col} fits {key}")
            opts = {o.key: o.default for o in g.options}
            for key, value in s.opts.items():
                check(key in opts, f"{name}/{s.graph}: option {key}")
                opts[key] = value
            sel = {r.key: s.sel.get(r.key, [] if r.multi else None) for r in g.roles}
            labels = LabelSettings(logx=s.logx, logy=s.logy)
            built = build_plot(g, ds, sel, opts, RowSettings(), StyleSettings(), labels)
            fig, warns, _ = run_plot(built)
            plt.close(fig)
            total += 1
    print(f"ok   {total} suggestions draw in the app")


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILURE(S)'}")
    sys.exit(1 if failures else 0)
