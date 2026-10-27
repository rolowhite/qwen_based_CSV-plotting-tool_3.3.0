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


def test_a_part_missing_from_the_answer_is_asked_for_in_the_same_one_follow_up():
    two = "A fair coin is tossed 10 times. Find the probability of (a) exactly 3 heads; (b) no heads."
    replies = [{"calls": ["comb(10, 3) / 2**10"]}, "**Answer:** (b) $15/128$",
               {"calls": ["0.5**10"]}, "**Answer:** (a) $15/128$ (b) $1/1024$"]
    with FakeOllama(TOOLS, replies=replies) as fake:
        sol = solver.solve(_qwen(fake), two)
        asked = fake.requests[2]["messages"][-1]["content"]
    assert "doesn't give part (a)" in asked and len(fake.requests) == 4
    assert solver.answer_text(sol.markdown) == "**Answer:** (a) $15/128$ (b) $1/1024$" and sol.checked
    assert solver.missing_parts("**Answer:** 0.1", "Find it.") == []          # one question: no parts to check


def test_the_exercises_a_problem_mentions_go_along_as_context():
    with FakeOllama(TOOLS, replies=["**Answer:** 1"]) as fake:
        solver.solve(_qwen(fake), "For the data of Exercise 3.40, find the mean.", context="Exercise 3.40: f(x)=2x.")
        prompt = fake.requests[0]["messages"][1]["content"]
    assert prompt.endswith("this is what they say:\n\nExercise 3.40: f(x)=2x.")


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
    with FakeGemini(out_of_quota=set(fg.MODELS)) as fake:          # every free model: used up for today
        with pytest.raises(gemini.GeminiError, match="used up for today") as quota:
            solver.solve(_gem(fake), COIN)
        assert quota.value.kind == "quota" and len(fake.requests) == 3
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


def test_an_overloaded_model_falls_through_before_it_starts_and_is_retried_once_after(monkeypatch):
    monkeypatch.setattr(solver, "BUSY_WAIT", 0)
    with FakeGemini(busy={"gemini-3.8-flash"}, replies=[fg.text("**Answer:** 0.1171875")] * 2) as fake:
        sol = solver.solve(_gem(fake), COIN + " It is 0.1171875.")
        assert sol.model == "gemini-3.6-flash"
        again = solver.solve(_gem(fake), COIN + " It is 0.1171875.")      # the busy one is skipped for a while
        assert again.model == "gemini-3.6-flash"
        assert sum("3.8-flash" in path for path, _, _ in fake.requests) == 1
    solver.GeminiBackend.busy_until.clear()
    with FakeGemini(replies=[fg.call("comb(10, 3) / 2**10")]) as fake:     # starts, then its model gets busy
        backend = _gem(fake)
        backend.begin(solver.SYSTEM, COIN)
        backend.turn()
        fake.busy.add("gemini-3.8-flash")
        with pytest.raises(gemini.GeminiError, match="busy") as busy:
            backend.turn()
        assert busy.value.kind == "busy" and backend.model == "gemini-3.8-flash"     # no switch mid-solve
        assert sum("3.8-flash" in path for path, _, _ in fake.requests) == 3          # first, then one retry


def test_a_per_minute_limit_waits_as_google_asks_and_a_used_up_model_falls_through():
    import time
    with FakeGemini(replies=[fg.call("comb(10, 3) / 2**10"), fg.text("**Answer:** 15/128")]) as fake:
        backend = _gem(fake)
        backend.begin(solver.SYSTEM, COIN)
        backend.turn()
        fake.rate_limited.add("gemini-3.8-flash")                    # mid-solve: wait 1 s, same model again
        backend.results([(None, "x")], ["15/128 ≈ 0.1171875"])
        start = time.time()
        text, _ = backend.turn()
    assert 0.9 <= time.time() - start < 5 and text == "**Answer:** 15/128" and backend.model == "gemini-3.8-flash"
    with FakeGemini(out_of_quota={"gemini-3.8-flash"}, replies=[fg.text("**Answer:** 0.1171875")]) as fake:
        sol = solver.solve(_gem(fake), COIN + " It is 0.1171875.")
    assert sol.model == "gemini-3.6-flash"                            # before it starts: the next free model
    err = gemini._error(429, b'{"error": {"message": "slow down", "details": [{"@type": "x.RetryInfo", '
                             b'"retryDelay": "34s"}]}}', "m")
    assert err.kind == "rate" and err.retry_after == 34.0 and "34 s" in str(err)


def test_a_model_that_stalls_counts_as_busy_and_falls_through():
    with FakeGemini(slow={"gemini-3.8-flash": 2}, replies=[fg.text("**Answer:** 0.1171875")]) as fake:
        backend = solver.GeminiBackend(gemini.Gemini("test-key", base=fake.url, timeout=0.5), "gemini-3.8-flash",
                                       gemini.MODELS)
        sol = solver.solve(backend, COIN + " It is 0.1171875.")
    assert sol.model == "gemini-3.6-flash"
    err = None
    with FakeGemini(slow={"gemini-3.8-flash": 2}) as fake:
        try:
            gemini.Gemini("test-key", base=fake.url, timeout=0.5).generate("gemini-3.8-flash", {})
        except gemini.GeminiError as exc:
            err = exc
    assert err is not None and err.kind == "busy" and "didn't answer within" in str(err)


def test_the_answer_may_follow_a_lone_answer_label():
    md = "Steps.\n\n**Answer:**\n\n$P(X=2)=0.2009$\n\nThat is all."
    assert solver.answer_text(md) == "**Answer:**\n\n$P(X=2)=0.2009$"
    assert solver.answer_text("**Answer:** 1\n\n**Answer:** 2") == "**Answer:** 2"


def test_recheck_replaces_the_solution_only_when_it_gives_an_answer():
    replies = [fg.text("Guess.\n\n**Answer:** 0.2"), fg.call("comb(10, 3) / 2**10"),
               fg.text("Recomputed: binomial.\n\n**Answer:** 0.1171875")]
    with FakeGemini(replies=replies) as fake:
        backend = _gem(fake)
        first = solver.solve(backend, COIN + " (about 0.2?)")
        again = solver.recheck(backend, first, "**Answer:** 0.1171875", COIN)
        assert "Another solver's final answer was: **Answer:** 0.1171875" in fake.bodies()[1]["contents"][-1]["parts"][0]["text"]
    assert solver.answer_text(again.markdown) == "**Answer:** 0.1171875" and again.checked
