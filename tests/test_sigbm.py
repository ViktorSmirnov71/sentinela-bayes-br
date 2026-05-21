"""Tests for SIGBM loader + fixture generator + cohort builder.

These exercise the actual end-to-end path used by experiment 00, so a regression
in any of: schema canonicalisation, fixture marginals, or label join surfaces here.
"""
from __future__ import annotations

from sentinela.features.build import FeatureTableSpec, build_cohort_panel
from sentinela.io import fixtures
from sentinela.io.sigbm import (
    CANONICAL_COLUMNS,
    CONSTRUCTION_METHODS,
    _dms_to_decimal,
    _emergency_from_anm,
    _method_from_anm,
    _ops_status_from_anm,
    _to_float_brazil,
)


def test_fixture_matches_canonical_schema():
    df = fixtures.make_fixture(n=10, seed=0)
    assert list(df.columns) == list(CANONICAL_COLUMNS)
    assert df["dam_id"].is_unique
    assert df["construction_method"].isin(CONSTRUCTION_METHODS).all()


def test_fixture_reference_dams_present():
    df = fixtures.make_fixture(n=10, seed=0)
    assert {"FIX-REF-FUNDAO", "FIX-REF-B1"}.issubset(set(df["dam_id"]))
    refs = df[df["dam_id"].isin({"FIX-REF-FUNDAO", "FIX-REF-B1"})]
    assert (refs["construction_method"] == "upstream").all()
    assert (refs["ore_type"] == "iron").all()
    assert (refs["state"] == "MG").all()


def test_dms_to_decimal():
    # From a real row in Relatorio_20260721.csv (Vale's Volta Grande 3).
    assert abs(_dms_to_decimal("-21°04'21.600\"") - (-21.07267)) < 1e-4
    # Northern-hemisphere example (Amapá dam Vila Nova).
    assert abs(_dms_to_decimal("00°24'06.026\"") - 0.40167) < 1e-4
    # Garbage in → NaN out.
    import math
    assert math.isnan(_dms_to_decimal("not a coord"))


def test_brazilian_decimal_parsing():
    assert _to_float_brazil("57.463.773,00") == 57463773.0
    assert _to_float_brazil("19,60") == 19.6
    assert _to_float_brazil("0,00") == 0.0
    import math
    assert math.isnan(_to_float_brazil("-"))


def test_method_from_anm_maps_real_labels():
    # All five distinct values present in the real export.
    assert _method_from_anm("10 - Alteamento a montante") == "upstream"
    assert _method_from_anm("2 - Alteamento a jusante") == "downstream"
    assert _method_from_anm("5 - Alteamento por linha de centro") == "centerline"
    assert _method_from_anm("0 - Etapa única") == "single_stage"
    assert _method_from_anm("Indefinido") == "unknown"
    assert _method_from_anm("10 - Desconhecido") == "unknown"


def test_ops_status_from_anm():
    assert _ops_status_from_anm("Ativa") == "active"
    assert _ops_status_from_anm("Inativa") == "inactive"
    assert _ops_status_from_anm("Em Construção") == "under_construction"
    assert _ops_status_from_anm("Em descaracterização (projeto/obras/monitoramento)") == "decommissioning"


def test_emergency_from_anm():
    assert _emergency_from_anm("Sem emergência") == 0
    assert _emergency_from_anm("Nível de Alerta") == 1
    assert _emergency_from_anm("Nível de Emergência 1") == 1
    assert _emergency_from_anm("Nível de Emergência 2") == 2
    assert _emergency_from_anm("Nível de Emergência 3") == 3


def test_real_anm_csv_loads_and_validates():
    """Full end-to-end load of the committed sample, if available."""
    from pathlib import Path

    from sentinela.io.sigbm import load

    p = Path(__file__).resolve().parents[1] / "data" / "raw" / "sigbm" / "Relatorio_20260721.csv"
    if not p.exists():
        import pytest
        pytest.skip("real SIGBM CSV not present in this checkout")
    df = load(p)
    assert len(df) > 800              # ANM publishes ~900 dams
    assert df["dam_id"].is_unique
    assert df["construction_method"].isin(CONSTRUCTION_METHODS).all()
    assert df["cri"].between(0, 3).all()
    assert df["lat"].between(-35, 6).all()    # Brazil's latitude span
    assert df["lon"].between(-75, -30).all()


def test_cohort_panel_attaches_positive_labels_for_reference_failure():
    """With B1 (2019-01-25) in the failure table and the FIX-REF-B1 dam in the
    cohort, the 12 months ending at the failure month (2018-02 through 2019-01)
    should be labelled y=1. That is: y_t = 1 iff failure occurs in [t, t+12).
    """
    from pathlib import Path

    from sentinela.io.wmtf import load_brazilian_failures

    repo_root = Path(__file__).resolve().parents[1]
    failures = load_brazilian_failures(repo_root / "data" / "external" / "brazilian_failures.csv")

    sigbm = fixtures.make_fixture(n=20, seed=0)
    spec = FeatureTableSpec(start_month="2018-01", end_month="2025-12",
                            horizon_months=12, severity_min=4)
    panel = build_cohort_panel(sigbm, failures, spec)

    b1 = panel[panel["dam_id"] == "FIX-REF-B1"]
    positives = b1[b1["y"] == 1]
    months = sorted(p.strftime("%Y-%m") for p in positives["month"].astype("period[M]").dt.to_timestamp())
    expected = [f"2018-{m:02d}" for m in range(2, 13)] + ["2019-01"]
    assert months == expected, f"expected 2018-02..2019-01 positives for B1, got {months}"


def test_cohort_panel_zero_label_far_from_failure():
    from pathlib import Path

    from sentinela.io.wmtf import load_brazilian_failures

    repo_root = Path(__file__).resolve().parents[1]
    failures = load_brazilian_failures(repo_root / "data" / "external" / "brazilian_failures.csv")
    sigbm = fixtures.make_fixture(n=20, seed=0)
    spec = FeatureTableSpec(start_month="2018-01", end_month="2025-12",
                            horizon_months=12, severity_min=4)
    panel = build_cohort_panel(sigbm, failures, spec)

    # A non-reference dam should have zero positives across all months.
    arbitrary = panel[panel["dam_id"] == "FIX-0001"]
    assert arbitrary["y"].sum() == 0


def test_cohort_panel_censoring_weight_zero_near_panel_end():
    from pathlib import Path

    from sentinela.io.wmtf import load_brazilian_failures

    repo_root = Path(__file__).resolve().parents[1]
    failures = load_brazilian_failures(repo_root / "data" / "external" / "brazilian_failures.csv")
    sigbm = fixtures.make_fixture(n=10, seed=0)
    spec = FeatureTableSpec(start_month="2018-01", end_month="2025-12",
                            horizon_months=12, severity_min=4)
    panel = build_cohort_panel(sigbm, failures, spec)

    last_month = panel["month"].max()
    last_rows = panel[panel["month"] == last_month]
    assert (last_rows["censored_weight"] == 0.0).all()
    assert (last_rows["in_horizon"] == False).all()  # noqa: E712
