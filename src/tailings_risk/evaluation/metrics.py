"""Calibration and discrimination metrics used by every experiment.

Definitions exactly as in docs/04-methods.md §6.2. Kept centrally so experiment
results are mutually comparable.
"""
from __future__ import annotations

import numpy as np


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 15) -> float:
    """Equal-width-bin ECE."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (y_prob > lo) & (y_prob <= hi)
        if mask.sum() == 0:
            continue
        ece += (mask.sum() / n) * abs(y_true[mask].mean() - y_prob[mask].mean())
    return float(ece)


def adaptive_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 15) -> float:
    """Equal-mass-bin ECE."""
    order = np.argsort(y_prob)
    y_true_s = np.asarray(y_true)[order]
    y_prob_s = np.asarray(y_prob)[order]
    bins = np.array_split(np.arange(len(y_true_s)), n_bins)
    n = len(y_true_s)
    ace = 0.0
    for idx in bins:
        if len(idx) == 0:
            continue
        ace += (len(idx) / n) * abs(y_true_s[idx].mean() - y_prob_s[idx].mean())
    return float(ace)


def brier_decomposition(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 15) -> dict[str, float]:
    """Murphy decomposition: BS = REL - RES + UNC."""
    y_true = np.asarray(y_true).astype(float)
    y_prob = np.asarray(y_prob).astype(float)
    base = y_true.mean()
    unc = base * (1 - base)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rel, res = 0.0, 0.0
    n = len(y_true)
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (y_prob > lo) & (y_prob <= hi)
        if mask.sum() == 0:
            continue
        nk = mask.sum()
        pk = y_prob[mask].mean()
        ok = y_true[mask].mean()
        rel += (nk / n) * (pk - ok) ** 2
        res += (nk / n) * (ok - base) ** 2
    return {
        "brier": float(np.mean((y_prob - y_true) ** 2)),
        "reliability": float(rel),
        "resolution": float(res),
        "uncertainty": float(unc),
    }


def split_conformal_threshold(y_true: np.ndarray, y_prob: np.ndarray, alpha: float = 0.1) -> float:
    """Score threshold for binary split-conformal at miscoverage alpha.

    For binary classification we use the nonconformity score s = 1 - p_y, where
    p_y is the predicted probability of the true class.
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    s = np.where(y_true == 1, 1 - y_prob, y_prob)
    n = len(s)
    rank = int(np.ceil((n + 1) * (1 - alpha)))
    rank = min(rank, n)
    return float(np.sort(s)[rank - 1])


def empirical_coverage_binary(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> float:
    """Empirical coverage of the conformal prediction set at the given threshold."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    covered = np.where(y_true == 1, 1 - y_prob <= threshold, y_prob <= threshold)
    return float(covered.mean())
