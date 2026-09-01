"""时钟五类趋势分类（规格 §4.4 / 手册 2.4，V2.1 标定，§15 第一轮落地）。

用 SMA60 的 60 交易日年化对数斜率 s60 把趋势分五类（s20 同理 20 日窗）：

- 一类（1→12 点，斜率加速上涨）：s60 > 100%，或 s20 ≥ 2×s60 且 s60 > 40%
  （后者捕捉「斜率正在陡峭化」）；
- 二类（2:30→1 点，稳定上涨，模块 A 主战场）：10% ≤ s60 ≤ 100%（非一类）；
- 三类（2:30→3:30，横盘）：|s60| < 10%（模块 B 环境须叠加密集两条件）；
- 四类（3:30→5 点，稳定下跌）：二类负值镜像；
- 五类（5→6 点，加速下跌）：一类负值镜像。

角度（30°≈2 点半、75°≈12 点半）只是视觉语言，不做严格换算；分箱边界全部
读自账本 ``clock_classifier``（〔标定 V2.1，待彪哥确认〕，敏感性 ×0.5/×2）。

严格前向：斜率只用当日及此前已完成日 K（滚动窗口因果）；数据不足（均线
或窗口未走满）返回 0 = insufficient。本模块与 tradability_gate 一样不向
主事件日志写每日事件（会产生海量事件），由回测与界面按需读取。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import RuleSpec, get_rule

RULE_ID = "clock_classifier"

TYPE_INSUFFICIENT = 0
TYPE1_ACCELERATING_UP = 1
TYPE2_STEADY_UP = 2
TYPE3_SIDEWAYS = 3
TYPE4_STEADY_DOWN = 4
TYPE5_ACCELERATING_DOWN = 5

CLOCK_TYPE_CN: dict[int, str] = {
    TYPE_INSUFFICIENT: "数据不足",
    TYPE1_ACCELERATING_UP: "一类（1→12点：斜率加速上涨）",
    TYPE2_STEADY_UP: "二类（2:30→1点：稳定上涨·主战场）",
    TYPE3_SIDEWAYS: "三类（2:30→3:30：横向整理）",
    TYPE4_STEADY_DOWN: "四类（3:30→5点：稳定下跌）",
    TYPE5_ACCELERATING_DOWN: "五类（5→6点：斜率加速下跌）",
}


def _params(spec: RuleSpec) -> dict[str, float | int]:
    return {
        "window": int(spec.param("window", 60)),
        "window_s20": int(spec.param("window_s20", 20)),
        "annualization": float(spec.param("annualization", 252)),
        "type3_max_abs_s60": float(spec.param("type3_max_abs_s60", 0.10)),
        "type2_min_s60": float(spec.param("type2_min_s60", 0.10)),
        "type1_min_s60": float(spec.param("type1_min_s60", 1.00)),
        "type1_s20_multiple": float(spec.param("type1_s20_multiple", 2.0)),
        "type1_s60_floor": float(spec.param("type1_s60_floor", 0.40)),
    }


def slope_series(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """s60 / s20：SMA 均线的年化对数斜率（对数坐标 + 固定时长，手册 2.4）。"""
    params = _params(get_rule(RULE_ID))
    sma60 = frame["sma60"].astype(float)
    sma20 = frame["sma20"].astype(float)
    window = int(params["window"])
    window_s20 = int(params["window_s20"])
    annualization = float(params["annualization"])
    s60 = (np.log(sma60 / sma60.shift(window)) / window * annualization).rename("s60")
    s20 = (np.log(sma20 / sma20.shift(window_s20)) / window_s20 * annualization).rename("s20")
    return s60, s20


def _classify_values(s60: pd.Series, s20: pd.Series) -> np.ndarray:
    params = _params(get_rule(RULE_ID))
    t1_min = float(params["type1_min_s60"])
    t1_mult = float(params["type1_s20_multiple"])
    t1_floor = float(params["type1_s60_floor"])
    t2_min = float(params["type2_min_s60"])

    a, b = s60.to_numpy(dtype=float), s20.to_numpy(dtype=float)
    result = np.full(len(a), TYPE_INSUFFICIENT, dtype=int)
    valid = ~np.isnan(a)
    # 一类优先于二类：加速分支（s20 >= 2 x s60 且 s60 > 40%）在 s60 仍处
    # 二类区间时即判一类（规格 §4.4 回测代理的分箱次序）。NaN 参与 >=
    # 比较结果为 False，天然排除数据不足情形。
    type1 = valid & ((a > t1_min) | ((b >= t1_mult * a) & (a > t1_floor)))
    type5 = valid & ((a < -t1_min) | ((b <= t1_mult * a) & (a < -t1_floor)))
    type2 = valid & ~type1 & (a >= t2_min)
    type4 = valid & ~type5 & (a <= -t2_min)
    type3 = valid & ~type1 & ~type5 & ~type2 & ~type4
    result[type1] = TYPE1_ACCELERATING_UP
    result[type5] = TYPE5_ACCELERATING_DOWN
    result[type2] = TYPE2_STEADY_UP
    result[type4] = TYPE4_STEADY_DOWN
    result[type3] = TYPE3_SIDEWAYS
    return result


def clock_series(frame: pd.DataFrame) -> pd.Series:
    """整段日线的时钟五类序列（int 0..5，0 = 数据不足）。"""
    if frame.empty or "sma60" not in frame.columns or "sma20" not in frame.columns:
        return pd.Series(TYPE_INSUFFICIENT, index=frame.index, name="clock_type", dtype=int)
    s60, s20 = slope_series(frame)
    return pd.Series(_classify_values(s60, s20), index=frame.index, name="clock_type")


def classify_clock(frame: pd.DataFrame, position: int) -> int:
    """单日分类（与 tradability_gate.classify_trend_type 同风格的入口）。"""
    if frame.empty or not 0 <= position < len(frame):
        return TYPE_INSUFFICIENT
    s60, s20 = slope_series(frame)
    values = _classify_values(s60, s20)
    return int(values[position])


def is_entry_allowed(clock_type: int) -> bool:
    """多头新开仓是否允许：仅二类（主战场）。

    规格表 4.4：一类无持仓不参与；三类只做埋伏与假突破反转（模块 B/D）；
    四/五类为空头侧。模块 A 的 A1 门禁 = 本函数为真。
    """
    return clock_type == TYPE2_STEADY_UP


__all__ = [
    "CLOCK_TYPE_CN",
    "RULE_ID",
    "TYPE1_ACCELERATING_UP",
    "TYPE2_STEADY_UP",
    "TYPE3_SIDEWAYS",
    "TYPE4_STEADY_DOWN",
    "TYPE5_ACCELERATING_DOWN",
    "TYPE_INSUFFICIENT",
    "classify_clock",
    "clock_series",
    "is_entry_allowed",
    "slope_series",
]
