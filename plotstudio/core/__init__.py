"""All data analysis of CSV Plot Studio. Nothing in this package imports tkinter.

Every function returns plain dataclasses, so it can be used (and tested) without a window:

    from plotstudio.core import recommend
    profiles, suggestions, warnings = recommend(df, target="survived")

    from plotstudio.core.analyses import run
    result = run("plot_suggestions", df, target="survived")      # -> PlotSuggestions

* ``profiler``          what kind of data each column holds, plus its quality numbers
* ``assoc``             how strongly two columns are linked (r / ρ, η, Cramér's V, trend, AUC)
* ``plot_recommender``  which plots to draw first, each with a one-line reason
* ``overrides``         "treat this column as a category": relabelling without changing data
* ``analyses``          plugin analyses, each a module with ``run(df, **opts) -> Result``
"""
from .plot_recommender import Note, Suggestion, recommend
from .profiler import ColumnProfile, profile_column, profile_frame

__all__ = ["ColumnProfile", "Note", "Suggestion", "profile_column", "profile_frame", "recommend"]
