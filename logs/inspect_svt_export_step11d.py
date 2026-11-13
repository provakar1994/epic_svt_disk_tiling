#!/usr/bin/env python3
"""Step 11d: inspect exported tracking-only ROOT geometries (run inside the EIC container).

For each export: count placed tiling modules per type (assembly volumes named A6xx/B5xx/B6xx)
and, for one inward (x1x) and one outward (x0x) prototype, print the local z interval of every
daughter class (epoxy, baseplate, film, inactive Si, active Si, Cu, FPC Kapton/Al, AncASIC) so
the Step 11b stack (Cu inside 50 um, inward Al on the back of the baseplate) can be read off.
Usage: python3 inspect_svt_export_step11d.py <export.root> [<export.root> ...]
"""
import re
import sys
from collections import Counter

import ROOT

MODULE_RE = re.compile(r"^(A6|B5|B6)[01][01]$")


def count_modules(top):
    """Walk the geometry tree and count placements of module assemblies by volume name."""
    counts = Counter()
    stack = [top]
    while stack:
        node = stack.pop()
        vol = node.GetVolume()
        name = vol.GetName()
        if MODULE_RE.match(name):
            counts[name] += 1
            continue  # do not descend into modules
        for i in range(node.GetNdaughters()):
            stack.append(node.GetDaughter(i))
    return counts


def daughter_z_intervals(volume):
    """Local z interval [um] of each daughter class of a module prototype."""
    intervals = {}
    for i in range(volume.GetNdaughters()):
        node = volume.GetNode(i)
        name = node.GetVolume().GetName()
        key = re.sub(r"component\d+_?", "", name)
        key = re.sub(r"rsu\d+_?", "", key) or "component"
        key = key + " [" + node.GetVolume().GetMaterial().GetName() + "]"
        z = node.GetMatrix().GetTranslation()[2]
        dz = node.GetVolume().GetShape().GetDZ()
        lo, hi = (z - dz) * 1e4, (z + dz) * 1e4  # cm -> um
        if key in intervals:
            lo = min(lo, intervals[key][0])
            hi = max(hi, intervals[key][1])
        intervals[key] = (lo, hi)
    return intervals


for path in sys.argv[1:]:
    f = ROOT.TFile.Open(path)
    geo = f.Get("default") or next(
        (k.ReadObj() for k in f.GetListOfKeys() if k.GetClassName() == "TGeoManager"), None)
    print(f"== {path}")
    counts = count_modules(geo.GetTopNode())
    print(f"placed tiling modules: {sum(counts.values())}  " +
          " ".join(f"{k}:{v}" for k, v in sorted(counts.items())))
    for proto in ("B610", "B600", "A610", "A600"):
        vol = geo.GetVolume(proto)
        if not vol:
            continue
        print(f"  prototype {proto} (local z, um, sorted by low edge):")
        for key, (lo, hi) in sorted(daughter_z_intervals(vol).items(), key=lambda kv: kv[1][0]):
            print(f"    {lo:9.2f} .. {hi:9.2f}  ({hi - lo:7.2f})  {key}")
