"""Hierarchical Bayesian failure-risk model.

Three-level structure, in increasing model complexity:

  level 0  global prior failure rate (drawn from the literature)
  level 1  construction-method effect (Beta-Binomial smoothed posterior)
  level 2  per-operator random effect (logit shift, shrunk to zero)
  level 3  continuous engineering modifiers (height, volume, age, CRI)
           applied as smooth logit shifts with calibrated coefficients

The output is a per-dam predicted 12-month-ahead failure probability with all
shrinkage explicit. Designed for the small-positive regime — every
contribution is bounded so a single positive event cannot make any individual
operator look like an outlier.

Why this shape and not, say, PyMC: at the current data scale (n=12 linked
positives) a full MCMC fit would just recover the priors. The contribution of
this module is to *embed the literature priors as a tractable model* and to
make the chain of effects auditable. When linked positives grow, the same
structural form can be re-fit with proper MCMC; the present implementation is
the small-data analytic limit of the same model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .baselines import BetaBinomialStratifiedRate


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


class HierarchicalFailureRisk:
    """Compose construction-method base + operator effect + engineering shifts.

    The model is fully analytical, so `fit` only estimates per-class posteriors
    via Beta-Binomial smoothing (level 1) and per-operator shrinkage estimates
    (level 2); levels 0 and 3 are baked in from the literature.
    """

    # Engineering modifiers, on the LOGIT scale. Each coefficient is the shift
    # in log-odds per unit of the standardised feature; values come from
    # Bowker-Chambers / Rana 2021 effect-size estimates and are deliberately
    # conservative so they cannot dominate the construction-method prior.
    ENG_COEFFICIENTS = {
        "height_m_z":     0.30,   # taller dams fail more often
        "volume_m3_z":    0.15,   # larger impoundments fail more often
        "age_years_z":    0.10,   # older dams fail more often
        "cri_ord":        0.20,   # higher ANM CRI ordinal = higher risk
    }

    # InSAR precursor coefficients on the LOGIT scale. Sign convention:
    # POSITIVE coefficient on a feature means LARGER feature value -> MORE risk.
    # All four features are bounded in their effect by INSAR_TOTAL_CAP so that
    # InSAR cannot override the engineering / regulatory base by an
    # unreasonable factor.
    INSAR_COEFFICIENTS = {
        # Subsidence (negative LOS velocity) increases risk: each -10 mm/yr
        # adds 0.3 logit units. Sign flip so we apply -coef * value.
        "los_velocity_mm_yr_neg10": 0.30,
        # Accelerating subsidence is the Carla precursor: positive
        # `los_accel_90d_mm_yr2` (per our sign convention) means
        # "subsidence accelerating". Each +50 mm/yr^2 adds 0.5 logit.
        "los_accel_per_50":         0.50,
        # More-negative spectral slope = more drift power: each -0.5 slope
        # below zero adds 0.2 logit.
        "spectral_slope_neg":       0.20,
        # Grebby anomaly: variance ratio - 1 (i.e. crest moving more than
        # the stable reference). Each unit excess adds 0.3 logit.
        "variance_excess":          0.30,
    }
    INSAR_TOTAL_CAP = 1.5    # cap on the summed InSAR logit shift per dam

    # Operator shrinkage strength: a per-operator logit shift is pulled toward
    # zero by this many "equivalent observations" of zero deviation.
    OPERATOR_SHRINKAGE_LAMBDA = 50.0

    def __init__(
        self,
        base_rate_model: BetaBinomialStratifiedRate | None = None,
        eng_coefficients: dict[str, float] | None = None,
        operator_shrinkage_lambda: float | None = None,
    ) -> None:
        self.base = base_rate_model or BetaBinomialStratifiedRate(alpha=10_000.0)
        self.eng = eng_coefficients or self.ENG_COEFFICIENTS
        self.op_lambda = operator_shrinkage_lambda or self.OPERATOR_SHRINKAGE_LAMBDA
        self.feature_means_: dict[str, float] = {}
        self.feature_stds_: dict[str, float] = {}
        self.operator_logit_shift_: dict[str, float] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight=None) -> None:
        # Level 1: construction-method Beta-Binomial posterior.
        self.base.fit(X, y)

        # Standardise continuous features against the cohort.
        for col in ("height_m", "volume_m3", "age_at_month_years"):
            if col in X.columns:
                values = pd.to_numeric(X[col], errors="coerce")
                self.feature_means_[col] = float(values.mean(skipna=True))
                self.feature_stds_[col] = float(values.std(skipna=True)) or 1.0

        # Level 2: per-operator logit shift via James-Stein-style shrinkage.
        # For each operator, compare its empirical failure rate to the base
        # rate predicted by construction method alone; shrink toward zero.
        if "operator_cnpj" in X.columns:
            base_p = self.base.predict_proba(X)
            base_logit = _logit(base_p)
            obs_logit = _logit(np.asarray(y).astype(float))
            df = pd.DataFrame({
                "op": X["operator_cnpj"].astype(str),
                "delta": obs_logit - base_logit,
                "weight": 1.0,
            })
            grouped = df.groupby("op").agg(
                delta_mean=("delta", "mean"),
                n=("weight", "sum"),
            )
            grouped["shrunk"] = grouped["delta_mean"] * grouped["n"] / (grouped["n"] + self.op_lambda)
            # Cap shrinkage shifts at +/- 1.0 logit units (~factor of 2.7 odds).
            grouped["shrunk"] = grouped["shrunk"].clip(-1.0, 1.0)
            self.operator_logit_shift_ = grouped["shrunk"].to_dict()

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        # Level 1.
        p = self.base.predict_proba(X)
        logit = _logit(p)

        # Level 3 — engineering modifiers (z-scored features × coefficients).
        for src, coef_key in (
            ("height_m", "height_m_z"),
            ("volume_m3", "volume_m3_z"),
            ("age_at_month_years", "age_years_z"),
        ):
            if src in X.columns and coef_key in self.eng and src in self.feature_means_:
                z = (pd.to_numeric(X[src], errors="coerce")
                       - self.feature_means_[src]) / self.feature_stds_[src]
                z = z.fillna(0.0).to_numpy()
                logit = logit + self.eng[coef_key] * z

        if "cri" in X.columns and "cri_ord" in self.eng:
            cri = pd.to_numeric(X["cri"], errors="coerce").fillna(2).to_numpy()
            # Centre CRI ordinal around 2 (medium) so it adds 0 at the median.
            logit = logit + self.eng["cri_ord"] * (cri - 2)

        # Level 2 — per-operator logit shift.
        if "operator_cnpj" in X.columns and self.operator_logit_shift_:
            ops = X["operator_cnpj"].astype(str).to_numpy()
            shifts = np.asarray([self.operator_logit_shift_.get(o, 0.0) for o in ops])
            logit = logit + shifts

        # Level 4 — InSAR precursor features. Bounded total shift so InSAR
        # can refine within-class ranking but cannot fully override Level 1-3.
        insar_shift = np.zeros(len(X))
        if "los_velocity_mm_yr" in X.columns:
            v = pd.to_numeric(X["los_velocity_mm_yr"], errors="coerce").fillna(0.0).to_numpy()
            # negative velocity = subsiding, increases risk; normalise to 10mm/yr units
            insar_shift = insar_shift + self.INSAR_COEFFICIENTS["los_velocity_mm_yr_neg10"] * (-v / 10.0)
        if "los_accel_90d_mm_yr2" in X.columns:
            a = pd.to_numeric(X["los_accel_90d_mm_yr2"], errors="coerce").fillna(0.0).to_numpy()
            insar_shift = insar_shift + self.INSAR_COEFFICIENTS["los_accel_per_50"] * (a / 50.0)
        if "spectral_slope" in X.columns:
            s = pd.to_numeric(X["spectral_slope"], errors="coerce").fillna(0.0).to_numpy()
            insar_shift = insar_shift + self.INSAR_COEFFICIENTS["spectral_slope_neg"] * (-s / 0.5)
        if "crest_vs_stable_variance_ratio" in X.columns:
            vr = pd.to_numeric(X["crest_vs_stable_variance_ratio"], errors="coerce").fillna(1.0).to_numpy()
            insar_shift = insar_shift + self.INSAR_COEFFICIENTS["variance_excess"] * (vr - 1.0)
        insar_shift = np.clip(insar_shift, -self.INSAR_TOTAL_CAP, self.INSAR_TOTAL_CAP)
        logit = logit + insar_shift

        return _sigmoid(logit)
