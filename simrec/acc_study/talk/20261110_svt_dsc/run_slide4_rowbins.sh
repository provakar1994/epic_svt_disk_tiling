#!/usr/bin/env bash
# Recorded 2026-11-10: slide 4 with row-matched |tan theta_y| bins (removes bin/row aliasing).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda
conda activate tracking
cd "$here/../.."
python3 "$here/slide4_incidence_angle_rowbins.py"
