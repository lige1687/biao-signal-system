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
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from lei_signal.api.labels import RISK_STATE_CN, STRUCTURE_STATUS_CN, STRUCTURE_TYPE_CN
from lei_signal.api.macd_events import build_macd_events
from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.domain.types import COLOR_CN, STAGE_CN
from lei_signal.plans.models import ActionItem, TradePlan

_MAX_EVENTS = 20
_MAX_MACD_BARS = 60


def _last_value(frame: pd.DataFrame, column: str) -> float | None:
    """取 frame 最后一行的数值；列缺失或为 NaN 时显式置 None，不猜测。"""
    if column not in frame.columns:
        return None
    value = frame[column].iloc[-1]
    if pd.isna(value):
        return None
    return float(value)


def build_discussion_context(
    result: AnalysisResult,
    review_dump: dict[str, Any] | None,
    plans: list[TradePlan],
    action_items: list[ActionItem],
) -> dict[str, Any]:
    a = result.assessment
    close = float(result.frame["close"].iloc[-1])
    ema20 = _last_value(result.frame, "ema20")
    sma_long = _last_value(result.frame, "sma120")

    structures = [
        {
            "side": s.side,
            "type_cn": STRUCTURE_TYPE_CN.get(s.structure_type, s.structure_type),
            "rule_id": s.source_rule_id,
            "state_cn": STRUCTURE_STATUS_CN.get(s.status.value, s.status.value),
            "key_prices": {
                "c_price": s.c_price,
                "neckline": s.neckline,
                "reference_high": s.reference_high,
            },
        }
        for s in result.structures
    ]
    recent = [
        {
            "available_date": str(e.available_date),
            "rule_id": e.rule_id,
            "summary_cn": e.reason_cn,
        }
        for e in result.events[-_MAX_EVENTS:]
    ]
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
    return {
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
        "volume": {"events": [
            e for e in recent if e["rule_id"] and "volume" in str(e["rule_id"])
        ]},
        "volume_profile": profile,
        "macd": build_macd_events(result, max_bars=_MAX_MACD_BARS)[-12:],
        "recent_events": recent,
        "buy_point_review": review_dump,
        "plans": plan_rows,
    }


__all__ = ["build_discussion_context"]
