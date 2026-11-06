#!/usr/bin/env python3
"""Write refplanes/plane_map.csv (v2) from the DD4hep-evaluated overlay geometry.
Runs INSIDE the container (DD4hep python); DETECTOR_PATH = epic/install/share/epic.
Usage: python3 make_plane_map.py   (reads generated/epic_craterlake_tracking_only_refplanes.xml)

Columns 1-9 (fixed interface, names unchanged):
  disk        ED0..ED4 (negative z), HD0..HD4 (positive z)
  side        negative | positive
  z_disk_mm   signed nominal disk centre (definitions_craterlake.xml *_zmin constants)
  z_plane_mm  signed plane centre = sign*(|z_disk| - 6 mm); slab is +/- 0.05 mm
  rmin_mm     smallest radius from the beam axis covered by the plane
              (= r_inner_about_center - |center_x|); v2 inner edge is off-centre, see below
  rmax_mm     largest radius r such that the full circle of radius r is covered
              (= r_outer_about_center - |center_x| = disk rmax + 20 mm)
  system      DD4hep system id of the plane's detector
  barrel      volume id 'barrel' (3 positive side, 2 negative/reflected side)
  layer       volume id 'layer' = layer index within that detector (NOT always the disk index)
Added columns (v2):
  center_x_mm, center_y_mm       centre of the plane annulus (= centre of the smallest circle
                                 enclosing both buffered beam-pipe openings)
  r_inner_about_center_mm        inner radius about that centre (enclosing-circle radius)
  r_outer_about_center_mm        outer radius about that centre
  uncovered_max_depth_mm         largest distance from the plane inner edge into the region that is
                                 outside both openings but inside the plane hole (0 = exact)
  uncovered_area_mm2             area of that region (grid estimate, 0.02 mm cells)
  note                           opening geometry
A point (x, y) is on the plane iff r_in <= hypot(x - center_x, y - center_y) <= r_out.
"""
import csv
import os

import numpy as np
import dd4hep

CM = 10.0
here = os.path.dirname(os.path.abspath(__file__))
xml = os.path.join(here, "generated", "epic_craterlake_tracking_only_refplanes.xml")
d = dd4hep.Detector.getInstance()
d.fromXML(xml)
c = lambda n: d.constantAsDouble(n) * CM

PREFIX = {"HD0": "InnerTrackerEndcapP", "ED0": "InnerTrackerEndcapN"}
for k in range(1, 5):
    PREFIX[f"HD{k}"] = f"TrackerEndcapPDisk{k}"
    PREFIX[f"ED{k}"] = f"TrackerEndcapNDisk{k}"
# disk -> (detector name, layer index in that detector)
DETECTOR = {"HD0": ("SVTDiskRefPlanesP", 0), "HD1": ("SVTDiskRefPlanesP", 1),
            "HD2": ("SVTDiskRefPlanesHD2", 0), "HD3": ("SVTDiskRefPlanesHD3", 0),
            "HD4": ("SVTDiskRefPlanesHD4", 0),
            "ED0": ("SVTDiskRefPlanesN", 0), "ED1": ("SVTDiskRefPlanesN", 1),
            "ED2": ("SVTDiskRefPlanesN", 2), "ED3": ("SVTDiskRefPlanesED3", 0),
            "ED4": ("SVTDiskRefPlanesED4", 0)}


def uncovered(cx, rin, openings, step=0.02):
    """Grid estimate of the hole region outside both openings: area and max depth from the edge."""
    xs = np.arange(cx - rin, cx + rin + step, step)
    X, Y = np.meshgrid(xs, np.arange(-rin, rin + step, step))
    in_hole = np.hypot(X - cx, Y) < rin
    outside_openings = np.ones_like(in_hole)
    for ox, oy, orad in openings:
        outside_openings &= np.hypot(X - ox, Y - oy) > orad
    region = in_hole & outside_openings
    if not region.any():
        return 0.0, 0.0
    depth = rin - np.hypot(X[region] - cx, Y[region])
    return float(depth.max()), float(region.sum() * step * step)


rows = []
for disk in [f"ED{i}" for i in range(5)] + [f"HD{i}" for i in range(5)]:
    p = PREFIX[disk]
    side = "negative" if disk.startswith("ED") else "positive"
    name, layer = DETECTOR[disk]
    det = d.detector(name)
    lcx, lcy, lr = c(f"{p}_lepton_center_x"), c(f"{p}_lepton_center_y"), c(f"{p}_lepton_radius")
    hcx, hcy, hr = c(f"{p}_hadron_center_x"), c(f"{p}_hadron_center_y"), c(f"{p}_hadron_radius")
    cx, rin, rout = c(f"SVTDiskRefPlane_{disk}_cx"), c(f"SVTDiskRefPlane_{disk}_rin"), c(f"SVTDiskRefPlane_{disk}_rout")
    z_disk = (-1 if side == "negative" else 1) * c(f"{p}_zmin")
    depth, area = uncovered(cx, rin, [(lcx, lcy, lr), (hcx, hcy, hr)])
    same = abs(lcx - hcx) < 1e-9 and abs(lr - hr) < 1e-9
    nested = abs(hcx - lcx) + lr <= hr + 1e-9 or abs(hcx - lcx) + hr <= lr + 1e-9
    kind = ("coincident openings" if same else "lepton inside hadron opening" if nested
            else "openings not nested: enclosing circle leaves a sliver")
    note = (f"{kind}; lepton (x={lcx:.3f}, y={lcy:.3f}, r={lr:.3f}) hadron (x={hcx:.3f}, y={hcy:.3f}, r={hr:.3f}) mm")
    rows.append([disk, side, f"{z_disk:.3f}", f"{c(f'SVTDiskRefPlane_{disk}_z'):.3f}", f"{rin - abs(cx):.3f}",
                 f"{rout - abs(cx):.3f}", det.id(), 2 if side == "negative" else 3, layer,
                 f"{cx:.3f}", "0.000", f"{rin:.3f}", f"{rout:.3f}", f"{depth:.3f}", f"{area:.1f}", note])

header = ["disk", "side", "z_disk_mm", "z_plane_mm", "rmin_mm", "rmax_mm", "system", "barrel", "layer",
          "center_x_mm", "center_y_mm", "r_inner_about_center_mm", "r_outer_about_center_mm",
          "uncovered_max_depth_mm", "uncovered_area_mm2", "note"]
with open(os.path.join(here, "plane_map.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)
print(open(os.path.join(here, "plane_map.csv")).read())
