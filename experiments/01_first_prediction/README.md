# 01 — First real prediction run on the 911-dam cohort

## Goal

Produce a defensible **current per-dam 12-month-ahead failure probability**
for every active dam in the SIGBM 2026 snapshot, using only static
engineering metadata (no InSAR yet — the HyP3 pipeline is still running for
the Fundão proxy dam_id 8765). The headline artefact is a ranked CSV of the
top-30 highest-risk dams.

## Why a Bayesian-prior model, not LightGBM

The natural first instinct is to train a discriminative model (LightGBM,
logistic regression, TabPFN) on the cohort panel and let it learn risk from
data. We tried that. With only one linked positive event (Fundão / dam_id
8765 in 2015), any flexible model either:

- **Memorises** Fundão's unique feature signature (LightGBM with
  `min_data_in_leaf=20` assigned 8765 a 99.9% probability and all other
  dams ≈ 0% — useless), or
- **Smooths to zero** when sufficiently regularised (LightGBM with
  `min_data_in_leaf=500` assigned every dam ≈ 0%, AUROC dropped to 0.18 —
  also useless).

This is the canonical small-positives problem: discriminative models cannot
extract more signal than the data contains. The honest model class is a
**Beta-Binomial posterior with literature-informed priors**:

$$ \hat{p}_c = \frac{k_c + \alpha\, p_c^{\text{prior}}}{n_c + \alpha} $$

where $c$ is construction method, $p_c^{\text{prior}}$ is the historical
annual failure rate from Rana et al. 2021 + Bowker–Chambers, and $\alpha$
is the prior strength in equivalent dam-months. This is implemented in
`sentinela.models.baselines.BetaBinomialStratifiedRate`.

## Method

- **Cohort.** `data/processed/cohort_panel.parquet` — 911 dams across
  126,288 (dam, month) rows, 2014-01 to 2025-12. 115,764 in-horizon rows;
  12 positives from the Fundão event.
- **Model.** `BetaBinomialStratifiedRate(stratify_col="construction_method",
  alpha=10_000)` with literature priors:

  | construction | prior (annual) | empirical (this cohort) | posterior |
  |---|---|---|---|
  | upstream     | 0.5%   | 12/5,940  ≈ 0.20% | **0.39%** |
  | downstream   | 0.05%  | 0/29,436          | **0.013%** |
  | centerline   | 0.1%   | 0/15,180          | **0.040%** |
  | single_stage | 0.1%   | 0/64,152          | **0.013%** |
  | unknown      | 0.1%   | 0/1,056           | **0.090%** |

  The posterior pulls upstream toward the empirical rate (data outweighs
  the 10k prior dam-months) and the other classes toward the literature
  prior (no observed positives, prior dominates).

## Outputs

- `results/01_first_prediction/metrics.json` — training log-loss, ECE, AUROC.
- `results/01_first_prediction/predictions.parquet` — predicted probability
  for every (dam, month) row in the panel.
- `results/01_first_prediction/top_risk_dams.csv` — top-30 highest-risk
  active dams as of the latest snapshot.

## First-run headline metrics

- Train log-loss: **0.00094**
- Train AUROC:   **0.9744** (model discriminates upstream from non-upstream)
- Train ECE:     **0.00026** (calibration is excellent by construction —
  this is a smoothed empirical rate, not a fitted classifier)

## What the top-30 ranking looks like

All 30 entries are upstream-method dams (45 such dams exist in the cohort).
They are tied at the posterior rate (≈ 0.39%/year) because construction
method is currently the only stratification axis. Once we add InSAR
precursor features (in progress), height / volume, and rainfall, the model
will spread the risk across upstream dams differentially. The current
ranking is therefore a **shortlist of the 45 dams that need further
analysis**, not a final risk ordering within that shortlist.

Notable dams in the top-30 that show up immediately:

- Several Vale-operated dams in MG (Xingu, Pontal, Campo Grande, Forquilha
  I/II/III, Sul Superior).
- **Cava do Germano (8751)** — the surviving companion dam at the Samarco
  Fundão complex.
- **Barragem B1 (8505)**, Mineração Geral do Brasil, Brumadinho — same
  name as Vale's 2019 failure but a different operator at the same
  municipality.
- Several Morro do Ipê facilities (Mina Ipê B1 / B1-Auxiliar / B2).

## What this experiment is NOT

- Not an operational risk assessment. The model uses only construction
  method; many other engineering features matter and aren't yet in the
  surface.
- Not a regulatory or investor-facing ranking. Outputs are research-grade
  with explicit uncertainty caveats (see `docs/06-ethics-and-limitations.md`).
- Not a validation of the literature priors against Brazilian data. The
  empirical-vs-prior comparison in the table above is what we have so
  far; a published validation needs more linked positives (Brumadinho
  proxy via historical SIGBM, the four pre-2015 failures).

## Reproduce

```bash
python experiments/01_first_prediction/run.py
```
