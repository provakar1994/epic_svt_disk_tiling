#!/usr/bin/env python3
"""Convert the 20261110_ES/rsu_opt per-disk <disk>_rows.csv files into the single row-family
table read by analyze_refplane_efficiency.py --rows-csv (acceptance_v4_step13, 2026-11-13).

Why: the v3 analysis read 20261001_ES/SVT_endcap_corrugation_rows_33_36.csv with columns
  disk,row_index,row_y_mm,surface_offset_mm,family,pitch_mm,flat_width_mm
(the analysis uses only disk, family, row_y_mm, pitch_mm). The Step 13 geometry (EPIC 78ade4686)
reads the delivered per-disk files instead, schema
  disk_id,row_index,row_type,x_outer_mm,row_y_mm,facet_z_mm,half_pitch_mm
which has no family column.

Conversion (one output row per delivered row; the delivered files are only read):
  disk              file prefix (ED0..ED4, HD0..HD4)
  row_y_mm          copied (global EPIC y; the builder SiEndcapModuleTracker_geo.cpp uses it
                    directly as y on both sides; checked below against the built sensors)
  pitch_mm          2 * half_pitch_mm  (same-surface flat pitch; 33 or 36 mm)
  family            A if pitch_mm == 36, B if pitch_mm == 33 (anything else stops the script)
  surface_offset_mm z_center_mm (from <disk>_metadata.txt) - facet_z_mm, as in the builder
  flat_width_mm     empty (not in the delivery; not used by the analysis)
  row_type, x_outer_mm, facet_z_mm, half_pitch_mm  copied for traceability
The analysis then defines the family-A y region of a disk as
  [min(row_y - pitch/4), max(row_y + pitch/4)) over its A rows (= row_y +/- half_pitch/2).

Check (optional, --active-csv): every sensitive box of the built Step 13 geometry should sit over a
row channel, i.e. its y centre should be close to row_y +/- (sensor half height). The script prints,
per disk, the median and 99th percentile of |box y centre - nearest row_y| using y ("same") and -y
("flipped"). With the right convention, "same" is ~4.6 mm (half an RSU) with a narrow spread; on
disks without y-mirror symmetry "flipped" is worse.

Usage:
  python3 make_row_families_20261110.py OUTPUT_CSV [--active-csv geometry/active_silicon_rectangles_step13.csv]
Refuses to overwrite OUTPUT_CSV.
"""
import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EPIC_DIR = HERE.parents[2]
TILING_DIR = EPIC_DIR / "compact/tracking/silicon_disks_tiling/20261110_ES/rsu_opt"
DISKS = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
FAMILY_BY_PITCH = {36.0: "A", 33.0: "B"}


def read_metadata_value(path: Path, key: str) -> float:
    for line in path.read_text().splitlines():
        if line.split("=")[0].strip() == key:
            return float(line.split("=", 1)[1].split("#")[0])
    raise ValueError(f"{key} not found in {path}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--tiling-dir", type=Path, default=TILING_DIR)
    parser.add_argument("--active-csv", type=Path, help="optional y-convention check")
    args = parser.parse_args()
    if args.output_csv.exists():
        raise SystemExit(f"ERROR: {args.output_csv} exists; move it to tmp/retained first")

    tables = []
    print(f"Tiling directory: {args.tiling_dir}")
    for disk in DISKS:
        rows_path = args.tiling_dir / f"{disk}_rows.csv"
        meta_path = args.tiling_dir / f"{disk}_metadata.txt"
        print(f"  {sha256(rows_path)}  {rows_path.name}")
        rows = pd.read_csv(rows_path)
        z_center = read_metadata_value(meta_path, "z_center_mm")
        pitch = (2.0 * rows.half_pitch_mm).round(6)
        unknown = sorted(set(pitch) - set(FAMILY_BY_PITCH))
        if unknown:
            raise ValueError(f"{disk}: pitch values {unknown} are neither 33 nor 36 mm")
        out = pd.DataFrame({
            "disk": disk, "row_index": rows.row_index, "row_y_mm": rows.row_y_mm,
            "surface_offset_mm": (z_center - rows.facet_z_mm).round(4),
            "family": pitch.map(FAMILY_BY_PITCH), "pitch_mm": pitch, "flat_width_mm": np.nan,
            "row_type": rows.row_type, "x_outer_mm": rows.x_outer_mm,
            "facet_z_mm": rows.facet_z_mm, "half_pitch_mm": rows.half_pitch_mm,
        })
        tables.append(out)
        family_a = out[out.family == "A"]
        a_range = "none"
        if len(family_a):
            a_range = (f"[{(family_a.row_y_mm - family_a.pitch_mm / 4).min():.2f}, "
                       f"{(family_a.row_y_mm + family_a.pitch_mm / 4).max():.2f})")
        print(f"    {disk}: {len(out)} rows ({(out.family == 'A').sum()} A / {(out.family == 'B').sum()} B; "
              f"{(out.row_type == 'BLOCKED').sum()} BLOCKED), z_center {z_center:g}, family-A y range {a_range}")
    table = pd.concat(tables, ignore_index=True)

    if args.active_csv:
        boxes = pd.read_csv(args.active_csv, usecols=["disk", "y0_mm", "y1_mm", "y2_mm", "y3_mm"])
        print(f"\ny-convention check against {args.active_csv} (sha256 {sha256(args.active_csv)[:12]}...):")
        print("  |box y centre - nearest row_y| [mm]: median / 99th percentile, same y vs flipped y")
        for disk in DISKS:
            y_centre = boxes.loc[boxes.disk == disk, ["y0_mm", "y1_mm", "y2_mm", "y3_mm"]].mean(axis=1).to_numpy()
            row_y = np.sort(table.loc[table.disk == disk, "row_y_mm"].to_numpy())
            result = []
            for sign in (+1, -1):
                distance = np.min(np.abs(sign * y_centre[:, None] - row_y[None, :]), axis=1)
                result.append(f"{np.median(distance):6.3f} / {np.percentile(distance, 99):6.3f}")
            print(f"  {disk}: {len(y_centre):6d} boxes   same {result[0]}   flipped {result[1]}")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output_csv, index=False)
    print(f"\nWrote {args.output_csv} ({len(table)} rows), sha256 {sha256(args.output_csv)}")


if __name__ == "__main__":
    main()
