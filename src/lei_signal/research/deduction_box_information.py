"""Research-only, close-known future SMA20 deduction-price box.

The box uses t-19 through t-10 closes. Qualification never reads future prices.
It is a conditional risk-information proxy, not a trading trigger.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np

from . import workflow_inputs as shared

DEFINITION_REF = "research.trend.future_deduction_box20_10@1.0.0"
ASSETS = ("510300.SS", "510050.SS", "510500.SS", "588000.SS")
BASELINE = ("prior20high_distance", "ret20", "ema20_distance", "r1", "vol20",
            "sma60_up", "asset_510050", "asset_510500", "asset_588000")
WARMUP = 252


def qualify_deduction_panel(payload: dict, contract: dict, root: Path) -> dict:
    """Reuse V01's source mathematics with an explicit source-only contract."""
    from .volume_information import qualify_volume_panel
    source_contract = {
        "data": {**contract["data"], "qualification": {
            "adapter": "volume_etf_economic/1.0",
            "manifest_path": contract["data"]["qualification"]["manifest_path"]}},
        "universe": contract["universe"],
        "feature": {"kind": "volume_anomaly_information", "definition_ref":
                    "research.volume.abnormal20@1.0.0", "lookback": 20,
                    "warmup": 252, "missing_policy": "segmented"},
        "target": {"kind": "downside_event", "start_offset": 1,
                   "end_offset": 21, "entry_field": "close", "threshold": 5,
                   "price_measure": "economic_price"},
        "question": {"sampling": "daily"},
    }
    checked = qualify_volume_panel(payload, source_contract, root)
    return {"quality": checked["quality"], "warnings": [
        "逐行来源、行动与经济价格按V01来源数学重新核对；成交量不进入D01特征。",
        "历史资料到达时间和全部行动完整性未认证；仅作回顾性经济价格研究。"]}


def _known(row):
    return (row.get("status") == "quoted" and row.get("action_known") is True
            and all(shared._number(row.get(k)) for k in ("open", "high", "low", "close"))
            and row["low"] <= min(row["open"], row["close"])
            <= max(row["open"], row["close"]) <= row["high"])


def _validate(payload, contract):
    f, t = contract["feature"], contract["target"]
    if (f.get("kind") != "future_deduction_box_information" or
        f.get("definition_ref") != DEFINITION_REF or f.get("lookback") != 20 or
        f.get("box_horizon") != 10 or f.get("warmup") != WARMUP or
        f.get("missing_policy") != "segmented"):
        raise ValueError("D01 requires exact N20/K10/252 segmented research definition")
    if (t.get("kind") != "mae" or t.get("start_offset") != 1 or
        t.get("end_offset") != 21 or t.get("entry_field") != "close" or
        t.get("path_field", "close") != "close" or
        t.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("D01 requires t+1..t+21 closing-path MAE")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("D01 retains all scheduled daily observations")
    if payload.get("data_mode") != "synthetic" and payload.get("price_series") != "economic_price":
        raise ValueError("D01 needs qualified economic OHLC")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("calendar must be ordered unique dates")
    for day in calendar:
        shared._date(day)
    assets = contract["universe"]["assets"]
    if not isinstance(assets, list) or not assets or len(set(assets)) != len(assets):
        raise ValueError("assets must be ordered unique codes")
    if payload.get("data_mode") != "synthetic" and tuple(assets) != ASSETS:
        raise ValueError("D01 freezes four domestic ETF identities")
    by_key = {}
    for row in payload["bars"]:
        key = (row["asset"], row["date"])
        if key in by_key or row["asset"] not in assets or row["date"] not in calendar:
            raise ValueError("duplicate or out-of-scope bar")
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close")):
            raise ValueError("nonquoted bar carries OHLC")
        if row["status"] == "quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid quoted OHLC")
        if _known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def prepare_deduction_observations(payload: dict, contract: dict, *, compute_labels: bool = True) -> dict:
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    index_of = {day: i for i, day in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset in assets:
        rows = [dict(by_key.get((asset, day), {"asset": asset, "date": day, "status": "vendor_missing"})) for day in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        closes, ema20, counts = [], None, Counter()
        for row in rows:
            day = row["date"]
            if day > available_end:
                break
            if _known(row):
                close = float(row["close"])
                closes.append(close)
                ema20 = close if ema20 is None else (2 * close + 19 * ema20) / 21
            else:
                closes, ema20 = [], None
                counts["price_reset_rows"] += 1
            if day not in selected or not first <= day <= last:
                continue
            ready = len(closes) >= WARMUP
            features = {name: None for name in (*BASELINE, "added")}
            context = None
            box_top = None
            if ready:
                current = closes[-1]
                box_top = max(closes[-20:-10])
                context = current > ema20 and current <= closes[-21]
                daily = [closes[i] / closes[i-1] - 1 for i in range(len(closes)-20, len(closes))]
                features.update(prior20high_distance=100*(current/max(closes[-21:-1])-1),
                    ret20=100*(current/closes[-21]-1), ema20_distance=100*(current/ema20-1),
                    r1=100*(current/closes[-2]-1),
                    vol20=statistics.stdev(daily)*math.sqrt(252)*100,
                    sma60_up=int(sum(closes[-60:]) > sum(closes[-65:-5])),
                    added=100*(current/box_top-1))
                for code in ASSETS[1:]:
                    features["asset_" + code[:6]] = int(asset == code or
                        (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, label_end, label_reason = (shared._label(label_rows, index_of[day], target=contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            reason = None if ready else "continuous252_or_economic_price_missing"
            eligible = bool(ready and context and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                "stratum": f"{asset}|{day[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "target_label_reason": label_reason,
                "label_reason": reason or ("outside_early_ema_context" if ready and not context else label_reason),
                "feature_reason": reason, "tested_condition": None,
                "context": context, "box_top": box_top, "ready_252": ready,
                "continuous_real_ohlc": len(closes), "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["context"] += int(bool(context))
            counts["eligible"] += int(eligible)
        per_asset[asset] = dict(counts)
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in
                ("observations", "ready_252", "context", "eligible", "price_reset_rows")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["K10抵扣价盒仅为原文未来方框的固定两周研究代理；不推断买卖。"]}


def _phase(day):
    return "early_2022_2024" if day <= "2024-12-31" else "eval_2025" if day <= "2025-12-31" else "eval_2026H1"


def _x_rank(rows, cols):
    if not rows:
        return {"rows": 0, "rank": 0, "nonzero_columns": [], "zero_variance": list(cols)}
    x = np.array([[r[c] for c in cols] for r in rows], dtype=float)
    assets = [r["asset"] for r in rows]
    w = np.array([1/sum(a == b for b in assets) for a in assets], dtype=float)
    w /= w.sum()
    mean = w @ x
    std = np.sqrt(w @ ((x-mean)**2))
    zero = std < 1e-12
    z = (x-mean) / np.where(zero, 1, std)
    z[:, zero] = 0
    s = np.linalg.svd(np.sqrt(w)[:, None]*z, compute_uv=False)
    rank = int(sum(s > (s[0]*1e-12 if len(s) else 0)))
    return {"rows": len(rows), "rank": rank,
            "nonzero_columns": [c for c, q in zip(cols, zero) if not q],
            "zero_variance": [c for c, q in zip(cols, zero) if q],
            "singular_values": s.tolist()}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """Use present/past X and future calendar dates only, never future values."""
    source = qualify_deduction_panel(payload, contract, root)
    prepared = prepare_deduction_observations(payload, contract, compute_labels=False)
    calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    rows = []
    for obs in prepared["observations"]:
        d = obs["date"]
        row = {"id": obs["id"], "asset": obs["asset"], "date": d, "phase": _phase(d),
               "ready_252": obs["ready_252"], "context": obs["context"],
               "box_top": obs["box_top"], "reason": obs["feature_reason"],
               **obs["features"]}
        for horizon in (5, 10, 20, 60, 120):
            end = calendar[index[d]+horizon+1] if index[d]+horizon+1 < len(calendar) else None
            row[f"h{horizon}_end"] = end
            row[f"h{horizon}_mature"] = bool(end and _phase(end) == _phase(d))
        rows.append(row)
    periods = {}
    for phase in ("early_2022_2024", "eval_2025", "eval_2026H1"):
        rr = [r for r in rows if r["phase"] == phase]
        periods[phase] = {"scheduled": len(rr), "ready": sum(r["ready_252"] for r in rr),
            "context": sum(r["context"] is True for r in rr),
            "context_mature20": sum(r["context"] is True and r["h20_mature"] for r in rr),
            "positive_side_mature20": sum(r["context"] is True and r["h20_mature"] and r["added"] >= 0 for r in rr)}
    folds, ranks = [], []
    for fold in contract["split"]["folds"]:
        train = [r for r in rows if r["context"] is True and r["h20_end"] and
                 r["date"] <= fold["train_end"] and r["h20_end"] < fold["eval_start"]]
        ev = [r for r in rows if r["context"] is True and
              fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              r["h20_end"] and r["h20_end"] <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev),
                      "evaluation_positive_side": sum(r["added"] >= 0 for r in ev)})
        for model, cols in (("B1", BASELINE), ("B2", (*BASELINE, "added"))):
            rank = _x_rank(train, cols)
            ranks.append({"fold": fold, "model": model, **rank,
                          "evaluation_rows": len(ev), "full_nonzero_rank": rank["rank"] == len(rank["nonzero_columns"])})
    return {"features": rows, "qualification": {"data_sha256": contract["data"]["sha256"],
        "outcome_values_used_for_design": False,
        "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                   "dates": len({r["date"] for r in rows}), "episodes": None},
        "scientific_support": {"periods": periods, "folds": folds,
            "model_feature_count": 10, "context_total": sum(r["context"] is True for r in rows),
            "source_and_predecessor_note": "Predecessor vol20 used log returns; D01 frozen protocol uses simple returns."},
        "source_quality": source["quality"], "source_warnings": source["warnings"],
        "coverage": prepared["coverage"]}, "input_rank": {"outcome_values_used": False, "fold_models": ranks}}


def write_qualification(result: dict, out_dir: Path):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "features.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result["features"][0]))
        writer.writeheader(); writer.writerows(result["features"])
    for name, value in (("qualification.json", result["qualification"]),
                        ("input-rank.json", result["input_rank"])):
        with (out_dir / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
