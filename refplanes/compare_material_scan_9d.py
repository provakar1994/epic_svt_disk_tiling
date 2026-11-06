#!/usr/bin/env python3
"""Step 9d comparison (host, tracking env): total X0 per scan line, installed vs overlay.

material_scan_agg.csv: rows = eta (index), columns = per-detector X0 (number of radiation
lengths, R_xy <= 200 cm) plus 'Others'. Total = row sum over all columns.

Expected difference: each plane replaces 0.1 mm of world Air by 0.1 mm of Vacuum (1e-15 g/cm3).
Air X0 = 36.62 g/cm2 / 1.205e-3 g/cm3 = 303.9 m, so each crossing removes
0.1 mm / |cos(theta)| / 303.9 m = 3.3e-7 / |cos(theta)| X0. Upper bound per line:
n_planes(side) * 0.1 mm / |cos theta| / X0_air with n_planes = 5 (one side).
Gate (revised after the v1 run, see Step 9d in the log): on every scan line
  -bound - 1e-12 <= delta_total <= 1e-12, i.e. the planes add no material and remove at most the
  displaced Air. Informational only: (a) lines whose 4-decimal rounding of the total flips, and
  (c) per-detector column changes; material_scan assigns steps to detectors by volume containment,
  and adding detectors reshuffles that attribution without changing the total.
Usage: python3 compare_material_scan_9d.py OUT_9D_DIR
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

X0_AIR_MM = 36.62 / 1.205e-3 * 10.0   # g/cm2 / (g/cm3) = cm -> mm
out = Path(sys.argv[1])
ok_all = True
for phi in (20, 200):
    a = pd.read_csv(out / "installed" / f"phi{phi}" / "material_scan_agg.csv", index_col=0)
    b = pd.read_csv(out / "overlay" / f"phi{phi}" / "material_scan_agg.csv", index_col=0)
    eta = a.index.to_numpy()
    assert np.allclose(eta, b.index.to_numpy())
    ta, tb = a.sum(axis=1).to_numpy(), b.sum(axis=1).to_numpy()
    delta = tb - ta
    theta = 2 * np.arctan(np.exp(-eta))
    bound = 5 * 0.1 / np.abs(np.cos(theta)) / X0_AIR_MM
    plane_cols = [c for c in b.columns if c.startswith("SVTDiskRefPlanes")]
    common = [c for c in a.columns if c != "Others"]
    col_diff = max(np.abs(b[c] - a[c]).max() for c in common)
    flips = int((np.round(ta, 4) != np.round(tb, 4)).sum())
    gate = bool(np.all((delta <= 1e-12) & (delta >= -bound - 1e-12)))
    ok_all &= gate
    i = np.argmax(np.abs(delta))
    print(f"phi = {phi} deg, {len(eta)} lines, eta {eta[0]:.2f}..{eta[-1]:.2f}")
    print(f"  total X0 range installed: {ta.min():.5f} .. {ta.max():.5f}")
    print(f"  plane detector columns in overlay: {plane_cols}; their max X0 = "
          f"{max([b[c].max() for c in plane_cols] or [0]):.3e}")
    print(f"  max |delta total| = {abs(delta[i]):.3e} X0 at eta = {eta[i]:.3f} (air-displacement bound there "
          f"{bound[i]:.3e}); mean delta = {delta.mean():.3e}")
    print(f"  lines with |delta| > 0: {(np.abs(delta) > 0).sum()}")
    print(f"  max |delta| over the {len(common)} pre-existing detector columns: {col_diff:.3e}")
    print(f"  delta in 'Others': max |.| = {np.abs(b['Others'] - a['Others']).max():.3e}")
    print(f"  max delta (must be <= 0): {delta.max():.3e}; lines with 4-decimal rounding flip (info): {flips}")
    print(f"  gate (no added material, removal within the Air-displacement bound): {'ok' if gate else 'FAIL'}")
print(f"\nStep 9d zero-material gate: {'PASS' if ok_all else 'FAIL'}")
sys.exit(0 if ok_all else 1)
