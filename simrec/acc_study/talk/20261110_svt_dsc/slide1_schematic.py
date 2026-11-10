#!/usr/bin/env python3
"""Slide 1: side-view schematic of the reference-plane method (NOT to scale).

Left : vertex on the beam axis, a track to an endcap disk, the zero-material
       reference plane 6 mm upstream of the disk.
Right: zoom of the corrugated disk (y-z cut), TO SCALE from the built geometry
       (2026-11-10 fix: sensors sit on 32 mm baseplates ~0.6 mm above the carbon
       flats, not on the flats). Rows alternate sides; neighbouring sensors overlap
       by ~2 mm in y. A near-normal track crossing the overlap hits silicon; a steep
       track can slip between the end of one row and the start of the next.

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
    """y-z cut through the corrugated support, TO SCALE (mm, equal aspect).

    Numbers from the built geometry (outward-facing B rows, 33 mm pitch, e.g. HD1):
      carbon: 0.15 mm skin, outer surfaces at z = -/+ 3.0 mm (h = 6 mm), 45 deg webs,
              flat width 16.5 - 5.85 = 10.65 mm (sharp-corner model; bends not drawn);
      module: 32 mm baseplate (z 3.34-3.49 mm) glued on the flat, sensor on top
              (active Si centre at z = -/+ 3.596 mm, 18.514 mm active width in y);
      rows alternate sides every 16.5 mm in y -> neighbouring sensors overlap by 2.0 mm.
    Inward-facing modules (sensor at -/+ 3.01 mm, facing the carbon; D2-D4 only) are not drawn.
    """
    row_dy = 16.5                    # y spacing of neighbouring rows (opposite sides)
    z_mid = 2.925                    # carbon mid-surface (outer surface 3.0, skin 0.15)
    web_dy = 2 * z_mid               # 45 deg web: dy = dz
    flat_half = (row_dy - web_dy) / 2
    z_base = (3.3425, 3.4925)        # baseplate z range on the + side
    z_sens = 3.596                   # active sensor centre
    base_half, sens_half = 16.0, 18.514 / 2
    y_rows = np.arange(-16.5, 34.0, row_dy)          # sides alternate: -, +, -, +
    side = {yc: (1 if i % 2 else -1) for i, yc in enumerate(y_rows)}   # +1 = downstream (+z) side

    # Carbon corrugation (mid-surface polyline: flats joined by 45 deg webs).
    ys, zs = [], []
    for yc in y_rows:
        ys += [yc - flat_half, yc + flat_half]; zs += [side[yc] * z_mid] * 2
    ax.plot(zs, ys, color=C_SUPPORT, lw=2.0, solid_joinstyle="miter")

    for yc in y_rows:
        sg = side[yc]
        # Baseplate (thin dark bar) and sensor (coloured bar), both on the outer side of the flat.
        ax.add_patch(Rectangle((sg * z_base[0] if sg > 0 else -z_base[1], yc - base_half),
                               z_base[1] - z_base[0], 2 * base_half, color="#2f4f2f", lw=0))
        ax.plot([sg * z_sens] * 2, [yc - sens_half, yc + sens_half], color=C_DOWN if sg > 0 else C_UP,
                lw=4, solid_capstyle="butt")

    # Overlap between the + row at y = 0 and the - row at y = 16.5.
    y_ov0, y_ov1 = 16.5 - sens_half, sens_half
    ax.axhspan(y_ov0, y_ov1, color="0.85", zorder=0)
    ax.annotate("sensor\noverlap\n≈ 2 mm", xy=(-8.0, 0.5 * (y_ov0 + y_ov1)), xytext=(-10.6, -4.0),
                fontsize=10, ha="left", va="center", arrowprops=dict(arrowstyle="->", lw=1.0))
    ax.annotate("sensor on a 32 mm\nbaseplate, ~0.6 mm\nabove the carbon flat", xy=(z_sens, -2.0),
                xytext=(6.0, -9.0), fontsize=10, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", lw=1.0))

    # Tracks travel from the vertex side (left, -z) to the right.
    yc_ov = 0.5 * (y_ov0 + y_ov1)
    z = np.array([-9.0, 9.0])
    ax.plot(z, yc_ov + 0.05 * z, color=C_HIT, lw=2.0)                    # near-normal: hits both rows
    zz = np.linspace(-9.0, 9.0, 50)
    ax.plot(zz, yc_ov + 0.6 * zz, color=C_MISS, lw=2.0, ls="--")         # steep (~31 deg): misses both
    ax.text(5.0, 16.5, "steep:\nno hit", color=C_MISS, fontsize=12, ha="left", va="center")
    ax.text(5.0, 4.0, "near-normal:\nhit", color=C_HIT, fontsize=12, ha="left", va="center")

    ax.set_xlim(-11, 12)
    ax.set_ylim(-13, 30)
    ax.set_aspect("equal")
    ax.set_xticks([-3.6, 0, 3.6])
    ax.set_xticklabels(["-3.6", "0", "+3.6"])
    ax.set_xlabel("z - z_disk [mm]")
    ax.set_ylabel("y [mm] (across rows)")
    ax.set_yticks([0, 16.5])
    ax.set_title("Disk zoom (to scale)")
    key = [Line2D([], [], color=C_UP, lw=4, label="sensors, upstream side"),
           Line2D([], [], color=C_DOWN, lw=4, label="sensors, downstream side"),
           Line2D([], [], color="#2f4f2f", lw=4, label="module baseplate"),
           Line2D([], [], color=C_SUPPORT, lw=2.0, label="carbon corrugation (45° webs)")]
    return key


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 5.6), gridspec_kw={"width_ratios": [1.25, 1.0]})
    fig.patch.set_facecolor("white")
    box = draw_overview(a1)
    key = draw_zoom(a2)
    fig.legend(handles=key, loc="lower center", ncol=4, fontsize=10.5, frameon=False,
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
