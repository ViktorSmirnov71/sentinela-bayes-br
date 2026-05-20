"""Smoke tests for evaluation metrics — caught real bugs in calibration math before."""
from __future__ import annotations

import numpy as np

from tailings_risk.evaluation.metrics import (
    brier_decomposition,
    expected_calibration_error,
)


def test_perfectly_calibrated_constant_predictor_has_zero_resolution():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, size=1000)
    p = np.full_like(y, fill_value=y.mean(), dtype=float)
    d = brier_decomposition(y, p)
    # constant predictor: resolution = 0 exactly
    assert d["resolution"] == 0.0
    # reliability should also be ~0 since we predicted the base rate
    assert d["reliability"] < 1e-9


def test_perfect_predictor_has_zero_ece():
    y = np.array([0, 0, 1, 1, 1])
    p = y.astype(float)
    assert expected_calibration_error(y, p) == 0.0
