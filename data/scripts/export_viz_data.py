"""Export per-dam visualisation data for the Three.js 3D map.

Joins the latest hierarchical-model predictions with SIGBM geocoordinates,
samples the Brazil DEM at each dam's location, and writes:
    viz/data/dams.json        per-dam record with lat/lon/elevation/risk/...
    viz/data/summary.json     cohort-level stats and metadata
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGBM = REPO_ROOT / "data" / "processed" / "sigbm_canonical.parquet"
PREDS = REPO_ROOT / "results" / "01_first_prediction" / "predictions.parquet"
TERRAIN = REPO_ROOT / "viz" / "data" / "terrain.json"
OUT_DIR = REPO_ROOT / "viz" / "data"

LATEST_MONTH = "2025-12"


def load_terrain():
    """Return (elev_grid HxW, lon_min, lon_max, lat_min, lat_max) for sampling."""
    if not TERRAIN.exists():
        print(f"  warning: {TERRAIN.relative_to(REPO_ROOT)} not found; "
              f"dam elevations will be 0. Run build_terrain.py first.")
        return None
    payload = json.loads(TERRAIN.read_text())
    elev = np.asarray(payload["elevation_m"], dtype=np.float32).reshape(
        payload["height"], payload["width"]
    )
    return elev, payload["lon_min"], payload["lon_max"], payload["lat_min"], payload["lat_max"]


def sample_elevation(terrain, lon: float, lat: float) -> float:
    """Bilinear-interpolate the DEM at (lon, lat). NaN-safe."""
    if terrain is None:
        return 0.0
    elev, lon_min, lon_max, lat_min, lat_max = terrain
    h, w = elev.shape
    # Map to grid coordinates. Note: row 0 corresponds to lat_max (north).
    fx = (lon - lon_min) / (lon_max - lon_min) * (w - 1)
    fy = (lat_max - lat) / (lat_max - lat_min) * (h - 1)
    if fx < 0 or fx > w - 1 or fy < 0 or fy > h - 1:
        return 0.0
    x0, y0 = int(fx), int(fy)
    x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
    dx, dy = fx - x0, fy - y0
    v = (
        elev[y0, x0] * (1 - dx) * (1 - dy)
        + elev[y0, x1] * dx * (1 - dy)
        + elev[y1, x0] * (1 - dx) * dy
        + elev[y1, x1] * dx * dy
    )
    return float(v)


def main() -> int:
    sigbm = pd.read_parquet(SIGBM)
    preds = pd.read_parquet(PREDS)
    latest = preds[preds["month"] == LATEST_MONTH].copy()
    df = latest.merge(sigbm, on="dam_id", how="left")

    df = df[df["lat"].notna() & df["lon"].notna() & (df["risk_12m"] > 0)].copy()
    # Drop rows where coords are clearly bogus (e.g. (0, 0)).
    df = df[(df["lat"].between(-35, 6)) & (df["lon"].between(-75, -30))].copy()

    terrain = load_terrain()
    dams = []
    for r in df.itertuples(index=False):
        elev = sample_elevation(terrain, r.lon, r.lat)
        dams.append({
            "dam_id": r.dam_id,
            "name": r.name,
            "operator": r.operator_name,
            "state": r.state,
            "municipality": r.municipality,
            "lat": float(r.lat),
            "lon": float(r.lon),
            "terrain_elevation_m": elev,
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
