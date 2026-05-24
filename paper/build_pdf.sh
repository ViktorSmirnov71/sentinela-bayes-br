#!/usr/bin/env bash
# Build the Sentinela manuscript to PDF with figures and tables appended.
#
# Assembles a build copy of manuscript.md, appends an image gallery of every
# figure and the markdown tables, then runs pandoc -> xelatex.
set -euo pipefail

PAPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$PAPER_DIR/.." && pwd)"
BUILD="$PAPER_DIR/_build_manuscript.md"
OUT="$PAPER_DIR/manuscript.pdf"

# Strip the `keywords:` block from the YAML frontmatter — pandoc emits XMP
# metadata (\xmpquote) for it that the default xelatex template can't compile.
# We drop the keywords key and its list item line.
awk '
  /^keywords:/ {skip=1; next}
  skip && /^  - / {skip=0; next}
  {skip=0; print}
' "$PAPER_DIR/manuscript.md" > "$BUILD"

# --- append the figure gallery (only the fig*.png publication figures) ---
{
  echo ""
  echo "\\newpage"
  echo ""
  echo "# Appendix A — Figures"
  echo ""
  for f in fig1_cohort_composition fig2_posterior_rates fig3_top_risk_ranking \
           fig4_terrain_3d fig5_retrospectives fig6_insar_comparison; do
    if [ -f "$REPO/figures/$f.png" ]; then
      echo "![]($REPO/figures/$f.png){ width=95% }"
      echo ""
    fi
  done
  echo "\\newpage"
  echo ""
  echo "# Appendix B — Tables"
  echo ""
  cat "$PAPER_DIR/tables/tables.md"
} >> "$BUILD"

# Latin Modern (xelatex default) lacks a few Unicode math glyphs in TEXT mode.
# Wrap them in math mode in the build copy so the math font renders them.
# manuscript.md keeps the nice Unicode for GitHub rendering.
python3 - "$BUILD" "$REPO" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); repo = sys.argv[2]; t = p.read_text()
# Resolve GitHub-relative image paths to absolute for the pandoc build.
t = t.replace("](../figures/", f"]({repo}/figures/")
for u, m in [("≥", r"$\geq$"), ("≤", r"$\leq$"), ("≈", r"$\approx$"),
             ("α", r"$\alpha$"), ("σ", r"$\sigma$"), ("²", r"$^2$")]:
    t = t.replace(u, m)
p.write_text(t)
PY

echo "==> running pandoc + xelatex"
pandoc "$BUILD" \
  --from=markdown+tex_math_dollars \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=10pt \
  -V colorlinks=true \
  -V linkcolor=blue \
  -V documentclass=article \
  --toc --toc-depth=2 \
  -o "$OUT" 2>&1 | tail -20 || {
    echo "xelatex build hit an error; retrying without --toc and with simpler opts" >&2
    pandoc "$BUILD" --pdf-engine=xelatex -V geometry:margin=1in -o "$OUT"
  }

rm -f "$BUILD"
echo "==> wrote $OUT ($(du -h "$OUT" | cut -f1))"
