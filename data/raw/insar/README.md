# data/raw/insar/

HyP3-processed Sentinel-1 InSAR products land here, organised by SIGBM
`dam_id`:

```
data/raw/insar/
├── README.md         (this file)
├── 8765/             Barragem de Germano (Fundão proxy)
│   ├── S1AA_20141015T...unw_phase.tif
│   ├── S1AA_20141027T...unw_phase.tif
│   └── ...
├── 8505/             Barragem B1 (Mineracao Geral, Brumadinho)
└── ...
```

The whole tree is **gitignored** — InSAR products are tens to hundreds of
megabytes each and are reproducible from public ASF data. The committed
artefacts derived from them live in `data/processed/insar_features.parquet`.

## Credentials

ASF requires a free NASA Earthdata Login. Sign up at
<https://urs.earthdata.nasa.gov/users/new>, then export your credentials:

```bash
export EARTHDATA_USERNAME=<your-username>
export EARTHDATA_PASSWORD=<your-password>
```

or add a `.netrc` entry for `urs.earthdata.nasa.gov`. HyP3 gives every
account 1,000 free InSAR jobs per month with a typical queue time of 1 to 48
hours per job.

## How to populate this directory

```bash
# Submit jobs for one dam (e.g. dam_id 8765, the Fundão modeling proxy):
python data/scripts/build_insar_features.py pull \
       --dam-ids 8765 \
       --start 2014-10-01 --end 2015-11-30 \
       --orbit ASCENDING

# Wait for completion (HyP3 emails when each job is ready).
# Then download products into data/raw/insar/8765/. The HyP3 console at
# https://hyp3-api.asf.alaska.edu/ has bulk-download URLs and a CLI.

# Once products are local, extract features:
python data/scripts/build_insar_features.py features
```

## What "completed" looks like

A successful HyP3 InSAR job yields a `.zip` per pair containing:
- `S1AA_<refDate>_<secDate>_..._unw_phase.tif` — unwrapped phase (this is
  what `timeseries.py` samples).
- `S1AA_..._corr.tif` — coherence map.
- `S1AA_..._inc_map.tif` — incidence-angle map.
- `S1AA_..._dem.tif`, `S1AA_..._water_mask.tif`, supporting metadata.

Unzip everything under `data/raw/insar/<dam_id>/`. The `features` subcommand
recursively globs for `*_unw_phase.tif` so directory depth is flexible.

## Why this stays local-only

- Each pair product is ~100 MB. For 8765 over Oct-2014 to Nov-2015 with a
  ~12-day revisit and 3-neighbour SBAS pairing, that is ~100 pairs × 100 MB
  ≈ 10 GB per dam.
- The products are bit-for-bit reproducible from open ASF data; no scientific
  reason to commit them.
- All scientific information is captured in `data/processed/insar_features.parquet`,
  which is ~1 KB per dam and is committed.
