#!/usr/bin/env bash
# Recorded: straight-line projection vs true mean hit position (z=0 sample).
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda
conda activate tracking
python3 "$script_dir/check_straight_line_projection.py"
