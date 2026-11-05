#!/usr/bin/env python3
"""How wrong is the straight-line (no field) hit position we use for missed particles?

For primaries that DO hit a disk, compare the stored mean hit position on that
disk with the straight-line projection of the generated direction to the same z:
    x_pred = vx + (z_hit - vz) * px/pz,  y_pred = vy + (z_hit - vz) * py/pz.
Reports the median and 90th percentile of the transverse miss distance
|d| = |(x,y)_hit - (x,y)_pred| and of |dy| per disk and momentum bin.
Caveat: mean_hit is the mean over all hits of the primary on that disk, so a
particle crossing two overlapping modules (different z) gets an averaged point;
this adds at most a few mm only for those particles and is the same at all p.
Sample: z=0, first N shards per eta sign (enough statistics, quick to run).
"""
from pathlib import Path
import numpy as np
from reduce_disk_acceptance import DISKS, configuration_name

here = Path(__file__).resolve().parent
N_SHARDS = 10
P_BINS = [(0.5, 1.0), (1.0, 2.0), (2.0, 3.0), (5.0, 7.0), (10.0, 12.0), (18.5, 20.01)]

print(f"{'disk':4s} {'p bin [GeV]':>12s} {'n':>7s} {'med|d|':>7s} {'p90|d|':>7s} {'med|dy|':>7s} {'p90|dy|':>7s}  [mm]")
for side in DISKS:
    shards = sorted((here / "extracted/acceptance_v1" / configuration_name(0, side)).glob("particles_*.npz"))[:N_SHARDS]
    data = [np.load(s) for s in shards]
    cat = lambda k: np.concatenate([d[k] for d in data]).astype(float)
    p, px, py, pz = cat("p_GeV"), cat("px_GeV"), cat("py_GeV"), cat("pz_GeV")
    vx, vy, vz = cat("vertex_x_mm"), cat("vertex_y_mm"), cat("vertex_z_mm")
    mask = np.concatenate([d["hit_mask"] for d in data])
    hx, hy, hz = cat("mean_hit_x_mm"), cat("mean_hit_y_mm"), cat("mean_hit_z_mm")
    for index, row in enumerate(DISKS[side]):
        hit = (mask & np.uint8(1 << index)) != 0
        dz = hz[:, index] - vz
        dx = hx[:, index] - (vx + dz * px / pz)
        dy = hy[:, index] - (vy + dz * py / pz)
        d = np.hypot(dx, dy)
        for lo, hi in P_BINS:
            sel = hit & (p >= lo) & (p < hi)
            if sel.sum() < 100:
                continue
            q = lambda a, f: np.percentile(np.abs(a[sel]), f)
            print(f"{row[0]:4s} {lo:5.1f}-{hi:5.2f}  {sel.sum():7d} {q(d,50):7.2f} {q(d,90):7.2f} {q(dy,50):7.2f} {q(dy,90):7.2f}")
