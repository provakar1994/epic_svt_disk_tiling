#!/usr/bin/env python3
"""Validate event counts and required PODIO collections in smoke outputs."""

from pathlib import Path

import uproot


OUTPUT_DIR = Path("/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/smoke_20261026")
TAG = "smoke_vz_000mm_eta_p0p6_to_p3p8_n10"
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
