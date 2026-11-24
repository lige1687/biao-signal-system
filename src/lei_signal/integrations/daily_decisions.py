"""Present existing trading evidence; never calculate a new trading signal."""

from __future__ import annotations

import html
import math
from datetime import datetime
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def product_label(row: dict) -> str:
    code = str(row.get("code") or row.get("fund_code") or row.get("symbol") or "").strip()
    name = str(row.get("display_name") or row.get("name") or row.get("fund_name") or "").strip()
    if not name or name == code:
        name = "名称待核对"
    return f"{name}（{code}）" if code else name


def _payload(value: dict | None) -> dict:
    value = value or {}
    return value.get("data") or {} if "available" in value else value


def _positive(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def plan_scenario(plan: dict, *, product: dict | None = None) -> dict:
    """Arithmetic from a saved plan; neither a price estimate nor an entry approval."""
    product = product or {"symbol": plan.get("symbol")}
    source_symbol = plan.get("symbol")
    product_symbol = product.get("symbol") or product.get("code")
    same_product = bool(source_symbol and source_symbol == product_symbol)
    entry = _positive(plan.get("entry_price_ref"))
    stop = _positive(plan.get("invalidation_price") or plan.get("stop_price"))
    target = _positive(plan.get("target_b_price") or plan.get("take_profit_price"))
    valid = same_product and plan.get("direction", "long") == "long" and all((entry, stop, target))
    valid = bool(valid and stop < entry < target)
    return {
        "product": product_label(product),
        "plan_id": plan.get("plan_id"),
        "plan_kind": plan.get("plan_kind", "entry"),
        "state": plan.get("state"),
        "entry": entry if same_product else None,
        "stop": stop if same_product else None,
        "target": target if same_product else None,
        "reward_risk": round((target - entry) / (entry - stop), 6) if valid else None,
        "risk_pct": round((entry - stop) / entry * 100, 4) if valid else None,
        "reward_pct": round((target - entry) / entry * 100, 4) if valid else None,
        "source": plan.get("target_b_source") or "用户计划；价格依据待核对",
        "recorded_at": plan.get("updated_at"),
        "invalidation": plan.get("invalidation_criteria_cn")
        or plan.get("stop_plan_cn")
        or "待补充",
        "take_profit": plan.get("take_profit_plan_cn") or "待补充",
        "entry_condition": plan.get("entry_trigger_cn") or "待补充",
        "limitations": [
            "按计划价格算潜在盈利与损失，尚未扣费用，不是成功概率或下单指令。",
            *([] if same_product else ["计划与当前产品不是同一对象，不能借用其价格。"]),
            *([] if valid else ["进入、失效和目标位置不齐或关系不合理，不能计算盈亏比。"]),
            *(
                ["已有持仓观察计划，不代表原始买入理由已核实。"]
                if plan.get("plan_kind") == "holding_watch"
                else []
            ),
        ],
    }


def _holding_review(item: dict, plan: dict, *, now: datetime, slot: str) -> dict:
    meta = (item.get("technical") or {}).get("meta") or {}
    gaps = list(item.get("gaps") or [])
    if not plan or plan.get("state") != "entered":
        gaps.append("尚无已确认且关联此持仓的计划")
    if not item.get("technical"):
        gaps.append("尚无同产品合格技术行情")
    if meta.get("is_intraday_forming"):
        gaps.append("日线仍在形成，不能作为收盘条件确认")
    if not meta.get("last_bar_date"):
        gaps.append("行情日期未提供")
    elif str(meta["last_bar_date"])[:10] > now.date().isoformat():
        gaps.append("行情日期晚于本次检查")
    if plan and (not item.get("symbol") or plan.get("symbol") != item["symbol"]):
        gaps.append("计划与持仓产品未核为同一对象")
    if item.get("status") not in {"no_trigger", "action_required"}:
        gaps.append(item.get("reason_cn") or "系统尚未确认资料可用于条件检查")
    alerts = item.get("alerts") or []
    dated = []
    if not gaps and slot == "1440":
        for alert in alerts:
            if not alert.get("data_as_of") or not alert.get("actionable_from"):
                gaps.append("条件证据缺少数据日期或可采用日期")
                continue
            if (
                str(alert["actionable_from"])[:10] > now.date().isoformat()
                or str(alert["data_as_of"])[:10] > now.date().isoformat()
            ):
                gaps.append("条件尚未到可采用日期")
                continue
            dated.append(alert)
    if slot == "1135":
        state = "午间仅汇报信息"
        dated = []
    elif gaps:
        state = "无法判断；待补资料"
        dated = []
    elif dated:
        state = "系统原计划条件有变化，请按列出的证据复核"
    else:
        state = "本次合格资料未检出系统已登记的触发条件"
    return {
        "product": product_label(item),
        "holding_id": item.get("holding_id"),
        "nav": item.get("nav"),
        "data_as_of": meta.get("last_bar_date"),
        "status": state,
        "gaps": list(dict.fromkeys(gaps)),
        "alerts": dated,
        "scenario": plan_scenario(plan, product=item) if plan else None,
        "manual_review": plan.get("invalidation_criteria_cn") or None,
        "note": "文字理由需人工复核；没有触发不代表风险为零。",
    }


def build_daily_decisions(
    *,
    portfolio: dict,
    plans: dict | None = None,
    opportunities: dict | None = None,
    news: dict | None = None,
    research: dict | None = None,
    slot: str = "1440",
    now: datetime | None = None,
) -> dict:
    if slot not in {"1135", "1440"}:
        raise ValueError("unsupported slot")
    now = now or datetime.now(SHANGHAI)
    if now.tzinfo is None:
        raise ValueError("timezone required")
    now = now.astimezone(SHANGHAI)
    p = _payload(portfolio)
    plans_by_id = {x.get("plan_id"): x for x in _payload(plans).get("plans", [])}
    holdings = []
    for item in p.get("items", []):
        linked = item.get("plan") or {}
        plan = plans_by_id.get(linked.get("plan_id"), linked)
        holdings.append(_holding_review(item, plan, now=now, slot=slot))
    opportunities_data = _payload(opportunities)
    candidates = []
    # Today's scan table lacks source bar dates/prices; expose its verdict as a
    # candidate requiring detailed evidence, never upgrade to a buy instruction.
    for group in ("actionable", "waiting", "blocked"):
        for candidate in opportunities_data.get(group, []):
            candidates.append(
                {
                    "product": product_label(candidate),
                    "symbol": candidate.get("symbol"),
                    "system_group": group,
                    "system_verdict": candidate.get("verdict_cn"),
                    "scenario": candidate.get("best_scenario_cn"),
                    "blocking_reasons": candidate.get("blocking_reasons", []),
                    "missing": candidate.get("missing_summary_cn"),
                    "scan_date": opportunities_data.get("scan_date"),
                    "source_generated_at": opportunities_data.get("generated_at"),
                    "next_step": "读取该产品的详细价格依据、行情时点及有效条件后再设计计划。",
                    "is_trade_instruction": False,
                }
            )
    items = _payload(news).get("items", [])
    relationships = []
    for item in p.get("items", []):
        code = item.get("code")
        related = []
        for article in items:
            symbols = article.get("symbols") or []
            if isinstance(symbols, list) and code and code in symbols:
                related.append(
                    {
                        "title": article.get("title"),
                        "url": article.get("url"),
                        "published_at": article.get("published_at"),
                        "content_basis": article.get("content_basis"),
                        "association": "系统条目明确关联此产品；影响方向仍需读正文核实",
                    }
                )
        if related:
            relationships.append({"product": product_label(item), "articles": related})
    return {
        "generated_at": now.isoformat(),
        "slot": slot,
        "holdings": holdings,
        "coverage": p.get("coverage", {}),
        "opportunities": candidates,
        "related_news": relationships,
        "research_evidence": {
            "catalog": _payload(research).get("items", []),
            "current_trade_win_probability": None,
            "note": "研究结论需核产品、时期、费用与来源；不换算为这笔交易的胜率。",
        },
        "source_errors": {
            name: value.get("errors")
            for name, value in (
                ("portfolio", portfolio),
                ("plans", plans),
                ("opportunities", opportunities),
                ("news", news),
                ("research", research),
            )
            if value and value.get("errors")
        },
        "limitations": ["扫描时间不等于行情时间。", "只呈现系统已登记条件，不自动下单或改仓。"],
    }


def render_scenario_svg(scenario: dict) -> str:
    """A standalone, deterministic conditional price map, without execution UI."""
    values = [scenario.get(k) for k in ("stop", "entry", "target")]
    valid = all(_positive(v) is not None for v in values) and values[0] < values[1] < values[2]
    title = html.escape(scenario.get("product") or "名称待核对")
    source = html.escape(str(scenario.get("source") or "价格依据待核对"))
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="780" height="280" viewBox="0 0 780 280">',
        '<rect width="780" height="280" fill="#f7f8fa"/>',
        f'<text x="32" y="38" font-family="sans-serif" font-size="22">{title} · 条件场景</text>',
    ]
    if valid:
        lo, _, hi = values
        colors = ("#b42318", "#175cd3", "#067647")
        parts.append('<line x1="60" y1="110" x2="700" y2="110" stroke="#98a2b3" stroke-width="3"/>')
        for label, value, color in zip(
            ("失效位置", "计划进入", "目标位置"), values, colors, strict=True
        ):
            x = 60 + (value - lo) / (hi - lo) * 640
            parts.extend(
                [
                    f'<circle cx="{x:.2f}" cy="110" r="7" fill="{color}"/>',
                    f'<text x="{x:.2f}" y="145" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="14">{label}</text>',
                    f'<text x="{x:.2f}" y="168" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="16">{value:g}</text>',
                ]
            )
        parts.append(
            f'<text x="32" y="210" font-family="sans-serif" font-size="16">潜在盈利 / 损失：'
            f"{scenario.get('reward_risk')} 倍；费用未扣，非成功概率</text>"
        )
    else:
        parts.append(
            '<text x="32" y="120" font-family="sans-serif" font-size="18">'
            "缺少同产品有效价格，暂不绘制目标或止损位置。</text>"
        )
    parts.extend(
        [
            '<text x="32" y="242" font-family="sans-serif" font-size="13">依据：'
            f"{source[:85]}</text>",
            "</svg>",
        ]
    )
    return "\n".join(parts)
