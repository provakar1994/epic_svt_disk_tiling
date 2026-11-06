#!/usr/bin/env bash
# Generate the reference-plane overlay detector XML (Step 9b).
#
# Copies the INSTALLED $DETECTOR_PATH/epic_craterlake_tracking_only.xml to
#   refplanes/generated/epic_craterlake_tracking_only_refplanes.xml
# and inserts exactly one line
#   <include ref="<absolute path>/refplanes/silicon_disks_refplanes.xml"/>
# right after the silicon_disks_modules.xml include. All other includes keep
# their ${DETECTOR_PATH} form, so the generated XML must be loaded with
# DETECTOR_PATH pointing at the same install (epic/install/share/epic).
# Provenance (EPIC commit, sha256 of source XML and of the plane XML) goes to
#   generated/epic_craterlake_tracking_only_refplanes.provenance.txt
#
# Usage: make_refplanes_xml.sh        (host or container; needs only bash/awk/git)
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic_root="$(cd "$here/../.." && pwd)"
detector_path="${DETECTOR_PATH:-$epic_root/install/share/epic}"
source_xml="$detector_path/epic_craterlake_tracking_only.xml"
plane_xml="$here/silicon_disks_refplanes.xml"
out_dir="$here/generated"
out_xml="$out_dir/epic_craterlake_tracking_only_refplanes.xml"
sidecar="$out_dir/epic_craterlake_tracking_only_refplanes.provenance.txt"

[[ -f "$source_xml" ]] || { echo "ERROR: source XML not found: $source_xml" >&2; exit 2; }
[[ -f "$plane_xml" ]] || { echo "ERROR: plane XML not found: $plane_xml" >&2; exit 2; }
anchor='compact/tracking/silicon_disks_modules.xml"'
n_anchor=$(grep -c "$anchor" "$source_xml" || true)
[[ "$n_anchor" -eq 1 ]] || { echo "ERROR: expected 1 silicon_disks_modules.xml include, found $n_anchor" >&2; exit 2; }
grep -q "silicon_disks_refplanes.xml" "$source_xml" && { echo "ERROR: source already includes the planes" >&2; exit 2; }

mkdir -p "$out_dir"
# Insert the include on the line after the anchor, with the anchor's indentation.
awk -v anchor="$anchor" -v ref="$plane_xml" '
  { print }
  index($0, anchor) > 0 {
    match($0, /^[ \t]*/); indent = substr($0, 1, RLENGTH)
    print indent "<include ref=\"" ref "\"/>"
  }' "$source_xml" > "$out_xml.tmp"
mv "$out_xml.tmp" "$out_xml"

{
  echo "Generated: $(date -u --iso-8601=seconds) by $here/make_refplanes_xml.sh"
  echo "EPIC checkout: $epic_root"
  echo "EPIC commit: $(git -C "$epic_root" rev-parse HEAD) ($(git -C "$epic_root" rev-parse --abbrev-ref HEAD))"
  echo "EPIC tracked changes (git status --short --untracked-files=no):"
  git -C "$epic_root" status --short --untracked-files=no | sed 's/^/  /'
  echo "DETECTOR_PATH: $detector_path"
  echo "source sha256: $(sha256sum "$source_xml")"
  echo "plane XML sha256: $(sha256sum "$plane_xml")"
  echo "output sha256: $(sha256sum "$out_xml")"
} > "$sidecar"

echo "Wrote $out_xml"
echo "Wrote $sidecar"
