"""Matching a problem text to a library exercise: typed copies, exercise numbers, ties, not found, numbers."""
import pytest

import nb_fixtures as fx
from plotstudio.core.notebook import library, lookup


@pytest.fixture
def index(tmp_path):
    return lookup.Index(library.load([fx.write_sample(tmp_path)]))


@pytest.mark.parametrize("text, expected", [
    ("20,000 and 1/4, .50 and 3.0 with -0.250", ["20000", "1/4", "0.25", "0.5", "3", "-0.25"]),
    (r"$P=\frac{7}{12}$ and $\tfrac12$", ["7/12", "0.583333", "1/2", "0.5"]),
    ("For the data of Exercise 1.1, n = 15", ["ex1.1", "15"]),
    ("x2 and 3a are not numbers, 1.5% is", ["1.5"]),
])
def test_numbers_are_normalised(text, expected):
    assert lookup.numbers(text) == expected


def test_a_typed_copy_is_found_first_and_shown_directly(index):
    r = index.lookup("A box holds 7 red and 5 blue marbles. Two marbles are drawn without replacement. "
                     "Find the probability that both are red.")
    assert r.status == "match" and r.best.exercise.number == "1.1"
    assert r.best.score >= lookup.HIGH and len(r.candidates) == 3


def test_a_leading_exercise_number_helps_only_when_the_words_agree(index):
    r = index.lookup("2.1 The weights of six parcels are 2.1, 3.4, 2.8, 3.0, 2.6 and 3.1 kg. Find the mean.")
    assert r.label == "2.1" and r.status == "match" and r.best.exercise.number == "2.1" and r.best.label_match
    wrong = index.lookup("1.2 The weights of six parcels are 2.1, 3.4, 2.8, 3.0, 2.6 and 3.1 kg.")
    assert wrong.best.exercise.number == "2.1", "a number alone must not beat the text"
    assert "don't match Exercise 1.2" in wrong.note


def test_only_an_exercise_number_is_a_direct_lookup(index):
    r = index.lookup("Exercise 1.3")
    assert r.status == "match" and r.best.exercise.number == "1.3"


def test_same_words_and_only_small_numbers_is_a_tie_not_a_guess(index):
    r = index.lookup("The weights of six parcels are given in kg. Find the sample mean.")
    assert r.status == "choose"
    assert {c.exercise.number for c in r.candidates[:2]} == {"2.1", "2.2"}
    assert r.candidates[0].score - r.candidates[1].score < lookup.MARGIN


def test_numbers_tell_apart_problems_with_the_same_words(index):
    r = index.lookup("The weights of six parcels are 4.1, 1.4, 5.8, 2.0, 6.6 and 0.1 kg. Find the sample mean.")
    assert r.best.exercise.number == "2.2" and "5.8" in r.best.shared_numbers


def test_an_unrelated_problem_is_not_in_the_library(index):
    r = index.lookup("A regression of yield on rainfall gives a slope estimate; test whether it is zero.")
    assert r.status == "none" and r.best.score < lookup.LOW


def test_an_exercise_without_a_problem_block_is_matched_with_less_trust(index):
    r = index.lookup("A plant makes 20000 parts a day; 2% are faulty. How many faulty parts are expected each day?")
    assert r.best.exercise.number == "1.4"
    assert r.best.score <= lookup.NO_PROBLEM_FACTOR


def test_empty_text(index):
    assert index.lookup("  ").status == "empty"


def test_search_by_number_and_by_words(index):
    assert [e.number for e in index.search("2")] == ["2.1", "2.2"]
    assert index.search("1.3")[0].number == "1.3"
    assert index.search("lamp exponential")[0].number == "1.3"


def test_every_real_exercise_finds_itself():
    lib = library.load([fx.real_library()])
    index = lookup.Index(lib)
    misses = [e.number for e in lib.exercises
              if index.lookup(e.problem_md.replace("**Problem:**", "")).best.exercise is not e]
    assert len(misses) <= len(lib.exercises) // 100, misses   # 1 of 1207 when written (2.16, a tie)
