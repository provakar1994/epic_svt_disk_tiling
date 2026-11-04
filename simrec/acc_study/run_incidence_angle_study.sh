#!/usr/bin/env bash
# Recorded: D0/D1 hit efficiency vs incidence angle for all five vertex samples.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda
conda activate tracking
python3 "$script_dir/study_incidence_angle.py"
