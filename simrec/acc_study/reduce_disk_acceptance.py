#!/usr/bin/env python3
"""Reduce extracted particle shards or ROOT files into acceptance summaries.

The event-level numerator is the number of generated primary pi+ particles with
at least one directly associated TrackerEndcapHit on a disk. Multiple hits from
one particle on the same disk count once. The integrated denominator is every
selected generated particle in the matching eta sample.

For 2D maps, every generated particle is assigned a reference (x, y) coordinate
by straight-line projection from its generated vertex and momentum to the
nominal disk z. This gives missing-hit particles a well-defined coordinate. It
is a reference coordinate, not a magnetic-field propagation; projection
residuals against observed hit positions are saved for review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from mc_tracking_hits import KEY, iter_mc_tracking_hits


COLLECTION = "TrackerEndcapHits"
PARTICLE_PDG = 211

# A disk is identified by (system, layer), never by layer alone. Nominal z is
# the centre of the sensitive stack, estimated from the installed geometry.
DISKS = {
    "negative": [
        ("ED0", 68, 1, -250.0),
        ("ED1", 69, 1, -450.0),
        ("ED2", 70, 2, -650.0),
        ("ED3", 70, 3, -850.0),
        ("ED4", 70, 4, -1020.0),
    ],
    "positive": [
        ("HD0", 77, 1, 250.0),
        ("HD1", 78, 1, 450.0),
        ("HD2", 79, 2, 700.0),
        ("HD3", 79, 3, 950.0),
        ("HD4", 79, 4, 1200.0),
    ],
}

# acceptance_v1: 0, +/-10 mm; acceptance_v2_vz100mm: +/-100 mm (10 cm).
VERTEX_LABELS = {-100: "m100", -10: "m010", 0: "000", 10: "p010", 100: "p100"}
ETA_LABELS = {
    "negative": "m3p8_to_m0p6",
    "positive": "p0p6_to_p3p8",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--extracted-root", type=Path,
                        help="Reusable particle-shard directory from extract_disk_particles.py.")
    inputs.add_argument("--campaign-root", type=Path,
                        help="Legacy direct-ROOT mode; rereads the expensive simulation files.")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Directory for per-vertex NPZ/CSV summaries.")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0, -10, 10],
                        choices=sorted(VERTEX_LABELS), help="Vertex z values to process [mm].")
    parser.add_argument("--abs-eta-range", type=float, nargs=2, metavar=("MIN", "MAX"),
                        help="Optional half-open |eta| selection [MIN, MAX).")
    parser.add_argument("--momentum-range-gev", type=float, nargs=2, metavar=("MIN", "MAX"),
                        help="Optional half-open generated |p| selection [MIN, MAX) GeV.")
    parser.add_argument("--step-size", type=int, default=10_000,
                        help="Events read per bounded-memory block (default: 10000).")
    parser.add_argument("--bin-size-mm", type=float, default=10.0,
                        help="Square 2D-bin width at each disk plane (default: 10 mm).")
    parser.add_argument("--xy-limit-mm", type=float, default=450.0,
                        help="Map range is +/- this value in x and y (default: 450 mm).")
    parser.add_argument("--max-files-per-side", type=int,
                        help="Testing option: process only the first N files per eta side.")
    parser.add_argument("--stop-events-per-file", type=int,
                        help="Testing option: stop after this many entries in every file.")
    return parser.parse_args()


def configuration_name(vertex_z_mm: int, side: str) -> str:
    return f"vz_{VERTEX_LABELS[vertex_z_mm]}mm_eta_{ETA_LABELS[side]}"


def wilson_interval(successes: int, total: int, z_value: float = 1.0) -> tuple[float, float]:
    """Return the approximately 68% Wilson binomial interval."""
    if total == 0:
        return np.nan, np.nan
    fraction = successes / total
    denominator = 1.0 + z_value**2 / total
    centre = (fraction + z_value**2 / (2.0 * total)) / denominator
    half_width = z_value * np.sqrt(
        fraction * (1.0 - fraction) / total + z_value**2 / (4.0 * total**2)
    ) / denominator
    return centre - half_width, centre + half_width


def new_accumulator(x_edges: np.ndarray, y_edges: np.ndarray) -> dict:
    shape = (10, len(x_edges) - 1, len(y_edges) - 1)
    return {
        "denominator_total": np.zeros(10, dtype=np.int64),
        "numerator_total": np.zeros(10, dtype=np.int64),
        "raw_hits_total": np.zeros(10, dtype=np.int64),
        "denominator_xy": np.zeros(shape, dtype=np.int64),
        "numerator_xy": np.zeros(shape, dtype=np.int64),
        "missing_xy": np.zeros(shape, dtype=np.int64),
        "outside_xy": np.zeros(10, dtype=np.int64),
        "invalid_projection": np.zeros(10, dtype=np.int64),
        "residual_count": np.zeros(10, dtype=np.int64),
        "residual_sum_x_mm": np.zeros(10, dtype=np.float64),
        "residual_sum_y_mm": np.zeros(10, dtype=np.float64),
        "residual_sum_r2_mm2": np.zeros(10, dtype=np.float64),
    }


def accumulate_block(accumulator: dict, block: dict, disk_offset: int,
                     disk_rows: list[tuple[str, int, int, float]],
                     x_edges: np.ndarray, y_edges: np.ndarray) -> None:
    """Reduce one bounded-memory block; no block-level table is retained."""
    particles = block["particles"]
    hits = block["hits"]
    particle_index = pd.MultiIndex.from_frame(particles[KEY])

    px = particles["px_GeV"].to_numpy(dtype=float)
    py = particles["py_GeV"].to_numpy(dtype=float)
    pz = particles["pz_GeV"].to_numpy(dtype=float)
    vertex_x = particles["vertex_x_mm"].to_numpy(dtype=float)
    vertex_y = particles["vertex_y_mm"].to_numpy(dtype=float)
    vertex_z = particles["vertex_z_mm"].to_numpy(dtype=float)

    for local_index, (_, system, layer, disk_z_mm) in enumerate(disk_rows):
        disk_index = disk_offset + local_index
        disk_hits = hits.loc[(hits.hit_collection == COLLECTION)
                             & (hits.system == system) & (hits.layer == layer)]
        unique_hit_keys = disk_hits[KEY].drop_duplicates()
        hit_particle_index = pd.MultiIndex.from_frame(unique_hit_keys)
        has_hit = particle_index.isin(hit_particle_index)

        accumulator["denominator_total"][disk_index] += len(particles)
        accumulator["numerator_total"][disk_index] += int(has_hit.sum())
        accumulator["raw_hits_total"][disk_index] += len(disk_hits)

        with np.errstate(divide="ignore", invalid="ignore"):
            scale = (disk_z_mm - vertex_z) / pz
            projected_x = vertex_x + scale * px
            projected_y = vertex_y + scale * py
        valid = np.isfinite(projected_x) & np.isfinite(projected_y)
        accumulator["invalid_projection"][disk_index] += int((~valid).sum())

        denominator_hist = np.histogram2d(
            projected_x[valid], projected_y[valid], bins=(x_edges, y_edges)
        )[0].astype(np.int64)
        numerator_hist = np.histogram2d(
            projected_x[valid & has_hit], projected_y[valid & has_hit],
            bins=(x_edges, y_edges)
        )[0].astype(np.int64)
        missing_hist = np.histogram2d(
            projected_x[valid & ~has_hit], projected_y[valid & ~has_hit],
            bins=(x_edges, y_edges)
        )[0].astype(np.int64)
        accumulator["denominator_xy"][disk_index] += denominator_hist
        accumulator["numerator_xy"][disk_index] += numerator_hist
        accumulator["missing_xy"][disk_index] += missing_hist
        accumulator["outside_xy"][disk_index] += int(valid.sum() - denominator_hist.sum())

        # Average multiple hit coordinates for a particle before comparing with
        # its projected coordinate. This is diagnostic only; acceptance does not
        # depend on the projection residual.
        if has_hit.any():
            observed = disk_hits.groupby(KEY, observed=True)[["x_mm", "y_mm"]].mean()
            observed = observed.reindex(particle_index[has_hit])
            dx = observed.x_mm.to_numpy() - projected_x[has_hit]
            dy = observed.y_mm.to_numpy() - projected_y[has_hit]
            finite_residual = np.isfinite(dx) & np.isfinite(dy)
            dx, dy = dx[finite_residual], dy[finite_residual]
            accumulator["residual_count"][disk_index] += len(dx)
            accumulator["residual_sum_x_mm"][disk_index] += dx.sum()
            accumulator["residual_sum_y_mm"][disk_index] += dy.sum()
            accumulator["residual_sum_r2_mm2"][disk_index] += np.square(dx).sum() + np.square(dy).sum()


def accumulate_extracted(accumulator: dict, stored, keep: np.ndarray, disk_offset: int,
                         disk_rows: list[tuple[str, int, int, float]],
                         x_edges: np.ndarray, y_edges: np.ndarray) -> None:
    """Reduce selected rows from one reusable particle shard."""
    px = stored["px_GeV"][keep].astype(float)
    py = stored["py_GeV"][keep].astype(float)
    pz = stored["pz_GeV"][keep].astype(float)
    vertex_x = stored["vertex_x_mm"][keep].astype(float)
    vertex_y = stored["vertex_y_mm"][keep].astype(float)
    vertex_z = stored["vertex_z_mm"][keep].astype(float)
    hit_mask = stored["hit_mask"][keep]
    hit_count = stored["hit_count"][keep]
    hit_x = stored["mean_hit_x_mm"][keep]
    hit_y = stored["mean_hit_y_mm"][keep]

    for local_index, (_, _, _, disk_z_mm) in enumerate(disk_rows):
        disk_index = disk_offset + local_index
        has_hit = (hit_mask & np.uint8(1 << local_index)) != 0
        accumulator["denominator_total"][disk_index] += len(hit_mask)
        accumulator["numerator_total"][disk_index] += int(has_hit.sum())
        accumulator["raw_hits_total"][disk_index] += int(hit_count[:, local_index].sum())

        with np.errstate(divide="ignore", invalid="ignore"):
            scale = (disk_z_mm - vertex_z) / pz
            projected_x = vertex_x + scale * px
            projected_y = vertex_y + scale * py
        valid = np.isfinite(projected_x) & np.isfinite(projected_y)
        accumulator["invalid_projection"][disk_index] += int((~valid).sum())
        denominator_hist = np.histogram2d(projected_x[valid], projected_y[valid],
                                          bins=(x_edges, y_edges))[0].astype(np.int64)
        numerator_hist = np.histogram2d(projected_x[valid & has_hit], projected_y[valid & has_hit],
                                        bins=(x_edges, y_edges))[0].astype(np.int64)
        missing_hist = np.histogram2d(projected_x[valid & ~has_hit], projected_y[valid & ~has_hit],
                                      bins=(x_edges, y_edges))[0].astype(np.int64)
        accumulator["denominator_xy"][disk_index] += denominator_hist
        accumulator["numerator_xy"][disk_index] += numerator_hist
        accumulator["missing_xy"][disk_index] += missing_hist
        accumulator["outside_xy"][disk_index] += int(valid.sum() - denominator_hist.sum())

        if has_hit.any():
            dx = hit_x[has_hit, local_index].astype(float) - projected_x[has_hit]
            dy = hit_y[has_hit, local_index].astype(float) - projected_y[has_hit]
            finite = np.isfinite(dx) & np.isfinite(dy)
            dx, dy = dx[finite], dy[finite]
            accumulator["residual_count"][disk_index] += len(dx)
            accumulator["residual_sum_x_mm"][disk_index] += dx.sum()
            accumulator["residual_sum_y_mm"][disk_index] += dy.sum()
            accumulator["residual_sum_r2_mm2"][disk_index] += np.square(dx).sum() + np.square(dy).sum()


def process_extracted_side(args: argparse.Namespace, configuration: str, side: str,
                           disk_offset: int, accumulator: dict,
                           x_edges: np.ndarray, y_edges: np.ndarray) -> list[dict]:
    """Apply late kinematic cuts while streaming small extracted NPZ shards."""
    shard_directory = args.extracted_root / configuration
    shards = sorted(shard_directory.glob("particles_*.npz"))
    if args.max_files_per_side is not None:
        shards = shards[:args.max_files_per_side]
    if not shards:
        raise FileNotFoundError(f"No extracted shards found in {shard_directory}")
    records = []
    print(f"{configuration}: reducing {len(shards)} extracted shards", flush=True)
    for shard_number, shard in enumerate(shards, start=1):
        with np.load(shard, allow_pickle=False) as stored:
            shard_metadata = json.loads(str(stored["metadata_json"]))
            if shard_metadata["configuration"] != configuration or shard_metadata["side"] != side:
                raise ValueError(f"Shard metadata/configuration mismatch: {shard}")
            eta = stored["eta"].astype(float)
            momentum = stored["p_GeV"].astype(float)
            keep = np.ones(len(eta), dtype=bool)
            if args.abs_eta_range is not None:
                keep &= (np.abs(eta) >= args.abs_eta_range[0]) & (np.abs(eta) < args.abs_eta_range[1])
            if args.momentum_range_gev is not None:
                keep &= ((momentum >= args.momentum_range_gev[0])
                         & (momentum < args.momentum_range_gev[1]))
            accumulate_extracted(accumulator, stored, keep, disk_offset, DISKS[side], x_edges, y_edges)
            selected_particles = int(keep.sum())
        records.append({
            "side": side, "configuration": configuration,
            "path": str(shard.resolve()), "source_root": shard_metadata["source_root"],
            "bytes": shard.stat().st_size,
            "processed_entries": shard_metadata["processed_entries"],
            "extracted_particles": shard_metadata["selected_particles"],
            "selected_particles": selected_particles,
        })
        print(f"  [{shard_number:02d}/{len(shards):02d}] {shard.name}: "
              f"{selected_particles:,} selected", flush=True)
    return records


def process_vertex(args: argparse.Namespace, vertex_z_mm: int,
                   x_edges: np.ndarray, y_edges: np.ndarray) -> None:
    disk_rows = DISKS["negative"] + DISKS["positive"]
    accumulator = new_accumulator(x_edges, y_edges)
    input_records = []

    for side, disk_offset in (("negative", 0), ("positive", 5)):
        config = configuration_name(vertex_z_mm, side)
        if args.extracted_root is not None:
            input_records.extend(process_extracted_side(
                args, config, side, disk_offset, accumulator, x_edges, y_edges))
            continue
        root_directory = args.campaign_root / config / "rootfiles"
        files = sorted(path for path in root_directory.glob("sim_*.root")
                       if ".tmp." not in path.name)
        if args.max_files_per_side is not None:
            files = files[:args.max_files_per_side]
        if not files:
            raise FileNotFoundError(f"No simulation ROOT files found in {root_directory}")

        print(f"{config}: processing {len(files)} simulation files", flush=True)
        eta_range = None
        if args.abs_eta_range is not None:
            eta_low, eta_high = args.abs_eta_range
            eta_range = (-eta_high, -eta_low) if side == "negative" else (eta_low, eta_high)
        for file_number, filename in enumerate(files, start=1):
            processed_entries = 0
            selected_particles = 0
            for block in iter_mc_tracking_hits(
                filename,
                collections=COLLECTION,
                primary_only=True,
                pdgs=[PARTICLE_PDG],
                eta_range=eta_range,
                p_range=args.momentum_range_gev,
                stop=args.stop_events_per_file,
                step_size=args.step_size,
            ):
                accumulate_block(accumulator, block, disk_offset, DISKS[side], x_edges, y_edges)
                selected_particles += len(block["particles"])
                processed_entries = block["metadata"]["entry_range"][1]
            input_records.append({
                "side": side,
                "configuration": config,
                "path": str(filename.resolve()),
                "bytes": filename.stat().st_size,
                "processed_entries": processed_entries,
                "selected_particles": selected_particles,
            })
            print(f"  [{file_number:02d}/{len(files):02d}] {filename.name}: "
                  f"{processed_entries} entries", flush=True)

    labels = np.asarray([row[0] for row in disk_rows])
    systems = np.asarray([row[1] for row in disk_rows], dtype=np.int64)
    layers = np.asarray([row[2] for row in disk_rows], dtype=np.int64)
    disk_z = np.asarray([row[3] for row in disk_rows], dtype=np.float64)
    sides = np.asarray(["negative"] * 5 + ["positive"] * 5)

    summary_rows = []
    for disk_index, label in enumerate(labels):
        total = int(accumulator["denominator_total"][disk_index])
        passed = int(accumulator["numerator_total"][disk_index])
        acceptance = passed / total if total else np.nan
        ci_low, ci_high = wilson_interval(passed, total)
        residual_count = int(accumulator["residual_count"][disk_index])
        residual_rms = np.sqrt(accumulator["residual_sum_r2_mm2"][disk_index] / residual_count) \
            if residual_count else np.nan
        summary_rows.append({
            "vertex_z_mm": vertex_z_mm,
            "side": sides[disk_index],
            "disk": label,
            "system": systems[disk_index],
            "layer": layers[disk_index],
            "nominal_z_mm": disk_z[disk_index],
            "n_generated": total,
            "n_with_hit": passed,
            "n_raw_hits": int(accumulator["raw_hits_total"][disk_index]),
            "acceptance": acceptance,
            "wilson68_low": ci_low,
            "wilson68_high": ci_high,
            "n_projected_outside_map": int(accumulator["outside_xy"][disk_index]),
            "n_invalid_projection": int(accumulator["invalid_projection"][disk_index]),
            "projection_residual_rms_mm": residual_rms,
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    vertex_label = f"vz_{VERTEX_LABELS[vertex_z_mm]}mm"
    csv_path = args.output_dir / f"disk_acceptance_{vertex_label}.csv"
    npz_path = args.output_dir / f"disk_acceptance_{vertex_label}.npz"
    metadata = {
        "format_version": 2,
        "input_mode": "extracted_npz" if args.extracted_root is not None else "direct_root",
        "vertex_z_mm": vertex_z_mm,
        "particle_pdg": PARTICLE_PDG,
        "primary_selection": "generatorStatus == 1",
        "abs_eta_range": args.abs_eta_range,
        "momentum_range_GeV": args.momentum_range_gev,
        "hit_collection": COLLECTION,
        "integrated_denominator": "all selected generated primary particles in the matching eta-side sample",
        "map_coordinate": "straight-line projection from generated vertex/momentum to nominal disk z",
        "nominal_z_source": "compact/tracking/definitions_craterlake.xml",
        "units": "positions mm; momentum GeV; acceptance dimensionless",
        "bin_size_mm": args.bin_size_mm,
        "xy_limit_mm": args.xy_limit_mm,
        "step_size": args.step_size if args.extracted_root is None else None,
        "input_files": input_records,
    }

    csv_temp = csv_path.with_suffix(".tmp.csv")
    pd.DataFrame(summary_rows).to_csv(csv_temp, index=False)
    csv_temp.replace(csv_path)
    npz_temp = npz_path.with_suffix(".tmp.npz")
    np.savez_compressed(
        npz_temp,
        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
        disk_label=labels,
        side=sides,
        system=systems,
        layer=layers,
        nominal_z_mm=disk_z,
        x_edges_mm=x_edges,
        y_edges_mm=y_edges,
        **accumulator,
    )
    npz_temp.replace(npz_path)
    print(f"Wrote {csv_path}")
    print(f"Wrote {npz_path}")


def main() -> None:
    args = parse_args()
    if args.step_size < 1 or args.bin_size_mm <= 0 or args.xy_limit_mm <= 0:
        raise SystemExit("ERROR: step size, bin size, and map limit must be positive")
    for option_name, bounds in (("--abs-eta-range", args.abs_eta_range),
                                ("--momentum-range-gev", args.momentum_range_gev)):
        if bounds is not None and (not np.all(np.isfinite(bounds)) or bounds[0] < 0
                                   or bounds[0] >= bounds[1]):
            raise SystemExit(f"ERROR: {option_name} requires finite 0 <= MIN < MAX")
    if args.max_files_per_side is not None and args.max_files_per_side < 1:
        raise SystemExit("ERROR: --max-files-per-side must be positive")
    if args.stop_events_per_file is not None and args.stop_events_per_file < 1:
        raise SystemExit("ERROR: --stop-events-per-file must be positive")
    if args.extracted_root is not None and args.stop_events_per_file is not None:
        raise SystemExit("ERROR: --stop-events-per-file applies only to direct ROOT mode")
    number_of_bins = int(round(2.0 * args.xy_limit_mm / args.bin_size_mm))
    if not np.isclose(number_of_bins * args.bin_size_mm, 2.0 * args.xy_limit_mm):
        raise SystemExit("ERROR: 2*xy-limit must be exactly divisible by bin-size")
    edges = np.linspace(-args.xy_limit_mm, args.xy_limit_mm, number_of_bins + 1)
    for vertex_z_mm in args.vertices:
        process_vertex(args, vertex_z_mm, edges, edges.copy())


if __name__ == "__main__":
    main()
