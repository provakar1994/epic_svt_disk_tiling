#!/usr/bin/env python3
"""Per-disk material maps for the SVT endcap disks from ACTS Geant4 material tracks.

Input: the ROOT file written by scripts/material_map/material_recording_epic.py
(tree `material_tracks`, geantinos from the origin). Each Geant4 step carries its
position (mat_x, mat_y, mat_z, mm), step length (mm), X0 and L0 (mm).

Disk assignment of a step (all three cuts must pass):
  1. |mat_z - z_disk| < dz            (default dz = 5 mm = half of SiTrackerEndcapLayer_thickness)
  2. r_xy < r_max + r_margin           (disk outer radius from the tiling constants)
  3. outside both beampipe openings    (lepton and hadron circles, incl. 5 mm bake-out buffer)
Cut 3 removes the beam pipe, which sits inside the disk z window but in the hole.
Anything else inside the annulus at the disk z (e.g. disk-mounted services) IS counted.

Per track and disk:  t_disk = sum over assigned steps of step_length / X0   (same for L0).
Maps show the mean of t_disk over tracks in a bin, so tracks that pass through
tiling gaps contribute zeros (the map is a material budget, not a hit map).

x-y maps use the straight-line intersection of the geantino with the plane z = z_disk:
  r_int = z_disk / sinh(eta),  x = r_int cos(phi),  y = r_int sin(phi)
which is exact only for a vertex at the origin (checked at startup).
"""

import argparse
import json
from pathlib import Path

import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_pdf
import numpy as np
import uproot
from matplotlib import pyplot as plt


DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "material_map" / "step8m_20261020T164956Z_geant4_material_tracks.root"
BAKEOUT_BUFFER_MM = 5.0
# ACTS stores density in native units GeV/mm^3; 1 g/cm^3 = 5.60959e23 GeV / 1e3 mm^3
RHO_ACTS_PER_G_CM3 = 5.60959e20

# The ACTS tree stores only (effective Z, density) per step, not material names.
# Names below were matched by hand against compact/materials.xml and the materials used in
# src/SiEndcapModuleTracker_geo.cpp. Keys: (Z rounded to 0.01, rho in g/cm3 rounded to 0.001).
# "Silicon" includes active + inactive sensor and the LEC/REC placeholders (all the same material).
# "SVT_Endcap_Glue" is used for both the film and the external epoxy / adhesive.
MATERIAL_NAMES = {
    (6.00, 1.500): "CarbonFiber",
    (14.00, 2.330): "Silicon",
    (5.69, 1.180): "SVT_Endcap_Glue",
    (29.00, 8.960): "Copper",
    (13.00, 2.699): "Aluminum",
    (6.36, 1.430): "Kapton",
}
MAT_COLORS = ["dimgray", "royalblue", "gold", "darkorange", "forestgreen", "darkviolet", "indianred", "darkturquoise"]
OTHERS_COLOR = "silver"


def material_names(mz, mrho):
    """Name per step from (Z, rho); unknown materials get a 'Z=..,rho=..' label."""
    # integer keys (Z*100, rho*1000) avoid float-equality pitfalls after rounding
    keys = np.column_stack([np.rint(mz * 100.0), np.rint(mrho / RHO_ACTS_PER_G_CM3 * 1000.0)]).astype(np.int64)
    uk, inv = np.unique(keys, axis=0, return_inverse=True)
    name_by_key = {(int(round(zz * 100)), int(round(rho * 1000))): n for (zz, rho), n in MATERIAL_NAMES.items()}
    labels = np.array([name_by_key.get((int(zk), int(rk)), f"Z={zk / 100:.2f},rho={rk / 1000:.3f}") for zk, rk in uk])
    return labels[inv.ravel()]

# Disk table from compact/tracking/definitions_craterlake.xml (branch si_disk_hole, commit c5da03dcf).
# name, z_mm (module centre plane), r_max_mm, (lepton x_c, r), (hadron x_c, r); opening radii exclude the buffer.
# Names follow the project convention: disk IDs 0-9 = ED4 ... HD4 (HD3 is delivered as HD3b).
DISKS = [
    ("ED4", -1020.0, 430.0, (0.0, 33.500), (25.630340, 14.285)),
    ("ED3",  -850.0, 430.0, (0.0, 33.500), (21.379454, 14.285)),
    ("ED2",  -650.0, 430.0, (0.0, 31.757), (0.0, 31.757)),
    ("ED1",  -450.0, 405.0, (0.0, 31.757), (0.0, 31.757)),
    ("ED0",  -250.0, 230.0, (0.0, 31.757), (0.0, 31.757)),
    ("HD0",   250.0, 230.0, (0.0, 31.757), (0.0, 31.757)),
    ("HD1",   450.0, 405.0, (0.0, 31.757), (0.0, 31.757)),
    ("HD2",   700.0, 430.0, (0.0, 31.757), (-0.990167, 35.037842)),
    ("HD3",   950.0, 430.0, (0.0, 31.757), (-6.616117, 40.661072)),
    ("HD4",  1200.0, 430.0, (0.0, 31.757), (-12.242066, 46.284301)),
]

BRANCHES = ["v_x", "v_y", "v_z", "v_eta", "v_phi",
            "mat_x", "mat_y", "mat_z", "mat_step_length", "mat_X0", "mat_L0", "mat_Z", "mat_rho"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="ACTS material_tracks ROOT file")
    p.add_argument("--tree", default="material_tracks")
    p.add_argument("--output-dir", type=Path, default=Path("disk_material_map"))
    p.add_argument("--max-tracks", type=int, default=None, help="stop after this many tracks (default: all)")
    p.add_argument("--chunk", default="200 MB", help="uproot.iterate step size")
    p.add_argument("--disks", default="all", help="comma-separated disk names, e.g. HD1,HD2 (default: all)")
    p.add_argument("--dz-mm", type=float, default=5.0, help="half-width of the disk z window")
    p.add_argument("--r-margin-mm", type=float, default=2.0, help="margin added to the disk outer radius")
    p.add_argument("--eta-bins", type=int, default=100)
    p.add_argument("--phi-bins", type=int, default=180)
    p.add_argument("--xy-bin-mm", type=float, default=4.0, help="x-y map bin size at the disk plane")
    p.add_argument("--r-bin-mm", type=float, default=2.0, help="bin size of the azimuthally averaged X0(r) profile")
    p.add_argument("--zmax-percentile", type=float, default=99.5, help="colour scale upper limit percentile")
    return p.parse_args()


def disk_geometry(name, z, rmax, lep, had, r_margin):
    """Opening radii with buffer, eta range of the annulus, and plotting extents."""
    lep_r = lep[1] + BAKEOUT_BUFFER_MM
    had_r = had[1] + BAKEOUT_BUFFER_MM
    # smallest radius any disk material can have = closest point to the origin outside the union
    # of the two openings (found numerically: openings can be offset and need not contain the origin)
    phis = np.linspace(-np.pi, np.pi, 1441)
    rs = np.arange(0.0, rmax, 0.05)
    R, P = np.meshgrid(rs, phis)
    X, Y = R * np.cos(P), R * np.sin(P)
    outside = (np.hypot(X - lep[0], Y) > lep_r) & (np.hypot(X - had[0], Y) > had_r)
    r_hole_min = float(R[outside].min())
    sign = np.sign(z)
    eta_lo = np.arcsinh(abs(z) / (rmax + r_margin))
    eta_hi = np.arcsinh(abs(z) / r_hole_min)
    eta_range = (eta_lo, eta_hi) if sign > 0 else (-eta_hi, -eta_lo)
    return dict(name=name, z=z, rmax=rmax, lep_x=lep[0], lep_r=lep_r, had_x=had[0], had_r=had_r,
                eta_range=eta_range, rcut=rmax + r_margin)


def outside_openings(g, x, y):
    return (np.hypot(x - g["lep_x"], y) > g["lep_r"]) & (np.hypot(x - g["had_x"], y) > g["had_r"])


class DiskAccumulator:
    """Sums of per-track material and track counts on eta-phi, x-y and r grids."""

    def __init__(self, g, args):
        self.g = g
        self.eta_edges = np.linspace(*g["eta_range"], args.eta_bins + 1)
        self.phi_edges = np.linspace(-np.pi, np.pi, args.phi_bins + 1)
        half = np.ceil(g["rcut"] / args.xy_bin_mm) * args.xy_bin_mm
        self.xy_edges = np.arange(-half, half + 0.5 * args.xy_bin_mm, args.xy_bin_mm)
        self.r_edges = np.arange(0.0, g["rcut"] + args.r_bin_mm, args.r_bin_mm)
        shp_ep = (args.eta_bins, args.phi_bins)
        shp_xy = (len(self.xy_edges) - 1,) * 2
        self.ep = {k: np.zeros(shp_ep) for k in ("x0", "l0", "n")}
        self.xy = {k: np.zeros(shp_xy) for k in ("x0", "l0", "n")}
        self.r = {k: np.zeros(len(self.r_edges) - 1) for k in ("x0", "n")}
        # per-material X0 sums on the same grids; divided by the same track counts above,
        # so the per-material means add up exactly to the total map
        self.mat_ep, self.mat_xy, self.mat_r = {}, {}, {}
        self.mat_total = {}  # material name -> summed X0 over all tracks
        self.n_annulus = 0   # tracks whose plane intersection lies on the disk annulus
        self.x0_annulus = 0.0
        self.steps_used = 0

    def fill_materials(self, eta, phi, step_tidx, step_x0, step_names):
        """Fill per-material sums; each step is placed at its track's (eta, phi) / plane intersection."""
        g = self.g
        s_eta, s_phi = eta[step_tidx], phi[step_tidx]
        r_int = g["z"] / np.sinh(s_eta)  # positive: steps can only exist on tracks heading to this disk
        xi, yi = r_int * np.cos(s_phi), r_int * np.sin(s_phi)
        for name in np.unique(step_names):
            m = step_names == name
            w = step_x0[m]
            if name not in self.mat_total:
                self.mat_total[name] = 0.0
                self.mat_ep[name] = np.zeros_like(self.ep["x0"])
                self.mat_xy[name] = np.zeros_like(self.xy["x0"])
                self.mat_r[name] = np.zeros_like(self.r["x0"])
            self.mat_total[name] += float(w.sum())
            self.mat_ep[name] += np.histogram2d(s_eta[m], s_phi[m], bins=[self.eta_edges, self.phi_edges], weights=w)[0]
            self.mat_xy[name] += np.histogram2d(xi[m], yi[m], bins=[self.xy_edges, self.xy_edges], weights=w)[0]
            self.mat_r[name] += np.histogram(r_int[m], bins=self.r_edges, weights=w)[0]

    def materials_by_size(self):
        return sorted(self.mat_total, key=lambda k: -self.mat_total[k])

    def fill(self, eta, phi, t_x0, t_l0):
        g = self.g
        # eta-phi map
        for k, v in (("x0", t_x0), ("l0", t_l0), ("n", None)):
            h, _, _ = np.histogram2d(eta, phi, bins=[self.eta_edges, self.phi_edges], weights=v)
            self.ep[k] += h
        # straight-line intersection with the disk plane (only tracks heading toward this disk)
        same_side = np.sign(eta) == np.sign(g["z"])
        r_int = g["z"] / np.sinh(eta[same_side])
        xi, yi = r_int * np.cos(phi[same_side]), r_int * np.sin(phi[same_side])
        vx0, vl0 = t_x0[same_side], t_l0[same_side]
        for k, v in (("x0", vx0), ("l0", vl0), ("n", None)):
            h, _, _ = np.histogram2d(xi, yi, bins=[self.xy_edges, self.xy_edges], weights=v)
            self.xy[k] += h
        for k, v in (("x0", vx0), ("n", None)):
            h, _ = np.histogram(r_int, bins=self.r_edges, weights=v)
            self.r[k] += h
        on_disk = (r_int < g["rmax"]) & outside_openings(g, xi, yi)
        self.n_annulus += int(on_disk.sum())
        self.x0_annulus += float(vx0[on_disk].sum())


def mean_map(s, n):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, s / n, np.nan)


def process(args, accs):
    n_done = 0
    for chunk in uproot.iterate(f"{args.input}:{args.tree}", BRANCHES, step_size=args.chunk, library="ak"):
        if args.max_tracks is not None and n_done >= args.max_tracks:
            break
        if args.max_tracks is not None:
            chunk = chunk[: args.max_tracks - n_done]
        n_tr = len(chunk)
        # straight-line projection assumes geantinos start at the origin
        vmax = max(float(ak.max(abs(chunk[c]))) for c in ("v_x", "v_y", "v_z"))
        if vmax > 1e-6:
            raise RuntimeError(f"vertex not at origin (max |v| = {vmax} mm); x-y projection would be wrong")
        eta = chunk["v_eta"].to_numpy().astype(np.float64)
        phi = chunk["v_phi"].to_numpy().astype(np.float64)

        # flatten steps and remember the track index of each step
        counts = ak.num(chunk["mat_z"]).to_numpy()
        tidx = np.repeat(np.arange(n_tr), counts)
        x = ak.flatten(chunk["mat_x"]).to_numpy()
        y = ak.flatten(chunk["mat_y"]).to_numpy()
        z = ak.flatten(chunk["mat_z"]).to_numpy()
        sl = ak.flatten(chunk["mat_step_length"]).to_numpy()
        wx0 = sl / ak.flatten(chunk["mat_X0"]).to_numpy()
        wl0 = sl / ak.flatten(chunk["mat_L0"]).to_numpy()
        mz = ak.flatten(chunk["mat_Z"]).to_numpy()
        mrho = ak.flatten(chunk["mat_rho"]).to_numpy()

        # coarse preselection to the SVT disk region to keep the per-disk loops cheap
        pre = (np.abs(z) > 200.0) & (np.abs(z) < 1250.0) & (np.hypot(x, y) < 450.0)
        x, y, z, tidx, wx0, wl0, mz, mrho = (a[pre] for a in (x, y, z, tidx, wx0, wl0, mz, mrho))
        r = np.hypot(x, y)

        for acc in accs:
            g = acc.g
            sel = (np.abs(z - g["z"]) < args.dz_mm) & (r < g["rcut"]) & outside_openings(g, x, y)
            t_x0 = np.bincount(tidx[sel], weights=wx0[sel], minlength=n_tr)
            t_l0 = np.bincount(tidx[sel], weights=wl0[sel], minlength=n_tr)
            acc.steps_used += int(sel.sum())
            acc.fill(eta, phi, t_x0, t_l0)
            if sel.any():
                acc.fill_materials(eta, phi, tidx[sel], wx0[sel], material_names(mz[sel], mrho[sel]))
        n_done += n_tr
        print(f"processed {n_done} tracks", flush=True)
    return n_done


def draw_disk(pdf, acc, args):
    g = acc.g
    ep = mean_map(acc.ep["x0"], acc.ep["n"]) * 100.0
    xy = mean_map(acc.xy["x0"], acc.xy["n"]) * 100.0
    rp = mean_map(acc.r["x0"], acc.r["n"]) * 100.0
    vmax = np.nanpercentile(xy[xy > 0], args.zmax_percentile) if np.any(xy > 0) else 1.0
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("white")

    fig, axs = plt.subplots(1, 3, figsize=(21, 6.5), dpi=120, gridspec_kw={"width_ratios": [1.25, 1.0, 1.0]})
    fig.suptitle(f"{g['name']}  (z = {g['z']:.0f} mm, |dz| < {args.dz_mm:g} mm)   "
                 f"<x/X0> on annulus = {100 * acc.x0_annulus / max(acc.n_annulus, 1):.3f} %", fontsize=15)

    ax = axs[0]
    im = ax.pcolormesh(acc.phi_edges, acc.eta_edges, ep, cmap=cmap, vmin=0, vmax=vmax, shading="flat")
    ax.set_xlabel(r"$\phi$ [rad]"); ax.set_ylabel(r"$\eta$")
    fig.colorbar(im, ax=ax, label=r"$x/X_0$ [%]")

    ax = axs[1]
    im = ax.pcolormesh(acc.xy_edges, acc.xy_edges, xy.T, cmap=cmap, vmin=0, vmax=vmax, shading="flat")
    t = np.linspace(0, 2 * np.pi, 400)
    for xc, rc in ((g["lep_x"], g["lep_r"]), (g["had_x"], g["had_r"]), (0.0, g["rmax"])):
        ax.plot(xc + rc * np.cos(t), rc * np.sin(t), "r-", lw=0.6)
    ax.set_aspect("equal"); ax.set_xlabel("x at disk plane [mm]"); ax.set_ylabel("y [mm]")
    fig.colorbar(im, ax=ax, label=r"$x/X_0$ [%]")

    # stacked per-material X0(r); the stack top equals the total profile rp
    ax = axs[2]
    rc = 0.5 * (acc.r_edges[1:] + acc.r_edges[:-1])
    mats, colors = plot_materials(acc)
    bottom = np.zeros_like(rc)
    for name, col in zip(mats, colors):
        prof = np.nan_to_num(mean_map(stack_sum(acc.mat_r, name, mats), acc.r["n"]) * 100.0)
        ax.fill_between(rc, bottom, bottom + prof, step="mid", color=col, lw=0, label=name)
        bottom += prof
    ax.step(rc, np.nan_to_num(rp), where="mid", color="k", lw=0.6)
    ax.axvline(g["rmax"], color="r", lw=0.6, ls="--")
    ax.set_xlabel(r"$r$ at disk plane [mm]"); ax.set_ylabel(r"$\langle x/X_0 \rangle_\phi$ [%]")
    ax.set_xlim(0, g["rcut"]); ax.set_ylim(0, 1.25 * max(np.nanmax(rp), 1e-6)); ax.grid(ls=":")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    add_eta_axis(ax, g)
    fig.tight_layout()
    pdf.savefig(fig)
    fig.savefig(args.output_dir / f"disk_material_{g['name']}.png")
    plt.close(fig)

    draw_material_maps(pdf, acc, args, "xy")
    draw_material_maps(pdf, acc, args, "etaphi")


def plot_materials(acc, n_max=len(MAT_COLORS)):
    """Largest materials get their own colour; the rest are grouped into 'Others'."""
    mats = acc.materials_by_size()
    if len(mats) <= n_max:
        return mats, MAT_COLORS[: len(mats)]
    return mats[: n_max - 1] + ["Others"], MAT_COLORS[: n_max - 1] + [OTHERS_COLOR]


def stack_sum(store, name, shown):
    """Sum array for one material, or for every material not in `shown` when name == 'Others'."""
    if name != "Others":
        return store[name]
    return sum(v for k, v in store.items() if k not in shown)


def add_eta_axis(ax, g):
    """Secondary top axis: eta of a straight track from the origin hitting the disk at radius r."""
    sgn = np.sign(g["z"])
    r_of_eta = lambda e: np.abs(g["z"]) / np.sinh(np.clip(np.abs(e), 1e-3, None))
    eta_of_r = lambda r: sgn * np.arcsinh(np.abs(g["z"]) / np.clip(r, 1e-3, None))
    sec = ax.secondary_xaxis("top", functions=(eta_of_r, r_of_eta))
    # ticks only inside the disk eta range (the mapping diverges at r -> 0)
    lo, hi = sorted(np.abs(g["eta_range"]))
    ticks, last_r = [], np.inf
    for t in np.arange(np.ceil(lo * 4) / 4, hi + 1e-9, 0.25):  # increasing eta -> decreasing r
        r_t = r_of_eta(t)
        if last_r - r_t >= 0.06 * g["rcut"]:  # keep labels at least ~6 % of the axis apart
            ticks.append(t)
            last_r = r_t
    ticks = np.array(ticks)
    sec.set_xticks(sgn * ticks)
    sec.set_xticklabels([f"{sgn * t:.2f}" for t in ticks], fontsize=7)
    sec.set_xlabel(r"$\eta$")


def draw_material_maps(pdf, acc, args, kind):
    """One panel per material (largest first), each with its own colour scale."""
    g = acc.g
    mats, _ = plot_materials(acc, n_max=6)
    ncol = 3
    nrow = int(np.ceil(len(mats) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(6.5 * ncol, 5.5 * nrow), dpi=110, squeeze=False)
    tot = sum(acc.mat_total.values()) or 1.0
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("white")
    t = np.linspace(0, 2 * np.pi, 400)
    for ax, name in zip(axs.flat, mats):
        if kind == "xy":
            m = mean_map(stack_sum(acc.mat_xy, name, mats), acc.xy["n"]) * 100.0
            data, xe, ye = m.T, acc.xy_edges, acc.xy_edges
        else:
            m = mean_map(stack_sum(acc.mat_ep, name, mats), acc.ep["n"]) * 100.0
            data, xe, ye = m, acc.phi_edges, acc.eta_edges
        pos = data[np.isfinite(data) & (data > 0)]
        vmax = np.percentile(pos, args.zmax_percentile) if pos.size else 1.0
        im = ax.pcolormesh(xe, ye, data, cmap=cmap, vmin=0, vmax=vmax, shading="flat")
        share = sum(v for k, v in acc.mat_total.items() if k not in mats) if name == "Others" else acc.mat_total[name]
        ax.set_title(f"{name}  ({100 * share / tot:.1f} % of disk X0)", fontsize=11)
        if kind == "xy":
            for xc, rr in ((g["lep_x"], g["lep_r"]), (g["had_x"], g["had_r"]), (0.0, g["rmax"])):
                ax.plot(xc + rr * np.cos(t), rr * np.sin(t), "r-", lw=0.5)
            ax.set_aspect("equal"); ax.set_xlabel("x [mm]"); ax.set_ylabel("y [mm]")
        else:
            ax.set_xlabel(r"$\phi$ [rad]"); ax.set_ylabel(r"$\eta$")
        fig.colorbar(im, ax=ax, label=r"$x/X_0$ [%]")
    for ax in list(axs.flat)[len(mats):]:
        ax.axis("off")
    fig.suptitle(f"{g['name']} (z = {g['z']:.0f} mm): material breakdown, {'x-y at disk plane' if kind == 'xy' else 'eta-phi'}",
                 fontsize=14)
    fig.tight_layout()
    pdf.savefig(fig)
    fig.savefig(args.output_dir / f"disk_material_{g['name']}_materials_{kind}.png")
    plt.close(fig)


def write_outputs(accs, args, n_tracks):
    out = args.output_dir
    # numeric maps for later analysis (sum and count kept so maps can be merged / rebinned)
    for acc in accs:
        np.savez_compressed(
            out / f"disk_material_{acc.g['name']}.npz",
            eta_edges=acc.eta_edges, phi_edges=acc.phi_edges, xy_edges=acc.xy_edges, r_edges=acc.r_edges,
            ep_x0_sum=acc.ep["x0"], ep_l0_sum=acc.ep["l0"], ep_n=acc.ep["n"],
            xy_x0_sum=acc.xy["x0"], xy_l0_sum=acc.xy["l0"], xy_n=acc.xy["n"],
            r_x0_sum=acc.r["x0"], r_n=acc.r["n"],
            material_names=np.array(acc.materials_by_size()),
            **{f"mat_xy_x0_sum__{k}": v for k, v in acc.mat_xy.items()},
            **{f"mat_ep_x0_sum__{k}": v for k, v in acc.mat_ep.items()},
            **{f"mat_r_x0_sum__{k}": v for k, v in acc.mat_r.items()})
    with uproot.recreate(out / "disk_material_maps.root") as f:
        for acc in accs:
            n = acc.g["name"]
            f[f"{n}_etaphi_X0pct"] = (np.nan_to_num(mean_map(acc.ep["x0"], acc.ep["n"]) * 100), acc.eta_edges, acc.phi_edges)
            f[f"{n}_etaphi_L0pct"] = (np.nan_to_num(mean_map(acc.ep["l0"], acc.ep["n"]) * 100), acc.eta_edges, acc.phi_edges)
            f[f"{n}_xy_X0pct"] = (np.nan_to_num(mean_map(acc.xy["x0"], acc.xy["n"]) * 100), acc.xy_edges, acc.xy_edges)
            f[f"{n}_xy_ntracks"] = (acc.xy["n"], acc.xy_edges, acc.xy_edges)
            f[f"{n}_r_X0pct"] = (np.nan_to_num(mean_map(acc.r["x0"], acc.r["n"]) * 100), acc.r_edges)
            for mat in acc.materials_by_size():
                tag = mat.replace("=", "").replace(",", "_").replace(".", "p")
                f[f"{n}_{tag}_xy_X0pct"] = (np.nan_to_num(mean_map(acc.mat_xy[mat], acc.xy["n"]) * 100), acc.xy_edges, acc.xy_edges)
                f[f"{n}_{tag}_etaphi_X0pct"] = (np.nan_to_num(mean_map(acc.mat_ep[mat], acc.ep["n"]) * 100), acc.eta_edges, acc.phi_edges)
                f[f"{n}_{tag}_r_X0pct"] = (np.nan_to_num(mean_map(acc.mat_r[mat], acc.r["n"]) * 100), acc.r_edges)

    # text summary: mean budget per disk and material breakdown
    lines = [f"input: {args.input}", f"tracks: {n_tracks}", f"dz: {args.dz_mm} mm, r_margin: {args.r_margin_mm} mm",
             "", f"{'disk':5s} {'z[mm]':>8s} {'tracks_on_annulus':>18s} {'<x/X0>[%]':>10s} {'steps':>10s}"]
    summary = {}
    for acc in accs:
        g = acc.g
        mean = 100 * acc.x0_annulus / max(acc.n_annulus, 1)
        summary[g["name"]] = dict(z_mm=g["z"], tracks_on_annulus=acc.n_annulus, mean_x0_pct=mean)
        lines.append(f"{g['name']:5s} {g['z']:8.0f} {acc.n_annulus:18d} {mean:10.4f} {acc.steps_used:10d}")
    lines += ["", "material breakdown: share of the disk X0 and mean x/X0 on the annulus per material",
              "(names matched from (effective Z, density), see MATERIAL_NAMES in the script)"]
    for acc in accs:
        tot = sum(acc.mat_total.values()) or 1.0
        mean = 100 * acc.x0_annulus / max(acc.n_annulus, 1)
        lines.append(f"-- {acc.g['name']}")
        summary[acc.g["name"]]["materials"] = {}
        for name in acc.materials_by_size():
            share = acc.mat_total[name] / tot
            summary[acc.g["name"]]["materials"][name] = dict(share=share, mean_x0_pct=share * mean)
            lines.append(f"   {name:24s} {100 * share:6.2f} %   ~{share * mean:.4f} % X0")
    (out / "disk_material_summary.txt").write_text("\n".join(lines) + "\n")
    (out / "disk_material_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n".join(lines))


def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    wanted = None if args.disks == "all" else {d.strip() for d in args.disks.split(",")}
    geos = [disk_geometry(*d, args.r_margin_mm) for d in DISKS if wanted is None or d[0] in wanted]
    accs = [DiskAccumulator(g, args) for g in geos]
    n_tracks = process(args, accs)

    pdf = matplotlib.backends.backend_pdf.PdfPages(args.output_dir / "disk_material_maps.pdf")
    for acc in accs:
        draw_disk(pdf, acc, args)
    pdf.close()
    write_outputs(accs, args, n_tracks)


if __name__ == "__main__":
    main()
