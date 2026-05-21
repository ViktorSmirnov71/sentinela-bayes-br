"""Synthetic Sentinel-1 LOS time series with documented ground-truth properties.

Used by tests to verify the feature extractors recover the signal that
post-Brumadinho papers (Grebby 2021, Carlà 2019) identified in real data:

    stable baseline -> creep -> accelerating creep -> failure

The generator returns numpy arrays in the same format as the real-data
pipeline (times in days since the first observation; LOS displacement in mm,
negative = subsidence) so tests can be sharp about expected values.
"""
from __future__ import annotations

import numpy as np


def brumadinho_like(
    *,
    revisit_days: int = 12,
    total_months: int = 60,
    months_baseline: int = 36,
    months_creep: int = 12,
    months_accel: int = 12,
    creep_mm_per_year: float = -24.0,
    accel_mm_per_year2: float = -120.0,
    atmosphere_noise_mm: float = 3.0,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic LOS displacement series with a known precursor.

    Three regimes:
      [0, months_baseline)              white noise only.
      [months_baseline, +months_creep)  linear creep at `creep_mm_per_year`.
      [..., +months_accel)              additional quadratic acceleration term.

    Returns
    -------
    times_days, los_mm
    """
    assert total_months == months_baseline + months_creep + months_accel
    rng = np.random.default_rng(seed)

    n = int(total_months * 30.4375 / revisit_days)
    times_days = np.arange(n) * revisit_days
    los = np.zeros(n)

    creep_start = months_baseline * 30.4375
    accel_start = (months_baseline + months_creep) * 30.4375

    creep_per_day = creep_mm_per_year / 365.25
    accel_per_day2 = accel_mm_per_year2 / (365.25 ** 2)

    in_creep = times_days >= creep_start
    in_accel = times_days >= accel_start

    los[in_creep] += creep_per_day * (times_days[in_creep] - creep_start)
    dt_a = times_days[in_accel] - accel_start
    los[in_accel] += 0.5 * accel_per_day2 * (dt_a ** 2)

    los += rng.normal(0.0, atmosphere_noise_mm, size=n)
    return times_days, los


def stable_reference(
    *,
    n: int,
    revisit_days: int = 12,
    atmosphere_noise_mm: float = 3.0,
    seed: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Reference series at a geomorphically stable nearby point (noise only)."""
    rng = np.random.default_rng(seed)
    times_days = np.arange(n) * revisit_days
    los = rng.normal(0.0, atmosphere_noise_mm, size=n)
    return times_days, los
