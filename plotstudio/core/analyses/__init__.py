"""Analyses as plugins: every module here exposes ``run(df, **opts) -> Result``.

The window looks an analysis up by name, runs it in a background thread and only renders the
result. Add one by writing a module with NAME, TITLE and run(), and listing it below.
"""
from __future__ import annotations

from . import feature_suggestions, plot_suggestions
from .base import Result

ANALYSES = {plot_suggestions.NAME: plot_suggestions, feature_suggestions.NAME: feature_suggestions}


def run(name: str, df, **opts) -> Result:
    """Run the analysis called `name` on df (KeyError for an unknown name)."""
    return ANALYSES[name].run(df, **opts)


__all__ = ["ANALYSES", "Result", "run"]
