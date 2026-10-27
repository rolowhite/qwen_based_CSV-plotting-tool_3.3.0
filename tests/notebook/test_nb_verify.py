"""The background re-check: an answer from one solver is solved again, and a sure disagreement is a Correction."""
import time

import pytest

import nb_fixtures as fx  # noqa: F401  (puts the test folder on sys.path)
from fake_ollama import FakeOllama
from plotstudio.core.notebook import session, solver, verify

COIN = "A fair coin is tossed 10 times. Find the probability of exactly 3 heads."
MODELS = {"text-only": ["completion", "tools"]}
RIGHT = [{"text": "**Given:** $n=10$.", "calls": ["comb(10, 3) / 2**10"]}, "So $P=15/128$.\n\n**Answer:** $0.1171875$"]
WRONG = [{"text": "**Given:** $n=10$.", "calls": ["comb(10, 4) / 2**10"]}, "So $P=0.205$.\n\n**Answer:** $0.205078125$"]


def _solution(answer, checked=True):
    return solver.Solution(f"Work.\n\n**Answer:** ${answer}$", "m", [], 1.0, checked)


def _pending(by="qwen", shown="Work.\n\n**Answer:** $0.205078125$"):
    return verify.Pending("", COIN, shown, by)


def test_a_sure_disagreement_is_a_correction_that_apologises_and_gives_the_right_solution():
    verdict = verify.judge(_pending(), _solution("0.1171875"))
    assert verdict.agrees is False
    assert "Correction" in verdict.correction and "sorry" in verdict.correction and "0.1171875" in verdict.correction


def test_agreement_an_unchecked_recheck_and_no_result_say_nothing():
    assert verify.judge(_pending(), _solution("0.205078125")).correction == ""
    assert verify.judge(_pending(), _solution("0.1171875", checked=False)).correction == ""     # can't be trusted either
    assert verify.judge(_pending(shown="no answer line"), _solution("0.1171875")).agrees is None


def test_a_stored_solution_without_an_answer_line_is_judged_by_the_numbers_it_contains():
    stored = "$P=1-e^{-1.6}=$ **0.7981**."
    assert verify.judge(_pending("library", stored), _solution("0.7981")).correction == ""
    assert "Correction" in verify.judge(_pending("library", stored), _solution("0.9")).correction


def test_only_an_answer_nobody_cross_checked_is_queued_for_a_recheck(tmp_path):
    with FakeOllama(MODELS, replies=RIGHT) as fake:
        turn = session.Turn(session.Source("typed", text=COIN), None, fake.url, pace=0)
        turn.run(lambda event: None)
    assert [(p.by, p.problem) for p in turn.pending] == [("qwen", COIN)]
    assert "0.1171875" in turn.pending[0].shown


def test_the_checker_solves_again_and_finds_the_mistake():
    with FakeOllama(MODELS, replies=RIGHT) as fake:
        verdict = session.Checker(fake.url).check(_pending())
    assert verdict.agrees is False and "0.1171875" in verdict.correction
    with FakeOllama(MODELS, replies=WRONG) as fake:           # the same mistake twice: nothing to correct
        assert session.Checker(fake.url).check(_pending()).correction == ""
