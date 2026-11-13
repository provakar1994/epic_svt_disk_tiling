#!/bin/bash
# rsu_opt vs rsu6 fiducial hit-efficiency bars (5-page PDF). Output: ../../results/talk/20261113_rsu6_compare/
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
module load conda
conda activate tracking
python rsu_opt_vs_rsu6_vertex_bars.py | tee ../../results/talk/20261113_rsu6_compare/rsu_opt_vs_rsu6_vertex_bars.txt
