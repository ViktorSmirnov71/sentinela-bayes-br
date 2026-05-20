"""SIGBM loader — ANM mining-dam registry.

Primary access path is Base dos Dados (BigQuery-mirrored, harmonized columns).
Fallback is the public ANM CSV at app.anm.gov.br/sigbm/publico.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SIGBM_BD_TABLE = "basedosdados.br_anm_sigbm.barragens"


def fetch(dest_dir: Path) -> Path:
    """Download the latest SIGBM snapshot to dest_dir / sigbm.parquet."""
    raise NotImplementedError(
        "Implement Base dos Dados pull. Requires BD_BILLING_PROJECT env var."
    )


def load(path: Path) -> pd.DataFrame:
    """Load a previously fetched SIGBM parquet into a canonical schema.

    Canonical columns: dam_id, name, operator_cnpj, lat, lon, construction_method,
    height_m, volume_m3, age_years, cri, dpa, ore_type, status_active,
    emergency_level, snapshot_date.
    """
    raise NotImplementedError
