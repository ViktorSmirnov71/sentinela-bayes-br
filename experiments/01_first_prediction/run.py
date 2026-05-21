"""Experiment 01 — first real prediction run on the 911-dam cohort.

Usage:
    python experiments/01_first_prediction/run.py
    python experiments/01_first_prediction/run.py --seed 1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from sentinela.evaluation.metrics import (
    brier_decomposition,
    expected_calibration_error,
)
from sentinela.models.baselines import BetaBinomialStratifiedRate
from sentinela.utils.seed import seed_everything

REPO_ROOT = Path(__file__).resolve().parents[2]
COHORT_PANEL = REPO_ROOT / "data" / "processed" / "cohort_panel.parquet"
SIGBM_CANONICAL = REPO_ROOT / "data" / "processed" / "sigbm_canonical.parquet"
OUT_DIR = REPO_ROOT / "results" / "01_first_prediction"

CATEGORICAL = ["construction_method", "state", "ore_type"]
NUMERIC = ["cri", "dpa"]

# Why this feature surface (deliberately small): with one linked positive
# event (Fundão / dam_id 8765), any feature that uniquely identifies that dam
# — height_m, volume_m3, operator identity, exact age — lets LightGBM
# memorise the single positive instead of producing a generalisable model.
# We restrict to features that partition the cohort into broad, non-unique
# groups: construction method, ore type, state, and the two regulator-
# assigned ordinals. The resulting model is essentially a smoothed
# construction-method-stratified rate with weak state/ore/CRI/DPA refinements.


def build_design_matrix(panel: pd.DataFrame) -> pd.DataFrame:
    """Assemble the (deliberately small) feature DataFrame for LightGBM."""
    X = panel[CATEGORICAL + NUMERIC].copy()
    for col in CATEGORICAL:
        X[col] = X[col].astype("category")
    return X


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args()
    seed_everything(args.seed)

    print(f"loading cohort panel from {COHORT_PANEL.relative_to(REPO_ROOT)}")
    panel = pd.read_parquet(COHORT_PANEL)
    panel["month"] = pd.PeriodIndex(panel["month"], freq="M")
    print(f"  panel rows: {len(panel):,}")
    print(f"  in-horizon: {int(panel['in_horizon'].sum()):,}")
    print(f"  positives:  {int(panel['y'].sum())}")

    print(f"loading SIGBM canonical from {SIGBM_CANONICAL.relative_to(REPO_ROOT)}")
    sigbm = pd.read_parquet(SIGBM_CANONICAL)

    train = panel[panel["in_horizon"]].copy()
    X_train = build_design_matrix(train)
    y_train = train["y"].astype(int).to_numpy()

    print(f"fitting Beta-Binomial stratified model on {len(X_train):,} in-horizon rows "
          f"({int(y_train.sum())} positives)")
    model = BetaBinomialStratifiedRate(
        stratify_col="construction_method", alpha=10_000.0,
    )
    model.fit(X_train, pd.Series(y_train))
    print("  posterior failure rate per construction method:")
    for cls, p in sorted(model.posterior_.items(), key=lambda kv: -kv[1]):
        n = int((X_train["construction_method"].astype(str) == cls).sum())
        k = int(y_train[(X_train["construction_method"].astype(str) == cls).to_numpy()].sum())
        print(f"    {cls:<14s}  posterior={p:.5f}  (n_rows={n:,}  positives={k})")

    p_train = model.predict_proba(X_train)
    metrics = {
        "n_train_rows": int(len(X_train)),
        "n_train_positives": int(y_train.sum()),
        "base_rate": float(y_train.mean()),
        "train_log_loss": float(log_loss(y_train, np.clip(p_train, 1e-9, 1 - 1e-9))),
        "train_auroc": float(roc_auc_score(y_train, p_train)) if y_train.sum() > 0 else float("nan"),
        "train_ece": expected_calibration_error(y_train, p_train),
    }
    metrics.update({f"train_brier_{k}": v for k, v in brier_decomposition(y_train, p_train).items()})
    print(f"  train_log_loss = {metrics['train_log_loss']:.5f}")
    print(f"  train_auroc    = {metrics['train_auroc']:.4f}")
    print(f"  train_ece      = {metrics['train_ece']:.5f}")

    # Predict on every panel row, then slice to the latest snapshot for the ranking.
    X_all = build_design_matrix(panel)
    panel["risk_12m"] = model.predict_proba(X_all)

    latest_month = panel["month"].max()
    snap = panel[panel["month"] == latest_month].copy()
    snap = snap.merge(
        sigbm[["dam_id", "name", "operator_name", "municipality", "emergency_level",
               "ops_status", "lat", "lon"]],
        on="dam_id", how="left",
    )
    snap = snap.sort_values("risk_12m", ascending=False)
    top = snap.head(args.top_n)[[
        "dam_id", "name", "operator_name", "state", "municipality",
        "construction_method", "ore_type", "height_m", "volume_m3",
        "cri", "dpa", "emergency_level", "ops_status",
        "lat", "lon", "risk_12m",
    ]]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel_out = panel[["dam_id", "month", "y", "in_horizon", "risk_12m"]].copy()
    panel_out["month"] = panel_out["month"].astype(str)
    panel_out.to_parquet(OUT_DIR / "predictions.parquet")
    top.to_csv(OUT_DIR / "top_risk_dams.csv", index=False)
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"\nlatest snapshot month: {latest_month}")
    print(f"top {args.top_n} dams by predicted 12-month failure probability:")
    print("  rank dam_id  state  method            risk   name (operator)")
    for i, r in enumerate(top.itertuples(index=False), 1):
        print(f"  {i:>4} {r.dam_id:>6}  {r.state:<3}    "
              f"{r.construction_method:<14}  {r.risk_12m:.4f}  "
              f"{r.name[:30]:<30s} ({r.operator_name[:30]})")
    print(f"\nwrote {OUT_DIR / 'top_risk_dams.csv'}")
    print(f"wrote {OUT_DIR / 'predictions.parquet'}")
    print(f"wrote {OUT_DIR / 'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
