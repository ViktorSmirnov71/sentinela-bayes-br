# Data audit

For each candidate dataset we record: provenance, access mechanism, schema,
temporal coverage, spatial coverage, license, and the role it plays in the
modelling pipeline. Datasets are grouped by function.

A. Cohort and labels
B. Precursor signals (remote sensing)
C. Forcing variables (climate, hydrology)
D. Static metadata and exposure
E. Reference / cross-validation datasets

---

## A. Cohort and labels

### A1. SIGBM — Sistema Integrado de Gestão de Barragens de Mineração

- **Provenance.** Agência Nacional de Mineração (ANM), Brazil. The successor
  to DNPM, post-Brumadinho regulatory framework (Lei 14.066/2020).
- **Content.** National registry of all mining-tailings storage facilities
  in Brazil. Per dam: name, operator (CNPJ), latitude/longitude, construction
  method, height (m), reservoir volume (m³), licensing status, ANM Risk
  Category (CRI), Damage-Potential Category (DPA), age, ore type, declared
  emergency level.
- **Access.**
  - Web app: `https://app.anm.gov.br/sigbm/publico`
  - Cleaned tabular mirror: `basedosdados.org/dataset/0dccae0e-f872-450b-a209-075a5e877150`
  - dados.gov.br dataset: `https://dados.gov.br/dataset/barragens-de-mineracao`
- **Schema.** Tabular, ~30 columns, ~700 rows (active dams).
- **Coverage.** 2019–present, quarterly snapshots.
- **License.** Brazilian public open data.
- **Role.** Defines the cohort $\mathcal{D}$. Provides $x^{\text{static}}$ and
  $x^{\text{ops}}$. The CRI/DPA columns are *not* used as labels but as
  features and as a sanity-check comparator.

### A2. Global Tailings Portal (GTP)

- **Provenance.** GRID-Arendal under UNEP and Church of England Pensions Board
  investor-led disclosure initiative; launched January 2020.
- **Content.** ~1,800 dams globally with operator-disclosed attributes. Brazil
  coverage overlaps SIGBM but with operator-self-reported risk and history.
- **Access.** `https://tailing.grida.no/` — request-gated CSV at present.
- **License.** Open, with attribution. Some operator disclosures redacted.
- **Role.** Cross-validation of SIGBM static metadata. Provides international
  reference cohort for generalisation experiments outside Brazil.

### A3. World Mine Tailings Failures (WMTF)

- **Provenance.** Bowker & Chambers (2015–), maintained at
  `worldminetailingsfailures.org`.
- **Content.** Failure events from 1915 onwards with severity classification
  (Bowker–Chambers categories 1–5), construction type, fatalities, volume
  released.
- **Access.** Spreadsheet-distributed; updates by request.
- **Coverage.** Global. Brazilian failures: Fundão (2015), B1 Córrego do Feijão
  (2019), and a handful of pre-2015 events. We will manually augment with
  documented near-misses from MP-MG and ANM emergency-level declarations.
- **Role.** Positive labels $F_{i,[t,t+H]} = 1$. Severity ≥ category 4 is the
  primary cutoff; sensitivity analysis at ≥ category 3.

---

## B. Precursor signals (remote sensing)

### B1. Sentinel-1 SAR (ESA Copernicus)

- **Provenance.** ESA Copernicus programme.
- **Content.** C-band Synthetic Aperture Radar; IW mode, dual-polarisation
  (VV+VH); 6–12-day revisit; 5×20 m resolution per burst.
- **Access.**
  - Copernicus Data Space Ecosystem (CDSE): `dataspace.copernicus.eu` — free
    full-archive, requires registration.
  - AWS Open Data Registry: `registry.opendata.aws/sentinel-1/` — mirror.
- **Temporal.** 2014-10-03 (S1A launch) to present. S1B failed in 2021; S1C
  launched 2024.
- **License.** Copernicus open licence; free, full, open.
- **Role.** Source for InSAR-derived displacement time series at each dam.
  Processing options: MintPy, SNAP+StaMPS, ISCE2+MintPy, or hosted services
  (ASF HyP3, ARIA, COMET-LiCS). We will use HyP3-generated short-baseline
  pairs as the default backbone and reserve full ISCE2 + MintPy for the
  retrospective Brumadinho / Fundão reanalyses.
- **Caveats.** Geometric distortion in steep terrain; phase-decorrelation
  over the impoundment surface itself; ascending and descending passes
  required for vertical/horizontal decomposition.

### B2. BrazilDAM dataset

- **Provenance.** Ferreira et al. 2020 [@brazildam].
- **Content.** Sentinel-2 and Landsat-8 image cutouts at 769 SIGBM dam
  locations, 2016–2019, with detection labels.
- **Access.** Publicly distributed (arxiv.org/abs/2003.07948).
- **Role.** Pre-processed crop geometry per dam — useful as a starting point
  for defining the InSAR analysis window per facility.

### B3. NASADEM / Copernicus DEM 30 m

- **Provenance.** NASA / ESA.
- **Content.** Global elevation; required for InSAR topographic phase removal
  and for downstream-flow modelling.
- **Role.** InSAR processing dependency; runout-path priors.

---

## C. Forcing variables (climate, hydrology)

### C1. INMET BDMEP

- **Provenance.** Instituto Nacional de Meteorologia, Brazil.
- **Content.** Daily meteorological station records since 1961: precipitation,
  temperature, humidity, pressure, wind.
- **Access.** `bdmep.inmet.gov.br` — bulk CSV download; registration required.
- **License.** Brazilian public open data.
- **Role.** Station-based rainfall forcing. Interpolated to dam centroids.

### C2. CHIRPS

- **Provenance.** UCSB Climate Hazards Group / USGS.
- **Content.** Daily 0.05° rainfall, 1981–present.
- **Access.** `https://www.chc.ucsb.edu/data/chirps`.
- **License.** Public domain.
- **Role.** Spatially complete rainfall forcing. Used jointly with INMET to
  estimate antecedent moisture indices (API, SPI-3, SPI-6).

### C3. ERA5-Land

- **Provenance.** ECMWF Copernicus Climate Change Service.
- **Content.** Hourly reanalysis: precipitation, soil moisture (4 layers),
  evapotranspiration, runoff, 0.1° grid.
- **Access.** CDS API.
- **License.** Copernicus.
- **Role.** Soil-moisture state as antecedent feature; cross-check on CHIRPS
  rainfall.

---

## D. Static metadata and exposure

### D1. IBGE Censo Demográfico + Aglomerados Subnormais

- **Provenance.** Instituto Brasileiro de Geografia e Estatística.
- **Content.** Population at fine spatial granularity (setor censitário) and
  delineations of informal settlements.
- **Access.** `ibge.gov.br/estatisticas/sociais/populacao/`; `basedosdados.org`.
- **Role.** Downstream-population exposure for translating $P(F)$ into expected
  fatalities or affected population.

### D2. ANM mining titles & operators

- **Provenance.** ANM SIGMINE.
- **Content.** Active mining concessions, operator identity, ore type.
- **Access.** `app.anm.gov.br/sigmine/` and `dados.gov.br`.
- **Role.** Static features; joins to SIGBM by CNPJ.

### D3. SNISB

- **Provenance.** ANA — Agência Nacional de Águas. Established under Lei
  12.334/2010. Governs *all* dams ≥ 15 m height OR ≥ 3 hm³ reservoir, not
  only tailings.
- **Content.** ~23,000 dams in 2016 census (general-purpose, not tailings-only).
- **Access.** `snirh.gov.br/portal/snisb/`.
- **License.** Public.
- **Role.** Cross-reference for non-tailings dams in the same basin (cascading
  failure risk).

---

## E. Reference / cross-validation datasets

### E1. EGMS (European Ground Motion Service)

- **Role.** *Not* directly usable for Brazil (Europe only) but the EGMS
  processing chain, validation studies, and parameter conventions are an open
  reference design for any analogous Brazilian product we publish. Our InSAR
  outputs will follow EGMS conventions where compatible (LOS velocity,
  persistent-scatterer density per km², decomposed vertical/east).

### E2. Manual incident corpus (to be built)

- A small (~50 entry) curated database of documented incidents that did *not*
  reach full failure: emergency-level declarations from SIGBM, MP-MG dossiers,
  press coverage, ANP-issued warnings. Negative-class enrichment for the
  rare-event problem. This is hand-curated; provenance for each entry will
  be tracked in `data/interim/incidents/sources.csv`.

---

## What we are *not* using (and why)

- **Operator-internal piezometer / inclinometer time series.** These exist
  but are proprietary and unevenly available. Including them would defeat
  the open-reproducibility goal. We comment on the gap in
  `docs/06-ethics-and-limitations.md`.
- **High-resolution commercial SAR (TerraSAR-X, ICEYE).** Out of budget; data
  not redistributable.
- **Operator self-disclosed monitoring data.** Same concern; we want the
  result to be reproducible from open data alone.

---

## Storage and licensing posture

`data/raw/` and `data/interim/` and `data/processed/` are gitignored.
Provenance for every materialised file is recorded in `data/MANIFEST.csv`
(produced by the loaders in `src/sentinela/io/`). No raw data is committed
to the repository.
