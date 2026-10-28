"""Quick solutions for the problems beginners meet most: confidence intervals and tests of one or two means or
proportions. The model only COPIES the given numbers (a short JSON reply, seconds); Python does every step, with
the books' printed table values, and writes the solution in the books' notation. It is used only when

  * the problem asks for one thing (a lettered list of parts goes to the full solver),
  * the copied numbers all stand in the problem's own text (a number the model made up refuses the quick way),
  * the type is one of the six below.

Anything else returns None and the normal solver takes over. Like every fast answer it is re-checked later by
another solver in the background.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import calculator, lookup, ollama

TYPES = ("ci_mean", "ci_prop", "test_mean", "test_prop", "test_two_means", "test_paired")
NUMBERS = ("mean", "sd", "n", "confidence", "alpha", "mu0", "successes", "proportion", "p0",
           "mean1", "sd1", "n1", "mean2", "sd2", "n2")
CANDIDATE = re.compile(r"confidence|significance|hypothes|\bH_?[01]\b|null|interval estimate|interval for", re.I)
_PART = re.compile(r"\(([a-h])\)")
# more than the numbers is asked (a comment, an explanation), or the population is small (a finite-population
# correction): the full solver reads those
EXTRA = re.compile(r"\b(?:comment|explain|interpret|discuss|describe|why|compare)\b|\bthere are \d|population of \d|"
                   r"\bfinite\b|\bcorrection\b|\bsample size\b|\bType II\b|\bpower\b", re.I)
SCHEMA = {"type": "object", "required": ["type"], "properties": {
    "type": {"enum": list(TYPES) + ["other"]},
    **{name: {"type": ["number", "null"]} for name in NUMBERS},
    "sigma_known": {"type": ["boolean", "null"]},
    "equal_variances": {"type": ["boolean", "null"]},
    "tails": {"enum": ["two", "left", "right", None]},
    "differences": {"type": ["array", "null"], "items": {"type": "number"}},
}}
PROMPT = """Read this statistics problem and copy its numbers into JSON. Do not solve it. Use null for anything the
problem does not say. type is one of:
 ci_mean (confidence interval for one mean), ci_prop (for one proportion), test_mean (hypothesis test of one mean),
 test_prop (of one proportion), test_two_means (compare two independent means), test_paired (paired / before-after
 data), other (anything else, or more than one question).
Fields: mean, sd, n (the sample); sigma_known = true when the sd is the POPULATION standard deviation (sigma), false
for a sample standard deviation; confidence = the percentage, like 95; alpha = the significance level, like 0.05;
mu0 = the hypothesised mean; successes (a count) or proportion (p-hat, as written) with n; p0 = the hypothesised
proportion; mean1, sd1, n1 and mean2, sd2, n2 for two samples; equal_variances = true only if the problem says to
assume equal variances (or the same standard deviation); differences = the paired differences if listed;
tails = two (H1 has not-equal), right (H1 has greater than) or left (H1 has less than). For paired data given as a
mean and sd of differences use mean, sd, n. Copy numbers exactly as written."""


@dataclass
class Quick:
    kind: str
    markdown: str


def candidate(problem: str) -> bool:
    """Worth asking the model about: it talks of a confidence level, a hypothesis or a significance level, and asks
    for one thing."""
    return bool(CANDIDATE.search(problem)) and not EXTRA.search(problem) and len(set(_PART.findall(problem))) <= 1


def extract(backend, problem: str) -> Optional[dict]:
    """The model's copy of the givens, or None when it can't (or won't) say."""
    try:
        raw = backend.chat.text(backend.model, [{"role": "user", "content": f"{PROMPT}\n\nProblem:\n{problem}"}],
                                format=SCHEMA, think=backend.think,
                                options={"temperature": 0, "num_ctx": 4096, "num_predict": 500})
        data = json.loads(raw)
    except (ollama.OllamaError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("type") in TYPES else None


def grounded(values: dict, problem: str) -> bool:
    """Every number the model copied is a number of the problem (a percentage or a share may be written either way)."""
    seen = set()
    for token in lookup.numbers(problem):
        if not token.startswith("ex") and "/" not in token:
            seen.add(float(token))
    wanted = [v for k, v in values.items() if k in NUMBERS and v is not None]
    wanted += [d for d in values.get("differences") or []]
    return all(any(math.isclose(v, s, rel_tol=1e-9) or math.isclose(v * 100, s, rel_tol=1e-9)
                   or math.isclose(v / 100, s, rel_tol=1e-9) for s in seen) for v in wanted)


# ---------------------------------------------------------------------------------------------- numbers --
def _f(x: float) -> str:
    """4 decimals, trailing zeros dropped; tiny numbers keep 4 significant figures."""
    if x != 0 and abs(x) < 0.001:
        return f"{x:.4g}"
    return f"{x:.4f}".rstrip("0").rstrip(".") or "0"


def _p(x: float) -> str:
    return "less than 0.0001" if x < 0.0001 else _f(x)


def _stats():
    from scipy import stats
    return stats


def _z_crit(upper_tail: float) -> float:
    return calculator._zcrit(1 - upper_tail)


def _t_crit(upper_tail: float, df: float) -> float:
    return calculator._tcrit(upper_tail, df)


def _need(values: dict, *names) -> Optional[list]:
    got = [values.get(n) for n in names]
    return got if all(v is not None for v in got) else None


# ----------------------------------------------------------------------------------------------- solvers --
def ci_mean(v) -> Optional[Quick]:
    g = _need(v, "mean", "sd", "n", "confidence")
    if g is None or not 50 <= g[3] < 100 or g[2] < 2 or g[1] <= 0:
        return None
    mean, sd, n, conf = g[0], g[1], g[2], g[3]
    tail = (1 - conf / 100) / 2
    se = sd / math.sqrt(n)
    if v.get("sigma_known"):
        crit, name, how = _z_crit(tail), "z", "the normal table"
        method = r"Confidence interval for $\mu$ ($\sigma$ known): $\bar{X} \pm z\frac{\sigma}{\sqrt{n}}$."
        sym = r"\sigma"
    else:
        crit, name, how = _t_crit(tail, n - 1), "t", f"the $t$ table with $df = {int(n) - 1}$"
        method = r"Confidence interval for $\mu$ ($\sigma$ unknown): $\bar{X} \pm t\frac{s}{\sqrt{n}}$ with $df = n - 1$."
        sym = "s"
    margin = crit * se
    lo, hi = mean - margin, mean + margin
    return Quick("ci_mean", f"""**Given:** $\\bar{{X}} = {_f(mean)}$, ${sym} = {_f(sd)}$, $n = {_f(n)}$, ${_f(conf)}\\%$ confidence.

**Method:** {method}

The critical value from {how} is ${name} = {_f(crit)}$.

$$\\bar{{X}} \\pm {name}\\frac{{{sym}}}{{\\sqrt{{n}}}} = {_f(mean)} \\pm {_f(crit)}\\left(\\frac{{{_f(sd)}}}{{\\sqrt{{{_f(n)}}}}}\\right) = {_f(mean)} \\pm {_f(crit)}({_f(se)}) = {_f(mean)} \\pm {_f(margin)}.$$

**Answer:** the {_f(conf)}% confidence interval for $\\mu$ is **{_f(lo)} to {_f(hi)}**.""")


def ci_prop(v) -> Optional[Quick]:
    n, conf = v.get("n"), v.get("confidence")
    p = v.get("proportion") if v.get("successes") is None else v["successes"] / n if n else None
    if n is None or conf is None or p is None or n < 2 or not 50 <= conf < 100:
        return None
    p = p / 100 if p > 1 else p
    if not 0 < p < 1:
        return None
    tail = (1 - conf / 100) / 2
    z = _z_crit(tail)
    se = math.sqrt(p * (1 - p) / n)
    lo, hi = p - z * se, p + z * se
    return Quick("ci_prop", f"""**Given:** $p = {_f(p)}$, $n = {_f(n)}$, ${_f(conf)}\\%$ confidence.

**Method:** Confidence interval for a proportion: $p \\pm z\\sqrt{{\\frac{{p(1-p)}}{{n}}}}$.

The critical value from the normal table is $z = {_f(z)}$.

$$p \\pm z\\sqrt{{\\frac{{p(1-p)}}{{n}}}} = {_f(p)} \\pm {_f(z)}\\sqrt{{\\frac{{{_f(p)}(1-{_f(p)})}}{{{_f(n)}}}}} = {_f(p)} \\pm {_f(z)}({_f(se)}) = {_f(p)} \\pm {_f(z * se)}.$$

**Answer:** the {_f(conf)}% confidence interval for the proportion is **{_f(lo)} to {_f(hi)}**.""")


def _decision(stat: float, name: str, crit: float, tails: str, df: Optional[float], alpha: float):
    """(rule text, reject?, exact p-value) for a z or t statistic."""
    st = _stats()
    dist = st.norm if name == "z" else st.t(df)
    if tails == "two":
        reject, p = abs(stat) > crit, 2 * dist.sf(abs(stat))
        rule = f"reject $H_0$ if ${name} < -{_f(crit)}$ or ${name} > {_f(crit)}$"
    elif tails == "right":
        reject, p = stat > crit, dist.sf(stat)
        rule = f"reject $H_0$ if ${name} > {_f(crit)}$"
    else:
        reject, p = stat < -crit, dist.cdf(stat)
        rule = f"reject $H_0$ if ${name} < -{_f(crit)}$"
    return rule, reject, float(p)


def _test(kind, given, method, h0, h1, stat_line, stat, name, df, tails, alpha) -> Quick:
    tail = alpha / 2 if tails == "two" else alpha
    crit = _z_crit(tail) if name == "z" else _t_crit(tail, df)
    rule, reject, p = _decision(stat, name, crit, tails, df, alpha)
    exact = p
    if name == "z":             # the normal table's p-value: z to 2 decimals, the area to 4, as the book works it
        area = 0.5 - calculator._ztable(abs(stat))
        p = round(2 * area if tails == "two" else area if (stat > 0) == (tails == "right") else 1 - area, 4)
    shown_p = _p(p) if abs(p - exact) < 0.00005 else f"{_p(p)} (exact: {_p(exact)})"
    where = "the normal table" if name == "z" else f"the $t$ table with $df = {_f(df)}$"
    verdict = "reject" if reject else "do not reject"
    return Quick(kind, f"""**Given:** {given}.

**Method:** {method}

**Hypotheses:** {h0} and {h1}.

**Decision rule** (${_f(alpha)}$ level, {'two' if tails == 'two' else 'one'}-tailed, critical value from {where}): {rule}.

**Test statistic:**
$$ {stat_line} $$

**Decision:** ${name} = {_f(stat)}$, so {verdict} $H_0$. The $p$-value is {shown_p}.

**Answer:** ${name} = {_f(stat)}$; **{verdict} $H_0$** ($p$-value {shown_p}).""")


def _hyp(symbol: str, value, tails: str):
    rel = {"two": r"\neq", "right": ">", "left": "<"}[tails]
    return f"$H_0: {symbol} = {_f(value)}$", f"$H_1: {symbol} {rel} {_f(value)}$"


def test_mean(v) -> Optional[Quick]:
    g = _need(v, "mean", "mu0", "sd", "n", "alpha")
    tails = v.get("tails")
    if g is None or tails not in ("two", "left", "right") or not 0 < g[4] < 0.5 or g[3] < 2 or g[2] <= 0:
        return None
    mean, mu0, sd, n, alpha = g
    z_test = bool(v.get("sigma_known"))
    stat = (mean - mu0) / (sd / math.sqrt(n))
    sym = r"\sigma" if z_test else "s"
    name = "z" if z_test else "t"
    h0, h1 = _hyp(r"\mu", mu0, tails)
    return _test("test_mean", f"$\\bar{{X}} = {_f(mean)}$, $n = {_f(n)}$, ${sym} = {_f(sd)}$, $\\mu_0 = {_f(mu0)}$",
                 f"One-sample ${name}$-test for a mean (${sym}$ {'known' if z_test else 'unknown'}): "
                 f"${name} = \\frac{{\\bar{{X}} - \\mu_0}}{{{sym}/\\sqrt{{n}}}}$.", h0, h1,
                 f"{name} = \\frac{{{_f(mean)} - {_f(mu0)}}}{{{_f(sd)}/\\sqrt{{{_f(n)}}}}} = "
                 f"\\frac{{{_f(mean - mu0)}}}{{{_f(sd / math.sqrt(n))}}} = {_f(stat)}",
                 stat, name, None if z_test else n - 1, tails, alpha)


def test_prop(v) -> Optional[Quick]:
    n, p0, alpha, tails = v.get("n"), v.get("p0"), v.get("alpha"), v.get("tails")
    p = v.get("proportion") if v.get("successes") is None else v["successes"] / n if n else None
    if None in (n, p0, alpha, p) or tails not in ("two", "left", "right") or n < 2 or not 0 < alpha < 0.5:
        return None
    p, p0 = (p / 100 if p > 1 else p), (p0 / 100 if p0 > 1 else p0)
    if not (0 < p0 < 1 and 0 <= p <= 1):
        return None
    se = math.sqrt(p0 * (1 - p0) / n)
    stat = (p - p0) / se
    h0, h1 = _hyp(r"\pi", p0, tails)
    return _test("test_prop", f"$p = {_f(p)}$, $n = {_f(n)}$, $\\pi_0 = {_f(p0)}$",
                 r"One-sample $z$-test for a proportion: $z = \frac{p - \pi_0}{\sqrt{\pi_0(1-\pi_0)/n}}$.", h0, h1,
                 f"z = \\frac{{{_f(p)} - {_f(p0)}}}{{\\sqrt{{{_f(p0)}(1-{_f(p0)})/{_f(n)}}}}} = "
                 f"\\frac{{{_f(p - p0)}}}{{{_f(se)}}} = {_f(stat)}", stat, "z", None, tails, alpha)


def test_two_means(v) -> Optional[Quick]:
    g = _need(v, "mean1", "sd1", "n1", "mean2", "sd2", "n2", "alpha")
    tails = v.get("tails")
    equal = v.get("equal_variances")
    z_test = bool(v.get("sigma_known"))
    if g is None or tails not in ("two", "left", "right") or not 0 < g[6] < 0.5 or min(g[2], g[5]) < 2 or \
            (not z_test and equal is None):
        return None                 # whether to pool is the book's choice: if the problem doesn't say, the full solver
    m1, s1, n1, m2, s2, n2, alpha = g
    diff = m1 - m2
    h0, h1 = _hyp(r"\mu_1 - \mu_2", 0, tails)
    given = (f"$\\bar{{X}}_1 = {_f(m1)}$, $s_1 = {_f(s1)}$, $n_1 = {_f(n1)}$; $\\bar{{X}}_2 = {_f(m2)}$, "
             f"$s_2 = {_f(s2)}$, $n_2 = {_f(n2)}$")
    if z_test:
        se = math.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
        stat = diff / se
        return _test("test_two_means", given.replace("s_", r"\sigma_"),
                     r"Two-sample $z$-test (population standard deviations known): "
                     r"$z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}}$.", h0, h1,
                     f"z = \\frac{{{_f(diff)}}}{{\\sqrt{{{_f(s1)}^2/{_f(n1)} + {_f(s2)}^2/{_f(n2)}}}}} = "
                     f"\\frac{{{_f(diff)}}}{{{_f(se)}}} = {_f(stat)}", stat, "z", None, tails, alpha)
    if equal:
        df = n1 + n2 - 2
        sp2 = ((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / df
        se = math.sqrt(sp2 * (1 / n1 + 1 / n2))
        stat = diff / se
        return _test("test_two_means", given,
                     r"Pooled two-sample $t$-test: $s_p^2 = \frac{(n_1-1)s_1^2 + (n_2-1)s_2^2}{n_1+n_2-2}$ and "
                     r"$t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{s_p^2(1/n_1 + 1/n_2)}}$ with $df = n_1 + n_2 - 2$.",
                     h0, h1,
                     f"s_p^2 = {_f(sp2)},\\quad t = \\frac{{{_f(diff)}}}{{\\sqrt{{{_f(sp2)}(1/{_f(n1)} + 1/{_f(n2)})}}}} = "
                     f"\\frac{{{_f(diff)}}}{{{_f(se)}}} = {_f(stat)}", stat, "t", df, tails, alpha)
    a, b = s1 ** 2 / n1, s2 ** 2 / n2
    df = math.floor((a + b) ** 2 / (a ** 2 / (n1 - 1) + b ** 2 / (n2 - 1)))      # the book rounds Welch's df down
    se = math.sqrt(a + b)
    stat = diff / se
    return _test("test_two_means", given,
                 r"Two-sample $t$-test, unequal variances: $t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{s_1^2/n_1 + "
                 r"s_2^2/n_2}}$ with $df$ rounded down.", h0, h1,
                 f"t = \\frac{{{_f(diff)}}}{{\\sqrt{{{_f(s1)}^2/{_f(n1)} + {_f(s2)}^2/{_f(n2)}}}}} = "
                 f"\\frac{{{_f(diff)}}}{{{_f(se)}}} = {_f(stat)}", stat, "t", df, tails, alpha)


def test_paired(v) -> Optional[Quick]:
    tails, alpha = v.get("tails"), v.get("alpha")
    diffs = v.get("differences")
    if diffs and len(diffs) >= 2:
        n = len(diffs)
        dbar = sum(diffs) / n
        sd = math.sqrt(sum((d - dbar) ** 2 for d in diffs) / (n - 1))
    else:
        g = _need(v, "mean", "sd", "n")
        if g is None:
            return None
        dbar, sd, n = g
    if tails not in ("two", "left", "right") or alpha is None or not 0 < alpha < 0.5 or n < 2 or sd <= 0:
        return None
    se = sd / math.sqrt(n)
    stat = dbar / se
    h0, h1 = _hyp(r"\mu_d", 0, tails)
    return _test("test_paired", f"$\\bar{{d}} = {_f(dbar)}$, $s_d = {_f(sd)}$, $n = {_f(n)}$",
                 r"Paired $t$-test: $t = \frac{\bar{d}}{s_d/\sqrt{n}}$ with $df = n - 1$.", h0, h1,
                 f"t = \\frac{{{_f(dbar)}}}{{{_f(sd)}/\\sqrt{{{_f(n)}}}}} = \\frac{{{_f(dbar)}}}{{{_f(se)}}} = {_f(stat)}",
                 stat, "t", n - 1, tails, alpha)


SOLVERS: Dict[str, Callable] = {"ci_mean": ci_mean, "ci_prop": ci_prop, "test_mean": test_mean,
                                "test_prop": test_prop, "test_two_means": test_two_means, "test_paired": test_paired}


def compute(values: dict, problem: str) -> Optional[Quick]:
    """The worked solution for the copied givens, or None (unknown type, a missing number, a number not in the problem)."""
    solve = SOLVERS.get(values.get("type"))
    if solve is None or not grounded(values, problem):
        return None
    try:
        return solve(values)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError):
        return None


def solve(backend, problem: str) -> Optional[Quick]:
    """The whole quick way: ask the model for the givens, then compute. None sends the problem to the full solver."""
    if not candidate(problem):
        return None
    values = extract(backend, problem)
    return compute(values, problem) if values else None
