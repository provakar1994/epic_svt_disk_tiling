#!/usr/bin/env bash
# Run an acceptance-study task list as packed commands on premium CPU nodes.
# Usage: sbatch submit_premium_packed.sh TASK_FILE
# Default: four nodes, up to 90 simultaneous serial commands per node.
#SBATCH --account=m3763
#SBATCH --qos=premium
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-acceptance
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=90
#SBATCH --cpus-per-task=2
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --time=03:00:00
#SBATCH --output=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/slurm/%x-%j.out

set -euo pipefail

show_usage() { echo "Usage: sbatch [SLURM_OPTIONS] $0 TASK_FILE" >&2; }
if [[ ${1:-} == --help || ${1:-} == -h ]]; then show_usage; exit 0; fi

if [[ ${1:-} == --worker ]]; then
  task_file="$2"
  rank="${SLURM_PROCID:?SLURM_PROCID is not set}"
  task_number=$((${TASK_LINE_OFFSET:-0} + rank + 1))
  task_command="$(awk -v wanted="$task_number" '
    /^[[:space:]]*($|#)/ { next }
    { count++ }
    count == wanted { print; exit }
  ' "$task_file")"
  [[ -n "$task_command" ]] || { echo "ERROR: no task $task_number for rank $rank" >&2; exit 1; }
  task_log="${TASK_LOG_DIRECTORY}/task_$(printf '%04d' "$task_number").log"
  {
    echo "=== Starting task $task_number on rank $rank ==="
    echo "Started: $(date --iso-8601=seconds)"
    echo "Command: $task_command"
    bash -lc "$task_command"
    echo "Finished: $(date --iso-8601=seconds)"
    echo "=== Completed task $task_number ==="
  } > "$task_log" 2>&1
  exit 0
fi

[[ $# -eq 1 ]] || { show_usage; exit 2; }
[[ -n ${SLURM_JOB_ID:-} ]] || { echo 'ERROR: submit this wrapper with sbatch.' >&2; exit 2; }
task_file="$(realpath -e -- "$1")" || { echo "ERROR: task file not found: $1" >&2; exit 2; }
total_tasks="$(awk '!/^[[:space:]]*($|#)/ { count++ } END { print count + 0 }' "$task_file")"
[[ "$total_tasks" -gt 0 ]] || { echo 'ERROR: task file has no commands.' >&2; exit 2; }

tasks_per_node="${TASKS_PER_NODE:-90}"
[[ "$tasks_per_node" =~ ^[1-9][0-9]*$ && "$tasks_per_node" -le 128 ]] || {
  echo 'ERROR: TASKS_PER_NODE must be from 1 through 128.' >&2; exit 2;
}
node_count="${SLURM_JOB_NUM_NODES:-1}"
wave_capacity=$((node_count * tasks_per_node))
allocated_slots="${SLURM_NTASKS:-$wave_capacity}"
needed_slots="$wave_capacity"
(( total_tasks < needed_slots )) && needed_slots="$total_tasks"
(( allocated_slots >= needed_slots )) || { echo "ERROR: need $needed_slots ranks, received $allocated_slots." >&2; exit 2; }
number_of_waves=$(((total_tasks + wave_capacity - 1) / wave_capacity))

script_candidate="${SUBMIT_BATCH_SCRIPT:-}"
if [[ -z "$script_candidate" ]]; then
  study_dir="$(cd "$(dirname "$task_file")/../.." && pwd)"
  script_candidate="$study_dir/submit_premium_packed.sh"
fi
script_path="$(realpath -e -- "$script_candidate")" || {
  echo "ERROR: cannot resolve shared wrapper: $script_candidate" >&2; exit 2;
}
container_runtime="${EIC_CONTAINER_RUNTIME:-/cvmfs/oasis.opensciencegrid.org/mis/singularity/bin/singularity}"
container_image="${EIC_IMAGE:-/cvmfs/singularity.opensciencegrid.org/eicweb/eic_xl:26.09.0-stable}"
[[ -x "$container_runtime" ]] || { echo "ERROR: container runtime unavailable: $container_runtime" >&2; exit 2; }
[[ -e "$container_image" ]] || { echo "ERROR: container image unavailable: $container_image" >&2; exit 2; }
export APPTAINER_BINDPATH=/global,/pscratch
task_log_root="${TASK_LOG_ROOT:-/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/slurm_tasks}"
export TASK_LOG_DIRECTORY="$task_log_root/$SLURM_JOB_ID"
mkdir -p "$TASK_LOG_DIRECTORY"

echo "=== Starting packed premium job ==="
echo "Job ID:         $SLURM_JOB_ID"
echo "Nodes:          $node_count"
echo "Tasks:          $total_tasks"
echo "Tasks/node cap: $tasks_per_node"
echo "Wave capacity:  $wave_capacity"
echo "Waves:          $number_of_waves"
echo "Task file:      $task_file"
echo "Task logs:      $TASK_LOG_DIRECTORY"
echo "Runtime:        $container_runtime"
echo "Container:      $container_image"

for ((wave = 0; wave < number_of_waves; wave++)); do
  offset=$((wave * wave_capacity))
  remaining=$((total_tasks - offset))
  wave_tasks="$wave_capacity"
  (( remaining < wave_tasks )) && wave_tasks="$remaining"
  export TASK_LINE_OFFSET="$offset"
  echo "Wave $((wave + 1))/$number_of_waves: tasks $((offset + 1))-$((offset + wave_tasks))"
  printf -v worker_command '%q ' bash "$script_path" --worker "$task_file"
  srun --exact --network=no_vni --kill-on-bad-exit=0 \
    --nodes="$node_count" --ntasks="$wave_tasks" \
    --cpus-per-task="${SLURM_CPUS_PER_TASK:-2}" --cpu-bind=cores \
    "$container_runtime" exec "$container_image" \
    /opt/local/bin/eic-shell "$worker_command"
done

echo "=== Completed all $total_tasks tasks ==="
