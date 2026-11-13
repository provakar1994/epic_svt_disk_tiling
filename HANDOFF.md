# Handoff: SVT endcap disk tiling in EPIC

Written 2026-11-13, when Provakar Datta (pdatta) handed the project over for about six weeks.
**Start here.** This note is meant to be enough on its own for the first days. The long logs are
listed in section 8; they are for looking things up, not for reading start to finish.

---

## 0. In one paragraph

We implement the SVT endcap disk layout delivered by Ernst S. (the tiling provider) in the EPIC
DD4hep geometry. Each of the 10 disks (ED0-ED4 at negative z, HD0-HD4 at positive z) is a corrugated
carbon-fibre plate carrying RSU-based sensor modules on both faces. Ernst delivers the module
placements as CSV files. A C++ builder in EPIC turns them into volumes. We then check the geometry
for overlaps and audits, and measure what it does downstream: material (x/X0), single-pion hit
acceptance per disk, and tracking efficiency and resolution. The geometry is complete and validated
for the 2026-11-10 delivery. Both delivered scenarios (rsu_opt = production, rsu6 = all 6-RSU
modules) have full downstream results. What remains is mostly physics follow-up and questions for
Ernst (section 5).

## 1. Day-one setup

**Access.** Everything is under `/global/cfs/cdirs/m3763/pdatta/` (group `m3763`, group-writable) and
`/pscratch/sd/p/pdatta/svt_disk_tiling/` (world-readable since 2026-11-13, not writable by others).

**Recommended way to work.** Treat pdatta's EPIC checkout and its `install/` as a frozen reference.
All the current results were made from them. Put new builds and new outputs in your own space:
1. Clone EPIC: `git clone https://github.com/eic/epic.git`, then `git checkout si_disk_hole` (PR 1073).
   Copy in the untracked helpers from `epic_local/` (see `epic_local/README.md`).
2. Clone this project repo (`git@github.com:provakar1994/epic_svt_disk_tiling.git`, branch `main`)
   into `<your epic>/proj_svt_disk_tiling`. Many scripts expect to sit there.
   - Not in git (gitignored):
     - `ES_material/` (Ernst's deliveries): read-only, copy it over.
     - `matmap/`, `matscan/`, `simrec/acc_study/{results,extracted}`, `simrec/treffi_study/out`:
       outputs. Read them in place from pdatta's copy.
3. Hard-coded paths. Many scripts contain `/global/cfs/cdirs/m3763/pdatta/epic` and
   `/pscratch/sd/p/pdatta/...`. List them with `git grep -l /pscratch/sd/p/pdatta` and
   `git grep -l /global/cfs/cdirs/m3763/pdatta`. When you copy a script for a new step, repoint
   these two roots. Do not edit the old scripts: they are the record of how a result was made.

If you prefer to work directly in pdatta's checkout instead (allowed by group permissions), do not
rebuild `install/` without recording it. Every Step 13/14 result points at that install.

**Software.**
- Container: `eic_xl:26.09.0-stable`. One-shot commands:
  `refplanes/eic_exec.sh "<command>"` (singularity from cvmfs; sources `install/bin/thisepic.sh`).
  Interactive: `eic-shell --version 26.09.0-stable` from your eic-shell install.
- Build EPIC inside the container: `epic_local/setup_local.sh 1 0` (build and install), `1 1` (fresh).
- Analysis Python runs on the host in conda env `tracking` (Python 3.11, uproot/awkward/pandas/
  matplotlib). That env lives in pdatta's home. Recreate it with
  `conda env create -n tracking -f epic_local/conda_tracking_env.yml` after `module load conda`.
- Slurm account `m3763`. Campaigns use `simrec/acc_study/submit_premium_packed.sh`
  (4 premium CPU nodes, 90 tasks per node, about 2 h 40 min for 300 × 100k events). Its
  `#SBATCH --output` points to pdatta's scratch, so pass `--output=` or edit your copy.

## 2. The two repositories and where things are

| What | Where | State on 2026-11-13 |
|---|---|---|
| EPIC (geometry code) | `/global/cfs/cdirs/m3763/pdatta/epic`, branch `si_disk_hole` → `eic/epic` PR 1073 | pushed, HEAD `3b2065e76` = tree of `78ade4686` (merge of a bot formatting commit only) |
| Project (logs, scripts, analysis) | `.../epic/proj_svt_disk_tiling`, branch `main` → `provakar1994/epic_svt_disk_tiling` | pushed |
| Deliveries from Ernst (read-only) | `proj_svt_disk_tiling/ES_material/` (20261001, 20261110, 20261110-r, PDFs) | not in git |
| Delivered tiling as loaded by EPIC | `epic/compact/tracking/silicon_disks_tiling/<delivery>/<scenario>/` | byte-identical copies |
| Material maps (ACTS) | `proj_svt_disk_tiling/matmap/<run>/material-map_map.cbor` | gitignored, 151 GB |
| Per-disk material scans | `proj_svt_disk_tiling/matscan/disk_material_map/<tag>/` | gitignored |
| Sim/rec campaigns | `/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/<campaign>/` | **scratch: purged after ~8 weeks without access** |
| Acceptance results | `proj_svt_disk_tiling/simrec/acc_study/results/` | gitignored |
| Tracking results | `proj_svt_disk_tiling/simrec/treffi_study/out/` (caches on scratch) | gitignored |

Code that matters in EPIC:
- `src/SiEndcapModuleTracker_geo.cpp`: module builder and `tiling-directory` reader (corrugation,
  RSU stack, FPC, x mirror).
- `compact/tracking/silicon_disks_modules.xml`: stack constants. Its six `module_placements`
  select the production scenario `20261110_ES/rsu_opt`.
- `compact/tracking/definitions_craterlake.xml`: disk z, radii, beam-pipe openings.

## 3. Where things stand

**Geometry (EPIC `78ade4686`, Step 13).**
- Delivery `20261110_ES`, production scenario `rsu_opt` (2164 modules). `rsu6` (2150 modules) and
  the facing-flipped `20261110-r_ES` package load through overlay XMLs (section 4).
- Corrugation is built from the delivered `<disk>_rows.csv`. Every bridge FPC points away from y = 0
  (Ernst's convention).
- All four geometries (ES/-r × rsu_opt/rsu6) pass:
  - 0 overlaps: ROOT at 0.01 mm, Geant4 at 0.1 mm;
  - corrugation flats match the rows to 0.000 µm;
  - handedness audit 100 %.

**Downstream results.** Summary with job IDs: `logs/overnight_step13_summary_20261113.md`.

| | rsu_opt | rsu6 vs rsu_opt |
|---|---|---|
| Material, mean x/X0 on the annulus | 0.27-0.31 % X0 per disk; −0.8 to −1.1 % vs the old Step 8q geometry, fully explained | D0 +7.8 % (more RSUs: 456 vs 412); other disks within 0.4 % |
| Hit acceptance, fiducial, vz = 0 | 97.4-98.4 % per disk | D0 +0.25 pt; others within ±0.03 pt; ED4 full-annulus −0.16 pt |
| Hit acceptance, nearest disk at vz = ±10 cm | 94.5 % (ED0 at −10, HD0 at +10) | 94.9 % |
| Tracking resolutions and pulls | unchanged vs the old geometry (ratios 0.99-1.01) | unchanged |
| Tracking efficiency, forward dip 1.6 < η < 1.85, p > 2 GeV | 0.777 | 0.829 (+5.2 pt), see open item 2 |

Talk-ready plots:
- rsu_opt vs rsu6 per disk and vertex: `simrec/acc_study/results/talk/20261113_rsu6_compare/rsu_opt_vs_rsu6_fid_efficiency.pdf` (5 pages).
- The 2026-11-10 SVT DSC talk figures: `simrec/acc_study/results/talk/20261110_svt_dsc/`.

**Nothing pending in Slurm.** All results above are final.

## 4. How to do the common things

Every step so far follows one pattern. Write a script in `logs/` (or the study directory), run it,
keep its `.txt` report next to it, and add a dated entry to the relevant log (section 8). When you
redo something, copy the latest version of the script (Step 13 for rsu_opt, Step 14 for rsu6) under
a new step name. Then update its gates.

**Important:** the Step 13/14 scripts refuse to run unless EPIC HEAD is `78ade4686`. HEAD is now
`3b2065e76`, which has an identical tree (`git diff 78ade4686 3b2065e76` is empty). Copies for new
steps need a new expected HEAD or tree hash.

| Task | Latest script(s) | Notes |
|---|---|---|
| Rebuild and freeze the install | `logs/freeze_install_step13.sh` (run via `refplanes/eic_exec.sh`) | checks the installed XML equals the checkout and the scenario, runs a load test, records checksums |
| Load a non-production scenario | `logs/make_svt_overlay.sh <delivery> <scenario>`; frozen rsu6 copy in `geometry_overlays/step13/rsu6/` | overlay XMLs swap the six `module_placements` paths; run from a directory without `compact/` (paths resolve CWD-first) |
| Overlap and audit checks | `logs/run_svt_step13_all.sh` → `check_svt_step13.sh`; Geant4: `logs/submit_svt_geant_step13.sh` | about 20 min of Geant4 per geometry |
| Visualization ROOT file | `logs/make_svt_visualize.sh <delivery>/<scenario>` | outputs in `out/` |
| ACTS material map | `logs/regenerate_svt_material_map_step13{,_rsu6}.sh`, submitted with `logs/submit_material_map_step13{,_rsu6}.sh` | about 1 h 10 min; must use the same XML as reconstruction; guide: `logs/MATERIAL_MAP_RERUN_GUIDE.md` |
| Per-disk material scan | `logs/run_svt_disk_material_scan_step13{,_rsu6}.sh` + `submit_...` | 6M geantinos in 4 η slices run in parallel. 64 GB is marginal (rsu6 slice 3 was OOM-killed; rerun alone with `logs/rerun_svt_disk_material_scan_step13_rsu6_slice3.sh`): give it more memory or run slices separately. Compare scans with `logs/compare_disk_material_summaries.py` |
| Reference planes (true-crossing acceptance) | `refplanes/step13/` (rsu_opt), `refplanes/step13_rsu6/` | zero-material planes in front of each disk; gates 9a/9b/9c/9e must pass before a campaign |
| Acceptance campaign | `simrec/acc_study/prepare_acceptance_tasks_v4_step13{,_rsu6}.sh`, then `sbatch submit_premium_packed.sh task_lists/<name>/tasks.txt` | π+ 0.5-20 GeV, η ±[0.6, 3.8], vz = 0 and ±100 mm, 300 × 100k events |
| Reconstruction | `prepare_recon_tasks_v4_step13{,_rsu6}.sh <map.cbor> <sha256>`, then the same sbatch with `--time=01:00:00` | checks the map was made from the same XML |
| Acceptance and tracking analysis | `simrec/run_v4_step13{,_rsu6}_phase3.sh <map sha> [acceptance\|tracking]` | about 20 min; comparisons via `compare_refplane_scenarios.py` and `treffi_study/compare_tracking_scenarios_20261113.py` |

Random-seed note. npsim draws the gun and the transport from one random stream. Equal seeds do not
give paired primaries, so scenario comparisons are independent samples and the errors already treat
them that way. Geantino scans with equal seeds are paired.

## 5. Open items, roughly in priority order

1. **Questions for Ernst**, from `logs/module_handedness_convention_20261112.md` sections 3.6 and 4:
   - (a) Ernst's beam-pipe openings are x-mirrored relative to EPIC, so we load his package with
     x_EPIC = −x_engineer. Is his x axis reversed, or his beam pipe?
   - (b) Does every bridge FPC point away from y = 0? We inferred this.
   - (c) Consequence of the mirror: every placed volume keeps the delivered type ID but is
     physically the mirror part (xx0 ↔ xx1). The geometry is correct; only the names are swapped.
     pdatta decided not to fix the names until Ernst answers (a). Fix options are in the note.
2. **Forward tracking-efficiency dip** at 1.6 < η < 1.85 (also smaller dips backward at
   1.3-1.4 and 1.6-1.7).
   - Diagnosed (2026-11-06) as a reconstruction failure: seeds exist, but the CKF returns no
     track. It is not missing silicon.
   - rsu6 reduces it by 5 pt with almost identical silicon coverage. So the dip is sensitive to
     the ACTS surface layout. Do not count this as an rsu6 advantage until it is understood.
   - Proposed next test: rerun EICrecon on failed dip events with CKF debug logging.
   - Details: `simrec/treffi_study/tracking_performance_study_20261106.md` (2026-11-06 and
     2026-11-13 entries).
3. **rsu_opt vs rsu6 decision.** rsu6 buys about +0.25 pt acceptance on D0 for +7.8 % D0 material.
   All plots and numbers exist. This is a physics/engineering call with the SVT group.
4. Small, untraced steep-track acceptance gain (+0.05-0.11 pt on D0/D1 at displaced vertices),
   Step 13 vs the old v3 geometry. Probably row-layout coverage. Low priority.
5. ACTS map vs Geant4 material deviation of −17 to −30 % at 2 < |η| < 3. Inherited from Step 8q,
   not new. Worth a look before final tracking numbers.
6. The `20261110-r` (facing-flipped) package is validated geometrically but has no downstream runs.
   It was meant for systematics.
7. PR 1073 on `eic/epic`: check CI on the PR page after the 2026-11-13 push. pre-commit.ci will
   likely push a formatting commit again. Pull it before your next commit.

## 6. Conventions that are easy to get wrong

- CSV `x_origin_mm, y_origin_mm` = midpoint of the LEC / first-RSU boundary; the module extends
  toward x = 0.
- CSV `z_baseplate_mm` is really the corrugation (facet) reference surface.
- Engineer to EPIC: `x_EPIC = −x_engineer` (see open item 1). Disk IDs 0-9 = ED4, ED3, ED2, ED1,
  ED0, HD0, HD1, HD2, HD3, HD4.
- Ernst's chirality rule: POSITIVE ⇔ sx·sy·sz = +1, with sx = −sign(x_origin), sy = sign(y_origin)
  and sz = −face_sign·facing_sign. The Module Definitions PDF's Left/Right labels are inconsistent.
  Follow the tiling package.
- Beam-pipe openings come from the EPIC beam pipe (+5 mm buffer); the delivery's openings are only
  used to validate.
- RSU silicon = 33.5 inactive + 14 active + 2.5 µm Cu. The modelled sensitive area is 1.75 % below
  the catalogue area on purpose (inactive strips kept).
- The ACTS material map must be made from the same detector XML used in reconstruction. The prepare
  scripts enforce this.
- Corrugation flat edges: the webs are centred halfway between rows. This is our assumption; Ernst
  gave no rule.

More background: `CLAUDE.md` (same list, for AI assistants working in this repo) and `CONCEPTS.md`
(q/p, DCA, pulls, covariance, PWG requirements).

## 7. Working rules pdatta followed (please keep them)

- `ES_material/` and the delivered CSVs are read-only.
- Never delete outputs. Move them to `<epic>/tmp/retained/<date>/` and log the move in
  `<epic>/tmp/file_actions.log`.
- Every run is a script plus a saved report. Every step is a dated entry in the relevant log.
- Never modify another user's files, e.g. Shujie's under `/global/cfs/cdirs/m3763/shujie/`. They are
  group-writable but not ours. `simrec/treffi_study/shujie/modules` is a symlink into them.
- Shujie Li's reference code list: `/global/homes/s/shujie/eic_dir/reference_codebase.md`.

## 8. What to read, and when

Read now (about an hour):
1. This note.
2. `logs/overnight_step13_summary_20261113.md`: the current results, one page.
3. `logs/module_handedness_convention_20261112.md`: the convention and the Ernst questions.

Look up when needed (long, chronological, newest at the bottom):
- `logs/rsu_opt_endcap_20261004.md`: the geometry implementation log. For current context, read
  from "Step 11a" to the end.
- `simrec/acc_study/acceptance_study_20261026.md`: the acceptance study. Its `README.md` explains
  the method.
- `simrec/treffi_study/tracking_performance_study_20261106.md`: the tracking study.
- `logs/MATERIAL_MAP_RERUN_GUIDE.md`: material-map recipe.

Safe to ignore (history): `logs/SVT_ENDCAP_CORRUGATED_*`, `logs/*_HANDOFF*.md`, `logs/step8*_*.md`,
`logs/overnight_plan_*.md`, `logs/plan_rsu_opt_endcap_20261004.md`, `Running_NOTES.md`, and the
roughly 300 per-step check scripts and reports in `logs/`. Look one up only when the main log cites it.

## 9. People

- Ernst S.: tiling provider (deliveries in `ES_material/`); open questions in section 5.
- Shujie Li: EPIC tracking and material-map reference code; owner of the reference scripts the
  campaign runner was modelled on.
- Provakar Datta (pdatta): back around the end of December 2026.
