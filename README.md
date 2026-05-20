# tailings-risk

Calibrated, per-dam failure-risk modelling for Brazilian mine-tailings storage
facilities. Combines the public ANM/SIGBM registry, Sentinel-1 InSAR ground-
deformation time series, INMET extreme-rainfall records, satellite indices,
and downstream-exposure geography to produce probabilistic risk forecasts
with proper uncertainty quantification.

The work targets a gap in the current literature: existing studies either
(a) post-hoc reconstruct precursors for individual failures (Brumadinho 2019,
Fundão 2015), or (b) classify dams by deterministic engineering scores. There
is no published, openly reproducible, per-dam probabilistic forecaster that
fuses the available open data with calibrated uncertainty. That is the contribution.

## Status

Pre-pilot. Scope, data audit, methodology, and research questions are documented
in `docs/`. Code in `src/` is a typed skeleton; experiments in `experiments/`
will be added as the work proceeds.

## Quickstart

```bash
git clone <this-repo>
cd tailings-risk
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## How to read this repository

- `docs/00-overview.md` — one-page abstract and scope.
- `docs/01-problem.md` — formal problem statement.
- `docs/02-related-work.md` — synthesis of the relevant literature (the gap).
- `docs/03-data.md` — full audit of available datasets.
- `docs/04-methods.md` — planned methodology.
- `docs/05-research-questions.md` — falsifiable hypotheses.
- `docs/06-ethics-and-limitations.md` — what this work can and cannot claim.
- `docs/refs.bib` — bibliography in BibTeX.

Anything not in one of those directories is intentional: code is in `src/`,
configs in `configs/`, runs in `experiments/`, outputs in `results/` (gitignored).

## License

MIT for code. See `LICENSE`. Data licenses vary by source — see `docs/03-data.md`.

## Citation

If this work informs other research, please cite the project (see `CITATION.cff`)
and the underlying data sources individually as listed in `docs/refs.bib`.
