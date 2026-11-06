#!/usr/bin/env python3
"""Compare two disk_material_summary.json files (from disk_material_map.py) disk by disk.

Usage: compare_disk_material_summaries.py A.json labelA B.json labelB
Prints the mean x/X0 on the annulus per disk and per material, and the relative change B/A - 1.
Both summaries are track-weighted means over geantinos whose disk-plane intersection lies on
the annulus, with eta-uniform sampling, so they are comparable even if the eta ranges differ.
Statistical precision of the per-disk mean is ~0.1 % relative for >5e5 tracks (not computed here).
"""
import json
import sys


def main():
    a_file, a_lab, b_file, b_lab = sys.argv[1:5]
    a, b = json.load(open(a_file)), json.load(open(b_file))
    print(f"{'disk':5s} {a_lab + ' [%X0]':>14s} {b_lab + ' [%X0]':>14s} {'change':>9s}   tracks {a_lab}/{b_lab}")
    for disk in a:
        if disk not in b:
            continue
        va, vb = a[disk]["mean_x0_pct"], b[disk]["mean_x0_pct"]
        print(f"{disk:5s} {va:14.4f} {vb:14.4f} {100 * (vb / va - 1):+8.2f} %   "
              f"{a[disk]['tracks_on_annulus']}/{b[disk]['tracks_on_annulus']}")
    print("\nper material: mean x/X0 contribution on the annulus [% X0] and relative change")
    for disk in a:
        if disk not in b or "materials" not in a[disk] or "materials" not in b[disk]:
            continue
        print(f"-- {disk}")
        mats = sorted(set(a[disk]["materials"]) | set(b[disk]["materials"]),
                      key=lambda m: -a[disk]["materials"].get(m, {}).get("mean_x0_pct", 0.0))
        for m in mats:
            va = a[disk]["materials"].get(m, {}).get("mean_x0_pct", 0.0)
            vb = b[disk]["materials"].get(m, {}).get("mean_x0_pct", 0.0)
            ch = f"{100 * (vb / va - 1):+8.2f} %" if va > 0 else "     new"
            print(f"   {m:22s} {va:9.5f} {vb:9.5f} {ch}")


if __name__ == "__main__":
    main()
