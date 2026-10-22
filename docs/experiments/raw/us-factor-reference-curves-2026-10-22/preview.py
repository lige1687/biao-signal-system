"""Render a static preview from the already-reconciled display points; no new study."""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[4]
FOLDER = ROOT / "web/public/research/us-factor-reference-curves-20261022"
x = json.loads((FOLDER / "data.json").read_text())["datasets"]["OP|big|primary"]
points = x["points"]
fig, ax = plt.subplots(figsize=(10, 4.8))
fig.subplots_adjust(bottom=.19, left=.075, right=.985, top=.89)
colors = {"L":"#5489de","N":"#7448c7","H":"#c55745","B":"#58a886"}
labels = {"L":"Low profitability","N":"Middle","H":"High profitability","B":"Three-group baseline"}
for g in ["L", "N", "H", "B"]:
    ax.plot(range(len(points)), [r["nav"][g] for r in points], label=labels[g], color=colors[g], linewidth=1.9)
ax.set_title("US large-stock operating profitability | 2015–2024", loc="left", fontsize=14, pad=15)
ax.set_ylabel("Growth of 100")
ix = [0,24,48,72,96,120]
ax.set_xticks(ix, [points[i]["month"] for i in ix])
ax.grid(axis="y", alpha=.18)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(loc="upper left", frameon=False, ncols=2, fontsize=9)
fig.text(.02,.025,"French 202608/CIZ published portfolios. Monthly endpoints. Before personal trading costs. Seen history.", fontsize=8, color="#64748b")
fig.savefig(FOLDER / "op-big-primary.png", dpi=150)
