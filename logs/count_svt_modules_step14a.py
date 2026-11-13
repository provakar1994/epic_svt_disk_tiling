#!/usr/bin/env python3
"""Step 14a: load a compact XML with DD4hep and count the placed SVT endcap tiling modules.

Proves which tiling scenario a top-level XML actually builds (20261110_ES: rsu_opt 2164 modules,
rsu6 2150). Module assemblies are recognised by volume name A6xx/B5xx/B6xx, as in
logs/inspect_svt_export_step11d.py. Run inside eic-shell (DETECTOR_PATH set) from the same working
directory as the job that uses the XML (module_placements paths are resolved cwd-first).
Usage: python count_svt_modules_step14a.py <compact.xml> [expected_count]   (exit 1 on mismatch)
"""
import re
import sys
from collections import Counter

import ROOT  # noqa: F401  (loads the TGeo dictionaries)
import dd4hep

MODULE_RE = re.compile(r"^(A6|B5|B6)[01][01]$")


def count_modules(top):
    counts = Counter()
    stack = [top]
    while stack:
        node = stack.pop()
        name = node.GetVolume().GetName()
        if MODULE_RE.match(name):
            counts[name] += 1
            continue
        for i in range(node.GetNdaughters()):
            stack.append(node.GetDaughter(i))
    return counts


xml = sys.argv[1]
expected = int(sys.argv[2]) if len(sys.argv) > 2 else None
det = dd4hep.Detector.getInstance()
det.fromXML(xml)
counts = count_modules(det.manager().GetTopNode())
total = sum(counts.values())
print(f"SVT_MODULE_COUNT {total}  xml={xml}")
print("  per type: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
if expected is not None and total != expected:
    print(f"ERROR: expected {expected} SVT endcap modules, found {total}")
    sys.exit(1)
