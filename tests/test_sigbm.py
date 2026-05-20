"""Tests for SIGBM loader + fixture generator + cohort builder.

These exercise the actual end-to-end path used by experiment 00, so a regression
in any of: schema canonicalisation, fixture marginals, or label join surfaces here.
"""
from __future__ import annotations

from sentinela.features.build import FeatureTableSpec, build_cohort_panel
from sentinela.io import fixtures
from sentinela.io.sigbm import CANONICAL_COLUMNS, CONSTRUCTION_METHODS, _canonicalise


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


def test_canonicalise_renames_portuguese_columns():
    import pandas as pd
    src = pd.DataFrame({
        "id_barragem": ["X1"],
        "nome_barragem": ["Test"],
        "latitude": [-20.0],
        "longitude": [-44.0],
        "metodo_construtivo": ["Alteamento a montante"],
        "altura_atual_m": [50.0],
        "volume_atual_m3": [1e6],
        "minerio_principal": ["ferro"],
        "uf": ["MG"],
        "nome_municipio": ["Brumadinho"],
        "cri_atual": [2],
        "dpa_atual": [3],
        "nivel_emergencia": [0],
        "cnpj_empreendedor": ["33.592.510/0001-54"],
        "nome_empreendedor": ["Vale S.A."],
    })
    out = _canonicalise(src)
    assert out.iloc[0]["construction_method"] == "upstream"
    assert out.iloc[0]["operator_cnpj"] == "33592510000154"  # zero-padded, digits-only
    assert list(out.columns) == list(CANONICAL_COLUMNS)


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
