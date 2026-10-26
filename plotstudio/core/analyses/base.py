"""What every analysis returns."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Result:
    """Base of every analysis result (each analysis adds its own fields).

    rows_used    rows the numbers were computed on (a sample for big files)
    total_rows   rows in the data
    seconds      how long the analysis took
    """
    rows_used: int
    total_rows: int
    seconds: float = 0.0

    @property
    def sampled(self) -> bool:
        return self.rows_used < self.total_rows

    @property
    def sample_note(self) -> str:
        """'computed on a 50,000-row sample' for big files, else ''."""
        return f"computed on a {self.rows_used:,}-row sample" if self.sampled else ""
