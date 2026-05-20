"""Single entry point exposing project commands.

Usage:
    sentinela pull sigbm
    sentinela pull wmtf
    sentinela run experiments/01_insar_ablation/config.yaml
"""
from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True, help="Sentinela command-line interface.")


@app.command()
def version() -> None:
    """Print the package version."""
    from . import __version__
    typer.echo(__version__)


@app.command()
def pull(source: str) -> None:
    """Download a named data source into data/raw/.

    SOURCE is one of: sigbm, wmtf, gtp, brazildam, chirps, era5, ibge.
    """
    raise NotImplementedError(f"Loader for {source!r} not yet implemented.")


@app.command()
def run(config_path: str) -> None:
    """Run the experiment described by CONFIG_PATH."""
    raise NotImplementedError("Experiment runner not yet implemented.")


if __name__ == "__main__":
    app()
