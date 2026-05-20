# Ethics and limitations

Tailings-dam failure prediction is a high-stakes domain. Decisions taken on
the basis of model outputs can affect community-evacuation orders, regulatory
enforcement, and operator credit ratings. The following constraints govern
how outputs of this project may be presented and used.

## What this work is

A *research artefact*: a reproducible, open-data model of failure
probability for academic study and as a comparator for regulatory and
operator models.

## What this work is not

- **Not an operational early-warning system.** EWS requires redundancy,
  certified pipelines, 24/7 staffing, and regulatory mandate. This project
  has none of those things and outputs must not be relied upon for evacuation
  decisions.
- **Not a substitute for engineering inspection.** Geotechnical site
  investigation, piezometer monitoring, and qualified-engineer-of-record
  sign-off remain the standard of care. Our model uses only public proxies
  for those signals.
- **Not a per-dam liability instrument.** The model produces probabilities
  with uncertainty. Mapping those to individual-dam decisions requires
  decision-curve analysis with local cost structure that we do not have.

## Disclosure posture

- Model outputs at the individual-dam level will be released with explicit
  uncertainty bounds and a written explanation of what they do and do not
  mean.
- If results are shared with regulators (ANM, MPMG) or operators in advance
  of public release, that engagement is documented.
- We will not produce a public dashboard that ranks named operators by risk
  score without first sharing the methodology and giving an opportunity to
  respond to the operators concerned. This is a *responsible disclosure*
  norm, not a legal requirement.

## Limitations to declare in any published artefact

- **Censoring.** Most dams have not failed. The model is trained on a
  highly imbalanced and right-censored target. The reported metrics reflect
  this.
- **Selection.** Failures pre-Sentinel-1 (before 2014–2015) have no equivalent
  precursor data. The training cohort is therefore biased toward failures
  with InSAR coverage. We will not claim generalisation to pre-radar regimes.
- **Survivor bias.** Dams that show precursors and were subsequently
  remediated are coded as non-failures. This conservatively biases the
  precursor → failure mapping toward zero.
- **Label provenance.** WMTF severity coding is one analyst's judgement.
  Sensitivity analyses report results at multiple severity cutoffs.
- **Open-data only.** We deliberately exclude operator-internal monitoring
  signals (piezometers, inclinometers). The result is a conservative
  open-data lower bound on what is predictively possible; with proprietary
  data, higher discrimination is plausible. We do not claim otherwise.

## Use of model outputs in this repository

- Any plot or table naming individual dams must cite the underlying data
  sources and link to this document for context.
- Any prospective forecast (i.e., a forecast for a still-active dam) must
  be accompanied by a calibration plot for the relevant temporal split.

## Authorship and review

The project is conducted in an academic / research-software register. Before
any external-facing publication (preprint, conference, regulator briefing),
the authors should solicit:

1. an InSAR-processing review from a geodesist;
2. a geotechnical-engineering review of construction-type assumptions;
3. a statistics / ML review of calibration and conformal claims.

These reviews should be acknowledged in the manuscript.
