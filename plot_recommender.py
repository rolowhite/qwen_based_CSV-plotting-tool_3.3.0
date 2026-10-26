"""plot_recommender: the CSV Plot Studio plot recommender, importable from the repo root.

    from plot_recommender import recommend, profile_column
    profiles, suggestions, warnings = recommend(df, target="survived")
    print(profile_column(df["fare"]))

    python plot_recommender.py data.csv [target]

The engine lives in plotstudio/core (the reviewed, bug-fixed version of the original file); this
module only re-exports it, so scripts written for the original API keep working.
"""
from plotstudio.core.plot_recommender import Note, Suggestion, main, recommend
from plotstudio.core.profiler import ColumnProfile, profile_column

__all__ = ["ColumnProfile", "Note", "Suggestion", "profile_column", "recommend"]

if __name__ == "__main__":
    raise SystemExit(main())
