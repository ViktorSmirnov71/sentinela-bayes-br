# Related work

Citations resolve against `docs/refs.bib`. The aim of this synthesis is to
locate the specific gap that the present work fills.

## 1. Post-hoc reconstruction of individual failures

The most cited recent line is the satellite-precursor reconstruction of
Brumadinho B1. **Grebby et al. (2021)** [@grebby2021] in *Communications
Earth & Environment* applied advanced InSAR time-series analysis to Sentinel-1
data over B1 and detected ground-deformation precursors at least five months
before the 25 January 2019 collapse, with two flagged risk milestones in
February–August 2018 and June–December 2018. **Carlà et al. (2019)**
[@carla2019] independently derived an inverse-velocity-based time-of-failure
prediction from precursory deformation. **Du et al. (2020)** [@du2020]
performed an InSAR time-series risk assessment of the Brumadinho dam cluster.
**Gama et al. (2023)** [@gama2023] published a slip-surface mechanism account
in *Communications Earth & Environment*, attributing the failure to delayed
static liquefaction along an identified surface.

For Fundão (Mariana 2015), **Mura et al. (2018)** [@mura2018] applied DInSAR
with TerraSAR-X to the Germano mining area post-collapse to monitor the
remaining dikes; **Carlà et al. (2018)** and related work documented that
Fundão had detectable settlement signatures of $\sim 60$ mm consistent with
internal erosion in the months before failure.

**Common feature of this line:** retrospective, single-event, focused on
demonstrating that InSAR *could have* detected precursors. None produces a
generalisable forecaster.

## 2. Generalised early-warning and ML on InSAR

**Macchiarulo et al. (2023)** [@macchiarulo2023] showed that a joint analysis
of InSAR-derived surface deformation and SAR-derived moisture content reduces
false alarms in tailings-dam risk assessment. **Manconi et al. (2024)**
[@manconi2024] in *Bulletin of Engineering Geology* reviewed practical
considerations for operational Sentinel-1 InSAR monitoring of tailings dams.
**Zhang et al. (2025)** [@zhang2025] proposed an InSAR-based framework that
robustly separates consolidation settlement from failure-relevant deformation,
reducing false alarms by ~48% in their evaluation. **Zheng et al. (2025)**
[@zheng2025] integrated InSAR with 3D numerical modelling to simulate
mechanical behaviour and improve risk assessment.

A separate line applies deep learning directly to tailings-pond imagery.
**Wang et al. (2025)** [@wang2025] used UAV imagery + deep learning for
hazard identification. **Yang et al. (2025)** [@yang2025] proposed a
time-series-decomposition + Elman-network model for tailings-dam displacement
interval prediction.

**Common feature of this line:** still site-specific or methodologically
focused on one signal at a time. Models do not output calibrated probabilities
at a population scale, do not jointly use construction-type metadata, and are
not validated on a held-out failure cohort.

## 3. Population-scale risk classification

**De Lima et al. (2022)** [@delima2022] classified Brazilian TSFs by risk
using SIGBM-derived features (without InSAR). This is the closest direct
antecedent to the present work, but treats the ANM administrative risk score
as the supervised target rather than failure itself, and does not incorporate
remote-sensing precursors.

**Rana et al. (2021)** [@rana2021] published a global statistical model of
tailings-dam failure frequency vs. construction type using WMTF data; the
result is a population baseline rate, not a per-dam forecast.

## 4. Datasets and inventories

- **SIGBM** (ANM, 2019–) [@anm_sigbm] — Brazilian national mine-tailings dam
  registry; public web app and downloadable tabular extract via
  basedosdados.org.
- **Global Tailings Portal** (GRID-Arendal / Church of England Pensions Board,
  2020) [@gtp2020] — first global public TSF database (~1,800 dams).
- **World Mine Tailings Failures** (Bowker & Chambers, 2015–) [@wmtf] —
  failure-event database from 1915 onwards, severity-classified.
- **BrazilDAM** (Ferreira et al., 2020) [@brazildam] — labelled Sentinel-2 /
  Landsat-8 imagery of 769 SIGBM dams, 2016–2019, primarily for detection.
- **EGMS** (Copernicus, 2022–) [@egms] — Europe-wide InSAR ground-motion
  service. No Brazilian equivalent yet, but the processing chain is open and
  reproducible against Sentinel-1 archives.

## 5. The gap

Combining the three lines:

- post-hoc precursor work proves the *signal exists*;
- methodological InSAR-ML work proves the *signal can be extracted*;
- population-scale work proves a *cohort exists* but uses administrative scores
  as labels, not failures.

What does not exist in the open literature:

> A reproducible, openly published, per-dam probabilistic forecaster for
> Brazilian TSFs that (i) uses SIGBM as its cohort, (ii) ingests Sentinel-1
> InSAR-derived precursor features, (iii) is trained against documented
> failure / near-miss events with explicit survival censoring, and (iv) is
> evaluated on Fundão and Brumadinho as held-out positives with proper
> uncertainty quantification.

That is the target.

## Open questions surfaced by the review

- The Grebby and Carlà reconstructions disagree on optimal precursor lead time
  (~5 vs ~2 months). A systematic ablation across InSAR feature transforms is
  worth doing.
- The Macchiarulo result on moisture content suggests SAR-VV/VH backscatter
  ratios contain failure-relevant information beyond displacement. We should
  include them.
- Construction-type heterogeneity is acknowledged everywhere and modelled
  nowhere as a multitask structure. Plausible source of gain.
