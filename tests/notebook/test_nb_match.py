"""A problem is answered from the library only when it is surely that exercise with the same numbers."""
from collections import Counter

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


def test_a_book_page_that_says_more_than_the_library_still_matches_with_its_printed_number(index):
    # the page shows the label and says more than the stored problem; the stored solution uses 0.3182
    page = MARBLES + " Give $P$ to four places, like $0.3182$."
    assert library_match.match(index, page) is None                          # no printed number: exact only
    assert library_match.match(index, page, label="1.1").number == "1.1"
    assert library_match.match(index, "1.1 " + page).number == "1.1"
    assert library_match.match(index, page, label="1.2") is None             # another printed number
    assert library_match.match(index, MARBLES + " Use 3 draws.", label="1.1") is None     # 3: not in the solution
    assert library_match.match(index, MARBLES.replace("7 red", "8 red"), label="1.1") is None   # 7 is missing


def test_an_exercise_without_its_own_problem_text_is_never_used(index):
    text = "A plant makes 20,000 parts a day; 2% are faulty. How many faulty parts are expected each day?"
    assert index.lookup(text).best.exercise.number == "1.4"
    assert library_match.match(index, text) is None


def test_another_question_about_the_same_exercise_is_not_given_its_answer(index):
    # same "numbers" as 1.2 (only the mention of Exercise 1.1), a different question: solved live instead
    other = "For the marbles of Exercise 1.1, find the chance that the first marble is blue."
    assert library_match.match(index, other) is None
    same = "For the marbles of Exercise 1.1, find the probability that the two marbles have different colours."
    assert library_match.match(index, same).number == "1.2"
    assert library_match.match(index, other, label="1.2").number == "1.2"    # the page prints 1.2: trust that


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
    # the library's tables use the minus sign −, a model writes -; a list without spaces is still a list
    assert library_match.problem_numbers("at −15 and −10") == library_match.problem_numbers("at -15 and -10")
    assert lookup.numbers("101,94,33,56,122,83") == ["101", "94", "33", "56", "122", "83"]
    assert lookup.numbers("20,000 parts and 1,234,567 more") == ["20000", "1234567"]
    # from real screenshots: the library's " / " between table rows (1.21), braced subscripts (12.62)
    assert lookup.numbers("98 102 / 83 55") == ["98", "102", "83", "55"] and lookup.numbers("1/4") == ["1/4", "0.25"]
    assert library_match.problem_numbers("$x_2$ and $x_{2}$") == Counter({"2": 2})
    assert library_match.problem_numbers("as in Exercise 1.28; see Exercise 1.28") == Counter({"ex1.28": 1})
    # the library writes \le1 and \pm0.0100, a model writes \le 1 and \pm 0.0100
    assert library_match.problem_numbers(r"$0\le y\le1$, $2.4\pm0.0100$") == \
        library_match.problem_numbers(r"$0 \le y \le 1$, $2.4 \pm 0.0100$")
