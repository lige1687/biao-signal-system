"""标的形态×打法适配器（叙事层，纯规则零 LLM）。

用户口径（2026-09-06）：给一个标的，Agent 要主动说「它适合什么打法」，
而不是无脑等信号触发——基于历史经验与当前形态的相似处。

分类依据来自 2026-09-06 核心八 ETF 两年闭环实测（docs/experiments/
etf-eight-twoyear-2026-09-06.md），阈值即实测标的的真实读数：
- 稳涨型（通信 63%/沪深300 57% 环境占比、破线 ≤20 次）→ A 趋势回调
  两年 +92.6R，主战场；
- 急涨型（科创 49% 环境占比、31 次破线、+142% 持有）→ A 几乎上不了车，
  仅有的信号在末端；
- 下跌型（白酒/恒科）→ C 抄底反复送钱（恒科 10 笔 9 亏）；
- 震荡型 → 无趋势期少动。

红线：形态分类是**描述性叙事**（涨法画像），不是新买卖信号；打法建议
引用的是回测历史经验（experience.json），不参与技术判定、不改变买点
资格门（升级为规则需用户拍板）。阈值为叙事层 v1 口径（实测定标），
未进规则账本——若日后参与判定须先入账本。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

# ---- 形态度量窗口（近一年交易日） ----
_WINDOW = 250
# ---- 分类阈值（来源：2026-09-06 八 ETF 实测定标 + 时点切片校验） ----
_ENV_STEADY = 0.55     # 稳涨型：环境成立占比 ≥ 此值（通信66%/沪深300回测窗57%）
_BREAKS_STEADY = 20    # 稳涨型：一年破线 ≤ 此值（沪深300一年口径15、两年20）
_FAST_RET = 0.50       # 急涨型：一年涨幅 > 50%（科创顶部前 +129%）……
                       # 且 env < 稳涨线——涨得多但均线环境不稳（=急）。
                       # 注：早期版本用「破线≥25」是两年窗口径，一年窗急涨
                       # 段实测仅 14-18 次，已改涨幅+环境的组合判别。
_DOWNTREND = -0.15     # 下跌型：一年涨跌幅 < -15%（白酒-33%/恒科-26%）

# ---- 形态 → 适合打法（大白话，配经验索引 findings 背书） ----
_FIT_CN = {
    "steady_uptrend": (
        "稳涨型：近一年涨势稳、回调浅、均线健康。历史经验里趋势回调打法（A模块）"
        "在这类形态上两年 +93R（通信/黄金/沪深300），是最适合的打法。"
    ),
    "fast_uptrend": (
        "急涨型：涨得快、回调又深又频繁。历史经验里 A 趋势回调在这种形态上"
        "几乎上不了车（科创50 两年持有 +142% 系统反而没吃到、仅有的信号买在顶部）"
        "——不硬套趋势回调，等它走出回调浅的稳涨段再考虑。"
    ),
    "downtrend": (
        "下跌型：近一年趋势向下。历史经验里抄底打法（C 破底翻）在下跌型标的上"
        "反复送钱（恒生科技 10 笔 9 亏、白酒全亏）——不抢反弹，要等大级别的"
        "情绪/基本面反转信号。"
    ),
    "range": (
        "震荡型：近一年无明确方向。历史经验里无趋势期系统少动为妙；"
        "可留意均线密集后的标志性动作（B 模块的形态，近两年核心池少有触发）。"
    ),
}
_REGIME_CN = {
    "steady_uptrend": "稳涨型", "fast_uptrend": "急涨型",
    "downtrend": "下跌型", "range": "震荡型",
}
# 形态 → 经验索引查询条件（联动历史成绩）
_REGIME_QUERY = {
    "steady_uptrend": {"signal": "module_A_stable", "pool": "etf_mixed"},
    "fast_uptrend": {"signal": "module_A_stable", "pool": "etf_mixed"},
    "downtrend": {"signal": "module_C_2b", "pool": "etf_mixed"},
    "range": None,
}


def measure_regime(frame: pd.DataFrame, window: int = _WINDOW) -> dict[str, Any]:
    """近 window 根的形态度量（纯数值，分类与叙事由此派生）。

    frame 需含 close 列（分析服务的日线 frame）。数据不足 120 根时
    available=False（宁缺毋滥，不做短窗分类）。
    """
    close = frame["close"]
    if len(close) < 120:
        return {"available": False, "note_cn": "历史数据不足，暂不分类形态"}
    n = min(window, len(close))
    c = close.iloc[-n:]
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-n:]
    ema60 = close.ewm(span=60, adjust=False).mean().iloc[-n:]
    bull = ema20 > ema60
    ema_up = ema20.diff() > 0
    env_ok = float((bull & ema_up).mean())
    below = c < ema20 * 0.985
    breaks = int((below & ~below.shift(1, fill_value=False)).sum())
    touch = int(((c <= ema20 * 1.015) & (c >= ema20 * 0.985)).sum())
    ret = float(c.iloc[-1] / c.iloc[0] - 1)
    return {
        "available": True,
        "window": int(n),
        "env_ratio": round(env_ok, 3),
        "breaks_20": breaks,
        "touch_days": touch,
        "ret": round(ret, 4),
        "note_cn": "形态度量：环境占比=多头排列且20日线向上同时成立的天数占比；"
                   "破线次数=收盘有效跌破20日线（-1.5%以下）的次数",
    }


def classify_regime(metrics: dict[str, Any]) -> str | None:
    """形态分类（顺序：下跌 → 稳涨 → 急涨 → 震荡）。

    稳涨优先于急涨：通信一年 +62% 涨幅大但均线环境健康（env 66%、破线 11）
    → 稳涨；科创顶部前 +129% 但 env 54%、均线乱 → 急涨。急涨的本质特征
    是「涨幅巨大 + 环境撑不住稳涨标准」，而非单纯的破线次数。
    """
    if not metrics.get("available"):
        return None
    ret = metrics.get("ret") or 0.0
    env = metrics.get("env_ratio") or 0.0
    breaks = metrics.get("breaks_20") or 0
    if ret < _DOWNTREND:
        return "downtrend"
    if env >= _ENV_STEADY and breaks <= _BREAKS_STEADY:
        return "steady_uptrend"
    if ret > _FAST_RET:
        return "fast_uptrend"
    return "range"


def fit_advice(frame: pd.DataFrame) -> dict[str, Any] | None:
    """完整适配输出：形态度量 + 分类 + 打法建议 + 联动历史经验。

    讨论材料用（agent 链路）；None = 数据不足不做判断。
    """
    metrics = measure_regime(frame)
    regime = classify_regime(metrics)
    if regime is None:
        return metrics if isinstance(metrics, dict) else None
    out: dict[str, Any] = {
        **metrics,
        "regime": regime,
        "regime_cn": _REGIME_CN[regime],
        "fit_cn": _FIT_CN[regime],
        "note_cn": (
            "形态×打法适配：叙事层参考（涨法画像+历史经验），"
            "不参与技术判定、不改变买点资格"
        ),
    }
    query = _REGIME_QUERY.get(regime)
    if query:
        try:
            from lei_signal.copilot.experience import query_experience

            exp = query_experience(query, limit=2)
            out["experience"] = exp["items"] or None
        except Exception:  # noqa: BLE001  经验缺席不影响形态结论
            out["experience"] = None
    return out


__all__ = ["measure_regime", "classify_regime", "fit_advice"]
