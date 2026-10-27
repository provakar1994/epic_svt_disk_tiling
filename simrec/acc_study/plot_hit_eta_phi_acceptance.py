#!/usr/bin/env python3
"""Map disk hit acceptance in generated (eta, phi), without track projection.

The denominator is every generated primary pi+ in a half-open momentum bin.
The numerator is the subset with at least one directly associated hit on a
given disk. Each generated particle is counted once per disk. Since eta and
phi come from the generated momentum, this map does not use a disk-plane
projection or observed hit coordinates.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.backends.backend_pdf import PdfPages
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
PHI_MIN_RAD = -math.pi
PHI_MAX_RAD = math.pi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracted-root", type=Path, required=True,
                        help="Root directory containing reusable particle NPZ shards.")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New output directory. Existing output is never overwritten.")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0],
                        choices=sorted(VERTEX_LABELS))
    parser.add_argument("--momentum-bin", type=float, nargs=2, action="append",
                        metavar=("MIN_GEV", "MAX_GEV"),
                        help="Half-open momentum bin; may be repeated. Defaults scan 0.5--20 GeV.")
    parser.add_argument("--eta-bin-width", type=float, default=0.1,
                        help="Eta bin width; default 0.1.")
    parser.add_argument("--minimum-bin-denominator", type=int, default=20,
                        help="Mask acceptance bins with fewer generated particles; default 20.")
    return parser.parse_args()


def make_eta_edges(side: str, bin_width: float) -> np.ndarray:
    """Return edges covering the gun's generated eta range for one side."""
    low, high = (-3.8, -0.6) if side == "negative" else (0.6, 3.8)
    number_of_bins = int(round((high - low) / bin_width))
    if not np.isclose(number_of_bins * bin_width, high - low):
        raise ValueError("eta bin width must divide the generated 3.2-unit eta span")
    return np.linspace(low, high, number_of_bins + 1)


def accumulate_shards(extracted_root: Path, vertex_z_mm: int,
                      momentum_bins: list[tuple[float, float]],
                      eta_bin_width: float) -> list[dict]:
    """Read each shard once and accumulate denominator/numerator maps."""
    eta_edges_by_side = {
        "negative": make_eta_edges("negative", eta_bin_width),
        "positive": make_eta_edges("positive", eta_bin_width),
    }
    phi_edges = np.linspace(PHI_MIN_RAD, PHI_MAX_RAD, 65)
    number_eta_bins = len(eta_edges_by_side["positive"]) - 1
    accumulators = []
    for low, high in momentum_bins:
        accumulators.append({
            "denominator": np.zeros((10, number_eta_bins, len(phi_edges) - 1), dtype=np.int64),
            "numerator": np.zeros((10, number_eta_bins, len(phi_edges) - 1), dtype=np.int64),
            "denominator_total": np.zeros(10, dtype=np.int64),
            "numerator_total": np.zeros(10, dtype=np.int64),
            "eta_edges": np.stack([
                eta_edges_by_side[side] for side in ("negative", "positive") for _ in range(5)
            ]),
            "phi_edges": phi_edges,
            "momentum_low_GeV": low,
            "momentum_high_GeV": high,
        })

    found_any = False
    for side in ("negative", "positive"):
        configuration = configuration_name(vertex_z_mm, side)
        shard_dir = extracted_root / configuration
        shards = sorted(shard_dir.glob("particles_*.npz"))
        if not shards:
            raise FileNotFoundError(
                f"No extracted particle shards for {configuration} under {shard_dir}"
            )
        found_any = True
        disk_rows = DISKS[side]
        disk_offset = 0 if side == "negative" else 5
        eta_edges = eta_edges_by_side[side]

        print(f"{configuration}: reading {len(shards)} extracted shards", flush=True)
        for shard_number, shard_path in enumerate(shards, start=1):
            with np.load(shard_path, allow_pickle=False) as stored:
                momentum = stored["p_GeV"]
                eta = stored["eta"]
                phi = stored["phi_rad"]
                hit_mask = stored["hit_mask"]

                for accumulator in accumulators:
                    selected = ((momentum >= accumulator["momentum_low_GeV"])
                                & (momentum < accumulator["momentum_high_GeV"]))
                    if not selected.any():
                        continue
                    selected_eta = eta[selected]
                    selected_phi = phi[selected]
                    denominator = np.histogram2d(
                        selected_eta, selected_phi, bins=(eta_edges, phi_edges)
                    )[0].astype(np.int64)

                    for local_disk_index, disk_row in enumerate(disk_rows):
                        disk_index = disk_offset + local_disk_index
                        has_hit = (hit_mask[selected] & np.uint8(1 << local_disk_index)) != 0
                        numerator = np.histogram2d(
                            selected_eta[has_hit], selected_phi[has_hit],
                            bins=(eta_edges, phi_edges)
                        )[0].astype(np.int64)
                        accumulator["denominator"][disk_index] += denominator
                        accumulator["numerator"][disk_index] += numerator
                        accumulator["denominator_total"][disk_index] += int(selected.sum())
                        accumulator["numerator_total"][disk_index] += int(has_hit.sum())

            if shard_number % 10 == 0 or shard_number == len(shards):
                print(f"  {side}: {shard_number}/{len(shards)} shards", flush=True)

    if not found_any:
        raise FileNotFoundError(f"No shards found below {extracted_root}")

    for accumulator in accumulators:
        if np.any(accumulator["numerator"] > accumulator["denominator"]):
            raise AssertionError("hit numerator exceeds generated denominator")
    return accumulators


def disk_labels() -> list[str]:
    return [row[0] for side in ("negative", "positive") for row in DISKS[side]]


def momentum_tag(low: float, high: float) -> str:
    return f"p{low:g}_to_{high:g}".replace(".", "p")


def plot_map(accumulator: dict, vertex_z_mm: int, minimum_bin_denominator: int,
             kind: str, output_path: Path | None = None):
    """Plot a 2x5 grid in eta (horizontal) and phi (vertical)."""
    labels = disk_labels()
    fig, axes = plt.subplots(5, 2, figsize=(13, 15), constrained_layout=True)
    last_image = None
    shared_count_max = max(2, int(accumulator["numerator"].max()))
    for row in range(5):
        for column in range(2):
            disk_index = column * 5 + row
            axis = axes[row, column]
            denominator = accumulator["denominator"][disk_index]
            numerator = accumulator["numerator"][disk_index]
            eta_edges = accumulator["eta_edges"][disk_index]
            phi_edges = accumulator["phi_edges"]

            if kind == "counts":
                values = np.ma.masked_less_equal(numerator.T, 0)
                last_image = axis.pcolormesh(
                    eta_edges, phi_edges, values, shading="auto",
                    norm=LogNorm(vmin=1, vmax=shared_count_max), cmap="viridis"
                )
                title = f"{labels[disk_index]} hit particles"
            else:
                fraction = np.divide(
                    numerator, denominator,
                    out=np.zeros_like(numerator, dtype=float), where=denominator > 0
                )
                values = np.ma.masked_where(
                    denominator < minimum_bin_denominator, fraction
                )
                last_image = axis.pcolormesh(
                    eta_edges, phi_edges, values.T, shading="auto",
                    vmin=0.0, vmax=1.0, cmap="viridis"
                )
                title = f"{labels[disk_index]}: hit / generated"

            axis.set_title(title)
            axis.set_xlabel("generated $\\eta$")
            axis.set_ylabel("generated $\\phi$ [rad]")
            axis.set_xlim(eta_edges[0], eta_edges[-1])
            axis.set_ylim(PHI_MIN_RAD, PHI_MAX_RAD)

    fig.colorbar(last_image, ax=axes.ravel().tolist(), shrink=0.78,
                 label="particles per bin" if kind == "counts" else "hit fraction")
    low = accumulator["momentum_low_GeV"]
    high = accumulator["momentum_high_GeV"]
    title = (f"Generated-particle disk hit map, z_vertex={vertex_z_mm} mm, "
             f"{low:g} <= p < {high:g} GeV")
    if kind == "fraction":
        title += f" (bins require >= {minimum_bin_denominator} generated particles)"
    fig.suptitle(title, fontsize=15)
    if output_path is not None:
        fig.savefig(output_path, dpi=160)
    return fig


def main() -> None:
    args = parse_args()
    momentum_bins = [tuple(bounds) for bounds in args.momentum_bin] if args.momentum_bin else DEFAULT_MOMENTUM_BINS
    if args.eta_bin_width <= 0 or args.minimum_bin_denominator < 1:
        raise SystemExit("ERROR: eta-bin-width and minimum-bin-denominator must be positive")
    for low, high in momentum_bins:
        if not (np.isfinite(low) and np.isfinite(high) and low >= 0 and low < high):
            raise SystemExit(f"ERROR: invalid momentum bin [{low}, {high})")
    if len(set(momentum_bins)) != len(momentum_bins):
        raise SystemExit("ERROR: duplicate momentum bins")
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {args.output_dir}")

    args.output_dir.mkdir(parents=True)
    summary_rows = []
    all_labels = disk_labels()
    for vertex_z_mm in args.vertices:
        accumulators = accumulate_shards(
            args.extracted_root, vertex_z_mm, momentum_bins, args.eta_bin_width
        )
        counts_pdf = args.output_dir / f"hit_counts_vz_{VERTEX_LABELS[vertex_z_mm]}mm.pdf"
        fraction_pdf = args.output_dir / f"hit_fraction_vz_{VERTEX_LABELS[vertex_z_mm]}mm.pdf"
        with PdfPages(counts_pdf) as counts_pages, PdfPages(fraction_pdf) as fraction_pages:
            for accumulator in accumulators:
                low = accumulator["momentum_low_GeV"]
                high = accumulator["momentum_high_GeV"]
                tag = momentum_tag(low, high)
                stem = f"hit_eta_phi_vz_{VERTEX_LABELS[vertex_z_mm]}mm_{tag}"
                count_png = args.output_dir / f"{stem}_counts.png"
                fraction_png = args.output_dir / f"{stem}_fraction.png"
                count_figure = plot_map(
                    accumulator, vertex_z_mm, args.minimum_bin_denominator,
                    "counts", count_png
                )
                counts_pages.savefig(count_figure)
                plt.close(count_figure)
                fraction_figure = plot_map(
                    accumulator, vertex_z_mm, args.minimum_bin_denominator,
                    "fraction", fraction_png
                )
                fraction_pages.savefig(fraction_figure)
                plt.close(fraction_figure)

                for disk_index, label in enumerate(all_labels):
                    denominator_hist = accumulator["denominator"][disk_index]
                    numerator_hist = accumulator["numerator"][disk_index]
                    denominator_total = int(accumulator["denominator_total"][disk_index])
                    numerator_total = int(accumulator["numerator_total"][disk_index])
                    summary_rows.append({
                        "vertex_z_mm": vertex_z_mm,
                        "momentum_min_GeV": low,
                        "momentum_max_GeV_exclusive": high,
                        "disk": label,
                        "generated_particles": denominator_total,
                        "particles_with_disk_hit": numerator_total,
                        "integrated_hit_fraction": (
                            numerator_total / denominator_total if denominator_total else np.nan
                        ),
                        "generated_particles_in_eta_phi_bins": int(denominator_hist.sum()),
                        "hit_particles_in_eta_phi_bins": int(numerator_hist.sum()),
                        "eta_phi_bins_with_generated_particles": int(np.count_nonzero(denominator_hist)),
                        "eta_phi_bins_unmasked": int(np.count_nonzero(
                            denominator_hist >= args.minimum_bin_denominator
                        )),
                    })
                npz_path = args.output_dir / f"{stem}.npz"
                metadata = {
                    "vertex_z_mm": vertex_z_mm,
                    "momentum_range_GeV_half_open": [low, high],
                    "eta_phi_bin_definition": "generated primary momentum direction",
                    "eta_bin_width": args.eta_bin_width,
                    "phi_range_rad": [PHI_MIN_RAD, PHI_MAX_RAD],
                    "minimum_bin_denominator": args.minimum_bin_denominator,
                    "disk_order": all_labels,
                    "numerator_definition": "unique generated primary with >=1 associated disk hit",
                    "denominator_definition": "all generated primary pi+ in this momentum bin",
                    "projection_used": False,
                }
                np.savez_compressed(
                    npz_path,
                    metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
                    denominator=accumulator["denominator"],
                    numerator=accumulator["numerator"],
                    denominator_total=accumulator["denominator_total"],
                    numerator_total=accumulator["numerator_total"],
                    eta_edges=accumulator["eta_edges"],
                    phi_edges=accumulator["phi_edges"],
                )

        print(f"Wrote {counts_pdf} and {fraction_pdf}", flush=True)

    summary_path = args.output_dir / "hit_eta_phi_summary.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
