"""Registered finite weekly state analyses; no new OLS fit or chosen threshold.

Score/dependence helpers adapted from the prior sealed EMA study. Its frozen
code and results are unchanged; new inputs/definitions and identity are explicit.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
PERIODS = {"early": ("2022-01-04", "2024-12-31"),
           "2025": ("2025-01-01", "2025-12-31"),
           "2026H1": ("2026-01-01", "2026-06-30")}
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")

def aggregate(frame, col):
    """Each observed ETF receives equal total weight."""
    return float(frame.groupby("asset")[col].mean().mean()) if len(frame) else None


def scores(frame):
    return {m: math.sqrt(aggregate(frame.assign(loss=(frame[m]-frame.y)**2), "loss"))
            for m in ("B0", "B1", "B2", "ETF_mean")}


def rmse_blocks(frame, axis, length):
    rng = np.random.default_rng(20261004)
    ix = {d: i for i, d in enumerate(axis)}
    position = frame.date.map(ix).to_numpy(int)
    assets = sorted(frame.asset.unique())
    asset_masks = [frame.asset.to_numpy() == a for a in assets]
    losses = [(frame[m].to_numpy()-frame.y.to_numpy())**2 for m in ("B1", "B2")]
    draws, invalid = [], 0
    for _ in range(1000):
        starts = rng.integers(0, len(axis), int(np.ceil(len(axis)/length)))
        chosen = ((starts[:, None] + np.arange(length)) % len(axis)).ravel()[:len(axis)]
        count = np.bincount(chosen, minlength=len(axis))[position]
        if any(count[mask].sum() == 0 for mask in asset_masks):
            invalid += 1
            continue
        mse = [np.mean([count[mask] @ loss[mask] / count[mask].sum() for mask in asset_masks])
               for loss in losses]
        draws.append(float(np.sqrt(mse[0])-np.sqrt(mse[1])))
    return {"length": length, "draws": 1000, "seed": 20261004, "invalid": invalid,
            "lo": float(np.quantile(draws, .025)), "hi": float(np.quantile(draws, .975)),
            "scope": "synchronised full evaluation date axis, equal ETF; finite dependence sensitivity, not proof"}


def core(target):
    folder = RAW / target / "core-01"
    result, checked, contract = (read(folder / f) for f in ("result.json", "preflight.json", "contract.json"))
    obs = checked["observations"]
    preds = pd.DataFrame(result["predictions"])
    training, means = [], {}
    fit_details = {(r["fold"], r["model"]): r for r in result["execution"]["fit_details"]}
    max_saved_difference = 0.0
    state_means = {}
    for i, fold in enumerate(contract["split"]["folds"]):
        train = [r for r in obs if r["eligible"] and r["date"] <= fold["train_end"] and r["label_end"] < fold["eval_start"]]
        tf = pd.DataFrame([{**r["features"], "asset": r["asset"], "date": r["date"], "y": r["y"]} for r in train])
        means[str(i)] = tf.groupby("asset").y.mean().to_dict()
        state_means[str(i)] = {state: aggregate(pd.DataFrame([{ "asset": r["asset"], "y": r["y"]} for r in train if r["week20_state"] == state]), "y") for state in ("green", "black", "gray")}
        tf["ETF_mean"] = tf.asset.map(means[str(i)])
        tf["B0"] = aggregate(tf, "y")
        pf = preds[preds.fold.astype(str) == str(i)]
        lookup = {r["id"]: r for r in obs}
        for model in ("B1", "B2"):
            details = fit_details[(str(i), model)]
            cols = details["features"]
            mean, std, coefficient = (np.asarray(details[k]) for k in ("mean", "std", "coef"))
            tf[model] = (tf[cols].to_numpy()-mean)/std @ coefficient + details["intercept"]
            px = np.asarray([[lookup[pid]["features"][c] for c in cols] for pid in pf.id])
            recovered = (px-mean)/std @ coefficient + details["intercept"]
            max_saved_difference = max(max_saved_difference, float(np.max(np.abs(recovered-pf[model].to_numpy()))))
        training.append({"fold": str(i), "rows": len(tf), "dates": tf.date.nunique(), "rmse": scores(tf)})
    preds["ETF_mean"] = [means[str(row.fold)][row.asset] for row in preds.itertuples()]
    lookup_all = {r["id"]:r for r in obs}
    preds["X_only"] = [state_means[str(row.fold)][lookup_all[row.id]["week20_state"]] for row in preds.itertuples()]
    assert preds.X_only.notna().all()
    overall = scores(preds)
    for item in result["performance"]:
        if item["metric"] == "RMSE":
            assert abs(item["value"]-overall[item["model"]]) < 1e-10
    assert max_saved_difference < 1e-10
    axis = [d for d in contract["calendar"] if any(f["eval_start"] <= d <= f["eval_end"] for f in contract["split"]["folds"])]
    subsets = {}
    for name, sub in [("all", preds), *[("year_"+str(y), g) for y, g in preds.groupby(preds.date.str[:4])],
                      *[("asset_"+a, g) for a, g in preds.groupby("asset")],
                      *[("without_"+a, preds[preds.asset != a]) for a in sorted(preds.asset.unique())]]:
        value = scores(sub)
        subsets[name] = {"rows": len(sub), "dates": int(sub.date.nunique()), "rmse": value,
                         "B1_minus_B2": value["B1"]-value["B2"],
                         "B2_beats_ETF_mean": value["B2"] < value["ETF_mean"]}
    return {"files": {f: sha(folder/f) for f in ("result.json", "contract.json", "receipt.json")},
            "fits": result["execution"]["fits"], "training": training, "training_means": means, "training_state_means": state_means,
            "factor_only_rmse": float(np.sqrt(aggregate(preds.assign(loss=(preds.X_only-preds.y)**2), "loss"))),
            "subsets": subsets, "blocks": [rmse_blocks(preds, axis, n) for n in (20, 60)],
            "coefficient_readback_max_difference": max_saved_difference}, checked, preds


def describe(frame):
    metrics = ["return", "up", "return_over5", "mae", "mfe", "drawdown", "mae_over5", "mae_over10", "mae_over15", "return_below5", "return_below10", "return_below15"]
    if not len(frame):
        return {"rows": 0, "dates": 0, "assets": 0}
    result = {"rows": len(frame), "dates": int(frame.date.nunique()), "assets": int(frame.asset.nunique()),
              "metrics": {m: aggregate(frame, m) for m in metrics},
              "pooled_median_return": float(frame["return"].median()),
              "per_asset": {a: {"rows":len(g), "dates":int(g.date.nunique()),
                  "mean_return":float(g["return"].mean()), "median_return":float(g["return"].median()),
                  "mean_mae":float(g.mae.mean()), "up_pct":float(g.up.mean())}
                  for a,g in frame.groupby("asset")}}
    result["metrics"]["mean_mfe_over_mean_mae"] = (result["metrics"]["mfe"] / result["metrics"]["mae"]
                                                     if result["metrics"]["mae"] else None)
    return result


def iso(day):
    from datetime import date
    return date.fromisoformat(day).isocalendar()[:2]


def independent_features(panel, observations):
    """Manual week grouping/seed recurrence, independent of the new adapter."""
    from datetime import date
    from collections import defaultdict
    from statistics import stdev
    prices = {(b["asset"], b["date"]): b for b in panel["bars"]}
    dates = panel["calendar"]
    grouped = defaultdict(list)
    for d in dates:
        grouped[iso(d)].append(d)
    keys = sorted(grouped)
    first_partial = date.fromisoformat(dates[0]).weekday() != 0
    expected, first_ready = {}, {}
    numerical_error = 0.0
    state_mismatches = timing_mismatches = 0
    for asset in sorted({r["asset"] for r in observations}):
        weekly = {}
        sequence = []
        ema = None
        for k in keys:
            bars = [prices.get((asset, d)) for d in grouped[k]]
            good = (not (k == keys[0] and first_partial) and
                    all(b and b.get("status") == "quoted" and b.get("action_known") is True for b in bars))
            if not good:
                sequence, ema = [], None
                weekly[k] = None
                continue
            sequence.append(float(bars[-1]["close"]))
            if len(sequence) == 20:
                ema = sum(sequence)/20
            elif len(sequence) > 20:
                ema = (2/21)*sequence[-1] + (19/21)*ema
            n = len(sequence)
            if n >= 120:
                close, lag = sequence[-1], sequence[-21]
                state = "green" if close > ema and close > lag else "black" if close < ema and close < lag else "gray"
                weekly[k] = {"state": state, "date": grouped[k][-1], "count": n,
                             "week_ret20": 100*(close/sequence[-21]-1),
                             "week_ret60": 100*(close/sequence[-61]-1)}
            else:
                weekly[k] = None
        closes, e20, e60 = [], None, None
        for day in dates:
            b = prices.get((asset, day))
            if not b or b.get("status") != "quoted" or b.get("action_known") is not True:
                closes, e20, e60 = [], None, None
                continue
            closes.append(float(b["close"]))
            n = len(closes)
            if n == 20:
                e20 = sum(closes)/20
            elif n > 20:
                e20 = (2/21)*closes[-1] + (19/21)*e20
            if n == 60:
                e60 = sum(closes)/60
            elif n > 60:
                e60 = (2/61)*closes[-1] + (59/61)*e60
            previous = [k for k in keys if k < iso(day)]
            wk = weekly[previous[-1]] if previous else None
            if n < 252 or wk is None:
                continue
            first_ready.setdefault(asset, day)
            def color(e, lag):
                return "green" if closes[-1] > e and closes[-1] > lag else "black" if closes[-1] < e and closes[-1] < lag else "gray"
            c20, c60 = color(e20, closes[-21]), color(e60, closes[-61])
            # EMA20 previous value reconstructed from the current recurrence.
            e20previous = (e20-(2/21)*closes[-1])/(19/21)
            expected[asset+'|'+day] = {**wk, "daily20": c20, "features": {
                "color20_green": int(c20 == "green"), "color20_black": int(c20 == "black"),
                "color60_green": int(c60 == "green"), "color60_black": int(c60 == "black"),
                "ema20_up": int(e20 > e20previous), "ret20": 100*(closes[-1]/closes[-21]-1),
                "ret60": 100*(closes[-1]/closes[-61]-1),
                "vol20": stdev(math.log(closes[j]/closes[j-1]) for j in range(n-20, n))*math.sqrt(252)*100,
                "week_ret20": wk["week_ret20"], "week_ret60": wk["week_ret60"],
                "week20_green": int(wk["state"] == "green"), "week20_black": int(wk["state"] == "black")}}
    qualified = 0
    for r in observations:
        e = expected.get(r["id"])
        assert (r["feature_reason"] is None) == (e is not None), r["id"]
        if e is None:
            continue
        qualified += 1
        state_mismatches += int(r["week20_state"] != e["state"])
        timing_mismatches += int(r["last_completed_week_date"] != e["date"])
        assert iso(r["last_completed_week_date"]) < iso(r["date"])
        for name, value in e["features"].items():
            numerical_error = max(numerical_error, abs(value-r["features"][name]))
    assert numerical_error < 1e-9 and not state_mismatches and not timing_mismatches
    return {"scheduled_rows": len(observations), "qualified_rows": qualified,
            "first_ready_by_asset": first_ready, "feature_max_absolute_difference": numerical_error,
            "state_mismatches": state_mismatches, "week_availability_mismatches": timing_mismatches,
            "source_price_values_uploaded": False}


def main():
    cores, checked = {}, None
    for target in ("return", "risk"):
        cores[target], checked, _ = core(target)
    assert sum(v["fits"] for v in cores.values()) == 8
    c = read(RAW/"return/core-01/contract.json")
    panel_path = ROOT/c["data"]["path"]
    assert sha(panel_path) == c["data"]["sha256"]
    panel = read(panel_path)
    observations = checked["observations"]
    manual = independent_features(panel, observations)
    calendar = panel["calendar"]
    ix = {d: i for i,d in enumerate(calendar)}
    prices = {(b["asset"],b["date"]): b for b in panel["bars"]}
    rows, label_errors = [], {"return": 0.0, "risk": 0.0}
    return_obs = {r["id"]: r for r in read(RAW/"return/core-01/preflight.json")["observations"]}
    for r in observations:
        if r["feature_reason"] is not None:
            continue
        i = ix[r["date"]]
        for h in (5,10,20,60,120):
            if i+h+1 >= len(calendar):
                continue
            bars = [prices.get((r["asset"],calendar[j])) for j in range(i+1,i+h+2)]
            if any(not b or b.get("status") != "quoted" or b.get("action_known") is not True for b in bars):
                continue
            values = np.asarray([b["close"] for b in bars], float)
            ret = float(100*(values[-1]/values[0]-1))
            mae = float(100*max(0,1-values.min()/values[0]))
            mfe = float(100*max(0,values.max()/values[0]-1))
            dd = float(100*np.max(1-values/np.maximum.accumulate(values)))
            if h == 20 and r["eligible"]:
                label_errors["risk"] = max(label_errors["risk"],abs(mae-r["y"]))
                label_errors["return"] = max(label_errors["return"],abs(ret-return_obs[r["id"]]["y"]))
            rows.append({"asset":r["asset"],"date":r["date"],"end":calendar[i+h+1],"horizon":h,
                "weekstate":r["week20_state"],"daystate":manual_daystate(r),
                "return":ret,"mae":mae,"mfe":mfe,"drawdown":dd,
                "up":100*int(ret>0),"return_over5":100*int(ret>5),
                "return_below5":100*int(ret < -5),"return_below10":100*int(ret < -10),"return_below15":100*int(ret < -15),
                "mae_over5":100*int(mae>5),"mae_over10":100*int(mae>10),"mae_over15":100*int(mae>15)})
    assert max(label_errors.values()) < 1e-10
    frame = pd.DataFrame(rows)
    groups, conditions = {}, {}
    for h, hf in frame.groupby("horizon"):
        for period,(start,end) in {"all":("2022-01-04","2026-06-30"),**PERIODS}.items():
            part = hf[(hf.date>=start)&(hf.date<=end)&(hf.end<=end)]
            key=f"{int(h)}|{period}"
            groups[key] = {"baseline": describe(part), "states": {s:describe(part[part.weekstate==s]) for s in ("green","black","gray")}}
            if h == 20:
                conditions[key] = {day: {"baseline":describe(part[part.daystate==day]),
                    "week_states":{s:describe(part[(part.daystate==day)&(part.weekstate==s)]) for s in ("green","black","gray")}}
                    for day in ("green","black","gray")}
    state_runs = {}
    for asset,g in frame[frame.horizon==20].sort_values(["asset","date"]).groupby("asset"):
        counts = {s:0 for s in ("green","black","gray")}
        last_state, last_index = None, None
        for r in g.itertuples():
            current = ix[r.date]
            if last_index is None or current != last_index+1 or r.weekstate != last_state:
                counts[r.weekstate] += 1
            last_state, last_index = r.weekstate, current
        state_runs[asset] = counts
    put(RAW/"analysis.json", {"definition_ref":read(RAW/"brief.json")["ref"], "core":cores,
        "groups":groups,"conditional_groups":conditions,"independent_features":manual,
        "descriptive_state_runs": {"counts_by_asset":state_runs,
            "definition":"runs of identical prior-week state on consecutive included mature daily observations; not LEI trend identity, trade opportunities or independent evidence"},
        "direct_target_max_difference":label_errors,
        "budget":{"real_ols_fits":8,"max_real_ols_fits":8,"new_source_requests":0,"market_requests":0,"paid_requests":0,
                  "auxiliary_training_mean_estimators":"per target/fold overall,ETF and color-only means; no additional OLS; registered before results"},
        "limits":["all history already seen; later periods not blind","four ETFs only","weekly known-price expression",
                  "previous ISO week conservative release; not exact simultaneous color-change event","actual historical arrival/actions completeness unknown",
                  "capital/opportunity trading/live profit unmeasured"]})
    print(json.dumps({"independent_features":manual,"label_error":label_errors,"core":{k:v["subsets"]["all"] for k,v in cores.items()}},ensure_ascii=False))


def manual_daystate(row):
    f=row["features"]
    return "green" if f["color20_green"] else "black" if f["color20_black"] else "gray"


if __name__ == "__main__":
    main()
