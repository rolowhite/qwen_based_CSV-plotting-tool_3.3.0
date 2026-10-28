"""The only place the Notebook computes numbers: a small calculator the solving models call as a tool.

evaluate("comb(10, 3) * 0.5**10") -> "15/128 ≈ 0.1171875". The expression is parsed with ast and walked against a
whitelist; nothing is ever run with eval or exec. Integers and fractions stay exact (3/4 is 3/4, not 0.75);
anything else is a float shown to 10 significant digits. Distribution values come from scipy.stats, so no
table look-ups:  dist('binom', 'pmf', 3, n=10, p=0.5),  dist('norm', 'cdf', 1.96),  dist('t', 'ppf', 0.975, df=14).
A refusal raises CalcError with a reason, which goes back to the model so it can fix its call.
"""
from __future__ import annotations

import ast
import math
import operator
import statistics
from fractions import Fraction
from numbers import Number

MAX_LENGTH = 500
MAX_EXPONENT = 10_000
MAX_INT_ARG = 10_000          # factorial, comb, perm
MAX_DIGITS = 1_000            # an exact result longer than this is refused

DISTRIBUTIONS = {"norm", "t", "chi2", "f", "binom", "poisson", "hypergeom", "geom", "nbinom", "expon", "gamma",
                 "uniform", "weibull_min", "beta", "lognorm", "studentized_range"}
DIST_FUNCTIONS = {"pdf", "pmf", "cdf", "sf", "ppf", "isf"}
DIST_PARAMS = {"loc", "scale", "df", "dfn", "dfd", "n", "p", "mu", "M", "N", "a", "b", "c", "s", "k"}
CONSTANTS = {"pi": math.pi, "e": math.e, "inf": math.inf}
MAX_MATRIX = 12              # rows and columns of a matrix the exact (fraction) routines take
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
          ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
COMPARE = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
           ast.Eq: operator.eq, ast.NotEq: operator.ne}


class CalcError(ValueError):
    """The expression isn't allowed or can't be computed; the message says why."""


def _int_arg(x, name):
    if isinstance(x, Fraction) and x.denominator == 1:
        x = int(x)
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if not isinstance(x, int) or isinstance(x, bool) or x < 0:
        raise CalcError(f"{name} needs whole numbers that are 0 or more")
    if x > MAX_INT_ARG:
        raise CalcError(f"{name} is limited to arguments up to {MAX_INT_ARG}")
    return x


def _real(x) -> float:
    return float(x)


def _log(x, base=None):
    if _real(x) <= 0 or (base is not None and (_real(base) <= 0 or _real(base) == 1)):
        raise CalcError("log needs a positive number (and a positive base other than 1)")
    return math.log(_real(x)) if base is None else math.log(_real(x), _real(base))


def _values(args):
    """mean(1, 2, 3) and mean([1, 2, 3]) both work."""
    values = list(args[0]) if len(args) == 1 and isinstance(args[0], (list, tuple)) else list(args)
    if not values:
        raise CalcError("give at least one value")
    # whole numbers as fractions, so statistics keeps the result exact (var(1, 2, 3, 4) is 5/3)
    return [Fraction(v) if isinstance(v, int) and not isinstance(v, bool) else v for v in values]


def _dist(name, fn, x, **params):
    if name not in DISTRIBUTIONS:
        raise CalcError(f"dist knows {', '.join(sorted(DISTRIBUTIONS))}")
    if fn not in DIST_FUNCTIONS:
        raise CalcError(f"dist's second argument is one of {', '.join(sorted(DIST_FUNCTIONS))}")
    unknown = set(params) - DIST_PARAMS
    if unknown:
        raise CalcError(f"unknown parameter(s) {', '.join(sorted(unknown))}; use scipy's names "
                        f"({', '.join(sorted(DIST_PARAMS))})")
    from scipy import stats
    method = getattr(getattr(stats, name), fn, None)
    if method is None:
        raise CalcError(f"{name} has no {fn} ({'pmf' if fn == 'pdf' else 'pdf'} instead?)")
    try:
        value = method(_real(x), **{k: _real(v) for k, v in params.items()})
    except TypeError as exc:
        raise CalcError(f"dist('{name}', '{fn}', ...) needs other parameters: {exc}") from exc
    value = float(value)
    if math.isnan(value):
        raise CalcError(f"dist('{name}', '{fn}', ...) is undefined for these values (check the parameters)")
    return value



def _matrix(m, name):
    """A matrix [[1, 2], [3, 4]] as rows of exact fractions."""
    if not (isinstance(m, list) and m and all(isinstance(r, list) and r and len(r) == len(m[0]) for r in m)):
        raise CalcError(f"{name} needs a matrix written like [[1, 2], [3, 4]] (rows of the same length)")
    if len(m) > MAX_MATRIX or len(m[0]) > MAX_MATRIX:
        raise CalcError(f"{name} is limited to {MAX_MATRIX} x {MAX_MATRIX}")
    return [[Fraction(repr(x)) if isinstance(x, float) else Fraction(x) for x in r] for r in m]


def _mul(a, b):
    if len(a[0]) != len(b):
        raise CalcError("matmul: the first matrix needs as many columns as the second has rows")
    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def _inverse(m):
    n = len(m)
    if len(m[0]) != n:
        raise CalcError("inv and det need a square matrix")
    a = [row[:] + [Fraction(int(i == j)) for j in range(n)] for i, row in enumerate(m)]
    for c in range(n):
        pivot = next((r for r in range(c, n) if a[r][c] != 0), None)
        if pivot is None:
            raise CalcError("the matrix is singular (it has no inverse)")
        a[c], a[pivot] = a[pivot], a[c]
        a[c] = [x / a[c][c] for x in a[c]]
        for r in range(n):
            if r != c and a[r][c] != 0:
                a[r] = [x - a[r][c] * y for x, y in zip(a[r], a[c])]
    return [row[n:] for row in a]


def _det(m):
    n = len(m)
    if len(m[0]) != n:
        raise CalcError("inv and det need a square matrix")
    a, det = [row[:] for row in m], Fraction(1)
    for c in range(n):
        pivot = next((r for r in range(c, n) if a[r][c] != 0), None)
        if pivot is None:
            return Fraction(0)
        if pivot != c:
            a[c], a[pivot], det = a[pivot], a[c], -det
        det *= a[c][c]
        for r in range(c + 1, n):
            a[r] = [x - a[r][c] / a[c][c] * y for x, y in zip(a[r], a[c])]
    return det


def _ols(x, y):
    """Least squares (X'X)^-1 X'y: X has a column of 1s when the line has an intercept. Exact."""
    x = _matrix(x, "ols")
    y = _matrix([[v] for v in y] if isinstance(y, list) and y and not isinstance(y[0], list) else y, "ols")
    if len(x) != len(y):
        raise CalcError("ols: X and y need the same number of rows")
    xt = [list(r) for r in zip(*x)]
    return [r[0] for r in _mul(_inverse(_mul(xt, x)), _mul(xt, y))]


def _integrate(expression, a, b):
    """The integral of an expression in x, e.g. integrate('3*x**-4', 1, inf), numerically (scipy.integrate.quad)."""
    if not isinstance(expression, str):
        raise CalcError("integrate(expression in x, lower, upper), for example integrate('2*x', 0, 1)")
    try:
        tree = ast.parse(expression.strip().replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise CalcError(f"not a valid expression ({exc.msg})") from exc
    from scipy import integrate

    value, _err = integrate.quad(lambda x: _real(_eval(tree, {"x": x})), _real(a), _real(b), limit=200)
    return value


def _stats():
    from scipy import stats
    return stats


def _ztable(z):
    """The area between 0 and z as a textbook's normal table prints it: z to 2 decimals, the area to 4."""
    return round(_stats().norm.cdf(round(_real(z), 2)) - 0.5, 4)


def _zcrit(p):
    """The z with area p to its left, as printed (zcrit(0.975) is 1.96; 1.645 for 0.95)."""
    p = _real(p)
    if not 0 < p < 1:
        raise CalcError("zcrit needs an area between 0 and 1")
    return 1.645 if abs(p - 0.95) < 1e-12 else round(_stats().norm.ppf(p), 2)


def _tcrit(tail, df):
    """The t critical value as a textbook's t table prints it (3 decimals) for upper-tail area `tail`."""
    tail = _real(tail)
    if not 0 < tail < 1 or _real(df) < 1:
        raise CalcError("tcrit(upper_tail_area, df) needs an area between 0 and 1 and df of at least 1")
    return round(_stats().t.ppf(1 - tail, _real(df)), 3)


def _corr(x, y):
    if not (isinstance(x, list) and isinstance(y, list)):
        raise CalcError("corr(x_values, y_values) needs two lists")
    return statistics.correlation([_real(v) for v in x], [_real(v) for v in y])


FUNCTIONS = {
    "det": lambda m: _det(_matrix(m, "det")),
    "inv": lambda m: _inverse(_matrix(m, "inv")),
    "matmul": lambda a, b: _mul(_matrix(a, "matmul"), _matrix(b, "matmul")),
    "transpose": lambda m: [list(r) for r in zip(*_matrix(m, "transpose"))],
    "ols": _ols,
    "corr": _corr,
    "integrate": _integrate,
    "ztable": _ztable,
    "zcrit": _zcrit,
    "tcrit": _tcrit,
    "comb": lambda n, k: math.comb(_int_arg(n, "comb"), _int_arg(k, "comb")),
    "perm": lambda n, k=None: math.perm(_int_arg(n, "perm"), None if k is None else _int_arg(k, "perm")),
    "factorial": lambda n: math.factorial(_int_arg(n, "factorial")),
    "sqrt": lambda x: math.sqrt(_real(x)),
    "exp": lambda x: math.exp(_real(x)),
    "log": _log,
    "ln": lambda x: _log(x),
    "sin": lambda x: math.sin(_real(x)),
    "cos": lambda x: math.cos(_real(x)),
    "tan": lambda x: math.tan(_real(x)),
    "abs": abs,
    "round": lambda x, n=0: round(_real(x), int(n)),
    "min": lambda *a: min(_values(a)),
    "max": lambda *a: max(_values(a)),
    "sum": lambda *a: sum(_values(a)),
    "mean": lambda *a: statistics.mean(_values(a)),
    "var": lambda *a: statistics.variance(_values(a)),         # sample (n - 1)
    "stdev": lambda *a: statistics.stdev(_values(a)),
    "pvar": lambda *a: statistics.pvariance(_values(a)),       # population (n)
    "pstdev": lambda *a: statistics.pstdev(_values(a)),
    "Fraction": lambda a, b=1: Fraction(a) / Fraction(b),
    "dist": _dist,
}
KEYWORDS = {"dist": DIST_PARAMS, "log": {"base"}, "round": {"n"}}


def _too_big(base, exponent) -> bool:
    if isinstance(base, (int, Fraction)) and isinstance(exponent, int) and abs(exponent) > 1:
        size = max(abs(base.numerator), abs(base.denominator)) if isinstance(base, Fraction) else abs(base)
        return size > 1 and abs(exponent) * math.log10(size) > MAX_DIGITS
    return False


def _eval(node, env=None):
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalcError("only numbers can be written directly")
        return node.value
    if isinstance(node, ast.Name):
        if env and node.id in env:
            return env[node.id]
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise CalcError(f"unknown name '{node.id}' (only pi and e, and the listed functions)")
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e, env) for e in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval(node.operand, env)
        return -value if isinstance(node.op, ast.USub) else +value
    if isinstance(node, ast.BinOp):
        left, right = _eval(node.left, env), _eval(node.right, env)
        if isinstance(node.op, ast.Pow):
            if abs(_real(right)) > MAX_EXPONENT or _too_big(left, right):
                raise CalcError("that power is too large")
            if isinstance(left, (int, Fraction)) and isinstance(right, int):
                return Fraction(left) ** right
            return _real(left) ** _real(right)
        if type(node.op) not in BINARY:
            raise CalcError("allowed operators: + - * / // % **")
        if isinstance(node.op, ast.Div) and isinstance(left, (int, Fraction)) and isinstance(right, (int, Fraction)):
            if right == 0:
                raise CalcError("division by zero")
            return Fraction(left) / Fraction(right)                 # 3/4 stays exactly 3/4
        return BINARY[type(node.op)](left, right)
    if isinstance(node, ast.Compare):
        values = [_eval(node.left, env)] + [_eval(c, env) for c in node.comparators]
        if any(type(op) not in COMPARE for op in node.ops):
            raise CalcError("allowed comparisons: < <= > >= == !=")
        return all(COMPARE[type(op)](a, b) for op, a, b in zip(node.ops, values, values[1:]))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
            hint = " Write dist('binom', 'pmf', 3, n=10, p=0.5) instead of binom.pmf(...)." \
                if isinstance(node.func, ast.Attribute) else ""
            raise CalcError(f"unknown function.{hint} Allowed: {', '.join(sorted(FUNCTIONS))}")
        name = node.func.id
        if env is not None and name == "integrate":
            raise CalcError("integrate can't be used inside integrate")
        args = node.args
        if name == "dist":                 # its first two arguments are names: 'binom' or binom, 'pmf' or pmf
            if len(args) != 3:
                raise CalcError("dist(name, fn, x, **params), for example dist('binom', 'pmf', 3, n=10, p=0.5)")
            labels = [a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else
                      a.id if isinstance(a, ast.Name) else None for a in args[:2]]
            if None in labels:
                raise CalcError("dist's first two arguments are names like 'binom' and 'pmf'")
            values = labels + [_eval(args[2], env)]
        elif name == "integrate" and args and isinstance(args[0], ast.Constant):      # its first argument is an expression
            values = [args[0].value] + [_eval(a, env) for a in args[1:]]
        else:
            values = [_eval(a, env) for a in args]
        allowed = KEYWORDS.get(name, set())
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None or kw.arg not in allowed:
                raise CalcError(f"{name} takes no keyword '{kw.arg}'" + (
                    f" (allowed: {', '.join(sorted(allowed))})" if allowed else ""))
            kwargs[kw.arg] = _eval(kw.value, env)
        try:
            return FUNCTIONS[name](*values, **kwargs)
        except CalcError:
            raise
        except (TypeError, ValueError, ZeroDivisionError, OverflowError, statistics.StatisticsError) as exc:
            raise CalcError(f"{name}: {exc}") from exc
    raise CalcError(f"'{type(node).__name__}' isn't allowed: only numbers, + - * / ** ( ) and the listed functions")


def show(value) -> str:
    """The result as text: exact where it is exact, with the decimal beside a fraction."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(show(v) for v in value) + "]"
    if isinstance(value, Fraction):
        if value.denominator == 1:
            value = value.numerator
        else:
            if len(str(value.numerator)) + len(str(value.denominator)) > MAX_DIGITS:
                raise CalcError("the exact result is too long")
            return f"{value} ≈ {float(value):.10g}"
    if isinstance(value, int):
        if len(str(abs(value))) > MAX_DIGITS:
            raise CalcError("the result has too many digits")
        return str(value)
    if isinstance(value, Number):
        if math.isnan(value) or math.isinf(value):
            raise CalcError("the result isn't a finite number")
        return f"{float(value):.10g}"
    raise CalcError("the result isn't a number")


def evaluate(expression: str) -> str:
    """The value of `expression` as text, or CalcError with the reason."""
    if not isinstance(expression, str) or not expression.strip():
        raise CalcError("give an expression, for example comb(10, 3) * 0.5**10")
    if len(expression) > MAX_LENGTH:
        raise CalcError(f"the expression is longer than {MAX_LENGTH} characters: split it into steps")
    text = expression.strip().replace("^", "**").replace("×", "*").replace("−", "-")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise CalcError(f"not a valid expression ({exc.msg})") from exc
    try:
        return show(_eval(tree))
    except RecursionError as exc:
        raise CalcError("the expression is nested too deeply") from exc
    except OverflowError as exc:
        raise CalcError("the result is too large") from exc
    except ZeroDivisionError as exc:
        raise CalcError("division by zero") from exc
    except TypeError as exc:            # e.g. -[1, 2] or [1] + 2: a list only goes into mean(), sum() ...
        raise CalcError(f"these values can't be combined that way ({exc})") from exc
