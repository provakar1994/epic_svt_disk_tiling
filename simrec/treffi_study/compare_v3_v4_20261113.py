#!/usr/bin/env python3
"""Compare acceptance_v3_refplanes (Step 8q geometry + Step 8q map) and acceptance_v4_step13
(Step 13 geometry + Step 13 map) endcap tracking results at vz = 0. Modelled on
compare_v1_v3_20261106.py (same resolution/pull and forward-dip sections), plus the efficiency
per momentum bin with the difference and its binomial error.

1. Resolutions and pull widths: sigma(v4)/sigma(v3) per quantity and PWG eta bin (median, min,
   max over the p bins) from the PWG-binned summary CSVs; pull widths median over p bins.
2. Efficiency per p bin, per side, 1 < |eta| < 3.8 and p edges 0.5, 1, 2, 5, 10, 20 GeV (the
   "efficiency check" table of endcap_tracking_performance.py), from the cached per-primary tables:
     eff = matched / generated,  diff = eff_v4 - eff_v3,
     err(diff) = sqrt(e3 (1 - e3) / N3 + e4 (1 - e4) / N4)   (independent samples).
3. Forward dip 1.6 < eta < 1.85 and the references 1.35-1.55 and 2.1-2.4, p > 2 GeV, primary =
   MCParticles[0], forward vz = 0 sample (same selection as compare_v1_v3_20261106.py), with the
   same binomial difference error.
Usage (defaults are the v3 and v4 50-file outputs):
  python compare_v3_v4_20261113.py [--summary-v3 CSV] [--summary-v4 CSV] [--cache-v3 DIR] [--cache-v4 DIR]
      [--files-per-config 50] > out/v3_vs_v4_pwg_vz0_50files/compare_v3_v4.txt
--files-per-config limits the cache files read per side (first N chunks, sorted, cached at full
statistics only), so both samples use the same chunks as the summary CSVs.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REDUCED = "/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study"
SIDES = {"backward": "*vz_000mm_eta_m3p8_to_m0p6_chunk_*_n100000.npz",
         "forward": "*vz_000mm_eta_p0p6_to_p3p8_chunk_*_n100000.npz"}
P_EDGES = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
DIP_WINDOWS = ((1.35, 1.55), (1.6, 1.85), (2.1, 2.4))


def load(cache_dir, pattern, files_per_config):
    paths = sorted(glob.glob(os.path.join(cache_dir, pattern)))[:files_per_config]
    if not paths:
        raise SystemExit(f"ERROR: no cache files {pattern} in {cache_dir}")
    tables = []
    for path in paths:
        with np.load(path) as d:
            tables.append(pd.DataFrame({k: d[k] for k in ("eta_mc", "p_mc", "matched", "mc_index")}))
    return pd.concat(tables, ignore_index=True), len(paths)


def binomial_diff(k3, n3, k4, n4):
    e3, e4 = k3 / n3, k4 / n4
    return e3, e4, e4 - e3, np.sqrt(e3 * (1 - e3) / n3 + e4 * (1 - e4) / n4)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--summary-v3", default=f"{HERE}/out/v3_pwg_vz0_50files/summary_v3_pwg_vz0_50files.csv")
    parser.add_argument("--summary-v4", default=f"{HERE}/out/v4_pwg_vz0_50files/summary_v4_pwg_vz0_50files.csv")
    parser.add_argument("--cache-v3", default=f"{REDUCED}/reduced_acceptance_v3_refplanes")
    parser.add_argument("--cache-v4", default=f"{REDUCED}/reduced_acceptance_v4_step13")
    parser.add_argument("--files-per-config", type=int, default=50)
    args = parser.parse_args()
    pd.set_option("display.width", 200)
    print(f"v3 summary: {args.summary_v3}\nv4 summary: {args.summary_v4}")
    print(f"v3 cache:   {args.cache_v3}\nv4 cache:   {args.cache_v4}\n")

    # 1. Resolutions and pull widths.
    v3 = pd.read_csv(args.summary_v3)
    v4 = pd.read_csv(args.summary_v4)
    keys = [c for c in v3.columns if c in ("side", "eta_lo", "eta_hi", "p_lo", "p_hi", "quantity")]
    merged = v3.merge(v4, on=keys, suffixes=("_v3", "_v4"))
    merged["ratio"] = merged["sigma_v4"] / merged["sigma_v3"]
    print("sigma(v4)/sigma(v3) per quantity and eta bin, median and range over p bins:")
    summary = merged.groupby(["quantity", "side", "eta_lo", "eta_hi"])["ratio"].agg(["median", "min", "max", "count"])
    print(summary.round(3).to_string())
    print("\nPull widths (median over p bins), v3 -> v4:")
    pulls = merged[merged["quantity"].str.startswith("pull")]
    print(pulls.groupby(["quantity", "side", "eta_lo", "eta_hi"])[["sigma_v3", "sigma_v4"]].median().round(3).to_string())

    # 2. and 3. need the per-primary caches.
    tables = {}
    for name, cache in (("v3", args.cache_v3), ("v4", args.cache_v4)):
        for side, pattern in SIDES.items():
            tables[name, side], n_files = load(cache, pattern, args.files_per_config)
            print(f"\n[{name} {side}] {n_files} cache files, {len(tables[name, side])} primaries", end="")
    print()

    print("\nEfficiency per p bin, 1 < |eta| < 3.8, all primaries (diff = v4 - v3, binomial error):")
    print(f"  {'side':8s} {'p bin [GeV]':12s} {'N v3':>9s} {'eff v3':>7s} {'N v4':>9s} {'eff v4':>7s} {'diff':>8s} {'err':>7s}")
    for side in SIDES:
        edges = list(zip(P_EDGES[:-1], P_EDGES[1:])) + [(P_EDGES[0], P_EDGES[-1])]
        for lo, hi in edges:
            counts = []
            for name in ("v3", "v4"):
                t = tables[name, side]
                sel = t[(np.abs(t["eta_mc"]) > 1.0) & (np.abs(t["eta_mc"]) < 3.8) & (t["p_mc"] >= lo) & (t["p_mc"] < hi)]
                counts += [sel["matched"].sum(), len(sel)]
            e3, e4, diff, err = binomial_diff(*counts)
            label = f"{lo:g}-{hi:g}" if (lo, hi) != (P_EDGES[0], P_EDGES[-1]) else "all"
            print(f"  {side:8s} {label:12s} {counts[1]:9d} {e3:7.4f} {counts[3]:9d} {e4:7.4f} {diff:+8.4f} {err:7.4f}")

    print("\nForward dip and reference windows (p > 2 GeV, primary = MCParticles[0], vz = 0):")
    for lo, hi in DIP_WINDOWS:
        counts = []
        for name in ("v3", "v4"):
            t = tables[name, "forward"]
            sel = t[(t["mc_index"] == 0) & (t["eta_mc"] > lo) & (t["eta_mc"] < hi) & (t["p_mc"] > 2)]
            counts += [sel["matched"].sum(), len(sel)]
        e3, e4, diff, err = binomial_diff(*counts)
        print(f"  {lo}-{hi}: v3 n = {counts[1]:7d} eff = {e3:.4f} | v4 n = {counts[3]:7d} eff = {e4:.4f} "
              f"| diff {diff:+.4f} +- {err:.4f}")


if __name__ == "__main__":
    main()
