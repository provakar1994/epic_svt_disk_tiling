#!/usr/bin/env python3
"""Step 9a/9b cross-check (v2, inside the container): point sampling of each plane slab on the
INSTALLED geometry (no planes) with TGeo FindNode. Every sampled point of the planned plane region
(r_in <= |p - centre| <= r_out about the annulus centre in plane_map.csv, 3 z values in the slab)
must be in the world volume, i.e. no existing volume occupies it.
Also reports the margin between each plane hole and the beam pipe at the plane z: the largest
beam-axis radius of a non-world point found in the hole along each sampled direction.
v1 (centred annuli from plane_clearance_9a.json): tmp/retained/2026-11-06/refplanes_v1/."""
import csv
import math
import os

import ROOT
import dd4hep

here = os.path.dirname(os.path.abspath(__file__))
xml = os.path.join(os.environ["DETECTOR_PATH"], "epic_craterlake_tracking_only.xml")
description = dd4hep.Detector.getInstance()
description.fromXML(xml)
geo = ROOT.gGeoManager

all_ok = True
for row in csv.DictReader(open(os.path.join(here, "plane_map.csv"))):
    zp, cx = float(row["z_plane_mm"]), float(row["center_x_mm"])
    rin, rout = float(row["r_inner_about_center_mm"]), float(row["r_outer_about_center_mm"])
    bad = n = 0
    first = None
    hole_max_material = 0.0   # largest |p - centre| inside the hole that is not world (beam pipe)
    for zs in (zp - 0.0499, zp, zp + 0.0499):
        for i in range(180):
            phi = 2 * math.pi * (i + 0.5) / 180
            ux, uy = math.cos(phi), math.sin(phi)
            r = rin + 0.01
            while r <= rout:
                geo.FindNode((cx + r * ux) / 10, (r * uy) / 10, zs / 10)
                n += 1
                if geo.GetLevel() > 0:
                    bad += 1
                    if first is None:
                        first = (round(r, 2), round(math.degrees(phi), 1), zs, geo.GetPath())
                r += 0.5
            r = rin - 0.05
            while r > 0:
                geo.FindNode((cx + r * ux) / 10, (r * uy) / 10, zs / 10)
                if geo.GetLevel() > 0 and "vac" not in geo.GetCurrentVolume().GetName().lower():
                    hole_max_material = max(hole_max_material, r)
                    break
                r -= 0.05
    ok = bad == 0
    all_ok &= ok
    print(f"{row['disk']}: z={zp:8.2f} centre x={cx:7.3f} r=[{rin:.3f},{rout:.3f}] points={n} non-world={bad} "
          f"| outermost beam-pipe wall in hole at {hole_max_material:.2f} mm from centre "
          f"(clearance to plane edge {rin - hole_max_material:.2f} mm) {'ok' if ok else 'FAIL first=' + str(first)}")
print("Cross-check:", "PASS" if all_ok else "FAIL")
