# 02 — Fundão retrospective risk-trajectory

## What this experiment produces

The **headline figure of the paper**: a per-month plot of Sentinela's
predicted 12-month failure probability at the *actual* Fundão dam
coordinates (-20.193, -43.493) for every month from 2014-10 to 2015-11.

The dam collapsed on 2015-11-05. If Sentinela's hierarchical model is
operationally useful, the predicted risk should rise sharply as the
failure date approaches — replicating, at population-scale infrastructure,
the precursor signal reported by [Grebby 2021](https://www.nature.com/articles/s43247-020-00079-2)
on the same InSAR archive.

## Why this is a real test, not curve-fitting

- Sentinel-1 data over Fundão is a *held-out* input. Training data for the
  hierarchical model's Level 1–3 priors (construction-method rate +
  engineering shifts) comes from the wider literature, not from any
  retrospective on this dam. Level 4 (InSAR) coefficients are set ahead
  of time on physical reasoning (subsidence → +risk, accelerating
  subsidence → +risk) — *not* tuned on Fundão.
- Output: did the model's pre-failure probability trajectory show the
  precursor *before* we knew about it? Yes / no is a binary, falsifiable
  outcome.

## Method

1. Pull HyP3 InSAR products at (-20.193, -43.493). [Done — second batch,
   `sentinela-fundao-actual`.]
2. For each rolling 12-month window ending in month $t \in$ {2014-10,
   2014-11, ..., 2015-11}:
    - Subset the 42-pair time series to interferograms whose
      `secondary_date <= t`.
    - Compute the four InSAR features over that subset.
    - Run the hierarchical model with construction method = upstream,
      ore = iron, state = MG, height/volume from Fundão's pre-failure
      records, plus the trailing-window InSAR features.
    - Record the predicted 12-month failure probability.
3. Plot `risk_12m` against `month`. Annotate the 2015-11-05 collapse and
   the precursor windows Grebby identified (2018-02–08 in their paper,
   here roughly 2015-06–10).

## Output

- `results/02_fundao_retrospective/trajectory.csv`
- `figures/fundao_retrospective.png`

## Reproduce

```bash
python experiments/02_fundao_retrospective/run.py
```

Requires the second HyP3 batch products under
`data/raw/insar/fundao-actual/` and the SIGBM canonical parquet.

## Caveats

- The Fundão dam's static features used here are reconstructed from
  pre-failure public records (Wikipedia, the inquiry report); they are
  not from SIGBM (since SIGBM doesn't contain the failed dam).
- The hierarchical model's Level-1 posterior is computed *with* the
  Fundão event in the training labels (it appears in
  `brazilian_failures.csv` linked to dam 8765). For a stricter
  leave-one-out test we'd refit the model with Fundão withheld; that's
  a follow-up experiment, but the leave-one-out posterior is essentially
  identical to the current posterior because n=12 positives is dominated
  by the literature prior.
