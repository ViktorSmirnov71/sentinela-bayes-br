# paper/

Manuscript draft for the Sentinela research artefact.

## Files

- `manuscript.md` — full IMRaD manuscript. Reads as a standalone document
  and cites the BibTeX entries in `docs/refs.bib`.

## Build to PDF

```bash
# From the repo root:
pandoc paper/manuscript.md \
       --citeproc \
       --bibliography docs/refs.bib \
       --csl=https://www.zotero.org/styles/nature \
       --metadata link-citations=true \
       -o paper/manuscript.pdf
```

Requires `pandoc` (`brew install pandoc`). For arXiv-style LaTeX output:

```bash
pandoc paper/manuscript.md \
       --citeproc --bibliography docs/refs.bib \
       --pdf-engine=xelatex \
       -V geometry:margin=1in \
       -V mainfont="Charter" \
       -o paper/manuscript.pdf
```

## What this manuscript IS

A pre-print draft documenting the methodology, the snapshot results, the
honest limitations, and the in-progress workstreams (InSAR ingest, CHIRPS
rainfall, historical SIGBM recovery). The reproducibility section gives
the exact commands to regenerate every artefact cited in the paper.

## What this manuscript IS NOT

- A finalised submission. Several results blocks (InSAR ablation, RQ4
  retrospective, decision-curve analysis) are flagged as in progress and
  will land before any external publication.
- A regulatory or operational document. See
  `docs/06-ethics-and-limitations.md` for the disclosure posture.
