"""MACD 强度解读（研究代理）：把 MACD 当强度/乖离读，不当转折。

趋势转折 5 步骤中，MACD 只能表达「交叉」与「多头排列+乖离率」；
「破线」与「均线拐头」由系统既有的 LEI 颜色与均线斜率补齐。
不产生交易事件：金叉/死叉只是强度描述，不构成买点。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

#: 盲区固定文案：明示 MACD 看不到的两步，指向系统既有补齐来源。
#: 这条文案会随 MACD Factor 一起进入 supports/conflicts，让"补齐"始终可见。
BLIND_SPOT_CN = (
    "MACD 仅表达交叉与多头排列乖离（强度）；"
    "破线见 LEI 颜色（close vs EMA20），均线拐头见均线斜率（ema20_slope 等）"
)

StrengthStatus = Literal[
    "多头扩散",
    "多头收敛",
    "空头扩散",
    "空头收敛",
    "金叉",
    "死叉",
    "数据不足",
]


@dataclass(frozen=True, slots=True)
class MacdStrengthReading:
    """MACD 强度解读结果。只描述强度，不构成买卖依据。"""

    status: StrengthStatus
    dif: float
    dea: float
    hist: float
    prev_hist: float | None
    cross: Literal["金叉", "死叉", "无"]
    dimension_value: Literal["支持", "冲突", "中性"]
    label_cn: str
    detail_cn: str
    blind_spot_cn: str = BLIND_SPOT_CN


def read_macd_strength(
    row: pd.Series, prev_row: pd.Series | None
) -> MacdStrengthReading | None:
    """读当日 MACD 强度。

    row      当日 frame 行（含 ``macd_dif`` / ``macd_dea`` / ``macd_hist``）
    prev_row 前一日行（用于交叉与扩散/收敛判定）；None 时只给静态强度

    DIF/DEA/hist 缺失或 NaN（含前导 warmup 段）返回 None。
    """
    dif = row.get("macd_dif")
    dea = row.get("macd_dea")
    hist = row.get("macd_hist")
    if dif is None or dea is None or hist is None:
        return None
    if pd.isna(dif) or pd.isna(dea) or pd.isna(hist):
        return None

    dif_f, dea_f, hist_f = float(dif), float(dea), float(hist)

    # 前一日柱体（用于扩散/密集判定）
    prev_hist: float | None = None
    if prev_row is not None:
        ph = prev_row.get("macd_hist")
        if ph is not None and not pd.isna(ph):
            prev_hist = float(ph)

    # 交叉：DIF 与 DEA 上下穿（MACD 能表达的「交叉」，强度转向信号）
    cross: Literal["金叉", "死叉", "无"] = "无"
    if prev_row is not None:
        prev_dif = prev_row.get("macd_dif")
        prev_dea = prev_row.get("macd_dea")
        if (
            prev_dif is not None
            and prev_dea is not None
            and not pd.isna(prev_dif)
            and not pd.isna(prev_dea)
        ):
            prev_dif_f, prev_dea_f = float(prev_dif), float(prev_dea)
            if prev_dif_f <= prev_dea_f and dif_f > dea_f:
                cross = "金叉"
            elif prev_dif_f >= prev_dea_f and dif_f < dea_f:
                cross = "死叉"

    # 扩散/密集：hist 同号且幅度变化（MACD 能表达的「乖离扩散/密集」）
    # hist 翻号已被 cross 捕获，故此处只处理同号情形。
    contracting = (
        prev_hist is not None and hist_f * prev_hist > 0 and abs(hist_f) < abs(prev_hist)
    )

    bullish = dif_f > 0  # 多头排列乖离方向

    if cross == "金叉":
        status: StrengthStatus = "金叉"
        dimension_value: Literal["支持", "冲突", "中性"] = "支持"
    elif cross == "死叉":
        status = "死叉"
        dimension_value = "冲突"
    elif bullish:
        status = "多头收敛" if contracting else "多头扩散"
        dimension_value = "中性" if contracting else "支持"
    else:
        status = "空头收敛" if contracting else "空头扩散"
        dimension_value = "中性" if contracting else "冲突"

    label_cn = f"MACD {status}（研究代理）"

    parts: list[str] = [f"DIF={dif_f:.4f}，DEA={dea_f:.4f}，柱={hist_f:.4f}"]
    if cross != "无":
        parts.append(f"当日{cross}（DIF 穿越 DEA，强度转向信号）")
    elif prev_hist is not None:
        if hist_f * prev_hist > 0 and abs(hist_f) > abs(prev_hist):
            parts.append("柱体放大（乖离扩散）")
        elif contracting:
            parts.append("柱体收缩（乖离密集）")
    parts.append("多头排列乖离" if bullish else "空头排列乖离")
    detail_cn = "；".join(parts)

    return MacdStrengthReading(
        status=status,
        dif=dif_f,
        dea=dea_f,
        hist=hist_f,
        prev_hist=prev_hist,
        cross=cross,
        dimension_value=dimension_value,
        label_cn=label_cn,
        detail_cn=detail_cn,
    )


__all__ = ["BLIND_SPOT_CN", "MacdStrengthReading", "read_macd_strength"]
