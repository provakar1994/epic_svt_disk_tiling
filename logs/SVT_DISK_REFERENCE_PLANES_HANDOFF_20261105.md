# Hand-off: zero-material reference planes in front of the SVT endcap disks

Date: 2026-11-05. Written for a fresh Claude session that will implement this.
Read `proj_svt_disk_tiling/CLAUDE.md` first (conventions, retention rules),
then this file, then the last entries of
`proj_svt_disk_tiling/simrec/acc_study/acceptance_study_20261026.md`.

## 1. Goal

Add a study-only geometry option that places a thin, zero-material
(vacuum), sensitive annulus a few mm on the interaction-point side of each of
the 10 SVT endcap disks (ED0-ED4, HD0-HD4). Every primary that reaches a disk
then leaves a "reference hit" with its true crossing point and true local
momentum. The silicon geometry, material and hit collection
(`TrackerEndcapHits`) must stay exactly as they are.

## 2. Why (results that motivate it)

The acceptance study (`simrec/acc_study`) measures per-disk hit efficiency for
pi+ (0.5-20 GeV, |eta| 0.6-3.8, vz = 0 and +/-100 mm). For particles that miss a
disk, it currently infers where they would have crossed with a straight line
from the generated (eta, phi): R = |z_disk - z_vtx| / sinh|eta|. Comparing that
with the true mean hit position for particles that DO hit
(`check_straight_line_projection.py`, z = 0) shows:

| p [GeV]  | D0 median (90%) | D1         | D4 (ED / HD)            |
|----------|-----------------|------------|-------------------------|
| 0.5-1    | 9.4 mm (19)     | 22 (57)    | 53 (124) / 64 (140)     |
| 1-2      | 4.7 (9.5)       | 11 (29)    | 26 (61) / 32 (69)       |
| 2-3      | 2.8 (5.6)       | 6.4 (17)   | 16 (36) / 19 (41)       |
| 18.5-20  | 0.36 (0.7)      | 0.8 (2.2)  | 2.0 (4.6) / 2.5 (5.2)   |

These errors (field bending plus multiple scattering, scaling as 1/p) are too
large for the studies now requested:

- **Collaborator request (row structure):** efficiency loss separately for the
  36 mm-pitch (small |y|) and 33 mm-pitch (large |y|) corrugation regions on
  disks 2-4, and efficiency vs x on all disks. This needs millimetre-level
  positions: rows are 16.5 mm apart and the overlaps are mm-scale.
- **Incidence-angle components:** efficiency vs tan(theta_y) and tan(theta_x)
  from the local direction at the disk. The near-vertex disk loses about 3 points
  at vz = +/-100 mm, and this is understood to be an incidence-angle effect
  (`study_incidence_angle.py`).
- **Low momentum (priority):** finer bins below 3 GeV (0.5-1, 1-2, 2-3 GeV),
  motivated by the tracking efficiency dropping below 1 GeV at large |eta|. At
  low p, the straight-line error exceeds the fiducial margins (30 mm inner and
  40 mm outer), so the current low-p fiducial efficiencies are partly a mapping
  artefact.

A reference plane also gives a clean denominator, "primary reached the disk".
Pions that decay or interact upstream never cross the plane. That splits the
loss into upstream physics versus the disk's own silicon and gap geometry; the
collaborator expects the tile structure alone to cost just under 2%.

## 3. Requirements

1. **Study-only.** Do not change the PR geometry (`silicon_disks_modules.xml`,
   `definitions_craterlake.xml`, etc. on branch `si_disk_hole`, PR 1073).
   Recommended: a new branch from `si_disk_hole` (for example
   `si_disk_refplanes`), plus a new feature XML and a new configuration YAML.
   Ask the user before creating the branch.
2. **Zero material.** Planes are made of `Vacuum`, thin (about 0.1 mm; anything
   from 1 um to 0.5 mm is fine), and must not change any other volume.
3. **Own readout.** Use a new collection, for example `SVTDiskRefPlaneHits`,
   separate from `TrackerEndcapHits`. Encode system/layer so that each plane maps
   one-to-one to a disk; keep the disk's own layer id, or document the mapping.
4. **Zero-energy hits must be recorded on the planes only.** See section 6.1;
   this is the main pitfall.
5. **No overlaps.** `checkOverlaps` and `scripts/checkOverlaps.py` must be
   clean for the new configuration.

## 4. Geometry facts (verified 2026-11-05 in the epic checkout)

- **Disk z** (`compact/tracking/definitions_craterlake.xml`):
  - ED0/HD0 (`InnerTrackerEndcapN/P_zmin`): +/-250 mm.
  - HD1-HD4 (`TrackerEndcapPDisk1-4_zmin`): 450, 700, 950, 1200 mm.
  - ED1-ED4 (`TrackerEndcapNDisk1-4_zmin`): 450, 650, 850, 1020 mm. The negative
    side is built with `reflect="true"`.
- **Layer envelope:** `SiTrackerEndcapLayer_thickness = 10*mm`, and
  `*Layer*_zmin = Mod_zmin - thickness/2`. So each disk layer envelope spans
  roughly z_disk +/- 5 mm. Confirm this in `silicon_disks_modules.xml` (lines
  of the form `zstart=...Layer..._zmin`).
- **Layer envelope rmin** (`silicon_disks_modules.xml` ~L344):
  - 37.0 mm: inner disks (D0).
  - 54.45 mm: middle disks (D1).
  - 47.0 mm: outer disks (D2-D4).
- **Layer envelope rmax:** rmax + 1 um. The disk rmax values are 230 / 405 /
  430 mm (D0 / D1 / D2-4).
- **Beam openings:** the beam openings (lepton and hadron, with offset centres)
  sit inside the envelope rmin region of the disk. The acceptance study reads
  them from `definitions_craterlake.xml` (see `read_disk_boundaries` in
  `simrec/acc_study/plot_disk_hit_efficiency_eta_phi.py`).
- **Corrugation** (`silicon_disks_modules.xml` ~L183):
  - h = 6 mm surface-to-surface, theta = 45 deg, 0.15 mm carbon skin.
  - Modules are placed row-wise from
    `compact/tracking/silicon_disks_tiling/20261001_ES/SVT_endcap_corrugation_rows_33_36.csv`.
  - D0/D1 use uniform 33 mm rows. D2-D4 have 36 mm central and 33 mm outer
    regions.
  - Unverified: the same XML still has `SiEndcapCorrugation_d = 34.77*mm/2`;
    check whether the builder ignores it when a row file is given.
- **Detector type** of the disks: `epic_SiEndcapModuleTracker`
  (`src/SiEndcapModuleTracker_geo.cpp`).
- **Inner support cone** (`compact/tracking/support_service_craterlake.xml`
  ~L683):
  - Starts at `InnerSupportCone_zmin = InnerTrackerEndcapP_zmin + 10 mm`, that
    is |z| = 260 mm, and runs at 45 deg (r ≈ |z| - 3 mm), outward to the support
    cylinder.
  - A plane in front of D1+ must stay inside the cone radius at its z. Also
    check the support cylinders (`TrackerSupportCyl*`) at large r and the
    vertex/barrel layers near D0.
- **Configurations:** top-level XMLs are generated from
  `configurations/*.yml` plus `templates/epic.xml.jinja2` at build time.
  - The acceptance sims use `epic_craterlake_tracking_only.xml`, built from
    `configurations/craterlake_tracking_only.yml`.
  - The `tracking:` features list includes `silicon_disks_modules`.
  - A new feature file (for example
    `compact/tracking/silicon_disks_refplanes.xml`) plus a new YAML (for example
    `configurations/craterlake_tracking_only_refplanes.yml`, a copy with the
    extra feature) is the least invasive route. Check how features map to files
    before relying on this.
- **Build:** use `setup_local.sh` in the epic checkout (mode `1 0`: configure,
  build, install; `2 0` also runs `dd_web_display` and both overlap checks).
  - Per the project CLAUDE.md, EIC-shell runs are usually done by the user
    (`~/weic/eic-shell`, image `26.09.0-stable`).
  - The campaigns ran in `eic_xl:26.09.0-stable` via singularity (see
    `simrec/acc_study/submit_premium_packed.sh`).
  - Do not claim build or overlap passes that were not actually run.

## 5. Suggested design

- **Placement:** one annulus per disk, centred on the IP side just outside the
  layer envelope.
  - HD side: z_plane = z_disk - 5 mm - 1 mm (centre about 6 mm upstream).
  - ED side: z_plane = -(|z_disk| - 6 mm).
  - Keep z_plane as a named constant per disk, so analysis code can read it.
- **Radial extent:**
  - rmin equal to the disk layer envelope rmin. It already clears the beampipe
    and has passed overlap checks.
  - rmax somewhat beyond the disk rmax (for example +20 mm), so particles bent
    just outside the disk are still recorded, but limited by the support cone
    and cylinders at that z.
  - If that is not possible, use rmax = disk envelope rmax.
- **Builder:**
  - Simplest is a small dedicated builder, or an existing generic one, that
    makes N sensitive vacuum Tube volumes with a tracker sensitive type and one
    readout.
  - Candidates to inspect: `src/SimpleDiskDetector_geo.cpp`
    (`epic_SolenoidEndcap`; check whether it supports `sensitive` and
    readout) and existing tracker builders.
  - Do not reuse `epic_SiEndcapModuleTracker`.
- **Mother volume:** place the planes where the disks live, without overlapping
  the disk envelopes. Verify with overlap checks rather than by assumption.
- **Readout:** a plain tracker readout with no segmentation, or a coarse
  CartesianGridXY, with id fields `system:8,layer:4,...`. Use a new system id
  not used elsewhere (check `compact/` for taken ids).

## 6. Pitfalls

1. **Hit filter (most important).**
   - ddsim/npsim normally drops tracker steps below an energy-deposit threshold
     (the ddsim default tracker filter is `edep1kev`). Vacuum deposits nothing,
     so the plane would record nothing.
   - Verify the ePIC npsim defaults with `npsim --dumpSteeringFile`.
   - Then disable the filter for the plane collection only (ddsim
     `filter.mapDict`, or a steering file), leaving `TrackerEndcapHits` on its
     normal filter. Otherwise the silicon efficiency itself changes.
   - Record the steering file in the repo.
2. **Multiple crossings:** low-p particles can loop and cross a plane more
   than once. The extractor should keep the first crossing (earliest time) per
   primary per plane.
3. **Secondaries:** keep only hits whose MCParticle relation
   (`_SVTDiskRefPlaneHits_particle`, same pattern as
   `_TrackerEndcapHits_particle`) points to the primary (generatorStatus == 1).
   Check that DD4hep/EDM4hep attribute the step to the primary and not to a
   secondary (`isProducedBySecondary` / quality bit).
4. **Sensitive volume in vacuum:** make sure a step is actually created and
   recorded in a 0.1 mm vacuum slab (check the smoke-test output for one hit
   per crossing, with momentum filled).
5. **Unchanged silicon:** a 10k-event comparison with and without planes
   (same seed is not bit-identical, so compare statistically) should give the
   same `TrackerEndcapHits` efficiency per disk within errors.
6. **Material map:** the reconstruction material map
   (`scripts/material_map/step8m_..._material-map_map.cbor`) is not needed for a
   sim-only campaign. If eicrecon is ever run on this geometry, vacuum planes
   should not need a new map; confirm before doing it.

## 7. Validation checklist

- [ ] Build with the new config, then `dd_web_display` export: the planes are
      visible upstream of every disk.
- [ ] `checkOverlaps --option m --t 0.01 -c <new xml>` and
      `python scripts/checkOverlaps.py -c <new xml>`: no overlaps.
- [ ] Material scan (or a geantino run) shows zero added material.
- [ ] 10-100 event smoke test (pi+, vz = 0 and +100 mm): `SVTDiskRefPlaneHits`
      present; every primary has at most one hit per plane before looping; z
      equals z_plane; |p| ≈ generated |p|; the MCParticle relation is filled.
- [ ] Silicon-unchanged check (pitfall 5).
- [ ] Log every step in the project log
      (`proj_svt_disk_tiling/logs/rsu_opt_endcap_20261004.md` for geometry;
      `simrec/acc_study/acceptance_study_20261026.md` for campaign and
      analysis).

## 8. After the geometry (for the acceptance-study session)

- **Campaign:**
  - `simrec/acc_study/run_sim.sh` already supports `sim` mode (skip eicrecon).
  - It hard-codes `xml=$DETECTOR_PATH/epic_craterlake_tracking_only.xml`, so add
    an option or a copy for the new XML.
  - Task lists come from `prepare_acceptance_tasks*.sh`; submission is via
    `submit_premium_packed.sh`.
  - The last campaign ran 200 tasks of 100k events in 2h46 on 3 premium nodes.
- **Open user decision:** extend the gun below 0.5 GeV (for example to
  0.2 GeV), and/or add a low-p-enriched sample. Ask before preparing tasks.
- **Extraction:** extend `extract_disk_particles.py`, or write a sibling
  script, to store per primary per disk:
  - Whether the primary crossed the plane.
  - First-crossing x, y, z.
  - Local px, py, pz at the plane.
  - The existing silicon hit mask.
- **Analyses then enabled:**
  - Efficiency maps in true (x,y).
  - Efficiency vs |y| with the 36/33 mm boundary marked, and vs x.
  - Efficiency vs local tan(theta_x) and tan(theta_y).
  - Exact fiducial cuts.
  - Fine low-p bins.
  - Decomposition into "reached the plane" times "hit given reached".

## 9. Contacts and conventions

- **User:** pdatta (LBL).
- Work one step at a time, as in the project CLAUDE.md:
  - Write a check script in `logs/`, run it, save its `.txt` report, and stop
    for user review.
  - Suggested steps: (a) builder and feature XML; (b) build and overlaps;
    (c) filter and smoke test; (d) silicon-unchanged check.
- Never delete files: move them to `<repo>/tmp/retained/<date>/` and log the
  move in `<repo>/tmp/file_actions.log`.
- Write a recorded script before running anything.
- Commits end with the attribution line given in the session.
- Python environment on Perlmutter: `module load conda; conda activate tracking`.
