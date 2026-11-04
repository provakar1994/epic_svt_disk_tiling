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
