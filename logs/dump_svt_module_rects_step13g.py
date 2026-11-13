#!/usr/bin/env python3
"""Step 13g: dump every SVT endcap tiling-module box as a global x-y rectangle (run inside the EIC container).

Read-only. Input: dd_web_display ROOT exports (TGeo). For every placed tiling module (volume
named A6xx/B5xx/B6xx) and every direct daughter of the module prototype, write one CSV row:
  module type, module global center (x, y, z) [mm], daughter key (name without component/rsu
  indices), material, shape class, thickness [um] (= 2*DZ of the box), and the four global x-y
  corners of the box [mm] (box axes may be rotated in x-y; corners are exact).
Nested daughters (e.g. sensitive tiles inside active_si) are not written; the script counts any
nested daughter whose material differs from its mother and prints that count (must be 0 for the
mother box to represent the material correctly).
Used by logs/analyze_material_step13_vs_8q.py to predict per-material x/X0 ratios.

Usage: python3 dump_svt_module_rects_step13g.py <export.root> <out.csv>
"""
import csv
import re
import sys
from collections import Counter

import ROOT

MODULE_RE = re.compile(r"^(A6|B5|B6)[01][01]$")
CM_TO_MM = 10.0


def key_of(name):
    key = re.sub(r"component\d+_?", "", name)
    key = re.sub(r"rsu\d+_?", "", key)
    return key or "component"


def count_foreign_nested(volume, mother_material):
    """Daughters (any depth) whose material differs from their mother."""
    n = 0
    for i in range(volume.GetNdaughters()):
        dv = volume.GetNode(i).GetVolume()
        if dv.GetMaterial().GetName() != mother_material:
            n += 1
        n += count_foreign_nested(dv, dv.GetMaterial().GetName())
    return n


def main(path, out_csv):
    f = ROOT.TFile.Open(path)
    geo = f.Get("default") or next(
        (k.ReadObj() for k in f.GetListOfKeys() if k.GetClassName() == "TGeoManager"), None)
    top = geo.GetTopVolume()
    it = ROOT.TGeoIterator(top)
    modules = Counter()
    foreign = Counter()
    non_box = Counter()
    rows = 0
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["module_type", "mod_x", "mod_y", "mod_z", "key", "material", "shape",
                    "thickness_um", "x0", "y0", "x1", "y1", "x2", "y2", "x3", "y3", "zc"])
        node = it.Next()
        while node:
            vol = node.GetVolume()
            name = vol.GetName()
            if MODULE_RE.match(name):
                # Global matrix: read BEFORE it.Skip(). (A first version called Skip() first; the
                # iterator state then belonged to the next node and 6 of 2164 modules got the
                # identity matrix of their parent assembly.)
                gmat = ROOT.TGeoHMatrix(it.GetCurrentMatrix())
                it.Skip()  # do not descend into the module with the iterator; handled here
                modules[name] += 1
                c = gmat.GetTranslation()
                for i in range(vol.GetNdaughters()):
                    dnode = vol.GetNode(i)
                    dvol = dnode.GetVolume()
                    mat = dvol.GetMaterial().GetName()
                    shape = dvol.GetShape()
                    key = key_of(dvol.GetName())
                    if shape.ClassName() != "TGeoBBox":
                        non_box[(key, shape.ClassName())] += 1
                    if modules[name] == 1:
                        foreign[(name, key)] += count_foreign_nested(dvol, mat)
                    full = ROOT.TGeoHMatrix(gmat)
                    full.Multiply(dnode.GetMatrix())
                    dx, dy, dz = shape.GetDX(), shape.GetDY(), shape.GetDZ()
                    corners = []
                    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                        loc = ROOT.std.vector("double")([sx * dx, sy * dy, 0.0])
                        glob = ROOT.std.vector("double")(3)
                        full.LocalToMaster(loc.data(), glob.data())
                        corners += [glob[0] * CM_TO_MM, glob[1] * CM_TO_MM]
                    zc = full.GetTranslation()[2] * CM_TO_MM
                    w.writerow([name, f"{c[0]*CM_TO_MM:.4f}", f"{c[1]*CM_TO_MM:.4f}", f"{c[2]*CM_TO_MM:.4f}",
                                key, mat, shape.ClassName(), f"{2*dz*CM_TO_MM*1000:.3f}"]
                               + [f"{v:.4f}" for v in corners] + [f"{zc:.4f}"])
                    rows += 1
            node = it.Next()
    print(f"== {path}")
    print(f"placed tiling modules: {sum(modules.values())}  " +
          " ".join(f"{k}:{v}" for k, v in sorted(modules.items())))
    print(f"rows written: {rows} -> {out_csv}")
    print(f"non-box daughters: {dict(non_box) if non_box else 0}")
    bad = {k: v for k, v in foreign.items() if v}
    print(f"nested daughters with a material different from their mother (first module of each type): "
          f"{bad if bad else 0}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
