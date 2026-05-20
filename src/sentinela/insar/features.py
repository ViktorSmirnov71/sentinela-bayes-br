"""Derive precursor features from per-dam LOS displacement time series.

Feature set is grounded in:
- Grebby et al. 2021 — anomaly variance ratio dam vs. surrounding ground.
- Carlà et al. 2019 — inverse-velocity precursor.
- Macchiarulo et al. 2023 — moisture-corrected displacement.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class InsarFeatures:
    los_velocity_mm_yr: float
    los_accel_90d_mm_yr2: float
    spectral_slope: float
    crest_vs_stable_variance_ratio: float
    persistent_scatterer_density: float
    coherence_p10: float


def los_velocity(times_days: np.ndarray, los_mm: np.ndarray) -> float:
    """Robust linear-trend slope (mm/yr) via Theil–Sen."""
    raise NotImplementedError


def acceleration_90d(times_days: np.ndarray, los_mm: np.ndarray) -> float:
    """Maximum 90-day acceleration in LOS displacement (mm/yr²)."""
    raise NotImplementedError


def spectral_slope(times_days: np.ndarray, los_mm: np.ndarray) -> float:
    """Slope of the displacement-time-series PSD on a log-log axis (Carlà-style)."""
    raise NotImplementedError


def crest_vs_stable_variance_ratio(
    crest_series: np.ndarray, stable_series: np.ndarray
) -> float:
    """Ratio of trailing-window variance of dam-crest displacement to a
    geomorphically stable nearby reference (Grebby-style anomaly indicator)."""
    raise NotImplementedError
