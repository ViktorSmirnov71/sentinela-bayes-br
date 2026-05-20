"""Loader for Brazilian-failure event labels.

Until the full World Mine Tailings Failures spreadsheet is obtained from
worldminetailingsfailures.org (manual download), the project uses a curated
Brazilian-events table at `data/external/brazilian_failures.csv` as its
canonical label source. That CSV is citation-anchored and small enough to live
in the repository.

When the full WMTF spreadsheet is available, drop it at `data/raw/wmtf/` and
extend `load_wmtf_full` to canonicalise it to the same schema as
`load_brazilian_failures`. The downstream feature-building code only depends
on the canonical schema.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CANONICAL_LABEL_COLUMNS: tuple[str, ...] = (
    "event_id",
    "date",
    "state",
    "municipality",
    "mine",
    "operator",
    "dam_name",
    "construction_method",
    "ore",
    "severity_bowker_chambers",
    "fatalities",
    "volume_released_m3",
    "fixture_dam_id",
    "real_sigbm_dam_id",
    "source_url",
    "notes",
)


def load_brazilian_failures(path: Path | str) -> pd.DataFrame:
    """Load the curated Brazilian-failure events table.

    Parses dates, coerces numeric columns, and validates the canonical schema.
    """
    df = pd.read_csv(path)
    missing = [c for c in CANONICAL_LABEL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"brazilian_failures.csv missing columns: {missing}")
    df["date"] = pd.to_datetime(df["date"])
    df["severity_bowker_chambers"] = pd.to_numeric(df["severity_bowker_chambers"], errors="raise")
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0).astype(int)
    df["volume_released_m3"] = pd.to_numeric(df["volume_released_m3"], errors="coerce").fillna(0.0)
    return df[list(CANONICAL_LABEL_COLUMNS)]


def load_wmtf_full(path: Path | str) -> pd.DataFrame:  # pragma: no cover
    """Reserved for the full WMTF spreadsheet — not yet wired."""
    raise NotImplementedError(
        "Manual WMTF download required. Place file under data/raw/wmtf/ and "
        "implement canonicalisation to match CANONICAL_LABEL_COLUMNS."
    )
