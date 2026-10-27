"""The solving models' calculator: exact where it can be, scipy for distributions, and nothing but arithmetic."""
import ast
import math
from pathlib import Path

import pytest

from plotstudio.core.notebook import calculator
from plotstudio.core.notebook.calculator import CalcError, evaluate


@pytest.mark.parametrize("expr, value", [
    ("comb(10, 3) * 0.5**10", "0.1171875"),
    ("comb(10, 3) / 2**10", "15/128 ≈ 0.1171875"),
    ("perm(5, 2)", "20"), ("factorial(6)", "720"),
    ("3/4 + 1/6", "11/12 ≈ 0.9166666667"), ("Fraction(2, 7) * 7", "2"),
    ("7/12 * 6/11", "7/22 ≈ 0.3181818182"),
    ("mean([2.1, 3.4, 2.8, 3.0, 2.6, 3.1])", "2.833333333"),
    ("var(1, 2, 3, 4)", "5/3 ≈ 1.666666667"), ("pvar([1, 2, 3, 4])", "5/4 ≈ 1.25"),
    ("stdev([2, 4, 4, 4, 5, 5, 7, 9])", "2.138089935"),
    ("sqrt(2)", "1.414213562"), ("log(8, 2)", "3"), ("ln(e)", "1"), ("exp(-1.6)", "0.201896518"),
    ("1 - exp(-8*0.2)", "0.798103482"), ("0.5^3", "0.125"), ("2^10", "1024"),
    ("round(0.123456, 3)", "0.123"), ("max(3, 9, 4) - min([3, 9, 4])", "6"), ("2 < 3 <= 3", "True"),
    ("-(1/2)", "-1/2 ≈ -0.5"), ("7 // 2 + 7 % 2", "4"),
])
def test_values(expr, value):
    assert evaluate(expr) == value


@pytest.mark.parametrize("call, scipy_call", [
    ("dist('norm', 'cdf', 1.96)", lambda s: s.norm.cdf(1.96)),
    ("dist('norm', 'ppf', 0.975, loc=10, scale=2)", lambda s: s.norm.ppf(0.975, loc=10, scale=2)),
    ("dist('t', 'ppf', 0.975, df=14)", lambda s: s.t.ppf(0.975, 14)),
    ("dist('chi2', 'sf', 3.84, df=1)", lambda s: s.chi2.sf(3.84, 1)),
    ("dist('f', 'isf', 0.05, dfn=3, dfd=10)", lambda s: s.f.isf(0.05, 3, 10)),
    ("dist(binom, pmf, 3, n=10, p=0.5)", lambda s: s.binom.pmf(3, 10, 0.5)),
    ("dist('poisson', 'cdf', 2, mu=4)", lambda s: s.poisson.cdf(2, 4)),
    ("dist('hypergeom', 'pmf', 1, M=52, n=4, N=5)", lambda s: s.hypergeom.pmf(1, 52, 4, 5)),
    ("dist('geom', 'pmf', 3, p=0.2)", lambda s: s.geom.pmf(3, 0.2)),
    ("dist('nbinom', 'pmf', 2, n=3, p=0.4)", lambda s: s.nbinom.pmf(2, 3, 0.4)),
    ("dist('expon', 'cdf', 0.2, scale=1/8)", lambda s: s.expon.cdf(0.2, scale=0.125)),
    ("dist('gamma', 'cdf', 2, a=3, scale=0.5)", lambda s: s.gamma.cdf(2, 3, scale=0.5)),
    ("dist('uniform', 'cdf', 0.3, loc=0, scale=2)", lambda s: s.uniform.cdf(0.3, 0, 2)),
])
def test_distributions_match_scipy(call, scipy_call):
    from scipy import stats
    assert float(evaluate(call)) == pytest.approx(float(scipy_call(stats)), rel=1e-9)


@pytest.mark.parametrize("expr, words", [
    ("__import__('os').system('dir')", "unknown function"),
    ("().__class__", "isn't allowed"),
    ("binom.pmf(3, 10, 0.5)", "instead of binom.pmf"),
    ("x + 1", "unknown name 'x'"),
    ("(lambda: 1)()", "unknown function"),
    ("[i for i in range(3)]", "isn't allowed"),
    ("'a' * 3", "only numbers"),
    ("10 ** 100000", "too large"),
    ("2 ** 4000", "too large"),
    ("factorial(20000)", "up to 10000"),
    ("comb(3.5, 2)", "whole numbers"),
    ("1 / 0", "division by zero"),
    ("dist('cauchy', 'pdf', 0)", "dist knows"),
    ("dist('binom', 'pdf', 3, n=10, p=0.5)", "pmf instead"),
    ("dist('norm', 'cdf', 1, sigma=2)", "no keyword 'sigma'"),
    ("sqrt(x=4)", "no keyword"),
    ("1 +", "not a valid expression"),
    ("1" + "+1" * 300, "longer than 500"),
    ("log(-1)", "positive"),
    ("-[1, 2]", "can't be combined"),
])
def test_refusals_say_why(expr, words):
    with pytest.raises(CalcError, match=words):
        evaluate(expr)


def test_the_module_never_evaluates_text():
    tree = ast.parse(Path(calculator.__file__).read_text(encoding="utf-8"))
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert not called & {"eval", "exec", "compile", "__import__"}


def test_results_are_exact_or_ten_digits():
    assert evaluate("1/3") == "1/3 ≈ 0.3333333333"
    assert evaluate("pi") == f"{math.pi:.10g}"
    assert evaluate("Fraction(1, 3) + 0.5") == "0.8333333333"           # a float makes it a float
