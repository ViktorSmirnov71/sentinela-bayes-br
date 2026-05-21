"""Build per-dam InSAR precursor features from HyP3 products.

This script has two modes:

  pull        Submit HyP3 InSAR jobs for the target dams over the configured
              time window. Async; jobs queue at ASF and complete in 1-48 h.
              Requires EARTHDATA_USERNAME / EARTHDATA_PASSWORD.

  features    Read previously-downloaded HyP3 products from
              data/raw/insar/<dam_id>/ and write per-dam InSAR features to
              data/processed/insar_features.parquet. Pure local computation;
              no network or credentials required.

For an end-to-end first run:

    export EARTHDATA_USERNAME=...
    export EARTHDATA_PASSWORD=...
    python data/scripts/build_insar_features.py pull --dam-ids 8765 --start 2014-01-01 --end 2015-11-30
    # ... wait 1-48h for HyP3 ...
    # download products into data/raw/insar/8765/
    python data/scripts/build_insar_features.py features

The first concrete target dam_id is 8765 (Barragem de Germano, the Samarco
upstream structure used as the Fundão modeling proxy; see docs/03-data.md).

Implementation: thin orchestration on top of
    sentinela.io.sentinel1.*       (ASF + HyP3)
    sentinela.insar.timeseries.*   (per-dam LOS sampling)
    sentinela.insar.features.*     (precursor feature extraction)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGBM_CANONICAL = REPO_ROOT / "data" / "processed" / "sigbm_canonical.parquet"
INSAR_RAW_DIR = REPO_ROOT / "data" / "raw" / "insar"
INSAR_FEATURES_OUT = REPO_ROOT / "data" / "processed" / "insar_features.parquet"


def cmd_pull(args: argparse.Namespace) -> int:
    """Search ASF and submit HyP3 jobs for the listed dams."""
    from sentinela.io.sentinel1 import (
        bbox_for_dam,
        pick_best_orbit,
        search_scenes,
        short_baseline_pairs,
        submit_insar_pairs,
    )

    sigbm = pd.read_parquet(SIGBM_CANONICAL)
    dam_ids = list(map(str, args.dam_ids))
    rows = sigbm[sigbm["dam_id"].isin(dam_ids)]
    if rows.empty:
        print(f"no dams in {SIGBM_CANONICAL.name} match {dam_ids}")
        return 1

    for _, dam in rows.iterrows():
        bbox = bbox_for_dam(dam["lat"], dam["lon"], radius_km=args.radius_km)
        print(f"\n== dam {dam['dam_id']} ({dam['name']}) ==")
        print(f"  bbox: {bbox}")
        if args.orbit == "auto":
            orbit, count = pick_best_orbit(bbox, args.start, args.end)
            print(f"  orbit auto-selected: {orbit} ({count} scenes; "
                  f"the other orbit was the lesser-covered alternative)")
        else:
            orbit = args.orbit
        scenes = search_scenes(bbox, args.start, args.end, orbit=orbit)
        print(f"  {len(scenes)} S1 scenes in window ({orbit})")
        pairs = short_baseline_pairs(scenes, n_temporal_neighbors=args.neighbors)
        print(f"  {len(pairs)} SBAS pairs to submit")
        if args.dry_run:
            print("  (dry-run: skipping submission)")
            continue
        batch = submit_insar_pairs(
            pairs, project_name=f"sentinela-{dam['dam_id']}", dry_run=False
        )
        print(f"  submitted batch: {batch}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Report HyP3 batch status for one or more project names."""
    from collections import Counter

    import hyp3_sdk as sdk

    hyp3 = sdk.HyP3()
    project_names = args.project_names or [f"sentinela-{d}" for d in args.dam_ids]
    for name in project_names:
        batch = hyp3.find_jobs(name=name)
        if not batch.jobs:
            print(f"== {name}: no jobs found ==")
            continue
        print(f"== {name} ==")
        print(f"  total:  {len(batch)}")
        print(f"  {batch}")
        breakdown = Counter(j.status_code for j in batch.jobs)
        for status, n in sorted(breakdown.items()):
            print(f"    {status:10s} {n}")
        failed = [j for j in batch.jobs if j.status_code == "FAILED"]
        if failed:
            print("  FAILED jobs:")
            for j in failed[:5]:
                print(f"    {j.job_id} -- {j.processing_times}")
    return 0


def cmd_features(args: argparse.Namespace) -> int:
    """Extract per-dam features from local HyP3 products."""
    from sentinela.insar.features import TimeSeries, compute_features
    from sentinela.insar.timeseries import build_los_timeseries, timeseries_to_arrays

    sigbm = pd.read_parquet(SIGBM_CANONICAL)
    rows: list[dict] = []
    for products in sorted(INSAR_RAW_DIR.iterdir()) if INSAR_RAW_DIR.exists() else []:
        if not products.is_dir():
            continue
        dam_id = products.name
        meta = sigbm[sigbm["dam_id"] == dam_id]
        if meta.empty:
            print(f"  skip {dam_id}: not in SIGBM canonical")
            continue
        m = meta.iloc[0]
        ts = build_los_timeseries(products, dam_id=dam_id, dam_lat=m["lat"], dam_lon=m["lon"])
        if ts.empty:
            print(f"  skip {dam_id}: no HyP3 products found")
            continue
        td, los, stable = timeseries_to_arrays(ts)
        feats = compute_features(TimeSeries(
            times_days=td, los_mm=los, stable_reference_mm=stable,
        ))
        rows.append({
            "dam_id": dam_id,
            "n_obs": len(ts),
            "los_velocity_mm_yr": feats.los_velocity_mm_yr,
            "los_accel_90d_mm_yr2": feats.los_accel_90d_mm_yr2,
            "spectral_slope": feats.spectral_slope,
            "crest_vs_stable_variance_ratio": feats.crest_vs_stable_variance_ratio,
            "persistent_scatterer_density": feats.persistent_scatterer_density,
            "coherence_p10": feats.coherence_p10,
        })

    if not rows:
        print("no features extracted (no HyP3 products under data/raw/insar/<dam_id>/)")
        return 1

    out = pd.DataFrame(rows)
    INSAR_FEATURES_OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(INSAR_FEATURES_OUT)
    print(f"wrote {INSAR_FEATURES_OUT.relative_to(REPO_ROOT)} ({len(out)} dams)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pull = sub.add_parser("pull", help="submit HyP3 jobs for listed dams")
    p_pull.add_argument("--dam-ids", nargs="+", required=True)
    p_pull.add_argument("--start", default="2014-01-01")
    p_pull.add_argument("--end", default="2025-12-31")
    p_pull.add_argument(
        "--orbit",
        choices=("auto", "ASCENDING", "DESCENDING"),
        default="auto",
        help="Sentinel-1 orbit. 'auto' picks the better-covered orbit per dam "
             "(default; recommended). 'ASCENDING' / 'DESCENDING' force a choice.",
    )
    p_pull.add_argument("--radius-km", type=float, default=5.0)
    p_pull.add_argument("--neighbors", type=int, default=3)
    p_pull.add_argument("--dry-run", action="store_true",
                        help="search ASF but do not submit jobs")
    p_pull.set_defaults(func=cmd_pull)

    p_stat = sub.add_parser("status", help="report HyP3 batch status by project name")
    g = p_stat.add_mutually_exclusive_group(required=True)
    g.add_argument("--dam-ids", nargs="+",
                   help="dam IDs; project name will be 'sentinela-<dam_id>'")
    g.add_argument("--project-names", nargs="+",
                   help="explicit HyP3 project names")
    p_stat.set_defaults(func=cmd_status)

    p_feat = sub.add_parser("features", help="extract features from local products")
    p_feat.set_defaults(func=cmd_features)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
