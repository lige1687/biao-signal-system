"""规则意图识别 + 报单文本解析（纯函数，零 LLM）。

方案三的第一层：关键词命中直达流水线；识别不到回落通用讨论（agent.py 的
/agent/chat）。路由表可持续补充——这里只是「常见说法」的快捷方式，不是
意图的权威定义。报单解析是 best-effort：抽不全的字段进 missing，由前端
确认卡补齐，解析错误不阻断报单。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from lei_signal.api.schemas import TradePreviewDTO

#: 意图关键词表（顺序即优先级：报单优先于推荐，避免「买了什么好」误判）。
_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("trade_report", ("买了", "卖了", "申购", "赎回", "报单", "下单了", "成交了")),
    ("recommend", ("今天看什么", "推荐", "有什么机会", "扫一下自选", "标的雷达")),
    ("holdings", ("持仓", "我的仓位", "持仓速览")),
    ("review", ("复盘", "周报", "这周做得怎么样")),
)

_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(万|w|W|k|K|千|块|元)?")
_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_SIDE_BUY = ("买", "申购")
_SIDE_SELL = ("卖", "赎回")


@dataclass(slots=True)
class Intent:
    kind: str                    # recommend|holdings|trade_report|review|chat
    symbol: str | None = None
    params: dict = field(default_factory=dict)


def parse_intent(message: str) -> Intent:
    text = (message or "").strip()
    for kind, needles in _INTENT_RULES:
        if any(n in text for n in needles):
            return Intent(kind=kind)
    return Intent(kind="chat")


def _resolve_side(text: str) -> str | None:
    buy = any(n in text for n in _SIDE_BUY)
    sell = any(n in text for n in _SIDE_SELL)
    if buy and not sell:
        return "buy"
    if sell and not buy:
        return "sell"
    return None


def _resolve_amount(text: str) -> float | None:
    # 先剔除 6 位基金代码，避免「买了1万515880」把 515880 当成金额。
    stripped = _CODE_RE.sub(" ", text)
    m = _AMOUNT_RE.search(stripped)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2)
    if unit in ("万", "w", "W"):
        value *= 10_000.0
    elif unit in ("k", "K", "千"):
        value *= 1_000.0
    return value


def _resolve_date(text: str, today: str) -> str:
    if "昨天" in text:
        return (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    if "前天" in text:
        return (date.fromisoformat(today) - timedelta(days=2)).isoformat()
    # 无日期词默认今天（报单默认收盘口径）
    return today


#: 「…块的纳斯达克100基金」→ 名字跟在金额单位后面。
_NAME_AFTER_AMOUNT_RE = re.compile(r"[块元万]([\u4e00-\u9fa5A-Za-z0-9]{2,20}?)基金")
#: 「卖了1.5万白酒基金」→ 名字直接贴着「基金」。
_NAME_DIRECT_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9]{2,20}?)基金")
_NAME_NOISE = re.compile(r"^[\d.\s]+(?:[kwKW千万块元]|千)?")
_NAME_TOKENS = ("我买了", "买了", "我卖了", "卖了", "申购了", "申购", "赎回了", "赎回")


def _resolve_name(text: str) -> str | None:
    """基金名 best-effort：优先取金额单位之后的串，其次紧贴「基金」的串。"""
    m = _NAME_AFTER_AMOUNT_RE.search(text)
    if m:
        return m.group(1)
    m = _NAME_DIRECT_RE.search(text)
    if m:
        name = m.group(1)
        for token in _NAME_TOKENS:
            name = name.replace(token, "")
        name = _NAME_NOISE.sub("", name)
        return name or None
    return None


def parse_trade_report(message: str, *, today: str) -> TradePreviewDTO:
    text = (message or "").strip()
    side = _resolve_side(text)
    amount = _resolve_amount(text)
    code_m = _CODE_RE.search(text)
    missing: list[str] = []
    if side is None:
        side = "buy"
        missing.append("side")
    if amount is None:
        missing.append("amount")
    if code_m is None:
        missing.append("fund_code")
    name = None
    if code_m is None:
        name = _resolve_name(text)
        if name is None:
            missing.append("fund_name")
    return TradePreviewDTO(
        fund_code=code_m.group(1) if code_m else None,
        fund_name=name,
        side=side,
        side_cn="申购" if side == "buy" else "赎回",
        amount=amount,
        trade_date=_resolve_date(text, today),
        missing=missing,
    )
