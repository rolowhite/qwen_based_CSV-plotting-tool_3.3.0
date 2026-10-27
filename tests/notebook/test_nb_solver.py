"""Solving with a model and the calculator (fake Ollama and fake Gemini): tool calls run and come back, the round
cap, the one follow-up for an answer number the calculator never gave, comparing answers, and Gemini's details
(the picture, the key kept out of errors, signatures sent back, retired models)."""
import pytest

import fake_gemini as fg
from fake_gemini import FakeGemini
from fake_ollama import FakeOllama
from plotstudio.core.notebook import gemini, ollama, solver

QWEN = "qwen3-vl:8b-instruct"
TOOLS = {QWEN: ["completion", "vision", "tools"]}
COIN = "A fair coin is tossed 10 times. Find the probability of exactly 3 heads."


def _qwen(fake):
    return solver.OllamaBackend(ollama.Chat(fake.url), QWEN)


def _gem(fake, model="gemini-3.8-flash", key="test-key"):
    return solver.GeminiBackend(gemini.Gemini(key, base=fake.url), model, gemini.MODELS)


def _picture():
    from PIL import Image
    return Image.new("RGB", (600, 200), "white")


def test_qwen_calls_the_calculator_and_gets_the_result_back():
    replies = [{"text": "**Given:** $n=10$, $p=0.5$. Binomial:", "calls": ["comb(10, 3) * 0.5**10"]},
               "So $P(X=3)=0.1171875$.\n\n**Answer:** $0.1171875$"]
    with FakeOllama(TOOLS, replies=replies) as fake:
        sol = solver.solve(_qwen(fake), COIN)
        second = fake.requests[1]
    assert sol.tool_log == [{"expression": "comb(10, 3) * 0.5**10", "result": "0.1171875"}]
    assert second["tools"][0]["function"]["name"] == "calculate"
    assert second["messages"][-1] == {"role": "tool", "content": "0.1171875", "tool_name": "calculate",
                                      "tool_call_id": "call_0"}
    assert sol.markdown.startswith("**Given:**") and "**Answer:** $0.1171875$" in sol.markdown and sol.checked


def test_a_calculator_refusal_goes_back_to_the_model():
    replies = [{"calls": ["binom.pmf(3, 10, 0.5)"]}, {"calls": ["dist('binom', 'pmf', 3, n=10, p=0.5)"]},
               "**Answer:** 0.1171875"]
    with FakeOllama(TOOLS, replies=replies) as fake:
        sol = solver.solve(_qwen(fake), COIN)
    assert sol.tool_log[0]["result"].startswith("error: unknown function. Write dist(")
    assert sol.tool_log[1]["result"] == "0.1171875" and sol.checked


def test_an_answer_number_not_from_the_calculator_gets_one_follow_up():
    replies = ["By symmetry the chance is about 0.12.\n\n**Answer:** 0.12",          # mental arithmetic
               {"calls": ["comb(10, 3) / 2**10"]}, "**Answer:** $15/128 \\approx 0.1171875$"]
    with FakeOllama(TOOLS, replies=replies) as fake:
        sol = solver.solve(_qwen(fake), COIN)
        follow_up = fake.requests[1]["messages"][-1]
    assert follow_up["role"] == "user" and "0.12" in follow_up["content"] and len(fake.requests) == 3
    assert sol.markdown.endswith("**Answer:** $15/128 \\approx 0.1171875$") and "**Answer:** 0.12" not in sol.markdown
    assert sol.checked


def test_only_one_follow_up_even_when_it_is_still_wrong():
    with FakeOllama(TOOLS, replies=["**Answer:** 0.12", "**Answer:** 0.13", "never asked"]) as fake:
        sol = solver.solve(_qwen(fake), COIN)
        assert len(fake.requests) == 2
    assert sol.checked is False and sol.markdown == "**Answer:** 0.13"


def test_the_round_cap_stops_a_model_that_never_finishes(monkeypatch):
    monkeypatch.setattr(solver, "MAX_ROUNDS", 3)
    with FakeOllama(TOOLS, replies=[{"calls": ["1+1"]}] * 5) as fake:
        with pytest.raises(solver.SolverError, match="after 3 calculator rounds"):
            solver.solve(_qwen(fake), COIN)


@pytest.mark.parametrize("a, b, same", [
    ("**Answer:** 0.1171875", "**Answer:** $P(X=3)\\approx0.1172$", True),
    ("**Answer:** (a) 0.6496 (b) 1.25", "**Answer:** (a) 0.65, (b) 1.250", True),
    ("**Answer:** 0.6496", "**Answer:** 0.6", False),
    ("**Answer:** 11.72%", "**Answer:** 0.1172", True),
    ("**Answer:** 0.1171875", "**Answer:** 0.1171875 and 0.25", False),
    ("**Answer:** 0.1171875", "**Answer:** 0.1171875 with p = 0.5", True),        # 0.5 is from the problem
    ("**Answer:** The estimators differ.", "**Answer:** 0.5", None),
])
def test_agree_compares_the_results_not_the_numbers_from_the_problem(a, b, same):
    assert solver.agree(a, b, "Toss 10 times; n = 10, p = 0.5, x = 3.") is same


def test_gemini_gets_the_picture_and_sends_signatures_back():
    replies = [fg.call("comb(10, 3) * 0.5**10"), fg.text("Binomial, so $0.1171875$.\n\n**Answer:** 0.1171875")]
    with FakeGemini(replies=replies) as fake:
        sol = solver.solve(_gem(fake), COIN, image=_picture())
        first, second = fake.bodies()
    parts = first["contents"][0]["parts"]
    assert parts[0]["text"].endswith(COIN) and parts[1]["inlineData"]["mimeType"] == "image/png"
    assert first["tools"][0]["functionDeclarations"][0]["name"] == "calculate"
    assert first["systemInstruction"]["parts"][0]["text"] == solver.SYSTEM
    model_turn, answer = second["contents"][1], second["contents"][2]
    assert model_turn["role"] == "model" and model_turn["parts"][0]["thoughtSignature"] == "sig-1"
    assert answer["parts"][0]["functionResponse"]["response"] == {"result": "0.1171875"}
    assert sol.model == "gemini-3.8-flash" and sol.checked


def test_gemini_errors_are_plain_and_never_show_the_key():
    with FakeGemini(key="right") as fake:
        with pytest.raises(gemini.GeminiError) as bad:
            gemini.Gemini("wrong-secret-key", base=fake.url).models()
        assert bad.value.kind == "key" and "wrong-secret-key" not in str(bad.value)
        assert "wrong-secret-key" not in fake.requests[0][0]                     # not in the URL either
    with FakeGemini(replies=[{"status": 429, "message": "Resource has been exhausted"}]) as fake:
        with pytest.raises(gemini.GeminiError, match="free quota is used up") as quota:
            solver.solve(_gem(fake), COIN)
        assert quota.value.kind == "quota"
    with pytest.raises(gemini.GeminiError, match="No connection") as offline:
        gemini.Gemini("k", base="http://127.0.0.1:9").models()
    assert offline.value.kind == "network" and "k" not in repr(gemini.Gemini("k"))


def test_a_retired_model_falls_through_to_the_next_free_one():
    with FakeGemini(models=["gemini-3.6-flash"], replies=[fg.text("**Answer:** 0.1171875")]) as fake:
        sol = solver.solve(_gem(fake), COIN + " It is 0.1171875.")
        assert [p for p, _, b in fake.requests] == ["/v1beta/models/gemini-3.8-flash:generateContent",
                                                    "/v1beta/models/gemini-3.6-flash:generateContent"]
    assert sol.model == "gemini-3.6-flash"
    assert gemini.pick(["gemini-3.5-flash-lite", "gemini-3.6-flash"]) == "gemini-3.6-flash"
    assert gemini.pick(["x"], wanted="x") == "x" and gemini.pick(["x"]) is None


def test_recheck_replaces_the_solution_only_when_it_gives_an_answer():
    replies = [fg.text("Guess.\n\n**Answer:** 0.2"), fg.call("comb(10, 3) / 2**10"),
               fg.text("Recomputed: binomial.\n\n**Answer:** 0.1171875")]
    with FakeGemini(replies=replies) as fake:
        backend = _gem(fake)
        first = solver.solve(backend, COIN + " (about 0.2?)")
        again = solver.recheck(backend, first, "**Answer:** 0.1171875", COIN)
        assert "Another solver's final answer was: **Answer:** 0.1171875" in fake.bodies()[1]["contents"][-1]["parts"][0]["text"]
    assert solver.answer_text(again.markdown) == "**Answer:** 0.1171875" and again.checked
