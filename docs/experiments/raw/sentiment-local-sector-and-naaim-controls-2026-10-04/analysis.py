"""One frozen retrospective comparison. No as-of trading qualification."""
import argparse
import hashlib
import importlib.util
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
PRICE = ["r20", "r63", "dma200", "dd252", "rv20"]
MODELS = {"P": PRICE, "PX": PRICE + ["naaim"]}


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def kernel():
    spec = importlib.util.spec_from_file_location("frozen_naaim_ridge", ROOT / "snapshots/naaim_ridge.py")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def check_inputs():
    manifest = json.loads((ROOT / "inputs.json").read_text())
    for entry in manifest["files"]:
        path = REPO / entry["path"]
        assert path.stat().st_size == entry["size"], entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], entry["path"]
    return {entry["role"]: REPO / entry["path"] for entry in manifest["files"]}


def price_features(c, k):
    past = c[k-251:k+1]
    if k < 251 or len(past) != 252 or not np.isfinite(past).all() or past.min() <= 0:
        raise ValueError("252 positive finite original quote positions required")
    returns = c[k-19:k+1] / c[k-20:k] - 1
    return {"r20":100*(c[k]/c[k-20]-1), "r63":100*(c[k]/c[k-63]-1),
            "dma200":100*(c[k]/np.mean(c[k-199:k+1])-1),
            "dd252":100*(c[k]/np.max(past)-1),
            "rv20":100*np.std(returns, ddof=1)*math.sqrt(20)}


def observations(paths):
    px = pd.read_csv(paths["prices"], parse_dates=["Date"])
    survey = pd.read_csv(paths["survey"], parse_dates=["date"])
    old = pd.read_csv(paths["saved_predictions"], parse_dates=["anchor_date", "target_end"])
    assert px.Date.is_unique and px.Date.is_monotonic_increasing
    assert survey.date.is_unique and survey.date.is_monotonic_increasing
    c = px.Close.to_numpy(float)
    rows, excluded = [], []
    for item in survey.itertuples():
        k = int(px.Date.searchsorted(item.date, side="right"))
        if k < 251 or k + 21 >= len(c):
            excluded.append({"date": str(item.date.date()), "reason": "warmup_or_immature"})
            continue
        past, future = c[k-251:k+1], c[k+1:k+22]
        if not (np.isfinite(past).all() and np.isfinite(future).all() and past.min() > 0 and future.min() > 0 and np.isfinite(item.naaim)):
            excluded.append({"date": str(item.date.date()), "reason": "nonfinite_or_nonpositive"})
            continue
        rows.append({"source_date": item.date, "anchor_date": px.Date.iloc[k],
                     "target_start": px.Date.iloc[k+1], "target_end": px.Date.iloc[k+21],
                     "anchor_index": k, **price_features(c,k),
                     "naaim": float(item.naaim), "y": 100*(future[-1]/future[0]-1)})
    frame = pd.DataFrame(rows)
    evaluation = frame[frame.anchor_date.dt.year.isin([2025, 2026])]
    assert len(old) == len(evaluation) == 78
    assert old.anchor_date.tolist() == evaluation.anchor_date.tolist()
    for col in ["r20", "naaim", "y"]:
        np.testing.assert_allclose(old[col], evaluation[col], rtol=1e-12, atol=1e-10)
    assert old.target_end.tolist() == evaluation.target_end.tolist()
    return frame, old, excluded


def prepare():
    f, old, excluded = observations(check_inputs())
    support = {}
    for year in [2025, 2026]:
        tr = f[f.target_end < pd.Timestamp(f"{year}-01-01")]
        te = f[f.anchor_date.dt.year == year]
        assert len(tr) >= 40 and len(te) > 0
        z = (tr[MODELS["PX"]] - tr[MODELS["PX"]].mean()) / tr[MODELS["PX"]].std(ddof=0)
        assert np.isfinite(z.to_numpy()).all()
        support[str(year)] = {"train_rows": len(tr), "eval_rows": len(te),
            "train_latest_target_end": str(tr.target_end.max().date()),
            "unregularized_design_rank": int(np.linalg.matrix_rank(np.column_stack([np.ones(len(z)),z]))),
            "parameters_including_intercept": 7,
            "train_adjacent_overlapping_pairs": int((np.diff(tr.anchor_index) < 20).sum()),
            "independent_events": "unknown; overlapping intervals are not independent observations"}
    result = {"source_rows": len(f) + len(excluded), "valid_rows": len(f), "excluded": excluded,
              "evaluation_rows": len(old), "source_range": [str(f.source_date.min().date()),str(f.source_date.max().date())],
              "support": support, "old_prediction_comparison": "same 78 anchors, labels, NAAIM, r20 verified; no old refit",
              "eligibility": "current revised retrospective survey association only; original publication/revision and actual provider arrival unknown",
              "effects_inspected": False, "new_fits": 0}
    dump(ROOT / "qualification.json", result)
    print(json.dumps(result, ensure_ascii=False))


def metrics(f):
    out = {}
    for name in ["I", "B", "X", "BX", "P", "PX"]:
        error = f[f"pred_{name}"].to_numpy() - f.y.to_numpy()
        out[name] = {"n":len(f), "mse_pp2":float(np.mean(error**2)),
                     "rmse_pp":float(np.sqrt(np.mean(error**2))), "mae_pp":float(np.mean(np.abs(error)))}
    for a,b in [("PX","P"),("PX","I"),("BX","B"),("P","B"),("PX","BX")]:
        out[f"{a}_vs_{b}_improvement_pct"] = 100*(1-out[a]["mse_pp2"]/out[b]["mse_pp2"])
    return out


def run():
    state = json.loads((ROOT / "research-state.json").read_text())
    freeze = json.loads((ROOT / "execution-freeze.json").read_text())
    for name, digest in freeze["files"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    assert state["core_fits"] == 0 and state["status"] == "frozen"
    f, old, excluded = observations(check_inputs())
    output = ROOT / "run-01"
    output.mkdir(exist_ok=False)
    begin = time.monotonic()
    state.update(status="running",started_at=datetime.now(timezone.utc).isoformat(),pid=__import__('os').getpid())
    dump(ROOT / "research-state.json", state)
    all_test, fits = [], []
    core = kernel()
    for year in [2025, 2026]:
        tr = f[f.target_end < pd.Timestamp(f"{year}-01-01")]
        te = f[f.anchor_date.dt.year == year].copy()
        assert tr.target_end.max() < te.anchor_date.min()
        for name,cols in MODELS.items():
            state["core_fits"] += 1
            assert state["core_fits"] <= 4
            dump(ROOT / "research-state.json", state)
            fitted = core.fit(tr[cols].to_numpy(),tr.y.to_numpy(),penalty=0.001)
            te[f"pred_{name}"] = core.predict(fitted,te[cols].to_numpy())
            fits.append({"year":year,"model":name,"columns":cols,"train_n":len(tr),"test_n":len(te),
                         **dict(zip(["beta","mu","scale"],[a.tolist() for a in fitted]))})
        all_test.append(te)
    v = pd.concat(all_test).sort_values("anchor_date").reset_index(drop=True)
    for name in ["I","B","X","BX"]:
        v[f"pred_{name}"] = old[f"pred_{name}"].to_numpy()
    assert np.isfinite(v[[f"pred_{m}" for m in ["I","B","X","BX","P","PX"]]].to_numpy()).all()
    v.to_csv(output/"predictions.csv",index=False)
    f.to_csv(output/"observations.csv",index=False)
    dump(output/"fits.json",fits)
    result = {"overall":metrics(v),"years":{str(y):metrics(v[v.anchor_date.dt.year==y]) for y in [2025,2026]},
              "eval_range":[str(v.anchor_date.min().date()),str(v.anchor_date.max().date())],
              "last_target_end":str(v.target_end.max().date()),"excluded":excluded}
    # All following calculations reuse the same four fits. No model search.
    e_p=(v.pred_P.to_numpy()-v.y.to_numpy())**2
    e_px=(v.pred_PX.to_numpy()-v.y.to_numpy())**2
    intervals={}
    for length in [8,16]:
        rng=np.random.default_rng(20261004+length); samples=[]; n=len(v)
        for _ in range(2000):
            starts=rng.integers(0,n-length+1,math.ceil(n/length))
            indices=np.concatenate([np.arange(a,a+length) for a in starts])[:n]
            samples.append(100*(1-e_px[indices].mean()/e_p[indices].mean()))
        intervals[str(length)]={"draws":2000,"interval_pct":np.quantile(samples,[.025,.975]).tolist()}
    delta=e_p-e_px; biggest=np.argsort(-delta)[:5];keep=np.ones(len(v),bool);keep[biggest]=False
    result.update(uncertainty=intervals,adjacent_targets={"pairs":len(v)-1,"overlapping_pairs":int((np.diff(v.anchor_index)<20).sum()),"median_shared_segments":float(np.median(np.maximum(0,20-np.diff(v.anchor_index))))},
                  top5={"sum_error_reduction_pp2":float(delta[biggest].sum()),"total_error_reduction_pp2":float(delta.sum()),"remove_top5_improvement_pct":float(100*(1-e_px[keep].mean()/e_p[keep].mean()))},
                  sample_chain={"raw":len(f)+len(excluded),"qualified_features":len(f),"mature_common_eval":len(v)},
                  raw_evaluation={"up_rows":int((v.y>0).sum()),"up_pct":float(100*(v.y>0).mean()),"mean_return_pp":float(v.y.mean()),"median_return_pp":float(v.y.median())})
    dump(output/"results.json",result)
    state.update(status="awaiting_review",finished_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-begin,next_action="independent four-fit check; no core rerun")
    dump(ROOT/"research-state.json",state)
    print(json.dumps({"core_fits":state["core_fits"],"n":len(v),"overall":result["overall"]},ensure_ascii=False))


if __name__ == "__main__":
    ap=argparse.ArgumentParser();ap.add_argument("mode",choices=["prepare","run"])
    args=ap.parse_args()
    prepare() if args.mode=="prepare" else run()
