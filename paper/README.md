# paper/

The Sentinela research paper: *Forecasting Brazil's Next Tailings-Dam
Disaster*.

## Files

| file | role |
|---|---|
| `manuscript.md`   | authoring source (Markdown, full IMRaD). Renders on GitHub. |
| `manuscript.tex`  | generated standalone LaTeX source (editable). |
| `manuscript.pdf`  | compiled paper (20 pages, hero figure + 6 figures + 5 tables). |
| `preamble.tex`    | LaTeX preamble: fonts, booktabs, titlesec, hyperref, headers. |
| `make_figures.py` | regenerates the figure set into `../figures/`. |
| `make_tables.py`  | regenerates the tables into `tables/`. |
| `build_latex.sh`  | **primary build**: Markdown → standalone LaTeX → PDF (xelatex). |
| `build_pdf.sh`    | legacy direct Markdown → PDF (pandoc default template). |
| `tables/`         | five publication tables as CSV + `tables.md`. |

## Build (LaTeX path — recommended)

```bash
python paper/make_figures.py     # (re)generate figures
python paper/make_tables.py      # (re)generate tables
bash   paper/build_latex.sh      # md -> manuscript.tex -> manuscript.pdf
```

`build_latex.sh` converts `manuscript.md` to a **standalone, editable**
`manuscript.tex` (via pandoc, with `preamble.tex` injected), then compiles
it twice with xelatex to resolve the table of contents and references.

### Editing in LaTeX directly

`manuscript.tex` is a complete LaTeX document. If you want to leave the
Markdown workflow and format by hand in LaTeX:

1. Run `build_latex.sh` once to generate `manuscript.tex`.
2. Stop running the script (it would overwrite your edits).
3. Edit `manuscript.tex` and `preamble.tex` directly; recompile with
   `cd paper && xelatex manuscript.tex` (twice).

Formatting knobs live in `preamble.tex` — switch `\setmainfont`, change
`titlesec` section styling, or add `\twocolumn` to the documentclass
options in `build_latex.sh` for a two-column journal layout (note: the
wide hero figure and the top-15 table then need `figure*` / `table*`).

## Requirements

- `pandoc` (`brew install pandoc`)
- a TeX distribution with `xelatex` (MacTeX / TeX Live) and the
  TeX Gyre fonts (bundled with TeX Live)

## What this manuscript IS / IS NOT

A pre-print documenting the methodology, the 2026-snapshot results, the
two retrospective experiments, and the honest limitations. **Not** a
finalised journal submission, and **not** a regulatory or operational
document — see `../docs/06-ethics-and-limitations.md`.
