# Overnight plan, 2026-11-06 (reference planes + true-crossing efficiency)

Written by the coordinating Claude session at the start of the overnight run,
so that a resumed session or the user can see what was intended and where to
pick up. Status is in the logs named below, not here.

## User decisions (2026-11-05 evening)
- Step 8q (rounded bends) accepted; Geant4 passed; commits `c5da03dcf`,
  `311634084` pushed by the user. Nothing to merge from `origin/si_disk_hole`.
- Material map and eicrecon deferred.
- Reference planes: front planes only, as an overlay in this project repo;
  no EPIC repo changes, no branch.
- Batch: premium queue authorized for the campaign.
- Gun 0.5-20 GeV unchanged. Momentum bins: 0.1 GeV steps over 0.5-1, then 1-2,
  2-3, then 2 GeV steps from 3 (last bin 19-20).
- Overnight: advance automatically when numerical gates pass, stop on failure;
  visual check of the overlay in the morning.
- Agents: individual agents coordinated by the main session (no scripted workflow).

## Work split
- Geometry agent: Step 9a-9f in `logs/rsu_opt_endcap_20261004.md`; files in
  `refplanes/`. 9a clearance table, 9b overlay XML/generator/plane_map.csv,
  9c export + ROOT/Geant4 overlaps, 9d zero-material scan, 9e filter steering +
  100-event smoke tests (`/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/smoke/`),
  9f 10k-event silicon-unchanged check.
- Analysis agent: `simrec/acc_study` tooling (run_sim.sh ACC_XML/ACC_STEERING
  overrides, prepare_acceptance_tasks_refplanes.sh, extract_disk_particles_refplanes.py,
  analyze_refplane_efficiency.py); log in `simrec/acc_study/acceptance_study_20261026.md`.
- Coordinator: after both pass, generate `task_lists/acceptance_v3_refplanes`
  (vz 0, +/-100 mm x 2 eta x 50 chunks x 100k, sim only, 300 tasks), submit
  `sbatch submit_premium_packed.sh <tasks>` (4 nodes, 1 wave, 3 h), monitor,
  then extraction and analysis, then a morning summary in
  `simrec/acc_study/acceptance_study_20261026.md`.

## If this session died
Read the two logs above for the last completed step; nothing in the EPIC repo
is modified by this work. Check `squeue -u pdatta` for a running campaign.
