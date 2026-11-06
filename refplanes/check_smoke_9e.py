#!/usr/bin/env python3
"""Step 9e smoke-test checks on the overlay npsim outputs (host, conda env 'tracking').

Reads sim_*.root in the smoke directory with the acceptance study's reader
(simrec/acc_study/mc_tracking_hits.py, imported read-only) and checks:
  A. SVTDiskRefPlaneHits exists (podio collection catalogue);
  B. every plane hit decodes to a known (system, layer) of plane_map.csv; |z - z_plane| <= 0.05 mm
     (slab half-thickness); r_in <= distance to the annulus centre <= r_out (v2 off-centre planes);
     eDep < 1e-12 GeV (Vacuum is not exactly empty);
  C. |p_hit| / |p_generated| for hits linked to the generated primary (generatorStatus == 1);
  D. MCParticle relation filled for every plane hit; fraction of plane hits linked to the primary
     (reported); attribution consistency: every primary-linked hit with |p_hit|/|p_gen| < 0.9 carries
     quality bit 30 (producedBySecondary, i.e. an unsaved secondary re-attributed to the primary);
  E. cross-check: primaries with >= 1 TrackerEndcapHits hit on a disk also have a plane hit there;
  F. number of plane hits per primary per plane (multiple crossings);
  G. npsim log: plane SDs have no filter, every other tracker SD keeps npsim's default filter;
     TrackerEndcapHits has no eDep == 0 hit.
Gates: A, B exact; C median ratio >= 0.99 and min ratio >= 0.95 for primary-linked hits WITHOUT the
producedBySecondary bit ("clean"); D relation valid for all hits + attribution consistency;
E >= 95 % of (primary, disk) silicon pairs matched; G exact. F is reported only.
Change from v1 (recorded in the log): v1 gated D on ">= 80 % of plane hits on the primary"; with no
filter the planes record every crossing particle incl. photons and neutrons, and two showering events
put one v1 file at 29.6 %. That number is now reported, not gated.
Usage: python3 check_smoke_9e.py SMOKE_DIR
"""
import csv
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "simrec" / "acc_study"))
from mc_tracking_hits import read_mc_tracking_hits  # noqa: E402

PLANES = "SVTDiskRefPlaneHits"
SILICON = "TrackerEndcapHits"
# silicon disk mapping (simrec/acc_study/README.md): (system, layer) -> disk
SILICON_DISKS = {(68, 1): "ED0", (69, 1): "ED1", (70, 2): "ED2", (70, 3): "ED3", (70, 4): "ED4",
                 (77, 1): "HD0", (78, 1): "HD1", (79, 2): "HD2", (79, 3): "HD3", (79, 4): "HD4"}
PRODUCED_BY_SECONDARY_BIT = 1 << 30

plane_map = {(int(r["system"]), int(r["layer"])): r for r in csv.DictReader(open(here / "plane_map.csv"))}
failures = []


def check(ok, msg):
    print(f"  [{'ok' if ok else 'FAIL'}] {msg}")
    if not ok:
        failures.append(msg)


def check_file(path):
    print(f"\n=== {path.name} ===")
    import uproot
    with uproot.open(path) as root:
        info = root["podio_metadata"]["events___CollectionTypeInfo"].array()[0]
        names = [str(n) for n in info[[f for f in info.fields if f.endswith("name")][0]]]
        n_events = root["events"].num_entries
    check(PLANES in names, f"A: {PLANES} in collections ({n_events} events)")
    if PLANES not in names:
        return None
    data = read_mc_tracking_hits(path, collections=[PLANES, SILICON], primary_only=False)
    parts, hits = data["particles"], data["hits"]
    key = ["event_entry", "mc_index"]
    prim = parts[parts.generator_status == 1].copy()
    p_gen = prim.set_index(key)["p_GeV"]

    ph = hits[hits.hit_collection == PLANES].copy()
    sh = hits[hits.hit_collection == SILICON].copy()
    # B. geometry of the plane hits
    ph["disk"] = [plane_map.get((int(s), int(l)), {}).get("disk", "?") for s, l in zip(ph.system, ph.layer)]
    check((ph.disk != "?").all(), f"B: all {len(ph)} plane hits map to plane_map.csv (unknown: {(ph.disk == '?').sum()})")
    zpl = np.array([float(plane_map[(int(s), int(l))]["z_plane_mm"]) for s, l in zip(ph.system, ph.layer)])
    col = lambda name: np.array([float(plane_map[(int(s), int(l))][name]) for s, l in zip(ph.system, ph.layer)])
    rin, rout, cx = col("r_inner_about_center_mm"), col("r_outer_about_center_mm"), col("center_x_mm")
    dz = np.abs(ph.z_mm.to_numpy() - zpl)
    rho = np.hypot(ph.x_mm.to_numpy() - cx, ph.y_mm.to_numpy())
    r = np.hypot(ph.x_mm, ph.y_mm).to_numpy()
    check(dz.max() <= 0.05 + 1e-6, f"B: max |z - z_plane| = {dz.max():.5f} mm (<= 0.05)")
    check(((rho >= rin - 1e-3) & (rho <= rout + 1e-3)).all(),
          f"B: r_in <= distance to annulus centre <= r_out for all hits (beam-axis r range {r.min():.2f}-{r.max():.2f} mm)")
    # ePIC 'Vacuum' has a tiny non-zero density, so eDep is ~1e-18 GeV rather than exactly 0
    check((ph.energy_deposit_GeV < 1e-12).all(), f"B: eDep < 1e-12 GeV (1 meV) for all plane hits "
          f"(max {ph.energy_deposit_GeV.max():.3g} GeV, exactly zero: {(ph.energy_deposit_GeV == 0).sum()}/{len(ph)})")
    if "path_length_mm" in ph:
        print(f"  info: plane-hit pathLength [mm] min/median/max = {ph.path_length_mm.min():.4f}/"
              f"{ph.path_length_mm.median():.4f}/{ph.path_length_mm.max():.4f}")

    # D. relation to primaries
    gs = parts.set_index(key)["generator_status"]
    ph_gs = gs.reindex(pd.MultiIndex.from_frame(ph[key])).to_numpy()
    on_primary = ph_gs == 1
    frac_primary = on_primary.mean() if len(ph) else 0.0
    check(len(ph) > 0 and np.isfinite(ph_gs.astype(float)).all(), "D: every plane hit has a valid MCParticle relation")
    print(f"  info D: {on_primary.sum()}/{len(ph)} = {frac_primary:.1%} of plane hits point to the generatorStatus==1 primary; "
          f"events with any non-primary plane hit: {ph[~on_primary].event_entry.nunique()}/{n_events}")
    php = ph[on_primary].copy()
    by_sec = (php.quality.astype(np.int64) & PRODUCED_BY_SECONDARY_BIT) != 0
    p_hit = np.sqrt(php.px_GeV ** 2 + php.py_GeV ** 2 + php.pz_GeV ** 2).to_numpy()
    ratio = p_hit / p_gen.reindex(pd.MultiIndex.from_frame(php[key])).to_numpy()
    low = ratio < 0.9
    check(bool(np.all(by_sec[low])), f"D: all {int(low.sum())} primary-linked hits with |p| ratio < 0.9 carry producedBySecondary "
          f"(bit set on {int(by_sec.sum())}/{len(php)} primary-linked hits)")
    # C. momentum, clean primary hits
    rc = ratio[~by_sec.to_numpy()]
    q = np.quantile(rc, [0.0, 0.01, 0.1, 0.5, 0.9, 1.0])
    check(np.median(rc) >= 0.99 and rc.min() >= 0.95,
          f"C: clean primary hits ({len(rc)}): |p_hit|/|p_gen| quantiles (0,1,10,50,90,100%) = " + ", ".join(f"{v:.4f}" for v in q))
    print(f"  info: clean hits with ratio > 1.0001: {(rc > 1.0001).sum()}")

    # F. multiple crossings (clean primary hits, and all primary-linked hits)
    print("  F: all primary-linked hits per (primary, plane): " + ", ".join(
        f"{k}x: {v}" for k, v in php.groupby(key + ["disk"]).size().value_counts().sort_index().items()))
    php = php[~by_sec.to_numpy()]
    per = php.groupby(key + ["disk"]).size()
    counts = per.value_counts().sort_index()
    print("  F: clean primary hits per (primary, plane): " + ", ".join(f"{k}x: {v}" for k, v in counts.items()))
    # E. silicon cross-check
    sh["disk"] = [SILICON_DISKS.get((int(s), int(l)), "?") for s, l in zip(sh.system, sh.layer)]
    sh_gs = gs.reindex(pd.MultiIndex.from_frame(sh[key])).to_numpy()
    si_pairs = set(map(tuple, sh[sh_gs == 1][key + ["disk"]].drop_duplicates().to_numpy().tolist()))
    pl_pairs = set(map(tuple, php[key + ["disk"]].drop_duplicates().to_numpy().tolist()))
    matched = len(si_pairs & pl_pairs)
    check(len(si_pairs) > 0 and matched / len(si_pairs) >= 0.95,
          f"E: (primary, disk) with silicon hit that also have a plane hit: {matched}/{len(si_pairs)}"
          f" = {matched / max(len(si_pairs), 1):.1%}")
    missing = sorted(si_pairs - pl_pairs)[:5]
    if missing:
        print(f"  info: first unmatched silicon pairs (event, mc_index, disk): {missing}")
    print(f"  info: (primary, disk) with plane hit but no silicon hit: {len(pl_pairs - si_pairs)}/{len(pl_pairs)}")
    check((sh.energy_deposit_GeV > 0).all(), f"G: TrackerEndcapHits all eDep > 0 (min {sh.energy_deposit_GeV.min():.3g} GeV, n={len(sh)})")
    return dict(file=path.name, events=n_events, plane_hits=len(ph), on_primary=int(on_primary.sum()),
                si_pairs=len(si_pairs), matched=matched, crossings=counts.to_dict())


def check_log(log):
    """G: filter assignment printed by DDSim Filter.applyFilters."""
    text = log.read_text(errors="replace")
    default = re.findall(r"Adding default filter '(\w+)' to sensitive detector for '(\w+)'", text)
    mapped = re.findall(r"Adding filter '(\w+)' matched with '(\w+)' to sensitive detector for '(\w+)'", text)
    nofilter = re.findall(r"Not adding any filter to sensitive detector for '(\w+)'", text)
    default_sd = {sd: f for f, sd in default}
    print(f"\n=== filter assignment in {log.name} ===")
    print(f"  default-filter SDs: {len(default_sd)} -> filters {sorted(set(default_sd.values()))}")
    print(f"  pattern-mapped: {mapped}")
    print(f"  no-filter messages: {nofilter}")
    check(not any("SVTDiskRefPlanes" in sd for sd in default_sd), "G: no default filter on SVTDiskRefPlanes SDs")
    endcap_sd = [sd for sd in default_sd if "TrackerEndcap" in sd]
    check(len(endcap_sd) == 6 and all(default_sd[sd] == "edep0" for sd in endcap_sd),
          f"G: the 6 SVT endcap SDs keep npsim's default filter: {[(sd, default_sd[sd]) for sd in endcap_sd]}")
    check(all(f == "edep0" for f in default_sd.values()), "G: every default-filtered SD uses edep0 (npsim default)")
    check(not any("SVTDiskRefPlanes" in m[2] for m in mapped), "G: no filter attached via pattern to plane SDs")
    names = ["SVTDiskRefPlanes" + s for s in ("P", "N", "HD2", "HD3", "HD4", "ED3", "ED4")]
    check(all(re.search(rf"\b{n}\b", text) for n in names), "G: all 7 plane SDs appear in the log")


def main():
    smoke = Path(sys.argv[1])
    summaries = []
    for path in sorted(smoke.glob("sim_*.root")):
        s = check_file(path)
        if s:
            summaries.append(s)
        check_log(path.with_suffix(".log"))
    print("\n=== summary ===")
    print(pd.DataFrame(summaries).to_string(index=False))
    print(f"\nStep 9e smoke checks: {'PASS' if not failures else 'FAIL (' + str(len(failures)) + ')'}")
    for f in failures:
        print("  failed:", f)
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
