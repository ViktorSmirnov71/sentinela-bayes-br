# Research questions

Pre-registered, falsifiable hypotheses. Each is paired with the experiment
that tests it. The point of writing these *before* running anything is to
make negative results publishable and to avoid post-hoc storytelling.

---

## RQ1 — Does open InSAR signal contribute beyond static+climate features?

**Hypothesis H1.** Adding the InSAR feature block $x^{\text{insar}}$ to a
model already containing $x^{\text{static}}$ and $x^{\text{climate}}$ improves
12-month-prior AUROC on held-out failures by at least 0.05.

**Null.** AUROC gain $\le 0.01$.

**Why it matters.** The literature (Grebby, Carlà) shows the signal exists
at known failures. RQ1 asks whether it generalises across the active cohort.

**Experiment.** `experiments/01_insar_ablation/`.

---

## RQ2 — Does a foundation tabular model improve calibration over GBMs at this cohort size?

**Hypothesis H2.** TabPFN-3 achieves lower Expected Calibration Error than
a tuned LightGBM with isotonic regression on the same features and splits.

**Null.** ECE difference within 0.005 in either direction.

**Why it matters.** TabPFN's claimed advantage is calibrated small-data
inference. Tailings-dam forecasting is precisely small-data, high-stakes,
calibration-sensitive.

**Experiment.** `experiments/02_tabpfn_vs_gbm/`.

---

## RQ3 — Does construction-method stratification beat a pooled model?

**Hypothesis H3.** A multitask architecture with per-construction-method
heads (upstream / downstream / centerline) outperforms a pooled single-head
model on the upstream subset by at least 0.03 AUROC.

**Null.** Difference $\le 0.01$.

**Why it matters.** Upstream-method TSFs failed at disproportionate rates
(Brumadinho B1, Fundão both upstream). If their failure physics is genuinely
distinct, the model architecture should reflect it.

**Experiment.** `experiments/03_construction_multitask/`.

---

## RQ4 — Does the model rank the two reference failures in the top decile of risk 12 months prior?

**Hypothesis H4.** With Fundão (2015-11) and B1 (2019-01) held out of
training, the primary model assigns each a 12-month-prior failure probability
in the top decile of then-active dams.

**Null.** Either dam is outside the top decile.

**Why it matters.** This is the headline qualitative claim of the project.
It is binary and unambiguous; the protocol is pre-registered.

**Experiment.** `experiments/04_retrospective_reference_failures/`.

---

## RQ5 — Does the regulator-issued ANM CRI add information beyond engineering + InSAR features?

**Hypothesis H5.** Adding the ANM CRI ordinal as a feature to a model that
already has the underlying engineering and InSAR signals improves AUROC by
$\le 0.01$. (I.e., CRI is a summary of features the model already sees.)

**Null.** CRI adds AUROC > 0.03 (in which case CRI encodes information
not in the public features and should be sought as a separate input).

**Why it matters.** Probes whether the regulator's administrative score is
informationally redundant once the data is openly modelled. Has policy
implications either way.

**Experiment.** `experiments/05_regulator_score_ablation/`.

---

## RQ6 — Is there an unforeseen correlation between operator identity and post-engineering residual risk?

**Hypothesis H6 (exploratory).** After controlling for construction method,
height, volume, age, and ore type, operator identity (encoded as a random
effect in the Bayesian reference model of §4.5) explains a non-trivial
fraction of failure-event variance (residual operator-level $\sigma^2 > 0.1$
on the logit scale, with 95% posterior CI excluding zero).

**Null.** $\sigma^2 \le 0.05$.

**Why it matters.** A positive finding suggests that some operators carry
residual risk beyond the engineering profile of their dams — a result with
clear policy and investor-disclosure relevance, and a candidate "unforeseen
cross-domain correlation" the project explicitly seeks.

**Experiment.** `experiments/06_operator_random_effects/`.

---

## RQ7 — Does antecedent rainfall modulate the InSAR-precursor → failure mapping?

**Hypothesis H7.** The marginal effect of an elevated InSAR-precursor signal
on near-term failure probability is larger when SPI-3 indicates a wet
trailing quarter. Operationalised as a significant InSAR × rainfall
interaction term in a logistic specification with $p < 0.01$ after
multiple-comparison correction.

**Null.** No interaction.

**Why it matters.** The Brumadinho post-hoc literature is split on whether
rainfall played a causal role (Grebby et al. rule out overtopping but the
preceding rainy period coincided with accelerating deformation). A clean
test of the interaction at population scale would settle a live question.

**Experiment.** `experiments/07_rainfall_insar_interaction/`.

---

## Numbered registration

This document is the canonical pre-registration. Changes after first commit
must be appended with a dated diff at the bottom of this file, not
silently edited.
