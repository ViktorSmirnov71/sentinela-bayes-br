"""Build per-dam LOS displacement time series from HyP3 unwrapped-phase rasters.

HyP3 InSAR products land as directories named like
    S1AA_<refDate>T<...>_<secDate>T<...>_VVP012_INT80_G_unw_phase.tif
where the GeoTIFF inside is the unwrapped-phase raster reprojected to UTM with
LOS displacement metadata. For each (dam, pair) we sample the median pixel
within a small buffer around the dam centroid; we also sample a "stable
reference" point ~3 km away so the variance-ratio feature has a clean
baseline.

The output is a tidy DataFrame:

    dam_id  reference_date  secondary_date  los_mm  stable_ref_mm  coherence_mean

This module's functions are pure I/O over rasters — heavy geospatial deps
(`rasterio`, `geopandas`) are lazy-imported so the rest of the package stays
importable without the `insar` extra installed.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# HyP3 product naming: dates are at positions 2 and 6 in the underscore split.
_HYP3_NAME_RE = re.compile(
    r"S1[AB]{2}_(?P<ref>\d{8}T\d{6})_(?P<sec>\d{8}T\d{6})_.+_unw_phase\.tif$",
    re.IGNORECASE,
)


def _parse_hyp3_dates(p: Path) -> tuple[datetime, datetime] | None:
    m = _HYP3_NAME_RE.search(p.name)
    if not m:
        return None
    return (
        datetime.strptime(m.group("ref"), "%Y%m%dT%H%M%S"),
        datetime.strptime(m.group("sec"), "%Y%m%dT%H%M%S"),
    )


def _sample_raster_median(
    raster_path: Path, lon: float, lat: float, buffer_m: float = 100.0
) -> float:
    """Return median raster value within `buffer_m` of (lat, lon).

    Reprojects the sample-window from WGS84 into the raster's CRS, masks the
    pixels inside that window, returns their median. NaN if no valid pixels.
    """
    import rasterio
    from rasterio.warp import transform as warp_transform
    from rasterio.windows import from_bounds

    with rasterio.open(raster_path) as src:
        xs, ys = warp_transform("EPSG:4326", src.crs, [lon], [lat])
        cx, cy = xs[0], ys[0]
        # Raster CRS is metric (UTM) for HyP3 products; buffer_m is in metres.
        minx, miny = cx - buffer_m, cy - buffer_m
        maxx, maxy = cx + buffer_m, cy + buffer_m
        try:
            win = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        except (rasterio.errors.WindowError, ValueError):
            return float("nan")
        data = src.read(1, window=win, masked=True)
        arr = np.ma.filled(data.astype(float), np.nan)
        valid = arr[np.isfinite(arr)]
        if valid.size == 0:
            return float("nan")
        return float(np.median(valid))


def _offset_point(
    lat: float, lon: float, bearing_deg: float = 90.0, distance_km: float = 3.0
) -> tuple[float, float]:
    """Move (lat, lon) by `distance_km` along `bearing_deg` on a sphere."""
    # First-order spherical approximation; sufficient at the km scale.
    R = 6371.0  # km
    br = math.radians(bearing_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    new_lat = math.asin(
        math.sin(lat_r) * math.cos(distance_km / R)
        + math.cos(lat_r) * math.sin(distance_km / R) * math.cos(br)
    )
    new_lon = lon_r + math.atan2(
        math.sin(br) * math.sin(distance_km / R) * math.cos(lat_r),
        math.cos(distance_km / R) - math.sin(lat_r) * math.sin(new_lat),
    )
    return math.degrees(new_lat), math.degrees(new_lon)


def build_los_timeseries(
    products_dir: Path,
    dam_id: str,
    dam_lat: float,
    dam_lon: float,
    *,
    dam_buffer_m: float = 100.0,
    stable_ref_distance_km: float = 3.0,
    stable_ref_bearing_deg: float = 90.0,
) -> pd.DataFrame:
    """Assemble a per-dam LOS displacement time series from HyP3 products.

    Each HyP3 pair yields one observation: median LOS displacement (mm) at the
    dam centroid, plus the same at a nearby stable reference point for the
    Grebby-style variance-ratio computation.

    Parameters
    ----------
    products_dir
        Directory containing HyP3 unwrapped-phase GeoTIFFs.
    dam_id, dam_lat, dam_lon
        Identifier and WGS84 coordinates of the dam.
    dam_buffer_m
        Half-width in metres of the sampling window around the centroid.
    stable_ref_distance_km, stable_ref_bearing_deg
        Where to place the reference point relative to the dam. Defaults to
        3 km east (chosen to avoid contamination from the dam's downstream
        runout corridor; real deployments should set this per-dam after
        inspecting the local geomorphology).

    Returns
    -------
    DataFrame with columns:
        dam_id, reference_date, secondary_date, los_mm, stable_ref_mm
    """
    ref_lat, ref_lon = _offset_point(
        dam_lat, dam_lon, bearing_deg=stable_ref_bearing_deg, distance_km=stable_ref_distance_km
    )
    rows: list[dict] = []
    for path in sorted(Path(products_dir).rglob("*_unw_phase.tif")):
        dates = _parse_hyp3_dates(path)
        if dates is None:
            continue
        ref_dt, sec_dt = dates
        los = _sample_raster_median(path, dam_lon, dam_lat, buffer_m=dam_buffer_m)
        stable = _sample_raster_median(path, ref_lon, ref_lat, buffer_m=dam_buffer_m)
        rows.append({
            "dam_id": dam_id,
            "reference_date": ref_dt,
            "secondary_date": sec_dt,
            "los_mm": los,
            "stable_ref_mm": stable,
        })
    return pd.DataFrame(rows).sort_values("secondary_date").reset_index(drop=True)


def timeseries_to_arrays(
    ts: pd.DataFrame, reference_date: datetime | None = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert the long-form time series into arrays for the feature extractors.

    Returns `(times_days, los_mm, stable_ref_mm)`. `times_days` counts days
    since `reference_date`; if omitted, the first observation is the origin.
    """
    if ts.empty:
        empty = np.array([], dtype=float)
        return empty, empty, empty
    t0 = reference_date or ts["secondary_date"].min()
    times = (ts["secondary_date"] - t0).dt.total_seconds().to_numpy() / 86400.0
    return (
        times.astype(float),
        ts["los_mm"].to_numpy(dtype=float),
        ts["stable_ref_mm"].to_numpy(dtype=float),
    )
