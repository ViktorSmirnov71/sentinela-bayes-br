"""INMET BDMEP loader — Brazilian meteorological station records."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load(path: Path) -> pd.DataFrame:
    """Load INMET station daily CSVs into a stacked dataframe.

    Canonical columns: station_id, date, prec_mm, temp_c, rh_pct, lat, lon.
    """
    raise NotImplementedError
