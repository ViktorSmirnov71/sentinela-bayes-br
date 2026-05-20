# Overview

## One-paragraph summary

We build a per-dam probabilistic failure-risk model for Brazilian mine-tailings
storage facilities (TSFs), using the public ANM/SIGBM registry as the unit of
analysis, Sentinel-1 InSAR time series as the primary precursor signal,
INMET-derived rainfall and antecedent moisture as forcing variables, and IBGE
downstream-population data to translate failure probability into
expected-consequence space. The model targets *calibrated 12-month-ahead failure
probability* per dam with conformal coverage guarantees, and is validated
retrospectively against the 2015 Fundão (Mariana) and 2019 B1 (Brumadinho)
failures and prospectively against the SIGBM risk-classification updates.

## Why now

Three things changed in the last six years that make this work newly tractable:

1. **ANM SIGBM (2019–)** became a structured, queryable national registry of
   every tailings dam in Brazil with construction type, height, volume, age,
   and risk classification. Before SIGBM the inventory was fragmented across
   state agencies.
2. **Sentinel-1 (2014–)** ESA Copernicus radar with 6–12-day revisit at C-band
   gives free, full-archive InSAR coverage of every Brazilian mining region.
   Brumadinho-era papers ([Carlà et al. 2019][1]; [Grebby et al. 2021][2])
   showed that the failure was detectable from Sentinel-1 alone ≥5 months in
   advance.
3. **Tabular foundation models** (TabPFN-3, 2025) make calibrated probabilistic
   prediction on small datasets (n ≈ 300–700 dams) genuinely feasible without
   bespoke Bayesian engineering.

The literature has progressed from "InSAR can post-hoc identify precursors at
known failures" toward "InSAR + ML can flag elevated risk at active facilities",
but no published model jointly (a) uses SIGBM as the cohort, (b) propagates
calibrated uncertainty per dam, and (c) is reproducibly open from data to
forecast.

## What we are not doing

- We are not building a numerical slope-stability solver. Established codes
  (PLAXIS, FLAC, GeoStudio) do that; we treat their physics as priors and as
  feature inputs, not as the model.
- We are not claiming we can predict the instant of failure. Brumadinho went
  from accelerating creep to collapse in ~10 seconds. We forecast *probability
  of failure within a horizon*, not timing.
- We are not building an operational early-warning system. That requires
  regulatory mandate, redundancy, and 24/7 ops we cannot provide.

## What this repository should contain when complete

- A reproducible data pipeline from public sources to a per-dam-per-month
  feature table.
- A reproducible training and evaluation pipeline.
- An ablation study isolating the marginal contribution of InSAR, rainfall,
  construction-type, and downstream-exposure features.
- A retrospective study on Fundão (2015) and B1 (2019).
- A short manuscript drafted in `paper/` (added when results justify it).

[1]: https://www.nature.com/articles/s41598-019-50402-x
[2]: https://www.nature.com/articles/s43247-020-00079-2
