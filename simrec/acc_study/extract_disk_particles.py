#!/usr/bin/env python3
"""Extract reusable per-primary disk-hit shards from acceptance ROOT files.

This is the expensive stage and should normally run once. Each output NPZ has
one row per selected generated primary pi+ and retains zero-hit particles. Eta
and momentum cuts are deliberately absent: they belong in the later reduction
stage so many selections can reuse the same extraction.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from mc_tracking_hits import KEY, iter_mc_tracking_hits
from reduce_disk_acceptance import COLLECTION, DISKS, PARTICLE_PDG, VERTEX_LABELS, configuration_name


FLOAT_COLUMNS = (
    "px_GeV", "py_GeV", "pz_GeV", "p_GeV", "eta", "phi_rad",
    "vertex_x_mm", "vertex_y_mm", "vertex_z_mm",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Root directory for configuration/shard NPZ files.")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0, -10, 10],
                        choices=sorted(VERTEX_LABELS))
    parser.add_argument("--step-size", type=int, default=10_000)
    parser.add_argument("--max-files-per-side", type=int,
                        help="Testing option: extract only the first N ROOT files per side.")
    parser.add_argument("--stop-events-per-file", type=int,
                        help="Testing option: extract only this many entries per ROOT file.")
    return parser.parse_args()


def append_block(storage: dict, block: dict, disk_rows: list[tuple[str, int, int, float]]) -> None:
    """Append one event block as compact per-particle arrays."""
    particles = block["particles"]
    hits = block["hits"]
    particle_index = pd.MultiIndex.from_frame(particles[KEY])
    number_of_particles = len(particles)

    event_entry = particles["event_entry"].to_numpy(dtype=np.int64)
    mc_index = particles["mc_index"].to_numpy(dtype=np.int64)
    if np.any((event_entry < 0) | (event_entry > np.iinfo(np.uint32).max)):
        raise ValueError("event_entry does not fit uint32")
    if np.any((mc_index < 0) | (mc_index > np.iinfo(np.uint32).max)):
        raise ValueError("mc_index does not fit uint32")
    storage["event_entry"].append(event_entry.astype(np.uint32))
    storage["mc_index"].append(mc_index.astype(np.uint32))
    for name in FLOAT_COLUMNS:
        storage[name].append(particles[name].to_numpy(dtype=np.float32))

    hit_mask = np.zeros(number_of_particles, dtype=np.uint8)
    hit_count = np.zeros((number_of_particles, 5), dtype=np.uint16)
    hit_x = np.full((number_of_particles, 5), np.nan, dtype=np.float32)
    hit_y = np.full((number_of_particles, 5), np.nan, dtype=np.float32)
    hit_z = np.full((number_of_particles, 5), np.nan, dtype=np.float32)

    for disk_index, (_, system, layer, _) in enumerate(disk_rows):
        disk_hits = hits.loc[(hits.hit_collection == COLLECTION)
                             & (hits.system == system) & (hits.layer == layer)]
        if disk_hits.empty:
            continue
        grouped = disk_hits.groupby(KEY, observed=True)
        counts = grouped.size().reindex(particle_index, fill_value=0).to_numpy(dtype=np.int64)
        if np.any(counts > np.iinfo(np.uint16).max):
            raise ValueError("per-particle disk hit count does not fit uint16")
        positions = grouped[["x_mm", "y_mm", "z_mm"]].mean().reindex(particle_index)
        has_hit = counts > 0
        hit_mask[has_hit] |= np.uint8(1 << disk_index)
        hit_count[:, disk_index] = counts.astype(np.uint16)
        hit_x[:, disk_index] = positions.x_mm.to_numpy(dtype=np.float32)
        hit_y[:, disk_index] = positions.y_mm.to_numpy(dtype=np.float32)
        hit_z[:, disk_index] = positions.z_mm.to_numpy(dtype=np.float32)

    storage["hit_mask"].append(hit_mask)
    storage["hit_count"].append(hit_count)
    storage["mean_hit_x_mm"].append(hit_x)
    storage["mean_hit_y_mm"].append(hit_y)
    storage["mean_hit_z_mm"].append(hit_z)


def extract_file(filename: Path, output_path: Path, side: str, configuration: str,
                 step_size: int, stop: Optional[int]) -> dict:
    """Extract one ROOT file atomically and return one manifest record."""
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite extracted shard: {output_path}")
    storage = {name: [] for name in (
        "event_entry", "mc_index", *FLOAT_COLUMNS, "hit_mask", "hit_count",
        "mean_hit_x_mm", "mean_hit_y_mm", "mean_hit_z_mm",
    )}
    source_metadata = None
    processed_entries = 0
    for block in iter_mc_tracking_hits(
        filename, collections=COLLECTION, primary_only=True, pdgs=[PARTICLE_PDG],
        stop=stop, step_size=step_size,
    ):
        append_block(storage, block, DISKS[side])
        source_metadata = block["metadata"]
        processed_entries = block["metadata"]["entry_range"][1]

    arrays = {}
    for name, parts in storage.items():
        if parts:
            arrays[name] = np.concatenate(parts, axis=0)
        elif name in ("hit_count", "mean_hit_x_mm", "mean_hit_y_mm", "mean_hit_z_mm"):
            dtype = np.uint16 if name == "hit_count" else np.float32
            arrays[name] = np.empty((0, 5), dtype=dtype)
        else:
            dtype = np.uint32 if name in ("event_entry", "mc_index") else np.float32
            arrays[name] = np.empty(0, dtype=dtype)

    metadata = {
        "format_version": 1,
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
        "units": "momenta GeV; positions mm; angles dimensionless/radians",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".tmp.npz")
    np.savez_compressed(temporary_path,
                        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)), **arrays)
    temporary_path.replace(output_path)
    return {"configuration": configuration, "side": side, "source_root": str(filename.resolve()),
            "shard": str(output_path.resolve()), "processed_entries": processed_entries,
            "selected_particles": len(arrays["event_entry"]), "bytes": output_path.stat().st_size}


def main() -> None:
    args = parse_args()
    if args.step_size < 1:
        raise SystemExit("ERROR: --step-size must be positive")
    if args.max_files_per_side is not None and args.max_files_per_side < 1:
        raise SystemExit("ERROR: --max-files-per-side must be positive")
    if args.stop_events_per_file is not None and args.stop_events_per_file < 1:
        raise SystemExit("ERROR: --stop-events-per-file must be positive")

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
                                      args.step_size, args.stop_events_per_file)
                manifest_rows.append(record)
                print(f"  [{file_number:02d}/{len(files):02d}] {output_path.name}: "
                      f"{record['selected_particles']:,} particles, {record['bytes']:,} bytes", flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "extraction_manifest.csv"
    temporary_manifest = manifest_path.with_suffix(".tmp.csv")
    pd.DataFrame(manifest_rows).to_csv(temporary_manifest, index=False)
    temporary_manifest.replace(manifest_path)
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
