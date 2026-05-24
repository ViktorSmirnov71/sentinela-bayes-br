"""Generate publication tables for the Sentinela manuscript.

Writes both CSV (paper/tables/*.csv) and a single markdown bundle
(paper/tables/tables.md) for direct inclusion in the manuscript.

Tables
------
  T1  cohort summary by construction method
  T2  prior vs posterior failure rate
  T3  top-15 highest-risk dams
  T4  retrospective comparison (Fundão vs B1)
  T5  hierarchical-model structure / coefficients
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
PROC = REPO / "data" / "processed"
RES = REPO / "results"
OUT = REPO / "paper" / "tables"


def _md(df: pd.DataFrame, floatfmt: str = "{:.4g}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |",
             "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df.iterrows():
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append(floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sigbm = pd.read_parquet(PROC / "sigbm_canonical.parquet")
    md_chunks: list[str] = []

    # ---- T1: cohort summary by construction method ----
    g = sigbm.groupby("construction_method").agg(
        n_dams=("dam_id", "count"),
        mean_height_m=("height_m", "mean"),
        median_volume_m3=("volume_m3", "median"),
        n_high_cri=("cri", lambda s: int((s == 3).sum())),
        n_emergency=("emergency_level", lambda s: int((s >= 1).sum())),
    ).reset_index().sort_values("n_dams", ascending=False)
    g["mean_height_m"] = g["mean_height_m"].round(1)
    g.to_csv(OUT / "t1_cohort_by_method.csv", index=False)
    md_chunks.append("### Table 1 — Cohort summary by construction method\n\n" + _md(g))

    # ---- T2: prior vs posterior ----
    t2 = pd.DataFrame({
        "construction_method": ["upstream", "unknown", "centerline", "single_stage", "downstream"],
        "n_dam_months": [5940, 1056, 15180, 64152, 29436],
        "positives": [12, 0, 0, 0, 0],
        "prior_annual_pct": [0.50, 0.10, 0.10, 0.10, 0.05],
        "posterior_annual_pct": [0.389, 0.090, 0.040, 0.013, 0.013],
    })
    t2.to_csv(OUT / "t2_posterior_rates.csv", index=False)
    md_chunks.append("### Table 2 — Prior vs. posterior failure rate (Beta-Binomial, α=10,000)\n\n" + _md(t2))

    # ---- T3: top-15 ----
    top = pd.read_csv(RES / "01_first_prediction" / "top_risk_dams.csv").head(15)
    t3 = top[["dam_id", "name", "operator_name", "state", "construction_method",
              "height_m", "emergency_level", "risk_12m"]].copy()
    t3["risk_12m_pct"] = (t3["risk_12m"] * 100).round(3)
    t3 = t3.drop(columns=["risk_12m"])
    t3["operator_name"] = t3["operator_name"].str.slice(0, 28)
    t3["name"] = t3["name"].str.slice(0, 28)
    t3.to_csv(OUT / "t3_top15.csv", index=False)
    md_chunks.append("### Table 3 — Top-15 highest-risk active dams (2026 snapshot)\n\n" + _md(t3))

    # ---- T4: retrospective comparison ----
    fund = pd.read_csv(RES / "02_fundao_retrospective" / "trajectory.csv")
    b1 = pd.read_csv(RES / "03_b1_brumadinho_retrospective" / "trajectory.csv")
    t4 = pd.DataFrame({
        "event": ["Fundão (Samarco)", "Brumadinho B1 (Vale)"],
        "collapse_date": ["2015-11-05", "2019-01-25"],
        "insar_pairs": [int(fund["n_insar_obs"].max()), int(b1["n_insar_obs"].max())],
        "max_risk_pct": [round(fund["risk_12m"].max() * 100, 2), round(b1["risk_12m"].max() * 100, 2)],
        "collapse_month_risk_pct": [
            round(fund[fund["month"] == "2015-11"]["risk_12m"].iloc[0] * 100, 2),
            round(b1[b1["month"] == "2019-01"]["risk_12m"].iloc[0] * 100, 2),
        ],
        "peak_month": [
            fund.loc[fund["risk_12m"].idxmax(), "month"],
            b1.loc[b1["risk_12m"].idxmax(), "month"],
        ],
        "matches_grebby_window": ["n/a (Fundão not in Grebby)", "yes (peak in milestone-1)"],
    })
    t4.to_csv(OUT / "t4_retrospective.csv", index=False)
    md_chunks.append("### Table 4 — Retrospective comparison at the two reference failures\n\n" + _md(t4))

    # ---- T5: model structure ----
    t5 = pd.DataFrame({
        "level": ["0 prior", "1 construction", "2 operator", "3 engineering", "4 InSAR"],
        "mechanism": [
            "literature base rate (Rana 2021 / Bowker-Chambers)",
            "Beta-Binomial posterior per construction method",
            "James-Stein shrunk per-operator logit shift",
            "bounded logit shifts: height, volume, age, CRI",
            "bounded logit shifts: LOS velocity, accel, spectral slope, variance ratio",
        ],
        "bound": ["—", "—", "±1.0 logit", "0.10–0.30 per z", "±1.5 logit total"],
        "data_source": [
            "literature", "SIGBM + WMTF labels", "SIGBM + labels",
            "SIGBM static fields", "Sentinel-1 HyP3 InSAR",
        ],
    })
    t5.to_csv(OUT / "t5_model_structure.csv", index=False)
    md_chunks.append("### Table 5 — Hierarchical model structure\n\n" + _md(t5))

    (OUT / "tables.md").write_text("\n\n".join(md_chunks) + "\n")
    print(f"wrote 5 CSV tables + tables.md to {OUT.relative_to(REPO)}/")
    for c in md_chunks:
        print("  -", c.splitlines()[0].replace("### ", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
