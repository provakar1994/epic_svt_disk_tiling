#!/usr/bin/env bash
# Phase 3 of acceptance_v4_step13 (2026-11-13): analysis after the sim (Slurm 61213457) and the
# Step 13 reconstruction have finished. Runs, in this order:
#   acceptance (simrec/acc_study, conda "tracking"; log acc_study/logs/phase3_v4_step13_<UTC>.log)
#     1. run_extract_refplanes_v4_step13.sh 0 | 100 | -100   (in parallel, as for v3)
#     2. run_refplane_efficiency_v4_step13.sh                 -> results/refplane_efficiency_v5/
#     3. compare_refplane_v3_v4.py (v3 = results/refplane_efficiency_v4)
#                                    -> results/refplane_efficiency_v5/compare_v3_v4.{txt,csv}
#   tracking (simrec/treffi_study, conda "tracking"; log treffi_study/logs/phase3_v4_step13_<UTC>.log)
#     4. run_v4_step13_analysis_20261113.sh STEP13_MAP_SHA256
# No step needs the container: the only eic-shell input, the Step 13 active-silicon dump
# (acc_study/geometry/active_silicon_rectangles_step13.csv), was made beforehand by
# acc_study/run_dump_active_silicon_step13.sh. The v3 analyses also ran in conda "tracking".
# Gates: acceptance needs 50 sim files per configuration (all 6) and no sim_*.tmp.* files, and free
# output locations; tracking needs check_rec_campaign_ready.sh to pass with the given map sha256.
# Usage: ./run_v4_step13_phase3.sh STEP13_MAP_SHA256 [all|acceptance|tracking] [--check-only]
#   STEP13_MAP_SHA256 may be "none" for the acceptance part only (it does not use the map).
#   --check-only: run the gates of the selected parts and stop.
set -euo pipefail
shopt -s nullglob
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
acc="$here/acc_study"; trk="$here/treffi_study"
usage() { echo "Usage: $0 STEP13_MAP_SHA256 [all|acceptance|tracking] [--check-only]" >&2; exit 2; }
[[ $# -ge 1 && $# -le 3 ]] || usage
map_sha="$1"; part="${2:-all}"; check_only=0
[[ "${3:-}" == "" || "${3:-}" == --check-only ]] || usage
[[ "${3:-}" == --check-only ]] && check_only=1
case "$part" in all|acceptance|tracking) ;; --check-only) part=all; check_only=1 ;; *) usage ;; esac
if [[ "$part" != acceptance ]]; then
  [[ "$map_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: the tracking part needs the 64-hex Step 13 map sha256" >&2; exit 2; }
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
campaign_root=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v4_step13

acceptance_gate() {
  local bad=0 config sims tmps f
  for config in vz_{000,p100,m100}mm_eta_{m3p8_to_m0p6,p0p6_to_p3p8}; do
    sims=(); for f in "$campaign_root/$config/rootfiles"/sim_*.root; do [[ "$f" == *.tmp.* ]] || sims+=("$f"); done
    tmps=("$campaign_root/$config/rootfiles"/sim_*.tmp.*)
    echo "  $config: sim files ${#sims[@]}/50, sim_*.tmp.* ${#tmps[@]}"
    [[ ${#sims[@]} -eq 50 && ${#tmps[@]} -eq 0 ]] || bad=1
  done
  for f in "$acc/extracted/acceptance_v4_step13/extraction_manifest_vz_"*.csv "$acc/results/refplane_efficiency_v5"; do
    [[ ! -e "$f" ]] || { echo "  output exists: $f"; bad=1; }
  done
  for f in "$acc/geometry/active_silicon_rectangles_step13.csv" "$acc/geometry/row_families_20261110_ES_rsu_opt.csv" \
           "$acc/results/refplane_efficiency_v4/vz_000mm/summary.txt"; do
    [[ -s "$f" ]] || { echo "  missing input: $f"; bad=1; }
  done
  if [[ $bad -eq 0 ]]; then echo "Acceptance gate: PASS"; else echo "Acceptance gate: FAIL"; fi
  return $bad
}

run_acceptance() {
  echo "=== acceptance part, $(date -Is)"
  acceptance_gate || return 1
  [[ $check_only -eq 0 ]] || return 0
  local pids=() vz status=0
  for vz in 0 100 -100; do
    "$acc/run_extract_refplanes_v4_step13.sh" "$vz" > /dev/null &   # own log in acc_study/logs; gate errors (stderr) land here
    pids+=($!)
  done
  for pid in "${pids[@]}"; do wait "$pid" || status=1; done
  [[ $status -eq 0 ]] || { echo "ERROR: an extraction failed; see acc_study/logs/extract_refplanes_v4_step13_*.log"; return 1; }
  echo "Extraction finished: $(date -Is)"
  "$acc/run_refplane_efficiency_v4_step13.sh" || { echo "ERROR: run_refplane_efficiency_v4_step13.sh failed"; return 1; }
  ( module load conda; conda activate tracking
    python3 "$acc/compare_refplane_v3_v4.py" --out-prefix "$acc/results/refplane_efficiency_v5/compare_v3_v4" \
      > "$acc/results/refplane_efficiency_v5/compare_v3_v4.txt" ) || { echo "ERROR: compare_refplane_v3_v4.py failed"; return 1; }
  echo "Wrote $acc/results/refplane_efficiency_v5/compare_v3_v4.txt"
  echo "=== acceptance part finished, $(date -Is)"
}

run_tracking() {
  echo "=== tracking part, $(date -Is)"
  if [[ $check_only -eq 1 ]]; then
    "$trk/run_v4_step13_analysis_20261113.sh" "$map_sha" --check-only || return 1
  else
    "$trk/run_v4_step13_analysis_20261113.sh" "$map_sha" || { echo "ERROR: tracking analysis failed"; return 1; }
  fi
  echo "=== tracking part finished, $(date -Is)"
}

# Note: the two parts run as the left side of "||" below, where bash ignores set -e, so every
# step inside run_acceptance/run_tracking checks its own status and returns 1 on failure.
mkdir -p "$acc/logs" "$trk/logs"
failed=0
# pipefail is set, so "|| status=$?" catches a failure of the part (not of tee).
if [[ "$part" != tracking ]]; then
  status=0
  run_acceptance 2>&1 | tee "$acc/logs/phase3_v4_step13_${stamp}.log" || status=$?
  if [[ $status -ne 0 ]]; then
    echo "ERROR: acceptance part failed" >&2
    [[ $check_only -eq 1 ]] || exit 1      # with --check-only, still report the tracking gate
    failed=1
  fi
fi
if [[ "$part" != acceptance ]]; then
  status=0
  run_tracking 2>&1 | tee "$trk/logs/phase3_v4_step13_${stamp}.log" || status=$?
  [[ $status -eq 0 ]] || { echo "ERROR: tracking part failed" >&2; exit 1; }
fi
[[ $failed -eq 0 ]] || exit 1
echo "Phase 3 ($part) done: $(date -Is)"
