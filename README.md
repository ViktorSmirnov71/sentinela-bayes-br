# Sentinela: Bayesian Failure Forecasting for Brazilian Tailings Dams

![status](https://img.shields.io/badge/status-pre--pilot-orange)
![license](https://img.shields.io/badge/license-MIT-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)

> **Status: pre-pilot.** Methodology and research questions are pre-registered
> in `docs/`. No results yet. The first commit timestamp is the pre-registration
> reference; subsequent material changes are dated in `CHANGELOG.md`.

> **Patronage.** Sentinela is pro bono work conducted on behalf of
> [Arakon](https://arakon.co.uk) as a theoretical thought experiment on rapid
> machine-learning model deployment for high-stakes infrastructure decisions.
> It is research, not product: the goal is to characterise what is and is not
> possible with a small, carefully chosen open-data pipeline and a modern
> tabular foundation model.

## Introduction

A **tailings dam** is the engineered wall that holds back the slurry of finely
ground rock left over from a mining operation. Brazil has roughly 700 of them.
When one fails, the contents are released as a fast-moving wave of toxic mud.
Mariana 2015 flattened a town and contaminated 600 km of the Doce river.
Brumadinho 2019 killed about 270 people in ninety seconds. Predicting which
dams are at risk *before* they fail is one of the highest-stakes
geotechnical-engineering problems open today.

After Brumadinho, two things became reproducibly true. First, the European
Copernicus programme has been quietly imaging every square metre of Brazil with
millimetre-precision radar (Sentinel-1) every six to twelve days since 2014.
Second, the post-mortems on Brumadinho showed that the collapse was *visible*
in that satellite data at least five months in advance: the ground on the dam
face was already moving in a characteristic accelerating pattern. Nobody acted
on it, because nobody was systematically looking.

**Sentinela** is the systematic version of that "looking". For every active
dam in the Brazilian regulator's public registry, we combine the satellite
ground-motion signal, antecedent rainfall, basic engineering metadata
(construction type, height, age), and downstream population to produce one
number per dam per month: *the probability of catastrophic failure within the
next twelve months*, with calibrated uncertainty.

We are not building an operational early-warning system. We are building a
reproducible, open-data **research artefact** that establishes how well such a
forecaster can perform from purely public inputs, and where its remaining gaps
lie. The first headline test is whether, with Mariana and Brumadinho withheld
from training entirely, our model assigns those two dams a top-decile failure
probability in the months preceding their collapse.

## Context: what's the modelling challenge, in plain terms

Three things make this problem hard, and each maps to a piece of methodology
worth understanding.

**1. Most dams haven't failed *yet*.** Out of ~700 active dams we have on the
order of 10 documented catastrophic failures. A model that predicts "no
failure" for every dam is 99% accurate and entirely useless. What we want is
not classification but **calibrated probability**: when the model says "8%
chance", that should actually correspond to an 8% empirical failure rate. The
closest real-world analogy is cardiology. You don't want a binary "will this
patient have a heart attack", you want a calibrated annual risk percentage.
The technical name for getting this right is **survival analysis under
right-censoring**, and the metric that matters is **Expected Calibration
Error**, not accuracy.

**2. The dataset is tiny by deep-learning standards.** Most neural networks
overfit hopelessly on 700 rows with 10 positive labels. Classical Bayesian
methods can handle that scale but require careful per-problem statistical
engineering. We use **TabPFN**, a transformer pre-trained on millions of
synthetic tabular datasets that has *learned, in advance, how to be a
calibrated Bayesian learner on small tabular problems*. The technical name for
what it does is **amortized in-context Bayesian inference**: it pays the cost
of posterior computation once, during pre-training, and then any new dataset
is handled in a single forward pass with no additional fitting. It is the
same mechanism that lets large language models "learn" from a handful of
in-prompt examples.

**3. The signal we care about lives in a noisy time series.** Sentinel-1
InSAR data measures sub-millimetre ground motion, but it is contaminated by
atmospheric distortion, seasonal vegetation changes, and phase-unwrapping
errors. Turning a ten-year displacement record into a handful of clean
features that capture "pathological pre-failure motion" is its own subfield.
We use the precursor features identified by the Brumadinho post-mortem
literature ([Grebby 2021](https://www.nature.com/articles/s43247-020-00079-2),
[Carlà 2019](https://www.nature.com/articles/s41598-019-50402-x)): velocity,
acceleration, spectral slope, anomaly variance, applied at population scale.

The full reasoning behind the dataset selection, cleaning pipeline, and model
architecture lives in `docs/`. The bibliography is in `docs/refs.bib`. The
falsifiable, pre-registered research questions are in
`docs/05-research-questions.md`.

## Quickstart

```bash
git clone https://github.com/ViktorSmirnov71/sentinela-bayes-br
cd sentinela-bayes-br
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## How to read this repository

- `docs/00-overview.md`: one-page abstract and scope.
- `docs/01-problem.md`: formal problem statement.
- `docs/02-related-work.md`: literature synthesis and the identified gap.
- `docs/03-data.md`: full audit of the datasets and cleaning steps.
- `docs/04-methods.md`: cohort definition, features, baselines, validation.
- `docs/05-research-questions.md`: pre-registered, falsifiable hypotheses.
- `docs/06-ethics-and-limitations.md`: what this work can and cannot claim.
- `docs/refs.bib`: bibliography in BibTeX.

Code lives in `src/sentinela/`; configurations in `configs/`; experiment runs
in `experiments/` (outputs to `results/`, gitignored). Nothing should appear
outside these locations.

## License

MIT for code. See `LICENSE`. Data licenses vary by source: see `docs/03-data.md`.

## Citation

If this work informs other research, please cite the project (see
`CITATION.cff`) and the underlying data sources individually as listed in
`docs/refs.bib`.
