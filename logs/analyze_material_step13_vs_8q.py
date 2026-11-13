#!/usr/bin/env python3
"""Step 13g: explain the Step 8q -> Step 13 SVT endcap material changes and compare the two ACTS maps.

Host script (conda env `tracking`), read-only on all inputs. Writes nothing except stdout;
run as  python logs/analyze_material_step13_vs_8q.py > logs/analyze_material_step13_vs_8q.txt

Inputs
  scans : matscan/disk_material_map/{step8q_20261106T153414Z,step13_20261113T065150Z}/
          disk_material_summary.json and disk_material_<disk>.npz (from disk_material_map.py)
  geom  : matscan/disk_material_map/step13g_geometry_rects/{step8q,step13}_module_rects.csv
          (every module daughter box as a global x-y rectangle; logs/run_dump_svt_module_rects_step13g.sh
          from out/visualize_8q.root and out/visualize_step13.root)
  maps  : matmap/{step8q_20261106T222257Z,step13_20261113T054800Z}/ (run_log.txt, config-map_regenerated.json,
          material-map_map.root, material-map_mapped.root, propagation_material_regenerated.root)

Sections
  A  per-disk scan totals and their statistical precision
  B  observed per-material changes (scan summary) and per y-half changes (x-y maps)
  C  geometry prediction. For geantinos uniform in eta and phi from the origin, the track-weighted
     mean of x/X0 of a thin layer of thickness t at |z| is proportional to  (t/X0) * Integral dA / r^2
     (track density per area ~ |z|/(r^2 sqrt(r^2+z^2)), path factor 1/cos(theta) = sqrt(r^2+z^2)/|z|).
     So the predicted Step13/Step8q ratio of a material on a disk is
         sum_boxes t * I(box)  [Step 13]  /  sum_boxes t * I(box)  [Step 8q],
     I(box) = Integral over the box footprint, restricted to the scan region (r < r_max + 2 mm, outside
     both beam-pipe openings incl. 5 mm buffer), of dA / r^2  (midpoint rule, 0.5 mm cells).
     X0 cancels in the ratio of one material. Corrugated carbon is not in the dump (frames, not modules).
  D  top-half FPC/AncASIC move (Step 13 flip) in the geometry and in the scan x-y maps
  E  ACTS map review: run_log warnings, files, surfaces/bins, per-surface map change, map vs Geant4 x/X0(eta)
"""
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import uproot

PROJ = Path("/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling")
EPIC = PROJ.parent
SCAN = {"8q": PROJ / "matscan/disk_material_map/step8q_20261106T153414Z",
        "13": PROJ / "matscan/disk_material_map/step13_20261113T065150Z"}
RECTS = {"8q": PROJ / "matscan/disk_material_map/step13g_geometry_rects/step8q_module_rects.csv",
         "13": PROJ / "matscan/disk_material_map/step13g_geometry_rects/step13_module_rects.csv"}
MAP = {"8q": PROJ / "matmap/step8q_20261106T222257Z", "13": PROJ / "matmap/step13_20261113T054800Z"}
R_MARGIN = 2.0
CELL = 0.5  # mm, integration cell for I(box)

# disk table and opening geometry exactly as used by the scan
_spec = importlib.util.spec_from_file_location("dmm", EPIC / "scripts/subdetector_tests/disk_material_map.py")
dmm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dmm)
GEOS = {d[0]: dmm.disk_geometry(*d, R_MARGIN) for d in dmm.DISKS}
DISK_NAMES = [d[0] for d in dmm.DISKS]

# scan material categories -> module-box keys in the geometry dump
CATEGORY = {"Silicon": "Silicon", "Aluminum": "Aluminum", "Kapton": "Kapton", "Copper": "Copper",
            "SVT_Endcap_Glue": "SVT_Endcap_Glue", "CarbonFiber": "CarbonFiber"}


def pct(a, b):
    return 100.0 * (b / a - 1.0)


def header(title):
    print("\n" + "=" * 100 + f"\n{title}\n" + "=" * 100)


# ----------------------------------------------------------------------------------------------
# A + B: scans
# ----------------------------------------------------------------------------------------------
def load_scans():
    js = {k: json.load(open(v / "disk_material_summary.json")) for k, v in SCAN.items()}
    npz = {k: {d: np.load(v / f"disk_material_{d}.npz") for d in DISK_NAMES} for k, v in SCAN.items()}
    return js, npz


def section_a(js):
    header("A. Per-disk mean x/X0 on the annulus (scan), Step 8q -> Step 13")
    print("stat. error estimate: sigma_rel(mean) ~ sqrt((1-f)/(f N)) with f = fraction of tracks crossing the"
          "\nmaterial (from C below for each material); for the total the per-track spread is dominated by"
          "\ncarbon/silicon coverage, so the total's error is quoted from the silicon estimate (upper bound).")
    print(f"{'disk':5s} {'8q[%X0]':>9s} {'13[%X0]':>9s} {'change':>8s}  {'N_ann 8q':>9s} {'N_ann 13':>9s}")
    for d in DISK_NAMES:
        a, b = js["8q"][d], js["13"][d]
        print(f"{d:5s} {a['mean_x0_pct']:9.4f} {b['mean_x0_pct']:9.4f} {pct(a['mean_x0_pct'], b['mean_x0_pct']):+7.2f}%"
              f"  {a['tracks_on_annulus']:9d} {b['tracks_on_annulus']:9d}")


def half_ratios(npz, d, mat):
    """Observed Step13/Step8q ratio of the track-weighted mean of one material in y>0 / y<0 (x-y map bins)."""
    out = {}
    for lab in ("top", "bot", "all"):
        vals = []
        for k in ("8q", "13"):
            z = npz[k][d]
            e = z["xy_edges"]
            c = 0.5 * (e[1:] + e[:-1])
            _, Y = np.meshgrid(c, c, indexing="ij")
            sel = {"top": Y > 0, "bot": Y < 0, "all": np.ones_like(Y, bool)}[lab]
            vals.append(z["mat_xy_x0_sum__" + mat][sel].sum() / z["xy_n"][sel].sum())
        out[lab] = pct(*vals)
    return out


# ----------------------------------------------------------------------------------------------
# C: geometry prediction
# ----------------------------------------------------------------------------------------------
def load_rects(tag):
    df = pd.read_csv(RECTS[tag])
    # assign each box to the nearest disk in z (all within a few mm)
    zs = np.array([GEOS[d]["z"] for d in DISK_NAMES])
    idx = np.abs(df["zc"].values[:, None] - zs[None, :]).argmin(axis=1)
    df["disk"] = np.array(DISK_NAMES)[idx]
    df["dz_disk"] = df["zc"].values - zs[idx]
    return df


def box_integrals(df, g):
    """I(box) = sum over cells inside the scan region of cell_area / r^2; also split by sign of y."""
    p0 = df[["x0", "y0"]].values
    p1 = df[["x1", "y1"]].values
    p3 = df[["x3", "y3"]].values
    u, v = p1 - p0, p3 - p0
    lu, lv = np.hypot(*u.T), np.hypot(*v.T)
    I_all = np.zeros(len(df))
    I_top = np.zeros(len(df))
    for i in range(len(df)):
        nu, nv = max(1, int(np.ceil(lu[i] / CELL))), max(1, int(np.ceil(lv[i] / CELL)))
        su = (np.arange(nu) + 0.5) / nu
        sv = (np.arange(nv) + 0.5) / nv
        S, T = np.meshgrid(su, sv, indexing="ij")
        x = p0[i, 0] + S * u[i, 0] + T * v[i, 0]
        y = p0[i, 1] + S * u[i, 1] + T * v[i, 1]
        r2 = x * x + y * y
        inside = (np.sqrt(r2) < g["rcut"]) & dmm.outside_openings(g, x, y)
        w = np.where(inside, 1.0 / r2, 0.0) * (lu[i] * lv[i] / (nu * nv))
        I_all[i] = w.sum()
        I_top[i] = w[y > 0].sum()
    return I_all, I_top


def weighted_by_disk(df):
    """Per disk and material: sum t*I (all, top, bottom) and per box-key."""
    rows = []
    for d in DISK_NAMES:
        sub = df[df.disk == d]
        I_all, I_top = box_integrals(sub, GEOS[d])
        t = sub["thickness_um"].values
        tmp = pd.DataFrame({"disk": d, "key": sub["key"].values, "material": sub["material"].values,
                            "tI": t * I_all, "tI_top": t * I_top, "tI_bot": t * (I_all - I_top), "I": I_all,
                            "y": sub[["y0", "y1", "y2", "y3"]].values.mean(axis=1),
                            "mod_y": sub["mod_y"].values})
        rows.append(tmp)
    return pd.concat(rows, ignore_index=True)


def annulus_integral(g):
    """Integral of dA/r^2 over the scan region (for coverage fractions)."""
    e = np.arange(-g["rcut"], g["rcut"] + CELL, CELL)
    c = 0.5 * (e[1:] + e[:-1])
    X, Y = np.meshgrid(c, c, indexing="ij")
    r2 = X * X + Y * Y
    inside = (np.sqrt(r2) < g["rcut"]) & dmm.outside_openings(g, X, Y) & (r2 > 0)
    return float(np.where(inside, 1.0 / np.where(r2 > 0, r2, 1), 0.0).sum() * CELL * CELL)


def main():
    js, npz = load_scans()
    print("Step 13g material analysis: Step 8q -> Step 13 (EPIC 311634084 -> 78ade4686)")
    print("scans:", SCAN["8q"].name, "->", SCAN["13"].name)
    print("maps :", MAP["8q"].name, "->", MAP["13"].name)
    section_a(js)

    # ---------------- geometry
    rect = {k: load_rects(k) for k in ("8q", "13")}
    header("C0. Geometry dump sanity (module boxes)")
    for k, df in rect.items():
        g = df.groupby(["key", "material"])["thickness_um"].agg(["size", "mean"])
        print(f"-- {k}: {len(df)} boxes, {df.drop_duplicates(['mod_x','mod_y','mod_z']).shape[0]} modules, "
              f"max |z_box - z_disk| = {df.dz_disk.abs().max():.2f} mm")
        print(g.to_string())
    # same footprints apart from the flipped electronics?
    # match boxes by module type, module x-y (rounded to 0.01 mm), key and the box's order along
    # the module (several RSU boxes share one key); module z is not used because it moved by tens of um
    for df in rect.values():
        df["mx"], df["my"] = df.mod_x.round(2), df.mod_y.round(2)
        df["bx"] = df[["x0", "x1", "x2", "x3"]].mean(axis=1) + 1e-3 * df[["y0", "y1", "y2", "y3"]].mean(axis=1)
        df.sort_values(["module_type", "mx", "my", "key", "bx"], inplace=True)
        df["ord"] = df.groupby(["module_type", "mx", "my", "key"]).cumcount()
    keys = ["module_type", "mx", "my", "key", "ord"]
    m = rect["8q"].merge(rect["13"], on=keys, suffixes=("_a", "_b"))
    mods = m.drop_duplicates(["module_type", "mx", "my"])
    dzm = (mods.mod_z_b - mods.mod_z_a) * 1000 * np.sign(mods.mod_z_a)
    print("module centre z shift Step13 - Step8q (um, sign: + = away from z = 0): "
          + ", ".join(f"{v:+.1f}: {n}" for v, n in dzm.round(1).value_counts().sort_index().items()))
    cols = [f"{c}{i}" for i in range(4) for c in "xy"]
    moved = np.zeros(len(m), bool)
    for c in cols:
        moved |= np.abs(m[c + "_a"].values - m[c + "_b"].values) > 1e-2
    print(f"\nboxes matched by (module, key): {len(m)} of {len(rect['8q'])}/{len(rect['13'])}")
    mv = m[moved]
    print("boxes whose x-y footprint changed, by key and module half (mod_y > 0 = top):")
    print(mv.groupby(["key", mv.mod_y_a > 0]).size().rename("n").to_string())
    tchg = m[np.abs(m.thickness_um_a - m.thickness_um_b) > 1e-6]
    print("boxes whose thickness changed:",
          tchg.groupby("key").apply(lambda s: f"{len(s)} ({s.thickness_um_a.iloc[0]}->{s.thickness_um_b.iloc[0]} um)").to_dict())

    w = {k: weighted_by_disk(rect[k]) for k in ("8q", "13")}

    header("C1. Silicon: thickness-only expectation and 1/r^2-weighted prediction vs scan")
    print("RSU silicon (inactive+active) 36+14 = 50 um -> 33.5+14 = 47.5 um: ratio 47.5/50 = 0.9500 (-5.00 %)."
          "\nSilicon in the scan also contains LEC/REC (50 um, unchanged) and the AncASIC (300 um, unchanged"
          "\nthickness, moved in y on top-half modules). Area-only prediction (all disks, no weighting):")
    for k in ("8q", "13"):
        s = rect[k][rect[k].material == "Silicon"]
        x = s[["x0", "x1", "x2", "x3"]].values
        y = s[["y0", "y1", "y2", "y3"]].values
        area = 0.5 * np.abs(sum(x[:, i] * y[:, (i + 1) % 4] - x[:, (i + 1) % 4] * y[:, i] for i in range(4)))
        vol = pd.Series(area * s.thickness_um.values / 1e3, index=s.key.values).groupby(level=0).sum() / 1e3
        if k == "8q":
            vol8 = vol
        print(f"  {k}: Si volume [cm^3] by key: " + ", ".join(f"{i} {v:.2f}" for i, v in vol.items())
              + f"; total {vol.sum():.2f}")
    print(f"  area-only total Si ratio = {vol.sum() / vol8.sum():.4f} ({pct(vol8.sum(), vol.sum()):+.2f} %); "
          f"RSU share of Step 8q Si = {(vol8['inactive_si'] + vol8['active_si']) / vol8.sum():.3f}")

    print(f"\n{'disk':5s} {'Si obs':>8s} {'Si pred':>8s} {'pred thick-only':>15s} {'RSU share':>9s} {'ASIC share':>10s}")
    for d in DISK_NAMES:
        a = w["8q"][(w["8q"].disk == d) & (w["8q"].material == "Silicon")]
        b = w["13"][(w["13"].disk == d) & (w["13"].material == "Silicon")]
        rsu = a[a.key.isin(["inactive_si", "active_si"])].tI.sum()
        asic = a[a.key == "ancasic"].tI.sum()
        # thickness-only: keep Step 8q positions, scale RSU by 0.95
        thick_only = (a.tI.sum() - 0.05 * rsu) / a.tI.sum()
        obs = js["13"][d]["materials"]["Silicon"]["mean_x0_pct"] / js["8q"][d]["materials"]["Silicon"]["mean_x0_pct"]
        print(f"{d:5s} {100*(obs-1):+7.2f}% {pct(a.tI.sum(), b.tI.sum()):+7.2f}% {100*(thick_only-1):+14.2f}% "
              f"{rsu / a.tI.sum():9.3f} {asic / a.tI.sum():10.3f}")

    header("C2. All materials: 1/r^2-weighted geometry prediction vs scan (whole annulus and y halves)")
    print("obs = scan summary (share x mean, as in the scan report); obs_top/obs_bot from x-y map bins (y>0 / y<0);"
          "\npred = module boxes only (CarbonFiber pred covers the 150 um baseplates, not the corrugated frame)."
          "\nsig = estimated 1-sigma stat. error of the Step13/Step8q difference, sqrt(2*(1-f)/(f N_ann)),"
          "\nf = coverage = sum(I)/I_annulus of that material's boxes (overlaps counted twice -> f slightly high).")
    I_ann = {d: annulus_integral(GEOS[d]) for d in DISK_NAMES}
    summary_rows = []
    for d in DISK_NAMES:
        print(f"-- {d}  (N_ann 8q/13 = {js['8q'][d]['tracks_on_annulus']}/{js['13'][d]['tracks_on_annulus']})")
        print(f"   {'material':16s} {'obs':>7s} {'pred':>7s} {'sig':>6s} | {'obs_top':>7s} {'pred_top':>8s} | "
              f"{'obs_bot':>7s} {'pred_bot':>8s}")
        n_ann = js["8q"][d]["tracks_on_annulus"]
        for mat in ["Silicon", "Aluminum", "Kapton", "Copper", "SVT_Endcap_Glue", "CarbonFiber"]:
            a = w["8q"][(w["8q"].disk == d) & (w["8q"].material == mat)]
            b = w["13"][(w["13"].disk == d) & (w["13"].material == mat)]
            obs = pct(js["8q"][d]["materials"][mat]["mean_x0_pct"], js["13"][d]["materials"][mat]["mean_x0_pct"])
            hr = half_ratios(npz, d, mat)
            if mat in ("Aluminum", "Kapton"):  # FPC boxes do not overlap each other
                f = a.I.sum() / I_ann[d]
            elif mat == "Silicon":
                f = a[a.key == "inactive_si"].I.sum() / I_ann[d]
            else:
                f = None
            sig = f"{100*np.sqrt(2*(1-min(f,0.999))/(min(f,0.999)*n_ann)):5.2f}%" if f else "   n/a"
            print(f"   {mat:16s} {obs:+6.2f}% {pct(a.tI.sum(), b.tI.sum()):+6.2f}% {sig} | {hr['top']:+6.2f}% "
                  f"{pct(a.tI_top.sum(), b.tI_top.sum()):+7.2f}% | {hr['bot']:+6.2f}% {pct(a.tI_bot.sum(), b.tI_bot.sum()):+7.2f}%")
            summary_rows.append((d, mat, obs, pct(a.tI.sum(), b.tI.sum())))
    s = pd.DataFrame(summary_rows, columns=["disk", "mat", "obs", "pred"])
    print("\nmean over the 10 disks (obs / pred):")
    print(s.groupby("mat")[["obs", "pred"]].mean().round(2).to_string())

    header("C3. Total x/X0: predicted change from module boxes (scan shares of Step 8q) vs observed")
    print("pred_total = sum_m share_m(8q) * pred_m   (CarbonFiber taken as observed, since the corrugated frame"
          "\nchanged in Step 12 and is not in the box dump)")
    for d in DISK_NAMES:
        tot = 0.0
        for mat in ["Silicon", "Aluminum", "Kapton", "Copper", "SVT_Endcap_Glue", "CarbonFiber"]:
            share = js["8q"][d]["materials"][mat]["share"]
            row = s[(s.disk == d) & (s.mat == mat)].iloc[0]
            tot += share * (row.obs if mat == "CarbonFiber" else row.pred)
        obs = pct(js["8q"][d]["mean_x0_pct"], js["13"][d]["mean_x0_pct"])
        si_part = js["8q"][d]["materials"]["Silicon"]["share"] * s[(s.disk == d) & (s.mat == "Silicon")].iloc[0].pred
        print(f"{d:5s} obs {obs:+6.2f}%  pred {tot:+6.2f}%   (of which Silicon {si_part:+6.2f}%)")

    # ---------------- D: FPC flip
    header("D. Step 13 FPC/AncASIC flip: where the electronics moved (geometry) and x-y map symmetry (scan)")
    print("  per box key: mean y offset of the box centre from the module y origin, signed + = away from y = 0,"
          "\n  and how far the box reaches away from y = 0 (mm); top = mod_y > 0, bot = mod_y < 0")
    for k in ("8q", "13"):
        df = rect[k]
        yc = df[["y0", "y1", "y2", "y3"]].mean(axis=1)
        ymin, ymax = df[["y0", "y1", "y2", "y3"]].min(axis=1), df[["y0", "y1", "y2", "y3"]].max(axis=1)
        sgn = np.sign(df.mod_y)
        dy_away = (yc - df.mod_y) * sgn
        reach = np.where(sgn > 0, ymax - df.mod_y, df.mod_y - ymin)
        for key in ("left_bridge_fpc_kapton", "right_bridge_fpc_kapton", "ancasic", "inactive_si"):
            sel = df.key == key
            top, bot = sel & (df.mod_y > 0), sel & (df.mod_y < 0)
            print(f"  {k:3s} {key:24s} dy_away top {dy_away[top].mean():+6.2f} bot {dy_away[bot].mean():+6.2f} | "
                  f"reach top {reach[top].mean():6.2f} bot {reach[bot].mean():6.2f}")
    print("  (module y origin = LEC/first-RSU boundary midpoint, i.e. the RSU centre line)")
    print("\n  scan x-y maps: correlation of the y>0 map with the mirrored (y -> -y) y<0 map, per material."
          "\n  Expected: Step 13 FPC (Al/Kapton) maps become mirror-symmetric like Si/carbon (if the delivery is"
          "\n  y-symmetric), Step 8q not.")
    print(f"  {'disk':5s} {'mat':9s} {'8q corr':>8s} {'13 corr':>8s}")
    for d in ("ED4", "ED1", "ED0", "HD0", "HD3"):
        for mat in ("Aluminum", "Kapton", "Silicon"):
            cs = []
            for k in ("8q", "13"):
                z = npz[k][d]
                mm = z["mat_xy_x0_sum__" + mat] / np.where(z["xy_n"] > 0, z["xy_n"], np.nan)
                ny = mm.shape[1]
                top, bot = mm[:, ny // 2:], mm[:, : ny // 2][:, ::-1]
                ok = np.isfinite(top) & np.isfinite(bot)
                cs.append(np.corrcoef(top[ok], bot[ok])[0, 1])
            print(f"  {d:5s} {mat:9s} {cs[0]:8.3f} {cs[1]:8.3f}")

    # ---------------- E: maps
    header("E. ACTS material map review: Step 8q map vs Step 13 map")
    for k in ("8q", "13"):
        log = (MAP[k] / "run_log.txt").read_text(errors="replace").splitlines()
        cnt = {}
        for line in log:
            if re.search(r"warn|error|fatal|exception", line, re.I):
                key = re.sub(r"\d{2}:\d{2}:\d{2}", "", line).strip()[:110]
                cnt[key] = cnt.get(key, 0) + 1
        print(f"-- {k}: run_log {len(log)} lines; warning/error-like lines:")
        for key, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
            print(f"     {n:4d}  {key}")
        tail = [l for l in log if l.startswith("real") or "Completed map" in l]
        print("     " + " | ".join(tail))
        for sub in ("plots", "Validation/regenerated", "Surfaces/regenerated/map_plot",
                    "Surfaces/regenerated/ratio_plot", "Surfaces/1D_plot", "Surfaces/dist_plot"):
            print(f"     {sub}: {len(list((MAP[k] / sub).iterdir()))} files")

    cfg = {k: json.load(open(MAP[k] / "config-map_regenerated.json")) for k in MAP}

    # count surfaces with material mapping enabled (generic walk of the JSON)
    def walk(o, acc):
        if isinstance(o, dict):
            if "material" in o and isinstance(o["material"], dict) and o["material"].get("mapMaterial"):
                acc.append(json.dumps(o["material"].get("binUtility", {}), sort_keys=True))
            for v in o.values():
                walk(v, acc)
        elif isinstance(o, list):
            for v in o:
                walk(v, acc)
        return acc

    for k in MAP:
        acc = walk(cfg[k], [])
        print(f"-- config-map_regenerated.json {k}: {len(acc)} entries with mapMaterial=true")
    print(f"   binnings identical between maps: {walk(cfg['8q'], []) == walk(cfg['13'], [])}")

    surf = {}
    for k in MAP:
        u = uproot.open(MAP[k] / "material-map_map.root")
        names = sorted({n.split("/")[0].split(";")[0] for n in u.keys() if n.startswith("SurfaceMaterial")})
        surf[k] = {}
        for n in names:
            t = u[n + "/t"].values()
            x0 = u[n + "/x0"].values()
            tx = np.where(x0 > 0, t / np.where(x0 > 0, x0, 1), 0.0)
            surf[k][n] = (t.shape, float(tx.mean()), int((t > 0).sum()))
    print(f"\nmaterial-map_map.root: surfaces 8q {len(surf['8q'])}, 13 {len(surf['13'])}, same names: "
          f"{sorted(surf['8q']) == sorted(surf['13'])}")
    print(f"total bins 8q {sum(np.prod(v[0]) for v in surf['8q'].values())}, "
          f"13 {sum(np.prod(v[0]) for v in surf['13'].values())}")
    print("per surface: bins, filled bins, unweighted bin-mean t/X0 [%] and change (|change| > 0.3 % or bin count change):")
    for n in sorted(surf["8q"]):
        a, b = surf["8q"][n], surf["13"].get(n)
        if b is None:
            print(f"   {n}: missing in 13")
            continue
        ch = pct(a[1], b[1]) if a[1] > 0 else 0.0
        flag = "  <--" if (abs(ch) > 0.3 or a[0] != b[0] or a[2] != b[2]) else ""
        if flag:
            print(f"   {n.replace('SurfaceMaterial_', ''):28s} {str(a[0]):>10s} filled {a[2]:5d}->{b[2]:5d}  "
                  f"{100*a[1]:.4f} -> {100*b[1]:.4f}  {ch:+6.2f}%{flag}")

    print("\nmap (propagation_material_regenerated) vs Geant4 (material-map_mapped) total t_X0 vs eta,"
          "\nas in Mat_map.C (Comp_Val_geant_mat_X0_Eta / Ratio_Val_geant_mat_X0_Eta), 0.5-wide eta bins:")
    edges = np.arange(-4.0, 4.01, 0.5)
    prof = {}
    for k in MAP:
        for lab, fn in (("geant", "material-map_mapped.root"), ("map", "propagation_material_regenerated.root")):
            t = uproot.open(MAP[k] / fn)["material_tracks"]
            arr = t.arrays(["v_eta", "t_X0"], library="np")
            e, x = arr["v_eta"], arr["t_X0"]
            s_, _ = np.histogram(e, edges, weights=x)
            n_, _ = np.histogram(e, edges)
            fine_e = np.arange(-4.0, 4.001, 0.05)
            fs, _ = np.histogram(e, fine_e, weights=x)
            fn_, _ = np.histogram(e, fine_e)
            prof[(k, lab)] = (s_ / np.maximum(n_, 1), n_, fs / np.maximum(fn_, 1))
    print(f"{'eta bin':>12s} | {'8q geant':>9s} {'8q map':>9s} {'map/g-1':>8s} | {'13 geant':>9s} {'13 map':>9s} "
          f"{'map/g-1':>8s} | {'geant 13/8q-1':>13s}")
    for i in range(len(edges) - 1):
        g8, m8 = prof[("8q", "geant")][0][i], prof[("8q", "map")][0][i]
        g13, m13 = prof[("13", "geant")][0][i], prof[("13", "map")][0][i]
        print(f"[{edges[i]:+.1f},{edges[i+1]:+.1f}) | {g8:9.4f} {m8:9.4f} {pct(g8, m8):+7.2f}% | {g13:9.4f} {m13:9.4f} "
              f"{pct(g13, m13):+7.2f}% | {pct(g8, g13):+12.2f}%")
    fine_c = 0.5 * (np.arange(-4.0, 4.001, 0.05)[1:] + np.arange(-4.0, 4.001, 0.05)[:-1])
    for lo, hi in ((1.0, 3.5), (-3.5, -1.0)):
        sel = (fine_c > lo) & (fine_c < hi)
        for k in MAP:
            r = prof[(k, "map")][2][sel] / prof[(k, "geant")][2][sel] - 1
            print(f"eta in ({lo:+.1f},{hi:+.1f}) {k:3s}: 0.05-bin map/geant - 1: mean {100*r.mean():+.2f}%, "
                  f"rms {100*r.std():.2f}%, max |.| {100*np.abs(r).max():.2f}%")
    print(f"tracks: " + ", ".join(f"{k} {lab} {prof[(k, lab)][1].sum()}" for k in MAP for lab in ("geant", "map")))


if __name__ == "__main__":
    main()
