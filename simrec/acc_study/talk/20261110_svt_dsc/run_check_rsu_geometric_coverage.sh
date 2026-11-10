#!/bin/bash
# Geometric-coverage check of the "~98% from inactive RSU regions" talk claim.
# Writes check_rsu_geometric_coverage.txt next to this script.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
module load conda
conda activate tracking
python "$HERE/check_rsu_geometric_coverage.py" \
    --shards-per-side 4 \
    --grid-mm 10 \
    --area-points 2000000 \
    --output "$HERE/check_rsu_geometric_coverage.txt"
