#!/usr/bin/env python3
"""dp/p vs p in the PWG eta regions, compared with the PWG requirement.

Input: one or more summary CSVs from endcap_tracking_performance.py, produced with
--eta-edges 1.0 2.5 3.0 3.5 (the endcap PWG regions). Each CSV is one dataset
(geometry/configuration) and is passed as LABEL=PATH.

Layout follows Shujie's tracking_single_particle_perf plots:
  top row    : -3.5<eta<-3.0, -3.0<eta<-2.5, -2.5<eta<-1.0   (backward)
  bottom row :  1.0<eta<2.5,   2.5<eta<3.0,   3.0<eta<3.5    (forward)
--quantity resol_qop plots the relative q/p resolution, which equals dp/p for small
resolutions and stays Gaussian for large ones (use it where dp/p > ~10%).
The barrel bin -1<eta<1 is not covered by the acceptance campaign (|eta| > 0.6 only).

PWG requirement (pwg_requirements.txt, preTDR v2.1 sec. 8.3.3):
  sigma_p/p [%] = sqrt((dp_par1 * p[GeV])^2 + dp_par2^2)
Points are drawn at the mean generated p of each momentum bin; the horizontal
bar shows the bin width (the campaign is flat in p, so each bin is a p range).

Usage:
  python plot_pwg_resolution.py --out FILE.png LABEL=summary.csv [LABEL2=summary2.csv ...]
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

# (side, |eta| lo, |eta| hi) in the panel order described above.
PANELS = [
    ("backward", 3.0, 3.5), ("backward", 2.5, 3.0), ("backward", 1.0, 2.5),
    ("forward", 1.0, 2.5), ("forward", 2.5, 3.0), ("forward", 3.0, 3.5),
]
MARKERS = ["o", "x", "s", "^", "v", "D"]
COLORS = ["tab:blue", "tab:red", "tab:green", "tab:orange", "tab:purple", "tab:brown"]


def load_pwg(path):
    return pd.read_csv(path, sep=r"\s+", comment="#")


def pwg_dp(pwg, eta, p):
    """PWG dp/p requirement [%] at signed eta (bin containing eta) and momentum p [GeV]."""
    row = pwg[(pwg["eta_lo"] <= eta) & (pwg["eta_hi"] > eta)].iloc[0]
    return np.sqrt((row["dp_par1"] * p) ** 2 + row["dp_par2"] ** 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("datasets", nargs="+", help="LABEL=summary.csv")
    parser.add_argument("--out", required=True)
    parser.add_argument("--quantity", default="resol_dp")
    parser.add_argument("--pwg-file", default=os.path.join(HERE, "pwg_requirements.txt"))
    parser.add_argument("--p-max", type=float, default=20.0)
    args = parser.parse_args()

    pwg = load_pwg(args.pwg_file)
    datasets = []
    for item in args.datasets:
        label, path = item.split("=", 1)
        summary = pd.read_csv(path)
        datasets.append((label, summary[summary["quantity"] == args.quantity]))

    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for ax, (side, a_lo, a_hi) in zip(axes.flat, PANELS):
        sign = -1 if side == "backward" else 1
        eta_lo, eta_hi = sorted((sign * a_lo, sign * a_hi))
        for k, (label, q) in enumerate(datasets):
            g = q[(q["side"] == side) & np.isclose(q["eta_lo"], a_lo) & np.isclose(q["eta_hi"], a_hi)]
            if g.empty:
                raise SystemExit(f"ERROR: {label} has no {side} bin {a_lo}<|eta|<{a_hi}; "
                                 "run endcap_tracking_performance.py with --eta-edges 1.0 2.5 3.0 3.5")
            g = g.sort_values("p_lo")
            xerr = [g["p_mean"] - g["p_lo"], g["p_hi"] - g["p_mean"]]
            ax.errorbar(g["p_mean"], g["sigma"], xerr=xerr, yerr=g["sigma_err"], ls="none",
                        marker=MARKERS[k % len(MARKERS)], ms=4, lw=0.8,
                        color=COLORS[k % len(COLORS)], label=label)
        if args.quantity in ("resol_dp", "resol_qop"):
            p_line = np.linspace(0, args.p_max, 200)
            ax.plot(p_line, pwg_dp(pwg, 0.5 * (eta_lo + eta_hi), p_line), "k--", label="PWG requirement")
        ax.text(0.05, 0.93, rf"{eta_lo:g}<$\eta$<{eta_hi:g}", transform=ax.transAxes, fontsize=13, va="top")
        ax.set_xlim(0, args.p_max)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("momentum [GeV/c]")
    ylabel = {"resol_dp": r"$\delta p/p$ [%]",
              "resol_qop": r"$\delta(q/p)/(q/p)$ [%]"}.get(args.quantity, args.quantity)
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel)
    axes[0, -1].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(args.out, dpi=130)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
