# Experiments

Each experiment is a directory containing:

```
NN_short_name/
├── README.md      # hypothesis being tested (mapped to docs/05-research-questions.md)
├── config.yaml    # overrides on configs/default.yaml
└── run.py         # entry point; calls into src/tailings_risk/
```

Outputs are written to `../results/NN_short_name/`.

## Planned experiments (mirroring `docs/05-research-questions.md`)

| ID | Subject | RQ |
|----|---------|----|
| 01 | InSAR feature ablation                | RQ1 |
| 02 | TabPFN vs LightGBM calibration        | RQ2 |
| 03 | Multitask by construction method      | RQ3 |
| 04 | Retrospective Fundão & B1 forecast    | RQ4 |
| 05 | ANM CRI marginal information          | RQ5 |
| 06 | Operator random-effects (Bayesian)    | RQ6 |
| 07 | Rainfall × InSAR interaction          | RQ7 |

Experiments are added to this directory as they are scoped and started.
