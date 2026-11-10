"""Slide 4: fiducial hit efficiency vs |tan(theta_y)| at the disk.

Input : results/refplane_efficiency_v4/vz_{m100,000,p100}mm/histograms.npz
        <DISK>__tany_num / <DISK>__tany_den, shape (n_selections, n_p_bins, n_tan_bins).
        tan(theta_y) = py/|pz| of the primary's local momentum at the reference plane.
Steps : take the "fid" selection, sum over all momentum bins (0.5-20 GeV),
        fold +/- tan bins into |tan| (sum num and den of mirror bins),
        optionally merge REBIN adjacent |tan| bins, mask bins with den < MIN_DEN,
        efficiency = num/den with binomial error sqrt(e(1-e)/den).
Why rebin: for the disk 15 cm from a displaced vertex, tan_y ~ y/L for straight-ish
        tracks, so 0.05-wide tan bins alias onto alternating row-overlap / row-gap
        positions in y and produce a sawtooth. Merging pairs (0.10 bins) removes it.
        Both versions are written (main = 0.10 bins, backup "_fine" = 0.05 bins).
Output: results/talk/20261110_svt_dsc/slide4_incidence_angle{,_fine}.{png,pdf}
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ACC = Path(__file__).resolve().parents[2]
RESULTS = ACC / "results" / "refplane_efficiency_v4"
OUTDIR = ACC / "results" / "talk" / "20261110_svt_dsc"

SELECTION = "fid"
MIN_DEN = 2000
DISKS = {"HD0": ("-", "o"), "HD1": ("--", "s")}          # disk -> (linestyle, marker)
DISK_Z_MM = {"ED0": -250, "ED1": -450, "HD0": 250, "HD1": 450}
VERTICES = [("m100", -100, "#0072B2"), ("000", 0, "#555555"), ("p100", 100, "#D55E00")]
ONSET_BAND = (0.35, 0.40)   # first bins below the flat ~98.5% plateau (0.05 binning)
PRINT_AT = [0.1, 0.3, 0.5, 0.7]


def folded_efficiency(npz, disk, rebin):
    """Return |tan| bin edges, efficiency, error, den (fid, summed over momentum)."""
    i_sel = list(npz["selections"]).index(SELECTION)
    edges = npz["tan_edges"]
    num = npz[f"{disk}__tany_num"][i_sel].sum(axis=0)
    den = npz[f"{disk}__tany_den"][i_sel].sum(axis=0)
    n_half = len(num) // 2
    assert np.isclose(edges[n_half], 0.0), "tan bins must be symmetric about 0"
    # mirror bin of +k is the k-th bin counted backwards from 0
    num_abs = num[n_half:] + num[:n_half][::-1]
    den_abs = den[n_half:] + den[:n_half][::-1]
    abs_edges = edges[n_half:]
    if rebin > 1:
        num_abs = num_abs.reshape(-1, rebin).sum(axis=1)
        den_abs = den_abs.reshape(-1, rebin).sum(axis=1)
        abs_edges = abs_edges[::rebin]
    with np.errstate(invalid="ignore", divide="ignore"):
        eff = num_abs / den_abs
        err = np.sqrt(eff * (1 - eff) / den_abs)
    bad = den_abs < MIN_DEN
    eff[bad] = np.nan
    err[bad] = np.nan
    return abs_edges, 100 * eff, 100 * err, den_abs


def make_plot(rebin, suffix):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.axvspan(*ONSET_BAND, color="#f2c94c", alpha=0.25, lw=0, zorder=0)
    ax.text(ONSET_BAND[1] + 0.01, 99.4, "onset of row-gap losses (19°–22°)",
            ha="left", va="center", fontsize=12, color="#7a5c00")
    ax.axhline(98.0, color="red", ls="--", lw=1.5, label="expected 98%", zorder=1)

    print(f"\n=== rebin={rebin} (bin width {0.05 * rebin:.2f}), selection={SELECTION} ===")
    print(f"{'curve':<22} {'L[mm]':>5} " + " ".join(f"{'@' + str(t):>7}" for t in PRINT_AT))
    for tag, vz_mm, colour in VERTICES:
        npz = np.load(RESULTS / f"vz_{tag}mm" / "histograms.npz")
        for disk, (ls, marker) in DISKS.items():
            edges, eff, err, den = folded_efficiency(npz, disk, rebin)
            centres = 0.5 * (edges[:-1] + edges[1:])
            dist_cm = abs(DISK_Z_MM[disk] - vz_mm) / 10
            vz_label = f"{vz_mm / 10:+.0f}".replace("+0", "0")
            ax.errorbar(centres, eff, yerr=err, color=colour, ls=ls, marker=marker, ms=6,
                        lw=1.8, capsize=0, mfc=colour if ls == "-" else "white",
                        label=f"{disk}, $v_z$ = {vz_label} cm  ({dist_cm:.0f} cm away)")
            vals = [eff[np.searchsorted(edges, t, side="right") - 1] for t in PRINT_AT]
            print(f"{disk + ' vz=' + vz_label + 'cm':<22} {abs(DISK_Z_MM[disk] - vz_mm):5d} "
                  + " ".join(f"{v:7.2f}" if np.isfinite(v) else "      -" for v in vals))

    # |tan| > 1.0 is not shown: only the 15 cm curve reaches it, at the fid outer edge
    ax.set_xlim(0, 1.0)
    ax.set_ylim(84 if rebin > 1 else 74, 100)
    ax.set_xlabel(r"|tan $\theta_y$|   ($\theta_y$: incidence angle projected onto the vertical y–z plane)",
                  fontsize=13)
    # Same axis in degrees on top (theta_y = atan |tan theta_y|).
    top = ax.secondary_xaxis("top", functions=(lambda t: np.degrees(np.arctan(t)),
                                               lambda d: np.tan(np.radians(np.clip(d, 0, 89)))))
    top.set_xticks([0, 10, 20, 30, 40])
    top.set_xlabel(r"$\theta_y$ [deg]", fontsize=13)
    top.tick_params(labelsize=12)
    ax.set_ylabel("Hit efficiency in fiducial annulus [%]", fontsize=14)
    ax.tick_params(labelsize=13)
    ax.grid(color="#e5e5e5", lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    title = r"Row overlap stops covering the gap above $\theta_y$ ≈ 19° (|tan $\theta_y$| ≈ 0.35)"
    if rebin == 1:
        title = r"0.05 bins: 15 cm disk aliases row gaps (y ≈ L tan $\theta_y$)"
    ax.set_title(title, fontsize=16)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), fontsize=11, ncol=3,
              frameon=False, columnspacing=1.2, handlelength=2.5)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUTDIR / f"slide4_incidence_angle{suffix}.{ext}", dpi=200,
                    facecolor="white")
    print("wrote", OUTDIR / f"slide4_incidence_angle{suffix}.png")


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    make_plot(rebin=2, suffix="")
    make_plot(rebin=1, suffix="_fine")


if __name__ == "__main__":
    main()
