#!/usr/bin/env python3
"""Per-plane validation of refplanes extraction shards (smoke test or campaign).

For every shard and disk of its side, prints:
  reached     primaries with plane_reached
  si_hit      primaries with >= 1 TrackerEndcapHits hit on the disk
  hit_no_pl   primaries with a silicon hit but no accepted plane crossing
              (should be ~0: every primary that reaches the disk crosses the plane)
  multi       primaries with > 1 accepted crossing of the plane (loopers)
  max|dz|     max |plane hit z - z_plane_mm| [mm] (plane thickness / 2 expected)
  r range     min/max beam-axis radius of first crossings vs plane rmin/rmax [mm]
  off_pl      first crossings outside the plane annulus about its centre
              (v2 map: r_inner <= |p - centre| <= r_outer, 0.01 mm tolerance;
              must be 0; planes need not be centred on the beam axis)
  p_pl/p_gen  median and min of |p at plane| / generated |p| (median ~1; the
              minimum can be well below 1 after an interaction upstream)
  t>0         all first-crossing times positive
  |dr| med/90 true point at disk (straight from plane, own momentum) minus
              mean silicon hit, transverse [mm], primaries with both
plus the shard-level counters (total, accepted, dropped-not-primary,
secondary-flagged, other-side plane hits).
Usage: validate_refplanes_shards_20261106.py EXTRACTED_ROOT PLANE_MAP
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from reduce_disk_acceptance import DISKS

root, plane_map = Path(sys.argv[1]), pd.read_csv(sys.argv[2]).set_index("disk")
problems = 0
for path in sorted(root.glob("*/particles_*.npz")):
    with np.load(path) as stored:
        s = {k: stored[k] for k in stored.files}
    meta = json.loads(str(s["metadata_json"]))
    side = meta["side"]
    print(f"=== {path.parent.name}/{path.name}: {len(s['p_GeV'])} primaries, plane collection present "
          f"{meta['plane_collection_present']}, plane hits total {meta['plane_hits_total']}, accepted "
          f"{meta['plane_hits_accepted']}, dropped (not primary) {meta['plane_hits_dropped_not_primary']}, "
          f"secondary-flagged {meta['plane_hits_secondary_flagged']}, other side {meta['plane_hits_other_side']}")
    print(f"  {'disk':4s} {'reached':>7s} {'si_hit':>6s} {'hit_no_pl':>9s} {'multi':>5s} {'max|dz|':>8s} "
          f"{'r_min..r_max (plane rmin..rmax)':>34s} {'off_pl':>6s} {'p_pl/p_gen med,min':>18s} {'t>0':>4s} {'|dr| med/90':>12s}")
    p_gen = s["p_GeV"].astype(float)
    for i, (disk, *_rest) in enumerate(DISKS[side]):
        row = plane_map.loc[disk]
        bit = np.uint8(1 << i)
        reached = (s["plane_mask"] & bit) != 0
        hit = (s["hit_mask"] & bit) != 0
        x, y, z, t = (s[k][:, i].astype(float) for k in ("plane_x_mm", "plane_y_mm", "plane_z_mm", "plane_t_ns"))
        px, py, pz = (s[k][:, i].astype(float) for k in ("plane_px_GeV", "plane_py_GeV", "plane_pz_GeV"))
        r = np.hypot(x, y)[reached]
        ratio = (np.sqrt(px**2 + py**2 + pz**2) / p_gen)[reached]
        dz = np.abs(z[reached] - row.z_plane_mm)
        centre = (row.get("center_x_mm", 0.0), row.get("center_y_mm", 0.0))
        r_inner = row.get("r_inner_about_center_mm", row.rmin_mm)
        r_outer = row.get("r_outer_about_center_mm", row.rmax_mm)
        d_centre = np.hypot(x - centre[0], y - centre[1])[reached]
        off_plane = int(((d_centre < r_inner - 0.01) | (d_centre > r_outer + 0.01)).sum())
        both = reached & hit
        step = row.z_disk_mm - z
        dr = np.hypot(x + step * px / pz - s["mean_hit_x_mm"][:, i], y + step * py / pz - s["mean_hit_y_mm"][:, i])[both]
        hit_no_plane = int((hit & ~reached).sum())
        text = lambda a, f: f"{f(a):.3f}" if len(a) else "-"
        print(f"  {disk:4s} {reached.sum():7d} {hit.sum():6d} {hit_no_plane:9d} "
              f"{int((s['plane_crossings'][:, i] > 1).sum()):5d} {text(dz, np.max):>8s} "
              f"{text(r, np.min):>8s}..{text(r, np.max):<8s} ({row.rmin_mm:g}..{row.rmax_mm:g}) {off_plane:6d} "
              f"{text(ratio, np.median):>8s},{text(ratio, np.min):<8s} "
              f"{str(bool(np.all(t[reached] > 0))):>5s} "
              f"{text(dr, np.median):>6s}/{text(dr, lambda a: np.percentile(a, 90)):<6s}")
        problems += hit_no_plane + off_plane
        if len(dz) and dz.max() > 0.5:
            problems += 1
print(f"Total problems (silicon hit without plane + off-plane first crossings + |dz| > 0.5 mm): {problems}")
print("OVERALL:", "PASS" if problems == 0 else "FAIL")
