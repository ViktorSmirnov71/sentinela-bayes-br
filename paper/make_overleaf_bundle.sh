#!/usr/bin/env bash
# Build a self-contained Overleaf-ready zip of the paper.
#
# Produces paper/sentinela_overleaf.zip containing:
#   main.tex            the standalone manuscript (figure paths -> figures/)
#   figures/*.png       every figure the .tex references
#
# Drag the zip into overleaf.com (New Project -> Upload Project), set the
# compiler to XeLaTeX (Menu -> Compiler -> XeLaTeX — required, we use
# fontspec), and it compiles in the browser with live preview.
set -euo pipefail

PAPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$PAPER_DIR/.." && pwd)"
STAGE="$(mktemp -d)"
ZIP="$PAPER_DIR/sentinela_overleaf.zip"

# Regenerate the standalone .tex to be sure it's current.
bash "$PAPER_DIR/build_latex.sh" >/dev/null

mkdir -p "$STAGE/figures"

# Copy figures the manuscript references.
cp "$REPO/figures/fig0_hero.png" "$STAGE/figures/" 2>/dev/null || true
for f in fig1_cohort_composition fig2_posterior_rates fig3_top_risk_ranking \
         fig4_terrain_3d fig5_retrospectives fig6_insar_comparison; do
  cp "$REPO/figures/$f.png" "$STAGE/figures/" 2>/dev/null || true
done

# Rewrite absolute image paths in the .tex to the relative figures/ dir.
python3 - "$PAPER_DIR/manuscript.tex" "$REPO" "$STAGE/main.tex" <<'PY'
import sys, pathlib
src, repo, dst = sys.argv[1], sys.argv[2], sys.argv[3]
t = pathlib.Path(src).read_text()
t = t.replace(f"{repo}/figures/", "figures/")
t = t.replace("../figures/", "figures/")   # title-page hero path
pathlib.Path(dst).write_text(t)
PY

( cd "$STAGE" && zip -qr "$ZIP" main.tex figures )
rm -rf "$STAGE"
echo "==> wrote $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "    Upload to overleaf.com (New Project -> Upload Project),"
echo "    then set Menu -> Compiler -> XeLaTeX."
