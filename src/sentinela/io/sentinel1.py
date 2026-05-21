"""Sentinel-1 SAR / InSAR access via the ASF API + HyP3 hosted processing.

Why this is a thin orchestration layer
--------------------------------------
The heavy lifting of interferogram generation is done by **HyP3**, ASF's free
hosted Sentinel-1 processing service. We do not run ISCE2 / SNAP locally;
instead we submit job batches to HyP3, poll until they complete, then
download the processed unwrapped-phase GeoTIFFs. This avoids 10+ GB local
downloads of raw SLCs and dependency on a working CUDA toolchain.

Credentials
-----------
Set these two environment variables (or create a `.netrc` entry for
`urs.earthdata.nasa.gov`):

    EARTHDATA_USERNAME=<your NASA Earthdata Login username>
    EARTHDATA_PASSWORD=<your NASA Earthdata Login password>

Free Earthdata account: https://urs.earthdata.nasa.gov/users/new
HyP3 quota: 1,000 free processing jobs per month per user, ~24 h queue time.

What this module exposes
------------------------
    search_scenes(bbox, start, end, orbit) -> list of Sentinel-1 SLC scenes
    short_baseline_pairs(scenes, n_temporal_neighbors)
                                          -> SBAS pair list
    submit_insar_pairs(pairs, project)    -> HyP3 batch (async)
    download_completed(batch, dest_dir)   -> downloaded product paths
    bbox_for_dam(lat, lon, radius_km)     -> WGS84 bbox around a dam centroid

`asf_search` and `hyp3_sdk` are optional dependencies (installed via
`pip install -e ".[insar]"`); the imports are lazy so the main package
remains importable without them.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Scene:
    """Minimal in-memory record of a Sentinel-1 SLC granule."""

    granule: str
    track: int
    orbit: str   # "ASCENDING" or "DESCENDING"
    start_time: datetime
    bbox: tuple[float, float, float, float]   # (min_lon, min_lat, max_lon, max_lat)


def _resolve_credentials() -> tuple[str | None, str | None]:
    """Return (username, password) if explicitly available, else (None, None).

    Resolution order:
      1. Environment variables EARTHDATA_USERNAME / EARTHDATA_PASSWORD.
      2. A `.netrc` entry for `urs.earthdata.nasa.gov` (hyp3_sdk handles this
         automatically when we pass None/None, so we just verify the entry
         exists before letting the SDK proceed).
      3. Otherwise raise a friendly RuntimeError telling the user what to do.
    """
    user = os.environ.get("EARTHDATA_USERNAME")
    pwd = os.environ.get("EARTHDATA_PASSWORD")
    if user and pwd:
        return user, pwd

    # Check ~/.netrc for an Earthdata entry.
    try:
        import netrc

        nrc = netrc.netrc()
        auth = nrc.authenticators("urs.earthdata.nasa.gov")
        if auth:
            # hyp3_sdk will read .netrc itself when we pass None for both.
            return None, None
    except (FileNotFoundError, netrc.NetrcParseError):
        pass

    raise RuntimeError(
        "Earthdata credentials not found. Either:\n"
        "  (a) export EARTHDATA_USERNAME and EARTHDATA_PASSWORD in your shell, or\n"
        "  (b) add a .netrc entry for urs.earthdata.nasa.gov "
        "(chmod 600 ~/.netrc).\n"
        "Free Earthdata Login: https://urs.earthdata.nasa.gov/users/new"
    )


def bbox_for_dam(
    lat: float, lon: float, radius_km: float = 5.0
) -> tuple[float, float, float, float]:
    """Compute a small WGS84 bounding box centred on a dam.

    Used to constrain the ASF search to scenes that actually cover the dam.
    `radius_km` is the half-width of the box; 5 km is enough margin for most
    facilities while keeping the search cheap.
    """
    lat_deg = radius_km / 111.0
    lon_deg = radius_km / (111.0 * max(0.1, abs(math.cos(math.radians(lat)))))
    return (lon - lon_deg, lat - lat_deg, lon + lon_deg, lat + lat_deg)


def search_scenes(
    bbox: tuple[float, float, float, float],
    start: str,
    end: str,
    orbit: str = "ASCENDING",
) -> list[Scene]:
    """Search the ASF catalog for Sentinel-1 IW SLC scenes intersecting `bbox`.

    Parameters
    ----------
    bbox
        (min_lon, min_lat, max_lon, max_lat) in WGS84 decimal degrees.
    start, end
        ISO-8601 dates, inclusive (e.g. "2018-01-01").
    orbit
        "ASCENDING" or "DESCENDING".
    """
    import asf_search as asf  # lazy import

    wkt = (
        f"POLYGON(({bbox[0]} {bbox[1]}, {bbox[2]} {bbox[1]}, "
        f"{bbox[2]} {bbox[3]}, {bbox[0]} {bbox[3]}, {bbox[0]} {bbox[1]}))"
    )
    results = asf.geo_search(
        platform=[asf.PLATFORM.SENTINEL1],
        processingLevel=[asf.PRODUCT_TYPE.SLC],
        beamMode=[asf.BEAMMODE.IW],
        flightDirection=orbit,
        intersectsWith=wkt,
        start=start,
        end=end,
    )
    out: list[Scene] = []
    for r in results:
        props = r.properties
        geom = r.geometry["coordinates"][0]
        lons = [p[0] for p in geom]
        lats = [p[1] for p in geom]
        # HyP3 expects the bare scene name (e.g. S1A_IW_SLC__1SDV_...) without
        # the "-SLC" suffix that asf_search appends to `fileID`. `sceneName` is
        # the canonical bare identifier.
        granule = props.get("sceneName") or props["fileID"].removesuffix("-SLC")
        out.append(Scene(
            granule=granule,
            track=int(props.get("pathNumber", 0)),
            orbit=props.get("flightDirection", "").upper(),
            start_time=datetime.fromisoformat(props["startTime"].replace("Z", "+00:00")),
            bbox=(min(lons), min(lats), max(lons), max(lats)),
        ))
    return sorted(out, key=lambda s: s.start_time)


def pick_best_orbit(
    bbox: tuple[float, float, float, float],
    start: str,
    end: str,
) -> tuple[str, int]:
    """Return the orbit ("ASCENDING" or "DESCENDING") with more SLC coverage.

    Necessary because the Sentinel-1 ascending/descending coverage pattern
    over Brazil is uneven, especially in the early-mission years
    (2014-2016) when much of Minas Gerais was descending-only. Calling this
    before scene search ensures we don't silently submit a zero-scene job.

    Returns (orbit_name, scene_count). Ties go to DESCENDING because for the
    motivating dam (Mariana) descending coverage is the primary orbit.
    """
    asc = len(search_scenes(bbox, start, end, orbit="ASCENDING"))
    desc = len(search_scenes(bbox, start, end, orbit="DESCENDING"))
    if desc >= asc:
        return ("DESCENDING", desc)
    return ("ASCENDING", asc)


def short_baseline_pairs(
    scenes: list[Scene], n_temporal_neighbors: int = 3
) -> list[tuple[Scene, Scene]]:
    """Generate the short-baseline-subset (SBAS) pair list.

    Pairs are formed WITHIN a relative-orbit track (`track` attribute).
    Sentinel-1 has many tracks that may both intersect a small bbox; pairs
    formed across tracks have geometric baselines that exceed the InSAR
    coherence limit and will fail at HyP3 processing time. We discovered
    this empirically on the Brumadinho B1 submission: cross-track pairs
    accounted for ~40% of HyP3 failures before this fix.

    Within each track, pair each scene with its `n_temporal_neighbors`
    closest temporal successors — the standard SBAS-style design used by
    HyP3 batch processing.
    """
    by_track: dict[int, list[Scene]] = {}
    for s in scenes:
        by_track.setdefault(s.track, []).append(s)

    pairs: list[tuple[Scene, Scene]] = []
    for track_scenes in by_track.values():
        track_scenes = sorted(track_scenes, key=lambda s: s.start_time)
        for i, s in enumerate(track_scenes):
            for j in range(i + 1, min(len(track_scenes), i + 1 + n_temporal_neighbors)):
                pairs.append((s, track_scenes[j]))
    return pairs


def submit_insar_pairs(
    pairs: list[tuple[Scene, Scene]],
    project_name: str,
    *,
    looks: str = "20x4",
    include_los_displacement: bool = True,
    dry_run: bool = False,
) -> Any:
    """Submit a batch of InSAR pair jobs to HyP3.

    Returns the HyP3 `Batch` object; the caller polls or waits for completion.
    Set `dry_run=True` to validate the submission shape without using quota.
    """
    if dry_run:
        return {"submitted": False, "n_pairs": len(pairs), "project": project_name}

    import hyp3_sdk as sdk  # lazy import

    user, pwd = _resolve_credentials()
    hyp3 = sdk.HyP3(username=user, password=pwd)
    batch = sdk.Batch()
    for ref, sec in pairs:
        batch += hyp3.submit_insar_job(
            granule1=ref.granule,
            granule2=sec.granule,
            name=project_name,
            looks=looks,
            include_los_displacement=include_los_displacement,
            include_inc_map=True,
            include_dem=False,
            include_wrapped_phase=False,
        )
    return batch


def download_completed(batch: Any, dest_dir: Path) -> list[Path]:
    """Wait for and download a HyP3 batch into `dest_dir`. Returns product paths."""
    import hyp3_sdk as sdk  # lazy import

    user, pwd = _resolve_credentials()
    hyp3 = sdk.HyP3(username=user, password=pwd)
    dest_dir.mkdir(parents=True, exist_ok=True)
    completed = hyp3.watch(batch)
    paths: list[Path] = []
    for job in completed.jobs:
        if job.succeeded():
            for f in job.files:
                paths.append(Path(f.download(location=dest_dir)))
    return paths
