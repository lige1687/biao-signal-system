"""Independent arithmetic check for the frozen breadth review contract.

Uses only the saved breadth JSON and SPY adjusted-close CSV. No project modules.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BREADTH = ROOT / "docs/experiments/raw/sentiment-short-history-2026-10-02/inputs/ma_percentage_historical.json"
PRICES = ROOT / "docs/experiments/raw/sentiment-naaim-public-window-2026-09-30/inputs/px_SPY.csv"
OUT = Path(__file__).resolve().parent / "independent-labels.json"
EXPECTED = {
    BREADTH: "613fa152ee6cf2820df59f5566eb4601bda2f1c71747b7bda96d8128282011c7",
    PRICES: "952f397be0ccc5745185b91cce6acc781737c0f30a7a34aa8a230ae892ed5e45",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for path, digest in EXPECTED.items():
    actual = sha256(path)
    if actual != digest:
        raise SystemExit(f"input hash drift: {path}: {actual}")

with BREADTH.open() as f:
    source_rows = json.load(f)["data"]
with PRICES.open(newline="") as f:
    price_rows = list(csv.DictReader(f))
dates = [row["Date"] for row in price_rows]
close = [float(row["Close"]) for row in price_rows]
if any(not math.isfinite(x) or x <= 0 for x in close):
    raise SystemExit("invalid SPY close")
if dates != sorted(dates) or len(dates) != len(set(dates)):
    raise SystemExit("SPY calendar is not unique and ordered")
idx = {date: i for i, date in enumerate(dates)}
breadth = {row["date"]: float(row["ma_20"]["percentage_above"]) for row in source_rows}
if len(breadth) != len(source_rows) or any(not math.isfinite(x) for x in breadth.values()):
    raise SystemExit("duplicate date or invalid B20")

counts = {name: 0 for name in ("unmatched_quote", "unmatured", "insufficient_source_prefix", "boundary_purge", "train", "eval")}
classified = []
for row in source_rows:
    t = row["date"]
    if t not in idx:
        group = "unmatched_quote"
    else:
        i = idx[t]
        if i + 21 >= len(dates):
            group = "unmatured"
        elif any(d not in breadth for d in dates[i - 20:i + 1]):
            group = "insufficient_source_prefix"
        else:
            end = dates[i + 21]
            if t < "2026-01-01" and end >= "2026-01-01":
                group = "boundary_purge"
            elif t < "2026-01-01" and end < "2026-01-01":
                group = "train"
            elif t >= "2026-01-01":
                group = "eval"
            else:
                raise SystemExit(f"unclassified maturity date {t}, {end}")
    counts[group] += 1
    classified.append({"date": t, "partition": group})

if len(source_rows) != 404 or counts != {
    "unmatched_quote": 20, "unmatured": 21, "insufficient_source_prefix": 20,
    "boundary_purge": 21, "train": 175, "eval": 147,
}:
    raise SystemExit(f"partition mismatch: {len(source_rows)} {counts}")

oracles = []
for t in ("2025-04-07", "2026-01-02", "2026-08-04"):
    i = idx[t]
    prior, future = close[i - 20:i + 1], close[i + 1:i + 22]
    if len(prior) != 21 or len(future) != 21 or any(not math.isfinite(x) or x <= 0 for x in prior + future):
        raise SystemExit(f"invalid 21-close window at {t}")
    prior_date, prior20_date = dates[i - 20], dates[i - 20]
    target_start, target_end = dates[i + 1], dates[i + 21]
    b20 = breadth[t]
    old_b20 = breadth.get(prior20_date)
    if old_b20 is None:
        raise SystemExit(f"missing B20 delta endpoint for {t}: {prior20_date}")
    peak = future[0]
    worst = 0.0
    worst_date = target_start
    for day, price in zip(dates[i + 1:i + 22], future):
        peak = max(peak, price)
        loss = 100.0 * (1.0 - price / peak)
        if loss > worst:
            worst, worst_date = loss, day
    oracles.append({
        "anchor_date": t,
        "prior_price_endpoint_date_t_minus_20": prior_date,
        "target_start_date_t_plus_1": target_start,
        "target_end_date_t_plus_21": target_end,
        "close_t_minus_20": prior[0],
        "close_t": prior[-1],
        "r20_percent": 100.0 * (prior[-1] / prior[0] - 1.0),
        "b20_percentage_points": b20,
        "b20_t_minus_20_percentage_points": old_b20,
        "delta20_percentage_points": b20 - old_b20,
        "target20_return_percent": 100.0 * (future[-1] / future[0] - 1.0),
        "max_future_peak_to_trough_decline_percent": worst,
        "max_decline_date": worst_date,
        "future_first_close": future[0],
        "future_last_close": future[-1],
        "future_close_count": len(future),
    })

result = {
    "input_hashes": {str(p.relative_to(ROOT)): sha256(p) for p in EXPECTED},
    "source_rows": len(source_rows),
    "all_spy_quote_closes_positive_finite": True,
    "spy_quote_rows": len(close),
    "partition_counts": counts,
    "common_mature_dates": counts["train"] + counts["eval"] + counts["boundary_purge"],
    "common_mature_split": {"train": counts["train"], "eval": counts["eval"], "cross_year_purge": counts["boundary_purge"]},
    "partition_dates": classified,
    "oracle_labels": oracles,
}
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"partition_counts": counts, "oracle_labels": oracles}, indent=2))
