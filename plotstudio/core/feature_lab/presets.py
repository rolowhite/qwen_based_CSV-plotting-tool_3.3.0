"""Built-in patterns for the regex_extract generator, and known orders for ordinal encoding.

Dataset-specific knowledge lives here (and only here): the core code never names a column.
A preset is offered for a text column only when its pattern matches most of the values.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Preset:
    key: str
    title: str               # shown in the list, e.g. "title from name"
    pattern: str             # one group in brackets: the part that is kept
    output: str              # the new column's name ("{col}" = the source column)
    why: str
    min_match: float = 0.8   # share of the filled values the pattern must match
    max_groups: int = 30     # more distinct values than this (after grouping rare ones): not offered
    min_share: float = 0.01  # values rarer than this become "Other" (learned on the training rows)
    mapping: dict = field(default_factory=dict)   # spellings of the same value
    kinds: tuple = ("text", "id", "category")      # the column kinds it is tried on


PRESETS = [
    Preset(
        key="title_from_name", title="title from name", pattern=r",\s*([^.]+)\.", output="title",
        why="The title inside a full name such as 'Braund, Mr. Owen Harris' (Mr, Mrs, Miss, Master; rare ones "
            "become Other). It carries sex, age group and rank in one word.",
        mapping={"Mlle": "Miss", "Ms": "Miss", "Mme": "Mrs"}),
    Preset(
        key="first_letter", title="first letter", pattern=r"^\s*([A-Za-z])", output="{col}_letter",
        why="The first letter of a code, e.g. the deck of a cabin 'C85' is C. Codes often start with the group "
            "they belong to.", min_match=0.6, kinds=("id", "category")),
]

# value sets with a natural order (lower case); a category whose values all fall in one of these
# is encoded as 0, 1, 2 ... in this order instead of one 0/1 column per value
ORDERS = [
    ["very low", "low", "medium", "high", "very high"],
    ["low", "mid", "high"],
    ["small", "medium", "large", "extra large"],
    ["xs", "s", "m", "l", "xl", "xxl"],
    ["never", "rarely", "sometimes", "often", "always"],
    ["very bad", "bad", "poor", "fair", "average", "good", "very good", "excellent"],
    ["strongly disagree", "disagree", "neutral", "agree", "strongly agree"],
    ["none", "primary", "secondary", "bachelor", "master", "doctorate"],
    ["cold", "cool", "warm", "hot"],
    ["first", "second", "third"],
    ["1st", "2nd", "3rd"],
]


def known_order(values) -> list | None:
    """The values in their natural order if they all belong to one known order, else None."""
    lower = {str(v).strip().lower(): v for v in values}
    if len(lower) < 3:
        return None
    for order in ORDERS:
        if set(lower) <= set(order):
            return [lower[w] for w in order if w in lower]
    return None
