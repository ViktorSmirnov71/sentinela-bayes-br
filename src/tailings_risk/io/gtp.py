"""Global Tailings Portal loader — GRID-Arendal global TSF disclosure database."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load(path: Path) -> pd.DataFrame:
    """Load GTP CSV into canonical schema.

    Used as a cross-validation source for SIGBM metadata and as the international
    reference cohort for generalisation experiments.
    """
    raise NotImplementedError
