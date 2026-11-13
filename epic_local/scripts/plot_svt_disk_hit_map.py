#!/usr/bin/env python3
"""Plot an x-y hit map for one SVT endcap disk from an EDM4hep ROOT file."""

import argparse
from pathlib import Path
from typing import List, Tuple


DEFAULT_INPUT = Path("/global/cfs/cdirs/m3763/pdatta/npsim/sim_tracking.root")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Discover SVT disks from separated hit-z bands and plot the x-y hit "
            "distribution for one disk. Disk indices are sorted from negative to positive z."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="input EDM4hep ROOT file")
    parser.add_argument("--tree", default="events", help="ROOT tree name")
    parser.add_argument("--collection", default="TrackerEndcapHits", help="hit collection prefix")
    parser.add_argument(
        "--list-disks",
        action="store_true",
        help="list discovered hit-z bands and exit unless a disk selection is also given",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--disk-index",
        type=int,
        help="zero-based disk index from --list-disks, sorted by global z",
    )
    selection.add_argument(
        "--disk-z-mm",
        type=float,
        help="select the discovered disk whose median global z is closest to this value",
    )
    parser.add_argument(
        "--z-gap-mm",
        type=float,
        default=20.0,
        help="minimum empty z gap separating two disks (default: 20 mm)",
    )
    parser.add_argument("--bins", type=int, default=300, help="number of x and y histogram bins")
    parser.add_argument(
        "--xy-limit-mm",
        type=float,
        help="use symmetric x/y plot limits of +/- this value instead of automatic limits",
    )
    parser.add_argument("--output", type=Path, help="output PNG path")
    return parser.parse_args()


def load_hit_positions(input_path: Path, tree_name: str, collection: str):
    try:
        import awkward as ak
        import numpy as np
        import uproot
    except ImportError as exc:
        raise SystemExit(
            "This script requires uproot, awkward, numpy, and matplotlib. "
            "Run it in an EIC/ROOT analysis environment or install those Python packages."
        ) from exc

    branch_names = [f"{collection}.position.{axis}" for axis in "xyz"]
    with uproot.open(input_path) as root_file:
        if tree_name not in root_file:
            available = ", ".join(root_file.keys(cycle=False))
            raise SystemExit(f"tree '{tree_name}' not found; available objects: {available}")
        tree = root_file[tree_name]
        missing = [name for name in branch_names if name not in tree]
        if missing:
            matches = [name for name in tree.keys() if collection in name and "position" in name]
            raise SystemExit(
                f"missing branches {missing}; matching branches in '{tree_name}': {matches}"
            )
        arrays = tree.arrays(branch_names, library="ak")

    flattened = []
    for branch_name in branch_names:
        flattened.append(ak.to_numpy(ak.flatten(arrays[branch_name], axis=None)))
    if not flattened[0].size:
        raise SystemExit(f"collection '{collection}' contains no hits")

    finite = np.isfinite(flattened[0]) & np.isfinite(flattened[1]) & np.isfinite(flattened[2])
    return tuple(values[finite] for values in flattened)


def discover_disks(z_values, z_gap_mm: float) -> List[Tuple[float, float, float, int]]:
    import numpy as np

    if z_gap_mm <= 0.0:
        raise SystemExit("--z-gap-mm must be positive")
    order = np.argsort(z_values)
    sorted_z = z_values[order]
    split_indices = np.flatnonzero(np.diff(sorted_z) > z_gap_mm) + 1
    groups = np.split(sorted_z, split_indices)
    return [
        (float(np.median(group)), float(group[0]), float(group[-1]), int(group.size))
        for group in groups
        if group.size
    ]


def print_disks(disks: List[Tuple[float, float, float, int]]) -> None:
    print("index  median_z_mm   z_min_mm   z_max_mm       hits")
    for index, (median_z, z_min, z_max, count) in enumerate(disks):
        print(f"{index:5d}  {median_z:11.3f}  {z_min:9.3f}  {z_max:9.3f}  {count:9d}")


def select_disk(args: argparse.Namespace, disks: List[Tuple[float, float, float, int]]) -> int:
    if args.disk_index is not None:
        if args.disk_index < 0 or args.disk_index >= len(disks):
            raise SystemExit(f"--disk-index must be between 0 and {len(disks) - 1}")
        return args.disk_index
    if args.disk_z_mm is not None:
        return min(range(len(disks)), key=lambda index: abs(disks[index][0] - args.disk_z_mm))
    raise SystemExit("select a disk with --disk-index or --disk-z-mm; use --list-disks first")


def plot_hit_map(args: argparse.Namespace, x_values, y_values, z_values, disk_index: int, disk) -> Path:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.colors import LogNorm
    except ImportError as exc:
        raise SystemExit("This script requires matplotlib and numpy") from exc

    median_z, z_min, z_max, expected_count = disk
    disk_mask = (z_values >= z_min) & (z_values <= z_max)
    disk_x = x_values[disk_mask]
    disk_y = y_values[disk_mask]
    if disk_x.size != expected_count:
        raise RuntimeError("internal disk-selection count mismatch")

    figure, axis = plt.subplots(figsize=(8, 7), constrained_layout=True)
    histogram = axis.hist2d(
        disk_x,
        disk_y,
        bins=args.bins,
        cmin=1,
        cmap="viridis",
        norm=LogNorm(vmin=1),
    )
    colorbar = figure.colorbar(histogram[3], ax=axis)
    colorbar.set_label("hits / bin")
    axis.set_xlabel("global x [mm]")
    axis.set_ylabel("global y [mm]")
    axis.set_title(
        f"{args.collection}: disk {disk_index}, z = {median_z:.2f} mm\n"
        f"{disk_x.size:,} hits; z range [{z_min:.2f}, {z_max:.2f}] mm"
    )
    axis.set_aspect("equal", adjustable="box")
    axis.grid(alpha=0.15)

    if args.xy_limit_mm is not None:
        if args.xy_limit_mm <= 0.0:
            raise SystemExit("--xy-limit-mm must be positive")
        axis.set_xlim(-args.xy_limit_mm, args.xy_limit_mm)
        axis.set_ylim(-args.xy_limit_mm, args.xy_limit_mm)
    else:
        extent = 1.05 * float(np.max(np.abs(np.concatenate((disk_x, disk_y)))))
        axis.set_xlim(-extent, extent)
        axis.set_ylim(-extent, extent)

    output_path = args.output or Path(f"out/svt_hit_map_disk_{disk_index}.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)
    return output_path


def main() -> None:
    args = parse_args()
    if not args.input.is_file():
        raise SystemExit(f"input file not found: {args.input}")

    x_values, y_values, z_values = load_hit_positions(args.input, args.tree, args.collection)
    disks = discover_disks(z_values, args.z_gap_mm)
    if not disks:
        raise SystemExit("no disk hit-z bands were discovered")

    if args.list_disks:
        print_disks(disks)
        if args.disk_index is None and args.disk_z_mm is None:
            return

    disk_index = select_disk(args, disks)
    output_path = plot_hit_map(args, x_values, y_values, z_values, disk_index, disks[disk_index])
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
