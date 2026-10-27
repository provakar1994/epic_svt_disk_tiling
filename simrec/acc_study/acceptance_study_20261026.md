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
