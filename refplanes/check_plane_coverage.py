#!/usr/bin/env python3
"""Plane coverage of the silicon (host, conda env 'tracking').

For every TrackerEndcapHits hit linked to a generated primary (generatorStatus == 1), test whether
its (x, y) lies on the plane region of that disk:  r_in <= hypot(x - cx, y - cy) <= r_out.
A hit in the plane HOLE (closer than r_in to the annulus centre) is silicon the plane cannot see at
that (x, y). Reported per disk: number of primaries with a silicon hit on the disk, the fraction of
them with at least one hit in the hole, and the smallest beam-axis radius of a silicon hit.
Evaluated for v2 (refplanes/plane_map.csv) and, for comparison, v1 (centred annuli,
tmp/retained/2026-11-06/refplanes_v1/plane_map.csv: centre 0, r_in = rmin_mm).
The silicon hit sits 6-11 mm downstream of the plane, so this is a geometric proxy; the direct test
is the smoke check E (silicon hit without plane hit).
Usage: python3 check_plane_coverage.py SIM_ROOT [SIM_ROOT ...]
"""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "simrec" / "acc_study"))
from mc_tracking_hits import read_mc_tracking_hits  # noqa: E402

SILICON_DISKS = {(68, 1): "ED0", (69, 1): "ED1", (70, 2): "ED2", (70, 3): "ED3", (70, 4): "ED4",
                 (77, 1): "HD0", (78, 1): "HD1", (79, 2): "HD2", (79, 3): "HD3", (79, 4): "HD4"}


def load_maps():
    v2 = {r["disk"]: (float(r["center_x_mm"]), float(r["center_y_mm"]), float(r["r_inner_about_center_mm"]),
                      float(r["r_outer_about_center_mm"])) for r in csv.DictReader(open(here / "plane_map.csv"))}
    v1_path = here.parent / "tmp" / "retained" / "2026-11-06" / "refplanes_v1" / "plane_map.csv"
    v1 = {r["disk"]: (0.0, 0.0, float(r["rmin_mm"]), float(r["rmax_mm"])) for r in csv.DictReader(open(v1_path))}
    return {"v1": v1, "v2": v2}


maps = load_maps()
frames = []
for f in sys.argv[1:]:
    d = read_mc_tracking_hits(f, collections=["TrackerEndcapHits"], primary_only=True)
    h = d["hits"]
    h = h.assign(disk=[SILICON_DISKS.get((int(s), int(l)), "?") for s, l in zip(h.system, h.layer)],
                 source=Path(f).name)
    frames.append(h[["source", "event_entry", "mc_index", "disk", "x_mm", "y_mm"]])
    print(f"{Path(f).name}: {len(h)} primary-linked silicon hits")
hits = pd.concat(frames, ignore_index=True)
hits["r_mm"] = np.hypot(hits.x_mm, hits.y_mm)
rows = []
for disk in [f"ED{i}" for i in range(5)] + [f"HD{i}" for i in range(5)]:
    hd = hits[hits.disk == disk]
    n_prim = hd[["source", "event_entry", "mc_index"]].drop_duplicates().shape[0]
    row = dict(disk=disk, primaries=n_prim, hits=len(hd), si_rmin_mm=hd.r_mm.min() if len(hd) else np.nan)
    for ver, m in maps.items():
        cx, cy, rin, rout = m[disk]
        rho = np.hypot(hd.x_mm - cx, hd.y_mm - cy)
        in_hole = hd[rho < rin]
        outside = hd[rho > rout]
        k = in_hole[["source", "event_entry", "mc_index"]].drop_duplicates().shape[0]
        row[f"{ver}_hole_primaries"] = k
        row[f"{ver}_hole_frac"] = k / n_prim if n_prim else np.nan
        row[f"{ver}_beyond_rout_hits"] = len(outside)
        row[f"{ver}_max_hole_depth_mm"] = float((rin - rho[rho < rin]).max()) if len(in_hole) else 0.0
    rows.append(row)
table = pd.DataFrame(rows)
with pd.option_context("display.width", 250, "display.float_format", "{:.5f}".format):
    print(table.to_string(index=False))
print("\nhole_frac = fraction of primaries with a silicon hit on the disk that have >= 1 silicon hit inside the")
print("plane hole; max_hole_depth = deepest such hit below the plane inner edge (about the annulus centre).")
