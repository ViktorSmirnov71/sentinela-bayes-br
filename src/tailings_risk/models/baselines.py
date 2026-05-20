"""Baselines required by docs/04-methods.md §4: B0–B3."""
from __future__ import annotations

import numpy as np
import pandas as pd


class PopulationBaseRate:
    """B0 — constant predicted probability equal to the empirical annual rate."""

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight=None) -> None:
        self.rate_ = float(y.mean())

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.rate_)


class ConstructionStratifiedRate:
    """B1 — separate base rate per construction method."""

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight=None) -> None:
        df = X[["construction_method"]].assign(y=y.values)
        self.rates_ = df.groupby("construction_method")["y"].mean().to_dict()
        self.fallback_ = float(y.mean())

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return X["construction_method"].map(self.rates_).fillna(self.fallback_).to_numpy()


class AnmCriClassifier:
    """B2 — interpret the ANM Risk Category as a classifier directly."""

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight=None) -> None:
        df = X[["cri"]].assign(y=y.values)
        self.rates_ = df.groupby("cri")["y"].mean().to_dict()
        self.fallback_ = float(y.mean())

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return X["cri"].map(self.rates_).fillna(self.fallback_).to_numpy()


class LightGbmBaseline:
    """B3 — tuned LightGBM on static + climate features only."""

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.model_ = None

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight=None) -> None:
        import lightgbm as lgb
        self.model_ = lgb.LGBMClassifier(**self.kwargs)
        self.model_.fit(X, y, sample_weight=sample_weight)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model_.predict_proba(X)[:, 1]
