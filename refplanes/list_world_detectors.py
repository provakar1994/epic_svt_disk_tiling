#!/usr/bin/env python3
"""Print the comma-separated names of all world children of a compact XML (inside the container).
Used by material_scan_9d.sh in place of '--detectors all', which fails in material_scan.py with
this container's pandas (cppyy std::string names are compared element-wise).
Usage: python3 list_world_detectors.py XML"""
import sys
import dd4hep

description = dd4hep.Detector.getInstance()
description.fromXML(sys.argv[1])
print("DETECTORS=" + ",".join(str(name) for name, _ in description.world().children()))
