#!/usr/bin/env bash
# Submit the Step 8n 20,000-event fixed-vertex sample without replacing earlier outputs.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
runner_dir="$repo_root/proj_svt_disk_tiling/simrec"
batch_script="$runner_dir/submit_premium_packed.sh"
output_dir="/pscratch/sd/p/pdatta/svt_disk_tiling/simout"
geometry="$repo_root/install/share/epic/epic_craterlake_tracking_only_disk_tiles_new.xml"
source_modules="$repo_root/compact/tracking/silicon_disks_modules.xml"
installed_modules="$repo_root/install/share/epic/compact/tracking/silicon_disks_modules.xml"
events=20000
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
record="$repo_root/proj_svt_disk_tiling/logs/submit_npsim_step8n_${stamp}.txt"

jobs=()
for vertex in vm10mm v0mm v10mm; do
  case "$vertex" in
    vm10mm) runner_name=run_sim.sh ;;
    v0mm) runner_name=run_sim_v0mm.sh ;;
    v10mm) runner_name=run_sim_v10mm.sh ;;
  esac
  for index in 0 1 2 3 4; do
    jobs+=("${vertex}_8n_job_${index}|${runner_name}")
  done
done

[[ -f "$batch_script" && -f "$geometry" ]] || {
  echo 'ERROR: batch wrapper or installed geometry is missing.' >&2
  exit 1
}
cmp -s "$source_modules" "$installed_modules" || {
  echo 'ERROR: installed silicon-disks module geometry differs from source; reinstall first.' >&2
  exit 1
}
mkdir -p "$output_dir"
queued_names="$(squeue -h -u "$USER" -o '%j')"
for entry in "${jobs[@]}"; do
  IFS='|' read -r tag runner_name <<< "$entry"
  [[ -f "$runner_dir/$runner_name" ]] || {
    echo "ERROR: missing runner for $tag" >&2
    exit 1
  }
  if [[ -e "$output_dir/sim_${tag}.root" || -e "$output_dir/sim_${tag}.log" ]]; then
    echo "ERROR: output already exists for $tag" >&2
    exit 1
  fi
  if rg -Fxq "svt_${tag}" <<< "$queued_names"; then
    echo "ERROR: job already queued for $tag" >&2
    exit 1
  fi
done

sbatch --test-only --job-name=svt_vm10mm_8n_job_0 \
  --chdir="$repo_root" --output="$output_dir/slurm-%x-%j.out" \
  "$batch_script" vm10mm_8n_job_0 "$events" "$runner_dir/run_sim.sh"

[[ ! -e "$record" ]] || { echo "ERROR: record already exists: $record" >&2; exit 1; }
{
  echo "Step 8n npsim submissions at $stamp UTC"
  echo "Geometry: $geometry"
  echo "Events per job: $events"
  echo 'Gun settings: unchanged from the 2026-10-19 fixed-vertex runners'
  sha256sum "$geometry" "$batch_script" \
    "$runner_dir/run_sim.sh" "$runner_dir/run_sim_v0mm.sh" "$runner_dir/run_sim_v10mm.sh"
  echo
  for entry in "${jobs[@]}"; do
    IFS='|' read -r tag runner_name <<< "$entry"
    job_id="$(sbatch --parsable --job-name="svt_${tag}" \
      --chdir="$repo_root" --output="$output_dir/slurm-%x-%j.out" \
      "$batch_script" "$tag" "$events" "$runner_dir/$runner_name")"
    echo "$job_id | $tag | $runner_name"
  done
} | tee "$record"
echo "Submission record: $record"
