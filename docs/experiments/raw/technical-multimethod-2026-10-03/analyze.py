"""Finite complementary analyses; no new fit, request, or chosen threshold."""
from pathlib import Path
import hashlib
import json
import math
import warnings

import numpy as np
import pandas as pd

from lei_signal.research.alphalens_component import component_analysis
from lei_signal.research.momentum_prototype import rank_diagnostic

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
    rng = np.random.default_rng(20261003)
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
    return {"length": length, "draws": 1000, "seed": 20261003, "invalid": invalid,
            "lo": float(np.quantile(draws, .025)), "hi": float(np.quantile(draws, .975)),
            "scope": "synchronised full evaluation date axis, equal ETF; finite dependence sensitivity, not proof"}


def core(target):
    folder = RAW / "persistence" / target / "core-01"
    result, checked, contract = (read(folder / f) for f in ("result.json", "preflight.json", "contract.json"))
    obs = checked["observations"]
    preds = pd.DataFrame(result["predictions"])
    training, means = [], {}
    fit_details = {(r["fold"], r["model"]): r for r in result["execution"]["fit_details"]}
    max_saved_difference = 0.0
    for i, fold in enumerate(contract["split"]["folds"]):
        train = [r for r in obs if r["eligible"] and r["date"] <= fold["train_end"] and r["label_end"] < fold["eval_start"]]
        tf = pd.DataFrame([{**r["features"], "asset": r["asset"], "date": r["date"], "y": r["y"]} for r in train])
        means[str(i)] = tf.groupby("asset").y.mean().to_dict()
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
            "fits": result["execution"]["fits"], "training": training, "training_means": means,
            "subsets": subsets, "blocks": [rmse_blocks(preds, axis, n) for n in (20, 60)],
            "coefficient_readback_max_difference": max_saved_difference}, checked, preds


def describe(frame):
    metrics = ["return", "up", "return_over5", "mae", "mfe", "drawdown", "mae_over5", "mae_over10", "mae_over15", "return_below5", "return_below10", "return_below15"]
    if not len(frame):
        return {"rows": 0, "dates": 0, "assets": 0}
    result = {"rows": len(frame), "dates": int(frame.date.nunique()), "assets": int(frame.asset.nunique()),
              "metrics": {m: aggregate(frame, m) for m in metrics}}
    result["metrics"]["mean_mfe_over_mean_mae"] = (result["metrics"]["mfe"] / result["metrics"]["mae"]
                                                     if result["metrics"]["mae"] else None)
    return result


def main():
    cores, checked = {}, None
    for target in ("return", "risk"):
        cores[target], checked, _ = core(target)
    brief = read(RAW/"brief.json")
    assert sum(v["fits"] for v in cores.values()) == 8
    contract = read(RAW/"persistence/return/core-01/contract.json")
    panel_path = ROOT / contract["data"]["path"]
    assert sha(panel_path) == contract["data"]["sha256"]
    panel = read(panel_path)
    calendar = panel["calendar"]
    day_ix = {d: i for i, d in enumerate(calendar)}
    prices = {(b["asset"], b["date"]): b for b in panel["bars"]}
    valid_obs = [r for r in checked["observations"] if r["feature_reason"] is None]
    rows, label_audit = [], 0.0
    # Direct close paths; no high/low, future peak used as a predictor, or filter.
    for row in valid_obs:
        i = day_ix[row["date"]]
        for horizon in (5, 10, 20, 60, 120):
            if i+horizon+1 >= len(calendar):
                continue
            bars = [prices.get((row["asset"], calendar[j])) for j in range(i+1, i+horizon+2)]
            if any(b is None or b.get("status") != "quoted" or b.get("action_known") is not True for b in bars):
                continue
            values = np.asarray([b["close"] for b in bars], float)
            ret = 100*(values[-1]/values[0]-1)
            mae = 100*max(0, 1-values.min()/values[0])
            mfe = 100*max(0, values.max()/values[0]-1)
            dd = float(100*np.max(1-values/np.maximum.accumulate(values)))
            if horizon == 20 and row["eligible"]:
                label_audit = max(label_audit, abs(mae-row["y"]))
            rows.append({"asset": row["asset"], "date": row["date"], "end": calendar[i+horizon+1], "horizon": horizon,
                "factor": row["features"]["ema20_up_share20"], "ret20": row["features"]["ret20"],
                "color20": row["color20"], "bull": row["bull_group"],
                "return": ret, "up": 100*int(ret>0), "return_over5": 100*int(ret>5),
                "return_below5": 100*int(ret < -5), "return_below10": 100*int(ret < -10), "return_below15": 100*int(ret < -15),
                "mae": mae, "mfe": mfe, "drawdown": dd,
                "mae_over5": 100*int(mae>5), "mae_over10": 100*int(mae>10), "mae_over15": 100*int(mae>15)})
    assert label_audit < 1e-10
    frame = pd.DataFrame(rows)
    frame["bin"] = pd.cut(frame.factor, [0,.25,.5,.75,1], labels=["0_to_25", "25_to_50", "50_to_75", "75_to_100"], include_lowest=True)
    summaries, ranks, conditions = {}, {}, {}
    for horizon, hf in frame.groupby("horizon"):
        for period, (start, end) in {"all": ("2022-01-04", "2026-06-30"), **PERIODS}.items():
            part = hf[(hf.date>=start)&(hf.date<=end)&(hf.end<=end)]
            key = f"{int(horizon)}|{period}"
            summaries[key] = {"baseline": describe(part), "bins": {str(b): describe(g) for b,g in part.groupby("bin", observed=True)}}
            ranks[key] = {}
            for asset,g in part.groupby("asset"):
                ranks[key][asset] = {target: rank_diagnostic(pd.DataFrame({"momentum": g.factor, "target": g[target]}))
                                    for target in ("return", "mae", "mfe")}
            if horizon==20:
                conditions[key] = {"color20_"+str(c): {"baseline": describe(g), "bins": {str(b): describe(s) for b,s in g.groupby("bin", observed=True)}} for c,g in part.groupby("color20")}
                conditions[key]["strict_bull"] = {"baseline": describe(part[part.bull]), "bins": {str(b): describe(s) for b,s in part[part.bull].groupby("bin", observed=True)}}
    hf = frame[frame.horizon==20].copy()
    af = hf.rename(columns={"return":"20D", "bin":"factor_quantile"})
    af["date"] = pd.to_datetime(af.date)
    af = af.set_index(["date","asset"])[["factor","factor_quantile","20D"]].sort_index()
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        upstream = component_analysis(af)
    ic = upstream["information_coefficient"]["20D"]
    max_rank_difference, constant_dates = 0.0, 0
    for day,g in hf.groupby("date"):
        native = rank_diagnostic(pd.DataFrame({"momentum":g.factor,"target":g["return"]}))["value"]
        candidate = ic.loc[pd.Timestamp(day)]
        if native is None:
            assert pd.isna(candidate)
            constant_dates += 1
        else:
            max_rank_difference = max(max_rank_difference, abs(native-float(candidate)))
    assert max_rank_difference < 1e-12
    group_means = upstream["mean_return_by_date_and_quantile"]["20D"]
    native_means = af.groupby(["factor_quantile",af.index.get_level_values("date")], observed=True)["20D"].mean()
    differences = (group_means-native_means.reindex(group_means.index)).abs()
    assert float(differences.max()) < 1e-10
    upstream_periods = {}
    for period,(start,end) in {"all":("2022-01-04","2026-06-30"),**PERIODS}.items():
        ids = hf[(hf.date>=start)&(hf.date<=end)&(hf.end<=end)].date.unique()
        selected = ic.reindex(pd.to_datetime(ids))
        upstream_periods[period] = {"dates":len(selected), "valid_dates":int(selected.notna().sum()), "mean_rank_relationship":float(selected.mean()),
                                  "positive_dates":int((selected>0).sum()), "negative_dates":int((selected<0).sum()), "missing_dates":int(selected.isna().sum())}
    report = {"stage":"completed finite EMA studies; adjacent-event source qualification only",
        "definition_refs": [s["ref"] for s in brief["studies"]], "source_sha256":brief["source_sha256"], "input_sha256":sha(panel_path),
        "core":cores, "groups":summaries,"time_ranks_by_etf":ranks,"conditional_groups":conditions,
        "open_source":{"repository":"https://github.com/stefan-jansen/alphalens-reloaded", "commit":"f0a07c22d554e4b4036983cc80320b432714fe7e",
                       "same_date_rank":upstream_periods, "constant_factor_dates":constant_dates,
                       "rank_readback_max_difference":max_rank_difference,"group_mean_max_difference":float(differences.max()),
                       "warnings":sorted({str(w.message) for w in emitted}),
                       "stderr_used_for_inference":False,"frame_rows":len(hf),"frame_dates":hf.date.nunique(),
                       "meaning":"four fixed ETFs same date;20D is20 trading intervals, not calendar days; not deciles or an ETF portfolio"},
        "direct_risk_target_max_difference":label_audit,"budget":{"real_fits":8,"max_fits":12,"source_requests":6,"market_requests":0,"paid_requests":0},
        "limits":["all history already seen;later years are time-separated reuse,not blind test","existing price transformation,not independent new raw data",
                  "historical arrival and all corporate actions not proved","selection/rebalancing/execution/account/live profit not measured",
                  "four ETFs cannot support top10% vs top20% or universewide claims","event source gate stopped before outcomes;no event increment asserted"],
        "verdict":{"persistence":"本实验范围内未发现实际增量","transition":"证据不足"}}
    put(RAW/"analysis.json",report)
    print("completed", "real fits8", "groups",len(summaries), "rank readback",max_rank_difference, "risk direct error",label_audit)


if __name__=="__main__":
    main()
