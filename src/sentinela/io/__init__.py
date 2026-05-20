"""Data loaders.

One module per source. Each exposes:
    fetch(dest: Path) -> Path     # download/copy raw to data/raw
    load() -> pd.DataFrame        # canonicalised in-memory table
"""
