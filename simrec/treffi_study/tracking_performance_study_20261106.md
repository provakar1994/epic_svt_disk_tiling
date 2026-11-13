# SVT endcap tracking performance study

Started: 2026-11-06

## Scope

Measure single-particle tracking performance in the endcaps (1 < |eta| < 3.5)
for the SVT disk tiling geometry, using the reconstructed files of the
acceptance campaign (`simrec/acc_study/`, `acceptance_v1`). Quantities:

- tracking efficiency vs eta and vs p;
- Gaussian-core resolutions vs p: dp/p, delta(q/p)/(q/p), theta, phi, DCAr, DCAz;
- pull widths: q/p, theta, phi, DCAr, DCAz;
- final deliverable: dp/p vs p in the PWG eta regions with the PWG requirement,
  in the style of Shujie's `tracking_single_particle_perf_epic_vs_no_L4_HD4.pdf`
  (page 3), with more momentum points.

Starting point: Shujie's barrel notebook `plot_single_resol.ipynb` (one file,
fixed p, barrel), now kept in `shujie/` (read-only reference; `shujie/modules`
is a symlink to Shujie's live module directory, see "Open issues").

Concepts used here (q/p, DCA, pulls, Cov6f layout, dp/p skew) are explained
in the project-wide `CONCEPTS.md`.

## Input data

`/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1/` (see
`simrec/acc_study/acceptance_study_20261026.md` for production details).

- Gun: one pi+ per event, flat in eta over [0.6, 3.8] or [-3.8, -0.6], flat in
  p over [0.5, 20] GeV, phi uniform, vertex (0, 0, vz) with vz = 0, +10, -10 mm.
- 50 chunks x 100k events per (vz, eta side); this study uses vz = 0 so far.
- Geometry `install/share/epic/epic_craterlake_tracking_only.xml` (local
  install at the time of the campaign, 2026-10-26, Step 8m era), material map
  `scripts/material_map/step8m_20261020T164956Z_material-map_map.cbor`
  (sha256 in each `logs/rec_*.log`). eic_xl 26.09.0-stable (edm4eic 8.10).
- Note: tracking-only geometry (no PID/calorimeter material), not full ePIC.

## Method and conventions

Code: `endcap_tracking_performance.py` (reduce + fit + plots),
`plot_pwg_resolution.py` (PWG-style comparison plot),
`run_endcap_tracking_performance.sh` (records the command and runs both),
`pwg_requirements.txt` (copy of Shujie's table, preTDR v2.1 sec. 8.3.3).

- Primaries: `MCParticles.generatorStatus == 1` and charge != 0.
- Matching: `CentralCKFTrackAssociations` (`_rec` -> CentralCKFTracks,
  `_sim` -> MCParticles, collection IDs from `podio_metadata`). If several
  tracks match one primary, the highest-weight one is used (`n_assoc` kept).
  Efficiency = primaries with >= 1 matched track / primaries (Wilson 68% errors).
- Track parameters: `CentralCKFTrackParameters` at the perigee around (0,0,0).
  Track index i in CentralCKFTracks = entry i in the parameters collection;
  checked per file (theta from Track momentum vs parameters: 100% agreement).
- Covariance: edm4eic `Cov6f`, ACTS basis [l0, l1, phi, theta, q/p, t],
  packed lower-triangular, diagonal (i,i) at index i + i(i+1)/2:
  var(loc.a)=cov[0], var(loc.b)=cov[2], var(phi)=cov[5], var(theta)=cov[9],
  var(q/p)=cov[14]. Checked against the edm4eic 8.10 header in the container.
- Residuals: dp/p = (p_rec - p_mc)/p_mc [%], delta(q/p)/(q/p) [%],
  dtheta, dphi (wrapped to [-pi, pi]) [mrad], DCAr = loc.a [um] (true value 0,
  vertex on the beam line), DCAz = loc.b - vz_mc [um] (checked: <loc.b> = 9.8 mm
  for vz = +10 mm).
- Pulls: residual / sqrt(variance); q/p pull uses signed q/p (Shujie's notebook
  used |q/p|).
- Sides: backward = eta < 0 = electron-going endcap (ED disks),
  forward = eta > 0 = hadron-going endcap (HD disks).
- Binning: side x |eta| x p. p bins 0.5-1, 1-2, ..., 19-20 GeV. |eta| edges
  1.0, 2.5, 3.0, 3.5 (PWG regions) or 1.0, 1.5, ..., 3.5 (fine).
- Gaussian-core fit: same algorithm as Shujie's `epic_analysis_base.hist_gaus`
  (2026-10-08): median / 1.4826*MAD iterated with a +/-3 scale clip, 101-bin
  histogram over centre +/- 3 scale, unweighted Gaussian least-squares fit.
  Re-implemented locally (scipy `curve_fit` instead of lmfit), not imported.

Outputs: `out/<tag>/` (plots, `summary_<tag>.csv`, `fitcheck_<tag>.pdf`,
`run_<tag>.log`). Per-file reduced tables (one row per primary):
`/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_acceptance_v1/`.

## Progress

### 2026-11-06: first version

- Wrote the three scripts above. Smoke test (5k events/side) and a 5-chunk run.
- Bug found by the user in review: the fit-check PDF drew the fitted Gaussian
  with a wrong normalisation (multiplied instead of divided by the bin width).
  The fitted sigma did not depend on it. Fixed; fit-check now shows data over
  mean +/- 6 sigma on a log scale, fitted curve and fit window, one page per
  (side, |eta| bin, quantity).
- Fit changed from my own +/-2 sigma weighted fit to Shujie's `hist_gaus`
  algorithm for comparability with the reference plots.
- Added delta(q/p)/(q/p): in backward 3 < |eta| < 3.5 at high p the dp/p
  distribution is strongly skewed (sharp low edge, long high tail) because
  p = 1/(q/p) and the resolution is tens of percent. The q/p form stays Gaussian.
- Superseded outputs `out/smoke_5k`, `out/vz0_5files` moved to
  `tmp/retained/2026-11-06/simrec/treffi_study/out/` (logged in `tmp/file_actions.log`).
- Runs (50 chunks/side, vz = 0, 10M primaries):
  `ETA_EDGES=pwg ./run_endcap_tracking_performance.sh pwg_vz0_50files 50` and
  `./run_endcap_tracking_performance.sh fine_vz0_50files 50`.

Results (`out/pwg_vz0_50files/`, `out/fine_vz0_50files/`): 10M primaries,
7.61M matched, 51 primaries with > 1 matched track; all 1320 fits converged.
Gaussian-core sigma [%] in selected p bins (p_lo of the 1 GeV bin; 0.5 = 0.5-1 GeV):

| side | abs(eta) | dp/p 0.5 / 5 / 10 / 19 | d(q/p)/(q/p) 0.5 / 5 / 10 / 19 | q/p pull width 0.5 / 5 / 10 / 19 |
|---|---|---|---|---|
| backward | 1.0-2.5 | 1.15 / 1.33 / 1.53 / 1.94 | 1.15 / 1.33 / 1.53 / 1.94 | 1.14 / 1.10 / 1.08 / 1.05 |
| backward | 2.5-3.0 | 3.98 / 4.63 / 5.46 / 7.62 | 3.92 / 4.66 / 5.49 / 7.70 | 1.22 / 1.11 / 1.06 / 1.03 |
| backward | 3.0-3.5 | 7.38 / 16.4 / 31.6 / 42.7 | 6.88 / 13.1 / 17.1 / 26.7 | 1.23 / 1.53 / 1.59 / 1.67 |
| forward | 1.0-2.5 | 1.18 / 1.41 / 1.58 / 1.90 | 1.18 / 1.41 / 1.58 / 1.90 | 1.18 / 1.13 / 1.08 / 1.02 |
| forward | 2.5-3.0 | 3.42 / 3.81 / 4.21 / 5.33 | 3.36 / 3.83 / 4.24 / 5.37 | 1.26 / 1.18 / 1.09 / 0.98 |
| forward | 3.0-3.5 | 7.55 / 9.24 / 11.2 / 16.6 | 6.72 / 9.21 / 11.1 / 15.5 | 1.37 / 1.27 / 1.19 / 1.16 |

- Above the PWG requirement in every endcap region. Compared with the "epic"
  points in Shujie's reference (read by eye from page 3 of
  `tracking_single_particle_perf_epic_vs_no_L4_HD4.pdf`): 1 < |eta| < 2.5 is
  ~20-50% worse (ref ~0.9-1.0% at low p, ~1.2-1.3% at 15 GeV), 2.5-3.0 is similar
  to slightly worse, backward 3.0-3.5 is much worse at high p (ref ~12% at 15 GeV
  vs 21.6% d(q/p)/(q/p) or ~38% dp/p here).
- dp/p and d(q/p)/(q/p) agree where sigma < ~8%; they diverge in 3 < |eta| < 3.5
  (skewed dp/p). Use d(q/p)/(q/p) there.
- q/p pulls > 1 (up to 1.67 backward 3-3.5): track errors underestimated.
- Cause of the difference to the reference not yet identified. Candidates:
  (a) Step 8m material map vs `epic_craterlake_tracking_only.xml` mismatch
  (project rule: map must be generated from the same XML as reconstruction);
  (b) geometry/software differences vs Shujie's samples (unknown details);
  (c) eta-bin population differences (flat eta here; reference unknown).
  Proposed check: same gun settings on main-branch geometry with its matching
  material map (needs an eic-shell run by the user).

### 2026-11-06: forward efficiency dip at 1.6 < eta < 1.85

Question (user): origin of the efficiency dip in the hadron-going endcap near eta ~ 1.7.
Scripts: `diagnose_forward_dip.py` (via `run_diagnose_forward_dip.sh`) and
`diagnose_forward_dip_tracks.py`; reports and plots in `out/diagnose_forward_dip/`
(`diagnose_forward_dip.txt`, `diagnose_forward_dip_tracks.txt`, `dip_*.png`).
All numbers for p > 2 GeV.

Findings:
1. Not uniform in phi: per-5-deg efficiency in the dip ranges 0.61-0.89, rms 0.071
   vs 0.006 expected from statistics (`dip_eff_eta_phi.png`). Narrow low-efficiency
   stripes also at eta 1.2-1.3 near phi = 0, +/-90, 180 deg.
2. Not missing silicon: Geant4 truth disk hits (acceptance-study extraction,
   10 files) show the dip window is exactly where the primary hits HD0-HD3 but
   not HD4 (HD3 starts at eta 1.6, HD4 at 1.8; both uniform in phi,
   `dip_truth_disk_hits_eta_phi.png`). Efficiency there: 4 disks hit 0.78,
   5 disks 0.87, while just below (1.35-1.55, HD0-HD2) 3 disks give 0.98 and
   above (2.1-2.4) 4 disks give 0.99.
3. Not a hadronic interaction: failed primaries survive to the world boundary
   (median endpoint far outside the detector) and have the same median number of
   MCParticles (3) as reconstructed ones. Contrast: failures at 2.1-2.4 are
   interactions (median endpoint z = 186 mm, 20 MCParticles).
4. Seeding works, the CKF returns nothing: 96% of failed dip events have
   >= 1 CentralTrackSeed, but 1677 of 1705 have zero CentralCKFTracks.
5. The dip moves with the vertex: minimum at eta 1.69 / 1.71 / 1.59 for
   vz = -100 / 0 / +100 mm and gets much deeper for +100 mm (eff 0.25).
   Straight-line estimate of a fixed structure: r ~ 750 mm, z ~ 1860 mm (rough;
   from noisy minima). Failed events also carry more barrel MPGD/TOF hits
   (1.16 vs 0.22 TOF barrel hits per event), origin not understood.
6. EICrecon logs are at info level: no per-event CKF/propagation messages.

Interpretation (not confirmed): a reconstruction-side failure for tracks that
leave the silicon past the outer edge of HD4 (after HD3), not a physics loss.
Candidates: (a) ACTS navigation/propagation failure in the CKF for these
trajectories (the track then is dropped as a whole); (b) Step 8m material map
not matching `epic_craterlake_tracking_only.xml`, giving wrong material
effects that are phi-dependent through the map binning (consistent with the
phi structure and with q/p pull widths > 1).
Proposed tests (eic-shell): rerun EICrecon on failed dip events with CKF
debug logging; rerun one forward chunk with a material map made from the same
XML (and without a material map); same gun on the main-branch geometry.

### 2026-11-06: efficiency vs eta in bins of true momentum

- `endcap_tracking_performance.py`: new `plot_efficiency_eta` (called from
  `plot_efficiency`) replaces the single p-integrated efficiency-vs-eta curve.
  Layout: columns backward / forward, only 1 < |eta| < 3.8 drawn; rows full range
  and zoom 0.80-1.01. One curve per true-p bin (plasma colormap ordered by p) plus
  the p-integrated curve (black). Wilson errors as before. Also writes
  `efficiency_eta_check_<tag>.txt` (integrated efficiency per side and p bin).
  Efficiency vs p plot unchanged.
- New options: `--eff-p-edges` (default 0.5 1 2 5 10 20 GeV), `--eff-eta-width`
  (default 0.05), `--efficiency-only` (skip fits/CSV/resolution plots). Run script
  environment: `EFF_P_EDGES`, `EFF_ETA_WIDTH`, `EFF_ONLY=1` (log then goes to
  `run_<tag>_efficiency.log`; the full-run log is kept).
- Regenerated from the cached .npz tables (no ROOT reading, ~25 s per tag) with
  `./redo_efficiency_plots_20261106.sh`, which first moves the old
  `efficiency_{eta,p}_<tag>.png` to
  `tmp/retained/2026-11-06/simrec/treffi_study/out_efficiency_before_p_bins/<tag>/`
  (logged in `tmp/file_actions.log`).
- Outputs: `out/{pwg,fine}_vz0_50files/efficiency_eta_<tag>.png`,
  `efficiency_eta_check_<tag>.txt`, `efficiency_p_<tag>.png` (same content as before).
- Check: the new p-integrated curve merged to 0.1 eta bins equals the old single
  curve exactly (max difference 0; e.g. forward eta 1.7-1.8: 0.681).

Observations (1 < |eta| < 3.8, 10M primaries):

| side | 0.5-1 | 1-2 | 2-5 | 5-10 | 10-20 GeV | all p |
|---|---|---|---|---|---|---|
| backward | 0.404 | 0.695 | 0.767 | 0.783 | 0.789 | 0.769 |
| forward | 0.339 | 0.671 | 0.761 | 0.781 | 0.789 | 0.765 |

(integrated values include the acceptance edge above |eta| ~ 3.2).
- Plateau efficiency rises with p: ~0.98 for p > 5 GeV, ~0.96-0.97 for 2-5 GeV,
  ~0.85-0.95 for 1-2 GeV. The p-integrated plateau (~0.96) is pulled down by p < 2 GeV.
- 0.5-1 GeV is far below the others everywhere (0.1-0.85), falling towards large
  |eta| on both sides (backward ~0.2 at |eta| 3, forward ~0.1 at eta 3).
  1-2 GeV also loses efficiency earlier at large |eta| (forward from eta ~ 2.8).
- The forward dip at 1.6 < eta < 1.85 is present at every p (minimum ~0.57 for
  1-2 GeV, ~0.65 for p > 2 GeV), so it is not a low-momentum effect.
- Backward structures at eta ~ -1.6 and -1.3 also appear at all p.

## Open issues

- `shujie/modules` points to `/global/cfs/cdirs/m3763/shujie/worksim/scripts/modules`,
  which is group-writable (m3763), so pdatta can modify Shujie's files. Nothing
  in this study imports from it.

### 2026-11-06: efficiency vs eta plot simplified

Removed the zoom row and the black p-integrated curve from `plot_efficiency_eta` (now one row,
backward | forward, one curve per p bin). The p-integrated efficiency is still written to
`efficiency_eta_check_<tag>.txt`. Regenerated with
`bash redo_efficiency_plots_20261106.sh before_no_zoom "superseded: zoom panel and all-p curve removed (same file name)"`
(the script now takes a retention label and reason); previous PNGs in
`tmp/retained/2026-11-06/simrec/treffi_study/out_efficiency_before_no_zoom/`.

### 2026-11-06: reconstruction of acceptance_v3_refplanes with the Step 8q map

Goal: consistency (not yet the dip). Simulation, material map and reconstruction now all use the
same geometry: installed `epic_craterlake_tracking_only.xml` (sha256 `c0141309…`, EPIC `311634084`,
Step 8q). Map: `matmap/step8q_20261106T222257Z/material-map_map.cbor` (sha256 `b5ce1f2e…`, made from
the tracking-only XML; see Step 10 in `logs/rsu_opt_endcap_20261004.md`). The v3 sim used the
reference-plane overlay XML; reconstruction uses the plain XML (planes have no ACTS parameters and are
Vacuum; their hit collections are ignored by EICrecon).

- `simrec/acc_study/run_sim.sh`: new optional `ACC_MATERIAL_MAP` (default unchanged: Step 8m map).
- `simrec/acc_study/prepare_recon_tasks_v3_step8q.sh` -> `task_lists/acceptance_v3_refplanes_rec_step8q/`
  (300 recon tasks, 6 configurations x 50 chunks x 100k; outputs `rec_<tag>.root` next to the sim files).
- Smoke test (500 events, vz0 forward chunk 001, `/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/recon_smoke_v3_step8q/`):
  map loaded, warning set identical to the v1 rec log, matched fraction 0.78 (v1 integrated ~0.77).
- Submitted: `sbatch --time=01:00:00 --job-name=svt-v3-rec submit_premium_packed.sh task_lists/acceptance_v3_refplanes_rec_step8q/tasks.txt`
  -> Slurm job 60936753 (4 premium nodes, one wave).
- `run_endcap_tracking_performance.sh`: new `CAMPAIGN` (default acceptance_v1), `CAMPAIGN_LABEL`, `CONFIGS`;
  cache `treffi_study/reduced_<CAMPAIGN>/`. Run the analysis only after the job ends (the `rec_*.root`
  glob would also match `rec_*.tmp.*.root` files of running tasks).

### 2026-11-06: v3 (Step 8q map) results vs v1 (Step 8m map)

Reconstruction job 60936753: 300/300 tasks completed (5 min 50 s), every rec log loads the Step 8q map
(sha256 `b5ce1f2e…`), no failures. Analysis: `run_v3_step8q_analysis_20261106.sh` -> `out/v3_fine_vz0_50files/`,
`out/v3_pwg_vz0_50files/`, `out/v1_vs_v3_pwg_vz0_50files/pwg_resol_{dp,qop}_v1_vs_v3.png`; comparison
`compare_v1_v3_20261106.py` -> `out/v1_vs_v3_pwg_vz0_50files/compare_v1_v3.txt`.

- Every resolution and pull width agrees within statistics: sigma(v3)/sigma(v1) has median 0.995–1.010 for all
  quantities and PWG eta bins (largest single-bin deviations at 3 < |eta| < 3.5, where statistics are low).
- Pull widths are unchanged, e.g. q/p: 1.07–1.10 for |eta| < 3, 1.19 (forward) and 1.57 (backward) at 3–3.5.
- Efficiency unchanged: integrated per p bin within 0.002; forward dip 1.6 < eta < 1.85 (p > 2 GeV, vz = 0)
  0.7742 (v1) vs 0.7743 (v3); references 1.35–1.55 and 2.1–2.4 also unchanged.
- Conclusion: the map / geometry inconsistency did not affect these results. The forward dip, the
  above-requirement resolution and the >1 pulls are not caused by it. Caveat: identical results could also
  mean the two maps hardly differ inside the tracker; a run with no material map would show how much the
  map matters at all.

### 2026-11-13: v4 (acceptance_v4_step13, Step 13 map) analysis prepared, not run

No rec files yet. New: `run_v4_step13_analysis_20261113.sh STEP13_MAP_SHA256 [--check-only]` (same
outputs as v3: `out/v4_fine_vz0_50files/`, `out/v4_pwg_vz0_50files/`,
`out/v3_vs_v4_pwg_vz0_50files/{pwg_resol_{dp,qop}_v3_vs_v4.png,compare_v3_v4.txt}`; cache
`reduced_acceptance_v4_step13/`). It refuses unless `check_rec_campaign_ready.sh` passes (100 vz = 0 rec
files, no *.tmp.*, every rec log has the given map sha256, a map-loading line and "Finished:"), rejects
the Step 8q sha256, and refuses to overwrite outputs. `compare_v3_v4_20261113.py`: sigma and pull-width
ratios, efficiency per p bin (1 < |eta| < 3.8) with binomial difference errors, forward dip 1.6-1.85 and
references 1.35-1.55, 2.1-2.4 (p > 2 GeV). Tests: gate PASS on v3 with b5ce1f2e..., FAIL with a wrong
sha256 and on the running v4 campaign; compare script v3-vs-v3 reproduces the v3 efficiency-check table
and dip 0.7743 with zero differences. Driver: `../run_v4_step13_phase3.sh` (see Step 13f in
acceptance_study_20261026.md). Expected runtime ~15 min (v3 log).

### 2026-11-13: v4 (Step 13 geometry and map) vs v3

Recon 61217238 (300/300, map sha256 cba82219…). `out/v3_vs_v4_pwg_vz0_50files/compare_v3_v4.txt`:
sigma(v4)/sigma(v3) median 0.986-1.006 everywhere; efficiency per p bin within 0.0024; forward dip
0.7743 -> 0.7773 (+0.0030 +- 0.0010), references +0.0010 / -0.0005. No change in substance.

### 2026-11-13: efficiency definition and the EICrecon chain behind it (written up for the eta 1.7 dip)

Efficiency (`endcap_tracking_performance.py`, `reduce_file` + `efficiency_vs_eta`):
- Denominator: every MCParticle with generatorStatus == 1 and charge != 0 (= the one gun pi+ per event),
  binned in its generated eta and p. No acceptance, hit-count, decay or interaction requirement.
- Numerator: the same particle with >= 1 entry in CentralCKFTrackAssociations whose rec side is in
  CentralCKFTracks and sim side is that MCParticle (collection IDs from podio_metadata). Any weight > 0
  counts: no purity, chi2, nMeasurements, charge or momentum-agreement cut. Duplicates are not penalised.
- Errors: Wilson 68% interval.
EICrecon chain (read from EICrecon v1.40.0-32 source in /global/cfs/cdirs/m3763/shujie/EICrecon, read-only;
the container runs 1.41.0, defaults not re-checked there):
- Seeds (CentralTrackSeeds, ACTS orthogonal seeder) from CentralTrackingRecHits = SiBarrelVertex, SiBarrel,
  SiEndcapTracker, MPGDBarrel, OuterMPGDBarrel, Backward/ForwardMPGDEndcap hits, restricted to
  r <= 440 mm and -1500 <= z <= 1700 mm (TrackSeedingConfig defaults; also deltaR, impactMax 3 mm,
  minPt ~ 3.7 MeV, B = 1.7 T used for seeding).
- CKF (CentralCKFTrajectories) uses CentralTrackerMeasurements = all of the above + TOFBarrel + TOFEndcap
  cluster hits, chi2 cut 15, max 10 compatible measurements per surface. A track is silently dropped
  (debug-level message only) if track finding, smoothing or the extrapolation to the perigee fails, or if it
  has < 4 measurements.
- Ambiguity solver: max 1 shared hit, >= 4 measurements.
- Association weight (ActsToTracks): fraction of the track's measurements (outliers excluded) whose sim hit
  belongs to the MCParticle; barrel, MPGD and TOF hits all count.

### 2026-11-13: Step 14b, rsu6 vs rsu_opt (20261110_ES), vz = 0, 50 files per side

Inputs: rsu_opt = `acceptance_v4_step13` + map cba82219…; rsu6 = `acceptance_v4_step13_rsu6`, rec with the rsu6
tracking overlay (453fda16…) and rsu6 map c4cf9a3a… (all 300 rec logs show it). Driver
`../run_v4_step13_rsu6_phase3.sh`; report `out/v4_rsu6_vs_rsuopt_pwg_vz0_50files/compare_rsuopt_vs_rsu6.txt`.
Follow-up script `compare_eff_vs_eta_rsuopt_rsu6.py` -> `out/v4_rsu6_vs_rsuopt_pwg_vz0_50files/eff_vs_eta_p2.txt`.
Samples are independent (npsim shared random stream), errors are independent-sample binomial.
- Resolutions/pulls: median sigma(rsu6)/sigma(rsu_opt) 0.990-1.011 in every quantity and PWG eta bin: unchanged.
- Efficiency, 1 < |eta| < 3.8: backward 0.7697 -> 0.7712 (+0.0015 +- 0.0003), forward 0.7657 -> 0.7709
  (+0.0052 +- 0.0003); every p bin goes up.
- Forward dip 1.6-1.85 (p > 2 GeV): 0.7773 -> 0.8293 (+0.0521 +- 0.0009). References: 1.35-1.55 +0.0011,
  2.1-2.4 +0.0003.
- Per 0.1 in |eta| (p > 2 GeV): the whole gain sits in the known low-efficiency (CKF-failure) windows:
  forward 1.6-1.7 +0.049, 1.7-1.8 +0.071, 1.8-1.9 +0.010; backward 1.3-1.4 +0.017, 1.6-1.7 +0.014,
  1.4-1.6 / 1.7-1.8 +0.004..0.007. Where the efficiency is already ~0.98 (|eta| > 1.9) nothing changes
  (|diff| <= 0.002).
- Not a silicon-coverage effect: straight lines from the origin hit D0 active silicon in 98.4 % (rsu_opt) vs
  98.8 % (rsu6) of 1.6 < eta < 1.85 (scratch estimate from the active-silicon rectangle dumps), and the dip
  failures were shown (2026-11-06) to have all disk hits with seeds but no CKF track.
- Interpretation (not confirmed): the dip is a reconstruction (CKF/navigation) failure, and its size depends
  on the ACTS surface layout of the disks; rsu6 (different module count/placement on every disk, 6-RSU only
  on D0) happens to trigger it less often. This should NOT be read as a detector advantage of rsu6 until the
  dip itself is understood (CKF debug rerun on failed events, as proposed 2026-11-06).
