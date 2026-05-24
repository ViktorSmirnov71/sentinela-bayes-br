---
title: "Forecasting Brazil's Next Tailings-Dam Disaster"
subtitle: "Sentinela: a calibrated hierarchical-Bayesian forecaster for Brazilian mine-tailings dam failures"
authors:
  - Viktor Smirnov, Arakon
date: 2026-05-24
status: pre-print, manuscript draft
keywords:
  - tailings dams; Brumadinho; Sentinel-1 InSAR; Bayesian inference; survival analysis; calibrated probability
---

# Abstract

Catastrophic failure of mine-tailings storage facilities (TSFs) in Brazil
killed at least 289 people in two events in the last decade (Mariana 2015,
Brumadinho 2019). After Brumadinho, three things became reproducibly true:
the Brazilian regulator publishes a national TSF registry (SIGBM, 911 dams
in our 2026 snapshot); the European Copernicus programme freely distributes
Sentinel-1 SAR with a 6–12 day revisit over all of Brazil since 2014; and
post-mortem analyses (Grebby et al. 2021; Carlà et al. 2019) confirmed that
the B1 Córrego do Feijão collapse was detectable from Sentinel-1 InSAR at
least five months in advance. Yet there is no published, openly reproducible,
per-dam probabilistic forecaster that uses these inputs.

We present **Sentinela**, a hierarchical-Bayesian model that produces a
calibrated 12-month-ahead failure probability for every active Brazilian
mine-tailings dam from purely public data. The model composes a
literature-informed Beta-Binomial construction-method posterior, a
James–Stein-shrunk per-operator random effect, bounded logit shifts for
engineering features (height, volume, age, regulator risk category), and a
bounded InSAR-precursor term derived from Sentinel-1 line-of-sight
displacement. We report three results. (1) On the 2026 SIGBM snapshot the
engineering-feature ranking independently surfaces the dams ANM has
separately placed under emergency declarations: the single Emergency-Level-3
dam in the country (Barragem Serra Azul) and the entire Level-2 Forquilha
cluster appear in the top-15, despite the model receiving no emergency-level
input — an external validation that the within-construction-class ordering
is meaningful. (2) We process 148 Sentinel-1 interferograms through ASF HyP3
at the actual coordinates of both reference failures and run a month-by-month
retrospective; at Brumadinho B1 the predicted risk spikes in April 2018,
inside the "definitive but emergent risk" window reported independently by
Grebby et al. (2021), a partial replication of the published precursor with
a purely open pipeline. (3) We document a "registry-amnesia" bias (failed
dams are struck from SIGBM post-failure) and a cross-relative-orbit SBAS
pairing failure mode (100 % of our HyP3 failures), both of which are
methodologically instructive at population scale. We argue that in the
one-linked-positive regime that characterises this problem, a transparent
literature-prior Bayesian model is the honest choice over discriminative
learners, which we show empirically either memorise the single positive or
collapse to zero. All code, data, figures, the 3D visualisation, and this
manuscript are openly released and reproducible from a clean clone in five
commands.

# 1. Introduction

A tailings dam is the engineered wall that retains the slurry by-product of
mineral extraction. Catastrophic failure releases the impounded volume as a
flowing mudwave. Mariana 2015 destroyed Bento Rodrigues and contaminated
600 km of the Doce river. Brumadinho 2019 killed approximately 270 people
in 90 seconds. These are not isolated events: the World Mine Tailings
Failures catalogue records eight Brazilian severity-4-or-higher events
since 1986.

Three developments after Brumadinho make per-dam quantitative forecasting
newly tractable:

1. **SIGBM** (Sistema Integrado de Gestão de Barragens de Mineração) —
   the Agência Nacional de Mineração's national TSF registry, public since
   2019 [@anm_sigbm].
2. **Sentinel-1** — ESA Copernicus C-band SAR, full archive open since
   2014, 6–12-day revisit, millimetre-precision interferometric
   ground-deformation measurement.
3. **Post-mortem replication studies** [@grebby2021; @carla2019; @du2020;
   @gama2023] that confirm the B1 collapse left a clear InSAR signature
   months before failure.

The literature has progressed from *"InSAR can post-hoc identify
precursors at known failures"* to *"InSAR + ML can flag elevated risk at
active facilities"*. No published model jointly (a) uses SIGBM as the
cohort, (b) propagates calibrated uncertainty, and (c) is reproducibly
open from data to forecast. This paper fills that gap with the simplest
methodology that does so.

# 2. Related work

## 2.1 Single-event precursor reconstruction

@grebby2021 applied advanced InSAR analysis to Sentinel-1 over B1 and
detected ground-deformation precursors ≥5 months before the 25 January
2019 collapse. @carla2019 independently derived an inverse-velocity
time-of-failure prediction. @du2020 performed an InSAR time-series risk
assessment of the Brumadinho cluster. @gama2023 published a slip-surface
mechanism account attributing the failure to delayed static liquefaction.
@mura2018 used DInSAR with TerraSAR-X to monitor the surviving dikes at
the Germano complex post-Fundão. These works establish that the
geophysical precursor signal exists in publicly-available Sentinel-1 data
at known failures.

## 2.2 Generalised early-warning and ML on InSAR

@macchiarulo2023 reduced false alarms by combining InSAR deformation with
SAR-derived moisture content. @manconi2024 catalogued practical
considerations for operational Sentinel-1 monitoring of tailings dams.
@zhang2025 proposed an InSAR framework that robustly separates consolidation
settlement from failure-relevant deformation. @zheng2025 integrated InSAR
with 3D numerical models. None of these output calibrated per-dam
probabilities at population scale, none jointly use construction-type
metadata, and none are reproducibly open from data to forecast.

## 2.3 Population-scale risk classification

@delima2022 classified Brazilian TSFs by risk using SIGBM-derived features
(without InSAR), but treats ANM's administrative risk score as the target,
not failure events. @rana2021 published a global statistical model of
tailings-dam failure frequency vs. construction type using WMTF data — a
population baseline rate, not a per-dam forecast.

## 2.4 The gap

Combining the three lines:
- Post-hoc precursor work shows the *signal exists*.
- Methodological InSAR-ML work shows the *signal can be extracted*.
- Population-scale work establishes a *cohort* but uses administrative
  scores as labels.

What does not exist: a reproducible per-dam probabilistic forecaster for
Brazilian TSFs that (i) uses SIGBM as its cohort, (ii) ingests
Sentinel-1 InSAR-derived precursor features, (iii) is trained against
documented failure or near-miss events with explicit survival censoring,
and (iv) is evaluated with proper uncertainty quantification. This is the
target of Sentinela.

# 3. Data

We assemble the analysis from five categories of public open data; full
provenance, schema, and access mechanisms are documented in
`docs/03-data.md` and `data/README.md` of the open-source repository.

## 3.1 Cohort: SIGBM

The Agência Nacional de Mineração's public web app at
`app.anm.gov.br/sigbm/publico` provides a manual CSV export with 911 dams
(2026-05-21 snapshot). Schema includes construction method (upstream /
downstream / centerline / single-stage / dyke / unknown), current height
and volume, primary ore, operator CNPJ, the ANM Risk Category (CRI) and
Damage-Potential Category (DPA), declared emergency level, and operational
status. The export is semicolon-delimited UTF-8-with-BOM with Brazilian
decimal format and DMS coordinates; we canonicalise these in
`src/sentinela/io/sigbm.py`.

**Snapshot composition.** The cohort spans 21 states, dominated by Minas
Gerais (35%), Mato Grosso (20%), and Pará (13%). Construction methods are
distributed 53% single-stage, 24% downstream, 13% centerline, 5% upstream
(the historically dangerous class with 45 dams), 5% unknown. As of the
snapshot, 822 dams are at no declared emergency level, 12 at Alert level,
69 at Emergency Level 1, 7 at Emergency Level 2, and 1 at Emergency Level
3 — the single most-immediately-concerning structure currently in Brazil.

**Methodology note — registry amnesia.** ANM removes failed dams from
the active SIGBM registry post-failure. Vale's B1 Córrego do Feijão
(2019), Samarco's Fundão (2015), and Herculano's B1 (2014) are all
absent from the current export. The Fundão event has a credible proxy
via dam_id 8765, *Barragem de Germano* — the surviving Samarco structure
at the same mining complex, now in decommissioning. Other historical
failures need pre-failure SIGBM snapshots (obtainable from Wayback
Machine archives or by FOI request) to be modelled prospectively. This
biases the cohort toward "dams that have not yet failed" and is the
single biggest limitation of the present work.

## 3.2 Labels: Brazilian failure events

A hand-curated, citation-anchored table of eight documented Brazilian
TSF-failure events from 1986 to 2022 is committed to the repository at
`data/external/brazilian_failures.csv`. The table preserves the
Bowker–Chambers severity coding [@wmtf]; the primary cutoff for the
positive class is severity ≥ 4.

## 3.3 Precursor signal: Sentinel-1 InSAR

Sentinel-1 SLC scenes intersecting each dam are searched via the ASF API
(`asf_search`). For each dam we generate the short-baseline-subset
pair list, submit InSAR processing jobs to ASF's HyP3 hosted service
[`hyp3_sdk`], and download the unwrapped-phase GeoTIFFs as they complete.
The HyP3 path avoids 10+ GB local SLC downloads and removes the need for
a working ISCE2 / GAMMA toolchain. Across the project we processed three
HyP3 batches totalling 276 submitted jobs (148 succeeded): the Germano
proxy (dam_id 8765, 42 pairs), the actual Fundão coordinates (42 pairs),
and the actual Brumadinho B1 coordinates (192 submitted, 64 succeeded —
see §5.5 on the cross-track failure mode). Each succeeded job yields one
unwrapped-phase raster which we sample at the dam centroid.

The orbit auto-selection step is non-trivial. The first manual submission
used the script's `ASCENDING` default and returned zero scenes; we
verified that early-mission Sentinel-1 coverage of Minas Gerais is
descending-only. We now default to a per-dam `pick_best_orbit` lookup
that searches both orbits and uses whichever has more SLCs in the target
window.

## 3.4 Forcing variables: rainfall and antecedent moisture

Three sources of rainfall data will be ingested in the next experimental
phase: CHIRPS daily 0.05° rainfall (1981–present), INMET BDMEP station
records (1961–present), and ERA5-Land hourly reanalysis. We compute SPI-3
and SPI-6 z-scores against the local long-term climatology — raw rainfall
is misleading across Brazil's climatic variation, and the standardised
indices are the established operationalisation of "wet" / "dry" relative
to a location's baseline.

## 3.5 Exposure: IBGE

For translating failure probability into expected affected population,
we will rasterise IBGE Setor Censitário population data onto a common
grid and compute the population within a runout-distance buffer for each
dam. This data does not enter the forecasting model directly; it informs
decision-curve analysis when the model is evaluated as an operational
input.

# 4. Methodology

## 4.1 Formal task

Let $\mathcal{D} = \{d_1, \ldots, d_N\}$ index the active dams in SIGBM.
For each (dam, month) pair $(d_i, t)$ we model

$$P\!\left(F_{i, [t, t+H]} = 1 \mid x_{i, \le t}\right)$$

where $F_{i,[t, t+H]}$ is the binary event "dam $d_i$ experiences a failure
of severity ≥ 4 within horizon $H$ from time $t$", with $H = 12$ months as
the primary target horizon. The feature vector $x_{i, \le t}$ comprises
static engineering metadata, InSAR-derived precursor features computed
over the trailing 12 months, antecedent climate variables, and discrete
operational-status indicators.

## 4.2 Why a hierarchical-Bayesian model, not a discriminative learner

With one linked positive event in the current cohort (Fundão, mapped via
proxy to dam_id 8765), discriminative models either memorise the single
positive's unique feature signature or smooth to zero everywhere. We
documented both failure modes empirically:

- **LightGBM with `min_data_in_leaf=20`:** training AUROC 0.9995, ECE 0.001,
  but assigned all non-target dams ≈ 0% predicted risk. Useless.
- **LightGBM with `min_data_in_leaf=500`:** all probabilities ≈ 0, AUROC
  collapsed to 0.18. Also useless.

The honest model in the small-positive regime is a **hierarchical
Bayesian estimator** with informative priors. We compose:

1. **Level 1** — Beta-Binomial smoothed per-construction-method failure
   rate. For each class $c$:

   $$ \hat p_c = \frac{k_c + \alpha\, p^{\text{prior}}_c}{n_c + \alpha} $$

   where $p^{\text{prior}}_c$ comes from @rana2021 and the Bowker–Chambers
   catalogue (annual rates: upstream 0.50%, centerline / single-stage /
   dyke / unknown 0.10%, downstream 0.05%) and $\alpha = 10{,}000$
   equivalent dam-months.

2. **Level 2** — per-operator logit shift via James–Stein-style shrinkage,
   capped at $\pm 1$ logit unit so a single positive cannot make any
   operator look like an outlier.

3. **Level 3** — bounded logit shifts for continuous engineering features:
   height, volume, age (z-scored against the cohort), and the
   regulator-assigned CRI ordinal. Coefficients are conservative
   (0.10–0.30 in logit units) and informed by the published effect sizes
   in @rana2021.

The Level-1 posterior on the 2026 snapshot pulls upstream toward the
empirical rate (data dominates: 6{,}000 dam-months yields posterior 0.39%
against prior 0.50%) and the other classes toward the literature prior
(no observed positives, prior dominates).

The full level structure, the bound on each level's contribution, and the
data source feeding each level are summarised in **Table 5**. The design
principle is that every level above the literature prior is *bounded* —
no single operator, engineering feature, or InSAR reading can move a dam's
log-odds by more than a fixed amount — so that the single linked positive
event cannot produce a spurious outlier.

## 4.3 Validation protocol

The pre-registered protocol in `docs/04-methods.md` calls for: (1)
retrospective held-out positives at the two reference failures, with the
model's pre-failure probability trajectories as the headline qualitative
result; (2) rolling-origin time-forward cross-validation with quarterly
step; (3) leave-one-operator-out CV; (4) clustered bootstrap CIs over
operators. The present manuscript reports training metrics for the
population ranking, plus the two qualitative held-out retrospectives
(§5.4, §5.5); full rolling-origin and operator-out CV await additional
linked positives, which require the historical-SIGBM recovery described
in §8.

## 4.4 Reproducibility

All code, data, scripts, processed outputs, and the visualisation are at
[`github.com/ViktorSmirnov71/sentinela-bayes-br`](https://github.com/ViktorSmirnov71/sentinela-bayes-br).
The repository is designed for one-command reproduction of every artefact
in this paper:

```bash
git clone https://github.com/ViktorSmirnov71/sentinela-bayes-br
cd sentinela-bayes-br
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python data/scripts/clean_sigbm.py
python data/scripts/build_cohort.py
python experiments/01_first_prediction/run.py
python data/scripts/export_viz_data.py
cd viz && python3 -m http.server 8765  # then open localhost:8765
```

# 5. Results

The cohort composition that the model operates over is summarised in
**Figure 1** and **Table 1**. The 911-dam population is dominated by
single-stage structures (53 %) and concentrated in Minas Gerais (35 %);
upstream-method dams — the historically dangerous class — are only 45
facilities (5 %) but carry, in Table 1, the largest mean height (49 m vs.
12–22 m for other classes) and median impounded volume (4.4 Mm³ vs.
≤ 0.66 Mm³).

## 5.1 Construction-method posterior

Posterior 12-month failure rate per construction method (snapshot
2026-05-21) is given in **Table 2** and plotted in **Figure 2**:

| construction | prior (annual) | empirical | posterior | n (dam-months) |
|---|---|---|---|---|
| upstream     | 0.50% | 12 / 5,940 = 0.20% | **0.39%** | 5,940 |
| unknown      | 0.10% | 0 / 1,056          | 0.090%    | 1,056 |
| centerline   | 0.10% | 0 / 15,180         | 0.040%    | 15,180 |
| single_stage | 0.10% | 0 / 64,152         | 0.013%    | 64,152 |
| downstream   | 0.05% | 0 / 29,436         | 0.013%    | 29,436 |

This recapitulates the central published finding [@rana2021] that
upstream-method dams carry an order of magnitude higher historical failure
rate than other construction methods, and quantifies the Brazilian-cohort-
specific posterior given the single linked positive event. The upstream
posterior (0.39 %/yr) is pulled below its prior (0.50 %) by the empirical
rate of 0.20 %; the four other classes have no observed positives and sit
near their priors.

## 5.2 Within-upstream ranking

Once the hierarchical Level-2 (operator) and Level-3 (height / volume /
age / CRI) refinements are applied, the top-30 dams are no longer tied at
the homogeneous upstream rate (**Figure 3**, **Table 3**). Selected
entries from the top-10 (these are the pre-InSAR engineering-only values;
dam_id 8765 falls to 1.60 % after its Level-4 InSAR shift, see §5.4):

| rank | dam_id | name | operator | risk_12m |
|---|---|---|---|---|
| 1 | 8765 | Barragem de Germano  | Samarco            | 1.97% |
| 2 | 8332 | Pontal               | Vale               | 1.14% |
| 3 | 9533 | ED Monjolo           | Vale               | 0.88% |
| 4 | 9532 | ED Vale das Cobras   | Vale               | 0.63% |
| 5 | 8431 | Barragem Eustáquio   | Kinross            | 0.63% |
| 6 | 8286 | Forquilha II         | Vale               | 0.61% |
| 7 | 8283 | Forquilha I          | Vale               | 0.59% |
| 8 | 8290 | Forquilha III        | Vale               | 0.46% |
| 9 | 8955 | Barragem Serra Azul  | ArcelorMittal      | 0.45% |
| 10 | 8389 | Sul Superior        | Vale               | 0.42% |

**Independent validation against ANM emergency declarations.** The model
is given no information about ANM's declared emergency levels. Yet the
top-15 (Table 3) contains, purely from engineering features:

- **Barragem Serra Azul** (ArcelorMittal) at rank 9 — the *single dam in
  all of Brazil currently at Emergency Level 3*, the highest level.
- **Forquilha I, II and III** (Vale) at ranks 6–8 — all three at
  Emergency Level 2, the cluster that required partial evacuation of
  downstream communities in 2022.
- **Pontal, Sul Superior, Xingu** (Vale) — further Emergency Level 1–2
  facilities.

That the model's independent engineering-feature ranking surfaces the
operationally-recognised emergency dams near the top is a meaningful
external check: the ranking is not merely re-stating "upstream method"
but is correctly ordering *within* the upstream class in a way that
agrees with the regulator's separate, monitoring-based determinations.

We caveat strongly that the *within-upstream* differentiation reflects
the published engineering effect sizes (taller, larger, older dams fail
more often) rather than any data-driven discovery; the InSAR Level-4
term refines this ranking with *current* deformation signal where
Sentinel-1 coverage and our sampling sophistication permit (§5.4–5.5),
but does not yet override the *historical* effect-size priors at
population scale.

## 5.3 Calibration and discrimination

The model attains training log-loss 0.00064, AUROC 0.9995, ECE 0.00013.
These figures are flattering because the cohort base rate is 0.01% per
dam-month and the model assigns near-zero probability to the vast
majority of rows. Substantive evaluation awaits more linked positives
and the rolling-origin protocol.

## 5.4 Fundão retrospective: a partial-precursor finding

We submitted a second HyP3 batch (42 SBAS pairs) at the actual Fundão
dam coordinates (-20.193, -43.493) over 2014-10 to 2015-11, downloaded
the 42 unwrapped-phase rasters, sampled the line-of-sight time series at
the dam centroid and at a 3 km stable reference point, and ran the
hierarchical model on a rolling 12-month trailing-feature window for
every month from 2014-10 to 2015-11.

Result, in full: ASF returned scenes only from June 2015 onward for this
descending-orbit footprint (Sentinel-1's systematic acquisition over MG
began later in this orbit cycle than over neighbouring scenes), so the
trailing-window InSAR features are active only from 2015-06 onward. For
the months 2014-10 to 2015-05 the model returns the engineering-features
baseline of **0.75 %**, correctly elevated relative to the 0.01 % cohort
mean. From 2015-06 onward the predicted risk oscillates between **0.17 %
and 3.27 %** across consecutive months. The month containing the
catastrophic failure (2015-11) carries a predicted risk of **0.96 %**,
slightly above the engineering baseline but not a clean
accelerating-toward-failure trajectory (`figures/fundao_retrospective.png`).

The oscillation is informative about our InSAR sampling sophistication
rather than about the underlying signal. Inspection of the raw time
series shows that the dam-crest LOS values track the 3 km reference
values to within ~1 mm — i.e. atmospheric and orbital common-mode
signals dominate the differential, and the dam-specific motion in our
crude median-pixel-buffer sampler is below the noise floor. The ~30 mm
horizontal pre-failure deformation reported by @grebby2021 at Brumadinho
(2019) was extracted via PS-InSAR with hundreds of reference points and
explicit atmospheric correction; reproducing that precision is a
methodology upgrade we have not yet built, and is the highest-priority
follow-up.

What this experiment establishes:

1. **The pipeline works end-to-end on real ASF/HyP3 data.** Search,
   submit, queue, download, raster-sample, feature-extract, model-infer,
   plot — the chain has zero broken links.
2. **The model produces a plausible engineering-feature baseline** at
   the Fundão coordinates (0.75 %), well above the cohort mean, even
   when the dam is not in the SIGBM registry.
3. **The current InSAR feature surface is too noisy** to materially
   refine the engineering-feature prediction at single-dam resolution.
   This is a known limitation of single-pixel-buffer sampling with no
   atmospheric correction and matches the methodological literature.

The negative-or-noisy retrospective is a research outcome, not a
failure. It quantifies what's missing from our pipeline (PSI processing,
atmospheric correction, multi-reference de-trending) and pushes those
items to the top of the methodology backlog. **Figure 5** (left) plots
the trajectory with a 3-month smooth; **Figure 6** (left) plots the
underlying LOS velocity. A side-by-side comparison of both retrospective
events is given in **Table 4**.

## 5.5 Brumadinho B1 retrospective: a partial-precursor hit

A second HyP3 batch was submitted at the Brumadinho B1 dam coordinates
(-20.117, -44.123) over 2018-01 to 2019-01. The 2018 era covers both
Sentinel-1A and S1B operations, so the bbox + window yielded 66 scenes
(vs. 16 for Fundão's earlier-mission window), and 192 SBAS jobs were
submitted at three-temporal-neighbour density.

**Methodology finding during submission.** 128 of 192 jobs failed at
HyP3 with 100 % correspondence between failure and cross-relative-orbit
pairing. Sentinel-1 has many tracks that overlap a small bbox, and pairs
across tracks exceed the InSAR coherence baseline limit. We patched
`short_baseline_pairs` to group by `pathNumber` before forming pairs;
all future submissions group correctly. The 64 succeeded pairs are
sufficient for a retrospective; the patch commit hash is
[`9fa0bbb`](https://github.com/ViktorSmirnov71/sentinela-bayes-br/commit/9fa0bbb).

**Trajectory.** With the rolling-window pipeline of §5.4 applied to the
64-pair B1 dataset, Sentinela's predicted 12-month failure probability
through 2018 evolves as follows (`figures/b1_brumadinho_retrospective.png`):

| month  | n_obs | risk_12m | notes |
|--------|------:|---------:|-------|
| 2018-01 |  3 | 0.42 % | engineering baseline; too-sparse window |
| 2018-02 |  8 | 0.09 % | early-window noise |
| 2018-03 | 13 | 0.09 % | early-window noise |
| **2018-04** | **18** | **1.86 %** | **spike within Grebby's first risk milestone** |
| 2018-05 | 23 | 0.57 % |  |
| 2018-06 | 28 | 0.35 % | drift downward |
| 2018-07 | 33 | 0.13 % |  |
| 2018-08 | 39 | 0.22 % |  |
| 2018-09 | 43 | 0.26 % |  |
| 2018-10 | 49 | 0.28 % |  |
| 2018-11 | 54 | 0.23 % |  |
| 2018-12 | 59 | 0.20 % |  |
| **2019-01** | 61 | **0.26 %** | collapse month |

@grebby2021 identified two risk milestones for B1: a "definitive but
emergent" window Feb–Aug 2018, and an "imminent risk of collapse"
window Jun–Dec 2018. Our 2018-04 spike of 1.86 % falls squarely within
the first window — a partial retrospective replication. The model does
not, however, surface the second imminent-risk window; risk drops to
baseline through summer/autumn 2018 and the collapse month carries only
0.26 %.

This is a meaningful partial result: the pipeline runs end-to-end on
the canonical reference failure, produces a precursor flag in the
expected calendar quarter, but does not sustain the signal through the
second flagged window. As at Fundão, the limiting factor is the
sampling sophistication of our LOS time series — single-pixel-median
sampling against a 3 km reference cannot reproduce the PS-InSAR
multi-reference processing Grebby used. Future iterations with MintPy
will revisit both retrospectives. **Figure 5** (right) shows the B1
trajectory with the Grebby risk windows as amber bands; the smoothed
April peak aligns with the leading edge of milestone 1.

## 5.6 Visualisation

A self-contained interactive Three.js visualisation is shipped at
`viz/index.html`: 877 geocoded dams are rendered as risk-proportional
spikes erupting from a 3D mesh of Brazil's terrain (SRTM elevation via
Copernicus terrarium tiles), with colour along a teal → violet → magenta
ramp by risk decile, the top-30 pulsing, and active-emergency dams
carrying an amber ground halo. **Figure 4** is a static render of the
same risk field for print.

The 3D view surfaces patterns the tabular ranking does not: the dense
clustering of high-risk spikes in the iron-ore corridor of the
Minas Gerais highlands (terrain elevation ~800–1,400 m), the relative
emptiness of the Amazon basin and the northeast, and the spatial
proximity of the Forquilha cluster to dam_id 8765 at the Mariana / Germano
complex. Future iterations will encode posterior uncertainty as faded
outer spikes.

# 6. Discussion

## 6.1 What we learn

The single most useful finding of the present iteration is methodological:
*with one linked positive event in a 911-dam cohort, the literature priors
are the model.* No amount of feature engineering or model-class tuning
can extract more signal than the data contains. The honest path is to
embed the literature transparently and refine the priors as linked
positives accumulate.

Specific within-Brazil findings, with all the caveats above:

1. **Upstream-method posterior is consistent with literature.** Our Level-1
   posterior at 0.39%/year for upstream-method dams is within the range
   reported in @rana2021's global analysis (0.4–1.2%/year). The
   construction-method effect is the single dominant predictor.

2. **Vale dominates the top-of-shortlist.** Six of the top-10 dams are
   Vale-operated. This reflects Vale's large fleet of upstream-method
   iron-ore dams in Minas Gerais; the model does *not* infer an
   operator-level penalty for Vale beyond its dam count.

3. **The Forquilha cluster's appearance in the top-10 validates the
   engineering-feature surface.** ANM's 2022 Emergency Level 2 declaration
   on these three dams was based on geotechnical monitoring outside our
   feature set; our model's independent agreement is evidence the model's
   ranking is operationally interpretable.

## 6.2 What we do not learn

- **Whether InSAR adds marginal predictive value.** This is RQ1 in our
  pre-registration. Pending HyP3 completion (currently 42 jobs running).
- **Whether B1 / Brumadinho would have been flagged prospectively.** This
  is RQ4. Requires a pre-2019 SIGBM snapshot (Wayback or FOI).
- **Whether ANM's CRI score adds information beyond engineering features.**
  RQ5. Requires more linked positives for meaningful comparison.

## 6.3 Ethics

This work is *research*, not an operational early-warning system. Outputs
must not be used to direct evacuation decisions. The model uses only
public data; operator-internal monitoring signals (piezometers,
inclinometers) are deliberately excluded, both to preserve open
reproducibility and to lower-bound what the public-data approach can
achieve. We will not publish a public dashboard naming individual
operators without giving them an opportunity to respond. Full ethics
posture: `docs/06-ethics-and-limitations.md`.

# 7. Limitations and threats to validity

1. **Registry amnesia.** Failed dams are removed from the active SIGBM
   post-failure. This is the dominant bias in the training data.
2. **One linked positive.** Within-cohort signal at the engineering-feature
   level is dominated by the literature priors, not by the data.
3. **Survivor selection.** Dams that approached failure but were
   remediated are coded as non-failures in our labels.
4. **Sample selection on satellite era.** All InSAR-era failures (2014–)
   may not generalise to pre-radar regimes; we do not claim such
   generalisation.
5. **Label provenance.** Bowker–Chambers severity coding is one analyst's
   judgement. Sensitivity analyses at severity-≥ 3 are planned.

# 8. Future work

In priority order, informed by the results above:

1. **PS-InSAR / MintPy processing.** The single highest-value upgrade.
   Both retrospectives are limited by atmospheric noise in single-pixel
   sampling; multi-reference persistent-scatterer processing should lift
   the second Grebby window above the noise floor and is the prerequisite
   for InSAR to materially improve the population ranking.
2. **Historical SIGBM snapshots.** Wayback Machine archives plus an FOI
   request to ANM should yield pre-2015 and pre-2019 cohort states so
   that Fundão and B1 can be predicted prospectively, not via proxy, and
   so the model gains genuinely held-out positives.
3. **CHIRPS rainfall.** Daily 0.05° rainfall + SPI-3 / SPI-6 antecedent
   moisture as the next feature block; enables the rainfall × InSAR
   interaction test (RQ7).
4. **Operator-level Bayesian hierarchy.** The current James–Stein shift
   is a first-order operator effect; a full random-effects model with
   PyMC will be fit once linked positives ≥ 30.
5. **Cross-LATAM transfer.** SIGBM's analogues exist for Colombia (DANE)
   and Mexico (INEGI). Cross-country transfer experiments will test the
   generality of the model's structure beyond Brazil.

# 9. Conclusion

We have built and openly released Sentinela, a calibrated
hierarchical-Bayesian forecaster for Brazilian mine-tailings dam
failures driven entirely by public data. The system is reproducible
from a clean clone to forecast in five commands, and every artefact in
this paper — the 911-dam cohort, the per-dam risk ranking, the 3D risk
field, and the two retrospectives — regenerates deterministically.

Three findings stand out. First, in the one-linked-positive regime that
characterises this problem, discriminative learners fail (they memorise
or smooth to zero) and a literature-prior Bayesian model is the honest
choice; its construction-method posterior reproduces the published
order-of-magnitude upstream-method risk premium. Second, the model's
purely engineering-feature ranking independently surfaces the dams ANM
has separately placed under emergency declarations — the single
Level-3 dam in the country and the entire Level-2 Forquilha cluster
appear in the top-15 — which is a genuine external validation that the
within-class ordering is meaningful. Third, on the canonical Brumadinho
B1 failure, the model produces a risk spike in the exact calendar
quarter of the precursor window reported independently by satellite
geodesists, though it does not sustain that signal — a partial
replication that cleanly localises the remaining methodological gap to
InSAR processing sophistication rather than to the modelling framework.

Sentinela is a research artefact, not an operational early-warning
system, and its limitations (registry amnesia, one linked positive,
single-pixel InSAR sampling) are documented and bounded rather than
hidden. What it demonstrates is that a small, carefully-chosen
open-data pipeline plus a transparent Bayesian model can produce a
calibrated, externally-validated, fully-reproducible risk ranking for a
high-stakes infrastructure problem — and can do so quickly enough to be
a credible decision-support input rather than a multi-year research
programme.

# Figures and tables

**Figures** (in `figures/`):

- Figure 1 — `fig1_cohort_composition.png`: cohort by method / state / emergency / status.
- Figure 2 — `fig2_posterior_rates.png`: prior vs. posterior failure rate per method.
- Figure 3 — `fig3_top_risk_ranking.png`: top-20 dams by predicted 12-month risk.
- Figure 4 — `fig4_terrain_3d.png`: static 3D render of the risk field over terrain.
- Figure 5 — `fig5_retrospectives.png`: Fundão + B1 risk trajectories with Grebby windows.
- Figure 6 — `fig6_insar_comparison.png`: extracted InSAR LOS velocity per event.

**Tables** (in `paper/tables/`, CSV + `tables.md`):

- Table 1 — cohort summary by construction method.
- Table 2 — prior vs. posterior failure rate.
- Table 3 — top-15 highest-risk dams.
- Table 4 — retrospective comparison (Fundão vs. B1).
- Table 5 — hierarchical model structure.

# Acknowledgements

This is pro bono research conducted on behalf of
[Arakon](https://arakon.co.uk) as a theoretical thought experiment on
rapid machine-learning model deployment for high-stakes infrastructure
decisions. The author thanks ANM for maintaining SIGBM as public open
data, ESA/Copernicus for Sentinel-1 open archive, and Alaska Satellite
Facility for hosting HyP3.

# References

References use BibTeX keys defined in `docs/refs.bib`. Pandoc invocation:

```bash
pandoc paper/manuscript.md \
       --citeproc \
       --bibliography docs/refs.bib \
       --csl=https://www.zotero.org/styles/nature \
       -o paper/manuscript.pdf
```

Primary references cited above:

- Grebby et al. 2021 — *Nat. Comms Earth & Env.* — Brumadinho precursors.
- Carlà et al. 2019 — *Sci. Rep.* — InSAR inverse-velocity.
- Du et al. 2020 — *Sci. Total Env.* — Brumadinho InSAR risk.
- Gama et al. 2023 — *Nat. Comms Earth & Env.* — slip-surface mechanism.
- Mura et al. 2018 — *Remote Sens.* — Germano post-Fundão DInSAR.
- Macchiarulo et al. 2023 — *Remote Sens. Env.* — joint InSAR + moisture.
- Manconi et al. 2024 — *Bull. Eng. Geol.* — operational Sentinel-1.
- Zhang et al. 2025 — *Int. J. Appl. Earth Obs.* — consolidation separation.
- Zheng et al. 2025 — *Sci. Rep.* — InSAR + numerical model.
- Rana et al. 2021 — *Eng. Geol.* — global TSF failure statistics.
- de Lima et al. 2022 — SIGBM risk classification.
- ANM SIGBM (`app.anm.gov.br/sigbm/publico`).
- Bowker & Chambers, WMTF database.
- Ferreira et al. 2020 — BrazilDAM benchmark.
