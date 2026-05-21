"""Tests for the Beta-Binomial stratified-rate model."""
from __future__ import annotations

import numpy as np
import pandas as pd

from sentinela.models.baselines import BetaBinomialStratifiedRate


def _toy_panel(n_upstream: int = 5000, n_downstream: int = 30_000, positives_upstream: int = 10):
    rng = np.random.default_rng(0)
    methods = (
        ["upstream"] * n_upstream + ["downstream"] * n_downstream
    )
    rng.shuffle(methods)
    df = pd.DataFrame({"construction_method": methods})
    y = np.zeros(len(df), dtype=int)
    upstream_idx = df.index[df["construction_method"] == "upstream"]
    chosen = rng.choice(upstream_idx, size=positives_upstream, replace=False)
    y[chosen] = 1
    return df, y


def test_posterior_blends_prior_and_data():
    df, y = _toy_panel()
    model = BetaBinomialStratifiedRate(alpha=10_000)
    model.fit(df, pd.Series(y))
    # Upstream: 10/5000 empirical (0.20%), prior 0.50%, alpha=10000.
    # posterior = (10 + 10000*0.005) / (5000 + 10000) = 60 / 15000 = 0.004
    assert abs(model.posterior_["upstream"] - 0.004) < 1e-6
    # Downstream: 0 empirical, prior 0.05%, alpha=10000.
    # posterior = (0 + 10000*0.0005) / (30000 + 10000) = 5/40000 = 0.000125
    assert abs(model.posterior_["downstream"] - 0.000125) < 1e-6


def test_data_dominates_when_n_far_exceeds_alpha():
    df, y = _toy_panel(n_upstream=200_000, positives_upstream=200)
    model = BetaBinomialStratifiedRate(alpha=10_000)
    model.fit(df, pd.Series(y))
    # Empirical 200/200000 = 0.001. Prior 0.005. With alpha << n, posterior ≈ empirical.
    assert abs(model.posterior_["upstream"] - 0.0012380) < 1e-4


def test_prior_dominates_when_alpha_far_exceeds_n():
    df, y = _toy_panel(n_upstream=20, positives_upstream=0)
    model = BetaBinomialStratifiedRate(alpha=10_000)
    model.fit(df, pd.Series(y))
    # No upstream positives, very small n_upstream. Posterior ~ prior 0.005.
    assert abs(model.posterior_["upstream"] - 0.005) < 1e-4


def test_predict_proba_returns_per_row_posterior():
    df, y = _toy_panel()
    model = BetaBinomialStratifiedRate(alpha=10_000)
    model.fit(df, pd.Series(y))
    p = model.predict_proba(df)
    assert p.shape == (len(df),)
    upstream_mask = (df["construction_method"] == "upstream").to_numpy()
    assert np.allclose(p[upstream_mask], model.posterior_["upstream"])
    assert np.allclose(p[~upstream_mask], model.posterior_["downstream"])


def test_unknown_class_falls_back_to_default_prior():
    df = pd.DataFrame({"construction_method": ["upstream", "downstream", "exotic_method"]})
    y = pd.Series([0, 0, 0])
    model = BetaBinomialStratifiedRate(alpha=10_000, default_prior=0.002)
    model.fit(df, y)
    # 'exotic_method' isn't in priors and isn't in posterior_ (fit didn't see it
    # at train time — wait, it did). Actually fit sees all unique classes from
    # the training data, so exotic_method gets posterior = (0 + 10000*0.002)/(1 + 10000).
    p = model.predict_proba(df)
    expected_exotic = (0 + 10_000 * 0.002) / (1 + 10_000)
    assert abs(p[2] - expected_exotic) < 1e-6
