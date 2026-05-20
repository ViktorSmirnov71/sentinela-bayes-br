# 00 — Baselines on static features

## Purpose
End-to-end smoke run of the full pipeline: SIGBM (fixture) ▸ failure-label join
▸ cohort × month panel ▸ static-feature baselines (B0 population rate, B1
construction-stratified rate, B2 ANM CRI as classifier).

This experiment exists **before** RQ1–RQ7 because no result is interpretable
until the pipeline runs end-to-end and we know what the trivial baselines look
like. The numbers it produces are not publishable on their own; they are the
floor every later experiment must beat.

## Inputs
- `data/external/brazilian_failures.csv` (committed)
- Either a real SIGBM table (`data/raw/sigbm/*.csv`) or the synthetic fixture
  generated on the fly via `sentinela.io.fixtures.make_fixture`.

## Outputs
- `results/00_baselines/metrics.csv` — per-model log-loss, ECE, Brier, AUROC.
- `results/00_baselines/predictions.parquet` — per-(dam, month) predictions
  for downstream analysis.

## How to run
```bash
python experiments/00_baselines/run.py            # uses fixture
python experiments/00_baselines/run.py --sigbm-path data/raw/sigbm/<file>.csv
```

## What "good" looks like at this stage
- Pipeline runs without errors.
- B0 reports a log-loss equal to the binary entropy of the empirical failure
  rate (analytic sanity check).
- B1 beats B0 if and only if construction-method carries real signal, which
  it should given the engineering literature (upstream > others).
- B2 (ANM CRI) beats B0 if and only if the regulator's score correlates with
  the failure labels in this cohort. On the fixture with only 2 reference
  failures it may not — that's expected and informative.
