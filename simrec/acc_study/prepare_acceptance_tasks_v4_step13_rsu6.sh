#!/usr/bin/env bash
# Generate the auditable 300-task Step 13 reference-plane campaign for the 20261110_ES/rsu6 tiling
# scenario; do not submit it.
# Step 14b copy (2026-11-13) of prepare_acceptance_tasks_v4_step13.sh (acceptance_v4_step13, rsu_opt).
# Same physics as v4; changes:
#   - campaign acceptance_v4_step13_rsu6 (EPIC 78ade4686 install + frozen rsu6 overlay
#     proj_svt_disk_tiling/geometry_overlays/step13/rsu6/);
#   - ACC_XML / ACC_STEERING point at the rsu6 refplane overlay in refplanes/step13_rsu6/;
#   - refuses to run unless refplanes/step13_rsu6/identity_check_step13_rsu6.sh passes (Step 13
#     install identity + overlay sha256 from its provenance.txt); kept in identity_check.txt;
#   - every task line starts with "cd <simrec/acc_study> &&": the module_placements path in the overlay
#     is relative (compact/tracking/silicon_disks_tiling/20261110_ES/rsu6) and is resolved against the
#     CWD before $DETECTOR_PATH; simrec/acc_study has no compact/ subdirectory (checked here), so the
#     installed CSVs are used whatever directory sbatch is called from;
#   - SEEDS: deliberately the SAME as acceptance_v4_step13 (base 44000000, 44000001-44005050), as requested
#     for a paired rsu_opt vs rsu6 comparison. CAVEAT (found in the Step 14b smoke test, 2026-11-13):
#     npsim without --random.enableEventSeed draws the gun and the Geant4 transport from ONE random
#     stream, so the primaries are identical only until the first event whose transport differs
#     between the geometries (events 0-1 of task 151 identical, event 2 on different). The samples are
#     therefore statistically equivalent but effectively independent, not paired. The generated
#     manifest.tsv must be byte-identical to task_lists/acceptance_v4_step13/manifest.tsv. The seed
#     overlap check allows exactly that paired sim manifest, plus task lists DERIVED from it that cannot
#     generate events (every task "run_sim.sh recon" on the paired campaign output root, e.g.
#     acceptance_v4_step13_rec_step13; eicrecon does not use the seed). Any other overlap is an error.
#
# Usage:
#   ./prepare_acceptance_tasks_v4_step13_rsu6.sh [CAMPAIGN]
#   DRY_RUN_TASK_ROOT=/some/dir ./prepare_acceptance_tasks_v4_step13_rsu6.sh [CAMPAIGN]
#       writes task_lists-style output under /some/dir/CAMPAIGN only; creates nothing on /pscratch.
#   SEED_CHECK_TASK_LISTS=/dir (testing only; default task_lists/): directory whose */manifest.tsv
#       are checked for seed overlaps.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"          # proj_svt_disk_tiling
runner="$script_dir/run_sim.sh"
campaign="${1:-acceptance_v4_step13_rsu6}"
[[ "$campaign" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'ERROR: unsafe campaign name.' >&2; exit 2; }
[[ -x "$runner" ]] || { echo "ERROR: runner is not executable: $runner" >&2; exit 2; }
[[ ! -e "$script_dir/compact" ]] || { echo "ERROR: $script_dir/compact exists; it would shadow DETECTOR_PATH" >&2; exit 2; }

refplanes_xml="$project_dir/refplanes/step13_rsu6/generated/epic_craterlake_tracking_only_rsu6_refplanes.xml"
refplanes_steering="$project_dir/refplanes/step13_rsu6/npsim_refplanes_steering.py"
overlay_provenance="$project_dir/geometry_overlays/step13/rsu6/provenance.txt"
identity_check="$project_dir/refplanes/step13_rsu6/identity_check_step13_rsu6.sh"
identity_text="$("$identity_check")" || { echo "$identity_text" >&2; echo "ERROR: rsu6 geometry identity check failed." >&2; exit 2; }

paired_campaign="acceptance_v4_step13"
paired_manifest="$script_dir/task_lists/$paired_campaign/manifest.tsv"
storage_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study"
paired_output_root="$storage_root/$paired_campaign"
[[ -f "$paired_manifest" ]] || { echo "ERROR: paired manifest missing: $paired_manifest" >&2; exit 2; }

dry_run_root="${DRY_RUN_TASK_ROOT:-}"
if [[ -n "$dry_run_root" ]]; then
  task_dir="$dry_run_root/$campaign"
else
  task_dir="$script_dir/task_lists/$campaign"
fi
task_file="$task_dir/tasks.txt"
manifest="$task_dir/manifest.tsv"
output_root="$storage_root/$campaign"
[[ ! -e "$task_dir" ]] || { echo "ERROR: task directory exists: $task_dir" >&2; exit 2; }
for required in "$refplanes_xml" "$refplanes_steering" "$overlay_provenance"; do
  [[ -f "$required" ]] || { echo "ERROR: file not found: $required" >&2; exit 2; }
done

if [[ -n "$dry_run_root" ]]; then
  mkdir -p "$task_dir"
else
  mkdir -p "$task_dir" "$storage_root/slurm" "$output_root"
fi
echo "$identity_text" > "$task_dir/identity_check.txt"

vertex_values=(0 0 100 100 -100 -100)
vertex_labels=(000 000 p100 p100 m100 m100)
eta_mins=(0.6 -3.8 0.6 -3.8 0.6 -3.8)
eta_maxs=(3.8 -0.6 3.8 -0.6 3.8 -0.6)
eta_labels=(p0p6_to_p3p8 m3p8_to_m0p6 p0p6_to_p3p8 m3p8_to_m0p6 p0p6_to_p3p8 m3p8_to_m0p6)
events=100000
chunks=50
expected_tasks=$(( ${#vertex_values[@]} * chunks ))
seed_base=44000000  # SAME as acceptance_v4_step13 on purpose (paired comparison); see header

printf 'task\tconfiguration\tvertex_z_mm\teta_min\teta_max\tchunk\tevents\tseed\ttag\n' > "$manifest"
{
  echo "# Campaign: $campaign (scenario 20261110_ES/rsu6; paired with $paired_campaign, same seeds)"
  echo '# 3 vertex positions (z = 0, +100, -100 mm) x 2 eta ranges x 50 chunks = 300 tasks'
  echo '# 100,000 events/task; 30,000,000 events total; mode sim (no reconstruction)'
  echo "# ACC_XML=$refplanes_xml"
  echo "# ACC_STEERING=$refplanes_steering"
  echo "# ACC_XML sha256: $(sha256sum "$refplanes_xml" | cut -d' ' -f1)"
  echo "# rsu6 overlay provenance: $overlay_provenance (sha256 $(sha256sum "$overlay_provenance" | cut -d' ' -f1))"
  echo "# Task CWD: $script_dir (no compact/ subdirectory; relative tiling path -> \$DETECTOR_PATH)"
  echo "# Geometry identity (refplanes/step13_rsu6/identity_check_step13_rsu6.sh):"
  echo "$identity_text" | sed 's/^/#   /'
} > "$task_file"

task_number=0
for config_index in "${!vertex_values[@]}"; do
  configuration="vz_${vertex_labels[$config_index]}mm_eta_${eta_labels[$config_index]}"
  output_dir="$output_root/$configuration"
  for ((chunk = 1; chunk <= chunks; chunk++)); do
    task_number=$((task_number + 1))
    chunk_label="$(printf '%03d' "$chunk")"
    seed=$((seed_base + config_index * 1000 + chunk))
    tag="${configuration}_chunk_${chunk_label}_n${events}"
    printf '%d\t%s\t%s\t%s\t%s\t%d\t%d\t%d\t%s\n' \
      "$task_number" "$configuration" "${vertex_values[$config_index]}" \
      "${eta_mins[$config_index]}" "${eta_maxs[$config_index]}" "$chunk" \
      "$events" "$seed" "$tag" >> "$manifest"
    command=("$runner" sim "$output_dir" "$tag" "$events" \
      "${vertex_values[$config_index]}" "${eta_mins[$config_index]}" \
      "${eta_maxs[$config_index]}" "$seed")
    printf 'cd %q && ' "$script_dir" >> "$task_file"
    printf 'ACC_XML=%q ACC_STEERING=%q ' "$refplanes_xml" "$refplanes_steering" >> "$task_file"
    printf '%q ' "${command[@]}" >> "$task_file"
    printf '\n' >> "$task_file"
  done
done

[[ "$task_number" -eq "$expected_tasks" ]] || { echo "ERROR: generated $task_number tasks, expected $expected_tasks." >&2; exit 1; }
unique_seeds="$(awk 'NR > 1 {print $8}' "$manifest" | sort -u | wc -l)"
[[ "$unique_seeds" -eq "$expected_tasks" ]] || { echo "ERROR: generated $unique_seeds unique seeds, expected $expected_tasks." >&2; exit 1; }
unique_tags="$(awk 'NR > 1 {print $9}' "$manifest" | sort -u | wc -l)"
[[ "$unique_tags" -eq "$expected_tasks" ]] || { echo "ERROR: generated $unique_tags unique tags, expected $expected_tasks." >&2; exit 1; }

# Paired design: the manifest (task, configuration, vertex, eta, chunk, events, seed, tag) must equal
# the rsu_opt v4 manifest byte for byte.
cmp -s "$manifest" "$paired_manifest" || { echo "ERROR: manifest differs from paired $paired_manifest" >&2; exit 1; }
echo "Paired manifest: byte-identical to $paired_manifest (sha256 $(sha256sum "$manifest" | cut -d' ' -f1))"

# Seed overlap: allowed = the paired sim manifest and recon-only task lists on the paired output root.
seed_lists_dir="${SEED_CHECK_TASK_LISTS:-$script_dir/task_lists}"
is_derived_recon() {  # task-list dir -> 0 if every task is run_sim.sh recon on the paired output root
  local tasks="$1/tasks.txt" n_all n_ok
  [[ -f "$tasks" ]] || return 1
  n_all="$(awk '!/^[[:space:]]*($|#)/' "$tasks" | wc -l)"
  n_ok="$(awk '!/^[[:space:]]*($|#)/' "$tasks" | grep -cF "run_sim.sh recon $paired_output_root/" || true)"
  [[ "$n_all" -gt 0 && "$n_all" -eq "$n_ok" ]]
}
shopt -s nullglob
checked=(); allowed=()
for other in "$seed_lists_dir"/*/manifest.tsv; do
  [[ "$(realpath "$other")" != "$(realpath "$manifest")" ]] || continue
  other_dir="$(dirname "$other")"
  if [[ "$(basename "$other_dir")" == "$paired_campaign" ]] && cmp -s "$other" "$paired_manifest"; then
    allowed+=("$other (paired sim manifest)"); continue
  fi
  if is_derived_recon "$other_dir"; then allowed+=("$other (recon of $paired_campaign, no event generation)"); continue; fi
  checked+=("$other")
done
if (( ${#checked[@]} > 0 )); then
  overlap="$(comm -12 <(awk 'NR > 1 {print $8}' "$manifest" | sort -u) \
                     <(awk 'FNR > 1 {print $8}' "${checked[@]}" | sort -u) | wc -l)"
  [[ "$overlap" -eq 0 ]] || { echo "ERROR: $overlap seeds overlap other campaigns: ${checked[*]}" >&2; exit 1; }
fi
echo "Seed overlap with ${#checked[@]} other manifest(s): none"
for a in "${allowed[@]}"; do echo "Seed overlap allowed by design: $a"; done

echo "Prepared: $task_file ($task_number tasks, $unique_seeds unique seeds)"
echo "Manifest: $manifest"
echo "Output:   $output_root"
if [[ -n "$dry_run_root" ]]; then
  echo "DRY RUN: nothing created under task_lists/ or $storage_root"
else
  echo "Submit (from $script_dir): sbatch --time=04:00:00 --job-name=svt-v4r6-sim submit_premium_packed.sh task_lists/$campaign/tasks.txt"
fi
