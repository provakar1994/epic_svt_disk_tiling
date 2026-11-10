#!/usr/bin/env python3
"""Slide 2 (right): ED4 fiducial hit efficiency vs p at v_z = 0 (reference-plane analysis v4).

Input: efficiency_vs_p.csv, selection == "fid" only (r_in+30 mm <= r < rmax-40 mm at
the true point). Bin centre = midpoint of [p_min, p_max] with the last bin capped at
20 GeV (stored as 20.01 to include the gun endpoint). Error bars: binomial.
ED3 and ED2 are drawn lightly for context.

Output: results/talk/20261110_svt_dsc/slide2_ED4_vs_p.{png,pdf}
Run from acc_study/ (see run_slides_1_2.sh).
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

CSV = Path("results/refplane_efficiency_v4/vz_000mm/efficiency_vs_p.csv")
INTEGRATED = Path("results/refplane_efficiency_v4/vz_000mm/integrated_efficiency.csv")
OUT_DIR = Path("results/talk/20261110_svt_dsc")
plt.rcParams.update({"font.size": 13, "axes.titlesize": 15})

STYLE = {"ED4": dict(color="#1f3a93", fmt="o-", ms=6, lw=2.0, capsize=3, alpha=1.0, zorder=5),
         "ED3": dict(color="0.55", fmt="s-", ms=4, lw=1.0, capsize=2, alpha=0.6, zorder=3),
         "ED2": dict(color="0.75", fmt="^-", ms=4, lw=1.0, capsize=2, alpha=0.6, zorder=2)}


def main():
    df = pd.read_csv(CSV)
    df = df[df.selection == "fid"]
    integ = pd.read_csv(INTEGRATED)
    integ = integ[integ.selection == "fid"].set_index("disk")

    fig, ax = plt.subplots(figsize=(6.5, 5.6))
    fig.patch.set_facecolor("white")
    for disk in ("ED2", "ED3", "ED4"):
        d = df[df.disk == disk].sort_values("p_min_GeV")
        centres = 0.5 * (d.p_min_GeV + d.p_max_GeV.clip(upper=20.0))
        label = f"{disk} (all p: {100 * integ.loc[disk, 'efficiency']:.1f}%)"
        ax.errorbar(centres, 100 * d.efficiency, yerr=100 * d.binomial_error, label=label, **STYLE[disk])
        if disk == "ED4":
            print(f"ED4 fid vs p: min {100*d.efficiency.min():.2f}%  max {100*d.efficiency.max():.2f}%  "
                  f"integrated {100*integ.loc[disk, 'efficiency']:.2f} +- {100*integ.loc[disk, 'binomial_error']:.2f}%")

    ax.axhline(98.0, color="red", ls="--", lw=1.5, label="expected 98%")
    ax.set_xscale("log")
    ax.set_xlim(0.45, 22)
    ax.set_xticks([0.5, 1, 2, 5, 10, 20]); ax.set_xticklabels(["0.5", "1", "2", "5", "10", "20"])
    ax.set_ylim(96.0, 100.2)
    ax.set_xlabel("p [GeV]")
    ax.set_ylabel("hit efficiency in fiducial annulus [%]")
    ax.set_title("ED4 efficiency flat in p, v_z = 0 cm")
    ax.grid(alpha=0.3)
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(l) for l in labels if l.startswith("ED4")] + \
            [labels.index(l) for l in labels if l.startswith("ED3")] + \
            [labels.index(l) for l in labels if l.startswith("ED2")] + [labels.index("expected 98%")]
    ax.legend([handles[i] for i in order], [labels[i] for i in order], loc="upper right", fontsize=12)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT_DIR / f"slide2_ED4_vs_p.{ext}", dpi=200, facecolor="white")
    print("wrote", OUT_DIR / "slide2_ED4_vs_p.png")


if __name__ == "__main__":
    main()
