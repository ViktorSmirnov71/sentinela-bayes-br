# Methods

This document specifies the planned methodology. It is the contract that
experiments under `experiments/` must satisfy.

## 1. Cohort definition

The unit of analysis is the (dam, month) pair $(d_i, t)$ for
$d_i \in \mathcal{D}$ and $t \in [2015\text{-}01,\, \text{present}]$. Sentinel-1
coverage begins late 2014; we drop pre-2015 rows to keep the InSAR-feature
column populated.

Dams enter the cohort on the first SIGBM snapshot that records them and exit
on decommissioning, demolition, or failure. Right-censoring is handled
explicitly (see §6).

## 2. Outcome definition

The primary outcome is a binary failure event $F_{i,[t,t+H]}$ with $H = 12$
months, drawn from the WMTF database (Bowker–Chambers severity ≥ 4) augmented
with the manual incident corpus (see `docs/03-data.md` §E2). A *secondary*
outcome considers severity ≥ 3 (sensitivity analysis).

Near-misses — emergency-level escalations and ANM-issued risk increases — are
modelled as a separate auxiliary task for multitask training (see §5).

## 3. Features

### 3.1 Static features $x^{\text{static}}$

From SIGBM:

- construction method (categorical: upstream, downstream, centerline, dyke,
  unknown)
- ore type (one-hot)
- height (m)
- declared volume (m³)
- age since first impoundment (years)
- ANM CRI and DPA (ordinal, used as features not labels)
- operator identity (categorical, with a frequency-based encoding)
- slope angle and length of downstream embankment (from DEM)

### 3.2 InSAR features $x^{\text{insar}}_{i,t}$

Per dam, for both ascending and descending Sentinel-1 tracks, compute on the
trailing 12-month window:

- mean and median line-of-sight (LOS) velocity (mm/yr)
- maximum 90-day acceleration (mm/yr²)
- spectral slope of LOS displacement time series (Carlà-style precursor)
- variance ratio of displacement on the dam crest vs. on stable surrounding
  ground (a Grebby-style anomaly indicator)
- persistent-scatterer density on the dam
- decorrelation index (coherence quantile)

We will use the HyP3 short-baseline InSAR products via the ASF API as the
operational backbone, and use MintPy + ISCE2 for the retrospective Fundão /
B1 analyses where time-series quality is critical.

### 3.3 Climate features $x^{\text{climate}}_{i,t}$

From CHIRPS interpolated to the dam centroid, with INMET station correction:

- 30 / 90 / 365-day cumulative rainfall
- SPI-3, SPI-6
- API (antecedent precipitation index) with $k = 0.85$
- count of daily-rainfall extreme events (> 99th-percentile of local
  climatology) in trailing 90 days

From ERA5-Land:

- soil-moisture in surface layer at month $t$
- evapotranspiration anomaly

### 3.4 Operational features $x^{\text{ops}}_{i,t}$

From SIGBM disclosures:

- emergency-level status changes
- declared inactivity / decommissioning state
- months since last licensed inspection (where available)

## 4. Baselines

Two principled baselines are required before any deep model is considered
publishable.

- **B0. Population base rate.** Constant probability equal to the annual
  failure rate from WMTF, applied uniformly. Establishes the irreducible
  baseline log-loss.
- **B1. Construction-type stratified rate.** Separate base rate per
  construction method. Captures the Rana et al. 2021 effect alone.
- **B2. ANM CRI as classifier.** Treat the administrative risk score as a
  fixed predictor. Establishes whether *any* learned model beats the
  regulator's own ranking.
- **B3. Gradient-boosted trees on static + climate features only.**
  XGBoost / LightGBM with the static and climate features. Isolates the
  marginal value of InSAR features when added in the main model.

## 5. Primary model

Given the small cohort size ($N \approx 700$) and the value of calibrated
probabilities, the primary model is a **TabPFN-3 classifier** over the joint
feature vector, with:

- **Survival-aware loss.** Adapted log-loss that masks contribution from
  right-censored rows (Cox-style partial-likelihood is not a clean fit; we
  instead use a discrete-time hazard reformulation with month-level
  intervals).
- **Stratification.** Per-construction-method head; a shared trunk over
  generic features and a head-specific output for upstream / downstream /
  centerline.
- **Calibration.** Train-time temperature scaling against a held-out
  calibration fold; split-conformal on top for prediction-set guarantees
  under exchangeability.

We compare against an explicit Bayesian survival model (Weibull AFT with
hierarchical operator effects, fit in PyMC) as a calibrated reference and
sanity check.

## 6. Validation protocol

### 6.1 Splits

- **Retrospective held-out positives.** Fundão (2015-11) and B1 (2019-01) are
  withheld from training entirely. The model's pre-failure probability
  trajectories at these dams are the headline qualitative result.
- **Time-forward CV.** Rolling-origin splits: train on $t \le T - 24$ months,
  test on $T$, slide quarterly. Reports out-of-time AUROC, log-loss, and
  Brier.
- **Operator-out CV.** Hold out one operator at a time, test on their dams.
  Tests generalisation beyond operator-specific signatures.

### 6.2 Metrics

- AUROC on the failure event (with confidence intervals via clustered bootstrap
  over operators).
- Brier score and reliability/resolution decomposition (Murphy).
- Expected Calibration Error and adaptive ECE.
- Decision-curve analysis: expected net benefit at threshold $\tau$,
  parameterised by exposure population.
- Empirical conformal coverage at $\alpha \in \{0.1, 0.05, 0.01\}$.

### 6.3 What counts as success

The pre-specified primary success criterion is:

> The model assigns Fundão (Nov 2015) and B1 (Jan 2019) a 12-month-prior
> failure probability in the top decile of all then-active dams, with
> calibrated ECE ≤ 0.05 on the time-forward CV.

This is set before any modelling is attempted. Failure to meet it is reported.

## 7. Ablations

- Remove InSAR features → measures their marginal contribution.
- Remove climate features → same for rainfall / moisture.
- Replace TabPFN with B3 (GBM) → isolates foundation-model contribution.
- Replace conformal with naive softmax → isolates uncertainty machinery.
- Replace WMTF labels with ANM CRI as target → reproduces de Lima et al. 2022
  setup for direct comparison.

## 8. Reproducibility

Each experiment is a directory under `experiments/` containing:

- `config.yaml` — fully specified hyperparameters
- `run.py` — entry point
- `README.md` — hypothesis, command to reproduce, expected runtime
- outputs written to `results/<experiment-id>/`

Random seeds are pinned. Data manifest hashes are checked at the start of
each run.

## 9. Out of scope (deferred)

- Multi-physics coupling with finite-element slope-stability codes.
- Estimating runout extent from failure-volume releases (separate problem).
- Cross-country transfer beyond Brazil (mentioned in §10 but deferred).
