"""Slide 4 (v3): fid hit efficiency vs |tan(theta_y)| with row-matched bins (no sawtooth).

Why: for a straight track from the vertex, tan(theta_y) ~ y / L (L = |z_disk - v_z|). D0/D1
module rows repeat every 16.5 mm in y (33 mm pitch, rows alternating between the two faces),
so a fixed tan bin covers a different number of rows on each curve; adjacent bins then catch
alternately more row gap or more row overlap -> sawtooth. Here each curve gets bins of width
    w = n * 16.5 mm / L,   n = the integer that brings w closest to TARGET_WIDTH,
so every bin averages over a whole number of row periods.

Input : extracted/acceptance_v3_refplanes/<config>/particles_*.npz (per-primary shards).
Selection (same as analyze_refplane_efficiency.py "fid"): plane reached on the disk, true point
        (first plane crossing propagated straight along its momentum to z_disk) inside the
        fid annulus r_in+30 <= r < rmax-40 (geometry from load_geometry), 0.5 <= p < 20.01 GeV.
        tan(theta_y) = py/|pz| at the plane; efficiency = has silicon hit on the disk.
Output: results/talk/20261110_svt_dsc/slide4_incidence_angle.{png,pdf}
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ACC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ACC))
import analyze_refplane_efficiency as ana                      # noqa: E402
from reduce_disk_acceptance import DISKS, configuration_name   # noqa: E402

OUTDIR = ACC / "results" / "talk" / "20261110_svt_dsc"
EXTRACTED = ACC / "extracted" / "acceptance_v3_refplanes"
ROW_SPACING_MM = 16.5          # D0/D1: uniform 33 mm pitch, rows alternate faces
TARGET_WIDTH = 0.10
MIN_DEN = 2000
X_MAX = 1.0
DISK_STYLE = {"HD0": ("-", "o"), "HD1": ("--", "s")}
VERTICES = [(-100, "#0072B2"), (0, "#555555"), (100, "#D55E00")]
ONSET_BAND = (0.35, 0.40)


def collect(geometry, vz, disk):
    """|tan theta_y| and hit flag of fid-selected primaries on one disk."""
    g = geometry[disk]
    i = g["index"]
    bit = np.uint8(1 << i)
    tans, hits = [], []
    for shard in sorted((EXTRACTED / configuration_name(vz, g["side"])).glob("particles_*.npz")):
        with np.load(shard) as s:
            reached = (s["plane_mask"] & bit) != 0
            hit = (s["hit_mask"] & bit) != 0
            p = s["p_GeV"].astype(float)
            xp, yp, zp = (s[f"plane_{a}_mm"][:, i].astype(float) for a in "xyz")
            px, py, pz = (s[f"plane_p{a}_GeV"][:, i].astype(float) for a in "xyz")
        with np.errstate(divide="ignore", invalid="ignore"):
            dz = g["z_disk"] - zp
            r = np.hypot(xp + dz * px / pz, yp + dz * py / pz)
            tan_y = np.abs(py / np.abs(pz))
        sel = reached & (p >= 0.5) & (p < 20.01) & (r >= g["fid"][0]) & (r < g["fid"][1]) & np.isfinite(tan_y)
        tans.append(tan_y[sel]); hits.append(hit[sel])
    return np.concatenate(tans), np.concatenate(hits)


def main():
    sys.argv = ["x"]
    geometry = ana.load_geometry(ana.parse_args())
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.axvspan(*ONSET_BAND, color="#f2c94c", alpha=0.25, lw=0, zorder=0)
    ax.text(ONSET_BAND[1] + 0.01, 99.4, "onset of row-gap losses (19°–22°)", ha="left", va="center",
            fontsize=12, color="#7a5c00")
    ax.axhline(98.0, color="red", ls="--", lw=1.5, label="expected 98%", zorder=1)
    for vz, colour in VERTICES:
        for disk, (ls, marker) in DISK_STYLE.items():
            L = abs(geometry[disk]["z_disk"] - vz)
            period = ROW_SPACING_MM / L
            n = max(1, int(round(TARGET_WIDTH / period)))
            width = n * period
            edges = np.arange(0.0, X_MAX + width, width)
            tan_y, hit = collect(geometry, vz, disk)
            den = np.histogram(tan_y, edges)[0]
            num = np.histogram(tan_y[hit], edges)[0]
            with np.errstate(divide="ignore", invalid="ignore"):
                eff = 100 * num / den
                err = 100 * np.sqrt(num / den * (1 - num / den) / den)
            ok = den >= MIN_DEN
            centres = 0.5 * (edges[1:] + edges[:-1])
            label_vz = f"{vz / 10:+.0f}".replace("+0", "0")
            ax.errorbar(centres[ok], eff[ok], yerr=err[ok], color=colour, ls=ls, marker=marker, ms=6, lw=1.8,
                        mfc=colour if ls == "-" else "white",
                        label=f"{disk}, $v_z$ = {label_vz} cm  ({L / 10:.0f} cm away)")
            print(f"{disk} vz={vz:+4d} L={L:4.0f} mm: bin width {width:.3f} ({n} row spacings); "
                  + " ".join(f"{c:.2f}:{e:.1f}" for c, e in zip(centres[ok], eff[ok])))
    ax.set_xlim(0, X_MAX); ax.set_ylim(84, 100)
    ax.set_xlabel(r"|tan $\theta_y$|   ($\theta_y$: incidence angle projected onto the vertical y–z plane)", fontsize=13)
    ax.set_ylabel("Hit efficiency in fiducial annulus [%]", fontsize=14)
    top = ax.secondary_xaxis("top", functions=(lambda t: np.degrees(np.arctan(t)),
                                               lambda d: np.tan(np.radians(np.clip(d, 0, 89)))))
    top.set_xticks([0, 10, 20, 30, 40]); top.set_xlabel(r"$\theta_y$ [deg]", fontsize=13); top.tick_params(labelsize=12)
    ax.tick_params(labelsize=13)
    ax.grid(color="#e5e5e5", lw=0.8); ax.set_axisbelow(True)
    ax.spines[["right"]].set_visible(False)
    ax.set_title(r"Row overlap stops covering the gap above $\theta_y$ ≈ 19° (|tan $\theta_y$| ≈ 0.35)", fontsize=16)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), fontsize=11, ncol=3, frameon=False,
              columnspacing=1.2, handlelength=2.5)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUTDIR / f"slide4_incidence_angle.{ext}", dpi=200, facecolor="white")
    print("wrote", OUTDIR / "slide4_incidence_angle.png")


if __name__ == "__main__":
    main()
