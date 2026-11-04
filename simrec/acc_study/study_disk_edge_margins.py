#!/usr/bin/env python3
"""Measure the low-efficiency edge bands of each disk, to choose fiducial margins.

Per generated primary and disk:

  R = |z_disk - z_vertex| / sinh(|eta|)

is the straight-line radius of the generated direction at the nominal disk z
(the same display coordinate as the disk-view maps, computed per particle, so
there is no 0.1-eta bin quantisation). Hit efficiency is profiled in R,
integrated over phi, separately per momentum bin.

For each disk and momentum bin:
  edge50 (inner/outer) = radius where the profile crosses 50% efficiency,
                         linearly interpolated between bin centres
                         (the active silicon edge, phi-averaged)
  plateau              = pooled efficiency over the central 40-60% of the
                         span between the two edge50 radii
  band end (in/out)    = first bin, walking from the edge50 bin into the disk,
                         that starts a run of N consecutive bins with
                         efficiency >= plateau - tolerance
  band width           = |band end - edge50|

For reference the geometry envelope from definitions_craterlake.xml is also
reported: r_in = largest axis distance of the beam-pipe openings incl. 5 mm
bakeout buffer (= XML *_rmin), r_out = XML rmax. Margins measured from these
are given in mm and as % of (r_out - r_in).

A first version measured margins from the XML edges with a 1-point tolerance;
dips inside the disk (narrow rings at 92-93%) and a slow radial trend tripped
that criterion, so edges are now located by their 50% crossing first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from reduce_disk_acceptance import DISKS, VERTEX_LABELS, configuration_name
from plot_disk_hit_efficiency_eta_phi import read_disk_boundaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extracted-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New output directory; existing output is never overwritten.")
    parser.add_argument("--geometry-xml", type=Path, required=True)
    parser.add_argument("--vertex", type=int, default=0, choices=sorted(VERTEX_LABELS))
    parser.add_argument("--momentum-bin", type=float, nargs=2, action="append", required=True,
                        metavar=("MIN_GEV", "MAX_GEV"), help="Half-open momentum bin; repeat.")
    parser.add_argument("--r-bin-mm", type=float, default=2.5)
    parser.add_argument("--tolerance-percent", type=float, default=3.0,
                        help="Band ends where efficiency >= plateau - this (percentage points).")
    parser.add_argument("--consecutive-bins", type=int, default=3,
                        help="Bins in a row that must pass, to be robust to fluctuations.")
    parser.add_argument("--minimum-bin-generated", type=int, default=100,
                        help="Radial bins with fewer generated particles are ignored.")
    return parser.parse_args()


def accumulate(extracted_root: Path, vertex_z_mm: int, momentum_bins, r_edges) -> dict:
    """Return {(disk, momentum bin): (generated per R bin, hit per R bin)}."""
    histograms = {}
    for side in ("negative", "positive"):
        configuration = configuration_name(vertex_z_mm, side)
        shards = sorted((extracted_root / configuration).glob("particles_*.npz"))
        if not shards:
            raise FileNotFoundError(f"No extracted shards for {configuration}")
        print(f"{configuration}: reading {len(shards)} shards", flush=True)
        for row in DISKS[side]:
            for m in momentum_bins:
                histograms[(row[0], m)] = [np.zeros(len(r_edges) - 1, np.int64),
                                           np.zeros(len(r_edges) - 1, np.int64)]
        for shard_path in shards:
            with np.load(shard_path, allow_pickle=False) as stored:
                momentum = stored["p_GeV"]
                abs_eta = np.abs(stored["eta"].astype(float))
                vertex_z = stored["vertex_z_mm"].astype(float)
                hit_mask = stored["hit_mask"]
            for local_index, row in enumerate(DISKS[side]):
                label, disk_z = row[0], row[3]
                radius = np.abs(disk_z - vertex_z) / np.sinh(abs_eta)
                has_hit = (hit_mask & np.uint8(1 << local_index)) != 0
                for m in momentum_bins:
                    selected = (momentum >= m[0]) & (momentum < m[1])
                    histograms[(label, m)][0] += np.histogram(radius[selected], r_edges)[0]
                    histograms[(label, m)][1] += np.histogram(radius[selected & has_hit], r_edges)[0]
    return histograms


def find_run_start(efficiency, valid, start, step, threshold, consecutive):
    """First index, walking from `start` by `step`, that begins a run of
    `consecutive` valid bins all >= threshold; None if never reached."""
    index = start
    while 0 <= index < len(efficiency):
        run = [index + step * k for k in range(consecutive)]
        if all(0 <= i < len(efficiency) and valid[i] and efficiency[i] >= threshold for i in run):
            return index
        index += step
    return None


def crossing_50(r_centres, efficiency, inner_index, outer_index):
    """Interpolated 50% crossings next to the first/last bin above 50%."""
    def interpolate(i_below, i_above):
        e_below, e_above = efficiency[i_below], efficiency[i_above]
        if not (np.isfinite(e_below) and np.isfinite(e_above)) or e_above == e_below:
            return r_centres[i_above]
        fraction = (50.0 - e_below) / (e_above - e_below)
        return r_centres[i_below] + fraction * (r_centres[i_above] - r_centres[i_below])
    inner = interpolate(inner_index - 1, inner_index) if inner_index > 0 else r_centres[0]
    outer = interpolate(outer_index + 1, outer_index) if outer_index + 1 < len(r_centres) else r_centres[-1]
    return inner, outer


def analyse_profile(generated, hit, r_edges, r_centres, tolerance, consecutive, minimum_generated):
    valid = generated >= minimum_generated
    efficiency = np.divide(100.0 * hit, generated, out=np.full(len(hit), np.nan), where=generated > 0)
    above = np.where(valid & (efficiency > 50.0))[0]
    first, last = int(above.min()), int(above.max())
    edge_in, edge_out = crossing_50(r_centres, efficiency, first, last)
    span = edge_out - edge_in
    central = (r_centres >= edge_in + 0.4 * span) & (r_centres < edge_in + 0.6 * span)
    plateau = 100.0 * hit[central].sum() / generated[central].sum()
    threshold = plateau - tolerance
    inner_index = find_run_start(efficiency, valid, first, +1, threshold, consecutive)
    outer_index = find_run_start(efficiency, valid, last, -1, threshold, consecutive)
    band_in = r_edges[inner_index] if inner_index is not None else np.nan
    band_out = r_edges[outer_index + 1] if outer_index is not None else np.nan
    return dict(efficiency=efficiency, edge50_in=edge_in, edge50_out=edge_out, plateau=plateau,
                threshold=threshold, band_end_in=band_in, band_end_out=band_out)


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {args.output_dir}")
    momentum_bins = [tuple(m) for m in args.momentum_bin]
    boundaries = read_disk_boundaries(args.geometry_xml)
    r_edges = np.arange(0.0, 500.0 + args.r_bin_mm, args.r_bin_mm)
    r_centres = 0.5 * (r_edges[:-1] + r_edges[1:])
    histograms = accumulate(args.extracted_root, args.vertex, momentum_bins, r_edges)
    args.output_dir.mkdir(parents=True)

    order = list(DISKS["negative"][::-1]) + list(DISKS["positive"])  # ED4 .. ED0, HD0 .. HD4
    labels = [row[0] for row in order]
    rows, profiles = [], {}
    for label in labels:
        circles = boundaries[label]
        r_in = max(np.hypot(xc, yc) + r for xc, yc, r in circles[:2])
        r_out = circles[2][2]
        xml_width = r_out - r_in
        for m in momentum_bins:
            generated, hit = histograms[(label, m)]
            result = analyse_profile(generated, hit, r_edges, r_centres, args.tolerance_percent,
                                     args.consecutive_bins, args.minimum_bin_generated)
            profiles[(label, m)] = result
            margin_in_xml = result["band_end_in"] - r_in
            margin_out_xml = r_out - result["band_end_out"]
            rows.append({
                "disk": label, "momentum_min_GeV": m[0], "momentum_max_GeV_exclusive": m[1],
                "xml_r_in_mm": r_in, "xml_r_out_mm": r_out, "xml_width_mm": xml_width,
                "edge50_in_mm": result["edge50_in"], "edge50_out_mm": result["edge50_out"],
                "active_width_mm": result["edge50_out"] - result["edge50_in"],
                "plateau_percent": result["plateau"], "threshold_percent": result["threshold"],
                "band_end_in_mm": result["band_end_in"], "band_end_out_mm": result["band_end_out"],
                "band_width_in_mm": result["band_end_in"] - result["edge50_in"],
                "band_width_out_mm": result["edge50_out"] - result["band_end_out"],
                "margin_from_xml_in_mm": margin_in_xml, "margin_from_xml_out_mm": margin_out_xml,
                "margin_from_xml_in_percent_width": 100.0 * margin_in_xml / xml_width,
                "margin_from_xml_out_percent_width": 100.0 * margin_out_xml / xml_width,
            })
    table = pd.DataFrame(rows)
    table.to_csv(args.output_dir / "disk_edge_margins.csv", index=False)
    np.savez_compressed(
        args.output_dir / "disk_edge_profiles.npz", r_edges=r_edges,
        **{f"{label}_p{m[0]:g}_{kind}".replace(".", "p"): histograms[(label, m)][k]
           for label in labels for m in momentum_bins for k, kind in enumerate(("generated", "hit"))})

    low, mid, high = momentum_bins[0], momentum_bins[len(momentum_bins) // 2], momentum_bins[-1]
    shown = [(low, "tab:red"), (mid, "tab:green"), (high, "tab:blue")]
    pdf_path = args.output_dir / f"disk_edge_margins_vz_{VERTEX_LABELS[args.vertex]}mm.pdf"
    with PdfPages(pdf_path) as pages:
        # Summary: band widths (from the 50% edge) and margins measured from the XML edges.
        quantities = [("band_width_in_mm", "inner band width [mm]"),
                      ("band_width_out_mm", "outer band width [mm]"),
                      ("margin_from_xml_in_mm", "inner margin from XML r_in [mm]"),
                      ("margin_from_xml_out_mm", "outer margin from XML r_out [mm]"),
                      ("margin_from_xml_in_percent_width", "inner margin [% of XML width]"),
                      ("margin_from_xml_out_percent_width", "outer margin [% of XML width]")]
        fig, axes = plt.subplots(3, 2, figsize=(14, 12), constrained_layout=True)
        x = np.arange(len(labels))
        for axis, (column, ylabel) in zip(axes.flat, quantities):
            for k, (m, color) in enumerate(shown):
                values = [table[(table.disk == d) & (table.momentum_min_GeV == m[0])][column].iloc[0]
                          for d in labels]
                axis.plot(x + 0.12 * (k - 1), values, "o", color=color,
                          label=f"{m[0]:g} <= p < {m[1]:g} GeV")
            axis.set_xticks(x, labels)
            axis.set_ylabel(ylabel)
            axis.set_ylim(bottom=0)
            axis.grid(ls=":")
        axes[0, 0].legend()
        fig.suptitle("Disk edge bands: from the 50% crossing to plateau - "
                     f"{args.tolerance_percent:g} pt ({args.consecutive_bins} consecutive "
                     f"{args.r_bin_mm:g} mm bins), z_vtx={args.vertex} mm")
        pages.savefig(fig)
        fig.savefig(args.output_dir / "edge_margins_summary.png", dpi=110)
        plt.close(fig)

        # One page per disk: full profile, inner-edge zoom, outer-edge zoom.
        for label in labels:
            info = table[table.disk == label]
            r_in, r_out = info.xml_r_in_mm.iloc[0], info.xml_r_out_mm.iloc[0]
            fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), constrained_layout=True)
            for axis, (x_low, x_high) in zip(axes, ((0, 480), (r_in - 20, r_in + 80),
                                                    (r_out - 120, r_out + 30))):
                for m, color in shown:
                    result = profiles[(label, m)]
                    axis.step(r_centres, result["efficiency"], where="mid", color=color, lw=1.0,
                              label=f"{m[0]:g}-{m[1]:g} GeV")
                    axis.axhline(result["threshold"], color=color, ls=":", lw=0.7)
                    for radius in (result["band_end_in"], result["band_end_out"]):
                        if np.isfinite(radius):
                            axis.axvline(radius, color=color, ls="--", lw=0.8)
                for edge in (r_in, r_out):
                    axis.axvline(edge, color="k", lw=1.2)
                axis.axhline(50.0, color="gray", lw=0.6)
                axis.set_xlim(x_low, x_high)
                axis.set_ylim(0, 102)
                axis.set_xlabel("straight-line radius at disk [mm]")
                axis.set_ylabel("hit efficiency [%] (phi-integrated)")
                axis.grid(ls=":")
            axes[0].legend(loc="lower center")
            axes[0].set_title(f"{label}: black = XML r_in {r_in:.1f}, r_out {r_out:.0f} mm")
            axes[1].set_title("inner edge (dashed: band end, dotted: plateau - tol)")
            axes[2].set_title("outer edge")
            pages.savefig(fig)
            fig.savefig(args.output_dir / f"{label}_edge_profile.png", dpi=110)
            plt.close(fig)
    print(f"Wrote {pdf_path}")
    print(table[table.momentum_min_GeV.isin([low[0], mid[0], high[0]])][
        ["disk", "momentum_min_GeV", "edge50_in_mm", "edge50_out_mm", "plateau_percent",
         "band_width_in_mm", "band_width_out_mm", "margin_from_xml_in_mm", "margin_from_xml_out_mm",
         "margin_from_xml_in_percent_width", "margin_from_xml_out_percent_width"]
    ].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
