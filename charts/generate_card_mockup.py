#!/usr/bin/env python3
"""Pokemon-card-style mockup of a single model card.

Static sketch. Matches 1999 Wizards Base Set layout closely. The art
slot is a stylized lab-monogram + holo treatment (matplotlib cannot paint
a real Mitsuhiro Arita illustration — for that, run the design prompt
through an image generator and composite the result into the art panel).

Slot map (Pokemon -> model card):
  Stage badge / Evolves-from   ->  generation + previous gen
  HP                            ->  word count
  Type icon                     ->  dominant eval type (R/C/M/S)
  Art                           ->  stylized lab monogram with holo
  Descriptor ribbon             ->  "Frontier Gen Model. Length: Xk. Weight: N evals."
  Attacks                       ->  headline benchmarks with score
  Weakness / Resistance         ->  weakest / strongest safety category
  Retreat cost                  ->  uniqueness orbs
  Flavor text                   ->  one-liner summary
  LV / number                   ->  generation level / set position
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, Wedge
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

OUT = Path(__file__).parent / "card_mockup_opus46.png"

# ---- Card data (would normally come from the API) ----
CARD = {
    "name":          "Claude Opus 4.6",
    "lab":           "Anthropic",
    "stage":         "STAGE 4",
    "evolves_from":  "Evolves from Claude Opus 4.5",
    "stage_hint":    "Put Opus 4.6 on the Stage 3 card",
    "hp":            "47k",
    "hp_unit":       "WC",
    "type":          "R",
    "descriptor":    "Frontier Gen Model.  Length: 47k words.  Weight: 18 evals.",
    "attacks": [
        {"cost": ["R"],      "name": "MMLU",      "score": "89.4",
         "desc": "Tests broad academic reasoning across 57 subjects."},
        {"cost": ["R", "C"], "name": "SWE-bench", "score": "67.1",
         "desc": "Resolves real GitHub issues in production codebases."},
    ],
    "weakness":      ("C", "x2"),
    "resistance":    ("S", "-12"),
    "retreat":       1,
    "flavor":        ("18 benchmarks reported. 73% lab-unique — most "
                      "of its eval choices are not echoed by peer labs."),
    "level":         "LV.46",
    "number":        "47/50",
}

# ---- Style ----
LAB_COLOR       = "#D4732A"   # Anthropic coral
LAB_COLOR_DARK  = "#8B4A1A"
LAB_COLOR_LIGHT = "#F4B27D"
CARD_YELLOW     = "#F1CB47"   # outer Pokemon yellow
CARD_INNER      = "#F7E59B"   # inner cream panel
GOLD            = "#C7A040"
GOLD_DARK       = "#8B6F1A"
INK             = "#1B1816"
RIBBON          = "#F5D78A"
HP_RED          = "#B83228"

TYPE_COLORS = {
    "R": ("#7F5AB8", "#3D2862"),
    "C": ("#5C8C3F", "#2D4A1B"),
    "M": ("#3F8DB0", "#1F4A5C"),
    "S": ("#C8423B", "#6E1F1A"),
}

# ---- Canvas ----
W_IN, H_IN = 5.0, 7.0
fig = plt.figure(figsize=(W_IN, H_IN), dpi=240, facecolor="#1F1F1F")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

# ---- Outer yellow border ----
ax.add_patch(FancyBboxPatch(
    (0.012, 0.010), 0.976, 0.980,
    boxstyle="round,pad=0,rounding_size=0.030",
    linewidth=0, facecolor=CARD_YELLOW, zorder=1))
# Subtle inner edge bevel
ax.add_patch(FancyBboxPatch(
    (0.020, 0.018), 0.960, 0.964,
    boxstyle="round,pad=0,rounding_size=0.025",
    linewidth=1.5, edgecolor=GOLD_DARK, facecolor="none", zorder=2))

# ---- Inner cream panel ----
PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 0.062, 0.046, 0.876, 0.908
ax.add_patch(FancyBboxPatch(
    (PANEL_X, PANEL_Y), PANEL_W, PANEL_H,
    boxstyle="round,pad=0,rounding_size=0.012",
    linewidth=0.6, edgecolor=GOLD_DARK, facecolor=CARD_INNER, zorder=3))

# ---- Top strip: stage badge + evolves-from + stage hint ----
strip_y = 0.935
# Stage badge box
badge_x, badge_w = 0.085, 0.082
ax.add_patch(Rectangle((badge_x, strip_y - 0.012), badge_w, 0.026,
                        facecolor="none", edgecolor=INK, linewidth=0.6,
                        zorder=4))
ax.text(badge_x + badge_w / 2, strip_y, CARD["stage"], fontsize=7.2,
        fontweight="bold", color=INK, ha="center", va="center",
        family="serif", zorder=5)
ax.text(0.180, strip_y, CARD["evolves_from"], fontsize=7,
        color=INK, family="serif", style="italic", va="center", zorder=4)
ax.text(0.915, strip_y, CARD["stage_hint"], fontsize=5.5,
        color=INK, family="serif", ha="right", va="center", zorder=4)

# ---- Name + HP + Type ----
name_y = 0.890
ax.text(0.092, name_y, CARD["name"], fontsize=15, fontweight="bold",
        color=INK, family="serif", va="center", zorder=4)

# HP — right-aligned with type icon to its right
hp_str = f"{CARD['hp']} HP"
ax.text(0.840, name_y, hp_str, fontsize=15, fontweight="bold",
        color=HP_RED, family="serif", ha="right", va="center", zorder=4)
# Type icon
t_fc, t_ec = TYPE_COLORS[CARD["type"]]
ax.add_patch(Circle((0.885, name_y), 0.020, facecolor=t_fc,
                     edgecolor=t_ec, linewidth=1.2, zorder=5))
ax.text(0.885, name_y, CARD["type"], fontsize=10, fontweight="bold",
        color="white", ha="center", va="center", zorder=6)

# ---- Art frame ----
ART_X, ART_Y, ART_W, ART_H = 0.105, 0.490, 0.790, 0.370
# Outer gold double-frame
ax.add_patch(Rectangle((ART_X - 0.014, ART_Y - 0.014),
                        ART_W + 0.028, ART_H + 0.028,
                        facecolor=GOLD, zorder=4))
ax.add_patch(Rectangle((ART_X - 0.006, ART_Y - 0.006),
                        ART_W + 0.012, ART_H + 0.012,
                        facecolor="#F0D078", edgecolor=GOLD_DARK,
                        linewidth=0.8, zorder=5))
# Art canvas — radial gradient simulation via concentric rounded rects
ax.add_patch(Rectangle((ART_X, ART_Y), ART_W, ART_H,
                        facecolor="#FFE9B8", zorder=6))
# Layered subtle gradient (cheap radial fake)
for i, (alpha, scale) in enumerate(zip([0.18, 0.14, 0.10, 0.06],
                                         [0.60, 0.45, 0.30, 0.16])):
    cx, cy = ART_X + ART_W / 2, ART_Y + ART_H * 0.45
    rw = ART_W * scale; rh = ART_H * scale
    ax.add_patch(Rectangle((cx - rw / 2, cy - rh / 2), rw, rh,
                            facecolor=LAB_COLOR_LIGHT, alpha=alpha,
                            zorder=7 + i))

# HOLO starburst rays (white, low alpha) emanating from center
np.random.seed(7)
center_x, center_y = ART_X + ART_W / 2, ART_Y + ART_H * 0.50
n_rays = 22
for i in range(n_rays):
    angle = 2 * np.pi * i / n_rays + np.random.uniform(-0.05, 0.05)
    length = ART_H * np.random.uniform(0.45, 0.62)
    x2 = center_x + np.cos(angle) * length
    y2 = center_y + np.sin(angle) * length
    ax.add_line(Line2D([center_x, x2], [center_y, y2],
                        color="white", alpha=0.25,
                        linewidth=np.random.uniform(0.6, 1.6), zorder=12))

# Sparkle stars (small white plus signs)
for _ in range(28):
    sx = ART_X + 0.05 + np.random.random() * (ART_W - 0.10)
    sy = ART_Y + 0.05 + np.random.random() * (ART_H - 0.10)
    s = np.random.uniform(0.004, 0.010)
    ax.add_line(Line2D([sx - s, sx + s], [sy, sy], color="white",
                        alpha=np.random.uniform(0.4, 0.8),
                        linewidth=0.5, zorder=13))
    ax.add_line(Line2D([sx, sx], [sy - s, sy + s], color="white",
                        alpha=np.random.uniform(0.4, 0.8),
                        linewidth=0.5, zorder=13))

# Big stylized lab monogram "A" (the "creature")
ax.text(center_x, center_y - ART_H * 0.04, "A", fontsize=170,
        fontweight="bold", color=LAB_COLOR,
        ha="center", va="center", family="serif", zorder=14,
        path_effects=[pe.withStroke(linewidth=5, foreground=LAB_COLOR_DARK)])

# Floating benchmark glyphs around the monogram
np.random.seed(3)
for _ in range(14):
    angle = np.random.uniform(0, 2 * np.pi)
    r = np.random.uniform(0.12, 0.20) * ART_H * 1.6
    gx = center_x + np.cos(angle) * r * 0.9
    gy = center_y + np.sin(angle) * r * 0.6
    sz = np.random.uniform(0.008, 0.014)
    glow = LAB_COLOR if np.random.random() < 0.30 else "#D4C8A8"
    ax.add_patch(Circle((gx, gy), sz, facecolor=glow,
                         edgecolor=LAB_COLOR_DARK, linewidth=0.4,
                         alpha=0.85, zorder=16))

# ---- Descriptor RIBBON below art (Pokemon's signature banner) ----
rib_x, rib_w = 0.135, 0.730
rib_y, rib_h = 0.452, 0.034
# Tail triangles on each end
tail_l = Polygon([(rib_x, rib_y),
                   (rib_x - 0.014, rib_y + rib_h / 2),
                   (rib_x, rib_y + rib_h)],
                  facecolor=GOLD, edgecolor=GOLD_DARK, linewidth=0.5,
                  zorder=17)
tail_r = Polygon([(rib_x + rib_w, rib_y),
                   (rib_x + rib_w + 0.014, rib_y + rib_h / 2),
                   (rib_x + rib_w, rib_y + rib_h)],
                  facecolor=GOLD, edgecolor=GOLD_DARK, linewidth=0.5,
                  zorder=17)
ax.add_patch(tail_l); ax.add_patch(tail_r)
ax.add_patch(Rectangle((rib_x, rib_y), rib_w, rib_h,
                        facecolor=RIBBON, edgecolor=GOLD_DARK,
                        linewidth=0.6, zorder=18))
ax.text(rib_x + rib_w / 2, rib_y + rib_h / 2, CARD["descriptor"],
        fontsize=7.2, color=INK, ha="center", va="center",
        family="serif", style="italic", zorder=19)

# ---- Attacks ----
def draw_attack(y_top, atk):
    """Render one attack row. y_top is the top y of the row."""
    y_mid = y_top - 0.025
    # Energy cost: tightly grouped circles, far left
    n_cost = len(atk["cost"])
    cost_x_start = 0.108
    for j, kind in enumerate(atk["cost"]):
        cx = cost_x_start + j * 0.034
        fc, ec = TYPE_COLORS[kind]
        ax.add_patch(Circle((cx, y_mid), 0.0165,
                              facecolor=fc, edgecolor=ec, linewidth=1.0,
                              zorder=5))
        ax.text(cx, y_mid, kind, fontsize=8.2, fontweight="bold",
                color="white", ha="center", va="center", zorder=6)
    # Attack name
    name_x = cost_x_start + n_cost * 0.034 + 0.024
    ax.text(name_x, y_mid + 0.010, atk["name"], fontsize=14,
            fontweight="bold", color=INK, family="serif",
            va="center", zorder=4)
    # Score, far right
    ax.text(0.880, y_mid + 0.010, atk["score"], fontsize=15,
            fontweight="bold", color=INK, family="serif",
            ha="right", va="center", zorder=4)
    # Description, smaller, below name
    ax.text(name_x, y_mid - 0.018, atk["desc"], fontsize=6.4,
            color=INK, family="serif", style="italic",
            va="center", zorder=4)
    # Underline
    ax.add_line(Line2D([0.10, 0.90], [y_top - 0.062, y_top - 0.062],
                        color=INK, linewidth=0.45, zorder=3))

draw_attack(0.420, CARD["attacks"][0])
draw_attack(0.350, CARD["attacks"][1])

# ---- Weakness / Resistance / Retreat ----
wrr_label_y = 0.260
wrr_value_y = 0.232
ax.text(0.220, wrr_label_y, "weakness", fontsize=6.5, color=INK,
        ha="center", family="serif", zorder=4)
ax.text(0.500, wrr_label_y, "resistance", fontsize=6.5, color=INK,
        ha="center", family="serif", zorder=4)
ax.text(0.780, wrr_label_y, "retreat cost", fontsize=6.5, color=INK,
        ha="center", family="serif", zorder=4)

# Weakness
wfc, wec = TYPE_COLORS[CARD["weakness"][0]]
ax.add_patch(Circle((0.193, wrr_value_y), 0.018, facecolor=wfc,
                     edgecolor=wec, linewidth=0.9, zorder=5))
ax.text(0.193, wrr_value_y, CARD["weakness"][0], fontsize=8.5,
        fontweight="bold", color="white", ha="center", va="center",
        zorder=6)
ax.text(0.245, wrr_value_y, CARD["weakness"][1], fontsize=10.5,
        fontweight="bold", color=INK, va="center", family="serif",
        zorder=4)

# Resistance
rfc, rec = TYPE_COLORS[CARD["resistance"][0]]
ax.add_patch(Circle((0.473, wrr_value_y), 0.018, facecolor=rfc,
                     edgecolor=rec, linewidth=0.9, zorder=5))
ax.text(0.473, wrr_value_y, CARD["resistance"][0], fontsize=8.5,
        fontweight="bold", color="white", ha="center", va="center",
        zorder=6)
ax.text(0.527, wrr_value_y, CARD["resistance"][1], fontsize=10.5,
        fontweight="bold", color=INK, va="center", family="serif",
        zorder=4)

# Retreat orbs
for j in range(CARD["retreat"]):
    ax.add_patch(Circle((0.760 + j * 0.034, wrr_value_y), 0.014,
                         facecolor="#E5DCC8", edgecolor=INK, linewidth=0.7,
                         zorder=5))
    # Inner small star/dot
    ax.add_patch(Circle((0.760 + j * 0.034, wrr_value_y), 0.004,
                         facecolor=INK, alpha=0.4, zorder=6))

# WRR row delimiters
ax.add_line(Line2D([0.10, 0.90], [0.282, 0.282], color=INK,
                    linewidth=0.45, zorder=3))
ax.add_line(Line2D([0.10, 0.90], [0.205, 0.205], color=INK,
                    linewidth=0.45, zorder=3))

# ---- Flavor text + Level + Number (single row near bottom) ----
flavor_y = 0.150
# Wrap flavor (~64 chars)
words = CARD["flavor"].split()
lines, cur = [], ""
for w in words:
    if len(cur) + len(w) + 1 > 64:
        lines.append(cur); cur = w
    else:
        cur = (cur + " " + w).strip()
if cur:
    lines.append(cur)
for i, ln in enumerate(lines):
    ax.text(0.10, flavor_y - i * 0.022, ln, fontsize=6.6,
            color=INK, family="serif", style="italic", va="center", zorder=4)

# Level + number, right-aligned, on the same line as last flavor line
lv_y = flavor_y - (len(lines) - 1) * 0.022
ax.text(0.795, lv_y, CARD["level"], fontsize=7,
        fontweight="bold", color=INK, family="serif",
        ha="right", va="center", zorder=4)
ax.text(0.880, lv_y, f"#{CARD['number'].split('/')[0]}", fontsize=7,
        fontweight="bold", color=INK, family="serif",
        ha="right", va="center", zorder=4)

# ---- Bottom credits ----
bot_y = 0.072
ax.text(0.105, bot_y, "Illus. Free Systems Lab", fontsize=5.3,
        color=INK, family="serif", style="italic", zorder=4)
ax.text(0.520, bot_y, "© 2026 Free Systems Lab · Stanford GSB",
        fontsize=5.3, color=INK, ha="center", family="serif", zorder=4)
ax.text(0.835, bot_y, CARD["number"], fontsize=6.5,
        fontweight="bold", color=INK, family="serif",
        ha="right", va="center", zorder=4)
# Set symbol (small lab-color filled circle)
ax.add_patch(Circle((0.880, bot_y), 0.008,
                     facecolor=LAB_COLOR, edgecolor=LAB_COLOR_DARK,
                     linewidth=0.5, zorder=5))

# ---- Save ----
fig.savefig(OUT, dpi=240, bbox_inches="tight", pad_inches=0.10,
            facecolor="#1F1F1F")
print(f"Wrote {OUT}")
