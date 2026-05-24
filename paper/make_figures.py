"""Generate the full publication figure set for the Sentinela manuscript.

Reads only committed artefacts (data/processed/*.parquet,
results/*/, viz/data/*.json) and writes PNGs into figures/.

Figures
-------
  fig1_cohort_composition.png      4-panel: method / state / emergency / ops
  fig2_posterior_rates.png         prior vs posterior failure rate per method
  fig3_top_risk_ranking.png        top-20 dams by predicted 12-month risk
  fig4_terrain_3d.png              static 3D render of terrain + risk spikes
  fig5_retrospectives.png          Fundao + B1 trajectories, with 3-mo smooth
  fig6_insar_comparison.png        InSAR feature comparison across the two events

Run:
  python paper/make_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
FIG = REPO / "figures"
RES = REPO / "results"
PROC = REPO / "data" / "processed"
VIZ = REPO / "viz" / "data"

# Consistent palette with the viz.
TEAL, VIOLET, ROSE, BLUE, AMBER, SLATE = (
    "#0ea5a4", "#6d28d9", "#c8186c", "#1d6cff", "#f59e0b", "#1a2230"
)
plt.style.use("seaborn-v0_8-whitegrid")


def fig1_cohort_composition() -> None:
    sigbm = pd.read_parquet(PROC / "sigbm_canonical.parquet")
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    # (a) construction method
    m = sigbm["construction_method"].value_counts()
    colours = [ROSE if k == "upstream" else SLATE for k in m.index]
    axes[0, 0].barh(m.index[::-1], m.values[::-1], color=colours[::-1])
    axes[0, 0].set_title("(a) Construction method", fontsize=11, loc="left")
    axes[0, 0].set_xlabel("dams")
    for i, v in enumerate(m.values[::-1]):
        axes[0, 0].text(v + 4, i, str(v), va="center", fontsize=8)

    # (b) top-10 states
    s = sigbm["state"].value_counts().head(10)
    axes[0, 1].barh(s.index[::-1], s.values[::-1], color=BLUE)
    axes[0, 1].set_title("(b) State (top 10)", fontsize=11, loc="left")
    axes[0, 1].set_xlabel("dams")

    # (c) emergency level
    e = sigbm["emergency_level"].value_counts().sort_index()
    ec = [SLATE, AMBER, "#e8830a", ROSE][: len(e)]
    axes[1, 0].bar([str(i) for i in e.index], e.values, color=ec)
    axes[1, 0].set_title("(c) Declared emergency level", fontsize=11, loc="left")
    axes[1, 0].set_xlabel("level (0 = none)")
    axes[1, 0].set_ylabel("dams")
    axes[1, 0].set_yscale("log")
    for i, v in enumerate(e.values):
        axes[1, 0].text(i, v * 1.1, str(v), ha="center", fontsize=8)

    # (d) operational status
    o = sigbm["ops_status"].value_counts()
    axes[1, 1].barh(o.index[::-1], o.values[::-1], color=TEAL)
    axes[1, 1].set_title("(d) Operational status", fontsize=11, loc="left")
    axes[1, 1].set_xlabel("dams")

    fig.suptitle("Figure 1 — Brazilian mine-tailings cohort composition (SIGBM 2026, n=911)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(FIG / "fig1_cohort_composition.png", dpi=140, facecolor="white")
    plt.close(fig)
    print("wrote fig1_cohort_composition.png")


def fig2_posterior_rates() -> None:
    # Values from experiment 01 (committed in its README/metrics).
    methods = ["upstream", "unknown", "centerline", "single_stage", "downstream"]
    prior = [0.50, 0.10, 0.10, 0.10, 0.05]
    posterior = [0.389, 0.090, 0.040, 0.013, 0.013]
    x = np.arange(len(methods))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - w / 2, prior, w, label="literature prior", color=SLATE, alpha=0.55)
    ax.bar(x + w / 2, posterior, w, label="Beta-Binomial posterior", color=ROSE)
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=15)
    ax.set_ylabel("annual failure probability (%)")
    ax.set_title("Figure 2 — Prior vs. posterior failure rate by construction method",
                 fontsize=12, fontweight="bold", loc="left")
    ax.legend()
    for xi, pv in zip(x, posterior, strict=False):
        ax.text(xi + w / 2, pv + 0.012, f"{pv:.3f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_posterior_rates.png", dpi=140, facecolor="white")
    plt.close(fig)
    print("wrote fig2_posterior_rates.png")


def fig3_top_risk_ranking() -> None:
    top = pd.read_csv(RES / "01_first_prediction" / "top_risk_dams.csv").head(20)
    labels = [f"{r.name[:26]} · {r.state}" for r in top.itertuples(index=False)]
    vals = top["risk_12m"].to_numpy() * 100
    colours = [ROSE if lvl >= 1 else VIOLET for lvl in top["emergency_level"]]
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh(labels[::-1], vals[::-1], color=colours[::-1])
    ax.set_xlabel("predicted 12-month failure probability (%)")
    ax.set_title("Figure 3 — Top-20 highest-risk active dams (rose = active emergency)",
                 fontsize=12, fontweight="bold", loc="left")
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_top_risk_ranking.png", dpi=140, facecolor="white")
    plt.close(fig)
    print("wrote fig3_top_risk_ranking.png")


def _load_terrain_grid(step: int = 2):
    terrain = json.loads((VIZ / "terrain.json").read_text())
    W, H = terrain["width"], terrain["height"]
    elev = np.asarray(terrain["elevation_m"], dtype=float).reshape(H, W)
    elev_s = elev[::step, ::step]
    hh, ww = elev_s.shape
    lon = np.linspace(terrain["lon_min"], terrain["lon_max"], ww)
    lat = np.linspace(terrain["lat_max"], terrain["lat_min"], hh)
    LON, LAT = np.meshgrid(lon, lat)
    return terrain, LON, LAT, elev_s


def fig_cover() -> None:
    """Minimalist cover render: a single axis-free 3D view of the national
    risk field — terrain surface + glowing risk spikes, no gridlines, ticks,
    labels, or in-figure text. Designed to sit cleanly on the title page."""
    dams = json.loads((VIZ / "dams.json").read_text())
    _terr, LON, LAT, ELEV = _load_terrain_grid(step=2)
    max_risk = max(d["risk_12m"] for d in dams)

    # Flatten the terrain into a gentle relief so the spikes are the focus,
    # not the Andean foothills. Spikes are then scaled relative to the
    # flattened base.
    flat = 0.28
    ELEVf = ELEV * flat
    base_max = float(ELEVf.max())

    fig = plt.figure(figsize=(11, 6.5), facecolor="white")
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    # Soft, near-uniform terrain in a pale cool grey so it recedes.
    ax.plot_surface(LON, LAT, ELEVf, color="#c8d0d8", linewidth=0,
                    antialiased=True, alpha=0.45, rstride=1, cstride=1,
                    shade=True)
    spike_scale = (base_max * 1.7) / max_risk
    for d in dams:
        if d["risk_12m"] < max_risk * 0.04:
            continue
        z0 = d["terrain_elevation_m"] * flat
        z1 = z0 + d["risk_12m"] * spike_scale
        t = (d["risk_12m"] / max_risk) ** 0.45
        colour = ROSE if t > 0.6 else VIOLET if t > 0.3 else TEAL
        ax.plot([d["lon"], d["lon"]], [d["lat"], d["lat"]], [z0, z1],
                color=colour, lw=1.5, alpha=0.95, zorder=5,
                solid_capstyle="round")
        ax.scatter([d["lon"]], [d["lat"]], [z1], color=colour,
                   s=11, zorder=6, edgecolors="none")
    ax.set_axis_off()              # remove all panes / ticks / labels
    ax.set_box_aspect((1.5, 1.5, 0.7))
    ax.view_init(elev=26, azim=-60)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(FIG / "fig_cover.png", dpi=200, facecolor="white",
                bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("wrote fig_cover.png")


def fig0_hero() -> None:
    """Two-panel 'hero' 3D render for the top of the paper:
       (A) dramatic full-Brazil risk field, (B) labelled Minas Gerais zoom."""
    dams = json.loads((VIZ / "dams.json").read_text())
    _terr, LON, LAT, ELEV = _load_terrain_grid(step=2)
    max_risk = max(d["risk_12m"] for d in dams)

    fig = plt.figure(figsize=(15, 7.5), facecolor="white")

    # ---------- Panel A: full Brazil, dramatic oblique ----------
    axA = fig.add_subplot(1, 2, 1, projection="3d", computed_zorder=False)
    axA.plot_surface(LON, LAT, ELEV, cmap="gist_earth", linewidth=0,
                     antialiased=True, alpha=0.75, rstride=1, cstride=1)
    spike_scale = 5000.0 / max_risk
    for d in dams:
        if d["risk_12m"] < max_risk * 0.05:
            continue
        z0 = d["terrain_elevation_m"]
        z1 = z0 + d["risk_12m"] * spike_scale
        t = (d["risk_12m"] / max_risk) ** 0.45
        colour = ROSE if t > 0.6 else VIOLET if t > 0.3 else TEAL
        axA.plot([d["lon"], d["lon"]], [d["lat"], d["lat"]], [z0, z1],
                 color=colour, lw=1.3, alpha=0.92, zorder=5)
        axA.scatter([d["lon"]], [d["lat"]], [z1], color=colour, s=6, zorder=6)
    axA.set_title("(A) National failure-risk field", fontsize=12, fontweight="bold", pad=0)
    axA.set_xlabel("lon", fontsize=8)
    axA.set_ylabel("lat", fontsize=8)
    axA.set_zlabel("elevation + risk (m)", fontsize=8)
    axA.view_init(elev=28, azim=-62)
    axA.tick_params(labelsize=7)

    # ---------- Panel B: Minas Gerais zoom, labelled ----------
    axB = fig.add_subplot(1, 2, 2, projection="3d", computed_zorder=False)
    # MG window around the iron-ore corridor.
    lon_lo, lon_hi, lat_lo, lat_hi = -45.0, -42.5, -21.0, -19.0
    # Build a sub-grid by cropping rows/cols that fall in range.
    col_ok = np.where((LON[0, :] >= lon_lo) & (LON[0, :] <= lon_hi))[0]
    row_ok = np.where((LAT[:, 0] >= lat_lo) & (LAT[:, 0] <= lat_hi))[0]
    if len(col_ok) > 2 and len(row_ok) > 2:
        r0, r1, c0, c1 = row_ok[0], row_ok[-1] + 1, col_ok[0], col_ok[-1] + 1
        axB.plot_surface(LON[r0:r1, c0:c1], LAT[r0:r1, c0:c1], ELEV[r0:r1, c0:c1],
                         cmap="gist_earth", linewidth=0, antialiased=True,
                         alpha=0.7, rstride=1, cstride=1)
    mg = [d for d in dams if lon_lo <= d["lon"] <= lon_hi and lat_lo <= d["lat"] <= lat_hi]
    mg.sort(key=lambda d: -d["risk_12m"])
    spike_scale_b = 2500.0 / max_risk
    label_targets = {"Barragem de Germano": "Fundão complex (Germano)",
                     "Forquilha I": "Forquilha cluster",
                     "Barragem Serra Azul": "Serra Azul (Emerg. L3)"}
    for d in mg:
        z0 = d["terrain_elevation_m"]
        z1 = z0 + d["risk_12m"] * spike_scale_b
        t = (d["risk_12m"] / max_risk) ** 0.45
        colour = ROSE if t > 0.6 else VIOLET if t > 0.3 else TEAL
        axB.plot([d["lon"], d["lon"]], [d["lat"], d["lat"]], [z0, z1],
                 color=colour, lw=1.6, alpha=0.95, zorder=5)
        axB.scatter([d["lon"]], [d["lat"]], [z1], color=colour, s=12, zorder=6)
        if d["name"] in label_targets:
            axB.text(d["lon"], d["lat"], z1 + 250, label_targets[d["name"]],
                     fontsize=8, fontweight="bold", color=SLATE, zorder=7)
    axB.set_title("(B) Minas Gerais iron-ore corridor", fontsize=12, fontweight="bold", pad=0)
    axB.set_xlabel("lon", fontsize=8)
    axB.set_ylabel("lat", fontsize=8)
    axB.set_zlabel("elevation + risk (m)", fontsize=8)
    axB.view_init(elev=30, azim=-58)
    axB.tick_params(labelsize=7)

    fig.suptitle(
        "Sentinela — predicted 12-month tailings-dam failure-risk field over Brazil\n"
        "spike height scales with failure probability · teal-violet-magenta by risk decile · 877 active dams",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(FIG / "fig0_hero.png", dpi=170, facecolor="white")
    plt.close(fig)
    print("wrote fig0_hero.png")


def fig4_terrain_3d() -> None:
    """Static 3D render of the terrain surface with risk spikes — a paper
    still of the interactive viz."""
    terrain = json.loads((VIZ / "terrain.json").read_text())
    dams = json.loads((VIZ / "dams.json").read_text())
    W, H = terrain["width"], terrain["height"]
    elev = np.asarray(terrain["elevation_m"], dtype=float).reshape(H, W)
    # Downsample for a clean surface (full grid is 320x280).
    step = 3
    elev_s = elev[::step, ::step]
    hh, ww = elev_s.shape
    lon = np.linspace(terrain["lon_min"], terrain["lon_max"], ww)
    lat = np.linspace(terrain["lat_max"], terrain["lat_min"], hh)
    LON, LAT = np.meshgrid(lon, lat)

    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    ax.plot_surface(
        LON, LAT, elev_s, cmap="terrain", linewidth=0, antialiased=True,
        alpha=0.65, rstride=1, cstride=1,
    )
    # Risk spikes: vertical lines from terrain elevation upward, scaled by risk.
    max_risk = max(d["risk_12m"] for d in dams)
    spike_scale = 4000.0 / max_risk   # metres of spike per unit probability
    for d in dams:
        if d["risk_12m"] < max_risk * 0.04:
            continue  # declutter: only draw the meaningful ones
        z0 = d["terrain_elevation_m"]
        z1 = z0 + d["risk_12m"] * spike_scale
        t = (d["risk_12m"] / max_risk) ** 0.45
        colour = (ROSE if t > 0.66 else VIOLET if t > 0.33 else TEAL)
        ax.plot([d["lon"], d["lon"]], [d["lat"], d["lat"]], [z0, z1],
                color=colour, lw=1.1, alpha=0.9)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_zlabel("elevation (m) + risk spike")
    ax.set_title("Figure 4 — Predicted failure-risk field over Brazilian terrain\n"
                 "(spike height scales with 12-month failure probability; only top-risk dams drawn)",
                 fontsize=11, fontweight="bold")
    ax.view_init(elev=32, azim=-58)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_terrain_3d.png", dpi=150, facecolor="white")
    plt.close(fig)
    print("wrote fig4_terrain_3d.png")


def _load_traj(name: str) -> pd.DataFrame:
    df = pd.read_csv(RES / name / "trajectory.csv")
    df["month_dt"] = pd.to_datetime(df["month"] + "-01")
    return df


def fig5_retrospectives() -> None:
    fund = _load_traj("02_fundao_retrospective")
    b1 = _load_traj("03_b1_brumadinho_retrospective")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), sharey=False)

    for ax, df, title, collapse, windows in (
        (a1, fund, "Fundão (Samarco, 2015)", "2015-11-05", []),
        (a2, b1, "Brumadinho B1 (Vale, 2019)", "2019-01-25",
         [("2018-02-27", "2018-08-26", "Grebby milestone 1"),
          ("2018-06-27", "2018-12-24", "Grebby milestone 2")]),
    ):
        r = df["risk_12m"] * 100
        sm = r.rolling(3, center=True, min_periods=1).mean()
        ax.plot(df["month_dt"], r, color=ROSE, lw=1.3, marker="o", ms=3,
                alpha=0.55, label="monthly")
        ax.plot(df["month_dt"], sm, color=ROSE, lw=2.4, label="3-month smooth")
        for ws, we, _lbl in windows:
            ax.axvspan(pd.Timestamp(ws), pd.Timestamp(we), color=AMBER, alpha=0.15)
        ax.axvline(pd.Timestamp(collapse), color=SLATE, ls="--", lw=1)
        ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
        ax.set_ylabel("predicted 12-month risk (%)")
        ax.legend(fontsize=8, loc="upper right")
        ax.tick_params(axis="x", rotation=30)

    fig.suptitle("Figure 5 — Retrospective risk trajectories at the two reference failures "
                 "(amber bands = Grebby 2021 risk windows)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(FIG / "fig5_retrospectives.png", dpi=140, facecolor="white")
    plt.close(fig)
    print("wrote fig5_retrospectives.png")


def fig6_insar_comparison() -> None:
    fund = _load_traj("02_fundao_retrospective")
    b1 = _load_traj("03_b1_brumadinho_retrospective")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.5), sharex=False)
    for ax, df, title in (
        (a1, fund, "Fundão"), (a2, b1, "Brumadinho B1"),
    ):
        ax.plot(df["month_dt"], df["los_velocity_mm_yr"], color=BLUE,
                marker="s", ms=3, lw=1.5, label="LOS velocity (mm/yr)")
        ax.axhline(0, color="black", lw=0.5, alpha=0.4)
        ax.set_title(f"InSAR LOS velocity · {title}", fontsize=11, loc="left")
        ax.set_ylabel("mm/yr")
        ax.tick_params(axis="x", rotation=30)
        ax.legend(fontsize=8)
    fig.suptitle("Figure 6 — Extracted InSAR line-of-sight velocity across the rolling window",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(FIG / "fig6_insar_comparison.png", dpi=140, facecolor="white")
    plt.close(fig)
    print("wrote fig6_insar_comparison.png")


def main() -> int:
    FIG.mkdir(exist_ok=True)
    fig_cover()
    fig0_hero()
    fig1_cohort_composition()
    fig2_posterior_rates()
    fig3_top_risk_ranking()
    fig4_terrain_3d()
    fig5_retrospectives()
    fig6_insar_comparison()
    print("all figures written to figures/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
