"""Independent CSV arithmetic, price paths and augmented least-squares checks."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


obs = rows(P / "run-01/all-observations.csv")
pred = rows(P / "run-01/predictions.csv")
expected = json.loads((P / "run-01/results.json").read_text())
errors = {}
for name in ["I", "B", "X", "BX"]:
    values = [(float(r[f"pred_{name}"]) - float(r["y"])) ** 2 for r in pred]
    errors[name] = math.fsum(values) / len(values)
    assert abs(errors[name] - expected["overall"][name]["mse_pp2"]) < 1e-10
improvement = 100 * (1 - errors["BX"] / errors["B"])
assert abs(improvement - expected["overall"]["BX_vs_B_improvement_pct"]) < 1e-10
quotes = rows(P / "inputs/px_SPY.csv")
dates = [r["Date"] for r in quotes]
prices = [float(r["Close"]) for r in quotes]
label_checks = []
for date in ["2024-07-03", "2025-04-16", "2026-06-24"]:
    r = next(r for r in obs if r["source_date"] == date)
    t = next(i for i, d in enumerate(dates) if d > date)
    path = prices[t + 1:t + 22]
    y = 100 * (path[-1] / path[0] - 1)
    r20 = 100 * (prices[t] / prices[t - 20] - 1)
    peak = path[0]
    fall = 0
    for close in path:
        peak = max(peak, close)
        fall = max(fall, 100 * (1 - close / peak))
    assert dates[t + 1] == r["target_start"] and dates[t + 21] == r["target_end"]
    assert max(abs(y - float(r["y"])), abs(r20 - float(r["r20"])), abs(fall - float(r["window_fall"]))) < 1e-10
    label_checks.append({"source_date": date, "target_start": dates[t + 1], "target_end": dates[t + 21], "return_pp": y, "fall_pp": fall})
state_path = P / "research-state.json"
state = json.loads(state_path.read_text())
saved_fits = json.loads((P / "run-01/fits.json").read_text())
max_beta_difference = 0
for record in saved_fits:
    state["actual"]["review_refits"] += 1
    save(state_path, state)
    assert state["actual"]["review_refits"] <= 8
    train = [r for r in obs if r["target_end"] < f"{record['year']}-01-01"]
    y = np.array([float(r["y"]) for r in train])
    cols = record["columns"]
    if not cols:
        beta = np.array([math.fsum(y) / len(y)])
    else:
        x = np.array([[float(r[c]) for c in cols] for r in train])
        mu, scale = x.mean(axis=0), x.std(axis=0)
        a = np.column_stack([np.ones(len(y)), (x - mu) / scale])
        extra = np.diag([0.] + [math.sqrt(len(y) * .001)] * len(cols))
        beta = np.linalg.lstsq(np.vstack([a, extra]), np.concatenate([y, np.zeros(len(cols) + 1)]), rcond=None)[0]
        assert np.max(np.abs(mu - record["mu"])) < 1e-10
        assert np.max(np.abs(scale - record["scale"])) < 1e-10
    diff = float(np.max(np.abs(beta - record["beta"])))
    max_beta_difference = max(diff, max_beta_difference)
    assert diff < 1e-10 and len(train) == record["train_n"]
mask = sorted(range(len(pred)), key=lambda i: (float(pred[i]["pred_B"]) - float(pred[i]["y"]))**2 - (float(pred[i]["pred_BX"]) - float(pred[i]["y"]))**2, reverse=True)[:5]
without = [r for i, r in enumerate(pred) if i not in mask]
def mse(name):
    return math.fsum((float(r[f"pred_{name}"]) - float(r["y"]))**2 for r in without) / len(without)
assert abs(100 * (1 - mse("BX") / mse("B")) - expected["remove_largest_five_improvement_pct"]) < 1e-10
group_counts = {g: sum(r["state"] == g for r in obs) for g in ["low40", "high100", "middle"]}
assert group_counts == {g: d["n"] for g, d in expected["raw_groups_descriptive"].items()}
artifacts = {str(f.relative_to(P)): hashlib.sha256(f.read_bytes()).hexdigest() for f in (P / "run-01").iterdir() if f.is_file()}
save(P / "independent-review.json", {"passed": True, "review_role": "same controller different calculation; no external reviewer", "evaluation_rows": len(pred), "source_rows": len(obs), "mse_pp2": errors, "increment_pct": improvement, "price_label_checks": label_checks, "review_refits": 8, "max_beta_difference": max_beta_difference, "group_counts": group_counts, "artifact_sha256": artifacts, "limits": "Numeric agreement does not validate first publication, causal effect, future robustness or real trades."})
print(json.dumps({"passed": True, "rows": len(pred), "max_beta_difference": max_beta_difference}))
