"""Assemble the per-dam-per-month feature table.

Joins SIGBM cohort × monthly grid with InSAR, climate, and ops feature blocks.
The output is the single artefact every downstream experiment consumes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class FeatureTableSpec:
    start_month: str
    end_month: str | None
    include_insar: bool
    include_climate: bool
    include_ops: bool


def build_feature_table(spec: FeatureTableSpec, paths: dict[str, Path]) -> pd.DataFrame:
    """Materialise the (dam_id, month) feature table.

    Output columns (canonical):
        dam_id, month,
        construction_method, height_m, volume_m3, age_years, cri, dpa, ore_type,
        los_velocity_mm_yr, los_accel_90d_mm_yr2, spectral_slope,
        crest_vs_stable_variance_ratio, persistent_scatterer_density, coherence_p10,
        rain_30d_mm, rain_90d_mm, rain_365d_mm, spi3, spi6, api,
        soil_moisture, et_anomaly,
        emergency_level, inactive_flag, months_since_inspection
    """
    raise NotImplementedError
