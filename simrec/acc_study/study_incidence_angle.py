#!/usr/bin/env python3
"""Hit efficiency of D0/D1 vs track incidence tan(theta) = R/L = 1/sinh|eta|,
for every vertex sample, inside each disk's fiducial annulus.

Question: is the efficiency drop of the disk nearest a displaced vertex
(ED0 at vz=-100, HD0 at vz=+100, L=150 mm) a pure incidence-angle effect?
If yes, curves from different vertices overlap at equal tan(theta), and the
nearest-vertex sample just reaches larger tan(theta) than the z=0 sample can.
R is the straight-line radius (no field); eta is about the true vertex.
All momenta 0.5-20 GeV. Output: printed table + PNG.
"""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reduce_disk_acceptance import DISKS, configuration_name

here = Path(__file__).resolve().parent
EXTRACTED = {-100: "acceptance_v2_vz_m100mm", -10: "acceptance_v1_vz_m010mm", 0: "acceptance_v1",
             10: "acceptance_v1_vz_p010mm", 100: "acceptance_v2_vz_p100mm"}
FIDUCIAL = {"ED0": (66.8, 190.0), "HD0": (66.8, 190.0), "ED1": (66.8, 365.0), "HD1": (66.8, 365.0)}
TAN_EDGES = np.arange(0.0, 1.85, 0.1)

counts = {}  # (disk, vz) -> [generated, hit] per tan bin
for vz, root in EXTRACTED.items():
    for side in DISKS:
        shards = sorted((here / "extracted" / root / configuration_name(vz, side)).glob("particles_*.npz"))
        for shard in shards:
            with np.load(shard) as s:
                eta = np.abs(s["eta"].astype(float)); mask = s["hit_mask"]; vtx = s["vertex_z_mm"].astype(float)
            tan_theta = 1.0 / np.sinh(eta)
            for index, row in enumerate(DISKS[side]):
                disk = row[0]
                if disk not in FIDUCIAL:
                    continue
                radius = np.abs(row[3] - vtx) * tan_theta
                inside = (radius >= FIDUCIAL[disk][0]) & (radius < FIDUCIAL[disk][1])
                hit = inside & ((mask & np.uint8(1 << index)) != 0)
                gen_h = np.histogram(tan_theta[inside], TAN_EDGES)[0]
                hit_h = np.histogram(tan_theta[hit], TAN_EDGES)[0]
                c = counts.setdefault((disk, vz), np.zeros((2, len(TAN_EDGES) - 1), np.int64))
                c[0] += gen_h; c[1] += hit_h
        print(f"read vz={vz}", file=sys.stderr, flush=True)

centres = 0.5 * (TAN_EDGES[1:] + TAN_EDGES[:-1])
fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
for ax, disk in zip(axes.ravel(), ["ED0", "HD0", "ED1", "HD1"]):
    print(f"\n{disk}: efficiency [%] per tan(theta) bin (blank: <2000 generated)")
    print("tan_lo " + " ".join(f"{v:+5d}mm" for v in EXTRACTED))
    for b, lo in enumerate(TAN_EDGES[:-1]):
        cells = []
        for vz in EXTRACTED:
            g, h = counts[(disk, vz)][:, b]
            cells.append(f"{100*h/g:7.1f}" if g >= 2000 else "       ")
        print(f"{lo:5.1f}  " + " ".join(cells))
    for vz in EXTRACTED:
        g, h = counts[(disk, vz)]
        ok = g >= 2000
        ax.plot(centres[ok], 100 * h[ok] / g[ok], "o-", ms=3, label=f"vz={vz:+d} mm")
    ax.set_title(f"{disk}, fiducial annulus {FIDUCIAL[disk][0]}-{FIDUCIAL[disk][1]} mm")
    ax.grid(alpha=0.3)
axes[0, 0].set_ylim(80, 100); axes[0, 0].legend(fontsize=8)
for ax in axes[1]: ax.set_xlabel("tan(theta) = R / |z_disk - z_vtx|  (incidence angle)")
for ax in axes[:, 0]: ax.set_ylabel("hit efficiency [%]")
fig.suptitle("D0/D1 hit efficiency vs incidence angle, all momenta, all vertices")
fig.tight_layout()
out = here / "results" / "incidence_angle_d0_d1_v1.png"
fig.savefig(out, dpi=130)
print(f"\nWrote {out}")
