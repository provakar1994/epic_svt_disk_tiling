#!/usr/bin/env bash
# Recorded 2026-11-10: slide 4 with projected-angle label + degree axis, and the backup
# all-disk theta_y figure (replaces draft page 23 screenshot).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda
conda activate tracking
python3 "$here/slide4_incidence_angle.py"
python3 "$here/backup_theta_y_all_disks.py"
