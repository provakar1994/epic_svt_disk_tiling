#!/usr/bin/env python3
"""Step 12: check the exported corrugation flats against the delivered <disk>_rows.csv.

Run inside the EIC container (needs ROOT):
    python3 inspect_svt_corrugation_step12.py <export.root> <tiling scenario dir>

Expected geometry, computed here independently of the C++ builder:
  * Rows sorted by y; the carbon flat at row_y lies on the surface opposite facet_z,
    i.e. on the side sign(center_z - facet_z) of the disk center (metadata z_center_mm).
  * One boundary flat beyond each end row at row_y -/+ half_pitch, opposite surface.
  * Each 45 deg web is centered halfway between adjacent flats; its y span is
    W = (h - t)/tan(45 deg) = 6.0 - 0.15 = 5.85 mm (mid-surface).
    Flat i reaches (spacing - W)/2 toward each neighbour (sharp-corner apex).
  * Rounded bends (R = 5 mm) trim T = R*tan(22.5 deg) = 2.0711 mm from each flat end
    that joins a web. The exported Box pieces are these straight flats.
Exported flats are named <layer>_frame_flat<row_index>_<n>; a flat may be split into
several x pieces (disk boundary / openings) and at y = 0, so pieces are merged per flat.
Boundary flats (row_index <= -1000) that lie outside the disk may be absent.
Pass: every expected flat inside the disk is found, y edges agree within 1 um and the
surface side agrees.
"""
import math
import re
import sys
from pathlib import Path

import ROOT

H_MM, T_CF_MM, THETA_DEG, BEND_R_MM = 6.0, 0.15, 45.0, 5.0
WEB_Y_MM = (H_MM - T_CF_MM) / math.tan(math.radians(THETA_DEG))
TRIM_MM = BEND_R_MM * math.tan(math.radians(THETA_DEG) / 2.0)
TOL_MM = 1.0e-3

LAYER_TO_SHORT = {
    "OuterTrackerEndcapN_disk4": "ED4", "OuterTrackerEndcapN_disk3": "ED3",
    "OuterTrackerEndcapN_disk2": "ED2", "MiddleTrackerEndcapN_disk1": "ED1",
    "InnerTrackerEndcapN_disk1": "ED0", "InnerTrackerEndcapP_disk1": "HD0",
    "MiddleTrackerEndcapP_disk1": "HD1", "OuterTrackerEndcapP_disk2": "HD2",
    "OuterTrackerEndcapP_disk3": "HD3", "OuterTrackerEndcapP_disk4": "HD4",
}
MODULE_RE = re.compile(r"^(A6|B5|B6)[01][01]$")
FLAT_RE = re.compile(r"^(?P<layer>\w+?_disk\d)_frame_flat(?P<row>-?\d+)_\d+$")


def read_metadata(path):
    values = {}
    for line in open(path):
        line = line.split("#")[0]
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def expected_flats(scenario_dir, short):
    """Straight flats {row_index: (y_lo, y_hi, side, outer_radius)} in mm, global y."""
    hd3 = "HD3" if (scenario_dir / "HD3_rows.csv").exists() else "HD3b"
    key = hd3 if short == "HD3" else short
    meta = read_metadata(scenario_dir / f"{key}_metadata.txt")
    center_z = float(meta["z_center_mm"])
    lines = (scenario_dir / f"{key}_rows.csv").read_text().split()
    header = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        rec = dict(zip(header, line.split(",")))
        side = 1 if center_z - float(rec["facet_z_mm"]) > 0 else -1
        rows.append([int(rec["row_index"]), float(rec["row_y_mm"]), side, float(rec["half_pitch_mm"])])
    rows.sort(key=lambda r: r[1])
    low, high = rows[0], rows[-1]
    rows.insert(0, [-1000 - low[0], low[1] - low[3], -low[2], low[3]])
    rows.append([-1000 - high[0], high[1] + high[3], -high[2], high[3]])

    flats = {}
    for i, (row_index, y, side, _) in enumerate(rows):
        spacing_low = y - rows[i - 1][1] if i > 0 else rows[i + 1][1] - y
        spacing_high = rows[i + 1][1] - y if i + 1 < len(rows) else y - rows[i - 1][1]
        y_lo = y - (spacing_low - WEB_Y_MM) / 2.0 + (TRIM_MM if i > 0 else 0.0)
        y_hi = y + (spacing_high - WEB_Y_MM) / 2.0 - (TRIM_MM if i + 1 < len(rows) else 0.0)
        flats[row_index] = (y_lo, y_hi, side)
    return flats, center_z, float(meta["outer_radius_mm"])


def exported_flats(geo):
    """Merge exported flat pieces: {(layer, row_index): [y_lo, y_hi, z_center]} in mm."""
    found = {}

    def walk(node, matrix):
        # matrix = global transform of this node (product of all parent placements)
        vol = node.GetVolume()
        name = vol.GetName()
        if MODULE_RE.match(name):
            return  # module assemblies contain no frame pieces; skip their ~1.5M daughters
        match = FLAT_RE.match(name)
        if match:
            translation = matrix.GetTranslation()  # cm
            y_c, z_c = translation[1] * 10.0, translation[2] * 10.0
            dy = vol.GetShape().GetDY() * 10.0
            key = (match["layer"], int(match["row"]))
            entry = found.setdefault(key, [y_c - dy, y_c + dy, z_c])
            entry[0] = min(entry[0], y_c - dy)
            entry[1] = max(entry[1], y_c + dy)
            return
        for i in range(node.GetNdaughters()):
            child = node.GetDaughter(i)
            child_matrix = ROOT.TGeoHMatrix(matrix)
            child_matrix.Multiply(child.GetMatrix())
            walk(child, child_matrix)

    walk(geo.GetTopNode(), ROOT.TGeoHMatrix())
    return found


def main():
    root_file, scenario_dir = sys.argv[1], Path(sys.argv[2])
    f = ROOT.TFile.Open(root_file)
    geo = next(k.ReadObj() for k in f.GetListOfKeys() if k.GetClassName() == "TGeoManager")
    found = exported_flats(geo)
    n_flats = n_bad = 0
    max_dev = 0.0
    for layer, short in LAYER_TO_SHORT.items():
        flats, center_z, radius = expected_flats(scenario_dir, short)
        dev_disk = 0.0
        missing = []
        for row_index, (y_lo, y_hi, side) in flats.items():
            got = found.get((layer, row_index))
            if got is None:
                # Allowed only for boundary flats fully outside the disk.
                if row_index <= -1000 and min(abs(y_lo), abs(y_hi)) >= radius:
                    continue
                missing.append(row_index)
                continue
            n_flats += 1
            dev = max(abs(got[0] - y_lo), abs(got[1] - y_hi))
            got_side = 1 if got[2] - center_z > 0 else -1
            if dev > TOL_MM or got_side != side:
                n_bad += 1
                print(f"  MISMATCH {short} flat {row_index}: expected y {y_lo:.4f}..{y_hi:.4f} side {side},"
                      f" got {got[0]:.4f}..{got[1]:.4f} side {got_side}")
            dev_disk = max(dev_disk, dev)
        extra = sorted(r for (l, r) in found if l == layer and r not in flats)
        n_bad += len(missing) + len(extra)
        max_dev = max(max_dev, dev_disk)
        widths = [hi - lo for lo, hi, _ in flats.values()]
        print(f"{short}: expected {len(flats)} flats (straight width {min(widths):.3f}..{max(widths):.3f} mm),"
              f" exported {sum(1 for (l, _) in found if l == layer)}, max |dy| {dev_disk * 1000:.3f} um,"
              f" missing {missing}, unexpected {extra}")
    verdict = "PASS" if n_bad == 0 else "FAIL"
    print(f"{verdict}: {n_flats} flats checked on 10 disks, max |dy| {max_dev * 1000:.3f} um, {n_bad} problems")
    sys.exit(0 if n_bad == 0 else 1)


if __name__ == "__main__":
    main()
