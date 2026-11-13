#!/usr/bin/env python3
"""Step 14b: prove from the simulated hits which SVT endcap tiling scenario was simulated.

For every TrackerEndcapHits hit (all particles, endcap systems only) test whether its (x, y, z) lies
inside an active sensor box of
  rsu6    geometry/active_silicon_rectangles_step13_rsu6.csv (dump of the rsu6 overlay, 154800 boxes)
  rsu_opt geometry/active_silicon_rectangles_step13.csv      (dump of the installed rsu_opt, 152628 boxes)
Boxes are axis-aligned in x/y (checked); inside = |x - xc| <= half_x + TOL, |y - yc| <= half_y + TOL,
|z - zc| <= half_z + TOL with TOL = 0.005 mm (Geant4 hit positions are pre/post-step means inside
the 14 um silicon). A hit from the rsu6 geometry is inside an rsu6 box by construction (fraction 1);
the rsu_opt boxes differ (other module positions/lengths), so a clearly lower fraction is expected.
Gate: rsu6 fraction == 1 and rsu_opt fraction < 0.99 over all files.
Usage: python3 check_scenario_hits_rsu6.py SIM_FILE [SIM_FILE ...]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from mc_tracking_hits import read_mc_tracking_hits

HERE = Path(__file__).resolve().parent
TOL = 0.005
BOXES = {"rsu6": HERE / "geometry/active_silicon_rectangles_step13_rsu6.csv",
         "rsu_opt": HERE / "geometry/active_silicon_rectangles_step13.csv"}
ENDCAP_SYSTEMS = {68, 69, 70, 77, 78, 79}


def load_boxes(path):
    b = pd.read_csv(path)
    axis_aligned = (np.isclose(b.x0_mm, b.x3_mm) & np.isclose(b.x1_mm, b.x2_mm)
                    & np.isclose(b.y0_mm, b.y1_mm) & np.isclose(b.y2_mm, b.y3_mm))
    assert axis_aligned.all(), f"{path}: non axis-aligned boxes"
    b["xc"] = (b.x0_mm + b.x1_mm) / 2
    b["yc"] = (b.y0_mm + b.y2_mm) / 2
    b["hx"] = (b.x1_mm - b.x0_mm).abs() / 2
    b["hy"] = (b.y2_mm - b.y0_mm).abs() / 2
    return b


def inside_any(hits, boxes):
    """Boolean array: hit inside at least one box (boxes pre-selected by |dz| < 1 mm)."""
    result = np.zeros(len(hits), dtype=bool)
    bz = boxes.z_center_mm.to_numpy()
    for i, (x, y, z) in enumerate(hits[["x_mm", "y_mm", "z_mm"]].to_numpy()):
        sel = np.abs(bz - z) < 1.0
        if not sel.any():
            continue
        b = boxes[sel]
        result[i] = np.any((np.abs(x - b.xc.to_numpy()) <= b.hx.to_numpy() + TOL)
                           & (np.abs(y - b.yc.to_numpy()) <= b.hy.to_numpy() + TOL)
                           & (np.abs(z - b.z_center_mm.to_numpy()) <= b.half_z_mm.to_numpy() + TOL))
    return result


def main():
    boxes = {name: load_boxes(path) for name, path in BOXES.items()}
    for name, b in boxes.items():
        print(f"{name}: {len(b)} boxes from {BOXES[name]}")
    totals = {name: [0, 0] for name in boxes}
    for f in sys.argv[1:]:
        hits = read_mc_tracking_hits(f, collections=["TrackerEndcapHits"], primary_only=False)["hits"]
        hits = hits[hits.system.isin(ENDCAP_SYSTEMS)].reset_index(drop=True)
        line = f"{Path(f).name}: {len(hits)} endcap hits"
        for name, b in boxes.items():
            n_in = int(inside_any(hits, b).sum())
            totals[name][0] += n_in
            totals[name][1] += len(hits)
            line += f" | inside {name} boxes {n_in} ({n_in / max(len(hits), 1):.4f})"
        print(line)
    frac = {name: k / max(n, 1) for name, (k, n) in totals.items()}
    print("TOTAL: " + " | ".join(f"{name} {k}/{n} = {frac[name]:.4f}" for name, (k, n) in totals.items()))
    ok = frac["rsu6"] == 1.0 and frac["rsu_opt"] < 0.99 and totals["rsu6"][1] > 0
    print(f"Scenario-from-hits gate (rsu6 == 1, rsu_opt < 0.99): {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
