#!/usr/bin/env python3
"""Compare the endcap tracking results of two campaigns at vz = 0 with configurable inputs and labels
(Step 14b, 2026-11-13). Same three sections as compare_v3_v4_20261113.py (unchanged; its load() and
binomial_diff() are reused). Defaults: A = acceptance_v4_step13 (20261110_ES/rsu_opt, Step 13 map),
B = acceptance_v4_step13_rsu6 (20261110_ES/rsu6, rsu6 Step 13 map).
  1. sigma(B)/sigma(A) per quantity and PWG eta bin (median, min, max over p bins); pull widths.
  2. efficiency per p bin and side, 1 < |eta| < 3.8: diff = e_B - e_A,
     err = sqrt(eA (1 - eA) / NA + eB (1 - eB) / NB)  (independent-sample formula).
  3. forward dip 1.6 < eta < 1.85 and references 1.35-1.55, 2.1-2.4 (p > 2 GeV, MCParticles[0]).
SEEDS: the rsu6 campaign uses the same --random.seed values as rsu_opt, but npsim draws gun and
transport from one random stream, so the primaries diverge after the first event whose transport
differs (Step 14b smoke test); the samples are effectively independent and the independent-sample
error is appropriate. The "N equal" column shows whether the generated counts per bin coincide.
Usage:
  python compare_tracking_scenarios_20261113.py [--summary-a CSV] [--summary-b CSV] [--cache-a DIR]
      [--cache-b DIR] [--label-a L] [--label-b L] [--files-per-config 50]
"""
import argparse

import numpy as np
import pandas as pd

from compare_v3_v4_20261113 import DIP_WINDOWS, HERE, P_EDGES, REDUCED, SIDES, binomial_diff, load


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--summary-a", default=f"{HERE}/out/v4_pwg_vz0_50files/summary_v4_pwg_vz0_50files.csv")
    parser.add_argument("--summary-b", default=f"{HERE}/out/v4_rsu6_pwg_vz0_50files/summary_v4_rsu6_pwg_vz0_50files.csv")
    parser.add_argument("--cache-a", default=f"{REDUCED}/reduced_acceptance_v4_step13")
    parser.add_argument("--cache-b", default=f"{REDUCED}/reduced_acceptance_v4_step13_rsu6")
    parser.add_argument("--label-a", default="rsu_opt")
    parser.add_argument("--label-b", default="rsu6")
    parser.add_argument("--files-per-config", type=int, default=50)
    args = parser.parse_args()
    la, lb = args.label_a, args.label_b
    pd.set_option("display.width", 200)
    print(f"{la} summary: {args.summary_a}\n{lb} summary: {args.summary_b}")
    print(f"{la} cache:   {args.cache_a}\n{lb} cache:   {args.cache_b}\n")

    a = pd.read_csv(args.summary_a)
    b = pd.read_csv(args.summary_b)
    keys = [c for c in a.columns if c in ("side", "eta_lo", "eta_hi", "p_lo", "p_hi", "quantity")]
    merged = a.merge(b, on=keys, suffixes=("_A", "_B"))
    merged["ratio"] = merged["sigma_B"] / merged["sigma_A"]
    print(f"sigma({lb})/sigma({la}) per quantity and eta bin, median and range over p bins:")
    print(merged.groupby(["quantity", "side", "eta_lo", "eta_hi"])["ratio"].agg(["median", "min", "max", "count"])
          .round(3).to_string())
    print(f"\nPull widths (median over p bins), {la} -> {lb} (columns sigma_A = {la}, sigma_B = {lb}):")
    pulls = merged[merged["quantity"].str.startswith("pull")]
    print(pulls.groupby(["quantity", "side", "eta_lo", "eta_hi"])[["sigma_A", "sigma_B"]].median().round(3).to_string())

    tables = {}
    for name, cache in (("A", args.cache_a), ("B", args.cache_b)):
        for side, pattern in SIDES.items():
            tables[name, side], n_files = load(cache, pattern, args.files_per_config)
            print(f"\n[{la if name == 'A' else lb} {side}] {n_files} cache files, {len(tables[name, side])} primaries", end="")
    print()

    print(f"\nEfficiency per p bin, 1 < |eta| < 3.8, all primaries (diff = {lb} - {la}, "
          f"independent-sample binomial error):")
    print(f"  {'side':8s} {'p bin [GeV]':12s} {'N ' + la:>11s} {'eff':>7s} {'N ' + lb:>11s} {'eff':>7s} "
          f"{'diff':>8s} {'err':>7s}  N equal")
    for side in SIDES:
        edges = list(zip(P_EDGES[:-1], P_EDGES[1:])) + [(P_EDGES[0], P_EDGES[-1])]
        for lo, hi in edges:
            counts = []
            for name in ("A", "B"):
                t = tables[name, side]
                sel = t[(np.abs(t["eta_mc"]) > 1.0) & (np.abs(t["eta_mc"]) < 3.8) & (t["p_mc"] >= lo) & (t["p_mc"] < hi)]
                counts += [sel["matched"].sum(), len(sel)]
            ea, eb, diff, err = binomial_diff(*counts)
            label = f"{lo:g}-{hi:g}" if (lo, hi) != (P_EDGES[0], P_EDGES[-1]) else "all"
            print(f"  {side:8s} {label:12s} {counts[1]:11d} {ea:7.4f} {counts[3]:11d} {eb:7.4f} {diff:+8.4f} "
                  f"{err:7.4f}  {'yes' if counts[1] == counts[3] else 'NO'}")

    print("\nForward dip and reference windows (p > 2 GeV, primary = MCParticles[0], vz = 0):")
    for lo, hi in DIP_WINDOWS:
        counts = []
        for name in ("A", "B"):
            t = tables[name, "forward"]
            sel = t[(t["mc_index"] == 0) & (t["eta_mc"] > lo) & (t["eta_mc"] < hi) & (t["p_mc"] > 2)]
            counts += [sel["matched"].sum(), len(sel)]
        ea, eb, diff, err = binomial_diff(*counts)
        print(f"  {lo}-{hi}: {la} n = {counts[1]:7d} eff = {ea:.4f} | {lb} n = {counts[3]:7d} eff = {eb:.4f} "
              f"| diff {diff:+.4f} +- {err:.4f}")


if __name__ == "__main__":
    main()
