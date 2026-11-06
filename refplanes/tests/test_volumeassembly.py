#!/usr/bin/env python3
"""Inspect the DD4hep_VolumeAssembly feasibility test (inside the container).
Usage: python3 test_volumeassembly.py COMPACT_XML DETECTOR_NAME"""
import sys

import ROOT
import dd4hep

xml, name = sys.argv[1], sys.argv[2]
d = dd4hep.Detector.getInstance()
d.fromXML(xml)
det = d.detector(name)
print(f"detector {name}: id={det.id()} type={det.type()} placement valid={det.placement().isValid()}")
sd = d.sensitiveDetector(name)
print(f"sensitive detector valid={sd.isValid()} type='{sd.type() if sd.isValid() else None}' "
      f"readout='{sd.readout().name() if sd.isValid() else None}'")


def walk(node, path, level):
    vol = node.GetVolume()
    if vol.GetShape().ClassName() != "TGeoShapeAssembly" or level < 3:
        pv = dd4hep.PlacedVolume(node)
        ids = {p.first: p.second for p in pv.volIDs()} if pv.isValid() else {}
        v = dd4hep.Volume(vol)
        print(f"  {'  ' * level}{node.GetName()} shape={vol.GetShape().ClassName()} mat={vol.GetMaterial().GetName()} "
              f"sensitive={v.isSensitive()} ids={ids} z={node.GetMatrix().GetTranslation()[2] * 10:.3f} mm")
    for i in range(node.GetNdaughters()):
        walk(node.GetDaughter(i), path + "/" + node.GetName(), level + 1)


print("detector placement volIDs:", {p.first: p.second for p in det.placement().volIDs()})
def de_tree(de, level=0):
    print(f"  DE {'  ' * level}{de.name()} id={de.id()} placed={de.placement().isValid()} "
          f"ids={({p.first: p.second for p in de.placement().volIDs()} if de.placement().isValid() else None)}")
    for kv in de.children():
        de_tree(kv.second, level + 1)
de_tree(det)
walk(det.placement().ptr(), "", 0)
# point tests in global coordinates (mm): inside the openings must be outside the plane
geo = ROOT.gGeoManager
for x, y, z in [(0, 0, 1194), (-12.242 - 51.0, 0, 1194), (-12.242 - 51.5, 0, 1194), (40, 0, 1194), (37.5, 0, 1194),
                (0, 54, 1194), (300, 0, 1194), (0, 0, -1014), (-45, 0, -1014), (45, 0, -1014), (0, 40, -1014)]:
    geo.FindNode(x / 10, y / 10, z / 10)
    print(f"  point ({x:8.3f},{y:6.1f},{z:6.0f}) -> {geo.GetPath()}")
