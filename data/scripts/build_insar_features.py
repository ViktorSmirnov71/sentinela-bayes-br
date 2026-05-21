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


def cmd_download(args: argparse.Namespace) -> int:
    """Download succeeded HyP3 products into data/raw/insar/<id>/.

    Files arrive as .zip per pair; we extract them so the *_unw_phase.tif
    rasters that the feature extractor consumes are present at the
    expected path.

    Accepts either:
      --dam-ids <id> ...    -> project name 'sentinela-<id>', local dir <id>
      --project-name <name> -> arbitrary project; local dir = name without
                               'sentinela-' prefix (or the name itself if no
                               such prefix). Useful for ad-hoc submissions
                               like the actual Fundão coordinates that are
                               not in the SIGBM cohort.
    """
    import zipfile
    from collections import Counter

    import hyp3_sdk as sdk

    if args.project_name:
        targets = [(args.project_name,
                    args.project_name.removeprefix("sentinela-"))]
    else:
        targets = [(f"sentinela-{d}", d) for d in args.dam_ids]

    hyp3 = sdk.HyP3()
    for name, dir_id in targets:
        batch = hyp3.find_jobs(name=name)
        if not batch.jobs:
            print(f"== {name}: no jobs found ==")
            continue
        ok = [j for j in batch.jobs if j.status_code == "SUCCEEDED"]
        breakdown = Counter(j.status_code for j in batch.jobs)
        print(f"== {name} ==")
        print(f"  total {len(batch)}; breakdown: {dict(breakdown)}")
        if not ok:
            print("  no succeeded jobs to download yet")
            continue
        dest = INSAR_RAW_DIR / dir_id
        dest.mkdir(parents=True, exist_ok=True)
        print(f"  downloading {len(ok)} products into {dest.relative_to(REPO_ROOT)}")
        # Download each job's product zip; skip if already present.
        from tqdm import tqdm

        for job in tqdm(ok, desc=f"  {dir_id}", unit="job"):
            for path in job.download_files(location=dest, create=True):
                if path.suffix == ".zip" and not args.no_unzip:
                    try:
                        with zipfile.ZipFile(path) as zf:
                            zf.extractall(dest)
                        if args.cleanup_zip:
                            path.unlink()
                    except zipfile.BadZipFile:
                        print(f"    warning: bad zip {path}; skipping unpack")
        n_tifs = sum(1 for _ in dest.rglob("*_unw_phase.tif"))
        print(f"  done: {n_tifs} *_unw_phase.tif files now under {dest.relative_to(REPO_ROOT)}")
    return 0


def cmd_features(args: argparse.Namespace) -> int:
    """Extract per-dam features from local HyP3 products.

    Default: iterate every subdir of data/raw/insar/; match against SIGBM.
    --target <id> --coords LAT LON  : single ad-hoc location (e.g. an actual
        failed-dam coordinate that's no longer in SIGBM).
    """
    from sentinela.insar.features import TimeSeries, compute_features
    from sentinela.insar.timeseries import build_los_timeseries, timeseries_to_arrays

    rows: list[dict] = []

    if args.target and args.coords:
        # Ad-hoc single-target path: bypass SIGBM lookup.
        dam_lat, dam_lon = args.coords
        products = INSAR_RAW_DIR / args.target
        if not products.exists():
            print(f"  {products.relative_to(REPO_ROOT)} not found")
            return 1
        ts = build_los_timeseries(products, dam_id=args.target,
                                  dam_lat=dam_lat, dam_lon=dam_lon)
        if ts.empty:
            print(f"  no HyP3 products under {products.relative_to(REPO_ROOT)}")
            return 1
        td, los, stable = timeseries_to_arrays(ts)
        feats = compute_features(TimeSeries(
            times_days=td, los_mm=los, stable_reference_mm=stable,
        ))
        rows.append({
            "dam_id": args.target,
            "n_obs": len(ts),
            "los_velocity_mm_yr": feats.los_velocity_mm_yr,
            "los_accel_90d_mm_yr2": feats.los_accel_90d_mm_yr2,
            "spectral_slope": feats.spectral_slope,
            "crest_vs_stable_variance_ratio": feats.crest_vs_stable_variance_ratio,
            "persistent_scatterer_density": feats.persistent_scatterer_density,
            "coherence_p10": feats.coherence_p10,
        })
        # Ad-hoc target uses its own output file so it doesn't clobber the
        # SIGBM-cohort parquet that experiment 01 reads.
        out_path = INSAR_FEATURES_OUT.with_name(f"insar_features_{args.target}.parquet")
        out = pd.DataFrame(rows)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(out_path)
        print(f"wrote {out_path.relative_to(REPO_ROOT)}")
        print(out.T.to_string())
        return 0

    # Default path: SIGBM-cohort iteration.
    sigbm = pd.read_parquet(SIGBM_CANONICAL)
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

    p_dl = sub.add_parser("download", help="download succeeded HyP3 products locally")
    dl_grp = p_dl.add_mutually_exclusive_group(required=True)
    dl_grp.add_argument("--dam-ids", nargs="+",
                        help="dam IDs; project = 'sentinela-<id>', local dir = <id>")
    dl_grp.add_argument("--project-name",
                        help="explicit HyP3 project name; local dir = name without "
                             "'sentinela-' prefix (for ad-hoc submissions)")
    p_dl.add_argument("--no-unzip", action="store_true",
                      help="keep .zip files instead of unpacking the *_unw_phase.tif")
    p_dl.add_argument("--cleanup-zip", action="store_true",
                      help="remove .zip files after successful extraction")
    p_dl.set_defaults(func=cmd_download)

    p_feat = sub.add_parser("features", help="extract features from local products")
    p_feat.add_argument("--coords", nargs=2, type=float, metavar=("LAT", "LON"),
                        help="for an ad-hoc directory under data/raw/insar/<id>/ that "
                             "isn't a SIGBM dam, sample at this (lat, lon) instead.")
    p_feat.add_argument("--target", help="single directory id to process "
                                          "(default: every dir under data/raw/insar)")
    p_feat.set_defaults(func=cmd_features)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
