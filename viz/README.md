# viz/ — Sentinela 3D ghost map

A self-contained Three.js visualisation of the Sentinela hierarchical-model
output over the Brazilian mining-dam cohort. Renders all 877 geocoded active
dams as glowing pillars sited at their WGS84 coordinates over a simplified
Brazil silhouette, with pillar height proportional to the model's predicted
12-month failure probability.

## What you see

- A dark, atmospheric scene. Brazil drawn as a cyan ribbon at ground level.
- 877 pillars, coloured along a cyan → violet → magenta ramp by risk decile.
- The 30 highest-risk dams pulse with a stronger glow.
- Dams in declared Emergency Level ≥ 1 get a yellow halo on the ground.
- A floating particle field gives the "ghost dust" texture.

## How to launch

```bash
cd ~/Desktop/sentinela-bayes-br/viz
python3 -m http.server 8765   # any static server is fine
open http://localhost:8765
```

(You cannot open `index.html` directly via `file://` because the JS imports
JSON via fetch, which most browsers block from file URLs.)

## Interaction

| input | action |
|---|---|
| left-click drag | orbit camera |
| right-click drag | pan |
| scroll | zoom |
| hover a pillar | inspect: name, operator, state, method, CRI/DPA, predicted risk |

## How the data is produced

1. The hierarchical model is fit by `experiments/01_first_prediction/run.py`
   and writes per-(dam, month) probabilities to
   `results/01_first_prediction/predictions.parquet`.
2. `data/scripts/export_viz_data.py` selects the latest snapshot month,
   joins on SIGBM canonical metadata, filters to geocoded dams within
   Brazil's bbox, and writes the JSON consumed by this visualisation.

Re-running the script after a fresh model run regenerates `data/dams.json`
in place; reload the browser to see the updated risk field.

## What the visualisation IS

- A research-grade visual reading of the Bayesian-prior model's output.
- A way to inspect geographic risk patterns at a glance.
- A figure to include in the manuscript at `paper/manuscript.md`.

## What the visualisation IS NOT

- An operational decision tool — see `docs/06-ethics-and-limitations.md`.
- A regulator-issued ranking. Pillar heights reflect a research model
  trained on a single linked failure event with literature-informed priors.
- A confidence statement about individual dams. The model carries
  uncertainty that is not currently rendered visually (a future iteration
  could encode posterior 90% intervals as faded outer pillars).

## Files

```
viz/
├── README.md          (this file)
├── index.html         page shell, overlay/legend/stats
├── js/main.js         Three.js scene, animation loop, raycasting
└── data/
    ├── dams.json              per-dam risk + metadata (generated)
    ├── summary.json           cohort summary stats     (generated)
    └── brazil_outline.json    simplified country outline (committed)
```
