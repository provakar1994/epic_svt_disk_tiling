#!/usr/bin/env python3
"""Compare the reference-plane hit efficiency of two analysis result directories with configurable
inputs and labels (Step 14b, 2026-11-13). Default: acceptance_v4_step13 (20261110_ES/rsu_opt,
results/refplane_efficiency_v5) vs acceptance_v4_step13_rsu6 (20261110_ES/rsu6,
results/refplane_efficiency_v5_rsu6).

Reuses parse_summary / load_quantities / check_summary_against_csv from compare_refplane_v3_v4.py
(unchanged), so the quantities, the summary.txt cross-check (0.01 points) and the CSV inputs are the
same as for the v3 vs v4 comparison. Per (vertex, disk, quantity):
  diff = e_B - e_A [points],  err = sqrt(e_A (1 - e_A) / N_A + e_B (1 - e_B) / N_B),  pull = diff / err.

SEEDS: acceptance_v4_step13_rsu6 uses the same --random.seed values as acceptance_v4_step13, but npsim
(without --random.enableEventSeed) draws the gun AND the transport from one random stream, so the
primaries are identical only up to the first event whose transport differs between the geometries
(checked in the Step 14b smoke test: events 0-1 identical, then different). The two samples are
therefore effectively independent and the independent-sample error above is appropriate. The script
prints on how many disks the fid denominators coincide (equal only for truly paired primaries).
Usage:
  python3 compare_refplane_scenarios.py [--a DIR] [--b DIR] [--label-a L] [--label-b L]
         [--vertices 0 100 -100] [--out-prefix PATH]
Writes PATH.csv (default: B dir/compare_<label-a>_vs_<label-b>) and prints the tables.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from compare_refplane_v3_v4 import (DISK_ORDER, LABELS, check_summary_against_csv, load_quantities,
                                    parse_summary)

HERE = Path(__file__).resolve().parent
QUANTITIES = ["fid", "active", "nomargin", "fid_family_A", "fid_family_B", "active_family_A",
              "active_family_B", "sl_fid_reached_fraction", "sl_fid_straight_line_eff"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", type=Path, default=HERE / "results/refplane_efficiency_v5")
    parser.add_argument("--b", type=Path, default=HERE / "results/refplane_efficiency_v5_rsu6")
    parser.add_argument("--label-a", default="rsu_opt")
    parser.add_argument("--label-b", default="rsu6")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0, 100, -100], choices=sorted(LABELS))
    parser.add_argument("--out-prefix", type=Path)
    args = parser.parse_args()
    la, lb = args.label_a, args.label_b
    out_prefix = args.out_prefix or args.b / f"compare_{la}_vs_{lb}"

    merged_all = []
    for vz in args.vertices:
        tables = {}
        for key, label, root in (("A", la, args.a), ("B", lb, args.b)):
            vertex_dir = root / f"vz_{LABELS[vz]}mm"
            summary = parse_summary(vertex_dir / "summary.txt")
            tables[key] = load_quantities(vertex_dir, vz)
            check_summary_against_csv(summary, tables[key], vertex_dir / "summary.txt")
            print(f"[{label}] {vertex_dir}")
            for line in summary["header"]:
                if line.split(":")[0] in ("extracted root", "rows csv", "active outline", "plane map"):
                    print(f"    {line}")
        merged = tables["A"].merge(tables["B"], on=["vertex_z_mm", "disk", "quantity"], suffixes=("_A", "_B"))
        for key in ("A", "B"):
            merged[f"eff_{key}"] = merged[f"k_{key}"] / merged[f"N_{key}"]
        var = sum(merged[f"eff_{k}"] * (1 - merged[f"eff_{k}"]) / merged[f"N_{k}"] for k in ("A", "B"))
        merged["diff_pts"] = 100 * (merged.eff_B - merged.eff_A)
        merged["diff_err_indep_pts"] = 100 * np.sqrt(var)
        merged["pull_indep"] = merged.diff_pts / merged.diff_err_indep_pts.replace(0, np.nan)
        merged_all.append(merged)

        fid = merged[merged.quantity == "fid"]
        n_same = int((fid.N_A == fid.N_B).sum())
        print(f"\n=== vertex z = {vz:+d} mm: efficiency [%] {la} -> {lb}, diff +- independent-sample "
              f"binomial error [points] ===")
        print(f"fid denominators identical on {n_same}/{len(fid)} disks "
              f"(identical only for truly paired primaries; not expected with npsim's shared random stream)")
        for quantity in QUANTITIES:
            sub = merged[merged.quantity == quantity].set_index("disk")
            sub = sub.reindex([d for d in DISK_ORDER if d in sub.index])
            if not len(sub):
                continue
            print(f"\n{quantity}:")
            for disk, r in sub.iterrows():
                note = f"   {la} {r.note_A}; {lb} {r.note_B}" if quantity.startswith("fid_family_A") else ""
                print(f"  {disk}  {la} {100 * r.eff_A:6.2f} (N={r.N_A:>8d})  {lb} {100 * r.eff_B:6.2f} "
                      f"(N={r.N_B:>8d})  diff {r.diff_pts:+6.2f} +- {r.diff_err_indep_pts:4.2f}  "
                      f"pull {r.pull_indep:+6.1f}{note}")

    result = pd.concat(merged_all, ignore_index=True)
    result = result.rename(columns={c: c.replace("_A", f"_{la}").replace("_B", f"_{lb}")
                                    for c in result.columns if c.endswith(("_A", "_B"))})
    out_csv = out_prefix.with_suffix(".csv")
    if out_csv.exists():
        raise SystemExit(f"ERROR: {out_csv} exists; move it to tmp/retained first")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_csv, index=False)
    print(f"\nCaveats: each side uses its own row-family table and active-silicon dump (see the header lines "
          f"above); samples are statistically independent (see SEEDS in the docstring).")
    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
