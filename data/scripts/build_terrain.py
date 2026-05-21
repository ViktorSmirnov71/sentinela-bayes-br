"""Build a Brazil DEM (digital elevation model) from public AWS terrain tiles.

Source: the **terrarium** format tiles published on the AWS Open Data Registry
at `s3://elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`. These are PNG tiles
where each pixel's RGB encodes elevation in metres:

    elevation_m = (R * 256 + G + B / 256) - 32768

We fetch tiles at zoom 5 (~5 km per pixel — plenty for a viz that operates at
the country scale), stitch them into one large elevation array clipped to
Brazil's bounding box, downsample to a viz-friendly resolution, and write
the result as a compact JSON heightmap consumed by the Three.js terrain mesh.

Reproducibility: deterministic given the upstream tiles. Re-running yields
byte-identical output.
"""
from __future__ import annotations

import json
import math
from io import BytesIO
from pathlib import Path

import numpy as np
import requests
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "viz" / "data"

# Brazil bbox (WGS84): lon -75 .. -30, lat -35 .. 6.
LON_MIN, LON_MAX = -75.0, -30.0
LAT_MIN, LAT_MAX = -35.0, 6.0

ZOOM = 5
TILE_BASE = "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"
TILE_SIZE = 256
DOWNSAMPLE_TO = (320, 280)   # (width, height) of the output heightmap


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_lon_w(x: int, z: int) -> float:
    return x / (2 ** z) * 360.0 - 180.0


def tile_to_lat_n(y: int, z: int) -> float:
    n = 2 ** z
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def decode_terrarium(arr: np.ndarray) -> np.ndarray:
    """Decode a (H, W, 3) uint8 terrarium image to metres of elevation."""
    r = arr[..., 0].astype(np.int32)
    g = arr[..., 1].astype(np.int32)
    b = arr[..., 2].astype(np.int32)
    return (r * 256 + g + b / 256.0) - 32768.0


def fetch_tile(z: int, x: int, y: int) -> np.ndarray | None:
    url = TILE_BASE.format(z=z, x=x, y=y)
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        print(f"  miss z={z} x={x} y={y}: HTTP {r.status_code}")
        return None
    img = Image.open(BytesIO(r.content)).convert("RGB")
    return np.asarray(img)


def main() -> int:
    x_min, y_max_tile = lonlat_to_tile(LON_MIN, LAT_MIN, ZOOM)
    x_max, y_min_tile = lonlat_to_tile(LON_MAX, LAT_MAX, ZOOM)
    n_tiles_x = x_max - x_min + 1
    n_tiles_y = y_max_tile - y_min_tile + 1
    print(f"zoom {ZOOM}: {n_tiles_x} x {n_tiles_y} = {n_tiles_x * n_tiles_y} tiles")

    big = np.zeros((n_tiles_y * TILE_SIZE, n_tiles_x * TILE_SIZE), dtype=np.float32)

    for ty in range(y_min_tile, y_max_tile + 1):
        for tx in range(x_min, x_max + 1):
            arr = fetch_tile(ZOOM, tx, ty)
            if arr is None:
                continue
            elev = decode_terrarium(arr).astype(np.float32)
            dy, dx = (ty - y_min_tile) * TILE_SIZE, (tx - x_min) * TILE_SIZE
            big[dy:dy + TILE_SIZE, dx:dx + TILE_SIZE] = elev

    # Crop to exact Brazil bbox in pixel coordinates.
    lon_w_tile = tile_to_lon_w(x_min, ZOOM)
    lon_e_tile = tile_to_lon_w(x_max + 1, ZOOM)
    lat_n_tile = tile_to_lat_n(y_min_tile, ZOOM)
    lat_s_tile = tile_to_lat_n(y_max_tile + 1, ZOOM)
    full_w = big.shape[1]
    full_h = big.shape[0]
    px_l = int((LON_MIN - lon_w_tile) / (lon_e_tile - lon_w_tile) * full_w)
    px_r = int((LON_MAX - lon_w_tile) / (lon_e_tile - lon_w_tile) * full_w)
    px_t = int((lat_n_tile - LAT_MAX) / (lat_n_tile - lat_s_tile) * full_h)
    px_b = int((lat_n_tile - LAT_MIN) / (lat_n_tile - lat_s_tile) * full_h)
    cropped = big[px_t:px_b, px_l:px_r]
    print(f"cropped to {cropped.shape[1]} x {cropped.shape[0]} px")

    # Clamp negative elevations (ocean) to 0 so the mesh doesn't sink below ground.
    cropped = np.where(cropped < 0, 0, cropped)

    # Block-mean downsample.
    out_w, out_h = DOWNSAMPLE_TO
    block_w = cropped.shape[1] // out_w
    block_h = cropped.shape[0] // out_h
    trim_w = block_w * out_w
    trim_h = block_h * out_h
    trimmed = cropped[:trim_h, :trim_w]
    reshaped = trimmed.reshape(out_h, block_h, out_w, block_w)
    downsampled = reshaped.mean(axis=(1, 3))
    print(f"downsampled to {downsampled.shape[1]} x {downsampled.shape[0]}")
    print(f"  elevation range: {float(downsampled.min()):.0f} .. {float(downsampled.max()):.0f} m")

    payload = {
        "width": int(downsampled.shape[1]),
        "height": int(downsampled.shape[0]),
        "lon_min": LON_MIN, "lon_max": LON_MAX,
        "lat_min": LAT_MIN, "lat_max": LAT_MAX,
        "elev_min_m": float(downsampled.min()),
        "elev_max_m": float(downsampled.max()),
        # Row-major flattened elevation array, rounded to nearest metre to
        # shrink the JSON. Read in JS as a Float32Array via row * width + col.
        "elevation_m": np.round(downsampled).astype(int).flatten().tolist(),
        "source": "terrarium tiles via elevation-tiles-prod (AWS Open Data)",
        "zoom_level": ZOOM,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "terrain.json"
    out_path.write_text(json.dumps(payload))
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
