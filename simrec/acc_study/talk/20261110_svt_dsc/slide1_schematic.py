#!/usr/bin/env python3
"""Slide 1: side-view schematic of the reference-plane method (NOT to scale).

Left : vertex on the beam axis, a track to an endcap disk, the zero-material
       reference plane 6 mm upstream of the disk.
Right: zoom of the corrugated disk (y-z cut), TO SCALE from the built geometry
       (2026-11-10 fixes: modules sit over the channels, i.e. aligned to the
       opposite-side flats, with 32 mm baseplates glued to the neighbouring flats;
       corrugation bends drawn with the 5 mm mid-surface radius). Rows alternate sides; neighbouring sensors overlap
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


def fillet(points, radius, n_arc=24):
    """Replace every interior corner of a polyline [(y, z), ...] by a circular arc of the given
    radius (tangent to both segments), as the builder does for the corrugation bends."""
    pts = [np.asarray(p, float) for p in points]
    out = [pts[0]]
    for prev, corner, nxt in zip(pts[:-2], pts[1:-1], pts[2:]):
        u = (corner - prev) / np.linalg.norm(corner - prev)
        v = (nxt - corner) / np.linalg.norm(nxt - corner)
        turn = np.arccos(np.clip(np.dot(u, v), -1, 1))           # deflection angle
        if turn < 1e-6:
            out.append(corner); continue
        t = radius * np.tan(turn / 2)                               # tangent length
        a, b = corner - u * t, corner + v * t
        normal = np.array([-u[1], u[0]])
        if np.dot(normal, v) < 0:
            normal = -normal
        centre = a + normal * radius
        ang0 = np.arctan2(*(a - centre)[::-1]); ang1 = np.arctan2(*(b - centre)[::-1])
        d = (ang1 - ang0 + np.pi) % (2 * np.pi) - np.pi
        for th in np.linspace(ang0, ang0 + d, n_arc):
            out.append(centre + radius * np.array([np.cos(th), np.sin(th)]))
    out.append(pts[-1])
    return np.array(out)


def draw_zoom(ax):
    """y-z cut through the corrugated support, TO SCALE (mm, equal aspect).

    Numbers from the built geometry (outward-facing B rows, 33 mm pitch, e.g. HD1) and
    compact/tracking/silicon_disks_modules.xml:
      carbon: 0.15 mm skin, outer surfaces at z = -/+ 3.0 mm (h = 6 mm), 45 deg webs,
              mid-surface bend radius 5 mm (straight flat 6.5 mm of the 10.65 mm sharp width);
      modules sit OVER THE CHANNELS: "module rows align to opposite-side flat centers".
              A +z module is centred where the carbon flat is on the -z side; its 32 mm
              baseplate spans the ~22 mm channel opening and is glued to the two
              neighbouring +z flats; the 18.5 mm active sensor (centre z = +3.596 mm) sits
              above the opening. Same mirrored for -z modules.
      neighbouring rows alternate sides every 16.5 mm in y -> sensor overlap 2.0 mm.
    Inward-facing modules (sensor at -/+ 3.01 mm, facing into the channel; D2-D4) not drawn.
    """
    row_dy = 16.5
    z_mid = 2.925                    # carbon mid-surface (outer surface 3.0, skin 0.15)
    flat_half = (row_dy - 2 * z_mid) / 2          # sharp-corner flat half-width (5.325)
    bend_r = 5.0
    z_base = (3.3425, 3.4925)        # baseplate z range (outer side)
    z_sens = 3.596                   # active sensor centre
    base_half, sens_half = 16.0, 18.514 / 2

    # Carbon flats: -z flats at y = 0, +-33; +z flats at y = +-16.5, 49.5 ...
    flat_y = np.arange(-33.0, 50.0, row_dy)
    flat_side = {round(y, 3): (-1 if round(y / row_dy) % 2 == 0 else 1) for y in flat_y}
    sharp = []
    for y in flat_y:
        zf = flat_side[round(y, 3)] * z_mid
        sharp += [(y - flat_half, zf), (y + flat_half, zf)]
    curve = fillet(sharp, bend_r)
    ax.plot(curve[:, 1], curve[:, 0], color=C_SUPPORT, lw=2.0)

    # Modules over the channels: a row at y sits on the side OPPOSITE to the flat at y.
    for y in np.arange(-16.5, 34.0, row_dy):
        sg = -flat_side[round(y, 3)]
        z0 = z_base[0] if sg > 0 else -z_base[1]
        ax.add_patch(Rectangle((z0, y - base_half), z_base[1] - z_base[0], 2 * base_half,
                               color="#2f4f2f", lw=0))
        ax.plot([sg * z_sens] * 2, [y - sens_half, y + sens_half], color=C_DOWN if sg > 0 else C_UP,
                lw=4, solid_capstyle="butt")

    # Overlap between the +z row at y = 0 and the -z row at y = 16.5.
    y_ov0, y_ov1 = 16.5 - sens_half, sens_half
    ax.axhspan(y_ov0, y_ov1, color="0.85", zorder=0)
    ax.annotate("sensor\noverlap\n≈ 2 mm", xy=(-8.0, 0.5 * (y_ov0 + y_ov1)), xytext=(-10.6, -4.0),
                fontsize=10, ha="left", va="center", arrowprops=dict(arrowstyle="->", lw=1.0))
    ax.annotate("sensor over the channel;\n32 mm baseplate glued\nto the neighbouring flats",
                xy=(z_sens, -3.0), xytext=(5.6, -9.5), fontsize=10, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", lw=1.0))

    # Tracks travel from the vertex side (left, -z) to the right.
    yc_ov = 0.5 * (y_ov0 + y_ov1)
    z = np.array([-9.0, 9.0])
    ax.plot(z, yc_ov + 0.05 * z, color=C_HIT, lw=2.0)                    # near-normal: hits both rows
    zz = np.linspace(-9.0, 9.0, 50)
    ax.plot(zz, yc_ov + 0.6 * zz, color=C_MISS, lw=2.0, ls="--")         # steep (~31 deg): misses both
    ax.text(5.6, 16.5, "steep:\nno hit", color=C_MISS, fontsize=12, ha="left", va="center")
    ax.text(5.6, 4.0, "near-normal:\nhit", color=C_HIT, fontsize=12, ha="left", va="center")

    ax.set_xlim(-11, 12)
    ax.set_ylim(-13, 30)
    ax.set_aspect("equal")
    ax.set_xticks([-3.6, 0, 3.6])
    ax.set_xticklabels(["-3.6", "0", "+3.6"])
    ax.set_xlabel("z - z_disk [mm]")
    ax.set_ylabel("y [mm] (across rows)")
    ax.set_yticks([0, 16.5])
    ax.set_title("Disk zoom (to scale)")
    key = [Line2D([], [], color=C_UP, lw=4, label="sensors, upstream"),
           Line2D([], [], color=C_DOWN, lw=4, label="sensors, downstream"),
           Line2D([], [], color="#2f4f2f", lw=4, label="module baseplate"),
           Line2D([], [], color=C_SUPPORT, lw=2.0, label="carbon corrugation (R = 5 mm bends)")]
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
