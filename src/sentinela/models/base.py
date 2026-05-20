"""Common model interface.

Every model in this project implements the same fit / predict_proba surface so
experiments are model-agnostic and ablations are clean.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np
import pandas as pd


class FailureRiskModel(Protocol):
    """Minimal contract.

    fit(X, y, sample_weight) takes:
        X: pd.DataFrame    — feature table from features.build.
        y: pd.Series       — binary failure-event labels (1 = failure within horizon).
        sample_weight: np.ndarray | None
            — used to encode survival censoring as zero-weight masking on
              right-censored intervals.
    """

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: np.ndarray | None = None) -> None: ...
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray: ...
