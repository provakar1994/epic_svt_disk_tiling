#!/usr/bin/env python3
"""Geantino material recording with a selectable random seed (Step 8q disk material scan).

Thin wrapper around scripts/material_map/Examples/Scripts/Python/material_recording.py
(runMaterialRecording), identical except for the seed: upstream hard-codes
RandomNumbers(seed=228), so parallel eta slices would share one random sequence
(identical phi values across slices). Here the module-level RandomNumbers is replaced
by one bound to --seed before runMaterialRecording is called. Run inside eic-shell from
scripts/material_map/ (needs its epic.py and the cached Examples on sys.path).
"""

import argparse
import os
import sys

import acts.examples
import acts.examples.dd4hep  # noqa: F401  (registers DD4hep detector bindings)
import acts.examples.geant4  # noqa: F401

material_dir = os.getcwd()
sys.path.insert(0, os.path.join(material_dir, "Examples", "Scripts", "Python"))
sys.path.insert(0, material_dir)  # epic.py lives in scripts/material_map (the cwd)
import epic  # noqa: E402  scripts/material_map/epic.py
import material_recording  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--xmlFile", required=True, help="DD4hep compact file")
    p.add_argument("-n", "--events", type=int, required=True)
    p.add_argument("-t", "--tracks", type=int, required=True, help="geantinos per event")
    p.add_argument("--eta-min", type=float, required=True)
    p.add_argument("--eta-max", type=float, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("-o", "--outputName", required=True, help="output ROOT file (absolute path)")
    args = p.parse_args()

    seed = args.seed
    material_recording.RandomNumbers = lambda seed_unused=None, **kw: acts.examples.RandomNumbers(seed=seed)

    detector = epic.getDetector(args.xmlFile)
    material_recording.runMaterialRecording(
        detector=detector,
        s=acts.examples.Sequencer(events=args.events, numThreads=1),
        tracksPerEvent=args.tracks,
        etaRange=(args.eta_min, args.eta_max),
        outputFileBase=args.outputName.replace(".root", ""),
    ).run()


if __name__ == "__main__":
    main()
