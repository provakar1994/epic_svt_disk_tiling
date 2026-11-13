#!/usr/bin/env python3
"""Step 13d: check the hard-coded DISKS table in scripts/subdetector_tests/disk_material_map.py
against compact/tracking/definitions_craterlake.xml at EPIC HEAD, and against the delivered
20261110_ES/rsu_opt disk geometry and module z positions.

Read-only. Reports mismatches; does not fix anything.
Usage (conda env "tracking", outside eic-shell):
  python proj_svt_disk_tiling/logs/check_disk_table_step13.py > proj_svt_disk_tiling/logs/check_disk_table_step13.txt

Conventions:
  - XML lengths are evaluated in mm (mm = 1, cm = 10).
  - Table opening radii exclude the 5 mm bake-out buffer, so the XML radius minus
    Beampipe_bakeout_buffer is compared.
  - Negative-side (ED) disks: z is compared as -<zmin>, the XML centre x values as written
    ("detector-aligned layer coordinates"), as the table stores them.
  - Module z: z_sensor_mm from <disk>_modules.csv (as supplied, no offsets since Step 11b),
    compared with the scan window |z - z_disk| < dz (default dz = 5 mm).
"""
import csv
import importlib.util
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

EPIC = Path("/global/cfs/cdirs/m3763/pdatta/epic")
TILING = EPIC / "compact/tracking/silicon_disks_tiling/20261110_ES/rsu_opt"
DZ_MM = 5.0
TOL = 1e-6

# table name -> (XML prefix, z sign)
XML_PREFIX = {
    "ED4": ("TrackerEndcapNDisk4", -1), "ED3": ("TrackerEndcapNDisk3", -1),
    "ED2": ("TrackerEndcapNDisk2", -1), "ED1": ("TrackerEndcapNDisk1", -1),
    "ED0": ("InnerTrackerEndcapN", -1), "HD0": ("InnerTrackerEndcapP", +1),
    "HD1": ("TrackerEndcapPDisk1", +1), "HD2": ("TrackerEndcapPDisk2", +1),
    "HD3": ("TrackerEndcapPDisk3", +1), "HD4": ("TrackerEndcapPDisk4", +1),
}
DISK_ID = {n: i for i, n in enumerate(["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"])}


def xml_constants():
    """Constants of definitions_craterlake.xml at HEAD (from git, not the working tree)."""
    text = subprocess.run(["git", "-C", str(EPIC), "show", "HEAD:compact/tracking/definitions_craterlake.xml"],
                          check=True, capture_output=True, text=True).stdout
    raw = {c.get("name"): c.get("value") for c in ET.fromstring(text).iter("constant")}
    cache = {}

    def value(name):
        if name not in cache:
            expr = raw[name]
            names = {n: value(n) for n in set(re.findall(r"[A-Za-z_]\w*", expr))
                     if n in raw}
            cache[name] = float(eval(expr, {"mm": 1.0, "cm": 10.0, "m": 1000.0, "max": max, "abs": abs,
                                            "min": min, "math": math}, names))
        return cache[name]
    return value


def load_table():
    spec = importlib.util.spec_from_file_location("dmm", EPIC / "scripts/subdetector_tests/disk_material_map.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.DISKS


def main():
    head = subprocess.run(["git", "-C", str(EPIC), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    print(f"EPIC HEAD={head}")
    print(f"tiling={TILING.relative_to(EPIC)}  scan dz={DZ_MM} mm")
    val = xml_constants()
    buf = val("Beampipe_bakeout_buffer")
    delivered = {r["label"]: r for r in csv.DictReader(open(TILING / "disk_geometry_used.csv"))}
    n_bad = 0
    for name, z, rmax, (lx, lr), (hx, hr) in load_table():
        p, sign = XML_PREFIX[name]
        zmin_key = f"{p}_zmin" if not p.startswith("InnerTrackerEndcapN") else "InnerTrackerEndcapN_zmin"
        xml_row = dict(z=sign * val(zmin_key), rmax=val(f"{p}_rmax"),
                       lx=val(f"{p}_lepton_center_x"), lr=val(f"{p}_lepton_radius") - buf,
                       hx=val(f"{p}_hadron_center_x"), hr=val(f"{p}_hadron_radius") - buf)
        ly, hy = val(f"{p}_lepton_center_y"), val(f"{p}_hadron_center_y")
        tab_row = dict(z=z, rmax=rmax, lx=lx, lr=lr, hx=hx, hr=hr)
        diffs = [f"{k}: table {tab_row[k]:g} vs XML {xml_row[k]:g}"
                 for k in tab_row if abs(tab_row[k] - xml_row[k]) > TOL]
        if abs(ly) > TOL or abs(hy) > TOL:
            diffs.append(f"nonzero opening centre y in XML (lepton {ly:g}, hadron {hy:g}); table assumes y = 0")
        d = delivered[name]
        if abs(float(d["z_center_m"]) * 1000 - z) > TOL or abs(float(d["outer_radius_m"]) * 1000 - rmax) > TOL:
            diffs.append(f"delivery disk_geometry_used.csv z={float(d['z_center_m'])*1000:g} "
                         f"r_out={float(d['outer_radius_m'])*1000:g}")
        mods = list(csv.DictReader(open(TILING / f"{name}_modules.csv")))
        zs = [float(m["z_sensor_mm"]) for m in mods]
        zb = [float(m["z_baseplate_mm"]) for m in mods]
        # delivered z is engineer frame; compare |z| with |table z| (sign checked separately)
        zs_rel = [abs(v) - abs(z) for v in zs]
        out = sum(abs(v) > DZ_MM for v in zs_rel)
        sign_ok = all(math.copysign(1, v) == math.copysign(1, z) for v in zs)
        status = "OK" if not diffs else "MISMATCH"
        n_bad += bool(diffs)
        print(f"{name}: {status}  z={z:g} rmax={rmax:g} lepton=({lx:g},{lr:g}) hadron=({hx:g},{hr:g})")
        for line in diffs:
            print(f"    {line}")
        print(f"    modules={len(mods)} disk_id={set(int(m['disk_id']) for m in mods)} (expected {DISK_ID[name]})"
              f"  z_sensor-|z_disk| in [{min(zs_rel):+.3f}, {max(zs_rel):+.3f}] mm"
              f"  z_baseplate in [{min(zb):.3f}, {max(zb):.3f}]  outside dz window: {out}"
              f"  z sign matches table: {sign_ok}")
    print(f"RESULT: {'table matches definitions_craterlake.xml at HEAD' if n_bad == 0 else f'{n_bad} disk(s) mismatch'}")


if __name__ == "__main__":
    main()
