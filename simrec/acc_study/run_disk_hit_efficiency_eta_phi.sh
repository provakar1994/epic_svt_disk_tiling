#!/usr/bin/env bash
# Recorded per-disk hit-efficiency maps in generated (eta, phi), z=0 sample.
# One page per disk and momentum selection; the region is set from all momenta.
# v2: same definitions as v1, plus the rounded efficiency [%] printed in each bin.
# v3: adds disk-plane views (eta edges -> straight-line radius at nominal disk z).
# v4: disk view gets an inner-edge zoom panel and per-bin numbers where they fit.
# v5: disk views show the XML disk openings (+5 mm bakeout buffer) and outer radius in red.
#     The XML is the parent epic checkout (branch si_disk_hole); these constants are
#     unchanged since the 2026-10-26 simulation campaign.
# v6: pages ordered ED4..ED0, HD0..HD4; uniform 2 GeV momentum bins from 0.5 GeV,
#     last bin 18.5-20 GeV (20.01 includes the gun endpoint).
# v7: first PDF page = cross-disk fiducial summary; first page per disk = fiducial
#     efficiency vs momentum. Fiducial annulus: XML r_in + 30 mm <= R < rmax - 40 mm
#     (margins from results/disk_edge_margins_v2, run_disk_edge_margin_study.sh).
# v8: disk views also draw the fiducial annulus (magenta dashed circles).
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Usage: <runner> [vertex_mm]   (0 default; -10 or 10 for the displaced-vertex samples)
vertex="${1:-0}"
case "$vertex" in
  0)   vertex_label="";              extracted_root="$script_dir/extracted/acceptance_v1" ;;
  -10) vertex_label="_vz_m010mm";    extracted_root="$script_dir/extracted/acceptance_v1_vz_m010mm" ;;
  10)  vertex_label="_vz_p010mm";    extracted_root="$script_dir/extracted/acceptance_v1_vz_p010mm" ;;
  *)   echo "ERROR: vertex must be 0, -10 or 10" >&2; exit 2 ;;
esac
output_dir="$script_dir/results/disk_hit_efficiency_v8${vertex_label}"
geometry_xml="$script_dir/../../../compact/tracking/definitions_craterlake.xml"

module load conda
conda activate tracking

python3 "$script_dir/plot_disk_hit_efficiency_eta_phi.py" \
  --extracted-root "$extracted_root" \
  --output-dir "$output_dir" \
  --vertices "$vertex" \
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
  --eta-bin-width 0.1 \
  --phi-bin-width-deg 10 \
  --minimum-bin-denominator 20 \
  --region-min-row-efficiency 0.01 \
  --geometry-xml "$geometry_xml" \
  --fiducial-inner-margin-mm 30 \
  --fiducial-outer-margin-mm 40
