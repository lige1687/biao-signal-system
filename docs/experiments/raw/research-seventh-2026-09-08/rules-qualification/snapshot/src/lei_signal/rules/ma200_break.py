"""跌破 200 日均线分步检查清单（文主任增量 #4，道路层分级预警）。

A 股自测依据：docs/experiments/ma200-breakdown-checklist-astock-2026-09-05.md
（时间分档成立；急速/缓慢形态分组在 A 股反向、不实现）。

严格前向状态机：收盘跌破 SMA200 的上升沿开启一个回合；回合内按交易日计数，
第 3/5/10/20 天仍未收回时分档产出预警事件；任一收盘收回即静默结束回合。
每档事件每回合至多一次；只用当日及此前数据，无前视。

红线：分级预警、只预警不必然反向；「跌破」绝不等于翻空信号；
不改动 lei_color/趋势状态机的任何判定。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

RULE_ID = "ma200_break_checklist"

SUB_BREAK_STARTED = "ma200_break_started"
SUB_D3_WATCH = "ma200_break_d3_watch"
SUB_D5_CHECK = "ma200_break_d5_check"
SUB_D10_WARN = "ma200_break_d10_warn"
SUB_D20_RISK = "ma200_break_d20_risk"


def _spec_params(spec: RuleSpec) -> dict:
    return {
        "ma_period": int(spec.param("ma_period", 200)),
        "cross_ma_short": int(spec.param("cross_ma_short", 50)),
        "d3_watch_days": int(spec.param("d3_watch_days", 3)),
        "d5_check_days": int(spec.param("d5_check_days", 5)),
        "d5_drop_pct": float(spec.param("d5_drop_pct", -3.0)),
        "d5_below_ma_pct": float(spec.param("d5_below_ma_pct", -2.0)),
        "slope_lookback": int(spec.param("slope_lookback", 5)),
        "d10_warn_days": int(spec.param("d10_warn_days", 10)),
        "d20_risk_days": int(spec.param("d20_risk_days", 20)),
    }


def _emit(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    sub_rule: str,
    severity: Severity,
    strength: int,
    reason: str,
    evidence: dict,
) -> SignalEvent:
    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"{sub_rule}:{symbol}:{day.isoformat()}",
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=Direction.BEARISH,
        severity=severity,
        strength=strength,
        reason_cn=reason,
        provenance=spec.provenance,
        evidence={"sub_rule": sub_rule, "research_proxy": True, **evidence},
        invalidation={
            "condition": (
                "分级预警事件为单次触发，不因后续价格回升回溯改写；"
                "收盘收回 200 日线即静默结束本回合（只预警，不构成卖出信号）"
            )
        },
    )


def _d5_checks(
    close_break: float,
    close_now: float,
    sma200_now: float,
    sma200_slope_ref: float,
    sma50_now: float,
    params: dict,
) -> dict[str, bool]:
    """d5 三项检查（阈值全部来自规则账本）。"""
    cum_drop = (close_now / close_break - 1.0) * 100.0 if close_break else 0.0
    below_ma = (close_now / sma200_now - 1.0) * 100.0 if sma200_now else 0.0
    slope_down = sma200_slope_ref > 0 and sma200_now < sma200_slope_ref
    return {
        "drop_since_break": cum_drop <= params["d5_drop_pct"],
        "below_ma_and_slope_down": (
            below_ma <= params["d5_below_ma_pct"] and slope_down
        ),
        "ma50_below_ma200": sma50_now < sma200_now,
    }


def detect_ma200_break_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别 200 日线跌破分档预警事件（每回合各档至多一次）。"""
    spec = get_rule(RULE_ID)
    params = _spec_params(spec)
    ma_period = params["ma_period"]
    if frame.empty or "close" not in frame.columns or len(frame) < ma_period + 2:
        return []

    close = frame["close"].astype(float)
    sma200 = close.rolling(ma_period, min_periods=ma_period).mean()
    sma50 = close.rolling(params["cross_ma_short"],
                          min_periods=params["cross_ma_short"]).mean()
    values = close.to_numpy()
    ma200_values = sma200.to_numpy()
    ma50_values = sma50.to_numpy()

    events: list[SignalEvent] = []
    in_episode = False
    days_below = 0          # 跌破日=第 0 天
    break_close = 0.0
    break_day: date | None = None
    emitted: set[str] = set()

    for i, timestamp in enumerate(frame.index):
        if pd.isna(ma200_values[i]) or pd.isna(values[i]):
            continue
        below = values[i] < ma200_values[i]
        prev_above = (
            i > 0
            and not pd.isna(ma200_values[i - 1])
            and not pd.isna(values[i - 1])
            and values[i - 1] >= ma200_values[i - 1]
        )
        day = timestamp.date()

        if not in_episode:
            if below and prev_above:
                in_episode = True
                days_below = 0
                break_close = float(values[i])
                break_day = day
                emitted = set()
                events.append(
                    _emit(
                        spec=spec, symbol=symbol, day=day,
                        sub_rule=SUB_BREAK_STARTED, severity=Severity.WATCH,
                        strength=45,
                        reason=(
                            f"收盘跌破 {ma_period} 日均线（{break_close:.2f} < "
                            f"{ma200_values[i]:.2f}）。A 股自测：历史上此类跌破六成在 "
                            "5 天内收回、八成在 20 天内收回——先观望 3 天，不是卖出信号"
                        ),
                        evidence={
                            "close": break_close,
                            "sma200": float(ma200_values[i]),
                            "days_below": days_below,
                        },
                    )
                )
            continue

        # 回合中：收回即静默结束
        if not below:
            in_episode = False
            continue

        days_below += 1
        common = {
            "close": float(values[i]),
            "sma200": float(ma200_values[i]),
            "days_below": days_below,
            "break_date": break_day.isoformat() if break_day else "",
        }

        if days_below == params["d3_watch_days"] and SUB_D3_WATCH not in emitted:
            emitted.add(SUB_D3_WATCH)
            events.append(
                _emit(
                    spec=spec, symbol=symbol, day=day,
                    sub_rule=SUB_D3_WATCH, severity=Severity.WATCH,
                    strength=50,
                    reason=(
                        f"跌破 {ma_period} 日线已 {days_below} 天未收回——继续观望，"
                        "第 5 天起检查清单"
                    ),
                    evidence=common,
                )
            )

        if days_below == params["d5_check_days"] and SUB_D5_CHECK not in emitted:
            slope_ref = (
                ma200_values[i - params["slope_lookback"]]
                if i >= params["slope_lookback"]
                and not pd.isna(ma200_values[i - params["slope_lookback"]])
                else float("nan")
            )
            checks = _d5_checks(
                close_break=break_close,
                close_now=float(values[i]),
                sma200_now=float(ma200_values[i]),
                sma200_slope_ref=float(slope_ref),
                sma50_now=float(ma50_values[i]) if not pd.isna(ma50_values[i]) else float("inf"),
                params=params,
            )
            if any(checks.values()):
                emitted.add(SUB_D5_CHECK)
                hit = "、".join(
                    {"drop_since_break": "5日累计跌幅达标",
                     "below_ma_and_slope_down": "低于均线2%且均线走低",
                     "ma50_below_ma200": "50/200死叉"}[k]
                    for k, v in checks.items() if v
                )
                events.append(
                    _emit(
                        spec=spec, symbol=symbol, day=day,
                        sub_rule=SUB_D5_CHECK, severity=Severity.IMPORTANT,
                        strength=65,
                        reason=(
                            f"跌破 {ma_period} 日线第 {days_below} 天：检查项命中（{hit}）"
                            "——历史上命中后深跌风险升高，仅预警"
                        ),
                        evidence={**common, "checks": checks},
                    )
                )

        if days_below == params["d10_warn_days"] and SUB_D10_WARN not in emitted:
            emitted.add(SUB_D10_WARN)
            events.append(
                _emit(
                    spec=spec, symbol=symbol, day=day,
                    sub_rule=SUB_D10_WARN, severity=Severity.IMPORTANT,
                    strength=70,
                    reason=(
                        f"跌破 {ma_period} 日线已 {days_below} 天未收回（历史上约两成"
                        "跌破会走到这一步）——趋势受损的明确预警，不是卖出信号"
                    ),
                    evidence=common,
                )
            )

        if days_below == params["d20_risk_days"] and SUB_D20_RISK not in emitted:
            emitted.add(SUB_D20_RISK)
            events.append(
                _emit(
                    spec=spec, symbol=symbol, day=day,
                    sub_rule=SUB_D20_RISK, severity=Severity.CRITICAL,
                    strength=80,
                    reason=(
                        f"跌破 {ma_period} 日线已 {days_below} 天未收回——进入系统性"
                        "风险观察档（历史上此状态后 20 日内再跌 10%+ 的比例升高），"
                        "仅预警；具体操作仍以趋势状态机为准"
                    ),
                    evidence=common,
                )
            )

    return events


__all__ = [
    "RULE_ID",
    "SUB_BREAK_STARTED",
    "SUB_D10_WARN",
    "SUB_D20_RISK",
    "SUB_D3_WATCH",
    "SUB_D5_CHECK",
    "detect_ma200_break_events",
]
