#!/usr/bin/env bash
# Recorded pre-campaign smoke test for acceptance_v4_step13 (2026-11-12).
# Runs two real task lines of task_lists/acceptance_v4_step13/tasks.txt through run_sim.sh, exactly
# as the campaign calls them (same ACC_XML / ACC_STEERING, vertex, eta range, seed), except:
#   - EVENTS 100000 -> 200, tag suffix _n100000 -> _smoke_n200;
#   - OUTPUT_DIR moved from the campaign root to a separate smoke root (campaign layout kept:
#     <smoke root>/<configuration>/{rootfiles,logs}).
# Two tasks (not one) so that both eta sides of one vertex exist: extract_disk_particles_refplanes.py
# needs both sides of a vertex. Chosen: vz = +100 mm, chunk 001, both eta signs (tasks 101 and 151;
# vz = +100 is where v3 showed the steepest-incidence HD0 loss).
# Both run in parallel in one container call. Check with check_smoke_test_20261112_v4_step13.sh.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
task_file="$script_dir/task_lists/acceptance_v4_step13/tasks.txt"
smoke_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/smoke_20261112_v4_step13"
task_numbers=(101 151)
container_runtime="/cvmfs/oasis.opensciencegrid.org/mis/singularity/bin/singularity"
container_image="/cvmfs/singularity.opensciencegrid.org/eicweb/eic_xl:26.09.0-stable"
campaign_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v4_step13"

[[ -f "$task_file" ]] || { echo "ERROR: task file not found: $task_file" >&2; exit 2; }
[[ ! -e "$smoke_root" ]] || { echo "ERROR: smoke output already exists: $smoke_root" >&2; exit 2; }

commands=()
for n in "${task_numbers[@]}"; do
  line="$(awk -v wanted="$n" '/^[[:space:]]*($|#)/ {next} {count++} count == wanted {print; exit}' "$task_file")"
  [[ -n "$line" ]] || { echo "ERROR: no task $n" >&2; exit 2; }
  # Exactly one occurrence of each substituted field is required.
  [[ "$(grep -o " 100000 " <<< "$line" | wc -l)" -eq 1 && "$(grep -o "$campaign_root/" <<< "$line" | wc -l)" -eq 1 ]] \
    || { echo "ERROR: unexpected task line $n: $line" >&2; exit 2; }
  smoke_line="${line/ 100000 / 200 }"
  smoke_line="${smoke_line/$campaign_root\//$smoke_root/}"
  smoke_line="${smoke_line/_n100000 /_smoke_n200 }"
  echo "task $n (campaign): $line"
  echo "task $n (smoke):    $smoke_line"
  commands+=("$smoke_line")
done

mkdir -p "$smoke_root"
{
  echo "Smoke test of acceptance_v4_step13, $(date -u --iso-8601=seconds) on $(hostname)"
  echo "Task file: $task_file (sha256 $(sha256sum "$task_file" | cut -d' ' -f1))"
  for i in "${!commands[@]}"; do echo "Command $((i + 1)): ${commands[$i]}"; done
} > "$smoke_root/smoke_commands.txt"

export APPTAINER_BINDPATH=/global,/pscratch
inner="(${commands[0]}) & (${commands[1]}) & wait"
start=$(date +%s)
"$container_runtime" exec "$container_image" /opt/local/bin/eic-shell "$inner"
echo "Wall time for both tasks (parallel): $(( $(date +%s) - start )) s" | tee -a "$smoke_root/smoke_commands.txt"
