#!/usr/bin/env python3
"""Slide 1: side-view schematic of the reference-plane method (NOT to scale).

Left : vertex on the beam axis, a track to an endcap disk, the zero-material
       reference plane 6 mm upstream of the disk.
Right: zoom of the corrugated disk (y-z cut). Module rows alternate between the
       upstream and downstream faces (sensor planes at z_disk -/+ 3.6 mm,
       corrugation height 6 mm, 45 deg webs) and adjacent rows overlap in y.
       A near-normal track crossing the overlap hits silicon; a steep track can
       slip between the end of an upstream row and the start of a downstream row.
The zoom uses mm-like units with equal aspect so the 45 deg webs and track
angles are shown truthfully; row width and overlap are illustrative only.

Output: results/talk/20261110_svt_dsc/slide1_schematic.{png,pdf}
Run from acc_study/ (see run_slides_1_2.sh).
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import ConnectionPatch, Rectangle
from matplotlib.lines import Line2D
import numpy as np

OUT_DIR = Path("results/talk/20261110_svt_dsc")
plt.rcParams.update({"font.size": 13, "axes.titlesize": 15})

C_SUPPORT = "0.45"
C_UP = "#1f77b4"      # rows on the upstream (vertex-side) face
C_DOWN = "#ff7f0e"    # rows on the downstream face
C_PLANE = "#9467bd"
C_HIT = "#2ca02c"
C_MISS = "#d62728"


def draw_overview(ax):
    """Vertex, beam axis, track, reference plane and disk (arbitrary units)."""
    z_disk, z_plane = 8.0, 7.35
    r_in, r_out = 0.9, 5.0
    ax.axhline(0, color="k", lw=1.0, ls="-.")
    ax.text(0.15, -0.35, "beam axis", fontsize=12, va="top")
    ax.plot(0, 0, "ko", ms=8, zorder=5)
    ax.text(0.0, 0.35, "vertex", fontsize=13, ha="center")

    # Disk: thin zig-zag (corrugated support) with a beam-pipe hole below r_in.
    r = np.linspace(r_in, r_out, 400)
    ax.plot(z_disk + 0.09 * np.sign(np.sin(2 * np.pi * r / 0.5)), r, color=C_SUPPORT, lw=1.6)
    ax.text(z_disk + 0.25, r_out - 0.05, "disk", fontsize=13, va="top")

    # Reference plane: zero-material sensitive annulus 6 mm upstream.
    ax.plot([z_plane, z_plane], [r_in, r_out + 0.1], color=C_PLANE, lw=1.2, ls="--")
    ax.annotate("reference plane\n(zero material,\n6 mm upstream)", xy=(z_plane, 4.6),
                xytext=(3.4, 4.5), fontsize=12, color=C_PLANE, ha="center", va="center",
                arrowprops=dict(arrowstyle="->", color=C_PLANE, lw=1.2))

    # Track: slightly curved path from the vertex to the disk.
    z = np.linspace(0, z_disk + 0.6, 200)
    rt = 0.40 * z + 0.006 * z**2
    ax.plot(z, rt, color="k", lw=2.0)
    r_at_plane = 0.40 * z_plane + 0.006 * z_plane**2
    ax.plot(z_plane, r_at_plane, "o", color=C_PLANE, ms=7, zorder=6)
    ax.annotate("true crossing,\npropagated straight\nto disk z", xy=(z_plane, r_at_plane),
                xytext=(5.0, 1.2), fontsize=12, ha="center", va="center",
                arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(3.0, 0.40 * 3.0 + 0.4, r"$\pi^+$", fontsize=15, rotation=20)

    # Zoom box around the track impact on the disk.
    r_hit = 0.40 * z_disk + 0.006 * z_disk**2
    box = Rectangle((z_disk - 0.3, r_hit - 0.45), 0.6, 0.9, fill=False, ec="k", lw=1.2)
    ax.add_patch(box)

    ax.set_xlim(-0.6, 9.4)
    ax.set_ylim(-1.0, 5.6)
    ax.set_xlabel("z (along beam)")
    ax.set_ylabel("r")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Reference-plane method")
    return box


def draw_zoom(ax):
    """y-z cut through the corrugated support (mm-like units, equal aspect)."""
    half_h = 3.0          # corrugation flats at z = -/+ 3 (height 6 mm)
    z_sensor = 3.6        # sensor planes at z_disk -/+ 3.6 mm
    pitch = 18.0          # y distance between neighbouring rows (opposite faces)
    width = 20.0          # row width in y -> 2 mm overlap with each neighbour
    web = 2 * half_h      # 45 deg web spans 6 mm in y
    y_rows = np.arange(-18.0, 37.0, pitch)    # alternate faces: up, down, up, down

    # Trapezoidal corrugation: flat (length pitch - web) centred on each row, 45 deg webs.
    ys, zs = [], []
    for i, yc in enumerate(y_rows):
        zf = half_h if i % 2 else -half_h
        ys += [yc - (pitch - web) / 2, yc + (pitch - web) / 2]
        zs += [zf, zf]
    ax.plot(zs, ys, color=C_SUPPORT, lw=2.5, solid_joinstyle="round")

    # Sensor rows on the outer face of each flat.
    for i, yc in enumerate(y_rows):
        upstream = not (i % 2)
        z0 = -z_sensor if upstream else z_sensor
        ax.plot([z0, z0], [yc - width / 2, yc + width / 2], color=C_UP if upstream else C_DOWN,
                lw=5, solid_capstyle="butt")

    # Overlap region between the downstream row at y=0 and the upstream row at y=18.
    y_ov0, y_ov1 = y_rows[2] - width / 2, y_rows[1] + width / 2
    ax.axhspan(y_ov0, y_ov1, color="0.85", zorder=0)
    ax.annotate("overlap", xy=(-9.5, 0.5 * (y_ov0 + y_ov1)), xytext=(-9.5, y_ov0 - 7),
                fontsize=12, ha="center", arrowprops=dict(arrowstyle="->", lw=1.0))

    # Tracks travel from the vertex side (left) to the right.
    z = np.array([-10.0, 10.0])
    # Near-normal track through the overlap: hits both rows.
    y_n = 0.5 * (y_ov0 + y_ov1) + 0.08 * z - 0.5
    ax.plot(z, y_n, color=C_HIT, lw=2.2)
    # Steep track (45 deg): passes below the upstream row and above the downstream row.
    zz = np.linspace(-10, 10, 50); yy = (y_ov0 - 1.0) + 1.0 * (zz + z_sensor)
    m = (yy > 5) & (yy < 30)
    ax.plot(zz[m], yy[m], color=C_MISS, lw=2.2, ls="--")
    ax.text(6.0, 25.5, "steep:\nno hit", color=C_MISS, fontsize=13, ha="left", va="center")
    ax.text(4.8, 7.0, "near-normal:\nhit", color=C_HIT, fontsize=13, ha="left", va="top")

    ax.set_xlim(-14, 19)
    ax.set_ylim(-9, 35)
    ax.set_aspect("equal")
    ax.set_xticks([-z_sensor, z_sensor])
    ax.set_xticklabels(["-3.6", "+3.6"])
    ax.set_xlabel("z - z_disk [mm]")
    ax.set_ylabel("y (row direction)")
    ax.set_yticks([])
    ax.set_title("Disk zoom: rows on both faces")
    key = [Line2D([], [], color=C_UP, lw=5, label="rows, upstream face"),
           Line2D([], [], color=C_DOWN, lw=5, label="rows, downstream face"),
           Line2D([], [], color=C_SUPPORT, lw=2.5, label="carbon support (45° webs)")]
    return key


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 5.6), gridspec_kw={"width_ratios": [1.25, 1.0]})
    fig.patch.set_facecolor("white")
    box = draw_overview(a1)
    key = draw_zoom(a2)
    fig.legend(handles=key, loc="lower center", ncol=3, fontsize=12, frameon=False,
               bbox_to_anchor=(0.5, 0.0))
    # Connector lines from the zoom box to the zoom panel.
    for (xa, ya), (xb, yb) in [((box.get_x() + box.get_width(), box.get_y() + box.get_height()), (0, 1)),
                               ((box.get_x() + box.get_width(), box.get_y()), (0, 0))]:
        fig.add_artist(ConnectionPatch(xyA=(xa, ya), coordsA=a1.transData, xyB=(xb, yb),
                                       coordsB=a2.transAxes, color="0.5", lw=1.0))
    a1.text(0.98, 0.02, "not to scale", transform=a1.transAxes, fontsize=12, style="italic",
            color="0.3", ha="right", va="bottom")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(OUT_DIR / f"slide1_schematic.{ext}", dpi=200, facecolor="white")
    print("wrote", OUT_DIR / "slide1_schematic.png")


if __name__ == "__main__":
    main()
