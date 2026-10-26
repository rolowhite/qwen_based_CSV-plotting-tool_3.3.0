"""Encoding helper: how a model should read each category column (also as pipeline steps).

* fewer than 10 groups                 -> one-hot (one 0/1 column per group)
* groups with a natural order          -> ordinal (0, 1, 2 ... in that order)
* 10 or more groups                    -> target encoding computed OUT-OF-FOLD, with a warning:
  each row gets the target mean of its group from the other folds, so it never sees its own
  target (plain target means would leak the answer into the feature)
"""
from __future__ import annotations

from ..pipeline import Step
from . import scoring
from .base import FeatureSuggestion
from .presets import known_order

ONE_HOT_LIMIT = 10
FOLDS = 5
SMOOTHING = 10

TE_WARNING = ("Target encoding uses the target, so it is computed out-of-fold: the rows are split into 5 folds and "
              "each row gets the mean of its group from the other 4. A row never sees its own answer, so the "
              "model's score stays honest. New data (test) gets the means of all training rows.")


def suggest_encodings(ctx) -> list:
    """One encoding suggestion per category column that a model can't read as it is."""
    out = []
    df, target = ctx.df, ctx.target
    for c in df.columns:
        if c == target.name or ctx.kind(c) != "category":
            continue
        s = df[c]
        if scoring.is_number(s):
            continue                       # numbers with few values: already numbers, in order
        if any(step.op in ("onehot", "ordinal", "target_enc") and c in step.cols for step in ctx.pipeline):
            continue
        groups = s.dropna().unique().tolist()
        if len(groups) < 2:
            continue
        order = known_order(groups)
        if order:
            step = Step("ordinal", [c], ctx.new_name(f"{c}_order"), {"order": order})
            why = (f"{c}: ordinal. Its groups have a natural order ({' < '.join(map(str, order))}), "
                   "so 0, 1, 2 ... keeps that order in one column.")
        elif len(groups) < ONE_HOT_LIMIT:
            step = Step("onehot", [c], c)
            why = f"{c}: one-hot. {len(groups)} groups -> one 0/1 column each (fewer than {ONE_HOT_LIMIT} groups)."
        elif target.task in ("binary", "regression"):
            params = {"target": target.name, "k": FOLDS, "smoothing": SMOOTHING, "seed": 0}
            if target.task == "binary":
                params["positive"] = target.positive
            step = Step("target_enc", [c], ctx.new_name(f"{c}_te"), params)
            why = (f"{c}: target encoding (out-of-fold). {len(groups)} groups are too many for one-hot, so each "
                   f"group becomes the mean of {target.word()} in it.")
        else:
            continue                       # many groups and a target with 3+ classes: nothing simple fits
        s_ = FeatureSuggestion(step=step, generator="encoding", title=f"encode {c}", sources=[c], why=why,
                               kind="encoding")
        if step.op == "target_enc":
            s_.warning = TE_WARNING
        out.append(s_)
    return out
