# data/

This directory is the project's complete data layer: everything ingested,
everything produced, and the scripts that connect the two. The repository is
designed so a clean clone can reproduce every artefact in this folder by
running the scripts in `data/scripts/`.

## Navigation

```
data/
├── README.md                             ← (this file) navigation key
│
├── raw/                                  ← inputs as obtained from the source
│   ├── README.md
│   └── sigbm/
│       └── Relatorio_20260721.csv        ← ANM SIGBM export, 911 dams (committed)
│
├── external/                             ← citation-anchored, hand-curated
│   ├── README.md
│   └── brazilian_failures.csv            ← 8 documented failure events (committed)
│
├── interim/                              ← reserved for intermediate artefacts
│   └── (gitignored)
│
├── processed/                            ← model-ready cleaned outputs
│   ├── README.md
│   ├── sigbm_canonical.parquet           ← cleaned SIGBM (committed, 67 KB)
│   └── cohort_panel.parquet              ← (dam, month) panel with labels (committed, 51 KB)
│
└── scripts/                              ← runnable pipeline entry points
    ├── README.md
    ├── clean_sigbm.py                    ← raw/sigbm/*.csv  ->  processed/sigbm_canonical.parquet
    └── build_cohort.py                   ← canonical + external/failures  ->  processed/cohort_panel.parquet
```

## Pipeline flow

```
                  ┌──────────────────────────────────┐
                  │   raw/sigbm/Relatorio_*.csv      │   (manual download from ANM)
                  └────────────────┬─────────────────┘
                                   │
                  data/scripts/clean_sigbm.py
                                   │
                                   ▼
                  ┌──────────────────────────────────┐
                  │   processed/sigbm_canonical      │   (911 dams, canonical schema)
                  └────────────────┬─────────────────┘
                                   │
                                   ├── external/brazilian_failures.csv  (8 events)
                                   │
                  data/scripts/build_cohort.py       │
                                   │                ▼
                                   ▼
                  ┌──────────────────────────────────┐
                  │   processed/cohort_panel         │   (126,288 dam-month rows, labels)
                  └────────────────┬─────────────────┘
                                   │
                                   ▼
                  experiments/00_baselines/run.py   ->   results/00_baselines/
```

## How to reproduce every file in this folder

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Step 1: clean the raw SIGBM CSV into the canonical parquet.
python data/scripts/clean_sigbm.py

# Step 2: build the (dam, month) cohort panel with horizon-windowed labels.
python data/scripts/build_cohort.py

# Step 3: run baselines (writes to results/00_baselines/).
python experiments/00_baselines/run.py --sigbm data/raw/sigbm/Relatorio_20260721.csv
```

A clean clone of the repository contains the raw input and the cleaned
outputs both. Steps 1 and 2 will regenerate the parquets byte-for-byte from
the committed CSV; deletion-and-regeneration is a useful diff check when
modifying the cleaning pipeline.

## Folder roles in one sentence each

| Folder | Role | Committed to git? |
|---|---|---|
| `raw/` | Inputs exactly as obtained from the data source (untouched). | Selectively — the published SIGBM snapshot is committed; future raw files default to local-only. |
| `external/` | Hand-curated, citation-anchored tables that have no machine source (e.g. historical failure events). | Yes, in full. |
| `interim/` | Working scratch for pipeline intermediates. | No. |
| `processed/` | Model-ready outputs produced by `scripts/`. | Yes, in full — they ARE the published research artefacts. |
| `scripts/` | Thin runnable entry points to the cleaning pipeline. The heavy logic lives in `src/sentinela/`. | Yes. |

## Provenance for each file

| File | Source | Generator | Documented in |
|---|---|---|---|
| `raw/sigbm/Relatorio_20260721.csv` | https://app.anm.gov.br/sigbm/publico  ->  Data Extraction, manual download 2026-05-21 | (none — input) | `docs/03-data.md` §A1 |
| `external/brazilian_failures.csv` | Hand-curated from WMTF, Wikipedia, WISE Uranium, ANM press releases | (none — input) | `data/external/README.md` |
| `processed/sigbm_canonical.parquet` | Derived from `raw/sigbm/Relatorio_*.csv` | `data/scripts/clean_sigbm.py` | `docs/03-data.md` §A1 |
| `processed/cohort_panel.parquet` | Derived from `sigbm_canonical.parquet` + `external/brazilian_failures.csv` | `data/scripts/build_cohort.py` | `docs/04-methods.md` §3 |

## Where the heavy logic lives

The scripts in `data/scripts/` are intentionally thin (≤ 80 lines each) so
that the data pipeline is visible alongside the data it produces. The
substantive work — parsing the ANM CSV, normalising Portuguese categoricals,
parsing DMS coordinates, building the (dam, month) panel, attaching labels
with right-censoring weights — is in the importable package:

- `src/sentinela/io/sigbm.py`         — SIGBM canonicalisation.
- `src/sentinela/io/wmtf.py`          — failure-events loader.
- `src/sentinela/features/build.py`   — cohort panel builder.

This split keeps the data pipeline reproducible from a single `python …` call
while keeping the implementation testable and reusable from experiments.
