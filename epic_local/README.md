# epic_local: helper files that live only in the EPIC working copy

The project uses these files, but they are **not** in the EPIC repository (branch `si_disk_hole`). In
`/global/cfs/cdirs/m3763/pdatta/epic` they are either untracked or locally modified. These are copies,
made on 2026-11-13 so that this project repo holds everything it needs.

The project scripts call the copies in the EPIC checkout, not the ones here. If the EPIC checkout is
ever recreated, copy these files back to the same relative paths.

| File here | Location in the EPIC checkout | What it is |
|---|---|---|
| `scripts/subdetector_tests/disk_material_map.py` | same | Per-disk material maps (the "material scan") from an ACTS geantino `material_tracks` file. The disk table is hard-coded from `definitions_craterlake.xml`. |
| `scripts/subdetector_tests/run_disk_material_map.sh` | same | Wrapper; runs in conda `tracking`. Default output: `proj_svt_disk_tiling/matscan/disk_material_map/`. |
| `scripts/material_map/run_material_map_validation.sh` (+ `.patch` = `git diff`) | same; a tracked EPIC file, **modified** | Upstream ACTS material-map script. Local changes: the caller may set `DETECTOR_CONFIG`, and a new `--skip-current-map-validation` option. |
| `setup_local.sh` | EPIC root | Builds and installs EPIC, then sources `install/bin/thisepic.sh`. Modes: `1 0` build, `1 1` fresh build, `0 0` source only. Run it inside eic-shell. |
| `configurations/craterlake_tracking_only_disk_tiles_new.yml` | same | Old (October) reduced configuration, not used since Step 11. |
| `scripts/plot_svt_disk_hit_map.py` | `scripts/` | Old (July) x-y hit-map plotter, not used since Step 11. |
| `conda_tracking_env.yml` | not in EPIC: `conda env export -n tracking --no-builds` of pdatta's env | The host analysis environment (Python 3.11). Recreate it with `module load conda; conda env create -n tracking -f conda_tracking_env.yml`. |
