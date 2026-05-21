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
    # Include decommissioning + inactive dams in the cohort: they were active at
    # the time of any pre-decommission failure we want to label. Dams flagged
    # `under_construction` are excluded since they had no failure-relevant history.
    eligible_status = ("active", "inactive", "decommissioning")
    cohort = sigbm[sigbm["ops_status"].isin(eligible_status)].copy()
    panel = cohort.assign(_key=1).merge(
        pd.DataFrame({"month": months, "_key": 1}), on="_key"
    ).drop(columns="_key")

    # Compute age at each panel month from the snapshot date in ordinal months.
    # pd.Period arithmetic on Series misbehaves on recent pandas + Python 3.14;
    # routing through numpy ints sidesteps the dtype confusion.
    snapshot_ord = pd.Period(sigbm["snapshot_date"].max(), freq="M").ordinal
    month_ord_arr = np.asarray([p.ordinal for p in panel["month"]], dtype=np.int64)
    panel["age_at_month_years"] = panel["age_years"].to_numpy(dtype=float) + (
        (month_ord_arr - snapshot_ord) / 12.0
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
    # Per-event linkage: prefer real_sigbm_dam_id, fall back to fixture_dam_id.
    # This lets the same failures CSV serve both the synthetic-fixture path and
    # the real-data path without rewriting the table.
    def _as_dam_id(v) -> str | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, float):
            return str(int(v))
        s = str(v).strip()
        return s if s else None

    severe["dam_id"] = severe["real_sigbm_dam_id"].apply(_as_dam_id).fillna(
        severe["fixture_dam_id"].apply(_as_dam_id)
    )
    severe = severe.dropna(subset=["dam_id"])
    failure_lookup = severe.set_index("dam_id")["failure_month"].to_dict()

    panel = panel.copy()
    # Use month ordinals (number of months since 1970-01) to avoid Period
    # subtraction on mixed NaN/Period series, which crashes recent pandas.
    failure_ord_lookup = {k: v.ordinal for k, v in failure_lookup.items()}
    panel["_failure_ord"] = panel["dam_id"].map(failure_ord_lookup)
    panel["_month_ord"] = np.asarray([p.ordinal for p in panel["month"]], dtype=np.int64)
    panel["months_to_failure"] = panel["_failure_ord"] - panel["_month_ord"]

    panel["y"] = (
        panel["months_to_failure"].between(0, spec.horizon_months - 1, inclusive="both")
        .fillna(False).astype(int)
    )
    panel = panel.drop(columns=["_failure_ord", "_month_ord"])

    # Censoring: a row is in-horizon if its 12-month-ahead window fully lies
    # before the panel's end. Computed on ordinals to keep dtype clean.
    cutoff_ord = max(p.ordinal for p in panel["month"])
    row_ord = np.asarray([p.ordinal for p in panel["month"]], dtype=np.int64)
    panel["in_horizon"] = (row_ord + spec.horizon_months) <= cutoff_ord
    panel["censored_weight"] = panel["in_horizon"].astype(float)

    return panel.drop(columns=["months_to_failure"])
