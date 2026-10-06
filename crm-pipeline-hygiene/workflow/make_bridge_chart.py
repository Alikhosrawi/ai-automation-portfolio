"""Draws screenshots/04-forecast-bridge.png from the outbox and the scored test result. Needs matplotlib."""
import csv, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
facts = json.load(open(os.path.join(HERE, "..", "data", "outbox", "facts.json"), encoding="utf-8"))
score = json.load(open(os.path.join(HERE, "..", "test", "results", "primary-seed-score.json")))
num = lambda s: float(s.replace("€", "").replace(",", ""))
raw, cleaned = num(facts["q4_forecast_as_exported"]), num(facts["q4_forecast_cleaned"])
dup, zom = num(facts["removed_duplicate_copies"]["weighted"]), num(facts["removed_no_activity_over_60_days"]["weighted"])
true = score["forecast"]["true"]

TOTAL, REMOVE, INK, INK2, GRID, BG = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
fig, ax = plt.subplots(figsize=(11, 6), dpi=200)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
bars = [("As exported", 0, raw, TOTAL), (f"Duplicate copies\n({facts['removed_duplicate_copies']['deals']} deals)", raw - dup, raw, REMOVE),
        (f"No activity 60+ days\n({facts['removed_no_activity_over_60_days']['deals']} deals)", cleaned, raw - dup, REMOVE),
        ("After cleaning", 0, cleaned, TOTAL)]
w = 0.52
for i, (label, lo, hi, col) in enumerate(bars):
    ax.add_patch(FancyBboxPatch((i - w / 2, lo), w, hi - lo, boxstyle="round,pad=0,rounding_size=0.02", fc=col, ec=BG, lw=2, mutation_aspect=40000))
    val = hi - lo
    txt = f"€{val/1e6:.2f}M" if col == TOTAL else f"−€{val/1e3:.0f}k"
    if col == TOTAL:
        ax.text(i, hi + 30000, txt, ha="center", va="bottom", fontsize=12, color=INK, fontweight="bold")
    else:  # below the bar, so it never collides with the dashed truth line
        ax.text(i, lo - 30000, txt, ha="center", va="top", fontsize=12, color=INK, fontweight="bold")
for i in range(3):  # connectors
    y = [raw, raw - dup, cleaned][i]
    ax.plot([i + w / 2, i + 1 - w / 2], [y, y], color=INK2, lw=1, ls=(0, (2, 2)))
ax.plot([-0.45, 3.35], [true, true], color=INK, lw=1.4, ls=(0, (6, 3)))
ax.text(3.42, true, f"True forecast (answer key)\n€{true/1e6:.2f}M", va="center", ha="left", fontsize=10.5, color=INK)
ax.text(0, 1.035, f"The {facts['not_counted_no_amount']['deals']} deals with no amount count as €0, so the cleaned figure is a floor: filling them in can only raise it.",
         fontsize=10.5, color=INK2, ha="left", transform=ax.transAxes)
ax.set_xticks(range(4)); ax.set_xticklabels([b[0] for b in bars], fontsize=11, color=INK)
ax.set_xlim(-0.6, 4.35); ax.set_ylim(0, raw * 1.12)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"€{v/1e6:.1f}M"))
ax.tick_params(axis="y", colors=INK2, labelsize=10, length=0); ax.tick_params(axis="x", length=0)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("Q4 weighted forecast, Monday 12 Oct 2026 (fictional company)", loc="left", fontsize=14, color=INK, pad=34, fontweight="bold")
out = os.path.join(HERE, "..", "screenshots", "04-forecast-bridge.png")
plt.tight_layout(); plt.savefig(out, facecolor=BG); print(out)
