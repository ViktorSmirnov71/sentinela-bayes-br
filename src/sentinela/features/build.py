"""Assemble the per-dam-per-month feature table.

Joins the SIGBM cohort with a monthly time grid; attaches static engineering
features; joins on the curated Brazilian-failure events table to produce
horizon-windowed binary labels with right-censoring weights.

InSAR and climate feature blocks attach later (separate modules); this builder
produces the cohort skeleton that those blocks merge onto.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

STATIC_FEATURE_COLUMNS: tuple[str, ...] = (
    "construction_method",
    "height_m",
    "volume_m3",
    "age_years",
    "cri",
    "dpa",
    "ore_type",
    "state",
    "operator_cnpj",
)


@dataclass(frozen=True)
class FeatureTableSpec:
    start_month: str         # "YYYY-MM"
    end_month: str           # "YYYY-MM"
    horizon_months: int = 12
    severity_min: int = 4


def build_cohort_panel(
    sigbm: pd.DataFrame,
    failures: pd.DataFrame,
    spec: FeatureTableSpec,
) -> pd.DataFrame:
    """Materialise the (dam_id, month) panel with static features and labels.

    Parameters
    ----------
    sigbm
        Output of `sentinela.io.sigbm.load`. Single-snapshot table is sufficient
        for v1; multi-snapshot extensions are deferred until real data arrives.
    failures
        Output of `sentinela.io.wmtf.load_brazilian_failures`.
    spec
        Time bounds and label horizon.

    Returns
    -------
    DataFrame with columns:
        dam_id, month, <STATIC_FEATURE_COLUMNS>, age_at_month_years,
        y, in_horizon, censored_weight
    """
    months = pd.period_range(spec.start_month, spec.end_month, freq="M")
    cohort = sigbm[sigbm["status_active"]].copy()
    panel = cohort.assign(_key=1).merge(
        pd.DataFrame({"month": months, "_key": 1}), on="_key"
    ).drop(columns="_key")

    snapshot_month = pd.Period(sigbm["snapshot_date"].max(), freq="M")
    panel["age_at_month_years"] = panel["age_years"] + (
        (panel["month"] - snapshot_month).apply(lambda x: x.n) / 12.0
    )

    panel = _attach_labels(panel, failures, spec)

    keep = [
        "dam_id", "month", *STATIC_FEATURE_COLUMNS, "age_at_month_years",
        "y", "in_horizon", "censored_weight",
    ]
    return panel[keep].reset_index(drop=True)


def _attach_labels(
    panel: pd.DataFrame, failures: pd.DataFrame, spec: FeatureTableSpec
) -> pd.DataFrame:
    """Attach horizon-windowed binary labels with right-censoring weights.

    For each (dam, month) row:
        y = 1   if the dam fails within [month, month + horizon_months]
                AND severity >= spec.severity_min
        y = 0   otherwise
        in_horizon       = whether the row's horizon window ends before the
                           current observation cutoff (defines what is censored)
        censored_weight  = 1.0 if horizon fully observed; 0.0 if censored at
                           the end of the panel (typical survival weighting)

    The link between a failure event and a SIGBM row uses
    `fixture_dam_id` (while we're on synthetic SIGBM) or `real_sigbm_dam_id`
    once real SIGBM data is wired.
    """
    severe = failures[failures["severity_bowker_chambers"] >= spec.severity_min].copy()
    severe["failure_month"] = severe["date"].dt.to_period("M")
    link_col = "real_sigbm_dam_id" if severe["real_sigbm_dam_id"].notna().any() else "fixture_dam_id"
    severe = severe.dropna(subset=[link_col]).rename(columns={link_col: "dam_id"})
    failure_lookup = severe.set_index("dam_id")["failure_month"].to_dict()

    panel = panel.copy()
    panel["failure_month"] = panel["dam_id"].map(failure_lookup)
    panel["months_to_failure"] = (
        (panel["failure_month"] - panel["month"]).map(lambda x: x.n if pd.notna(x) else np.nan)
    )
    panel["y"] = (
        panel["months_to_failure"].between(0, spec.horizon_months - 1, inclusive="both")
    ).astype(int)

    cutoff = panel["month"].max()
    panel["in_horizon"] = (panel["month"] + spec.horizon_months) <= cutoff
    panel["censored_weight"] = panel["in_horizon"].astype(float)

    return panel.drop(columns=["failure_month", "months_to_failure"])
