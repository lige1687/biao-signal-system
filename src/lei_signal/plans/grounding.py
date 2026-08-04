"""LLM 输出接地校验 + 禁用词 + 降级模板渲染（红线：判定权在 Python）。

LLM 只负责把 alert 讲成人话。其输出必须过 ``verify_grounding`` 白名单校验：
1. 抽取所有 ``rule_id:xxx`` 标签，必须 ⊆ 本次喂入的 alert 的 rule_id 集合（超集即拒）；
2. 不得命中禁用词表（买入/卖出/建议买/该买/加仓/减仓/抄底）。
两次都过不了 -> 降级为固定模板直出。监督员宁可说话生硬，不可说错。
"""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from lei_signal.plans.models import ActionItem, PlanAlert, TradePlan

#: 禁用词表（买入/卖出指令类）。命中即拒绝。
FORBIDDEN_TERMS: tuple[str, ...] = (
    "买入", "卖出", "建议买", "该买", "加仓", "减仓", "抄底",
)

#: 渲染结果中「判定方式为研究代理」的固定短语（两层标注的判定侧）。
RESEARCH_PROXY_MARKER = "判定方式为研究代理"

_RULE_ID_PATTERN = re.compile(r"rule_id[:：]\s*([A-Za-z_][A-Za-z0-9_]*)")


def verify_grounding(text: str, allowed_rule_ids: set[str] | frozenset[str]) -> tuple[bool, str]:
    """校验 LLM 输出是否接地。返回 (ok, reason)。

    - 禁用词命中 -> 拒绝；
    - 文中出现的 rule_id 标签必须是 allowed_rule_ids 的子集 -> 超集即拒。
    """
    for term in FORBIDDEN_TERMS:
        if term in text:
            return False, f"禁用词命中: {term}"
    found = set(_RULE_ID_PATTERN.findall(text))
    extra = found - set(allowed_rule_ids)
    if extra:
        return False, f"引用了未喂入的 rule_id: {sorted(extra)}"
    return True, ""


def _severity_mark(severity: str) -> str:
    return {"block": "■ 阻断", "remind": "■ 提醒", "hint": "□ 提示"}.get(severity, "□ 提示")


def _action_kind_cn(kind: str | None) -> str:
    return {"ENTER": "入场", "EXIT": "退出", "REVIEW": "复核"}.get(kind or "", "")


def _evidence_kv(evidence: dict[str, Any]) -> str:
    items = [f"{k}={v}" for k, v in evidence.items() if v is not None]
    return ", ".join(items) if items else "-"


def template_render(
    alerts: list[PlanAlert],
    *,
    plan: TradePlan | None = None,
    action_items: list[ActionItem] | None = None,
    context_min: dict[str, Any] | None = None,
) -> str:
    """固定模板渲染（降级路径，也作无 LLM 时的默认渲染）。"""
    lines: list[str] = []
    ctx = context_min or {}
    if plan is not None:
        lines.append(
            f"【计划】{plan.symbol} 模块{plan.module} · "
            f"{plan.entry_rule_id or '-'} · 状态 {plan.state} · 有效期至 {plan.valid_until or '-'}"
        )
    if ctx:
        stale = "（数据陈旧，仅供参考）" if ctx.get("cache_fallback_used") else ""
        lines.append(
            f"【数据】{ctx.get('last_bar_date', '-')}（{ctx.get('provider', '-')}）{stale}"
        )
    lines.append("")

    open_items = [i for i in (action_items or []) if i.state == "open"]
    if open_items:
        for item in open_items:
            lines.append(f"▶ 待办（催办第 {item.nag_count} 次）")
            lines.append(f"  {_action_kind_cn(item.kind)}：{item.source_alert_code}")
            lines.append(f"  可执行日：{item.due_from or '-'}")
            lines.append("  -> 你可以：标记已执行 / 推迟（需说明原因）")
            lines.append("")

    for a in alerts:
        lines.append(_severity_mark(a.severity))
        lines.append(f"  {a.next_step_cn or a.code}")
        lines.append(f"  [rule_id:{a.rule_id} | 证据:{_evidence_kv(a.evidence)}]")
        provenance_line = ""
        if a.principle_source:
            provenance_line = f"{a.principle_source} | {RESEARCH_PROXY_MARKER}"
            if a.caveat_cn:
                provenance_line += f"（{a.caveat_cn}）"
        elif a.logic_provenance == "research_proxy":
            provenance_line = RESEARCH_PROXY_MARKER
        if provenance_line:
            lines.append(f"  {provenance_line}")
        lines.append("")

    lines.append("【下一步观察】以上 next_step 均来自判定层，非 LLM 自创")
    return "\n".join(lines).strip()


def render_alerts(
    alerts: list[PlanAlert],
    *,
    plan: TradePlan | None = None,
    action_items: list[ActionItem] | None = None,
    context_min: dict[str, Any] | None = None,
    llm_render: Callable[[list[PlanAlert], dict[str, Any] | None], str] | None = None,
    max_attempts: int = 2,
) -> str:
    """渲染 alert 列表。``llm_render`` 为 None 时直接用模板；否则校验，两次失败降级。"""
    if llm_render is None:
        return template_render(alerts, plan=plan, action_items=action_items,
                               context_min=context_min)
    allowed = {a.rule_id for a in alerts if a.rule_id}
    for _ in range(max_attempts):
        try:
            text = llm_render(alerts, context_min)
        except Exception:  # noqa: BLE001  LLM 调用失败也降级，不抛给用户
            break
        ok, _reason = verify_grounding(text, allowed)
        if ok:
            return text
    return template_render(alerts, plan=plan, action_items=action_items,
                           context_min=context_min)


__all__ = [
    "FORBIDDEN_TERMS",
    "RESEARCH_PROXY_MARKER",
    "render_alerts",
    "template_render",
    "verify_grounding",
]
