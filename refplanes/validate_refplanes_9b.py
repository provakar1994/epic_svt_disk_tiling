#!/usr/bin/env python3
"""Step 9b static validator (v2) for the reference-plane overlay. Runs INSIDE the container
(DD4hep python, DETECTOR_PATH = epic/install/share/epic). No simulation.

Checks
 1. generated XML = installed epic_craterlake_tracking_only.xml + exactly one added line, the
    include of refplanes/silicon_disks_refplanes.xml, directly after silicon_disks_modules.xml;
 2. the plane system ids (54-58, 86, 87) are not used in compact/ (repo and installed) as *_ID
    constants or literal detector ids, and after loading every detector id >= 0 is unique;
 3. plane XML has no ACTS hooks (layer_material, ParametersPlugin, acts_, segmentation);
 4. loading the overlay: for every disk, the PLACED slice (world x/y/z centre, tube rmin/rmax about
    its own centre, half-thickness, material, sensitivity, volume ids) matches plane_map.csv;
 5. the slab lies outside the disk layer envelope (z_disk +/- 5 mm), on the IP side;
 6. opening geometry: both openings have centre_y = 0; the plane hole (circle about the annulus
    centre, radius r_in) contains both buffered openings (plane never enters an opening) and is
    the smallest such circle (touches the leftmost and rightmost opening edge); the outer edge
    covers every r <= disk rmax + 20 mm; grouped detectors (HD0+HD1, ED0+ED1+ED2) have cx = 0;
 7. readout SVTDiskRefPlaneHits: id spec system:8,barrel:3,layer:4,slice:4, no segmentation.
v1 of this validator (centred annuli): tmp/retained/2026-11-06/refplanes_v1/validate_refplanes_9b_v1.py
"""
import csv
import difflib
import os
import re
import sys

import ROOT  # noqa: F401  (loads TGeo)
import dd4hep

CM = 10.0
TOL = 1e-3  # mm; plane_map.csv holds 3 decimals
here = os.path.dirname(os.path.abspath(__file__))
epic_root = os.path.abspath(os.path.join(here, "..", ".."))
detector_path = os.environ["DETECTOR_PATH"]
source_xml = os.path.join(detector_path, "epic_craterlake_tracking_only.xml")
overlay_xml = os.path.join(here, "generated", "epic_craterlake_tracking_only_refplanes.xml")
plane_xml = os.path.join(here, "silicon_disks_refplanes.xml")
PLANE_IDS = {54: "SVTDiskRefPlanesP", 55: "SVTDiskRefPlanesN", 56: "SVTDiskRefPlanesHD2",
             57: "SVTDiskRefPlanesHD3", 58: "SVTDiskRefPlanesHD4", 86: "SVTDiskRefPlanesED3",
             87: "SVTDiskRefPlanesED4"}
PREFIX = {"HD0": "InnerTrackerEndcapP", "ED0": "InnerTrackerEndcapN"}
for k in range(1, 5):
    PREFIX[f"HD{k}"] = f"TrackerEndcapPDisk{k}"
    PREFIX[f"ED{k}"] = f"TrackerEndcapNDisk{k}"
failures = []


def check(ok, msg):
    print(f"  [{'ok' if ok else 'FAIL'}] {msg}")
    if not ok:
        failures.append(msg)


print("1. Generated XML vs installed source")
src = open(source_xml).read().splitlines()
gen = open(overlay_xml).read().splitlines()
diff = [x for x in difflib.unified_diff(src, gen, lineterm="", n=0) if not x.startswith(("---", "+++", "@@"))]
check(len(diff) == 1 and diff[0].startswith("+") and diff[0][1:].strip() == f'<include ref="{plane_xml}"/>',
      f"exactly one added line: {diff}")
idx = [i for i, line in enumerate(gen) if "silicon_disks_refplanes.xml" in line]
check(len(idx) == 1 and "compact/tracking/silicon_disks_modules.xml" in gen[idx[0] - 1],
      f"include directly after silicon_disks_modules.xml (line {idx[0] + 1 if idx else None})")
bad_inc = [line.strip() for line in gen if "<include ref=" in line and "refplanes" not in line
           and "${DETECTOR_PATH}" not in line and "${DD4hepINSTALL}" not in line]
check(not bad_inc, f"other includes keep ${{DETECTOR_PATH}}/${{DD4hepINSTALL}}: offending={bad_inc}")

print("2. Plane detector ids unused elsewhere")
id_alt = "|".join(str(i) for i in PLANE_IDS)
for base in (os.path.join(epic_root, "compact"), os.path.join(detector_path, "compact")):
    hits = []
    for dirpath, _, files in os.walk(base):
        for fn in files:
            if fn.endswith(".xml"):
                text = open(os.path.join(dirpath, fn), errors="replace").read()
                hits += [f"{fn}:{m.group(1)}={m.group(2)}" for m in
                         re.finditer(rf'name="(\w+_ID)"\s+value="\s*({id_alt})\s*"', text)]
                hits += [f"{fn}:detector id={m.group(1)}" for m in
                         re.finditer(rf'<detector[^>]*\bid="\s*({id_alt})\s*"', text)]
    check(not hits, f"no *_ID constant or detector id in {sorted(PLANE_IDS)} under {base}: {hits}")

print("3. No ACTS hooks in the plane XML")
ptext = re.sub(r"<comment>.*?</comment>", "", open(plane_xml).read(), flags=re.S)
for word in ("layer_material", "ParametersPlugin", "acts_", "<segmentation"):
    check(word not in ptext, f"'{word}' absent")

print("4-6. Load overlay; placed volumes vs plane_map.csv; envelope; openings")
description = dd4hep.Detector.getInstance()
description.fromXML(overlay_xml)
c = lambda n: description.constantAsDouble(n) * CM
ids = {}
for kv in description.detectors():
    de = dd4hep.DetElement(kv.second)
    ids.setdefault(de.id(), []).append(de.name())
dup = {k: v for k, v in ids.items() if len(v) > 1 and k >= 0}
check(not dup, f"all detector ids >= 0 unique: duplicates={dup}")
check(all(ids.get(k) == [v] for k, v in PLANE_IDS.items()), f"plane ids: {[(k, ids.get(k)) for k in PLANE_IDS]}")
thick = c("SVTDiskRefPlane_thickness")
env_half = c("SiTrackerEndcapLayer_thickness") / 2
for name in ("HD0", "HD1", "ED0", "ED1", "ED2"):
    check(abs(c(f"SVTDiskRefPlane_{name}_cx")) < 1e-9, f"{name}: grouped detector centre cx = 0")

for row in csv.DictReader(open(os.path.join(here, "plane_map.csv"))):
    disk, p = row["disk"], PREFIX[row["disk"]]
    z_disk, z_plane = float(row["z_disk_mm"]), float(row["z_plane_mm"])
    cx, rin, rout = float(row["center_x_mm"]), float(row["r_inner_about_center_mm"]), float(row["r_outer_about_center_mm"])
    sdet = description.detector(PLANE_IDS[int(row["system"])])
    layer_index = int(row["layer"])
    layer_de = [kv.second for kv in sdet.children() if kv.second.id() == layer_index][0]
    slice_de = [kv.second for kv in layer_de.children()][0]
    t = slice_de.nominal().worldTransformation().GetTranslation()
    xc, yc, zc = t[0] * CM, t[1] * CM, t[2] * CM
    vol = slice_de.volume()
    shape = vol.GetShape()
    srmin, srmax, sdz = shape.GetRmin() * CM, shape.GetRmax() * CM, shape.GetDz() * CM
    vid = {q.first: q.second for q in slice_de.placement().volIDs()}
    lvid = {q.first: q.second for q in layer_de.placement().volIDs()}
    good = (abs(zc - z_plane) < TOL and abs(c(f"SVTDiskRefPlane_{disk}_z") - z_plane) < TOL
            and abs(xc - cx) < TOL and abs(yc) < 1e-9 and abs(srmin - rin) < TOL and abs(srmax - rout) < TOL
            and abs(float(row["rmin_mm"]) - (rin - abs(cx))) < 2 * TOL
            and abs(float(row["rmax_mm"]) - (rout - abs(cx))) < 2 * TOL
            and abs(2 * sdz - thick) < 1e-9 and vol.GetMaterial().GetName() == "Vacuum" and vol.isSensitive()
            and sdet.id() == int(row["system"]) and lvid.get("barrel") == int(row["barrel"])
            and lvid.get("layer") == layer_index and vid.get("slice") == 0)
    check(good, f"{disk}: {sdet.name()} placed centre=({xc:.3f},{yc:.3f},{zc:.3f}) tube r=[{srmin:.3f},{srmax:.3f}] "
                f"dz={sdz:.3f} mat={vol.GetMaterial().GetName()} sensitive={vol.isSensitive()} "
                f"layer-ids={lvid} slice-ids={vid}")
    slab_hi = abs(zc) + sdz
    env_lo = abs(z_disk) - env_half
    check(slab_hi < env_lo and abs(zc) < abs(z_disk) and (zc > 0) == (z_disk > 0),
          f"{disk}: slab |z| <= {slab_hi:.3f} < envelope |z| >= {env_lo:.3f} (gap {env_lo - slab_hi:.3f} mm), IP side")
    # use the evaluated constants here (plane_map.csv is rounded to 1e-3 mm)
    cx, rin, rout = c(f"SVTDiskRefPlane_{disk}_cx"), c(f"SVTDiskRefPlane_{disk}_rin"), c(f"SVTDiskRefPlane_{disk}_rout")
    openings = [(c(f"{p}_{k}_center_x"), c(f"{p}_{k}_center_y"), c(f"{p}_{k}_radius")) for k in ("lepton", "hadron")]
    contain = [rin - (abs(ox - cx) + orad) for ox, oy, orad in openings]   # >= 0: opening inside the hole
    edges_l = min(ox - orad for ox, oy, orad in openings)
    edges_r = max(ox + orad for ox, oy, orad in openings)
    check(all(abs(oy) < 1e-9 for _, oy, _ in openings) and min(contain) > -1e-6
          and abs((cx - rin) - edges_l) < 1e-6 and abs((cx + rin) - edges_r) < 1e-6,
          f"{disk}: openings inside the plane hole (margins {contain[0]:.3f} lepton, {contain[1]:.3f} hadron mm); "
          f"hole = smallest enclosing circle")
    check(rout - abs(cx) >= c(f"{p}_rmax") + 20.0 - 1e-6, f"{disk}: outer edge covers r <= {rout - abs(cx):.3f} mm "
          f"(disk rmax {c(f'{p}_rmax'):.1f} + 20)")
    print(f"       uncovered sliver: max depth {row['uncovered_max_depth_mm']} mm, area {row['uncovered_area_mm2']} mm2")

print("7. Readout")
ro = description.readout("SVTDiskRefPlaneHits")
spec = ro.idSpec().fieldDescription()
widths = ",".join(f"{f.split(':')[0]}:{f.split(':')[2]}" for f in spec.split(","))
check(widths == "system:8,barrel:3,layer:4,slice:4", f"id spec = {spec} -> {widths}")
check(not ro.segmentation().isValid(), "no segmentation")

print(f"\nStep 9b validator (v2): {'PASS' if not failures else 'FAIL (' + str(len(failures)) + ')'}")
sys.exit(0 if not failures else 1)
