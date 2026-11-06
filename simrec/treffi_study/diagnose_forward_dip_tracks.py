#!/usr/bin/env python3
"""Forward dip, check 5: what happened to the primary and the CKF in failed events.

For primaries with p > 2 GeV in the dip (1.6 < eta < 1.85) and in two reference
windows, compare matched vs failed events:
- number of CentralCKFTracks in the event (0 = CKF produced nothing);
- number of MCParticles in the event (secondaries => interaction);
- where the primary ended (MCParticles.endpoint), i.e. where Geant4 stopped it.

Usage: python diagnose_forward_dip_tracks.py [ROOT_FILE] > report.txt
"""

import sys

import awkward as ak
import numpy as np
import uproot

import endcap_tracking_performance as etp

DEFAULT = ("/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1/vz_000mm_eta_p0p6_to_p3p8/"
           "rootfiles/rec_vz_000mm_eta_p0p6_to_p3p8_chunk_001_n100000.root")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    table, _ = etp.reduce_file(path)
    with uproot.open(path) as f:
        a = f["events"].arrays(["CentralCKFTracks/CentralCKFTracks.chi2", "MCParticles/MCParticles.PDG",
                                "MCParticles/MCParticles.endpoint.x", "MCParticles/MCParticles.endpoint.y",
                                "MCParticles/MCParticles.endpoint.z"])
    table = table[table["mc_index"] == 0].set_index("entry")  # the gun primary is MCParticles[0]
    idx = table.index.to_numpy()
    table["n_tracks"] = ak.to_numpy(ak.num(a["CentralCKFTracks/CentralCKFTracks.chi2"]))[idx]
    table["n_mc"] = ak.to_numpy(ak.num(a["MCParticles/MCParticles.PDG"]))[idx]
    ex = ak.to_numpy(a["MCParticles/MCParticles.endpoint.x"][:, 0])
    ey = ak.to_numpy(a["MCParticles/MCParticles.endpoint.y"][:, 0])
    table["end_r"] = np.hypot(ex, ey)[idx]
    table["end_z"] = ak.to_numpy(a["MCParticles/MCParticles.endpoint.z"][:, 0])[idx]

    print(f"File: {path}\np > 2 GeV; primary = MCParticles[0]\n")
    for name, (lo, hi) in [("dip", (1.6, 1.85)), ("reference", (2.1, 2.4)), ("below dip", (1.35, 1.55))]:
        sel = table[(table["eta_mc"] > lo) & (table["eta_mc"] < hi) & (table["p_mc"] > 2)]
        for matched in (True, False):
            g = sel[sel["matched"] == matched]
            if g.empty:
                continue
            counts = np.bincount(g["n_tracks"], minlength=3)
            print(f"{name:9s} {lo}-{hi} matched={matched!s:5s} n={len(g):5d}  "
                  f"tracks/event 0:{counts[0]} 1:{counts[1]} >=2:{counts[2:].sum()}  "
                  f"median nMC {g['n_mc'].median():.0f}  "
                  f"primary end: median z {g['end_z'].median():.0f} mm, r {g['end_r'].median():.0f} mm; "
                  f"fraction ending at z < 1300 mm: {np.mean(g['end_z'] < 1300):.3f}")
    failed = table[(table["eta_mc"] > 1.6) & (table["eta_mc"] < 1.85) & (table["p_mc"] > 2) & ~table["matched"]]
    print("\nFailed dip primaries, endpoint quantiles [mm]:")
    print(failed[["end_z", "end_r"]].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(0).to_string())


if __name__ == "__main__":
    main()
