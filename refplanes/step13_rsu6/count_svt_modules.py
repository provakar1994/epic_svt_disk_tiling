"""Step 14b: count SVT endcap modules in a compact XML (runs INSIDE the container, DD4hep python).
A module = a direct DetElement child of a layer DetElement of the six SVT endcap detectors
(names disk<k>_row<r>_module<m>_<side>). Expected from the delivered <disk>_modules.csv row counts:
  20261110_ES/rsu_opt: 2164 (N: 78, 236, 773; P: 78, 236, 763)
  20261110_ES/rsu6   : 2150 (N: 76, 236, 766; P: 76, 236, 760)
Usage: python3 count_svt_modules.py COMPACT_XML EXPECTED_TOTAL
"""
import sys
import dd4hep

xml, expected = sys.argv[1], int(sys.argv[2])
d = dd4hep.Detector.getInstance()
d.fromXML(xml)
names = [f"{p}TrackerEndcap{s}" for s in "NP" for p in ("Inner", "Middle", "Outer")]
total = 0
for name in names:
    det = d.detector(name)
    n = 0
    for layer in det.children():
        n += len(dd4hep.DetElement(layer.second).children())
    total += n
    print(f"  {name:22s} modules = {n}")
print(f"Geometry: {xml}")
print(f"SVT endcap modules total = {total} (expected {expected}): {'PASS' if total == expected else 'FAIL'}")
sys.exit(0 if total == expected else 1)
