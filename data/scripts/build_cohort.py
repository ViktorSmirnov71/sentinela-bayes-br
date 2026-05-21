"""Build the (dam_id, month) cohort panel with horizon-windowed labels.

Thin runnable wrapper around `sentinela.features.build.build_cohort_panel`.
Consumes:
    data/processed/sigbm_canonical.parquet     (output of clean_sigbm.py)
    data/external/brazilian_failures.csv       (committed labels)

Produces:
    data/processed/cohort_panel.parquet        (model-ready)

Usage
-----
    python data/scripts/build_cohort.py
    python data/scripts/build_cohort.py --start-month 2014-01 --end-month 2025-12
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from sentinela.features.build import FeatureTableSpec, build_cohort_panel
from sentinela.io.wmtf import load_brazilian_failures

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SIGBM = REPO_ROOT / "data" / "processed" / "sigbm_canonical.parquet"
DEFAULT_FAILURES = REPO_ROOT / "data" / "external" / "brazilian_failures.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "cohort_panel.parquet"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sigbm", type=Path, default=DEFAULT_SIGBM)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start-month", default="2014-01")
    parser.add_argument("--end-month", default="2025-12")
    parser.add_argument("--horizon-months", type=int, default=12)
    parser.add_argument("--severity-min", type=int, default=4)
    args = parser.parse_args()

    print(f"reading  {args.sigbm.relative_to(REPO_ROOT)}")
    sigbm = pd.read_parquet(args.sigbm)
    print(f"  cohort: {len(sigbm):,} dams")

    print(f"reading  {args.failures.relative_to(REPO_ROOT)}")
    failures = load_brazilian_failures(args.failures)
    severe = failures["severity_bowker_chambers"] >= args.severity_min
    print(f"  events: {len(failures)} total; {severe.sum()} severe (>= {args.severity_min})")

    spec = FeatureTableSpec(
        start_month=args.start_month,
        end_month=args.end_month,
        horizon_months=args.horizon_months,
        severity_min=args.severity_min,
    )
    panel = build_cohort_panel(sigbm, failures, spec)

    print(f"panel:    {len(panel):,} rows")
    print(f"  in-horizon: {int(panel['in_horizon'].sum()):,}")
    print(f"  positives:  {int(panel['y'].sum()):,}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Pyarrow doesn't support Period dtype directly; serialise month as YYYY-MM.
    out = panel.copy()
    out["month"] = out["month"].astype(str)
    out.to_parquet(args.output)
    print(f"wrote    {args.output.relative_to(REPO_ROOT)}  ({args.output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
