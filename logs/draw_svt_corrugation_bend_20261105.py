#!/usr/bin/env python3
"""To-scale sketch of the proposed rounded corrugation bend (33 mm B row).

Coordinates: y = across rows (horizontal), z = disk normal (vertical), mm.
Convention (proposed): bend radius R on the carbon mid-surface; CSV
flat_width_mm (10.65 mm) is the sharp-corner width to the flat/web line
intersection ("apex"); each web-joined flat end is trimmed by T = R tan(alpha/2).
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Rectangle

h, t, R = 6.0, 0.15, 5.0
alpha = math.radians(45.0)            # web deflection angle w.r.t. the flat
pitch = 33.0
half = pitch / 2.0
zm = h / 2 - t / 2                    # mid-surface z of the +side flats (2.925)
dz = 2 * zm                           # mid-surface separation (5.85)
w_sharp = half - dz / math.tan(alpha) # 10.65
T = R * math.tan(alpha / 2)           # 2.071
w_flat = w_sharp - 2 * T              # 6.508
web_len = dz / math.sin(alpha)        # 8.273

def profile(y0_top, direction):
    """Mid-surface of top flat (centre y0_top, z=+zm) -> bend -> web -> bend -> bottom flat.
    direction=+1 goes to +y, -1 to -y. Returns (sharp, rounded) polylines and key points."""
    s = direction
    apex_top = (y0_top + s * w_sharp / 2, zm)
    apex_bot = (y0_top + s * (half - w_sharp / 2), -zm)
    sharp = [(y0_top, zm), apex_top, apex_bot, (y0_top + s * half, -zm)]
    # top bend: centre below the flat end
    tp1 = (apex_top[0] - s * T, zm)
    c_top = (tp1[0], zm - R)
    # bottom bend: centre above the bottom flat start
    tp4 = (apex_bot[0] + s * T, -zm)
    c_bot = (tp4[0], -zm + R)
    rounded = [(y0_top, zm), tp1]
    for k in range(31):
        phi = alpha * k / 30
        rounded.append((c_top[0] + s * R * math.sin(phi), c_top[1] + R * math.cos(phi)))
    tp2 = rounded[-1]
    arc_b = []
    for k in range(31):
        phi = alpha * (1 - k / 30)
        arc_b.append((c_bot[0] - s * R * math.sin(phi), c_bot[1] - R * math.cos(phi)))
    tp3 = arc_b[0]
    rounded += arc_b + [tp4, (y0_top + s * half, -zm)]
    return sharp, rounded, dict(apex_top=apex_top, apex_bot=apex_bot, tp1=tp1, tp2=tp2,
                                tp3=tp3, tp4=tp4, c_top=c_top, c_bot=c_bot)

def offset(poly, d):
    """Parallel offset of a polyline by d (left normal), for drawing the skin faces."""
    out = []
    for i, (y, z) in enumerate(poly):
        a = poly[max(i - 1, 0)]; b = poly[min(i + 1, len(poly) - 1)]
        ty, tz = b[0] - a[0], b[1] - a[1]
        n = math.hypot(ty, tz) or 1.0
        out.append((y - d * tz / n, z + d * ty / n))
    return out

def draw_skin(ax, poly, color, label=None):
    up, dn = offset(poly, t / 2), offset(poly, -t / 2)
    ys = [p[0] for p in up] + [p[0] for p in dn[::-1]]
    zs = [p[1] for p in up] + [p[1] for p in dn[::-1]]
    ax.fill(ys, zs, color=color, lw=0, label=label)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.0), gridspec_kw=dict(width_ratios=[1.5, 1]))

# ---------- panel (a): one full 33 mm period, module on the +z face ----------
ax = ax1
for direction in (+1, -1):
    for y0 in (-half, half):
        if (y0 > 0 and direction > 0) or (y0 < 0 and direction < 0):
            continue
        sharp, rounded, P = profile(y0, direction)
        ax.plot(*zip(*sharp), "--", color="0.55", lw=1.0,
                label="current sharp model (mid-surface)" if (direction, y0) == (1, -half) else None)
        draw_skin(ax, rounded, "tab:blue",
                  label="proposed rounded carbon (t = 0.15 mm)" if (direction, y0) == (1, -half) else None)
# central bottom flat (y = 0) and the two top flats at +/- 16.5
ax.axhline(h / 2, color="0.8", lw=0.6); ax.axhline(-h / 2, color="0.8", lw=0.6)
mod_w = 32.0
ax.add_patch(Rectangle((-mod_w / 2, h / 2 + 0.08), mod_w, 0.15, color="tab:green", alpha=0.6,
                       label="module baseplate (32 mm, on +z face)"))
for yg in (-mod_w / 2, mod_w / 2 - 2.5):
    ax.add_patch(Rectangle((yg, h / 2), 2.5, 0.08, color="tab:red", label="2.5 mm glue lines" if yg < 0 else None))
ax.add_patch(Rectangle((-20.56 / 2, h / 2 - 1.0), 20.56, 1.0, fill=False, ec="tab:orange", lw=1.2, ls=":",
                       label="inward keep-clear 20.56 x 1.00 mm"))
# dimensions
def dim(ax, y1, y2, z, text, dzt=0.25):
    ax.annotate("", (y1, z), (y2, z), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text((y1 + y2) / 2, z + dzt, text, ha="center", va="bottom", fontsize=9)
dim(ax, -half, half, h / 2 + 1.6, f"pitch = {pitch:.0f} mm (same-surface flat centres)")
dim(ax, -w_flat / 2, w_flat / 2, -h / 2 - 1.2, f"straight flat {w_flat:.3f}", -0.75)
dim(ax, -w_sharp / 2, w_sharp / 2, -h / 2 - 2.6, f"CSV sharp width {w_sharp:.2f} (to apexes)", -0.75)
ax.annotate("", (19.5, -h / 2), (19.5, h / 2), arrowprops=dict(arrowstyle="<->", lw=0.8))
ax.text(19.8, 0, f"h = {h:.0f} mm\n(outer faces)", va="center", fontsize=9)
ax.text(-16.5, h / 2 - 0.55, "+z flat", ha="center", fontsize=8, color="tab:blue")
ax.text(0, -h / 2 + 0.35, "-z flat (channel centre)", ha="center", fontsize=8, color="tab:blue")
ax.set_xlim(-22, 24); ax.set_ylim(-7.0, 6.3); ax.set_aspect("equal")
ax.set_xlabel("y across rows [mm]"); ax.set_ylabel("z normal to disk [mm]")
ax.set_title("(a) one 33 mm (B) period, to scale")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=8.5, ncol=3)

# ---------- panel (b): zoom on one top bend ----------
ax = ax2
sharp, rounded, P = profile(-half, +1)
ax.plot(*zip(*sharp), "--", color="0.55", lw=1.0, label="sharp model")
draw_skin(ax, rounded, "tab:blue", label="rounded skin, radii R ± t/2")
ax.plot(*zip(*rounded), color="navy", lw=0.6, label="mid-surface")
A, C, t1, t2 = P["apex_top"], P["c_top"], P["tp1"], P["tp2"]
for p, name, dy, dzz in ((A, "apex", 0.15, 0.25), (C, "bend centre", -1.9, -0.45),
                         (t1, "tangent pt 1", -1.9, -0.35), (t2, "tangent pt 2", 0.25, 0.0)):
    ax.plot(*p, "ko", ms=3.5); ax.text(p[0] + dy, p[1] + dzz, name, fontsize=8.5)
# R: radii to both tangent points
ax.plot([C[0], t1[0]], [C[1], t1[1]], color="tab:purple", lw=1)
ax.plot([C[0], t2[0]], [C[1], t2[1]], color="tab:purple", lw=1)
ax.text(C[0] - 0.55, (C[1] + t1[1]) / 2, "R = 5", color="tab:purple", fontsize=10, rotation=90, va="center")
# bisector centre -> apex, alpha/2 angle at centre
ax.plot([C[0], A[0]], [C[1], A[1]], ":", color="tab:purple", lw=1)
ax.add_patch(Arc(C, 2.2, 2.2, theta1=90 - math.degrees(alpha), theta2=90, color="tab:purple"))
ax.text(C[0] + 0.75, C[1] + 0.75, "α", color="tab:purple", fontsize=11)
ax.add_patch(Arc(C, 3.6, 3.6, theta1=90 - math.degrees(alpha) / 2, theta2=90, color="tab:brown"))
ax.text(C[0] + 0.25, C[1] + 1.95, "α/2", color="tab:brown", fontsize=10)
# alpha at apex: between flat extension and web
ext = (A[0] + 2.0, A[1])
ax.plot([A[0], ext[0]], [A[1], ext[1]], ":", color="0.4", lw=0.8)
ax.add_patch(Arc(A, 2.4, 2.4, theta1=-math.degrees(alpha), theta2=0, color="tab:red"))
ax.text(A[0] + 1.3, A[1] - 0.55, "α = 45°", color="tab:red", fontsize=10)
# T along the flat and along the web
ax.annotate("", t1, A, arrowprops=dict(arrowstyle="<->", color="tab:green", lw=1.2))
ax.text((t1[0] + A[0]) / 2, A[1] + 0.18, f"T = {T:.3f}", color="tab:green", ha="center", fontsize=10)
ax.annotate("", A, t2, arrowprops=dict(arrowstyle="<->", color="tab:green", lw=1.2))
ax.text((A[0] + t2[0]) / 2 + 0.25, (A[1] + t2[1]) / 2 + 0.1, "T", color="tab:green", fontsize=10)
sag = R * (1 / math.cos(alpha / 2) - 1)
ax.text(C[0] + 0.6, -5.3,
        f"arc angle at centre = deflection α\nT = R·tan(α/2) = {T:.3f} mm\n"
        f"arc length = R·α = {R * alpha:.3f} mm (< 2T = {2 * T:.3f})\n"
        f"apex-to-arc gap = R(1/cos(α/2) − 1) = {sag:.3f} mm\n"
        f"straight flat = {w_sharp:.2f} − 2T = {w_flat:.3f} mm\n"
        f"straight web = {web_len:.3f} − 2T = {web_len - 2 * T:.3f} mm",
        fontsize=8.5, family="monospace", bbox=dict(fc="white", ec="0.7"))
ax.set_xlim(t1[0] - 2.2, A[0] + 3.4); ax.set_ylim(-5.5, h / 2 + 0.7); ax.set_aspect("equal")
ax.set_xlabel("y [mm]"); ax.set_title("(b) zoom: one +z bend (B row, mid-surface R)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=8.5, ncol=3)

fig.tight_layout()
out = __file__.replace(".py", ".png")
fig.savefig(out, dpi=160)
print(out)
