"""Research-only fixed tsfresh price expressions on a common ETF population."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import importlib.util
import math
from pathlib import Path

import numpy as np

from . import workflow_inputs as shared
from .top_structure_information import _known, qualify_top_panel
from .trend_slope_change_information import (
    ASSETS, BASELINE_FEATURES, DEFINITION_REF as SLOPE_REF, PHASES, WARMUP,
    _phase, prepare_slope_observations,
)

KIND = "tsfresh_price_information"
DEFINITION_REFS = (
    "research.external.mean_abs_log_change20@1.0.0",
    "research.external.return_autocorrelation20_lag1@1.0.0",
)
ADDED_FEATURES = ("mean_abs_log_change20", "return_autocorrelation20_lag1")
CALCULATOR_PATH = ".agents/skills/lei-quant-tools/scripts/tsfresh_calculators.py"
LICENSE_PATH = ".agents/skills/lei-quant-tools/scripts/tsfresh-LICENSE.txt"


def _calculators():
    """Load only the pinned, reviewed project copy; never search import paths."""
    path = Path(__file__).resolve().parents[3] / CALCULATOR_PATH
    spec = importlib.util.spec_from_file_location("lei_tsfresh_fixed_calculators", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("fixed tsfresh calculator source unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate(payload, contract):
    feature = contract["feature"]
    if (feature.get("kind") != KIND or feature.get("definition_ref") != DEFINITION_REFS[0] or
            feature.get("definition_refs") != list(DEFINITION_REFS) or
            feature.get("lookback") != 20 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented"):
        raise ValueError("tsfresh requires both fixed definitions and segmented252")
    target = contract["target"]
    if (target.get("kind") != "forward_return" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("tsfresh target is t+1 to t+21 economic close return")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("daily sampling required")
    if payload.get("data_mode") != "synthetic" and (
            payload.get("price_series") != "economic_price" or
            tuple(contract["universe"]["assets"]) != ASSETS or
            contract["question"].get("period") != ["2022-01-04", "2026-06-30"]):
        raise ValueError("real tsfresh panel requires fixed four ETFs and economic price")


def _slope_contract(contract):
    old = deepcopy(contract)
    old["feature"] = {"kind": "slope_change_information", "definition_ref": SLOPE_REF,
                      "lookback": 60, "warmup": WARMUP, "missing_policy": "segmented"}
    return old


def prepare_tsfresh_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """Preserve slope background and label clock; require both candidates on every comparison."""
    _validate(payload, contract)
    if compute_labels and payload.get("data_mode") != "synthetic" and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True):
        raise ValueError("real future labels require explicit effect authorization")
    prepared = prepare_slope_observations(payload, _slope_contract(contract), compute_labels=compute_labels)
    indexed = {(bar["asset"], bar["date"]): bar for bar in payload["bars"]}
    calc = _calculators()
    by_id = {row["id"]: row for row in prepared["observations"]}
    counts = Counter()
    per_asset = {}
    for asset in contract["universe"]["assets"]:
        segment = []
        asset_counts = Counter()
        for day in payload["calendar"]:
            bar = indexed.get((asset, day))
            if bar is None or not _known(bar):
                segment = []
            else:
                segment.append(float(bar["close"]))
            row = by_id.get(f"{asset}|{day}")
            if row is None:
                continue
            candidate = {name: None for name in ADDED_FEATURES}
            if len(segment) >= 21:
                logs = 100 * np.log(np.asarray(segment[-21:], dtype=float))
                returns = np.diff(logs)
                raw = (float(calc.mean_abs_change(logs)),
                       float(calc.autocorrelation(returns, lag=1)))
                candidate = {name: value if math.isfinite(value) else None
                             for name, value in zip(ADDED_FEATURES, raw)}
            row["features"].pop("added")
            row["features"].update(candidate)
            background_ready = row["ready_252"]
            common = bool(background_ready and all(
                row["features"].get(name) is not None and
                math.isfinite(row["features"][name])
                for name in (*BASELINE_FEATURES, *ADDED_FEATURES)))
            row["ready_252"] = common
            row["eligible"] = bool(common and (row["y"] is not None if compute_labels else True))
            row["feature_reason"] = (None if common else
                "continuous252_or_indicator_missing" if not background_ready else
                "tsfresh_candidate_unknown")
            row["label_reason"] = row["feature_reason"] or row["target_label_reason"]
            row["tested_condition"] = None  # continuous expression; no sign filter
            row["definition_ref"] = DEFINITION_REFS[0]
            row["definition_refs"] = list(DEFINITION_REFS)
            asset_counts["observations"] += 1
            asset_counts["ready_252"] += int(common)
            asset_counts["eligible"] += int(row["eligible"])
            asset_counts[row["feature_reason"] or "feature_ready"] += 1
        asset_counts["price_reset_rows"] = prepared["coverage"]["per_asset"][asset]["price_reset_rows"]
        per_asset[asset] = dict(asset_counts)
        counts.update(asset_counts)
    coverage = {key: counts[key] for key in (
        "observations", "ready_252", "eligible", "price_reset_rows",
        "continuous252_or_indicator_missing", "tsfresh_candidate_unknown", "feature_ready")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REFS[0],
                    definition_refs=list(DEFINITION_REFS), common_population=True)
    return {"observations": prepared["observations"], "coverage": coverage,
            "warnings": ["固定价格表达仅供研究；行动历史到达时间与完整性仍未知。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """Source and calendar support only; this path never accesses future prices."""
    _validate(payload, contract)
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_tsfresh_observations(payload, contract, compute_labels=False)
    rows = prepared["observations"]
    dates = payload["calendar"]
    index = {day: i for i, day in enumerate(dates)}
    def end(row):
        j = index[row["date"]] + 21
        return dates[j] if j < len(dates) else None
    phases = {}
    for phase in PHASES:
        subset = [r for r in rows if _phase(r["date"]) == phase]
        phases[phase] = {"scheduled": len(subset),
                         "ready_252": sum(r["ready_252"] for r in subset),
                         "feature_unknown": sum(not r["ready_252"] for r in subset),
                         "calendar_mature_same_phase": sum(bool(r["ready_252"] and end(r) and
                                                            _phase(end(r)) == phase) for r in subset)}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in rows if r["ready_252"] and r["date"] <= fold["train_end"] and
                 end(r) and end(r) < fold["eval_start"]]
        ev = [r for r in rows if r["ready_252"] and fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev),
                      "train_dates": len({r["date"] for r in train}),
                      "evaluation_dates": len({r["date"] for r in ev})})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "scientific_support": {"phases": phases, "folds": folds,
                                   "model_feature_count": len(BASELINE_FEATURES) + len(ADDED_FEATURES),
                                   "definition_refs": list(DEFINITION_REFS),
                                   "unknown_reasons": dict(Counter(r["feature_reason"] for r in rows if r["feature_reason"])),
                                   "note": "Future support uses calendar dates only, not future prices."}}
