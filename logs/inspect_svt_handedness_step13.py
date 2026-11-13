#!/usr/bin/env python3
"""Step 13: check module handedness/orientation of the exported tiling modules against the
provider's convention (ES_material/20261016-Module Definitions.pdf and
ES_material/20261110/transition/module_cad_export.py).

Run inside the EIC container (needs ROOT):
    python3 inspect_svt_handedness_step13.py <export.root> <tiling scenario dir>

Provider convention, in the delivery (engineer) frame (module_cad_export.py):
  local x = from LEC toward REC     -> global sign sx = -sign(x_origin)  (toward the disk centre)
  local y = toward the bridge FPC   -> global sign sy = +sign(y_origin)  (away from y = 0)
  local z = away from the carbon    -> global sign sz = -face_sign*facing_sign
            (face_sign FRONT(+1) if z_baseplate < z_center, facing_sign OUTWARD(+1))
  POSITIVE chirality <=> sx*sy*sz = +1, NEGATIVE <=> -1 (checked against type_id by the provider).
EPIC conversion used by the builder (Step 7s): x_EPIC = -x_engineer, y, z unchanged.
A pure x reflection keeps every direction rule above except that the parity flips, so
the EPIC-built part must be the mirror partner: parity_EPIC = -parity_source.

Measured per placed module in global EPIC coordinates (centroids of the daughter volumes):
  rec_dir    = sign(x_rec - x_lec)
  fpc_dir    = sign(y_fpc - y_active)   (bridge-FPC Kapton pieces)
  normal     = sign(z_cu - z_carbon)
  parity     = rec_dir * fpc_dir * normal  (det of the (x, y, z) local frame, axis-aligned)
"""
import csv
import math
import re
import sys
from collections import Counter
from pathlib import Path

import ROOT

LAYER_TO_SHORT = {
    "OuterTrackerEndcapN_layer4": "ED4", "OuterTrackerEndcapN_layer3": "ED3",
    "OuterTrackerEndcapN_layer2": "ED2", "MiddleTrackerEndcapN_layer1": "ED1",
    "InnerTrackerEndcapN_layer1": "ED0", "InnerTrackerEndcapP_layer1": "HD0",
    "MiddleTrackerEndcapP_layer1": "HD1", "OuterTrackerEndcapP_layer2": "HD2",
    "OuterTrackerEndcapP_layer3": "HD3", "OuterTrackerEndcapP_layer4": "HD4",
}
MODULE_RE = re.compile(r"^(A6|B5|B6)[01][01]$")


def sign(value):
    return 1 if value > 0 else -1


def read_metadata(path):
    values = {}
    for line in open(path):
        line = line.split("#")[0]
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def source_modules(scenario_dir, short):
    """Delivered modules of one disk with the provider's expected directions (engineer frame)."""
    key = short
    if short == "HD3" and not (scenario_dir / "HD3_modules.csv").exists():
        key = "HD3b"
    center_z = float(read_metadata(scenario_dir / f"{key}_metadata.txt")["z_center_mm"])
    catalog = {r["type_id"]: r for r in csv.DictReader(open(scenario_dir / "catalog.csv"))}
    mods = []
    for r in csv.DictReader(open(scenario_dir / f"{key}_modules.csv")):
        x, y = float(r["x_origin_mm"]), float(r["y_origin_mm"])
        face_sign = 1 if float(r["z_baseplate_mm"]) < center_z else -1
        facing = catalog[r["type_id"]]["facing"]
        chir = catalog[r["type_id"]]["chirality"]
        facing_sign = 1 if facing == "OUTWARD" else -1
        sx, sy, sz = -sign(x), sign(y), -face_sign * facing_sign
        label = 1 if chir in ("POSITIVE", "LEFT") else -1   # 20261001 LEFT == POSITIVE
        mods.append(dict(row=int(r["row_index"]), mod=int(r["mod_index"]), type=r["type_id"],
                         x=x, y=y, sx=sx, sy=sy, sz=sz, parity=sx * sy * sz, label=label,
                         face="FRONT" if face_sign > 0 else "BACK", facing=facing))
    return mods


def centroid(points):
    n = len(points)
    return [sum(p[i] for p in points) / n for i in range(3)] if n else None


def module_measurements(geo):
    """{short: [measurement dict]} for every placed tiling module, global mm."""
    out = {}

    def walk(node, matrix, short):
        vol = node.GetVolume()
        name = vol.GetName()
        for key, value in LAYER_TO_SHORT.items():
            if node.GetName().startswith(key + "_"):
                short = value
        if MODULE_RE.match(name):
            parts = {"lec": [], "rec": [], "active": [], "fpc": [], "asic": [], "cu": [], "carbon": []}
            for i in range(node.GetNdaughters()):
                d = node.GetDaughter(i)
                m = ROOT.TGeoHMatrix(matrix)
                m.Multiply(d.GetMatrix())
                t = m.GetTranslation()
                p = (t[0] * 10.0, t[1] * 10.0, t[2] * 10.0)
                dn = d.GetVolume().GetName()
                if dn.endswith("_lec"):
                    parts["lec"].append(p)
                elif dn.endswith("_rec"):
                    parts["rec"].append(p)
                elif dn.endswith("_active_si"):
                    parts["active"].append(p)
                elif "bridge_fpc_kapton" in dn:
                    parts["fpc"].append(p)
                elif dn.endswith("_ancasic"):
                    parts["asic"].append(p)
                elif dn.endswith("_cu"):
                    parts["cu"].append(p)
                elif d.GetVolume().GetMaterial().GetName().startswith("CarbonFiber"):
                    parts["carbon"].append(p)
            c = {k: centroid(v) for k, v in parts.items()}
            if None in (c["lec"], c["rec"], c["active"], c["fpc"], c["cu"], c["carbon"]):
                print(f"  WARNING incomplete module {name} on {short}: "
                      f"{ {k: len(v) for k, v in parts.items()} }")
                return
            meas = dict(type=name, short=short, lec=c["lec"], active=c["active"],
                        rec_dir=sign(c["rec"][0] - c["lec"][0]),
                        fpc_dir=sign(c["fpc"][1] - c["active"][1]),
                        fpc_dy=c["fpc"][1] - c["active"][1],
                        normal=sign(c["cu"][2] - c["carbon"][2]))
            meas["parity"] = meas["rec_dir"] * meas["fpc_dir"] * meas["normal"]
            out.setdefault(short, []).append(meas)
            return
        for i in range(node.GetNdaughters()):
            child = node.GetDaughter(i)
            child_matrix = ROOT.TGeoHMatrix(matrix)
            child_matrix.Multiply(child.GetMatrix())
            walk(child, child_matrix, short)

    walk(geo.GetTopNode(), ROOT.TGeoHMatrix(), None)
    return out


def main():
    root_file, scenario_dir = sys.argv[1], Path(sys.argv[2])
    f = ROOT.TFile.Open(root_file)
    geo = next(k.ReadObj() for k in f.GetListOfKeys() if k.GetClassName() == "TGeoManager")
    measured = module_measurements(geo)
    total = Counter()
    examples = []
    for short in LAYER_TO_SHORT.values():
        src = source_modules(scenario_dir, short)
        got = measured.get(short, [])
        # Match each placed module to the delivered row: same type, nearest (x_EPIC, y) of the
        # LEC centroid to the mirrored source origin (the origin is the LEC/RSU boundary).
        unused = list(src)
        disk = Counter()
        for m in got:
            cands = [s for s in unused if s["type"] == m["type"]]
            best = min(cands, key=lambda s: math.hypot(-s["x"] - m["lec"][0], s["y"] - m["lec"][1]))
            unused.remove(best)
            dist = math.hypot(-best["x"] - m["lec"][0], best["y"] - m["lec"][1])
            disk["matched"] += 1
            disk["match_far"] += dist > 10.0
            # Provider directions mapped to EPIC by x -> -x.
            exp_rec, exp_fpc, exp_n = -best["sx"], best["sy"], best["sz"]
            disk["source_label_ok"] += best["parity"] == best["label"]
            disk["rec_ok"] += m["rec_dir"] == exp_rec
            disk["fpc_ok"] += m["fpc_dir"] == exp_fpc
            half = "top" if best["y"] > 0 else "bottom"   # provider: sign(0) = -1
            disk[f"n_{half}"] += 1
            disk[f"fpc_ok_{half}"] += m["fpc_dir"] == exp_fpc
            disk["normal_ok"] += m["normal"] == exp_n
            disk["parity_is_mirror_of_label"] += m["parity"] == -best["label"]
            if len(examples) < 12 and short == "ED1" and best["row"] <= 1:
                examples.append((short, best, m))
        disk["unmatched_source"] = len(unused)
        total.update(disk)
        n = disk["matched"]
        print(f"{short}: placed {n}/{len(src)}  source label==parity {disk['source_label_ok']}/{n}  "
              f"REC toward centre {disk['rec_ok']}/{n}  FPC away from y=0 {disk['fpc_ok']}/{n}  "
              f"normal {disk['normal_ok']}/{n}  built parity == -label {disk['parity_is_mirror_of_label']}/{n}  "
              f"far matches {disk['match_far']}\n      FPC away from y=0 by half: y>0 {disk['fpc_ok_top']}/{disk['n_top']}, "
              f"y<=0 {disk['fpc_ok_bottom']}/{disk['n_bottom']}")
    print("\nExamples (ED1 rows 0-1; EPIC frame; source x shown in engineer frame):")
    for short, s, m in examples:
        print(f"  {short} row {s['row']} mod {s['mod']} {s['type']} {s['facing']:7s} {s['face']:5s} "
              f"x_src {s['x']:+8.2f} y {s['y']:+7.2f} | EPIC LEC x {m['lec'][0]:+8.2f} "
              f"rec_dir {m['rec_dir']:+d} fpc_dir {m['fpc_dir']:+d} (dy {m['fpc_dy']:+.2f}) "
              f"normal {m['normal']:+d} parity {m['parity']:+d} label {s['label']:+d}")
    n = total["matched"]
    checks = ["rec_ok", "fpc_ok", "normal_ok", "parity_is_mirror_of_label", "source_label_ok"]
    bad = sum(n - total[c] for c in checks) + total["unmatched_source"] + total["match_far"]
    print(f"\nTOTAL {n} modules: " + ", ".join(f"{c} {total[c]}" for c in checks) +
          f", unmatched {total['unmatched_source']}; FPC away from y=0: y>0 {total['fpc_ok_top']}/{total['n_top']},"
          f" y<=0 {total['fpc_ok_bottom']}/{total['n_bottom']}")
    print(("PASS" if bad == 0 else "FAIL") + f": {bad} deviations from the provider convention (after x mirror)")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
