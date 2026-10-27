"""Remembered answers: a live answer is shown again only once it is verified."""
import nb_fixtures as fx  # noqa: F401
from plotstudio.core.notebook import cache


def test_an_answer_is_served_only_once_verified_and_survives_a_restart(tmp_path):
    path = tmp_path / "answers.json"
    c = cache.Cache(path)
    c.remember("A fair coin  is tossed 10 times.", "solution", "qwen", verified=False)
    assert c.answer("a fair coin is tossed 10 times.") is None                       # spacing and case don't matter
    c.verify("A fair coin is tossed 10 times.")
    assert cache.Cache(path).answer("A fair coin is tossed 10 times.")["markdown"] == "solution"
    c.remember("A fair coin is tossed 10 times.", "another", "qwen", verified=False)   # never replaces a verified one
    assert c.answer("A fair coin is tossed 10 times.")["markdown"] == "solution"
    c.drop("A fair coin is tossed 10 times.")
    assert cache.Cache(path).answer("A fair coin is tossed 10 times.") is None


def test_readings_are_remembered_by_picture_and_the_oldest_go_first(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "MAX_ENTRIES", 3)
    c = cache.Cache(tmp_path / "a.json")
    for n in range(5):
        c.remember_reading(f"digest{n}", [["", f"problem {n}"]])
    assert c.reading("digest0") is None and cache.Cache(tmp_path / "a.json").reading("digest4") == [["", "problem 4"]]
    assert len(c.readings) == 3
