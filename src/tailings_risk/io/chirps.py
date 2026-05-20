"""CHIRPS daily precipitation loader (0.05° global)."""
from __future__ import annotations

from pathlib import Path

import xarray as xr


def open_chirps(path: Path) -> xr.Dataset:
    """Open the CHIRPS netCDF over Brazil and return the precip variable."""
    raise NotImplementedError
