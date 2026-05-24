#!/usr/bin/env bash
# Convert the Sentinela manuscript to a standalone, editable LaTeX source and
# compile it to PDF with xelatex.
#
# Output:
#   paper/manuscript.tex   editable LaTeX source (regenerated each run)
#   paper/manuscript.pdf   compiled PDF
#
# The markdown (manuscript.md) remains the authoring source. Run this whenever
# the markdown changes. If you prefer to hand-edit the .tex directly, stop
# running this script and edit manuscript.tex + recompile with xelatex.
set -euo pipefail

PAPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$PAPER_DIR/.." && pwd)"
BUILD="$PAPER_DIR/_build_manuscript.md"
TEX="$PAPER_DIR/manuscript.tex"

# --- assemble build copy ---
# Drop the entire YAML frontmatter so pandoc does NOT emit its own
# \maketitle (we supply a custom title page via --include-before-body).
awk '
  BEGIN {infm=0; seen=0}
  NR==1 && $0=="---" {infm=1; seen=1; next}
  infm && $0=="---" {infm=0; next}
  infm {next}
  {print}
' "$PAPER_DIR/manuscript.md" > "$BUILD"

{
  echo ""
  echo "# Appendix A — Figures"
  echo ""
  for f in fig1_cohort_composition fig2_posterior_rates fig3_top_risk_ranking \
           fig4_terrain_3d fig5_retrospectives fig6_insar_comparison; do
    [ -f "$REPO/figures/$f.png" ] && { echo "![]($REPO/figures/$f.png)"; echo ""; }
  done
  echo "# Appendix B — Tables"
  echo ""
  cat "$PAPER_DIR/tables/tables.md"
} >> "$BUILD"

# Resolve GitHub-relative hero image path to absolute for the build.
python3 - "$BUILD" "$REPO" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); repo = sys.argv[2]
t = p.read_text().replace("](../figures/", f"]({repo}/figures/")
p.write_text(t)
PY

echo "==> pandoc: markdown -> standalone LaTeX"
pandoc "$BUILD" \
  --standalone \
  --from=markdown+tex_math_dollars+pipe_tables \
  --to=latex \
  --include-in-header="$PAPER_DIR/preamble.tex" \
  --include-before-body="$PAPER_DIR/titlepage.tex" \
  --toc --toc-depth=2 \
  -V documentclass=article \
  -V classoption=11pt \
  -V geometry:margin=1in \
  -V colorlinks=true \
  -V linkcolor=RoyalBlue \
  -V urlcolor=RoyalBlue \
  -V title-meta="Forecasting Brazil's Next Tailings-Dam Disaster" \
  -o "$TEX"

echo "==> xelatex (pass 1/2)"
( cd "$PAPER_DIR" && xelatex -interaction=nonstopmode -halt-on-error manuscript.tex >/tmp/sentinela_tex.log 2>&1 ) || {
  echo "xelatex failed; tail of log:" >&2; tail -25 /tmp/sentinela_tex.log >&2; exit 1; }
echo "==> xelatex (pass 2/2, resolving refs + toc)"
( cd "$PAPER_DIR" && xelatex -interaction=nonstopmode -halt-on-error manuscript.tex >/tmp/sentinela_tex.log 2>&1 )

# Clean aux files.
( cd "$PAPER_DIR" && rm -f manuscript.aux manuscript.log manuscript.out manuscript.toc )
rm -f "$BUILD"
echo "==> wrote $TEX and $PAPER_DIR/manuscript.pdf ($(du -h "$PAPER_DIR/manuscript.pdf" | cut -f1))"
