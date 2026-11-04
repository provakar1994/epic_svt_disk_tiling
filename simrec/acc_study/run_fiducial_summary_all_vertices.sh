#!/usr/bin/env bash
# Recorded: one PDF with the cross-disk fiducial summary page for vz = -10, 0, +10 mm,
# redrawn from the v8 fiducial_efficiency CSVs.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda
conda activate tracking
python3 "$script_dir/make_fiducial_summary_all_vertices.py" \
  --results-dir "$script_dir/results" \
  --version v8 \
  --output "$script_dir/results/fiducial_summary_all_vertices_v8.pdf"
