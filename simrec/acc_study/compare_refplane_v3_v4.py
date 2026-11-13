#!/usr/bin/env python3
"""Compare the reference-plane hit efficiency of acceptance_v3_refplanes (Step 8q geometry,
results/refplane_efficiency_v4 = newest v3 presentation; numbers identical to v1-v3) with
acceptance_v4_step13 (Step 13 geometry, results/refplane_efficiency_v5). 2026-11-13.

Inputs per vertex directory vz_<label>mm/ of each result:
  summary.txt                (headline table; parsed and used as a cross-check + provenance)
  integrated_efficiency.csv  (exact numerator/denominator of fid, active, nomargin)
  family_AB_efficiency.csv   (family A = 36 mm rows, B = 33 mm rows, disks 2-4, all momenta)
  decomposition_vs_p.csv     (sl_fid acceptance, all momenta: reached fraction and the old
                              straight-line "hit / generated" efficiency of this sample)
Every quantity is a binomial fraction e = k/N. The two campaigns are independent samples, so
  diff = e_v4 - e_v3,   err(diff) = sqrt(e_v3 (1 - e_v3) / N_v3 + e_v4 (1 - e_v4) / N_v4)
(in percentage points). "pull" = diff / err(diff).
Caveats printed with the table:
  - family A/B regions come from different row tables (v3: 20261001 combined table, v4:
    20261110_ES/rsu_opt per-disk rows); the y ranges are printed and differ by < 1 mm;
  - active outlines come from different geometry dumps (v3: EPIC 311634084, v4: Step 13);
  - the summary.txt headline values must agree with the CSVs to 0.01 points, otherwise the
    script stops.
Usage:
  python3 compare_refplane_v3_v4.py [--v3 DIR] [--v4 DIR] [--vertices 0 100 -100] [--out-prefix PATH]
Writes PATH.csv (one row per vertex, disk, quantity) and prints the tables (tee them to PATH.txt).
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LABELS = {0: "000", 100: "p100", -100: "m100"}
DISK_ORDER = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
SUMMARY_LINE = re.compile(r"^(ED\d|HD\d)\s+((?:\s*\d+\.\d+\+-\d+\.\d+ \(N=\d+\)){3})\s*$")
SUMMARY_ENTRY = re.compile(r"(\d+\.\d+)\+-\d+\.\d+ \(N=(\d+)\)")


def parse_summary(path: Path) -> dict:
    """Integrated fid/active/nomargin table and provenance lines from summary.txt."""
    text = path.read_text().splitlines()
    header = [line for line in text[:8] if ":" in line]
    table = {}
    for line in text:
        match = SUMMARY_LINE.match(line)
        if match and match.group(1) not in table:      # first table = integrated efficiency
            values = SUMMARY_ENTRY.findall(match.group(2))
            table[match.group(1)] = {sel: (float(v), int(n)) for sel, (v, n) in
                                     zip(("fid", "active", "nomargin"), values)}
    if len(table) != 10:
        raise ValueError(f"{path}: found {len(table)} disks in the integrated table, expected 10")
    return {"header": header, "integrated": table}


def load_quantities(vertex_dir: Path, vz: int) -> pd.DataFrame:
    """One row per (disk, quantity) with numerator k, denominator N and an optional note."""
    rows = []
    integrated = pd.read_csv(vertex_dir / "integrated_efficiency.csv")
    for r in integrated.itertuples():
        rows.append((r.disk, r.selection, r.numerator, r.denominator, ""))
    family = pd.read_csv(vertex_dir / "family_AB_efficiency.csv")
    family = family[(family.p_bin == "all") & family.selection.isin(["fid", "active"])]
    for r in family.itertuples():
        rows.append((r.disk, f"{r.selection}_family_{r.family[0]}", r.numerator, r.denominator,
                     f"A y range {r.family_A_y_range_mm}"))
    decomposition = pd.read_csv(vertex_dir / "decomposition_vs_p.csv")
    decomposition = decomposition[(decomposition.acceptance == "sl_fid") & (decomposition.p_bin == "all")]
    for r in decomposition.itertuples():
        rows.append((r.disk, "sl_fid_reached_fraction", r.reached, r.generated, ""))
        rows.append((r.disk, "sl_fid_straight_line_eff", r.hit_any, r.generated, ""))
    table = pd.DataFrame(rows, columns=["disk", "quantity", "k", "N", "note"])
    table["vertex_z_mm"] = vz
    return table


def check_summary_against_csv(summary: dict, table: pd.DataFrame, path: Path) -> None:
    for disk, values in summary["integrated"].items():
        for sel, (pct, n) in values.items():
            row = table[(table.disk == disk) & (table.quantity == sel)].iloc[0]
            if int(row.N) != n or abs(100 * row.k / row.N - pct) > 0.0051:
                raise ValueError(f"{path}: {disk} {sel} summary {pct}% N={n} vs CSV "
                                 f"{100 * row.k / row.N:.4f}% N={row.N}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--v3", type=Path, default=HERE / "results/refplane_efficiency_v4")
    parser.add_argument("--v4", type=Path, default=HERE / "results/refplane_efficiency_v5")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0, 100, -100], choices=sorted(LABELS))
    parser.add_argument("--out-prefix", type=Path, help="write PATH.csv (default: v4 dir/compare_v3_v4)")
    args = parser.parse_args()
    out_prefix = args.out_prefix or args.v4 / "compare_v3_v4"

    pd.set_option("display.width", 250)
    merged_all = []
    for vz in args.vertices:
        tables = {}
        for name, root in (("v3", args.v3), ("v4", args.v4)):
            vertex_dir = root / f"vz_{LABELS[vz]}mm"
            summary = parse_summary(vertex_dir / "summary.txt")
            tables[name] = load_quantities(vertex_dir, vz)
            check_summary_against_csv(summary, tables[name], vertex_dir / "summary.txt")
            print(f"[{name}] {vertex_dir}")
            for line in summary["header"]:
                if line.split(":")[0] in ("extracted root", "rows csv", "active outline", "plane map"):
                    print(f"    {line}")
        merged = tables["v3"].merge(tables["v4"], on=["vertex_z_mm", "disk", "quantity"], suffixes=("_v3", "_v4"))
        for name in ("v3", "v4"):
            merged[f"eff_{name}"] = merged[f"k_{name}"] / merged[f"N_{name}"]
        var = sum(merged[f"eff_{n}"] * (1 - merged[f"eff_{n}"]) / merged[f"N_{n}"] for n in ("v3", "v4"))
        merged["diff_pts"] = 100 * (merged.eff_v4 - merged.eff_v3)
        merged["diff_err_pts"] = 100 * np.sqrt(var)
        merged["pull"] = merged.diff_pts / merged.diff_err_pts.replace(0, np.nan)
        merged_all.append(merged)

        print(f"\n=== vertex z = {vz:+d} mm: efficiency [%] v3 -> v4, diff +- binomial error [points] ===")
        for quantity in ["fid", "active", "nomargin", "fid_family_A", "fid_family_B", "active_family_A",
                         "active_family_B", "sl_fid_reached_fraction", "sl_fid_straight_line_eff"]:
            sub = merged[merged.quantity == quantity].set_index("disk")
            sub = sub.reindex([d for d in DISK_ORDER if d in sub.index])
            if not len(sub):
                continue
            print(f"\n{quantity}:")
            for disk, r in sub.iterrows():
                note = ""
                if quantity.startswith("fid_family_A"):
                    note = f"   v3 {r.note_v3}; v4 {r.note_v4}"
                print(f"  {disk}  v3 {100 * r.eff_v3:6.2f} (N={r.N_v3:>8d})  v4 {100 * r.eff_v4:6.2f} "
                      f"(N={r.N_v4:>8d})  diff {r.diff_pts:+6.2f} +- {r.diff_err_pts:4.2f}  "
                      f"pull {r.pull:+6.1f}{note}")

    result = pd.concat(merged_all, ignore_index=True)
    columns = ["vertex_z_mm", "disk", "quantity", "k_v3", "N_v3", "eff_v3", "k_v4", "N_v4", "eff_v4",
               "diff_pts", "diff_err_pts", "pull", "note_v3", "note_v4"]
    out_csv = out_prefix.with_suffix(".csv")
    if out_csv.exists():
        raise SystemExit(f"ERROR: {out_csv} exists; move it to tmp/retained first")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    result[columns].to_csv(out_csv, index=False)
    print(f"\nCaveats: family A/B regions use different row tables (v3 20261001, v4 20261110_ES/rsu_opt); "
          f"active outlines use different geometry dumps (v3 EPIC 311634084, v4 Step 13).")
    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
