"""Generate a synthetic SIGBM-shaped fixture for end-to-end pipeline development.

The fixture is NOT real SIGBM data. It matches the canonical schema and the
real population's gross marginals (state distribution heavily weighted toward
MG, ~60% iron ore, ~30% upstream construction, height/volume log-normal) so
the pipeline produces sensible numbers, but no individual row corresponds to
any real dam.

Two of the synthetic rows are deliberately constructed as fixture stand-ins
for the historical reference failures (Fundão 2015, B1 Brumadinho 2019),
labelled in `data/external/brazilian_failures.csv` so that the retrospective
RQ4 test can run end-to-end against the fixture before real SIGBM data is
ingested. They use distinctive `dam_id`s prefixed with `FIX-REF-` to make
their fictional origin obvious.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .sigbm import CANONICAL_COLUMNS

# Real SIGBM marginals (approximate, from public ANM annual reports).
STATE_WEIGHTS = {
    "MG": 0.40, "PA": 0.13, "MT": 0.08, "BA": 0.07, "GO": 0.07,
    "SP": 0.05, "AP": 0.04, "RS": 0.03, "MS": 0.03, "AM": 0.03,
    "RO": 0.02, "PR": 0.02, "SC": 0.02, "TO": 0.01,
}
ORE_WEIGHTS = {
    "iron": 0.58, "gold": 0.12, "bauxite": 0.06, "copper": 0.05,
    "manganese": 0.04, "phosphate": 0.04, "niobium": 0.02, "other": 0.09,
}
METHOD_WEIGHTS = {
    "upstream": 0.30, "downstream": 0.32, "centerline": 0.18,
    "dyke": 0.10, "unknown": 0.10,
}


def make_fixture(n: int = 120, seed: int = 0) -> pd.DataFrame:
    """Return a synthetic SIGBM table with `n` dams plus 2 reference fixtures."""
    rng = np.random.default_rng(seed)
    snapshot = date(2026, 3, 31)

    states = rng.choice(list(STATE_WEIGHTS), size=n, p=list(STATE_WEIGHTS.values()))
    ores = rng.choice(list(ORE_WEIGHTS), size=n, p=list(ORE_WEIGHTS.values()))
    methods = rng.choice(list(METHOD_WEIGHTS), size=n, p=list(METHOD_WEIGHTS.values()))
    heights = np.clip(rng.lognormal(mean=3.0, sigma=0.7, size=n), 5, 200)
    volumes = np.clip(rng.lognormal(mean=14.0, sigma=1.5, size=n), 1e4, 5e8)
    ages = np.clip(rng.gamma(shape=2.0, scale=10.0, size=n), 0, 80)
    cri = rng.choice([1, 2, 3], size=n, p=[0.45, 0.40, 0.15])
    dpa = rng.choice([1, 2, 3], size=n, p=[0.20, 0.40, 0.40])
    emergency = rng.choice([0, 1, 2, 3], size=n, p=[0.92, 0.05, 0.02, 0.01])

    rows = []
    for i in range(n):
        rows.append({
            "dam_id": f"FIX-{i+1:04d}",
            "name": f"Fixture Dam {i+1}",
            "operator_cnpj": f"{rng.integers(10**13, 10**14):014d}",
            "operator_name": f"Operator {rng.integers(1, 30):02d} Mineracao S.A.",
            "lat": _state_centroid_lat(states[i]) + rng.normal(0, 0.4),
            "lon": _state_centroid_lon(states[i]) + rng.normal(0, 0.4),
            "state": states[i],
            "municipality": f"Municipality {rng.integers(1, 850):03d}",
            "construction_method": methods[i],
            "height_m": float(heights[i]),
            "volume_m3": float(volumes[i]),
            "age_years": float(ages[i]),
            "cri": int(cri[i]),
            "dpa": int(dpa[i]),
            "ore_type": ores[i],
            "status_active": True,
            "emergency_level": int(emergency[i]),
            "snapshot_date": snapshot,
        })

    # Reference-failure stand-ins (Fundão 2015, B1 Brumadinho 2019).
    rows.extend([
        {
            "dam_id": "FIX-REF-FUNDAO",
            "name": "Fixture Fundao (stand-in)",
            "operator_cnpj": "16628281000161",
            "operator_name": "Samarco Mineracao S.A.",
            "lat": -20.21, "lon": -43.46,
            "state": "MG", "municipality": "Mariana",
            "construction_method": "upstream",
            "height_m": 110.0, "volume_m3": 55_000_000.0, "age_years": 7.0,
            "cri": 2, "dpa": 3, "ore_type": "iron",
            "status_active": True, "emergency_level": 3,
            "snapshot_date": snapshot,
        },
        {
            "dam_id": "FIX-REF-B1",
            "name": "Fixture B1 Corrego do Feijao (stand-in)",
            "operator_cnpj": "33592510000154",
            "operator_name": "Vale S.A.",
            "lat": -20.12, "lon": -44.13,
            "state": "MG", "municipality": "Brumadinho",
            "construction_method": "upstream",
            "height_m": 86.0, "volume_m3": 12_000_000.0, "age_years": 43.0,
            "cri": 2, "dpa": 3, "ore_type": "iron",
            "status_active": True, "emergency_level": 3,
            "snapshot_date": snapshot,
        },
    ])

    return pd.DataFrame(rows, columns=list(CANONICAL_COLUMNS))


# Rough Brazilian-state centroids (good enough for fixture geocoding).
_STATE_LATLON = {
    "MG": (-18.10, -44.38), "PA": (-3.93, -52.48), "MT": (-12.64, -55.42),
    "BA": (-12.96, -41.71), "GO": (-15.83, -49.84), "SP": (-22.19, -48.79),
    "AP": (0.92, -52.00),   "RS": (-30.17, -53.50), "MS": (-20.51, -54.54),
    "AM": (-4.15, -64.04),  "RO": (-10.83, -63.34), "PR": (-24.79, -51.76),
    "SC": (-27.45, -50.95), "TO": (-9.97, -48.32),
}


def _state_centroid_lat(state: str) -> float:
    return _STATE_LATLON.get(state, (-15.0, -55.0))[0]


def _state_centroid_lon(state: str) -> float:
    return _STATE_LATLON.get(state, (-15.0, -55.0))[1]


def write_fixture(path: Path, n: int = 120, seed: int = 0) -> Path:
    df = make_fixture(n=n, seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
