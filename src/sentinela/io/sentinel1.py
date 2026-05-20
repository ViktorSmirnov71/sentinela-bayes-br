"""Sentinel-1 SAR / InSAR access and processing entry points.

Primary processing path is HyP3 (ASF) for short-baseline InSAR pairs over each
dam centroid. The full ISCE2 + MintPy path is reserved for the retrospective
Fundão / B1 reanalyses where time-series quality matters most.

Functions here orchestrate requests; the heavy lifting lives in
src/sentinela/insar/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Scene:
    granule: str   # e.g. S1A_IW_SLC__1SDV_20180102T083421_...
    track: int
    orbit: str     # ASCENDING or DESCENDING
    start_time: str
    bbox: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat


def search(
    bbox: tuple[float, float, float, float],
    start: str,
    end: str,
    orbit: str = "ASCENDING",
) -> list[Scene]:
    """Search the ASF catalog for Sentinel-1 SLC scenes intersecting bbox."""
    raise NotImplementedError("Wire to asf_search.")


def request_hyp3_insar_pairs(
    scenes: list[Scene],
    dest_dir: Path,
    max_pairs: int = 24,
) -> list[Path]:
    """Submit short-baseline InSAR pair jobs to ASF HyP3 and return result paths."""
    raise NotImplementedError("Wire to hyp3_sdk.")
