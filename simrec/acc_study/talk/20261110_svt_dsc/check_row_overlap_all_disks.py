#!/usr/bin/env python3
"""Row spacing / y-overlap per disk and fid efficiency vs |tan theta_y| for all disks (v_z = 0).

Row overlap in y between adjacent rows (opposite faces) = RSU y length (18.514 mm, from
active_silicon_rectangles.csv box extents) - spacing between adjacent row centres (rows CSV).
Expected onset of row-gap losses: |tan theta_y| ~ overlap / dz, dz ~ 6.6-7.2 mm between faces.
Efficiency vs |tan theta_y|: refplane_efficiency_v4 histograms, fid selection, all p, +/- folded,
0.10 bins, bins with < 2000 entries masked. Also the fraction of fid tracks per |tan| bin.
"""
import numpy as np
import pandas as pd

RSU_Y = 18.514
rows = pd.read_csv("../../../compact/tracking/silicon_disks_tiling/20261001_ES/SVT_endcap_corrugation_rows_33_36.csv")
rows["disk"] = rows.disk.replace({"HD3b": "HD3"})
order = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
print("Adjacent-row spacing [mm] and y-overlap = 18.514 - spacing, per family")
for disk in order:
    r = rows[rows.disk == disk].sort_values("row_y_mm")
    y = r.row_y_mm.to_numpy(); fam = r.family.to_numpy()
    sp = np.diff(y)
    pair_fam = np.where(fam[:-1] == fam[1:], fam[:-1], "mixed")
    parts = []
    for f in ("A", "B", "mixed"):
        s = sp[pair_fam == f]
        if s.size:
            parts.append(f"{f}: spacing {np.unique(np.round(s, 2))} -> overlap {np.unique(np.round(RSU_Y - s, 2))}")
    print(f"  {disk}: " + "; ".join(parts))

h = np.load("results/refplane_efficiency_v4/vz_000mm/histograms.npz")
sel = list(h["selections"]).index("fid")
edges = h["tan_edges"]
centres = 0.5 * (edges[1:] + edges[:-1])
abs_edges = np.arange(0.0, 1.01, 0.1)
print("\nfid efficiency [%] vs |tan theta_y| (v_z = 0, all p); share of tracks in brackets")
print("disk  " + " ".join(f"{lo:.1f}-{lo+0.1:.1f}".rjust(13) for lo in abs_edges[:-1]))
for disk in order:
    num = h[f"{disk}__tany_num"][sel].sum(0); den = h[f"{disk}__tany_den"][sel].sum(0)
    idx = np.digitize(np.abs(centres), abs_edges) - 1
    n = np.bincount(idx[idx >= 0], weights=num[idx >= 0], minlength=len(abs_edges))[:len(abs_edges) - 1]
    d = np.bincount(idx[idx >= 0], weights=den[idx >= 0], minlength=len(abs_edges))[:len(abs_edges) - 1]
    cells = [(f"{100*a/b:5.1f} ({100*b/d.sum():4.1f}%)" if b >= 2000 else "-").rjust(13) for a, b in zip(n, d)]
    print(f"{disk}  " + " ".join(cells))
