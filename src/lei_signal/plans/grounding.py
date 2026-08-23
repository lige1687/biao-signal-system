"""LLM 输出接地校验 + 禁用词 + 降级模板渲染（红线：判定权在 Python）。

LLM 只负责把 alert 讲成人话。其输出必须过 ``verify_grounding`` 白名单校验：
1. 抽取所有 ``rule_id:xxx`` 标签，必须 ⊆ 本次喂入的 alert 的 rule_id 集合（超集即拒）；
2. 不得命中禁用词表（买入/卖出/建议买/该买/加仓/减仓/抄底）。
两次都过不了 -> 降级为固定模板直出。监督员宁可说话生硬，不可说错。
"""
from __future__ import annotations

import re
import unicodedata
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

#: 数值接地：日期（整段豁免）与数值 token（整数/小数/科学计数法，尾部可带 %）。
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUM_TOKEN_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%?")

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

#: 归一化：NFKC（全角数字/％/逗号 -> 半角）、零宽字符、千分位逗号、中文数字。
#: 零宽族覆盖 U+200B/200C/200D + U+2060 词连接符 + U+00AD 软连字符 + U+FEFF。
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\u00ad\ufeff]")
_THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3}\b)")  # 只剥数字间逗号
_CN_RUN_RE = re.compile(r"[零一二两三四五六七八九十百千万亿]+")
_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}
_CN_BIG = {"万": 10_000, "亿": 100_000_000}


def _cn_num_to_int(s: str) -> int | None:
    """中文数字 -> int。保守解析：吃不准返回 None（调用方跳过该段，不做校验）。

    支持常用价位写法：八千七百=8700、一千九=1900、八千五=8500、
    三万五千=35000、一万三=13000、十五=15、两千零五=2005、一亿五千万=1.5e8。
    口语尾规则：单位后直接跟裸数字（中间无零）按单位/10 落位（八千五=8500）。
    """
    total = 0        # 已完成的亿/万大节
    section = 0      # 当前万以下小节（十百千级）
    num: int | None = None   # 待落位的裸数字
    last_unit = 0    # 最近一次单位（含万/亿），供口语尾落位
    last_big = 0     # 最近一次大单位（须严格递减）
    zero_gap = False  # 零间隔（两百零五=205，非口语尾）
    for ch in s:
        if ch in _CN_DIGIT:
            d = _CN_DIGIT[ch]
            if num is not None:
                return None  # 连续裸数字（一二/八千五五）不是合法中文数字
            if d == 0:
                zero_gap = True  # 零只标记跳位，不落值
            else:
                num = d
        elif ch in _CN_UNIT:
            u = _CN_UNIT[ch]
            if last_unit and u >= last_unit:
                return None  # 单位不递减（十百/千千）非法
            if num is None:
                if u != 10 or section or total:
                    return None  # 仅句首「十」可省略首一（十=10、十万）
                num = 1
            section += num * u
            num = None
            last_unit = u
            zero_gap = False
        else:  # 万 / 亿
            b = _CN_BIG.get(ch)
            if b is None:
                return None  # 不认识的字符，保守跳过
            if last_big and b >= last_big:
                return None
            if num is None and section == 0:
                return None  # 裸「万」「亿」（万一/万亿）不吃
            section += num or 0
            total += section * b
            section = 0
            num = None
            last_unit = b
            last_big = b
            zero_gap = False
    if total == 0 and section == 0 and num is None:
        return None  # 空串/纯零
    value = total + section
    if num is not None:
        if last_unit and not zero_gap:
            value += num * (last_unit // 10)  # 口语尾：八千五=8500、一万三=13000
        else:
            value += num  # 零间隔或无单位：两百零五=205、五=5
    return value


def _convert_cn_numerals(text: str) -> str:
    """把可解析的中文数字片段替换为阿拉伯数字；解析不了的保持原样（=不校验）。"""
    out: list[str] = []
    last = 0
    for m in _CN_RUN_RE.finditer(text):
        s, e = m.span()
        adj = ((s > 0 and text[s - 1] in "0123456789.")
               or (e < len(text) and text[e] in "0123456789."))
        val = None if adj else _cn_num_to_int(m.group())
        out.append(text[last:s])
        out.append(m.group() if val is None else str(val))
        last = e
    out.append(text[last:])
    return "".join(out)


def _normalize_numeric_text(text: str) -> str:
    """数值接地入口归一化：防绕过（中文数字/全角/零宽）+ 防误拆（千分位）。"""
    text = unicodedata.normalize("NFKC", text)  # ４３２１->4321、％->%、，->,
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _convert_cn_numerals(text)
    text = _THOUSANDS_RE.sub("", text)  # 1,938.56 -> 1938.56
    return text


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

    入口先归一化：NFKC（全角/％）、剔零宽字符、中文数字转阿拉伯（八千七百->8700）、
    剥千分位逗号（1,938.56->1938.56）；无法保守解析的中文数字片段跳过（=不校验）。

    豁免：日期、纯小整数（|n| < 100，序号/量词/次数）、圆圈数字。
    校验：小数、百分数、绝对值 >= 100 的整数（价位）、科学计数法。
    """
    text = _normalize_numeric_text(text)
    text = _DATE_RE.sub(" ", text)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", " ", text)  # NFKC 已转 ASCII，此处兜底
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
