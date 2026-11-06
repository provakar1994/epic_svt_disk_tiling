#!/usr/bin/env bash
# Feasibility test of DD4hep_VolumeAssembly for opening-shaped planes.
# Builds tests/generated_test.xml = installed tracking-only XML + one include of the test XML
# (same insertion as make_refplanes_xml.sh), then inspects it. Report: tests/run_test_volumeassembly.txt
# Usage: run_test_volumeassembly.sh [TEST_XML] [DETECTOR_NAME]
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic=/global/cfs/cdirs/m3763/pdatta/epic
test_xml="${1:-$here/test_volumeassembly_planes.xml}"
det="${2:-RefPlaneVATest}"
top="$here/generated_test_$(basename "$test_xml")"
awk -v anchor='compact/tracking/silicon_disks_modules.xml"' -v ref="$test_xml" \
  '{ print } index($0, anchor) > 0 { print "  <include ref=\"" ref "\"/>" }' \
  "$epic/install/share/epic/epic_craterlake_tracking_only.xml" > "$top"
report="$here/run_test_volumeassembly_$(basename "$test_xml" .xml).txt"
{
  echo "Started: $(date -u --iso-8601=seconds)"; echo "test XML: $test_xml"; echo "top XML: $top"
  "$here/../eic_exec.sh" "python3 $here/test_volumeassembly.py $top $det"
  echo "exit status: $?"
} > "$report" 2>&1
grep -v "Info in\|INFO\|^\s*$\|envelope26" "$report" | tail -40
