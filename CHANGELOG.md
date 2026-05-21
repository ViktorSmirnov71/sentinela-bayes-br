# Changelog

All notable changes to this project will be documented here. Pre-registration
amendments (changes to `docs/05-research-questions.md` or `docs/04-methods.md`)
must be recorded with a dated entry and a one-line rationale.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added (2026-05-21, eighth push — 3D terrain mesh)
- `data/scripts/build_terrain.py`: fetches AWS Open Data terrarium-format
  tiles, decodes RGB to elevation, clips to Brazil bbox, downsamples to
  320 x 280, writes `viz/data/terrain.json` (~386 KB).
- `data/scripts/export_viz_data.py` now bilinear-samples the DEM at each
  dam's lat/lon and writes `terrain_elevation_m` into `dams.json`. Barragem
  de Germano correctly resolves at ~803 m elevation in Mariana, MG.
- `viz/js/main.js` rewritten: flat plane replaced by a 3D PlaneGeometry
  mesh with elevation-displaced vertices, faceted low-poly material with
  per-vertex elevation-tinted colour, semi-transparent wireframe overlay,
  Brazil coastline traced along the terrain surface, and dam spikes
  positioned at their actual terrain elevation. Vertical exaggeration
  ~70x for country-scale legibility. Cone-shaped spikes replace cylinder
  pillars to emphasise the eruption-from-ground visual.

### Added (2026-05-21, seventh push — research release)
- `src/sentinela/models/hierarchical.py`: three-level hierarchical Bayesian
  failure-risk model. Level 1 = Beta-Binomial construction-method posterior.
  Level 2 = James-Stein-shrunk per-operator logit shift (capped at +/- 1
  logit). Level 3 = bounded logit shifts for height, volume, age, CRI.
  Output: per-dam probability with all shrinkage explicit and auditable.
- `tests/test_hierarchical.py` — 4 tests: end-to-end, height monotonicity,
  CRI monotonicity, operator-shift cap. 30/30 tests pass overall.
- `experiments/01_first_prediction/` rewired to use the hierarchical model.
  Top-10 ranking now spreads risk within the upstream-method shortlist;
  the Vale Forquilha I/II/III cluster (ANM Emergency Level 2 in 2022)
  surfaces in the top-10 from engineering features alone.
- `data/scripts/export_viz_data.py`: writes `viz/data/dams.json` and
  `viz/data/summary.json` from the model outputs and SIGBM canonical join.
- `viz/`: Three.js 3D visualisation of the 877 geocoded dams over a
  simplified Brazil silhouette. Pillar height = predicted 12-month risk;
  colour ramp cyan -> violet -> magenta; top-30 pulse; emergency-level
  dams carry a yellow ground halo. Self-contained: HTML + JS only, served
  by any static-file server.
- `paper/manuscript.md`: full IMRaD draft of the Sentinela research paper.
  Covers motivation, related work, data audit, methodology, results,
  limitations, ethics, future work. Builds to PDF via pandoc.
- `paper/README.md` documents the build command.

### Added (2026-05-21, sixth push — first real prediction model)
- `sentinela.models.baselines.BetaBinomialStratifiedRate`: Beta-Binomial
  smoothed per-class failure rate with literature-derived priors (Rana 2021,
  Bowker-Chambers). Designed for the n=1-linked-positive regime where
  discriminative models either memorise or smooth to zero.
- `experiments/01_first_prediction/`: first real prediction run on the
  911-dam cohort. Produces:
    - `results/01_first_prediction/top_risk_dams.csv` (top-30 ranked).
    - `results/01_first_prediction/predictions.parquet` (per-row probs).
    - `results/01_first_prediction/metrics.json` (training metrics).
- Posterior failure rates per construction method (this snapshot):
    upstream 0.39%, unknown 0.09%, centerline 0.04%, single_stage 0.013%,
    downstream 0.013%. Empirical data dominates on upstream; literature
    prior dominates on the other classes.
- 5 new tests for the Beta-Binomial model (prior/data blending, edge cases,
  unknown-class fallback). 26/26 tests pass.

### Changed (2026-05-21, fifth push)
- `sentinela.io.sentinel1.pick_best_orbit` added. Searches both ASCENDING and
  DESCENDING for a given bbox and time window, returns whichever has more
  Sentinel-1 SLC coverage. Needed because the early-mission (2014-2016)
  coverage over Brazil is uneven — Minas Gerais is DESCENDING-only for the
  Fundão 2014-10 to 2015-11 precursor window, which the previous
  ASCENDING default would have silently submitted as a zero-scene job.
- `data/scripts/build_insar_features.py pull` default for `--orbit` is now
  `auto`. The explicit `ASCENDING` / `DESCENDING` overrides remain available.

### Added (2026-05-21, fourth push — InSAR pipeline)
- Real implementations of the Sentinel-1 InSAR precursor feature extractors
  in `src/sentinela/insar/features.py`:
  - `los_velocity` — Theil-Sen robust slope (mm/yr).
  - `acceleration_90d` — quadratic-fit second derivative over the trailing
    12 months (Carla 2019 inverse-velocity precursor, mm/yr²).
  - `spectral_slope` — log-log slope of the Welch PSD.
  - `crest_vs_stable_variance_ratio` — Grebby 2021 anomaly indicator.
  - `compute_features` aggregator returning the full `InsarFeatures` bundle.
- `src/sentinela/insar/synthetic.py` — generator for Brumadinho-like LOS time
  series (stable -> creep -> quadratic acceleration with calibrated noise),
  used as the ground-truth fixture for unit tests.
- `tests/test_insar_features.py` — eight tests verifying the extractors
  recover the synthetic signal directionally and quantitatively.
- `src/sentinela/io/sentinel1.py` rewritten as a real orchestration layer
  over `asf_search` + `hyp3_sdk` (both lazy-imported):
  - `bbox_for_dam`, `search_scenes`, `short_baseline_pairs`,
    `submit_insar_pairs`, `download_completed`, plus credential-check helper.
- `src/sentinela/insar/timeseries.py` — per-dam LOS-displacement time-series
  builder. Samples HyP3 unwrapped-phase GeoTIFFs at the dam centroid with a
  configurable buffer, plus a stable reference point ~3 km away for the
  variance-ratio computation.
- `data/scripts/build_insar_features.py` — two-mode runnable script:
  - `pull` submits HyP3 InSAR jobs for the configured dam IDs (queues async).
  - `features` extracts per-dam features from local HyP3 products and writes
    `data/processed/insar_features.parquet`.
- `data/raw/insar/README.md` — credential setup guide (NASA Earthdata Login)
  and the end-to-end workflow from credential export to processed features.
- `docs/04-methods.md` §3.2 expanded with the precise feature definitions and
  citations to Grebby 2021 and Carla 2019.

### Added (2026-05-21, third push)
- `data/` reorganised into a self-contained, reproducible data layer:
  - `data/README.md` is the new navigation key with a tree diagram, pipeline
    flow chart, and provenance table for every file.
  - `data/scripts/clean_sigbm.py` and `data/scripts/build_cohort.py` are
    runnable entry points around the package; both deterministic.
  - `data/processed/sigbm_canonical.parquet` (67 KB) and
    `data/processed/cohort_panel.parquet` (51 KB) committed as the model-
    ready artefacts. Reproducible byte-for-byte from a clean clone via the
    two scripts.
  - `data/raw/sigbm/Relatorio_20260721.csv` (254 KB) committed as the
    published baseline snapshot.
  - Per-folder READMEs under `data/raw/`, `data/processed/`, and
    `data/scripts/` documenting roles, schema, and regeneration commands.
- `.gitignore` rewritten with file-level globs so specific data artefacts can
  be exempted from the local-only default. Documented inline.

### Added (2026-05-21)
- Real SIGBM data ingest path verified end-to-end. `Relatorio_20260721.csv`
  (911 dams, manual export from `app.anm.gov.br/sigbm/publico`) loads cleanly.
- `src/sentinela/io/sigbm.py` rewritten to handle the actual ANM CSV format:
  semicolon-delimited UTF-8-with-BOM, Brazilian decimals, DMS coordinates,
  Portuguese categoricals. Adds `ops_status` and `pnsb_included` to the
  canonical schema; expands `CONSTRUCTION_METHODS` with `single_stage` (the
  largest real category at 53% of dams).
- `data/external/brazilian_failures.csv` updated: Fundão linked to
  `real_sigbm_dam_id = 8765` (Barragem de Germano, the surviving Samarco
  structure at the same complex). Other historical failures documented as
  unlinkable in the current registry.
- `docs/03-data.md` updated with real-snapshot composition statistics and a
  methodology note on registry amnesia (failed dams are removed from SIGBM
  post-failure, which biases the cohort).
- Tests cover real-format parsing (DMS, Brazilian decimals, method/ops/
  emergency normalisation) and an end-to-end smoke test against the
  committed CSV.
- First baseline run on real data: B1 (construction-stratified) AUROC 0.974
  vs B2 (ANM CRI) 0.712 against the linked Fundão positive — replicates the
  literature finding that construction method dominates regulator-issued
  risk scores. n=1 positive remains the headline caveat.

### Added (2026-05-20, second push)
- `data/external/brazilian_failures.csv` (committed): citation-anchored table
  of eight Brazilian mining-related dam-failure events (1986-2022), used as
  primary positive-class labels until the full WMTF spreadsheet is wired.
- `src/sentinela/io/fixtures.py`: representative synthetic SIGBM table
  generator with real-marginal weights (state, ore, construction method) and
  two reference-failure stand-in rows (`FIX-REF-FUNDAO`, `FIX-REF-B1`).
- `src/sentinela/io/sigbm.py`: real loader with canonicalisation, validation,
  and Base-dos-Dados / manual-export access paths documented.
- `src/sentinela/io/wmtf.py`: loader for the curated Brazilian failures CSV
  (full WMTF spreadsheet support stubbed for later).
- `src/sentinela/features/build.py`: cohort × month panel builder with
  horizon-windowed binary labels and right-censoring weights.
- `src/sentinela/utils/seed.py`: deterministic-seeding helper.
- `experiments/00_baselines/`: end-to-end pipeline smoke run producing real
  metrics from fixture or real SIGBM data. First successful run reports
  B1 (construction-stratified) AUROC ≈ 0.88 against the fixture cohort.
- Tests covering schema canonicalisation, fixture reference dams, label
  attachment, and censoring weights.

### Changed (2026-05-20)
- Project renamed from `tailings-risk` to `sentinela-bayes-br`; full title
  "Sentinela: Bayesian Failure Forecasting for Brazilian Tailings Dams". Python
  package renamed `tailings_risk` → `sentinela`; CLI entry point `sentinela`.
  Repository moved to `github.com/ViktorSmirnov71/sentinela-bayes-br`.
- README rewritten with an Introduction + Context section explaining the
  problem in plain terms before bridging to the methodology.

### Added
- Initial scientific scaffolding: 7 documents under `docs/` (overview, problem
  statement, related work, data audit, methods, research questions, ethics),
  BibTeX bibliography, typed Python package skeleton with real implementations
  for calibration metrics and B0–B3 baselines, configs, tests, CI workflow.
- Pre-registered research questions RQ1–RQ7.
