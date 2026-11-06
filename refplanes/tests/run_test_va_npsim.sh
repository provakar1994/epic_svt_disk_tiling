#!/usr/bin/env bash
# 10-event npsim through the VolumeAssembly test plane (HD4), then print the cellIDs of its hits.
# Report: tests/run_test_va_npsim.txt
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
top="$here/generated_test_test_volumeassembly_planes.xml"
out=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/tests; mkdir -p "$out"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
{
  "$here/../eic_exec.sh" "npsim --compactFile $top --steeringFile $here/test_va_steering.py \
    --outputFile $out/va_test_$stamp.root --numberOfEvents 10 --random.seed 7 --enableGun \
    --gun.distribution eta --gun.etaMin 3.4 --gun.etaMax 4.0 --gun.particle pi+ \
    --gun.momentumMin '5*GeV' --gun.momentumMax '20*GeV' --output.part WARNING" 2>&1 | grep -i "RefPlaneVATest\|sensitive detector type\|Unknown\|error\|exception" | grep -v envelope26 | head -20
  module load conda >/dev/null 2>&1; conda activate tracking
  python3 -c "
import uproot, awkward as ak
t = uproot.open('$out/va_test_$stamp.root')['events']
c = ak.flatten(t['RefPlaneVATestHits/RefPlaneVATestHits.cellID'].array())
z = ak.flatten(t['RefPlaneVATestHits/RefPlaneVATestHits.position.z'].array())
print('n hits', len(c)); print('cellIDs', [hex(int(v)) for v in c[:10]]); print('z', list(z[:10]))
print('system', [int(v) & 0xff for v in c[:10]], 'barrel', [(int(v) >> 8) & 7 for v in c[:10]], 'layer', [(int(v) >> 11) & 15 for v in c[:10]])
"
} > "$here/run_test_va_npsim.txt" 2>&1
cat "$here/run_test_va_npsim.txt"
