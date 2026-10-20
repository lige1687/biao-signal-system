"""可复用预测/状态检验：IC 与状态诊断分流。

- 逐观察日横截面 Rank IC：薄映射到 ``momentum_prototype.rank_diagnostic``
  的并列平均名次数学核；每期输出 n、剔除原因、日期，不只给均值。
- 二元状态（双均线）：状态真/假时后续结果的样本数、均值、中位数与差额；
  缺失/未就绪单列，不强制排名 IC。
- 共同状态（宽度，universe 轴）：按明确目标实体做跨日期诊断；
  误请求横截面 IC 时返回 not_applicable，不把同日复制成多份独立证据。
- 统计不确定性第一版不伪造：稳健置信区间明确 not_implemented；
  时间相关不当独立样本显著性证据；等权分组只是诊断，不是可投资因子收益。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.research.factor_lab.contracts import (
    IdentityFormatError,
    require_tz_aware,
    validate_protocol,
)
from lei_signal.research.momentum_prototype import rank_diagnostic

EQUAL_WEIGHT_NOTE = "等权均值仅为诊断，不构成可投资因子收益"
DEPENDENCE_NOTE = (
    "重叠标签窗与共同状态使各期样本互相不独立；相关系数只是描述，"
    "不构成'结果不是巧合'的显著性证据"
)
NOT_IMPLEMENTED_CI = "not_implemented"

TARGET_REQUIRED = {"observation_date", "entity_id", "label_start", "label_end",
                   "label_available_at", "target"}


def _validated_targets(targets: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(targets, pd.DataFrame) or not set(targets.columns) >= TARGET_REQUIRED:
        got = (sorted(targets.columns) if isinstance(targets, pd.DataFrame)
               else type(targets))
        raise IdentityFormatError(
            f"targets need columns {sorted(TARGET_REQUIRED)}; got {got}")
    if targets.duplicated(["observation_date", "entity_id"]).any():
        raise IdentityFormatError("duplicate (observation_date, entity_id) in targets")
    out = targets.copy()
    for col in ("observation_date", "label_start", "label_end"):
        out[col] = pd.to_datetime(out[col])
    inverted = out["label_start"].notna() & out["label_end"].notna() \
        & (out["label_start"] > out["label_end"])
    if inverted.any():
        raise IdentityFormatError(
            f"label time inverted on {int(inverted.sum())} rows (label_start > label_end)")
    # None/NaT 归一为 NaT：进入统计前统一给出 label_available_unknown；
    # 非空但无时区是格式错误（无法证明何时可知）。
    out["label_available_at"] = [
        require_tz_aware(ts, "label_available_at")
        if pd.notna(ts) else pd.NaT
        for ts in out["label_available_at"]
    ]
    return out


def _row_exclusion_reason(row, cutoff: pd.Timestamp,
                          feature_lag_days: int) -> str | None:
    """共享逐行排除判定：值缺失/非有限 → 时间顺序 → 成熟 → 可知 → 特征可得。

    clean = 排除原因为 None 的行；n、IC、状态均值与分组只消费 clean 行。
    """
    if row.get("_target_present") != "both":
        return "no_target_row"
    if pd.isna(row.get("value")):
        msg = row.get("missing_reason")
        return f"value_missing:{msg}" if pd.notna(msg) else "value_missing"
    value = pd.to_numeric(row.get("value"), errors="coerce")
    if pd.isna(value) or not np.isfinite(value):
        return "value_not_finite"
    if pd.isna(row.get("target")):
        return "target_missing"
    target = pd.to_numeric(row.get("target"), errors="coerce")
    if pd.notna(target) and not np.isfinite(target):
        return "target_not_finite"
    if pd.isna(row.get("label_start")) or pd.isna(row.get("label_end")):
        return "label_time_missing"
    if row["label_start"] <= row["observation_date"]:
        return "label_window_not_after_observation"
    if pd.Timestamp(row["label_end"]).date() > cutoff.date():
        return "label_not_mature_by_cutoff"
    if pd.isna(row.get("label_available_at")):
        return "label_available_unknown"
    if pd.Timestamp(row["label_available_at"]) > cutoff:
        return "label_unknown_at_evaluation"
    if feature_lag_days > 0:
        # 特征在观察日决策时点之后才可知：整行不得进入统计。
        return "feature_not_available_by_decision_time"
    return None


def _instrument_pairs(batch_values: pd.DataFrame, targets: pd.DataFrame,
                      cutoff: pd.Timestamp, feature_lag_days: int = 0) -> pd.DataFrame:
    values = batch_values.copy()
    values["observation_date"] = pd.to_datetime(values["observation_date"])
    pairs = values.merge(targets, on=["observation_date", "entity_id"],
                         how="outer", indicator="_target_present")
    pairs["exclusion_reason"] = pairs.apply(
        _row_exclusion_reason, axis=1, cutoff=cutoff, feature_lag_days=feature_lag_days)
    return pairs


def _universe_pairs(batch_values: pd.DataFrame, targets: pd.DataFrame,
                    entity: str, cutoff: pd.Timestamp,
                    feature_lag_days: int = 0) -> pd.DataFrame:
    values = batch_values.copy()
    values["observation_date"] = pd.to_datetime(values["observation_date"])
    entity_targets = targets[targets["entity_id"].astype(str) == entity]
    pairs = values.merge(entity_targets, on=["observation_date"], how="outer",
                         suffixes=("", "_target"), indicator="_target_present")
    pairs = pairs.drop(columns=["entity_id_target"], errors="ignore")
    pairs["entity_id"] = pairs["entity_id"].fillna(entity)
    pairs["exclusion_reason"] = pairs.apply(
        _row_exclusion_reason, axis=1, cutoff=cutoff, feature_lag_days=feature_lag_days)
    return pairs


def _cross_section_ic(pairs: pd.DataFrame, *, min_pairs: int = 3) -> dict:
    """逐观察日横截面IC。

    所有观察日都保留（含完全没有目标行的日期，n=0），不给静默丢日期；
    min_pairs 用声明值实际执行，输出与行为一致。
    """
    periods = []
    for day, group in pairs.groupby("observation_date"):
        excluded = group["exclusion_reason"].dropna().value_counts().to_dict()
        clean = group[group["exclusion_reason"].isna()]
        n = int(len(clean))
        if n < min_pairs:
            periods.append({
                "date": str(pd.Timestamp(day).date()),
                "n": n,
                "ic": None,
                "reason": "fewer_than_min_pairs",
                "excluded_counts": {str(k): int(v) for k, v in excluded.items()},
            })
            continue
        frame = pd.DataFrame({
            "momentum": pd.to_numeric(clean["value"], errors="coerce"),
            "target": pd.to_numeric(clean["target"], errors="coerce"),
        })
        result = rank_diagnostic(frame)
        reason = result["reason"]
        value = result["value"]
        if value is None and reason is None:
            reason = "constant_rank"
        periods.append({
            "date": str(pd.Timestamp(day).date()),
            "n": n,
            "ic": value,
            "reason": reason,
            "excluded_counts": {str(k): int(v) for k, v in excluded.items()},
        })
    values = [p["ic"] for p in periods if p["ic"] is not None]
    return {
        "diagnostic": "cross_section_ic",
        "tie_method": "average",
        "min_pairs": min_pairs,
        "n_periods": len(periods),
        "n_periods_with_value": len(values),
        "mean_ic": sum(values) / len(values) if values else None,
        "periods": periods,
        "summary_caveats": {
            "ic_meaning": "当期分数排序与随后结果排序的吻合程度；不等于可获利或策略价值",
            "correlation_robust_confidence_interval": NOT_IMPLEMENTED_CI,
            "dependence_risk": DEPENDENCE_NOTE,
        },
    }


def _state_outcomes(pairs: pd.DataFrame) -> dict:
    entities = []
    in_window = pairs[pairs["exclusion_reason"] != "no_target_row"]
    for entity, group in in_window.groupby("entity_id"):
        excluded = group["exclusion_reason"].dropna().value_counts().to_dict()
        usable = group[group["exclusion_reason"].isna()].copy()
        usable["state"] = pd.to_numeric(usable["value"], errors="coerce")
        usable = usable[usable["state"].isin([0, 1])]
        groups = {}
        for label, flag in (("state_true", 1), ("state_false", 0)):
            subset = usable[usable["state"] == flag]["target"]
            groups[label] = {
                "n": int(len(subset)),
                "mean_target": float(subset.mean()) if len(subset) else None,
                "median_target": float(subset.median()) if len(subset) else None,
            }
        mean_true = groups["state_true"]["mean_target"]
        mean_false = groups["state_false"]["mean_target"]
        entities.append({
            "entity_id": str(entity),
            "n_usable": int(len(usable)),
            "groups": groups,
            "mean_difference_true_minus_false": (
                mean_true - mean_false
                if mean_true is not None and mean_false is not None else None
            ),
            "excluded_counts": {str(k): int(v) for k, v in excluded.items()},
            "not_ready_single_listed": True,
        })
    return {
        "diagnostic": "state_outcomes",
        "entities": entities,
        "summary_caveats": {
            "meaning": "状态为真/假时后续结果的样本数与均值差额；不是交易收益",
            "same_state_episode_not_independent": DEPENDENCE_NOTE,
            "correlation_robust_confidence_interval": NOT_IMPLEMENTED_CI,
        },
    }


def _time_series_state(pairs: pd.DataFrame, entity: str) -> dict:
    excluded = pairs["exclusion_reason"].dropna().value_counts().to_dict()
    usable = pairs[pairs["exclusion_reason"].isna()]
    frame = pd.DataFrame({
        "value": pd.to_numeric(usable["value"], errors="coerce"),
        "target": pd.to_numeric(usable["target"], errors="coerce"),
    }).dropna()
    n = len(frame)
    entry: dict = {
        "target_entity": entity,
        "n": n,
        "excluded_counts": {str(k): int(v) for k, v in excluded.items()},
    }
    if n < 3:
        entry.update({"status": "insufficient", "reason": "fewer_than_three_pairs",
                      "mean_state": None, "mean_target": None,
                      "pearson_over_time": None, "spearman_over_time": None})
        return entry
    entry.update({
        "status": "descriptive_only",
        "mean_state": float(frame["value"].mean()),
        "mean_target": float(frame["target"].mean()),
        "pearson_over_time": float(frame["value"].corr(frame["target"])),
        "spearman_over_time": float(frame["value"].corr(frame["target"],
                                                        method="spearman")),
    })
    return entry


def _quantile_groups_q2(date_group: pd.DataFrame) -> dict:
    """q=2 固定分组：按不同分数的中位数分界，并列不拆散。"""
    usable = date_group[date_group["exclusion_reason"].isna()].copy()
    usable["value"] = pd.to_numeric(usable["value"], errors="coerce")
    usable["target"] = pd.to_numeric(usable["target"], errors="coerce")
    usable = usable.dropna(subset=["value"])
    distinct = sorted(usable["value"].unique())
    if len(distinct) < 2:
        return {"status": "insufficient", "reason": "insufficient_distinct_values",
                "n_distinct": len(distinct)}
    if len(distinct) % 2 == 0:
        boundary = (distinct[len(distinct) // 2 - 1] + distinct[len(distinct) // 2]) / 2
    else:
        boundary = distinct[len(distinct) // 2]
    low = usable[usable["value"] < boundary]
    high = usable[usable["value"] > boundary]
    middle = usable[usable["value"] == boundary]
    return {
        "status": "ok",
        "boundary_value": float(boundary),
        "groups": {
            "low": {"n": int(len(low)),
                    "mean_target": float(low["target"].mean()) if len(low) else None,
                    "entities": [str(e) for e in low["entity_id"]]},
            "high": {"n": int(len(high)),
                     "mean_target": float(high["target"].mean()) if len(high) else None,
                     "entities": [str(e) for e in high["entity_id"]]},
        },
        "excluded_middle_entities": [str(e) for e in middle["entity_id"]],
        "note": EQUAL_WEIGHT_NOTE,
    }


def evaluate_predictive(batch, targets: pd.DataFrame, *, protocol: dict) -> dict:
    """把通用 value/target 配对分流到横截面 IC / 状态 / 共同状态诊断。"""
    validate_protocol(protocol, expected_kinds={"predictive_diagnostic", "state_diagnostic"})
    spec = protocol.get("diagnostics")
    allowed_keys = {"type", "min_pairs", "quantiles", "feature_available_lag_days",
                    "target_entities"}
    if not isinstance(spec, dict) or spec.get("type") not in {
        "cross_section_ic", "state_outcomes", "time_series_state"}:
        raise IdentityFormatError(
            "protocol.diagnostics.type must be one of cross_section_ic/"
            "state_outcomes/time_series_state"
        )
    unknown_keys = set(spec) - allowed_keys
    if unknown_keys:
        raise IdentityFormatError(
            f"protocol.diagnostics has undeclared keys: {sorted(unknown_keys)}")
    min_pairs = spec.get("min_pairs", 3)
    if not isinstance(min_pairs, int) or isinstance(min_pairs, bool) or min_pairs < 3:
        raise IdentityFormatError("diagnostics.min_pairs must be an integer >= 3")
    feature_lag = spec.get("feature_available_lag_days", 0)
    if not isinstance(feature_lag, int) or isinstance(feature_lag, bool) or feature_lag < 0:
        raise IdentityFormatError(
            "diagnostics.feature_available_lag_days must be an integer >= 0")
    requested = spec["type"]
    axis = batch.metadata["entity_axis"]
    value_type = batch.metadata["value_type"]

    cutoff_raw = protocol.get("evaluation_cutoff")
    if cutoff_raw is None:
        raise IdentityFormatError("predictive evaluation requires protocol.evaluation_cutoff")
    cutoff = require_tz_aware(cutoff_raw, "evaluation_cutoff")

    base = {
        "definition_reference": batch.metadata["reference"],
        "entity_axis": axis,
        "value_type": value_type,
        "evaluation_cutoff": str(cutoff),
        "protocol": batch.metadata["protocol"],
    }

    def not_applicable(reason: str) -> dict:
        return {**base, "diagnostic": requested, "status": "not_applicable",
                "reason": reason}

    if requested == "time_series_state":
        if axis != "universe":
            return not_applicable(
                "time_series_state 面向 universe 共同状态；单产品配对请用 "
                "cross_section_ic 或 state_outcomes"
            )
        entities = spec.get("target_entities")
        if not isinstance(entities, list) or not entities:
            raise IdentityFormatError(
                "time_series_state requires protocol.diagnostics.target_entities list"
            )
        validated = _validated_targets(targets)
        entries = [
            _time_series_state(
                _universe_pairs(batch.values, validated, str(e), cutoff,
                                feature_lag_days=feature_lag), str(e)
            )
            for e in entities
        ]
        return {**base, "diagnostic": "time_series_state", "entities": entries,
                "summary_caveats": {
                    "meaning": "同一共同状态序列与单一目标实体后续结果的跨日期相关；描述性",
                    "time_correlation_not_significance": DEPENDENCE_NOTE,
                    "correlation_robust_confidence_interval": NOT_IMPLEMENTED_CI,
                }}

    if requested == "cross_section_ic" and axis == "universe":
        return not_applicable(
            "universe 共同状态同日对所有产品相同；复制成横截面不是独立证据"
        )
    if requested == "cross_section_ic" and value_type == "boolean":
        return not_applicable("二元状态不走排名IC；请用 state_outcomes（真/假后续结果）")
    if requested == "state_outcomes" and value_type != "boolean":
        return not_applicable("state_outcomes 需要二元状态值；连续值请用 cross_section_ic")

    pairs = _instrument_pairs(batch.values, _validated_targets(targets), cutoff,
                              feature_lag_days=feature_lag)
    if requested == "cross_section_ic":
        result = _cross_section_ic(pairs, min_pairs=min_pairs)
        if spec.get("quantiles") is not None:
            q = spec["quantiles"].get("q")
            if q != 2:
                raise IdentityFormatError("only explicit q=2 grouping is supported")
            groups = []
            for day, date_group in pairs.groupby("observation_date"):
                entry = _quantile_groups_q2(date_group)
                groups.append({"date": str(pd.Timestamp(day).date()), **entry})
            result["quantile_groups_q2"] = groups
            result["quantile_note"] = EQUAL_WEIGHT_NOTE
        return {**base, **result}
    return {**base, **_state_outcomes(pairs)}
