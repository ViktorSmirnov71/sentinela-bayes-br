"""Clean a raw ANM SIGBM CSV into a canonical-schema parquet.

This is a thin runnable wrapper around `sentinela.io.sigbm.load`. It exists in
`data/scripts/` so the data-cleaning pipeline is visible alongside the data
it produces, even though the actual parsing logic lives in the importable
package (`src/sentinela/io/sigbm.py`).

Usage
-----
    python data/scripts/clean_sigbm.py
        Default I/O: data/raw/sigbm/Relatorio_20260721.csv
                  -> data/processed/sigbm_canonical.parquet

    python data/scripts/clean_sigbm.py --input <path> --output <path>
        Override I/O paths.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sentinela.io.sigbm import load

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "data" / "raw" / "sigbm" / "Relatorio_20260721.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "sigbm_canonical.parquet"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    print(f"reading  {args.input.relative_to(REPO_ROOT)}")
    df = load(args.input)
    print(f"  rows:     {len(df):,}")
    print(f"  columns:  {list(df.columns)}")
    print(f"  states:   {df['state'].nunique()} distinct ({df['state'].value_counts().head(5).to_dict()} ...)")
    print(f"  methods:  {df['construction_method'].value_counts().to_dict()}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output)
    print(f"wrote    {args.output.relative_to(REPO_ROOT)}  ({args.output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
