"""规则意图识别 + 报单文本解析（纯函数，零 LLM）。

方案三的第一层：关键词命中直达流水线；识别不到回落通用讨论（agent.py 的
/agent/chat）。路由表可持续补充——这里只是「常见说法」的快捷方式，不是
意图的权威定义。报单解析是 best-effort：抽不全的字段进 missing，由前端
确认卡补齐，解析错误不阻断报单。

意图路由扩展（2026-09-19，agent-intent-routing）：旧五类之后追加
dca/sentiment/mindset 三类显式规则。优先级=元组顺序：旧五类在前、原序原词
（追加式扩展，旧行为零回归由构造保证）；新三类依次 dca→sentiment→mindset，
sentiment 先于 mindset 与 copilot/resolve.py 的 _TOPIC_RULES 自身顺序一致。

- sentiment/mindset 词表与 resolve.py 话题词表逐字一致（同一句话在 dispatch
  快捷层与 agent 讨论入口同向）；dca 刻意窄于 resolve.py 的 dca 话题词
  （不含 闲钱/每月/工资/新收入）——这些是资金用途词汇，归讨论入口处理，
  进本粗粒度层会误劫持（如「每月复盘」撞「每月」）。
- 本层是无否定处理的子串匹配（「别定投了」命中 dca，与「别买了」命中
  trade_report 同一既有局限）；否定/假设的精细处理归 resolve.py，不在本层复制。
- mindset 下游种子库 configs/mindset_seed.json 已于 2026-09-19 S1 接入
  （copilot/mindset.py 加载器）：种子在场时命中即出叙事卡、不带回落标注；
  种子缺失/损坏时仍带 fallback_reason 标注，由 dispatch 显式回落通用讨论
  且回落原因可观察（行为与接入前缺位场景一致）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from lei_signal.api.schemas import TradePreviewDTO

#: 意图关键词表（顺序即优先级：报单优先于推荐，避免「买了什么好」误判）。
#: 2026-09-19 尾部追加 dca/sentiment/mindset：旧五类在前零回归由构造保证；
#: sentiment 先于 mindset 与 resolve.py 话题词表同序；词表口径见模块 docstring。
_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("trade_report", ("买了", "卖了", "申购", "赎回", "报单", "下单了", "成交了")),
    ("scout", ("最近机会", "看看机会", "发掘机会", "机会扫描", "扫扫机会")),
    ("recommend", ("今天看什么", "推荐", "有什么机会", "扫一下自选", "标的雷达")),
    ("holdings", ("持仓", "我的仓位", "持仓速览")),
    ("review", ("复盘", "周报", "这周做得怎么样")),
    ("dca", ("定投", "分批投")),
    ("sentiment", ("情绪", "冰点", "强热", "恐慌", "热警报", "散户")),
    ("mindset", ("心态", "拿不住", "怕跌", "慌", "睡不着")),
)

#: 认知/心态下游种子库缺位时的显式回落原因（dispatch 回落分支消费，
#: 随回包 fallback_reason 字段可观察）。种子在场（copilot/mindset.py 校验
#: 通过）时不标注，直接出叙事卡。
_MINDSET_FALLBACK_REASON = "mindset_seed_missing"


def _mindset_seeds_ok() -> bool:
    # 独立小函数便于测试替换（intent 层只问在场与否，不搬种子内容）。
    from lei_signal.copilot.mindset import seeds_available  # noqa: PLC0415

    return seeds_available()

_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(万|w|W|k|K|千|块|元)?")
_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_SIDE_BUY = ("买", "申购")
_SIDE_SELL = ("卖", "赎回")


@dataclass(slots=True)
class Intent:
    # kind: trade_report|scout|recommend|holdings|review|dca|sentiment|mindset|chat
    kind: str
    symbol: str | None = None
    params: dict = field(default_factory=dict)
    #: 识别成功但下游未就绪时的显式回落原因（如 mindset 种子库缺位）；None=无标注。
    fallback_reason: str | None = None


def parse_intent(message: str) -> Intent:
    text = (message or "").strip()
    for kind, needles in _INTENT_RULES:
        if any(n in text for n in needles):
            fallback = (
                None if _mindset_seeds_ok() else _MINDSET_FALLBACK_REASON
            ) if kind == "mindset" else None
            return Intent(kind=kind, fallback_reason=fallback)
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
