#!/usr/bin/env python3
"""Diagnose the forward tracking-efficiency dip near eta ~ 1.7 (acceptance_v1).

Three checks:
1. Efficiency vs (eta, phi) from the cached per-primary tables: is the dip
   uniform in phi (layer coverage) or localised (tiling/supports)?
2. Hit content per event for primaries in the dip, failed vs reconstructed.
   One pi+ per event and noise disabled in the campaign, so every rec hit belongs
   to the primary or its secondaries. Also counts CentralTrackSeeds per event
   (did seeding fail, or did the CKF fail after seeding?).
4. Efficiency vs which HD disks the primary really hit (truth, acceptance-study extraction).
3. Efficiency vs eta for vz = -100, 0, +100 mm. A structure at a fixed detector
   position (r0, z0) appears at the eta where vz + r0*cot(theta) = z0, so the
   dip moves with vz; the shift gives r0 and z0 (straight-line approximation).

Usage: python diagnose_forward_dip.py --outdir DIR
"""

import argparse
import glob
import os

import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import uproot

import endcap_tracking_performance as etp

V1 = "/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1"
V2 = "/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v2_vz100mm"
CACHE = "/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_acceptance_v1"
HIT_COLLECTIONS = ["SiBarrelVertexRecHits", "SiBarrelTrackerRecHits", "SiEndcapTrackerRecHits",
                   "MPGDBarrelRecHits", "OuterMPGDBarrelRecHits", "ForwardMPGDEndcapRecHits",
                   "TOFBarrelSharedRecHits", "TOFEndcapSharedRecHits"]
DIP = (1.60, 1.85)        # eta window of the dip (from the eta efficiency plot)
REFERENCE = (2.10, 2.40)  # nearby eta window with good efficiency
P_MIN = 2.0               # GeV; avoid the low-p turn-on


def load_cache(pattern):
    tables = []
    for path in sorted(glob.glob(os.path.join(CACHE, pattern))):
        with np.load(path) as data:
            tables.append(pd.DataFrame({k: data[k] for k in data.files}))
    return pd.concat(tables, ignore_index=True)


def check_eta_phi(outdir):
    df = load_cache("rec_vz_000mm_eta_p0p6_to_p3p8_chunk_*_n100000.npz")
    df = df[df["p_mc"] > P_MIN]
    eta_bins = np.arange(1.2, 2.41, 0.05)
    phi_bins = np.linspace(-np.pi, np.pi, 73)
    n_gen, _, _ = np.histogram2d(df["eta_mc"], df["phi_mc"], [eta_bins, phi_bins])
    n_rec, _, _ = np.histogram2d(df.loc[df["matched"], "eta_mc"], df.loc[df["matched"], "phi_mc"],
                                 [eta_bins, phi_bins])
    eff = np.divide(n_rec, n_gen, out=np.full_like(n_rec, np.nan), where=n_gen > 0)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    mesh = ax.pcolormesh(np.degrees(phi_bins), eta_bins, eff, vmin=0.4, vmax=1.0, cmap="viridis")
    fig.colorbar(mesh, ax=ax, label="efficiency")
    ax.set_xlabel(r"$\phi_{MC}$ [deg]")
    ax.set_ylabel(r"$\eta_{MC}$")
    ax.set_title(f"Forward efficiency, vz = 0, p > {P_MIN} GeV ({len(df)} primaries)")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "dip_eff_eta_phi.png"), dpi=130)
    plt.close(fig)

    # Phi uniformity in the dip: spread of the per-phi-bin efficiency vs binomial expectation.
    in_dip = (df["eta_mc"] > DIP[0]) & (df["eta_mc"] < DIP[1])
    g = df[in_dip].groupby(pd.cut(df.loc[in_dip, "phi_mc"], phi_bins), observed=False)["matched"]
    e, n = g.mean().to_numpy(), g.size().to_numpy()
    expected = np.sqrt(np.mean(e) * (1 - np.mean(e)) / np.mean(n))
    return (f"[1] dip window {DIP}, p > {P_MIN}: mean eff {np.mean(e):.3f}; per-5deg-phi-bin eff "
            f"min {e.min():.3f} max {e.max():.3f} rms {e.std():.4f} (binomial expectation {expected:.4f})")


def event_hits(path, n_events):
    """Per event: generated eta/p, matched flag, seeds, hit counts and hit (r, z) lists."""
    table, _ = etp.reduce_file(path, n_events)
    table = table.set_index("entry")
    branches = [f"{c}/{c}.position.{x}" for c in HIT_COLLECTIONS for x in "xyz"]
    branches.append("CentralTrackSeeds/CentralTrackSeeds.perigee.z")
    branches.append("CentralCKFTrajectories/CentralCKFTrajectories.nMeasurements")
    with uproot.open(path) as f:
        arrays = f["events"].arrays(branches, entry_stop=n_events)
    out = pd.DataFrame({"eta": table["eta_mc"], "p": table["p_mc"], "matched": table["matched"]})
    out["n_seeds"] = ak.to_numpy(ak.num(arrays["CentralTrackSeeds/CentralTrackSeeds.perigee.z"]))[out.index]
    hits = {}
    for c in HIT_COLLECTIONS:
        x = arrays[f"{c}/{c}.position.x"]
        out[c] = ak.to_numpy(ak.num(x))[out.index]
        hits[c] = (np.hypot(x, arrays[f"{c}/{c}.position.y"]), arrays[f"{c}/{c}.position.z"])
    return out, hits


def check_hits(outdir, n_events):
    path = os.path.join(V1, "vz_000mm_eta_p0p6_to_p3p8/rootfiles/rec_vz_000mm_eta_p0p6_to_p3p8_chunk_001_n100000.root")
    ev, hits = event_hits(path, n_events)
    ev = ev[ev["p"] > P_MIN]
    lines = [f"[2] hits per event, p > {P_MIN} GeV, file chunk_001 ({n_events} events)"]
    groups = {
        "dip, failed": ev[(ev.eta > DIP[0]) & (ev.eta < DIP[1]) & ~ev.matched],
        "dip, reconstructed": ev[(ev.eta > DIP[0]) & (ev.eta < DIP[1]) & ev.matched],
        "reference, reconstructed": ev[(ev.eta > REFERENCE[0]) & (ev.eta < REFERENCE[1]) & ev.matched],
    }
    header = f"{'group':26s} {'n':>6s} {'seeds>0':>8s} " + " ".join(f"{c[:14]:>14s}" for c in HIT_COLLECTIONS)
    lines.append(header)
    for name, g in groups.items():
        row = f"{name:26s} {len(g):6d} {np.mean(g.n_seeds > 0):8.3f} "
        row += " ".join(f"{g[c].mean():14.2f}" for c in HIT_COLLECTIONS)
        lines.append(row)

    # Where are the hits? (z, r) of all hits for each group, normalised per event.
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), sharey=True)
    for ax, (name, g) in zip(axes, groups.items()):
        rs, zs = [], []
        for c in HIT_COLLECTIONS:
            r, z = hits[c]
            rs.append(ak.to_numpy(ak.flatten(r[g.index.to_numpy()])))
            zs.append(ak.to_numpy(ak.flatten(z[g.index.to_numpy()])))
        rs, zs = np.concatenate(rs), np.concatenate(zs)
        w = np.full(len(rs), 1.0 / max(len(g), 1))
        h = ax.hist2d(zs, rs, bins=[np.linspace(0, 1900, 191), np.linspace(0, 800, 161)], weights=w,
                      cmin=1e-3, vmax=0.3)
        ax.set_title(f"{name} (n={len(g)})")
        ax.set_xlabel("z [mm]")
    axes[0].set_ylabel("r [mm]")
    fig.colorbar(h[3], ax=axes, label="hits per event per bin")
    fig.savefig(os.path.join(outdir, "dip_hits_zr.png"), dpi=130)
    plt.close(fig)
    return "\n".join(lines)


def check_vertex_shift(outdir, files_per_config):
    configs = [(-100, V2, "vz_m100mm_eta_p0p6_to_p3p8"), (0, V1, "vz_000mm_eta_p0p6_to_p3p8"),
               (100, V2, "vz_p100mm_eta_p0p6_to_p3p8")]
    bins = np.arange(1.0, 2.61, 0.025)
    centers = 0.5 * (bins[1:] + bins[:-1])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    lines = ["[3] dip position vs vertex z (minimum of efficiency in 1.4 < eta < 2.1, p > 2 GeV)"]
    minima = []
    for vz, campaign, config in configs:
        tables = []
        for path in sorted(glob.glob(os.path.join(campaign, config, "rootfiles", "rec_*.root")))[:files_per_config]:
            cache = os.path.join(CACHE, os.path.basename(path).replace(".root", ".npz"))
            if os.path.exists(cache):
                with np.load(cache) as data:
                    tables.append(pd.DataFrame({k: data[k] for k in data.files}))
            else:
                table, _ = etp.reduce_file(path)
                np.savez_compressed(cache, **{c: table[c].to_numpy() for c in table.columns})
                tables.append(table)
        df = pd.concat(tables, ignore_index=True)
        df = df[df["p_mc"] > P_MIN]
        n_gen, _ = np.histogram(df["eta_mc"], bins)
        n_rec, _ = np.histogram(df.loc[df["matched"], "eta_mc"], bins)
        eff = n_rec / np.maximum(n_gen, 1)
        ax.plot(centers, eff, drawstyle="steps-mid", label=f"vz = {vz:+d} mm")
        window = (centers > 1.4) & (centers < 2.1)
        eta_min = centers[window][np.argmin(eff[window])]
        minima.append((vz, eta_min))
        lines.append(f"  vz = {vz:+4d} mm: dip minimum at eta = {eta_min:.3f}, eff = {eff[window].min():.3f}")
    ax.set_xlabel(r"$\eta_{MC}$")
    ax.set_ylabel("efficiency")
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "dip_eff_vs_vz.png"), dpi=130)
    plt.close(fig)

    # Straight line from (0, vz) at polar angle theta(eta): z = vz + r*cot(theta), cot(theta) = sinh(eta).
    # Two vertex positions with the dip at eta1, eta2 -> r0 = (vz2 - vz1)/(sinh(eta1) - sinh(eta2)).
    (vz_a, eta_a), (vz_b, eta_b) = minima[0], minima[-1]
    if not np.isclose(eta_a, eta_b):
        r0 = (vz_b - vz_a) / (np.sinh(eta_a) - np.sinh(eta_b))
        z0 = vz_a + r0 * np.sinh(eta_a)
        lines.append(f"  straight-line estimate from vz = {vz_a:+d}/{vz_b:+d} mm: r0 = {r0:.0f} mm, z0 = {z0:.0f} mm")
    else:
        lines.append("  dip did not move with vz (not a fixed-position structure at finite r)")
    return "\n".join(lines)


def check_disk_hits(outdir, n_files):
    """Efficiency vs which HD disks the primary actually hit (Geant4 truth).

    Truth disk hits come from the acceptance study extraction (simrec/acc_study,
    extract_disk_particles.py): hit_mask bit i = disk HDi has >= 1 TrackerEndcapHit
    directly associated with the primary. Joined to the tracking table on
    (chunk, event entry, mc_index).
    """
    extracted = ("/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/simrec/acc_study/"
                 "extracted/acceptance_v1/vz_000mm_eta_p0p6_to_p3p8")
    rows = []
    for chunk in range(1, n_files + 1):
        tag = f"vz_000mm_eta_p0p6_to_p3p8_chunk_{chunk:03d}_n100000"
        with np.load(os.path.join(extracted, f"particles_{tag}.npz")) as d:
            truth = pd.DataFrame({"entry": d["event_entry"].astype(int), "mc_index": d["mc_index"].astype(int),
                                  "hit_mask": d["hit_mask"]})
        with np.load(os.path.join(CACHE, f"rec_{tag}.npz")) as d:
            trk = pd.DataFrame({k: d[k] for k in ["entry", "mc_index", "eta_mc", "phi_mc", "p_mc", "matched"]})
        rows.append(trk.merge(truth, on=["entry", "mc_index"], how="inner"))
    df = pd.concat(rows, ignore_index=True)
    df = df[df["p_mc"] > P_MIN]
    df["n_disks"] = [bin(m).count("1") for m in df["hit_mask"]]
    df["pattern"] = ["".join(str((m >> i) & 1) for i in range(5)) for m in df["hit_mask"]]  # HD0..HD4

    lines = [f"[4] efficiency vs truth HD-disk hits, p > {P_MIN} GeV, {n_files} files, "
             "pattern = hit flags HD0 HD1 HD2 HD3 HD4"]
    for name, (lo, hi) in [("dip", DIP), ("reference", REFERENCE), ("below dip", (1.35, 1.55))]:
        sel = df[(df["eta_mc"] > lo) & (df["eta_mc"] < hi)]
        lines.append(f"  {name} {lo}<eta<{hi}: n={len(sel)}, eff={sel['matched'].mean():.3f}")
        by_n = sel.groupby("n_disks")["matched"].agg(["size", "mean"])
        lines.append("    by number of disks hit: " +
                     ", ".join(f"{n}: {r['mean']:.3f} (n={int(r['size'])})" for n, r in by_n.iterrows()))
        by_p = sel.groupby("pattern")["matched"].agg(["size", "mean"]).sort_values("size", ascending=False)
        for pat, r in by_p.head(6).iterrows():
            lines.append(f"    pattern {pat}: fraction {r['size'] / len(sel):.3f}, eff {r['mean']:.3f}")

    # Fraction of primaries hitting HD3 / HD4 vs eta and phi in the dip region.
    eta_bins = np.arange(1.2, 2.41, 0.05)
    phi_bins = np.linspace(-np.pi, np.pi, 73)
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.2))
    for ax, (title, values) in zip(axes, [("n disks hit (mean)", df["n_disks"]),
                                         ("HD3 hit fraction", (df["hit_mask"].to_numpy().astype(int) >> 3) & 1),
                                         ("HD4 hit fraction", (df["hit_mask"].to_numpy().astype(int) >> 4) & 1)]):
        s, _, _ = np.histogram2d(df["eta_mc"], df["phi_mc"], [eta_bins, phi_bins], weights=values)
        n, _, _ = np.histogram2d(df["eta_mc"], df["phi_mc"], [eta_bins, phi_bins])
        mesh = ax.pcolormesh(np.degrees(phi_bins), eta_bins, s / np.maximum(n, 1), cmap="viridis")
        fig.colorbar(mesh, ax=ax)
        ax.set_title(title)
        ax.set_xlabel(r"$\phi_{MC}$ [deg]")
    axes[0].set_ylabel(r"$\eta_{MC}$")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "dip_truth_disk_hits_eta_phi.png"), dpi=130)
    plt.close(fig)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--hit-events", type=int, default=100000)
    parser.add_argument("--vz-files", type=int, default=5)
    parser.add_argument("--truth-files", type=int, default=10)
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    report = [check_eta_phi(args.outdir), check_hits(args.outdir, args.hit_events),
              check_vertex_shift(args.outdir, args.vz_files),
              check_disk_hits(args.outdir, args.truth_files)]
    text = "\n\n".join(report)
    print(text)
    with open(os.path.join(args.outdir, "diagnose_forward_dip.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
