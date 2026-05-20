# Problem statement

## Domain

A *tailings storage facility* (TSF) is an engineered impoundment that retains
the slurry by-products of mineral extraction. There are roughly 700 TSFs
registered in Brazil's SIGBM and ~1,800 in the Global Tailings Portal worldwide.
Catastrophic failure releases the impounded volume as a flowing slurry; the
resulting human, environmental, and economic costs are large and concentrated
in time. The two reference events for this work are:

| Event | Date | Tailings released | Fatalities | Source |
|---|---|---|---|---|
| Fundão / Samarco (Mariana, MG) | 2015-11-05 | 43.7 Mm³ | 19 + ecological catastrophe along Doce river | [Wikipedia][1] |
| B1 / Córrego do Feijão (Brumadinho, MG) | 2019-01-25 | ~9.7 Mm³ | ~270 | [WISE Uranium][2] |

Independent geotechnical reviews of B1 (Robertson et al. 2019) identified
static liquefaction in the upstream-method-constructed dam as the proximate
mechanism. Independent satellite re-analyses (Grebby et al. 2021; Carlà et al.
2019) identified detectable surface-deformation precursors months in advance
that the operational monitoring missed or did not act on.

## Formal task

Let $\mathcal{D} = \{d_1, \dots, d_N\}$ be the set of active Brazilian TSFs
registered in SIGBM. For each dam $d_i$ at month $t$ we observe a feature
vector

$$ x_{i,t} = \big( x_{i}^{\text{static}},\ x_{i,t}^{\text{insar}},\ x_{i,t}^{\text{climate}},\ x_{i,t}^{\text{ops}} \big) $$

where:

- $x^{\text{static}}$ — construction method (upstream / downstream / centerline),
  height, volume, age, ore type, operator, ANM Damage-Potential Category (DPA),
  ANM Risk Category (CRI).
- $x^{\text{insar}}$ — Sentinel-1 InSAR-derived time-series features on the dam
  crest and downstream slope: velocity, acceleration, persistent-scatterer
  density, spectral slope of displacement, decorrelation indicators.
- $x^{\text{climate}}$ — INMET / CHIRPS-derived rainfall: cumulative 30/90/365-day
  totals, SPI-3 / SPI-6, antecedent moisture, extreme-event counts.
- $x^{\text{ops}}$ — operational status (active / inactive / under decommission)
  and structured incident events from SIGBM disclosures.

We model

$$ P\!\left(F_{i, [t,\, t+H]} = 1 \mid x_{i, \le t}\right) $$

where $F_{i, [t, t+H]}$ is the binary event "dam $d_i$ experiences a
documented failure or near-miss (Bowker–Chambers severity ≥ category 4) within
horizon $H$ from time $t$". Primary target horizon: $H = 12$ months. The model
must produce a calibrated probability and a conformal prediction set at
specified miscoverage $\alpha$.

## Why this is hard

- **Class imbalance.** Failures are rare ($\sim 10$ documented catastrophic
  failures in Brazil since 1985 against $\sim 700$ active dams). The positive
  class is small and consequentially asymmetric.
- **Censoring.** Most observed dams have *not yet failed*; the "no failure"
  label is right-censored, not negative.
- **Survivor selection.** Dams that should already have failed but did not
  bias the apparent precursor distribution.
- **Label noise.** Failure databases (SIGBM, GTP, WMTF) disagree on inclusion
  criteria and severity scoring.
- **Heterogeneity.** Construction methods differ in failure physics (upstream
  TSFs liquefy; downstream TSFs overtop). One model class for all dams is
  almost certainly wrong; multitask or stratified models are required.
- **Right-censored InSAR coverage.** Sentinel-1 begins in 2014–2015; failures
  before then have no equivalent precursor data.

The hardness is the contribution opportunity. Each item above corresponds to
a methodological choice with a literature, and a reproducible study that
makes those choices explicitly is publishable in its own right.

[1]: https://en.wikipedia.org/wiki/Mariana_dam_disaster
[2]: https://www.wise-uranium.org/mdafbr.html
