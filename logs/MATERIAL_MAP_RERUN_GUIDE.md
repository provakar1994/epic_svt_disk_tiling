# ACTS Material-Map Rerun Guide

This note preserves the local compatibility changes and workflow used to run
the EPIC ACTS material-map generation. The compatibility edits may be reverted
from the working tree and reapplied later when needed.

## What the local changes did

The changes were runtime compatibility workarounds. They did not alter detector
geometry or the contents of a generated material map.

### 1. Update the ACTS logger API

In `scripts/material_map/epic.py`, replace:

```python
logger = acts.getDefaultLogger("epic.getDetector", logLevel)
```

with:

```python
logger = acts.logging.getLogger("epic.getDetector")
```

Keep this existing line:

```python
customLogLevel = acts.examples.defaultLogging(logLevel=logLevel)
```

It is still used to configure the material decorator and DD4hep detector.

Apply this change when the active ACTS Python bindings do not provide
`acts.getDefaultLogger`.

### 2. Disable the obsolete ACTS PR 5359 patch

In `scripts/material_map/run_material_map_validation.sh`, comment out:

```bash
# patch_acts https://github.com/acts-project/acts/pull/5359.diff # landed in 46.3.0
```

PR 5359 is included in ACTS 46.3.0 and newer. Applying the patch again is
unnecessary and may fail because the source no longer matches its pre-merge
state.

The untracked file `scripts/material_map/5359.diff` is a downloaded copy of the
patch. It is not needed when the patch call is disabled.

## Version caution

First try the unmodified scripts in the intended EIC software environment, then
reapply only the workarounds that are needed:

- If `acts.getDefaultLogger` is unavailable, apply the logger change.
- For ACTS 46.3.0 or newer, keep the PR 5359 patch call disabled.
- An older ACTS environment may still require the PR 5359 patch.

The runner currently downloads example scripts from:

```bash
ACTS_VERSION="v46.8.1"
```

It only downloads a file when that file is absent. An older cached `Examples/`
tree can therefore remain in use after the runner is updated. In October 2026,
the cached `material_recording.py`, `material_mapping.py`, and
`material_validation.py` still used the older `outputDir` API, while the EPIC
wrappers expected ACTS v46.8.1 `outputFileBase` arguments. The resulting
`TypeError` occurs before material-track recording starts.

The one-time, non-destructive refresh is recorded in
`proj_svt_disk_tiling/logs/refresh_material_map_acts_examples_20261016.sh`.
It downloads and checks the v46.8.1 examples before moving the old cache and
`6010.diff`/`6012.diff` into
`proj_svt_disk_tiling/tmp/retained/2026-10-16/material_map_acts_refresh/`.
It also preserves the runner's local B0 validation-plot adjustment in
`Mat_map.C`. Both retained PR patches pass a dry-run against the new cache.
The original runner only applied each patch when its downloaded `.diff` file
was absent. The October smoke test found the patch files present but their
changes unapplied. The runner now checks the source state independently of
patch-file existence, applying each patch once or reporting a cleanly applied
patch on later runs. A subsequent attempt to apply PR 6010 directly on NERSC
failed when GNU `patch` tried to set the owner of a temporary file on the
shared filesystem. The runner now patches copies in `${TMPDIR:-/tmp}` and
copies the result over the original inode, preserving its owner and group.
It retains the scratch copies and originals under
`proj_svt_disk_tiling/tmp/retained/<date>/material_map_patches/` and logs the
move in `proj_svt_disk_tiling/tmp/file_actions.log`.

## Before running

1. Enter the intended EIC software environment.
2. Build and install the EPIC branch containing the geometry to be mapped.
3. Source `setup_local.sh` and confirm that `DETECTOR_PATH` points to that local
   installation.
4. Confirm that `${DETECTOR_PATH}/epic_craterlake_material_map.xml` includes
   `compact/tracking/silicon_disks_modules.xml`, not legacy `silicon_disks.xml`.
5. Allow at least 10 GB of free space and roughly two hours for a full run.

Run the workflow from `scripts/material_map`. The script downloads and modifies
ACTS example files relative to the current directory.

## Commands

Start with a small smoke test in the EIC shell, from the repository root:

```bash
bash proj_svt_disk_tiling/logs/check_material_map_acts_refresh_20261016.sh
```

The wrapper uses `--nevents 10 --nparticles 100` and a unique output prefix.
It retains the existing `plots/`, `Validation/`, and `Surfaces/` directories
before the runner recreates them, and records the paths in
`proj_svt_disk_tiling/tmp/file_actions.log`. It writes its transcript under
`proj_svt_disk_tiling/logs/`. Existing large ROOT files remain untouched. It
passes `--skip-current-map-validation`: this preserves validation and plots
for the regenerated map, while omitting the existing calibration map that
currently raises an ACTS cylinder-axis exception.

For a production-size run (`--nevents 1000 --nparticles 5000`), first use a
dedicated working directory or retain the existing ROOT outputs as well. Do
not run the unprefixed command in `scripts/material_map/`: it would overwrite
the previous multi-gigabyte results. The smoke-test wrapper only protects the
existing outputs for its recorded 10-event run.

Use `--verbose` only for ACTS surface and volume debugging after protecting
previous outputs. Verbose mode edits the downloaded
`Examples/Scripts/Python/material_mapping.py` in place. Recreate the downloaded
`Examples/` tree before a later clean non-verbose run if necessary.

## Workflow and outputs

The runner performs these steps:

1. Records Geant4 geantino material tracks.
2. Exports the ACTS tracking geometry.
3. Configures the surfaces and boundaries used for material mapping.
4. Maps the recorded material onto those ACTS surfaces.
5. Runs propagation validation with the regenerated map; also uses the current
   calibration map unless `--skip-current-map-validation` is given.
6. Produces the plots for whichever validation runs were enabled.

Important outputs are:

| Output | Purpose |
|---|---|
| `geant4_material_tracks.root` | Geant4 material-track recording |
| `geometry-map.json` | ACTS tracking geometry |
| `config-map.json` | Initial mapping configuration |
| `config-map_regenerated.json` | Modified mapping configuration |
| `material-map_map.cbor` | Regenerated map for EICrecon; prefixed in smoke runs |
| `material-map_mapped.root` | ACTS mapped material tracks |
| `propagation_material_regenerated.root` | Validation using the new map |
| `propagation_material_current.root` | Validation using the current calibration map |
| `plots/` | Geometry and material visualizations |
| `Validation/` | Regenerated/current validation plots |
| `Surfaces/` | Surface-level comparison plots |

The reference comparison uses:

```text
calibrations/materials-map.cbor
```

The 2026-10-16 smoke test recorded and mapped 10 events and validated the
regenerated ROOT map. It then failed loading the older calibration CBOR map:
ACTS rejected `{AxisPhi, AxisR}` binning on a cylinder. This does not establish
that the new map or detector geometry is faulty, but the existing-map
comparison remains unresolved. The separate repeated ROOT `TGeoVoxelFinder`
`envelope26` bounding-box warning also needs investigation before a
production map is accepted.

The same run produced no CBOR because the ACTS CBOR patch was not applied and
the runner passed `--matFileFormat` twice, leaving only `root` selected.
The runner now applies the patch based on source state, passes both formats as
one argument list, and fails if either requested output is missing.

## Test with EICrecon

Use an absolute path when selecting the regenerated map:

```bash
eicrecon \
  -Pacts:MaterialMap=/absolute/path/to/material-map_map.cbor \
  [other arguments]
```

## Operational notes

- The runner uses fixed output names and may overwrite previous results. Run it
  in a dedicated working directory or archive important outputs first.
- The existing production material-map ROOT files under `scripts/material_map/`
  are large. Preserve them before rerunning the smoke test there; `--prefix`
  avoids those ROOT filenames, but the runner also recreates `plots/`,
  `Validation/regenerated`, `Validation/current`, and `Surfaces/`.
- It exports `ACTS_SEQUENCER_DISABLE_FPEMON=1` to work around known floating-point
  exceptions in `RootMaterialTrackReader`.
- Geometry or material-thickness changes anywhere in the tracking volume can
  require a regenerated material map, including changes to passive structures.
