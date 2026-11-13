# SVT Endcap Disk Tiling Project

Project workspace for implementing the delivered SVT endcap RSU module tiling
(Ernst S. delivery in `ES_material/`) in the parent `epic` repository
(branch `si_disk_hole`, PR 1073). This directory is its own local git repo,
separate from EPIC (detached in EPIC commit `7cb35391f`).

## Read first

0. `HANDOFF.md` — entry point since the 2026-11-13 handover: status, how-tos, open items,
   and which of the documents below matter. Start there.
1. `logs/rsu_opt_endcap_20261004.md` — canonical implementation log. Read the
   last few sections for current status before doing anything.
2. `logs/plan_rsu_opt_endcap_20261004.md` — plan for the `rsu_opt` delivery.
3. `logs/SVT_ENDCAP_CORRUGATED_MODULE_PROJECT.md` — original guide and
   modeling philosophy (earlier `EIC_LAS_6RSU_CORR` prototype phase).
4. `simrec/acc_study/acceptance_study_20261026.md` and `README.md` — the
   separate acceptance simulation study.
5. `simrec/treffi_study/tracking_performance_study_20261106.md` — endcap
   tracking efficiency/resolution study on the acceptance campaign.
6. `CONCEPTS.md` — project-wide explanations of concepts (q/p, DCA, pulls,
   covariance layout, eta sides, PWG requirements). Add new concepts there;
   keep progress in the per-study logs.

Older notes (`SVT_ENDCAP_CORRUGATED_MODULE_LOG.md`, `*_HANDOFF.md`,
`step8*_*.md`) are supporting history, not current status.

## Key code in the parent repo

- `src/SiEndcapModuleTracker_geo.cpp` — module builder and `tiling-directory` reader.
- `compact/tracking/silicon_disks_modules.xml` — module dimensions/stack constants.
- `compact/tracking/silicon_disks_tiling/<delivery>/<scenario>/` — byte-for-byte copies of the deliveries:
  `20261110_ES/{rsu_opt,rsu6}` (production: rsu_opt), `20261110-r_ES/{rsu_opt,rsu6}` (facing-flipped,
  systematics), `20261001_ES/{rsu_opt,all_6rsu}` (old). Non-production ones load via
  `logs/make_svt_overlay.sh <delivery> <scenario>`; visual exports via `logs/make_svt_visualize.sh`.
- `compact/tracking/definitions_craterlake.xml` — disk z, radii, physical beampipe openings.

## Material scans

All material-scan outputs live in
`/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/matscan/` (gitignored; put new scans here too).

- `matscan/disk_material_map/<tag>/` — per-disk maps (eta-phi, x-y at disk plane, stacked X0(r),
  per-material pages, ROOT/npz, `disk_material_summary.{txt,json}`) from
  `scripts/subdetector_tests/disk_material_map.py` via `run_disk_material_map.sh` (default output dir
  is here). Input is an ACTS geantino `material_tracks` file. Scan-only recordings go in `<tag>/recording/`.
  - `step8m_full`: Step 8m geometry, full-eta ACTS recording. `step8q_20261106T153414Z`: Step 8q
    (rounded bends), 0.90<|eta|<4.25, 6M geantinos, made by `logs/run_svt_disk_material_scan_step8q.sh`.
  - `test_*`: 200k-track development runs.
- Older assembly-level scans (`material_scan.py`): `20260720/`, `20261016_*`, `step8n_*`.
- Compare two scans: `logs/compare_disk_material_summaries.py A.json labelA B.json labelB`.
- The disk table (z, r_max, openings) in `disk_material_map.py` is hard-coded from
  `definitions_craterlake.xml`; material names are matched from (Z, rho) in `MATERIAL_NAMES`.

## Material maps (ACTS)

ACTS material-map runs live in `matmap/<run>/` (gitignored), one directory per run, e.g.
`matmap/step8q_<UTC stamp>/material-map_map.cbor` (give this file to EICrecon via
`-Pacts:MaterialMap=`), with `provenance.txt`, `run_log.txt`, the intermediate ROOT/JSON files and
the validation plots (`plots/`, `Validation/`, `Surfaces/`). Make new maps with
`logs/regenerate_svt_material_map_step8q.sh` (or `sbatch logs/submit_material_map_step8q.sh`);
it runs the upstream `scripts/material_map/run_material_map_validation.sh` with the run directory
as working directory, so nothing is written to `scripts/material_map/`. Older runs were moved
there by `logs/organize_material_map_outputs_20261106.sh`; the Step 8m and production maps keep
a symlink at their old `scripts/material_map/` path.

## Conventions that are easy to get wrong

- CSV `x_origin_mm, y_origin_mm` = midpoint of the LEC/first-RSU boundary; module extends toward x = 0.
- CSV `z_baseplate_mm` is really the corrugation/facet reference surface, not the baseplate center.
- Engineer frame to EPIC: `x_EPIC = -x_engineer`; this reflection swaps LEFT/RIGHT chirality.
- Physical beampipe openings come from the EPIC beam pipe (+5 mm buffer); the delivery's openings only validate source placements.
- Disk IDs 0–9 map to ED4, ED3, ED2, ED1, ED0, HD0, HD1, HD2, HD3, HD4 (`HD3_*` files; `HD3b_*` in 20261001).
- Corrugation (Step 12): frames read `<disk>_rows.csv` from the tiling directory; flat edges = webs centered
  halfway between rows (our assumption). FPC: Kapton on the sensor side, Al on the baseplate back (all modules).
- Handedness (Step 13): follow Ernst's POSITIVE/NEGATIVE rule (module_cad_export.py); every bridge FPC points
  away from y = 0. The Module Definitions PDF Left/Right labels are inconsistent (logs/module_handedness_convention_20261112.md).
- Delivered placements are used as supplied (no z offsets) since Step 11b; RSU = 33.5 inactive + 14 active + 2.5 Cu um.
- Modeled sensitive area is intentionally 1.7487% below the catalogue area (inactive strips retained).
- ACTS material map must be generated from the same detector XML used for reconstruction.

## Working rules

- Absolute rule (see global `~/.claude/CLAUDE.md`): never modify, move, delete,
  or create files owned by, or inside directories owned by, any user other than
  `pdatta` (e.g. Shujie's `/global/cfs/cdirs/m3763/shujie/...`, reachable via
  `simrec/treffi_study/shujie/modules`). Check `stat -c %U` after `readlink -f`.

- `ES_material/` and delivered CSV/metadata are read-only.
- One step at a time: write a validator/check script in `logs/`, run it, save its `.txt` report, stop for user review.
- Append each step to `logs/rsu_opt_endcap_20261004.md` (files changed, formulas, commands, report paths, open issues). Keep rejected attempts documented.
- Do not claim overlap/compile passes that were not actually run; EIC-shell runs are usually done by the user (`~/weic/eic-shell`, image `26.09.0-stable`).
- Never delete: move to `tmp/retained/<date>/` and log in `tmp/file_actions.log`.
