"""SIGBM loader — ANM mining-dam registry.

Real-data access
----------------
A. Base dos Dados (recommended once GCP billing project is configured)
   Requires env var BD_BILLING_PROJECT pointing at a Google Cloud project with
   BigQuery enabled. Then:
       SELECT * FROM `basedosdados.br_anm_sigbm.barragens`

B. Manual export from the ANM public web app (default route)
   https://app.anm.gov.br/sigbm/publico  ->  *Data Extraction*  ->  CSV.
   The exported file is named `Relatorio_<YYYYMMDD>.csv`. Place it under
   `data/raw/sigbm/`.

The exported CSV is:
- Semicolon-delimited.
- UTF-8 with BOM.
- CRLF line endings.
- Brazilian decimal format (comma as decimal separator, dot as thousands
  separator). `_to_float_brazil` handles both safely.
- Lat / lon in degrees-minutes-seconds with a directional sign on the prefix
  (e.g. `-20°09'58.822"`). `_dms_to_decimal` parses these to decimal degrees.

Canonical schema (output of `load`)
-----------------------------------
    dam_id              str    SIGBM identifier
    name                str    Facility name
    operator_cnpj       str    Operator tax ID (zero-padded 14-char string;
                               blank for individuals with hidden CPF)
    operator_name       str
    lat, lon            float  WGS84 decimal degrees
    state               str    UF (two-letter Brazilian state code)
    municipality        str
    construction_method str    Categorical: upstream / downstream / centerline /
                               single_stage / dyke / unknown
    height_m            float  Current crest height
    volume_m3           float  Current impounded volume
    age_years           float  Years since first impoundment (NaN if unknown)
    cri                 int    Risk Category, 1=Baixo, 2=Medio, 3=Alto
    dpa                 int    Damage Potential, 1=Baixo, 2=Medio, 3=Alto
    ore_type            str    Primary ore (normalised to a short English label)
    status_active       bool   True iff operational status is "Ativa"
    ops_status          str    Granular: active / inactive / under_construction /
                               decommissioning / unknown
    emergency_level     int    0 = none / alert, 1-3 = SIGBM Niveis 1-3
    pnsb_included       bool   Whether the dam is in the PNSB (federal scope)
    snapshot_date       date   File-export date parsed from the filename if
                               available, otherwise today
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime
from pathlib import Path

import numpy as np
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
    "ops_status",
    "emergency_level",
    "pnsb_included",
    "snapshot_date",
)

CONSTRUCTION_METHODS: tuple[str, ...] = (
    "upstream",
    "downstream",
    "centerline",
    "single_stage",
    "dyke",
    "unknown",
)

OPS_STATUSES: tuple[str, ...] = (
    "active",
    "inactive",
    "under_construction",
    "decommissioning",
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
    """Load a SIGBM table (real ANM CSV export or canonical fixture/parquet).

    Auto-detects the real ANM format by header presence and applies the full
    semicolon / Brazilian-decimal / DMS-coordinate parsing pipeline.
    """
    p = Path(path)
    if p.suffix == ".parquet":
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p, sep=None, engine="python", encoding="utf-8-sig")

    is_real_anm = "Codigo" in df.columns
    if is_real_anm:
        df = _parse_real_anm(df, snapshot_from_filename(p))
    else:
        df = _canonicalise_fixture(df)

    _validate(df)
    return df


def snapshot_from_filename(p: Path) -> date:
    """Parse the YYYYMMDD in `Relatorio_YYYYMMDD.csv`; fall back to today."""
    m = re.search(r"(20\d{6})", p.name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError:
            pass
    return date.today()


# ---------------------------------------------------------------------------
# Real ANM CSV parsing
# ---------------------------------------------------------------------------

_ANM_RENAME = {
    "Codigo": "dam_id",
    "NomeBarragem": "name",
    "NomeEmpreendedor": "operator_name",
    "CpfCnpjFormatado": "operator_cnpj",
    "LatitudeFormatada": "_lat_dms",
    "LongitudeFormatada": "_lon_dms",
    "Municipio": "municipality",
    "UF": "state",
    "Minerio": "_ore_raw",
    "Altura": "_height_raw",
    "VolumeAtualFormatado": "_volume_raw",
    "MetodoConstrutivoFormatado": "_method_raw",
    "CategoriaRisco": "_cri_raw",
    "DanoPotencial": "_dpa_raw",
    "InseridaPNSBFormatada": "_pnsb_raw",
    "SituacaoNivelEmergencial": "_emergency_raw",
    "SituacaoOperacionalFormatado": "_ops_raw",
}

_ORDINAL_PT = {"baixo": 1, "médio": 2, "medio": 2, "alto": 3}


def _parse_real_anm(df: pd.DataFrame, snapshot: date) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in _ANM_RENAME.items() if k in df.columns})

    df["dam_id"] = df["dam_id"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["operator_name"] = df["operator_name"].astype(str).str.strip()
    df["operator_cnpj"] = df["operator_cnpj"].astype(str).apply(_clean_cnpj)

    df["lat"] = df["_lat_dms"].apply(_dms_to_decimal)
    df["lon"] = df["_lon_dms"].apply(_dms_to_decimal)

    df["height_m"] = df["_height_raw"].apply(_to_float_brazil)
    df["volume_m3"] = df["_volume_raw"].apply(_to_float_brazil)

    df["construction_method"] = df["_method_raw"].astype(str).apply(_method_from_anm)
    df["cri"] = df["_cri_raw"].astype(str).str.lower().str.strip().map(_ORDINAL_PT).fillna(0).astype(int)
    df["dpa"] = df["_dpa_raw"].astype(str).str.lower().str.strip().map(_ORDINAL_PT).fillna(0).astype(int)
    df["ore_type"] = df["_ore_raw"].astype(str).apply(_ore_norm)

    df["ops_status"] = df["_ops_raw"].astype(str).apply(_ops_status_from_anm)
    df["status_active"] = df["ops_status"] == "active"
    df["emergency_level"] = df["_emergency_raw"].astype(str).apply(_emergency_from_anm)
    df["pnsb_included"] = df["_pnsb_raw"].astype(str).str.strip().str.lower().eq("sim")

    df["age_years"] = np.nan  # not present in the public export
    df["snapshot_date"] = snapshot

    return df[list(CANONICAL_COLUMNS)]


# ---------------------------------------------------------------------------
# Fixture / parquet fallback path (small, kept for tests + fixture pipeline)
# ---------------------------------------------------------------------------

def _canonicalise_fixture(df: pd.DataFrame) -> pd.DataFrame:
    """Light path for the canonical-schema fixture CSV produced by fixtures.py."""
    if "snapshot_date" in df.columns:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.date
    else:
        df["snapshot_date"] = date.today()

    if "construction_method" in df.columns:
        df["construction_method"] = df["construction_method"].astype(str).str.lower().where(
            df["construction_method"].astype(str).str.lower().isin(CONSTRUCTION_METHODS),
            "unknown",
        )

    if "operator_cnpj" in df.columns:
        df["operator_cnpj"] = df["operator_cnpj"].astype(str).apply(_clean_cnpj)

    if "ops_status" not in df.columns:
        df["ops_status"] = np.where(df.get("status_active", True), "active", "inactive")
    if "pnsb_included" not in df.columns:
        df["pnsb_included"] = False

    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[list(CANONICAL_COLUMNS)]


# ---------------------------------------------------------------------------
# Cell-level parsers
# ---------------------------------------------------------------------------

_DMS_RE = re.compile(
    r"""^\s*(?P<sign>-?)\s*
        (?P<deg>\d+)\s*°\s*
        (?P<min>\d+)\s*'\s*
        (?P<sec>\d+(?:[.,]\d+)?)\s*"\s*$""",
    re.VERBOSE,
)


def _dms_to_decimal(value) -> float:
    """Parse strings like `-20°09'58.822"` to decimal degrees. NaN if unparseable."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    s = str(value).strip().replace(",", ".")
    m = _DMS_RE.match(s)
    if not m:
        return float("nan")
    deg = float(m.group("deg"))
    minutes = float(m.group("min"))
    sec = float(m.group("sec"))
    dec = deg + minutes / 60 + sec / 3600
    return -dec if m.group("sign") == "-" else dec


def _to_float_brazil(value) -> float:
    """Parse '57.463.773,00' or '19,60' to float. NaN if unparseable."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    s = str(value).strip()
    if not s or s in {"-", "N/A", "nan"}:
        return float("nan")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _clean_cnpj(value) -> str:
    """Strip CNPJ formatting; preserve blanks (individuals have masked CPF '***')."""
    if value is None:
        return ""
    s = str(value).strip()
    if s in {"", "***", "nan"}:
        return ""
    digits = re.sub(r"\D", "", s)
    return digits.zfill(14) if digits else ""


def _method_from_anm(value: str) -> str:
    v = str(value).strip().lower()
    if "montante" in v:
        return "upstream"
    if "jusante" in v:
        return "downstream"
    if "linha de centro" in v:
        return "centerline"
    if "etapa única" in v or "etapa unica" in v:
        return "single_stage"
    if "dique" in v:
        return "dyke"
    return "unknown"


def _ore_norm(value: str) -> str:
    v = str(value).strip().lower()
    if not v or v in {"nan", "-", "n/a"}:
        return "unknown"
    if "ferro" in v:
        return "iron"
    if "ouro" in v:
        return "gold"
    if "cobre" in v:
        return "copper"
    if "bauxita" in v:
        return "bauxite"
    if "estanho" in v:
        return "tin"
    if "mangan" in v:
        return "manganese"
    if "nique" in v:
        return "nickel"
    if "fosfato" in v or "fósforo" in v or "fosforo" in v:
        return "phosphate"
    if "niob" in v:
        return "niobium"
    if "zinco" in v:
        return "zinc"
    if "areia" in v:
        return "sand"
    if "argila" in v or "caulim" in v:
        return "clay"
    return "other"


def _ops_status_from_anm(value: str) -> str:
    v = str(value).strip().lower()
    if "constru" in v:
        return "under_construction"
    if "descaracteriz" in v:
        return "decommissioning"
    if v == "ativa":
        return "active"
    if v == "inativa":
        return "inactive"
    return "unknown"


def _emergency_from_anm(value: str) -> int:
    v = str(value).strip().lower()
    if "emergência 3" in v or "emergencia 3" in v:
        return 3
    if "emergência 2" in v or "emergencia 2" in v:
        return 2
    if "emergência 1" in v or "emergencia 1" in v or "alerta" in v:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

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
    bad_ops = set(df["ops_status"].dropna().unique()) - set(OPS_STATUSES)
    if bad_ops:
        raise ValueError(f"Unknown ops_status values: {bad_ops}")
