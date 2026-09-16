"""讨论场景的上下文构建：技术摘要全喂（spec 2026-08-23 §2.2）。

与 build_context_payload（四块裁剪，投递/监督讲解用）并存：
本模块只服务 /api/agent/chat 讨论场景，输出键固定，数值接地白名单由调用方现算。

字段接地（与 brief 假设的差异均已按真实字段核实，2026-08-23）：
- DailyAssessment 无 color_cn/stage_cn/risk_state_cn 属性，只有
  color/stage/risk_state 枚举；中文标签经 COLOR_CN/STAGE_CN/RISK_STATE_CN 映射。
- StructureInstance 无 rule_id/state_cn/key_prices 字段，真实字段为
  source_rule_id/status(structure)/c_price/neckline/reference_high。
- SignalEvent 无 summary_cn/description_cn 字段，真实字段为 reason_cn。
- frame 无 sma_long 列，长周期 SMA 列为 sma120（另有 sma60、ema60/ema120）。

裁剪守卫（Fix round 1，2026-08-23）：
- structures 只喂活跃结构（is_live = candidate/confirmed/active，types.py），
  上限 40 条；live 超限时按结构的可用日期（confirmed_date，缺省回退
  detected_date——后者为必填字段，故「无日期字段保序取前 40」仅作防御兜底）
  升序稳定排序后取最新 40（同日期保持流水线原序）。
- volume 维度从全部 events 按 rule_id 含 "volume" 过滤后截最新 10 条，
  不再从已截断的 recent_events 里过滤。
- key_prices 剔除值为 None 的键。
- payload 总量守卫（spec §2.2「超出时按行裁剪，事件类先砍最旧」）：
  json 序列化（ensure_ascii=False）超 30_000 字符时，每次裁 recent_events
  最旧 5 条并重测；裁到只剩 5 条仍超则保留 5 条，并在返回 dict 新增顶层键
  "truncated": True（契约增量键，Task 5 消费端允许增量；正常路径不出现）。
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd

from lei_signal.api.labels import RISK_STATE_CN, STRUCTURE_STATUS_CN, STRUCTURE_TYPE_CN
from lei_signal.api.macd_events import build_macd_events
from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.domain.types import COLOR_CN, STAGE_CN, SignalEvent, StructureInstance
from lei_signal.plans.models import ActionItem, TradePlan

_MAX_EVENTS = 20
_MAX_MACD_BARS = 60
_MAX_STRUCTURES = 40
_MAX_VOLUME_EVENTS = 10
_MAX_PAYLOAD_CHARS = 30_000
_MIN_EVENTS_AFTER_TRIM = 5
_EVENTS_TRIM_STEP = 5


def _last_value(frame: pd.DataFrame, column: str) -> float | None:
    """取 frame 最后一行的数值；列缺失或为 NaN 时显式置 None，不猜测。"""
    if column not in frame.columns:
        return None
    value = frame[column].iloc[-1]
    if pd.isna(value):
        return None
    return float(value)


def _structure_available_date(s: StructureInstance) -> date:
    """结构可用日期：已确认结构取 confirmed_date，否则回退必填的 detected_date。"""
    return s.confirmed_date or s.detected_date


def _event_row(e: SignalEvent) -> dict[str, Any]:
    return {
        "available_date": str(e.available_date),
        "rule_id": e.rule_id,
        "summary_cn": e.reason_cn,
    }


def _payload_chars(payload: dict[str, Any]) -> int:
    """payload 序列化字符数（ensure_ascii=False，与审查的 keep-CJK 口径一致）。"""
    return len(json.dumps(payload, ensure_ascii=False, default=str))



def _breadth_block() -> dict:
    """市场宽度叙事标注层：A股/美股占比直读大白话（不打分不判定）。

    美股自 2026-08-14 断档（成分股行情源限流），如实标注截至日——
    旧数不冒充当下（红线：数值直读，不推算）。"""
    from lei_signal.copilot import breadth as breadth_mod  # noqa: PLC0415

    out: dict = {"note_cn": "叙事标注层（research_proxy），不参与技术判定"}
    try:
        out["a_share_cn"] = breadth_mod.a_share_breadth_cn()
    except Exception:  # noqa: BLE001
        out["a_share_cn"] = None
    try:
        out["us_cn"] = breadth_mod.us_breadth_cn()
    except Exception:  # noqa: BLE001
        out["us_cn"] = None
    return out


_DIR_CN = {"bullish": "利多", "bearish": "利空", "neutral": "中性"}


def _news_block(
    news_brief: dict[str, Any] | None, symbol: str
) -> dict[str, Any]:
    """消息面叙事标注层：该标的多空计数/最新标题 + 全局多空温度。

    红线：只做「为什么」的叙事参考，不参与技术判定、不构成信号——键名里
    显式带 note_cn，LLM 引用时必须保留该口径。
    字段对齐 NewsfeedService.watchlist_brief 的真实输出（2026-09-05 核实）：
    item 的计数键是 bullish/bearish/neutral，最新一条在 top{title,direction}；
    旧代码读 bull_count/latest_title 等不存在的键，个股叙事恒为空 dict。
    """
    if not isinstance(news_brief, dict):
        return {"note_cn": "消息面未接入本次材料"}
    items = news_brief.get("items") or []
    mine = next(
        (i for i in items if isinstance(i, dict) and i.get("symbol") == symbol), None
    )
    mood = news_brief.get("mood") or {}
    out: dict[str, Any] = {
        "note_cn": "叙事标注层（为什么），不参与技术判定、不构成信号",
    }
    if mine:
        top = mine.get("top") or {}
        direction = top.get("direction")
        symbol_brief: dict[str, Any] = {
            k: mine.get(k)
            for k in ("bullish", "bearish", "neutral")
            if mine.get(k) is not None
        }
        if top.get("title"):
            symbol_brief["latest_title"] = top["title"]
        if direction:
            symbol_brief["latest_direction_cn"] = _DIR_CN.get(direction, direction)
        out["symbol_brief"] = symbol_brief or None
    else:
        out["symbol_brief"] = None  # 近期无已评分消息：如实说无，不硬凑
    if isinstance(mood, dict) and mood.get("bullish") is not None:
        out["market_mood"] = {
            "bullish": mood.get("bullish"),
            "bearish": mood.get("bearish"),
            "neutral": mood.get("neutral"),
        }
    return out


def _major_events_block(major_events: dict[str, Any] | None) -> dict[str, Any] | None:
    """重大事件叙事块（客观字段 only，2026-09-05 用户口径）。

    用户点名要「影响资本开支」级别的产业大事（英伟达/谷歌类），不要博主
    观点等主观信息——service 层已保证只出标题/类别/方向/分数/时间。
    传入 None（服务缺席）时整块不出，不硬凑。
    """
    if not isinstance(major_events, dict) or not major_events.get("available"):
        return None
    items = [
        {
            k: it.get(k)
            for k in ("title", "category_cn", "direction_cn", "importance", "when_cn")
            if it.get(k) is not None
        }
        for it in (major_events.get("items") or [])
        if isinstance(it, dict) and it.get("title")
    ]
    if not items:
        return None
    return {
        "note_cn": "客观事件参考（叙事层，不参与技术判定）",
        "items": items,
    }

def build_discussion_context(
    result: AnalysisResult,
    review_dump: dict[str, Any] | None,
    plans: list[TradePlan],
    action_items: list[ActionItem],
    news_brief: dict[str, Any] | None = None,
    major_events: dict[str, Any] | None = None,
) -> dict[str, Any]:
    a = result.assessment
    close = float(result.frame["close"].iloc[-1])
    ema20 = _last_value(result.frame, "ema20")
    sma_long = _last_value(result.frame, "sma120")

    live_structures = [s for s in result.structures if s.is_live]
    if len(live_structures) > _MAX_STRUCTURES:
        live_structures = sorted(live_structures, key=_structure_available_date)[
            -_MAX_STRUCTURES:
        ]
    structures = [
        {
            "side": s.side,
            "type_cn": STRUCTURE_TYPE_CN.get(s.structure_type, s.structure_type),
            "rule_id": s.source_rule_id,
            "state_cn": STRUCTURE_STATUS_CN.get(s.status.value, s.status.value),
            "key_prices": {
                k: v
                for k, v in {
                    "c_price": s.c_price,
                    "neckline": s.neckline,
                    "reference_high": s.reference_high,
                }.items()
                if v is not None
            },
        }
        for s in live_structures
    ]
    recent = [_event_row(e) for e in result.events[-_MAX_EVENTS:]]
    volume_events = [
        _event_row(e)
        for e in result.events
        if e.rule_id and "volume" in e.rule_id
    ][-_MAX_VOLUME_EVENTS:]
    profile = None
    if result.profile is not None:
        profile = {
            "proxy": True,  # 红线：界面与 LLM 都不得声称真实持仓成本
            "poc": result.profile.poc,
            "val": result.profile.val,
            "vah": result.profile.vah,
            "current_price": close,
        }
    plan_rows = [
        {
            "plan_id": p.plan_id, "state": p.state, "module": p.module,
            "direction": p.direction, "invalidation_price": p.invalidation_price,
            "valid_until": p.valid_until,
            "open_actions": sum(
                1 for i in action_items
                if i.plan_id == p.plan_id and i.state == "open"
            ),
        }
        for p in plans
    ]
    payload: dict[str, Any] = {
        "symbol": result.symbol,
        "display_name": result.display_name,
        "as_of": str(a.as_of),
        "assessment": {
            "color_cn": COLOR_CN.get(a.color.value, a.color.value),
            "stage_cn": STAGE_CN.get(a.stage.value, a.stage.value),
            "risk_state_cn": RISK_STATE_CN.get(a.risk_state.value, a.risk_state.value),
            "dimensions": dict(a.dimensions or {}),
        },
        "dual_ma": {"close": close, "ema20": ema20, "sma_long": sma_long},
        "structures": structures,
        "volume": {"events": volume_events},
        "volume_profile": profile,
        "macd": build_macd_events(result, max_bars=_MAX_MACD_BARS)[-12:],
        "recent_events": recent,
        "buy_point_review": review_dump,
        "plans": plan_rows,
        "news": _news_block(news_brief, result.symbol),
        "major_events": _major_events_block(major_events),
        "breadth": _breadth_block(),
    }
    # 总量守卫：超预算时事件类先砍最旧（recent_events 按时间升序，最旧在头部）。
    while (
        len(payload["recent_events"]) > _MIN_EVENTS_AFTER_TRIM
        and _payload_chars(payload) > _MAX_PAYLOAD_CHARS
    ):
        del payload["recent_events"][:_EVENTS_TRIM_STEP]
    if _payload_chars(payload) > _MAX_PAYLOAD_CHARS:
        payload["truncated"] = True
    return payload


__all__ = ["build_discussion_context"]
