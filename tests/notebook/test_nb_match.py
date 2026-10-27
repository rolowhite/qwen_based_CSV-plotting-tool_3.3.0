"""A problem is answered from the library only when it is surely that exercise with the same numbers."""
import pytest

import nb_fixtures as fx
from plotstudio.core.notebook import library, library_match, lookup

MARBLES = ("A box holds 7 red and 5 blue marbles. Two marbles are drawn without replacement. "
           "Find the probability that both are red.")


@pytest.fixture
def index(tmp_path):
    return lookup.Index(library.load([fx.write_sample(tmp_path)]))


def test_the_same_problem_is_a_hit(index):
    assert library_match.match(index, MARBLES).number == "1.1"
    assert library_match.match(index, MARBLES, label="1.1").number == "1.1"
    assert library_match.match(index, "1.1 " + MARBLES).number == "1.1"      # a typed label isn't a number


def test_one_changed_number_is_not_given_the_stored_answer(index):
    assert index.lookup(MARBLES.replace("7 red", "8 red")).status == "match"     # the words still match ...
    assert library_match.match(index, MARBLES.replace("7 red", "8 red")) is None   # ... the numbers don't
    assert library_match.match(index, MARBLES + " Use 3 draws.") is None


def test_an_exercise_without_its_own_problem_text_is_never_used(index):
    text = "A plant makes 20,000 parts a day; 2% are faulty. How many faulty parts are expected each day?"
    assert index.lookup(text).best.exercise.number == "1.4"
    assert library_match.match(index, text) is None


def test_a_tie_is_not_a_hit(index):
    assert index.lookup("The weights of six parcels are given in kg. Find the sample mean.").status == "choose"
    assert library_match.match(index, "The weights of six parcels are given in kg. Find the sample mean.") is None


def test_the_same_words_with_other_numbers_are_told_apart_by_the_numbers(index):
    first = "The weights of six parcels are 2.1, 3.4, 2.8, 3.0, 2.6 and 3.1 kg. Find the sample mean."
    second = "The weights of six parcels are 4.1, 1.4, 5.8, 2.0, 6.6 and 0.1 kg. Find the sample mean."
    assert library_match.match(index, first).number == "2.1"
    assert library_match.match(index, second).number == "2.2"
    assert library_match.match(index, second.replace("6.6", "6.7")) is None


def test_few_words_but_numbers_no_other_exercise_has(index):
    text = "Compute it: 4.1, 1.4, 5.8, 2.0, 6.6, 0.1."
    assert lookup.LOW <= index.lookup(text).best.score < lookup.HIGH
    assert library_match.match(index, text).number == "2.2"
    assert library_match.match(index, "Compute it: 7, 5.") is None      # only 2 numbers: not enough


def test_math_written_differently_keeps_the_same_numbers():
    assert library_match.problem_numbers(r"$\frac{7}{12}$ of 20,000") == \
        library_match.problem_numbers("7/12 of 20000")
    assert library_match.problem_numbers("3.13 The 3 values") == library_match.problem_numbers("The 3 values")
    # the library writes \le1 and \pm0.0100, a model writes \le 1 and \pm 0.0100
    assert library_match.problem_numbers(r"$0\le y\le1$, $2.4\pm0.0100$") == \
        library_match.problem_numbers(r"$0 \le y \le 1$, $2.4 \pm 0.0100$")
