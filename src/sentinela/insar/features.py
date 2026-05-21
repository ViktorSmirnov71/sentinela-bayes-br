"""Derive precursor features from per-dam Sentinel-1 LOS displacement time series.

Feature set is grounded in the post-Brumadinho retrospective literature:
- Grebby et al. 2021     — anomaly variance ratio (dam crest vs. stable reference)
                           plus accelerating-displacement detection.
- Carlà et al. 2019      — inverse-velocity precursor and spectral-slope analysis
                           of pre-failure displacement.
- Macchiarulo et al. 2023— moisture-corrected displacement (separately handled
                           by feature attachment in build.py; not in this file).

Every function in this module operates on numpy arrays of `times_days` (days
since the first observation) and `los_mm` (line-of-sight displacement in mm,
sign convention: negative = moving away from satellite = subsidence). They
are deterministic, side-effect free, and depend only on numpy / scipy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class InsarFeatures:
    """Precursor feature bundle for one dam at one evaluation time."""

    los_velocity_mm_yr: float
    los_accel_90d_mm_yr2: float
    spectral_slope: float
    crest_vs_stable_variance_ratio: float
    persistent_scatterer_density: float
    coherence_p10: float


# ---------------------------------------------------------------------------
# Velocity
# ---------------------------------------------------------------------------

def los_velocity(times_days: np.ndarray, los_mm: np.ndarray) -> float:
    """Robust linear-trend slope (mm/yr) via Theil–Sen.

    Theil–Sen is the median of all pairwise slopes; it is breakdown-robust
    (up to 29.3% outliers) which matters because InSAR series contain phase-
    unwrapping jumps and atmospheric artefacts at any time.
    """
    t, y = _clean(times_days, los_mm)
    if len(t) < 2:
        return float("nan")
    # Pairwise slopes (i < j): (y_j - y_i) / (t_j - t_i)
    ii, jj = np.triu_indices(len(t), k=1)
    dt = t[jj] - t[ii]
    valid = dt > 0
    if not valid.any():
        return float("nan")
    slopes = (y[jj][valid] - y[ii][valid]) / dt[valid]
    return float(np.median(slopes) * DAYS_PER_YEAR)


# ---------------------------------------------------------------------------
# Acceleration
# ---------------------------------------------------------------------------

def acceleration_90d(times_days: np.ndarray, los_mm: np.ndarray) -> float:
    """Acceleration of LOS displacement in the trailing 12-month window (mm/yr²).

    We fit a quadratic y = a t² + b t + c over the trailing window and report
    -2a as the acceleration magnitude in the "subsidence accelerating"
    direction (positive output means subsidence is accelerating; this is the
    Carlà 2019 inverse-velocity-style precursor). Quadratic fitting over the
    full window is far more noise-robust than first-differencing short-window
    velocity estimates, and it is the canonical operationalisation in the
    inverse-velocity literature.

    The function name preserves "90d" for compatibility with the planned
    methodology spec (where 90 days denoted the velocity-window size); the
    actual implementation uses a 12-month trailing window over which to
    estimate the quadratic, which is more numerically stable.
    """
    t, y = _clean(times_days, los_mm)
    if len(t) < 6:
        return float("nan")
    window_days = 365.0
    in_window = t >= (t.max() - window_days)
    if in_window.sum() < 4:
        return float("nan")
    sub_t = t[in_window]
    sub_y = y[in_window]
    # Convert time to years for interpretable coefficients.
    sub_t_yr = (sub_t - sub_t.min()) / DAYS_PER_YEAR
    a, _b, _c = np.polyfit(sub_t_yr, sub_y, 2)
    # y = a t² + b t + c   =>   y'' = 2a.
    # Positive output = subsidence is accelerating (the precursor direction).
    return float(-2.0 * a)


# ---------------------------------------------------------------------------
# Spectral slope
# ---------------------------------------------------------------------------

def spectral_slope(times_days: np.ndarray, los_mm: np.ndarray) -> float:
    """Slope of the displacement-time-series PSD on a log-log axis.

    We resample to a uniform grid by linear interpolation, only remove the
    series mean (NOT the trend — the trend IS the signal we want to detect),
    and fit a least-squares line in log-log space over the low-frequency half
    of the Welch periodogram. A more negative slope indicates more power
    concentrated at low frequencies — the spectral signature of drift /
    accelerating creep relative to white-noise atmospheric and InSAR
    measurement noise.
    """
    from scipy.signal import welch

    t, y = _clean(times_days, los_mm)
    if len(t) < 16:
        return float("nan")
    n = len(t)
    t_uni = np.linspace(t.min(), t.max(), n)
    y_uni = np.interp(t_uni, t, y)
    # Mean-centre only. Detrending here would remove the very signal we want
    # the spectral slope to be sensitive to.
    y_centred = y_uni - y_uni.mean()
    dt_med = float(np.median(np.diff(t_uni)))
    if dt_med <= 0:
        return float("nan")
    fs = 1.0 / dt_med  # samples per day
    freqs, pxx = welch(y_centred, fs=fs, nperseg=min(64, n))
    keep = (freqs > 0) & (pxx > 0)
    freqs = freqs[keep]
    pxx = pxx[keep]
    if len(freqs) < 4:
        return float("nan")
    lo = slice(0, max(4, len(freqs) // 2))
    slope, _ = np.polyfit(np.log(freqs[lo]), np.log(pxx[lo]), 1)
    return float(slope)


# ---------------------------------------------------------------------------
# Grebby-style variance ratio
# ---------------------------------------------------------------------------

def crest_vs_stable_variance_ratio(
    crest_series: np.ndarray, stable_series: np.ndarray
) -> float:
    """Ratio of dam-crest variance to a geomorphically stable reference variance.

    Operationalises the Grebby et al. 2021 "anomaly indicator" idea: detrend
    both series and compare their residual variance. A ratio >> 1 means the
    dam is moving in a way the surrounding stable ground is not, after the
    common-mode atmospheric and seasonal signals are removed by subtracting
    the local linear trend in each series.
    """
    crest = np.asarray(crest_series, dtype=float)
    stable = np.asarray(stable_series, dtype=float)
    crest = crest[np.isfinite(crest)]
    stable = stable[np.isfinite(stable)]
    if len(crest) < 4 or len(stable) < 4:
        return float("nan")
    crest_det = _detrend(crest)
    stable_det = _detrend(stable)
    var_stable = float(np.var(stable_det))
    var_crest = float(np.var(crest_det))
    if var_stable <= 0:
        return float("nan")
    return var_crest / var_stable


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

class TimeSeries(NamedTuple):
    """Per-dam Sentinel-1 LOS series with optional reference time-series."""

    times_days: np.ndarray
    los_mm: np.ndarray
    stable_reference_mm: np.ndarray | None = None
    coherence: np.ndarray | None = None
    persistent_scatterer_count: int | None = None
    dam_area_km2: float | None = None


def compute_features(ts: TimeSeries) -> InsarFeatures:
    """Compute the full precursor feature bundle for a single dam."""
    v = los_velocity(ts.times_days, ts.los_mm)
    a = acceleration_90d(ts.times_days, ts.los_mm)
    s = spectral_slope(ts.times_days, ts.los_mm)

    if ts.stable_reference_mm is not None:
        vr = crest_vs_stable_variance_ratio(ts.los_mm, ts.stable_reference_mm)
    else:
        vr = float("nan")

    if ts.coherence is not None and len(ts.coherence) > 0:
        coh_p10 = float(np.nanpercentile(ts.coherence, 10))
    else:
        coh_p10 = float("nan")

    if ts.persistent_scatterer_count is not None and ts.dam_area_km2:
        ps_density = ts.persistent_scatterer_count / ts.dam_area_km2
    else:
        ps_density = float("nan")

    return InsarFeatures(
        los_velocity_mm_yr=v,
        los_accel_90d_mm_yr2=a,
        spectral_slope=s,
        crest_vs_stable_variance_ratio=vr,
        persistent_scatterer_density=ps_density,
        coherence_p10=coh_p10,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(times_days: np.ndarray, los_mm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop NaNs, sort by time, ensure float dtype."""
    t = np.asarray(times_days, dtype=float)
    y = np.asarray(los_mm, dtype=float)
    if t.shape != y.shape:
        raise ValueError(f"shape mismatch: times {t.shape}, los {y.shape}")
    finite = np.isfinite(t) & np.isfinite(y)
    t, y = t[finite], y[finite]
    order = np.argsort(t)
    return t[order], y[order]


def _detrend(y: np.ndarray) -> np.ndarray:
    """Subtract least-squares linear trend (using the array's own index as x)."""
    if len(y) < 2:
        return y
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return y - (slope * x + intercept)
