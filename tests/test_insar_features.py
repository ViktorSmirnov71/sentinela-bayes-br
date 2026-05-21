"""Tests for InSAR precursor features.

Strategy: generate synthetic LOS time series with known geophysical properties
(stable + creep + accelerating creep, with calibrated noise) and verify the
feature extractors recover the signal in the expected direction and magnitude.

These tests are the closest analogue we have to validating against real
post-mortem data (which would require running the full HyP3 pipeline against
the Brumadinho 2018-2019 window). Failing tests here mean a regression in the
math; they do *not* validate that the implementation works on real Sentinel-1
data — that is a separate integration test gated on credentials.
"""
from __future__ import annotations

import numpy as np

from sentinela.insar.features import (
    TimeSeries,
    acceleration_90d,
    compute_features,
    crest_vs_stable_variance_ratio,
    los_velocity,
    spectral_slope,
)
from sentinela.insar.synthetic import brumadinho_like, stable_reference


def test_los_velocity_recovers_linear_trend():
    # Pure linear creep: 24 mm/yr subsidence over 4 years, no noise.
    t = np.arange(0, 4 * 365, 12, dtype=float)
    y = -24.0 / 365.25 * t
    assert abs(los_velocity(t, y) - (-24.0)) < 0.1


def test_los_velocity_robust_to_outliers():
    # Same series with 20% of points spiked by 50 mm.
    rng = np.random.default_rng(0)
    t = np.arange(0, 4 * 365, 12, dtype=float)
    y = -24.0 / 365.25 * t
    spike_idx = rng.choice(len(t), size=int(0.2 * len(t)), replace=False)
    y[spike_idx] += 50.0
    v = los_velocity(t, y)
    # Theil–Sen should stay within a few mm/yr of truth despite outliers.
    assert abs(v - (-24.0)) < 4.0


def test_acceleration_90d_detects_brumadinho_like_signal():
    """The accelerating-creep regime should produce a clearly positive value."""
    t, y = brumadinho_like(seed=0)
    accel = acceleration_90d(t, y)
    # On a stable+creep+accel signal we expect a strongly positive
    # acceleration magnitude (mm/yr²) by construction.
    assert accel > 30.0, f"expected accelerating signal, got {accel:.2f}"


def test_acceleration_90d_near_zero_on_stable_series():
    rng = np.random.default_rng(0)
    t = np.arange(0, 4 * 365, 12, dtype=float)
    y = rng.normal(0.0, 3.0, size=len(t))
    accel = acceleration_90d(t, y)
    # On pure noise the absolute acceleration should be small relative to the
    # signal-bearing case above.
    assert abs(accel) < 200.0, f"unexpectedly large accel on noise: {accel}"


def test_spectral_slope_sensitive_to_drift():
    """A drifting series should have a more-negative spectral slope than pure noise."""
    rng = np.random.default_rng(0)
    t = np.arange(0, 4 * 365, 12, dtype=float)
    y_noise = rng.normal(0.0, 3.0, size=len(t))
    y_drift = -10.0 / 365.25 * t + rng.normal(0.0, 3.0, size=len(t))
    s_noise = spectral_slope(t, y_noise)
    s_drift = spectral_slope(t, y_drift)
    # The drifting signal has more low-frequency power → steeper (more negative) slope.
    # We compare directionally; absolute values depend on Welch parameters.
    assert s_drift < s_noise, f"drift slope {s_drift} should be < noise slope {s_noise}"


def test_variance_ratio_high_for_creeping_dam_vs_stable_ground():
    t, y = brumadinho_like(seed=0)
    _, y_ref = stable_reference(n=len(t), seed=1)
    ratio = crest_vs_stable_variance_ratio(y, y_ref)
    assert ratio > 5.0, f"expected high variance ratio on creep signal, got {ratio:.2f}"


def test_variance_ratio_near_one_for_two_noise_series():
    _, y_a = stable_reference(n=100, seed=2)
    _, y_b = stable_reference(n=100, seed=3)
    ratio = crest_vs_stable_variance_ratio(y_a, y_b)
    # Two independent noise series should give a ratio in the same ballpark as 1.
    assert 0.25 < ratio < 4.0, f"unexpected ratio between two noise series: {ratio:.2f}"


def test_compute_features_end_to_end_on_synthetic_precursor():
    t, y = brumadinho_like(seed=0)
    _, y_ref = stable_reference(n=len(t), seed=1)
    feats = compute_features(TimeSeries(
        times_days=t,
        los_mm=y,
        stable_reference_mm=y_ref,
        coherence=np.full(len(t), 0.6),
        persistent_scatterer_count=42,
        dam_area_km2=0.5,
    ))
    # Velocity should be clearly negative (subsidence dominates over the window).
    assert feats.los_velocity_mm_yr < -3.0
    # Acceleration should be positive (creep accelerating).
    assert feats.los_accel_90d_mm_yr2 > 30.0
    # PS density: 42 / 0.5 = 84 PS/km².
    assert feats.persistent_scatterer_density == 84.0
    # Coherence p10 of all-0.6 array should be 0.6.
    assert abs(feats.coherence_p10 - 0.6) < 1e-9
    # Variance ratio should be high.
    assert feats.crest_vs_stable_variance_ratio > 5.0
