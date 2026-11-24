"""Fixed retrospective price/volume path expressions for ETF research.

No LEI trading rule, account return, or vendor arrival time is inferred here.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import pandas as pd

from lei_signal.research.factor_lab.benchmarks import local_features
from lei_signal.research.risk_shape_information import baseline_values
from lei_signal.research.session_composition_information import candidate_values as session_values
from lei_signal.research import workflow_inputs as shared


KIND = "price_volume_path_information"
ASSETS = ("510300.SS", "510050.SS", "510500.SS", "588000.SS",
          "512480.SS", "512400.SS", "512800.SS", "512170.SS")
ANCHOR = ASSETS[0]
FORMULAS = ("range_mean", "close_location_mean", "wick_balance_mean",
            "volume_concentration", "log_volume_std", "log_volume_slope",
            "volume_close_location_excess", "volume_range_excess", "volume_wick_excess")
REFS = {f"{name}{n}": f"research.price_volume.{name}{n}@1.0.0"
        for name in FORMULAS for n in (20, 60)}
PRICE_ONLY = set(FORMULAS[:3])
PRICE_BASE = ("S", "E", "return1", "return20", "return60", "volatility5",
    "volatility20", "volatility60", "market_return20", "market_volatility20", "beta60",
    "relative_return20", "negative_fraction60", "downside_rms60", "return_autocorr1_60",
    "current_negative_run", "direction20", "overnight_minus_intraday20",
    "atr20_fraction", "today_range", "today_close_location")
IDENTITY = tuple("asset_" + a.split(".")[0] for a in ASSETS[1:])
BASELINE_FEATURES = PRICE_BASE + IDENTITY
FOLDS = [
    {"train_end": "2022-12-30", "eval_start": "2023-01-03", "eval_end": "2023-12-29"},
    {"train_end": "2023-12-29", "eval_start": "2024-01-02", "eval_end": "2024-12-31"},
    {"train_end": "2024-12-31", "eval_start": "2025-01-02", "eval_end": "2025-12-31"},
    {"train_end": "2025-12-31", "eval_start": "2026-01-05", "eval_end": "2026-06-30"},
]


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def day_values(row, previous_close):
    """Scale-invariant session values, only after a genuine prior quote."""
    if previous_close is None or not _number(previous_close):
        return None
    o, h, l, c = (row.get(k) for k in ("open", "high", "low", "close"))
    if not all(_number(v) for v in (o, h, l, c)):
        return None
    eps = 1e-12 * max(1.0, h)
    if l > h + eps or l - eps > min(o, c) or max(o, c) > h + eps:
        return None
    spread = max(0.0, h - l)
    if spread == 0:
        if max(abs(x - h) for x in (o, c, l)) > eps:
            return None
        k = w = 0.0
    else:
        k = (2*c-h-l)/spread
        w = ((h-max(o,c))-(min(o,c)-l))/spread
    tr = max(h-l, abs(h-previous_close), abs(l-previous_close))
    return {"range": spread/previous_close, "close_location": k,
            "wick_balance": w, "true_range": tr,
            "volume": row.get("volume") if _number(row.get("volume")) else None}


def candidate_values(days, lookback, *, volume_known=True):
    """Return all nine fixed formulas for one complete length-n suffix."""
    if len(days) < lookback:
        return {name: None for name in FORMULAS}
    window = days[-lookback:]
    if any(d is None for d in window):
        return {name: None for name in FORMULAS}
    ranges = [d["range"] for d in window]
    locations = [d["close_location"] for d in window]
    wicks = [d["wick_balance"] for d in window]
    means = {"range_mean": math.fsum(ranges)/lookback,
             "close_location_mean": math.fsum(locations)/lookback,
             "wick_balance_mean": math.fsum(wicks)/lookback}
    if not volume_known or any(not _number(d.get("volume")) for d in window):
        return {**means, **{name: None for name in FORMULAS[3:]}}
    volumes = [d["volume"] for d in window]
    total = math.fsum(volumes)
    weights = [v/total for v in volumes]
    logs = [math.log(v) for v in volumes]
    center = math.fsum(logs)/lookback
    denom = lookback*(lookback*lookback-1)/12
    slope = math.fsum((i-(lookback-1)/2)*(v-center) for i,v in enumerate(logs))/denom
    return {**means,
            "volume_concentration": lookback*math.fsum(p*p for p in weights)-1,
            "log_volume_std": math.sqrt(math.fsum((x-center)**2 for x in logs)/lookback),
            "log_volume_slope": slope*(lookback-1),
            "volume_close_location_excess": math.fsum(p*x for p,x in zip(weights,locations))-means["close_location_mean"],
            "volume_range_excess": math.fsum(p*x for p,x in zip(weights,ranges))-means["range_mean"],
            "volume_wick_excess": math.fsum(p*x for p,x in zip(weights,wicks))-means["wick_balance_mean"]}


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    selected = feature.get("candidate")
    if (feature.get("kind") != KIND or selected not in REFS or
            REFS[selected] != feature.get("definition_ref") or
            feature.get("lookback") != int(selected[-2:]) or
            feature.get("warmup") != 252 or feature.get("missing_policy") != "segmented" or
            feature.get("anchor_asset") != contract["universe"]["assets"][0]):
        raise ValueError("price-volume path requires exact fixed card and warmup")
    if (target.get("kind") != "mae" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("path_field") != "close" or target.get("unit") != "percentage_point" or
            target.get("price_measure") != "economic_price"):
        raise ValueError("first batch freezes t+1..t+21 closing downside")
    if payload.get("data_mode") != "synthetic" and (
            payload.get("price_series") != "economic_price" or
            contract["universe"]["assets"] != list(ASSETS) or
            contract["question"]["period"] != ["2022-01-04", "2026-06-30"]):
        raise ValueError("real first batch requires fixed eight-source panel")
    calendar = payload["calendar"]
    if calendar != sorted(set(calendar)) or not calendar:
        raise ValueError("calendar is not sorted unique")
    by_key = {}
    for row in payload["bars"]:
        key = row["asset"], row["date"]
        if key in by_key or key[0] not in contract["universe"]["assets"] or key[1] not in calendar:
            raise ValueError("duplicate or out-of-scope quote")
        if row.get("status") == "quoted" and not all(_number(row.get(k)) for k in ("open","high","low","close")):
            raise ValueError("invalid quoted price")
        by_key[key] = row
    return calendar, by_key


def prepare_observations(payload, contract, *, compute_labels=False):
    if compute_labels and payload.get("data_mode") != "synthetic" and not (
        contract.get("permissions", {}).get("real_labels") is True and
        contract.get("permissions", {}).get("effect_authorized") is True):
        raise ValueError("real labels require effect authorization")
    calendar, by_key = _validate(payload, contract)
    first, last = contract["question"]["period"]
    selected_name = contract["feature"]["candidate"]
    lookback = contract["feature"]["lookback"]
    assets = contract["universe"]["assets"]
    anchor_rows = [by_key.get((assets[0], d)) for d in calendar]
    observations, counts = [], Counter()
    per_asset = {}
    for asset in assets:
        rows = [by_key.get((asset, d), {"asset": asset, "date": d, "status": "vendor_missing"}) for d in calendar]
        states = {}
        segment = []
        def commit_segment():
            if segment:
                frame = local_features(pd.DataFrame({"close": [r["close"] for _,r in segment]}),20)
                for (j,_), (_, state) in zip(segment, frame.iterrows()):
                    states[j] = state
                segment.clear()
        for j,(r,m) in enumerate(zip(rows,anchor_rows)):
            if r and m and r.get("status")==m.get("status")=="quoted":segment.append((j,r))
            else:commit_segment()
        commit_segment()
        own_close=[];own_open=[];market_close=[];days=[];vol_run=0;tr_ema=None
        acount=Counter()
        for i,date in enumerate(calendar):
            own, market = rows[i], anchor_rows[i]
            quoted = bool(own and market and own.get("status")==market.get("status")=="quoted")
            if quoted:
                previous = own_close[-1] if own_close else None
                own_close.append(float(own["close"]));own_open.append(float(own["open"]));market_close.append(float(market["close"]))
                d = day_values(own,previous)
                if d is not None:
                    days.append(d)
                    if len(days)>60:days.pop(0)
                if own.get("volume_break") or d is None or d["volume"] is None:
                    vol_run=1 if d is not None and d["volume"] is not None else 0
                else:vol_run+=1
                if d is not None:
                    if tr_ema is None and len(days)>=20:
                        tr_ema=math.fsum(x["true_range"] for x in days[-20:])/20
                    elif tr_ema is not None:
                        tr_ema=(2/21)*d["true_range"]+(19/21)*tr_ema
            else:
                own_close=[];own_open=[];market_close=[];days=[];vol_run=0;tr_ema=None
            if not first<=date<=last:continue
            counts["scheduled"]+=1;acount["scheduled"]+=1
            price_ready=len(own_close)>=252 and len(market_close)>=252 and tr_ema is not None
            base=baseline_values(own_close,market_close,states.get(i)) if price_ready else None
            feature=None
            if base is not None and days:
                direction=math.fsum(int(b>a)-int(b<a) for a,b in zip(own_close[-21:-1],own_close[-20:]))/20
                overnight=session_values(own_close,own_open)["overnight_minus_intraday20"]
                today=days[-1]
                extra={"direction20":direction,"overnight_minus_intraday20":overnight,
                       "atr20_fraction":tr_ema/own_close[-1],"today_range":today["range"],
                       "today_close_location":today["close_location"]}
                feature={**base,**extra,**{name:int(asset==code) for name,code in zip(IDENTITY,ASSETS[1:])}}
                candidate=candidate_values(days,lookback,volume_known=vol_run>=lookback)[selected_name[:-2]]
                feature[selected_name]=candidate
            common=bool(feature and all(isinstance(feature.get(name),(int,float)) and
                math.isfinite(feature[name]) for name in BASELINE_FEATURES+(selected_name,)))
            y,label_end,target_reason=(shared._label(rows,i,target=contract["target"])
                if compute_labels else (None,None,"not_computed"))
            reason=None if common else "background_or_window_unavailable"
            if common:counts["feature_ready"]+=1;acount["feature_ready"]+=1
            eligible=bool(common and (y is not None if compute_labels else True))
            if eligible:counts["eligible"]+=1;acount["eligible"]+=1
            observations.append({"id":f"{asset}|{date}","asset":asset,"date":date,
                "stratum":f"{asset}|{date[:4]}","features":feature or {},"eligible":eligible,
                "y":y,"label_end":label_end,"label_reason":reason or target_reason,
                "feature_reason":reason,"target_label_reason":target_reason,
                "tested_condition":None,"definition_ref":contract["feature"]["definition_ref"]})
        per_asset[asset]=dict(acount)
    return {"observations":observations,"coverage":{**counts,"per_asset":per_asset},
        "warnings":["回溯经济价与官方日线只证明固定源内计算；历史到达、完整个股覆盖和全部成交量单位变化未知。"]}


def build_qualification(payload,contract,root:Path):
    path=Path(root)/contract["data"]["qualification"]["manifest_path"]
    q=json.loads(path.read_text())
    if q["status"]!="qualified_retrospective_8_etfs_only" or q["workflow_input"]["sha256"]!=contract["data"]["sha256"]:
        raise ValueError("prepared panel qualification/source hash mismatch")
    if len(q["field_evidence"])!=11 or q["prepared_rows"]!=len(payload["bars"]):
        raise ValueError("source manifest is incomplete")
    for entry in q["field_evidence"]:
        p=Path(root)/entry["path"]
        if p.stat().st_size!=entry["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest()!=entry["sha256"]:
            raise ValueError("source evidence changed: "+entry["path"])
    ready=prepare_observations(payload,contract,compute_labels=False)
    dates=payload["calendar"]
    index={d:i for i,d in enumerate(dates)}
    horizon=contract["target"]["end_offset"]
    folds=[]
    for f in contract["split"]["folds"]:
        train=[r for r in ready["observations"] if r["eligible"] and r["date"]<=f["train_end"] and
               index[r["date"]]+horizon<len(dates) and dates[index[r["date"]]+horizon]<f["eval_start"]]
        test=[r for r in ready["observations"] if r["eligible"] and f["eval_start"]<=r["date"]<=f["eval_end"] and
              index[r["date"]]+horizon<len(dates) and dates[index[r["date"]]+horizon]<=f["eval_end"]]
        folds.append({"fold":f,"train":len(train),"evaluation":len(test),
                      "train_dates":len({r["date"] for r in train}),"evaluation_dates":len({r["date"] for r in test})})
    return {"data_sha256":contract["data"]["sha256"],"outcome_values_used_for_design":False,
            "source_quality":q["quality"],"source_warnings":ready["warnings"],
            "coverage":ready["coverage"],"counts":{"assets":len(contract["universe"]["assets"]),
            "observations":len(ready["observations"]),"dates":len(set(r["date"] for r in ready["observations"])),"episodes":None},
            "scientific_support":{"folds":folds,"model_feature_count":len(contract["evaluator"]["baseline_features"])+1,
                "unknown_reasons":dict(Counter(r["feature_reason"] for r in ready["observations"] if r["feature_reason"])),
                "note":"Current features and calendar maturity only; no future price outcome values read."}}
