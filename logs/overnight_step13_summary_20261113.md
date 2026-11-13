# Overnight Step 13 downstream reruns: summary (2026-11-13)

Geometry: EPIC `78ade4686` (Step 13: every bridge FPC away from y = 0), tiling 20261110_ES/rsu_opt.
Identity (`logs/freeze_install_step13.txt`): modules XML sha256 `6d04bd66…`, libepic.so `9ccf1a66…`.
Reference for comparisons: Step 8q geometry (EPIC `311634084`, 20261001 delivery), v3 campaign.
Every v3-vs-v4 difference therefore mixes the delivery change (Step 11), the RSU stack change (Step 11b),
the corrugation-from-rows change (Step 12) and the FPC flip (Step 13), not the FPC flip alone.

## Jobs

| what | Slurm | result |
|---|---|---|
| ACTS material map 1000x5000 | 61213413 | COMPLETED 1:07; `matmap/step13_20261113T054800Z/material-map_map.cbor`, sha256 `cba82219…` |
| per-disk material scan (6M geantinos) | 61213414 | COMPLETED 0:47; `matscan/disk_material_map/step13_20261113T065150Z/` |
| sim `acceptance_v4_step13` (300 x 100k, seeds 44000001-44005050) | 61213457 | COMPLETED 2:39; 300/300 tasks, 0 logs with errors |
| recon with the Step 13 map | 61217238 | COMPLETED 0:06; 300/300, every rec log shows map sha256 `cba82219…` |
| refplane gates for the Step 13 overlay (G4 overlaps) | 61212507 | 0 overlaps; all 9a/9b/9c/9e/coverage gates PASS (`refplanes/step13/`) |

## Material (logs/analyze_material_step13_vs_8q.txt, Step 13g in rsu_opt_endcap_20261004.md)

- Per-disk mean x/X0 on the annulus: -0.83 to -1.12 % (e.g. ED4 0.2736 -> 0.2706 % X0).
- Silicon -4.5 %: Step 11b inactive RSU Si 36 -> 33.5 um (RSU Si 50 -> 47.5 um). Predicted -4.52 %, observed -4.51 %.
- Al/Kapton -2.4 %: FPC flip moved 1077 top-half FPCs ~5 mm to larger |y|; the scan weights by ~1/r^2.
  Predicted -2.51 %, observed -2.41 %; top/bottom halves are now mirror-symmetric.
- Carbon +0.26 % on ED0/HD0 only (Step 12 rim flats); Cu, glue unchanged. Predicted totals match within 0.06 %.
- Map: same 59 surfaces / binning / warnings as Step 8q; SVT disk surfaces -0.2 to -1.1 %. Fit for reconstruction.
  The map-vs-Geant4 deviations at 2 < |eta| < 3 (-17 to -30 %) are inherited from Step 8q: separate follow-up.

## Acceptance: true-crossing efficiency (results/refplane_efficiency_v5/compare_v3_v4.txt)

- vz = 0, fiducial: v4 - v3 = -0.01 to +0.06 pt on all disks (e.g. ED4 98.31 -> 98.32, HD0 97.41 -> 97.47 %).
- Displaced vertices: small but significant gains on the disks nearest the vertex (steep tracks):
  vz = -100: ED1 +0.08 (4.7 sigma), ED0 +0.09 (3.2 sigma); vz = +100: HD0 +0.11 (3.9 sigma), HD1 +0.05 (3.2 sigma).
  Most likely a small coverage change in the row layout (20261110 rows / Step 12 corrugation) for steep tracks
  that pass between rows. Not yet traced; physically negligible (<= 0.11 pt).
- Caveat: A/B family regions use the 20261110 rows table (converted, ranges differ < 1 mm from v3); the
  `published_v8` column in summary.txt still holds the old-geometry numbers.

## Tracking performance (simrec/treffi_study/out/v3_vs_v4_pwg_vz0_50files/compare_v3_v4.txt)

- Resolutions and pulls: median sigma(v4)/sigma(v3) 0.986-1.006 in every quantity and PWG eta bin.
- Efficiency per p bin within 0.0024 (integrated backward 0.7692 -> 0.7697, forward 0.7655 -> 0.7657).
- Forward dip 1.6 < eta < 1.85 (p > 2 GeV): 0.7743 -> 0.7773 (+0.0030 +- 0.0010); references move +0.0010, -0.0005.
  The dip is unchanged in substance.

## Open items

1. Trace the +0.05-0.11 pt steep-track acceptance gain on D0/D1 (displaced vertices).
2. Map-vs-Geant4 deviations at 2 < |eta| < 3 (inherited).
3. Type-name chirality swap and global-x question: waiting for Ernst (module_handedness_convention_20261112.md).
4. Nothing from the overnight run is committed yet.

## Step 14: rsu6 comparison (20261110_ES/rsu6 vs rsu_opt, same EPIC 78ade4686, 2026-11-13)

Geometry via frozen overlay `geometry_overlays/step13/rsu6/` (2150 modules); refplane gates PASS (`refplanes/step13_rsu6/`).

| what | Slurm | result |
|---|---|---|
| ACTS map rsu6 | 61226513 | COMPLETED 1:07; `matmap/step13_rsu6_20261113T143431Z/`, sha256 `c4cf9a3a…` |
| disk material scan rsu6 | 61226514 + 61228502 | slice 3 OOM-killed, rerun same seed; COMPLETED; `matscan/disk_material_map/step13_rsu6_20261113T143518Z/` |
| sim `acceptance_v4_step13_rsu6` (same seeds as v4; samples still independent) | 61227160 | COMPLETED 2:41; 300/300 |
| recon with the rsu6 map | 61232634 | COMPLETED 0:06; 300/300, all logs show `c4cf9a3a…` |

- Material: D0 (ED0/HD0) +7.8 % (0.311 -> 0.336 % X0); other disks -0.09..+0.40 %. D0 in rsu6 = 76 six-RSU modules
  (456 RSUs) vs 56 five-RSU + 22 six-RSU (412 RSUs) in rsu_opt.
- Acceptance (`results/refplane_efficiency_v5_rsu6/compare_rsu_opt_vs_rsu6.txt`): D0 fid +0.24/+0.27 pt at vz=0
  (+0.22..+0.34 at vz=+-100); other disks within +-0.03 pt; ED4 no-margin -0.16 pt (252 vs 256 modules).
- Tracking (`simrec/treffi_study/out/v4_rsu6_vs_rsuopt_pwg_vz0_50files/`): resolutions/pulls unchanged
  (ratio medians 0.990-1.011). Efficiency up only in the known CKF-failure windows: forward dip 1.6-1.85
  0.7773 -> 0.8293 (+0.052), backward 1.3-1.4 +0.017. Not explained by silicon coverage; treat as a
  reconstruction sensitivity, not an rsu6 advantage, until the dip is understood.
- Nothing from Step 14 is committed.
