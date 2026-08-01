"""组合解释器：阶段、五个维度、支持/冲突与风险排序。

不输出不可解释的总分。每天输出机会阶段 + 维度 + 支持/冲突 + 风险排序，
每条提示都能追溯到规则 ID、版本、输入值和数据日期。

风险优先级只决定**提示排序**，不自动执行卖出。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.rules_config import get_rule, risk_priority, ruleset_version
from lei_signal.domain.types import (
    STAGE_CN,
    STAGE_RANK,
    DailyAssessment,
    Factor,
    LongTrendState,
    Provenance,
    RiskAlert,
    SignalColor,
    SignalEvent,
    Stage,
    StructureInstance,
)
from lei_signal.features.volume_profile import VolumeProfileProxy
from lei_signal.rules.resistance_b1 import B1Resistance
from lei_signal.state.machine import DayState

_SUPPORTIVE_LONG = {
    LongTrendState.LONG_IMPROVING,
    LongTrendState.LONG_BULL,
    LongTrendState.LONG_STABLE_BULL,
}

_RISK_LABELS = {
    "c_touched_or_broken": "触及C/跌破C",
    "top_plus_black": "Top+Black",
    "black": "黑色关键性波动",
    "active_top_structure": "有效顶部结构",
    "turned_gray": "颜色转灰",
    "volume_conflict": "量价冲突",
}


def build_assessment(
    *,
    symbol: str,
    frame: pd.DataFrame,
    day_state: DayState,
    previous_state: DayState | None,
    events: list[SignalEvent],
    structures: list[StructureInstance],
    b1: B1Resistance | None,
    profile: VolumeProfileProxy | None = None,
    data_status: str = "OK",
) -> DailyAssessment:
    """构造某一天的完整解释快照。"""
    day = day_state.day
    timestamp = pd.Timestamp(day)
    row = frame.loc[timestamp]

    new_events = [e for e in events if e.available_date == day]
    active_events = _active_events(events, structures, day)
    invalidated_events = _invalidated_events(events, structures, day)

    supports, conflicts = _build_factors(row, day_state, profile, b1)
    risks = _build_risks(row, day_state, structures, day)

    dimensions = _build_dimensions(day_state, row, b1, profile)

    assessment = DailyAssessment(
        symbol=symbol,
        as_of=day,
        stage=day_state.stage,
        color=day_state.color,
        new_events=new_events,
        active_events=active_events,
        invalidated_events=invalidated_events,
        supports=supports,
        conflicts=conflicts,
        risks=risks,
        primary_structure=day_state.primary_bottom,
        all_live_structures=list(day_state.live_bottoms),
        active_top=day_state.active_top,
        b1_price=b1.price if b1 else None,
        b1_pivot_date=b1.pivot_date if b1 else None,
        b1_available_date=b1.available_date if b1 else None,
        distance_to_b1_pct=b1.distance_pct if b1 else None,
        distance_to_b1_r=b1.distance_r if b1 else None,
        dimensions=dimensions,
        previous_stage=previous_state.stage if previous_state else None,
        data_status=data_status,
        rule_ruleset_version=ruleset_version(),
        last_data_date=frame.index[-1].date(),
    )
    assessment.stage_change_reason_cn = _stage_change_reason(assessment, day_state, previous_state)
    return assessment


def _active_events(
    events: list[SignalEvent],
    structures: list[StructureInstance],
    day: date,
) -> list[SignalEvent]:
    """仍然有效的历史事件。

    「有效」= 已可用、且其关联结构未失效。无结构关联的事件按 60 日观察窗保留，
    使界面不会无限堆积陈旧提示；窗口是展示口径，不改变事件本身。
    """
    dead_ids = {
        s.structure_id
        for s in structures
        if s.invalidated_date is not None and s.invalidated_date <= day
    }
    result: list[SignalEvent] = []
    for event in events:
        if event.available_date > day or event.available_date == day:
            continue
        if event.structure_id is not None:
            if event.structure_id not in dead_ids:
                result.append(event)
            continue
        if (day - event.available_date).days <= 60:
            result.append(event)
    return result


def _invalidated_events(
    events: list[SignalEvent],
    structures: list[StructureInstance],
    day: date,
) -> list[SignalEvent]:
    """已经失效的事件（其关联结构已失效）。"""
    dead_ids = {
        s.structure_id
        for s in structures
        if s.invalidated_date is not None and s.invalidated_date <= day
    }
    return [
        event
        for event in events
        if event.structure_id in dead_ids and event.available_date <= day
    ]


def _build_factors(
    row: pd.Series,
    day_state: DayState,
    profile: VolumeProfileProxy | None,
    b1: B1Resistance | None,
) -> tuple[list[Factor], list[Factor]]:
    """支持与冲突因素并排列出，不隐藏不利信息。"""
    supports: list[Factor] = []
    conflicts: list[Factor] = []

    color_spec = get_rule("lei_color")
    # 结构维度
    if day_state.live_bottoms:
        supports.append(
            Factor(
                dimension="结构",
                label_cn=f"存在{len(day_state.live_bottoms)}个有效底部结构",
                detail_cn="；".join(
                    f"{s.structure_type} C={s.c_price:.4f}"
                    for s in day_state.live_bottoms[:3]
                ),
                rule_id="bottom_c_lifecycle",
                rule_version=get_rule("bottom_c_lifecycle").version,
                provenance=get_rule("bottom_c_lifecycle").provenance,
                values={"count": len(day_state.live_bottoms)},
            )
        )
    else:
        conflicts.append(
            Factor(
                dimension="结构",
                label_cn="当前没有有效底部结构",
                detail_cn="没有可用的底部线索，或已全部因触及C失效",
                rule_id="bottom_c_lifecycle",
                rule_version=get_rule("bottom_c_lifecycle").version,
                provenance=get_rule("bottom_c_lifecycle").provenance,
            )
        )

    # 短周期维度
    if day_state.color is SignalColor.GREEN:
        supports.append(
            Factor(
                dimension="短周期",
                label_cn="当前为绿色",
                detail_cn=str(row.get("signal_reason", "")),
                rule_id=color_spec.rule_id,
                rule_version=color_spec.version,
                provenance=color_spec.provenance,
                values={
                    "close": float(row["close"]),
                    "ema20": float(row["ema20"]),
                    "close_lag20": float(row["close_lag20"]),
                },
            )
        )
    elif day_state.color is SignalColor.BLACK:
        conflicts.append(
            Factor(
                dimension="短周期",
                label_cn="当前为黑色（关键性波动）",
                detail_cn=str(row.get("signal_reason", "")),
                rule_id="key_wave_black",
                rule_version=get_rule("key_wave_black").version,
                provenance=get_rule("key_wave_black").provenance,
                values={
                    "close": float(row["close"]),
                    "ema20": float(row["ema20"]),
                    "close_lag20": float(row["close_lag20"]),
                },
            )
        )
    elif day_state.color is SignalColor.GRAY:
        conflicts.append(
            Factor(
                dimension="短周期",
                label_cn="当前为灰色（方向分歧，需要关注）",
                detail_cn=str(row.get("signal_reason", "")),
                rule_id=color_spec.rule_id,
                rule_version=color_spec.version,
                provenance=color_spec.provenance,
            )
        )

    if day_state.early_strength_active:
        spec = get_rule("ema20_reclaim_rising")
        supports.append(
            Factor(
                dimension="短周期",
                label_cn="早期转强仍有效",
                detail_cn=(
                    f"最近一次EMA20重新站上于{day_state.early_strength_date}，尚未被转黑否定"
                ),
                rule_id=spec.rule_id,
                rule_version=spec.version,
                provenance=spec.provenance,
                values={"reclaim_date": str(day_state.early_strength_date)},
            )
        )
    if day_state.joint_confirmed_now:
        spec = get_rule("dual_ma_bull_confirmed")
        supports.append(
            Factor(
                dimension="短周期",
                label_cn="双均线当前共同向上",
                detail_cn="收盘同时高于EMA20与MA20，两线均向上（读取当前状态，不要求当天穿越）",
                rule_id=spec.rule_id,
                rule_version=spec.version,
                provenance=spec.provenance,
                values={
                    "ema20": float(row["ema20"]),
                    "sma20": float(row["sma20"]),
                },
            )
        )

    # 长周期维度
    long_spec = get_rule("long_trend")
    long_values = {
        "daily_long": day_state.daily_long.value,
        "weekly_long": day_state.weekly_long.value,
        "ema60": float(row["ema60"]) if pd.notna(row.get("ema60")) else None,
        "ema120": float(row["ema120"]) if pd.notna(row.get("ema120")) else None,
    }
    if day_state.long_supportive:
        supports.append(
            Factor(
                dimension="长周期",
                label_cn="长周期背景支持或改善中",
                detail_cn=f"日线={day_state.daily_long.value}，周线={day_state.weekly_long.value}",
                rule_id=long_spec.rule_id,
                rule_version=long_spec.version,
                provenance=long_spec.provenance,
                values=long_values,
            )
        )
    else:
        conflicts.append(
            Factor(
                dimension="长周期",
                label_cn="长周期背景仍冲突",
                detail_cn=(
                    f"日线={day_state.daily_long.value}，周线={day_state.weekly_long.value}；"
                    "这只是冲突标签，不会阻止底部与短期信号被记录"
                ),
                rule_id=long_spec.rule_id,
                rule_version=long_spec.version,
                provenance=long_spec.provenance,
                values=long_values,
            )
        )

    # 量价维度
    volume_spec = get_rule("volume_proxies")
    ratio = row.get("volume_ratio20")
    if pd.notna(ratio):
        if bool(row.get("bearish_expansion", False)):
            conflicts.append(
                Factor(
                    dimension="量价",
                    label_cn="下跌放量（研究代理）",
                    detail_cn=f"量比={float(ratio):.2f}，达到阈值1.5",
                    rule_id=volume_spec.rule_id,
                    rule_version=volume_spec.version,
                    provenance=volume_spec.provenance,
                    values={"volume_ratio20": float(ratio)},
                )
            )
        elif bool(row.get("breakout_volume_ready", False)):
            supports.append(
                Factor(
                    dimension="量价",
                    label_cn="放量上行（研究代理）",
                    detail_cn=f"量比={float(ratio):.2f}，达到阈值1.5",
                    rule_id=volume_spec.rule_id,
                    rule_version=volume_spec.version,
                    provenance=volume_spec.provenance,
                    values={"volume_ratio20": float(ratio)},
                )
            )

    if profile is not None:
        profile_spec = get_rule("volume_profile_proxy")
        if "heavy_overhead_supply" in profile.tags:
            conflicts.append(
                Factor(
                    dimension="量价",
                    label_cn="上方套牢代理较重（筹码分布代理）",
                    detail_cn=(
                        f"当前价上方代理量占比 {profile.overhead_supply_ratio:.1%}，"
                        f"POC={profile.poc:.4f}"
                    ),
                    rule_id=profile_spec.rule_id,
                    rule_version=profile_spec.version,
                    provenance=profile_spec.provenance,
                    values={"overhead_supply_ratio": profile.overhead_supply_ratio},
                )
            )
        if "near_volume_support" in profile.tags:
            supports.append(
                Factor(
                    dimension="量价",
                    label_cn="接近代理支撑密集区（筹码分布代理）",
                    detail_cn=f"下方5%区间代理量占比 {profile.support_density:.1%}",
                    rule_id=profile_spec.rule_id,
                    rule_version=profile_spec.version,
                    provenance=profile_spec.provenance,
                    values={"support_density": profile.support_density},
                )
            )

    # 上方空间
    b1_spec = get_rule("resistance_b1")
    if b1 is not None:
        conflicts.append(
            Factor(
                dimension="上方空间",
                label_cn=f"存在B1阻力 {b1.price:.4f}",
                detail_cn=(
                    f"距离 {b1.distance_pct:.2f}%，"
                    f"拐点 {b1.pivot_date} 确认于 {b1.available_date}。"
                    "B1 是第一阻力，不是止盈目标，也不是入场门槛"
                ),
                rule_id=b1_spec.rule_id,
                rule_version=b1_spec.version,
                provenance=b1_spec.provenance,
                values={"b1_price": b1.price, "distance_pct": b1.distance_pct},
            )
        )
    return supports, conflicts


def _build_risks(
    row: pd.Series,
    day_state: DayState,
    structures: list[StructureInstance],
    day: date,
) -> list[RiskAlert]:
    """按配置的优先级排序风险提示。排序不代表自动执行卖出。"""
    order = risk_priority()
    found: list[RiskAlert] = []

    def priority_of(code: str) -> int:
        return order.index(code) if code in order else len(order)

    # 只有底部结构才有 C。顶部结构同样会在被新高解除时设置 invalidated_date，
    # 但那属于「顶部解除」而不是「触及C」，不得混入本风险项。
    touched_today = [
        s
        for s in structures
        if s.invalidated_date == day and s.side == "bottom" and s.c_price is not None
    ]
    if touched_today:
        found.append(
            RiskAlert(
                priority=priority_of("c_touched_or_broken"),
                code="c_touched_or_broken",
                label_cn=_RISK_LABELS["c_touched_or_broken"],
                detail_cn=(
                    f"{len(touched_today)}个底部结构因触及C而永久失效："
                    + "；".join(f"C={s.c_price:.4f}" for s in touched_today[:3])
                ),
                rule_id="bottom_c_lifecycle",
                rule_version=get_rule("bottom_c_lifecycle").version,
            )
        )

    is_black = day_state.color is SignalColor.BLACK
    if is_black and day_state.active_top is not None:
        found.append(
            RiskAlert(
                priority=priority_of("top_plus_black"),
                code="top_plus_black",
                label_cn=_RISK_LABELS["top_plus_black"],
                detail_cn=(
                    f"顶部警报仍有效（颈线{day_state.active_top.neckline:.4f}）"
                    "且当前为黑色关键性波动"
                ),
                rule_id="key_wave_black",
                rule_version=get_rule("key_wave_black").version,
            )
        )
    elif is_black:
        found.append(
            RiskAlert(
                priority=priority_of("black"),
                code="black",
                label_cn=_RISK_LABELS["black"],
                detail_cn=(
                    f"收盘{float(row['close']):.4f}同时低于EMA20"
                    f"{float(row['ema20']):.4f}与20日前收盘{float(row['close_lag20']):.4f}"
                ),
                rule_id="key_wave_black",
                rule_version=get_rule("key_wave_black").version,
            )
        )

    if day_state.active_top is not None and not is_black:
        found.append(
            RiskAlert(
                priority=priority_of("active_top_structure"),
                code="active_top_structure",
                label_cn=_RISK_LABELS["active_top_structure"],
                detail_cn=(
                    f"顶部警报仍未被新高解除，第一高点"
                    f"{day_state.active_top.reference_high:.4f}"
                ),
                rule_id="top_structure",
                rule_version=get_rule("top_structure").version,
            )
        )

    if day_state.color is SignalColor.GRAY:
        found.append(
            RiskAlert(
                priority=priority_of("turned_gray"),
                code="turned_gray",
                label_cn=_RISK_LABELS["turned_gray"],
                detail_cn="均线方向出现分歧，需要关注；灰色不等于卖出",
                rule_id="lei_color",
                rule_version=get_rule("lei_color").version,
            )
        )

    if bool(row.get("bearish_expansion", False)):
        found.append(
            RiskAlert(
                priority=priority_of("volume_conflict"),
                code="volume_conflict",
                label_cn=_RISK_LABELS["volume_conflict"],
                detail_cn="下跌放量（研究代理指标）",
                rule_id="volume_proxies",
                rule_version=get_rule("volume_proxies").version,
            )
        )

    return sorted(found, key=lambda alert: alert.priority)


def _build_dimensions(
    day_state: DayState,
    row: pd.Series,
    b1: B1Resistance | None,
    profile: VolumeProfileProxy | None,
) -> dict[str, str]:
    """五个维度的三态标签。"""
    structure = "支持" if day_state.live_bottoms else "冲突"
    if day_state.live_bottoms and day_state.primary_bottom is None:
        structure = "中性"

    if day_state.color is SignalColor.GREEN and (
        day_state.early_strength_active or day_state.joint_confirmed_now
    ):
        short_cycle = "支持"
    elif day_state.color in (SignalColor.BLACK, SignalColor.GRAY):
        # 黑色是关键性波动，灰色是方向分歧；两者都记为短周期冲突。
        short_cycle = "冲突"
    else:
        short_cycle = "中性"

    if day_state.daily_long in (LongTrendState.LONG_BULL, LongTrendState.LONG_STABLE_BULL):
        long_cycle = "支持"
    elif (
        day_state.daily_long is LongTrendState.LONG_IMPROVING
        or day_state.weekly_long in _SUPPORTIVE_LONG
    ):
        long_cycle = "改善中"
    else:
        long_cycle = "冲突"

    if bool(row.get("bearish_expansion", False)):
        volume_dimension = "冲突"
    elif bool(row.get("breakout_volume_ready", False)):
        volume_dimension = "支持"
    elif profile is not None and "heavy_overhead_supply" in profile.tags:
        volume_dimension = "冲突"
    else:
        volume_dimension = "中性"

    if b1 is None:
        space = "无B1数据"
    elif b1.distance_pct >= 10.0:
        space = "通畅"
    else:
        space = "存在B1阻力"

    return {
        "结构": structure,
        "短周期": short_cycle,
        "长周期": long_cycle,
        "量价": volume_dimension,
        "上方空间": space,
    }


def _stage_change_reason(
    assessment: DailyAssessment,
    day_state: DayState,
    previous_state: DayState | None,
) -> str:
    """较昨日升级或降级的原因。"""
    if previous_state is None:
        return f"首个评估日，当前阶段：{STAGE_CN[day_state.stage.value]}"

    current, previous = day_state.stage, previous_state.stage
    if current == previous:
        return f"阶段与昨日相同（{STAGE_CN[current.value]}）"

    current_rank = STAGE_RANK.get(current.value)
    previous_rank = STAGE_RANK.get(previous.value)
    reasons = "；".join(day_state.reasons) or "条件变化"

    if current_rank is not None and previous_rank is not None:
        direction = "升级" if current_rank > previous_rank else "降级"
    elif current in (Stage.RISK_WATCH, Stage.KEY_RISK, Stage.INVALIDATED):
        direction = "转入风险提示"
    else:
        direction = "变化"

    return (
        f"{direction}：{STAGE_CN[previous.value]} → {STAGE_CN[current.value]}。原因：{reasons}"
    )


def assessment_to_rows(assessment: DailyAssessment) -> list[dict[str, object]]:
    """把解释快照展开为可导出的行，用于 CSV 与界面追溯。"""
    rows: list[dict[str, object]] = []
    for factor in assessment.supports:
        rows.append(
            {
                "as_of": assessment.as_of,
                "kind": "support",
                "dimension": factor.dimension,
                "label_cn": factor.label_cn,
                "detail_cn": factor.detail_cn,
                "rule_id": factor.rule_id,
                "rule_version": factor.rule_version,
                "provenance": factor.provenance.value,
                "is_research_proxy": factor.provenance is Provenance.RESEARCH_PROXY,
                "values": factor.values,
            }
        )
    for factor in assessment.conflicts:
        rows.append(
            {
                "as_of": assessment.as_of,
                "kind": "conflict",
                "dimension": factor.dimension,
                "label_cn": factor.label_cn,
                "detail_cn": factor.detail_cn,
                "rule_id": factor.rule_id,
                "rule_version": factor.rule_version,
                "provenance": factor.provenance.value,
                "is_research_proxy": factor.provenance is Provenance.RESEARCH_PROXY,
                "values": factor.values,
            }
        )
    for alert in assessment.risks:
        rows.append(
            {
                "as_of": assessment.as_of,
                "kind": "risk",
                "dimension": "风险",
                "label_cn": alert.label_cn,
                "detail_cn": alert.detail_cn,
                "rule_id": alert.rule_id,
                "rule_version": alert.rule_version,
                "provenance": "",
                "is_research_proxy": False,
                "values": {"priority": alert.priority},
            }
        )
    return rows


__all__ = ["assessment_to_rows", "build_assessment"]
