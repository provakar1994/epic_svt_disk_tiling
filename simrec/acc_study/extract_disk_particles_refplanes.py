#!/usr/bin/env python3
"""Extract per-primary disk-hit shards plus reference-plane crossings.

Sibling of extract_disk_particles.py (which is unchanged). Each output NPZ has
one row per generated primary pi+ (generatorStatus == 1) and keeps zero-hit
particles; no eta or momentum cut is applied here.

Silicon fields (identical definitions, computed by the original
extract_disk_particles.append_block on TrackerEndcapHits):
  hit_mask (bit i = disk i of the side), hit_count, mean_hit_{x,y,z}_mm.

Reference-plane fields (collection SVTDiskRefPlaneHits; zero-material vacuum
annuli 6 mm on the IP side of every disk). Disk order = DISKS[side] in
reduce_disk_acceptance.py (index 0..4 = D0..D4 of that side):
  plane_mask          uint8 (n,): bit i set if the primary has >= 1 accepted
                      plane hit on plane i ("plane_reached").
  plane_crossings     uint16 (n,5): number of accepted plane hits on plane i
                      (a looping particle crosses more than once).
  plane_{x,y,z}_mm, plane_t_ns, plane_p{x,y,z}_GeV  float32 (n,5): the FIRST
                      crossing, i.e. the accepted hit with the earliest time;
                      NaN when the plane was not reached.
  plane_secondary_flagged  uint16 (n,5): hits linked to the primary but with
                      EDM4hep quality bit 30 (BITProducedBySecondary) set,
                      i.e. a step of an unsaved secondary attributed to the
                      primary. They are NOT accepted (not counted above).
"Accepted" plane hit: its MCParticle link points to a selected primary pi+
(generatorStatus == 1) and the producedBySecondary bit is not set. Plane hits
linked to any other MCParticle are dropped and counted per shard
(metadata: plane_hits_dropped_not_primary).

The plane -> disk mapping is data-driven from refplanes/plane_map.csv
(columns disk,side,z_disk_mm,z_plane_mm,rmin_mm,rmax_mm,system,barrel,layer;
disk names ED0..ED4, HD0..HD4; extra trailing columns are ignored). Plane hits
are identified by their decoded CellID fields (system, barrel, layer); the
plane layer is NOT the disk index (v2: system 54 = HD0/HD1 layers 0/1, 55 =
ED0-ED2 layers 0-2, 56/57/58 = HD2-HD4, 86/87 = ED3/ED4, layer 0), so the disk
always comes from the map. A plane hit whose ids are not in the map is an
error. Plane hits on the other side's planes are counted
(plane_hits_other_side) and otherwise ignored, as the silicon extractor does.

If a ROOT file has no SVTDiskRefPlaneHits collection (old campaigns), the
plane fields are written empty (mask 0, crossings 0, NaN positions) and
metadata plane_collection_present = false.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional

import awkward as ak
import numpy as np
import pandas as pd
import uproot

from extract_disk_particles import FLOAT_COLUMNS, append_block
from mc_tracking_hits import KEY, iter_mc_tracking_hits
from reduce_disk_acceptance import COLLECTION, DISKS, PARTICLE_PDG, VERTEX_LABELS, configuration_name


PLANE_COLLECTION = "SVTDiskRefPlaneHits"
PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PLANE_MAP = PROJECT_DIR / "refplanes" / "plane_map.csv"
PRODUCED_BY_SECONDARY_BIT = 30  # edm4hep::SimTrackerHit::BITProducedBySecondary
PLANE_FLOAT_FIELDS = {  # output name -> hit-table column (mc_tracking_hits naming)
    "plane_x_mm": "x_mm", "plane_y_mm": "y_mm", "plane_z_mm": "z_mm", "plane_t_ns": "time_ns",
    "plane_px_GeV": "px_GeV", "plane_py_GeV": "py_GeV", "plane_pz_GeV": "pz_GeV",
}
SILICON_ARRAYS = ("hit_mask", "hit_count", "mean_hit_x_mm", "mean_hit_y_mm", "mean_hit_z_mm")
PLANE_ARRAYS = ("plane_mask", "plane_crossings", "plane_secondary_flagged", *PLANE_FLOAT_FIELDS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Root directory for configuration/shard NPZ files.")
    parser.add_argument("--vertices", type=int, nargs="+", required=True,
                        choices=sorted(VERTEX_LABELS))
    parser.add_argument("--plane-map", type=Path, default=DEFAULT_PLANE_MAP,
                        help=f"plane_map.csv (default {DEFAULT_PLANE_MAP}).")
    parser.add_argument("--step-size", type=int, default=5_000)
    parser.add_argument("--max-files-per-side", type=int,
                        help="Testing option: extract only the first N ROOT files per side.")
    parser.add_argument("--stop-events-per-file", type=int,
                        help="Testing option: extract only this many entries per ROOT file.")
    return parser.parse_args()


def read_plane_map(path: Path) -> tuple[pd.DataFrame, dict]:
    """Return the plane table and {(system, barrel, layer): (side, disk index)}."""
    table = pd.read_csv(path)
    needed = ["disk", "side", "z_disk_mm", "z_plane_mm", "rmin_mm", "rmax_mm", "system", "barrel", "layer"]
    missing = [c for c in needed if c not in table.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    lookup = {}
    for row in table.itertuples(index=False):
        disk = str(row.disk).strip()
        side = "negative" if disk.startswith("ED") else "positive" if disk.startswith("HD") else None
        names = [d[0] for d in DISKS[side]] if side else []
        if disk not in names:
            raise ValueError(f"{path}: unknown disk name {disk!r}")
        if np.sign(row.z_plane_mm) != (-1 if side == "negative" else 1):
            raise ValueError(f"{path}: z_plane_mm sign does not match {disk}")
        ids = (int(row.system), int(row.barrel), int(row.layer))
        if ids in lookup:
            raise ValueError(f"{path}: duplicate plane ids {ids}")
        lookup[ids] = (side, names.index(disk))
    if len(lookup) != 10:
        raise ValueError(f"{path}: expected 10 planes, found {len(lookup)}")
    return table, lookup


def has_collection(filename: Path, name: str) -> bool:
    with uproot.open(filename) as root:
        return name in root["events"].keys(recursive=False)


def plane_hit_totals(filename: Path, step_size: int, stop: Optional[int]) -> list[int]:
    """Total plane hits (all MCParticle links) per event block, same blocks as the reader."""
    totals = []
    with uproot.open(filename) as root:
        tree = root["events"]
        branch = tree[PLANE_COLLECTION][f"{PLANE_COLLECTION}.cellID"]
        stop_entry = tree.num_entries if stop is None else min(stop, tree.num_entries)
        for start in range(0, stop_entry, step_size):
            end = min(start + step_size, stop_entry)
            totals.append(int(ak.sum(ak.num(branch.array(entry_start=start, entry_stop=end)))))
    return totals


def append_plane_block(storage: dict, block: dict, side: str, lookup: dict, counters: dict) -> None:
    """Append reference-plane arrays for one block (rows aligned with the particle table)."""
    particles = block["particles"]
    particle_index = pd.MultiIndex.from_frame(particles[KEY])
    n = len(particles)
    plane_mask = np.zeros(n, dtype=np.uint8)
    crossings = np.zeros((n, 5), dtype=np.uint16)
    flagged = np.zeros((n, 5), dtype=np.uint16)
    values = {name: np.full((n, 5), np.nan, dtype=np.float32) for name in PLANE_FLOAT_FIELDS}

    hits = block["hits"]
    plane_hits = hits.loc[hits.hit_collection == PLANE_COLLECTION]
    counters["plane_hits_linked_to_primary"] += len(plane_hits)
    if not plane_hits.empty:
        ids = list(zip(plane_hits.system.astype(int), plane_hits.cell_barrel.astype(int),
                       plane_hits.layer.astype(int)))
        unknown = sorted(set(ids) - set(lookup))
        if unknown:
            raise ValueError(f"plane hits with ids not in plane_map.csv: {unknown[:5]}")
        hit_side = np.array([lookup[i][0] for i in ids])
        hit_disk = np.array([lookup[i][1] for i in ids])
        secondary = (plane_hits.quality.to_numpy().astype(np.int64) >> PRODUCED_BY_SECONDARY_BIT) & 1 == 1
        counters["plane_hits_other_side"] += int((hit_side != side).sum())
        counters["plane_hits_secondary_flagged"] += int(((hit_side == side) & secondary).sum())
        for disk_index in range(5):
            on_disk = (hit_side == side) & (hit_disk == disk_index)
            if np.any(on_disk & secondary):
                flagged[:, disk_index] = (plane_hits.loc[on_disk & secondary].groupby(KEY, observed=True)
                                          .size().reindex(particle_index, fill_value=0).to_numpy())
            accepted = plane_hits.loc[on_disk & ~secondary]
            if accepted.empty:
                continue
            counters["plane_hits_accepted"] += len(accepted)
            counts = accepted.groupby(KEY, observed=True).size().reindex(particle_index, fill_value=0).to_numpy()
            if np.any(counts > np.iinfo(np.uint16).max):
                raise ValueError("plane crossing count does not fit uint16")
            # First crossing = earliest time; ties broken by hit_index (stable sort).
            first = (accepted.sort_values(["time_ns", "hit_index"], kind="mergesort")
                     .drop_duplicates(KEY, keep="first").set_index(KEY).reindex(particle_index))
            crossings[:, disk_index] = counts.astype(np.uint16)
            plane_mask[counts > 0] |= np.uint8(1 << disk_index)
            for name, column in PLANE_FLOAT_FIELDS.items():
                values[name][:, disk_index] = first[column].to_numpy(dtype=np.float32)

    storage["plane_mask"].append(plane_mask)
    storage["plane_crossings"].append(crossings)
    storage["plane_secondary_flagged"].append(flagged)
    for name in PLANE_FLOAT_FIELDS:
        storage[name].append(values[name])


def extract_file(filename: Path, output_path: Path, side: str, configuration: str,
                 step_size: int, stop: Optional[int], lookup: dict, plane_map_info: dict) -> dict:
    """Extract one ROOT file atomically and return one manifest record."""
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite extracted shard: {output_path}")
    plane_present = has_collection(filename, PLANE_COLLECTION)
    collections = [COLLECTION, PLANE_COLLECTION] if plane_present else COLLECTION
    storage = {name: [] for name in ("event_entry", "mc_index", *FLOAT_COLUMNS,
                                     *SILICON_ARRAYS, *PLANE_ARRAYS)}
    counters = {"plane_hits_linked_to_primary": 0, "plane_hits_accepted": 0,
                "plane_hits_secondary_flagged": 0, "plane_hits_other_side": 0}
    source_metadata = None
    processed_entries = 0
    for block in iter_mc_tracking_hits(
        filename, collections=collections, primary_only=True, pdgs=[PARTICLE_PDG],
        stop=stop, step_size=step_size,
    ):
        append_block(storage, block, DISKS[side])     # silicon: original code path
        append_plane_block(storage, block, side, lookup, counters)
        source_metadata = block["metadata"]
        processed_entries = block["metadata"]["entry_range"][1]

    plane_hits_total = sum(plane_hit_totals(filename, step_size, stop)) if plane_present else 0
    dropped = plane_hits_total - counters["plane_hits_linked_to_primary"]
    if dropped < 0:
        raise AssertionError("more primary-linked plane hits than plane hits")

    arrays = {}
    for name, parts in storage.items():
        if parts:
            arrays[name] = np.concatenate(parts, axis=0)
        elif name in ("hit_count", "plane_crossings", "plane_secondary_flagged"):
            arrays[name] = np.empty((0, 5), dtype=np.uint16)
        elif name.startswith(("mean_hit_", "plane_")) and name != "plane_mask":
            arrays[name] = np.empty((0, 5), dtype=np.float32)
        elif name in ("hit_mask", "plane_mask"):
            arrays[name] = np.empty(0, dtype=np.uint8)
        else:
            dtype = np.uint32 if name in ("event_entry", "mc_index") else np.float32
            arrays[name] = np.empty(0, dtype=dtype)

    metadata = {
        "format_version": "refplanes-1",
        "configuration": configuration,
        "side": side,
        "source_root": str(filename.resolve()),
        "source_bytes": filename.stat().st_size,
        "source_file_id": None if source_metadata is None else source_metadata["file_id"],
        "processed_entries": processed_entries,
        "selected_particles": len(arrays["event_entry"]),
        "selection": {"primary_only": True, "pdg": PARTICLE_PDG,
                      "abs_eta_range": None, "momentum_range_GeV": None},
        "disk_order": [row[0] for row in DISKS[side]],
        "hit_definition": "at least one directly MCParticle-associated TrackerEndcapHit",
        "plane_collection": PLANE_COLLECTION,
        "plane_collection_present": plane_present,
        "plane_hit_definition": "accepted = linked to a selected primary pi+ (generatorStatus==1) and "
                                "quality bit 30 (producedBySecondary) not set; first crossing = "
                                "earliest time among accepted hits on that plane",
        "plane_hits_total": plane_hits_total,
        "plane_hits_dropped_not_primary": dropped,
        **counters,
        "plane_map": plane_map_info,
        "plane_encoding": (source_metadata or {}).get("encodings", {}).get(PLANE_COLLECTION),
        "units": "momenta GeV; positions mm; time ns; angles dimensionless/radians",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".tmp.npz")
    np.savez_compressed(temporary_path,
                        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)), **arrays)
    temporary_path.replace(output_path)
    return {"configuration": configuration, "side": side, "source_root": str(filename.resolve()),
            "shard": str(output_path.resolve()), "processed_entries": processed_entries,
            "selected_particles": len(arrays["event_entry"]), "bytes": output_path.stat().st_size,
            "plane_collection_present": plane_present, "plane_hits_total": plane_hits_total,
            "plane_hits_accepted": counters["plane_hits_accepted"],
            "plane_hits_dropped_not_primary": dropped,
            "plane_hits_secondary_flagged": counters["plane_hits_secondary_flagged"],
            "plane_hits_other_side": counters["plane_hits_other_side"]}


def main() -> None:
    args = parse_args()
    if args.step_size < 1:
        raise SystemExit("ERROR: --step-size must be positive")
    if args.max_files_per_side is not None and args.max_files_per_side < 1:
        raise SystemExit("ERROR: --max-files-per-side must be positive")
    if args.stop_events_per_file is not None and args.stop_events_per_file < 1:
        raise SystemExit("ERROR: --stop-events-per-file must be positive")
    _, lookup = read_plane_map(args.plane_map)
    plane_map_info = {"path": str(args.plane_map.resolve()),
                      "sha256": hashlib.sha256(args.plane_map.read_bytes()).hexdigest(),
                      "content": args.plane_map.read_text()}

    # One manifest per vertex set, never overwritten (the original extractor
    # rewrites a single extraction_manifest.csv; see run_extract_vertex.sh).
    vertex_tag = "_".join(f"vz_{VERTEX_LABELS[v]}mm" for v in args.vertices)
    manifest_path = args.output_dir / f"extraction_manifest_{vertex_tag}.csv"
    if manifest_path.exists():
        raise FileExistsError(f"Refusing to overwrite {manifest_path}")

    manifest_rows = []
    for vertex_z_mm in args.vertices:
        for side in ("negative", "positive"):
            configuration = configuration_name(vertex_z_mm, side)
            root_directory = args.campaign_root / configuration / "rootfiles"
            files = sorted(path for path in root_directory.glob("sim_*.root")
                           if ".tmp." not in path.name)
            if args.max_files_per_side is not None:
                files = files[:args.max_files_per_side]
            if not files:
                raise FileNotFoundError(f"No simulation ROOT files found in {root_directory}")
            print(f"{configuration}: extracting {len(files)} files", flush=True)
            for file_number, filename in enumerate(files, start=1):
                shard_name = filename.name.replace("sim_", "particles_", 1).replace(".root", ".npz")
                output_path = args.output_dir / configuration / shard_name
                record = extract_file(filename, output_path, side, configuration,
                                      args.step_size, args.stop_events_per_file, lookup, plane_map_info)
                manifest_rows.append(record)
                print(f"  [{file_number:02d}/{len(files):02d}] {output_path.name}: "
                      f"{record['selected_particles']:,} particles, plane collection "
                      f"{'present' if record['plane_collection_present'] else 'ABSENT'}, plane hits "
                      f"{record['plane_hits_total']:,} total / {record['plane_hits_accepted']:,} accepted / "
                      f"{record['plane_hits_dropped_not_primary']:,} dropped (not primary) / "
                      f"{record['plane_hits_secondary_flagged']:,} secondary-flagged", flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    temporary_manifest = manifest_path.with_suffix(".tmp.csv")
    pd.DataFrame(manifest_rows).to_csv(temporary_manifest, index=False)
    temporary_manifest.replace(manifest_path)
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
