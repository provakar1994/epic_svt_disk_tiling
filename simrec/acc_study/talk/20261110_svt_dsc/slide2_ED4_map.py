#!/usr/bin/env python3
"""Slide 2 (left): ED4 x-y hit-efficiency map at v_z = 0 (reference-plane analysis v4).

Efficiency per 4 mm bin = xy_num / xy_den from histograms.npz (all primaries that
reached the reference plane, all momenta, no position cut). Masking is the same as
plot_map() in analyze_refplane_efficiency.py:
  - bins with den < 20 are not drawn;
  - bins with efficiency < 20% whose centre is outside the active-silicon outline
    (beam-pipe hole, beyond the disk) are drawn white.
Only the fiducial annulus and the beam-pipe openings + rmax are drawn.

Output: results/talk/20261110_svt_dsc/slide2_ED4_map.{png,pdf}
Run from acc_study/ so the analysis defaults resolve (see run_slides_1_2.sh).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

import analyze_refplane_efficiency as ana

DISK = "ED4"
RESULTS = Path("results/refplane_efficiency_v4/vz_000mm/histograms.npz")
OUT_DIR = Path("results/talk/20261110_svt_dsc")
MIN_DEN = 20           # same as --min-denominator-2d default
WHITE_BELOW_PCT = 20.0  # same as --map-white-below-pct default
plt.rcParams.update({"font.size": 13, "axes.titlesize": 15})


def main():
    sys.argv = ["x"]                   # use the analysis defaults (geometry paths, margins)
    args = ana.parse_args()
    geometry = ana.load_geometry(args)
    ana.build_active_outlines(args, geometry)
    g = geometry[DISK]

    h = np.load(RESULTS)
    edges = h["xy_edges"]
    eff = ana.ratio(h[f"{DISK}__xy_num"], h[f"{DISK}__xy_den"], MIN_DEN)   # index [ix, iy]

    centres = 0.5 * (edges[1:] + edges[:-1])
    xx, yy = np.meshgrid(centres, centres, indexing="ij")
    low = 100 * eff < WHITE_BELOW_PCT
    low &= ~ana.in_active_outline(g, xx.ravel(), yy.ravel()).reshape(xx.shape)
    eff = np.where(low, np.nan, eff)

    fig, ax = plt.subplots(figsize=(6.5, 5.6))
    fig.patch.set_facecolor("white")
    mesh = ax.pcolormesh(edges / 10, edges / 10, 100 * eff.T, vmin=80, vmax=100,
                         cmap="viridis", shading="flat", rasterized=True)
    cbar = fig.colorbar(mesh, ax=ax, extend="min", pad=0.02)
    cbar.set_label("hit efficiency [%]")

    t = np.linspace(0, 2 * np.pi, 400)
    for xc, yc, r in g["openings"]:
        ax.plot((xc + r * np.cos(t)) / 10, (yc + r * np.sin(t)) / 10, "r-", lw=1.6)
    ax.plot(g["rmax"] * np.cos(t) / 10, g["rmax"] * np.sin(t) / 10, "r-", lw=1.6)
    for r in g["fid"]:
        ax.plot(r * np.cos(t) / 10, r * np.sin(t) / 10, "m--", lw=2)

    lim = (g["rmax"] + 15) / 10
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
    ax.set_xlabel("x [cm]"); ax.set_ylabel("y [cm]")
    ax.set_title(f"{DISK} hit efficiency, v_z = 0 cm")
    key = [Line2D([], [], color="m", ls="--", lw=2, label="fiducial annulus"),
           Line2D([], [], color="r", lw=1.6, label="beam-pipe openings, r_max")]
    ax.legend(handles=key, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2,
              fontsize=12, frameon=False)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT_DIR / f"slide2_ED4_map.{ext}", dpi=200, facecolor="white")
    print("fid annulus [mm]:", g["fid"], " rmax:", g["rmax"])
    print("wrote", OUT_DIR / "slide2_ED4_map.png")


if __name__ == "__main__":
    main()
