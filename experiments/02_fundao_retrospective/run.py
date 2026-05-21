"""Experiment 02 — Fundão retrospective risk-trajectory.

Walks a rolling 12-month InSAR window through 2014-10..2015-11, runs the
hierarchical model at each step with the trailing-window precursor features,
and produces:

  results/02_fundao_retrospective/trajectory.csv
  figures/fundao_retrospective.png

Requires HyP3 products at data/raw/insar/fundao-actual/.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sentinela.insar.features import (
    acceleration_90d,
    crest_vs_stable_variance_ratio,
    los_velocity,
    spectral_slope,
)
from sentinela.insar.timeseries import build_los_timeseries
from sentinela.models.baselines import BetaBinomialStratifiedRate
from sentinela.models.hierarchical import HierarchicalFailureRisk

REPO_ROOT = Path(__file__).resolve().parents[2]
INSAR_DIR = REPO_ROOT / "data" / "raw" / "insar" / "fundao-actual"
RESULTS_DIR = REPO_ROOT / "results" / "02_fundao_retrospective"
FIG_PATH = REPO_ROOT / "figures" / "fundao_retrospective.png"

FUNDAO_LAT, FUNDAO_LON = -20.193, -43.493
COLLAPSE_DATE = pd.Timestamp("2015-11-05")

# Pre-failure Fundão engineering profile (Wikipedia / inquiry report).
FUNDAO_STATIC = {
    "construction_method": "upstream",
    "cri": 2,           # ANM CRI ordinal — pre-collapse risk classification
    "height_m": 110.0,  # crest height pre-failure
    "volume_m3": 55_000_000.0,
    "age_at_month_years": 7.0,
    "operator_cnpj": "16628281000161",   # Samarco's CNPJ
}


def fit_hierarchical_on_real_cohort() -> HierarchicalFailureRisk:
    """Refit the model on the live SIGBM cohort + Brazilian-failures labels."""
    from sentinela.features.build import FeatureTableSpec, build_cohort_panel
    from sentinela.io.wmtf import load_brazilian_failures

    sigbm = pd.read_parquet(REPO_ROOT / "data" / "processed" / "sigbm_canonical.parquet")
    failures = load_brazilian_failures(REPO_ROOT / "data" / "external" / "brazilian_failures.csv")
    spec = FeatureTableSpec(
        start_month="2014-01", end_month="2025-12",
        horizon_months=12, severity_min=4,
    )
    panel = build_cohort_panel(sigbm, failures, spec)
    train = panel[panel["in_horizon"]].copy()
    extras = sigbm[["dam_id", "height_m", "volume_m3", "operator_cnpj"]]
    X = train[["dam_id", "construction_method", "cri", "age_at_month_years"]].merge(
        extras, on="dam_id", how="left",
    ).drop(columns=["dam_id"])
    y = train["y"].astype(int)
    model = HierarchicalFailureRisk(BetaBinomialStratifiedRate(alpha=10_000.0))
    model.fit(X, y)
    return model


def main() -> int:
    if not INSAR_DIR.exists():
        print(f"missing {INSAR_DIR.relative_to(REPO_ROOT)}; "
              f"run `data/scripts/build_insar_features.py download --project-name sentinela-fundao-actual` first")
        return 1

    print("building full InSAR time series at Fundão coordinates")
    ts = build_los_timeseries(
        INSAR_DIR, dam_id="fundao-actual",
        dam_lat=FUNDAO_LAT, dam_lon=FUNDAO_LON,
    )
    if ts.empty:
        print("no InSAR products at expected paths")
        return 1
    print(f"  {len(ts)} (date, LOS) observations")
    print(f"  date range: {ts['secondary_date'].min().date()} .. {ts['secondary_date'].max().date()}")

    print("refitting hierarchical model on the cohort")
    model = fit_hierarchical_on_real_cohort()

    # Walk a rolling window through 2014-10 .. 2015-11.
    months = pd.period_range("2014-10", "2015-11", freq="M")
    rows = []
    for m in months:
        cutoff = m.end_time
        # 12-month trailing window ending at cutoff.
        window_start = (cutoff - pd.DateOffset(months=12))
        in_window = (ts["secondary_date"] >= window_start) & (ts["secondary_date"] <= cutoff)
        sub = ts[in_window].sort_values("secondary_date")
        n_obs = len(sub)

        if n_obs >= 4:
            t0 = sub["secondary_date"].min()
            times_days = (sub["secondary_date"] - t0).dt.total_seconds().to_numpy() / 86400.0
            los = sub["los_mm"].to_numpy(dtype=float)
            stable = sub["stable_ref_mm"].to_numpy(dtype=float)
            v = los_velocity(times_days, los)
            a = acceleration_90d(times_days, los)
            s = spectral_slope(times_days, los)
            vr = crest_vs_stable_variance_ratio(los, stable)
        else:
            v, a, s, vr = (np.nan, np.nan, np.nan, np.nan)

        X = pd.DataFrame([{
            **FUNDAO_STATIC,
            "los_velocity_mm_yr": v if np.isfinite(v) else 0.0,
            "los_accel_90d_mm_yr2": a if np.isfinite(a) else 0.0,
            "spectral_slope": s if np.isfinite(s) else 0.0,
            "crest_vs_stable_variance_ratio": vr if np.isfinite(vr) else 1.0,
        }])
        p = float(model.predict_proba(X)[0])
        rows.append({
            "month": m.strftime("%Y-%m"),
            "month_dt": cutoff,
            "n_insar_obs": n_obs,
            "los_velocity_mm_yr": v, "los_accel_90d_mm_yr2": a,
            "spectral_slope": s, "crest_vs_stable_variance_ratio": vr,
            "risk_12m": p,
        })

    df = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["month_dt"]).to_csv(RESULTS_DIR / "trajectory.csv", index=False)
    print(f"wrote {RESULTS_DIR / 'trajectory.csv'}")
    print()
    print(df[["month", "n_insar_obs", "los_velocity_mm_yr",
              "los_accel_90d_mm_yr2", "risk_12m"]].to_string(index=False))

    # ---- plot ----
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 7.5), sharex=True,
        gridspec_kw={"height_ratios": [2, 1], "hspace": 0.05},
    )

    ax1.plot(df["month_dt"], df["risk_12m"] * 100, color="#c8186c", lw=2.2,
             marker="o", markersize=4)
    ax1.axvline(COLLAPSE_DATE, color="#1a2230", lw=1, linestyle="--", alpha=0.8)
    ax1.text(COLLAPSE_DATE, ax1.get_ylim()[1] * 0.93,
             "  Fundão collapse\n  2015-11-05",
             fontsize=9, color="#1a2230", va="top")
    ax1.set_ylabel("Sentinela predicted\n12-month failure probability (%)", fontsize=11)
    ax1.set_title("Retrospective risk trajectory at the actual Fundão dam coordinates",
                  fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.3)

    ax2.plot(df["month_dt"], df["los_velocity_mm_yr"], color="#1d6cff", lw=1.6,
             marker="s", markersize=3, label="LOS velocity (mm/yr)")
    ax2.plot(df["month_dt"], df["los_accel_90d_mm_yr2"] / 10, color="#0ea5a4",
             lw=1.6, marker="^", markersize=3, label="LOS acceleration / 10 (mm/yr²)")
    ax2.axhline(0, color="black", lw=0.5, alpha=0.5)
    ax2.axvline(COLLAPSE_DATE, color="#1a2230", lw=1, linestyle="--", alpha=0.6)
    ax2.set_ylabel("InSAR features", fontsize=11)
    ax2.legend(loc="upper left", framealpha=0.9, fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax2.get_xticklabels(), rotation=30, ha="right")

    fig.tight_layout()
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=140, bbox_inches="tight", facecolor="white")
    print(f"wrote {FIG_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
