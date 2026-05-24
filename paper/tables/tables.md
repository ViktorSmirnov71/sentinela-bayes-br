### Table 1 — Cohort summary by construction method

| construction_method | n_dams | mean_height_m | median_volume_m3 | n_high_cri | n_emergency |
| --- | --- | --- | --- | --- | --- |
| single_stage | 486 | 11.9 | 7.657e+04 | 29 | 38 |
| downstream | 223 | 22.1 | 6.632e+05 | 14 | 14 |
| centerline | 115 | 22.4 | 3.197e+05 | 17 | 19 |
| upstream | 45 | 49.1 | 4.42e+06 | 13 | 14 |
| unknown | 42 | 2.2 | 0 | 4 | 4 |

### Table 2 — Prior vs. posterior failure rate (Beta-Binomial, α=10,000)

| construction_method | n_dam_months | positives | prior_annual_pct | posterior_annual_pct |
| --- | --- | --- | --- | --- |
| upstream | 5940 | 12 | 0.5 | 0.389 |
| unknown | 1056 | 0 | 0.1 | 0.09 |
| centerline | 15180 | 0 | 0.1 | 0.04 |
| single_stage | 64152 | 0 | 0.1 | 0.013 |
| downstream | 29436 | 0 | 0.05 | 0.013 |

### Table 3 — Top-15 highest-risk active dams (2026 snapshot)

| dam_id | name | operator_name | state | construction_method | height_m | emergency_level | risk_12m_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8765 | Barragem de Germano | SAMARCO MINERACAO S.A. EM RE | MG | upstream | 163 | 0 | 1.595 |
| 8332 | Pontal | VALE S.A. | MG | upstream | 69.9 | 1 | 1.143 |
| 9533 | ED Monjolo | VALE S.A. | MG | upstream | 145 | 0 | 0.879 |
| 9532 | ED Vale das Cobras | VALE S.A. | MG | upstream | 122.4 | 0 | 0.635 |
| 8431 | Barragem Eustáquio | KINROSS BRASIL MINERACAO S/A | MG | centerline | 114 | 0 | 0.632 |
| 8286 | Forquilha II | VALE S.A. | MG | upstream | 94.3 | 2 | 0.615 |
| 8283 | Forquilha I | VALE S.A. | MG | upstream | 94.44 | 2 | 0.587 |
| 8290 | Forquilha III | VALE S.A. | MG | upstream | 77 | 2 | 0.464 |
| 8955 | Barragem Serra Azul | ARCELORMITTAL BRASIL S.A. | MG | upstream | 80.1 | 3 | 0.453 |
| 8389 | Sul Superior | VALE S.A. | MG | upstream | 75.5 | 2 | 0.422 |
| 9534 | Xingu | VALE S.A. | MG | upstream | 72 | 1 | 0.406 |
| 8209 | Campo Grande | VALE S.A. | MG | upstream | 93.98 | 0 | 0.406 |
| 9320 | Barragem B2 - Mina Tico-Tico | MINERACAO MORRO DO IPE S.A. | MG | upstream | 86 | 0 | 0.399 |
| 8291 | Barragem MSG | MINERACAO SERRA GRANDE S A | GO | upstream | 92 | 0 | 0.388 |
| 8207 | Doutor | VALE S.A. | MG | upstream | 79.98 | 0 | 0.342 |

### Table 4 — Retrospective comparison at the two reference failures

| event | collapse_date | insar_pairs | max_risk_pct | collapse_month_risk_pct | peak_month | matches_grebby_window |
| --- | --- | --- | --- | --- | --- | --- |
| Fundão (Samarco) | 2015-11-05 | 42 | 3.27 | 0.96 | 2015-06 | n/a (Fundão not in Grebby) |
| Brumadinho B1 (Vale) | 2019-01-25 | 61 | 1.86 | 0.26 | 2018-04 | yes (peak in milestone-1) |

### Table 5 — Hierarchical model structure

| level | mechanism | bound | data_source |
| --- | --- | --- | --- |
| 0 prior | literature base rate (Rana 2021 / Bowker-Chambers) | — | literature |
| 1 construction | Beta-Binomial posterior per construction method | — | SIGBM + WMTF labels |
| 2 operator | James-Stein shrunk per-operator logit shift | ±1.0 logit | SIGBM + labels |
| 3 engineering | bounded logit shifts: height, volume, age, CRI | 0.10–0.30 per z | SIGBM static fields |
| 4 InSAR | bounded logit shifts: LOS velocity, accel, spectral slope, variance ratio | ±1.5 logit total | Sentinel-1 HyP3 InSAR |
