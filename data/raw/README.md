# data/raw/

Source inputs exactly as obtained, untouched. Files here are the project's
"ground truth" upstream of any cleaning; if a row looks wrong it should look
wrong here too. Treat anything in this folder as immutable input.

## What's committed

| File | Size | Date obtained | Source |
|---|---|---|---|
| `sigbm/Relatorio_20260721.csv` | 254 KB | 2026-05-21 | https://app.anm.gov.br/sigbm/publico → *Data Extraction* (manual export by V. Smirnov) |

## What's local-only (gitignored)

By default everything under `data/raw/` except the files explicitly re-allowed
in the top-level `.gitignore`. As new datasets are pulled (CHIRPS, Sentinel-1
InSAR, IBGE population grids, etc.) they go here and remain local unless
explicitly committed for reproducibility.

## How to obtain `Relatorio_*.csv`

1. Open https://app.anm.gov.br/sigbm/publico in a browser.
2. Click **Data Extraction** in the public-module menu.
3. Leave filters blank to extract the full national registry.
4. Download the resulting `Relatorio_YYYYMMDD.csv`.
5. Save it under `data/raw/sigbm/`.

The CSV is semicolon-delimited, UTF-8 with BOM, with Brazilian decimal format
and DMS coordinates. `sentinela.io.sigbm.load` (and via it
`data/scripts/clean_sigbm.py`) handles all of that.
