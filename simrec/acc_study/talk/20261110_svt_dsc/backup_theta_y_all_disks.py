"""Backup slide: fid hit efficiency vs |tan(theta_y)| for every disk pair, and the share of
steep tracks per disk (v_z = 0). Replaces the table screenshot on draft page 23.

Input : results/refplane_efficiency_v4/vz_000mm/histograms.npz
        <DISK>__tany_num / <DISK>__tany_den, shape (n_selections, n_p_bins, n_tan_bins);
        tan(theta_y) = py/|pz| of the primary's momentum at the reference plane.
Steps : fid selection, sum over momentum (0.5-20 GeV), ED and HD of the same index summed
        (they agree within ~0.2 points), +/- tan bins folded into |tan|, merged to 0.10 bins
        (0.05 bins alias onto row gap / overlap positions), bins with den < MIN_DEN masked.
Right : share of fid tracks with |tan theta_y| >= 0.35 (theta_y >= ~19 deg) per disk pair.
Output: results/talk/20261110_svt_dsc/backup_theta_y_all_disks.{png,pdf}
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ACC = Path(__file__).resolve().parents[2]
NPZ = ACC / "results" / "refplane_efficiency_v4" / "vz_000mm" / "histograms.npz"
OUTDIR = ACC / "results" / "talk" / "20261110_svt_dsc"
MIN_DEN = 2000
REBIN = 2
STEEP = 0.35
PAIRS = [("D0", ("ED0", "HD0")), ("D1", ("ED1", "HD1")), ("D2", ("ED2", "HD2")),
         ("D3", ("ED3", "HD3")), ("D4", ("ED4", "HD4"))]
COLOURS = ["#D55E00", "#E69F00", "#009E73", "#56B4E9", "#0072B2"]


def folded(npz, disks, rebin=REBIN):
    """|tan| edges, num, den for the fid selection, summed over momentum and the given disks."""
    i_sel = list(npz["selections"]).index("fid")
    edges = npz["tan_edges"]
    num = sum(npz[f"{d}__tany_num"][i_sel].sum(axis=0) for d in disks)
    den = sum(npz[f"{d}__tany_den"][i_sel].sum(axis=0) for d in disks)
    half = len(num) // 2
    assert np.isclose(edges[half], 0.0)
    num_abs = (num[half:] + num[:half][::-1]).reshape(-1, rebin).sum(axis=1)
    den_abs = (den[half:] + den[:half][::-1]).reshape(-1, rebin).sum(axis=1)
    return edges[half:][::rebin], num_abs, den_abs


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    npz = np.load(NPZ)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 5.6), gridspec_kw={"width_ratios": [2.2, 1]})
    ax.axhline(98.0, color="red", ls="--", lw=1.5, label="expected 98%")
    ax.axvline(STEEP, color="0.4", ls=":", lw=1.5)
    shares = []
    print(f"{'pair':<4} share|tan|>={STEEP}  eff per 0.10 bin from 0")
    for (label, disks), colour in zip(PAIRS, COLOURS):
        edges, num, den = folded(npz, disks)
        centres = 0.5 * (edges[:-1] + edges[1:])
        with np.errstate(invalid="ignore", divide="ignore"):
            eff = 100 * num / den
        eff[den < MIN_DEN] = np.nan
        ax.plot(centres, eff, "-o", color=colour, lw=2, ms=5, label=label)
        # Share from the native 0.05 bins, so that 0.35 is a bin edge.
        fine_edges, _, fine_den = folded(npz, disks, rebin=1)
        assert np.isclose(fine_edges, STEEP).any()
        share = 100 * fine_den[fine_edges[:-1] >= STEEP - 1e-9].sum() / fine_den.sum()
        shares.append(share)
        print(f"{label:<4} {share:6.1f}%   " + " ".join(f"{e:5.1f}" if np.isfinite(e) else "  -  " for e in eff[:10]))
    ax.set_xlim(0, 0.8); ax.set_ylim(88, 100)   # D1 0.8-0.9 bin (72%) sits at the fid outer edge; not shown
    ax.set_xlabel(r"|tan $\theta_y$|  ($\theta_y$: angle projected onto the vertical y–z plane)", fontsize=12)
    ax.set_ylabel("Hit efficiency in fiducial annulus [%]", fontsize=13)
    top = ax.secondary_xaxis("top", functions=(lambda t: np.degrees(np.arctan(t)),
                                               lambda d: np.tan(np.radians(np.clip(d, 0, 89)))))
    top.set_xticks([0, 10, 20, 30, 40]); top.set_xlabel(r"$\theta_y$ [deg]", fontsize=12)
    ax.set_title("Same efficiency-vs-angle curve on every disk ($v_z$ = 0)", fontsize=14)
    ax.grid(color="#e5e5e5"); ax.set_axisbelow(True)
    ax.legend(fontsize=11, loc="lower left", ncol=2, frameon=False)
    ax.tick_params(labelsize=12)

    x = np.arange(len(PAIRS))
    bars = bx.bar(x, shares, color=COLOURS, edgecolor="black", lw=0.5)
    bx.bar_label(bars, labels=[f"{s:.0f}%" if s >= 1 else f"{s:.1f}%" for s in shares], fontsize=12, padding=2)
    bx.set_xticks(x, [p[0] for p in PAIRS]); bx.tick_params(labelsize=12)
    bx.set_ylabel(r"share of tracks with $\theta_y$ ≥ 19° [%]", fontsize=12)
    bx.set_ylim(0, max(shares) * 1.2)
    bx.set_title("Steep tracks per disk", fontsize=14)
    bx.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUTDIR / f"backup_theta_y_all_disks.{ext}", dpi=200, facecolor="white")
    print("wrote", OUTDIR / "backup_theta_y_all_disks.png")


if __name__ == "__main__":
    main()
