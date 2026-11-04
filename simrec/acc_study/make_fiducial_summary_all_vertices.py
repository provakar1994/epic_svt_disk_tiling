#!/usr/bin/env python3
"""Collect the cross-disk fiducial summary page of each vertex into one PDF.

Redraws page 1 of each disk_hit_efficiency_vz_*.pdf from its saved
fiducial_efficiency_vz_*.csv with the same plotting function
(plot_fiducial_overview), so the pages are identical vector plots.
Page order: vz = -100, -10, 0, +10, +100 mm (pages whose CSV is missing are skipped
with a warning).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

from plot_disk_hit_efficiency_eta_phi import plot_fiducial_overview

DISK_ORDER = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
# (vertex z in mm, results directory suffix, file tag)
VERTICES = [(-100, "_vz_m100mm", "vz_m100mm"), (-10, "_vz_m010mm", "vz_m010mm"), (0, "", "vz_000mm"),
            (10, "_vz_p010mm", "vz_p010mm"), (100, "_vz_p100mm", "vz_p100mm")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True,
                        help="Directory holding disk_hit_efficiency_<version>[_vz_...] folders.")
    parser.add_argument("--version", default="v8")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite {args.output}")

    with PdfPages(args.output) as pages:
        for vertex_z_mm, suffix, tag in VERTICES:
            csv_path = args.results_dir / f"disk_hit_efficiency_{args.version}{suffix}" / f"fiducial_efficiency_{tag}.csv"
            if not csv_path.exists():
                print(f"WARNING: skipping vz={vertex_z_mm} mm, missing {csv_path}")
                continue
            table = pd.read_csv(csv_path)
            binned = table[~table.all_momenta].drop_duplicates(
                ["momentum_min_GeV", "momentum_max_GeV_exclusive"]).sort_values("momentum_min_GeV")
            bins = list(zip(binned.momentum_min_GeV, binned.momentum_max_GeV_exclusive))
            shown_bins = [bins[0], bins[len(bins) // 2], bins[-1]]  # same choice as the main script
            fig = plot_fiducial_overview(table, DISK_ORDER, shown_bins, vertex_z_mm)
            pages.savefig(fig)
            plt.close(fig)
            print(f"page: vz={vertex_z_mm} mm from {csv_path}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
