"""Experiment 00 — pipeline smoke run with static-feature baselines.

Run:
    python experiments/00_baselines/run.py                       # fixture
    python experiments/00_baselines/run.py --sigbm <path.csv>    # real SIGBM
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
from sentinela.features.build import FeatureTableSpec, build_cohort_panel
from sentinela.io import fixtures
from sentinela.io.sigbm import CANONICAL_COLUMNS, load as load_sigbm
from sentinela.io.wmtf import load_brazilian_failures
from sentinela.models.baselines import (
    AnmCriClassifier,
    ConstructionStratifiedRate,
    PopulationBaseRate,
)
from sentinela.utils.seed import seed_everything


REPO_ROOT = Path(__file__).resolve().parents[2]
FAILURES_CSV = REPO_ROOT / "data" / "external" / "brazilian_failures.csv"
RESULTS_DIR = REPO_ROOT / "results" / "00_baselines"


def load_or_fixture(sigbm_path: str | None) -> pd.DataFrame:
    """Real SIGBM if a path is given; otherwise synthetic fixture."""
    if sigbm_path:
        return load_sigbm(sigbm_path)
    df = fixtures.make_fixture(n=120, seed=0)
    # Already in canonical schema, but route through the loader's validator
    # by serialising and reloading so we exercise the same code path.
    tmp = RESULTS_DIR / "_fixture.csv"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(tmp, index=False)
    return load_sigbm(tmp)


def evaluate(name: str, y: np.ndarray, p: np.ndarray) -> dict:
    """Compute the standard metric bundle."""
    out = {"model": name, "n": int(len(y)), "positives": int(y.sum())}
    out["base_rate"] = float(y.mean())
    p = np.clip(p, 1e-9, 1 - 1e-9)
    out["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    try:
        out["auroc"] = float(roc_auc_score(y, p)) if y.sum() > 0 and y.sum() < len(y) else float("nan")
    except ValueError:
        out["auroc"] = float("nan")
    out["ece"] = expected_calibration_error(y, p)
    out.update({f"brier_{k}": v for k, v in brier_decomposition(y, p).items()})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sigbm", default=None, help="Path to real SIGBM CSV/parquet.")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    seed_everything(args.seed)

    sigbm = load_or_fixture(args.sigbm)
    print(f"SIGBM rows: {len(sigbm)} ({'real' if args.sigbm else 'fixture'})")
    print(f"  states: {sigbm['state'].value_counts().to_dict()}")
    print(f"  methods: {sigbm['construction_method'].value_counts().to_dict()}")

    failures = load_brazilian_failures(FAILURES_CSV)
    print(f"Failure events loaded: {len(failures)} "
          f"(severity >= 4: {(failures['severity_bowker_chambers'] >= 4).sum()})")

    # Panel extends back to 2014 to cover the Sentinel-1 era and to capture the
    # 12 pre-failure months for Fundão 2015-11 (the only Bowker–Chambers >= 4
    # event we can currently link to a surviving SIGBM dam_id).
    spec = FeatureTableSpec(
        start_month="2014-01", end_month="2025-12",
        horizon_months=12, severity_min=4,
    )
    panel = build_cohort_panel(sigbm, failures, spec)
    train = panel[panel["in_horizon"]].copy()
    print(f"Panel rows: {len(panel)}; in-horizon: {len(train)}; positives: {int(train['y'].sum())}")

    if train["y"].sum() == 0:
        print("No positives in panel. Check fixture / failure linkage. Continuing for pipeline smoke test.")

    X = train[["construction_method", "cri"]].copy()
    y = train["y"].astype(int)

    results = []
    predictions = pd.DataFrame({"dam_id": train["dam_id"], "month": train["month"].astype(str)})

    for name, model in [
        ("B0_base_rate", PopulationBaseRate()),
        ("B1_construction_rate", ConstructionStratifiedRate()),
        ("B2_anm_cri", AnmCriClassifier()),
    ]:
        model.fit(X, y)
        p = model.predict_proba(X)
        results.append(evaluate(name, y.to_numpy(), p))
        predictions[name] = p
        print(f"  {name:25s}  log_loss={results[-1]['log_loss']:.4f}  "
              f"ece={results[-1]['ece']:.4f}  auroc={results[-1]['auroc']:.4f}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_csv = RESULTS_DIR / "metrics.csv"
    pd.DataFrame(results).to_csv(metrics_csv, index=False)
    predictions.to_parquet(RESULTS_DIR / "predictions.parquet")
    (RESULTS_DIR / "spec.json").write_text(json.dumps({
        "spec": spec.__dict__,
        "sigbm_source": args.sigbm or "fixture",
        "panel_rows": len(panel),
        "in_horizon_rows": len(train),
        "positives": int(y.sum()),
    }, indent=2, default=str))
    print(f"wrote {metrics_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
