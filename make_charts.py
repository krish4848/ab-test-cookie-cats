"""Charts for the Cookie Cats A/B test. Usage: python3 -I make_charts.py <results.json> <out_dir>"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

res = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])

# Tokens from the reference palette (light mode)
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASE = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "font.family": "DejaVu Sans",
    "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": BASE, "axes.linewidth": 1,
})

def sgn(x, d=2):
    """Signed number with a real minus sign."""
    return f"{x:+.{d}f}".replace("-", "\u2212")

def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(length=0)

# ============================================================ Figure 1: forest
rows = [  # (y, label, all-players result, excl-zero-round result)
    (1, "Day-7 retention", res["retention"]["retention_7"],
     res["sensitivity_exclude_zero_round_users"]["retention_7"]),
    (0, "Day-1 retention", res["retention"]["retention_1"],
     res["sensitivity_exclude_zero_round_users"]["retention_1"]),
]
fig, ax = plt.subplots(figsize=(9, 4.4), dpi=200)
style(ax)
ax.set_xlim(-1.7, 0.55)
ax.set_ylim(-0.75, 1.65)
ax.grid(axis="x", color=GRID, linewidth=1, zorder=0)
ax.set_axisbelow(True)
ax.axvline(0, color=BASE, linewidth=1.5, zorder=1)

for y, label, a, b in rows:
    for off, r, color, ms in ((+0.13, a, BLUE, 9), (-0.13, b, MUTED, 8)):
        lo, hi = r["diff_ci95_wald_pp"]
        ax.plot([lo, hi], [y + off] * 2, color=color, linewidth=2,
                solid_capstyle="round", zorder=3)
        ax.plot(r["diff_pp"], y + off, "o", color=color, markersize=ms,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    lo, hi = a["diff_ci95_wald_pp"]
    ax.text(1.04, y + 0.13, f"{sgn(a['diff_pp'])} pp", transform=ax.get_yaxis_transform(),
            ha="left", va="center", fontsize=10.5, color=INK, fontweight="bold",
            clip_on=False)
    ax.text(1.04, y - 0.02, f"95% CI {sgn(lo)} to {sgn(hi)}",
            transform=ax.get_yaxis_transform(), ha="left", va="center",
            fontsize=8.5, color=INK2, clip_on=False)
    ax.text(-1.7, y + 0.46, label, ha="left", va="center", fontsize=10.5,
            color=INK, fontweight="bold")

# the axes-fraction x of the label column must be in axes coords: map via data xlim
ax.set_yticks([])
ax.set_xticks([-1.5, -1.0, -0.5, 0, 0.5])
ax.set_xticklabels(["−1.5", "−1.0", "−0.5", "0", "+0.5"], fontsize=9)
ax.set_xlabel("Difference in retention, gate_40 minus gate_30 (percentage points)",
              fontsize=9.5, labelpad=8)
ax.text(-0.03, 1.01, "\u2190 lower retention with gate_40", transform=ax.get_xaxis_transform(),
        ha="right", va="bottom", fontsize=8.5, color=MUTED)
ax.text(0.03, 1.01, "higher \u2192", transform=ax.get_xaxis_transform(),
        ha="left", va="bottom", fontsize=8.5, color=MUTED)

fig.text(0.055, 0.955, "Moving the gate to level 40 lowered day-7 retention",
         fontsize=14, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.055, 0.895,
         f"Cookie Cats A/B test, {res['srm']['n_gate_30']:,} players on gate_30 vs "
         f"{res['srm']['n_gate_40']:,} on gate_40",
         fontsize=9.5, color=INK2, ha="left", va="top")
handles = [Line2D([0], [0], color=BLUE, marker="o", markersize=7, linewidth=2,
                  markeredgecolor=SURFACE, label="All players"),
           Line2D([0], [0], color=MUTED, marker="o", markersize=7, linewidth=2,
                  markeredgecolor=SURFACE, label="Excluding players with 0 rounds")]
ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, -0.01),
          frameon=False, fontsize=9, labelcolor=INK2, handlelength=1.8)
fig.text(0.055, 0.025,
         f"Arm sizes differ more than chance usually produces (sample-ratio check p = "
         f"{res['srm']['p']:.3f}); see README caveats.",
         fontsize=8.5, color=MUTED, ha="left", va="bottom")
fig.subplots_adjust(left=0.055, right=0.80, top=0.80, bottom=0.2)
fig.savefig(out / "fig1_retention_effect.png")
plt.close(fig)

# ======================================== Figure 2: day-7 retention by rounds
order = ["0", "1-9", "10-29", "30-99", "100+"]
q4 = res["sql"]["Q4"]
val = {(r["version"], r["rounds_bucket"]): r["d7_retention"] * 100 for r in q4}
cnt = {(r["version"], r["rounds_bucket"]): r["n_players"] for r in q4}

fig, ax = plt.subplots(figsize=(9, 4.6), dpi=200)
style(ax)
w, off = 0.16, 0.088
xs = range(len(order))
c30 = [val[("gate_30", b)] for b in order]
c40 = [val[("gate_40", b)] for b in order]
ax.bar([x - off for x in xs], c30, width=w, color=BLUE, zorder=3)
ax.bar([x + off for x in xs], c40, width=w, color=ORANGE, zorder=3)
ax.set_xticks(list(xs))
ax.set_xticklabels([f"{b} rounds" if b != "0" else "0 rounds" for b in order], fontsize=9.5)
ax.set_ylim(0, 80)
ax.set_yticks([0, 20, 40, 60, 80])
ax.set_yticklabels(["0%", "20%", "40%", "60%", "80%"], fontsize=9)
ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
ax.set_axisbelow(True)
ax.spines["bottom"].set_color(BASE)
# selective direct labels: the 30-99 gap and the flat 100+ pair
for b in ("30-99", "100+"):
    i = order.index(b)
    top = max(val[("gate_30", b)], val[("gate_40", b)])
    ax.text(i, top + 1.5,
            f"{val[('gate_30', b)]:.1f}% vs {val[('gate_40', b)]:.1f}%",
            ha="center", va="bottom", fontsize=9, color=INK)
ax.set_xlabel("Total rounds played in the first 14 days", fontsize=9.5, labelpad=8)

fig.text(0.055, 0.955, "The day-7 gap sits among players with 10\u201399 rounds",
         fontsize=14, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.055, 0.895,
         "Descriptive only: rounds played is measured after assignment and may itself "
         "be affected by the gate.", fontsize=9.5, color=INK2, ha="left", va="top")
handles = [Line2D([0], [0], marker="s", color="none", markerfacecolor=BLUE,
                  markeredgecolor="none", markersize=9, label="gate_30 (control)"),
           Line2D([0], [0], marker="s", color="none", markerfacecolor=ORANGE,
                  markeredgecolor="none", markersize=9, label="gate_40 (treatment)")]
ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=9.5,
          labelcolor=INK2, handletextpad=0.4)
fig.subplots_adjust(left=0.07, right=0.97, top=0.80, bottom=0.17)
fig.savefig(out / "fig2_retention_by_rounds.png")
plt.close(fig)
print("charts written")
