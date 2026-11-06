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

## Open issues

- `shujie/modules` points to `/global/cfs/cdirs/m3763/shujie/worksim/scripts/modules`,
  which is group-writable (m3763), so pdatta can modify Shujie's files. Nothing
  in this study imports from it.
