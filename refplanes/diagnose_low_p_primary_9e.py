#!/usr/bin/env python3
"""Step 9e diagnostic (host, tracking env): primary-linked plane hits with |p_hit|/|p_gen| < 0.9 and
no producedBySecondary bit. For each such primary, list all its plane hits in time order
(disk, z, |p|, time, quality) and its MCParticle endpoint/momentum at endpoint, to see whether the
momentum drop happens between planes (an interaction the primary survives) or is a mis-attribution.
Usage: python3 diagnose_low_p_primary_9e.py SIM_ROOT"""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "simrec" / "acc_study"))
from mc_tracking_hits import read_mc_tracking_hits  # noqa: E402

BIT = 1 << 30
pm = {(int(r["system"]), int(r["layer"])): r["disk"] for r in csv.DictReader(open(here / "plane_map.csv"))}
d = read_mc_tracking_hits(sys.argv[1], collections=["SVTDiskRefPlaneHits", "TrackerEndcapHits"], primary_only=False)
parts, hits = d["particles"], d["hits"]
key = ["event_entry", "mc_index"]
prim = parts[parts.generator_status == 1].set_index(key)
h = hits.join(prim[["p_GeV"]].rename(columns={"p_GeV": "p_gen"}), on=key, how="inner")
h["p_hit"] = np.sqrt(h.px_GeV ** 2 + h.py_GeV ** 2 + h.pz_GeV ** 2)
h["ratio"] = h.p_hit / h.p_gen
h["by_sec"] = (h.quality.astype(np.int64) & BIT) != 0
h["where"] = [pm.get((int(s), int(l)), f"si{int(s)}/{int(l)}") if c == "SVTDiskRefPlaneHits" else f"Si:{int(s)}/{int(l)}"
              for s, l, c in zip(h.system, h.layer, h.hit_collection)]
sel = h[(h.hit_collection == "SVTDiskRefPlaneHits") & (h.ratio < 0.9) & ~h.by_sec]
print(f"{len(sel)} clean primary plane hits with ratio < 0.9")
cols = ["where", "z_mm", "time_ns", "p_hit", "ratio", "energy_deposit_GeV", "by_sec"]
end_cols = [c for c in prim.columns if c.startswith(("endpoint_", "simulator_status"))]
for (ev, mi), _ in sel.groupby(key):
    print(f"\n--- event {ev}, mc_index {mi}: p_gen = {prim.loc[(ev, mi), 'p_GeV']:.3f} GeV, eta = {prim.loc[(ev, mi), 'eta']:.3f}")
    print("    MCParticle", {c: round(float(prim.loc[(ev, mi), c]), 3) for c in end_cols})
    with pd.option_context("display.width", 200):
        print(h[(h.event_entry == ev) & (h.mc_index == mi)].sort_values("time_ns")[cols].to_string(index=False))
