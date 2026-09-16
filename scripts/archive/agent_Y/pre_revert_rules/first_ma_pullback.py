"""模块 A：稳定上涨趋势回调（规格 §9 模块 A / 手册 4.4，V2 重写版）。

V2 语义（v1「双阈值触碰 + 3 根确认窗口」口径已于 ruleset 2.x 重写替代）：

- **A1 环境门禁**：时钟二类（``clock_classifier``，s60 年化对数斜率 10%–100%
  且非加速分支）+ 日线完整多头排列（SMA20>SMA60>SMA120 且
  EMA20>EMA60>EMA120，规格 §4.5）+ 周线多头环境（已完成周 20/60/120 双组
  多头排列，规格 §6 简化版）。中长期均线「近乎平行」按规格 A1 只作后验
  记录（evidence.parallelism），不作门禁。
- **趋势生命周期（episode）**：A1 门禁由false->true 开启；SMA 排列破坏、
  收盘跌破 SMA120、或 LEI 颜色转黑时重置（趋势受损）。时钟离开二类或周线
  环境转空**不**重置生命周期，只阻断新触碰与新入场。
- **A2 触碰口径**：``Low <= SMA_N + 1 x ATR(20)`` 即视为触及该均线组
  （〔标定 V2.1，待彪哥确认〕，敏感性 0.5/1/1.5 ATR；允许击穿，深度由
  A5 结构失效兜底）；触碰日要求 ``close > close_lag_N``（该 SMA 仍处上行
  压力方向，规格 §4.2 抵扣价判据）。触碰前必须先站上该均线（close > SMA_N，
  「回撤」以离开为前提）。同一生命周期内第一次触碰记 **is_first=true**
  （「第一次回撤要特别重视」，手册 4.4），其后触碰 is_first=false、分别
  出事件（规格 §9 A2【原系统原则】要求分别统计）。
- **A3 结构条件**（至少一种，触碰后至入场前成立）：严格底部构造确认
  （``strict_structure``，确认日落在本轮回撤内且未被失效）；或破线后重新
  站回 EMA20（存在 close 由 <=EMA20 上穿 >EMA20 的交易日）。
- **A4 入场触发**（两版分别出事件）：早期版 = close > EMA20 且 EMA20 上行
  （§4.3 判据）；确认版 = 早期版条件且 SMA20 上行（close > close_lag20，
  §4.2 抵扣价判据）。信号收盘生成，回测在下一根开盘入场（规格 §3.3）。
- **A5 初始失效**：入场依据为均线组支撑，失效价 C = 本轮回撤自触碰日起的
  最低 low（结构低点，evidence.stop_price）；入场前收盘跌破该低点（close
  低于此前本轮回撤全部 low）即 failed（结构低点被破坏）。
- **回撤区离开**：未触发任何入场而收盘回到 ``SMA_N + 触碰带`` 上方，本回
  撤周期结束（failed，价格离开回撤区），需重新站上均线才可再次触碰。

严格前向：逐交易日推进，任何结论只用当日及此前已完成日 K；追加未来行情
不改变历史事件。ATR(20) 沿用全局 ``atr_method: simple_average``（口径
待拍板项，见 audit 4.1）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.features.indicators import average_true_range
from lei_signal.features.weekly_context import weekly_env_series
from lei_signal.rules.clock_classifier import (
    TYPE2_STEADY_UP,
    clock_series,
)
from lei_signal.rules.strict_structure import (
    SIDE_BOTTOM,
    StrictStructure,
    detect_strict_structures,
)

RULE_ID = "first_ma_pullback"
SUB_RULE_TOUCHED = "first_ma_pullback_touched"
SUB_RULE_CONFIRMED = "first_ma_pullback_confirmed"
SUB_RULE_FAILED = "first_ma_pullback_failed"

ENTRY_EARLY = "early"
ENTRY_CONFIRMED = "confirmed"

A3_STRUCTURE = "bottom_structure"
A3_RECLAIM = "ema20_reclaim"


@dataclass(slots=True)
class _CycleState:
    """单条均线的回撤周期状态机。"""

    armed: bool = False                 # close > SMA_N（站上均线才能谈回撤）
    open_: bool = False                 # 触碰周期进行中
    is_first: bool = True               # 本生命周期内该均线首次触碰
    touch_position: int | None = None
    touch_date: date | None = None
    reclaim_seen: bool = False          # A3：破线后重新站回 EMA20
    structure_id: str | None = None     # A3：本轮回撤内确认的底部构造
    early_emitted: bool = False
    confirmed_emitted: bool = False
    cycle_min_low: float | None = None
    prior_low: float | None = None      # min(low[touch..t-1])，A5 判破坏用


@dataclass(slots=True)
class _Episode:
    lifecycle_id: str
    anchor_date: date
    cycles: dict[int, _CycleState] = field(default_factory=dict)


def _params(spec: RuleSpec) -> tuple[tuple[int, ...], float, int]:
    periods = tuple(int(v) for v in spec.param("ma_periods", [20, 60, 120]))
    return (
        periods,
        float(spec.param("ma_touch_distance_atr", 1.0)),
        int(spec.param("ma_touch_atr_period", 20)),
    )


def _required_columns() -> set[str]:
    columns = {"open", "high", "low", "close", "signal_color"}
    for prefix in ("sma", "ema", "close_lag"):
        for period in (20, 60, 120):
            columns.add(f"{prefix}{period}")
    return columns


def _active_bottom_structures(
    structures: list[StrictStructure], start: date, as_of: date
) -> StrictStructure | None:
    """[start, as_of] 内确认、且 as_of 日仍未失效的最新底部构造。"""
    best: StrictStructure | None = None
    for structure in structures:
        if structure.side != SIDE_BOTTOM:
            continue
        if not (start <= structure.confirmed_date <= as_of):
            continue
        if structure.invalidated_date is not None and structure.invalidated_date <= as_of:
            continue
        if best is None or structure.confirmed_date > best.confirmed_date:
            best = structure
    return best


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    source_id: str,
    sub_rule: str,
    ma_period: int,
    is_first: bool,
    evidence: dict,
    reason: str,
    severity: Severity,
    strength: int,
    direction: Direction,
    lifecycle_id: str,
    touch_date: date | None,
) -> SignalEvent:
    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=source_id,
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=direction,
        severity=severity,
        strength=strength,
        reason_cn=reason,
        provenance=spec.provenance,
        lifecycle_id=lifecycle_id,
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "ma_period": ma_period,
            "is_first_touch": is_first,
            "touch_date": touch_date.isoformat() if touch_date else None,
            **evidence,
        },
        invalidation={
            "condition": (
                f"入场依据为 SMA{ma_period} 均线组支撑：收盘跌破本轮回撤结构低点"
                "（stop_price）即介入逻辑失效（规格 §9 A5）；趋势生命周期重置"
                "（SMA 排列破坏 / 收盘跌破 SMA120 / LEI 转黑）同样终止本轮回撤"
            )
        },
    )


def detect_first_ma_pullback_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别模块 A（V2）：时钟二类 + 多头排列 + 周线环境中的均线回撤事件。"""
    spec = get_rule(RULE_ID)
    periods, distance_atr, atr_period = _params(spec)
    if frame.empty or not _required_columns().issubset(frame.columns):
        return []

    atr20 = average_true_range(frame, atr_period)
    clock = clock_series(frame)
    weekly_bull = weekly_env_series(frame)
    structures = detect_strict_structures(frame)

    events: list[SignalEvent] = []
    episode: _Episode | None = None
    dates = [timestamp.date() for timestamp in frame.index]

    for position, day in enumerate(dates):
        row = frame.iloc[position]
        close = float(row["close"])
        sma_stack = bool(
            float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        )
        ema_stack = bool(
            float(row["ema20"]) > float(row["ema60"]) > float(row["ema120"])
        )
        clock_ok = int(clock.iloc[position]) == TYPE2_STEADY_UP
        weekly_ok = bool(weekly_bull.iloc[position])
        gate = (
            clock_ok
            and sma_stack
            and ema_stack
            and weekly_ok
            and all(
                pd.notna(row[col])
                for col in ("close", "sma20", "sma60", "sma120", "ema20", "ema60", "ema120")
            )
        )

        # ---- 趋势生命周期管理 ----
        if episode is None:
            if not gate:
                continue
            episode = _Episode(
                lifecycle_id=f"{RULE_ID}:{symbol}:{day.isoformat()}",
                anchor_date=day,
                cycles={period: _CycleState() for period in periods},
            )
        else:
            damaged = (
                not sma_stack
                or close < float(row["sma120"])
                or str(row["signal_color"]) == "black"
                or any(pd.isna(row[col]) for col in ("sma20", "sma60", "sma120"))
            )
            if damaged:
                for period, cycle in episode.cycles.items():
                    if cycle.open_:
                        events.append(
                            _make_event(
                                spec=spec, symbol=symbol, day=day,
                                source_id=(
                                    f"{episode.lifecycle_id}:{period}:"
                                    f"failed:{cycle.touch_date}"
                                ),
                                sub_rule=SUB_RULE_FAILED,
                                ma_period=period,
                                is_first=cycle.is_first,
                                evidence={
                                    "failure_reason": "趋势生命周期重置（排列破坏/跌破SMA120/转黑）",  # noqa: E501
                                    "close": close,
                                },
                                reason=(
                                    f"SMA{period} 回撤失败：趋势生命周期重置，本轮回撤终止"
                                ),
                                severity=Severity.INFO,
                                strength=30,
                                direction=Direction.NEUTRAL,
                                lifecycle_id=episode.lifecycle_id,
                                touch_date=cycle.touch_date,
                            )
                        )
                        cycle.open_ = False
                episode = None
                continue

        assert episode is not None
        atr = float(atr20.iloc[position]) if pd.notna(atr20.iloc[position]) else None
        if atr is None or atr <= 0:
            continue
        prev_row = frame.iloc[position - 1] if position > 0 else None

        for period, cycle in episode.cycles.items():
            ma_value = float(row[f"sma{period}"])
            if pd.isna(ma_value):
                continue
            band = ma_value + distance_atr * atr
            close_lag = row[f"close_lag{period}"]
            close_lag_value = float(close_lag) if pd.notna(close_lag) else None

            if cycle.open_:
                # ---- A5 结构失效：收盘跌破本轮回撤此前全部 low ----
                if cycle.prior_low is not None and close < cycle.prior_low:
                    events.append(
                        _make_event(
                            spec=spec, symbol=symbol, day=day,
                            source_id=(
                                f"{episode.lifecycle_id}:{period}:failed:{cycle.touch_date}"
                            ),
                            sub_rule=SUB_RULE_FAILED,
                            ma_period=period,
                            is_first=cycle.is_first,
                            evidence={
                                "failure_reason": "收盘跌破回撤结构低点（A5 结构失效）",
                                "close": close,
                                "structure_low": cycle.cycle_min_low,
                            },
                            reason=(
                                f"SMA{period} 回撤失败：收盘跌破本轮回撤结构低点，"
                                "介入逻辑失效"
                            ),
                            severity=Severity.INFO,
                            strength=30,
                            direction=Direction.NEUTRAL,
                            lifecycle_id=episode.lifecycle_id,
                            touch_date=cycle.touch_date,
                        )
                    )
                    cycle.open_ = False
                    cycle.armed = False
                    cycle.is_first = False
                    continue

                # ---- A3 状态推进 ----
                if (
                    prev_row is not None
                    and not cycle.reclaim_seen
                    and float(prev_row["close"]) <= float(prev_row["ema20"])
                    and close > float(row["ema20"])
                ):
                    cycle.reclaim_seen = True
                if cycle.structure_id is None:
                    bottom = _active_bottom_structures(
                        structures, cycle.touch_date or day, day
                    )
                    if bottom is not None:
                        cycle.structure_id = bottom.structure_id

                # ---- A4 入场触发（两版分别出事件） ----
                ema20 = float(row["ema20"])
                ema20_rising = (
                    prev_row is not None and ema20 > float(prev_row["ema20"])
                )
                above_ema20 = close > ema20
                a3_ok = cycle.reclaim_seen or cycle.structure_id is not None
                lag20 = row["close_lag20"]
                lag20_value = float(lag20) if pd.notna(lag20) else None
                sma20_rising = lag20_value is not None and close > lag20_value
                triggerable = (
                    clock_ok
                    and weekly_ok
                    and above_ema20
                    and ema20_rising
                    and a3_ok
                )
                stop_price = (
                    min(cycle.cycle_min_low or float("inf"), float(row["low"]))
                )
                if triggerable and not cycle.early_emitted:
                    cycle.early_emitted = True
                    events.append(
                        _make_event(
                            spec=spec, symbol=symbol, day=day,
                            source_id=(
                                f"{episode.lifecycle_id}:{period}:confirmed:"
                                f"{ENTRY_EARLY}:{cycle.touch_date}"
                            ),
                            sub_rule=SUB_RULE_CONFIRMED,
                            ma_period=period,
                            is_first=cycle.is_first,
                            evidence={
                                "entry_variant": ENTRY_EARLY,
                                "close": close,
                                "a3_source": (
                                    A3_STRUCTURE if cycle.structure_id else A3_RECLAIM
                                ),
                                "a3_structure_id": cycle.structure_id,
                                "stop_price": stop_price,
                                "entry_ref_close": close,
                                "ma_value": ma_value,
                                "atr20": atr,
                                "clock_type": int(clock.iloc[position]),
                                "weekly_bull_env": weekly_ok,
                            },
                            reason=(
                                f"SMA{period} 回撤入场（A4 早期版）：close > EMA20 且 "
                                f"EMA20 上行，A3="
                                f"{'底部构造' if cycle.structure_id else 'EMA20收复'}"
                            ),
                            severity=Severity.IMPORTANT,
                            strength=75,
                            direction=Direction.BULLISH,
                            lifecycle_id=episode.lifecycle_id,
                            touch_date=cycle.touch_date,
                        )
                    )
                if (
                    triggerable
                    and sma20_rising
                    and not cycle.confirmed_emitted
                ):
                    cycle.confirmed_emitted = True
                    events.append(
                        _make_event(
                            spec=spec, symbol=symbol, day=day,
                            source_id=(
                                f"{episode.lifecycle_id}:{period}:confirmed:"
                                f"{ENTRY_CONFIRMED}:{cycle.touch_date}"
                            ),
                            sub_rule=SUB_RULE_CONFIRMED,
                            ma_period=period,
                            is_first=cycle.is_first,
                            evidence={
                                "entry_variant": ENTRY_CONFIRMED,
                                "close": close,
                                "a3_source": (
                                    A3_STRUCTURE if cycle.structure_id else A3_RECLAIM
                                ),
                                "a3_structure_id": cycle.structure_id,
                                "stop_price": stop_price,
                                "entry_ref_close": close,
                                "ma_value": ma_value,
                                "atr20": atr,
                                "clock_type": int(clock.iloc[position]),
                                "weekly_bull_env": weekly_ok,
                            },
                            reason=(
                                f"SMA{period} 回撤入场（A4 确认版）：EMA20 与 SMA20 "
                                "共同向上（SMA 用抵扣价判据）"
                            ),
                            severity=Severity.IMPORTANT,
                            strength=80,
                            direction=Direction.BULLISH,
                            lifecycle_id=episode.lifecycle_id,
                            touch_date=cycle.touch_date,
                        )
                    )

                # ---- 周期收尾 ----
                if cycle.early_emitted and cycle.confirmed_emitted:
                    cycle.open_ = False
                    cycle.armed = False
                    cycle.is_first = False
                elif not cycle.early_emitted and not cycle.confirmed_emitted and close > band:
                    events.append(
                        _make_event(
                            spec=spec, symbol=symbol, day=day,
                            source_id=(
                                f"{episode.lifecycle_id}:{period}:failed:{cycle.touch_date}"
                            ),
                            sub_rule=SUB_RULE_FAILED,
                            ma_period=period,
                            is_first=cycle.is_first,
                            evidence={
                                "failure_reason": "价格离开回撤区且未触发入场",
                                "close": close,
                                "band": band,
                            },
                            reason=(
                                f"SMA{period} 回撤失败：收盘回到触碰带上方，本轮回撤未触发入场"
                            ),
                            severity=Severity.INFO,
                            strength=35,
                            direction=Direction.NEUTRAL,
                            lifecycle_id=episode.lifecycle_id,
                            touch_date=cycle.touch_date,
                        )
                    )
                    cycle.open_ = False
                    cycle.armed = False
                    cycle.is_first = False

                # 更新回撤低点轨迹
                if cycle.open_:
                    cycle.cycle_min_low = min(
                        cycle.cycle_min_low or float("inf"), float(row["low"])
                    )
                    cycle.prior_low = cycle.cycle_min_low
                continue

            # ---- 未在回撤周期：武装与触碰检测 ----
            if close > ma_value:
                cycle.armed = True
            if (
                cycle.armed
                and clock_ok
                and float(row["low"]) <= band
                and close_lag_value is not None
                and close > close_lag_value
            ):
                cycle.open_ = True
                cycle.touch_position = position
                cycle.touch_date = day
                cycle.cycle_min_low = float(row["low"])
                cycle.prior_low = float(row["low"])
                cycle.reclaim_seen = False
                cycle.structure_id = None
                cycle.early_emitted = False
                cycle.confirmed_emitted = False
                # A3 起点：触碰当日即已收复 EMA20 的情形（从前一日收盘判断）
                if (
                    prev_row is not None
                    and float(prev_row["close"]) <= float(prev_row["ema20"])
                    and close > float(row["ema20"])
                ):
                    cycle.reclaim_seen = True
                bottom = _active_bottom_structures(structures, day, day)
                if bottom is not None:
                    cycle.structure_id = bottom.structure_id
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day,
                        source_id=(
                            f"{episode.lifecycle_id}:{period}:touched:{day.isoformat()}"
                        ),
                        sub_rule=SUB_RULE_TOUCHED,
                        ma_period=period,
                        is_first=cycle.is_first,
                        evidence={
                            "close": close,
                            "ma_value": ma_value,
                            "atr20": atr,
                            "band": band,
                            "close_above_costbasis": True,
                            "clock_type": int(clock.iloc[position]),
                            "weekly_bull_env": weekly_ok,
                            "parallelism_sma60_slope5": (
                                float(row["sma60"]) - float(frame.iloc[position - 5]["sma60"])
                            ) / float(row["sma60"])
                            if position >= 5 and pd.notna(frame.iloc[position - 5]["sma60"])
                            else None,
                            "parallelism_sma120_slope5": (
                                float(row["sma120"]) - float(frame.iloc[position - 5]["sma120"])
                            ) / float(row["sma120"])
                            if position >= 5 and pd.notna(frame.iloc[position - 5]["sma120"])
                            else None,
                        },
                        reason=(
                            f"{'首次' if cycle.is_first else '非首次'}回撤触碰 SMA{period}："
                            f"Low <= SMA{period} + {distance_atr} x ATR({atr_period})，"
                            "该 SMA 仍处上行方向"
                        ),
                        severity=Severity.WATCH,
                        strength=55,
                        direction=Direction.BULLISH,
                        lifecycle_id=episode.lifecycle_id,
                        touch_date=day,
                    )
                )

    return events


__all__ = [
    "A3_RECLAIM",
    "A3_STRUCTURE",
    "ENTRY_CONFIRMED",
    "ENTRY_EARLY",
    "RULE_ID",
    "SUB_RULE_CONFIRMED",
    "SUB_RULE_FAILED",
    "SUB_RULE_TOUCHED",
    "detect_first_ma_pullback_events",
]
