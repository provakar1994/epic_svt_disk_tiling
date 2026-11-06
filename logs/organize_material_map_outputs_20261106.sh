#!/usr/bin/env bash
# Move existing material-map run outputs out of scripts/material_map/ into one directory per run
# under proj_svt_disk_tiling/matmap/<run>/ (same idea as matscan/). Moves only (no deletion);
# each move is logged in proj_svt_disk_tiling/tmp/file_actions.log. File names are kept, so
# transcripts in logs/ that cite a file name still identify it.
# The two maps cited by scripts (simrec/run_sim.sh, simrec/acc_study/run_sim.sh default to the
# Step 8m map) and in reconstruction logs get a symlink at their old path.
# Usage: bash organize_material_map_outputs_20261106.sh > organize_material_map_outputs_20261106.txt
set -euo pipefail
src=/global/cfs/cdirs/m3763/pdatta/epic/scripts/material_map
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
dest_root=$proj/matmap
action_log=$proj/tmp/file_actions.log

move() {  # move SOURCE_PATH RUN_NAME REASON
  local target="$dest_root/$2/$(basename "$1")"
  [[ -e "$target" ]] && { echo "ERROR: $target exists" >&2; exit 1; }
  mkdir -p "$dest_root/$2"
  mv "$1" "$target"
  printf '%s | %s | %s | move | %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$target" "$3" >> "$action_log"
  echo "moved $1 -> $target"
}

# Prefixed runs: prefix = run name.
for run in smoke_20261016T135951Z smoke_20261016T140206Z smoke_20261016T142017Z \
           production_20261016T144812Z step8m_20261020T164956Z step8q_smoke_20261106T214810Z; do
  for f in "$src/${run}_"*; do
    move "$f" "$run" "material-map run outputs, one directory per run"
  done
done

# Fixed-name plot directories in scripts/material_map/ are from the last run made there,
# the first Step 8q smoke run (2026-11-06 13:52-13:55 local).
for d in plots Validation Surfaces; do
  move "$src/$d" step8q_smoke_20261106T214810Z "fixed-name plots of that run"
done

# Unprefixed outputs, all dated 2026-07-19 (pre-SVT-tiling map run).
for f in config-map.json config-map_regenerated.json geant4_material_tracks.root geometry-map.json \
         material-map.cbor material-map_tracks.root propagation_material_current.root \
         propagation_material_regenerated.root; do
  move "$src/$f" unprefixed_20260719 "unprefixed material-map run outputs from 2026-07-19"
done

# Keep cited map paths working.
for run in step8m_20261020T164956Z production_20261016T144812Z; do
  ln -s "$dest_root/$run/${run}_material-map_map.cbor" "$src/${run}_material-map_map.cbor"
  echo "symlink $src/${run}_material-map_map.cbor -> $dest_root/$run/${run}_material-map_map.cbor"
done
echo "Remaining in $src:"; ls -A "$src"
