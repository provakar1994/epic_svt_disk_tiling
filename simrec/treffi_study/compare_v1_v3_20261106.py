#!/usr/bin/env python3
"""Compare acceptance_v1 (Step 8m map) and acceptance_v3_refplanes (Step 8q tracking-only map)
endcap tracking results: resolution and pull-width ratios per (side, eta bin) from the PWG-binned
summary CSVs, and the efficiency in the forward-dip window from the cached per-primary tables.
Usage: python compare_v1_v3_20261106.py > out/v1_vs_v3_pwg_vz0_50files/compare_v1_v3.txt
"""
import glob
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SUMMARY = {
    "v1": f"{HERE}/out/pwg_vz0_50files/summary_pwg_vz0_50files.csv",
    "v3": f"{HERE}/out/v3_pwg_vz0_50files/summary_v3_pwg_vz0_50files.csv",
}
CACHE = {
    "v1": "/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_acceptance_v1",
    "v3": "/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_acceptance_v3_refplanes",
}

v1 = pd.read_csv(SUMMARY["v1"])
v3 = pd.read_csv(SUMMARY["v3"])
keys = [c for c in v1.columns if c in ("side", "eta_lo", "eta_hi", "p_lo", "p_hi", "quantity")]
merged = v1.merge(v3, on=keys, suffixes=("_v1", "_v3"))
merged["ratio"] = merged["sigma_v3"] / merged["sigma_v1"]
print("sigma(v3)/sigma(v1) per quantity and eta bin, median and range over p bins:")
summary = merged.groupby(["quantity", "side", "eta_lo", "eta_hi"])["ratio"].agg(["median", "min", "max", "count"])
print(summary.round(3).to_string())
print("\nPull widths (median over p bins), v1 -> v3:")
pulls = merged[merged["quantity"].str.startswith("pull")]
print(pulls.groupby(["quantity", "side", "eta_lo", "eta_hi"])[["sigma_v1", "sigma_v3"]].median().round(3).to_string())


def load(cache_dir, pattern):
    tables = []
    for path in sorted(glob.glob(os.path.join(cache_dir, pattern))):
        with np.load(path) as d:
            tables.append(pd.DataFrame({k: d[k] for k in ("eta_mc", "p_mc", "matched", "mc_index")}))
    t = pd.concat(tables)
    return t[t["mc_index"] == 0]


print("\nForward dip and reference windows (p > 2 GeV, primary = MCParticles[0], vz = 0):")
for name in ("v1", "v3"):
    t = load(CACHE[name], "*vz_000mm_eta_p0p6_to_p3p8*.npz")
    for lo, hi in ((1.35, 1.55), (1.6, 1.85), (2.1, 2.4)):
        sel = t[(t["eta_mc"] > lo) & (t["eta_mc"] < hi) & (t["p_mc"] > 2)]
        print(f"  {name}  {lo}-{hi}: n = {len(sel):7d}  efficiency = {sel['matched'].mean():.4f}")
