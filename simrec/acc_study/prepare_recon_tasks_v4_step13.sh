#!/usr/bin/env bash
# Generate (do not submit) the 300 reconstruction tasks for the acceptance_v4_step13 npsim files,
# using a Step 13 ACTS material map made from epic_craterlake_tracking_only.xml.
# Step 13 copy (2026-11-12) of prepare_recon_tasks_v3_step8q.sh. Changes:
#   - reads the v4 sim manifest (task_lists/acceptance_v4_step13/manifest.tsv) and the v4 output root;
#   - the material map and its expected sha256 are ARGUMENTS (the Step 13 map is made separately,
#     under proj_svt_disk_tiling/matmap/step13_<stamp>/material-map_map.cbor);
#   - refuses to run unless refplanes/step13/identity_check_step13.sh passes (EPIC HEAD,
#     silicon_disks_modules.xml, libepic.so), because eicrecon uses the installed geometry and the
#     map must come from that same geometry;
#   - default task-list name acceptance_v4_step13_rec_step13.
# As in v3:
# - Reads tag, vertex, eta range and seed from the sim manifest (the seed is only recorded;
#   eicrecon does not use it).
# - Each task: ACC_MATERIAL_MAP=<map> run_sim.sh recon <v4 config dir> <tag> 100000 ...
#   ACC_XML is NOT set, so eicrecon uses the plain installed epic_craterlake_tracking_only.xml
#   (the reference planes are not in the ACTS geometry; the extra plane-hit collections in the
#   sim files are ignored).
# - Output: rec_<tag>.root / rec_<tag>.log next to the sim files.
# - Every sim file must exist (run after the sim campaign has completed).
# Submit with (from simrec/acc_study):
#   sbatch --time=01:00:00 --job-name=svt-v4-rec submit_premium_packed.sh task_lists/<name>/tasks.txt
# Usage: ./prepare_recon_tasks_v4_step13.sh MATERIAL_MAP_CBOR EXPECTED_SHA256 [TASK_LIST_NAME]
set -euo pipefail

usage() { echo "Usage: $0 MATERIAL_MAP_CBOR EXPECTED_SHA256 [TASK_LIST_NAME]" >&2; }
[[ $# -ge 2 && $# -le 3 ]] || { usage; exit 2; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
runner="$script_dir/run_sim.sh"
material_map="$(realpath -e -- "$1")" || { echo "ERROR: material map not found: $1" >&2; exit 2; }
expected_map_sha="$2"
name="${3:-acceptance_v4_step13_rec_step13}"
[[ "$expected_map_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: EXPECTED_SHA256 must be 64 hex digits" >&2; exit 2; }
[[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'ERROR: unsafe task-list name.' >&2; exit 2; }
sim_manifest="$script_dir/task_lists/acceptance_v4_step13/manifest.tsv"
output_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v4_step13"
task_dir="$script_dir/task_lists/$name"
identity_check="$project_dir/refplanes/step13/identity_check_step13.sh"

[[ ! -e "$task_dir" ]] || { echo "ERROR: task directory exists: $task_dir" >&2; exit 2; }
[[ -f "$sim_manifest" ]] || { echo "ERROR: missing $sim_manifest" >&2; exit 2; }
[[ "$(sha256sum "$material_map" | cut -d' ' -f1)" == "$expected_map_sha" ]] || { echo "ERROR: map checksum mismatch" >&2; exit 2; }
identity_text="$("$identity_check")" || { echo "$identity_text" >&2; echo "ERROR: Step 13 geometry identity check failed." >&2; exit 2; }
# Pre-check (new in v4): count missing sim files before creating the task directory, so a
# premature run leaves nothing behind.
n_missing=0
while IFS=$'\t' read -r _ configuration _ _ _ _ _ _ tag; do
  [[ -s "$output_root/$configuration/rootfiles/sim_${tag}.root" ]] || n_missing=$((n_missing + 1))
done < <(tail -n +2 "$sim_manifest")
[[ "$n_missing" -eq 0 ]] || { echo "ERROR: $n_missing of 300 sim files missing under $output_root; nothing written" >&2; exit 1; }

mkdir -p "$task_dir"
task_file="$task_dir/tasks.txt"
manifest="$task_dir/manifest.tsv"
echo "$identity_text" > "$task_dir/identity_check.txt"
{
  echo "# Reconstruction of acceptance_v4_step13 (300 x 100k events), mode recon"
  echo "# ACC_MATERIAL_MAP=$material_map (sha256 $expected_map_sha)"
  echo "# Compact XML: run_sim.sh default \$DETECTOR_PATH/epic_craterlake_tracking_only.xml"
  echo "# Geometry identity (refplanes/step13/identity_check_step13.sh):"
  echo "$identity_text" | sed 's/^/#   /'
} > "$task_file"
printf 'task\tconfiguration\tvertex_z_mm\teta_min\teta_max\tchunk\tevents\tseed\ttag\n' > "$manifest"

n=0
missing=0
while IFS=$'\t' read -r task configuration vz eta_min eta_max chunk events seed tag; do
  sim_file="$output_root/$configuration/rootfiles/sim_${tag}.root"
  [[ -s "$sim_file" ]] || { echo "MISSING sim file: $sim_file" >&2; missing=$((missing + 1)); continue; }
  [[ ! -e "$output_root/$configuration/rootfiles/rec_${tag}.root" ]] || { echo "ERROR: rec file exists for $tag" >&2; exit 1; }
  n=$((n + 1))
  printf '%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$n" "$configuration" "$vz" "$eta_min" "$eta_max" "$chunk" "$events" "$seed" "$tag" >> "$manifest"
  printf 'ACC_MATERIAL_MAP=%q ' "$material_map" >> "$task_file"
  printf '%q ' "$runner" recon "$output_root/$configuration" "$tag" "$events" "$vz" "$eta_min" "$eta_max" "$seed" >> "$task_file"
  printf '\n' >> "$task_file"
done < <(tail -n +2 "$sim_manifest")

[[ "$missing" -eq 0 && "$n" -eq 300 ]] || { echo "ERROR: $n tasks, $missing missing sim files (expected 300, 0)" >&2; exit 1; }
echo "Wrote $n tasks to $task_file"
echo "Submit (from $script_dir): sbatch --time=01:00:00 --job-name=svt-v4-rec submit_premium_packed.sh task_lists/$name/tasks.txt"
