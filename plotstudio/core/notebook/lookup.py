"""Find the library exercise a problem text belongs to.

Three signals, combined into one 0-1 score per exercise:
  words     TF-IDF cosine similarity of the words (LaTeX commands removed)
  numbers   the share of the query's numbers that the exercise also has, weighted by how rare each number
            is in the library (so 1, 2 and 0.5 count for little and 0.0129 counts for a lot)
  label     the text starts with an exercise number ("3.31 ...", "Exercise 3.31", "Ex. 3.31") that the
            library has. It adds weight only when the words agree; a number alone never outranks the text.
The top 3 are returned with a status: "match" (one clear winner), "choose" (let the user pick) or "none".
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

from .library import Exercise, Library

# thresholds: tune these from the Phase 5 evaluation, not by guessing
HIGH = 0.60          # at or above this, with MARGIN over #2, the top candidate is shown directly
LOW = 0.25           # below this the problem is "not in the library"
MARGIN = 0.10        # how far #1 must be ahead of #2 to be shown without asking
WORD_WEIGHT = 0.6    # the rest is the numbers' share (words only when the query has no numbers)
LABEL_BONUS = 0.35   # added when the text's leading exercise number matches and the words agree
LABEL_MIN_WORDS = 0.20
NO_PROBLEM_FACTOR = 0.85   # an exercise without a **Problem:** block is matched on its solution: trust it less
TOP = 3

STOPWORDS = frozenset("""a an and are as at be by for from has have if in is it its of on or that the this to was
were what which with will would can do does find let given suppose assume use using each than then there these
those their they be been being into over under also any all not no so such we you your our""".split())

_FRAC_TEX = re.compile(r"\\[dt]?frac\s*(?:\{\s*(-?\d+)\s*\}|(\d))\s*(?:\{\s*(\d+)\s*\}|(\d))")   # \frac{1}{4}, \tfrac12
_TEX_CMD = re.compile(r"\\[A-Za-z]+")
_MENTION = re.compile(r"\b(?:Exercises?|Ex\.)\s*\d+\.\d+(?:\s*(?:and|,|–|-)\s*\d+\.\d+)*", re.I)
_REF = re.compile(r"(\d+)\.(\d+)")
_LABEL = re.compile(r"^\s*(?:\*\*)?(?:(?:Exercise|Ex\.?|Problem)\s*)?(\d{1,2})\.(\d{1,3})\b(?!\.\d)", re.I)
# 20,000 is one number, but inside a list written without spaces ("33,56,122,83") the commas separate values
_NUMBER = re.compile(r"(?<![\w.])(-?(?:(?<!\d,)\d{1,3}(?:,\d{3})+(?!,\d)|\d+)(?:\.\d+)?|-?\.\d+)(?:\s*/\s*(\d+))?"
                     r"(?![\w])")
_WORD = re.compile(r"[a-z]+")


# ------------------------------------------------------------------------------------------- tokens --
def _norm_decimal(text: str) -> str:
    """'20,000' -> '20000', '.50' -> '0.5', '3.0' -> '3', '-0.250' -> '-0.25'."""
    t = text.replace(",", "")
    neg = t.startswith("-")
    t = t.lstrip("-")
    if t.startswith("."):
        t = "0" + t
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    t = t.lstrip("0") or "0"
    if t.startswith("."):
        t = "0" + t
    return ("-" + t) if neg and t != "0" else t


def numbers(text: str) -> List[str]:
    """Every number in the text, normalised. A fraction gives both forms: '1/4' -> ['1/4', '0.25'].
    A mention of another exercise gives 'ex3.49'."""
    text = _FRAC_TEX.sub(lambda m: f" {m.group(1) or m.group(2)}/{m.group(3) or m.group(4)} ", text)
    text = _TEX_CMD.sub(" ", text)      # "\le1" and "\le 1" are the same 1 (a letter before a digit hides it)
    text = text.replace("−", "-")  # the minus sign − (the library's tables) is the same as a hyphen-minus
    # "the data of Exercise 3.49" is not a value of this problem, but it tells 3.54 from 3.55: keep it as "ex3.49"
    out = [f"ex{int(a)}.{int(b)}" for m in _MENTION.finditer(text) for a, b in _REF.findall(m.group(0))]
    text = _MENTION.sub(" ", text)
    for m in _NUMBER.finditer(text):
        whole, denominator = m.group(1), m.group(2)
        if denominator is not None and "." not in whole and "," not in whole and int(denominator):
            out.append(f"{_norm_decimal(whole)}/{int(denominator)}")
            value = Fraction(int(whole), int(denominator))
            out.append(_norm_decimal(f"{float(value):.6f}"))
        else:
            out.append(_norm_decimal(whole))
            if denominator is not None:
                out.append(str(int(denominator)))
    return out


def words(text: str) -> List[str]:
    text = _TEX_CMD.sub(" ", text.lower())
    out = []
    for w in _WORD.findall(text):
        if len(w) < 2 or w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]          # shortcut: plural "s" only, no real stemming; upgrade if Phase 5 shows misses
        out.append(w)
    return out


def leading_label(text: str) -> Optional[str]:
    """The exercise number a problem text starts with ('3.31 A ...', 'Exercise 3.31', 'Ex. 3.31'), if any."""
    m = _LABEL.match(text)
    return f"{int(m.group(1))}.{int(m.group(2))}" if m else None


# -------------------------------------------------------------------------------------------- index --
@dataclass(frozen=True)
class Candidate:
    exercise: Exercise
    score: float
    word_score: float
    number_score: float
    shared_numbers: Tuple[str, ...] = ()
    missing_numbers: Tuple[str, ...] = ()     # in the query, not in the exercise
    label_match: bool = False


@dataclass
class LookupResult:
    status: str                                # "match" | "choose" | "none" | "empty"
    candidates: List[Candidate] = field(default_factory=list)
    label: Optional[str] = None                # the exercise number the text started with
    note: str = ""

    @property
    def best(self) -> Optional[Candidate]:
        return self.candidates[0] if self.candidates else None


def _tfidf(tokens: Sequence[str], idf: Dict[str, float]) -> Dict[str, float]:
    counts = Counter(t for t in tokens if t in idf)
    vec = {t: (1 + math.log(c)) * idf[t] for t, c in counts.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}


class Index:
    """Word vectors and number sets of every exercise, built once per library."""

    def __init__(self, library: Library):
        self.library = library
        docs = [e.problem_md or e.solution_md for e in library.exercises]
        self._words = [words(d) for d in docs]
        self._numbers = [set(numbers(d)) for d in docs]
        n = max(1, len(docs))
        df_w = Counter(t for ws in self._words for t in set(ws))
        df_n = Counter(t for ns in self._numbers for t in ns)
        self.idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df_w.items()}
        self.num_idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df_n.items()}
        self._unseen_num_idf = math.log(n + 1)
        self._vecs = [_tfidf(ws, self.idf) for ws in self._words]

    def _num_weight(self, token: str) -> float:
        return self.num_idf.get(token, self._unseen_num_idf)

    def score_all(self, text: str) -> List[Candidate]:
        label = leading_label(text)
        if label is not None:
            text = _LABEL.sub(" ", text, count=1)     # "3.31 A box contains ...": the label is not data
        q_vec = _tfidf(words(text), self.idf)
        q_nums = set(numbers(text))
        total_num = sum(self._num_weight(t) for t in q_nums)
        out = []
        for e, vec, nums in zip(self.library.exercises, self._vecs, self._numbers):
            w = sum(v * vec.get(t, 0.0) for t, v in q_vec.items())
            shared = q_nums & nums
            num = sum(self._num_weight(t) for t in shared) / total_num if total_num else 0.0
            score = WORD_WEIGHT * w + (1 - WORD_WEIGHT) * num if q_nums else w
            is_label = label is not None and e.number == label
            if is_label and (w >= LABEL_MIN_WORDS or not q_vec):
                score = min(1.0, score + LABEL_BONUS) if q_vec else max(score, HIGH)
            if not e.has_problem:
                score *= NO_PROBLEM_FACTOR
            out.append(Candidate(e, round(score, 4), round(w, 4), round(num, 4), tuple(sorted(shared)),
                                 tuple(sorted(q_nums - nums)), is_label))
        # words break ties: two problems that share only small numbers are told apart by their text
        out.sort(key=lambda c: (c.score, c.word_score), reverse=True)
        return out

    def lookup(self, text: str) -> LookupResult:
        if not text.strip() or not self.library.exercises:
            return LookupResult("empty", note="Type or read a problem first." if self.library.exercises
                                else "The library is empty.")
        ranked = self.score_all(text)[:TOP]
        label = leading_label(text)
        top = ranked[0]
        second = ranked[1].score if len(ranked) > 1 else 0.0
        if top.score < LOW:
            status, note = "none", "Not in your library."
        elif top.score >= HIGH and top.score - second >= MARGIN:
            status, note = "match", ""
        else:
            status = "choose"
            note = ("These match about equally well. Pick the right one." if top.score - second < MARGIN
                    else "Not sure. Pick the right one, or none.")
        if label and not any(c.label_match for c in ranked) and self.library.get(label):
            note = (note + " " if note else "") + f"The text starts with {label}, but its words don't match " \
                                                  f"Exercise {label}."
        return LookupResult(status, ranked, label, note)

    def search(self, query: str, limit: int = 30) -> List[Exercise]:
        """Library search box: an exercise number jumps to it, otherwise the best text matches."""
        q = query.strip()
        m = re.fullmatch(r"(?:ex(?:ercise)?\.?\s*)?(\d+)(?:\.(\d*))?", q, re.I)
        if m:
            prefix = f"{int(m.group(1))}." + (m.group(2) or "")
            exact = [e for e in self.library.exercises if e.number == prefix.rstrip(".")]
            starts = [e for e in self.library.exercises if e.number.startswith(prefix) and e not in exact]
            return (exact + starts)[:limit]
        if not q:
            return self.library.exercises[:limit]
        return [c.exercise for c in self.score_all(q)[:limit] if c.word_score > 0]
