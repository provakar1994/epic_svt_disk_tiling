#!/bin/bash
# Per-disk SVT endcap material maps from the ACTS Geant4 material-recording output.
# Usage: ./run_disk_material_map.sh [material_tracks.root] [output_dir] [extra args...]
#   e.g. ./run_disk_material_map.sh "" "" --max-tracks 200000   (quick test)
# Runs outside eic-shell: needs only uproot/awkward/matplotlib (conda env "tracking").
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
input=${1:-$here/../material_map/step8m_20261020T164956Z_geant4_material_tracks.root}
# material-scan outputs are kept in the SVT tiling project (proj_svt_disk_tiling/matscan/, gitignored)
outdir=${2:-$here/../../proj_svt_disk_tiling/matscan/disk_material_map/$(basename "${input%.root}")}
shift $(( $# > 2 ? 2 : $# )) || true

set +u
module load conda >/dev/null 2>&1 || true
eval "$(conda shell.bash hook)" && conda activate tracking
set -u
mkdir -p "$outdir"

python "$here/disk_material_map.py" --input "$input" --output-dir "$outdir" "$@" 2>&1 | tee "$outdir.log"
