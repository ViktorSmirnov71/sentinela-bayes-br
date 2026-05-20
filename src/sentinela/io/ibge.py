"""IBGE loaders for downstream-exposure features.

Primary needs:
- gridded population (for runout-extent exposure)
- aglomerados subnormais delineations (informal settlements)
- municipality boundaries (joins)
"""
from __future__ import annotations

from pathlib import Path


def load_population_grid(path: Path):
    """Return a population xarray DataArray on a regular grid over Brazil."""
    raise NotImplementedError


def load_aglomerados(path: Path):
    """Return a GeoDataFrame of informal-settlement polygons (IBGE)."""
    raise NotImplementedError
