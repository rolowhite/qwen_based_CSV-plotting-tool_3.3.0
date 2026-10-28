"""The two books as books: table rules and formulas per chapter, a footer that says where an answer is from, the
quick solutions checked against the answer key, and exercises named by number."""
import json

import pytest

import nb_fixtures as fx  # noqa: F401
from fake_ollama import FakeOllama
from plotstudio.core.notebook import calculator, footer, library, lookup, quick, session, solver

MODELS = {"text-only": ["completion", "tools"]}
PROBLEM = ("A sample of 64 smokers has a mean of 23 dollars a week; the population standard deviation is 6 dollars. "
           "Construct the 95 percent confidence interval for the population mean.")
GIVEN = {"type": "ci_mean", "mean": 23, "sd": 6, "n": 64, "confidence": 95, "sigma_known": True}


@pytest.fixture(scope="module")
def books():
    lib = library.load(library.BUILT_IN_FILES)
    return lib, lookup.Index(lib)


def _run(turn):
    events = []
    answers = turn.run(events.append)
    return answers, events


def test_the_built_in_books_are_clean_and_carry_their_chapters_rules(books):
    lib, _ = books
    for path in library.BUILT_IN_FILES:
        text = path.read_text(encoding="utf-8")
        assert not [c for c in set(text) if ord(c) < 32 and c != "\n"], f"{path.name} has control characters"
    e = lib.get("9.5", "lind")
    assert "Appendix B.1" in e.tables and "Confidence interval for $\\mu$ ($\\sigma$ known)" in e.conventions
    assert "\\frac" in lib.get("11.3", "lind").conventions and "\\neq" in lib.get("11.3", "lind").conventions
    assert "Table A" in lib.get("9.1", "walpole").tables


def test_a_stored_answer_says_where_it_is_from_and_what_comes_next(books):
    lib, _ = books
    text = footer.book_footer(lib.get("9.5", "lind"), lib)
    assert "From Lind, 15th edition · Chapter 9, Section 9.3" in text and "Exercise 9.5" in text
    assert "**Matches Lind Appendix C" in text and "**Formulas for this chapter**" in text
    assert "**Next in this section:** 9.6, 9.7. Type a number to solve it." in text
    assert "Checked:" in footer.book_footer(lib.get("3.14", "walpole"), lib)


def test_the_calculator_prints_what_the_books_tables_print():
    assert calculator.evaluate("ztable(1.96)") == "0.475" and calculator.evaluate("ztable(1.645)") == "0.4505"
    assert calculator.evaluate("zcrit(0.975)") == "1.96" and calculator.evaluate("zcrit(0.995)") == "2.58"
    assert calculator.evaluate("zcrit(0.95)") == "1.645" and calculator.evaluate("tcrit(0.025, 14)") == "2.145"
    with pytest.raises(calculator.CalcError):
        calculator.evaluate("zcrit(1.5)")


# ------------------------------------------------------------------------------------------ quick solutions --
@pytest.mark.parametrize("key, given, expect", [
    ("lind:9.42", dict(type="ci_mean", mean=24, sd=5, n=15, confidence=98, sigma_known=False), "20.61"),
    ("lind:9.83", dict(type="ci_prop", proportion=0.25, n=500, confidence=98), "0.2049"),
    ("lind:9.5", dict(type="ci_mean", mean=20, sd=5, n=49, confidence=95, sigma_known=True), "18.6"),
])
def test_quick_solutions_give_the_answer_in_the_back_of_the_book(books, key, given, expect):
    lib, _ = books
    e = lib._by_key[key]
    found = quick.compute(given, e.problem_md)
    assert found is not None and expect in solver.answer_text(found.markdown)
    assert expect in e.solution_md


def test_a_quick_z_test_uses_the_books_p_value_and_a_paired_test_works_from_the_differences():
    z = quick.compute(dict(type="test_mean", mean=49, mu0=50, sd=5, n=36, alpha=0.05, tails="two", sigma_known=True),
                      "mean 49, mu 50, sigma 5, 36 observations, .05 significance level, H0: mu = 50")
    assert "-1.2" in z.markdown and "do not reject $H_0$" in z.markdown and "0.2302 (exact: 0.2301)" in z.markdown
    paired = quick.compute(dict(type="test_paired", differences=[2, 3, 1, 4, 5], alpha=0.05, tails="right"),
                           "differences 2 3 1 4 5 at the .05 significance level, H1 greater")
    assert "$\\bar{d} = 3$" in paired.markdown and "$s_d = 1.5811$" in paired.markdown and "reject $H_0$" in paired.markdown


def test_the_quick_way_refuses_what_it_cannot_do_safely():
    assert quick.compute({**GIVEN, "n": 50}, PROBLEM) is None                     # a number the problem doesn't have
    assert quick.compute({"type": "test_two_means", "mean1": 5, "sd1": 1, "n1": 10, "mean2": 4, "sd2": 1, "n2": 10,
                          "alpha": 0.05, "tails": "two"}, "5 1 10 4 1 10 .05") is None      # pool or not: not said
    assert quick.compute({"type": "other"}, PROBLEM) is None
    assert quick.candidate(PROBLEM)
    assert not quick.candidate(PROBLEM + " Explain what it means.")                # more is asked than numbers
    assert not quick.candidate("(a) Find it. (b) Find the 95 percent confidence interval.")
    assert not quick.candidate("There are 300 welders. A sample of 30 ... 95 percent confidence interval.")


def test_a_quick_answer_comes_from_the_models_copy_of_the_numbers_and_waits_for_its_recheck(books):
    _, index = books
    with FakeOllama(MODELS, replies=[json.dumps(GIVEN)]) as fake:
        turn = session.Turn(session.Source("typed", text=PROBLEM), index, fake.url, pace=0)
        answers, events = _run(turn)
        assert len(fake.requests) == 1                                       # one short reply, no solving rounds
    assert "21.53 to 24.47" in answers[0] and turn.answers[0]["from"] == "quick:ci_mean"
    assert [p.by for p in turn.pending] == ["quick"]


def test_a_copy_with_an_invented_number_goes_to_the_full_solver(books):
    _, index = books
    solves = [{"text": "**Given:** n=64.", "calls": ["23 + 1.96 * 6 / sqrt(64)"]}, "**Answer:** 24.47"]
    with FakeOllama(MODELS, replies=[json.dumps({**GIVEN, "n": 50})] + solves) as fake:
        turn = session.Turn(session.Source("typed", text=PROBLEM), index, fake.url, pace=0)
        _run(turn)
    assert turn.answers[0]["from"].startswith("solver:")


# ----------------------------------------------------------------------------------------- numbers and books --
def test_an_exercise_can_be_named_by_its_number():
    assert session.reference("9.5") == ("", "9.5") and session.reference("Lind 9.5") == ("lind", "9.5")
    assert session.reference("exercise 09.50 from Walpole") == ("walpole", "9.50")
    assert session.reference("ex. 12.3?") == ("", "12.3") and session.reference("9.5 is a number I like") is None
    assert session.reference("4.10", need_book=True) is None and session.reference("lind 4.10", True) == ("lind", "4.10")


def _typed(index, text, prefer=""):
    turn = session.Turn(session.Source("typed", text=text), index, "http://127.0.0.1:9", pace=0, prefer=prefer)
    return turn, *_run(turn)


def test_a_typed_number_answers_or_asks_which_book(books):
    _, index = books
    turn, answers, events = _typed(index, "lind 9.5")
    assert answers[0].startswith("**Problem Lind 9.5.**") and "Matches Lind Appendix C" in answers[0]
    turn, answers, events = _typed(index, "9.5")                                    # both books have it
    assert answers == [] and [label for label, _ in turn.choices] == ["Walpole 9.5", "Lind 9.5"] or \
        sorted(label for label, _ in turn.choices) == ["Lind 9.5", "Walpole 9.5"]
    assert [e[0] for e in events].count("choose") == 1
    turn, answers, _ = _typed(index, "9.5", prefer="lind")                           # my book settles it
    assert answers[0].startswith("**Problem Lind 9.5.**")
    turn, answers, _ = _typed(index, "99.9")
    assert "I don't have Exercise 99.9 of Lind or Walpole" in answers[0]
    turn, answers, _ = _typed(index, "lind 3.14")                                    # only Walpole has chapter 3
    assert "Exercise 3.14 of Lind" in answers[0]


def test_the_chosen_option_is_answered_from_the_book_it_names(books):
    _, index = books
    chosen = session.Turn(session.Source("Problem", text="whatever the card held", label="Walpole 9.5"), index,
                          "http://127.0.0.1:9", pace=0)
    answers, _ = _run(chosen)
    assert answers[0].startswith("**Problem Walpole 9.5.**") and "From Walpole, 9th edition" in answers[0]


def test_the_closest_chapters_table_rules_go_to_the_solver(books):
    _, index = books
    e = books[0].get("9.5", "lind")
    variant = (e.problem_md.replace("**Problem:**", "", 1).replace("49", "64").replace("$5", "$6")
               .replace("$\\bar{X} = \\$20$", "$\\bar{X} = \\$23$").replace("95 percent", "90 percent"))   # all new numbers
    solves = [{"text": "**Given:** n=50.", "calls": ["21 + 1.96 * 5 / sqrt(50)"]}, "**Answer:** 22.39"]
    with FakeOllama(MODELS, replies=solves) as fake:
        turn = session.Turn(session.Source("typed", text=variant), index, fake.url, pace=0)
        _run(turn)
        prompt = fake.requests[0]["messages"][1]["content"]
    assert "Follow its table rules" in prompt and "Appendix B.1" in prompt and "ztable" in fake.requests[0]["messages"][0]["content"]
