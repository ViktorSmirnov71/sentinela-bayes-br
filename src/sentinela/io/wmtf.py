"""World Mine Tailings Failures loader — Bowker & Chambers event database.

Distribution is spreadsheet-based and requires manual download from
worldminetailingsfailures.org. Place the spreadsheet at
data/raw/wmtf/wmtf_<date>.xlsx and use load() to canonicalise.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load(path: Path) -> pd.DataFrame:
    """Load WMTF spreadsheet into canonical schema.

    Canonical columns: event_id, date, country, mine, operator,
    construction_method, severity_bowker_chambers, volume_released_m3,
    fatalities, lat, lon, notes.
    """
    raise NotImplementedError
