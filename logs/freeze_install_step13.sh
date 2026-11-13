#!/usr/bin/env bash
# Step 13 geometry freeze for the overnight downstream reruns (material map, material scan,
# acceptance_v4_step13 campaign). Rebuilds install/ from the committed EPIC HEAD and records the
# identity (HEAD, XML/library checksums, tiling scenario) that every later step checks against.
# Run INSIDE eic_xl:26.09.0-stable:
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash proj_svt_disk_tiling/logs/freeze_install_step13.sh"
# Report: proj_svt_disk_tiling/logs/freeze_install_step13.txt
set -euo pipefail
epic=/global/cfs/cdirs/m3763/pdatta/epic
proj=$epic/proj_svt_disk_tiling
report=$proj/logs/freeze_install_step13.txt
cd "$epic"
exec > >(tee "$report") 2>&1

echo "Step 13 install freeze: $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(hostname)"
[[ -z "$(git status --short --untracked-files=no -- src compact)" ]] \
  || { echo "ERROR: uncommitted changes in src/ or compact/"; exit 1; }
echo "EPIC HEAD=$(git rev-parse HEAD) ($(git log -1 --format=%s))"

cmake -S . -B build -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF > "$proj/tmp_freeze_configure.log" 2>&1
cmake --build build -j8 > "$proj/tmp_freeze_build.log" 2>&1
cmake --install build > "$proj/tmp_freeze_install.log" 2>&1
echo "build/install: OK"
mkdir -p "$epic/tmp/freeze_step13"
mv "$proj"/tmp_freeze_*.log "$epic/tmp/freeze_step13/"

# Installed geometry must equal the checkout and use the production tiling scenario.
cmp -s compact/tracking/silicon_disks_modules.xml install/share/epic/compact/tracking/silicon_disks_modules.xml \
  && echo "installed silicon_disks_modules.xml == checkout" || { echo "ERROR: installed module XML differs"; exit 1; }
scen=$(grep -o 'silicon_disks_tiling/[^"]*" format="tiling-directory"' install/share/epic/compact/tracking/silicon_disks_modules.xml | sort -u)
echo "tiling scenarios in installed XML: $scen"
[[ "$scen" == 'silicon_disks_tiling/20261110_ES/rsu_opt" format="tiling-directory"' ]] \
  || { echo "ERROR: production scenario is not 20261110_ES/rsu_opt"; exit 1; }

# Quick load test: the tracking-only geometry builds without errors.
source install/bin/thisepic.sh
export DETECTOR_PATH=$epic/install/share/epic
python3 - <<'PY'
import os
import dd4hep
d = dd4hep.Detector.getInstance()
d.fromXML(os.environ["DETECTOR_PATH"] + "/epic_craterlake_tracking_only.xml")
print("geometry load: OK, world daughters =", d.world().placement().volume().GetNdaughters())
PY

echo "checksums (sha256):"
sha256sum install/share/epic/epic_craterlake_tracking_only.xml install/share/epic/epic_craterlake_material_map.xml \
  install/share/epic/compact/tracking/silicon_disks_modules.xml install/lib/libepic.so
echo "FREEZE OK"
