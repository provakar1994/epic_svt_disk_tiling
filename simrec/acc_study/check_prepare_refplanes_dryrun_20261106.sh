#!/usr/bin/env bash
# Recorded dry run of prepare_acceptance_tasks_refplanes.sh.
# Writes the task list into a temporary directory under simrec/acc_study/tmp/,
# audits it (300 tasks, 6 configurations x 50, unique seeds/tags, no overlap with
# earlier campaigns, every line sim mode with ACC_XML/ACC_STEERING), then moves
# the temporary directory to proj_svt_disk_tiling/tmp/retained/2026-11-06/ and
# logs the move. Does NOT create task_lists/acceptance_v3_refplanes.
# Report: logs/check_prepare_refplanes_dryrun_20261106.txt
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
dry_root="$script_dir/tmp/dryrun_task_lists_refplanes_20261106"
retain_dir="$project_dir/tmp/retained/2026-11-06"
report="$script_dir/logs/check_prepare_refplanes_dryrun_20261106.txt"
campaign=acceptance_v3_refplanes
[[ ! -e "$dry_root" ]] || { echo "ERROR: $dry_root exists" >&2; exit 2; }
[[ ! -e "$script_dir/task_lists/$campaign" ]] || { echo "ERROR: real task list already exists" >&2; exit 2; }

{
  echo "check_prepare_refplanes_dryrun_20261106: $(date --iso-8601=seconds)"
  echo "prepare script sha256: $(sha256sum "$script_dir/prepare_acceptance_tasks_refplanes.sh" | cut -d' ' -f1)"
  DRY_RUN_TASK_ROOT="$dry_root" "$script_dir/prepare_acceptance_tasks_refplanes.sh" "$campaign"
  tasks="$dry_root/$campaign/tasks.txt"
  manifest="$dry_root/$campaign/manifest.tsv"
  echo "--- audit ---"
  echo "command lines:          $(grep -vc '^#' "$tasks")"
  echo "manifest rows:          $(awk 'NR>1' "$manifest" | wc -l)"
  echo "unique seeds:           $(awk 'NR>1{print $8}' "$manifest" | sort -u | wc -l)"
  echo "seed range:             $(awk 'NR>1{print $8}' "$manifest" | sort -n | sed -n '1p;$p' | paste -sd- )"
  echo "earlier seed ranges:"
  for m in "$script_dir"/task_lists/*/manifest.tsv; do
    echo "  $(basename "$(dirname "$m")"): $(awk 'NR>1{print $8}' "$m" | sort -n | sed -n '1p;$p' | paste -sd-)"
  done
  echo "tasks per configuration (vertex, eta range, events):"
  awk -F'\t' 'NR>1{n[$2" vz="$3" eta=["$4","$5"]"]++; e[$2" vz="$3" eta=["$4","$5"]"]+=$7} END{for(k in n) printf "  %-40s %3d tasks %9d events\n", k, n[k], e[k]}' "$manifest" | sort
  echo "lines in sim mode:      $(grep -v '^#' "$tasks" | grep -c '/run_sim.sh sim ')"
  echo "lines with ACC_XML and ACC_STEERING prefix: $(grep -v '^#' "$tasks" | grep -c '^ACC_XML=[^ ]*epic_craterlake_tracking_only_refplanes.xml ACC_STEERING=[^ ]*npsim_refplanes_steering.py ')"
  echo "first task line:"; awk '!/^#/{print; exit}' "$tasks"
  echo "last task line:";  awk '!/^#/{last=$0} END{print last}' "$tasks"
  echo "one packed wave on 4 nodes x 90 slots = 360 >= 300 tasks: $([[ $(grep -vc '^#' "$tasks") -le 360 ]] && echo yes || echo no)"
  echo "real task_lists/$campaign created: $([[ -e "$script_dir/task_lists/$campaign" ]] && echo YES-UNEXPECTED || echo no)"
} > "$report" 2>&1

# Retain (do not delete) the dry-run output and log the move.
mkdir -p "$retain_dir"
target="$retain_dir/simrec_acc_study_tmp_dryrun_task_lists_refplanes_20261106"
mv "$dry_root" "$target"
printf '%s | %s | %s | moved | Dry-run output of prepare_acceptance_tasks_refplanes.sh (audit in %s); not a real task list\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "proj_svt_disk_tiling/simrec/acc_study/tmp/dryrun_task_lists_refplanes_20261106" \
  "proj_svt_disk_tiling/tmp/retained/2026-11-06/$(basename "$target")" \
  "simrec/acc_study/logs/$(basename "$report")" >> "$project_dir/tmp/file_actions.log"
echo "dry-run output retained at: $target" >> "$report"
cat "$report"
