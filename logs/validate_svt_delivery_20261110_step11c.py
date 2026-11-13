#!/usr/bin/env python3
"""Step 11c: source-level validation of the 20261110 SVT endcap tiling delivery.

Reads only delivered CSV/metadata files (read-only) and writes a text report.

    module load conda; conda activate tracking
    python proj_svt_disk_tiling/logs/validate_svt_delivery_20261110_step11c.py

Checks (see overnight_plan_20261111.md, Step 11c):
  1. file completeness, headers, disk ids, unique keys, catalogue coverage
  2. chirality relabelling NEGATIVE/POSITIVE <-> RIGHT/LEFT per type_id
  3. placement z with the NEW module stack (Cu inside the 50 um sensor)
  4. old (20261001) vs new (20261110) module placements
  5. delivered rows.csv vs the reconstructed 20261001 lattice table
  6. bridge-FPC / neighbouring end-film (LEC/REC) pair audit (Step 8d logic)
  7. inward bridge FPC vs carbon: z intervals and y footprint

Conventions (same as SiEndcapModuleTracker_geo.cpp and the Step 8d audit):
  - Delivery is in the engineer frame; x_EPIC = -x_engineer, which also swaps
    the placed handedness (RIGHT/NEGATIVE -> left-handed in EPIC).
  - "Module normal" n = sign(z_sensor - z_baseplate), i.e. from baseplate to sensor.
  - u = signed distance along n measured from the CSV z_baseplate plane.
All lengths are mm unless the name says um.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TILING = ROOT / "compact/tracking/silicon_disks_tiling"
NEW = TILING / "20261110_ES"
OLD = TILING / "20261001_ES"
OLD_ROWS_TABLE = OLD / "SVT_endcap_corrugation_rows_33_36.csv"
REPORT = Path(__file__).with_suffix(".txt")

DISKS_NEW = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3", "HD4"]
DISKS_OLD = ["ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3b", "HD4"]

CATALOG_HEADER = ["type_id", "module_height_mm", "module_length_mm", "rsu_count", "facing",
                  "chirality", "active_height_mm", "active_length_mm", "sensor_height_mm",
                  "sensor_length_mm", "BLEC_mm", "BREC_mm", "LEC_mm", "REC_mm", "PER_mm"]
MODULES_HEADER = ["disk_id", "row_index", "mod_index", "type_id", "x_origin_mm", "y_origin_mm",
                  "z_baseplate_mm", "z_sensor_mm"]
ROWS_HEADER = ["disk_id", "row_index", "row_type", "x_outer_mm", "row_y_mm", "facet_z_mm",
               "half_pitch_mm"]
GEOMETRY_HEADER = ["label", "z_center_m", "outer_radius_m"]

TOL = 1.0e-4  # CSV values carry 4 decimals

# ---------------------------------------------------------------------------
# Module stack (thicknesses in mm).  NEW = what the code will use after Step 11b.
# ---------------------------------------------------------------------------
EXTERNAL_EPOXY = 0.080   # outward: under the baseplate on the carbon; inward: edge lines
BASEPLATE = 0.150        # carbon-fibre baseplate
FILM = 0.060             # film between baseplate and sensor
SENSOR_INACTIVE = 0.0335
SENSOR_ACTIVE = 0.014
SENSOR_CU = 0.0025       # Cu outer face = z_sensor plane
SENSOR = SENSOR_INACTIVE + SENSOR_ACTIVE + SENSOR_CU   # 0.050
FPC_KAPTON = 0.080
FPC_ALUMINUM = 0.030
CARBON_FLAT = 0.150      # corrugated carbon sheet thickness (Step 8e)
OUTWARD_FACET_OFFSET = 0.230  # delivered z_baseplate - facet_z along n for outward modules

# Old Step 8d model (20261001 delivery): CSV z_baseplate == facet, code-applied offsets.
OLD_INWARD_Z_CLEARANCE = 0.030
OLD_OPPOSITE_FACING_Z_OFFSET = 0.230

# Bridge FPC and end-film geometry (copied from audit_svt_fpc_pair_overlaps_step8d.py)
RSU_LENGTH = 21.666
EPOXY_GLUE_LINE_WIDTH = 2.5
FPC_GAP = 0.5
LEFT_FPC_X, LEFT_FPC_Y, LEFT_FPC_TOP_OFFSET = 10.0, 24.5, -7.5
RIGHT_FPC_X, RIGHT_FPC_Y, RIGHT_FPC_TOP_OFFSET = 4.0, 25.78, -6.22
FILM_Y_WIDTH = 19.564

# Straight (zero-thickness profile, 5 mm bends) flat widths from the 2026-11-05 review
STRAIGHT_FLAT_WIDTH = {16.5: 6.36, 18.0: 7.86}   # keyed by half pitch: B, A

# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
LINES = []
RESULTS = []


def say(text=""):
    print(text)
    LINES.append(text)


def verdict(name, ok, detail=""):
    RESULTS.append((name, ok))
    say(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))


def section(title):
    say()
    say("=" * 78)
    say(title)
    say("=" * 78)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def read_metadata(path):
    meta = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            meta[key.strip()] = value.split("#")[0].strip()
    return meta


def load_scenario(directory, disk_names):
    """Return catalog, modules (with column 'disk'), rows (or None), metadata dict."""
    catalog = pd.read_csv(directory / "catalog.csv")
    modules, rows, meta = [], [], {}
    for disk_id, disk in enumerate(disk_names):
        frame = pd.read_csv(directory / f"{disk}_modules.csv")
        frame["disk"] = disk
        frame["file_disk_id"] = disk_id
        modules.append(frame)
        rows_path = directory / f"{disk}_rows.csv"
        if rows_path.exists():
            r = pd.read_csv(rows_path)
            r["disk"] = disk
            rows.append(r)
        meta[disk] = read_metadata(directory / f"{disk}_metadata.txt")
    modules = pd.concat(modules, ignore_index=True)
    rows = pd.concat(rows, ignore_index=True) if rows else None
    return catalog, modules, rows, meta


# ---------------------------------------------------------------------------
# Check 1: completeness
# ---------------------------------------------------------------------------
def check_files(name, directory):
    ok = True
    problems = []
    expected = ["catalog.csv", "disk_geometry_used.csv"]
    for disk in DISKS_NEW:
        expected += [f"{disk}_modules.csv", f"{disk}_rows.csv", f"{disk}_metadata.txt"]
    missing = [f for f in expected if not (directory / f).exists()]
    extra = sorted(p.name for p in directory.iterdir() if p.name not in expected)
    if missing:
        ok = False
        problems.append(f"missing {missing}")
    if extra:
        problems.append(f"extra files {extra}")

    def header(path):
        return path.read_text().splitlines()[0].strip().split(",")

    if header(directory / "catalog.csv") != CATALOG_HEADER:
        ok = False
        problems.append("catalog header")
    if header(directory / "disk_geometry_used.csv") != GEOMETRY_HEADER:
        ok = False
        problems.append("disk_geometry_used header")
    for disk in DISKS_NEW:
        if header(directory / f"{disk}_modules.csv") != MODULES_HEADER:
            ok = False
            problems.append(f"{disk}_modules header")
        if header(directory / f"{disk}_rows.csv") != ROWS_HEADER:
            ok = False
            problems.append(f"{disk}_rows header")
    verdict(f"1.{name} files present and headers as expected", ok,
            "; ".join(problems) if problems else f"{len(expected)} files")
    if not ok:
        return None

    catalog, modules, rows, meta = load_scenario(directory, DISKS_NEW)

    # disk_id per file (modules, rows, metadata) and total_modules
    bad = modules[modules.disk_id != modules.file_disk_id]
    rows_bad = rows[rows.disk_id != rows.disk.map({d: i for i, d in enumerate(DISKS_NEW)})]
    meta_bad = [d for i, d in enumerate(DISKS_NEW) if int(meta[d]["disk_id"]) != i]
    count_bad = [d for d in DISKS_NEW
                 if int(meta[d]["total_modules"]) != (modules.disk == d).sum()]
    verdict(f"1.{name} disk_id matches file name (modules, rows, metadata) and metadata total_modules",
            bad.empty and rows_bad.empty and not meta_bad and not count_bad,
            f"module rows bad={len(bad)}, rows bad={len(rows_bad)}, meta bad={meta_bad}, "
            f"count mismatches={count_bad}")

    dup = modules.duplicated(["disk_id", "row_index", "mod_index"]).sum()
    dup_rows = rows.duplicated(["disk_id", "row_index"]).sum()
    verdict(f"1.{name} unique (disk,row,mod) and (disk,row) keys", dup == 0 and dup_rows == 0,
            f"{len(modules)} modules, duplicates={dup}; {len(rows)} rows, duplicates={dup_rows}")

    unknown = sorted(set(modules.type_id) - set(catalog.type_id))
    unused = sorted(set(catalog.type_id) - set(modules.type_id))
    verdict(f"1.{name} every module type in catalogue (catalogue type_id unique)",
            not unknown and catalog.type_id.is_unique,
            f"{len(catalog)} types, unknown={unknown}, unused catalogue types={unused}")

    # every module row exists in rows.csv
    keys = set(zip(rows.disk_id, rows.row_index))
    no_row = [k for k in zip(modules.disk_id, modules.row_index) if k not in keys]
    verdict(f"1.{name} every module's (disk,row) present in rows.csv", not no_row,
            f"missing={len(no_row)}")

    # disk_geometry_used.csv vs metadata
    geometry = pd.read_csv(directory / "disk_geometry_used.csv")
    geo_bad = []
    for disk in DISKS_NEW:
        g = geometry[geometry.label == disk]
        if len(g) != 1:
            geo_bad.append(disk)
            continue
        if (abs(g.z_center_m.iloc[0] * 1000 - float(meta[disk]["z_center_mm"])) > TOL
                or abs(g.outer_radius_m.iloc[0] * 1000 - float(meta[disk]["outer_radius_mm"])) > TOL):
            geo_bad.append(disk)
    verdict(f"1.{name} disk_geometry_used.csv agrees with metadata z_center/outer_radius",
            not geo_bad, f"bad={geo_bad}")
    return catalog, modules, rows, meta


# ---------------------------------------------------------------------------
# Check 2: chirality relabelling
# ---------------------------------------------------------------------------
def check_chirality(name, new_catalog, old_catalog):
    expected = {"NEGATIVE": "RIGHT", "POSITIVE": "LEFT"}
    merged = new_catalog.merge(old_catalog, on="type_id", how="outer",
                               suffixes=("_new", "_old"), indicator=True)
    only_one = merged[merged._merge != "both"]
    both = merged[merged._merge == "both"]
    label_bad = both[both.chirality_new.map(expected) != both.chirality_old]
    other_cols = [c for c in CATALOG_HEADER if c not in ("type_id", "chirality")]
    diff_cols = []
    for col in other_cols:
        a, b = both[col + "_new"], both[col + "_old"]
        same = np.isclose(a, b, atol=TOL) if pd.api.types.is_numeric_dtype(a) else (a == b)
        if not same.all():
            diff_cols.append((col, list(both.type_id[~same])))
    ok = only_one.empty and label_bad.empty and not diff_cols
    verdict(f"2.{name} chirality NEGATIVE<->RIGHT, POSITIVE<->LEFT; facing and dimensions unchanged", ok,
            f"{len(both)} types matched, unmatched={list(only_one.type_id)}, "
            f"label mismatches={list(label_bad.type_id)}, other column diffs={diff_cols}")
    counts = both.groupby(["chirality_new", "chirality_old"]).size().to_dict()
    say(f"    label pairs (new, old): count = {counts}")


# ---------------------------------------------------------------------------
# Check 3: placement z with the new stack
# ---------------------------------------------------------------------------
def stack_u(facing, model="new"):
    """Signed u intervals (along n, from the CSV z_baseplate plane) of the layers.

    new OUTWARD: [epoxy | baseplate | film | sensor] stacked from u=0 (epoxy bottom).
      Bridge FPC: Kapton then Al on the sensor side of the baseplate (unchanged).
    new INWARD:  z_baseplate = carbon facet; the 80 um epoxy edge lines sit between
      the carbon and the sensor-side face of the baseplate, so the baseplate is at
      u = -0.230..-0.080, film+sensor from -0.080 up to +0.030.
      Bridge FPC: Kapton stays on the sensor side (-0.080..0); Al moves to the back
      side of the baseplate (-0.260..-0.230).
    old: Step 8d model for the 20261001 CSV (z_baseplate == facet) including the
      code-applied translations (+0.260 outward, -0.030 inward).
    """
    if facing == "OUTWARD":
        base_lo = EXTERNAL_EPOXY
        shift = OLD_OPPOSITE_FACING_Z_OFFSET + OLD_INWARD_Z_CLEARANCE if model == "old" else 0.0
    else:
        base_lo = -EXTERNAL_EPOXY - BASEPLATE
        shift = -OLD_INWARD_Z_CLEARANCE if model == "old" else 0.0
    base_hi = base_lo + BASEPLATE
    layers = {
        "baseplate": (base_lo, base_hi),
        "film": (base_hi, base_hi + FILM),
        "sensor": (base_hi + FILM, base_hi + FILM + SENSOR),
        "kapton": (base_hi, base_hi + FPC_KAPTON),
    }
    if facing == "INWARD" and model == "new":
        layers["aluminum"] = (base_lo - FPC_ALUMINUM, base_lo)
    else:
        layers["aluminum"] = (base_hi + FPC_KAPTON, base_hi + FPC_KAPTON + FPC_ALUMINUM)
    return {k: (lo + shift, hi + shift) for k, (lo, hi) in layers.items()}


def check_placement_z(name, catalog, modules, rows, meta):
    say(f"  stack: sensor = {SENSOR_INACTIVE*1e3:.1f} inactive + {SENSOR_ACTIVE*1e3:.1f} active "
        f"+ {SENSOR_CU*1e3:.1f} Cu = {SENSOR*1e3:.1f} um")
    expected = {}
    for facing in ("OUTWARD", "INWARD"):
        u = stack_u(facing)
        expected[facing] = u["sensor"][1]
        say(f"  {facing:7s} u-intervals [mm]: " + ", ".join(
            f"{k} {lo:+.4f}..{hi:+.4f}" for k, (lo, hi) in u.items()))
    say(f"  expected |z_sensor - z_baseplate|: OUTWARD {expected['OUTWARD']*1e3:.1f} um "
        f"(80+150+60+50), INWARD {expected['INWARD']*1e3:.1f} um (60+50-80)")

    m = modules.merge(catalog[["type_id", "facing"]], on="type_id")
    m = m.merge(rows[["disk_id", "row_index", "row_y_mm", "facet_z_mm"]], on=["disk_id", "row_index"])
    m["n"] = np.sign(m.z_sensor_mm - m.z_baseplate_mm)
    m["dz"] = (m.z_sensor_mm - m.z_baseplate_mm).abs()
    m["u_facet"] = (m.z_baseplate_mm - m.facet_z_mm) * m.n
    m["z_center"] = m.disk.map(lambda d: float(meta[d]["z_center_mm"]))
    # inward modules face the channel, i.e. their normal points toward the disk mid-plane
    m["n_toward_center"] = np.sign(m.z_center - m.facet_z_mm) == m.n

    out = m[m.facing == "OUTWARD"]
    inw = m[m.facing == "INWARD"]
    say(f"  modules: {len(m)} = {len(out)} OUTWARD + {len(inw)} INWARD")

    bad = out[(out.dz - expected["OUTWARD"]).abs() > TOL]
    verdict(f"3.{name} OUTWARD |z_sensor - z_baseplate| = 0.340 mm", bad.empty,
            f"bad={len(bad)}, observed values={sorted(out.dz.round(4).unique())}")
    bad = inw[(inw.dz - expected["INWARD"]).abs() > TOL]
    verdict(f"3.{name} INWARD |z_sensor - z_baseplate| = 0.030 mm", bad.empty,
            f"bad={len(bad)}, observed values={sorted(inw.dz.round(4).unique())}")
    bad = inw[(inw.z_baseplate_mm - inw.facet_z_mm).abs() > TOL]
    verdict(f"3.{name} INWARD z_baseplate == row facet_z", bad.empty, f"bad={len(bad)}")
    bad = out[(out.u_facet - OUTWARD_FACET_OFFSET).abs() > TOL]
    verdict(f"3.{name} OUTWARD (z_baseplate - facet_z) * n = +0.230 mm", bad.empty,
            f"bad={len(bad)}, observed={sorted(out.u_facet.round(4).unique())}")
    bad = m[(m.y_origin_mm - m.row_y_mm).abs() > TOL]
    verdict(f"3.{name} module y_origin == row_y", bad.empty, f"bad={len(bad)}")
    # informational orientation check
    say(f"    orientation: INWARD normals toward disk mid-plane {inw.n_toward_center.sum()}/{len(inw)}; "
        f"OUTWARD normals away from mid-plane {(~out.n_toward_center).sum()}/{len(out)}")
    say(f"    note: OUTWARD epoxy bottom (u=0) lies {OUTWARD_FACET_OFFSET:.3f} mm off the facet plane "
        f"= {EXTERNAL_EPOXY:.3f} epoxy + {BASEPLATE:.3f} baseplate of an INWARD module on the same plane")
    return m


# ---------------------------------------------------------------------------
# Check 4: old vs new placements
# ---------------------------------------------------------------------------
def check_old_vs_new(name, new_modules, new_catalog, old_modules, expect_identical):
    keys = ["disk_id", "row_index", "mod_index"]
    facing = dict(zip(new_catalog.type_id, new_catalog.facing))
    merged = new_modules.merge(old_modules, on=keys, how="outer", suffixes=("_new", "_old"),
                               indicator=True)
    only_new = merged[merged._merge == "left_only"]
    only_old = merged[merged._merge == "right_only"]
    both = merged[merged._merge == "both"].copy()
    changed = both[(both.type_id_new != both.type_id_old)
                   | ((both.x_origin_mm_new - both.x_origin_mm_old).abs() > TOL)
                   | ((both.y_origin_mm_new - both.y_origin_mm_old).abs() > TOL)]
    say(f"  {name}: new {len(new_modules)} modules, old {len(old_modules)}; "
        f"keys only in new={len(only_new)}, only in old={len(only_old)}, "
        f"matched={len(both)}, matched with changed x/y/type={len(changed)}")

    # position-based comparison (independent of mod_index renumbering)
    def positions(frame):
        return set(zip(frame.disk_id, frame.row_index, frame.x_origin_mm.round(4),
                       frame.y_origin_mm.round(4), frame.type_id))
    pos_new, pos_old = positions(new_modules), positions(old_modules)
    removed = sorted(pos_old - pos_new)
    added = sorted(pos_new - pos_old)
    say(f"  position-based (disk,row,x,y,type): removed={len(removed)}, added={len(added)}")
    disk_name = dict(enumerate(DISKS_NEW))
    # per-row summary of the changed rows (module count old -> new)
    touched = sorted({(p[0], p[1]) for p in removed + added})
    for d, row in touched:
        n_old = ((old_modules.disk_id == d) & (old_modules.row_index == row)).sum()
        n_new = ((new_modules.disk_id == d) & (new_modules.row_index == row)).sum()
        types_old = list(old_modules[(old_modules.disk_id == d) & (old_modules.row_index == row)].type_id)
        types_new = list(new_modules[(new_modules.disk_id == d) & (new_modules.row_index == row)].type_id)
        say(f"    row changed: {disk_name[d]} row {row}: {n_old} modules {types_old} -> {n_new} {types_new}")
    old_by_pos = {(r.disk_id, r.row_index, round(r.x_origin_mm, 4), round(r.y_origin_mm, 4), r.type_id):
                  r.mod_index for r in old_modules.itertuples()}
    new_by_pos = {(r.disk_id, r.row_index, round(r.x_origin_mm, 4), round(r.y_origin_mm, 4), r.type_id):
                  r.mod_index for r in new_modules.itertuples()}
    for tag, items, lookup in (("removed (old only)", removed, old_by_pos),
                               ("added (new only)", added, new_by_pos)):
        for p in items:
            say(f"    {tag}: {disk_name[p[0]]} row {p[1]} mod {lookup[p]} {p[4]} "
                f"x={p[2]:+.4f} y={p[3]:+.4f}")
    if not changed.empty and len(changed) <= 60:
        for r in changed.itertuples():
            say(f"    key changed: {disk_name[r.disk_id]} row {r.row_index} mod {r.mod_index}: "
                f"{r.type_id_old} x={r.x_origin_mm_old:+.4f} -> {r.type_id_new} x={r.x_origin_mm_new:+.4f}")

    # z differences for modules at the same position and type
    same = both.drop(changed.index)
    same = same.assign(facing=same.type_id_new.map(facing),
                       n=np.sign(same.z_sensor_mm_new - same.z_baseplate_mm_new))
    for f in ("OUTWARD", "INWARD"):
        s = same[same.facing == f]
        dzb = ((s.z_baseplate_mm_new - s.z_baseplate_mm_old) * s.n).round(4)
        dzs = ((s.z_sensor_mm_new - s.z_sensor_mm_old) * s.n).round(4)
        say(f"    {f}: {len(s)} same-position modules; along n: dz_baseplate values "
            f"{dzb.value_counts().to_dict()}, dz_sensor values {dzs.value_counts().to_dict()}")
    if expect_identical:
        verdict(f"4.{name} x, y, type identical for every (disk,row,mod)",
                only_new.empty and only_old.empty and changed.empty,
                f"{len(both)} matched")
    else:
        # rsu6 vs all_6rsu: informational, the provider changed module content
        verdict(f"4.{name} differences enumerated (informational)", True,
                f"removed={len(removed)}, added={len(added)}, net={len(new_modules) - len(old_modules)}")


# ---------------------------------------------------------------------------
# Check 5: rows vs the reconstructed lattice
# ---------------------------------------------------------------------------
def blocked_by_opening(row_y, half_pitch, meta_disk, band="half_pitch"):
    """True if the row's y band overlaps an opening primitive's y extent."""
    half = half_pitch if band == "half_pitch" else band
    for i in range(int(meta_disk["n_opening_primitives"])):
        cy = float(meta_disk[f"opening_primitive_{i}_cy_mm"])
        b = float(meta_disk[f"opening_primitive_{i}_b_mm"])
        if row_y - half < cy + b and row_y + half > cy - b:
            return True
    return False


def check_rows(rows, rows_other, meta, old_modules):
    same = rows.drop(columns="disk").reset_index(drop=True).equals(
        rows_other.drop(columns="disk").reset_index(drop=True))
    verdict("5. rows.csv identical in rsu_opt and rsu6", same)

    old = pd.read_csv(OLD_ROWS_TABLE)
    old["disk"] = old.disk.replace({"HD3b": "HD3"})
    say("  per disk: new rows vs old lattice table (matched by row_index; old boundary rows -1/N excluded)")
    say("  disk  nNew nOld(-bnd) max|dy|  rows with |dy|>1e-4               hp==pitch/2  facet_z-zc==-offset")
    all_ok = True
    for disk in DISKS_NEW:
        r = rows[rows.disk == disk].set_index("row_index")
        o = old[old.disk == disk].set_index("row_index")
        # boundary rows exist only where the old table has row -1 (then also row N)
        has_boundary = (o.index == -1).any()
        last = o.index.max() - 1 if has_boundary else o.index.max()
        o_inner = o.loc[(o.index >= 0) & (o.index <= last)]
        common = r.index.intersection(o_inner.index)
        dy = (r.loc[common, "row_y_mm"] - o_inner.loc[common, "row_y_mm"])
        diff_rows = list(dy.index[dy.abs() > TOL])
        hp_ok = np.allclose(r.loc[common, "half_pitch_mm"], o_inner.loc[common, "pitch_mm"] / 2, atol=TOL)
        zc = float(meta[disk]["z_center_mm"])
        rel = r.loc[common, "facet_z_mm"] - zc
        opposite = np.allclose(rel, -o_inner.loc[common, "surface_offset_mm"], atol=TOL)
        same_sign = np.allclose(rel, o_inner.loc[common, "surface_offset_mm"], atol=TOL)
        all_ok &= len(r) == len(o_inner) and len(common) == len(r) and hp_ok and opposite
        rows_txt = (f"{diff_rows[0]}..{diff_rows[-1]} ({len(diff_rows)})" if diff_rows else "-")
        say(f"  {disk:4s} {len(r):5d} {len(o_inner):5d}   {dy.abs().max():6.4f}  {rows_txt:34s}"
            f" {str(hp_ok):11s}  {opposite} (same-sign: {same_sign})")
        if diff_rows:
            say("        dy[row] = " + ", ".join(f"{i}:{dy[i]:+.4f}" for i in diff_rows))
        if not has_boundary:
            say("        (old table has no boundary rows for this disk)")
        # adjacent-row spacing vs half pitch (a regular lattice has spacing == half_pitch)
        spacing = -np.diff(r.row_y_mm.values)
        for hp in sorted(r.half_pitch_mm.unique()):
            both_hp = (r.half_pitch_mm.values[:-1] == hp) & (r.half_pitch_mm.values[1:] == hp)
            if both_hp.any():
                s = spacing[both_hp]
                say(f"        adjacent-row spacing for half_pitch {hp}: {s.min():.4f}..{s.max():.4f} mm "
                    f"({both_hp.sum()} pairs)")
    verdict("5. row count, half_pitch == pitch/2 and facet_z - z_center == -surface_offset on every disk",
            all_ok)

    # old delivery: module z_baseplate (== facet) relative to old table at the same row
    ot = old.copy()
    ot["disk_id"] = ot.disk.map({d: i for i, d in enumerate(DISKS_NEW)})
    om = old_modules.merge(ot[["disk_id", "row_index", "surface_offset_mm"]], on=["disk_id", "row_index"])
    om["zc"] = om.disk.map(lambda d: float(meta[d.replace("HD3b", "HD3")]["z_center_mm"]))
    old_rel_opposite = np.allclose(om.z_baseplate_mm - om.zc, -om.surface_offset_mm, atol=TOL)
    say(f"  old 20261001 modules: z_baseplate - z_center == -surface_offset for all {len(om)}: {old_rel_opposite}")
    say("  => sign convention: the old table's surface_offset is the carbon flat located AT the row y;")
    say("     rows.csv facet_z (and every module's mounting plane) is the OPPOSITE surface, i.e. the plane of")
    say("     the two neighbouring same-surface flats at y +/- half_pitch that carry the module edges.")

    # x_outer and BLOCKED
    xo_bad = 0
    for disk in DISKS_NEW:
        r = rows[rows.disk == disk]
        R = float(meta[disk]["outer_radius_mm"])
        xo_bad += (np.abs(np.sqrt(R**2 - r.row_y_mm**2) - r.x_outer_mm) > TOL).sum()
    verdict("5. x_outer_mm == sqrt(outer_radius^2 - row_y^2) (half chord of the disk at row centre)",
            xo_bad == 0, f"mismatches={xo_bad}")

    say("  BLOCKED rows (row y band overlaps an opening primitive's y extent?)")
    hypothesis_ok = True
    for disk in DISKS_NEW:
        r = rows[rows.disk == disk]
        predicted = r.apply(lambda q: blocked_by_opening(q.row_y_mm, q.half_pitch_mm, meta[disk]), axis=1)
        actual = r.row_type == "BLOCKED"
        hypothesis_ok &= bool((predicted == actual).all())
        prims = [(float(meta[disk][f"opening_primitive_{i}_cy_mm"]),
                  float(meta[disk][f"opening_primitive_{i}_b_mm"]))
                 for i in range(int(meta[disk]["n_opening_primitives"]))]
        ext = max(cy + b for cy, b in prims)
        blocked = r[actual]
        say(f"    {disk:4s} opening |y|<={ext:.3f}: BLOCKED rows {list(blocked.row_index)} "
            f"y={[round(v, 3) for v in blocked.row_y_mm]}; mismatches vs rule="
            f"{list(r.row_index[predicted != actual])}")
    verdict("5. BLOCKED <=> |row_y - cy| < half_pitch + b for some opening primitive", hypothesis_ok)


# ---------------------------------------------------------------------------
# Check 6/7: module component boxes in detector coordinates (Step 8d logic)
# ---------------------------------------------------------------------------
def interval(center, width):
    return center - width / 2.0, center + width / 2.0


def overlap(a, b):
    return min(a[1], b[1]) - max(a[0], b[0])


def fpc_y_geometry(module_width, target_length, top_offset):
    """FPC y extent in module-local y: from the lower epoxy line's inner edge up to the top edge."""
    top_edge = module_width / 2.0 + top_offset
    lower_epoxy_inner_edge = -module_width / 2.0 + EPOXY_GLUE_LINE_WIDTH
    box_y = min(target_length, max(0.0, top_edge - lower_epoxy_inner_edge))
    return box_y, top_edge - box_y / 2.0


def build_boxes(catalog, modules, model):
    """Return lists of dicts for FPC boxes and LEC/REC end-film boxes (detector frame)."""
    spec_by_type = {r.type_id: r for r in catalog.itertuples()}
    fpcs, films = [], []
    for src in modules.itertuples():
        spec = spec_by_type[src.type_id]
        width = spec.module_height_mm
        chain = spec.rsu_count * RSU_LENGTH
        # engineer RIGHT/NEGATIVE becomes left-handed after x_EPIC = -x_engineer
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
        u = stack_u(spec.facing, model)

        def zint(name):
            vals = [src.z_baseplate_mm + n * v for v in u[name]]
            return min(vals), max(vals)

        common = dict(disk=src.disk, row=src.row_index, mod=src.mod_index, type_id=src.type_id,
                      facing=spec.facing, n=n, z_ref=src.z_baseplate_mm, y0=src.y_origin_mm,
                      width=width)
        lec_x = sensor_x + (chain / 2 + spec.LEC_mm / 2 if lec_after_rsu else -chain / 2 - spec.LEC_mm / 2)
        rec_x = sensor_x + (-chain / 2 - spec.REC_mm / 2 if lec_after_rsu else chain / 2 + spec.REC_mm / 2)
        for name, lx, bx in (("lec_film", lec_x, spec.LEC_mm), ("rec_film", rec_x, spec.REC_mm)):
            films.append(dict(common, name=name, x=interval(module_x + local_x_sign * lx, bx),
                              y=interval(src.y_origin_mm, FILM_Y_WIDTH), z=zint("film")))
        for side, after, span, endcap, tx, ty, top in (
                ("left", lec_after_rsu, spec.BLEC_mm, spec.LEC_mm, LEFT_FPC_X, LEFT_FPC_Y, LEFT_FPC_TOP_OFFSET),
                ("right", not lec_after_rsu, spec.BREC_mm, spec.REC_mm, RIGHT_FPC_X, RIGHT_FPC_Y,
                 RIGHT_FPC_TOP_OFFSET)):
            bx = min(tx, max(0.0, span - endcap - FPC_GAP))
            lx = (chain / 2 + endcap + FPC_GAP + bx / 2) if after else (-chain / 2 - endcap - FPC_GAP - bx / 2)
            lx += sensor_x
            by, ly = fpc_y_geometry(width, ty, top)
            for material in ("kapton", "aluminum"):
                fpcs.append(dict(common, name=f"{side}_fpc_{material}",
                                 x=interval(module_x + local_x_sign * lx, bx),
                                 y=interval(src.y_origin_mm + local_y_sign * ly, by), z=zint(material)))
    return fpcs, films


def fpc_film_pairs(catalog, modules, model):
    fpcs, films = build_boxes(catalog, modules, model)
    films_by_disk = {}
    for f in films:
        films_by_disk.setdefault(f["disk"], []).append(f)
    hits = []
    for p in fpcs:
        for f in films_by_disk[p["disk"]]:
            if (p["row"], p["mod"]) == (f["row"], f["mod"]):
                continue
            dims = [overlap(p[a], f[a]) for a in "xyz"]
            if all(d > 1e-6 for d in dims):
                hits.append((p, f, dims))
    pairs = sorted({tuple(sorted(((p["disk"], p["row"], p["mod"]), (f["disk"], f["row"], f["mod"]))))
                    for p, f, _ in hits})
    return hits, pairs, len(fpcs), len(films)


def report_pairs(label, catalog, modules, model):
    hits, pairs, nf, nfilm = fpc_film_pairs(catalog, modules, model)
    say(f"  {label}: {nf} FPC boxes, {nfilm} end-film boxes, {len(hits)} intersections, "
        f"{len(pairs)} unique module pairs")
    for p, f, d in hits:
        say(f"    {p['disk']} {p['row']}/{p['mod']} {p['type_id']} {p['facing']} {p['name']} vs "
            f"{f['row']}/{f['mod']} {f['type_id']} {f['facing']} {f['name']}; "
            f"overlap xyz = {d[0]:.4f},{d[1]:.4f},{d[2]:.4f} mm")
    return pairs


def check_inward_fpc(name, catalog, modules, rows):
    say(f"  {name}: z intervals along the inward normal from the facet plane "
        "(positive into the channel / carbon side):")
    u = stack_u("INWARD", "new")
    old_u = stack_u("INWARD", "old")
    carbon = (0.0, CARBON_FLAT)
    for label, layer in (("Kapton", "kapton"), ("Al", "aluminum")):
        lo, hi = u[layer]
        say(f"    {label:6s} new {lo:+.3f}..{hi:+.3f}  (old Step 8e: {old_u[layer][0] + OLD_INWARD_Z_CLEARANCE:+.3f}"
            f"..{old_u[layer][1] + OLD_INWARD_Z_CLEARANCE:+.3f} without the 30 um translation)"
            f"  overlap with carbon {carbon[0]:+.3f}..{carbon[1]:+.3f}: {overlap(u[layer], carbon):+.3f} mm")
    say(f"    baseplate {u['baseplate'][0]:+.3f}..{u['baseplate'][1]:+.3f}, film {u['film'][0]:+.3f}.."
        f"{u['film'][1]:+.3f}, sensor {u['sensor'][0]:+.3f}..{u['sensor'][1]:+.3f}")

    # per-module check in global z: Al interval vs carbon slab facet..facet+n*0.150
    fpcs, _ = build_boxes(catalog, modules, "new")
    inward = [p for p in fpcs if p["facing"] == "INWARD"]
    al_worst = kap_worst = -1e9
    for p in inward:
        slab = tuple(sorted((p["z_ref"], p["z_ref"] + p["n"] * CARBON_FLAT)))
        ov = overlap(p["z"], slab)
        if p["name"].endswith("aluminum"):
            al_worst = max(al_worst, ov)
        else:
            kap_worst = max(kap_worst, ov)
    verdict(f"7.{name} inward Al does not intersect the carbon flat; Kapton only touches",
            al_worst < -1e-6 and abs(kap_worst) < 1e-6,
            f"{len(inward)//2} inward FPC rectangles; max z overlap Al {al_worst:+.4f} mm, "
            f"Kapton {kap_worst:+.4f} mm (0 = shared surface)")

    # y footprint vs the neighbouring flats on the mounting surface (rows i-1, i+1)
    say(f"  {name}: y overlap of inward FPC rectangles with the neighbouring straight flats "
        "(B 6.36 / A 7.86 mm, centred on rows i+/-1 of rows.csv) -- for the record only")
    row_y = {(r.disk, r.row_index): (r.row_y_mm, r.half_pitch_mm) for r in rows.itertuples()}
    stats = {}
    worst = None
    for p in inward:
        if not p["name"].endswith("kapton"):
            continue          # Kapton and Al share the same x/y footprint
        y_c, hp = row_y[(p["disk"], p["row"])]
        family = "A" if p["width"] > 33.5 else "B"
        best = 0.0
        for step in (-1, 1):
            neighbour = row_y.get((p["disk"], p["row"] + step))
            if neighbour is None:   # lattice end: extrapolate one half pitch
                ny, nhp = y_c + np.sign(y_c - row_y[(p["disk"], p["row"] - step)][0]) * hp, hp
            else:
                ny, nhp = neighbour
            flat = interval(ny, STRAIGHT_FLAT_WIDTH[round(nhp, 1)])
            best = max(best, overlap(p["y"], flat))
        key = (family, p["name"].split("_")[0])
        s = stats.setdefault(key, [0, 0, 0.0])
        s[0] += 1
        if best > 1e-6:
            s[1] += 1
            s[2] = max(s[2], best)
            if worst is None or best > worst[0]:
                worst = (best, p)
    for (family, side), (total, n_ov, mx) in sorted(stats.items()):
        say(f"    {family} {side:5s} FPC: {n_ov}/{total} overlap a neighbouring flat in y, max {mx:.3f} mm")
    if worst:
        p = worst[1]
        say(f"    worst: {p['disk']} row {p['row']} mod {p['mod']} {p['type_id']} {p['name'][:-7]} "
            f"y={p['y'][0]:.3f}..{p['y'][1]:.3f}, overlap {worst[0]:.3f} mm")


# ---------------------------------------------------------------------------
def main():
    say("Step 11c validation of the 20261110 SVT endcap tiling delivery")
    say(f"new: {NEW.relative_to(ROOT)}  old: {OLD.relative_to(ROOT)}")

    section("Check 1: file completeness and consistency")
    new = {}
    for scen in ("rsu_opt", "rsu6"):
        new[scen] = check_files(scen, NEW / scen)
    if any(v is None for v in new.values()):
        say("cannot continue without complete files")
        return finish()
    old = {s: load_scenario(OLD / s, DISKS_OLD) for s in ("rsu_opt", "all_6rsu")}
    say(f"  module counts: new rsu_opt {len(new['rsu_opt'][1])}, new rsu6 {len(new['rsu6'][1])}, "
        f"old rsu_opt {len(old['rsu_opt'][1])}, old all_6rsu {len(old['all_6rsu'][1])}")

    section("Check 2: chirality relabelling")
    check_chirality("rsu_opt", new["rsu_opt"][0], old["rsu_opt"][0])
    check_chirality("rsu6", new["rsu6"][0], old["all_6rsu"][0])

    section("Check 3: placement z with the new module stack")
    for scen in ("rsu_opt", "rsu6"):
        catalog, modules, rows, meta = new[scen]
        check_placement_z(scen, catalog, modules, rows, meta)

    section("Check 4: old vs new placements")
    check_old_vs_new("rsu_opt vs old rsu_opt", new["rsu_opt"][1], new["rsu_opt"][0],
                     old["rsu_opt"][1], expect_identical=True)
    check_old_vs_new("rsu6 vs old all_6rsu", new["rsu6"][1], new["rsu6"][0],
                     old["all_6rsu"][1], expect_identical=False)

    section("Check 5: rows.csv vs reconstructed lattice table")
    check_rows(new["rsu_opt"][2], new["rsu6"][2], new["rsu_opt"][3], old["rsu_opt"][1])

    section("Check 6: bridge-FPC vs neighbouring LEC/REC film pairs")
    say("  self-check: old Step 8d model on the old delivery")
    old_pairs = report_pairs("old all_6rsu (old stack)", old["all_6rsu"][0], old["all_6rsu"][1], "old")
    verdict("6. Step 8d reproduction: old all_6rsu has 7 pairs", len(old_pairs) == 7,
            f"{len(old_pairs)} pairs")
    report_pairs("old rsu_opt (old stack)", old["rsu_opt"][0], old["rsu_opt"][1], "old")
    old_pair_positions = set()
    om = old["all_6rsu"][1].set_index(["disk", "row_index", "mod_index"])
    for pair in old_pairs:
        old_pair_positions.add(tuple(sorted(
            (k[0].replace("HD3b", "HD3"), k[1], round(om.loc[k, "x_origin_mm"], 4)) for k in pair)))
    for scen in ("rsu6", "rsu_opt"):
        catalog, modules = new[scen][0], new[scen][1]
        pairs = report_pairs(f"new {scen} (new stack)", catalog, modules, "new")
        nm = modules.set_index(["disk", "row_index", "mod_index"])
        new_pos = {tuple(sorted((k[0], k[1], round(nm.loc[k, "x_origin_mm"], 4)) for k in pair))
                   for pair in pairs}
        persisting = old_pair_positions & new_pos
        verdict(f"6.{scen} no bridge-FPC/end-film intersections", not pairs,
                f"{len(pairs)} pairs; of the 7 old all_6rsu pairs (by disk,row,x) {len(persisting)} persist")

    section("Check 7: inward bridge FPC vs carbon")
    for scen in ("rsu_opt", "rsu6"):
        catalog, modules, rows, _ = new[scen]
        check_inward_fpc(scen, catalog, modules, rows)

    return finish()


def finish():
    section("Summary")
    failed = [n for n, ok in RESULTS if not ok]
    say(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    for n in failed:
        say(f"  FAILED: {n}")
    say(f"OVERALL: {'PASS' if not failed else 'FAIL'}")
    REPORT.write_text("\n".join(LINES) + "\n")
    print(f"report written to {REPORT}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
