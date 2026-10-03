"""Three frozen, causal ETF risk-shape expressions for research only."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import math
import statistics

import pandas as pd

from lei_signal.research.factor_lab.benchmarks import local_features
from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel

KIND = "risk_shape_information"
ANCHOR = ASSETS[0]
REFS = {
    "vol_instability20": "research.risk.vol_instability20@1.0.0",
    "beta_asymmetry60": "research.risk.beta_asymmetry60@1.0.0",
    "negative_cluster60": "research.risk.negative_cluster60@1.0.0",
}
BASELINE_FEATURES = ("S", "E", "return1", "return20", "return60", "volatility5",
    "volatility20", "volatility60", "market_return20", "market_volatility20", "beta60",
    "relative_return20", "negative_fraction60", "downside_rms60", "return_autocorr1_60",
    "current_negative_run", "asset_510500", "asset_588000")
SOLO_FEATURES = ("asset_510500", "asset_588000")
FOLDS = [
    {"train_end": "2024-12-31", "eval_start": "2025-01-02", "eval_end": "2025-12-31"},
    {"train_end": "2025-12-31", "eval_start": "2026-01-05", "eval_end": "2026-06-30"},
]


def _std(xs):
    return statistics.stdev(xs) if len(xs) >= 2 else None


def _slope(xs, ys):
    if len(xs) < 2:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    den = sum((x-mx)**2 for x in xs)
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/den if den/(len(xs)-1) > 1e-12 else None


def _corr(xs, ys):
    sx, sy = _std(xs), _std(ys)
    if sx is None or sy is None or sx <= 1e-12 or sy <= 1e-12:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/((len(xs)-1)*sx*sy)


def candidate_values(asset_close, anchor_close):
    """Use aligned prices ending at t; returns are percentage points."""
    if len(asset_close) != len(anchor_close) or len(asset_close) < 61:
        return {name: None for name in REFS}
    own = [100*(b/a-1) for a,b in zip(asset_close[-61:-1], asset_close[-60:])]
    market = [100*(b/a-1) for a,b in zip(anchor_close[-61:-1], anchor_close[-60:])]
    v5 = [_std(own[i-4:i+1]) for i in range(40,60)]
    mean_v = statistics.mean(v5)
    instability = _std(v5)/mean_v if mean_v > 1e-12 else None
    down = [i for i,x in enumerate(market) if x < 0]
    up = [i for i,x in enumerate(market) if x > 0]
    down_beta = _slope([market[i] for i in down], [own[i] for i in down]) if len(down)>=10 else None
    up_beta = _slope([market[i] for i in up], [own[i] for i in up]) if len(up)>=10 else None
    transitions = list(zip((r<0 for r in own[:-1]), (r<0 for r in own[1:])))
    neg = [current for previous,current in transitions if previous]
    nonneg = [current for previous,current in transitions if not previous]
    cluster = ((sum(neg)/len(neg) - sum(nonneg)/len(nonneg))
               if len(neg)>=5 and len(nonneg)>=5 else None)
    return {"vol_instability20": instability,
            "beta_asymmetry60": down_beta-up_beta if down_beta is not None and up_beta is not None else None,
            "negative_cluster60": cluster}


def baseline_values(asset_close, anchor_close, state=None):
    if len(asset_close) != len(anchor_close) or len(asset_close)<61:
        return None
    own = [100*(b/a-1) for a,b in zip(asset_close[-61:-1],asset_close[-60:])]
    market = [100*(b/a-1) for a,b in zip(anchor_close[-61:-1],anchor_close[-60:])]
    ac = _corr(own[-60:-1],own[-59:])
    beta = _slope(market,own)
    if ac is None or beta is None:
        return None
    if state is None:
        state=local_features(pd.DataFrame({"close":asset_close}),20).iloc[-1]
    run=0
    for value in reversed(own):
        if value>=0: break
        run+=1
    return {"S":int(state["S"]), "E":int(state["E"]),
        "return1":own[-1], "return20":100*(asset_close[-1]/asset_close[-21]-1),
        "return60":100*(asset_close[-1]/asset_close[-61]-1),
        "volatility5":_std(own[-5:]), "volatility20":_std(own[-20:]),
        "volatility60":_std(own), "market_return20":100*(anchor_close[-1]/anchor_close[-21]-1),
        "market_volatility20":_std(market[-20:]), "beta60":beta,
        "relative_return20":100*(asset_close[-1]/asset_close[-21]-anchor_close[-1]/anchor_close[-21]),
        "negative_fraction60":sum(r<0 for r in own)/60,
        "downside_rms60":math.sqrt(sum(min(r,0)**2 for r in own)/60),
        "return_autocorr1_60":ac, "current_negative_run":run}


def _validate(payload, contract):
    feature,target=contract["feature"],contract["target"]
    ref=feature.get("definition_ref")
    if (feature.get("kind")!=KIND or ref not in REFS.values() or
        feature.get("lookback")!=60 or feature.get("anchor_asset")!=contract["universe"]["assets"][0] or
        feature.get("warmup")!=252 or feature.get("missing_policy")!="segmented" or
        feature.get("comparison_mode") not in {"main","solo"} or
        feature.get("candidate")!=next((name for name,value in REFS.items() if value==ref),None)):
        raise ValueError("risk shape requires exact card, comparison mode and segmented252")
    if (target.get("kind")!="mae" or target.get("start_offset")!=1 or target.get("end_offset")!=21 or
        target.get("entry_field")!="close" or target.get("path_field")!="close" or
        target.get("unit")!="percentage_point" or target.get("price_measure")!="economic_price"):
        raise ValueError("risk shape freezes t+1..t+21 closing MAE")
    if contract["question"].get("sampling")!="daily":
        raise ValueError("daily sampling required")
    assets=contract["universe"]["assets"]
    if payload.get("data_mode")!="synthetic" and (assets!=list(ASSETS) or payload.get("price_series")!="economic_price" or contract["question"].get("period")!=["2022-01-04","2026-06-30"]):
        raise ValueError("real source requires frozen four ETFs, period and economic prices")
    if not isinstance(assets,list) or len(assets)<2 or len(assets)!=len(set(assets)):
        raise ValueError("unique ordered assets required")
    calendar=payload["calendar"]
    if not isinstance(calendar,list) or not calendar or calendar!=sorted(set(calendar)):
        raise ValueError("ordered unique calendar required")
    for day in calendar: shared._date(day)
    by_key={}
    for row in payload["bars"]:
        key=(row["asset"],row["date"])
        if key in by_key or key[0] not in assets or key[1] not in calendar or row.get("status") not in shared.STATUSES:
            raise ValueError("duplicate, unknown or out-of-scope quote")
        if row["status"]!="quoted" and any(row.get(k) is not None for k in ("open","high","low","close")):
            raise ValueError("nonquote has price")
        if row["status"]=="quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open","high","low","close")):
            raise ValueError("invalid price")
        if _known(row) and "decision_at" in row:
            at=shared._available(row["decision_at"])
            if at.date()<shared._date(row["date"]) or (at.date()==shared._date(row["date"]) and at.hour<15):
                raise ValueError("close observed before session end")
        by_key[key]=row
    return assets,calendar,by_key


def prepare_risk_shape_observations(payload,contract,*,compute_labels=False):
    if compute_labels and payload.get("data_mode")!="synthetic" and not (
        contract.get("permissions",{}).get("real_labels") is True and contract.get("permissions",{}).get("effect_authorized") is True):
        raise ValueError("real future labels require explicit effect authorization")
    assets,calendar,by_key=_validate(payload,contract)
    anchor=assets[0]
    end=max((date for _,date in by_key),default=calendar[0])
    if "decision_at" in payload:
        end=min(end,shared._available(payload["decision_at"]).date().isoformat())
    selected=shared._selected(calendar,end,contract["question"],payload)
    first,last=contract["question"]["period"]
    selected_name=next(name for name,ref in REFS.items() if ref==contract["feature"]["definition_ref"])
    # Common clock: either missing series breaks all states for every asset.
    rows_by_asset={asset:[dict(by_key.get((asset,d),{"asset":asset,"date":d,"status":"vendor_missing"})) for d in calendar] for asset in assets}
    label_rows={asset:[row for row in rows if row["date"]<=end] for asset,rows in rows_by_asset.items()} if compute_labels else None
    observations=[]; counts=Counter(); per_asset={}
    for asset in assets:
        asset_counts=Counter()
        states={}; segment=[]
        def commit_segment():
            if segment:
                frame=local_features(pd.DataFrame({"close":[r["close"] for _,r in segment]}),20)
                for (j,_),(_,state) in zip(segment,frame.iterrows()):
                    states[j]=state
                segment.clear()
        for j,day in enumerate(calendar):
            if day>end: break
            own=rows_by_asset[asset][j]; market=rows_by_asset[anchor][j]
            if _known(own) and _known(market): segment.append((j,own))
            else: commit_segment()
        commit_segment()
        own_close=[]; anchor_close=[]; run=0
        for i,day in enumerate(calendar):
            if day>end: break
            own=rows_by_asset[asset][i]; market=rows_by_asset[anchor][i]
            if _known(own) and _known(market):
                own_close.append(float(own["close"])); anchor_close.append(float(market["close"])); run+=1
            else:
                own_close=[]; anchor_close=[]; run=0; counts["gap_rows"]+=1
            if day not in selected or not first<=day<=last: continue
            base=baseline_values(own_close,anchor_close,states[i]) if run>=252 else None
            candidates=candidate_values(own_close,anchor_close) if run>=252 else {name:None for name in REFS}
            common=base is not None and all(v is not None and math.isfinite(v) for v in candidates.values())
            features={k:(base[k] if common else None) for k in BASELINE_FEATURES if not k.startswith("asset_")}
            for code in ASSETS[2:]: features["asset_"+code.split(".")[0]]=int(asset==code or (payload.get("data_mode")=="synthetic" and asset=="synthetic-B" and code==ASSETS[2]))
            features.update({name:(value if common else None) for name,value in candidates.items()})
            excluded=asset==anchor
            y,label_end,target_reason=(shared._label(label_rows[asset],i,target=contract["target"])
                if compute_labels and not excluded else (None,None,"anchor_excluded" if excluded else "not_computed"))
            reason="anchor_excluded" if excluded else None if common else "joint_252_or_feature_missing"
            eligible=bool(not excluded and common and (y is not None if compute_labels else True))
            observations.append({"id":f"{asset}|{day}","asset":asset,"date":day,"stratum":f"{asset}|{day[:4]}",
                "features":features,"eligible":eligible,"y":y,"label_end":label_end,
                "label_reason":reason or target_reason,"feature_reason":reason,
                "target_label_reason":target_reason,"tested_condition":None,
                "continuous_real_ohlc":run,"ready_252":common,
                "definition_ref":contract["feature"]["definition_ref"]})
            counts["scheduled"]+=1; counts["anchor_excluded"]+=int(excluded)
            counts["common_ready"]+=int(common and not excluded); counts["eligible"]+=int(eligible)
            asset_counts["scheduled"]+=1; asset_counts["anchor_excluded"]+=int(excluded)
            asset_counts["common_ready"]+=int(common and not excluded)
            asset_counts["eligible"]+=int(eligible)
            if reason != "anchor_excluded":
                asset_counts[reason or "feature_ready"]+=1
        per_asset[asset]=dict(asset_counts)
    return {"observations":observations,"coverage":{**counts,"per_asset":per_asset},
        "warnings":["价格风险形态仅供回顾性研究；历史资料到达及行动完整性未知。"]}


def build_qualification(payload,contract,root:Path):
    source=qualify_top_panel(payload,contract,root)
    prepared=prepare_risk_shape_observations(payload,contract,compute_labels=False)
    rows=prepared["observations"]; calendar=payload["calendar"]; index={d:i for i,d in enumerate(calendar)}
    def label_end(row):
        j=index[row["date"]]+21
        return calendar[j] if j<len(calendar) else None
    folds=[]
    for fold in contract["split"]["folds"]:
        train=[r for r in rows if r["eligible"] and r["date"]<=fold["train_end"] and label_end(r) and label_end(r)<fold["eval_start"]]
        evaluation=[r for r in rows if r["eligible"] and fold["eval_start"]<=r["date"]<=fold["eval_end"] and label_end(r) and label_end(r)<=fold["eval_end"]]
        folds.append({"fold":fold,"train":len(train),"evaluation":len(evaluation),
            "train_dates":len({r["date"] for r in train}),"evaluation_dates":len({r["date"] for r in evaluation})})
    return {"data_sha256":contract["data"]["sha256"],"outcome_values_used_for_design":False,
        "source_quality":source["quality"],"source_warnings":source["warnings"],
        "coverage":prepared["coverage"],"counts":{"assets":len(contract["universe"]["assets"]),
            "observations":len(rows),"dates":len({r["date"] for r in rows}),"episodes":None},
        "scientific_support":{"folds":folds,"model_feature_count":
            len(BASELINE_FEATURES if contract["feature"]["comparison_mode"]=="main" else SOLO_FEATURES)+1,
            "unknown_reasons":dict(Counter(r["feature_reason"] for r in rows if r["feature_reason"])),
            "note":"Only current features and calendar maturity; future price outcomes unread."}}
