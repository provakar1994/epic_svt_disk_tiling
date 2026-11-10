#!/bin/bash
# Talk figures for slides 1-2 (SVT DSC, 2026-11-10): schematic, ED4 map, ED4 efficiency vs p.
# Inputs: results/refplane_efficiency_v4/vz_000mm/ ; outputs: results/talk/20261110_svt_dsc/
set -euo pipefail
module load conda
conda activate tracking
ACC=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/simrec/acc_study
HERE=$ACC/talk/20261110_svt_dsc
cd "$ACC"     # analysis defaults and relative output paths resolve from here
python "$HERE/slide1_schematic.py"
python "$HERE/slide2_ED4_map.py"
python "$HERE/slide2_ED4_vs_p.py"
