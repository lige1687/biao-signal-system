"""Validation for the optional research-question/evidence result block.

This module validates shape and a few explicit consistency rules only. It does
not choose a statistical method, calculate evidence, or assign a conclusion.
It intentionally depends on the Python standard library alone.
"""
from __future__ import annotations

import math
from datetime import date
from numbers import Real
from typing import Any


QUESTION_REQUIRED = {
    "question_id",
    "hypothesis_family",
    "factor_refs",
    "layer",
    "comparison",
    "sampling",
    "target",
    "baseline",
    "added_information",
    "method",
    "primary_metric",
    "auxiliary_metrics",
    "universe",
    "period",
    "validation",
    "dependence",
    "sources",
    "trial_history",
}
COMPARISONS = {"time_series", "cross_sectional", "joint"}
SAMPLING_MODES = {"daily", "periodic", "event", "other"}
LAYERS = {"factor_information", "decision_policy"}
EVIDENCE_STATES = {"completed", "not_computed", "insufficient", "not_applicable"}
CONCLUSIONS = {
    "增量获得支持",
    "有线索待验证",
    "当前未支持增量",
    "证据不足",
    "数据或定义存在问题",
}


class QuestionContractError(ValueError):
    """Raised when a question or result violates the frozen field contract."""


def _fail(path: str, reason: str) -> None:
    raise QuestionContractError(f"{path}: {reason}")


def _nonempty_text(value: Any, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a nonempty string")


def _nonempty_sequence(value: Any, path: str) -> None:
    if not isinstance(value, (list, tuple)) or not value:
        _fail(path, "must be a nonempty list")
    for index, item in enumerate(value):
        if isinstance(item, str):
            _nonempty_text(item, f"{path}[{index}]")
        elif isinstance(item, dict):
            if not item:
                _fail(f"{path}[{index}]", "must not be an empty object")
        else:
            _fail(f"{path}[{index}]", "items must be nonempty strings or objects")


def _nonempty_value(value: Any, path: str) -> None:
    """Accept a meaningful string, list/tuple, or mapping without flattening it."""
    if isinstance(value, str):
        _nonempty_text(value, path)
    elif isinstance(value, (list, tuple)):
        _nonempty_sequence(value, path)
    elif isinstance(value, dict):
        if not value:
            _fail(path, "must not be an empty object")
    else:
        _fail(path, "must be a nonempty string, list, or object")


def _mapping(value: Any, path: str, required: set[str]) -> dict:
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    missing = required - value.keys()
    if missing:
        _fail(path, f"missing keys: {', '.join(sorted(missing))}")
    return value


def _finite_number(value: Any, path: str, *, nullable: bool = False) -> bool:
    if value is None and nullable:
        return False
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        _fail(path, "must be a finite number" + (" or null" if nullable else ""))
    return True


def validate_question(question: dict) -> None:
    """Validate the flat research question block; caller-owned extra keys pass."""
    q = _mapping(question, "question", QUESTION_REQUIRED)
    for key in ("question_id", "hypothesis_family", "baseline", "added_information"):
        _nonempty_text(q[key], f"question.{key}")
    for key in ("universe", "period", "dependence", "sources", "trial_history"):
        _nonempty_value(q[key], f"question.{key}")
    for key in ("factor_refs", "auxiliary_metrics"):
        _nonempty_sequence(q[key], f"question.{key}")

    if not isinstance(q["layer"], str) or q["layer"] not in LAYERS:
        _fail("question.layer", f"must be one of {sorted(LAYERS)}")
    if not isinstance(q["comparison"], str) or q["comparison"] not in COMPARISONS:
        _fail("question.comparison", f"must be one of {sorted(COMPARISONS)}")
    if not isinstance(q["sampling"], str) or q["sampling"] not in SAMPLING_MODES:
        _fail("question.sampling", f"must be one of {sorted(SAMPLING_MODES)}")
    if q["comparison"] == "joint":
        _nonempty_text(q.get("joint_structure"), "question.joint_structure")
    if q["sampling"] == "other":
        _nonempty_text(q.get("sample_unit"), "question.sample_unit")
    if q["sampling"] == "event":
        _nonempty_text(q.get("event_definition"), "question.event_definition")

    target = _mapping(
        q["target"],
        "question.target",
        {"kind", "horizon", "start_offset", "end_offset", "price_basis"},
    )
    _nonempty_text(target["kind"], "question.target.kind")
    # Explicit non-applicable targets are valid for policy questions but must
    # carry a reason. Preserve their null horizon/offset fields as supplied.
    horizon = target["horizon"]
    if target["kind"] == "not_applicable":
        if q["layer"] != "decision_policy":
            _fail("question.target.kind", "not_applicable is reserved for decision_policy questions")
        _nonempty_text(target.get("reason"), "question.target.reason")
        if any(target[key] is not None for key in ("horizon", "start_offset", "end_offset", "price_basis")):
            _fail("question.target", "not_applicable target must use null horizon/offset/price_basis")
    else:
        _nonempty_text(target["price_basis"], "question.target.price_basis")
        if not (
            (isinstance(horizon, str) and horizon.strip())
            or (isinstance(horizon, Real) and not isinstance(horizon, bool) and math.isfinite(float(horizon)) and horizon > 0)
        ):
            _fail("question.target.horizon", "must be a positive number or nonempty string")
        _finite_number(target["start_offset"], "question.target.start_offset")
        _finite_number(target["end_offset"], "question.target.end_offset")
        if target["end_offset"] <= target["start_offset"]:
            _fail("question.target.end_offset", "must be after start_offset")
        if q["layer"] == "factor_information":
            if target["start_offset"] < 1:
                _fail("question.target.start_offset", "forward factor targets must start at least at offset 1")
            if isinstance(horizon, Real) and not isinstance(horizon, bool):
                if target["end_offset"] - target["start_offset"] != horizon:
                    _fail("question.target.horizon", "numeric horizon must equal end_offset - start_offset")

    method = _mapping(q["method"], "question.method", {"name", "reason"})
    _nonempty_text(method["name"], "question.method.name")
    _nonempty_text(method["reason"], "question.method.reason")
    method_name = method["name"].lower()
    if "cross_section_ic" in method_name or "rank_ic" in method_name:
        if q["comparison"] not in {"cross_sectional", "joint"}:
            _fail("question.method.name", "cross-sectional IC/rank method requires cross_sectional or joint comparison")
        reason = method["reason"].lower()
        if not any(token in reason for token in ("by date", "date-wise", "within date", "按日期", "同日")):
            _fail("question.method.reason", "cross-sectional IC/rank method must state that ranks are formed by date")
    metric = _mapping(
        q["primary_metric"],
        "question.primary_metric",
        {"name", "direction", "attention_threshold"},
    )
    _nonempty_text(metric["name"], "question.primary_metric.name")
    _nonempty_text(metric["direction"], "question.primary_metric.direction")
    threshold = metric["attention_threshold"]
    if threshold is None:
        _nonempty_text(metric.get("threshold_reason"), "question.primary_metric.threshold_reason")
    else:
        _finite_number(threshold, "question.primary_metric.attention_threshold")

    validation = _mapping(
        q["validation"],
        "question.validation",
        {"stage", "split_policy", "label_boundary_policy"},
    )
    for key in ("stage", "split_policy", "label_boundary_policy"):
        _nonempty_text(validation[key], f"question.validation.{key}")


def validate_result(question: dict, result: dict) -> None:
    """Validate reported evidence without deriving or upgrading its conclusion."""
    validate_question(question)
    r = _mapping(
        result,
        "result",
        {"question_id", "evidence", "conclusion", "primary", "sample", "sources"},
    )
    if r["question_id"] != question["question_id"]:
        _fail("result.question_id", "must exactly match question.question_id")
    if not isinstance(r["conclusion"], str) or r["conclusion"] not in CONCLUSIONS:
        _fail("result.conclusion", f"must be one of {sorted(CONCLUSIONS)}")

    evidence = _mapping(r["evidence"], "result.evidence", {"A", "B", "C"})
    for key in ("A", "B", "C"):
        if not isinstance(evidence[key], str) or evidence[key] not in EVIDENCE_STATES:
            _fail(f"result.evidence.{key}", f"must be one of {sorted(EVIDENCE_STATES)}")
    if r["conclusion"] == "增量获得支持" and evidence["B"] != "completed":
        _fail("result.evidence.B", "must be completed before claiming incremental support")
    if question["validation"]["stage"] == "exploration" and evidence["C"] == "completed":
        _fail("result.evidence.C", "cannot be completed for an exploration-stage question")

    primary = _mapping(
        r["primary"], "result.primary", {"difference", "interval", "missing_reason"}
    )
    difference_present = _finite_number(
        primary["difference"], "result.primary.difference", nullable=True
    )
    interval = primary["interval"]
    interval_present = interval is not None
    if interval_present:
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            _fail("result.primary.interval", "must be a two-number list or null")
        _finite_number(interval[0], "result.primary.interval[0]")
        _finite_number(interval[1], "result.primary.interval[1]")
        if interval[0] > interval[1]:
            _fail("result.primary.interval", "lower endpoint must not exceed upper endpoint")
    reason = primary["missing_reason"]
    interval_reason = primary.get("interval_missing_reason")
    if difference_present:
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            _fail("result.primary.missing_reason", "must be nonempty string or null")
    else:
        _nonempty_text(reason, "result.primary.missing_reason")
    if interval_present:
        if interval_reason is not None and (not isinstance(interval_reason, str) or not interval_reason.strip()):
            _fail("result.primary.interval_missing_reason", "must be nonempty string or null")
    else:
        _nonempty_text(interval_reason, "result.primary.interval_missing_reason")

    sample = _mapping(r["sample"], "result.sample", {"rows", "dates", "assets", "coverage"})
    for key in ("rows", "dates", "assets"):
        value = sample[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail(f"result.sample.{key}", "must be a nonnegative integer")
    coverage = sample["coverage"]
    if coverage is not None:
        _finite_number(coverage, "result.sample.coverage")
        if not 0 <= coverage <= 1:
            _fail("result.sample.coverage", "must be between 0 and 1")
    elif not reason:
        _fail("result.sample.coverage", "null coverage requires result.primary.missing_reason")
    _nonempty_sequence(r["sources"], "result.sources")


def validate_workflow_contract(contract: dict) -> None:
    """New controlled entry only; historical question blocks keep their schema.

    These are mechanical checks. Controller rationale is retained as a judgment,
    never converted into a machine verification flag.
    """
    c = _mapping(contract, "workflow", {
        "schema_version", "question", "data", "universe", "feature", "target", "split",
        "evaluator", "weights", "dependence", "budget", "history", "controller_review",
        "publication", "sources",
    })
    schema_version = c["schema_version"]
    if schema_version not in {"research-workflow/1.0", "research-workflow/1.1"}:
        _fail("workflow.schema_version", "unsupported schema")
    validate_question(c["question"])
    period = c["question"]["period"]
    if not isinstance(period, list) or len(period) != 2:
        _fail("workflow.question.period", "new runner needs explicit [start,end] dates")
    try:
        if date.fromisoformat(period[0]) > date.fromisoformat(period[1]):
            _fail("workflow.question.period", "start is after end")
    except (ValueError, TypeError):
        _fail("workflow.question.period", "must be valid dates")
    if c["question"]["layer"] != "factor_information":
        _fail("workflow.question.layer", "account/policy research needs its own executable evaluator")
    data = _mapping(c["data"], "workflow.data", {"path", "sha256", "mode"})
    if data["mode"] not in {"synthetic", "historical_reconstruction"}:
        _fail("workflow.data.mode", "unsupported data mode; production is prohibited")
    for key in ("path", "sha256"):
        _nonempty_text(data[key], f"workflow.data.{key}")
    u = _mapping(c["universe"], "workflow.universe", {
        "assets", "allow_partial", "rationale", "identity_basis",
    })
    _nonempty_sequence(u["assets"], "workflow.universe.assets")
    if len(set(u["assets"])) != len(u["assets"]):
        _fail("workflow.universe.assets", "duplicate assets")
    if type(u["allow_partial"]) is not bool:
        _fail("workflow.universe.allow_partial", "must be boolean")
    for key in ("rationale", "identity_basis"):
        _nonempty_text(u[key], f"workflow.universe.{key}")
    if c["question"]["universe"] != u["assets"]:
        _fail("workflow.universe", "question and executable asset pool differ")
    feature = _mapping(c["feature"], "workflow.feature", {
        "kind", "lookback", "bar_frequency", "missing_policy", "warmup",
    })
    if feature["kind"] not in {"sma_distance", "decline_event", "a01_signed_band", "a03_pullback_order", "space_prior_target", "ma_cluster_information", "volume_anomaly_information", "key_fluctuation_information", "profile_overhead_information", "simple_top3_information", "future_deduction_box_information", "double_ma_order_information", "slope_change_information", "simple_top_invalidation_information", "pullback_layer_change_information", "prior_top_dual_break_information", "ema_sma_waiting_path", "tsfresh_price_information", "ema_only_wait_age_information", "slope_change_risk_information", "ema_only_wait_age_risk_information", "green_black_state60_information"}:
        _fail("workflow.feature.kind", "no implemented adapter for this feature")
    if feature["missing_policy"] not in {"real_quote", "segmented"}:
        _fail("workflow.feature.missing_policy", "must freeze a supported recovery policy")
    if feature["bar_frequency"] != "daily_quote":
        _fail("workflow.feature.bar_frequency", "current feature adapter counts daily quoted bars; weekly sampling is not a weekly moving average")
    for key in ("lookback", "warmup"):
        if type(feature[key]) is not int or feature[key] < 1:
            _fail(f"workflow.feature.{key}", "must be a positive bar count")
    if feature["kind"] == "ema_only_wait_age_information":
        ref = "research.trend.ema_only_wait_age20@1.0.0"
        if (schema_version != "research-workflow/1.1" or feature["lookback"] != 20 or
                feature["warmup"] != 252 or feature["missing_policy"] != "segmented" or
                feature.get("definition_ref") != ref or c["question"]["factor_refs"] != [ref] or
                c["question"].get("sampling") != "daily" or feature.get("ema_seed") != "first_close" or
                feature.get("age_transform") != "log1p" or feature.get("sma_lag") != 20 or
                feature.get("censor_policy") != "left_censor_unknown_start"):
            _fail("workflow.feature", "current wait age freezes exact prefix-only EMA20/SMA20, segmented252, left censor and log1p age")
        if data["mode"] != "synthetic" and data.get("qualification", {}).get("adapter") != "top_etf_economic/1.0":
            _fail("workflow.data.qualification", "current-age study needs economic OHLC source qualification")
    if feature["kind"] in {"slope_change_risk_information", "ema_only_wait_age_risk_information"}:
        from lei_signal.research.technical_daily_risk_information import RISK_SOURCES
        ref = RISK_SOURCES[feature["kind"]][0]
        common = (schema_version == "research-workflow/1.1" and
                  feature["warmup"] == 252 and feature["missing_policy"] == "segmented" and
                  feature.get("definition_ref") == ref and c["question"]["factor_refs"] == [ref] and
                  c["question"].get("sampling") == "daily")
        if feature["kind"] == "slope_change_risk_information":
            valid = common and feature["lookback"] == 60
        else:
            valid = (common and feature["lookback"] == 20 and
                     feature.get("ema_seed") == "first_close" and
                     feature.get("age_transform") == "log1p" and feature.get("sma_lag") == 20 and
                     feature.get("censor_policy") == "left_censor_unknown_start")
        if not valid:
            _fail("workflow.feature", "daily risk requires its exact fixed research expression and segmented252 card")
        if data["mode"] != "synthetic" and data.get("qualification", {}).get("adapter") != "top_etf_economic/1.0":
            _fail("workflow.data.qualification", "daily risk requires economic OHLC source qualification")
        if data["mode"] != "synthetic" and (
                c["universe"]["assets"] != ["510300.SS", "510050.SS", "510500.SS", "588000.SS"] or
                c["question"]["period"] != ["2022-01-04", "2026-06-30"]):
            _fail("workflow.universe", "daily risk is limited to its original four ETFs and period")
    if feature["kind"] == "ema_sma_waiting_path":
        ref = "research.trend.ema20_sma20_waiting_path@1.0.0"
        if (schema_version != "research-workflow/1.1" or feature["lookback"] != 20 or feature["warmup"] != 252 or
                feature["missing_policy"] != "segmented" or feature.get("definition_ref") != ref or
                c["question"]["factor_refs"] != [ref] or c["question"].get("sampling") != "daily" or
                feature.get("ema_seed") != "first_close" or feature.get("ema_alpha") != "2/21" or
                type(feature.get("sma_lag")) is not int or feature["sma_lag"] != 20 or
                type(feature.get("terminal_offset")) is not int or feature["terminal_offset"] != 21):
            _fail("workflow.feature", "waiting path freezes exact daily first-close EMA20, lag20, segmented252 and H=t0+21")
        if data["mode"] != "synthetic" and data.get("qualification", {}).get("adapter") != "top_etf_economic/1.0":
            _fail("workflow.data.qualification", "waiting path requires source-only economic OHLC qualification")
    if feature["kind"] in {"slope_change_information", "simple_top_invalidation_information"}:
        ref = ("research.trend.slope_change60_20@1.0.0" if
               feature["kind"] == "slope_change_information" else
               "research.structure.simple_top3_invalidation@1.0.0")
        if (feature["lookback"] != 60 or feature["warmup"] != 252 or
                feature["missing_policy"] != "segmented" or
                feature.get("definition_ref") != ref or
                c["question"]["factor_refs"] != [ref] or
                c["question"].get("sampling") != "daily"):
            _fail("workflow.feature", "semantic study requires its exact daily segmented252 card")
        if (data["mode"] != "synthetic" and
                data.get("qualification", {}).get("adapter") != "top_etf_economic/1.0"):
            _fail("workflow.data.qualification", "semantic study requires source-only economic OHLC qualification")
    if feature["kind"] == "prior_top_dual_break_information":
        ref = "research.interaction.prior_top_dual_break20@1.0.0"
        if (feature["lookback"] != 60 or feature["warmup"] != 252 or
                feature["missing_policy"] != "segmented" or
                feature.get("definition_ref") != ref or
                c["question"]["factor_refs"] != [ref] or
                c["question"].get("sampling") != "daily"):
            _fail("workflow.feature", "prior-top combination study requires its exact daily segmented252 card")
        if (data["mode"] != "synthetic" and
                data.get("qualification", {}).get("adapter") != "top_etf_economic/1.0"):
            _fail("workflow.data.qualification", "prior-top combination study requires source-only economic OHLC qualification")
    if feature["kind"] == "pullback_layer_change_information":
        ref = "research.pullback.ma_layer_change@1.0.0"
        if (feature["lookback"] != 60 or feature["warmup"] != 252 or
                feature["missing_policy"] != "segmented" or
                feature.get("definition_ref") != ref or
                c["question"]["factor_refs"] != [ref] or
                c["question"].get("sampling") != "daily"):
            _fail("workflow.feature", "pullback-layer study requires its exact daily segmented252 card")
        if (data["mode"] != "synthetic" and
                data.get("qualification", {}).get("adapter") != "top_etf_economic/1.0"):
            _fail("workflow.data.qualification", "pullback-layer study requires source-only economic OHLC qualification")
    if feature["kind"] == "a01_signed_band":
        if feature["lookback"] != 60 or feature["warmup"] != 252 or feature["missing_policy"] != "segmented":
            _fail("workflow.feature", "A01 adapter freezes N60, segmented complete-OHLC252 and seeded ATR20")
        if "research.a01.signed_band@2.0.0" not in c["question"]["factor_refs"]:
            _fail("workflow.feature", "A01 geometry/recovery must resolve its exact registered definition")
    if feature["kind"] == "a03_pullback_order":
        if feature["lookback"] != 60 or feature["warmup"] != 252 or feature["missing_policy"] != "segmented":
            _fail("workflow.feature", "A03 adapter freezes N60 and continuous complete-OHLC252 recovery")
        if "research.a03.pullback_order@1.0.0" not in c["question"]["factor_refs"]:
            _fail("workflow.feature", "A03 event order must resolve its exact research definition")
    if feature["kind"] == "space_prior_target":
        if feature["lookback"] != 60 or feature["warmup"] != 252 or feature["missing_policy"] != "segmented":
            _fail("workflow.feature", "space adapter freezes prior60, continuous OHLC252 and segmented recovery")
        if "research.space.prior_upper_pivot@1.0.0" not in c["question"]["factor_refs"]:
            _fail("workflow.feature", "space adapter requires its exact registered research definition")
        if c["question"].get("sampling") != "periodic" or c["question"].get("frequency") != "weekly":
            _fail("workflow.question", "current space research freezes completed weekly observations")
    if feature["kind"] == "ma_cluster_information":
        if feature["lookback"] != 120 or feature["warmup"] != 252 or feature["missing_policy"] != "segmented":
            _fail("workflow.feature", "width research freezes N120 and continuous OHLC252 recovery")
        if feature.get("definition_ref") != "research.trend.ma_cluster_width@1.0.0" or "research.trend.ma_cluster_width@1.0.0" not in c["question"]["factor_refs"]:
            _fail("workflow.feature", "width comparison requires its separate registered research definition")
        if c["question"].get("sampling") != "periodic" or c["question"].get("frequency") != "weekly":
            _fail("workflow.question", "width research freezes completed weekly observations")
    if feature["kind"] == "volume_anomaly_information":
        if feature["lookback"] != 20 or feature["warmup"] != 252 or feature["missing_policy"] != "segmented":
            _fail("workflow.feature", "V01 freezes inclusive volume20 and continuous OHLC252")
        if feature.get("definition_ref") != "research.volume.abnormal20@1.0.0" or "research.volume.abnormal20@1.0.0" not in c["question"]["factor_refs"]:
            _fail("workflow.feature", "V01 requires its exact separate research definition")
        if c["question"].get("sampling") != "daily":
            _fail("workflow.question", "V01 retains all daily observations")
    if feature["kind"] == "simple_top3_information":
        if (feature["lookback"] != 60 or feature["warmup"] != 252 or
            feature["missing_policy"] != "segmented" or
            feature.get("definition_ref") != "research.structure.simple_top3@1.0.0" or
            c["question"]["factor_refs"] != ["research.structure.simple_top3@1.0.0"]):
            _fail("workflow.feature", "T01 requires exact registered research card, SMA60 and OHLC252")
        if c["question"].get("sampling") != "daily":
            _fail("workflow.question", "T01 retains all scheduled days")
    if feature["kind"] == "key_fluctuation_information":
        if (feature["lookback"] != 60 or feature["warmup"] != 252 or
            feature["missing_policy"] != "segmented" or
            feature.get("definition_ref") != "research.key_fluctuation.dual_break20@1.0.0" or
            c["question"]["factor_refs"] != ["research.key_fluctuation.dual_break20@1.0.0"] or
            c["question"].get("sampling") != "daily"):
            _fail("workflow.feature", "K01 requires exact daily dual-break card, SMA60 and segmented OHLC252")
        if data["mode"] != "synthetic" and data.get("qualification", {}).get("adapter") != "key_etf_economic/1.0":
            _fail("workflow.data.qualification", "K01 requires its source-only economic ETF qualifier")
    if feature["kind"] == "profile_overhead_information":
        if (feature["lookback"] != 120 or feature["warmup"] != 252 or
            feature["missing_policy"] != "segmented" or feature.get("bins") != 50 or
            feature.get("value_area") != .70 or feature.get("support_zone_pct") != .05 or
            feature.get("background_sma_lag") != 5 or
            feature.get("definition_ref") != "research.volume_profile.overhead120@1.0.0" or
            c["question"]["factor_refs"] != ["research.volume_profile.overhead120@1.0.0"] or
            c["question"].get("sampling") != "daily"):
            _fail("workflow.feature", "P01 freezes exact daily overhead120, bins50 and segmented OHLC252")
        if data["mode"] != "synthetic" and data.get("qualification", {}).get("adapter") != "profile_etf_economic/1.0":
            _fail("workflow.data.qualification", "P01 requires source-bound economic ETF OHLCV")
    if feature["kind"] == "future_deduction_box_information":
        if (feature["lookback"] != 20 or feature.get("box_horizon") != 10 or
            feature["warmup"] != 252 or feature["missing_policy"] != "segmented" or
            feature.get("definition_ref") != "research.trend.future_deduction_box20_10@1.0.0" or
            c["question"]["factor_refs"] != ["research.trend.future_deduction_box20_10@1.0.0"] or
            c["question"].get("sampling") != "daily"):
            _fail("workflow.feature", "D01 requires exact registered N20/K10 card and scheduled daily OHLC252")
        if (data.get("qualification", {}).get("adapter") != "deduction_etf_economic/1.0" and
            data["mode"] != "synthetic"):
            _fail("workflow.data.qualification", "D01 requires its source-only economic ETF qualifier")
    if feature["kind"] == "double_ma_order_information":
        if (feature["lookback"] != 120 or feature["warmup"] != 252 or feature["missing_policy"] != "segmented" or feature.get("definition_ref") != "research.trend.double_ma_order_state@1.0.0" or c["question"]["factor_refs"] != ["research.trend.double_ma_order_state@1.0.0"] or c["question"].get("sampling") != "daily"):
            _fail("workflow.feature", "T03 requires exact dual20/60/120 daily segmented252 card")
        if data["mode"] != "synthetic" and data.get("qualification", {}).get("adapter") != "double_order_etf_economic/1.0":
            _fail("workflow.data.qualification", "T03 requires its explicit economic source qualifier")
    target = _mapping(c["target"], "workflow.target", {
        "kind", "start_offset", "end_offset", "entry_field", "unit",
    })
    if target["kind"] not in {"forward_return", "mae", "max_drawdown", "up", "downside_event"}:
        _fail("workflow.target.kind", "unsupported target")
    binary = target["kind"] in {"up", "downside_event"}
    if target["unit"] != ("probability" if binary else "percentage_point"):
        _fail("workflow.target.unit", "target unit does not match formula")
    if target["entry_field"] not in {"close", "open"}:
        _fail("workflow.target.entry_field", "unsupported entry price")
    for key in ("start_offset", "end_offset"):
        if type(target[key]) is not int:
            _fail(f"workflow.target.{key}", "must be integer calendar offsets")
        if target[key] != c["question"]["target"][key]:
            _fail(f"workflow.target.{key}", "question and executable target differ")
    if target["kind"] != c["question"]["target"]["kind"]:
        _fail("workflow.target.kind", "question and executable target differ")
    if target["kind"] == "downside_event":
        _finite_number(target.get("threshold"), "workflow.target.threshold")
        if target["threshold"] <= 0:
            _fail("workflow.target.threshold", "positive loss threshold: 5 means return <= -5 percentage points")
        if target.get("threshold_unit") != "percentage_point":
            _fail("workflow.target.threshold_unit", "loss threshold is expressed in percentage points, not probability/fraction")
    measure = target.get("price_measure", "economic_price")
    if measure not in {"economic_price", "provider_index_price"}:
        _fail("workflow.target.price_measure", "unsupported price measurement")
    if measure == "provider_index_price" and data["mode"] != "synthetic":
        if data.get("qualification", {}).get("adapter") != "tencent_index_price/1.0":
            _fail("workflow.data.qualification", "index price labels require actual provider-series binding")
        if target["entry_field"] != "close" or c["question"]["validation"]["stage"] != "exploration":
            _fail("workflow.target", "provider proxy is historical close-price exploration only")
    s = _mapping(c["split"], "workflow.split", {"folds", "label_policy"})
    _nonempty_sequence(s["folds"], "workflow.split.folds")
    if s["label_policy"] not in {"purge", "require_mature"}:
        _fail("workflow.split.label_policy", "unknown maturity policy")
    if s.get("evaluation_label_policy", "mature") not in {"mature", "contained"}:
        _fail("workflow.split.evaluation_label_policy", "unknown evaluation label boundary")
    previous_end = None
    for i, fold in enumerate(s["folds"]):
        f = _mapping(fold, f"workflow.split.folds[{i}]", {"train_end", "eval_start", "eval_end"})
        try:
            dates = [date.fromisoformat(f[k]) for k in ("train_end", "eval_start", "eval_end")]
        except (ValueError, TypeError) as exc:
            _fail("workflow.split", f"invalid date: {exc}")
        if not dates[0] < dates[1] <= dates[2] or (previous_end and dates[1] <= previous_end):
            _fail("workflow.split", "training must precede disjoint evaluation folds")
        previous_end = dates[2]
    e = _mapping(c["evaluator"], "workflow.evaluator", {
        "kind", "version", "baseline_features", "added_features",
    })
    if e["kind"] not in {"prediction_ridge", "prediction_ols", "event_risk", "waiting_path_description"} or e["version"] != "1.0.0":
        _fail("workflow.evaluator", "unsupported evaluator/version")
    metric = c["question"]["primary_metric"]
    if e["kind"] == "waiting_path_description":
        if (feature["kind"] != "ema_sma_waiting_path" or e["baseline_features"] != ["early_reference"] or
                e["added_features"] != ["first_s_confirmation"] or target["kind"] != "forward_return" or
                target["start_offset"] != 1 or target["end_offset"] != 21 or target["entry_field"] != "close" or
                target.get("price_measure", "economic_price") != "economic_price" or
                c["question"]["target"]["horizon"] != 20 or metric["name"] != "paired_terminal_return_difference" or
                metric["direction"] != "higher" or metric["attention_threshold"] is not None or
                c["weights"]["policy"] != "equal_asset"):
            _fail("workflow.evaluator", "waiting path describes fixed common terminal prices; it neither fits nor predicts")
        if (s["folds"] != [
                {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
                s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained"):
            _fail("workflow.split", "waiting path freezes the two calendar phases for description, without training")
    elif feature["kind"] == "ema_sma_waiting_path":
        _fail("workflow.evaluator", "waiting path requires its descriptive evaluator")
    elif metric["name"] not in ({"Brier"} if binary else {"MSE", "RMSE"}) or metric["direction"] != "lower":
        _fail("workflow.question.primary_metric", "the implemented prediction evaluator minimizes its declared error metric")
    if c["question"]["method"]["name"] != e["kind"]:
        _fail("workflow.question.method", "question method differs from executable adapter")
    for key in ("baseline_features", "added_features"):
        _nonempty_sequence(e[key], f"workflow.evaluator.{key}")
    if set(e["baseline_features"]) & set(e["added_features"]):
        _fail("workflow.evaluator", "added information duplicates the baseline fields")
    if schema_version == "research-workflow/1.1":
        _validate_research_design(c)
    if e["kind"] == "prediction_ridge":
        _finite_number(e.get("lambda"), "workflow.evaluator.lambda")
        if e["lambda"] != 1.0:
            _fail("workflow.evaluator.lambda", "first adapter freezes normalized penalty at 1.0")
        if feature["kind"] == "a03_pullback_order" and e["added_features"] != ["added"]:
            _fail("workflow.evaluator.added_features", "A03 only adds the frozen first-touch indicator")
        if feature["kind"] == "ma_cluster_information" and (e["baseline_features"] != ["distance20_atr", "distance60_atr", "distance120_atr", "ret20", "vol20"] or e["added_features"] != ["added"]):
            _fail("workflow.evaluator", "width study freezes three signed ATR distances, ret20, vol20 and width percentage points")
        if feature["kind"] == "simple_top3_information" and (e["baseline_features"] != ["r1", "ret3", "ret20", "vol20", "black20", "asset_510050", "asset_510500", "asset_588000"] or e["added_features"] != ["added"]):
            _fail("workflow.evaluator", "T01 freezes price, black20 and three ETF identity fields plus the top indicator")
    if e["kind"] == "prediction_ols":
        if (feature["kind"] not in {"future_deduction_box_information", "double_ma_order_information", "key_fluctuation_information", "profile_overhead_information", "slope_change_information", "simple_top_invalidation_information", "tsfresh_price_information", "ema_only_wait_age_information", "slope_change_risk_information", "ema_only_wait_age_risk_information", "green_black_state60_information"} or
            target["kind"] in {"up", "downside_event"} or e.get("lambda", 0) != 0 or
            e.get("rcond", 1e-12) != 1e-12):
            _fail("workflow.evaluator", "OLS requires continuous target, zero penalty and rcond 1e-12")
    if feature["kind"] in {"slope_change_risk_information", "ema_only_wait_age_risk_information"}:
        if feature["kind"] == "slope_change_risk_information":
            from lei_signal.research.trend_slope_change_information import BASELINE_FEATURES
        else:
            from lei_signal.research.ema_only_wait_age_information import BASELINE_FEATURES
        fixed_folds = [
            {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
            {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"},
        ]
        if (e["kind"] != "prediction_ols" or e["baseline_features"] != list(BASELINE_FEATURES) or
                e["added_features"] != ["added"] or e.get("lambda") != 0 or
                e.get("rcond") != 1e-12 or e.get("minimum_training_rows") != 22 or
                target["kind"] != "mae" or target["start_offset"] != 1 or
                target["end_offset"] != 21 or target["entry_field"] != "close" or
                target.get("path_field") != "close" or target.get("price_measure") != "economic_price" or
                c["question"]["target"]["horizon"] != 20 or
                c.get("training_weights") != "equal_asset" or c["weights"]["policy"] != "equal_asset" or
                s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or
                s["folds"] != fixed_folds or metric["name"] != "RMSE" or
                c["dependence"].get("axis_scope") != "evaluation"):
            _fail("workflow.evaluator", "daily risk freezes exact B1 plus one expression and two contained 21-close MAE OLS folds")
    if feature["kind"] == "ema_only_wait_age_information":
        from lei_signal.research.ema_only_wait_age_information import BASELINE_FEATURES
        if (e["kind"] != "prediction_ols" or e["baseline_features"] != list(BASELINE_FEATURES) or
                e["added_features"] != ["added"] or e.get("lambda") != 0 or e.get("rcond") != 1e-12 or
                target["kind"] != "forward_return" or target["start_offset"] != 1 or target["end_offset"] != 21 or
                target["entry_field"] != "close" or target.get("price_measure") != "economic_price" or
                c.get("training_weights") != "equal_asset" or c["weights"]["policy"] != "equal_asset" or
                s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or
                s["folds"] != [
                    {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                    {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
                metric["name"] != "RMSE" or c["dependence"].get("axis_scope") != "evaluation"):
            _fail("workflow.evaluator", "age study freezes D01 nine current fields plus known box distance, one log-age and two contained return20 OLS folds")
    if feature["kind"] == "tsfresh_price_information":
        from lei_signal.research.trend_slope_change_information import BASELINE_FEATURES
        refs = ["research.external.mean_abs_log_change20@1.0.0",
                "research.external.return_autocorrelation20_lag1@1.0.0"]
        fields = ["mean_abs_log_change20", "return_autocorrelation20_lag1"]
        allowed_pairs = [(list(BASELINE_FEATURES), [fields[0]]),
                         (list(BASELINE_FEATURES), [fields[1]]),
                         (list(BASELINE_FEATURES), fields),
                         (list(BASELINE_FEATURES[7:]), fields)]
        if (feature["lookback"] != 20 or feature["warmup"] != 252 or
                feature["missing_policy"] != "segmented" or
                feature.get("definition_ref") != refs[0] or
                feature.get("definition_refs") != refs or
                c["question"]["factor_refs"] != refs or
                c["question"].get("sampling") != "daily" or
                e["kind"] != "prediction_ols" or
                (e["baseline_features"], e["added_features"]) not in allowed_pairs or
                target["kind"] != "forward_return" or
                target["start_offset"] != 1 or target["end_offset"] != 21 or
                target["entry_field"] != "close" or
                target.get("price_measure") != "economic_price" or
                c.get("training_weights") != "equal_asset" or
                c["weights"]["policy"] != "equal_asset" or
                s["label_policy"] != "purge" or
                s.get("evaluation_label_policy") != "contained" or
                s["folds"] != [
                    {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                    {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
                metric["name"] != "RMSE" or c["dependence"].get("axis_scope") != "evaluation"):
            _fail("workflow.evaluator", "tsfresh study freezes two exact price expressions and four declared OLS comparisons")
        if (data["mode"] != "synthetic" and
                data.get("qualification", {}).get("adapter") != "top_etf_economic/1.0"):
            _fail("workflow.data.qualification", "tsfresh study requires existing economic OHLC source qualification")
    if feature["kind"] in {"slope_change_information", "simple_top_invalidation_information"}:
        if feature["kind"] == "slope_change_information":
            from lei_signal.research.trend_slope_change_information import BASELINE_FEATURES
        else:
            from lei_signal.research.top_invalidation_information import BASELINE_FEATURES
        if (e["kind"] != "prediction_ols" or e["baseline_features"] != list(BASELINE_FEATURES) or
                e["added_features"] != ["added"] or target["kind"] != "forward_return" or
                target["start_offset"] != 1 or target["end_offset"] != 21 or
                target["entry_field"] != "close" or target.get("price_measure", "economic_price") != "economic_price" or
                c.get("training_weights") != "equal_asset" or c["weights"]["policy"] != "equal_asset" or
                s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or
                s["folds"] != [
                    {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                    {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
                metric["name"] != "RMSE" or c["dependence"].get("axis_scope") != "evaluation"):
            _fail("workflow.evaluator", "semantic study freezes exact B1 plus one expression, two return20 OLS folds")
    if feature["kind"] == "prior_top_dual_break_information":
        from lei_signal.research.prior_top_dual_break_information import BASELINE_FEATURES
        if (e["kind"] != "prediction_ridge" or e["lambda"] != 1.0 or
                e["baseline_features"] != list(BASELINE_FEATURES) or
                e["added_features"] != ["added"] or target["kind"] != "mae" or
                target["start_offset"] != 1 or target["end_offset"] != 21 or
                target["entry_field"] != "close" or target.get("path_field", "close") != "close" or
                target.get("price_measure", "economic_price") != "economic_price" or
                c.get("training_weights") != "equal_asset" or c["weights"]["policy"] != "equal_asset" or
                s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or
                s["folds"] != [
                    {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                    {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
                metric["name"] != "RMSE" or c["dependence"].get("axis_scope") != "evaluation"):
            _fail("workflow.evaluator", "prior-top combination freezes both components in B1 plus their product, two risk20 ridge folds")
    if feature["kind"] == "pullback_layer_change_information":
        from lei_signal.research.pullback_layer_change_information import BASELINE_FEATURES
        if (e["kind"] != "prediction_ridge" or e["lambda"] != 1.0 or
                e["baseline_features"] != list(BASELINE_FEATURES) or
                e["added_features"] != ["added"] or target["kind"] != "mae" or
                target["start_offset"] != 1 or target["end_offset"] != 21 or
                target["entry_field"] != "close" or target.get("path_field", "close") != "close" or
                target.get("price_measure", "economic_price") != "economic_price" or
                c.get("training_weights") != "equal_asset" or c["weights"]["policy"] != "equal_asset" or
                s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or
                s["folds"] != [
                    {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                    {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
                metric["name"] != "RMSE" or c["dependence"].get("axis_scope") != "evaluation"):
            _fail("workflow.evaluator", "pullback-layer study freezes B1 plus layer change, two risk20 ridge folds")
    if feature["kind"] == "key_fluctuation_information":
        if (e["kind"] != "prediction_ols" or
            e["baseline_features"] != ["r1", "ret3", "ret20", "vol20", "ema20_distance", "asset_510050", "asset_510500", "asset_588000"] or
            e["added_features"] != ["added"] or target["kind"] != "mae" or
            target["start_offset"] != 1 or target["end_offset"] != 21 or
            target["entry_field"] != "close" or target.get("path_field", "close") != "close" or
            target.get("price_measure", "economic_price") != "economic_price" or
            c.get("training_weights", "equal_asset") != "equal_asset" or
            c["weights"]["policy"] != "equal_asset" or
            s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or
            s["folds"] != [
                {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
            metric["name"] != "RMSE"):
            _fail("workflow.evaluator", "K01 freezes eight known baseline fields plus K, zero-penalty OLS and two contained MAE20 folds")
    if feature["kind"] == "profile_overhead_information":
        if (e["kind"] != "prediction_ols" or
            e["baseline_features"] != ["r1", "ret3", "ret20", "vol20", "ema20_distance",
                                       "sma60_atr_distance", "prior20_high_atr_distance",
                                       "prior120_high_atr_distance", "price_only_overhead_ratio",
                                       "asset_510050", "asset_510500", "asset_588000"] or
            e["added_features"] != ["added"] or target["kind"] != "forward_return" or
            target["start_offset"] != 1 or target["end_offset"] != 21 or
            target["entry_field"] != "close" or target.get("price_measure", "economic_price") != "economic_price" or
            e.get("lambda") != 0 or e.get("rcond") != 1e-12 or
            c.get("training_weights") != "equal_asset" or c["weights"]["policy"] != "equal_asset" or
            s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or
            s["folds"] != [
                {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}] or
            metric["name"] != "RMSE"):
            _fail("workflow.evaluator", "P01 freezes 12 price/geometry fields plus profile ratio, equal-asset twofold return20 OLS")
    if feature["kind"] == "double_ma_order_information":
        if (e["kind"] != "prediction_ols" or e["baseline_features"] != ['distance_sma20', 'distance_sma60', 'distance_sma120', 'distance_ema20', 'distance_ema60', 'distance_ema120', 'ret20', 'vol20', 'sma60_up5', 'asset_510050', 'asset_510500', 'asset_588000'] or e["added_features"] != ["added"] or target["kind"] != "mae" or target["start_offset"] != 1 or target["end_offset"] != 21 or target["entry_field"] != "close" or target.get("path_field", "close") != "close" or target.get("price_measure", "economic_price") != "economic_price" or c["weights"]["policy"] != "equal_asset" or c.get("training_weights") != "equal_asset" or s["label_policy"] != "purge" or s.get("evaluation_label_policy") != "contained" or s["folds"] != [{'train_end': '2024-12-31', 'eval_start': '2025-01-01', 'eval_end': '2025-12-31'}, {'train_end': '2025-12-31', 'eval_start': '2026-01-01', 'eval_end': '2026-06-30'}] or metric["name"] != "RMSE" or metric["attention_threshold"] != 0.10 or c["dependence"].get("axis_scope") != "evaluation"):
            _fail("workflow.evaluator", "T03 freezes exact pairedOLS/X/MAE20/RMSEpp/evaluationaxis/twofold design")
    if feature["kind"] == "future_deduction_box_information":
        if (e["kind"] != "prediction_ols" or
            e["baseline_features"] != ["prior20high_distance", "ret20", "ema20_distance", "r1", "vol20", "sma60_up", "asset_510050", "asset_510500", "asset_588000"] or
            e["added_features"] != ["added"] or
            target["kind"] != "mae" or target["start_offset"] != 1 or
            target["end_offset"] != 21 or target["entry_field"] != "close" or
            target.get("path_field", "close") != "close" or
            target.get("price_measure", "economic_price") != "economic_price" or
            c.get("training_weights", "equal_asset") != "equal_asset" or
            c["weights"]["policy"] != "equal_asset" or
            s.get("evaluation_label_policy") != "contained" or
            s["folds"] != [
                {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}]):
            _fail("workflow.target", "D01 freezes paired equal-asset OLS and two contained t+1..t+21 MAE folds")
    if feature["kind"] == "simple_top3_information" and (e["kind"] != "prediction_ridge" or target["kind"] != "mae" or target["start_offset"] != 1 or target["end_offset"] != 21 or target["entry_field"] != "close" or target.get("path_field", "close") != "close" or target.get("price_measure", "economic_price") != "economic_price"):
        _fail("workflow.target", "T01 freezes fixed t+1..t+21 closing-path MAE prediction")
    if e["kind"] == "event_risk" and (feature["kind"] not in {"decline_event", "volume_anomaly_information"} or target["kind"] != "downside_event"):
        _fail("workflow.evaluator", "event/risk adapter requires an event and a risk target")
    if feature["kind"] == "volume_anomaly_information" and (e["kind"] != "event_risk" or target["kind"] != "downside_event" or target["start_offset"] != 1 or target["end_offset"] != 21 or target["threshold"] != 5 or target["entry_field"] != "close" or target.get("price_measure", "economic_price") != "economic_price"):
        _fail("workflow.target", "V01 freezes optional grouped risk check at t+1..t+21 close, loss >=5%")
    if e["kind"] == "event_risk" and (e["baseline_features"] != ["existing_state"] or e["added_features"] != ["added"]):
        _fail("workflow.evaluator", "event adapter uses the declared state then state+event information sets")
    if c.get("training_weights", "equal_asset") not in {"equal_asset", "equal_date"}:
        _fail("workflow.training_weights", "unsupported training weighting policy")
    price_basis = c["question"]["target"]["price_basis"]
    expected_basis = (target["entry_field"] + "_to_close" if target["kind"] in {"forward_return", "up", "downside_event"}
                      else target["entry_field"] + "_to_" + target.get("path_field", "close") + "_path")
    if price_basis != expected_basis:
        _fail("workflow.target.price_basis", "question price basis differs from implemented endpoints/path")
    if target.get("path_field", "close") not in {"close", "low"} or (target["kind"] == "max_drawdown" and target.get("path_field", "close") != "close"):
        _fail("workflow.target.path_field", "only explicit low-price MAE or closing-price drawdown is supported")
    if feature["kind"] == "green_black_state60_information":
        from lei_signal.research.green_black_state_information import BASELINE_FEATURES
        ref = "research.trend.green_black60_state@1.0.0"
        fixed_folds = [
            {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
            {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"},
        ]
        if (schema_version != "research-workflow/1.1" or feature.get("definition_ref") != ref or
                c["question"]["factor_refs"] != [ref] or feature["lookback"] != 60 or
                feature["warmup"] != 252 or feature["missing_policy"] != "segmented" or
                target["kind"] not in {"forward_return", "mae"} or target["start_offset"] != 1 or
                target["end_offset"] != 61 or target["entry_field"] != "close" or
                target.get("path_field", "close") != "close" or measure != "economic_price" or
                e["kind"] != "prediction_ols" or e["baseline_features"] != list(BASELINE_FEATURES) or
                e["added_features"] != ["color60_green", "color60_black"] or
                e.get("lambda") != 0 or e.get("rcond") != 1e-12 or
                e.get("minimum_training_rows") != 22 or
                (data["mode"] != "synthetic" and s["folds"] != fixed_folds)):
            _fail("workflow.green_black_state60", "requires exact categorical state, fixed 61-close target and baseline")
    w = _mapping(c["weights"], "workflow.weights", {"policy", "comparison"})
    if w["policy"] not in {"equal_asset", "equal_date"} or w["comparison"] != "fixed_common":
        _fail("workflow.weights", "paired comparison requires a supported common weighting policy")
    dep = _mapping(c["dependence"], "workflow.dependence", {"block_length", "draws", "seed"})
    for key in ("block_length", "draws"):
        if type(dep[key]) is not int or dep[key] < 1:
            _fail(f"workflow.dependence.{key}", "must be a positive integer")
    if type(dep["seed"]) is not int:
        _fail("workflow.dependence.seed", "must be integer")
    if dep.get("axis_scope", "full") not in {"full", "evaluation"}:
        _fail("workflow.dependence.axis_scope", "unsupported calendar interval")
    if c.get("descriptive"):
        desc = _mapping(c["descriptive"], "workflow.descriptive", {"horizons", "groups", "minimum_each_background", "anchor", "path"})
        if feature["kind"] != "a01_signed_band" or desc["anchor"] != "next_close" or desc["path"] != "close":
            _fail("workflow.descriptive", "current grouped price adapter needs A01 next-close closing paths")
        if desc["horizons"] != [5, 10, 20, 60, 120] or desc["groups"] != ["deep_below", "slightly_below", "inside", "slightly_above", "far_above"]:
            _fail("workflow.descriptive", "this finite A01 batch preserves all five states and declared horizons")
        if type(desc["minimum_each_background"]) is not int or desc["minimum_each_background"] < 1:
            _fail("workflow.descriptive.minimum_each_background", "positive common-support minimum needed")
    b = _mapping(c["budget"], "workflow.budget", {"scientific_variants", "execution_seconds", "max_rows"})
    if feature["kind"] in {"slope_change_risk_information", "ema_only_wait_age_risk_information"} and (
            b["scientific_variants"] != 1 or b["execution_seconds"] != 7200):
        _fail("workflow.budget", "daily risk freezes one scientific configuration and a 7200-second ceiling")
    if feature["kind"] == "ema_sma_waiting_path" and (type(b.get("real_runs")) is not int or b["real_runs"] < 0):
        _fail("workflow.budget.real_runs", "waiting path requires an explicit nonnegative real-run ceiling")
    for key in ("scientific_variants", "max_rows"):
        if type(b[key]) is not int or b[key] < 1:
            _fail(f"workflow.budget.{key}", "must be positive integer")
    _finite_number(b["execution_seconds"], "workflow.budget.execution_seconds")
    if b["execution_seconds"] <= 0:
        _fail("workflow.budget.execution_seconds", "must be positive")
    h = _mapping(c["history"], "workflow.history", {"family", "ledger_path"})
    if h["family"] != c["question"]["hypothesis_family"]:
        _fail("workflow.history.family", "family identity cannot be reset by task naming")
    _nonempty_text(h["ledger_path"], "workflow.history.ledger_path")
    review = _mapping(c["controller_review"], "workflow.controller_review", {
        "universe_fit", "proxy_fidelity", "method_fit", "conclusion_scope",
    })
    normalized_reasons = []
    for key in ("universe_fit", "proxy_fidelity", "method_fit", "conclusion_scope"):
        item = _mapping(review[key], f"workflow.controller_review.{key}", {"reason", "source_refs"})
        _nonempty_text(item["reason"], f"workflow.controller_review.{key}.reason")
        normalized_reasons.append(" ".join(item["reason"].split()))
        _nonempty_sequence(item["source_refs"], f"workflow.controller_review.{key}.source_refs")
        if "verified" in item:
            _fail("workflow.controller_review", "rationale is a judgment, not a verified flag")
    if schema_version == "research-workflow/1.1" and len(set(normalized_reasons)) != len(normalized_reasons):
        _fail("workflow.controller_review", "1.1 requires four distinct reasons after whitespace normalization; this checks wording only, not semantic quality")
    p = _mapping(c["publication"], "workflow.publication", {
        "report_path", "category", "claimed_scope", "conclusion",
    })
    _nonempty_text(p["report_path"], "workflow.publication.report_path")
    _nonempty_text(p["category"], "workflow.publication.category")
    if p["claimed_scope"] not in {"full", "partial"} or p["conclusion"] not in {"not_supported", "insufficient", "supported"}:
        _fail("workflow.publication", "unsupported closure claim")
    if data["mode"] == "synthetic" and p["conclusion"] == "supported":
        _fail("workflow.publication", "synthetic evidence cannot support a market factor")
    if not isinstance(c["sources"], list):
        _fail("workflow.sources", "must be a list of actual path/hash bindings")
    for item in c["sources"]:
        _mapping(item, "workflow.sources[]", {"path", "sha256"})


def _validate_research_design(contract: dict) -> None:
    design = _mapping(contract.get("research_design"), "workflow.research_design", {"claim_mapping", "sample_fit"})
    claim = _mapping(design["claim_mapping"], "workflow.research_design.claim_mapping", {
        "original_statement", "source_section", "proxy_definition", "preserved_conditions",
        "omitted_conditions", "decision_use", "observation_time", "intended_action_time",
        "application_scope", "tested_scope", "unresolved_uses",
    })
    for key in ("original_statement", "source_section", "proxy_definition", "decision_use",
                "observation_time", "intended_action_time", "application_scope", "tested_scope"):
        _nonempty_text(claim[key], f"workflow.research_design.claim_mapping.{key}")
    _nonempty_sequence(claim["preserved_conditions"], "workflow.research_design.claim_mapping.preserved_conditions")
    for key in ("omitted_conditions", "unresolved_uses"):
        value = claim[key]
        if not isinstance(value, list):
            _fail(f"workflow.research_design.claim_mapping.{key}", "must be a list")
        for i, item in enumerate(value):
            _nonempty_text(item, f"workflow.research_design.claim_mapping.{key}[{i}]")

    sample = _mapping(design["sample_fit"], "workflow.research_design.sample_fit", {
        "qualification_artifact", "qualification_sha256", "outcome_values_used_for_design", "unit", "assets", "observations",
        "dates", "episodes", "paired_support", "dependence", "model_feature_count", "rationale", "decision",
    })
    for key in ("qualification_artifact", "qualification_sha256", "unit", "paired_support", "dependence", "rationale"):
        _nonempty_text(sample[key], f"workflow.research_design.sample_fit.{key}")
    qualification_hash = sample["qualification_sha256"]
    if len(qualification_hash) != 64 or any(char not in "0123456789abcdefABCDEF" for char in qualification_hash):
        _fail("workflow.research_design.sample_fit.qualification_sha256", "must be a 64-character hexadecimal SHA-256")
    if type(sample["outcome_values_used_for_design"]) is not bool:
        _fail("workflow.research_design.sample_fit.outcome_values_used_for_design", "must be boolean")
    if sample["outcome_values_used_for_design"]:
        _fail("workflow.research_design.sample_fit.outcome_values_used_for_design", "must be false; future outcome values cannot shape design")
    for key in ("assets", "observations", "dates", "model_feature_count"):
        if type(sample[key]) is not int or sample[key] < 0:
            _fail(f"workflow.research_design.sample_fit.{key}", "must be a nonnegative integer")
    episodes = sample["episodes"]
    if episodes is not None and (type(episodes) is not int or episodes < 0):
        _fail("workflow.research_design.sample_fit.episodes", "must be a nonnegative integer or null")
    evaluator = contract["evaluator"]
    features = set(evaluator["baseline_features"]) | set(evaluator["added_features"])
    if evaluator["kind"] == "waiting_path_description":
        if sample["model_feature_count"] != 0 or sample["decision"] != "describe_only":
            _fail("workflow.research_design.sample_fit", "waiting-path description requires decision=describe_only and zero model features")
        return
    if sample["model_feature_count"] != len(features):
        _fail("workflow.research_design.sample_fit.model_feature_count", "must equal the distinct baseline and added feature count")
    decision = sample["decision"]
    if decision not in {"estimate", "describe_only", "qualification_only"}:
        _fail("workflow.research_design.sample_fit.decision", "must be estimate, describe_only, or qualification_only")
    if decision != "estimate":
        _fail("workflow.research_design.sample_fit.decision", f"{decision} does not permit a statistical run; retain the qualification report without a statistical run")
