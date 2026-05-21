# data/scripts/

Runnable entry points for the data-cleaning pipeline. Each script is
deliberately thin — ≤ 80 lines — because the substantive logic lives in the
importable Python package under `src/sentinela/`. The split lets the data
pipeline be visible and reproducible alongside the data it produces, while
keeping the implementation testable and reusable from experiment code.

## Scripts

### `clean_sigbm.py`

Reads a raw ANM SIGBM CSV (semicolon-delimited, UTF-8 BOM, Brazilian decimal
format, DMS coordinates) and writes a canonical-schema parquet.

```bash
python data/scripts/clean_sigbm.py
# data/raw/sigbm/Relatorio_20260721.csv  ->  data/processed/sigbm_canonical.parquet

python data/scripts/clean_sigbm.py --input <path> --output <path>
```

Heavy lifting in `src/sentinela/io/sigbm.py::load` and `_parse_real_anm`.

### `build_cohort.py`

Reads the canonical SIGBM parquet and the curated failure-events CSV,
constructs the (`dam_id`, `month`) panel for the configured time window,
attaches horizon-windowed binary labels with right-censoring weights, and
writes the result to parquet.

```bash
python data/scripts/build_cohort.py
# data/processed/sigbm_canonical.parquet + data/external/brazilian_failures.csv
#   -> data/processed/cohort_panel.parquet

python data/scripts/build_cohort.py --start-month 2014-01 --end-month 2025-12 \
                                    --horizon-months 12 --severity-min 4
```

Heavy lifting in `src/sentinela/features/build.py::build_cohort_panel`.

### `build_insar_features.py`

Two-mode script for the Sentinel-1 InSAR pipeline.

```bash
# Submit HyP3 InSAR jobs for one or more dams (requires Earthdata credentials).
# Async; jobs queue at ASF and complete in 1-48 hours.
python data/scripts/build_insar_features.py pull \
       --dam-ids 8765 --start 2014-10-01 --end 2015-11-30

# Once HyP3 products are downloaded under data/raw/insar/<dam_id>/, extract
# per-dam precursor features (velocity, acceleration, spectral slope, variance
# ratio, coherence p10, PS density).
python data/scripts/build_insar_features.py features
```

Heavy lifting in `src/sentinela/io/sentinel1.py` (ASF + HyP3 orchestration),
`src/sentinela/insar/timeseries.py` (per-dam LOS sampling from rasters), and
`src/sentinela/insar/features.py` (feature extraction).

## Determinism

Both scripts are deterministic functions of their inputs and arguments. If
re-running produces a byte-identical parquet, the pipeline is unchanged; if
not, it is either an input change (new raw file) or a code change — log the
reason in `CHANGELOG.md`.

## Adding new pipeline stages

When ingesting a new data source (CHIRPS rainfall, Sentinel-1 InSAR
precursor features, IBGE population, etc.):

1. Implement the canonicalisation in `src/sentinela/io/<source>.py`.
2. Add a thin runnable script `data/scripts/clean_<source>.py` that calls it.
3. Add the produced artefact to `data/processed/` and to the table in
   `data/processed/README.md`.
4. If the artefact should be committed, allow-list it in `.gitignore`.
5. Update `data/README.md` (the navigation key) and the data audit
   `docs/03-data.md`.
