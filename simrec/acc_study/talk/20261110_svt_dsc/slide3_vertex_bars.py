"""Slide 3: fiducial hit efficiency per SVT endcap disk for three vertex positions.

Input : results/refplane_efficiency_v4/vz_{m100,000,p100}mm/integrated_efficiency.csv
        (selection == "fid" only; efficiency = primaries with >=1 Si hit on the disk /
        primaries crossing the zero-material reference plane 6 mm in front of it,
        inside the fiducial annulus r_in+30 mm .. rmax-40 mm).
Output: results/talk/20261110_svt_dsc/slide3_vertex_bars.{png,pdf}
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ACC = Path(__file__).resolve().parents[2]
RESULTS = ACC / "results" / "refplane_efficiency_v4"
OUTDIR = ACC / "results" / "talk" / "20261110_svt_dsc"

DISKS = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
DISK_Z_MM = {"ED0": -250, "ED1": -450, "ED2": -650, "ED3": -850, "ED4": -1020,
             "HD0": 250, "HD1": 450, "HD2": 700, "HD3": 950, "HD4": 1200}
# (directory tag, vertex z in mm, colour) -- shared colour convention for the talk
VERTICES = [("m100", -100, "#0072B2"), ("000", 0, "#555555"), ("p100", 100, "#D55E00")]


def load_fid_table():
    frames = []
    for tag, vz_mm, _ in VERTICES:
        df = pd.read_csv(RESULTS / f"vz_{tag}mm" / "integrated_efficiency.csv")
        df = df[df["selection"] == "fid"].copy()
        assert (df["vertex_z_mm"] == vz_mm).all()
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main():
    table = load_fid_table()
    eff = {}  # (disk, vz_mm) -> (eff %, err %)
    for _, row in table.iterrows():
        eff[(row["disk"], int(row["vertex_z_mm"]))] = (100 * row["efficiency"],
                                                         100 * row["binomial_error"])

    # Print the numbers for the record / speaker notes
    print(f"{'disk':>4} {'z[mm]':>6} " + " ".join(f"{'vz=' + str(v // 10) + 'cm':>16}" for _, v, _ in VERTICES))
    for disk in DISKS:
        cells = " ".join(f"{eff[(disk, v)][0]:7.2f} +/- {eff[(disk, v)][1]:4.2f}" for _, v, _ in VERTICES)
        print(f"{disk:>4} {DISK_Z_MM[disk]:6d} {cells}")

    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(len(DISKS))
    bar_w = 0.24
    y_bottom, y_top = 93.0, 100.0

    for i, (_, vz_mm, colour) in enumerate(VERTICES):
        vals = np.array([eff[(d, vz_mm)][0] for d in DISKS])
        errs = np.array([eff[(d, vz_mm)][1] for d in DISKS])
        xpos = x + (i - 1) * bar_w
        ax.bar(xpos, vals - y_bottom, bottom=y_bottom, width=bar_w * 0.9, color=colour,
               label=f"$v_z$ = {vz_mm / 10:+.0f} cm".replace("+0", "0"), zorder=2)
        ax.errorbar(xpos, vals, yerr=errs, fmt="none", ecolor="black", elinewidth=1,
                    capsize=2, zorder=3)

    ax.axhline(98.0, color="red", ls="--", lw=1.5, label="expected 98%", zorder=4)

    # Label the two near-vertex drops (ED0 at -10 cm, HD0 at +10 cm): value written
    # vertically inside the bar, plus one short callout in the empty band above 98%.
    for disk, vz_mm, i_vtx in [("ED0", -100, 0), ("HD0", 100, 2)]:
        val = eff[(disk, vz_mm)][0]
        xb = DISKS.index(disk) + (i_vtx - 1) * bar_w
        ax.text(xb, y_bottom + 0.12, f"{val:.1f}%", rotation=90, ha="center", va="bottom",
                fontsize=11, color="white", fontweight="bold", zorder=5)
    ax.text(4.5, 99.55, "disk nearest the vertex (15 cm): ED0 at $v_z$ = -10 cm, HD0 at +10 cm",
            ha="center", va="center", fontsize=13, color="#333333")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{d}\n{DISK_Z_MM[d] / 10:+.0f} cm" for d in DISKS], fontsize=13)
    ax.set_ylim(y_bottom, y_top)
    ax.set_ylabel("Hit efficiency in fiducial annulus [%]", fontsize=14)
    ax.tick_params(axis="y", labelsize=13)
    ax.grid(axis="y", color="#dddddd", lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("A displaced vertex costs ~3 points on the nearest disk", fontsize=16)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4, fontsize=13,
              frameon=False)

    fig.tight_layout()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUTDIR / f"slide3_vertex_bars.{ext}", dpi=200, facecolor="white")
    print("wrote", OUTDIR / "slide3_vertex_bars.png")


if __name__ == "__main__":
    main()
