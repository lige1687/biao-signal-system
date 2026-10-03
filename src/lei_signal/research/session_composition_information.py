"""Frozen same-ETF overnight/intraday economic-price composition; research only."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import math
import statistics

import pandas as pd

from lei_signal.research.factor_lab.benchmarks import local_features
from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel

KIND = "session_composition_information"
ANCHOR = ASSETS[0]
REFS = {"overnight_minus_intraday20": "research.price.overnight_minus_intraday20@1.0.0"}

BASELINE_FEATURES = ("S", "E", "return1", "return20", "return60", "volatility5",
    "volatility20", "volatility60", "market_return20", "market_volatility20", "beta60",
    "relative_return20", "negative_fraction60", "downside_rms60", "return_autocorr1_60",
    "current_negative_run", "asset_510500", "asset_588000")
SOLO_FEATURES = ("asset_510500", "asset_588000")
FOLDS = [
    {"train_end": "2024-12-31", "eval_start": "2025-01-02", "eval_end": "2025-12-31"},
    {"train_end": "2025-12-31", "eval_start": "2026-01-05", "eval_end": "2026-06-30"},
]


from .risk_shape_information import baseline_values


def candidate_values(closes, opens):
    """20 prior-close/open/close intervals ending at t, in log-change points.

    Economic OHLC includes effective split/cash actions using the source's
    retrospective close-known assumption. This is a price-index partition,
    not an actionable open or a self-financing intraday return.
    """
    name = "overnight_minus_intraday20"
    if len(closes) != len(opens) or len(closes) < 21:
        return {name: None}
    values = list(closes[-21:]) + list(opens[-20:])
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) or v <= 0 for v in values):
        return {name: None}
    return {name: 100 * math.fsum(math.log(o / previous) - math.log(current / o)
           for previous, o, current in zip(closes[-21:-1], opens[-20:], closes[-20:]))}


def _validate(payload, contract):
    feature,target=contract["feature"],contract["target"]
    ref=feature.get("definition_ref")
    if (feature.get("kind")!=KIND or ref not in REFS.values() or
        feature.get("lookback")!=20 or feature.get("anchor_asset")!=contract["universe"]["assets"][0] or
        feature.get("warmup")!=252 or feature.get("missing_policy")!="segmented" or
        feature.get("comparison_mode") not in {"main","solo"} or
        feature.get("candidate")!=next((name for name,value in REFS.items() if value==ref),None)):
        raise ValueError("session composition requires exact card, comparison mode and segmented252")
    if (target.get("kind")!="mae" or target.get("start_offset")!=1 or target.get("end_offset")!=21 or
        target.get("entry_field")!="close" or target.get("path_field")!="close" or
        target.get("unit")!="percentage_point" or target.get("price_measure")!="economic_price"):
        raise ValueError("session composition freezes t+1..t+21 closing MAE")
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


def prepare_session_composition_observations(payload,contract,*,compute_labels=False):
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
        own_close=[]; own_open=[]; anchor_close=[]; run=0
        for i,day in enumerate(calendar):
            if day>end: break
            own=rows_by_asset[asset][i]; market=rows_by_asset[anchor][i]
            if _known(own) and _known(market):
                own_close.append(float(own["close"])); own_open.append(float(own["open"])); anchor_close.append(float(market["close"])); run+=1
            else:
                own_close=[]; own_open=[]; anchor_close=[]; run=0; counts["gap_rows"]+=1
            if day not in selected or not first<=day<=last: continue
            base=baseline_values(own_close,anchor_close,states[i]) if run>=252 else None
            candidates=candidate_values(own_close,own_open) if run>=252 else {name:None for name in REFS}
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
        "warnings":["隔夜/日内经济价格构成仅作回顾性研究；行动现金在经济OHLC同时加入，不代表可成交开盘或真实资金路径；历史到达及行动完整性未知。"]}


def build_qualification(payload,contract,root:Path):
    source=qualify_top_panel(payload,contract,root)
    prepared=prepare_session_composition_observations(payload,contract,compute_labels=False)
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
