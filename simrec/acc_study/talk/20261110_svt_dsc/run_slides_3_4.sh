#!/bin/bash
# Make slide 3 (fid efficiency per disk x vertex) and slide 4 (fid efficiency vs |tan theta_y|)
# for the 2026-11-10 SVT DSC talk. Outputs go to ../../results/talk/20261110_svt_dsc/.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

module load conda
conda activate tracking

python slide3_vertex_bars.py
python slide4_incidence_angle.py
