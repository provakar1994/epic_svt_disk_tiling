#!/usr/bin/env python3
"""Per-disk silicon hit efficiency using the true crossing point from the
zero-material reference planes (campaign acceptance_v3_refplanes).

Input: shards from extract_disk_particles_refplanes.py (one row per generated
primary pi+, all momenta and eta; silicon hit mask + first plane crossing).
The analysis streams over shards; nothing is concatenated across files.

DEFINITIONS (one primary counts at most once per disk)
  Denominator, disk d : selected primaries with plane_reached on d, i.e. >= 1
                        accepted SVTDiskRefPlaneHits hit on d's plane (linked to
                        the primary, not producedBySecondary).
  Numerator, disk d   : those with >= 1 associated TrackerEndcapHits hit on d.
  True point at disk  : the first plane crossing (earliest time) propagated
                        STRAIGHT along its own momentum from the plane hit z to
                        z_disk (plane_map.csv z_disk_mm; |dz| ~ 6 mm):
                          x_t = x_p + (z_disk - z_p) * px_p/pz_p   (same for y)
                        Curvature over 6 mm is negligible (sagitta < 0.01 mm for
                        p_T > 0.3 GeV in 1.7 T).
  Position selections (applied to the true point; generated p is the binning):
    active    : (replaces "reached", 2026-11-06) true point inside the filled
                outline of the active silicon. The outline is the union of all
                sensitive boxes of the disk (both faces, projected along z),
                taken from the built geometry (geometry/active_silicon_rectangles.csv,
                dump_active_silicon_rectangles.py), rasterised on a
                --active-grid-mm grid (0.5 mm). Gaps narrower than about
                2 x --active-close-mm (1 mm) are bridged by a morphological
                closing, enclosed holes are filled, and the hole(s) containing
                a beam-pipe opening centre are kept open. Row-end notches at the
                outer staircase (~15-18 mm wide) stay outside the outline.
    nomargin  : "inside the disk": r_t < rmax and outside both buffered
                beam-pipe openings (lepton/hadron circles with the +5 mm
                bakeout buffer, offset centres) from definitions_craterlake.xml
                via read_disk_boundaries(). The inner boundary is the opening
                shape itself (--inner-boundary openings, default); with
                --inner-boundary xml_rmin it is the circle r_t >= XML *_rmin
                (= the circle circumscribing both openings).
    fid       : the old fiducial annulus on the true point,
                XML r_in + 30 mm <= r_t < XML rmax - 40 mm, r_in = XML *_rmin;
                identical to the straight-line annulus of
                plot_disk_hit_efficiency_eta_phi.py, so directly comparable.
  Efficiency = numerator / denominator, binomial error sqrt(e(1-e)/N).

  Decomposition (straight-line eta acceptance of the generated direction,
  R_sl = |z_disk - z_vtx| / sinh|eta| as in the old analysis):
    accept : XML r_in <= R_sl < rmax;   sl_fid : r_in+30 <= R_sl < rmax-40.
    reached fraction  = plane_reached / generated            (in accept/sl_fid)
    hit given reached = (reached and silicon hit) / reached
    product           = (reached and hit) / generated
    old-style eff     = (silicon hit) / generated  (= old straight-line
                        fiducial efficiency for sl_fid); it differs from the
                        product only by hits without a plane crossing, which
                        are counted separately (hit_without_plane).

  Momentum bins (generated |p|, GeV, half-open): edges
    0.5,0.6,...,1.0, 2, 3, 5, 7, ..., 19, 20 ; the last bin is [19, 20] and is
    implemented as [19, 20.01) to include the gun endpoint, as before.
  Local angles at the plane: tan(theta_x) = px/|pz|, tan(theta_y) = py/|pz|
    (first-crossing momentum). On the HD side this is px/pz, py/pz; on the ED
    side (pz < 0) the sign is chosen so that positive still means moving
    toward +x / +y.
  Row families: compact/tracking/silicon_disks_tiling/20261001_ES/
    SVT_endcap_corrugation_rows_33_36.csv (HD3b -> HD3). Each row covers
    row_y +/- pitch/4; the family-A (36 mm pitch) region of a disk is
    [min(row_y - pitch/4), max(row_y + pitch/4)) over its A rows and exists on
    disks 2-4 only. row_y is global EPIC y on both sides
    (check_row_family_y_convention_20261106.py). The A region is NOT symmetric
    in y on ED2, ED3, ED4, HD2, so efficiency vs signed y is the primary view;
    the |y| view marks both boundary values.
  2D maps: true (x, y), --xy-bin-mm square bins (default 4 mm), all momenta,
    every primary that reached the plane (no position cut). 1D profiles (y, |y|, x): 1 mm bins; tan bins 0.05.
  Plane shape: no assumption that a plane is centred on the beam axis. The
    plane annulus (plane_map.csv v2 columns center_x_mm, center_y_mm,
    r_inner/r_outer_about_center_mm; a point is on the plane if
    r_inner <= |p - centre| <= r_outer) is used only for the on-plane
    diagnostic and drawn on the maps; a 9-column map is read as a centred
    annulus rmin_mm..rmax_mm. Selections use the disk XML boundaries only.
    No assumption |p_plane| ~ |p_gen| either: propagation uses the plane
    momentum direction; the ratio is a printed diagnostic only.

OUTPUT (per vertex, results/refplane_efficiency_v1/vz_<label>mm/):
  summary.txt, integrated_efficiency.csv, efficiency_vs_p.csv,
  family_AB_efficiency.csv, decomposition_vs_p.csv, comparison_straight_line.csv,
  histograms.npz (every counter), refplane_efficiency_vz_<label>mm.pdf and PNGs.
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

from plot_disk_hit_efficiency_eta_phi import read_disk_boundaries
from reduce_disk_acceptance import DISKS, VERTEX_LABELS, configuration_name


HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parents[1]
EPIC_DIR = HERE.parents[2]
P_EDGES = np.array([0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 2, 3, 5, 7, 9, 11, 13, 15, 17, 19, 20.01])
P_GROUPS = [(0.5, 1.0), (1.0, 3.0), (3.0, 20.01)]     # coarse groups for 1D curves
LINE_EDGES = np.arange(-450.0, 450.0 + 1e-9, 1.0)      # y and x profiles, 1 mm
ABS_EDGES = np.arange(0.0, 450.0 + 1e-9, 1.0)
TAN_EDGES = np.round(np.arange(-1.5, 1.5 + 1e-9, 0.05), 10)
SELECTIONS = ("active", "nomargin", "fid")
DECOMP = ("accept", "sl_fid")
DISK_ORDER = [row[0] for row in DISKS["negative"][::-1]] + [row[0] for row in DISKS["positive"]]
# Old straight-line fiducial results (v8, all momenta) for the comparison table.
PUBLISHED_V8 = {0: "disk_hit_efficiency_v8/fiducial_efficiency_vz_000mm.csv",
                100: "disk_hit_efficiency_v8_vz_p100mm/fiducial_efficiency_vz_p100mm.csv",
                -100: "disk_hit_efficiency_v8_vz_m100mm/fiducial_efficiency_vz_m100mm.csv"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extracted-root", type=Path, default=HERE / "extracted/acceptance_v3_refplanes")
    parser.add_argument("--output-dir", type=Path, default=HERE / "results/refplane_efficiency_v1",
                        help="One subdirectory per vertex; an existing vertex subdirectory is never overwritten.")
    parser.add_argument("--vertices", type=int, nargs="+", default=[0, 100, -100], choices=sorted(VERTEX_LABELS))
    parser.add_argument("--plane-map", type=Path, default=PROJECT_DIR / "refplanes/plane_map.csv")
    parser.add_argument("--geometry-xml", type=Path, default=EPIC_DIR / "compact/tracking/definitions_craterlake.xml")
    parser.add_argument("--rows-csv", type=Path, default=EPIC_DIR /
                        "compact/tracking/silicon_disks_tiling/20261001_ES/SVT_endcap_corrugation_rows_33_36.csv")
    parser.add_argument("--published-results-dir", type=Path, default=HERE / "results",
                        help="Directory holding the v8 straight-line fiducial CSVs.")
    parser.add_argument("--active-csv", type=Path, default=HERE / "geometry/active_silicon_rectangles.csv",
                        help="Sensitive-box corners per disk from dump_active_silicon_rectangles.py.")
    parser.add_argument("--active-grid-mm", type=float, default=0.5)
    parser.add_argument("--active-close-mm", type=float, default=1.0)
    parser.add_argument("--xy-bin-mm", type=float, default=4.0)
    parser.add_argument("--inner-margin-mm", type=float, default=30.0)
    parser.add_argument("--outer-margin-mm", type=float, default=40.0)
    parser.add_argument("--inner-boundary", choices=["openings", "xml_rmin"], default="openings")
    parser.add_argument("--min-denominator-2d", type=int, default=20)
    parser.add_argument("--min-denominator-1d", type=int, default=100)
    parser.add_argument("--max-shards-per-side", type=int, help="Testing option.")
    return parser.parse_args()


# ----------------------------------------------------------------- geometry
def load_geometry(args) -> dict:
    """Per disk: z_disk, z_plane, openings, r_in, rmax, family-A y range."""
    plane_map = pd.read_csv(args.plane_map)
    boundaries = read_disk_boundaries(args.geometry_xml)
    rows = pd.read_csv(args.rows_csv)
    rows["disk"] = rows.disk.replace({"HD3b": "HD3"})
    geometry = {}
    for side in DISKS:
        for index, (disk, _, _, nominal_z) in enumerate(DISKS[side]):
            entry = plane_map.loc[plane_map.disk.str.strip() == disk]
            if len(entry) != 1:
                raise ValueError(f"plane_map.csv must have exactly one row for {disk}")
            entry = entry.iloc[0]
            circles = boundaries[disk]
            openings = circles[:2]
            r_in = max(np.hypot(xc, yc) + r for xc, yc, r in openings)   # = XML *_rmin
            family_a = rows[(rows.disk == disk) & (rows.family == "A")]
            a_range = None
            if len(family_a):
                a_range = (float((family_a.row_y_mm - family_a.pitch_mm / 4).min()),
                           float((family_a.row_y_mm + family_a.pitch_mm / 4).max()))
            geometry[disk] = {
                "side": side, "index": index, "z_disk": float(entry.z_disk_mm),
                "z_plane": float(entry.z_plane_mm), "nominal_z": nominal_z,
                "plane_rmin": float(entry.rmin_mm), "plane_rmax": float(entry.rmax_mm),
                # Plane annulus about its own centre (v2 map); centred fallback for 9-column maps.
                "plane_centre": (float(entry.get("center_x_mm", 0.0)), float(entry.get("center_y_mm", 0.0))),
                "plane_r_inner": float(entry.get("r_inner_about_center_mm", entry.rmin_mm)),
                "plane_r_outer": float(entry.get("r_outer_about_center_mm", entry.rmax_mm)),
                "openings": openings, "r_in": r_in, "rmax": circles[2][2],
                "fid": (r_in + args.inner_margin_mm, circles[2][2] - args.outer_margin_mm),
                "family_a_y": a_range,
            }
    return geometry


def build_active_outlines(args, geometry: dict) -> None:
    """Add the filled active-silicon outline (boolean raster) to each disk entry."""
    from scipy import ndimage
    boxes = pd.read_csv(args.active_csv)
    step = args.active_grid_mm
    limit = 450.0
    n = int(round(2 * limit / step))
    radius_px = max(1, int(round(args.active_close_mm / step)))
    yy, xx = np.mgrid[-radius_px:radius_px + 1, -radius_px:radius_px + 1]
    structure = xx**2 + yy**2 <= radius_px**2
    for disk, g in geometry.items():
        sub = boxes[boxes.disk == disk]
        if not len(sub):
            raise ValueError(f"no active-silicon boxes for {disk} in {args.active_csv}")
        union = np.zeros((n, n), bool)            # index [ix, iy]
        x_lo = sub[["x0_mm", "x1_mm", "x2_mm", "x3_mm"]].min(axis=1).to_numpy()
        x_hi = sub[["x0_mm", "x1_mm", "x2_mm", "x3_mm"]].max(axis=1).to_numpy()
        y_lo = sub[["y0_mm", "y1_mm", "y2_mm", "y3_mm"]].min(axis=1).to_numpy()
        y_hi = sub[["y0_mm", "y1_mm", "y2_mm", "y3_mm"]].max(axis=1).to_numpy()
        # A pixel is active if its centre lies inside a box.
        to_index = lambda v: np.clip(np.round((v + limit) / step).astype(int), 0, n)
        for a, b, c_, d in zip(to_index(x_lo), to_index(x_hi), to_index(y_lo), to_index(y_hi)):
            union[a:b, c_:d] = True
        closed = ndimage.binary_closing(union, structure=structure)
        filled = ndimage.binary_fill_holes(closed)
        holes, _ = ndimage.label(filled & ~closed)
        for xc, yc, _r in g["openings"]:
            ix, iy = int((xc + limit) / step), int((yc + limit) / step)
            if holes[ix, iy]:
                filled[holes == holes[ix, iy]] = False
            elif closed[ix, iy]:
                raise ValueError(f"{disk}: beam-pipe opening centre lies on active silicon")
        pixel_area = step * step
        g["active_outline"] = filled
        g["active_grid"] = (limit, step, n)
        g["active_stats"] = {"boxes": int(len(sub)), "box_area_sum_mm2": float((4 * sub.half_x_mm * sub.half_y_mm).sum()),
                             "union_area_mm2": float(union.sum() * pixel_area),
                             "outline_area_mm2": float(filled.sum() * pixel_area)}


def in_active_outline(g: dict, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    limit, step, n = g["active_grid"]
    ix = np.floor((x + limit) / step)
    iy = np.floor((y + limit) / step)
    ok = np.isfinite(ix) & np.isfinite(iy) & (ix >= 0) & (ix < n) & (iy >= 0) & (iy < n)
    result = np.zeros(len(x), bool)
    result[ok] = g["active_outline"][ix[ok].astype(int), iy[ok].astype(int)]
    return result


def binomial(k, n):
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        e = np.where(n > 0, k / n, np.nan)
        err = np.where(n > 0, np.sqrt(e * (1 - e) / n), np.nan)
    return e, err


# ------------------------------------------------------------- accumulation
def new_counters(xy_edges: np.ndarray) -> dict:
    n_p = len(P_EDGES) - 1
    shape_1d = lambda edges: (len(SELECTIONS), n_p, len(edges) - 1)
    c = {"p_den": np.zeros((len(SELECTIONS), n_p), np.int64), "p_num": np.zeros((len(SELECTIONS), n_p), np.int64),
         "ab_den": np.zeros((len(SELECTIONS), 2, n_p), np.int64), "ab_num": np.zeros((len(SELECTIONS), 2, n_p), np.int64),
         "dec_gen": np.zeros((2, n_p), np.int64), "dec_reach": np.zeros((2, n_p), np.int64),
         "dec_hit_and_reach": np.zeros((2, n_p), np.int64), "dec_hit_any": np.zeros((2, n_p), np.int64),
         "xy_den": np.zeros((len(xy_edges) - 1,) * 2, np.int64), "xy_num": np.zeros((len(xy_edges) - 1,) * 2, np.int64),
         "hit_without_plane": np.zeros(n_p, np.int64), "multi_crossing": 0,
         "first_crossing_off_plane": 0, "hit_reached": 0, "hit_reached_outside_active": 0,
         "true_minus_silicon_r_mm": [], "plane_dz_mm": [], "plane_p_over_gen_p": []}
    for name, edges in (("y", LINE_EDGES), ("absy", ABS_EDGES), ("x", LINE_EDGES), ("tanx", TAN_EDGES), ("tany", TAN_EDGES)):
        c[f"{name}_den"] = np.zeros(shape_1d(edges), np.int64)
        c[f"{name}_num"] = np.zeros(shape_1d(edges), np.int64)
    return c


def hist_by_p(values, p_index, selected, edges):
    """2D histogram (p bin, value bin) of selected entries."""
    good = selected & np.isfinite(values) & (p_index >= 0)
    return np.histogram2d(p_index[good], values[good],
                          bins=(np.arange(len(P_EDGES)), edges))[0].astype(np.int64)


def accumulate_disk(c: dict, g: dict, s: dict, xy_edges: np.ndarray, diag_rng) -> None:
    """Add one shard's particles to one disk's counters."""
    i = g["index"]
    bit = np.uint8(1 << i)
    reached = (s["plane_mask"] & bit) != 0
    hit = (s["hit_mask"] & bit) != 0
    p = s["p_GeV"].astype(float)
    p_index = np.digitize(p, P_EDGES) - 1
    p_index[(p_index < 0) | (p_index >= len(P_EDGES) - 1)] = -1
    in_p = p_index >= 0

    xp, yp, zp = (s[f"plane_{a}_mm"][:, i].astype(float) for a in "xyz")
    px, py, pz = (s[f"plane_p{a}_GeV"][:, i].astype(float) for a in "xyz")
    with np.errstate(divide="ignore", invalid="ignore"):
        dz = g["z_disk"] - zp
        xt = xp + dz * px / pz
        yt = yp + dz * py / pz
        tanx = px / np.abs(pz)
        tany = py / np.abs(pz)
    rt = np.hypot(xt, yt)
    outside_openings = np.ones(len(p), bool)
    for xc, yc, radius in g["openings"]:
        outside_openings &= np.hypot(xt - xc, yt - yc) > radius
    inner_ok = outside_openings if g["inner_boundary"] == "openings" else (rt >= g["r_in"])
    masks = {"active": reached & in_p & in_active_outline(g, xt, yt),
             "nomargin": reached & in_p & inner_ok & (rt < g["rmax"]),
             "fid": reached & in_p & (rt >= g["fid"][0]) & (rt < g["fid"][1])}

    nbin = len(P_EDGES) - 1
    for k, name in enumerate(SELECTIONS):
        sel = masks[name]
        c["p_den"][k] += np.bincount(p_index[sel], minlength=nbin)
        c["p_num"][k] += np.bincount(p_index[sel & hit], minlength=nbin)
        if g["family_a_y"] is not None:
            in_a = (yt >= g["family_a_y"][0]) & (yt < g["family_a_y"][1])
            for f, region in enumerate((in_a, ~in_a & np.isfinite(yt))):
                c["ab_den"][k, f] += np.bincount(p_index[sel & region], minlength=nbin)
                c["ab_num"][k, f] += np.bincount(p_index[sel & region & hit], minlength=nbin)
        for key, values, edges in (("y", yt, LINE_EDGES), ("absy", np.abs(yt), ABS_EDGES), ("x", xt, LINE_EDGES),
                                   ("tanx", tanx, TAN_EDGES), ("tany", tany, TAN_EDGES)):
            c[f"{key}_den"][k] += hist_by_p(values, p_index, sel, edges)
            c[f"{key}_num"][k] += hist_by_p(values, p_index, sel & hit, edges)

    sel = reached & in_p & np.isfinite(xt) & np.isfinite(yt)
    c["xy_den"] += np.histogram2d(xt[sel], yt[sel], bins=(xy_edges, xy_edges))[0].astype(np.int64)
    c["xy_num"] += np.histogram2d(xt[sel & hit], yt[sel & hit], bins=(xy_edges, xy_edges))[0].astype(np.int64)

    # Decomposition in the straight-line acceptance of the generated direction.
    radius_sl = np.abs(g["z_disk"] - s["vertex_z_mm"].astype(float)) / np.sinh(np.abs(s["eta"].astype(float)))
    for k, (low, high) in enumerate(((g["r_in"], g["rmax"]), g["fid"])):
        acc = in_p & (radius_sl >= low) & (radius_sl < high)
        c["dec_gen"][k] += np.bincount(p_index[acc], minlength=nbin)
        c["dec_reach"][k] += np.bincount(p_index[acc & reached], minlength=nbin)
        c["dec_hit_and_reach"][k] += np.bincount(p_index[acc & reached & hit], minlength=nbin)
        c["dec_hit_any"][k] += np.bincount(p_index[acc & hit], minlength=nbin)

    # Diagnostics (a random subsample of values is kept for medians).
    c["hit_without_plane"] += np.bincount(p_index[in_p & hit & ~reached], minlength=nbin)
    c["multi_crossing"] += int((s["plane_crossings"][:, i] > 1).sum())
    # First crossings must lie on the plane annulus (about the plane centre); 0.01 mm tolerance.
    d_centre = np.hypot(xp - g["plane_centre"][0], yp - g["plane_centre"][1])
    c["first_crossing_off_plane"] += int((reached & ((d_centre < g["plane_r_inner"] - 0.01)
                                                     | (d_centre > g["plane_r_outer"] + 0.01))).sum())
    both = reached & hit
    c["hit_reached"] += int((both & in_p).sum())
    c["hit_reached_outside_active"] += int((both & in_p & ~masks["active"]).sum())
    take = lambda m: m & (diag_rng.random(len(m)) < 0.05)
    sub = take(both)
    c["true_minus_silicon_r_mm"].append(np.hypot(xt[sub] - s["mean_hit_x_mm"][sub, i],
                                                 yt[sub] - s["mean_hit_y_mm"][sub, i]))
    sub = take(reached)
    c["plane_dz_mm"].append(zp[sub] - g["z_plane"])
    c["plane_p_over_gen_p"].append(np.sqrt(px[sub]**2 + py[sub]**2 + pz[sub]**2) / p[sub])


def accumulate_vertex(args, geometry: dict, vertex_z_mm: int, xy_edges: np.ndarray) -> tuple[dict, dict]:
    counters = {disk: new_counters(xy_edges) for disk in DISK_ORDER}
    provenance = {"shards": 0, "particles": 0, "shards_without_plane_collection": 0,
                  "plane_hits_total": 0, "plane_hits_accepted": 0, "plane_hits_dropped_not_primary": 0,
                  "plane_hits_secondary_flagged": 0, "plane_hits_other_side": 0, "shard_list": []}
    rng = np.random.default_rng(12345)
    for side in DISKS:
        configuration = configuration_name(vertex_z_mm, side)
        shards = sorted((args.extracted_root / configuration).glob("particles_*.npz"))
        if args.max_shards_per_side:
            shards = shards[:args.max_shards_per_side]
        if not shards:
            raise FileNotFoundError(f"No shards for {configuration} under {args.extracted_root}")
        print(f"{configuration}: {len(shards)} shards", flush=True)
        for path in shards:
            with np.load(path, allow_pickle=False) as stored:
                shard = {key: stored[key] for key in stored.files}
            meta = json.loads(str(shard.pop("metadata_json")))
            if not str(meta.get("format_version", "")).startswith("refplanes"):
                raise ValueError(f"{path} is not a refplanes shard")
            provenance["shards"] += 1
            provenance["particles"] += len(shard["p_GeV"])
            provenance["shards_without_plane_collection"] += int(not meta["plane_collection_present"])
            for key in ("plane_hits_total", "plane_hits_accepted", "plane_hits_dropped_not_primary",
                        "plane_hits_secondary_flagged", "plane_hits_other_side"):
                provenance[key] += int(meta[key])
            provenance["shard_list"].append(str(path))
            for disk, g in geometry.items():
                if g["side"] == side:
                    accumulate_disk(counters[disk], g, shard, xy_edges, rng)
    for c in counters.values():
        for key in ("true_minus_silicon_r_mm", "plane_dz_mm", "plane_p_over_gen_p"):
            c[key] = np.concatenate(c[key]) if c[key] else np.empty(0)
    return counters, provenance


# ------------------------------------------------------------------ tables
def p_label(k: int) -> str:
    high = 20.0 if P_EDGES[k + 1] > 20 else P_EDGES[k + 1]
    return f"{P_EDGES[k]:g}-{high:g}"


def build_tables(counters, geometry, vertex_z_mm, published):
    integrated, vs_p, ab, decomposition, comparison = [], [], [], [], []
    for disk in DISK_ORDER:
        c, g = counters[disk], geometry[disk]
        for k, sel in enumerate(SELECTIONS):
            n, m = int(c["p_den"][k].sum()), int(c["p_num"][k].sum())
            e, err = binomial(m, n)
            integrated.append({"vertex_z_mm": vertex_z_mm, "disk": disk, "selection": sel,
                               "denominator": n, "numerator": m, "efficiency": e, "binomial_error": err})
            e, err = binomial(c["p_num"][k], c["p_den"][k])
            for b in range(len(P_EDGES) - 1):
                vs_p.append({"vertex_z_mm": vertex_z_mm, "disk": disk, "selection": sel,
                             "p_min_GeV": P_EDGES[b], "p_max_GeV": P_EDGES[b + 1], "p_bin": p_label(b),
                             "denominator": int(c["p_den"][k, b]), "numerator": int(c["p_num"][k, b]),
                             "efficiency": e[b], "binomial_error": err[b]})
            if g["family_a_y"] is not None:
                for f, family in enumerate(("A_36mm", "B_33mm")):
                    for b in [None, *range(len(P_EDGES) - 1)]:
                        n = c["ab_den"][k, f].sum() if b is None else c["ab_den"][k, f, b]
                        m = c["ab_num"][k, f].sum() if b is None else c["ab_num"][k, f, b]
                        e, err = binomial(m, n)
                        ab.append({"vertex_z_mm": vertex_z_mm, "disk": disk, "selection": sel, "family": family,
                                   "family_A_y_range_mm": f"[{g['family_a_y'][0]:.2f}, {g['family_a_y'][1]:.2f})",
                                   "p_bin": "all" if b is None else p_label(b),
                                   "denominator": int(n), "numerator": int(m),
                                   "efficiency": float(e), "binomial_error": float(err)})
        for k, name in enumerate(DECOMP):
            for b in [None, *range(len(P_EDGES) - 1)]:
                pick = (lambda a: a[k].sum()) if b is None else (lambda a: a[k, b])
                gen, reach = int(pick(c["dec_gen"])), int(pick(c["dec_reach"]))
                hr, hany = int(pick(c["dec_hit_and_reach"])), int(pick(c["dec_hit_any"]))
                r, r_err = binomial(reach, gen)
                h, h_err = binomial(hr, reach)
                prod, prod_err = binomial(hr, gen)
                old, old_err = binomial(hany, gen)
                decomposition.append({"vertex_z_mm": vertex_z_mm, "disk": disk, "acceptance": name,
                                      "p_bin": "all" if b is None else p_label(b),
                                      "generated": gen, "reached": reach, "hit_and_reached": hr, "hit_any": hany,
                                      "reached_fraction": float(r), "reached_error": float(r_err),
                                      "hit_given_reached": float(h), "hit_given_reached_error": float(h_err),
                                      "product": float(prod), "product_error": float(prod_err),
                                      "old_style_efficiency": float(old), "old_style_error": float(old_err)})
        # Comparison with the straight-line fiducial efficiency.
        for b in [None, *range(len(P_EDGES) - 1)]:
            row = next(d for d in decomposition[::-1] if d["disk"] == disk and d["acceptance"] == "sl_fid"
                       and d["p_bin"] == ("all" if b is None else p_label(b)))
            k_fid = SELECTIONS.index("fid")
            k_nm = SELECTIONS.index("nomargin")
            n_f = c["p_den"][k_fid].sum() if b is None else c["p_den"][k_fid, b]
            m_f = c["p_num"][k_fid].sum() if b is None else c["p_num"][k_fid, b]
            n_n = c["p_den"][k_nm].sum() if b is None else c["p_den"][k_nm, b]
            m_n = c["p_num"][k_nm].sum() if b is None else c["p_num"][k_nm, b]
            e_f, err_f = binomial(m_f, n_f)
            e_n, err_n = binomial(m_n, n_n)
            comparison.append({
                "vertex_z_mm": vertex_z_mm, "disk": disk, "p_bin": "all" if b is None else p_label(b),
                "published_v8_straight_line_fid": published.get(disk, np.nan) if b is None else np.nan,
                "straight_line_fid_this_sample": row["old_style_efficiency"],
                "straight_line_fid_this_sample_err": row["old_style_error"],
                "sl_fid_reached_fraction": row["reached_fraction"],
                "sl_fid_hit_given_reached": row["hit_given_reached"],
                "true_point_fid": float(e_f), "true_point_fid_err": float(err_f),
                "true_point_nomargin": float(e_n), "true_point_nomargin_err": float(err_n),
                "true_fid_minus_straight_line_fid": float(e_f) - row["old_style_efficiency"],
            })
    return (pd.DataFrame(integrated), pd.DataFrame(vs_p), pd.DataFrame(ab),
            pd.DataFrame(decomposition), pd.DataFrame(comparison))


def read_published(args, vertex_z_mm) -> dict:
    path = args.published_results_dir / PUBLISHED_V8.get(vertex_z_mm, "missing")
    if not path.exists():
        return {}
    table = pd.read_csv(path)
    table = table[table.all_momenta.astype(bool)]
    return dict(zip(table.disk, table.fiducial_efficiency))


# ---------------------------------------------------------------- plotting
def ratio(num, den, minimum):
    with np.errstate(divide="ignore", invalid="ignore"):
        e = num / den
    return np.where(den >= minimum, e, np.nan)


def plot_vs_p(disk, c, vz):
    centres = 0.5 * (P_EDGES[:-1] + np.minimum(P_EDGES[1:], 20.0))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
    for k, sel in enumerate(SELECTIONS):
        e, err = binomial(c["p_num"][k], c["p_den"][k])
        a1.errorbar(centres, 100 * e, yerr=100 * err, fmt="o-", ms=3, capsize=2, label=f"true point: {sel}")
    k = DECOMP.index("sl_fid")
    old, old_err = binomial(c["dec_hit_any"][k], c["dec_gen"][k])
    a1.errorbar(centres, 100 * old, yerr=100 * old_err, fmt="s--", ms=3, capsize=2, color="gray",
                label="straight-line fid (old def., this sample)")
    a1.set_xscale("log"); a1.set_xlabel("generated p [GeV]"); a1.set_ylabel("hit efficiency [%]")
    a1.set_title(f"{disk}, vz={vz:+d} mm: hit | plane reached"); a1.grid(alpha=0.3); a1.legend(fontsize=7)
    for k, name in enumerate(DECOMP):
        r, _ = binomial(c["dec_reach"][k], c["dec_gen"][k])
        h, _ = binomial(c["dec_hit_and_reach"][k], c["dec_reach"][k])
        a2.plot(centres, 100 * r, "o-", ms=3, label=f"reached / generated ({name})")
        a2.plot(centres, 100 * h, "^-", ms=3, label=f"hit / reached ({name})")
        a2.plot(centres, 100 * r * h, "k:" if k else "k--", lw=1, label=f"product ({name})")
    a2.set_xscale("log"); a2.set_xlabel("generated p [GeV]"); a2.set_ylabel("[%]")
    a2.set_title("decomposition in straight-line acceptance"); a2.grid(alpha=0.3); a2.legend(fontsize=7)
    fig.tight_layout()
    return fig


def draw_boundaries(ax, g, with_family=True):
    t = np.linspace(0, 2 * np.pi, 400)
    for xc, yc, r in g["openings"]:
        ax.plot(xc + r * np.cos(t), yc + r * np.sin(t), "r-", lw=0.7)
    ax.plot(g["rmax"] * np.cos(t), g["rmax"] * np.sin(t), "r-", lw=0.7)
    for r in g["fid"]:
        ax.plot(r * np.cos(t), r * np.sin(t), "m--", lw=0.7)
    cx, cy = g["plane_centre"]
    for r in (g["plane_r_inner"], g["plane_r_outer"]):
        ax.plot(cx + r * np.cos(t), cy + r * np.sin(t), color="0.4", ls=(0, (1, 2)), lw=0.7)
    if with_family and g["family_a_y"] is not None:
        for y in g["family_a_y"]:
            ax.axhline(y, color="c", ls=":", lw=0.8)
    if "active_outline" in g:
        limit, step, n = g["active_grid"]
        centres = -limit + step * (np.arange(n) + 0.5)
        ax.contour(centres, centres, g["active_outline"].T.astype(float), levels=[0.5],
                   colors="orange", linewidths=0.6)


def plot_map(disk, c, g, xy_edges, vz, minimum):
    e = ratio(c["xy_num"], c["xy_den"], minimum)
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    mesh = ax.pcolormesh(xy_edges, xy_edges, 100 * e.T, vmin=80, vmax=100, cmap="viridis", shading="flat")
    fig.colorbar(mesh, ax=ax, label="hit efficiency [%] (plane reached)")
    draw_boundaries(ax, g)
    lim = g["plane_rmax"] + abs(g["plane_centre"][0]) + 10
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
    ax.set_xlabel("true x at disk [mm]"); ax.set_ylabel("true y at disk [mm]")
    ax.set_title(f"{disk}, vz={vz:+d} mm, all p, {xy_edges[1]-xy_edges[0]:g} mm bins "
                 f"(masked < {minimum}); red XML, magenta fid, orange active, cyan A/B, grey dotted plane")
    ax.title.set_fontsize(8)
    fig.tight_layout()
    return fig


def plot_profiles(disk, c, g, vz, minimum):
    k = SELECTIONS.index("nomargin")
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    panels = [("y", LINE_EDGES, "true y at disk [mm]"), ("absy", ABS_EDGES, "|true y| at disk [mm]"),
              ("x", LINE_EDGES, "true x at disk [mm]"), ("tan", TAN_EDGES, "local tan(theta) at plane")]
    for ax, (key, edges, label) in zip(axes.ravel(), panels):
        centres = 0.5 * (edges[1:] + edges[:-1])
        names = [("tanx", "tan theta_x = px/|pz|"), ("tany", "tan theta_y = py/|pz|")] if key == "tan" else [(key, "")]
        for name, tag in names:
            num, den = c[f"{name}_num"][k], c[f"{name}_den"][k]
            ax.plot(centres, 100 * ratio(num.sum(0), den.sum(0), minimum), "-", lw=0.9,
                    label=f"all p {tag}".strip())
            if key != "tan":
                for low, high in P_GROUPS:
                    rows = (P_EDGES[:-1] >= low - 1e-9) & (P_EDGES[1:] <= high + 1e-9)
                    ax.plot(centres, 100 * ratio(num[rows].sum(0), den[rows].sum(0), minimum), "-", lw=0.6,
                            alpha=0.8, label=f"{low:g}-{min(high, 20):g} GeV")
        if g["family_a_y"] is not None and key in ("y", "absy"):
            values = g["family_a_y"] if key == "y" else sorted({abs(v) for v in g["family_a_y"]})
            for v in values:
                ax.axvline(v, color="c", ls=":", lw=1.0)
            ax.text(0.01, 0.02, "cyan: A(36 mm)/B(33 mm) boundary", transform=ax.transAxes, fontsize=7)
        ax.set_xlabel(label); ax.set_ylabel("hit efficiency [%]"); ax.set_ylim(70, 101)
        ax.grid(alpha=0.3); ax.legend(fontsize=6, loc="lower right")
    fig.suptitle(f"{disk}, vz={vz:+d} mm, selection nomargin (true point inside disk), "
                 f"bins with < {minimum} entries masked", fontsize=9)
    fig.tight_layout()
    return fig


def plot_overview(integrated, vz):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(DISK_ORDER))
    for offset, sel in zip((-0.2, 0.0, 0.2), SELECTIONS):
        t = integrated[integrated.selection == sel].set_index("disk").loc[DISK_ORDER]
        ax.errorbar(x + offset, 100 * t.efficiency, yerr=100 * t.binomial_error, fmt="o", ms=4, label=sel)
    ax.set_xticks(x, DISK_ORDER); ax.set_ylabel("hit efficiency [%] (plane reached)")
    ax.set_title(f"Integrated hit efficiency, true crossing point, vz={vz:+d} mm, 0.5-20 GeV")
    ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout()
    return fig


# -------------------------------------------------------------------- main
def write_summary(path, args, vz, geometry, counters, provenance, tables, xy_edges):
    integrated, vs_p, ab, decomposition, comparison = tables
    lines = [f"Reference-plane hit efficiency, vertex z = {vz:+d} mm",
             f"extracted root: {args.extracted_root}", f"plane map: {args.plane_map}",
             f"geometry xml: {args.geometry_xml}", f"rows csv: {args.rows_csv}",
             f"inner boundary (nomargin): {args.inner_boundary}; fid margins {args.inner_margin_mm:g}/"
             f"{args.outer_margin_mm:g} mm; xy bins {args.xy_bin_mm:g} mm",
             f"active outline: {args.active_csv}; grid {args.active_grid_mm:g} mm, closing {args.active_close_mm:g} mm",
             "provenance: " + json.dumps({k: v for k, v in provenance.items() if k != "shard_list"}), ""]
    if provenance["shards_without_plane_collection"]:
        lines.append(f"WARNING: {provenance['shards_without_plane_collection']} shards have NO plane collection; "
                     "their primaries never enter a denominator.")
    lines.append("Integrated efficiency [%] (denominator = plane reached), binomial errors:")
    pivot = integrated.assign(text=lambda t: [f"{100*e:6.2f}+-{100*s:4.2f} (N={n})" for e, s, n in
                                              zip(t.efficiency, t.binomial_error, t.denominator)])
    lines.append(pivot.pivot(index="disk", columns="selection", values="text").loc[DISK_ORDER, list(SELECTIONS)]
                 .to_string())
    lines += ["", "Comparison with straight-line fiducial efficiency [%], all momenta:"]
    comp = comparison[comparison.p_bin == "all"].set_index("disk").loc[DISK_ORDER]
    lines.append((100 * comp[["published_v8_straight_line_fid", "straight_line_fid_this_sample",
                              "sl_fid_reached_fraction", "sl_fid_hit_given_reached", "true_point_fid",
                              "true_point_nomargin", "true_fid_minus_straight_line_fid"]]).round(2).to_string())
    lines += ["", "True-point fid efficiency [%] vs p (rows disk, columns p bin GeV):"]
    t = vs_p[vs_p.selection == "fid"].pivot(index="disk", columns="p_bin", values="efficiency")
    lines.append((100 * t.loc[DISK_ORDER, [p_label(b) for b in range(len(P_EDGES) - 1)]]).round(2).to_string())
    lines += ["", "Straight-line fid (old definition, this sample) minus true-point fid [points] vs p:"]
    t = comparison[comparison.p_bin != "all"].pivot(index="disk", columns="p_bin",
                                                     values="true_fid_minus_straight_line_fid")
    lines.append((-100 * t.loc[DISK_ORDER, [p_label(b) for b in range(len(P_EDGES) - 1)]]).round(2).to_string())
    if len(ab):
        lines += ["", "Family A (36 mm) vs B (33 mm) efficiency [%], all momenta, disks 2-4:"]
        t = ab[ab.p_bin == "all"].assign(text=lambda t: [f"{100*e:6.2f}+-{100*s:4.2f} (N={n})" for e, s, n in
                                                          zip(t.efficiency, t.binomial_error, t.denominator)])
        lines.append(t.pivot(index=["disk", "selection"], columns="family", values="text").to_string())
    lines += ["", "Diagnostics per disk: family-A y range; hits without plane crossing; multi-crossing primaries;",
              "first crossings off the plane annulus (must be 0); median |true point - mean silicon hit| (5% sample);",
              "max |plane z - z_plane|; median (min) |p_plane|/p_gen (5% sample);",
              "median denominator per occupied 2D bin inside the disk (nomargin);",
              "silicon-hit primaries whose true point is outside the active outline"]
    lines += ["", "Active-silicon outline per disk (areas in mm2): sensitive-box sum, union of both faces, filled outline:"]
    for disk in DISK_ORDER:
        lines.append(f"  {disk}: {geometry[disk]['active_stats']}")
    lines.append("")
    for disk in DISK_ORDER:
        c, g = counters[disk], geometry[disk]
        res, dzp, pr = c["true_minus_silicon_r_mm"], c["plane_dz_mm"], c["plane_p_over_gen_p"]
        centres = 0.5 * (xy_edges[1:] + xy_edges[:-1])
        xx, yy = np.meshgrid(centres, centres, indexing="ij")
        rr = np.hypot(xx, yy)
        inside = (rr < g["rmax"]) & (rr > g["r_in"])
        occupied = c["xy_den"][inside & (c["xy_den"] > 0)]
        lines.append(f"  {disk}: A={g['family_a_y']}, hit_without_plane={int(c['hit_without_plane'].sum())}, "
                     f"multi_crossing={c['multi_crossing']}, off_plane={c['first_crossing_off_plane']}, "
                     f"hits outside active outline={c['hit_reached_outside_active']}/{c['hit_reached']}, "
                     f"med|dr|={np.median(res) if len(res) else np.nan:.3f} mm, "
                     f"max|dz_plane|={np.max(np.abs(dzp)) if len(dzp) else np.nan:.4f} mm, "
                     f"med p_plane/p_gen={np.median(pr) if len(pr) else np.nan:.4f} "
                     f"(min {np.min(pr) if len(pr) else np.nan:.3f}), "
                     f"med 2D den={np.median(occupied) if len(occupied) else 0:.0f}, "
                     f"z_disk={g['z_disk']:g} (nominal {g['nominal_z']:g}), z_plane={g['z_plane']:g}")
    path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    args = parse_args()
    geometry = load_geometry(args)
    for g in geometry.values():
        g["inner_boundary"] = args.inner_boundary
    build_active_outlines(args, geometry)
    for disk in DISK_ORDER:
        print(f"active outline {disk}: {geometry[disk]['active_stats']}", flush=True)
    limit = 450.0
    n_bins = int(round(2 * limit / args.xy_bin_mm))
    if not np.isclose(n_bins * args.xy_bin_mm, 2 * limit):
        raise SystemExit("--xy-bin-mm must divide 900 mm")
    xy_edges = np.linspace(-limit, limit, n_bins + 1)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for vz in args.vertices:
        out = args.output_dir / f"vz_{VERTEX_LABELS[vz]}mm"
        if out.exists():
            raise FileExistsError(f"Refusing to overwrite {out}")
        counters, provenance = accumulate_vertex(args, geometry, vz, xy_edges)
        out.mkdir(parents=True)
        tables = build_tables(counters, geometry, vz, read_published(args, vz))
        names = ("integrated_efficiency", "efficiency_vs_p", "family_AB_efficiency",
                 "decomposition_vs_p", "comparison_straight_line")
        for name, table in zip(names, tables):
            table.to_csv(out / f"{name}.csv", index=False)
        arrays = {f"{disk}__{key}": value for disk, c in counters.items() for key, value in c.items()
                  if isinstance(value, np.ndarray)}
        np.savez_compressed(out / "histograms.npz", p_edges=P_EDGES, line_edges=LINE_EDGES, abs_edges=ABS_EDGES,
                            tan_edges=TAN_EDGES, xy_edges=xy_edges, selections=np.array(SELECTIONS),
                            metadata_json=np.asarray(json.dumps({
                                "vertex_z_mm": vz, "provenance": provenance, "args": {k: str(v) for k, v in vars(args).items()},
                                "geometry": {d: {k: (v if not isinstance(v, np.floating) else float(v))
                                                 for k, v in g.items() if k != "active_outline"}
                                             for d, g in geometry.items()}}, default=str)),
                            **arrays)
        write_summary(out / "summary.txt", args, vz, geometry, counters, provenance, tables, xy_edges)

        label = f"vz_{VERTEX_LABELS[vz]}mm"
        with PdfPages(out / f"refplane_efficiency_{label}.pdf") as pdf:
            fig = plot_overview(tables[0], vz)
            pdf.savefig(fig); fig.savefig(out / f"overview_{label}.png", dpi=130); plt.close(fig)
            for disk in DISK_ORDER:
                c, g = counters[disk], geometry[disk]
                for tag, fig in (("vs_p", plot_vs_p(disk, c, vz)),
                                 ("map_xy", plot_map(disk, c, g, xy_edges, vz, args.min_denominator_2d)),
                                 ("profiles", plot_profiles(disk, c, g, vz, args.min_denominator_1d))):
                    pdf.savefig(fig)
                    fig.savefig(out / f"{disk}_{tag}_{label}.png", dpi=130)
                    plt.close(fig)
        print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()
