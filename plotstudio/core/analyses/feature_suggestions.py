"""Analysis plugin: the Feature Lab's suggestions (new features ranked by how much they add)."""
from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

NAME = "feature_suggestions"
TITLE = "Feature suggestions"


def run(df: pd.DataFrame, target: Optional[str] = None, pipeline=None, *, infos: Optional[dict] = None,
        overrides: Optional[dict] = None, progress: Optional[Callable[[float, str], None]] = None):
    """New features for df (the training table after the pipeline's steps), measured against target.

    -> feature_lab.LabResult (imported here: the Lab itself builds on analyses.base)."""
    from ..feature_lab import suggest_features
    return suggest_features(df, target, pipeline=pipeline, infos=infos, overrides=overrides, progress=progress)
