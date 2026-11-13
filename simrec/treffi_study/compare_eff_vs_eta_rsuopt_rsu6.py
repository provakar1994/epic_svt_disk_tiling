"""Step 14b follow-up: tracking efficiency vs |eta| (p > 2 GeV, vz = 0), rsu_opt vs rsu6.
Same efficiency definition as endcap_tracking_performance.py (matched = >= 1 CKF association), read from the
reduced caches written by the phase-3 analysis. Independent-sample binomial errors (npsim samples are not paired).
Usage: python compare_eff_vs_eta_rsuopt_rsu6.py > out/v4_rsu6_vs_rsuopt_pwg_vz0_50files/eff_vs_eta_p2.txt"""
import glob
import numpy as np

caches = {"rsu_opt": "/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_acceptance_v4_step13",
          "rsu6": "/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_acceptance_v4_step13_rsu6"}
edges = np.round(np.arange(1.0, 3.81, 0.1), 2)

def counts(cache, side):
    pattern = "m3p8_to_m0p6" if side == "backward" else "p0p6_to_p3p8"
    files = sorted(glob.glob(f"{cache}/rec_vz_000mm_eta_{pattern}_chunk_*.npz"))[:50]
    n = np.zeros(len(edges) - 1); k = np.zeros(len(edges) - 1)
    for f in files:
        d = np.load(f)
        sel = d["p_mc"] > 2.0
        abs_eta = np.abs(d["eta_mc"][sel]); matched = d["matched"][sel].astype(bool)
        n += np.histogram(abs_eta, edges)[0]; k += np.histogram(abs_eta[matched], edges)[0]
    return n, k, len(files)

for side in ["backward", "forward"]:
    (na, ka, fa), (nb, kb, fb) = counts(caches["rsu_opt"], side), counts(caches["rsu6"], side)
    print(f"== {side}, p > 2 GeV, vz = 0 ({fa}/{fb} files): |eta| bin  eff rsu_opt  eff rsu6  diff +- err  pull")
    for i in range(len(edges) - 1):
        ea, eb = ka[i] / na[i], kb[i] / nb[i]
        err = np.sqrt(ea * (1 - ea) / na[i] + eb * (1 - eb) / nb[i])
        print(f"  {edges[i]:.1f}-{edges[i+1]:.1f}  {ea:.4f}  {eb:.4f}  {eb-ea:+.4f} +- {err:.4f}  {(eb-ea)/err if err > 0 else 0:+6.1f}")
