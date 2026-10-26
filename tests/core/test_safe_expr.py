"""The formula box: allowed formulas become pandas code; anything else is refused, never run."""
import numpy as np
import pandas as pd
import pytest

from plotstudio.core.feature_lab.safe_expr import ExprError, compile_expr
from plotstudio.core.pipeline import run_code

COLS = ["Fare", "SibSp", "Parch", "Age", "Sex", "Flight Distance"]


def evaluate(text, df):
    code, used = compile_expr(text, df.columns)
    return run_code([f"df['out'] = {code}"], df)["out"], used


@pytest.mark.parametrize("text", [
    "__import__('os').system('echo hacked')",
    "__import__",
    "Fare.__class__",
    "Fare.mean()",
    "df['Fare']",
    "().__class__.__bases__",
    "open('/etc/passwd')",
    "eval('1+1')",
    "exec('x=1')",
    "getattr(Fare, 'values')",
    "lambda: Fare",
    "[c for c in Fare]",
    "Fare if Age else SibSp",
    "log(x=Fare)",
    "sum(Fare)",
    "Fare in [1, 2]",
    "Fare is None",
    "(x := Fare)",
    "f'{Fare}'",
    "Farre * 2",
    "1 + 2",
    "",
    "Fare **",
])
def test_rejected(text):
    with pytest.raises(ExprError):
        compile_expr(text, COLS)


def test_messages_say_what_to_do():
    with pytest.raises(ExprError, match="Did you mean 'Fare'"):
        compile_expr("Farre / 2", COLS)
    with pytest.raises(ExprError, match="Attribute access"):
        compile_expr("Fare.values", COLS)
    with pytest.raises(ExprError, match="not an allowed function"):
        compile_expr("print(Fare)", COLS)


def test_allowed_formulas_match_pandas():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"Fare": rng.lognormal(2, 1, 50), "SibSp": rng.integers(0, 3, 50),
                       "Parch": rng.integers(0, 3, 50), "Age": rng.normal(30, 10, 50),
                       "Sex": rng.choice(["male", "female"], 50), "Flight Distance": rng.normal(900, 100, 50)})
    df.loc[3, "Age"] = np.nan
    cases = {
        "Fare / (SibSp + Parch + 1)": df.Fare / (df.SibSp + df.Parch + 1),
        "log1p(Fare) * (Age < 18)": np.log1p(df.Fare) * (df.Age < 18),
        "where(isna(Age), 1, 0)": pd.Series(np.where(df.Age.isna(), 1, 0), index=df.index),
        "`Flight Distance` / 1000": df["Flight Distance"] / 1000,
        "Age < 18 and Sex == 'female'": (df.Age < 18) & (df.Sex == "female"),
        "not Age > 30": ~(df.Age > 30),
        "1 < Age < 18": (1 < df.Age) & (df.Age < 18),
        "-Fare ** 2": -df.Fare ** 2,
        "Fare - (SibSp - Parch)": df.Fare - (df.SibSp - df.Parch),
        "clip(Fare, 0, 100)": np.clip(df.Fare, 0, 100),
        "maximum(SibSp, Parch) + round(Fare, 1)": np.maximum(df.SibSp, df.Parch) + np.round(df.Fare, 1),
    }
    for text, want in cases.items():
        got, used = evaluate(text, df)
        pd.testing.assert_series_equal(got.reset_index(drop=True), pd.Series(want).reset_index(drop=True),
                                       check_names=False, check_dtype=False)
        assert used and all(c in df.columns for c in used)


def test_divide_by_zero_becomes_a_gap_in_the_step():
    from plotstudio.core.pipeline import Pipeline, Step
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [0.0, 1.0]})
    pipe = Pipeline()
    pipe.add(Step("expr", ["a", "b"], "r", {"expr": "a / b"}), df)
    assert pipe.transform(df)["r"].isna().tolist() == [True, False]


@pytest.mark.parametrize("formula, want", [
    ("not flag", [True, False, False, True]),
    ("~flag", [True, False, False, True]),
    ("flag and Age > 18", [False, True, False, False]),
    ("flag or w", [True, True, True, True]),
    ("not w", [False, True, True, False]),                 # a gap counts as 0 (False), so 'not' gives True
    ("w and Age > 18", [False, False, False, True]),
    ("not b", [False, True, False, True]),
    ("not (Age > 18)", [True, False, True, False]),
    ("2 * flag and Age > 18", [False, True, False, False]),   # 2 is True (bitwise 2 & True would be 0)
])
def test_not_and_or_are_logical_on_numbers(formula, want):
    """Review 10: not / and / or became ~ & |, which are bitwise on numbers (not of a 0/1 flag gave -1 / -2)
    and fail on floats with gaps (TypeError)."""
    df = pd.DataFrame({"flag": [0, 1, 1, 0], "b": [True, False, True, False], "w": [1.0, np.nan, 0.0, 1.0],
                       "Age": [10.0, 30.0, np.nan, 50.0]})
    got, _ = evaluate(formula, df)
    assert got.tolist() == want, (formula, got.tolist())
