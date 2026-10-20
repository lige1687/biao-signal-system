"""过拟合风险与试验史检查：识别证据薄弱、偷看未来和反复挑优的风险。

这不是"证明没有过拟合"的开关：输出永远包含"风险尚未排除"，
没有 not_overfit=true。协议先固定按时间顺序的开发/验证/保留段；
本轮无训练器、不拟合模型，只生成合法配对与分段诊断。
前处理第一版明确 none，不做全历史标准化/填补/截尾。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.research.factor_lab.contracts import (
    IdentityFormatError,
    require_tz_aware,
    validate_protocol,
)
from lei_signal.research.momentum_prototype import rank_diagnostic

SEGMENTS = ("dev", "validation", "holdout")
TRIAL_OUTCOMES = {"success", "failed", "abandoned"}
TRIAL_REQUIRED = {
    "trial_id",
    "definition_reference",
    "parameters",
    "pool",
    "target",
    "input_identity",
    "split_id",
    "outcome",
    "selection_basis",
    "seen_segments",
    "run_version",
}

RISK_NOT_EXCLUDED = "not_excluded"
LIMITATIONS = [
    "本审计只识别已声明的结构风险；没有任何测试能简单宣布排除过拟合",
    "重叠标签与共享状态使有效样本小于表面行数；本输出不提供相关性稳健推断",
    "未列出的尝试（含其他任务/会话的尝试）无法由本工具发现；历史未知时按 unknown 处理",
    "已看过的保留段不能靠重命名或换工具恢复为未知",
]


def _validate_segment_cutoffs(cutoffs, global_cutoff) -> dict[str, pd.Timestamp]:
    """每段评价/拟合截止：必填、带时区、依次不提前、不晚于全局截止。"""
    if not isinstance(cutoffs, dict) or set(SEGMENTS) - set(cutoffs):
        raise IdentityFormatError(
            f"protocol.validation.segment_cutoffs required for {SEGMENTS} "
            "(tz-aware); 不暗猜段边界时刻")
    parsed: dict[str, pd.Timestamp] = {}
    for name in SEGMENTS:
        ts = pd.Timestamp(cutoffs[name])
        if ts.tzinfo is None:
            raise IdentityFormatError(
                f"segment_cutoffs.{name} must be timezone-aware: {cutoffs[name]!r}")
        parsed[name] = ts
    if global_cutoff is not None:
        for name in SEGMENTS:
            if parsed[name] > global_cutoff:
                raise IdentityFormatError(
                    f"segment_cutoffs.{name} must not exceed the global evaluation_cutoff")
    if not (parsed["dev"] <= parsed["validation"] <= parsed["holdout"]):
        raise IdentityFormatError("segment_cutoffs must be in chronological order")
    return parsed


def _validate_split(split: dict) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    if not isinstance(split, dict) or set(SEGMENTS) - set(split):
        raise IdentityFormatError(f"protocol.validation.split needs segments {SEGMENTS}")
    bounds = []
    for name in SEGMENTS:
        value = split[name]
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise IdentityFormatError(f"split.{name} must be [start, end]")
        start = pd.Timestamp(value[0])
        end = pd.Timestamp(value[1])
        if start > end:
            raise IdentityFormatError(f"split.{name} start after end")
        bounds.append((name, start, end))
    for (a, _, end_a), (b, start_b, _) in zip(bounds, bounds[1:], strict=False):
        if start_b <= end_a:
            raise IdentityFormatError(
                f"segments out of order or overlapping: {a}.end={end_a.date()} >= "
                f"{b}.start={start_b.date()}"
            )
    return bounds


def _segment_of(day: pd.Timestamp, bounds) -> str | None:
    for name, start, end in bounds:
        if start <= day <= end:
            return name
    return None


def _trial_record(trial: dict, index: int) -> dict:
    if not isinstance(trial, dict):
        raise IdentityFormatError(f"trials[{index}] must be a dict")
    missing = TRIAL_REQUIRED - set(trial)
    if missing:
        raise IdentityFormatError(f"trials[{index}] missing keys: {sorted(missing)}")
    if trial["outcome"] not in TRIAL_OUTCOMES:
        raise IdentityFormatError(
            f"trials[{index}].outcome must be one of {sorted(TRIAL_OUTCOMES)}"
        )
    seen = trial["seen_segments"]
    if not isinstance(seen, list) or any(s not in SEGMENTS for s in seen):
        raise IdentityFormatError(f"trials[{index}].seen_segments invalid: {seen}")
    return {**trial, "seen_segments": [str(s) for s in seen]}


def _segment_ic(segment_pairs: pd.DataFrame) -> dict | None:
    usable = segment_pairs[segment_pairs["exclusion_reason"].isna()]
    if usable.empty or "value" not in usable or "target" not in usable:
        return None
    frame = pd.DataFrame({
        "momentum": pd.to_numeric(usable["value"], errors="coerce"),
        "target": pd.to_numeric(usable["target"], errors="coerce"),
    }).dropna()
    result = rank_diagnostic(frame)
    return {"n": result["n"], "ic_pooled_over_segment": result["value"],
            "reason": result["reason"],
            "note": "段内合并相关仅作方向描述；合并跨日样本不是独立证据"}


def audit_validation(pairs: pd.DataFrame, trials: list[dict] | None, *,
                     protocol: dict) -> dict:
    """按冻结切分审计配对样本与尝试史，输出逐项风险证据。"""
    validate_protocol(protocol, expected_kinds={"predictive_diagnostic", "state_diagnostic"})
    spec = protocol.get("validation")
    if not isinstance(spec, dict):
        raise IdentityFormatError("protocol.validation section required")
    if spec.get("preprocessing", "none") != "none":
        raise IdentityFormatError(
            "preprocessing must be explicitly 'none' in this version; "
            "全历史标准化/填补/截尾未实现且不默认"
        )
    bounds = _validate_split(spec.get("split"))
    seen = spec.get("seen")
    if not isinstance(seen, dict) or set(SEGMENTS) - set(seen) or any(
        not isinstance(v, bool) for v in seen.values()
    ):
        raise IdentityFormatError(f"protocol.validation.seen must mark {SEGMENTS} booleans")
    global_cutoff = protocol.get("evaluation_cutoff")
    global_cutoff = pd.Timestamp(global_cutoff) if global_cutoff is not None else None
    segment_cutoffs = _validate_segment_cutoffs(spec.get("segment_cutoffs"), global_cutoff)

    required_cols = {"observation_date", "entity_id", "label_start", "label_end"}
    if not isinstance(pairs, pd.DataFrame) or not required_cols <= set(pairs.columns):
        raise IdentityFormatError(
            f"pairs need columns {sorted(required_cols)} (label_available_at 可选但建议)"
        )
    frame = pairs.copy()
    for col in ("observation_date", "label_start", "label_end"):
        frame[col] = pd.to_datetime(frame[col])
    if "exclusion_reason" not in frame:
        frame["exclusion_reason"] = None
    if "label_available_at" in frame:
        frame["label_available_at"] = [
            require_tz_aware(ts, "label_available_at") if pd.notna(ts) else None
            for ts in frame["label_available_at"]
        ]

    frame["segment"] = [
        _segment_of(pd.Timestamp(day), bounds) for day in frame["observation_date"]
    ]

    split_findings = []
    overlap_findings = []
    sample_counts = {}
    direction_notes = []

    unassigned = frame[frame["segment"].isna()]
    if len(unassigned):
        split_findings.append({
            "code": "samples_outside_declared_segments",
            "n": int(len(unassigned)),
            "detail": "落在所有已声明分段之外的观察不参与分段统计",
        })

    segment_names = [name for name, _, _ in bounds]
    for name, _start, _end in bounds:
        seg = frame[frame["segment"] == name].copy()
        raw_n = int(len(seg))
        next_name = (segment_names[segment_names.index(name) + 1]
                     if name != "holdout" else None)
        next_start = bounds[segment_names.index(next_name)][1] if next_name else None
        seg_cutoff = segment_cutoffs[name]

        # naive 可得时刻是格式错误（无法证明何时可知）；NaT 是未知，进排除。
        if len(seg) and "label_available_at" in seg:
            for ts in seg["label_available_at"]:
                if pd.notna(ts) and pd.Timestamp(ts).tzinfo is None:
                    raise IdentityFormatError(
                        "label_available_at must be timezone-aware; "
                        "无法证明何时可知")
        empty = pd.Series([], dtype="datetime64[ns]")
        ends = (pd.to_datetime(seg["label_end"], errors="coerce")
                if len(seg) else empty)
        avails = (pd.to_datetime(seg["label_available_at"], errors="coerce")
                  if len(seg) and "label_available_at" in seg
                  else pd.Series([pd.NaT] * len(seg), index=seg.index))
        unknown_avail = avails.isna()
        time_missing = ends.isna()
        immature = ends.notna() & (ends.dt.date > seg_cutoff.date())
        if avails.notna().any():
            # 走到这里非空值必然已带时区（naive 已在前面被拒绝）。
            known_late = avails.notna() & (avails > seg_cutoff)
        else:
            known_late = pd.Series(False, index=seg.index)
        crossing = pd.Series(False, index=seg.index)
        if next_start is not None:
            crossing = ends.notna() & (ends >= next_start)
        excluded_any = unknown_avail | time_missing | immature | known_late | crossing
        clean = seg[~excluded_any]
        cross = int(crossing.sum())
        n_unknown = int(unknown_avail.sum())
        n_immature = int(immature.sum())
        n_known_late = int(known_late.sum())

        if cross:
            overlap_findings.append({
                "code": "label_crosses_segment_boundary",
                "segment": name,
                "next_segment": next_name,
                "boundary": str(next_start.date()) if next_start is not None else None,
                "n_pairs": cross,
                "detail": (
                    "标签窗越过下一段起点（边界接触也算）：这些样本的结局部分 "
                    f"发生在{next_name}期间，已从{name}段干净样本中剔除"
                ),
                "example_observation_dates": [
                    str(pd.Timestamp(d).date())
                    for d in seg[crossing]["observation_date"].head(5)
                ],
            })
        if n_unknown:
            overlap_findings.append({
                "code": "label_available_unknown",
                "segment": name,
                "n_pairs": n_unknown,
                "detail": "label_available_at 缺失（None/NaT）：无法证明何时可知，已剔除",
            })
        if n_immature:
            overlap_findings.append({
                "code": "label_not_mature_by_segment_cutoff",
                "segment": name,
                "cutoff": str(seg_cutoff),
                "n_pairs": n_immature,
                "detail": "标签窗在该段评价截止之后才结束：评价时未成熟，已剔除",
            })
        if n_known_late:
            overlap_findings.append({
                "code": "label_known_after_segment_cutoff",
                "segment": name,
                "cutoff": str(seg_cutoff),
                "n_pairs": n_known_late,
                "detail": "label_available_at 晚于该段截止：结论在评价时不存在，已剔除",
            })
        dates = sorted(set(seg["observation_date"]))
        entities = sorted(set(seg["entity_id"].astype(str)))
        counts = {
            "n_pairs": raw_n,
            "n_usable_clean": int(len(clean)),
            "n_label_crossing_into_next_segment": cross,
            "n_label_available_unknown": n_unknown,
            "n_label_not_mature_by_segment_cutoff": n_immature,
            "n_label_known_after_segment_cutoff": n_known_late,
            "segment_cutoff": str(seg_cutoff),
            "distinct_observation_dates": len(dates),
            "distinct_entities": len(entities),
            "seen_marker": seen[name],
            "first_date": str(pd.Timestamp(dates[0]).date()) if dates else None,
            "last_date": str(pd.Timestamp(dates[-1]).date()) if dates else None,
        }
        if len(seg) and dates:
            per_date = seg.groupby("observation_date").size()
            worst_share = float(per_date.max() / len(seg))
            counts["max_single_date_share"] = round(worst_share, 4)
            if worst_share > 0.5:
                overlap_findings.append({
                    "code": "concentrated_on_few_dates",
                    "segment": name,
                    "max_single_date_share": round(worst_share, 4),
                    "detail": "大量样本集中在少数观察日：不是独立证据",
                })
        # clean 掩码同时决定段内统计，不只改变报告计数。
        ic = _segment_ic(clean)
        counts["segment_ic"] = ic
        if ic is not None:
            direction_notes.append((name, ic["ic_pooled_over_segment"]))
        sample_counts[name] = counts

    signed = [(n, i) for n, i in direction_notes if i is not None]
    if len(signed) >= 2:
        signs = {n: (i > 0) - (i < 0) for n, i in signed}
        if len(set(signs.values())) > 1:
            split_findings.append({
                "code": "direction_changes_across_segments",
                "signs": signs,
                "detail": "分段方向不一致：整体均值可能依赖少数时期",
            })

    trial_history_status = "unknown"
    trial_findings: list[dict] = []
    kept_trials: list[dict] = []
    if trials is None or (isinstance(trials, list) and len(trials) == 0):
        trial_history_status = "unknown"
        trial_findings.append({
            "code": "trial_history_unknown",
            "detail": "没有试验史不当作只试过1次；反复挑优的风险无法评估",
        })
    else:
        if not isinstance(trials, list):
            raise IdentityFormatError("trials must be a list of dicts or null")
        trial_history_status = "provided"
        seen_ids: set[str] = set()
        holdout_used = False
        for index, trial in enumerate(trials):
            record = _trial_record(trial, index)
            kept_trials.append(record)
            if record["trial_id"] in seen_ids:
                trial_findings.append({
                    "code": "duplicate_trial_id",
                    "trial_id": str(record["trial_id"]),
                })
            seen_ids.add(str(record["trial_id"]))
            if "holdout" in record["seen_segments"]:
                holdout_used = True
        if holdout_used:
            trial_findings.append({
                "code": "holdout_already_used",
                "detail": "保留段已用于观察/选择：不能再当作未见数据；"
                          "重命名或换工具不能恢复为未知",
            })
        n_success = sum(1 for t in kept_trials if t["outcome"] == "success")
        trial_findings.append({
            "code": "all_trials_kept",
            "n_trials": len(kept_trials),
            "n_success": n_success,
            "n_failed_or_abandoned": len(kept_trials) - n_success,
            "detail": "保存所有版本，不只存赢家；多次尝试会放大挑到偶然赢家的风险",
        })

    return {
        "split_findings": split_findings,
        "overlap_findings": overlap_findings,
        "trial_history_status": trial_history_status,
        "trial_findings": trial_findings,
        "trials_kept": kept_trials,
        "sample_counts": sample_counts,
        "preprocessing": "none",
        "seen_markers": {name: bool(seen[name]) for name in SEGMENTS},
        "limitations": LIMITATIONS,
        "overfit_risk_status": RISK_NOT_EXCLUDED,
        "note": "本审计生成合法配对与分段诊断，不训练模型，不自动给出通过结论",
    }
