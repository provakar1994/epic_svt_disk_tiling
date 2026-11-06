#!/usr/bin/env python3
"""Dump the active (sensitive) silicon rectangles of the 10 SVT endcap disks
from the built DD4hep geometry, for the "active" selection of
analyze_refplane_efficiency.py.

Run inside eic-shell (needs dd4hep + PyROOT); see run_dump_active_silicon.sh.

For every sensitive placed volume under the six SVT endcap detector elements
(Inner/Middle/OuterTrackerEndcap N/P), the four corners of the box in its local
z = 0 plane are transformed to global EPIC coordinates. The sensors lie in
planes of constant z (z-normal), so the xy rectangle is the sensor's projection
along z. Corners are written in mm.

Output CSV columns:
  disk, detector, layer, z_center_mm, half_x_mm, half_y_mm, half_z_mm,
  x0..x3_mm, y0..y3_mm (corners in order around the rectangle), shape, path
Any non-box sensitive shape stops the script (the analysis assumes boxes).
"""
import csv
import sys
from array import array

import dd4hep
import ROOT

XML = sys.argv[1]
OUT = sys.argv[2]

# (detector element, layer id) -> disk name. Layer 1 of Inner/Middle is
# ED0/HD0 and ED1/HD1; Outer layers 2, 3, 4 are disks 2, 3, 4.
DISK_OF = {
    ("InnerTrackerEndcapN", 1): "ED0", ("MiddleTrackerEndcapN", 1): "ED1",
    ("OuterTrackerEndcapN", 2): "ED2", ("OuterTrackerEndcapN", 3): "ED3",
    ("OuterTrackerEndcapN", 4): "ED4",
    ("InnerTrackerEndcapP", 1): "HD0", ("MiddleTrackerEndcapP", 1): "HD1",
    ("OuterTrackerEndcapP", 2): "HD2", ("OuterTrackerEndcapP", 3): "HD3",
    ("OuterTrackerEndcapP", 4): "HD4",
}

description = dd4hep.Detector.getInstance()
description.fromXML(XML)

cm_to_mm = 10.0  # TGeo lengths are in cm
rows = []
for detector in ("InnerTrackerEndcapN", "MiddleTrackerEndcapN", "OuterTrackerEndcapN",
                 "InnerTrackerEndcapP", "MiddleTrackerEndcapP", "OuterTrackerEndcapP"):
    for _, layer_de in description.detector(detector).children():
        disk = DISK_OF[(detector, layer_de.id())]
        layer_to_world = layer_de.nominal().worldTransformation()
        iterator = ROOT.TGeoIterator(layer_de.placement().GetVolume())
        node = iterator.Next()
        while node:
            volume = node.GetVolume()
            if dd4hep.Volume(volume).isSensitive():
                shape = volume.GetShape()
                if shape.ClassName() != "TGeoBBox":
                    sys.exit(f"ERROR: non-box sensitive shape {shape.ClassName()} in {disk}")
                to_world = ROOT.TGeoHMatrix(layer_to_world)
                to_world.Multiply(iterator.GetCurrentMatrix())
                dx, dy, dz = shape.GetDX(), shape.GetDY(), shape.GetDZ()
                local_corners = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
                xs, ys = [], []
                world = array("d", [0.0, 0.0, 0.0])
                for lx, ly in local_corners:
                    to_world.LocalToMaster(array("d", [lx, ly, 0.0]), world)
                    xs.append(world[0] * cm_to_mm)
                    ys.append(world[1] * cm_to_mm)
                world_centre = array("d", [0.0, 0.0, 0.0])
                to_world.LocalToMaster(array("d", [0.0, 0.0, 0.0]), world_centre)
                path = ROOT.TString()
                iterator.GetPath(path)
                rows.append([disk, detector, layer_de.id(), world_centre[2] * cm_to_mm,
                             dx * cm_to_mm, dy * cm_to_mm, dz * cm_to_mm,
                             *xs, *ys, shape.ClassName(), path.Data()])
            node = iterator.Next()

with open(OUT, "w", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["disk", "detector", "layer", "z_center_mm", "half_x_mm", "half_y_mm", "half_z_mm",
                     "x0_mm", "x1_mm", "x2_mm", "x3_mm", "y0_mm", "y1_mm", "y2_mm", "y3_mm",
                     "shape", "path"])
    for row in rows:
        writer.writerow([f"{v:.4f}" if isinstance(v, float) else v for v in row])

counts = {}
for row in rows:
    counts[row[0]] = counts.get(row[0], 0) + 1
print("SENSITIVE_BOXES", len(rows), counts)
