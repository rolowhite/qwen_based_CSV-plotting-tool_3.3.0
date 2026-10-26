"""Old name of ``plotstudio.core`` (2.1). Kept so ``from plotstudio.eda import recommend`` and
``python -m plotstudio.eda`` keep working; new code imports ``plotstudio.core``."""
from ..core import ColumnProfile, Note, Suggestion, profile_column, profile_frame, recommend

__all__ = ["ColumnProfile", "Note", "Suggestion", "profile_column", "profile_frame", "recommend"]
