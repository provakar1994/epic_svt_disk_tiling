#!/usr/bin/env bash
# Recorded check of the opt-in ACC_XML / ACC_STEERING overrides in run_sim.sh.
# No real simulation: a stub "npsim" placed first in PATH only prints its
# arguments and writes an empty output file, so the command line that
# run_sim.sh assembles can be compared with and without the overrides.
# Usage: ./check_run_sim_overrides_20261106.sh  (writes logs/check_run_sim_overrides_20261106.txt)
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/check_run_sim_overrides.XXXXXX")"
report="$script_dir/logs/check_run_sim_overrides_20261106.txt"
mkdir -p "$work_dir/bin" "$script_dir/logs"

# Stub npsim: echo arguments, create the --outputFile target.
cat > "$work_dir/bin/npsim" <<'STUB'
#!/usr/bin/env bash
echo "STUB npsim called with $# arguments"
out=""
while [[ $# -gt 0 ]]; do
  [[ "$1" == --outputFile ]] && out="$2"
  shift
done
: > "$out"
STUB
chmod +x "$work_dir/bin/npsim"

# Dummy override inputs (content irrelevant; only paths and hashes are checked).
echo '<lccdd/>' > "$work_dir/dummy_compact.xml"
echo '# dummy steering' > "$work_dir/dummy_steering.py"

run_case() {  # name, then env assignments
  local name="$1"; shift
  env PATH="$work_dir/bin:$PATH" "$@" \
    "$script_dir/run_sim.sh" sim "$work_dir/$name" "check_$name" 10 0 0.6 3.8 12345 >/dev/null
  echo "===== case: $name ($*) ====="
  grep -E '^(Command|Compact XML|Steering file):' "$work_dir/$name/logs/sim_check_$name.log"
  echo "sha256 lines:"
  grep -E '^[0-9a-f]{64}  ' "$work_dir/$name/logs/sim_check_$name.log"
}

{
  echo "check_run_sim_overrides_20261106: $(date --iso-8601=seconds)"
  echo "work dir: $work_dir"
  echo "run_sim.sh sha256: $(sha256sum "$script_dir/run_sim.sh" | cut -d' ' -f1)"
  run_case default
  run_case xml_only ACC_XML="$work_dir/dummy_compact.xml"
  run_case both ACC_XML="$work_dir/dummy_compact.xml" ACC_STEERING="$work_dir/dummy_steering.py"
  echo "===== case: missing steering file (must fail with status 2) ====="
  set +e
  env PATH="$work_dir/bin:$PATH" ACC_STEERING="$work_dir/does_not_exist.py" \
    "$script_dir/run_sim.sh" sim "$work_dir/missing" check_missing 10 0 0.6 3.8 12345
  echo "exit status: $?"
  set -e
  # The default-case command must equal the original command line exactly
  # (after removing the per-run temporary output path and work dir).
  echo "===== default command vs original run_sim.sh command template ====="
  default_cmd="$(grep '^Command:' "$work_dir/default/logs/sim_check_default.log")"
  expected="Command: npsim --compactFile $(cd "$script_dir/../../.." && pwd)/install/share/epic/epic_craterlake_tracking_only.xml --outputFile $work_dir/default/rootfiles/sim_check_default.tmp.local.0.root --numberOfEvents 10 --random.seed 12345 --enableGun --gun.phiMin 0\\*degree --gun.phiMax 360\\*degree --gun.distribution eta --gun.etaMin 0.6 --gun.etaMax 3.8 --gun.particle pi+ --gun.position 0\\ 0\\ 0\\*mm --gun.momentumMin 0.5\\*GeV --gun.momentumMax 20\\*GeV --gun.multiplicity 1 --output.part WARNING"
  if [[ "$default_cmd" == "$expected" ]]; then echo "default command identical to original: PASS"
  else echo "default command differs: FAIL"; echo "got:      $default_cmd"; echo "expected: $expected"; fi
} > "$report" 2>&1

cat "$report"
echo "Report: $report  (stub outputs kept in $work_dir)"
