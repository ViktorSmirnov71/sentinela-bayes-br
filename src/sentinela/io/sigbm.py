"""SIGBM loader — ANM mining-dam registry.

Two real-data access paths are documented below; both require a one-off step
the loader cannot fully automate. While that step is pending, a representative
synthetic fixture (data/external/sigbm_fixture.csv) lets the rest of the
pipeline run end-to-end against the canonical schema.

Access paths
------------
A. Base dos Dados (recommended once GCP billing project is configured)
   Requires env var BD_BILLING_PROJECT pointing at a Google Cloud project with
   BigQuery enabled. Then:
       SELECT * FROM `basedosdados.br_anm_sigbm.barragens`

B. Manual export from the ANM public web app
   https://app.anm.gov.br/sigbm/publico  ->  "Exportar" (CSV).
   Save the resulting file as data/raw/sigbm/Barragens_<YYYY-MM>.csv.

Canonical schema (output of `load`)
-----------------------------------
    dam_id              str    SIGBM identifier (or fixture-assigned ID)
    name                str    Facility name
    operator_cnpj       str    Operator tax ID (zero-padded 14-char string)
    operator_name       str
    lat, lon            float  WGS84 centroid
    state               str    UF (two-letter Brazilian state code)
    municipality        str
    construction_method str    Categorical: upstream / downstream / centerline /
                               dyke / unknown
    height_m            float
    volume_m3           float
    age_years           float  Years since first impoundment at snapshot date
    cri                 int    ANM Risk Category (CRI), 1=low - 3=high
    dpa                 int    Damage-Potential Category (DPA), 1=low - 3=high
    ore_type            str    Primary ore (iron, gold, copper, bauxite, etc.)
    status_active       bool   True if active at snapshot
    emergency_level     int    SIGBM Nivel de Emergencia (0, 1, 2, or 3)
    snapshot_date       date   Quarter-end of the snapshot
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

CANONICAL_COLUMNS: tuple[str, ...] = (
    "dam_id",
    "name",
    "operator_cnpj",
    "operator_name",
    "lat",
    "lon",
    "state",
    "municipality",
    "construction_method",
    "height_m",
    "volume_m3",
    "age_years",
    "cri",
    "dpa",
    "ore_type",
    "status_active",
    "emergency_level",
    "snapshot_date",
)

CONSTRUCTION_METHODS: tuple[str, ...] = (
    "upstream",
    "downstream",
    "centerline",
    "dyke",
    "unknown",
)


def fetch_basedosdados(dest: Path) -> Path:
    """Pull SIGBM via Base dos Dados (requires BD_BILLING_PROJECT)."""
    import os

    import basedosdados as bd

    project = os.environ.get("BD_BILLING_PROJECT")
    if not project:
        raise RuntimeError(
            "BD_BILLING_PROJECT environment variable not set. Either set it to a "
            "Google Cloud project with BigQuery enabled, or use the manual web-app "
            "export path documented at the top of this module."
        )
    df = bd.read_table(
        dataset_id="br_anm_sigbm",
        table_id="barragens",
        billing_project_id=project,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest)
    return dest


def load(path: Path | str) -> pd.DataFrame:
    """Load a SIGBM table (real or fixture) and coerce to the canonical schema."""
    p = Path(path)
    df = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)
    df = _canonicalise(df)
    _validate(df)
    return df


def _canonicalise(df: pd.DataFrame) -> pd.DataFrame:
    """Map known source-column names to canonical names; coerce types."""
    rename = {
        "id_barragem": "dam_id",
        "nome_barragem": "name",
        "cnpj_empreendedor": "operator_cnpj",
        "nome_empreendedor": "operator_name",
        "latitude": "lat",
        "longitude": "lon",
        "uf": "state",
        "nome_municipio": "municipality",
        "metodo_construtivo": "construction_method",
        "altura_atual_m": "height_m",
        "volume_atual_m3": "volume_m3",
        "minerio_principal": "ore_type",
        "cri_atual": "cri",
        "dpa_atual": "dpa",
        "nivel_emergencia": "emergency_level",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    if "construction_method" in df.columns:
        df["construction_method"] = (
            df["construction_method"]
            .astype(str)
            .str.lower()
            .map(_construction_method_norm)
            .fillna("unknown")
        )

    if "snapshot_date" in df.columns:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.date
    else:
        df["snapshot_date"] = date.today()

    if "status_active" in df.columns:
        df["status_active"] = df["status_active"].map(_truthy).astype(bool)
    elif "situacao" in df.columns:
        df["status_active"] = df["situacao"].astype(str).str.lower().str.contains("ativ")
    else:
        df["status_active"] = True

    if "operator_cnpj" in df.columns:
        df["operator_cnpj"] = (
            df["operator_cnpj"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(14)
        )

    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    return df[list(CANONICAL_COLUMNS)]


def _construction_method_norm(value: str) -> str | None:
    """Map Portuguese / English variants to the five canonical categories."""
    v = value.strip().lower()
    if "montante" in v or "upstream" in v:
        return "upstream"
    if "jusante" in v or "downstream" in v:
        return "downstream"
    if "linha de centro" in v or "centerline" in v or "centreline" in v:
        return "centerline"
    if "dique" in v or "dyke" in v or "dike" in v:
        return "dyke"
    if v in {"", "nan", "none", "null", "nao informado", "não informado"}:
        return "unknown"
    return None


def _truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "sim", "s", "ativa", "ativo"}


def _validate(df: pd.DataFrame) -> None:
    """Cheap schema checks; raise on contract violations."""
    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"SIGBM table missing canonical columns: {missing}")
    if df["dam_id"].is_unique is False and df["snapshot_date"].nunique() == 1:
        raise ValueError("dam_id must be unique within a single snapshot")
    bad_methods = set(df["construction_method"].dropna().unique()) - set(CONSTRUCTION_METHODS)
    if bad_methods:
        raise ValueError(f"Unknown construction_method values: {bad_methods}")
