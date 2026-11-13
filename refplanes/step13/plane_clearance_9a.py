#!/usr/bin/env python3
"""[Step 13 copy, 2026-11-12, refplanes/step13/: paths resolve inside step13/ (generated/, plane_map.csv, silicon_disks_refplanes.xml); otherwise unchanged from refplanes/plane_clearance_9a.py]
Step 9a: clearance table for the SVT disk reference planes.

Runs INSIDE eic_xl:26.09.0-stable (DD4hep python), on the installed
epic_craterlake_tracking_only.xml.  Run via plane_clearance_9a.sh.

For each of the 10 SVT endcap disks it
  1. confirms from the compact XML text that the disk layer envelope is
     zstart = Mod_zmin - SiTrackerEndcapLayer_thickness/2, length = thickness,
     and Mod_zmin = nominal disk z constant  ->  envelope = z_disk +/- 5 mm;
  2. evaluates z_disk, the disk *_rmin and *_rmax constants numerically;
  3. sets z_plane = sign * (|z_disk| - 6 mm) (plane slab +/- 0.05 mm);
  4. ray-traces the TGeo geometry radially from r = 0 at three z values
     inside the slab, for 720 azimuths, and records every non-world volume
     crossed. Inner obstacles (r_enter < rmin) must end below rmin; the first
     volume entered at r >= rmin limits rmax.
  5. rmax = min(disk_rmax + 20 mm, floor_0.5mm(r_block - 1 mm)).

Units: DD4hep/TGeo internal unit is cm; everything printed is mm.
Output: text on stdout and plane_clearance_9a.json next to this script.
"""
import json
import math
import os
import re
import sys

import ROOT
import dd4hep

CM_TO_MM = 10.0
HALF_THICKNESS_MM = 0.05      # plane slab is 0.1 mm thick
UPSTREAM_OFFSET_MM = 6.0      # plane centre is 6 mm upstream of the disk centre
RMAX_EXTRA_MM = 20.0          # requested rmax = disk rmax + 20 mm
CLEARANCE_MM = 1.0            # radial clearance kept to the limiting volume
N_PHI = 720

here = os.path.dirname(os.path.abspath(__file__))
detector_path = os.environ["DETECTOR_PATH"]
xml_file = os.path.join(detector_path, "epic_craterlake_tracking_only.xml")

# disk name, z constant, rmin constant, rmax constant, Layer zmin constant, Mod zmin constant, sign
DISKS = [
    ("ED0", "InnerTrackerEndcapN_zmin", "InnerTrackerEndcapN_rmin", "InnerTrackerEndcapN_rmax",
     "InnerTrackerEndcapNLayer1_zmin", "InnerTrackerEndcapNMod1_zmin", -1),
]
for k in range(1, 5):
    DISKS.append((f"ED{k}", f"TrackerEndcapNDisk{k}_zmin", f"TrackerEndcapNDisk{k}_rmin",
                  f"TrackerEndcapNDisk{k}_rmax", f"TrackerEndcapNLayer{k}_zmin",
                  f"TrackerEndcapNMod{k}_zmin", -1))
DISKS.append(("HD0", "InnerTrackerEndcapP_zmin", "InnerTrackerEndcapP_rmin", "InnerTrackerEndcapP_rmax",
              "InnerTrackerEndcapPLayer1_zmin", "InnerTrackerEndcapPMod1_zmin", +1))
for k in range(1, 5):
    DISKS.append((f"HD{k}", f"TrackerEndcapPDisk{k}_zmin", f"TrackerEndcapPDisk{k}_rmin",
                  f"TrackerEndcapPDisk{k}_rmax", f"TrackerEndcapPLayer{k}_zmin",
                  f"TrackerEndcapPMod{k}_zmin", +1))


def read_constants_text(path):
    """name -> value-expression string for every <constant> in a compact file."""
    text = open(path).read()
    return dict(re.findall(r'<constant\s+name="([^"]+)"\s+value="([^"]+)"', text))


def text_checks():
    """Confirm the layer-envelope and rmin expressions in the compact XML."""
    modules = read_constants_text(os.path.join(detector_path, "compact/tracking/silicon_disks_modules.xml"))
    defs = read_constants_text(os.path.join(detector_path, "compact/tracking/definitions_craterlake.xml"))
    mod_text = open(os.path.join(detector_path, "compact/tracking/silicon_disks_modules.xml")).read()
    ok = True
    lines = []
    for name, zc, rminc, rmaxc, layerc, modc, sign in DISKS:
        layer_expr = modules.get(layerc, "")
        mod_expr = modules.get(modc, "")
        rmin_expr = defs.get(rminc, "")
        good_layer = layer_expr.replace(" ", "") == f"{modc}-SiTrackerEndcapLayer_thickness/2"
        good_mod = mod_expr.strip() == zc
        good_zstart = f'zstart="{layerc}"' in mod_text
        good_rmin = rmin_expr.replace(" ", "").startswith("max(abs(") and "lepton_radius" in rmin_expr \
            and "hadron_radius" in rmin_expr
        ok &= good_layer and good_mod and good_zstart and good_rmin
        lines.append(f"  {name}: {layerc} = '{layer_expr}' [{'ok' if good_layer else 'BAD'}]; "
                     f"{modc} = '{mod_expr}' [{'ok' if good_mod else 'BAD'}]; "
                     f"envelope zstart uses it [{'ok' if good_zstart else 'BAD'}]; "
                     f"{rminc} = '{rmin_expr}' [{'ok' if good_rmin else 'BAD'}]")
    thick_expr = defs.get("SiTrackerEndcapLayer_thickness", "")
    buffer_expr = defs.get("Beampipe_bakeout_buffer", "")
    lines.insert(0, f"  SiTrackerEndcapLayer_thickness = '{thick_expr}', Beampipe_bakeout_buffer = '{buffer_expr}'")
    return ok, lines


def trace_ray(nav, top_node, phi, z_mm, r_end_mm):
    """Radial ray from r=0 at height z.  Returns [(r_in, r_out, path)] for non-world volumes (mm)."""
    ux, uy = math.cos(phi), math.sin(phi)
    z = z_mm / CM_TO_MM
    r_end = r_end_mm / CM_TO_MM
    nav.InitTrack(0.0, 0.0, z, ux, uy, 0.0)
    segments = []
    r = 0.0
    n_zero = 0
    while r < r_end:
        level = nav.GetLevel()
        path = nav.GetPath()
        nav.FindNextBoundaryAndStep(r_end - r)
        step = nav.GetStep()
        if level > 0:
            segments.append((r * CM_TO_MM, (r + step) * CM_TO_MM, path))
        r += step
        if step < 1e-9:
            n_zero += 1
            if n_zero > 1000:
                raise RuntimeError(f"navigator stuck at phi={phi}, z={z_mm}, r={r}")
        if nav.IsOutside():
            break
    return segments


def short_name(path):
    """Strip the world prefix and copy numbers to name the top-level volume of a path."""
    parts = [p for p in path.split("/") if p]
    return "/".join(parts[1:4]) if len(parts) > 1 else path


def main():
    ok_text, text_lines = text_checks()
    print("=== Step 9a: SVT reference-plane clearance table ===")
    print(f"Geometry: {xml_file}")
    print(f"Plane: Vacuum slab, thickness {2 * HALF_THICKNESS_MM} mm, centre z_plane = sign*(|z_disk| - {UPSTREAM_OFFSET_MM} mm)")
    print("\n-- Compact-XML expression checks (installed copies) --")
    for line in text_lines:
        print(line)
    print(f"Expression checks: {'PASS' if ok_text else 'FAIL'}")
    if not ok_text:
        print("STOP: rmin or layer-envelope expression not in the expected form.")
        sys.exit(1)

    description = dd4hep.Detector.getInstance()
    description.fromXML(xml_file)
    const = lambda n: description.constantAsDouble(n) * CM_TO_MM
    thickness = const("SiTrackerEndcapLayer_thickness")
    print(f"\nSiTrackerEndcapLayer_thickness = {thickness:.4f} mm -> envelope half-length {thickness / 2:.4f} mm")
    assert abs(const("InnerTrackerEndcapP_zmin") - 250.0) < 1e-9, "unit conversion check failed"

    geo = ROOT.gGeoManager
    nav = geo.GetCurrentNavigator() or geo.AddNavigator()
    top = geo.GetTopNode()
    print(f"TGeo top node: {top.GetName()}")

    results = []
    all_ok = True
    for name, zc, rminc, rmaxc, layerc, modc, sign in DISKS:
        z_abs = const(zc)
        z_disk = sign * z_abs
        layer_zmin = const(layerc)
        env_lo, env_hi = layer_zmin, layer_zmin + thickness       # |z| range of the disk envelope
        z_plane = sign * (z_abs - UPSTREAM_OFFSET_MM)
        rmin = const(rminc)
        disk_rmax = const(rmaxc)
        target = disk_rmax + RMAX_EXTRA_MM
        gap_to_env = env_lo - (abs(z_plane) + HALF_THICKNESS_MM)

        z_samples = [z_plane - HALF_THICKNESS_MM + 1e-4, z_plane, z_plane + HALF_THICKNESS_MM - 1e-4]
        inner_max = 0.0
        inner_name = ""
        block_r = float("inf")
        block_name = ""
        block_phi = None
        for zs in z_samples:
            for i in range(N_PHI):
                phi = 2 * math.pi * i / N_PHI
                for r_in, r_out, path in trace_ray(nav, top, phi, zs, target + 60.0):
                    if r_in < rmin:
                        if r_out > inner_max:
                            inner_max, inner_name = r_out, short_name(path)
                    elif r_in < block_r:
                        block_r, block_name, block_phi = r_in, short_name(path), math.degrees(phi)
        if block_r < target + CLEARANCE_MM:
            rmax = math.floor((block_r - CLEARANCE_MM) * 2.0) / 2.0
            limiting = block_name
        else:
            rmax = target
            limiting = "none (disk rmax + 20 mm)"
        inner_ok = inner_max < rmin
        env_ok = gap_to_env > 0
        row_ok = inner_ok and env_ok and rmax > disk_rmax
        all_ok &= row_ok
        results.append(dict(disk=name, side="N" if sign < 0 else "P", z_disk_mm=z_disk, z_plane_mm=z_plane,
                            env_absz_lo_mm=env_lo, env_absz_hi_mm=env_hi, gap_plane_to_env_mm=gap_to_env,
                            rmin_mm=rmin, rmin_const=rminc, disk_rmax_mm=disk_rmax, target_rmax_mm=target,
                            inner_obstacle_rmax_mm=inner_max, inner_obstacle=inner_name,
                            first_outer_volume_r_mm=block_r, first_outer_volume=block_name,
                            first_outer_volume_phi_deg=block_phi, rmax_mm=rmax, limiting_volume=limiting,
                            ok=row_ok))

    print("\n-- Clearance table (mm) --")
    hdr = (f"{'disk':4} {'z_disk':>8} {'z_plane':>8} {'env|z|':>15} {'gap':>5} {'rmin':>8} "
           f"{'bp_rmax':>8} {'d_rmax':>6} {'target':>6} {'r_block':>8} {'rmax':>6}  limiting / first outer volume")
    print(hdr)
    for r in results:
        print(f"{r['disk']:4} {r['z_disk_mm']:8.1f} {r['z_plane_mm']:8.1f} "
              f"{r['env_absz_lo_mm']:7.1f}-{r['env_absz_hi_mm']:<7.1f} {r['gap_plane_to_env_mm']:5.2f} "
              f"{r['rmin_mm']:8.3f} {r['inner_obstacle_rmax_mm']:8.3f} {r['disk_rmax_mm']:6.1f} "
              f"{r['target_rmax_mm']:6.1f} {r['first_outer_volume_r_mm']:8.2f} {r['rmax_mm']:6.1f}  "
              f"{r['limiting_volume']} | first outer: {r['first_outer_volume']} @phi={r['first_outer_volume_phi_deg']}"
              f"{'' if r['ok'] else '  <-- FAIL'}")
    print("\nColumns: env|z| = disk layer envelope |z| range; gap = |z| distance from plane face to envelope face;")
    print("bp_rmax = outer radius of the last volume starting below rmin (beam pipe), must be < rmin;")
    print("r_block = smallest radius at which any volume starts at r >= rmin within the slab (720 phi x 3 z rays);")
    print(f"rmax = disk rmax + {RMAX_EXTRA_MM} mm unless r_block < that + {CLEARANCE_MM} mm, then floor_0.5mm(r_block - {CLEARANCE_MM} mm).")
    with open(os.path.join(here, "plane_clearance_9a.json"), "w") as f:
        json.dump(results, f, indent=1)
    print(f"\nStep 9a overall: {'PASS' if all_ok else 'FAIL'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
