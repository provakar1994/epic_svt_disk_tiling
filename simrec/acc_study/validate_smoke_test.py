#!/usr/bin/env python3
"""Validate event counts and required PODIO collections in smoke outputs."""

from pathlib import Path

import uproot


import sys

# Optional arguments: OUTPUT_DIR TAG [EXPECTED_VERTEX_Z_MM]; defaults are the 2026-10-26 smoke test.
OUTPUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/smoke_20261026")
TAG = sys.argv[2] if len(sys.argv) > 2 else "smoke_vz_000mm_eta_p0p6_to_p3p8_n10"
EXPECTED_VERTEX_Z_MM = float(sys.argv[3]) if len(sys.argv) > 3 else None
EXPECTED_EVENTS = 10
EXPECTED_COLLECTIONS = {
    "EventHeader",
    "MCParticles",
    "SiBarrelRawHits",
    "SiBarrelVertexRawHits",
    "SiEndcapTrackerRawHits",
    "SiBarrelNoiseRawHits",
    "SiBarrelVertexNoiseRawHits",
    "SiEndcapTrackerNoiseRawHits",
    "SiBarrelRawHitsWithNoise",
    "SiBarrelVertexRawHitsWithNoise",
    "SiEndcapTrackerRawHitsWithNoise",
    "MPGDBarrelRawHits",
    "OuterMPGDBarrelRawHits",
    "BackwardMPGDEndcapRawHits",
    "ForwardMPGDEndcapRawHits",
    "SiBarrelTrackerRecHits",
    "SiBarrelVertexRecHits",
    "SiEndcapTrackerRecHits",
    "MPGDBarrelRecHits",
    "OuterMPGDBarrelRecHits",
    "BackwardMPGDEndcapRecHits",
    "ForwardMPGDEndcapRecHits",
    "TOFBarrelSharedRawHits",
    "TOFBarrelSharedRecHits",
    "TOFBarrelClusterHits",
    "TOFEndcapSharedRawHits",
    "TOFEndcapSharedRecHits",
    "TOFEndcapClusterHits",
    "CentralTrackingRecHits",
    "CentralWithoutTOFTrackerMeasurements",
    "CentralTrackerMeasurements",
    "CentralTrackSeeds",
    "CentralTrackSeedParameters",
    "CentralCKFTrajectories",
    "CentralCKFTrackParameters",
    "CentralCKFTracks",
    "CentralCKFTrackAssociations",
    "ReconstructedChargedWithoutPIDParticles",
    "CentralTrackVertices",
}


def collection_names(events_tree):
    names = set()
    for branch_name in events_tree.keys():
        root_name = branch_name.split("/", 1)[0]
        if root_name.endswith("_objIdx"):
            root_name = root_name.removesuffix("_objIdx")
        names.add(root_name)
    return names


simulation_file = OUTPUT_DIR / "rootfiles" / f"sim_{TAG}.root"
reconstruction_file = OUTPUT_DIR / "rootfiles" / f"rec_{TAG}.root"

for path in (simulation_file, reconstruction_file):
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"FAIL: missing or empty output: {path}")
    with uproot.open(path) as root_file:
        event_count = root_file["events"].num_entries
    if event_count != EXPECTED_EVENTS:
        raise SystemExit(f"FAIL: {path.name} has {event_count} events, expected {EXPECTED_EVENTS}")
    print(f"PASS: {path.name}: {event_count} events, {path.stat().st_size} bytes")

with uproot.open(reconstruction_file) as root_file:
    available_collections = collection_names(root_file["events"])

missing_collections = sorted(EXPECTED_COLLECTIONS - available_collections)
if missing_collections:
    raise SystemExit("FAIL: missing required collections: " + ", ".join(missing_collections))

print(f"PASS: all {len(EXPECTED_COLLECTIONS)} required collections are present")

if EXPECTED_VERTEX_Z_MM is not None:
    import awkward as ak
    import numpy as np
    with uproot.open(simulation_file) as root_file:
        tree = root_file["events"]
        vertex_z = tree["MCParticles/MCParticles.vertex.z"].array()
        status = tree["MCParticles/MCParticles.generatorStatus"].array()
    primary_z = ak.to_numpy(ak.flatten(vertex_z[status == 1]))
    if len(primary_z) != EXPECTED_EVENTS or not np.allclose(primary_z, EXPECTED_VERTEX_Z_MM):
        raise SystemExit(f"FAIL: primary vertex z {sorted(set(primary_z.round(3)))} mm, "
                         f"expected {EXPECTED_VERTEX_Z_MM} mm for {EXPECTED_EVENTS} primaries")
    print(f"PASS: all {len(primary_z)} primaries start at z = {EXPECTED_VERTEX_Z_MM} mm")
