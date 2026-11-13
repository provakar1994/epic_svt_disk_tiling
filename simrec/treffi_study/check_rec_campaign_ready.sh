#!/usr/bin/env bash
# Gate before a tracking analysis of a reconstructed acceptance campaign (2026-11-13).
# Usage: ./check_rec_campaign_ready.sh CAMPAIGN_DIR EXPECTED_MAP_SHA256 [N_PER_CONFIG] [CONFIG ...]
#   defaults: N_PER_CONFIG=50, CONFIGs = the two vz = 0 configurations.
# Passes (exit 0) only if, for every configuration:
#   - exactly N_PER_CONFIG non-empty rec_*.root files exist in <config>/rootfiles (no *.tmp.*);
#   - no *.tmp.* file exists in <config>/rootfiles (running or failed sim/recon task);
#   - every rec file has its log <config>/logs/rec_<tag>.log, and that log has the line
#     "<EXPECTED_MAP_SHA256>  <path>/material-map_map.cbor" (written by run_sim.sh before
#     eicrecon starts), an "acts ... loading materials map" line and a "Finished:" line.
# Prints one line per configuration and "GATE: PASS" or "GATE: FAIL".
set -uo pipefail
shopt -s nullglob
campaign_dir="${1:?usage: $0 CAMPAIGN_DIR EXPECTED_MAP_SHA256 [N_PER_CONFIG] [CONFIG ...]}"
sha="${2:?usage: $0 CAMPAIGN_DIR EXPECTED_MAP_SHA256 [N_PER_CONFIG] [CONFIG ...]}"
n_expected="${3:-50}"
shift 3 2>/dev/null || shift $#
configs=("$@")
[[ ${#configs[@]} -gt 0 ]] || configs=(vz_000mm_eta_m3p8_to_m0p6 vz_000mm_eta_p0p6_to_p3p8)
[[ "$sha" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: EXPECTED_MAP_SHA256 must be 64 lowercase hex digits"; echo "GATE: FAIL"; exit 1; }

bad=0
echo "Rec-campaign gate: $(date -u --iso-8601=seconds) $campaign_dir map sha256 $sha"
for config in "${configs[@]}"; do
  rootdir="$campaign_dir/$config/rootfiles"; logdir="$campaign_dir/$config/logs"
  tmp=("$rootdir"/*.tmp.*)
  rec=()
  for f in "$rootdir"/rec_*.root; do [[ "$f" == *.tmp.* ]] || rec+=("$f"); done
  n_empty=0; n_nolog=0; n_badsha=0; n_unfinished=0
  for f in "${rec[@]}"; do
    [[ -s "$f" ]] || n_empty=$((n_empty + 1))
    log="$logdir/$(basename "${f%.root}").log"
    if [[ ! -f "$log" ]]; then n_nolog=$((n_nolog + 1)); continue; fi
    grep -Eq "^${sha}  .*material-map_map\.cbor\$" "$log" && grep -q "loading materials map" "$log" \
      || n_badsha=$((n_badsha + 1))
    grep -q "^Finished:" "$log" || n_unfinished=$((n_unfinished + 1))
  done
  status=ok
  if [[ ${#rec[@]} -ne "$n_expected" || ${#tmp[@]} -ne 0 || $n_empty -ne 0 || $n_nolog -ne 0 || $n_badsha -ne 0 || $n_unfinished -ne 0 ]]; then
    status=FAIL; bad=1
  fi
  echo "  [$status] $config: rec files ${#rec[@]}/$n_expected, *.tmp.* ${#tmp[@]}, empty $n_empty," \
       "missing logs $n_nolog, logs without the map sha256 $n_badsha, logs without Finished $n_unfinished"
done
if [[ $bad -eq 0 ]]; then echo "GATE: PASS"; else echo "GATE: FAIL"; fi
exit $bad
