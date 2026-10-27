#!/usr/bin/env python3
"""Plot actual measured hit-particle counts in radius and azimuth.

Each generated primary with one or more associated hits on a disk contributes
once, at the mean (x, y) of its associated hits stored in the extracted shard.
Thus these are hit-associated particle counts, not raw SimTrackerHit counts.
No straight-line projection is used. A fraction map is not formed because a
missed particle has no measured hit radius or azimuth.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd

from reduce_disk_acceptance import DISKS, VERTEX_LABELS, configuration_name


DEFAULT_MOMENTUM_BINS = [
    (0.5, 1.5),
    (1.5, 3.0),
    (3.0, 5.0),
    (5.0, 10.0),
    (10.0, 20.01),  # include the gun's endpoint at 20 GeV
]
R_MAX_MM = 450.0
R_BIN_WIDTH_MM = 10.0
PHI_EDGES_RAD = np.linspace(-math.pi, math.pi, 65)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracted-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New output directory; existing output is never overwritten.")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0],
                        choices=sorted(VERTEX_LABELS))
    parser.add_argument("--momentum-bin", type=float, nargs=2, action="append",
                        metavar=("MIN_GEV", "MAX_GEV"),
                        help="Half-open momentum interval; may be repeated.")
    parser.add_argument("--r-max-mm", type=float, default=R_MAX_MM)
    parser.add_argument("--r-bin-width-mm", type=float, default=R_BIN_WIDTH_MM)
    return parser.parse_args()


def disk_labels() -> list[str]:
    return [row[0] for side in ("negative", "positive") for row in DISKS[side]]


def momentum_tag(low: float, high: float) -> str:
    return f"p{low:g}_to_{high:g}".replace(".", "p")


def accumulate_shards(extracted_root: Path, vertex_z_mm: int,
                      momentum_bins: list[tuple[float, float]],
                      r_edges: np.ndarray) -> list[dict]:
    """Read each shard once; bin hit-associated primaries at their mean hit xy."""
    accumulators = []
    for low, high in momentum_bins:
        accumulators.append({
            "counts": np.zeros((10, len(r_edges) - 1, len(PHI_EDGES_RAD) - 1), dtype=np.int64),
            "selected_primary_total": np.zeros(10, dtype=np.int64),
            "hit_primary_total": np.zeros(10, dtype=np.int64),
            "binned_hit_primary_total": np.zeros(10, dtype=np.int64),
            "outside_r_range": np.zeros(10, dtype=np.int64),
            "momentum_low_GeV": low,
            "momentum_high_GeV": high,
        })

    for side in ("negative", "positive"):
        configuration = configuration_name(vertex_z_mm, side)
        shard_dir = extracted_root / configuration
        shards = sorted(shard_dir.glob("particles_*.npz"))
        if not shards:
            raise FileNotFoundError(
                f"No extracted particle shards for {configuration} under {shard_dir}"
            )
        disk_offset = 0 if side == "negative" else 5
        print(f"{configuration}: reading {len(shards)} extracted shards", flush=True)

        for shard_number, shard_path in enumerate(shards, start=1):
            with np.load(shard_path, allow_pickle=False) as stored:
                momentum = stored["p_GeV"]
                hit_mask = stored["hit_mask"]
                hit_x = stored["mean_hit_x_mm"]
                hit_y = stored["mean_hit_y_mm"]

                for accumulator in accumulators:
                    selected = ((momentum >= accumulator["momentum_low_GeV"])
                                & (momentum < accumulator["momentum_high_GeV"]))
                    if not selected.any():
                        continue
                    selected_mask = hit_mask[selected]
                    selected_x = hit_x[selected]
                    selected_y = hit_y[selected]
                    for local_index in range(5):
                        disk_index = disk_offset + local_index
                        has_hit = (selected_mask & np.uint8(1 << local_index)) != 0
                        accumulator["selected_primary_total"][disk_index] += int(selected.sum())
                        accumulator["hit_primary_total"][disk_index] += int(has_hit.sum())
                        if not has_hit.any():
                            continue

                        x = selected_x[has_hit, local_index].astype(float)
                        y = selected_y[has_hit, local_index].astype(float)
                        if not (np.isfinite(x).all() and np.isfinite(y).all()):
                            raise ValueError(f"Non-finite measured hit coordinates in {shard_path}")
                        radius = np.hypot(x, y)
                        phi = np.arctan2(y, x)
                        inside = (radius >= r_edges[0]) & (radius <= r_edges[-1])
                        counts = np.histogram2d(
                            radius[inside], phi[inside], bins=(r_edges, PHI_EDGES_RAD)
                        )[0].astype(np.int64)
                        accumulator["counts"][disk_index] += counts
                        accumulator["binned_hit_primary_total"][disk_index] += int(inside.sum())
                        accumulator["outside_r_range"][disk_index] += int((~inside).sum())

            if shard_number % 10 == 0 or shard_number == len(shards):
                print(f"  {side}: {shard_number}/{len(shards)} shards", flush=True)

    for accumulator in accumulators:
        if np.any(accumulator["counts"].sum(axis=(1, 2))
                  != accumulator["binned_hit_primary_total"]):
            raise AssertionError("R-phi histogram counts do not match binned hit primaries")
    return accumulators


def plot_counts(accumulator: dict, vertex_z_mm: int, r_edges: np.ndarray,
                output_path: Path | None = None):
    labels = disk_labels()
    fig, axes = plt.subplots(5, 2, figsize=(13, 15), constrained_layout=True)
    maximum = max(2, int(accumulator["counts"].max()))
    last_image = None
    for row in range(5):
        for column in range(2):
            disk_index = column * 5 + row
            counts = accumulator["counts"][disk_index]
            values = np.ma.masked_less_equal(counts.T, 0)
            axis = axes[row, column]
            last_image = axis.pcolormesh(
                r_edges, PHI_EDGES_RAD, values, shading="auto",
                norm=LogNorm(vmin=1, vmax=maximum), cmap="viridis"
            )
            axis.set_title(f"{labels[disk_index]}: hit-associated primaries")
            axis.set_xlabel("measured hit radius $R$ [mm]")
            axis.set_ylabel("measured hit $\\phi$ [rad]")
            axis.set_xlim(r_edges[0], r_edges[-1])
            axis.set_ylim(-math.pi, math.pi)

    fig.colorbar(last_image, ax=axes.ravel().tolist(), shrink=0.78,
                 label="generated primaries per bin")
    low = accumulator["momentum_low_GeV"]
    high = accumulator["momentum_high_GeV"]
    fig.suptitle(
        f"Measured disk hit positions, z_vertex={vertex_z_mm} mm, "
        f"{low:g} <= p < {high:g} GeV\n"
        "one primary per disk at its mean associated-hit position",
        fontsize=14,
    )
    if output_path is not None:
        fig.savefig(output_path, dpi=160)
    return fig


def main() -> None:
    args = parse_args()
    momentum_bins = ([tuple(bounds) for bounds in args.momentum_bin]
                     if args.momentum_bin else DEFAULT_MOMENTUM_BINS)
    if args.r_max_mm <= 0 or args.r_bin_width_mm <= 0:
        raise SystemExit("ERROR: radial maximum and bin width must be positive")
    for low, high in momentum_bins:
        if not (np.isfinite(low) and np.isfinite(high) and low >= 0 and low < high):
            raise SystemExit(f"ERROR: invalid momentum bin [{low}, {high})")
    if len(set(momentum_bins)) != len(momentum_bins):
        raise SystemExit("ERROR: duplicate momentum bins")
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {args.output_dir}")

    number_r_bins = int(math.ceil(args.r_max_mm / args.r_bin_width_mm))
    r_edges = np.linspace(0.0, args.r_max_mm, number_r_bins + 1)
    args.output_dir.mkdir(parents=True)
    summary_rows = []
    labels = disk_labels()

    for vertex_z_mm in args.vertices:
        accumulators = accumulate_shards(
            args.extracted_root, vertex_z_mm, momentum_bins, r_edges
        )
        pdf_path = args.output_dir / f"hit_r_phi_counts_vz_{VERTEX_LABELS[vertex_z_mm]}mm.pdf"
        with PdfPages(pdf_path) as pages:
            for accumulator in accumulators:
                low = accumulator["momentum_low_GeV"]
                high = accumulator["momentum_high_GeV"]
                tag = momentum_tag(low, high)
                png_path = args.output_dir / (
                    f"hit_r_phi_vz_{VERTEX_LABELS[vertex_z_mm]}mm_{tag}_counts.png"
                )
                figure = plot_counts(accumulator, vertex_z_mm, r_edges, png_path)
                pages.savefig(figure)
                plt.close(figure)

                metadata = {
                    "vertex_z_mm": vertex_z_mm,
                    "momentum_range_GeV_half_open": [low, high],
                    "coordinate_definition": "radius and phi of per-particle mean associated hit x,y",
                    "count_definition": "one generated primary per disk with >=1 associated hit",
                    "r_edges_mm": r_edges.tolist(),
                    "phi_edges_rad": PHI_EDGES_RAD.tolist(),
                    "disk_order": labels,
                    "raw_hit_multiplicity_used": False,
                    "projection_used": False,
                }
                np.savez_compressed(
                    args.output_dir / f"hit_r_phi_vz_{VERTEX_LABELS[vertex_z_mm]}mm_{tag}.npz",
                    metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
                    counts=accumulator["counts"],
                    selected_primary_total=accumulator["selected_primary_total"],
                    hit_primary_total=accumulator["hit_primary_total"],
                    binned_hit_primary_total=accumulator["binned_hit_primary_total"],
                    outside_r_range=accumulator["outside_r_range"],
                    r_edges_mm=r_edges,
                    phi_edges_rad=PHI_EDGES_RAD,
                )

                for disk_index, label in enumerate(labels):
                    summary_rows.append({
                        "vertex_z_mm": vertex_z_mm,
                        "momentum_min_GeV": low,
                        "momentum_max_GeV_exclusive": high,
                        "disk": label,
                        "selected_generated_primaries": int(
                            accumulator["selected_primary_total"][disk_index]
                        ),
                        "primaries_with_disk_hit": int(
                            accumulator["hit_primary_total"][disk_index]
                        ),
                        "primaries_binned_in_r_phi": int(
                            accumulator["binned_hit_primary_total"][disk_index]
                        ),
                        "primaries_outside_r_range": int(
                            accumulator["outside_r_range"][disk_index]
                        ),
                    })
        print(f"Wrote {pdf_path}", flush=True)

    summary_path = args.output_dir / "hit_r_phi_counts_summary.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
