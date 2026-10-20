"""可交易性门禁与趋势类型分类（规格第 13 节 + 第 2.2 节，研究代理）。

横切层：用均线纠缠度 + ATR 分位 + 斜率把行情分成
横盘反复 / 横盘末期 / 趋势 / 加速衰竭，并逐条落地规格第 13 节的 9 条无交易条件，
输出"可交易性"状态 + 阻断原因清单。只算展示、不做硬拦截（与盈亏比一致的"只算不强制"口径）。

严格前向：分类与门禁只依赖当日及此前已完成日 K，追加未来行情不改变历史结论。
本模块不向主事件日志写每日事件（会产生海量事件），而是由回测与界面按需读取当前状态。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from lei_signal.domain.rules_config import RuleSpec, get_rule

RULE_ID = "tradability_gate"

# 趋势类型
INSUFFICIENT_DATA = "insufficient_data"
EXHAUSTION = "exhaustion"
LATE_CONSOLIDATION = "late_consolidation"
RANGING = "ranging"
TRENDING = "trending"
UNCLEAR = "unclear"

TREND_TYPE_CN: dict[str, str] = {
    INSUFFICIENT_DATA: "数据不足",
    EXHAUSTION: "加速衰竭",
    LATE_CONSOLIDATION: "横盘末期",
    RANGING: "横盘反复",
    TRENDING: "趋势",
    UNCLEAR: "趋势类型不明",
}

# 9 条无交易条件 code
C_TREND_UNCLEAR = "trend_type_unclear"
C_MODULE_UNCLEAR = "module_unclear"
C_ENTRY_UNDEFINED = "entry_target_stop_undefined"
C_RR_BELOW_3 = "rr_below_3"
C_RANGING_NO_ACTION = "ranging_no_action"
C_EXHAUSTION_NO_POSITION = "exhaustion_no_position"
C_MULTI_PERIOD_MESSY = "multi_period_messy"
C_INSUFFICIENT_DATA = "insufficient_data"
C_DEPENDS_ON_FUTURE = "depends_on_future"

CONDITION_LABEL_CN: dict[str, str] = {
    C_TREND_UNCLEAR: "1.无法明确当前趋势类型",
    C_MODULE_UNCLEAR: "2.交易模块不明确",
    C_ENTRY_UNDEFINED: "3.入场/目标/失效不能定义",
    C_RR_BELOW_3: "4.盈亏比<3（只算不强制）",
    C_RANGING_NO_ACTION: "5.横盘反复且无标志性动作",
    C_EXHAUSTION_NO_POSITION: "6.极端加速无持仓",
    C_MULTI_PERIOD_MESSY: "7.多周期杂乱",
    C_INSUFFICIENT_DATA: "8.数据不足",
    C_DEPENDS_ON_FUTURE: "9.依赖未来K线",
}

#: 环境层阻断条件（入场时条件 2/3/4 与结构性条件 9 不在环境层阻断）
ENV_BLOCKING_CODES = {
    C_TREND_UNCLEAR,
    C_RANGING_NO_ACTION,
    C_EXHAUSTION_NO_POSITION,
    C_MULTI_PERIOD_MESSY,
    C_INSUFFICIENT_DATA,
}


@dataclass(frozen=True, slots=True)
class ConditionCheck:
    code: str
    label_cn: str
    blocked: bool
    detail_cn: str


@dataclass(frozen=True, slots=True)
class TradabilityResult:
    trend_type: str
    trend_type_cn: str
    tradable: bool
    blocking_reasons: list[str] = field(default_factory=list)
    condition_checks: list[ConditionCheck] = field(default_factory=list)


def _params(spec: RuleSpec) -> tuple[int, float, int, float, float, int, int, int, int, float]:
    return (
        int(spec.param("minimum_consolidation_bars", 126)),
        float(spec.param("cluster_threshold", 0.02)),
        int(spec.param("entanglement_lookback", 20)),
        float(spec.param("acceleration_slope_pct", 0.03)),
        float(spec.param("bias_extreme", 0.50)),
        int(spec.param("atr_percentile_window", 120)),
        int(spec.param("messy_color_flip_lookback", 20)),
        int(spec.param("messy_color_flip_threshold", 4)),
        int(spec.param("signature_action_lookback", 10)),
        float(spec.param("signature_volume_ratio", 1.5)),
    )


_LINE_COLS = ("sma20", "sma60", "sma120", "ema20", "ema60", "ema120")


def _entanglement_series(frame: pd.DataFrame) -> pd.Series:
    high = frame[list(_LINE_COLS)].max(axis=1)
    low = frame[list(_LINE_COLS)].min(axis=1)
    return (high - low) / frame["close"]


def _atr_percentile(frame: pd.DataFrame, position: int, window: int) -> float | None:
    """当前 ATR/close 在过去 window 根中的分位（0..1），低=压缩。"""
    if "atr14" not in frame.columns or "close" not in frame.columns:
        return None
    start = max(0, position - window + 1)
    seg = frame.iloc[start: position + 1]
    atr_pct = seg["atr14"].astype(float) / seg["close"].astype(float)
    atr_pct = atr_pct.dropna()
    if len(atr_pct) < 2:
        return None
    current = float(atr_pct.iloc[-1])
    return float((atr_pct <= current).sum() / len(atr_pct))


def _color_flips(frame: pd.DataFrame, position: int, lookback: int) -> int:
    if "signal_color" not in frame.columns:
        return 0
    start = max(0, position - lookback + 1)
    colors = frame["signal_color"].astype(str).iloc[start: position + 1]
    if len(colors) < 2:
        return 0
    return int((colors.values[:-1] != colors.values[1:]).sum())


def _has_signature_action(
    frame: pd.DataFrame, position: int, lookback: int, volume_ratio: float
) -> bool:
    if "volume_ratio20" not in frame.columns:
        return False
    start = max(0, position - lookback + 1)
    seg = frame["volume_ratio20"].astype(float).iloc[start: position + 1].dropna()
    if seg.empty:
        return False
    return bool((seg >= volume_ratio).any())


def classify_trend_type(frame: pd.DataFrame, position: int) -> str:
    """对 position 当日分类趋势类型。只依赖当日及此前数据。"""
    spec = get_rule(RULE_ID)
    (
        min_bars,
        cluster_threshold,
        ent_lookback,
        accel_slope,
        bias_extreme,
        _atr_window,
        _flip_lookback,
        _flip_threshold,
        _sig_lookback,
        _sig_vol,
    ) = _params(spec)

    if position < min_bars:
        return INSUFFICIENT_DATA
    row = frame.iloc[position]
    if not all(pd.notna(row.get(col)) for col in _LINE_COLS + ("close", "atr14", "ema20_slope")):
        return INSUFFICIENT_DATA

    lines = [float(row[col]) for col in _LINE_COLS]
    close = float(row["close"])
    ema20 = float(row["ema20"])
    ema120 = float(row["ema120"])
    ema20_slope_pct = float(row["ema20_slope"]) / ema20 if ema20 else 0.0
    bias_ema120 = close / ema120 - 1.0
    entanglement = (max(lines) - min(lines)) / close

    # 加速衰竭：强加速 + 极端乖离
    if ema20_slope_pct >= accel_slope and bias_ema120 >= bias_extreme:
        return EXHAUSTION

    # 横盘：纠缠度低且持续
    start = max(0, position - ent_lookback + 1)
    ent_seg = _entanglement_series(frame).iloc[start: position + 1].dropna()
    consolidating = bool(
        entanglement <= cluster_threshold
        and not ent_seg.empty
        and float(ent_seg.mean()) <= cluster_threshold * 1.5
    )
    if consolidating:
        atr_pct = _atr_percentile(frame, position, _atr_window)
        if atr_pct is not None and atr_pct <= 0.25:
            return LATE_CONSOLIDATION
        return RANGING

    # 趋势：完整排列 + 方向一致
    bull_align = lines[0] > lines[1] > lines[2] and lines[3] > lines[4] > lines[5]
    bear_align = lines[0] < lines[1] < lines[2] and lines[3] < lines[4] < lines[5]
    if (bull_align or bear_align) and abs(ema20_slope_pct) >= 1e-6:
        return TRENDING

    return UNCLEAR


def evaluate_tradability(frame: pd.DataFrame, position: int) -> TradabilityResult:
    """评估可交易性 + 9 条无交易条件。只依赖当日及此前数据。"""
    spec = get_rule(RULE_ID)
    (
        min_bars,
        _cluster_threshold,
        _ent_lookback,
        _accel_slope,
        _bias_extreme,
        _atr_window,
        flip_lookback,
        flip_threshold,
        sig_lookback,
        sig_vol,
    ) = _params(spec)

    trend_type = classify_trend_type(frame, position)
    insufficient = trend_type == INSUFFICIENT_DATA or position < min_bars
    flips = _color_flips(frame, position, flip_lookback)
    messy = flips >= flip_threshold
    has_action = _has_signature_action(frame, position, sig_lookback, sig_vol)

    checks: list[ConditionCheck] = [
        ConditionCheck(
            C_TREND_UNCLEAR, CONDITION_LABEL_CN[C_TREND_UNCLEAR],
            trend_type in (UNCLEAR, INSUFFICIENT_DATA),
            f"当前趋势类型={TREND_TYPE_CN[trend_type]}",
        ),
        ConditionCheck(
            C_MODULE_UNCLEAR, CONDITION_LABEL_CN[C_MODULE_UNCLEAR], False,
            "环境层不判，需结合入场信号确定交易模块（A/B/C/D）",
        ),
        ConditionCheck(
            C_ENTRY_UNDEFINED, CONDITION_LABEL_CN[C_ENTRY_UNDEFINED], False,
            "环境层不判，入场前需明确入场依据/目标B/失效位",
        ),
        ConditionCheck(
            C_RR_BELOW_3, CONDITION_LABEL_CN[C_RR_BELOW_3], False,
            "只算不强制：入场时按 R/R 标注，<3 仅提示不拦截",
        ),
        ConditionCheck(
            C_RANGING_NO_ACTION, CONDITION_LABEL_CN[C_RANGING_NO_ACTION],
            trend_type == RANGING and not has_action,
            "横盘反复" + ("且近期无放量标志性动作" if not has_action else "但近期有放量标志性动作"),
        ),
        ConditionCheck(
            C_EXHAUSTION_NO_POSITION, CONDITION_LABEL_CN[C_EXHAUSTION_NO_POSITION],
            trend_type == EXHAUSTION,
            "极端加速阶段，无既有持仓则不开新仓",
        ),
        ConditionCheck(
            C_MULTI_PERIOD_MESSY, CONDITION_LABEL_CN[C_MULTI_PERIOD_MESSY], messy,
            f"近{flip_lookback}日颜色翻转{flips}次" + ("（杂乱）" if messy else ""),
        ),
        ConditionCheck(
            C_INSUFFICIENT_DATA, CONDITION_LABEL_CN[C_INSUFFICIENT_DATA], insufficient,
            f"position={position}，需≥{min_bars}根且均线齐全",
        ),
        ConditionCheck(
            C_DEPENDS_ON_FUTURE, CONDITION_LABEL_CN[C_DEPENDS_ON_FUTURE], False,
            "系统严格前向，信号不依赖未完成K线",
        ),
    ]

    blocking = [c.label_cn for c in checks if c.blocked and c.code in ENV_BLOCKING_CODES]
    tradable = len(blocking) == 0
    return TradabilityResult(
        trend_type=trend_type,
        trend_type_cn=TREND_TYPE_CN[trend_type],
        tradable=tradable,
        blocking_reasons=blocking,
        condition_checks=checks,
    )


__all__ = [
    "C_DEPENDS_ON_FUTURE",
    "C_ENTRY_UNDEFINED",
    "C_EXHAUSTION_NO_POSITION",
    "C_INSUFFICIENT_DATA",
    "C_MODULE_UNCLEAR",
    "C_MULTI_PERIOD_MESSY",
    "C_RANGING_NO_ACTION",
    "C_RR_BELOW_3",
    "C_TREND_UNCLEAR",
    "CONDITION_LABEL_CN",
    "ENV_BLOCKING_CODES",
    "EXHAUSTION",
    "INSUFFICIENT_DATA",
    "LATE_CONSOLIDATION",
    "RANGING",
    "RULE_ID",
    "TREND_TYPE_CN",
    "TRENDING",
    "TradabilityResult",
    "UNCLEAR",
    "ConditionCheck",
    "classify_trend_type",
    "evaluate_tradability",
]
