#!/usr/bin/env bash
# Recorded 10-event smoke test for the +/-10 cm campaign (vertex z = +100 mm),
# same container and runner as the production tasks in task_lists/acceptance_v2_vz100mm.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
runner="$script_dir/run_sim.sh"
output_dir="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/smoke_20261104_vz100mm"
container_runtime="/cvmfs/oasis.opensciencegrid.org/mis/singularity/bin/singularity"
container_image="/cvmfs/singularity.opensciencegrid.org/eicweb/eic_xl:26.09.0-stable"

[[ -x "$runner" ]] || { echo "ERROR: runner is not executable: $runner" >&2; exit 2; }
[[ -x "$container_runtime" ]] || { echo "ERROR: container runtime is unavailable: $container_runtime" >&2; exit 2; }
[[ -e "$container_image" ]] || { echo "ERROR: container image is unavailable: $container_image" >&2; exit 2; }
[[ ! -e "$output_dir" ]] || { echo "ERROR: smoke output already exists: $output_dir" >&2; exit 2; }

export APPTAINER_BINDPATH=/global,/pscratch
smoke_command=(
  "$runner" both "$output_dir"
  smoke_vz_p100mm_eta_p0p6_to_p3p8_n10
  10 100 0.6 3.8 42999999
)
printf -v command_string '%q ' "${smoke_command[@]}"

exec "$container_runtime" exec "$container_image" \
  /opt/local/bin/eic-shell "$command_string"
