"""全自选卖点信号提取（纯函数，不做新判定）。

四档口径（docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md §2）：
  hard  structure_invalidated     底部结构失效（trading-spec §2.3 / §7）
  hard  exit_proxy                收盘同破 EMA20 + 20 日抵扣价（trading-spec A6①，research_proxy）
  warn  top_structure_confirmed   顶部构造确认（trading-spec §7.4，预警不必然反向）
  warn  key_wave_black            反向关键性波动（trading-spec §2.2，预警不必然反向）
  soft  color_black               三色转黑（Round 3 生命周期状态机）

只读 result.frame / result.events / result.structures / result.history 四个字段，
数值与文案全部来自既有确定性输出，取不到就留空，绝不推算。
顶部结构失效（=创新高解除预警）是偏多事实，不进卖点面板。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

EXIT_RULE_ID = "exit_ema20_costbasis"
KEY_WAVE_RULE_ID = "key_wave_black"

#: recency 窗口：最近 N 根 K 线内触发的卖点才进面板（与买点侧 3 交易日一致）
RECENCY_BARS = 3

TIER_HARD = "hard"
TIER_WARN = "warn"
TIER_SOFT = "soft"

_COLOR_CN = {"green": "绿", "gray": "灰", "black": "黑"}


def _color_name(color: Any) -> str:
    raw = getattr(color, "value", color)
    return _COLOR_CN.get(str(raw), str(raw))


@dataclass(frozen=True, slots=True)
class SellSignal:
    """一条卖点提醒（提取结果，不含任何新判定）。"""

    kind: str
    tier: str
    kind_cn: str
    title: str
    reason_cn: str
    is_new: bool
    key_prices: dict[str, float] = field(default_factory=dict)
    provenance: str = "system"
    available_date: str = ""


def _recent_dates(frame: Any, recency_bars: int) -> tuple[set[date], date]:
    """最近 N 根 K 线的日期集合与当前（最后一根）日期。"""
    dates = [ts.date() for ts in frame.index[-recency_bars:]]
    return set(dates), dates[-1]


def extract_sell_signals(result: Any, *, recency_bars: int = RECENCY_BARS) -> list[SellSignal]:
    """从既有分析结果提取四档卖点信号；无 frame 或无命中返回空列表。"""
    frame = getattr(result, "frame", None)
    if frame is None or len(frame.index) == 0:
        return []
    window, today = _recent_dates(frame, recency_bars)
    events = list(getattr(result, "events", []) or [])
    structures = list(getattr(result, "structures", []) or [])
    signals: list[SellSignal] = []

    # S1 结构失效：只收底部结构（顶部结构失效 = 创新高解除预警，偏多，不进卖点）
    dead_bottoms = [
        s for s in structures
        if getattr(s, "side", "") == "bottom"
        and str(getattr(s, "status", "")) == "invalidated"
        and getattr(s, "invalidated_date", None) in window
    ]
    if dead_bottoms:
        latest = max(s.invalidated_date for s in dead_bottoms)
        reason = "；".join(
            r for r in (getattr(s, "invalidated_reason", None) for s in dead_bottoms) if r
        )
        c_prices = [
            float(s.c_price) for s in dead_bottoms
            if getattr(s, "c_price", None) is not None
        ]
        signals.append(SellSignal(
            kind="structure_invalidated", tier=TIER_HARD, kind_cn="结构失效",
            title=f"{len(dead_bottoms)} 个底部结构失效",
            reason_cn=reason or "底部结构被破坏（进出同一逻辑：什么逻辑进场就什么逻辑退出）",
            is_new=latest == today,
            key_prices={"invalidation_c": c_prices[-1]} if c_prices else {},
            available_date=latest.isoformat(),
        ))

    # S2 退出代理（research_proxy）：收盘同破 EMA20 与 20 日抵扣价的上升沿事件
    exit_events = [
        e for e in events
        if getattr(e, "rule_id", "") == EXIT_RULE_ID
        and getattr(e, "available_date", None) in window
    ]
    if exit_events:
        ev = max(exit_events, key=lambda e: e.available_date)
        evd = dict(getattr(ev, "evidence", {}) or {})
        signals.append(SellSignal(
            kind="exit_proxy", tier=TIER_HARD, kind_cn="退出代理",
            title="收盘同破 EMA20 与 20 日抵扣价",
            reason_cn=f"{getattr(ev, 'reason_cn', '')}（研究代理）".strip(),
            is_new=ev.available_date == today,
            key_prices={
                k: float(evd[k]) for k in ("ema20", "close_lag20", "close") if k in evd
            },
            provenance="research_proxy",
            available_date=ev.available_date.isoformat(),
        ))

    # S3a 顶部构造确认（预警路牌）
    tops_confirmed = [
        s for s in structures
        if getattr(s, "side", "") == "top"
        and getattr(s, "confirmed_date", None) in window
    ]
    if tops_confirmed:
        latest = max(s.confirmed_date for s in tops_confirmed)
        necklines = [
            float(s.neckline) for s in tops_confirmed
            if getattr(s, "neckline", None) is not None
        ]
        signals.append(SellSignal(
            kind="top_structure_confirmed", tier=TIER_WARN, kind_cn="顶部路牌",
            title=f"{len(tops_confirmed)} 个顶部构造确认",
            reason_cn="顶部构造确认——预警路牌，不必然等于反向（trading-spec §7.4）",
            is_new=latest == today,
            key_prices={"neckline": necklines[-1]} if necklines else {},
            available_date=latest.isoformat(),
        ))

    # S3b 反向关键性波动（预警路牌）
    key_waves = [
        e for e in events
        if getattr(e, "rule_id", "") == KEY_WAVE_RULE_ID
        and getattr(e, "available_date", None) in window
    ]
    if key_waves:
        ev = max(key_waves, key=lambda e: e.available_date)
        signals.append(SellSignal(
            kind="key_wave_black", tier=TIER_WARN, kind_cn="顶部路牌",
            title="反向关键性波动",
            reason_cn=f"{getattr(ev, 'reason_cn', '')}——预警路牌，不必然等于反向",
            is_new=ev.available_date == today,
            available_date=ev.available_date.isoformat(),
        ))

    # S4 颜色转黑：绿/灰 → 黑 的转换日落在窗口内
    history = list(getattr(result, "history", []) or [])
    if len(history) >= 2:
        cur, prev = history[-1], history[-2]
        cur_black = str(getattr(cur, "color", "")) == "black"
        prev_not_black = str(getattr(prev, "color", "")) != "black"
        if cur_black and prev_not_black and getattr(cur, "day", None) in window:
            signals.append(SellSignal(
                kind="color_black", tier=TIER_SOFT, kind_cn="颜色转黑",
                title="LEI 颜色转黑",
                reason_cn=f"三色状态由{_color_name(prev.color)}转黑（长趋势转弱提醒）",
                is_new=cur.day == today,
                available_date=cur.day.isoformat(),
            ))

    return signals


__all__ = [
    "EXIT_RULE_ID",
    "KEY_WAVE_RULE_ID",
    "RECENCY_BARS",
    "SellSignal",
    "TIER_HARD",
    "TIER_SOFT",
    "TIER_WARN",
    "extract_sell_signals",
]
