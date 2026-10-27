"""One turn: read (a fake Ollama), match, stream the answer, read again on a miss, log, and Stop."""
import json
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
    assert session.second_size(1400) == ollama.LONG_SIDE_MIN


def test_a_first_read_that_breaks_is_followed_by_the_second(index):
    replies = [{"text": '{"problems": [', "done_reason": "length"}, _reply(("", MARBLES))]
    with FakeOllama(MODELS, replies=replies) as fake:
        answers, _ = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
    assert "**Solution.**" in answers[0]
    with FakeOllama(MODELS, replies=["not json", "still not json"]) as fake:
        with pytest.raises(ollama.OllamaError, match="valid JSON"):       # both broke: said plainly
            _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))


def test_two_misses_give_the_neutral_sentence_and_what_couldnt_be_read(index):
    other = ("", "A die is rolled 4 times. Find the chance of two sixes.")
    replies = [_reply(other, unreadable=["the last line"]), _reply(other, unreadable=["the last line."])]
    with FakeOllama(MODELS, replies=replies) as fake:
        answers, _ = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
    assert answers == ["**Problem.**\n\n" + other[1] + "\n\n" + session.NOT_YET +
                       " Part of the picture couldn't be read: the last line."]


def test_every_problem_in_a_picture_gets_its_own_answer(index):
    reply = _reply(("1.1", MARBLES), ("", "A die is rolled 4 times."))
    with FakeOllama(MODELS, replies=[reply, reply]) as fake:
        answers, events = _run(session.Turn(session.Source("p.png", _picture()), index, fake.url, pace=0))
    assert len(answers) == 2 and [e[0] for e in events].count("start") == 2
    assert "**Solution.**" in answers[0] and session.NOT_YET in answers[1]


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
