"""趋势五步状态机（规格 §5 / 手册 4.6、视频 18，账本 trend_stage v2.0.0）。

以下降转上升为例的五步（规格原文），本系统仅做多（账本 direction 拍板），
故只实装多头侧；上升转下降为镜像，不在此实现：

1 破线：close > EMA20；
2 拐头：EMA20 上行（ema20_slope > 0，EMA 预警）且 SMA20 抵扣价判据
   close > close_lag20（SMA 确认，规格 §4.2）--两线不一致时不视为最强确认；
3 交叉：SMA20 > SMA60（口径写死：确认线跨期交叉，与模块 A 的 SMA 体系
   一致；EMA20 > SMA60 仅作敏感性对照口径 cross_basis="ema"，不进默认公式）；
4 排列：20/60/120 双组多头排列（EMA20>EMA60>EMA120 且 SMA20>SMA60>SMA120）；
5 大幅乖离：bias_ema120 = close/EMA120 − 1 >= 账本 tradability_gate.bias_extreme
   （规格 §17 已定（原则）50%）。

trend_stage(t) = 逐日满足 1..k 全部条件的最大 k（累进合取）：
- 破线失败 -> 0；拐头失败但破线仍成立 -> 1（「破线/拐头失败即降级」）；
- 0 = 未起步 / 数据不足（均线未预热时全部条件为假，自然为 0）。

核心思想「先胜而后战」（手册 4.6）：转折没走完就不能确认转折。与
interpreter 的底部生命周期 stage 是两套维度，不合并（账本 note 已写明）。
不灌 live 事件日志（与 strict_structure / reward_risk_filter 同纪律），
供回测分组（规格 §16）与 API 按需读取。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.rules_config import get_rule

RULE_ID = "trend_stage"

#: 交叉口径：默认确认线 SMA20>SMA60；"ema" = EMA20>SMA60（敏感性对照）。
CROSS_BASES = ("sma", "ema")

_REQUIRED_COLUMNS = (
    "close",
    "ema20",
    "ema60",
    "ema120",
    "sma20",
    "sma60",
    "sma120",
    "close_lag20",
    "ema20_slope",
)


def trend_stage_series(frame: pd.DataFrame, *, cross_basis: str = "sma") -> pd.Series:
    """逐日趋势五步状态（int8 0..5），多头侧；列缺失或数据不足时恒 0。"""
    if cross_basis not in CROSS_BASES:
        raise ValueError(f"未知交叉口径: {cross_basis}（可选 {CROSS_BASES}）")
    # 触发账本校验：规则未登记即报错，不静默使用默认值。
    get_rule(RULE_ID)

    if frame.empty or not set(_REQUIRED_COLUMNS).issubset(frame.columns):
        return pd.Series(0, index=frame.index, dtype="int8")

    close = frame["close"].astype(float)
    # NaN 参与比较按 False 处理（pandas 语义），预热期条件不成立 -> stage 0。
    cond_break = close > frame["ema20"]                                   # 1 破线
    cond_turn = (frame["ema20_slope"] > 0) & (close > frame["close_lag20"])  # 2 拐头
    if cross_basis == "ema":
        cond_cross = frame["ema20"] > frame["sma60"]                      # 3 交叉（对照口径）
    else:
        cond_cross = frame["sma20"] > frame["sma60"]                      # 3 交叉（默认口径）
    cond_align = (
        (frame["ema20"] > frame["ema60"])
        & (frame["ema60"] > frame["ema120"])
        & (frame["sma20"] > frame["sma60"])
        & (frame["sma60"] > frame["sma120"])
    )                                                                     # 4 双组排列
    bias_extreme = float(get_rule("tradability_gate").param("bias_extreme", 0.5))
    cond_bias = (close / frame["ema120"] - 1.0) >= bias_extreme           # 5 大幅乖离

    # 累进合取：step_k 计数当且仅当 1..k 全部成立（可回退）。
    c1 = cond_break.fillna(False)
    c2 = c1 & cond_turn.fillna(False)
    c3 = c2 & cond_cross.fillna(False)
    c4 = c3 & cond_align.fillna(False)
    c5 = c4 & cond_bias.fillna(False)
    stage = (
        c1.astype("int8")
        + c2.astype("int8")
        + c3.astype("int8")
        + c4.astype("int8")
        + c5.astype("int8")
    )
    return stage

__all__ = ["CROSS_BASES", "RULE_ID", "trend_stage_series"]
