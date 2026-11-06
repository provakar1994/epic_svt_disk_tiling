#!/usr/bin/env python3
"""Endcap single-particle tracking performance from the SVT disk acceptance campaign.

Endcap version of plot_single_resol.ipynb, which works on one barrel file at a
single momentum. The campaign (simrec/acc_study/run_sim.sh) generates one pi+
per event, flat in eta inside 0.6 < |eta| < 3.8 and flat in p inside 0.5-20 GeV.
Momentum is continuous, so every result here is binned in (side, |eta|, p).

Steps
1. reduce: for each rec_*.root file, write one table row per generated primary
   (true kinematics + the best-matched CentralCKF track, if any), cached as .npz.
2. plot:   combine the tables and make
   - tracking efficiency vs eta and vs p,
   - Gaussian-core resolutions vs p per |eta| bin (dp/p, theta, phi, DCAr, DCAz),
   - pull widths vs p per |eta| bin,
   - a fit-check PDF with every fitted distribution,
   - summary CSV with one row per (side, |eta| bin, p bin, quantity).

Conventions (checked against edm4eic 8.10, used by eic_xl 26.09.0-stable)
- TrackParameters.covariance is a Cov6f in the ACTS basis [l0, l1, phi, theta, q/p, t],
  packed lower-triangular: diagonal (i,i) -> index i + i*(i+1)/2.
  So var(loc.a)=cov[0], var(loc.b)=cov[2], var(phi)=cov[5], var(theta)=cov[9], var(q/p)=cov[14].
- CentralCKFTrackParameters are at the perigee around the origin (0,0,0); units mm, rad, e/GeV.
  loc.a = signed transverse DCA (true value 0, since the gun sits at x=y=0),
  loc.b = z at the point of closest approach (true value = MC vertex z).
- Track index i in CentralCKFTracks equals entry i in CentralCKFTrackParameters
  (same assumption as the barrel notebook; the reduce step prints a check).
- Efficiency = primaries with >=1 associated CentralCKF track / generated primaries
  (generatorStatus == 1, charge != 0). If several tracks match one primary, the
  one with the highest association weight is used and the count is kept as n_assoc.
- q/p pull uses the signed q/p (the barrel notebook used |q/p|), so charge flips appear
  as outliers outside the Gaussian core instead of being folded back in.
"""

import argparse
import glob
import os
import re
import time

import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import uproot
from scipy.optimize import curve_fit

CAMPAIGN_DIR = "/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1"

TRACKS = "CentralCKFTracks"
PARAMS = "CentralCKFTrackParameters"
ASSOC = "CentralCKFTrackAssociations"

# Diagonal covariance indices in the packed Cov6f (see module docstring).
COV_INDEX = {"loc_a": 0, "loc_b": 2, "phi": 5, "theta": 9, "qop": 14}

# Quantities that are fitted in each (side, |eta|, p) bin: column, axis label, kind.
QUANTITIES = [
    ("resol_dp", "dp/p [%]", "resolution"),
    ("resol_qop", r"$\delta(q/p)/(q/p)$ [%]", "resolution"),
    ("resol_theta", r"$\Delta\theta$ [mrad]", "resolution"),
    ("resol_phi", r"$\Delta\phi$ [mrad]", "resolution"),
    ("resol_dcar", r"DCA$_r$ [$\mu$m]", "resolution"),
    ("resol_dcaz", r"DCA$_z$ - $v_z$ [$\mu$m]", "resolution"),
    ("pull_qop", "pull q/p", "pull"),
    ("pull_theta", r"pull $\theta$", "pull"),
    ("pull_phi", r"pull $\phi$", "pull"),
    ("pull_dcar", r"pull DCA$_r$", "pull"),
    ("pull_dcaz", r"pull DCA$_z$", "pull"),
]

# ePIC convention: electron beam goes to -z. Backward = eta < 0 = electron-going
# endcap (ED disks), forward = eta > 0 = hadron-going endcap (HD disks).
SIDES = [("backward", -1), ("forward", 1)]
SIDE_LABEL = {"backward": r"backward ($\eta<0$, e-going)", "forward": r"forward ($\eta>0$, h-going)"}


# ----------------------------------------------------------------------------
# Step 1: reduce one ROOT file to a per-primary table
# ----------------------------------------------------------------------------

def collection_ids(file):
    """Map collection name -> podio collection ID for the events tree."""
    info = file["podio_metadata"].arrays(
        ["events___CollectionTypeInfo.name", "events___CollectionTypeInfo.collectionID"],
        library="np", entry_stop=1)
    names = info["events___CollectionTypeInfo.name"][0]
    ids = info["events___CollectionTypeInfo.collectionID"][0]
    return {str(n): int(i) for n, i in zip(names, ids)}


def flatten(jagged):
    """Jagged per-event array -> (entry, local index, flat numpy values)."""
    counts = ak.to_numpy(ak.num(jagged, axis=1))
    entry = np.repeat(np.arange(len(counts)), counts)
    local = ak.to_numpy(ak.flatten(ak.local_index(jagged, axis=1)))
    values = ak.to_numpy(ak.flatten(jagged, axis=1))
    return entry, local, values


def branch(collection, field):
    return f"{collection}/{collection}.{field}"


def reduce_file(path, max_events=None):
    """Return a DataFrame with one row per generated charged primary."""
    with uproot.open(path) as file:
        ids = collection_ids(file)
        tree = file["events"]

        mc_fields = ["generatorStatus", "charge", "momentum.x", "momentum.y", "momentum.z",
                     "vertex.x", "vertex.y", "vertex.z"]
        par_fields = ["theta", "phi", "qOverP", "loc.a", "loc.b", "covariance.covariance[21]"]
        names = [branch("MCParticles", f) for f in mc_fields]
        names += [branch(PARAMS, f) for f in par_fields]
        names += [branch(TRACKS, f) for f in ["momentum.x", "momentum.y", "momentum.z", "chi2", "ndf"]]
        names += [branch(ASSOC, "weight")]
        names += [branch(f"_{ASSOC}_rec", f) for f in ["index", "collectionID"]]
        names += [branch(f"_{ASSOC}_sim", f) for f in ["index", "collectionID"]]
        arrays = tree.arrays(names, entry_stop=max_events)
    n_events = len(arrays)

    # --- generated primaries ---------------------------------------------
    entry, mc_index, status = flatten(arrays[branch("MCParticles", "generatorStatus")])
    mc = pd.DataFrame({"entry": entry, "mc_index": mc_index, "status": status})
    for f in mc_fields[1:]:
        mc[f] = flatten(arrays[branch("MCParticles", f)])[2]
    mc = mc[(mc["status"] == 1) & (mc["charge"] != 0)].copy()
    px, py, pz = mc["momentum.x"], mc["momentum.y"], mc["momentum.z"]
    mc["p_mc"] = np.sqrt(px**2 + py**2 + pz**2)
    mc["theta_mc"] = np.arccos(pz / mc["p_mc"])
    mc["phi_mc"] = np.arctan2(py, px)
    mc["eta_mc"] = -np.log(np.tan(mc["theta_mc"] / 2.0))
    mc["qop_mc"] = mc["charge"] / mc["p_mc"]
    mc = mc.rename(columns={"vertex.x": "vx_mc", "vertex.y": "vy_mc", "vertex.z": "vz_mc"})
    mc = mc[["entry", "mc_index", "p_mc", "theta_mc", "phi_mc", "eta_mc", "qop_mc",
             "vx_mc", "vy_mc", "vz_mc"]]

    # --- track parameters (index = track index in CentralCKFTracks) ------
    entry, trk_index, theta = flatten(arrays[branch(PARAMS, "theta")])
    trk = pd.DataFrame({"entry": entry, "track_index": trk_index, "theta_rec": theta})
    trk["phi_rec"] = flatten(arrays[branch(PARAMS, "phi")])[2]
    trk["qop_rec"] = flatten(arrays[branch(PARAMS, "qOverP")])[2]
    trk["loc_a"] = flatten(arrays[branch(PARAMS, "loc.a")])[2]
    trk["loc_b"] = flatten(arrays[branch(PARAMS, "loc.b")])[2]
    cov = flatten(arrays[branch(PARAMS, "covariance.covariance[21]")])[2]
    for name, k in COV_INDEX.items():
        trk[f"var_{name}"] = cov[:, k]
    trk["chi2"] = flatten(arrays[branch(TRACKS, "chi2")])[2]
    trk["ndf"] = flatten(arrays[branch(TRACKS, "ndf")])[2]

    # Check of the index-alignment assumption: Track momentum direction vs parameters.
    tpx = flatten(arrays[branch(TRACKS, "momentum.x")])[2]
    tpy = flatten(arrays[branch(TRACKS, "momentum.y")])[2]
    tpz = flatten(arrays[branch(TRACKS, "momentum.z")])[2]
    if len(tpx) == len(trk):
        theta_from_track = np.arctan2(np.hypot(tpx, tpy), tpz)
        align_frac = np.mean(np.abs(theta_from_track - trk["theta_rec"].to_numpy()) < 1e-3)
    else:
        align_frac = np.nan

    # --- associations: keep only CentralCKFTracks <-> MCParticles --------
    entry, _, rec_index = flatten(arrays[branch(f"_{ASSOC}_rec", "index")])
    assoc = pd.DataFrame({"entry": entry, "track_index": rec_index})
    assoc["rec_col"] = flatten(arrays[branch(f"_{ASSOC}_rec", "collectionID")])[2]
    assoc["mc_index"] = flatten(arrays[branch(f"_{ASSOC}_sim", "index")])[2]
    assoc["sim_col"] = flatten(arrays[branch(f"_{ASSOC}_sim", "collectionID")])[2]
    assoc["weight"] = flatten(arrays[branch(ASSOC, "weight")])[2]
    assoc = assoc[(assoc["rec_col"] == ids[TRACKS]) & (assoc["sim_col"] == ids["MCParticles"])]

    n_assoc = assoc.groupby(["entry", "mc_index"]).size().rename("n_assoc").reset_index()
    best = (assoc.sort_values("weight", ascending=False)
                 .drop_duplicates(["entry", "mc_index"])
                 [["entry", "mc_index", "track_index", "weight"]])

    # --- one row per primary, track columns NaN when not matched ---------
    df = mc.merge(n_assoc, on=["entry", "mc_index"], how="left")
    df["n_assoc"] = df["n_assoc"].fillna(0).astype(int)
    df = df.merge(best, on=["entry", "mc_index"], how="left")
    df = df.merge(trk, on=["entry", "track_index"], how="left")
    df["matched"] = df["n_assoc"] > 0

    stats = {"n_events": n_events, "n_primaries": len(mc), "n_tracks": len(trk),
             "n_matched": int(df["matched"].sum()), "index_alignment_fraction": align_frac}
    return df, stats


# ----------------------------------------------------------------------------
# Derived quantities and fitting
# ----------------------------------------------------------------------------

def add_derived_columns(df):
    """Residuals (rec - true) and pulls. Rows without a valid track get NaN."""
    good = df["matched"].copy()
    for name in COV_INDEX:
        good &= df[f"var_{name}"] > 0
    df["has_valid_track"] = good

    dphi = np.angle(np.exp(1j * (df["phi_rec"] - df["phi_mc"])))  # wrap to [-pi, pi]
    dtheta = df["theta_rec"] - df["theta_mc"]
    p_rec = 1.0 / np.abs(df["qop_rec"])
    dcaz = df["loc_b"] - df["vz_mc"]

    df["resol_dp"] = (p_rec - df["p_mc"]) / df["p_mc"] * 100.0      # %
    # Relative q/p residual: equals -dp/p to first order, but stays Gaussian when the
    # resolution is tens of percent (dp/p is then skewed because p = 1/(q/p)).
    df["resol_qop"] = (df["qop_rec"] - df["qop_mc"]) / df["qop_mc"] * 100.0  # %
    df["resol_theta"] = dtheta * 1e3                                 # mrad
    df["resol_phi"] = dphi * 1e3                                     # mrad
    df["resol_dcar"] = df["loc_a"] * 1e3                             # um, true DCAr = 0
    df["resol_dcaz"] = dcaz * 1e3                                    # um
    df["pull_qop"] = (df["qop_rec"] - df["qop_mc"]) / np.sqrt(df["var_qop"])
    df["pull_theta"] = dtheta / np.sqrt(df["var_theta"])
    df["pull_phi"] = dphi / np.sqrt(df["var_phi"])
    df["pull_dcar"] = df["loc_a"] / np.sqrt(df["var_loc_a"])
    df["pull_dcaz"] = dcaz / np.sqrt(df["var_loc_b"])

    derived = [q[0] for q in QUANTITIES]
    df.loc[~good, derived] = np.nan
    return df


def gaus(x, height, mean, sigma):
    return height * np.exp(-0.5 * ((x - mean) / sigma) ** 2)


def fit_gaussian_core(values, clip=3.0, max_iters=5, bins=101, min_entries=50):
    """Gaussian fit to the core of a distribution.

    Same algorithm as Shujie's epic_analysis_base.hist_gaus (2026-10-08 version),
    re-implemented here so this study does not import another user's editable file:
    1. robust centre/scale = median and 1.4826*MAD, iteratively recomputed using only
       values within centre +/- clip*scale;
    2. histogram the values inside centre +/- clip*scale with `bins` bins;
    3. unweighted least-squares Gaussian fit to the bin counts.
    Returns dict(mean, mean_err, sigma, sigma_err, n, lo, hi, density_peak), where
    density_peak = fitted peak in entries per unit x (for drawing at any binning).
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    result = dict(mean=np.nan, mean_err=np.nan, sigma=np.nan, sigma_err=np.nan,
                  n=len(values), lo=np.nan, hi=np.nan, density_peak=np.nan)
    if len(values) < min_entries:
        return result

    center = np.median(values)
    mad = np.median(np.abs(values - center))
    scale = 1.4826 * mad if mad > 0 else np.std(values)
    if not np.isfinite(scale) or scale <= 0:
        return result
    for _ in range(max_iters):
        clipped = values[np.abs(values - center) <= clip * scale]
        if len(clipped) < min_entries:
            break
        new_center = np.median(clipped)
        mad = np.median(np.abs(clipped - new_center))
        new_scale = 1.4826 * mad if mad > 0 else np.std(clipped)
        if not np.isfinite(new_scale) or new_scale <= 0:
            break
        converged = np.isclose(new_center, center) and np.isclose(new_scale, scale)
        center, scale = new_center, new_scale
        if converged:
            break

    lo, hi = center - clip * scale, center + clip * scale
    counts, edges = np.histogram(values, bins=bins, range=(lo, hi))
    centers = 0.5 * (edges[1:] + edges[:-1])
    bin_width = edges[1] - edges[0]
    try:
        popt, pcov = curve_fit(gaus, centers, counts, p0=[counts.max(), center, scale])
    except (RuntimeError, ValueError):
        return result
    if not np.all(np.isfinite(pcov)):
        return result
    result.update(mean=popt[1], mean_err=np.sqrt(pcov[1, 1]), sigma=abs(popt[2]),
                  sigma_err=np.sqrt(pcov[2, 2]), lo=lo, hi=hi,
                  density_peak=popt[0] / bin_width)
    return result


def efficiency_with_error(n_pass, n_total):
    """Efficiency and Wilson 68% half-width (stays non-zero at eff = 0 or 1)."""
    n_pass = np.asarray(n_pass, float)
    n_total = np.asarray(n_total, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        eff = np.where(n_total > 0, n_pass / n_total, np.nan)
        z2 = 1.0
        center = (n_pass + z2 / 2) / (n_total + z2)
        half = np.sqrt(n_pass * (n_total - n_pass) / n_total + z2 / 4) / (n_total + z2)
    lo = np.clip(center - half, 0, 1)
    hi = np.clip(center + half, 0, 1)
    return eff, eff - lo, hi - eff


# ----------------------------------------------------------------------------
# Step 2: plots and summary table
# ----------------------------------------------------------------------------

def bin_label(lo, hi):
    return f"{lo:g}-{hi:g}"


def plot_efficiency(df, eta_edges, p_edges, outdir, tag):
    # Efficiency vs signed eta, fine bins over the generated range.
    bins = np.arange(-4.0, 4.0001, 0.1)
    n_gen, edges = np.histogram(df["eta_mc"], bins=bins)
    n_rec, _ = np.histogram(df.loc[df["matched"], "eta_mc"], bins=bins)
    eff, err_lo, err_hi = efficiency_with_error(n_rec, n_gen)
    centers = 0.5 * (edges[1:] + edges[:-1])

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(8, 6), sharex=True,
                                         gridspec_kw={"height_ratios": [3, 2]})
    ax_top.hist(df["eta_mc"], bins=bins, histtype="step", color="black", label="Generated primaries")
    ax_top.hist(df.loc[df["matched"], "eta_mc"], bins=bins, histtype="step", color="tab:blue",
                label="with matched CKF track")
    ax_top.set_ylabel("Entries")
    ax_top.legend(frameon=False)
    ax_top.grid(True, alpha=0.3)
    ok = n_gen > 0
    ax_bot.errorbar(centers[ok], eff[ok], yerr=[err_lo[ok], err_hi[ok]], fmt="o", ms=3, color="tab:blue")
    ax_bot.axhline(1.0, color="gray", lw=1, ls="--")
    for edge in eta_edges:
        for sign in (-1, 1):
            ax_bot.axvline(sign * edge, color="gray", lw=0.5, ls=":")
    ax_bot.set_xlabel(r"$\eta_{MC}$")
    ax_bot.set_ylabel("Efficiency")
    ax_bot.set_ylim(0, 1.05)
    ax_bot.grid(True, alpha=0.3)
    fig.suptitle(f"Tracking efficiency, {tag}")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"efficiency_eta_{tag}.png"), dpi=130)
    plt.close(fig)

    # Efficiency vs p per |eta| bin, one panel per side.
    p_fine = np.geomspace(p_edges[0], p_edges[-1], 21)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, (side, sign) in zip(axes, SIDES):
        side_df = df[np.sign(df["eta_mc"]) == sign]
        abs_eta = np.abs(side_df["eta_mc"])
        for lo, hi in zip(eta_edges[:-1], eta_edges[1:]):
            sel = side_df[(abs_eta >= lo) & (abs_eta < hi)]
            n_gen, edges = np.histogram(sel["p_mc"], bins=p_fine)
            n_rec, _ = np.histogram(sel.loc[sel["matched"], "p_mc"], bins=p_fine)
            eff, err_lo, err_hi = efficiency_with_error(n_rec, n_gen)
            centers = np.sqrt(edges[1:] * edges[:-1])
            ax.errorbar(centers, eff, yerr=[err_lo, err_hi], fmt="o-", ms=3, lw=1,
                        label=rf"{lo:g} < |$\eta$| < {hi:g}")
        ax.set_xscale("log")
        ax.set_xlabel("p$_{MC}$ [GeV]")
        ax.set_title(SIDE_LABEL[side])
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("Efficiency")
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"efficiency_p_{tag}.png"), dpi=130)
    plt.close(fig)


def fit_all_bins(df, eta_edges, p_edges, outdir, tag):
    """Fit every quantity in every (side, |eta|, p) bin; write the fit-check PDF.

    Fit-check PDF: one page per (side, |eta| bin, quantity), one panel per p bin.
    Black = data over mean +/- 6 sigma (log y, so tails are visible),
    red = fitted Gaussian drawn over the fit window, dashed = the fit window.
    """
    rows = []
    pdf = PdfPages(os.path.join(outdir, f"fitcheck_{tag}.pdf"))
    p_bins = list(zip(p_edges[:-1], p_edges[1:]))
    n_cols = 5
    n_rows = int(np.ceil(len(p_bins) / n_cols))
    for side, sign in SIDES:
        side_all = df[np.sign(df["eta_mc"]) == sign]
        for eta_lo, eta_hi in zip(eta_edges[:-1], eta_edges[1:]):
            abs_eta = np.abs(side_all["eta_mc"])
            eta_all = side_all[(abs_eta >= eta_lo) & (abs_eta < eta_hi)]
            # Select each p bin once; reuse for all quantities.
            bin_data = []
            for p_lo, p_hi in p_bins:
                sel_all = eta_all[(eta_all["p_mc"] >= p_lo) & (eta_all["p_mc"] < p_hi)]
                sel = sel_all[sel_all["has_valid_track"]]
                n_matched = int(sel_all["matched"].sum())
                eff, e_lo, e_hi = efficiency_with_error(n_matched, len(sel_all))
                base = dict(side=side, eta_lo=eta_lo, eta_hi=eta_hi, p_lo=p_lo, p_hi=p_hi,
                            p_mean=sel_all["p_mc"].mean(), n_gen=len(sel_all), n_matched=n_matched,
                            efficiency=float(eff), eff_err_lo=float(e_lo), eff_err_hi=float(e_hi),
                            dup_fraction=float((sel_all["n_assoc"] > 1).sum() / max(n_matched, 1)))
                bin_data.append((base, sel))

            for col, label, kind in QUANTITIES:
                fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.2 * n_cols, 2.4 * n_rows), squeeze=False)
                for k, (base, sel) in enumerate(bin_data):
                    fit = fit_gaussian_core(sel[col])
                    rows.append({**base, "quantity": col, "kind": kind, **fit})
                    ax = axes.flat[k]
                    if np.isfinite(fit["sigma"]):
                        lo = fit["mean"] - 6 * fit["sigma"]
                        hi = fit["mean"] + 6 * fit["sigma"]
                        n_plot_bins = 72
                        width = (hi - lo) / n_plot_bins
                        ax.hist(sel[col], bins=n_plot_bins, range=(lo, hi), histtype="step", color="black")
                        x = np.linspace(fit["lo"], fit["hi"], 200)
                        ax.plot(x, gaus(x, fit["density_peak"] * width, fit["mean"], fit["sigma"]),
                                color="tab:red")
                        for edge in (fit["lo"], fit["hi"]):
                            ax.axvline(edge, color="tab:red", ls="--", lw=0.6)
                        ax.set_yscale("log")
                        ax.set_ylim(bottom=0.5)
                        ax.text(0.02, 0.97, f"$\\sigma$={fit['sigma']:.3g}\nn={fit['n']}",
                                transform=ax.transAxes, va="top", fontsize=7)
                    ax.set_title(f"p {bin_label(base['p_lo'], base['p_hi'])} GeV", fontsize=8)
                    ax.tick_params(labelsize=6)
                for ax in axes.flat[len(bin_data):]:
                    ax.axis("off")
                fig.suptitle(rf"{SIDE_LABEL[side]}: {eta_lo:g} < |$\eta$| < {eta_hi:g},  {label}  ({tag})")
                fig.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
    pdf.close()
    return pd.DataFrame(rows)


def plot_vs_p(summary, kind, outdir, tag):
    """Fitted sigma vs p, one line per |eta| bin, one row of panels per side."""
    quantities = [q for q in QUANTITIES if q[2] == kind]
    fig, axes = plt.subplots(2, len(quantities), figsize=(3.6 * len(quantities), 7), squeeze=False)
    for r, (side, _) in enumerate(SIDES):
        side_sum = summary[summary["side"] == side]
        for c, (col, label, _) in enumerate(quantities):
            ax = axes[r, c]
            q = side_sum[side_sum["quantity"] == col]
            for (eta_lo, eta_hi), g in q.groupby(["eta_lo", "eta_hi"]):
                ax.errorbar(g["p_mean"], g["sigma"], yerr=g["sigma_err"], fmt="o-", ms=3, lw=1,
                            label=rf"{eta_lo:g}<|$\eta$|<{eta_hi:g}")
            ax.set_xscale("log")
            if kind == "pull":
                ax.axhline(1.0, color="gray", ls="--", lw=1)
                ax.set_ylim(0, 2)
            else:
                ax.set_ylim(bottom=0)
            ax.set_title(f"{SIDE_LABEL[side]}: {label}", fontsize=9)
            ax.set_xlabel("p$_{MC}$ [GeV]")
            ax.set_ylabel(r"$\sigma$ (Gaussian core)")
            ax.grid(True, alpha=0.3)
    axes[0, -1].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"{kind}_vs_p_{tag}.png"), dpi=130)
    plt.close(fig)


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def select_files(campaign_dir, configs, files_per_config):
    files = []
    for config in configs:
        found = sorted(glob.glob(os.path.join(campaign_dir, config, "rootfiles", "rec_*.root")))
        if not found:
            raise SystemExit(f"ERROR: no rec_*.root files for configuration {config} in {campaign_dir}")
        files += [(config, f) for f in found[:files_per_config]]
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign-dir", default=CAMPAIGN_DIR)
    parser.add_argument("--configs", nargs="+",
                        default=["vz_000mm_eta_m3p8_to_m0p6", "vz_000mm_eta_p0p6_to_p3p8"],
                        help="campaign sub-directories to use")
    parser.add_argument("--files-per-config", type=int, default=5)
    parser.add_argument("--max-events", type=int, default=None, help="per file (for quick tests)")
    parser.add_argument("--reduced-dir", required=True, help="cache for per-file .npz tables")
    parser.add_argument("--outdir", required=True, help="plots and summary CSV")
    parser.add_argument("--tag", default="endcap")
    parser.add_argument("--eta-edges", type=float, nargs="+", default=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
                        help="|eta| bin edges")
    parser.add_argument("--p-edges", type=float, nargs="+", default=[0.5, 1.0] + [float(p) for p in range(2, 21)],
                        help="momentum bin edges [GeV]")
    args = parser.parse_args()
    os.makedirs(args.reduced_dir, exist_ok=True)
    os.makedirs(args.outdir, exist_ok=True)

    # Step 1: reduce (cached; delete nothing, reuse what exists).
    tables = []
    for config, path in select_files(args.campaign_dir, args.configs, args.files_per_config):
        stem = os.path.basename(path).replace(".root", "")
        suffix = f"_n{args.max_events}" if args.max_events else ""
        cache = os.path.join(args.reduced_dir, f"{stem}{suffix}.npz")
        if os.path.exists(cache):
            with np.load(cache) as data:
                table = pd.DataFrame({k: data[k] for k in data.files})
            print(f"[cache] {cache}: {len(table)} primaries")
        else:
            start = time.time()
            table, stats = reduce_file(path, args.max_events)
            np.savez_compressed(cache, **{c: table[c].to_numpy() for c in table.columns})
            print(f"[reduce] {stem}: {stats}  ({time.time() - start:.0f} s)")
        table["config"] = config
        table["chunk"] = int(re.search(r"chunk_(\d+)", stem).group(1))
        tables.append(table)
    df = add_derived_columns(pd.concat(tables, ignore_index=True))

    print(f"Total primaries: {len(df)}, matched: {df['matched'].sum()}, "
          f"valid track params: {df['has_valid_track'].sum()}, "
          f"primaries with >1 matched track: {(df['n_assoc'] > 1).sum()}")

    # Step 2: plots and summary.
    plot_efficiency(df, args.eta_edges, args.p_edges, args.outdir, args.tag)
    summary = fit_all_bins(df, args.eta_edges, args.p_edges, args.outdir, args.tag)
    summary_path = os.path.join(args.outdir, f"summary_{args.tag}.csv")
    summary.to_csv(summary_path, index=False, float_format="%.6g")
    plot_vs_p(summary, "resolution", args.outdir, args.tag)
    plot_vs_p(summary, "pull", args.outdir, args.tag)
    print(f"Wrote plots and {summary_path}")


if __name__ == "__main__":
    main()
