# SVT acceptance simulation study

Started: 2026-10-26

## Scope

Run single-particle simulation and reconstruction for all combinations of:

- vertex z: `0 mm`, `+10 mm`, `-10 mm`, with `x = y = 0 mm`;
- eta range: `[0.6, 3.8]` and `[-3.8, -0.6]`;
- 50 statistically independent jobs per configuration;
- 100,000 events per job.

This gives 6 configurations, 300 jobs, 5,000,000 events per configuration,
and 30,000,000 events in total. Phi remains uniform over `[0, 360 degrees)`;
the current particle and momentum range are `pi+` and `[0.5, 20] GeV`.

The base runner is `run_sim.sh` in this directory. The EICrecon output
collection list will be expanded to match
`/global/cfs/cdirs/m3763/shujie/worksim/dead_sensor/run_sim_single.sh`.

## Planned organization

1. Make `run_sim.sh` a single-job runner with explicit arguments for tag,
   event count, vertex z, eta minimum, eta maximum, and random seed. Keep the
   compact XML and material-map paths centralized near the top of the script.
2. Build the `npsim` and `eicrecon` commands as Bash arrays. This avoids line
   continuation errors and makes the exact commands easy to log.
3. Use deterministic, unique seeds derived from the configuration index and
   chunk number. Record the seed in every task log and filename metadata.
4. Add a preparation script that writes a tab-separated manifest with one row
   per task. Each row will contain configuration ID, vertex z, eta bounds,
   chunk ID, event count, seed, and output tag. Validate that it contains
   exactly 300 unique tasks and 300 unique seeds before submission.
5. Add a Slurm worker/submission script that selects its task from the manifest.
   Submit as a throttled job array, initially with a conservative concurrency
   limit. Set the final memory and wall time from pilot measurements rather
   than launching 300 unbenchmarked jobs.
6. Store outputs by configuration, with separate `rootfiles/`, `logs/`, and
   `slurm/` directories. Use tags such as
   `vz_p010mm_eta_p0p6_to_p3p8_chunk_001` so every file is self-identifying.
7. Write ROOT files to temporary names and rename them only after successful
   completion. Refuse to overwrite final files or prior logs so reruns cannot
   silently replace campaign data.
8. Run one small local/container smoke test, then one 100k-event Slurm pilot.
   Check event counts, requested PODIO collections, random-seed recording,
   output readability, runtime, peak memory, and disk usage.
9. After the pilot passes, submit the full array and generate a status audit
   from the manifest, ROOT files, and logs. Resubmit only missing or failed
   manifest rows.

## EICrecon output collections

The requested list from the reference runner is:

`EventHeader,MCParticles,SiBarrelRawHits,SiBarrelVertexRawHits,SiEndcapTrackerRawHits,SiBarrelNoiseRawHits,SiBarrelVertexNoiseRawHits,SiEndcapTrackerNoiseRawHits,SiBarrelRawHitsWithNoise,SiBarrelVertexRawHitsWithNoise,SiEndcapTrackerRawHitsWithNoise,MPGDBarrelRawHits,OuterMPGDBarrelRawHits,BackwardMPGDEndcapRawHits,ForwardMPGDEndcapRawHits,SiBarrelTrackerRecHits,SiBarrelVertexRecHits,SiEndcapTrackerRecHits,MPGDBarrelRecHits,OuterMPGDBarrelRecHits,BackwardMPGDEndcapRecHits,ForwardMPGDEndcapRecHits,TOFBarrelSharedRawHits,TOFBarrelSharedRecHits,TOFBarrelClusterHits,TOFEndcapSharedRawHits,TOFEndcapSharedRecHits,TOFEndcapClusterHits,CentralTrackingRecHits,CentralWithoutTOFTrackerMeasurements,CentralTrackerMeasurements,CentralTrackSeeds,CentralTrackSeedParameters,CentralCKFTrajectories,CentralCKFTrackParameters,CentralCKFTracks,CentralCKFTrackAssociations,ReconstructedChargedWithoutPIDParticles,CentralTrackVertices`

The reference runner also uses single-threaded reconstruction, disables silicon
noise injection, and supplies explicit tracking and vertex input tags. These
settings should be carried over together with the collection list, then checked
in the smoke test, because some saved collections depend on those producers.

## Checks noted before implementation

- `run_sim.sh` currently has whitespace after the continuation backslash on
  the `--gun.etaMax` line; this must be fixed before any run.
- The existing submission script launches only one task and points to a missing
  `run_sim_v10mm.sh` inside this directory. It should be replaced by the
  manifest-driven campaign wrapper rather than copied 300 times.
- Vertex values are interpreted as millimetres, consistent with the existing
  `--gun.position "0 0 -10*mm"` command.
- Production submission is intentionally deferred until smoke and 100k-event
  pilot validation establish suitable Slurm resources.

## Progress

- 2026-10-26: Initialized this dedicated study log; inspected the base runner,
  current submission wrapper, and reference EICrecon collection list. No
  simulation jobs submitted yet.
- 2026-10-26: Implemented a parameterized single-task runner, deterministic
  300-row task/manifest generator, and packed premium-QOS wrapper. The wrapper
  defaults to four exclusive CPU nodes and at most 90 serial tasks per node,
  following the measured packing in the dead-sensor reference workflow. With
  300 tasks this produces one wave averaging 75 tasks per node. Scripts were
  prepared for validation only; no campaign was submitted.
- 2026-10-26: Generated `task_lists/acceptance_v1/tasks.txt` and its
  `manifest.tsv`. Validation found exactly 300 commands, 300 unique seeds, and
  50 jobs / 5,000,000 events for each configuration. All three scripts pass
  `bash -n`; their help interfaces and patch whitespace checks also pass.
  `shellcheck` is not installed in the current host environment. No simulation
  or reconstruction command was executed and no Slurm allocation was submitted.
- 2026-10-26: Prepared `run_smoke_test_20261026.sh` for an isolated 10-event
  end-to-end test at vertex `(0,0,0) mm` and eta `[0.6,3.8]`, using the same
  `eicweb/eic_xl:26.09.0-stable` image configured by the production wrapper.
- 2026-10-26: The end-to-end smoke completed with 10 simulated and 10
  reconstructed events and all 39 requested collections. Confirmed with the
  user that `epic_craterlake_tracking_only.xml` is the intended configuration
  and contains the disk modules. An unnecessary second test using the
  `_disk_tiles_new` XML was stopped once this was clarified; its incomplete
  diagnostic output remains isolated under `smoke_20261026_disk_tiles_new`.
- 2026-10-26: Initial production submission `60337236` was accepted on four
  premium nodes but failed before starting any task because Slurm named its
  spool copy `slurm_script`, which broke fallback resolution of the shared
  wrapper. Corrected the fallback to the explicit wrapper filename before
  resubmission. No campaign ROOT files or per-task logs were created by the
  failed allocation.
- 2026-10-26: Corrected submission `60337282` reached its 300-rank `srun`, but
  every rank failed before entering the task runner because Shifter could not
  resolve `eicweb/eic_xl:26.09.0-stable`. Cancelled the allocation after
  confirming zero task logs and zero simulation logs. Changed the packed
  wrapper to the CVMFS Apptainer runtime/image already validated by the smoke
  test before the next submission.
- 2026-10-26: Production job `60337326` was successfully submitted to premium
  QOS on four exclusive CPU nodes. It entered its single 300-task wave using
  the CVMFS `eic_xl:26.09.0-stable` Apptainer image. Confirmed 300/300 task
  logs and 300/300 npsim logs were created, and spot checks at tasks 1, 51,
  101, 151, 201, 251, and 300 matched all six vertex/eta configurations and
  the expected deterministic seeds. The job was RUNNING at handoff.
- 2026-10-26: Production job `60337326` completed successfully with exit code
  `0:0` after `02:41:35`. Final audit found 300 simulation ROOT files, 300
  reconstruction ROOT files, 300 completed task logs, zero task-error logs,
  zero temporary ROOT files, and zero zero-byte ROOT files.
- 2026-10-27: Added the disk-acceptance analysis implementation and dedicated
  README. The workflow streams `sim_*.root` blocks, associates hits through
  stored MCParticle ObjectIDs, counts at most one acceptance per particle/disk,
  keeps the three vertex samples separate, and saves integrated and projected
  2D-bin numerator/denominator summaries with validation and plotting scripts.
- 2026-10-27: Ran the recorded acceptance-analysis smoke workflow on 1,000
  events from each eta side at vertex z=0. Reduction, all numerical invariants,
  and five plot products passed. A review revision changed projection planes
  from sampled hit medians to the exact geometry-defined disk centres in
  `definitions_craterlake.xml`; the isolated v2 smoke rerun also passed.
- 2026-10-27: Added half-open absolute-eta and generated-momentum selections to
  the reducer and created `disk_acceptance_analysis.ipynb`. The notebook exposes
  selections and resource limits in one cell, prints exact commands, requires
  explicit opt-in for reduction, validates outputs, and displays integrated,
  hit/missing, 2D-acceptance, and projection-residual diagnostics inline.
- 2026-10-27: Cut-enabled smoke test with `1 <= |eta| < 2` and
  `1 <= |p| < 10 GeV` passed all invariants and stored the requested ranges in
  NPZ metadata. It selected 160 negative-side and 145 positive-side primaries
  from the two 1,000-event inputs. Notebook JSON and all nine code cells were
  validated; the cells also executed sequentially with the safe run gate off.
- 2026-10-27: Refactored the analysis into a reusable two-stage workflow. The
  one-time extractor now stores one row for every generated primary, including
  zero-hit particles, plus its kinematics, vertex, disk-hit mask/counts, and
  observed hit coordinates. Eta and momentum cuts are applied only by the fast
  reducer, so changing them preserves the denominator without reopening ROOT.
  A 5,000-event-per-side smoke extracted about 0.5 MB total and reused those
  shards for inclusive and cut reductions; both passed all invariants.
- 2026-10-27: Verified the refactor with a like-for-like 5,000-event-per-side
  comparison at `0.9 <= |eta| < 1.2`. The cached-particle result reproduced the
  direct ROOT result exactly for integrated counts, 2D histograms, and
  projection diagnostics (478 negative-side and 498 positive-side primaries).
- 2026-10-27: Implemented the hit-based generated `(eta, phi)` scan suggested
  in the acceptance discussion. It bins each generated primary by momentum and
  direction, counts it at most once per disk when its hit mask is set, and
  divides by all generated primaries in the same angular bin. This requires no
  disk-plane projection. Added a recorded runner and a dedicated steering
  notebook with count and hit-fraction maps for all ten disks.
- 2026-10-27: Ran the scan over all 100 existing extracted `z=0` shards
  (5,000,000 generated primaries per eta side) in five momentum intervals from
  0.5 to 20 GeV. No ROOT files were reread. For `0.5 <= p < 1.5 GeV`, all
  2,048 `(eta, phi)` bins per disk passed the 20-particle plotting threshold.
  The generated-sample integrated hit fractions ranged from 37.7% for HD0 to
  57.0% for ED3; the maps show angular boundaries and their momentum
  dependence. The `-10` and `+10 mm` vertex samples have not yet been extracted,
  so those scans remain to be run after their cached shards are available.
- 2026-10-27: Added a separate measured-hit `(R, phi)` count-only scan using
  each extracted primary's mean associated-hit `(x, y)` per disk. Each primary
  contributes once per disk, independent of raw hit multiplicity; no
  straight-line projection is used. Generated maps for the same five momentum
  intervals at `z=0` with a shared `0–450 mm` radial range and `10 mm` bins.
  All observed mean hit radii were inside the range (maximum 419.7 mm). The
  binned counts exactly match the number of hit-associated primaries placed in
  the maps. A dedicated notebook and recorded runner were added. These maps
  locate recorded hits only and do not provide missing-particle denominators.
- 2026-11-03: Added per-disk hit-efficiency maps in generated `(eta, phi)`
  (`plot_disk_hit_efficiency_eta_phi.py`, runner
  `run_disk_hit_efficiency_eta_phi.sh`), styled like the tracking-efficiency
  reference: 0.1 eta x 10 deg phi bins, efficiency in %, one page per disk.
  Bin efficiency = generated primaries with >=1 associated disk hit / all
  generated primaries in the bin. Each disk is shown over its own eta region:
  eta rows whose phi-integrated, all-momentum hit fraction is >= 1%. A first
  run with an any-hit region (stray hits stretched HD0 to 0.8-3.7) was
  retained under `tmp/retained/2026-11-03/`. Output at z=0:
  `results/disk_hit_efficiency_v1/`. All-momentum in-region efficiencies are
  84.5-88.3% (ED/HD0-2) and 79.4/80.9% (HD3/HD4); they include the partially
  covered edge rows (scalloped inner edge, phi~0 beam-pipe asymmetry). Below
  1.5 GeV they are 0.5-1.6 points lower.
- 2026-11-03: Regenerated the per-disk hit-efficiency maps with the rounded
  bin efficiency [%] printed in every unmasked bin (taller figure, width
  scaled with the number of eta bins). Output: `results/disk_hit_efficiency_v2/`;
  the runner now writes there. Summary CSV is identical to v1.
- 2026-11-03: Added disk-plane views of the same hit-efficiency bins. Only
  the eta bin edges are mapped, to R = |z_disk - z_vtx| / sinh|eta| at the
  nominal disk z; bin contents are unchanged (summary CSV identical to v2).
  This is a display coordinate, not a measured hit radius. Output:
  `results/disk_hit_efficiency_v3/` (`*_disk_view_*.png` and
  `disk_hit_efficiency_disk_view_vz_000mm.pdf`).
- 2026-11-03: Disk views now have an inner-edge zoom panel (|x|,|y| <= 3x
  the innermost display radius) and print the rounded bin efficiency where
  the bin is large enough on the page for the text. Output:
  `results/disk_hit_efficiency_v4/`; summary CSV identical to v3.
- 2026-11-04: Disk views now draw the geometry envelope in red: lepton and
  hadron beam-pipe openings (radius incl. 5 mm bakeout buffer) and the outer
  radius, read from the parent checkout's `definitions_craterlake.xml` (these
  constants are unchanged since the 2026-10-26 campaign). Opening centres are
  in global x: the measured inner hit edges of HD4 (+x 53, -x 78 mm) and ED4
  (+x 57, -x 50 mm) shift the same way as the hadron openings
  (-12.24 and +25.63 mm). The active edge lies ~10-15 mm outside the
  openings. Caveat: the gun stops at |eta| = 3.8, i.e. R ~ 53 mm on HD4, so
  the HD4 +x inner edge may be truncated by the sample, not the silicon.
  Output: `results/disk_hit_efficiency_v5/`; summary CSV identical to v4.
- 2026-11-04: Map pages now run ED4..ED0, HD0..HD4 and use uniform 2 GeV
  momentum bins from 0.5 GeV (last bin 18.5-20 GeV); output
  `results/disk_hit_efficiency_v6/`.
- 2026-11-04: Edge-margin study (`study_disk_edge_margins.py`, runner
  `run_disk_edge_margin_study.sh`, output `results/disk_edge_margins_v2/`):
  phi-integrated efficiency vs per-particle straight-line radius at the disk,
  2.5 mm bins. A v1 criterion (1 pt below plateau, scanned from the XML edges)
  was tripped by narrow interior dips (92-93%) and a slow radial decline;
  `results/disk_edge_margins_v1/` is kept as the record of that attempt. v2
  locates each active edge by its 50% crossing and the band end at
  plateau - 3 pt (3 consecutive bins). Findings at z=0: active edges are
  ~14-29 mm outside XML r_in (r_in = largest opening extent incl. 5 mm
  buffer) and ~24 mm inside XML rmax; edge bands are 6-12 mm wide and almost
  momentum independent. Measured from the XML edges, the needed margins are
  20-28 mm (inner) and 27.5-37.5 mm (outer) for all disks; exceptions are the
  HD1 outer edge (45-60 mm) and ED1 at low p (42.5 mm), where a lower-efficiency
  outer annulus (~92-93%) rather than the edge itself trips the threshold.
  As % of XML width the margins are not uniform (5-8% on large disks, 12-18% on
  ED0/HD0), so a fixed mm margin from the XML edges is preferred. Margin choice
  pending the user's decision.
- 2026-11-04: Added fiducial summaries (`results/disk_hit_efficiency_v7/`).
  Fiducial annulus per disk: XML r_in + 30 mm <= R < rmax - 40 mm, with R the
  per-particle straight-line radius at the nominal disk z; margins chosen from
  `results/disk_edge_margins_v2/`, fixed for all momenta. First page of both
  PDFs: per-disk fiducial efficiency for 0.5-2.5, 10.5-12.5 and 18.5-20 GeV
  (also `fiducial_summary_vz_000mm.png`); first page of each disk: fiducial
  efficiency vs momentum (`*_fiducial_vs_p_*.png`); numbers in
  `fiducial_efficiency_vz_000mm.csv`. At z=0 the all-momentum fiducial
  efficiencies are 96.05-96.63% (binomial errors ~0.01%); 18.5-20 GeV gives
  96.2-96.9%, 0.5-2.5 GeV gives 94.3-96.2% (largest drop on HD4 and ED4). The
  annulus covers ~80% of the XML disk area (61% for ED0/HD0). Map pages and
  their summary CSV are unchanged from v6. Two v7 reruns that only differed in
  summary-page label placement were moved to `tmp/retained/`.
- 2026-11-04: Correction to the margin choice above: the "27.5-37.5 mm outer"
  statement was based on three momentum bins only. Across all ten bins at z=0
  the v2 outer band end lies further in than rmax - 40 mm on ED1 (up to 57.5),
  HD1 (up to 75), ED0 (47.5, one bin) and HD0 (50, one bin). In those bins the
  50% edge is unchanged (381.5-383 mm on D1, 205.5-205.7 mm on D0) while the
  band end wanders (330-362 mm on D1), i.e. the plateau - 3 pt threshold is
  catching the lower-efficiency (~92-93%) outer ring and interior dips, not
  the edge fall-off. The 30/40 mm fiducial cut still excludes the edge
  fall-off on every disk and is kept.
- 2026-11-04: Extracted and processed the vz = -10 and +10 mm samples (two
  parallel agents). Runners now take an optional vertex argument
  (`run_disk_hit_efficiency_eta_phi.sh [vz]`, `run_disk_edge_margin_study.sh [vz]`;
  default 0 keeps the z=0 paths). New `run_extract_vertex.sh <vz>` writes each
  displaced vertex to its own root (`extracted/acceptance_v1_vz_m010mm/`,
  `extracted/acceptance_v1_vz_p010mm/`) because the extractor rewrites
  `extraction_manifest.csv` with only the current run's rows. Each: 100 shards,
  5,000,000 events per side, no temporary files. Outputs:
  `results/disk_hit_efficiency_v7_vz_{m010,p010}mm/`,
  `results/disk_edge_margins_v2_vz_{m010,p010}mm/`, same 30/40 mm fiducial
  annulus. All-momentum fiducial efficiencies agree with z=0 within 0.15
  points on every disk (ED0 96.48/96.61/96.73 and HD0 96.38/96.25/96.10 for
  -10/0/+10 mm show the largest, mirror-symmetric shifts); 0.5-2.5 GeV values
  agree within 0.2 points. Edge-study inner margins are unchanged (<= 28.2 mm);
  outer margins show the same D0/D1 pattern as z=0.
- 2026-11-04: Disk views now draw the fiducial annulus (magenta dashed
  circles at XML r_in + 30 mm and rmax - 40 mm) next to the red XML circles.
  Regenerated all three vertices with parallel agents:
  `results/disk_hit_efficiency_v8/`, `..._v8_vz_m010mm/`, `..._v8_vz_p010mm/`.
  Fiducial and map summary CSVs are identical to v7 for every vertex.
- 2026-11-04: Combined the cross-disk fiducial summary of all three vertices
  into `results/fiducial_summary_all_vertices_v8.pdf` (pages vz = -10, 0,
  +10 mm), redrawn from the v8 fiducial CSVs with the same plotting function
  (`make_fiducial_summary_all_vertices.py`, runner
  `run_fiducial_summary_all_vertices.sh`); pypdf is not available in the env.
- 2026-11-04: Verified the displaced-vertex samples are +/-10 mm (1 cm), not
  +/-10 cm: run_sim.sh passes `--gun.position "0 0 ${vertex_z_mm}*mm"`, the
  task list gives 10 / -10, and the primaries' MCParticles.vertex.z in the sim
  ROOT files and the extracted shards are exactly +/-10.000 mm. The mm
  convention came from the original submission command (`-10*mm`, see the
  2026-10-26 notes). The user intended +/-10 cm; that needs a new campaign.
- 2026-11-04: Prepared the +/-10 cm campaign `acceptance_v2_vz100mm` (not yet
  submitted). `prepare_acceptance_tasks_vz100mm.sh` is a copy of the v1
  generator with vertices +/-100 mm (run_sim.sh takes mm), 4 configurations x
  50 chunks x 100k = 20M events, seed base 42000000 (no overlap with v1).
  Validated: 200 tasks, 5M events per configuration, unique seeds. Output
  root /pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v2_vz100mm.
  Geometry: the current install (epic c5da03dcf). Relative to the v1 campaign
  (2026-10-26 install, same module-tiled disks: npsim log shows
  epic_SiEndcapModuleTracker) it differs only by the Step 8p support-cone start
  (+5 mm), the main-branch BIC layer-1 update and a calibration LUT/material-map
  constant; no disk geometry change. Smoke test
  `run_smoke_test_20261104_vz100mm.sh` (10 events, vz = +100 mm) passed:
  10/10 events sim and rec, all 39 collections, all primaries at z = 100.0 mm
  (`validate_smoke_test.py` now takes optional OUTPUT_DIR TAG VERTEX_Z_MM).
  Downstream: VERTEX_LABELS gains +/-100 (m100/p100); run_extract_vertex.sh and
  both plotting runners accept -100/100 (extraction roots
  extracted/acceptance_v2_vz_{m100,p100}mm).
- 2026-11-04: Submitted the +/-10 cm campaign as Slurm job `60805090`
  (`sbatch --nodes=3 --time=03:30:00 submit_premium_packed.sh
  task_lists/acceptance_v2_vz100mm/tasks.txt`; premium QOS, 200 tasks in one
  wave, ~67 per node, image eic_xl:26.09.0-stable from CVMFS). Time limit
  raised from 3:00 to 3:30 because acceptance_v1 needed 2:41 at 75 tasks/node.
  Task logs: /pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/slurm_tasks/60805090/;
  job log: .../acc_study/slurm/svt-acceptance-60805090.out.

  Important notes for comparing acceptance_v2_vz100mm with acceptance_v1:
  * Vertex units: acceptance_v1's displaced samples are +/-10 mm (1 cm), not
    the intended +/-10 cm; acceptance_v2_vz100mm is the intended +/-10 cm
    (run_sim.sh argument 100 = 100 mm). Configuration names: vz_p100mm, vz_m100mm.
  * Geometry differs from acceptance_v1. v1 used the 2026-10-26 install (branch
    si_disk_hole, before the 10-29 main merge, with the craterlake_tracking_only
    configuration already selecting silicon_disks_modules: npsim log shows six
    epic_SiEndcapModuleTracker disks). v2 uses the install built 2026-11-03 from
    c5da03dcf. Differences in what epic_craterlake_tracking_only.xml loads
    (git diff d8864c1a6..c5da03dcf plus the v1 working-tree state):
      - support_service_craterlake.xml: InnerSupportCone_zmin =
        InnerTrackerEndcapP_zmin + 10 mm (was + 5 mm), i.e. both inner support
        cones start at |z| = 260 mm instead of 255 mm (Step 8p overlap fix).
      - ecal/bic: BIC layer-1 update from main (#1200, flat imaging staves,
        carbon side walls); file moved to compact/ecal/bic/bic_layer1_only.xml.
        Outside the tracker volume.
      - calibrations.xml: newer bic_edepToNpe_layer.lut URL (BIC readout only).
      - definitions_craterlake.xml: adds the constant material-map =
        calibrations/materials-map.cbor (reconstruction input naming only;
        run_sim.sh still passes the step8m material map explicitly).
    Disk positions, openings, outer radii and module tiling are unchanged.
    The support-cone shift adds or removes a little material in front of D1+
    at small radii; expected effect on disk hit efficiency is negligible, but
    a z=0 rerun on the v2 geometry would be the clean check if v1 and v2
    numbers are ever compared at the 0.1-point level.
  * eta coverage at +/-10 cm: the gun is still 0.6 <= |eta| <= 3.8 about the
    displaced vertex. All fiducial annuli stay inside it (tightest: ED0/HD0
    from the near vertex, 150 mm away, where R = 190 mm is eta ~ 0.72), but
    the innermost silicon edge of the far disks is sampled less (e.g. HD4 from
    vz = -100 mm: R = 53 mm is eta ~ 3.89, beyond 3.8). Outside the fiducial
    region, so the summary numbers are unaffected; the inner-edge maps of
    HD4/ED4 from the far vertex are truncated.
  * Pending after the job: audit (200 sim + 200 rec ROOT files, no task
    errors), then `./run_extract_vertex.sh +/-100`,
    `./run_disk_hit_efficiency_eta_phi.sh +/-100`,
    `./run_disk_edge_margin_study.sh +/-100`, and extend
    make_fiducial_summary_all_vertices.py to the +/-100 mm pages.

- 2026-11-04 (job 60805090 finished, acceptance_v2_vz100mm):
  * sacct: COMPLETED 0:0, elapsed 02:45:40 on 3 premium nodes.
  * Outputs: 200 sim + 200 rec ROOT files, 0 leftover tmp files, 0 zero-byte
    ROOT files, 200/200 task logs report completion.
  * Next: extraction for vz = +100 and -100 mm (run_extract_vertex.sh), then
    plots and edge study.

- 2026-11-04 (vz = +/-100 mm results, v2 geometry, campaign acceptance_v2_vz100mm):
  * Extraction: extracted/acceptance_v2_vz_{p100,m100}mm, 2 eta signs x 50
    shards x 100k primaries each (logs/extract_vz_*100mm_20261104.log; the
    first -100 attempt failed only because logs/ did not exist yet when it
    started, rerun OK).
  * Plots: results/disk_hit_efficiency_v8_vz_{p100,m100}mm; edge study:
    results/disk_edge_margins_v2_vz_{p100,m100}mm. Five-vertex summary:
    results/fiducial_summary_all_vertices_v8_5vtx.pdf (the 3-vertex
    fiducial_summary_all_vertices_v8.pdf is kept unchanged).
  * All-momentum fiducial efficiency [%] (compare_fiducial_vertices.py),
    L = |z_disk - z_vtx| in mm:
        disk   vz=-100       -10      0        +10      vz=+100
        ED4    96.64(920)    96.43    96.39    96.37    96.14(1120)
        ED3    96.80(750)    96.60    96.56    96.53    96.37(950)
        ED2    96.74(550)    96.64    96.63    96.63    96.58(750)
        ED1    96.05(350)    96.45    96.51    96.54    96.67(550)
        ED0    93.98(150)    96.48    96.61    96.73    97.24(350)
        HD0    96.93(350)    96.38    96.25    96.10    93.23(150)
        HD1    96.25(550)    96.12    96.10    96.07    95.66(350)
        HD2    96.21(800)    96.32    96.33    96.34    96.60(600)
        HD3    96.02(1050)   96.24    96.26    96.29    96.85(850)
        HD4    95.71(1300)   96.03    96.05    96.13    96.63(1100)
  * Main finding: the disk nearest the displaced vertex (L = 150 mm) loses
    ~3 points (ED0 94.0 at -100, HD0 93.2 at +100; mirror-symmetric), D1 at
    L = 350 mm loses ~0.5. Far disks shift by +/-0.3, in the direction of a
    shorter/longer decay-in-flight path.
  * Incidence-angle check (study_incidence_angle.py,
    results/incidence_angle_d0_d1_v1.png, logs/incidence_angle_20261104.log):
    D0/D1 efficiency vs tan(theta) = R/L agrees within ~1 point across all
    five vertices where they overlap, falling from ~97% (tan 0.2-0.3) to
    ~94% (tan 0.7) and ~87% (tan 1.2). The near disk at L=150 mm samples
    tan(theta) 0.45-1.27 inside the fiducial annulus vs 0.27-0.76 at z=0, so
    the drop is an incidence-angle effect, not vertex-specific.
  * Hypothesis (NOT verified): module-to-module overlaps between modules at
    different z cover a gap only while overlap > dz * tan(theta); at large
    angle the projected overlap closes. Supported by the HD0 (+100) disk view:
    low arcs (75-88%) near phi = 90/270 deg at fixed radii, growing with R.
    Check: compare arc positions with the module y-edges, or measure dz and
    the overlap in the tiling XML.
  * Geometry caveat: ±100 mm uses the v2 install (c5da03dcf; disks
    unchanged, support cone +5 mm), so v1 vs v2 differences below ~0.1-0.2
    point are not interpretable.

- 2026-11-04: summary PDF reduced to vz = -100, 0, +100 mm
  (results/fiducial_summary_all_vertices_v8_vz_m100_0_p100.pdf); the +/-10 mm
  pages were dropped at the user's request (within 0.15 point of z=0). The
  5-page version was moved to tmp/retained/2026-11-04/.

- 2026-11-05: straight-line projection error (check_straight_line_projection.py,
  logs/check_straight_line_projection_20261105.log; z=0, 10 shards per side,
  primaries that hit the disk, mean hit vs straight-line point at the same z).
  Median |d| [mm] (90th percentile in brackets):
      p [GeV]     D0          D1          D4 (ED / HD)
      0.5-1       9.4 (19)    22 (57)     53 (124) / 64 (140)
      1-2         4.7 (9.5)   11 (29)     26 (61)  / 32 (69)
      2-3         2.8 (5.6)   6.4 (17)    16 (36)  / 19 (41)
      18.5-20     0.36 (0.7)  0.8 (2.2)   2.0 (4.6) / 2.5 (5.2)
  Scales as 1/p (field bending + scattering). Consequences:
  * Row-level studies (16.5 mm row spacing, mm-scale overlaps, tan theta_y)
    are NOT possible with the straight-line position except at high p on D0/D1.
  * At low p the fiducial cut itself is smeared (errors comparable to or larger
    than the 30/40 mm margins on D1-D4), so part of the low-p fiducial loss can
    be particles that really land in the hole or beyond rmax. The earlier
    statement that the low-p drop is "not explained by the straight-line
    mapping" is withdrawn until checked with true crossing points.
  * Next step under discussion: a zero-material sensitive plane in front of
    each disk to record the true crossing point and direction of every primary.

- 2026-11-06: reference-plane campaign and analysis tooling prepared (nothing
  submitted, no task list created). The planes themselves (SVTDiskRefPlaneHits,
  refplanes/) are built by the geometry session; this entry covers only the
  acceptance-study side. Interface used (refplanes/, read only):
  generated/epic_craterlake_tracking_only_refplanes.xml, npsim_refplanes_steering.py,
  plane_map.csv (planes 6 mm on the IP side, system 55/54 with barrel 2/3 and
  layer 0-4 for ED/HD; rmin = disk XML *_rmin; rmax = disk rmax + 20 mm).
  * run_sim.sh: opt-in env overrides ACC_XML (compact XML; default unchanged)
    and ACC_STEERING (npsim --steeringFile, placed before the other options so
    command-line options still win; default none). The sim log now also
    prints "Compact XML:" / "Steering file:" and the sha256 of both. Checked
    with a stub npsim (check_run_sim_overrides_20261106.sh,
    logs/check_run_sim_overrides_20261106.txt): with no overrides the npsim
    command line is identical to the original; overrides appear as intended;
    a missing steering file exits 2. No real npsim run.
  * prepare_acceptance_tasks_refplanes.sh: campaign acceptance_v3_refplanes,
    vz = 0, +100, -100 mm x eta [0.6,3.8] / [-3.8,-0.6] x 50 chunks x 100k =
    300 tasks, 30M events, mode sim, seeds 43000001-43005050 (v1
    41000001-41005050, v2 42000001-42003050; the script also checks overlap
    against every task_lists/*/manifest.tsv), each line prefixed
    ACC_XML=<refplanes xml> ACC_STEERING=<refplanes steering>. Real mode
    refuses if those files are missing. Tested only in dry-run mode
    (DRY_RUN_TASK_ROOT; check_prepare_refplanes_dryrun_20261106.sh,
    logs/check_prepare_refplanes_dryrun_20261106.txt): 300 lines, 300 unique
    seeds and tags, 6 x 50 tasks, 5M events per configuration, no overlap.
    Dry-run output retained in tmp/retained/2026-11-06/ (2 dirs; the first
    attempt stopped on a SIGPIPE in the audit script, logged).
    Wall time: 300 tasks on 4 x 90 slots = one wave at 75 tasks/node, same
    packing as acceptance_v1. Measured npsim time per 100k task (sim logs
    Started/Finished): v1 mean 2h23 max 2h38 (75/node), v2 mean 2h23 max 2h43
    (67/node). The default 3:00 limit leaves only ~15-20 min margin on the
    slowest task; submit with --time=03:30:00 as for v2.
  * extract_disk_particles_refplanes.py (+ run_extract_refplanes.sh <vz>):
    sibling of extract_disk_particles.py (unchanged); silicon fields come from
    the original append_block(). Adds per disk: plane_mask (plane_reached
    bits), plane_crossings, first crossing (earliest time) plane_{x,y,z}_mm,
    plane_t_ns, plane_p{x,y,z}_GeV, plane_secondary_flagged. Accepted plane
    hit = linked to a generatorStatus==1 pi+ and EDM4hep quality bit 30
    (producedBySecondary) not set. Shard metadata: total / accepted /
    dropped-not-primary / secondary-flagged / other-side plane-hit counts,
    plane_map content and sha256. Mapping data-driven from plane_map.csv via
    decoded (system, barrel, layer); unknown ids are an error. One extraction
    root extracted/acceptance_v3_refplanes with one manifest per vertex.
    Tests: (a) old file (v2 vz=+100 chunk 001, both sides, no plane
    collection; check_extract_refplanes_oldfile_20261106.sh): all 16 particle
    and silicon arrays bit-identical to the old shards, plane fields
    empty/NaN, 7 s per 100k-event file. (b) Hand-made block
    (check_extract_refplanes_synthetic_20261106.py): first crossing,
    multiple crossings, secondary flag, other-side and unmapped ids behave as
    specified. (c) Real smoke files (below).
  * analyze_refplane_efficiency.py (+ run_refplane_efficiency.sh [vz...]):
    definitions in the docstring. Denominator: primaries with plane_reached
    on disk d; numerator: those with >=1 TrackerEndcapHits hit on d. True
    point = first plane hit propagated straight along its own momentum to
    z_disk (6 mm). Selections on the true point: reached (no cut); nomargin =
    r < XML rmax and outside both buffered openings; fid = XML r_in + 30 <= r
    < rmax - 40 (the old annulus, now on the true point). Momentum bins
    [0.5,0.6,...,1.0,2,3,5,...,19,20]; the last bin 19-20 GeV is implemented
    as [19, 20.01) to include the gun endpoint (user's choice of a 1 GeV last
    bin). Outputs per vertex in results/refplane_efficiency_v1/vz_*/:
    integrated and vs-p efficiencies, family A/B table (disks 2-4), the
    decomposition reached/generated x hit/reached in the straight-line
    acceptance and straight-line fiducial annulus, the comparison with the
    v8 published straight-line fiducial numbers and with the old definition
    recomputed on the same sample, histograms.npz, summary.txt, a PDF and
    PNGs (overview, per disk: vs p + decomposition, 2D map, profiles vs y,
    |y|, x, tan theta_x/y). Streams shard by shard.
    Choices: 2D map 4 mm bins. Full statistics (5M per side) give a median
    of ~50 primaries per 4 mm bin on D2-D4 (from the synthetic test, scaled),
    i.e. ~3% per-bin error at 96%; 2 mm bins would give ~12. Row structure
    (18 / 16.5 mm row spacing, mm-scale overlaps) is resolved in the 1 mm 1D
    profiles, which have far more statistics. tan theta_x = px/|pz|,
    tan theta_y = py/|pz| (positive = toward +x / +y on both sides).
  * Row families: the A (36 mm) region is not symmetric in y. From the CSV
    (row band = row_y +/- pitch/4), A covers ED2/HD2 -144..126, ED3
    -180..162, ED4 -216..234, HD3 -207..207, HD4 -279..279 mm. The
    efficiency vs signed y is therefore the primary plot; the |y| plot marks
    both boundaries. check_row_family_y_convention_20261106.py
    (logs/check_row_family_y_convention_20261106.txt) uses the +/-3 mm row
    surface offsets seen in old silicon hit z. Result: CSV row_y is global y
    on ED2-ED4 and HD2, the disks where the sign is testable. HD3/HD4 and
    D0/D1 are mirror-symmetric, so the sign does not matter there.
  * Synthetic chain test (check_refplane_analysis_synthetic_20261106.sh;
    make_synthetic_refplane_shards_20261106.py; TOY plane fields on real old
    silicon shards, 3 shards per side and vertex): runs end to end for
    0/+100/-100 in 143 s (~3 s per shard, so ~15 min for the full
    campaign). The straight-line fid efficiency recomputed by the new code
    agrees with the v8 published values (e.g. vz=-100: HD4 95.73 vs 95.71, ED0 93.89 vs 93.98; 3 shards only). No
    physics content.
  * Real smoke files (geometry session, /pscratch/.../refplanes/smoke/,
    4 x 100 events, vz = 0 and +100 only; check_refplanes_smoke_chain_20261106.sh,
    validate_refplanes_shards_20261106.py,
    logs/check_refplanes_smoke_chain_20261106.txt; outputs in
    tmp/refplanes_smoke_chain_20261106/). Extraction, validation and analysis
    all ran. Plane hit z equals z_plane exactly; |p_plane|/p_gen median
    1.000 (min 0.985); all first-crossing times > 0; no multiple crossings in
    400 events; true point vs mean silicon hit median 0.4-1.7 mm (90%
    <= 3 mm), consistent with the +/-3 mm corrugation and module overlaps.
    Per 100 events: 418-1143 plane hits, 77-805 dropped (secondaries), 1-11
    primary-linked hits flagged producedBySecondary (excluded). One primary
    has a silicon hit with no plane crossing: HD4, r = 54 mm, below the HD4
    plane rmin (63.5 mm).
  * FINDING for the geometry session: plane rmin = XML *_rmin, the circle
    circumscribing both offset openings. On HD3/HD4 (not on ED3/ED4/HD2,
    whose silicon starts outside plane rmin) the silicon reaches smaller radii on the side away from the
    hadron-opening offset. In the old z=0 extraction about 1% of HD4
    silicon-hit primaries have r < 60.7 mm (plane rmin 63.5), and about 0.1%
    of HD3 have r < 50.6 mm (plane rmin 52.3). Such particles never enter
    the denominator, so the inner edge of HD3/HD4 is not sampled in the
    nomargin selection. The fid selection (r >= r_in + 30) is unaffected.
    Either accept this, or give the planes the opening shape (or the
    lepton-opening radius) as the inner boundary.
  * Interpretation note: on the smoke files, nomargin efficiency (~75-90%)
    is far below fid (~97-100%). The XML envelope includes regions that the
    tiling does not cover: around the openings (a square-ish untiled
    region, visible in the synthetic 2D maps) and near rmax. So nomargin
    measures coverage of the XML envelope, not tile gaps alone. The fid and
    A/B numbers in the tiled region are the ones to compare with the
    collaborator's ~2% expectation.
  * Not done / pending: the real task list and submission (needs the user),
    the campaign extraction and analysis, and a vz = -100 mm smoke test
    (none exists; the analysis code is identical for that vertex).
  * Update, v2 plane geometry (2026-11-06, after the geometry session's
    Step 9 v2; logs/rsu_opt_endcap_20261004.md Step 9). The FINDING above
    (HD3/HD4 plane holes) is resolved: v2 planes are off-centre annuli
    about the smallest circle enclosing both openings. There are 7 plane
    detectors: 54 = HD0/HD1 (layers 0/1), 55 = ED0-ED2 (layers 0-2),
    56/57/58 = HD2/HD3/HD4, 86/87 = ED3/ED4 (layer 0), with barrel 3 (HD) or
    2 (ED). plane_map.csv gains center_x_mm, center_y_mm,
    r_inner/r_outer_about_center_mm, uncovered_*, note.
    - Extractor: no logic change was needed, because the mapping is
      already keyed on (system, barrel, layer) through plane_map.csv.
      Verified that all 10 v2 ids map to the right disk; docstring updated.
    - Analysis: it never assumed centred planes, because the selections
      use the disk XML boundaries. New: it reads the plane annulus about
      its centre (a 9-column map falls back to a centred annulus), counts
      first crossings off the annulus (first_crossing_off_plane, must be
      0), draws the plane edges on the 2D maps, and prints the min as well
      as the median of |p_plane|/p_gen. Nothing assumes
      |p_plane| ~ |p_gen|; the propagation uses the plane momentum
      direction.
    - Validator: same off-plane test, plus an OVERALL PASS/FAIL line.
      Synthetic generator: on-plane test about the centre. The synthetic
      test was NOT rerun after these edits; the real smoke chain below
      exercises the same code.
    - The v1-plane smoke-chain output and report were moved to
      tmp/retained/2026-11-06/ (logged).
    - Rerun check_refplanes_smoke_chain_20261106.sh on the 6 v2 smoke
      files (vz = 0, +100, -100; both eta signs; 100 events each; the
      -100 pair is new). Report: logs/check_refplanes_smoke_chain_20261106.txt.
      Result: OVERALL PASS, 0 problems.
      0 silicon-hit primaries without a plane crossing (HD4 included); 0
      first crossings off the annulus; plane z = z_plane exactly; all times
      > 0; no multiple crossings. |p_plane|/p_gen median 1.000, but the
      minimum is 0.841 on HD3/HD4 (vz=0 fwd: the interacted primary the
      geometry session reported). True point vs mean silicon hit median
      0.4-2.0 mm (90% <= 3.2 mm). Primary-linked fraction of plane hits:
      55-81% per file (e.g. vz0_fwd 352 accepted, 277 dropped, 9 flagged
      out of 641). HD4 first crossings reach r = 470 mm (the off-centre
      r_outer is 462 about x = -12.2). Analysis wrote all three vertex
      directories (39 files each); fid efficiencies are 94-100% with
      N ~ 30-50 per disk, so there is no statistical content.
  * Campaign status (from the coordinator): acceptance_v3_refplanes
    (task_lists/acceptance_v3_refplanes, 300 tasks, sim only) was
    generated and submitted by the coordinator as Slurm job 60887803
    (premium, 4 nodes, --time=03:30:00) at about 05:00 UTC on 2026-11-06.
    A 20-event pre-campaign run through run_sim.sh with the ACC_XML /
    ACC_STEERING overrides succeeded, with plane hits at all 10 plane z
    values (report proj_svt_disk_tiling/refplanes/precampaign_runsim_test.txt;
    run by the coordinator/geometry session, not by this session).
    Campaign extraction not started; jobs still running.

## 2026-11-06 morning summary: true-crossing (reference-plane) efficiency, acceptance_v3_refplanes

Written by the coordinating session. Numbers are copied from
`results/refplane_efficiency_v1/vz_*/summary.txt`; nothing was rerun by hand.

**Runs**
- Slurm 60887803: COMPLETED in 02:40:23, exit 0.
  - 300/300 task logs end with "=== Completed task"; no Traceback, fatal or
    G4Exception lines.
  - 300 sim files of about 160 MB each in
    /pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v3_refplanes/.
- Extraction: `./run_extract_refplanes.sh 0|100|-100`, run in parallel,
  2026-11-06 07:40 UTC. Logs: `logs/extract_refplanes_vz_*_20261106T074007Z.log`.
- Analysis: `./run_refplane_efficiency.sh`. Log:
  `logs/refplane_efficiency_20261106T075625Z.log`.
- Each vertex has 100 shards and 10M primaries.

**Gates**
- First crossings off the plane annulus: 0 on every disk and vertex. PASS.
- |plane z − z_plane| < 0.05 mm everywhere.
- Median |p_plane|/p_gen is 0.9996–0.9999.
- Median |true point − mean silicon hit| is 0.41–1.78 mm.
- Silicon-hit primaries without a plane crossing: 0–12 per disk, out of about
  3M reached, so ≤ 4e-6. This is not exactly 0 as in the 100-event smoke
  test; likely scattered or curling entries, not inspected.
- Multi-crossing primaries: ≤ 14 per disk. Negligible.

**Main result (vz = 0)**
Fiducial efficiency (true crossing point inside the 30/40 mm fiducial
margins; denominator = plane reached):

| disk | old straight-line fid (this sample) | true-point fid | diff (pts) |
|---|---|---|---|
| ED4 | 96.41 | 98.31 | +1.91 |
| ED3 | 96.58 | 98.25 | +1.67 |
| ED2 | 96.66 | 98.04 | +1.37 |
| ED1 | 96.52 | 97.57 | +1.05 |
| ED0 | 96.62 | 97.42 | +0.80 |
| HD0 | 96.23 | 97.41 | +1.18 |
| HD1 | 96.10 | 97.55 | +1.45 |
| HD2 | 96.36 | 98.11 | +1.76 |
| HD3 | 96.29 | 98.35 | +2.07 |
| HD4 | 96.08 | 98.39 | +2.31 |

Statistical errors are ±0.01 pts. The old fid values in this sample
reproduce the published v8 values to within 0.03 pts.

- **Decomposition.** Old straight-line fid = (fraction that reaches the plane)
  × (hit given reached).
  - Reached fraction: 97.7–99.2%.
  - Hit given reached: equals the true-point fid to within 0.01 pts.
  - So the old 3.4–3.9% inefficiency was about half "never got there"
    (multiple scattering, curling and interactions before the disk, larger
    for the far disks) and half genuine module or coverage loss.
- **Momentum dependence.**
  - The true-point fid is flat in p: within about 0.3 pts from 0.5 to 20 GeV
    on every disk.
  - The old definition's low-p deficit disappears. At 0.5–0.6 GeV the
    old-minus-new difference was −5.2 pts on ED4 and −2.0 pts on ED0/HD0.
  - Remaining inefficiency is about 1.6–2.6%. It comes from row gaps (visible
    as horizontal bands in the xy maps) and the retained inactive strips.
- **A (36 mm) vs B (33 mm) rows, fid, vz = 0.**
  - A ≈ 98.3% on all of ED2–ED4 and HD2–HD4.
  - B is lower on ED2/HD2 (97.52 / 97.75) and ED3/HD3 (98.13 / 98.24).
  - B equals A within errors on ED4/HD4.
  - The B-only disks ED0/ED1/HD0/HD1 are at 97.4–97.6%.
- **Vertex dependence.**
  - Within about 0.8 pts of vz = 0, except the disk nearest the vertex:
    - HD0 at vz = +100: 94.43% (vz = 0: 97.41);
    - ED0 at vz = −100: 94.43% (vz = 0: 97.42).
  - These are symmetric, as they should be.
  - The HD0 map at vz = +100 shows wider, darker row-gap bands. Plane-to-vertex
    distance is 144 mm, so tanθ reaches about 1.3 at the fid edge. Steep
    incidence in y appears to defeat the row overlap. This is a physical
    geometry effect, not an analysis fault (to be confirmed by the user).
- **nomargin and reached selections (71–89%).**
  - These use the XML disk envelope, so they include untiled area.
  - They are not module efficiencies. A tiling-footprint boundary is needed if
    a no-margin number is wanted.

**Outputs:** `results/refplane_efficiency_v1/vz_{000,p100,m100}mm/` holds,
per vertex:
- `summary.txt`;
- CSVs: integrated efficiency, efficiency vs p, decomposition vs p, family A/B,
  comparison with the straight-line result;
- per-disk xy maps, profiles (x, y, tanθx, tanθy) and vs-p PNGs;
- an overview PNG, a combined PDF and `histograms.npz`.

**Open items for the user (morning)**
1. Visual check of the overlay geometry:
   `proj_svt_disk_tiling/refplanes/out_9c/detector_geometry.root`.
2. Review the HD0 (+100) and ED0 (−100) row-gap loss at steep incidence.
3. Decide whether to define a tiling-footprint (no-margin) boundary.
4. The family-A y range is asymmetric on ED2/HD2/ED3/ED4 (for example ED4 A is
   [−216, 234) mm). Check that this matches the delivered row layout.
5. Still deferred: eicrecon/ACTS with the overlay (unverified), and a new
   material map (needed after Step 8q in any case).
- Nothing was committed in either repository.

## 2026-11-06: "active" selection replaces "reached" (refplane_efficiency_v2)

User request: replace the no-cut "reached" selection with the active-silicon
boundary. User choice: use the filled outline, so that gaps inside it count as
inefficiency.

**Active-silicon rectangles from the built geometry**
- Scripts: `dump_active_silicon_rectangles.py` and the wrapper
  `run_dump_active_silicon.sh`. They run in eic_xl:26.09.0-stable on the
  local install, EPIC commit 311634084.
- Output: `geometry/active_silicon_rectangles.csv`. Log:
  `logs/dump_active_silicon_20261106T153907Z.log`.
- 152,628 sensitive boxes, all TGeoBBox, each 3.571 × 9.197 mm, all
  axis-aligned. Sensor centres are at z_disk ± 3.6 mm.
- Checks:
  - Per-disk box area equals catalogue `total_active_area_mm2` × (1 − 0.01749)
    on every disk.
  - x and y extents equal the metadata `sensor_max_x/y_mm`.
- Gap survey of the union of both faces, on a 0.1 mm raster:
  - interior gaps ≤ 0.7 mm only;
  - 14.5–18.5 mm notches at row ends of the outer staircase, which are not
    interior.

**Selection in `analyze_refplane_efficiency.py`**
- `active` = plane reached AND the true point is inside the filled outline.
- Building the outline:
  1. union of the boxes on a 0.5 mm raster;
  2. binary closing with a 1 mm radius;
  3. fill the enclosed holes;
  4. reopen the hole that contains a beam-pipe opening centre.
- New options: `--active-csv`, `--active-grid-mm` (0.5) and
  `--active-close-mm` (1.0).
- Outline area vs raw union: +3%, from raster seams and slivers.
- Maps: still all primaries that reached the plane. The outline is now drawn in
  orange.
- New diagnostic: silicon-hit primaries whose true point lies outside the
  outline.
  - 0.15–0.3% on disks 2–4, 0.4% on disk 1, about 1% on disk 0.
  - At ±100 mm, up to 1.8% on the disk nearest the vertex.
  - These are edge effects of projecting to z_disk rather than to the sensor
    face.
- Command: `OUTPUT_DIR=results/refplane_efficiency_v2 ./run_refplane_efficiency.sh`.
  Log: `logs/refplane_efficiency_20261106T161039Z.log`.
- v1 is untouched. In v2 the nomargin and fid numbers are identical to v1.

**Active efficiency [%] (errors ±0.01–0.02)**

| disk | vz 0 | vz +100 | vz −100 |
|---|---|---|---|
| ED4 | 98.11 | 98.13 | 98.08 |
| ED3 | 98.01 | 98.07 | 97.92 |
| ED2 | 97.78 | 97.94 | 97.51 |
| ED1 | 97.36 | 97.75 | 96.62 |
| ED0 | 96.83 | 97.74 | 94.02 |
| HD0 | 96.80 | 93.93 | 97.72 |
| HD1 | 97.33 | 96.61 | 97.75 |
| HD2 | 97.87 | 97.65 | 97.99 |
| HD3 | 98.20 | 98.13 | 98.23 |
| HD4 | 98.26 | 98.23 | 98.26 |

**Observations**
- Active efficiency is 0.1–0.6 points below fid. Including the beam-pipe and
  outer module edges costs little, most on ED0/HD0.
- A vs B rows at vz 0: A is 98.0–98.3%; B is lower on every disk, by 0.15
  points on ED4 up to 0.84 points on ED2.

## 2026-11-06: plot presentation update (refplane_efficiency_v3)

User requests, display only (numbers unchanged):
- **xy maps, white threshold.**
  - A bin is drawn white if its efficiency is < 20% AND its centre is outside
    the active-silicon outline (beyond the disk, beam-pipe hole), in addition
    to the existing < 20 entries mask.
  - The threshold is NOT applied inside the outline. Real gaps there must stay
    visible: 0.02–0.3% of inside bins are < 20% at vz = 0, but 3.8% on HD0 at
    vz = +100 (the steep-incidence row gaps). Outside the outline, 88–96% of
    bins are < 20%.
  - Options: `--map-white-below-pct` (20) and `--map-white-everywhere` (off).
  - The colour bar shows that values below 80% use the bottom colour.
  - Partly covered 4 mm bins straddling the outline edge remain as a thin dark
    rim.
- **Map title and key.**
  - The title is two lines: disk/vz/binning, then the white rule.
  - The colour-word key is replaced by a legend with line samples under the
    map.
  - The grey dotted circles are the inner/outer edges of the reference plane
    (annulus about its own centre, plane_map.csv). They are now labelled so.
- **Line widths:** boundary lines 0.6–0.8 → 1.5–1.6; profile curves
  0.9/0.6 → 1.6/1.1.
- **Selection order:** fid → active → nomargin (`SELECTIONS`). The
  `histograms.npz` selection axis follows this order; it is stored in the
  `selections` array.
- **Overview page.**
  - Three adjacent thin bars per disk, with value labels.
  - Red dashed reference line at the expected 98%.
  - The y axis does not start at 0 (stated in the title).
- **Run.**
  - Command: `OUTPUT_DIR=results/refplane_efficiency_v3 ./run_refplane_efficiency.sh`.
  - Log: `logs/refplane_efficiency_20261106T220223Z.log`.
  - Check: every integrated efficiency and denominator is identical to v2 for
    all three vertices.
  - Test runs (2 shards, vz = +100) went to the session scratchpad. Their logs
    are `logs/refplane_efficiency_20261106T2200*Z.log` and
    `logs/refplane_efficiency_20261106T2201*Z.log`.

## 2026-11-09: nomargin dropped from all plots (refplane_efficiency_v4)

**Why.** The bump near y = 0 in the D1 y-profile (about 78%, falling below 70%
at |y| ~ 15-50 mm) was a denominator artefact of nomargin, not inefficiency.
- The 1D profiles used nomargin: true point outside the buffered opening
  circle (r ~ 36.8 mm) and inside rmax, summed over x.
- The modules stop in a rectangular cut-out around the hole, at |x| ~ 48 mm
  for |y| < 30 and ~40 mm near |y| ~ 40 (52 / 40 mm on D2).
- The untiled ring between the circle and the module ends is 20% of the
  row's denominator at y = 0 and about 50% at |y| ~ 40, with ~0% efficiency.
  On the silicon it is 96-99%.
- Numbers from the v3 vz = 0 xy maps, 4 mm bins (scratchpad script
  `y_profile_centre.py`).

**Change (user request): nomargin is no longer plotted.**
- New `PLOT_SELECTIONS = ("fid", "active")`.
- The 1D profiles (y, |y|, x, tan theta) now use **active**.
- Efficiency vs p shows fid and active only.
- Overview: two adjacent bars per disk, with the 98% line.
- nomargin is still computed and written to the CSVs and `summary.txt`
  (traceability).

**Run.**
- Command: `OUTPUT_DIR=results/refplane_efficiency_v4 ./run_refplane_efficiency.sh`.
- Log: `logs/refplane_efficiency_20261109T162934Z.log`.
- Numbers are unchanged from v3.
- HD1 vz = 0 y-profile: the centre region now reads ~97-100%.

## 2026-11-10: talk figures (SVT DSC) and geometric check of the RSU-structure loss

**Figures.**
- Location: `results/talk/20261110_svt_dsc/` (PNG + PDF).
- Scripts: `talk/20261110_svt_dsc/`, runners `run_slides_1_2.sh` and
  `run_slides_3_4.sh`.
- Fid selection only; reference-plane results v4; nothing from the
  straight-line analysis.

| Figure | Content |
|---|---|
| slide1_schematic | method and corrugation zoom |
| slide2_ED4_map | ED4 x-y map, v_z = 0 |
| slide2_ED4_vs_p | ED4 (ED3/ED2 faint) vs p |
| slide3_vertex_bars | 10 disks x 3 vertices, y range 93-100 |
| slide4_incidence_angle | HD0/HD1 fid efficiency vs \|tan theta_y\|, 0.10 bins |
| slide4_incidence_angle_fine | 0.05-bin version: the nearest disk shows row/overlap aliasing |

**Slide 4 result.** All six curves (HD0/HD1 x 3 vertices) collapse within
~0.5 pt below \|tan theta_y\| = 0.5. Plateau ~98.3-98.9%, onset at
0.35-0.40, ~94% at 0.5, ~90% at 0.7.

**Geometric check (`check_rsu_geometric_coverage.{py,txt}`).**
- Inputs: v_z = 0, 4 shards per side, fid annulus. Each true track is traced
  through the as-built sensitive boxes, from
  `geometry/active_silicon_rectangles.csv`.
- RSU structure, from the box paths: 12 sensitive boxes per RSU
  (2 x-halves x 3 tiles x 2 y-halves), each 3.571 x 9.197 mm, for all 12,719
  RSUs.
- Gaps: 0.02 / 0.08 mm in x and 0.12 mm in y inside an RSU; 0.08 mm between
  RSUs.
- Inactive fraction: 1 - (21.426 x 18.394)/(21.666 x 18.514) = 1.7487%,
  confirmed on every disk.
- (a) measured vs (b) geometric with the true direction agree to <= 0.06 pt on
  all disks, so physics effects (secondaries, thresholds) are negligible.
- (c) geometric at normal incidence = coverage built into the layout:
  - D2-D4: 97.95-98.10%, so the layout explains the whole loss. Inclined
    tracks even recover 0.2-0.4 pt on D3/D4 by covering gaps between modules.
  - D0/D1: 98.35-98.49%, i.e. ~1.5-1.65 pt built in. The extra ~0.9-1.1 pt is
    angle-dependent: steep tracks pass between rows on opposite faces. The
    row overlap is 18.514 - 16.5 = 2.0 mm over ~6.6 mm in z, so
    \|tan theta_y\| > ~0.3. This is inferred from the geometry.
- (d) split of the normal-incidence loss:
  - gaps inside one RSU: 1.25-1.4 pt;
  - 0.08 mm RSU-RSU strips: ~0.3 pt;
  - between modules / row ends: 0.25-0.42 pt on D2-D4, 0 on D0/D1.

**Other.** `analyze_refplane_efficiency.py` overview y-axis top changed
101.5 -> 100.3 (applies to future runs; v4 not regenerated).

- 2026-11-10 (talk revision):
  * slide4_incidence_angle: x label is now "|tan theta_y| (theta_y: incidence
    angle projected onto the vertical y-z plane)", with a top axis in degrees.
    The onset is quoted as 19-22 deg. The previous slide4 files were moved to
    tmp/retained/2026-11-10/ (logged).
  * New backup_theta_y_all_disks: fid efficiency vs |tan theta_y| for D0-D4
    (ED+HD summed, v_z = 0, 0.10 bins), plus the share of fid tracks with
    theta_y >= 19 deg (from 0.05 bins): D0 35%, D1 23%, D2 11%, D3 3.5%,
    D4 0.5%. The "20-25% vs <8%" figures quoted earlier used |tan| >= 0.4
    (22 deg).
  * Runner: talk/20261110_svt_dsc/run_slide4_and_backup_v2.sh.
  * Material (disk_material_map step8q; step8m agrees within 0.001%):
    <x/X0> on the annulus is 0.27-0.31% per disk (ED4 0.274%), about 61%
    carbon fibre and 21% silicon.
