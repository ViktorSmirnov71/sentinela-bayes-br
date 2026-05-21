"""Tests for the hierarchical Bayesian failure-risk model."""
from __future__ import annotations

import numpy as np
import pandas as pd

from sentinela.models.hierarchical import HierarchicalFailureRisk


def _toy_cohort(n: int = 1000, seed: int = 0):
    rng = np.random.default_rng(seed)
    methods = rng.choice(
        ["upstream", "downstream", "centerline", "single_stage"],
        p=[0.05, 0.25, 0.15, 0.55],
        size=n,
    )
    df = pd.DataFrame({
        "construction_method": methods,
        "height_m": np.clip(rng.lognormal(3.0, 0.7, n), 5, 200),
        "volume_m3": np.clip(rng.lognormal(14.0, 1.5, n), 1e4, 5e8),
        "age_at_month_years": np.clip(rng.gamma(2.0, 10.0, n), 0, 80),
        "cri": rng.choice([1, 2, 3], p=[0.45, 0.40, 0.15], size=n),
        "operator_cnpj": rng.choice(["00000000000001", "00000000000002", "00000000000003"], size=n),
    })
    y = np.zeros(n, dtype=int)
    upstream_idx = df.index[df["construction_method"] == "upstream"]
    if len(upstream_idx) > 0:
        chosen = rng.choice(upstream_idx, size=min(3, len(upstream_idx)), replace=False)
        y[chosen] = 1
    return df, pd.Series(y)


def test_hierarchical_runs_end_to_end():
    df, y = _toy_cohort()
    model = HierarchicalFailureRisk()
    model.fit(df, y)
    p = model.predict_proba(df)
    assert p.shape == (len(df),)
    assert np.all((p >= 0) & (p <= 1))


def test_taller_upstream_dam_ranks_higher_than_shorter_one():
    df, y = _toy_cohort(n=2000)
    model = HierarchicalFailureRisk()
    model.fit(df, y)

    short_tall = pd.DataFrame({
        "construction_method": ["upstream", "upstream"],
        "height_m":          [20.0, 150.0],
        "volume_m3":         [1e6, 1e6],
        "age_at_month_years":[10.0, 10.0],
        "cri":               [2, 2],
        "operator_cnpj":     ["00000000000001", "00000000000001"],
    })
    p = model.predict_proba(short_tall)
    assert p[1] > p[0], f"taller dam should have higher predicted risk: short={p[0]} tall={p[1]}"


def test_higher_cri_ranks_higher_than_lower_cri():
    df, y = _toy_cohort(n=2000)
    model = HierarchicalFailureRisk()
    model.fit(df, y)
    low_high = pd.DataFrame({
        "construction_method": ["upstream", "upstream"],
        "height_m":          [50.0, 50.0],
        "volume_m3":         [1e6, 1e6],
        "age_at_month_years":[10.0, 10.0],
        "cri":               [1, 3],
        "operator_cnpj":     ["00000000000001", "00000000000001"],
    })
    p = model.predict_proba(low_high)
    assert p[1] > p[0]


def test_operator_shift_bounded():
    df, y = _toy_cohort(n=500)
    model = HierarchicalFailureRisk()
    model.fit(df, y)
    # No operator shrinkage shift may exceed +/- 1.0 logit units by design.
    for v in model.operator_logit_shift_.values():
        assert -1.0 <= v <= 1.0
