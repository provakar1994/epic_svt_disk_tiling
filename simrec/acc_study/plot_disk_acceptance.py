#!/usr/bin/env python3
"""Plot integrated and 2D acceptance from reduce_disk_acceptance.py outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+", help="One or more per-vertex NPZ summaries.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-denominator", type=int, default=50,
                        help="Mask acceptance bins with fewer generated particles (default: 50).")
    return parser.parse_args()


def load_summary(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as data:
        result = {name: data[name] for name in data.files}
    result["metadata"] = json.loads(str(result.pop("metadata_json")))
    return result


def plot_integrated(data: dict, output_path: Path) -> None:
    generated = data["denominator_total"]
    passed = data["numerator_total"]
    acceptance = np.divide(passed, generated, out=np.full(10, np.nan), where=generated > 0)
    # Wilson interval with z=1, matching the CSV output.
    denominator = 1.0 + 1.0 / generated
    centre = (acceptance + 1.0 / (2.0 * generated)) / denominator
    half = np.sqrt(acceptance * (1.0 - acceptance) / generated + 1.0 / (4.0 * generated**2)) / denominator

    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    positions = np.arange(10)
    ax.bar(positions, acceptance, color=["C0"] * 5 + ["C1"] * 5)
    ax.errorbar(positions, centre, yerr=half, fmt="none", color="black", capsize=2, linewidth=1)
    ax.set_xticks(positions, data["disk_label"])
    ax.set(ylabel="Fraction of generated primaries with >=1 hit", ylim=(0, 1.03),
           title=f"Disk-integrated simulated-hit acceptance, vertex z = {data['metadata']['vertex_z_mm']} mm")
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_hit_missing(data: dict, side: str, output_path: Path) -> None:
    indices = np.flatnonzero(data["side"] == side)
    hit_counts = data["numerator_xy"][indices]
    missing_counts = data["missing_xy"][indices]
    maximum = max(1, int(max(hit_counts.max(), missing_counts.max())))
    x_edges = data["x_edges_mm"] / 10.0
    y_edges = data["y_edges_mm"] / 10.0

    fig, axes = plt.subplots(len(indices), 2, figsize=(9, 18), sharex=True, sharey=True,
                             layout="constrained")
    image = None
    for row, disk_index in enumerate(indices):
        for column, (counts, title) in enumerate(((hit_counts[row], "with hit"),
                                                   (missing_counts[row], "missing hit"))):
            masked = np.ma.masked_less_equal(counts.T, 0)
            image = axes[row, column].pcolormesh(
                x_edges, y_edges, masked, shading="auto", cmap="viridis",
                norm=LogNorm(vmin=1, vmax=maximum),
            )
            axes[row, column].set_aspect("equal")
            axes[row, column].set_title(f"{data['disk_label'][disk_index]}: projected events {title}")
            axes[row, column].set_ylabel("projected y [cm]")
        axes[row, 0].set_xlabel("projected x [cm]")
        axes[row, 1].set_xlabel("projected x [cm]")
    if image is not None:
        fig.colorbar(image, ax=axes, label="Generated particles per bin")
    fig.suptitle(f"{side.capitalize()} disks, vertex z = {data['metadata']['vertex_z_mm']} mm")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_acceptance_maps(data: dict, side: str, minimum_denominator: int,
                         output_path: Path) -> None:
    indices = np.flatnonzero(data["side"] == side)
    x_edges = data["x_edges_mm"] / 10.0
    y_edges = data["y_edges_mm"] / 10.0
    fig, axes = plt.subplots(1, len(indices), figsize=(20, 4.6), sharex=True, sharey=True,
                             layout="constrained")
    image = None
    for axis, disk_index in zip(axes, indices):
        denominator = data["denominator_xy"][disk_index]
        numerator = data["numerator_xy"][disk_index]
        acceptance = np.divide(numerator, denominator, out=np.zeros_like(numerator, dtype=float),
                               where=denominator > 0)
        masked = np.ma.masked_where(denominator < minimum_denominator, acceptance)
        image = axis.pcolormesh(x_edges, y_edges, masked.T, shading="auto",
                                cmap="viridis", vmin=0, vmax=1)
        axis.set_aspect("equal")
        axis.set_title(str(data["disk_label"][disk_index]))
        axis.set_xlabel("projected x [cm]")
    axes[0].set_ylabel("projected y [cm]")
    if image is not None:
        fig.colorbar(image, ax=axes, label="Fraction with >=1 hit")
    fig.suptitle(f"{side.capitalize()} disk acceptance, vertex z = "
                 f"{data['metadata']['vertex_z_mm']} mm; denominator >= {minimum_denominator}")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    if args.minimum_denominator < 1:
        raise SystemExit("ERROR: --minimum-denominator must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in args.inputs:
        data = load_summary(input_path)
        vertex_z_mm = int(data["metadata"]["vertex_z_mm"])
        vertex_component = "000" if vertex_z_mm == 0 else f"{'p' if vertex_z_mm > 0 else 'm'}{abs(vertex_z_mm):03d}"
        vertex_label = f"vz_{vertex_component}mm"
        plot_integrated(data, args.output_dir / f"{vertex_label}_integrated_acceptance.png")
        for side in ("negative", "positive"):
            plot_hit_missing(data, side, args.output_dir / f"{vertex_label}_{side}_hit_missing.png")
            plot_acceptance_maps(
                data, side, args.minimum_denominator,
                args.output_dir / f"{vertex_label}_{side}_acceptance_map.png",
            )
        print(f"Plotted {input_path}")


if __name__ == "__main__":
    main()
