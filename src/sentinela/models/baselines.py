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


class BetaBinomialStratifiedRate:
    """Beta-Binomial smoothed per-class failure rate.

    Posterior rate for class c with prior strength alpha and prior mean p_c:
        p_hat_c = (positives_c + alpha * p_c) / (n_c + alpha)

    Where p_c is a literature-derived prior (e.g. Bowker-Chambers historical
    failure rates by construction method) and alpha is the prior weight in
    units of "equivalent dam-months of data". With n_c >> alpha the
    posterior converges to the empirical rate; with n_c << alpha it stays
    near the prior. This is the right model class when only a handful of
    positive events are linked to the cohort (the current Sentinela state).
    """

    LITERATURE_PRIORS_ANNUAL: dict[str, float] = {
        # Annual failure probability per dam, by construction method.
        # Calibrated against Rana et al. 2021 global TSF failure-frequency
        # analysis and the Bowker-Chambers severity catalogue. Upstream dams
        # have substantially higher historical failure rates.
        "upstream":     0.005,
        "downstream":   0.0005,
        "centerline":   0.001,
        "single_stage": 0.001,
        "dyke":         0.001,
        "unknown":      0.001,
    }

    def __init__(
        self,
        stratify_col: str = "construction_method",
        priors: dict[str, float] | None = None,
        alpha: float = 10_000.0,
        default_prior: float = 0.001,
    ) -> None:
        self.stratify_col = stratify_col
        self.priors = priors or self.LITERATURE_PRIORS_ANNUAL
        self.alpha = alpha
        self.default_prior = default_prior
        self.posterior_: dict[str, float] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight=None) -> None:
        col = self.stratify_col
        groups = X[col].astype(str)
        for cls in groups.unique():
            mask = groups == cls
            n = int(mask.sum())
            k = int(np.asarray(y)[mask].sum())
            p_c = self.priors.get(cls, self.default_prior)
            self.posterior_[cls] = (k + self.alpha * p_c) / (n + self.alpha)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        col = self.stratify_col
        return X[col].astype(str).map(self.posterior_).fillna(self.default_prior).to_numpy()


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
