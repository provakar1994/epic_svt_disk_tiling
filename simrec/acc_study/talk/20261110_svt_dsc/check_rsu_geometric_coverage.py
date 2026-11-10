#!/usr/bin/env python3
"""Check the talk claim: "the ~98% hit efficiency is primarily due to the
inactive regions built into the 12-tile structure of each RSU".

Inputs (read-only):
  geometry/active_silicon_rectangles.csv  every sensitive box of the built geometry
                                          (global EPIC coordinates, axis-aligned)
  extracted/acceptance_v3_refplanes/<config>/particles_*.npz  per-primary shards
                                          with the true reference-plane crossing
  results/refplane_efficiency_v4/vz_000mm/histograms.npz  per-disk geometry
                                          (z_disk, fid annulus) used by the
                                          published efficiency analysis

Per disk, for primaries that reached the reference plane (plane_mask bit) with
generated p in [0.5, 20.01) GeV and whose true point at z_disk lies in the fid
annulus (same definition as analyze_refplane_efficiency.py):
  true point: x_t = x_p + (z_disk - z_p) px/pz (straight, plane -> z_disk)
  (a) measured   : fraction with >= 1 silicon hit on the disk (hit_mask bit)
  (b) geom, true direction : the straight line along the plane momentum is
                   evaluated at each box's own z_center; hit if inside >= 1 box
  (c) geom, normal incidence: the true point (x_t, y_t) is tested against all
                   boxes projected along z (z offsets ignored)
  (c_area)       : same test for points uniform in area over the fid annulus
                   (pure layout coverage, no particle distribution)
  (d) split of the (c) misses (percentage points of the selected sample):
        intra-RSU  : inside an RSU bounding rectangle (between its 12 boxes:
                     tile gaps, x-half gap, central y gap)
        inter-RSU  : inside the RSU catalogue cell (bounding rectangle widened
                     in x by half the measured RSU-to-RSU gap on each side) but
                     not in the bounding rectangle, i.e. the RSU-to-RSU strip
        module/row : outside every RSU catalogue cell (between modules along a
                     row, between rows not covered by the overlap, row ends)
Run with run_check_rsu_geometric_coverage.sh (records the options).
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ACC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ACC))
from reduce_disk_acceptance import DISKS  # noqa: E402

DISK_ORDER = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
CONFIG = {"negative": "vz_000mm_eta_m3p8_to_m0p6", "positive": "vz_000mm_eta_p0p6_to_p3p8"}
P_LOW, P_HIGH = 0.5, 20.01           # same momentum window as the published analysis
TAN_BINS = [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.6), (0.6, 1.0)]
MEASURED_PUBLISHED = {"ED4": 98.31, "ED3": 98.25, "ED2": 98.04, "ED1": 97.57, "ED0": 97.42,
                      "HD0": 97.41, "HD1": 97.55, "HD2": 98.11, "HD3": 98.35, "HD4": 98.39}
PATH_RE = re.compile(r"^(?P<lyr>[^/]+)/(?P<mod>[^/]+)/component\d+_rsu(?P<rsu>\d+)_active_si_(?P<asi>\d+)/"
                     r"component\d+_rsu\d+_xhalf(?P<xh>\d+)_tile(?P<tile>\d+)_yhalf(?P<yh>\d+)_sensor_(?P<s>\d+)$")


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--active-csv", type=Path, default=ACC / "geometry/active_silicon_rectangles.csv")
    ap.add_argument("--extracted-root", type=Path, default=ACC / "extracted/acceptance_v3_refplanes")
    ap.add_argument("--geometry-npz", type=Path,
                    default=ACC / "results/refplane_efficiency_v4/vz_000mm/histograms.npz")
    ap.add_argument("--shards-per-side", type=int, default=4)
    ap.add_argument("--grid-mm", type=float, default=10.0, help="spatial-index cell size")
    ap.add_argument("--area-points", type=int, default=2_000_000)
    ap.add_argument("--output", type=Path, required=True)
    return ap.parse_args()


# ---------------------------------------------------------------- spatial index
class RectIndex:
    """Axis-aligned rectangles binned into a square grid; each point checks only
    the rectangles registered in its own cell (a rectangle is registered in every
    cell it overlaps, so the test is exact)."""

    def __init__(self, xmin, xmax, ymin, ymax, cell):
        self.r = np.column_stack([xmin, xmax, ymin, ymax]).astype(float)
        self.cell = cell
        self.x0 = np.floor(xmin.min() / cell) * cell - cell
        self.y0 = np.floor(ymin.min() / cell) * cell - cell
        self.nx = int(np.ceil((xmax.max() - self.x0) / cell)) + 2
        self.ny = int(np.ceil((ymax.max() - self.y0) / cell)) + 2
        lists = [[] for _ in range(self.nx * self.ny)]
        for k, (a, b, c, d) in enumerate(self.r):
            for ix in range(int((a - self.x0) // cell), int((b - self.x0) // cell) + 1):
                for iy in range(int((c - self.y0) // cell), int((d - self.y0) // cell) + 1):
                    lists[ix * self.ny + iy].append(k)
        kmax = max(len(v) for v in lists)
        self.table = np.full((len(lists), kmax), -1, dtype=np.int64)
        for c_id, v in enumerate(lists):
            self.table[c_id, :len(v)] = v

    def inside_any(self, x, y):
        out = np.zeros(len(x), bool)
        ix = np.floor((x - self.x0) / self.cell).astype(np.int64)
        iy = np.floor((y - self.y0) / self.cell).astype(np.int64)
        ok = np.isfinite(x) & np.isfinite(y) & (ix >= 0) & (ix < self.nx) & (iy >= 0) & (iy < self.ny)
        idx = np.flatnonzero(ok)
        cand = self.table[ix[idx] * self.ny + iy[idx]]          # (n, kmax)
        valid = cand >= 0
        rr = self.r[np.where(valid, cand, 0)]                   # (n, kmax, 4)
        xx, yy = x[idx, None], y[idx, None]
        hit = valid & (xx >= rr[..., 0]) & (xx < rr[..., 1]) & (yy >= rr[..., 2]) & (yy < rr[..., 3])
        out[idx] = hit.any(axis=1)
        return out


# ---------------------------------------------------------------- geometry
def load_boxes(path):
    d = pd.read_csv(path)
    e = d.path.str.extract(PATH_RE)
    if e.isna().any().any():
        raise ValueError("unparsed path(s) in active CSV")
    d = pd.concat([d, e], axis=1)
    xs = d[["x0_mm", "x1_mm", "x2_mm", "x3_mm"]].to_numpy()
    ys = d[["y0_mm", "y1_mm", "y2_mm", "y3_mm"]].to_numpy()
    d["xmin"], d["xmax"] = xs.min(axis=1), xs.max(axis=1)
    d["ymin"], d["ymax"] = ys.min(axis=1), ys.max(axis=1)
    return d


def rsu_table(d):
    """One row per RSU (disk, layer volume, module, rsu, active_si)."""
    g = d.groupby(["disk", "lyr", "mod", "rsu", "asi"], sort=False)
    s = g.agg(n_boxes=("s", "size"), n_tile_labels=("tile", "nunique"), n_xhalf=("xh", "nunique"),
              n_yhalf=("yh", "nunique"), xmin=("xmin", "min"), xmax=("xmax", "max"),
              ymin=("ymin", "min"), ymax=("ymax", "max"), z=("z_center_mm", "mean"),
              box_area=("half_x_mm", lambda v: 0.0)).reset_index()
    s["box_area"] = g.apply(lambda t: (4 * t.half_x_mm * t.half_y_mm).sum(), include_groups=False).values
    return s


def inter_rsu_gaps(rsus):
    """x gaps between neighbouring RSUs inside one module (same y range)."""
    gaps = []
    for _, m in rsus.groupby(["disk", "mod"]):
        m = m.sort_values("xmin")
        gaps.append(m.xmin.to_numpy()[1:] - m.xmax.to_numpy()[:-1])
    return np.concatenate(gaps)


def intra_rsu_gaps(d):
    """Unique x and y gaps between boxes inside one RSU (one example per disk is enough
    since all RSUs are identical copies; checked on all RSUs of ED0)."""
    xg, yg = set(), set()
    for _, t in d[d.disk == "ED0"].groupby(["mod", "rsu", "asi"]):
        xm = np.sort(np.unique(np.round(t.xmin, 4))); xM = np.sort(np.unique(np.round(t.xmax, 4)))
        ym = np.sort(np.unique(np.round(t.ymin, 4))); yM = np.sort(np.unique(np.round(t.ymax, 4)))
        xg.update(np.round(xm[1:] - xM[:-1], 4)); yg.update(np.round(ym[1:] - yM[:-1], 4))
    return sorted(xg), sorted(yg)


# ---------------------------------------------------------------- shards
def load_side(root, side, n_shards):
    files = sorted((root / CONFIG[side]).glob("particles_*.npz"))[:n_shards]
    keys = ["plane_mask", "hit_mask", "p_GeV", "plane_x_mm", "plane_y_mm", "plane_z_mm",
            "plane_px_GeV", "plane_py_GeV", "plane_pz_GeV"]
    parts = {k: [] for k in keys}
    for f in files:
        with np.load(f) as z:
            for k in keys:
                parts[k].append(z[k])
    return {k: np.concatenate(v) for k, v in parts.items()}, [f.name for f in files]


def frac(k, n):
    e = k / n
    return 100 * e, 100 * np.sqrt(e * (1 - e) / n)


def main():
    a = parse_args()
    lines = []
    out = lines.append
    rng = np.random.default_rng(12345)

    d = load_boxes(a.active_csv)
    rsus = rsu_table(d)
    meta = json.loads(str(np.load(a.geometry_npz, allow_pickle=True)["metadata_json"]))["geometry"]

    # ---------------- RSU structure from the path hierarchy
    out("RSU structure from geometry/active_silicon_rectangles.csv path hierarchy")
    out(f"  boxes: {len(d)}, RSUs: {len(rsus)}, modules: {rsus.groupby(['disk','mod']).ngroups}")
    out(f"  sensitive boxes per RSU: {rsus.n_boxes.value_counts().to_dict()}")
    out(f"  path labels per RSU: xhalf {sorted(d.xh.unique())} x tile {sorted(d.tile.unique())} "
        f"x yhalf {sorted(d.yh.unique())}  (= 2 x 3 x 2 = 12 sensitive boxes)")
    hx, hy = d.half_x_mm.unique(), d.half_y_mm.unique()
    out(f"  box size (all boxes): {2*hx[0]:.3f} x {2*hy[0]:.3f} mm (unique half sizes {hx}, {hy})")
    bx = (rsus.xmax - rsus.xmin).round(4).unique(); by = (rsus.ymax - rsus.ymin).round(4).unique()
    out(f"  RSU bounding rectangle: {bx} x {by} mm")
    xg, yg = intra_rsu_gaps(d)
    out(f"  gaps between boxes inside an RSU (ED0, all RSUs): x {xg} mm, y {yg} mm")
    g_inter = inter_rsu_gaps(rsus)
    gu, gc = np.unique(np.round(g_inter, 4), return_counts=True)
    out(f"  RSU-to-RSU x gaps inside modules: {dict(zip(gu.tolist(), gc.tolist()))} mm")
    gap_rsu = float(gu[np.argmax(gc)])
    rsu_pitch_x = float(bx[0]) + gap_rsu
    rsu_len_y = float(by[0])
    act_x = 6 * 2 * hx[0]; act_y = 2 * 2 * hy[0]
    out(f"  -> RSU catalogue cell = x pitch {rsu_pitch_x:.3f} mm (bbox + RSU gap) x y length {rsu_len_y:.3f} mm (bbox)")
    out(f"     sensitive per RSU: x {act_x:.3f} / {rsu_pitch_x:.3f} = {act_x/rsu_pitch_x:.5f};  "
        f"y {act_y:.3f} / {rsu_len_y:.3f} = {act_y/rsu_len_y:.5f}")
    inact = 1 - act_x * act_y / (rsu_pitch_x * rsu_len_y)
    out(f"     inactive fraction of the RSU cell = {100*inact:.4f} %  (x part {100*(1-act_x/rsu_pitch_x):.3f} %, "
        f"y part {100*(1-act_y/rsu_len_y):.3f} %)")
    out("  Per disk: box-area sum vs N_RSU x catalogue cell area")
    out(f"  {'disk':5s} {'N_RSU':>6s} {'box_area_mm2':>14s} {'N*cell_mm2':>14s} {'inactive_%':>10s}")
    for disk in DISK_ORDER:
        r = rsus[rsus.disk == disk]
        cell_area = len(r) * rsu_pitch_x * rsu_len_y
        out(f"  {disk:5s} {len(r):6d} {r.box_area.sum():14.1f} {cell_area:14.1f} {100*(1-r.box_area.sum()/cell_area):10.4f}")
    out("")

    # ---------------- per-disk coverage
    results = []
    shard_names = {}
    for side in ("negative", "positive"):
        s, shard_names[side] = load_side(a.extracted_root, side, a.shards_per_side)
        for i, (disk, _system, _layer, _z) in enumerate(DISKS[side]):
            g = meta[disk]
            assert g["index"] == i and g["side"] == side
            zd = g["z_disk"]
            fid_lo, fid_hi = g["fid"]
            bit = np.uint8(1 << i)
            reached = (s["plane_mask"] & bit) != 0
            hit = (s["hit_mask"] & bit) != 0
            p = s["p_GeV"].astype(float)
            xp, yp, zp = (s[f"plane_{c}_mm"][:, i].astype(float) for c in "xyz")
            px, py, pz = (s[f"plane_p{c}_GeV"][:, i].astype(float) for c in "xyz")
            with np.errstate(divide="ignore", invalid="ignore"):
                tx, ty = px / pz, py / pz
                xt, yt = xp + (zd - zp) * tx, yp + (zd - zp) * ty
            rt = np.hypot(xt, yt)
            sel = reached & (p >= P_LOW) & (p < P_HIGH) & (rt >= fid_lo) & (rt < fid_hi)
            n = int(sel.sum())
            xt, yt, xp, yp, zp, tx, ty, hit_s = xt[sel], yt[sel], xp[sel], yp[sel], zp[sel], tx[sel], ty[sel], hit[sel]

            b = d[d.disk == disk]
            # (c) normal incidence: all boxes projected along z
            idx_all = RectIndex(b.xmin.values, b.xmax.values, b.ymin.values, b.ymax.values, a.grid_mm)
            geo_c = idx_all.inside_any(xt, yt)
            # (b) true direction: evaluate the line at each box face z (4 discrete z per disk)
            geo_b = np.zeros(n, bool)
            for zc, bz in b.groupby("z_center_mm"):
                ix = RectIndex(bz.xmin.values, bz.xmax.values, bz.ymin.values, bz.ymax.values, a.grid_mm)
                geo_b |= ix.inside_any(xp + (zc - zp) * tx, yp + (zc - zp) * ty)
            # (d) split of (c) misses
            r = rsus[rsus.disk == disk]
            idx_rsu = RectIndex(r.xmin.values, r.xmax.values, r.ymin.values, r.ymax.values, a.grid_mm)
            idx_cell = RectIndex(r.xmin.values - gap_rsu / 2, r.xmax.values + gap_rsu / 2,
                                 r.ymin.values, r.ymax.values, a.grid_mm)
            miss = ~geo_c
            in_rsu = idx_rsu.inside_any(xt, yt)
            in_cell = idx_cell.inside_any(xt, yt)
            m_intra = miss & in_rsu
            m_inter = miss & ~in_rsu & in_cell
            m_mod = miss & ~in_cell
            # (c_area): uniform in area over the fid annulus
            u = rng.random(a.area_points)
            rr = np.sqrt(fid_lo**2 + u * (fid_hi**2 - fid_lo**2))
            ph = rng.uniform(0, 2 * np.pi, a.area_points)
            xa, ya = rr * np.cos(ph), rr * np.sin(ph)
            ca = idx_all.inside_any(xa, ya)
            ca_in_rsu = idx_rsu.inside_any(xa, ya)
            ca_in_cell = idx_cell.inside_any(xa, ya)

            tan_abs = np.hypot(tx, ty)
            # loss vs local incidence angle components (which direction opens gaps)
            tan_bins = []
            for name, t in (("|tan_x|", np.abs(tx)), ("|tan_y|", np.abs(ty))):
                for lo, hi in TAN_BINS:
                    m = (t >= lo) & (t < hi)
                    if m.sum() >= 1000:
                        tan_bins.append((name, lo, hi, int(m.sum()), 100 * (~geo_b[m]).mean(),
                                         100 * (~geo_c[m]).mean(), 100 * (~hit_s[m]).mean()))
            results.append(dict(
                disk=disk, n=n,
                a=frac(hit_s.sum(), n), b=frac(geo_b.sum(), n), c=frac(geo_c.sum(), n),
                c_area=frac(ca.sum(), a.area_points),
                d_intra=100 * m_intra.sum() / n, d_inter=100 * m_inter.sum() / n, d_mod=100 * m_mod.sum() / n,
                da_intra=100 * (~ca & ca_in_rsu).mean(), da_inter=100 * (~ca & ~ca_in_rsu & ca_in_cell).mean(),
                da_mod=100 * (~ca & ~ca_in_cell).mean(),
                hit_not_b=100 * (hit_s & ~geo_b).sum() / n, b_not_hit=100 * (~hit_s & geo_b).sum() / n,
                b_not_c=100 * (geo_b & ~geo_c).sum() / n, c_not_b=100 * (~geo_b & geo_c).sum() / n,
                tan_med=float(np.median(tan_abs)), tan_bins=tan_bins, fid=(fid_lo, fid_hi)))
            print(f"{disk}: n={n}", flush=True)

    out("Inputs: v_z = 0, shards per side = %d" % a.shards_per_side)
    for side in ("negative", "positive"):
        out(f"  {side}: {', '.join(shard_names[side])}")
    out(f"Selection: plane reached, generated p in [{P_LOW}, {P_HIGH}) GeV, true point at z_disk in fid annulus "
        f"(r about beam axis) from {a.geometry_npz.relative_to(ACC)}")
    out("")
    out("Efficiencies [%] (+- binomial stat. error). (a) measured silicon hit; (b) straight line along the")
    out("true direction tested at each box's own z; (c) normal incidence (all boxes projected along z);")
    out("(c_area) like (c) but points uniform in area over the fid annulus; pub = published v4 fid value (100 shards).")
    hdr = f"{'disk':5s} {'fid r [mm]':>14s} {'N':>7s} {'(a) meas':>13s} {'pub':>6s} {'(b) geo dir':>13s} {'(c) geo norm':>13s} {'(c_area)':>8s} {'med|tan|':>8s}"
    out(hdr)
    for r in results:
        out(f"{r['disk']:5s} {r['fid'][0]:6.1f}-{r['fid'][1]:6.1f} {r['n']:7d} "
            f"{r['a'][0]:6.2f}+-{r['a'][1]:4.2f} {MEASURED_PUBLISHED[r['disk']]:6.2f} "
            f"{r['b'][0]:6.2f}+-{r['b'][1]:4.2f} {r['c'][0]:6.2f}+-{r['c'][1]:4.2f} {r['c_area'][0]:8.2f} {r['tan_med']:8.3f}")
    out("")
    out("Losses [percentage points]: 1-(a), 1-(b), 1-(c); angle term (b)-(c); physics term (a)-(b)")
    out("(d) split of the normal-incidence loss 1-(c) [pp of the selected sample]; in brackets the same for c_area:")
    out(f"{'disk':5s} {'1-(a)':>6s} {'1-(b)':>6s} {'1-(c)':>6s} {'(b)-(c)':>8s} {'(a)-(b)':>8s} | "
        f"{'intra-RSU':>15s} {'RSU-RSU strip':>15s} {'module/row':>15s}")
    for r in results:
        out(f"{r['disk']:5s} {100-r['a'][0]:6.2f} {100-r['b'][0]:6.2f} {100-r['c'][0]:6.2f} "
            f"{r['b'][0]-r['c'][0]:+8.2f} {r['a'][0]-r['b'][0]:+8.2f} | "
            f"{r['d_intra']:6.2f} [{r['da_intra']:5.2f}] {r['d_inter']:6.2f} [{r['da_inter']:5.2f}] "
            f"{r['d_mod']:6.2f} [{r['da_mod']:5.2f}]")
    out("")
    out("Per-particle disagreement [% of selected]: hit but geo(b) miss, geo(b) hit but no hit; "
        "geo(b) hit & (c) miss, (c) hit & (b) miss")
    for r in results:
        out(f"{r['disk']:5s} hit&!b {r['hit_not_b']:5.2f}  b&!hit {r['b_not_hit']:5.2f}   "
            f"b&!c {r['b_not_c']:5.2f}  c&!b {r['c_not_b']:5.2f}")

    out("")
    out("Loss [pp] vs local slope at the plane (tan_x = px/pz, tan_y = py/pz; bins with >= 1000 particles):")
    out(f"{'disk':5s} {'slope':8s} {'bin':>10s} {'N':>7s} {'1-(a)':>6s} {'1-(b)':>6s} {'1-(c)':>6s}")
    for r in results:
        for name, lo, hi, nb, lb, lc, la in r["tan_bins"]:
            out(f"{r['disk']:5s} {name:8s} {lo:4.1f}-{hi:4.1f} {nb:7d} {la:6.2f} {lb:6.2f} {lc:6.2f}")

    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
