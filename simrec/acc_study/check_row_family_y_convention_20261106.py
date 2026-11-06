#!/usr/bin/env python3
"""Check that SVT_endcap_corrugation_rows_33_36.csv row_y_mm is global EPIC y
on BOTH sides (the ED disks are built with reflect="true"), and print the
signed-y extent of the 36 mm (family A) region of disks 2-4.

Method (z=0 sample acceptance_v1, first 10 shards per side, primaries with
exactly one silicon hit on the disk): rows alternate surface_offset_mm = +/-3
mm, so the measured |z_hit| - |z_disk| follows the CSV row pattern in y.
Predict the offset at each hit's y from the CSV (row band = row_y +/- pitch/4)
using y ("same") and using -y ("flipped"). Offsets are +/-3 mm, so everywhere
flipped = +same (region R2) or -same (region R1). The sign convention of the
offset relative to |z| is not known a priori, so only the RELATIVE sign
matters: if CSV y = global y, corr(same, dz) has the same sign in R1 and R2;
if CSV y = -global y, the signs are opposite. Mirror-symmetric disks (R2
empty or R1 empty) cannot be tested.
Run via: python3 check_row_family_y_convention_20261106.py > logs/check_row_family_y_convention_20261106.txt
"""
from pathlib import Path
import numpy as np
import pandas as pd
from reduce_disk_acceptance import DISKS, configuration_name

here = Path(__file__).resolve().parent
rows = pd.read_csv(here.parents[2] / "compact/tracking/silicon_disks_tiling/20261001_ES/SVT_endcap_corrugation_rows_33_36.csv")
rows["disk"] = rows.disk.replace({"HD3b": "HD3"})


def predicted_offset(y, disk_rows):
    out = np.full(len(y), np.nan)
    for row in disk_rows.itertuples():
        out[np.abs(y - row.row_y_mm) < row.pitch_mm / 4] = row.surface_offset_mm
    return out


for side in DISKS:
    shards = sorted((here / "extracted/acceptance_v1" / configuration_name(0, side)).glob("*.npz"))[:10]
    data = [np.load(s) for s in shards]
    hy = np.concatenate([d["mean_hit_y_mm"] for d in data]).astype(float)
    hz = np.concatenate([d["mean_hit_z_mm"] for d in data]).astype(float)
    hc = np.concatenate([d["hit_count"] for d in data])
    for index, (disk, _, _, z_disk) in enumerate(DISKS[side]):
        disk_rows = rows[rows.disk == disk]
        single = hc[:, index] == 1
        y, dz = hy[single, index], np.abs(hz[single, index]) - abs(z_disk)
        same, flipped = predicted_offset(y, disk_rows), predicted_offset(-y, disk_rows)
        valid = ~np.isnan(same) & ~np.isnan(flipped)
        region_1 = valid & (flipped == -same)
        region_2 = valid & (flipped == same)
        line = f"{disk}: single-hit primaries {single.sum():7d}; R1 n={region_1.sum():6d}, R2 n={region_2.sum():6d}:"
        if region_1.sum() > 200 and region_2.sum() > 200:
            c1 = np.corrcoef(same[region_1], dz[region_1])[0, 1]
            c2 = np.corrcoef(same[region_2], dz[region_2])[0, 1]
            line += f" corr(same,dz) R1 = {c1:+.3f}, R2 = {c2:+.3f}"
            line += "  -> CSV y = global y" if c1 * c2 > 0 else "  -> CSV y = -global y (!)"
        else:
            line += " pattern mirror-symmetric in y, sign not testable"
        print(line)
        family_a = disk_rows[disk_rows.family == "A"]
        if len(family_a):
            low = (family_a.row_y_mm - family_a.pitch_mm / 4).min()
            high = (family_a.row_y_mm + family_a.pitch_mm / 4).max()
            print(f"    family A (36 mm) region: {low:.2f} <= y < {high:.2f} mm "
                  f"({len(family_a)} rows); B (33 mm) elsewhere")
