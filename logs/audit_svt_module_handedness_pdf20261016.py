#!/usr/bin/env python3
"""Audit module handedness: 20261016 "Module Definitions" slides vs the EPIC builder.

Read-only. Reproduces, in Python, the per-row orientation logic of
src/SiEndcapModuleTracker_geo.cpp (state of 2026-11-11, uncommitted Step 11b):
  catalogue chirality -> source handedness (NEGATIVE/RIGHT -> "right", POSITIVE/LEFT -> "left")
  placed handedness   = swapped (x_EPIC = -x_engineer reflection)
  rotation_y = 0 if sensor normal is +z else pi
  rotation_z = 0 if local_x_axis_sign * normal_sign > 0 else pi   (RotationZYX = Rz*Ry)
  bridge FPC in the prototype: top edge at the RSU upper (+y) edge, body runs toward local -y;
  Step 8j: for y_origin <= 0 the FPC/AncASIC local y is reversed (body runs toward local +y).

Slide convention (ES_material/20261016-Module Definitions.pdf, slides 3, 4, 9-13):
  sensor frame: x from LEC toward REC, y toward the "top tiles", z away from the carbon fibre.
  handedness = side to which the FPC extends: +y_sensor -> "right handed", -y_sensor -> "left".
  Equivalent rotation-invariant definition used here:
      H = det[ a, b, c ],  a = LEC->REC unit vector, b = FPC side, c = sensor normal
      H = +1 <-> slide-13 "right handed",  H = -1 <-> "left handed".
  ED1 top half, back face (slides 7-12): every FPC tab points to global +Y (toward the rim).

Delivery convention (ES_material/20261110/transition/module_cad_export.py):
  sx = -sign(x_eng), sy = sign(y), sz = -face_sign*facing_sign, POSITIVE <-> sx*sy*sz = +1.
  With slide 9 (sx,sy,sz)=(1,1,1) as the POSITIVE reference pose, the FPC of every module
  points to sign(y) (toward the rim) and POSITIVE == slide-13 right handed.

Usage: python3 -I audit_svt_module_handedness_pdf20261016.py [scenario_dir] > report.txt
"""

import csv
import math
import sys
from collections import Counter
from pathlib import Path

EPIC = Path("/global/cfs/cdirs/m3763/pdatta/epic")
DEFAULT_DIR = EPIC / "compact/tracking/silicon_disks_tiling/20261110_ES/rsu_opt"
DISKS = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]

# Builder constants (compact/tracking/silicon_disks_modules.xml, mm).
RSU_LENGTH = 21.666  # checked below against catalogue active length / rsu_count
BLEC = 20.0
BREC = 10.0


def sign(v):
    return 1 if v > 0 else -1


def main():
    scen = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    catalog = {r["type_id"]: r for r in csv.DictReader(open(scen / "catalog.csv"))}
    chir_src = {t: (+1 if r["chirality"] in ("POSITIVE", "LEFT") else -1) for t, r in catalog.items()}

    counts = Counter()
    examples = {}
    n = 0
    for disk in DISKS:
        path = scen / f"{disk}_modules.csv"
        if not path.exists():
            path = scen / f"{disk}b_modules.csv"
        for m in csv.DictReader(open(path)):
            n += 1
            t = m["type_id"]
            cat = catalog[t]
            x_eng, y = float(m["x_origin_mm"]), float(m["y_origin_mm"])
            normal = sign(float(m["z_sensor_mm"]) - float(m["z_baseplate_mm"]))
            x_epic = -x_eng
            chir = chir_src[t]

            # --- delivery's own convention (engineer frame) ---
            sx, sy, sz = -sign(x_eng), sign(y), normal
            delivery_ok = (sx * sy * sz == chir)

            # --- builder ---
            source_hand = "left" if chir > 0 else "right"
            placed_hand = "right" if source_hand == "left" else "left"
            x_size = float(cat["module_length_mm"])
            chain = int(cat["rsu_count"]) * RSU_LENGTH
            if placed_hand == "left":   # LEC at local -x
                boundary_local = -x_size / 2 + BLEC
                lec_local_dir = -1
            else:                       # REC span first, LEC after the RSUs at local +x
                boundary_local = -x_size / 2 + BREC + chain
                lec_local_dir = +1
            x_center = x_epic - math.copysign(abs(boundary_local), x_epic)
            local_x_axis_sign = (x_epic - x_center) / boundary_local
            ry_pi = normal < 0
            rz_pi = (local_x_axis_sign * normal) < 0
            gx = (-1 if ry_pi else 1) * (-1 if rz_pi else 1)  # image of local +x
            gy = (-1 if rz_pi else 1)                          # image of local +y
            gz = (-1 if ry_pi else 1)                          # image of local +z
            assert gz == normal and gx * gy * gz == 1

            lec_global = gx * lec_local_dir          # global x direction of the LEC end
            fpc_local = -1 * (-1 if y <= 0 else 1)   # body toward -y; Step 8j flips y<=0
            fpc_global = gy * fpc_local
            a = -lec_global                          # LEC->REC along global x
            H_built = a * fpc_global * normal

            # Expected in EPIC (mirror of the delivery, FPC toward the rim as in the slides)
            fpc_expected = sign(y)
            H_expected_mirror = -chir

            key = (
                "delivery_parity_ok" if delivery_ok else "delivery_parity_BAD",
                "LEC_outer" if lec_global == sign(x_epic) else "LEC_inner",
                "local_y->sign(y)" if gy == sign(y) else "local_y->-sign(y)",
                "FPC_to_rim" if fpc_global == fpc_expected else "FPC_to_midplane",
                "H_matches_mirror" if H_built == H_expected_mirror else "H_opposite_mirror",
                "y>0" if y > 0 else "y<=0",
            )
            counts[key] += 1
            examples.setdefault(key, (disk, m["row_index"], m["mod_index"], t, x_eng, y, normal))

    print(f"scenario: {scen}")
    print(f"modules: {n}")
    print("H = det[LEC->REC, FPC side, sensor normal]; +1 = slide-13 'right handed'")
    print()
    for key, c in sorted(counts.items()):
        print(f"{c:5d}  " + "  ".join(key))
        d, r, i, t, xe, yy, nz = examples[key]
        print(f"       e.g. {d} row {r} mod {i} {t} x_eng={xe:.2f} y={yy:.2f} normal={nz:+d}")


if __name__ == "__main__":
    main()
