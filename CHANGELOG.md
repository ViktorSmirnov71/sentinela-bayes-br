# Changelog

All notable changes to this project will be documented here. Pre-registration
amendments (changes to `docs/05-research-questions.md` or `docs/04-methods.md`)
must be recorded with a dated entry and a one-line rationale.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
