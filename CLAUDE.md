# SVT Endcap Disk Tiling Project

Project workspace for implementing the delivered SVT endcap RSU module tiling
(Ernst S. delivery in `ES_material/`) in the parent `epic` repository
(branch `si_disk_hole`, PR 1073). This directory is its own local git repo,
separate from EPIC (detached in EPIC commit `7cb35391f`).

## Read first

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
- `compact/tracking/silicon_disks/{rsu_opt,all_6rsu}/` — byte-for-byte copies of the delivery.
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

## Conventions that are easy to get wrong

- CSV `x_origin_mm, y_origin_mm` = midpoint of the LEC/first-RSU boundary; module extends toward x = 0.
- CSV `z_baseplate_mm` is really the corrugation/facet reference surface, not the baseplate center.
- Engineer frame to EPIC: `x_EPIC = -x_engineer`; this reflection swaps LEFT/RIGHT chirality.
- Physical beampipe openings come from the EPIC beam pipe (+5 mm buffer); the delivery's openings only validate source placements.
- Disk IDs 0–9 map to ED4, ED3, ED2, ED1, ED0, HD0, HD1, HD2, HD3b, HD4 (file is `HD3b_modules.csv`).
- Modeled sensitive area is intentionally 1.7487% below the catalogue area (inactive strips retained).
- ACTS material map must be generated from the same detector XML used for reconstruction.

## Working rules

- `ES_material/` and delivered CSV/metadata are read-only.
- One step at a time: write a validator/check script in `logs/`, run it, save its `.txt` report, stop for user review.
- Append each step to `logs/rsu_opt_endcap_20261004.md` (files changed, formulas, commands, report paths, open issues). Keep rejected attempts documented.
- Do not claim overlap/compile passes that were not actually run; EIC-shell runs are usually done by the user (`~/weic/eic-shell`, image `26.09.0-stable`).
- Never delete: move to `tmp/retained/<date>/` and log in `tmp/file_actions.log`.
