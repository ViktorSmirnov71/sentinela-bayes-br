"""Export per-dam visualisation data for the Three.js 3D map.

Joins the latest hierarchical-model predictions with SIGBM geocoordinates,
then writes:
    viz/data/dams.json        per-dam record with lat/lon/risk/method/operator
    viz/data/summary.json     cohort-level stats and metadata
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGBM = REPO_ROOT / "data" / "processed" / "sigbm_canonical.parquet"
PREDS = REPO_ROOT / "results" / "01_first_prediction" / "predictions.parquet"
OUT_DIR = REPO_ROOT / "viz" / "data"

LATEST_MONTH = "2025-12"


def main() -> int:
    sigbm = pd.read_parquet(SIGBM)
    preds = pd.read_parquet(PREDS)
    latest = preds[preds["month"] == LATEST_MONTH].copy()
    df = latest.merge(sigbm, on="dam_id", how="left")

    df = df[df["lat"].notna() & df["lon"].notna() & (df["risk_12m"] > 0)].copy()
    # Drop rows where coords are clearly bogus (e.g. (0, 0)).
    df = df[(df["lat"].between(-35, 6)) & (df["lon"].between(-75, -30))].copy()

    dams = []
    for r in df.itertuples(index=False):
        dams.append({
            "dam_id": r.dam_id,
            "name": r.name,
            "operator": r.operator_name,
            "state": r.state,
            "municipality": r.municipality,
            "lat": float(r.lat),
            "lon": float(r.lon),
            "construction_method": r.construction_method,
            "ore_type": r.ore_type,
            "height_m": float(r.height_m) if pd.notna(r.height_m) else None,
            "volume_m3": float(r.volume_m3) if pd.notna(r.volume_m3) else None,
            "cri": int(r.cri) if pd.notna(r.cri) else None,
            "dpa": int(r.dpa) if pd.notna(r.dpa) else None,
            "emergency_level": int(r.emergency_level) if pd.notna(r.emergency_level) else 0,
            "ops_status": r.ops_status,
            "risk_12m": float(r.risk_12m),
        })

    dams.sort(key=lambda d: d["risk_12m"], reverse=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "dams.json").write_text(json.dumps(dams, ensure_ascii=False, indent=1))

    summary = {
        "snapshot_month": LATEST_MONTH,
        "n_dams": len(dams),
        "max_risk": dams[0]["risk_12m"],
        "min_risk": dams[-1]["risk_12m"],
        "mean_risk": sum(d["risk_12m"] for d in dams) / len(dams),
        "method_counts": df["construction_method"].value_counts().to_dict(),
        "emergency_counts": df["emergency_level"].astype(int).value_counts().sort_index().to_dict(),
        "state_counts": df["state"].value_counts().to_dict(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"wrote {OUT_DIR / 'dams.json'} ({len(dams)} dams)")
    print(f"wrote {OUT_DIR / 'summary.json'}")
    print(f"  max risk: {summary['max_risk']:.4f}  ({dams[0]['name']})")
    print(f"  min risk: {summary['min_risk']:.6f}  ({dams[-1]['name']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
