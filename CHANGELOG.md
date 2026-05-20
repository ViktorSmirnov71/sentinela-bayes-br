# Changelog

All notable changes to this project will be documented here. Pre-registration
amendments (changes to `docs/05-research-questions.md` or `docs/04-methods.md`)
must be recorded with a dated entry and a one-line rationale.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
