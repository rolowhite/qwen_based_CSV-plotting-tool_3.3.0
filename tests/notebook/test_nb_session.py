"""One turn: read (a fake Ollama), match, stream the answer, read again on a miss, log, and Stop."""
import json
import time
import threading

import pytest

import nb_fixtures as fx
from fake_ollama import FakeOllama
from plotstudio.core.notebook import library, lookup, ollama, session

MODELS = {"text-only": ["completion", "tools"], "vl": ["completion", "vision", "thinking"]}
MARBLES = ("A box holds 7 red and 5 blue marbles. Two marbles are drawn without replacement. "
           "Find the probability that both are red.")


def _reply(*problems, unreadable=()):
    return json.dumps({"problems": [{"label": l, "markdown": m} for l, m in problems], "unreadable": list(unreadable)})


@pytest.fixture
def index(tmp_path):
    return lookup.Index(library.load([fx.write_sample(tmp_path / "lib")]))


def _picture():
    from PIL import Image
    return Image.new("RGB", (900, 300), "white")


def _run(turn):
    events = []
    answers = turn.run(events.append)
    return answers, events


def test_a_hit_restates_the_problem_then_streams_the_solution(index, tmp_path):
    log = tmp_path / "history.jsonl"
    with FakeOllama(MODELS, replies=[_reply(("1.1", MARBLES))]) as fake:
        turn = session.Turn(session.Source("p.png", _picture()), index, fake.url, log_path=log, pace=0)
        answers, events = _run(turn)
        assert len(fake.requests) == 1 and fake.requests[0]["model"] == "vl"
        assert fake.requests[0]["think"] is False          # the model can think: switched off for copying
    assert [e[1] for e in events if e[0] == "status"] == ["Reading the problem…", "Solving…"]
    streamed = "".join(e[1] for e in events if e[0] == "text")
    assert streamed == answers[0] and [e[0] for e in events].count("text") > 3
    assert answers[0].startswith("**Problem 1.1.**\n\n" + MARBLES) and r"\mathbf{0.3182}" in answers[0]
    assert "library" not in answers[0].lower() and "Checker" not in answers[0]
    entry = json.loads(log.read_text(encoding="utf-8"))
    assert entry["answers"][0]["from"] == "library:sample:1.1" and entry["model"] == "vl"
    assert entry["stopped"] is False and entry["error"] is None and len(entry["reads"]) == 1


def test_a_miss_reads_again_at_another_size_and_can_still_hit(index):
    misread = MARBLES.replace("7 red", "1 red")
    with FakeOllama(MODELS, replies=[_reply(("", misread)), _reply(("", MARBLES))]) as fake:
        answers, events = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
        assert len(fake.requests) == 2
    assert "Reading it again more closely…" in [e[1] for e in events if e[0] == "status"]
    assert "**Solution.**" in answers[0] and MARBLES in answers[0]
    assert session.second_size(1200) == 1800 and session.second_size(2000) == 1333
    assert session.second_size(1500) == ollama.LONG_SIDE_MAX        # bigger, up to the cap, never smaller (a bug)


def test_a_first_read_that_breaks_is_followed_by_the_second(index):
    replies = [{"text": '{"problems": [', "done_reason": "length"}, _reply(("", MARBLES))]
    with FakeOllama(MODELS, replies=replies) as fake:
        answers, _ = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
    assert "**Solution.**" in answers[0]
    with FakeOllama(MODELS, replies=["not json", "still not json"]) as fake:
        with pytest.raises(ollama.OllamaError, match="valid JSON"):       # both broke: said plainly
            _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))


COIN = "A fair coin is tossed 10 times. Find the probability of exactly 3 heads."
QWEN_SOLVES = [{"text": "**Given:** $n=10$, $p=0.5$. Binomial:", "calls": ["comb(10, 3) / 2**10"]},
               "So $P(X=3)=15/128$.\n\n**Answer:** $0.1171875$"]


def test_a_problem_not_in_the_solutions_is_solved_and_says_what_couldnt_be_read(index, tmp_path):
    # replaces the 3.4.0 test of "I can't solve this one yet": such problems are now solved
    log = tmp_path / "history.jsonl"
    replies = [_reply(("", COIN), unreadable=["the last line"])]     # not in the library: no second reading
    with FakeOllama(MODELS, replies=replies + QWEN_SOLVES) as fake:
        answers, events = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, log_path=log,
                                            pace=0))
        solving = fake.requests[1]
    assert solving["model"] == "text-only" and solving["tools"][0]["function"]["name"] == "calculate"
    assert answers[0].startswith("**Problem.**\n\n" + COIN + "\n\n**Solution.**\n\n**Given:**")
    assert "**Answer:** $0.1171875$" in answers[0]
    assert answers[0].endswith("*Part of the picture couldn't be read: the last line.*")
    entry = json.loads(log.read_text(encoding="utf-8"))["answers"][0]
    assert entry["from"] == "solver:text-only" and entry["agree"] is None
    assert entry["solutions"][0]["tool_log"] == [{"expression": "comb(10, 3) / 2**10", "result": "15/128 ≈ 0.1171875"}]


def test_every_problem_in_a_picture_gets_its_own_answer(index):
    reply = _reply(("1.1", MARBLES), ("", COIN))
    with FakeOllama(MODELS, replies=[reply, reply] + QWEN_SOLVES) as fake:
        answers, events = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
    assert len(answers) == 2 and [e[0] for e in events].count("start") == 2
    assert r"\mathbf{0.3182}" in answers[0] and "**Answer:** $0.1171875$" in answers[1]


def _gemini_turn(index, ollama_url, gem_url, log=None, text=COIN):
    return session.Turn(session.Source("typed", text=text), index, ollama_url, log_path=log, pace=0,
                        gemini_key="test-key", gemini_base=gem_url)


def test_with_a_key_both_solve_and_geminis_solution_is_shown_when_they_agree(index, tmp_path):
    from fake_gemini import FakeGemini, call, text
    log = tmp_path / "history.jsonl"
    with FakeOllama(MODELS, replies=QWEN_SOLVES) as qwen, \
            FakeGemini(replies=[call("comb(10, 3) * 0.5**10"), text("Gemini's way.\n\n**Answer:** 0.1172")]) as gem:
        answers, events = _run(_gemini_turn(index, qwen.url, gem.url, log))
    assert "Gemini's way." in answers[0] and "Checking the answer…" in [e[1] for e in events if e[0] == "status"]
    raw = log.read_text(encoding="utf-8")
    entry = json.loads(raw)["answers"][0]
    assert entry["from"] == "solver:gemini-3.8-flash" and entry["agree"] is True and not entry["rechecked"]
    assert {s["solver"] for s in entry["solutions"]} == {"qwen", "gemini"} and "test-key" not in raw


def test_when_they_disagree_gemini_rechecks_once_and_its_answer_is_shown(index):
    from fake_gemini import FakeGemini, call, text
    # Gemini's first answer is calculator-backed but for 4 heads (so the answer check passes and they disagree)
    gem_replies = [call("comb(10, 4) / 2**10"), text("**Answer:** 0.205078125"), call("comb(10, 3) / 2**10"),
                   text("I recomputed it.\n\n**Answer:** 0.1171875"), text("never asked")]
    with FakeOllama(MODELS, replies=QWEN_SOLVES) as qwen, FakeGemini(replies=gem_replies) as gem:
        turn = _gemini_turn(index, qwen.url, gem.url)
        answers, _ = _run(turn)
        recheck = gem.bodies()[2]["contents"][-1]["parts"][0]["text"]
    assert "Another solver's final answer was: **Answer:** $0.1171875$" in recheck
    assert "I recomputed it." in answers[0] and turn.answers[0]["rechecked"] is True
    assert turn.answers[0]["agree"] is False


def test_geminis_used_up_quota_gives_qwens_solution_and_says_why(index):
    from fake_gemini import MODELS as FREE, FakeGemini
    with FakeOllama(MODELS, replies=QWEN_SOLVES) as qwen, FakeGemini(out_of_quota=set(FREE)) as gem:
        turn = _gemini_turn(index, qwen.url, gem.url)
        answers, _ = _run(turn)
    assert "**Answer:** $0.1171875$" in answers[0] and turn.answers[0]["from"] == "solver:text-only"
    assert "used up for today" in turn.gemini_problem and "gemini" in turn.answers[0]["errors"]


def test_without_ollama_a_typed_problem_is_solved_by_gemini_alone(index):
    from fake_gemini import FakeGemini, call, text
    with FakeGemini(replies=[call("comb(10, 3) / 2**10"), text("**Answer:** 0.1171875")]) as gem:
        turn = _gemini_turn(index, "http://127.0.0.1:9", gem.url)
        answers, _ = _run(turn)
    assert "**Answer:** 0.1171875" in answers[0] and turn.answers[0]["from"] == "solver:gemini-3.8-flash"
    assert "isn't running" in turn.answers[0]["errors"]["qwen"]


def test_a_mentioned_exercise_from_the_solutions_is_given_to_the_solvers(index):
    text = "For the marbles of Exercise 1.1, find the chance that the first marble is blue."
    with FakeOllama(MODELS, replies=QWEN_SOLVES) as fake:
        _run(session.Turn(session.Source("typed", text=text), index, fake.url, pace=0))
        prompt = fake.requests[0]["messages"][1]["content"]
    assert "Exercise 1.1: A box holds 7 red and 5 blue marbles." in prompt
    turn = session.Turn(session.Source("typed", text=MARBLES), index, match=False)
    assert turn._match(reader_problem(MARBLES)) is None            # match=False: always solved (the live eval)


def reader_problem(text):
    from plotstudio.core.notebook import reader
    return reader.Problem("", text)


def test_a_local_model_past_its_time_budget_is_stopped(index, monkeypatch):
    from fake_gemini import FakeGemini, call, text
    from plotstudio.core.notebook import solver
    monkeypatch.setattr(session, "SOLVE_BUDGET", 1)
    slow = [{"text": "Thinking about it at length " * 4, "delay": 0.6}]
    with FakeOllama(MODELS, replies=list(slow)) as qwen:
        with pytest.raises(solver.SolverError, match="took the model on this computer more than"):
            _run(session.Turn(session.Source("typed", text=COIN), index, qwen.url, pace=0))
    with FakeOllama(MODELS, replies=list(slow)) as qwen, \
            FakeGemini(replies=[call("comb(10, 3) / 2**10"), text("**Answer:** 0.1171875")]) as gem:
        turn = _gemini_turn(index, qwen.url, gem.url)
        answers, _ = _run(turn)                                     # the turn itself goes on: Gemini's answer
    assert "**Answer:** 0.1171875" in answers[0] and "took the model" in turn.answers[0]["errors"]["qwen"]


def test_a_model_that_runs_out_of_quota_mid_solve_starts_over_on_the_next_and_is_skipped_after(index):
    from fake_gemini import FakeGemini, call, text
    from plotstudio.core.notebook import solver
    replies = [call("comb(10, 3) / 2**10"), call("comb(10, 3) / 2**10"), text("**Answer:** 0.1171875"),
               call("comb(10, 3) / 2**10"), text("**Answer:** 0.1171875")]
    with FakeOllama(MODELS, replies=QWEN_SOLVES * 2) as qwen, \
            FakeGemini(quota_after={"gemini-3.8-flash": 1}, replies=replies) as gem:
        turn = _gemini_turn(index, qwen.url, gem.url)
        _run(turn)
        assert turn.answers[0]["from"] == "solver:gemini-3.6-flash" and turn.answers[0]["agree"] is True
        assert "gemini-3.8-flash" in solver.GeminiBackend.busy_until             # skipped from now on
        later = _gemini_turn(index, qwen.url, gem.url)
        _run(later)
        assert [p for p, _, _ in gem.requests][-1].startswith("/v1beta/models/gemini-3.6-flash")
        assert sum("3.8-flash" in p for p, _, _ in gem.requests) == 2           # never asked again


def test_a_slow_gemini_gives_way_to_qwens_answer_after_the_grace_period(index, monkeypatch):
    from fake_gemini import FakeGemini, text
    monkeypatch.setattr(session, "GEMINI_GRACE", 0.5)
    with FakeOllama(MODELS, replies=QWEN_SOLVES) as qwen, \
            FakeGemini(slow={"gemini-3.8-flash": 4}, replies=[text("**Answer:** too late")]) as gem:
        turn = _gemini_turn(index, qwen.url, gem.url)
        answers, _ = _run(turn)
    assert "**Answer:** $0.1171875$" in answers[0] and turn.answers[0]["from"] == "solver:text-only"
    assert turn.gemini_problem == "Gemini took too long this time."


def test_gemini_answering_first_is_not_kept_waiting_for_a_slow_local_model(index, monkeypatch):
    from fake_gemini import FakeGemini, call, text
    monkeypatch.setattr(session, "QWEN_GRACE", 0.3)
    slow = [{"text": "thinking " * 40, "delay": 1.0}]               # qwen would need seconds: it must not be waited for
    with FakeOllama(MODELS, replies=slow) as qwen, \
            FakeGemini(replies=[call("comb(10, 3) * 0.5**10"), text("Gemini's way.\n\n**Answer:** 0.1172")]) as gem:
        turn = _gemini_turn(index, qwen.url, gem.url)
        start = time.perf_counter()
        answers, _ = _run(turn)
        took = time.perf_counter() - start
    assert "Gemini's way." in answers[0] and turn.answers[0]["from"] == "solver:gemini-3.8-flash"
    assert took < 3 and "Gemini had already answered" in turn.answers[0]["errors"]["qwen"]


def test_a_pdf_text_layer_that_is_a_library_problem_needs_no_reading_model(index):
    with FakeOllama(MODELS, replies=[]) as fake:
        turn = session.Turn(session.Source("page.pdf", _picture(), hint="1.1 " + MARBLES.replace(" ", "\u00ad ", 1)
                                           .replace("\u00ad ", " ")), index, fake.url, pace=0)
        answers, events = _run(turn)
        assert fake.requests == []                                         # the picture was never read
    assert r"\mathbf{0.3182}" in answers[0] and "Reading the problem…" not in [e[1] for e in events]


def test_a_quick_ocr_reading_that_is_a_library_problem_needs_no_vision_model(index, monkeypatch):
    monkeypatch.setattr(session.reader, "ocr_text", lambda image: "1.1 " + MARBLES.replace("$", ""))
    with FakeOllama(MODELS, replies=[]) as fake:
        answers, events = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
        assert fake.requests == []                                         # the model never read the picture
    assert r"\mathbf{0.3182}" in answers[0] and [e[1] for e in events if e[0] == "status"][0] == "Reading the problem…"


def test_an_ocr_reading_that_is_no_library_problem_goes_on_to_the_vision_model(index, monkeypatch):
    monkeypatch.setattr(session.reader, "ocr_text", lambda image: "garbled 7 red 9 blue")
    with FakeOllama(MODELS, replies=[_reply(("1.1", MARBLES))]) as fake:
        answers, events = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
        assert len(fake.requests) == 1
    assert [e[1] for e in events if e[0] == "status"].count("Reading the problem…") == 1


def test_without_ollama_or_a_key_a_new_problem_needs_setting_up(index):
    turn = session.Turn(session.Source("typed", text=COIN), index, "http://127.0.0.1:9", pace=0)
    with pytest.raises(ollama.NotReady, match="isn't running"):
        _run(turn)


def test_typed_text_skips_reading_and_needs_no_ollama(index):
    turn = session.Turn(session.Source("typed", text=MARBLES), index, "http://127.0.0.1:9", pace=0)
    answers, events = _run(turn)
    assert "**Solution.**" in answers[0] and not [e for e in events if e[1] == "Reading the problem…"]


def test_no_vision_model_and_no_problem_found(index):
    with FakeOllama({"text-only": ["completion"]}) as fake:
        with pytest.raises(ollama.NotReady, match="ollama pull"):
            _run(session.Turn(session.Source("p.png", _picture()), index, fake.url))
    with FakeOllama(MODELS, replies=[_reply(), _reply()]) as fake:
        answers, _ = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
    assert answers == [session.NOTHING]


def test_stop_ends_the_stream_and_is_logged(index, tmp_path):
    log = tmp_path / "history.jsonl"
    turn = session.Turn(session.Source("typed", text=MARBLES), index, log_path=log, pace=0.05)
    seen = []

    def emit(event):
        seen.append(event)
        if event[0] == "text" and len(seen) == 4:
            threading.Thread(target=turn.cancel).start()

    with pytest.raises(ollama.Cancelled):
        turn.run(emit)
    assert sum(e[0] == "text" for e in seen) < 8
    assert json.loads(log.read_text(encoding="utf-8"))["stopped"] is True
