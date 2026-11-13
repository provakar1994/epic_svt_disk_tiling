"""Fiducial hit efficiency per SVT endcap disk, Step 13 geometry, tiling 20261110_ES: rsu_opt vs rsu6.

Pages (one PDF, plus one PNG per page):
  1. rsu_opt, three vertex positions (same layout as talk/20261110_svt_dsc/slide3_vertex_bars.py)
  2. rsu6 (all 6-RSU modules), same layout
  3-5. rsu_opt vs rsu6 per vertex (vz = -10, 0, +10 cm), with the difference rsu6 - rsu_opt above each disk

Input : results/refplane_efficiency_v5{,_rsu6}/vz_{m100,000,p100}mm/integrated_efficiency.csv, selection "fid"
        (efficiency = primaries with >= 1 Si hit on the disk / primaries crossing the zero-material reference
        plane in front of it, inside the fiducial annulus r_in+30 mm .. r_max-40 mm).
        rsu_opt = campaign acceptance_v4_step13, rsu6 = acceptance_v4_step13_rsu6 (same EPIC 78ade4686).
Errors: binomial per sample; the two campaigns are independent samples (npsim shared random stream),
        so the difference error is sqrt(e1^2 + e2^2).
Output: results/talk/20261113_rsu6_compare/rsu_opt_vs_rsu6_fid_efficiency.pdf and page PNGs.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

ACC = Path(__file__).resolve().parents[2]
SCENARIOS = {"rsu_opt": ACC / "results" / "refplane_efficiency_v5",
             "rsu6": ACC / "results" / "refplane_efficiency_v5_rsu6"}
LABELS = {"rsu_opt": "rsu_opt", "rsu6": "rsu6 (all 6-RSU)"}
OUTDIR = ACC / "results" / "talk" / "20261113_rsu6_compare"

DISKS = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
DISK_Z_MM = {"ED0": -250, "ED1": -450, "ED2": -650, "ED3": -850, "ED4": -1020,
             "HD0": 250, "HD1": 450, "HD2": 700, "HD3": 950, "HD4": 1200}
# (directory tag, vertex z in mm, colour) -- colour convention of the 2026-11-10 talk
VERTICES = [("m100", -100, "#0072B2"), ("000", 0, "#555555"), ("p100", 100, "#D55E00")]
SCENARIO_COLOURS = {"rsu_opt": "#555555", "rsu6": "#009E73"}
Y_BOTTOM, Y_TOP = 93.0, 100.0


def load_fid(scenario):
    """(disk, vz_mm) -> (efficiency %, binomial error %)."""
    eff = {}
    for tag, vz_mm, _ in VERTICES:
        df = pd.read_csv(SCENARIOS[scenario] / f"vz_{tag}mm" / "integrated_efficiency.csv")
        df = df[df["selection"] == "fid"]
        assert (df["vertex_z_mm"] == vz_mm).all() and sorted(df["disk"]) == sorted(DISKS)
        for _, row in df.iterrows():
            eff[(row["disk"], vz_mm)] = (100 * row["efficiency"], 100 * row["binomial_error"])
    return eff


def style_axes(ax, title):
    x = np.arange(len(DISKS))
    ax.axhline(98.0, color="red", ls="--", lw=1.5, label="expected 98%", zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d}\n{DISK_Z_MM[d] / 10:+.0f} cm" for d in DISKS], fontsize=13)
    ax.set_ylim(Y_BOTTOM, Y_TOP)
    ax.set_ylabel("Hit efficiency in fiducial annulus [%]", fontsize=14)
    ax.tick_params(axis="y", labelsize=13)
    ax.grid(axis="y", color="#dddddd", lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(title, fontsize=16)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4, fontsize=13, frameon=False)



def vertex_page(eff, scenario):
    """Pages 1-2: one scenario, three vertices (layout of slide3_vertex_bars.py)."""
    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(len(DISKS))
    bar_w = 0.24
    for i, (_, vz_mm, colour) in enumerate(VERTICES):
        vals = np.array([eff[(d, vz_mm)][0] for d in DISKS])
        errs = np.array([eff[(d, vz_mm)][1] for d in DISKS])
        ax.bar(x + (i - 1) * bar_w, vals - Y_BOTTOM, bottom=Y_BOTTOM, width=bar_w * 0.9, color=colour,
               label=f"$v_z$ = {vz_mm / 10:+.0f} cm".replace("+0", "0"), zorder=2)
        ax.errorbar(x + (i - 1) * bar_w, vals, yerr=errs, fmt="none", ecolor="black", elinewidth=1,
                    capsize=2, zorder=3)
    # value of the near-vertex drop written inside the bar, as on the original slide
    for disk, vz_mm, i_vtx in [("ED0", -100, 0), ("HD0", 100, 2)]:
        ax.text(DISKS.index(disk) + (i_vtx - 1) * bar_w, Y_BOTTOM + 0.12, f"{eff[(disk, vz_mm)][0]:.1f}%",
                rotation=90, ha="center", va="bottom", fontsize=11, color="white", fontweight="bold", zorder=5)
    ax.text(4.5, 99.55, "disk nearest the vertex (15 cm): ED0 at $v_z$ = -10 cm, HD0 at +10 cm",
            ha="center", va="center", fontsize=13, color="#333333")
    style_axes(ax, f"Fiducial hit efficiency per disk: 20261110_ES / {LABELS[scenario]}")
    fig.tight_layout()
    return fig


def comparison_page(eff_a, eff_b, vz_mm):
    """Pages 3-5: rsu_opt vs rsu6 at one vertex; difference (points, pull) above each disk."""
    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(len(DISKS))
    bar_w = 0.36
    for i, (scenario, eff) in enumerate([("rsu_opt", eff_a), ("rsu6", eff_b)]):
        vals = np.array([eff[(d, vz_mm)][0] for d in DISKS])
        errs = np.array([eff[(d, vz_mm)][1] for d in DISKS])
        xpos = x + (i - 0.5) * bar_w
        ax.bar(xpos, vals - Y_BOTTOM, bottom=Y_BOTTOM, width=bar_w * 0.9, color=SCENARIO_COLOURS[scenario],
               label=LABELS[scenario], zorder=2)
        ax.errorbar(xpos, vals, yerr=errs, fmt="none", ecolor="black", elinewidth=1, capsize=2, zorder=3)
    for j, d in enumerate(DISKS):
        (ea, sa), (eb, sb) = eff_a[(d, vz_mm)], eff_b[(d, vz_mm)]
        diff, err = eb - ea, np.hypot(sa, sb)
        significant = abs(diff / err) >= 3
        # round first so that -0.004 prints as +0.00, not -0.00
        diff_r, pull_r = round(diff, 2) + 0.0, round(diff / err) + 0
        ax.text(j, 99.2, f"{diff_r:+.2f}\n({pull_r:+d}$\\sigma$)", ha="center", va="center", fontsize=10.5,
                color="#000000" if significant else "#888888", fontweight="bold" if significant else "normal")
    ax.text(4.5, 99.75, "rsu6 - rsu_opt [points]  (bold: |pull| $\\geq$ 3)", ha="center", va="center",
            fontsize=12, color="#333333")
    style_axes(ax, f"rsu_opt vs rsu6, vertex $v_z$ = {vz_mm / 10:+.0f} cm".replace("+0 ", "0 "))
    fig.tight_layout()
    return fig


def main():
    eff = {s: load_fid(s) for s in SCENARIOS}
    print(f"{'disk':>4} {'vz[cm]':>6} {'rsu_opt':>16} {'rsu6':>16} {'diff':>14}")
    for _, vz_mm, _ in VERTICES:
        for d in DISKS:
            (ea, sa), (eb, sb) = eff["rsu_opt"][(d, vz_mm)], eff["rsu6"][(d, vz_mm)]
            print(f"{d:>4} {vz_mm / 10:+6.0f} {ea:8.2f} +- {sa:4.2f} {eb:8.2f} +- {sb:4.2f} "
                  f"{eb - ea:+6.2f} +- {np.hypot(sa, sb):4.2f}")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    figures = [("page1_rsu_opt_vertex_bars", vertex_page(eff["rsu_opt"], "rsu_opt")),
               ("page2_rsu6_vertex_bars", vertex_page(eff["rsu6"], "rsu6"))]
    for tag, vz_mm, _ in VERTICES:
        figures.append((f"page_compare_vz_{tag}mm", comparison_page(eff["rsu_opt"], eff["rsu6"], vz_mm)))
    # page order: rsu_opt, rsu6, then vz = -10, 0, +10 cm
    pdf_path = OUTDIR / "rsu_opt_vs_rsu6_fid_efficiency.pdf"
    with PdfPages(pdf_path) as pdf:
        for i, (name, fig) in enumerate(figures, start=1):
            pdf.savefig(fig, facecolor="white")
            fig.savefig(OUTDIR / f"{i}_{name.split('_', 1)[1] if name.startswith('page') else name}.png",
                        dpi=200, facecolor="white")
            plt.close(fig)
    print("wrote", pdf_path)


if __name__ == "__main__":
    main()
