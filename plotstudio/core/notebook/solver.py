"""Live solving: a model works a problem out step by step and takes every number from the calculator.

Two backends share one loop: OllamaBackend (the local qwen model) and GeminiBackend (when the user added a key).
The model may call one tool, calculate(expression), which runs calculator.evaluate. When the solution's
**Answer:** line has a number that no calculate result (and not the problem) gives, the model is asked once to
compute it and correct that line; there is no second retry. agree() compares two solutions' final answers.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from . import calculator, lookup, ollama
from .gemini import Gemini, GeminiError

MAX_ROUNDS = 25
REL = 1e-3                  # numbers this close are the same answer (0.6496 vs 0.65 is, 0.6 vs 0.65 isn't)
OLLAMA_OPTIONS = {"temperature": 0, "num_ctx": 8192, "num_predict": 4096}     # a regression's steps are long
BUSY_WAIT = 3.0             # s before the one retry of an overloaded Gemini model in the middle of a solve
MAX_WAIT = 60.0             # s at most for a per-minute limit before that retry
BUSY_SKIP = 600.0           # s an overloaded Gemini model is skipped at the start of later solves

SYSTEM = """You are a statistics tutor writing a worked solution on a board.
- Start with **Given:** and the facts the problem gives (briefly).
- Name the method in one sentence, then show each step.
- Get EVERY number by calling the calculate tool. Never do arithmetic in your head and never write a number that
  calculate did not return or the problem did not give. Ask for all the values a step needs at once (several
  calculate calls in one reply), and compute whole expressions, not single fractions.
- calculate understands + - * / ** ( ), comb(n, k), perm(n, k), factorial(n), sqrt, exp, log(x, base), ln, abs,
  round, min, max, sum, mean, var, stdev (sample), pvar, pstdev (population), Fraction(a, b), and
  dist(name, fn, x, **params) with name in norm, t, chi2, f, binom, poisson, hypergeom, geom, nbinom, expon,
  gamma, uniform, weibull_min (c, scale), beta (a, b), lognorm (s, scale), studentized_range (k, df) and fn in
  pdf, pmf, cdf, sf, ppf, isf, using scipy's parameter names. hypergeom is dist('hypergeom', 'pmf', x, M=population,
  n=successes in the population, N=draws), not the book's N, k, n. For example
  dist('binom', 'pmf', 3, n=10, p=0.5), dist('norm', 'cdf', 1.96, loc=0, scale=1), dist('t', 'ppf', 0.975, df=14).
  Use dist for distribution values instead of printed tables.
- Write math as LaTeX in $...$ or $$...$$.
- End with one line that starts with **Answer:** and gives the final result of every part, in order."""

TOOL = {
    "name": "calculate",
    "description": "Evaluate an arithmetic or statistics expression exactly and return its value as text.",
    "parameters": {"type": "object", "required": ["expression"], "properties": {
        "expression": {"type": "string", "description": "for example comb(10, 3) * 0.5**10"}}},
}
FOLLOW_UP = ("Your **Answer:** line has {numbers}, which no calculate result gives. Compute {it} with the "
             "calculate tool, then write only the corrected line, starting with **Answer:**.")
RECHECK = ("Another solver's final answer was: {other}\nCheck your solution: recompute its key steps with the "
           "calculate tool. Then write the complete solution again (corrected if you found a mistake), ending "
           "with the **Answer:** line.")
# the **Answer:** paragraph; when the label stands alone ("**Answer:**" then a blank line) the next one too
_ANSWER = re.compile(r"\*\*Answer:?\*\*:?(?:[ \t]*\n\s*(?=\S))?[^\n]*(?:\n(?!\s*\n)[^\n]*)*", re.I)


class SolverError(RuntimeError):
    """The model didn't produce a solution (it stopped, looped, or the reply was empty)."""


@dataclass
class Solution:
    markdown: str
    model: str
    tool_log: List[dict] = field(default_factory=list)
    seconds: float = 0.0
    checked: bool = True        # every answer number came from calculate or the problem


def _expression(args) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return args
    if isinstance(args, dict):
        return str(args.get("expression", ""))
    return ""


# -------------------------------------------------------------------------------------------- backends --
class OllamaBackend:
    """The local model through Ollama (it needs the "tools" capability)."""

    def __init__(self, chat: "ollama.Chat", model: str, think: Optional[bool] = None):
        self.chat, self.model, self.think = chat, model, think
        self.messages: list = []

    def begin(self, system: str, text: str, image=None):
        self.messages = [{"role": "system", "content": system}, {"role": "user", "content": text}]

    def turn(self) -> Tuple[str, List[Tuple[Optional[str], str]]]:
        text, raw = "", []
        for chunk in self.chat.stream(self.model, self.messages, think=self.think, options=OLLAMA_OPTIONS,
                                      tools=[{"type": "function", "function": TOOL}]):
            message = chunk.get("message") or {}
            text += message.get("content") or ""
            raw += message.get("tool_calls") or []
        self.messages.append({"role": "assistant", "content": text, **({"tool_calls": raw} if raw else {})})
        return text, [(c.get("id"), _expression((c.get("function") or {}).get("arguments"))) for c in raw]

    def results(self, calls, outputs):
        for (call_id, _), out in zip(calls, outputs):
            self.messages.append({"role": "tool", "content": out, "tool_name": "calculate",
                                  **({"tool_call_id": call_id} if call_id else {})})

    def say(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def cancel(self):
        self.chat.cancel()


class GeminiBackend:
    """Google's Gemini (the user's own key). It gets the problem's text and, when there is one, the picture."""

    busy_until: dict = {}           # model -> time.time() until which it is skipped (overloaded, or out of quota)

    def __init__(self, client: Gemini, model: str, fallbacks=()):
        order = [model] + [m for m in fallbacks if m != model]
        ready = [m for m in order if GeminiBackend.busy_until.get(m, 0) < time.time()]
        self.client, self.model = client, (ready or order)[0]
        self.fallbacks = [m for m in (ready or order)[1:]]
        self.contents: list = []
        self.system: dict = {}

    def begin(self, system: str, text: str, image=None):
        self.system = {"parts": [{"text": system}]}
        parts = [{"text": text}]
        if image is not None:
            parts.append({"inlineData": {"mimeType": "image/png", "data": ollama.prepare_image(image)}})
        self.contents = [{"role": "user", "parts": parts}]

    def turn(self):
        body = {"contents": self.contents, "systemInstruction": self.system,
                "tools": [{"functionDeclarations": [TOOL]}], "generationConfig": {"temperature": 0}}
        retried = False
        while True:
            try:
                data = self.client.generate(self.model, body)
                break
            except GeminiError as exc:
                started = any(c.get("role") == "model" for c in self.contents)
                if exc.kind in ("busy", "quota"):          # skip it in later solves: a while, or until the reset
                    skip = exc.retry_after if exc.kind == "quota" and exc.retry_after else BUSY_SKIP
                    GeminiBackend.busy_until[self.model] = time.time() + skip
                if exc.kind in ("model", "busy", "rate", "quota") and self.fallbacks and not started:
                    self.model = self.fallbacks.pop(0)       # retired, overloaded or out of quota: the next free one
                elif exc.kind in ("busy", "rate") and not retried:
                    retried = True                           # mid-solve its thought signatures tie it to this model
                    end = time.time() + min(exc.retry_after or BUSY_WAIT, MAX_WAIT)
                    while time.time() < end and not self.client.cancelled:      # Stop and the budget still work
                        time.sleep(0.2)
                else:
                    raise
        candidates = data.get("candidates") or []
        if not candidates:
            raise SolverError(f"Gemini gave no answer ({(data.get('promptFeedback') or {}).get('blockReason', '')})")
        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        self.contents.append({**content, "role": "model", "parts": parts})     # as received: keeps thought signatures
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
        calls = [((p["functionCall"] or {}).get("id"), _expression((p["functionCall"] or {}).get("args")))
                 for p in parts if isinstance(p, dict) and "functionCall" in p]
        finish = candidates[0].get("finishReason")
        if not calls and finish not in (None, "STOP"):
            raise SolverError(f"Gemini stopped early ({finish}).")
        return text, calls

    def results(self, calls, outputs):
        self.contents.append({"role": "user", "parts": [
            {"functionResponse": {"name": "calculate", "response": {"result": out}, **({"id": cid} if cid else {})}}
            for (cid, _), out in zip(calls, outputs)]})

    def say(self, text: str):
        self.contents.append({"role": "user", "parts": [{"text": text}]})

    def cancel(self):
        self.client.cancel()


# ------------------------------------------------------------------------------------------------ loop --
def _rounds(backend, texts: List[str], log: List[dict], cancelled: Callable[[], bool]):
    for _ in range(MAX_ROUNDS):
        if cancelled():
            raise ollama.Cancelled()
        text, calls = backend.turn()
        if text.strip():
            texts.append(text.strip())
        if not calls:
            return
        outputs = []
        for _, expression in calls:
            try:
                out = calculator.evaluate(expression)
            except calculator.CalcError as exc:
                out = f"error: {exc}"
            log.append({"expression": expression, "result": out})
            outputs.append(out)
        backend.results(calls, outputs)
    raise SolverError(f"The solver stopped after {MAX_ROUNDS} calculator rounds without finishing.")


def answer_text(markdown: str) -> str:
    """The last **Answer:** paragraph ('' when there is none)."""
    found = _ANSWER.findall(markdown)
    return found[-1] if found else ""


def _floats(text: str) -> List[Tuple[str, float]]:
    out = []
    for token in lookup.numbers(text):
        if token.startswith("ex") or "/" in token:          # exercise mentions; a fraction also comes as a decimal
            continue
        out.append((token, float(token)))
    return out


def _close(a: float, b: float) -> bool:
    return a == b or abs(a - b) <= REL * max(abs(a), abs(b)) or abs(a * 100 - b) <= REL * abs(b) or \
        abs(a - b * 100) <= REL * abs(a)                     # 11.72% is 0.1172


def result_numbers(markdown: str, problem: str) -> List[Tuple[str, float]]:
    """The answer's numbers that aren't simply copied from the problem."""
    given = {v for _, v in _floats(problem)}
    return [(t, v) for t, v in _floats(answer_text(markdown)) if v not in given]


def unchecked(markdown: str, problem: str, log: List[dict]) -> List[str]:
    """The answer's numbers that no calculate result gives."""
    known = [v for entry in log for _, v in _floats(entry["result"]) if not entry["result"].startswith("error")]
    return [t for t, v in result_numbers(markdown, problem) if not any(_close(v, k) for k in known)]


def agree(a: str, b: str, problem: str) -> Optional[bool]:
    """Do two solutions end with the same results? None when one of them has no result numbers to compare."""
    xs, ys = [v for _, v in result_numbers(a, problem)], [v for _, v in result_numbers(b, problem)]
    if not xs or not ys:
        return None
    return all(any(_close(x, y) for y in ys) for x in xs) and all(any(_close(y, x) for x in xs) for y in ys)


def _replace_answer(markdown: str, line: str) -> str:
    found = list(_ANSWER.finditer(markdown))
    if not found:
        return markdown.rstrip() + "\n\n" + line
    m = found[-1]
    return markdown[:m.start()] + line + markdown[m.end():]


_PART = re.compile(r"\(([a-h])\)")


def missing_parts(markdown: str, problem: str) -> List[str]:
    """The parts the problem asks for, (a), (b) ..., that the **Answer:** line doesn't mention."""
    asked = sorted(set(_PART.findall(problem)))
    answer = answer_text(markdown)
    return [f"({p})" for p in asked if f"({p})" not in answer] if len(asked) > 1 else []


def _follow_up(markdown: str, problem: str, log: List[dict]) -> str:
    """The one follow-up message, or '' when the answer line is complete and every number came from calculate."""
    asks = []
    numbers = unchecked(markdown, problem, log)
    if numbers:
        asks.append(FOLLOW_UP.format(numbers=", ".join(numbers), it="it" if len(numbers) == 1 else "them"))
    parts = missing_parts(markdown, problem)
    if parts:
        asks.append(f"Your **Answer:** line doesn't give part{'s' if len(parts) > 1 else ''} {', '.join(parts)}. "
                    "Solve what is missing (numbers from calculate), then write the complete **Answer:** line.")
    return " ".join(asks)


def solve(backend, problem: str, image=None, cancelled: Callable[[], bool] = lambda: False,
          context: str = "") -> Solution:
    """Work `problem` (Markdown) out with `backend`; every number from the calculator, checked once.
    `context` is reference text the problem relies on (the exercises it mentions)."""
    start = time.perf_counter()
    prompt = f"Solve this statistics problem.\n\n{problem}"
    if context:
        prompt += f"\n\nThe problem refers to other exercises; this is what they say:\n\n{context}"
    backend.begin(SYSTEM, prompt, image)
    texts, log = [], []
    _rounds(backend, texts, log, cancelled)
    markdown = "\n\n".join(texts).strip()
    if not markdown:
        raise SolverError("The solver wrote nothing.")
    checked = True
    ask = _follow_up(markdown, problem, log)
    if ask:
        backend.say(ask)
        more = []
        _rounds(backend, more, log, cancelled)
        line = answer_text("\n\n".join(more))
        if line:
            markdown = _replace_answer(markdown, line)
        checked = not _follow_up(markdown, problem, log)
    return Solution(markdown, backend.model, log, round(time.perf_counter() - start, 1), checked)


def recheck(backend, solution: Solution, other_answer: str, problem: str,
            cancelled: Callable[[], bool] = lambda: False) -> Solution:
    """One more round after two solvers disagreed: the backend re-checks its own solution with the other's answer
    in view. Returns the re-checked solution (or the original when the reply has no **Answer:** line)."""
    start = time.perf_counter()
    backend.say(RECHECK.format(other=other_answer or "(no answer line)"))
    texts = []
    _rounds(backend, texts, solution.tool_log, cancelled)
    markdown = "\n\n".join(texts).strip()
    if not answer_text(markdown):
        return solution
    return Solution(markdown, backend.model, solution.tool_log, round(solution.seconds + time.perf_counter() - start, 1),
                    not _follow_up(markdown, problem, solution.tool_log))
