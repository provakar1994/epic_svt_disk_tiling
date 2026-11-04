#!/usr/bin/env python3
"""Per-disk hit efficiency in generated (eta, phi), shown inside each disk's hit region.

Definitions (one generated primary pi+ counts at most once per disk):

  region of a disk  = eta bins whose phi-integrated fraction of generated
                      primaries with a directly associated hit on that disk is
                      >= --region-min-row-efficiency (default 1%), using ALL
                      momenta of the vertex sample. The same region is used for every
                      momentum page so the pages are directly comparable.
  numerator (bin)   = generated primaries in the bin with >=1 hit on the disk
  denominator (bin) = all generated primaries in the bin (same momentum selection)
  hit efficiency    = numerator / denominator  [%]

eta and phi are the generated momentum direction; no projection is used.
phi is shown in degrees in [0, 360). Reads the extracted particle shards only.

Fiducial average (summary pages; needs --geometry-xml):
  R per particle    = |z_disk - z_vertex| / sinh(|eta|), the straight-line
                      radius of the generated direction at the nominal disk z
  fiducial annulus  = XML r_in + inner margin <= R < XML r_out - outer margin,
                      r_in = largest axis distance of the beam-pipe openings
                      (incl. 5 mm bakeout buffer), r_out = XML rmax.
                      Default margins 30 / 40 mm, chosen from the edge study
                      (study_disk_edge_margins.py: measured margins 20-28 mm
                      inner, 27.5-37.5 mm outer). Same annulus for every
                      momentum bin, so the cut does not depend on efficiency.
  fiducial efficiency = hit / generated for particles in the annulus (pooled),
                      binomial error.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from reduce_disk_acceptance import DISKS, VERTEX_LABELS, configuration_name


ALL_MOMENTA = (0.5, 20.01)  # include the gun's 20 GeV endpoint
SIDE_ETA_RANGE = {"negative": (-3.8, -0.6), "positive": (0.6, 3.8)}

# Constant-name prefix of each disk in compact/tracking/definitions_craterlake.xml.
DISK_XML_PREFIX = {
    "ED0": "InnerTrackerEndcapN", "ED1": "TrackerEndcapNDisk1", "ED2": "TrackerEndcapNDisk2",
    "ED3": "TrackerEndcapNDisk3", "ED4": "TrackerEndcapNDisk4",
    "HD0": "InnerTrackerEndcapP", "HD1": "TrackerEndcapPDisk1", "HD2": "TrackerEndcapPDisk2",
    "HD3": "TrackerEndcapPDisk3", "HD4": "TrackerEndcapPDisk4",
}


def read_disk_boundaries(xml_path: Path) -> dict:
    """Return {disk: [(x_centre_mm, y_centre_mm, radius_mm), ...]} from the geometry XML.

    Circles per disk: lepton and hadron beam-pipe openings (radius already
    includes the 5 mm bakeout buffer) and the outer radius rmax. These are the
    design envelope; the RSU tiling places silicon inside it, so the active
    edge sits somewhat outside the openings and inside rmax. Centres are in
    global x, y (checked against measured hit edges on ED3, ED4 and HD4).
    """
    import re
    text = xml_path.read_text()
    raw = dict(re.findall(r'<constant\s+name="([^"]+)"\s+value="([^"]+)"', text))
    cache: dict = {}

    def value_mm(name: str) -> float:
        # Resolve a constant recursively; units mm=1, cm=10. Only names, numbers,
        # + - * / ( ) and max/abs appear in the expressions used here.
        if name not in cache:
            expression = raw[name]
            names = set(re.findall(r"[A-Za-z_]\w*", expression)) - {"mm", "cm", "max", "abs"}
            namespace = {n: value_mm(n) for n in names}
            namespace.update(mm=1.0, cm=10.0, max=max, abs=abs)
            cache[name] = float(eval(expression, {"__builtins__": {}}, namespace))
        return cache[name]

    boundaries = {}
    for disk, prefix in DISK_XML_PREFIX.items():
        boundaries[disk] = [
            (value_mm(f"{prefix}_lepton_center_x"), value_mm(f"{prefix}_lepton_center_y"),
             value_mm(f"{prefix}_lepton_radius")),
            (value_mm(f"{prefix}_hadron_center_x"), value_mm(f"{prefix}_hadron_center_y"),
             value_mm(f"{prefix}_hadron_radius")),
            (0.0, 0.0, value_mm(f"{prefix}_rmax")),
        ]
    return boundaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extracted-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New output directory; existing output is never overwritten.")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0],
                        choices=sorted(VERTEX_LABELS))
    parser.add_argument("--momentum-bin", type=float, nargs=2, action="append",
                        metavar=("MIN_GEV", "MAX_GEV"),
                        help="Extra half-open momentum bins; all momenta is always made.")
    parser.add_argument("--eta-bin-width", type=float, default=0.1)
    parser.add_argument("--phi-bin-width-deg", type=float, default=10.0)
    parser.add_argument("--minimum-bin-denominator", type=int, default=20,
                        help="Mask bins with fewer generated particles; default 20.")
    parser.add_argument("--geometry-xml", type=Path, default=None,
                        help="definitions_craterlake.xml; if given, draw the disk openings "
                             "and outer radius as red circles on the disk views.")
    parser.add_argument("--fiducial-inner-margin-mm", type=float, default=30.0,
                        help="Fiducial annulus starts this far outside XML r_in; default 30.")
    parser.add_argument("--fiducial-outer-margin-mm", type=float, default=40.0,
                        help="Fiducial annulus ends this far inside XML rmax; default 40.")
    parser.add_argument("--region-min-row-efficiency", type=float, default=0.01,
                        help="An eta row joins the disk region if its phi-integrated, "
                             "all-momentum hit fraction is at least this; default 0.01.")
    return parser.parse_args()


def make_edges(low: float, high: float, width: float) -> np.ndarray:
    number_of_bins = int(round((high - low) / width))
    if not np.isclose(number_of_bins * width, high - low):
        raise ValueError(f"bin width {width} must divide the range [{low}, {high}]")
    return np.linspace(low, high, number_of_bins + 1)


def accumulate(extracted_root: Path, vertex_z_mm: int, momentum_bins: list[tuple[float, float]],
               eta_edges: dict, phi_edges: np.ndarray, fiducial_annuli: dict | None = None) -> dict:
    """Return numerator/denominator histograms [momentum bin][disk] -> (eta, phi) arrays,
    and, if fiducial_annuli {disk: (r_low, r_high)} is given, fiducial
    [momentum bin][disk] -> [generated, hit] counts in that straight-line R annulus."""
    labels = [row[0] for side in ("negative", "positive") for row in DISKS[side]]
    shape = lambda side: (len(eta_edges[side]) - 1, len(phi_edges) - 1)
    numerator = {m: {} for m in momentum_bins}
    denominator = {m: {} for m in momentum_bins}
    fiducial = {m: {label: [0, 0] for label in labels} for m in momentum_bins}
    for side in ("negative", "positive"):
        for m in momentum_bins:
            for row in DISKS[side]:
                numerator[m][row[0]] = np.zeros(shape(side), dtype=np.int64)
                denominator[m][row[0]] = np.zeros(shape(side), dtype=np.int64)

        configuration = configuration_name(vertex_z_mm, side)
        shards = sorted((extracted_root / configuration).glob("particles_*.npz"))
        if not shards:
            raise FileNotFoundError(f"No extracted shards for {configuration} under {extracted_root}")
        print(f"{configuration}: reading {len(shards)} shards", flush=True)
        for shard_path in shards:
            with np.load(shard_path, allow_pickle=False) as stored:
                momentum = stored["p_GeV"]
                eta = stored["eta"]
                phi_deg = np.degrees(stored["phi_rad"]) % 360.0  # (-180,180] -> [0,360)
                hit_mask = stored["hit_mask"]
                vertex_z = stored["vertex_z_mm"].astype(float)
            in_annulus = {}
            if fiducial_annuli:
                for row in DISKS[side]:
                    radius = np.abs(row[3] - vertex_z) / np.sinh(np.abs(eta.astype(float)))
                    r_low, r_high = fiducial_annuli[row[0]]
                    in_annulus[row[0]] = (radius >= r_low) & (radius < r_high)
            for m in momentum_bins:
                selected = (momentum >= m[0]) & (momentum < m[1])
                generated = np.histogram2d(eta[selected], phi_deg[selected],
                                           bins=(eta_edges[side], phi_edges))[0].astype(np.int64)
                for local_index, row in enumerate(DISKS[side]):
                    has_hit = selected & ((hit_mask & np.uint8(1 << local_index)) != 0)
                    numerator[m][row[0]] += np.histogram2d(
                        eta[has_hit], phi_deg[has_hit], bins=(eta_edges[side], phi_edges)
                    )[0].astype(np.int64)
                    denominator[m][row[0]] += generated
                    if fiducial_annuli:
                        fiducial[m][row[0]][0] += int((selected & in_annulus[row[0]]).sum())
                        fiducial[m][row[0]][1] += int((has_hit & in_annulus[row[0]]).sum())

    for m in momentum_bins:
        for label in labels:
            if np.any(numerator[m][label] > denominator[m][label]):
                raise AssertionError(f"numerator exceeds denominator for {label}, {m}")
    return {"numerator": numerator, "denominator": denominator, "labels": labels,
            "fiducial": fiducial}


def hit_region(numerator_all_momenta: np.ndarray, denominator_all_momenta: np.ndarray,
               minimum_row_efficiency: float) -> tuple[int, int]:
    """First and last eta-bin index (inclusive) whose phi-integrated hit fraction
    reaches minimum_row_efficiency. The floor removes rows populated only by a
    few stray hits (e.g. low-momentum curlers) far outside the disk."""
    hits = numerator_all_momenta.sum(axis=1)
    generated = denominator_all_momenta.sum(axis=1)
    row_efficiency = np.divide(hits, generated, out=np.zeros(len(hits)), where=generated > 0)
    hit_eta_bins = np.where(row_efficiency >= minimum_row_efficiency)[0]
    if len(hit_eta_bins) == 0:
        raise ValueError("disk has no hit particles")
    return int(hit_eta_bins[0]), int(hit_eta_bins[-1])


def plot_disk(label: str, numerator: np.ndarray, denominator: np.ndarray,
              eta_edges: np.ndarray, phi_edges: np.ndarray, region: tuple[int, int],
              title_extra: str, minimum_bin_denominator: int):
    first, last = region
    num = numerator[first:last + 1]
    den = denominator[first:last + 1]
    edges = eta_edges[first:last + 2]
    efficiency = np.divide(100.0 * num, den, out=np.zeros(num.shape), where=den > 0)
    values = np.ma.masked_where(den < minimum_bin_denominator, efficiency)

    region_efficiency = 100.0 * num.sum() / den.sum()
    # Figure width grows with the number of eta bins so the per-bin numbers stay legible.
    fig, axis = plt.subplots(figsize=(3.0 + 0.6 * len(num), 12), constrained_layout=True)
    image = axis.pcolormesh(edges, phi_edges, values.T, vmin=0, vmax=100, cmap="viridis")

    # Write the rounded efficiency [%] at each unmasked bin centre; dark text on
    # the bright (high-efficiency) end of viridis, white text on the dark end.
    eta_centres = 0.5 * (edges[:-1] + edges[1:])
    phi_centres = 0.5 * (phi_edges[:-1] + phi_edges[1:])
    for i, eta_centre in enumerate(eta_centres):
        for j, phi_centre in enumerate(phi_centres):
            if values.mask is not np.ma.nomask and values.mask[i, j]:
                continue
            value = values[i, j]
            axis.text(eta_centre, phi_centre, f"{value:.0f}", ha="center", va="center",
                      fontsize=6, color="black" if value > 55 else "white")
    fig.colorbar(image, ax=axis, label="Hit efficiency [%]")
    axis.set_xlabel(r"Generated $\eta$")
    axis.set_ylabel(r"Generated $\phi$ [deg]")
    axis.set_ylim(0, 360)
    axis.set_yticks(np.arange(0, 361, 60))
    axis.set_title(f"{label} hit efficiency ({title_extra})\n"
                   f"region {edges[0]:.1f} <= eta < {edges[-1]:.1f}: "
                   f"{region_efficiency:.1f}% of {int(den.sum())} generated")
    return fig


def plot_disk_view(label: str, numerator: np.ndarray, denominator: np.ndarray,
                   eta_edges: np.ndarray, phi_edges: np.ndarray, region: tuple[int, int],
                   disk_z_mm: float, vertex_z_mm: float, title_extra: str,
                   minimum_bin_denominator: int, boundary_circles=None, fiducial_radii=None):
    """Same (eta, phi) bins as plot_disk, drawn on the disk plane.

    Only the bin EDGES are transformed: an eta edge becomes the radius where a
    straight line from the vertex at that eta reaches the nominal disk z,
        R = |z_disk - z_vertex| / sinh(|eta|),
    and phi stays the azimuth. Bin contents are unchanged. This is a display
    coordinate; low-momentum tracks bend, so their real hit radius differs.
    """
    first, last = region
    num = numerator[first:last + 1]
    den = denominator[first:last + 1]
    edges = eta_edges[first:last + 2]
    efficiency = np.divide(100.0 * num, den, out=np.zeros(num.shape), where=den > 0)
    values = np.ma.masked_where(den < minimum_bin_denominator, efficiency)

    radius_edges = abs(disk_z_mm - vertex_z_mm) / np.sinh(np.abs(edges))
    # Split every phi bin into 6 straight segments so the annuli look round.
    substeps = 6
    fine_phi = np.linspace(phi_edges[0], phi_edges[-1], (len(phi_edges) - 1) * substeps + 1)
    fine_values = np.repeat(values, substeps, axis=1)
    radius_grid, phi_grid = np.meshgrid(radius_edges, np.radians(fine_phi), indexing="ij")
    x_grid = radius_grid * np.cos(phi_grid)
    y_grid = radius_grid * np.sin(phi_grid)

    # Left: full disk. Right: zoom on the inner edge, where eta bins are narrow.
    fig, (full_axis, zoom_axis) = plt.subplots(1, 2, figsize=(19, 9.5), constrained_layout=True)
    circle_extent = max((np.hypot(xc, yc) + r for xc, yc, r in (boundary_circles or [])), default=0.0)
    r_full = max(radius_edges.max(), circle_extent) * 1.05
    r_zoom = 3.0 * radius_edges.min()
    for axis, r_lim in ((full_axis, r_full), (zoom_axis, r_zoom)):
        image = axis.pcolormesh(x_grid, y_grid, fine_values, vmin=0, vmax=100, cmap="viridis")
        axis.set_xlim(-r_lim, r_lim)
        axis.set_ylim(-r_lim, r_lim)
        axis.set_aspect("equal")
        axis.set_xlabel("x [mm]  (straight-line radius of generated direction)")
        axis.set_ylabel("y [mm]")
        # Geometry envelope from the XML: beam-pipe openings (+5 mm buffer) and rmax.
        circle_angle = np.linspace(0.0, 2.0 * np.pi, 400)
        for x_centre, y_centre, radius in (boundary_circles or []):
            axis.plot(x_centre + radius * np.cos(circle_angle),
                      y_centre + radius * np.sin(circle_angle), "r-", lw=0.9)
        # Fiducial annulus used for the summary efficiencies (centred on the axis).
        for radius in (fiducial_radii or []):
            axis.plot(radius * np.cos(circle_angle), radius * np.sin(circle_angle),
                      color="magenta", ls="--", lw=1.3)
    fig.colorbar(image, ax=[full_axis, zoom_axis], shrink=0.8, label="Hit efficiency [%]")
    zoom_axis.set_title(f"inner-edge zoom, |x|,|y| <= {r_zoom:.0f} mm"
                        + ("\nred: geometry openings (incl. 5 mm bakeout buffer) and outer radius"
                           if boundary_circles else "")
                        + (f"\nmagenta dashed: fiducial annulus {fiducial_radii[0]:.1f}-"
                           f"{fiducial_radii[1]:.0f} mm" if fiducial_radii else ""))
    region_efficiency = 100.0 * num.sum() / den.sum()
    full_axis.set_title(f"{label} hit efficiency, disk view ({title_extra})\n"
                        f"z_disk={disk_z_mm:g} mm, region {edges[0]:.1f} <= eta < {edges[-1]:.1f}: "
                        f"{region_efficiency:.1f}%")

    # Print each bin's rounded efficiency at its centre, but only where the bin
    # is large enough on the page for the text not to overlap its neighbours.
    fig.canvas.draw()  # settle the constrained layout so axis sizes are final
    font_size = 6.0
    text_size_points = 1.1 * max(2 * 0.6 * font_size, font_size)  # two digits, ~square
    phi_width_rad = np.radians(phi_edges[1] - phi_edges[0])
    phi_centres = np.radians(0.5 * (phi_edges[:-1] + phi_edges[1:]))
    for axis, r_lim in ((full_axis, r_full), (zoom_axis, r_zoom)):
        points_per_mm = axis.get_window_extent().width * 72.0 / fig.dpi / (2 * r_lim)
        for i in range(len(num)):
            r_low, r_high = sorted(radius_edges[i:i + 2])
            r_centre = 0.5 * (r_low + r_high)
            radial_points = (r_high - r_low) * points_per_mm
            arc_points = r_centre * phi_width_rad * points_per_mm
            if r_centre > r_lim or min(radial_points, arc_points) < text_size_points:
                continue
            for j, phi_centre in enumerate(phi_centres):
                if values.mask is not np.ma.nomask and values.mask[i, j]:
                    continue
                value = values[i, j]
                axis.text(r_centre * np.cos(phi_centre), r_centre * np.sin(phi_centre),
                          f"{value:.0f}", ha="center", va="center", fontsize=font_size,
                          color="black" if value > 55 else "white", clip_on=True)
    return fig


def momentum_centre(m: tuple[float, float]) -> float:
    return 0.5 * (m[0] + min(m[1], 20.0))  # the gun stops at 20 GeV


def plot_fiducial_vs_momentum(label: str, table: pd.DataFrame, vertex_z_mm: int):
    """Per-disk summary: fiducial-annulus hit efficiency vs momentum bin centre."""
    rows = table[(table.disk == label) & ~table.all_momenta]
    everything = table[(table.disk == label) & table.all_momenta].iloc[0]
    centre = rows.momentum_centre_GeV.to_numpy()
    half_width = 0.5 * (np.minimum(rows.momentum_max_GeV_exclusive, 20.0) - rows.momentum_min_GeV)
    fig, axis = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    axis.errorbar(centre, 100 * rows.fiducial_efficiency, xerr=half_width,
                  yerr=100 * rows.binomial_error, fmt="o", color="tab:blue", capsize=2)
    axis.axhline(100 * everything.fiducial_efficiency, color="gray", ls="--", lw=0.8,
                 label=f"all momenta: {100 * everything.fiducial_efficiency:.2f}%")
    for c, e in zip(centre, rows.fiducial_efficiency):
        axis.annotate(f"{100 * e:.1f}", (c, 100 * e), textcoords="offset points", xytext=(0, 7),
                      ha="center", fontsize=8)
    low = 100 * (rows.fiducial_efficiency - rows.binomial_error).min()
    axis.set_ylim(min(low - 1.0, 100 * everything.fiducial_efficiency - 2.0), 100.0)
    axis.set_xlim(0, 20.5)
    axis.set_xlabel("generated momentum, bin centre [GeV]")
    axis.set_ylabel("hit efficiency in fiducial annulus [%]")
    axis.grid(ls=":")
    axis.legend(loc="lower right")
    axis.set_title(f"{label}: fiducial hit efficiency vs momentum (z_vtx={vertex_z_mm} mm)\n"
                   f"{everything.fiducial_r_low_mm:.1f} <= R < {everything.fiducial_r_high_mm:.0f} mm "
                   f"(XML r_in + {everything.inner_margin_mm:g}, rmax - {everything.outer_margin_mm:g}); "
                   f"{100 * everything.fiducial_area_fraction:.0f}% of the XML disk area")
    return fig


def plot_fiducial_overview(table: pd.DataFrame, disk_order: list, shown_bins: list, vertex_z_mm: int):
    """First page: fiducial efficiency per disk for the lowest, middle and highest momentum bin."""
    fig, axis = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    x = np.arange(len(disk_order))
    colors = ["tab:red", "tab:green", "tab:blue"]
    lowest = 100.0
    for k, (m, color) in enumerate(zip(shown_bins, colors)):
        rows = [table[(table.disk == d) & (table.momentum_min_GeV == m[0])
                      & (table.momentum_max_GeV_exclusive == m[1])].iloc[0] for d in disk_order]
        values = np.array([100 * r.fiducial_efficiency for r in rows])
        errors = np.array([100 * r.binomial_error for r in rows])
        lowest = min(lowest, (values - errors).min())
        axis.errorbar(x + 0.15 * (k - 1), values, yerr=errors, fmt="o", color=color, capsize=2,
                      label=f"{m[0]:g} <= p < {min(m[1], 20.0):g} GeV")
        label_offset = (0, -12) if k == 1 else (0, 6)  # middle bin below, so labels do not collide
        for xi, v in zip(x + 0.15 * (k - 1), values):
            axis.annotate(f"{v:.1f}", (xi, v), textcoords="offset points", xytext=label_offset,
                          ha="center", fontsize=7, color=color)
    area = {r.disk: r.fiducial_area_fraction for r in table[table.all_momenta].itertuples()}
    axis.set_xticks(x, [f"{d}\n({100 * area[d]:.0f}% area)" for d in disk_order])
    axis.set_ylim(np.floor(lowest - 1.5), 100.0)
    axis.set_ylabel("hit efficiency in fiducial annulus [%]")
    axis.grid(axis="y", ls=":")
    axis.legend(loc="lower left")
    first = table.iloc[0]
    axis.set_title(f"Disk hit efficiency away from the edges (z_vtx={vertex_z_mm} mm): "
                   f"XML r_in + {first.inner_margin_mm:g} mm <= R < rmax - {first.outer_margin_mm:g} mm\n"
                   "simulated hits only (no sensor inefficiency); "
                   "% area = fiducial share of the XML disk area")
    return fig


def momentum_text(m: tuple[float, float]) -> str:
    return "all momenta" if m == ALL_MOMENTA else f"{m[0]:g} <= p < {m[1]:g} GeV"


def momentum_tag(m: tuple[float, float]) -> str:
    return "pall" if m == ALL_MOMENTA else f"p{m[0]:g}_to_{m[1]:g}".replace(".", "p")


def main() -> None:
    args = parse_args()
    momentum_bins = [ALL_MOMENTA] + [tuple(m) for m in (args.momentum_bin or [])
                                     if tuple(m) != ALL_MOMENTA]
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {args.output_dir}")
    eta_edges = {side: make_edges(*SIDE_ETA_RANGE[side], args.eta_bin_width)
                 for side in ("negative", "positive")}
    phi_edges = make_edges(0.0, 360.0, args.phi_bin_width_deg)
    boundaries = read_disk_boundaries(args.geometry_xml) if args.geometry_xml else None
    fiducial_annuli, xml_edges = None, {}
    if boundaries:
        fiducial_annuli = {}
        for disk, circles in boundaries.items():
            print(f"{disk} boundary circles (x_c, y_c, r) [mm]: "
                  + ", ".join(f"({x:.2f}, {y:.2f}, {r:.2f})" for x, y, r in circles))
            r_in = max(np.hypot(xc, yc) + r for xc, yc, r in circles[:2])  # = XML *_rmin
            r_out = circles[2][2]
            xml_edges[disk] = (r_in, r_out)
            fiducial_annuli[disk] = (r_in + args.fiducial_inner_margin_mm,
                                     r_out - args.fiducial_outer_margin_mm)
            print(f"{disk} fiducial annulus: {fiducial_annuli[disk][0]:.1f} <= R < "
                  f"{fiducial_annuli[disk][1]:.1f} mm")
    args.output_dir.mkdir(parents=True)

    summary_rows = []
    for vertex_z_mm in args.vertices:
        vertex_tag = f"vz_{VERTEX_LABELS[vertex_z_mm]}mm"
        result = accumulate(args.extracted_root, vertex_z_mm, momentum_bins, eta_edges, phi_edges,
                            fiducial_annuli)
        disk_order = [row[0] for row in DISKS["negative"][::-1]] + [row[0] for row in DISKS["positive"]]

        # Fiducial-annulus efficiencies (only with the geometry XML).
        fiducial_table = None
        if fiducial_annuli:
            fiducial_rows = []
            for label in disk_order:
                r_low, r_high = fiducial_annuli[label]
                r_in, r_out = xml_edges[label]
                for m in momentum_bins:
                    generated, hit = result["fiducial"][m][label]
                    efficiency = hit / generated
                    fiducial_rows.append({
                        "vertex_z_mm": vertex_z_mm, "disk": label,
                        "momentum_min_GeV": m[0], "momentum_max_GeV_exclusive": m[1],
                        "momentum_centre_GeV": momentum_centre(m), "all_momenta": m == ALL_MOMENTA,
                        "xml_r_in_mm": r_in, "xml_r_out_mm": r_out,
                        "inner_margin_mm": args.fiducial_inner_margin_mm,
                        "outer_margin_mm": args.fiducial_outer_margin_mm,
                        "fiducial_r_low_mm": r_low, "fiducial_r_high_mm": r_high,
                        "fiducial_area_fraction": (r_high**2 - r_low**2) / (r_out**2 - r_in**2),
                        "generated_in_fiducial": generated, "hit_in_fiducial": hit,
                        "fiducial_efficiency": efficiency,
                        "binomial_error": np.sqrt(efficiency * (1 - efficiency) / generated),
                    })
            fiducial_table = pd.DataFrame(fiducial_rows)
            fiducial_table.to_csv(args.output_dir / f"fiducial_efficiency_{vertex_tag}.csv", index=False)
            binned = [m for m in momentum_bins if m != ALL_MOMENTA]
            shown_bins = [binned[0], binned[len(binned) // 2], binned[-1]]

        pdf_path = args.output_dir / f"disk_hit_efficiency_{vertex_tag}.pdf"
        disk_view_pdf_path = args.output_dir / f"disk_hit_efficiency_disk_view_{vertex_tag}.pdf"
        with PdfPages(pdf_path) as pages, PdfPages(disk_view_pdf_path) as disk_view_pages:
            # First page of both PDFs: cross-disk fiducial summary.
            if fiducial_table is not None:
                fig = plot_fiducial_overview(fiducial_table, disk_order, shown_bins, vertex_z_mm)
                pages.savefig(fig)
                disk_view_pages.savefig(fig)
                fig.savefig(args.output_dir / f"fiducial_summary_{vertex_tag}.png", dpi=150)
                plt.close(fig)
            # Pages run in z order: ED4, ED3, ..., ED0, HD0, ..., HD4.
            for side, side_rows in (("negative", DISKS["negative"][::-1]),
                                    ("positive", DISKS["positive"])):
                for row in side_rows:
                    label = row[0]
                    disk_z_mm = row[3]  # nominal disk centre z from definitions_craterlake.xml
                    # First page of each disk: fiducial efficiency vs momentum.
                    if fiducial_table is not None:
                        fig = plot_fiducial_vs_momentum(label, fiducial_table, vertex_z_mm)
                        pages.savefig(fig)
                        disk_view_pages.savefig(fig)
                        fig.savefig(args.output_dir / f"{label}_fiducial_vs_p_{vertex_tag}.png", dpi=150)
                        plt.close(fig)
                    region = hit_region(result["numerator"][ALL_MOMENTA][label],
                                        result["denominator"][ALL_MOMENTA][label],
                                        args.region_min_row_efficiency)
                    for m in momentum_bins:
                        num = result["numerator"][m][label]
                        den = result["denominator"][m][label]
                        title_extra = f"z_vtx={vertex_z_mm} mm, {momentum_text(m)}"
                        fig = plot_disk(label, num, den, eta_edges[side], phi_edges, region,
                                        title_extra, args.minimum_bin_denominator)
                        pages.savefig(fig)
                        if m == ALL_MOMENTA:
                            fig.savefig(args.output_dir / f"{label}_hit_efficiency_{vertex_tag}_pall.png",
                                        dpi=150)
                        plt.close(fig)

                        fig = plot_disk_view(label, num, den, eta_edges[side], phi_edges, region,
                                             disk_z_mm, vertex_z_mm, title_extra,
                                             args.minimum_bin_denominator,
                                             boundaries.get(label) if boundaries else None,
                                             fiducial_annuli.get(label) if fiducial_annuli else None)
                        disk_view_pages.savefig(fig)
                        if m == ALL_MOMENTA:
                            fig.savefig(args.output_dir / f"{label}_disk_view_{vertex_tag}_pall.png",
                                        dpi=150)
                        plt.close(fig)

                        first, last = region
                        n_region = int(num[first:last + 1].sum())
                        d_region = int(den[first:last + 1].sum())
                        efficiency = n_region / d_region
                        summary_rows.append({
                            "vertex_z_mm": vertex_z_mm,
                            "momentum_min_GeV": m[0],
                            "momentum_max_GeV_exclusive": m[1],
                            "disk": label,
                            "region_eta_min": eta_edges[side][first],
                            "region_eta_max": eta_edges[side][last + 1],
                            "generated_in_region": d_region,
                            "hit_in_region": n_region,
                            "hit_efficiency_in_region": efficiency,
                            "binomial_error": np.sqrt(efficiency * (1 - efficiency) / d_region),
                            "hit_outside_region": int(num.sum()) - n_region,
                        })
                        np.savez_compressed(
                            args.output_dir / f"{label}_{vertex_tag}_{momentum_tag(m)}.npz",
                            numerator=num, denominator=den,
                            eta_edges=eta_edges[side], phi_edges_deg=phi_edges,
                            region_eta_bin_first_last=np.array(region),
                            metadata_json=np.asarray(json.dumps({
                                "disk": label, "vertex_z_mm": vertex_z_mm,
                                "momentum_range_GeV_half_open": list(m),
                                "region_definition": "eta rows with phi-integrated all-momentum hit fraction "
                                                     f">= {args.region_min_row_efficiency}",
                                "numerator": "generated primaries with >=1 associated disk hit",
                                "denominator": "all generated primaries in the bin",
                                "extracted_root": str(args.extracted_root),
                            })),
                        )
        print(f"Wrote {pdf_path}", flush=True)

    summary_path = args.output_dir / "disk_hit_efficiency_summary.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
