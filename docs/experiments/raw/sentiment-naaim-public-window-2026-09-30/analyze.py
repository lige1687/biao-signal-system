"""Restricted retrospective association; never an as-of trading backtest."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def fit(x, y, penalty=0.001):
    mu, scale = x.mean(axis=0), x.std(axis=0)
    if np.any(scale <= 0):
        raise ValueError("constant feature; no silent drop")
    z = np.column_stack([np.ones(len(y)), (x - mu) / scale])
    penalizer = np.diag([0] + [1] * x.shape[1])
    beta = np.linalg.solve(z.T @ z + len(y) * penalty * penalizer, z.T @ y)
    return beta, mu, scale


def predict(model, x):
    beta, mu, scale = model
    return np.column_stack([np.ones(len(x)), (x - mu) / scale]) @ beta


def synth():
    x = np.arange(40, dtype=float)[:, None]
    y = 2 + 3 * x[:, 0]
    model = fit(x, y, penalty=0)
    assert np.max(np.abs(predict(model, x) - y)) < 1e-10
    scaled = fit(100 * x, y, penalty=0)
    assert np.max(np.abs(predict(scaled, 100 * x) - y)) < 1e-10
    constant_rejected = False
    try:
        fit(np.ones((40, 1)), y)
    except ValueError:
        constant_rejected = True
    assert constant_rejected
    path = np.array([100., 90., 110.])
    assert abs(100 * (path[-1] / path[0] - 1) - 10) < 1e-10
    assert abs(100 * np.max(1 - path / np.maximum.accumulate(path)) - 10) < 1e-10
    dump(ROOT / "synthetic-check.json", {"passed": True, "cases": ["linear", "scale", "constant rejected", "return endpoint", "within-window fall"]})


def stats(frame):
    out = {}
    for m in ["I", "B", "X", "BX"]:
        e = frame[f"pred_{m}"].to_numpy() - frame.y.to_numpy()
        out[m] = {"n": len(e), "mse_pp2": float(np.mean(e**2)), "rmse_pp": float(np.sqrt(np.mean(e**2))), "mae_pp": float(np.mean(np.abs(e))), "mean_error_pp": float(np.mean(e))}
    out["BX_vs_B_improvement_pct"] = 100 * (1 - out["BX"]["mse_pp2"] / out["B"]["mse_pp2"])
    out["BX_vs_I_improvement_pct"] = 100 * (1 - out["BX"]["mse_pp2"] / out["I"]["mse_pp2"])
    return out


def run():
    state_path = ROOT / "research-state.json"
    state = json.loads(state_path.read_text())
    assert hashlib.sha256((ROOT / "protocol.json").read_bytes()).hexdigest() == state["protocol_sha256"]
    protocol = json.loads((ROOT / "protocol.json").read_text())
    manifest = json.loads((ROOT / "source-manifest.json").read_text())
    for f in manifest["files"]:
        assert hashlib.sha256(Path(f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]
    out = ROOT / "run-01"
    out.mkdir(exist_ok=False)
    px = pd.read_csv(ROOT / "inputs/px_SPY.csv", parse_dates=["Date"])
    assert px.Date.is_unique and px.Date.is_monotonic_increasing
    s = pd.read_csv(ROOT / "inputs/naaim-official-delayed.csv", parse_dates=["date"])
    c = px.Close.to_numpy()
    rows, excluded = [], []
    for item in s.itertuples():
        t = int(px.Date.searchsorted(item.date, side="right"))
        if t < 20 or t + 21 >= len(c):
            excluded.append({"date": str(item.date.date()), "reason": "warmup or immature"})
            continue
        background, path = c[t - 20:t + 1], c[t + 1:t + 22]
        if not (np.isfinite(background).all() and np.isfinite(path).all() and np.min(background) > 0 and np.min(path) > 0):
            excluded.append({"date": str(item.date.date()), "reason": "missing/invalid price"})
            continue
        rows.append({"source_date": item.date, "anchor_date": px.Date.iloc[t], "target_start": px.Date.iloc[t + 1], "target_end": px.Date.iloc[t + 21], "anchor_index": t, "r20": 100 * (c[t] / c[t - 20] - 1), "naaim": item.naaim, "y": 100 * (path[-1] / path[0] - 1), "window_fall": 100 * np.max(1 - path / np.maximum.accumulate(path)), "state": "low40" if item.naaim <= 40 else "high100" if item.naaim >= 100 else "middle"})
    f = pd.DataFrame(rows)
    f.to_csv(out / "all-observations.csv", index=False)
    dump(out / "exclusions.json", excluded)
    models = protocol["estimation"]["models"]
    estimates, fits = [], []
    for year in [2025, 2026]:
        cutoff = pd.Timestamp(f"{year}-01-01")
        train = f[f.target_end < cutoff]
        test = f[f.anchor_date.dt.year == year].copy()
        assert len(train) >= 40 and len(test) > 0
        assert train.target_end.max() < test.anchor_date.min()
        for name, cols in models.items():
            state["actual"]["fits"] += 1
            dump(state_path, state)
            assert state["actual"]["fits"] <= 8
            if not cols:
                test[f"pred_{name}"] = train.y.mean()
                metadata = {"beta": [float(train.y.mean())], "mu": [], "scale": []}
            else:
                model = fit(train[cols].to_numpy(), train.y.to_numpy())
                test[f"pred_{name}"] = predict(model, test[cols].to_numpy())
                metadata = dict(zip(["beta", "mu", "scale"], [a.tolist() for a in model]))
            fits.append({"year": year, "model": name, "columns": cols, "train_n": len(train), "train_latest_target_end": str(train.target_end.max().date()), "eval_n": len(test), **metadata})
        estimates.append(test)
    v = pd.concat(estimates).sort_values("anchor_date")
    assert np.isfinite(v[[f"pred_{m}" for m in models]].to_numpy()).all()
    v.to_csv(out / "predictions.csv", index=False)
    dump(out / "fits.json", fits)
    results = {"overall": stats(v), "years": {str(y): stats(v[v.anchor_date.dt.year == y]) for y in [2025, 2026]}}
    n = len(v)
    e_b = (v.pred_B.to_numpy() - v.y.to_numpy())**2
    e_bx = (v.pred_BX.to_numpy() - v.y.to_numpy())**2
    uncertainty = {}
    for length in [8, 16]:
        rng = np.random.default_rng(20260930 + length)
        samples = []
        for _ in range(2000):
            starts = rng.integers(0, n - length + 1, int(np.ceil(n / length)))
            indices = np.concatenate([np.arange(a, a + length) for a in starts])[:n]
            samples.append(100 * (1 - e_bx[indices].mean() / e_b[indices].mean()))
        np.savetxt(out / f"uncertainty-{length}.csv", samples, delimiter=",")
        uncertainty[str(length)] = {"draws": 2000, "interval_pct": np.quantile(samples, [.025, .975]).tolist()}
    groups = {}
    for name, group in f.groupby("state"):
        groups[name] = {"n": len(group), "positive_pct": float(100 * (group.y > 0).mean()), "mean_return_pp": float(group.y.mean()), "median_return_pp": float(group.y.median()), "mean_window_fall_pp": float(group.window_fall.mean()), "worst_window_fall_pp": float(group.window_fall.max())}
    f[f.state != "middle"].to_csv(out / "all-original-extreme-cases.csv", index=False)
    delta = e_b - e_bx
    largest = v.assign(error_reduction_pp2=delta).sort_values("error_reduction_pp2", ascending=False).head(5)
    largest.to_csv(out / "largest-five-contributions.csv", index=False)
    overlap = np.maximum(0, 20 - np.diff(v.anchor_index))
    results.update({"uncertainty": uncertainty, "raw_groups_descriptive": groups, "eligible_rows": len(f), "eval_rows": len(v), "excluded_rows": len(excluded), "adjacent_future_segment_overlap": {"pairs": len(overlap), "overlapping_pairs": int((overlap > 0).sum()), "median_shared_segments": float(np.median(overlap))}, "largest_five_error_reduction_pp2": float(largest.error_reduction_pp2.sum()), "total_error_reduction_pp2": float(delta.sum()), "remove_largest_five_improvement_pct": float(100 * (1 - e_bx[~v.index.isin(largest.index)].mean() / e_b[~v.index.isin(largest.index)].mean()))})
    dump(out / "results.json", results)
    state["execution"] = "running"
    state["next_action"] = "independent numeric review and readable report"
    dump(state_path, state)
    print(json.dumps({"rows": len(f), "evaluation": len(v), "fits": len(fits)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["synthetic", "run"])
    args = parser.parse_args()
    synth() if args.mode == "synthetic" else run()
