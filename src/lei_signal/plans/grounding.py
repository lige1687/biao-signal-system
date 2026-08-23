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

#: 数值接地：日期（整段豁免）与数值 token（整数/小数，尾部可带 %）。
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUM_TOKEN_RE = re.compile(r"-?\d+(?:\.\d+)?%?")

#: 渲染顺序：阻断优先，其后提醒、提示（规格 §13 语义）
_SEVERITY_ORDER = {"block": 0, "remind": 1, "hint": 2}


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
    next_step_by_code = {a.code: a.next_step_cn for a in alerts if a.next_step_cn}
    if open_items:
        for item in open_items:
            lines.append(f"▶ 待办（催办第 {item.nag_count} 次）")
            detail = next_step_by_code.get(item.source_alert_code) or item.source_alert_code
            lines.append(f"  {_action_kind_cn(item.kind)}：{detail}")
            lines.append(f"  可执行日：{item.due_from or '-'}")
            lines.append("  -> 你可以：标记已执行 / 推迟（需说明原因）")
            lines.append("")

    # 阻断优先（规格 §13「不开新仓」）：block 先讲，其后 remind、hint。
    # 否则「环境阻断」与「入场条件成立」并列，读起来像可以入场。
    ordered = sorted(alerts, key=lambda a: _SEVERITY_ORDER.get(a.severity, 9))
    entry_blocked = any(
        a.severity == "block" and str(a.code).startswith("ENTRY_") for a in alerts
    )
    if entry_blocked:
        lines.append("※ 本轮存在入场阻断条件，按规则不开新仓（规格 §13）；")
        lines.append("  下列入场类提醒被阻断条件压制，不构成可入场结论。")
        lines.append("")

    for a in ordered:
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


# ---------------- 数值接地（讨论场景主校验） ----------------


def collect_payload_numbers(payload: Any) -> frozenset[float]:
    """递归抽取 payload 中的数值。str 不抽（避免 rule_id 片段混入）。"""
    if isinstance(payload, bool):
        return frozenset()
    if isinstance(payload, (int, float)):
        return frozenset({float(payload)})
    if isinstance(payload, dict):
        out: set[float] = set()
        for v in payload.values():
            out |= collect_payload_numbers(v)
        return frozenset(out)
    if isinstance(payload, (list, tuple)):
        out = set()
        for v in payload:
            out |= collect_payload_numbers(v)
        return frozenset(out)
    return frozenset()


def extract_market_numbers(text: str) -> list[float]:
    """抽取需校验的行情数值。

    豁免：日期、纯小整数（|n| < 100，序号/量词/次数）、圆圈数字。
    校验：小数、百分数、绝对值 >= 100 的整数（价位）。
    """
    text = _DATE_RE.sub(" ", text)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", " ", text)
    out: list[float] = []
    for tok in _NUM_TOKEN_RE.findall(text):
        is_pct = tok.endswith("%")
        num = float(tok.rstrip("%"))
        has_decimal = "." in tok
        if not (has_decimal or is_pct or abs(num) >= 100):
            continue  # 序号/量词/次数豁免
        out.append(num)
    return out


def verify_numeric_grounding(
    text: str, allowed: frozenset[float], tolerance: float = 0.005
) -> tuple[bool, str]:
    """回答中的每个行情数值必须在白名单，或为其相对偏差/四舍五入。

    相对偏差：n 可能是 (b-a)/a*100 形式的百分数（payload 任意两数之差）。
    """
    nums = extract_market_numbers(text)
    base = [a for a in allowed if a != 0]
    for n in nums:
        ok = _within(n, allowed, tolerance)
        if not ok and n > 0 and base:
            # 百分比派生：n% ≈ 某两个白名单数的相对差
            for i, a in enumerate(base):
                for b in base[i + 1:]:
                    if abs(abs(b - a) / a * 100 - n) <= max(0.1, tolerance * 100):
                        ok = True
                        break
                if ok:
                    break
        if not ok:
            return False, f"数值 {n} 不在上下文白名单"
    return True, ""


def _within(n: float, allowed: frozenset[float], tolerance: float) -> bool:
    for a in allowed:
        if a == 0:
            if abs(n) < 1e-9:
                return True
        elif abs(n - a) / abs(a) <= tolerance:
            return True
    return False


__all__ = [
    "FORBIDDEN_TERMS",
    "RESEARCH_PROXY_MARKER",
    "collect_payload_numbers",
    "extract_market_numbers",
    "render_alerts",
    "template_render",
    "verify_grounding",
    "verify_numeric_grounding",
]
