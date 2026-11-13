#!/usr/bin/env python3
"""Step 11f: source-level validation of the 20261110 "-r" SVT endcap tiling package.

The provider's "-r" package (systematic studies) is staged byte-for-byte at
compact/tracking/silicon_disks_tiling/20261110-r_ES/{rsu_opt,rsu6}.  Its build log
(ES_material/20261110-r/transition/<scen>/flip_facing_build.log) says every disk
was "flipped".  This script reads only delivered CSV/metadata files and writes a
text report next to itself.

    module load conda; conda activate tracking
    python proj_svt_disk_tiling/logs/validate_svt_delivery_20261110r_step11f.py

Checks (both scenarios):
  0. staged files byte-identical to ES_material/20261110-r/transition/<scen>
  A. standalone checks reused from the Step 11c validator (imported, unchanged):
     11c check 1 (files/headers/keys/metadata), 3 (placement z with the Step 11b
     stack, plus a facing-vs-normal orientation statement), 5 (rows, BLOCKED, vs the
     reconstructed 20261001 lattice), 6 (bridge-FPC vs end-film pairs), 7 (inward
     FPC vs carbon)
  B. -r versus 20261110_ES (same scenario): x/y identity, type mapping, z changes,
     rows.csv, catalogue, metadata
  C. physical interpretation (mounting plane, sensor plane, facing counts per disk,
     in-plane footprint of the modelled electronics)
  D. all-component pair audit (any facing combination) with the 11c component model
     plus the AncASIC box of the Step 11b builder; ES vs -r

Conventions (same as the 11c validator / SiEndcapModuleTracker_geo.cpp):
  - module normal n = sign(z_sensor - z_baseplate) (from baseplate to sensor);
  - u = signed distance along n measured from the CSV z_baseplate plane;
  - engineer frame -> EPIC: x_EPIC = -x_engineer.
All lengths in mm.
"""

import filecmp
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the Step 11c validator (its loaders, check functions, stack model and
# component boxes).  Its say()/verdict() collect into v11c.LINES / v11c.RESULTS;
# this script uses the same lists and writes its own report file.
import validate_svt_delivery_20261110_step11c as v11c
from validate_svt_delivery_20261110_step11c import say, verdict, section, TOL, DISKS_NEW

ROOT = v11c.ROOT
TILING = ROOT / "compact/tracking/silicon_disks_tiling"
REV = TILING / "20261110-r_ES"          # "-r" package (flipped)
BASE = TILING / "20261110_ES"           # reference package (Step 11a-e)
OLD = TILING / "20261001_ES"            # needed only by 11c check 5 (lattice comparison)
SOURCE = ROOT / "proj_svt_disk_tiling/ES_material/20261110-r/transition"
REPORT = Path(__file__).with_suffix(".txt")
SCENARIOS = ("rsu_opt", "rsu6")
KEYS = ["disk_id", "row_index", "mod_index"]

# AncASIC (Step 11b builder, silicon_disks_modules.xml): 3.3 mm (x) x 15 mm (y),
# 80 um glue + 300 um chip, on the front-side FPC (Kapton+Al outward, Kapton inward),
# 5 mm from the left FPC's outer x edge, 1 mm below the left FPC's top y edge.
ANCASIC_X, ANCASIC_Y = 3.3, 15.0
ANCASIC_GLUE, ANCASIC_CHIP = 0.080, 0.300
ANCASIC_OUTER_EDGE_CLEARANCE, ANCASIC_TOP_CLEARANCE = 5.0, 1.0


# ---------------------------------------------------------------------------
# Check 0: staging provenance
# ---------------------------------------------------------------------------
def check_staging(scen):
    staged = sorted(p.name for p in (REV / scen).iterdir())
    bad = [f for f in staged if not filecmp.cmp(REV / scen / f, SOURCE / scen / f, shallow=False)]
    verdict(f"0.{scen} staged files byte-identical to ES_material/20261110-r/transition/{scen}",
            not bad, f"{len(staged)} files, differing={bad}")


# ---------------------------------------------------------------------------
# A: placement orientation statement (11c only printed it)
# ---------------------------------------------------------------------------
def check_orientation(scen, placed):
    """placed = output of v11c.check_placement_z (has facing, n, n_toward_center)."""
    for facing in ("INWARD", "OUTWARD"):
        sub = placed[placed.facing == facing]
        toward = int(sub.n_toward_center.sum())
        say(f"    {scen} {facing}: normal toward disk mid-plane {toward}/{len(sub)}, "
            f"away {len(sub) - toward}/{len(sub)}")
    inw = placed[placed.facing == "INWARD"]
    out = placed[placed.facing == "OUTWARD"]
    same_as_11c = inw.n_toward_center.all() and (~out.n_toward_center).all()
    inverted = (~inw.n_toward_center).all() and out.n_toward_center.all()
    state = ("same as 20261110_ES: INWARD -> mid-plane, OUTWARD -> away" if same_as_11c else
             "INVERTED w.r.t. 20261110_ES: INWARD -> away, OUTWARD -> mid-plane" if inverted else
             "MIXED (facing label does not determine the normal direction)")
    verdict(f"3.{scen}(-r) facing label determines the normal direction consistently", same_as_11c or inverted,
            state)


# ---------------------------------------------------------------------------
# B: -r versus 20261110_ES
# ---------------------------------------------------------------------------
def compare_packages(scen, rev, base):
    cat_r, mod_r, rows_r, meta_r = rev
    cat_b, mod_b, rows_b, meta_b = base
    m = mod_b.merge(mod_r, on=KEYS, how="outer", suffixes=("_es", "_r"), indicator=True)
    unmatched = int((m._merge != "both").sum())
    m = m[m._merge == "both"].copy()
    dx = (m.x_origin_mm_es - m.x_origin_mm_r).abs().max()
    dy = (m.y_origin_mm_es - m.y_origin_mm_r).abs().max()
    verdict(f"B.{scen} same (disk,row,mod) keys; x_origin, y_origin identical per key",
            unmatched == 0 and dx == 0 and dy == 0,
            f"{len(m)} matched, unmatched={unmatched}, max|dx|={dx}, max|dy|={dy} (exact compare)")

    # type mapping table and its meaning in the catalogue
    spec_b = cat_b.set_index("type_id")
    spec_r = cat_r.set_index("type_id")
    mapping = m.groupby(["type_id_es", "type_id_r"]).size()
    say(f"  {scen} type mapping 20261110_ES -> -r (count): " +
        ", ".join(f"{a}->{b} {n}" for (a, b), n in mapping.items()))
    same_cols = [c for c in v11c.CATALOG_HEADER if c not in ("type_id", "facing", "chirality")]
    map_bad = []
    for (a, b) in mapping.index:
        sa, sb = spec_b.loc[a], spec_r.loc[b]
        flips = sa.facing != sb.facing and sa.chirality != sb.chirality
        dims_same = all(np.isclose(sa[c], sb[c], atol=TOL) for c in same_cols)
        if not (flips and dims_same):
            map_bad.append((a, b))
        say(f"    {a} ({sa.facing}, {sa.chirality}) -> {b} ({sb.facing}, {sb.chirality}); "
            f"rsu_count {sa.rsu_count}->{sb.rsu_count}, width {sa.module_height_mm}->{sb.module_height_mm}, "
            f"all other catalogue columns equal: {dims_same}")
    one_to_one = mapping.index.get_level_values(0).is_unique
    verdict(f"B.{scen} each type maps to one type with facing AND chirality flipped, "
            "rsu_count/width/all dimensions kept", not map_bad and one_to_one,
            f"{len(mapping)} mappings, bad={map_bad}, one-to-one={one_to_one}")

    # z changes per old facing, expressed along the OLD normal n_es
    m["facing_es"] = m.type_id_es.map(spec_b.facing)
    m["facing_r"] = m.type_id_r.map(spec_r.facing)
    m["n_es"] = np.sign(m.z_sensor_mm_es - m.z_baseplate_mm_es)
    m["n_r"] = np.sign(m.z_sensor_mm_r - m.z_baseplate_mm_r)
    m["dzb"] = ((m.z_baseplate_mm_r - m.z_baseplate_mm_es) * m.n_es).round(4)
    m["dzs"] = ((m.z_sensor_mm_r - m.z_sensor_mm_es) * m.n_es).round(4)
    say(f"  {scen} z changes (-r minus ES) along the OLD normal n_es (+ = toward where the old sensor faced):")
    z_ok = True
    for f in ("INWARD", "OUTWARD"):
        s = m[m.facing_es == f]
        say(f"    old {f:7s} ({len(s)}): normal reversed {int((s.n_r == -s.n_es).sum())}/{len(s)}; "
            f"dz_baseplate {s.dzb.value_counts().to_dict()}, dz_sensor {s.dzs.value_counts().to_dict()}")
        z_ok &= bool((s.n_r == -s.n_es).all()) and s.dzb.nunique() == 1 and s.dzs.nunique() == 1
    verdict(f"B.{scen} every module's normal reversed; one dz_baseplate and one dz_sensor value per old facing",
            z_ok)

    # rows.csv byte-identical and parsed-identical
    byte_same = all(filecmp.cmp(REV / scen / f"{d}_rows.csv", BASE / scen / f"{d}_rows.csv", shallow=False)
                    for d in DISKS_NEW)
    verdict(f"B.{scen} <disk>_rows.csv byte-identical to 20261110_ES", byte_same)
    geo_same = filecmp.cmp(REV / scen / "disk_geometry_used.csv", BASE / scen / "disk_geometry_used.csv",
                           shallow=False)
    verdict(f"B.{scen} disk_geometry_used.csv byte-identical to 20261110_ES", geo_same)

    # catalogue as a set of rows (order differs)
    set_r = set(map(tuple, pd.read_csv(REV / scen / "catalog.csv", dtype=str).values))
    set_b = set(map(tuple, pd.read_csv(BASE / scen / "catalog.csv", dtype=str).values))
    order_same = list(cat_r.type_id) == list(cat_b.type_id)
    verdict(f"B.{scen} catalog.csv identical as a set of rows", set_r == set_b,
            f"{len(set_r)} rows; only in -r={len(set_r - set_b)}, only in ES={len(set_b - set_r)}; "
            f"same row order={order_same}")

    # metadata: keys whose values differ
    diffs = {}
    for d in DISKS_NEW:
        ka, kb = meta_r[d], meta_b[d]
        keys = sorted(set(ka) | set(kb))
        changed = [k for k in keys if ka.get(k) != kb.get(k)]
        if changed:
            diffs[d] = {k: (kb.get(k), ka.get(k)) for k in changed}
    say(f"  {scen} metadata keys differing (ES -> -r): {diffs if diffs else 'none'}")
    verdict(f"B.{scen} metadata differences listed (informational)", True,
            f"{sum(len(v) for v in diffs.values())} differing key(s) on {len(diffs)} disk(s)")
    return m


# ---------------------------------------------------------------------------
# C: physical interpretation
# ---------------------------------------------------------------------------
def interpret(scen, m, rows, meta):
    """m = merged ES/-r table from compare_packages."""
    rows_f = rows[["disk_id", "row_index", "facet_z_mm"]]
    m = m.merge(rows_f, on=["disk_id", "row_index"])
    m["zc"] = m.disk_id.map(lambda i: float(meta[DISKS_NEW[i]]["z_center_mm"]))
    # every row's facet plane lies on one of the two outer faces of the disk (z_center +- 3)
    m["face"] = np.sign(m.facet_z_mm - m.zc)

    # 1. mounting plane: does every module stay on the same row facet (same disk face)?
    for tag in ("es", "r"):
        n = m[f"n_{tag}"]
        m[f"u_facet_{tag}"] = ((m[f"z_baseplate_mm_{tag}"] - m.facet_z_mm) * n).round(4)
        m[f"sensor_from_facet_{tag}"] = ((m[f"z_sensor_mm_{tag}"] - m.facet_z_mm) * m.face).round(4)
    say(f"  {scen}: every module keeps its (disk,row), hence the same row facet_z and the same disk face")
    for f in ("INWARD", "OUTWARD"):
        s = m[m.facing_es == f]
        say(f"    old {f:7s}: (z_baseplate - facet_z)*n  ES {s.u_facet_es.value_counts().to_dict()}  "
            f"-r {s.u_facet_r.value_counts().to_dict()}")
        say(f"               sensor plane height above the disk face, (z_sensor - facet_z)*sign(facet_z - z_center) "
            f"[+ = outside the disk]:  ES {s.sensor_from_facet_es.value_counts().to_dict()}  "
            f"-r {s.sensor_from_facet_r.value_counts().to_dict()}")
        move = ((m.loc[s.index, "z_sensor_mm_r"] - m.loc[s.index, "z_sensor_mm_es"]) * s.face).round(4)
        say(f"               sensor-plane move outward from the disk (-r minus ES): {move.value_counts().to_dict()}")

    # 2. the set of sensor planes per disk face is unchanged, only the occupancy changes
    say(f"  {scen}: sensor planes per disk face, count of modules per (z_sensor - facet_z)*face value:")
    say("    disk  face   ES {plane: n}                     -r {plane: n}")
    for i, d in enumerate(DISKS_NEW):
        for face in (-1, 1):
            s = m[(m.disk_id == i) & (m.face == face)]
            say(f"    {d:4s} {'+' if face > 0 else '-'}{3:d}mm  {str(s.sensor_from_facet_es.value_counts().sort_index().to_dict()):33s}"
                f" {s.sensor_from_facet_r.value_counts().sort_index().to_dict()}")

    # 3. inward/outward counts per disk
    say(f"  {scen}: INWARD/OUTWARD counts per disk (ES -> -r)")
    for i, d in enumerate(DISKS_NEW):
        s = m[m.disk_id == i]
        say(f"    {d:4s} INWARD {int((s.facing_es == 'INWARD').sum()):4d} -> {int((s.facing_r == 'INWARD').sum()):4d}, "
            f"OUTWARD {int((s.facing_es == 'OUTWARD').sum()):4d} -> {int((s.facing_r == 'OUTWARD').sum()):4d}")
    say(f"    total INWARD {int((m.facing_es == 'INWARD').sum())} -> {int((m.facing_r == 'INWARD').sum())}, "
        f"OUTWARD {int((m.facing_es == 'OUTWARD').sum())} -> {int((m.facing_r == 'OUTWARD').sum())}")


def footprint_identity(scen, rev, base):
    """Compare the in-plane (x, y) boxes of the modelled components per key, ES vs -r."""
    boxes = {}
    for tag, (cat, mods, _, _) in (("es", base), ("r", rev)):
        fpcs, films = v11c.build_boxes(cat, mods, "new")
        boxes[tag] = {(b["disk"], b["row"], b["mod"], b["name"]): b for b in fpcs + films + ancasic_boxes(cat, mods)}
    max_dxy, max_dz_mid = 0.0, 0.0
    for key, b in boxes["es"].items():
        o = boxes["r"][key]
        max_dxy = max(max_dxy, *(abs(b[a][k] - o[a][k]) for a in "xy" for k in (0, 1)))
    verdict(f"C.{scen} in-plane x/y box of every modelled component (LEC/REC film, both bridge FPCs, AncASIC) "
            "identical ES vs -r per key", max_dxy < 1e-9,
            f"{len(boxes['es'])} boxes, max |d(x,y edge)| = {max_dxy:.2e} mm")


# ---------------------------------------------------------------------------
# D: all-component pair audit
# ---------------------------------------------------------------------------
def ancasic_boxes(catalog, modules):
    """AncASIC (glue + chip as one box) in detector coordinates.

    Same placement transform as v11c.build_boxes (copied); the local position follows
    SiEndcapModuleTracker_geo.cpp: x = left-FPC centre moved toward the LEC so that the
    chip's outer edge is 5 mm from the FPC's outer edge; y = 1 mm below the left FPC top.
    z: on the front-side FPC (Kapton+Al for outward, Kapton only for inward modules).
    """
    spec_by_type = {r.type_id: r for r in catalog.itertuples()}
    out = []
    for src in modules.itertuples():
        spec = spec_by_type[src.type_id]
        width = spec.module_height_mm
        chain = spec.rsu_count * v11c.RSU_LENGTH
        handedness = "left" if spec.chirality in ("RIGHT", "NEGATIVE") else "right"
        lec_after_rsu = handedness == "right"
        end_span = spec.BREC_mm if handedness == "right" else spec.BLEC_mm
        sensor_x = -spec.module_length_mm / 2.0 + end_span + chain / 2.0
        boundary_local = sensor_x + (chain / 2.0 if handedness == "right" else -chain / 2.0)
        epic_x_origin = -src.x_origin_mm
        module_x = epic_x_origin - (abs(boundary_local) if epic_x_origin > 0 else -abs(boundary_local))
        local_x_sign = (epic_x_origin - module_x) / boundary_local
        n = 1.0 if src.z_sensor_mm > src.z_baseplate_mm else -1.0
        local_y_sign = local_x_sign * n

        # left (LEC-side) bridge FPC box in module-local coordinates (as in 11c)
        bx = min(v11c.LEFT_FPC_X, max(0.0, spec.BLEC_mm - spec.LEC_mm - v11c.FPC_GAP))
        fpc_lx = sensor_x + ((chain / 2 + spec.LEC_mm + v11c.FPC_GAP + bx / 2) if lec_after_rsu
                             else (-chain / 2 - spec.LEC_mm - v11c.FPC_GAP - bx / 2))
        by, fpc_ly = v11c.fpc_y_geometry(width, v11c.LEFT_FPC_Y, v11c.LEFT_FPC_TOP_OFFSET)
        toward_lec = -1.0 if lec_after_rsu else 1.0
        lx = fpc_lx + toward_lec * (-bx / 2 + ANCASIC_OUTER_EDGE_CLEARANCE + ANCASIC_X / 2)
        ly = fpc_ly + by / 2 - ANCASIC_TOP_CLEARANCE - ANCASIC_Y / 2

        u = v11c.stack_u(spec.facing, "new")
        u_lo = u["kapton"][1] if spec.facing == "INWARD" else u["aluminum"][1]
        zs = [src.z_baseplate_mm + n * v for v in (u_lo, u_lo + ANCASIC_GLUE + ANCASIC_CHIP)]
        out.append(dict(disk=src.disk, row=src.row_index, mod=src.mod_index, type_id=src.type_id,
                        facing=spec.facing, n=n, z_ref=src.z_baseplate_mm, y0=src.y_origin_mm, width=width,
                        name="ancasic", x=v11c.interval(module_x + local_x_sign * lx, ANCASIC_X),
                        y=v11c.interval(src.y_origin_mm + local_y_sign * ly, ANCASIC_Y), z=(min(zs), max(zs))))
    return out


def body_boxes(catalog, modules):
    """Module body boxes (coarse extension of the 11c model).

    body: baseplate bottom .. sensor top over the full module footprint
          (module_length x module_height); the film/sensor are smaller in reality.
    epoxy_line_low/high (OUTWARD only): the external epoxy under the baseplate is two
          2.5 mm edge glue lines over the full module length (SiEndcapModuleTracker_geo.cpp,
          rsu_external_epoxy_pattern), u = 0..0.080.  For INWARD modules the edge lines
          lie inside the body z range already.
    """
    spec_by_type = {r.type_id: r for r in catalog.itertuples()}
    glue = v11c.EPOXY_GLUE_LINE_WIDTH
    out = []
    for src in modules.itertuples():
        spec = spec_by_type[src.type_id]
        chain = spec.rsu_count * v11c.RSU_LENGTH
        handedness = "left" if spec.chirality in ("RIGHT", "NEGATIVE") else "right"
        end_span = spec.BREC_mm if handedness == "right" else spec.BLEC_mm
        sensor_x = -spec.module_length_mm / 2.0 + end_span + chain / 2.0
        boundary_local = sensor_x + (chain / 2.0 if handedness == "right" else -chain / 2.0)
        epic_x_origin = -src.x_origin_mm
        module_x = epic_x_origin - (abs(boundary_local) if epic_x_origin > 0 else -abs(boundary_local))
        n = 1.0 if src.z_sensor_mm > src.z_baseplate_mm else -1.0
        u = v11c.stack_u(spec.facing, "new")
        width = spec.module_height_mm

        def zint(u_lo, u_hi):
            zs = [src.z_baseplate_mm + n * v for v in (u_lo, u_hi)]
            return min(zs), max(zs)

        common = dict(disk=src.disk, row=src.row_index, mod=src.mod_index, type_id=src.type_id,
                      facing=spec.facing, x=v11c.interval(module_x, spec.module_length_mm))
        out.append(dict(common, name="body", y=v11c.interval(src.y_origin_mm, width),
                        z=zint(u["baseplate"][0], u["sensor"][1])))
        if spec.facing == "OUTWARD":
            for edge, label in ((-1, "low"), (1, "high")):
                y_c = src.y_origin_mm + edge * (width / 2.0 - glue / 2.0)
                out.append(dict(common, name=f"epoxy_line_{label}", y=v11c.interval(y_c, glue),
                                z=zint(0.0, u["baseplate"][0])))
    return out


def pair_audit(boxes):
    """All intersecting box pairs between different modules on the same disk (vectorised).

    Returns a list of (box_a, box_b, (ox, oy, oz)) with a before b in list order.
    """
    hits = []
    by_disk = {}
    for b in boxes:
        by_disk.setdefault(b["disk"], []).append(b)
    for disk, bl in by_disk.items():
        lo = {a: np.array([b[a][0] for b in bl]) for a in "xyz"}
        hi = {a: np.array([b[a][1] for b in bl]) for a in "xyz"}
        mod_key = np.array([b["row"] * 1000 + b["mod"] for b in bl])
        ov = {a: np.minimum.outer(hi[a], hi[a]) - np.maximum.outer(lo[a], lo[a]) for a in "xyz"}
        mask = (ov["x"] > 1e-6) & (ov["y"] > 1e-6) & (ov["z"] > 1e-6)
        mask &= mod_key[:, None] != mod_key[None, :]
        mask = np.triu(mask, 1)
        for i, j in zip(*np.nonzero(mask)):
            hits.append((bl[i], bl[j], (ov["x"][i, j], ov["y"][i, j], ov["z"][i, j])))
    return hits


def component_name(b):
    return b["name"].replace("_kapton", "_kapton").replace("left_", "L").replace("right_", "R")


def summarise_hits(label, hits, nboxes, show=12):
    say(f"  {label}: {nboxes} boxes, {len(hits)} intersecting pairs")
    counts = {}
    for a, b, _ in hits:
        names = tuple(sorted((a["name"], b["name"])))
        fac = tuple(sorted((a["facing"], b["facing"])))
        counts[(names, fac)] = counts.get((names, fac), 0) + 1
    for (names, fac), c in sorted(counts.items()):
        say(f"    {names[0]} x {names[1]}  [{fac[0]}/{fac[1]}]: {c}")
    for a, b, d in hits[:show]:
        say(f"    e.g. {a['disk']} {a['row']}/{a['mod']} {a['type_id']} {a['name']} vs {b['row']}/{b['mod']} "
            f"{b['type_id']} {b['name']}: overlap xyz {d[0]:.3f},{d[1]:.3f},{d[2]:.3f}")
    return {hit_key(a, b) for a, b, _ in hits}


def hit_key(a, b):
    return tuple(sorted(((a["disk"], a["row"], a["mod"], a["name"]), (b["disk"], b["row"], b["mod"], b["name"]))))


def audit_scenario(scen, rev, base):
    results = {}
    for tag, (cat, mods, _, _) in (("20261110_ES", base), ("-r", rev)):
        fpcs, films = v11c.build_boxes(cat, mods, "new")
        comps = fpcs + films + ancasic_boxes(cat, mods)
        hits = pair_audit(comps)
        results[tag] = summarise_hits(f"{scen} {tag} components (FPC Kapton/Al, LEC/REC film, AncASIC)",
                                      hits, len(comps))
    new = results["-r"] - results["20261110_ES"]
    gone = results["20261110_ES"] - results["-r"]
    verdict(f"D.{scen} -r: no component-component intersection between different modules "
            "(any facing combination)", not results["-r"],
            f"-r {len(results['-r'])} pairs, ES {len(results['20261110_ES'])}; new in -r {len(new)}, "
            f"gone in -r {len(gone)}")

    # coarse extension: module body slabs vs everything (informational, ES as control)
    body = {}
    for tag, (cat, mods, _, _) in (("20261110_ES", base), ("-r", rev)):
        fpcs, films = v11c.build_boxes(cat, mods, "new")
        boxes = fpcs + films + ancasic_boxes(cat, mods) + body_boxes(cat, mods)
        body_names = {"body", "epoxy_line_low", "epoxy_line_high"}
        hits = [h for h in pair_audit(boxes) if body_names & {h[0]["name"], h[1]["name"]}]
        body[tag] = summarise_hits(f"{scen} {tag} module body (full-footprint slab + outward epoxy lines) "
                                   "vs body/components", hits, len(boxes), show=6)
    say(f"    body pairs new in -r: {len(body['-r'] - body['20261110_ES'])}, "
        f"gone in -r: {len(body['20261110_ES'] - body['-r'])}")
    verdict(f"D.{scen} (coarse, informational) module body/epoxy-line boxes: -r has no more pairs than "
            "the ROOT-overlap-clean 20261110_ES control", len(body["-r"]) <= len(body["20261110_ES"]),
            f"-r {len(body['-r'])}, ES {len(body['20261110_ES'])}")


# ---------------------------------------------------------------------------
def main():
    say("Step 11f validation of the 20261110 '-r' SVT endcap tiling package")
    say(f"-r: {REV.relative_to(ROOT)}  reference: {BASE.relative_to(ROOT)}")

    section("Check 0: staging provenance")
    for scen in SCENARIOS:
        check_staging(scen)
    for scen in SCENARIOS:
        log = SOURCE / scen / "flip_facing_build.log"
        flipped = [l for l in log.read_text().splitlines() if l.strip().endswith("flipped")]
        say(f"  {scen} flip_facing_build.log: {len(flipped)} disk lines ending in 'flipped'")

    section("A / 11c check 1: file completeness and consistency (-r)")
    rev, base = {}, {}
    for scen in SCENARIOS:
        rev[scen] = v11c.check_files(f"{scen}(-r)", REV / scen)
    if any(v is None for v in rev.values()):
        say("cannot continue without complete files")
        return finish()
    for scen in SCENARIOS:
        base[scen] = v11c.load_scenario(BASE / scen, DISKS_NEW)
    say(f"  module counts -r: rsu_opt {len(rev['rsu_opt'][1])}, rsu6 {len(rev['rsu6'][1])}; "
        f"20261110_ES: rsu_opt {len(base['rsu_opt'][1])}, rsu6 {len(base['rsu6'][1])}")

    section("A / 11c check 3: placement z with the Step 11b stack (-r)")
    for scen in SCENARIOS:
        catalog, modules, rows, meta = rev[scen]
        placed = v11c.check_placement_z(f"{scen}(-r)", catalog, modules, rows, meta)
        check_orientation(scen, placed)

    section("A / 11c check 5: rows.csv, BLOCKED rule, vs reconstructed 20261001 lattice (-r)")
    old_rsu_opt = v11c.load_scenario(OLD / "rsu_opt", v11c.DISKS_OLD)
    v11c.check_rows(rev["rsu_opt"][2], rev["rsu6"][2], rev["rsu_opt"][3], old_rsu_opt[1])

    section("A / 11c check 6: bridge-FPC vs neighbouring LEC/REC film pairs (-r, new stack)")
    say("  note: 11c check 6 (and the Step 8d audit) already tested every FPC against every other")
    say("  module's end films on the same disk, with no facing filter; Section D widens the component set.")
    for scen in SCENARIOS:
        pairs = v11c.report_pairs(f"-r {scen}", rev[scen][0], rev[scen][1], "new")
        verdict(f"6.{scen}(-r) no bridge-FPC/end-film intersections", not pairs, f"{len(pairs)} pairs")

    section("A / 11c check 7: inward bridge FPC vs carbon (-r)")
    for scen in SCENARIOS:
        catalog, modules, rows, _ = rev[scen]
        v11c.check_inward_fpc(f"{scen}(-r)", catalog, modules, rows)

    section("B: -r versus 20261110_ES (same scenario)")
    merged = {}
    for scen in SCENARIOS:
        merged[scen] = compare_packages(scen, rev[scen], base[scen])

    section("C: physical interpretation")
    say("  Geometry: each row's facet_z (rows.csv) is on one of the two outer faces of the 6 mm")
    say("  corrugated disk (facet_z - z_center = +-3 mm).  INWARD module: z_baseplate = facet, sensor")
    say("  toward the disk mid-plane; OUTWARD: z_baseplate = facet + 0.230 along n, sensor away from it.")
    for scen in SCENARIOS:
        interpret(scen, merged[scen], rev[scen][2], rev[scen][3])
        footprint_identity(scen, rev[scen], base[scen])

    section("D: all-component pair audit, any facing combination")
    say("  Component model: 11c build_boxes (left/right bridge FPC Kapton and Al, LEC and REC end films,")
    say("  Step 11b z stack) + AncASIC (glue+chip, x/y from the Step 11b builder relative to the left FPC).")
    say("  Not covered: the builder's upright-electronics y flip for rows at y <= 0 (Step 8j) and the")
    say("  RSU-referenced FPC top edge (Step 8k) -- the 11c model references the module edge instead;")
    say("  RSU silicon tile pattern, the corrugated carbon itself (beyond 11c check 7), cables/services.")
    say("  Boxes are axis-aligned; touching faces are not hits.")
    say("  Coarse extension (second audit per scenario): module body = baseplate..sensor top as one slab over")
    say("  the full module footprint, plus the OUTWARD external epoxy as the builder's two 2.5 mm edge lines.")
    say("  Rejected first version (2026-11-11): OUTWARD epoxy as a full-footprint layer gave 1677 (rsu_opt) /")
    say("  1664 (rsu6) pairs in BOTH ES and -r, all INWARD back-side Al (0.030 mm z overlap) vs a same-row")
    say("  OUTWARD neighbour's epoxy -- an artefact, since the builder places that epoxy as edge lines only.")
    for scen in SCENARIOS:
        audit_scenario(scen, rev[scen][1:2] and rev[scen], base[scen])

    return finish()


def finish():
    section("Summary")
    failed = [n for n, ok in v11c.RESULTS if not ok]
    say(f"{len(v11c.RESULTS) - len(failed)}/{len(v11c.RESULTS)} checks passed")
    for n in failed:
        say(f"  FAILED: {n}")
    say(f"OVERALL: {'PASS' if not failed else 'FAIL'}")
    REPORT.write_text("\n".join(v11c.LINES) + "\n")
    print(f"report written to {REPORT}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
