# data/external/

External data that travels with the repository because it is small, citation-
anchored, and required for the pipeline to run. Files here are committed to git
(unlike `data/raw/`, `data/interim/`, `data/processed/` which are gitignored).

## Contents

### `brazilian_failures.csv`

Hand-curated table of Brazilian mining-related dam failure events used as the
positive-class labels for Sentinela. Each row carries:

- `event_id` — internal stable identifier.
- `date` — failure date (ISO 8601).
- `state`, `municipality`, `mine`, `operator`, `dam_name` — geographic and
  facility metadata.
- `construction_method`, `ore` — engineering context.
- `severity_bowker_chambers` — Bowker–Chambers severity 1–5. We use ≥ 4 as the
  primary cutoff; sensitivity at ≥ 3 (which includes near-miss emergencies).
- `fatalities`, `volume_released_m3` — consequence metrics.
- `fixture_dam_id` — link to a synthetic row in the fixture SIGBM table, used
  while real SIGBM data has not been ingested. Cleared once real data lands.
- `real_sigbm_dam_id` — SIGBM identifier once available.
- `source_url` — primary citation supporting the entry.
- `notes` — short free-text context.

Every entry must have at least one verifiable source. Speculative or
press-only-confirmed events go in a separate `near_misses.csv` (not yet
created) rather than the canonical labels table.

## Schema-evolution policy

Adding new columns is fine. Renaming or removing existing columns requires a
CHANGELOG entry under "Changed" with a one-line rationale and a sweep of any
downstream loader in `src/sentinela/io/` that depends on the affected column.
