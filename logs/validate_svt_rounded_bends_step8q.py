#!/usr/bin/env python3
"""Validate the Step 8q rounded corrugation bends (static, no DD4hep needed).

Convention (user decision 2026-11-05): the bend radius R = 5 mm is the radius
of the carbon mid-surface. The explicit table's flat_width_mm (10.65 / 12.15 mm)
is the sharp-corner width to the apex where the flat and web mid-surface lines
meet. At each flat/web join the builder trims T = R*tan(|alpha|/2) from the flat
and from the web and inserts a cylindrical shell sector with radii R -/+ t/2.

This script reproduces the C++ arithmetic of place_corrugated_frame and
place_bend from the production CSV and XML, then checks:
  1. source wiring (XML constant/attributes, C++ parser and builder);
  2. every join leaves a positive straight flat and straight web;
  3. each placed bend, using the exact C++ tube angles and the
     RotationZYX(0, pi/2, 0) mapping, is tangent to and shares its end faces
     with the neighbouring flat and web boxes, and lies beyond their end planes;
  4. the bend y footprint used for x clipping covers the actual sector;
  5. every delivered 2.5 mm glue strip lies fully on a straight flat;
and reports (not asserted) the inward keep-clear intrusion and carbon change.
"""

import csv
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CPP = ROOT / "src/SiEndcapModuleTracker_geo.cpp"
XML = ROOT / "compact/tracking/silicon_disks_modules.xml"
DELIVERY = ROOT / "compact/tracking/silicon_disks_tiling/20261001_ES"
LATTICE = DELIVERY / "SVT_endcap_corrugation_rows_33_36.csv"
SCENARIOS = ("rsu_opt", "all_6rsu")
DISKS = ("ED4", "ED3", "ED2", "ED1", "ED0", "HD0", "HD1", "HD2", "HD3b", "HD4")
MODULE_WIDTH_MM = {"A": 35.0, "B": 32.0}
KEEP_CLEAR_MM = {"A": (21.94, 1.00), "B": (20.56, 1.00)}  # width x depth, source slide
GLUE_WIDTH_MM = 2.5
TOL = 1.0e-9  # mm, same dimensional tolerance as the C++ guard
GEOM_TOL = 1.0e-9


def xml_constant(name):
    """Evaluate a simple '<number>*mm' or '<number>*deg' XML constant in mm / rad."""
    text = XML.read_text()
    match = re.search(rf'<constant name="{name}"\s+value="([^"]+)"', text)
    assert match, f"missing XML constant {name}"
    expression = match.group(1).replace("mm", "1.0").replace("deg", f"{math.pi / 180.0!r}")
    return float(eval(expression, {"__builtins__": {}}))


def check_sources():
    xml_text = XML.read_text()
    cpp_text = CPP.read_text()
    frames = xml_text.count('type="corrugated"')
    attrs = xml_text.count('bend_radius="SiEndcapCorrugation_bend_radius"')
    assert frames == 10 and attrs == 10, (frames, attrs)
    for needle in (
        "_Unicode(bend_radius)",
        "auto place_bend = [&]",
        "Tube bend_solid(r_inner, r_outer, x_half, phi_start, phi_end);",
        "Transform3D(RotationZYX(0.0, M_PI / 2.0, 0.0),",
        "join.tangent_length = config.bend_radius * std::tan(std::abs(join.web_angle) / 2.0);",
        '-web_sign * M_PI / 2.0, join.web_angle);',
        'web_sign * M_PI / 2.0, join.web_angle);',
    ):
        assert needle in cpp_text, f"C++ source missing: {needle}"
    print(f"sources: {frames} corrugated frames, {attrs} carry bend_radius; C++ bend builder present")


def load_flats():
    by_disk = defaultdict(list)
    with LATTICE.open(newline="") as stream:
        for row in csv.DictReader(stream):
            by_disk[row["disk"]].append(
                {
                    "row_index": int(row["row_index"]),
                    "y": float(row["row_y_mm"]),
                    "offset": float(row["surface_offset_mm"]),
                    "family": row["family"],
                    "width": float(row["flat_width_mm"]),
                }
            )
    for rows in by_disk.values():
        rows.sort(key=lambda r: r["y"])  # C++ sorts explicit flats by increasing y
    return by_disk


def build_profile(flats, h, t, theta, radius):
    """Reproduce the C++ explicit-flat construction (y0 = z_center_offset = 0)."""
    web_y_span = (h - t) / math.tan(theta)
    z = [f["offset"] - math.copysign(t / 2.0, f["offset"]) for f in flats]
    joins = []
    trim_low = [0.0] * len(flats)
    trim_high = [0.0] * len(flats)
    for i in range(len(flats) - 1):
        left = flats[i]["y"] + flats[i]["width"] / 2.0
        right = flats[i + 1]["y"] - flats[i + 1]["width"] / 2.0
        gap = right - left
        assert gap + TOL >= web_y_span, "insufficient space for a web"
        if radius > 0.0:
            assert gap - web_y_span <= TOL, "web does not close the gap"
        angle = math.atan2(z[i + 1] - z[i], web_y_span)
        length = math.hypot(web_y_span, z[i + 1] - z[i])
        tangent = radius * math.tan(abs(angle) / 2.0)
        assert length - 2.0 * tangent > TOL, "no straight web"
        trim_high[i] = tangent
        trim_low[i + 1] = tangent
        joins.append(dict(i=i, left=left, right=right, angle=angle, length=length, T=tangent))
    straight = []
    for i, f in enumerate(flats):
        width = f["width"] - trim_low[i] - trim_high[i]
        assert width > TOL, "no straight flat"
        centre = f["y"] + (trim_low[i] - trim_high[i]) / 2.0
        straight.append((centre - width / 2.0, centre + width / 2.0, z[i]))
    return z, joins, straight


def cpp_bend(y_c, z_c, psi_start, psi_delta):
    """Tube angles exactly as place_bend computes them."""
    psi_low = min(psi_start, psi_start + psi_delta)
    psi_high = max(psi_start, psi_start + psi_delta)
    phi_start = math.fmod(psi_low + math.pi / 2.0, 2.0 * math.pi)
    if phi_start < 0.0:
        phi_start += 2.0 * math.pi
    return phi_start, phi_start + (psi_high - psi_low), psi_low, psi_high


def tube_point(y_c, z_c, r, phi):
    """Local tube point (r cos phi, r sin phi, 0) after RotationY(+90 deg): (x,y,z)->(z,y,-x)."""
    return (y_c + r * math.sin(phi), z_c - r * math.cos(phi))


def close(p, q, tol=GEOM_TOL):
    return abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol


def check_bend(y_c, z_c, psi_start, psi_delta, R, t, flat_end, flat_dir, web_end, web_dir):
    """flat_end/web_end: mid-surface tangent points; *_dir: unit vectors pointing INTO the bend."""
    phi_a, phi_b, psi_low, psi_high = cpp_bend(y_c, z_c, psi_start, psi_delta)
    ends = [tube_point(y_c, z_c, R, phi_a), tube_point(y_c, z_c, R, phi_b)]
    # Each tube end must coincide with one of the two tangent points.
    matched = {0: None, 1: None}
    for k, end in enumerate(ends):
        if close(end, flat_end):
            matched[k] = "flat"
        elif close(end, web_end):
            matched[k] = "web"
    assert sorted(v or "" for v in matched.values()) == ["flat", "web"], (ends, flat_end, web_end)
    for k, phi in ((0, phi_a), (1, phi_b)):
        point, direction = (flat_end, flat_dir) if matched[k] == "flat" else (web_end, web_dir)
        # Tangency: arc tangent (cos phi, sin phi) in global (y,z) is parallel to the piece axis.
        tangent = (math.cos(phi), math.sin(phi))
        assert abs(tangent[0] * direction[1] - tangent[1] * direction[0]) < 1e-9
        # Shared end face: tube edge points at R -/+ t/2 equal the box end-face corners.
        normal = (-direction[1], direction[0])
        corners = [(point[0] + s * t / 2 * normal[0], point[1] + s * t / 2 * normal[1]) for s in (-1, 1)]
        for r in (R - t / 2.0, R + t / 2.0):
            edge = tube_point(y_c, z_c, r, phi)
            assert any(close(edge, c) for c in corners), (edge, corners)
    # Material lies beyond both end planes (no interpenetration with the boxes).
    samples = []
    for n in range(41):
        phi = phi_a + (phi_b - phi_a) * n / 40
        for r in (R - t / 2.0, R, R + t / 2.0):
            samples.append(tube_point(y_c, z_c, r, phi))
    for point, direction in ((flat_end, flat_dir), (web_end, web_dir)):
        for s in samples:
            assert (s[0] - point[0]) * direction[0] + (s[1] - point[1]) * direction[1] >= -1e-9
    # Footprint used for x clipping (C++ logic) covers the sampled sector.
    y_vals = [y_c + r * math.cos(p) for p in (psi_low, psi_high) for r in (R - t / 2, R + t / 2)]
    for k in range(-2, 3):
        if psi_low < k * math.pi < psi_high:
            y_vals.append(y_c + (R + t / 2) * math.cos(k * math.pi))
    y_min, y_max = min(y_vals), max(y_vals)
    assert all(y_min - 1e-9 <= s[0] <= y_max + 1e-9 for s in samples)
    return samples


def carbon_points(flats, z, joins, straight, R, t, step=0.02):
    """Skin-face sample points of the whole profile (for the keep-clear audit)."""
    pts = []
    for y0, y1, zc in straight:
        n = max(2, int((y1 - y0) / step))
        for k in range(n + 1):
            y = y0 + (y1 - y0) * k / n
            pts += [(y, zc - t / 2), (y, zc + t / 2)]
    for j in joins:
        a, T = j["angle"], j["T"]
        d = (math.cos(a), math.sin(a))
        nrm = (-d[1], d[0])
        start = (j["left"] + T * d[0], z[j["i"]] + T * d[1])
        L = j["length"] - 2 * T
        n = max(2, int(L / step))
        for k in range(n + 1):
            c = (start[0] + d[0] * L * k / n, start[1] + d[1] * L * k / n)
            pts += [(c[0] + s * t / 2 * nrm[0], c[1] + s * t / 2 * nrm[1]) for s in (-1, 1)]
        if T > 0:
            sgn = 1.0 if a > 0 else -1.0
            for y_c, z_c, ps in ((j["left"] - T, z[j["i"]] + sgn * R, -sgn * math.pi / 2),
                                 (j["right"] + T, z[j["i"] + 1] - sgn * R, sgn * math.pi / 2)):
                pa, pb, _, _ = cpp_bend(y_c, z_c, ps, a)
                for k in range(61):
                    phi = pa + (pb - pa) * k / 60
                    pts += [tube_point(y_c, z_c, r, phi) for r in (R - t / 2, R + t / 2)]
    return pts


def main():
    check_sources()
    h = xml_constant("SiEndcapCorrugation_h")
    t = xml_constant("SiEndcapCorrugationCF_thickness")
    theta = xml_constant("SiEndcapCorrugation_theta")
    R = xml_constant("SiEndcapCorrugation_bend_radius")
    print(f"XML: h={h:.3f} mm, t={t:.3f} mm, theta={math.degrees(theta):.1f} deg, R(mid)={R:.3f} mm")
    assert abs(R - 5.0) < 1e-12

    by_disk = load_flats()
    total_bends = 0
    width_by_family = defaultdict(set)
    web_straight = set()
    profiles = {}
    for disk in DISKS:
        flats = by_disk[disk]
        z, joins, straight = build_profile(flats, h, t, theta, R)
        z0, joins0, straight0 = build_profile(flats, h, t, theta, 0.0)
        # R = 0 regression: no trims, the original sharp pieces.
        assert all(j["T"] == 0.0 for j in joins0)
        assert all(abs((s[1] - s[0]) - f["width"]) < 1e-12 for s, f in zip(straight0, flats))
        for f, s in zip(flats, straight):
            width_by_family[f["family"]].add(round(s[1] - s[0], 6))
        for j in joins:
            if j["T"] == 0.0:
                continue
            a, T = j["angle"], j["T"]
            d = (math.cos(a), math.sin(a))
            sgn = 1.0 if a > 0 else -1.0
            i = j["i"]
            web_straight.add(round(j["length"] - 2 * T, 6))
            # low bend: flat i (direction +y into the bend), web start (direction -d into the bend)
            flat_end = (j["left"] - T, z[i])
            web_start = (j["left"] + T * d[0], z[i] + T * d[1])
            assert close(flat_end, (straight[i][1], z[i]))
            check_bend(j["left"] - T, z[i] + sgn * R, -sgn * math.pi / 2, a, R, t,
                       flat_end, (1.0, 0.0), web_start, (-d[0], -d[1]))
            # high bend: web end (direction +d into the bend), flat i+1 (direction -y into the bend)
            flat_end = (j["right"] + T, z[i + 1])
            web_end = (j["right"] - T * d[0], z[i + 1] - T * d[1])
            assert close(flat_end, (straight[i + 1][0], z[i + 1]))
            check_bend(j["right"] + T, z[i + 1] - sgn * R, sgn * math.pi / 2, a, R, t,
                       flat_end, (-1.0, 0.0), web_end, d)
            total_bends += 2
        profiles[disk] = (flats, z, joins, straight, joins0, straight0)
        central_webs = sum(1 for j in joins if abs((j["left"] + j["right"]) / 2.0) < 1e-6)
        print(f"{disk:5s}: flats={len(flats):2d} webs={len(joins):2d} bends={2 * sum(j['T'] > 0 for j in joins):2d}"
              f"  (web centred on y=0: {central_webs})")
    print(f"bends before x-interval splitting: {total_bends}")
    print("straight flat widths [mm]:", {k: sorted(v) for k, v in width_by_family.items()})
    print("straight web lengths [mm]:", sorted(web_straight))
    print("PASS: every bend is tangent to, and shares end faces with, its flat and web boxes")

    # Glue strips on straight flats.
    for scenario in SCENARIOS:
        strips, minimum_margin = 0, float("inf")
        for disk in DISKS:
            flats, z, joins, straight, _, _ = profiles[disk]
            with (DELIVERY / scenario / f"{disk}_modules.csv").open(newline="") as stream:
                modules = list(csv.DictReader(stream))
            zs = [float(m["z_baseplate_mm"]) for m in modules]
            centre = (min(zs) + max(zs)) / 2.0
            for m in modules:
                fam = m["type_id"][0]
                y = float(m["y_origin_mm"])
                surface = float(m["z_baseplate_mm"]) - centre
                half = MODULE_WIDTH_MM[fam] / 2.0
                for g0, g1 in ((y - half, y - half + GLUE_WIDTH_MM), (y + half - GLUE_WIDTH_MM, y + half)):
                    strips += 1
                    best = -float("inf")
                    for f, (s0, s1, _) in zip(flats, straight):
                        if abs(f["offset"] - surface) > 1e-9:
                            continue
                        best = max(best, min(g0 - s0, s1 - g1))  # >= 0: strip fully on the straight flat
                    minimum_margin = min(minimum_margin, best)
        print(f"{scenario}: glue strips={strips}, minimum margin to straight-flat edge = {minimum_margin:.4f} mm")
        assert minimum_margin >= 0.0, "a glue strip extends onto a bend"
    print("PASS: every glue strip lies fully on a straight flat")

    # Informational: inward keep-clear intrusion and carbon change (not asserted).
    print("INFO keep-clear (box = source width x 1 mm below the module surface, centred on module y):")
    for scenario in ("rsu_opt",):
        for label, use_round in (("rounded R=5", True), ("sharp (Step 8i)", False)):
            worst = defaultdict(float)
            n_intruded = defaultdict(int)
            n_modules = defaultdict(int)
            worst_offset = defaultdict(float)
            for disk in DISKS:
                flats, z, joins, straight, joins0, straight0 = profiles[disk]
                pts = (carbon_points(flats, z, joins, straight, R, t) if use_round
                       else carbon_points(flats, z, joins0, straight0, 0.0, t))
                with (DELIVERY / scenario / f"{disk}_modules.csv").open(newline="") as stream:
                    modules = list(csv.DictReader(stream))
                zs = [float(m["z_baseplate_mm"]) for m in modules]
                centre = (min(zs) + max(zs)) / 2.0
                for m in modules:
                    fam = m["type_id"][0]
                    n_modules[fam] += 1
                    y = float(m["y_origin_mm"])
                    s = 1.0 if float(m["z_baseplate_mm"]) - centre > 0 else -1.0
                    # module offset from its channel centre (nearest opposite-surface flat)
                    channel = min((f for f in flats if f["offset"] * s < 0), key=lambda f: abs(f["y"] - y))
                    worst_offset[fam] = max(worst_offset[fam], abs(y - channel["y"]))
                    width, depth = KEEP_CLEAR_MM[fam]
                    z_face = s * h / 2.0
                    z_lo, z_hi = sorted((z_face, z_face - s * depth))
                    depth_in = 0.0
                    for py, pz in pts:
                        if z_lo + 1e-6 < pz < z_hi - 1e-6 and abs(py - y) < width / 2.0:
                            depth_in = max(depth_in, width / 2.0 - abs(py - y))
                    if depth_in > 0.0:
                        n_intruded[fam] += 1
                    worst[fam] = max(worst[fam], depth_in)
            for fam in sorted(n_modules):
                print(f"  {scenario} {label:16s} {fam}: modules with carbon in box = "
                      f"{n_intruded[fam]}/{n_modules[fam]}, worst y intrusion = {worst[fam]:.3f} mm "
                      f"(max module offset from channel centre {worst_offset[fam]:.3f} mm)")
    sharp_len = round_len = 0.0
    for disk in DISKS:
        flats, z, joins, straight, joins0, straight0 = profiles[disk]
        sharp_len += sum(s[1] - s[0] for s in straight0) + sum(j["length"] for j in joins0)
        round_len += (sum(s[1] - s[0] for s in straight)
                      + sum(j["length"] - 2 * j["T"] + 2 * R * abs(j["angle"]) for j in joins))
    print(f"INFO mid-surface carbon length (all disks, per unit x): rounded/sharp = {round_len / sharp_len:.4f}")
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
