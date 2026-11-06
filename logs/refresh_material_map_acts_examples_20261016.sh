#!/usr/bin/env bash
# One-time refresh of the ACTS example cache used by the EPIC material-map runner.
# Preserve the existing examples and patch downloads before installing v46.8.1.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
material_dir="$repo_root/scripts/material_map"
archive_dir="$repo_root/proj_svt_disk_tiling/tmp/retained/2026-10-16/material_map_acts_refresh"
action_log="$repo_root/proj_svt_disk_tiling/tmp/file_actions.log"
refresh_log="$repo_root/proj_svt_disk_tiling/logs/refresh_material_map_acts_examples_20261016.txt"
acts_version="v46.8.1"

if [[ -e "$archive_dir" ]]; then
  printf 'ERROR: archive already exists: %s\n' "$archive_dir" >&2
  exit 1
fi
if [[ ! -d "$material_dir/Examples" ]]; then
  printf 'ERROR: missing cached Examples directory: %s\n' "$material_dir/Examples" >&2
  exit 1
fi
if ! grep -Fq 'ACTS_VERSION="v46.8.1"' "$material_dir/run_material_map_validation.sh"; then
  printf '%s\n' 'ERROR: runner no longer selects ACTS v46.8.1.' >&2
  exit 1
fi

exec > >(tee "$refresh_log") 2>&1
printf 'ACTS example refresh: %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf 'Source tag: %s\n' "$acts_version"

staging_dir="$(mktemp -d "$repo_root/proj_svt_disk_tiling/tmp/acts_examples_stage.XXXXXXXX")"
acts_files=(
  Examples/Scripts/Python/geometry.py
  Examples/Scripts/Python/material_mapping.py
  Examples/Scripts/Python/material_recording.py
  Examples/Scripts/Python/material_validation.py
  Examples/Scripts/MaterialMapping/writeMapConfig.py
  Examples/Scripts/MaterialMapping/configureMap.py
  Examples/Scripts/MaterialMapping/GeometryVisualisationAndMaterialHandling.py
  Examples/Scripts/MaterialMapping/Mat_map.C
  Examples/Scripts/MaterialMapping/Mat_map_surface_plot.C
  Examples/Scripts/MaterialMapping/Mat_map_surface_plot_ratio.C
  Examples/Scripts/MaterialMapping/Mat_map_surface_plot_dist.C
  Examples/Scripts/MaterialMapping/Mat_map_surface_plot_1D.C
  Examples/Scripts/MaterialMapping/Mat_map_detector_plot.C
  Examples/Scripts/MaterialMapping/materialPlotHelper.cpp
  Examples/Scripts/MaterialMapping/materialPlotHelper.hpp
)

for relative_path in "${acts_files[@]}"; do
  output_path="$staging_dir/$relative_path"
  mkdir -p "$(dirname "$output_path")"
  curl --fail --silent --show-error --location --max-time 60 \
    --output "$output_path" \
    "https://raw.githubusercontent.com/acts-project/acts/$acts_version/$relative_path"
  printf 'Downloaded %s\n' "$relative_path"
done

python3 -B - "$staging_dir" <<'PY'
import ast
import sys
from pathlib import Path

python_dir = Path(sys.argv[1]) / "Examples/Scripts/Python"
expected_keywords = {
    "material_recording.py": ("runMaterialRecording", "outputFileBase"),
    "material_mapping.py": ("runMaterialMapping", "outputFileBase"),
    "material_validation.py": ("runMaterialValidation", "outputFileBase"),
}
for filename, (function_name, parameter_name) in expected_keywords.items():
    tree = ast.parse((python_dir / filename).read_text(), filename=filename)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    function = functions[function_name]
    parameter_names = [argument.arg for argument in function.args.args]
    assert parameter_name in parameter_names, (filename, parameter_names)
    print("Verified {} accepts {}".format(function_name, parameter_name))
PY

# Keep the local validation-map adjustment normally applied on first download
# by run_material_map_validation.sh.
patch -d "$staging_dir" -p1 <<'PATCH'
diff -aru a/Examples/Scripts/MaterialMapping/Mat_map.C b/Examples/Scripts/MaterialMapping/Mat_map.C
--- a/Examples/Scripts/MaterialMapping/Mat_map.C
+++ b/Examples/Scripts/MaterialMapping/Mat_map.C
@@ -145,7 +145,8 @@

     // 2D map for Validation input
     TCanvas *VM = new TCanvas("VM","Validation Map") ;
-    Val_file->Draw("mat_y:mat_z","std::abs(mat_x)<1");
+    Val_file->Draw("sqrt(mat_x**2+mat_y**2):mat_z>>mat_map1","(mat_z>-5000)&(mat_z<8000)");
+    VM->SetGrid();

     eta_0->Draw("Same");
     eta_1p->Draw("Same");
PATCH

mkdir -p "$archive_dir"
mv "$material_dir/Examples" "$archive_dir/Examples"
printf '%s | scripts/material_map/Examples/ | %s | move | retain pre-v46.8.1 ACTS example cache\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${archive_dir#"$repo_root/"}/Examples/" >> "$action_log"

for patch_name in 6010.diff 6012.diff; do
  if [[ -f "$material_dir/$patch_name" ]]; then
    mv "$material_dir/$patch_name" "$archive_dir/$patch_name"
    printf '%s | scripts/material_map/%s | %s | move | force patch refresh with the v46.8.1 examples\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$patch_name" \
      "${archive_dir#"$repo_root/"}/$patch_name" >> "$action_log"
  fi
done

mv "$staging_dir/Examples" "$material_dir/Examples"
printf '%s | %s | scripts/material_map/Examples/ | move | install verified ACTS v46.8.1 examples\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  "${staging_dir#"$repo_root/"}/Examples/" >> "$action_log"
printf 'PASS: refreshed %s ACTS examples; original cache retained at %s\n' \
  "$acts_version" "$archive_dir"
printf '%s\n' 'The runner will download and apply patches 6010 and 6012 on the next smoke test.'
