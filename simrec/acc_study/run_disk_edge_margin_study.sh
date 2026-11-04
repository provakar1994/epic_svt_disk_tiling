#!/usr/bin/env bash
# Recorded edge-margin study: phi-integrated hit efficiency vs straight-line
# radius at each disk, near the XML inner/outer edges, per 2 GeV momentum bin.
# Used to choose the fiducial margins for the per-disk average efficiency.
# v1 (1-pt tolerance from the XML edges) was tripped by interior dips; v2 locates
# each edge by its 50% crossing and measures the band to plateau - 3 pt.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
extracted_root="$script_dir/extracted/acceptance_v1"
output_dir="$script_dir/results/disk_edge_margins_v2"
geometry_xml="$script_dir/../../../compact/tracking/definitions_craterlake.xml"

module load conda
conda activate tracking

python3 "$script_dir/study_disk_edge_margins.py" \
  --extracted-root "$extracted_root" \
  --output-dir "$output_dir" \
  --geometry-xml "$geometry_xml" \
  --vertex 0 \
  --momentum-bin 0.5 2.5 \
  --momentum-bin 2.5 4.5 \
  --momentum-bin 4.5 6.5 \
  --momentum-bin 6.5 8.5 \
  --momentum-bin 8.5 10.5 \
  --momentum-bin 10.5 12.5 \
  --momentum-bin 12.5 14.5 \
  --momentum-bin 14.5 16.5 \
  --momentum-bin 16.5 18.5 \
  --momentum-bin 18.5 20.01 \
  --r-bin-mm 2.5 \
  --tolerance-percent 3.0 \
  --consecutive-bins 3
