# 03 — Brumadinho B1 retrospective risk-trajectory

## What this experiment produces

A per-month plot of Sentinela's predicted 12-month failure probability at
the **actual Brumadinho B1 dam coordinates** (-20.117, -44.123) for every
month from 2018-01 to 2019-01.

The dam collapsed on 2019-01-25, killing approximately 270 people. The
literature ([Grebby 2021](https://www.nature.com/articles/s43247-020-00079-2))
identifies a clear precursor signal in Sentinel-1 data from this same
period with ≥5 month lead time. If Sentinela's hierarchical model is
operationally useful, its predicted risk should rise sharply through
2018 as the failure date approaches.

This is the cleaner of the two retrospectives because:

- **Denser Sentinel-1 coverage.** S1A and S1B were both operational
  through 2018, giving 66 scenes vs 16 for the Fundão window.
- **62 successful HyP3 pairs** (with our new track-aware pairing the
  failure rate drops to near-zero, but this batch was submitted before
  the fix and lost 122 jobs to cross-track failures).
- **Published precursor signature**: Grebby reported ≥30 mm horizontal
  acceleration in late 2018 at this exact location.

## Method

Identical to experiment 02 but:

- `B1_LAT, B1_LON = -20.117, -44.123`
- Window: 2018-01 to 2019-01
- Static engineering profile (Vale's pre-failure record):
  - construction_method: upstream
  - height_m: 86
  - volume_m3: 12_000_000
  - age_at_month_years: 43
  - cri: 2
  - operator_cnpj: 33592510000154 (Vale S.A.)

## Output

- `results/03_b1_brumadinho_retrospective/trajectory.csv`
- `figures/b1_brumadinho_retrospective.png`

## Reproduce

```bash
python experiments/03_b1_brumadinho_retrospective/run.py
```

Requires HyP3 products at `data/raw/insar/b1-brumadinho/`.

## What success / failure means

- **Success**: the predicted risk trajectory rises monotonically (or
  near-so) through 2018, with peaks in the months Grebby flagged
  (roughly Feb–Aug 2018 first risk milestone, Jun–Dec 2018 imminent).
  Would represent a real retrospective replication of the published
  precursor with our open-pipeline tooling.

- **Failure**: the trajectory oscillates noisily (as it did at Fundão)
  without a clean upward trend. Would confirm that the bottleneck is
  our sampler sophistication, not the underlying signal — push the
  MintPy / PS-InSAR upgrade to the top of the methodology backlog.

Either outcome is publishable. The fact that we get the *same* answer
across two independent retrospective events would be a strong
methodological statement.
