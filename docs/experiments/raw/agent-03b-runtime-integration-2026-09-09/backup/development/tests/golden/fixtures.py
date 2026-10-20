"""黄金样例：人工构造并逐行核对的 OHLCV 序列。

这些序列不是随机数据，而是为了精确触发某一条规则而构造，
用于锁定公式行为。任何改动都必须先说明规则依据，不得为迎合结果调整。
"""
from __future__ import annotations

import pandas as pd


def _frame(rows: list[dict[str, float]], start: str = "2024-01-02") -> pd.DataFrame:
    """把 OHLCV 行构造成交易日索引（按工作日排列）的 DataFrame。"""
    index = pd.bdate_range(start=start, periods=len(rows))
    frame = pd.DataFrame(rows, index=index)
    frame.index.name = "date"
    return frame[["open", "high", "low", "close", "volume"]]


def golden_color_series() -> pd.DataFrame:
    """三色黄金样例。

    构造方式：前 21 根单调上行使 EMA20 与 close_lag20 均就绪，
    之后人工制造绿→灰→黑三段，便于逐日核对严格公式。
    """
    rows: list[dict[str, float]] = []
    # 0..20：从 10 缓慢上行到 20，使前 20 根为 unknown、第 21 根起就绪。
    for i in range(21):
        close = 10.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.3, "low": close - 0.4, "close": close,
             "volume": 1_000_000}
        )
    # 21..25：继续上行 -> 绿色（高于 EMA20 且高于 20 日前收盘）
    for i in range(5):
        close = 20.5 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.3, "low": close - 0.4, "close": close,
             "volume": 1_100_000}
        )
    # 26..33：横盘微跌，跌破 EMA20 但仍高于 20 日前收盘 -> 灰色
    for i in range(8):
        close = 22.0 - i * 0.35
        rows.append(
            {"open": close + 0.2, "high": close + 0.3, "low": close - 0.4, "close": close,
             "volume": 900_000}
        )
    # 34..45：深跌，同时低于 EMA20 与 20 日前收盘 -> 黑色
    for i in range(12):
        close = 19.0 - i * 0.6
        rows.append(
            {"open": close + 0.3, "high": close + 0.4, "low": close - 0.5, "close": close,
             "volume": 1_400_000}
        )
    return _frame(rows)


def golden_bullish_engulfing() -> pd.DataFrame:
    """阳线反包黄金样例，且长周期背景为空头。

    用于证明：反包在 EMA60 < EMA120 的环境中仍必须被记录，不得被 Block。
    索引 -1 为反包日，索引 -2 为其前一根阴线。
    """
    rows: list[dict[str, float]] = []
    # 长下跌段，确保 EMA60 < EMA120（需要 >120 根）
    for i in range(140):
        close = 100.0 - i * 0.4
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.5, "close": close,
             "volume": 1_000_000}
        )
    # 倒数第二根：阴线 close < open
    rows.append({"open": 46.0, "high": 46.2, "low": 43.5, "close": 44.0, "volume": 1_200_000})
    # 最后一根：阳线反包 —— open(43.9) <= 前收(44.0)，close(46.5) >= 前开(46.0)
    rows.append({"open": 43.9, "high": 46.8, "low": 43.6, "close": 46.5, "volume": 2_500_000})
    return _frame(rows, start="2023-01-02")


def golden_bullish_outside_reversal() -> pd.DataFrame:
    """阳线外包反转黄金样例。

    末根：Low <= 前 Low，Close >= 前 High，且 Close > Open。
    """
    rows: list[dict[str, float]] = []
    for i in range(30):
        close = 50.0 - i * 0.3
        rows.append(
            {"open": close + 0.2, "high": close + 0.4, "low": close - 0.4, "close": close,
             "volume": 1_000_000}
        )
    rows.append({"open": 41.5, "high": 42.0, "low": 40.0, "close": 40.5, "volume": 1_100_000})
    # 外包：low 39.5 <= 40.0；close 42.5 >= 42.0；close > open
    rows.append({"open": 40.0, "high": 42.8, "low": 39.5, "close": 42.5, "volume": 2_000_000})
    return _frame(rows, start="2024-01-02")


def golden_bottom_c_invalidation() -> pd.DataFrame:
    """底部 C 失效黄金样例。

    结构确认后先上涨，随后最低价跌破 C。用于证明：
    触及 C 后结构永久失效，且此后的上涨不能使其复活。
    """
    rows: list[dict[str, float]] = []
    # 下跌探底
    for i in range(25):
        close = 60.0 - i * 0.8
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.5, "close": close,
             "volume": 1_000_000}
        )
    # 第一低点区（C 区域），low 触及 39.0
    rows.append({"open": 40.5, "high": 41.0, "low": 39.0, "close": 40.0, "volume": 1_500_000})
    # 反弹形成颈线
    for i in range(6):
        close = 41.0 + i * 0.8
        rows.append(
            {"open": close - 0.3, "high": close + 0.6, "low": close - 0.5, "close": close,
             "volume": 1_200_000}
        )
    # 二次回落但高于第一低点 -> 高低点抬高
    for i in range(5):
        close = 45.0 - i * 0.7
        rows.append(
            {"open": close + 0.2, "high": close + 0.4, "low": close - 0.5, "close": close,
             "volume": 1_100_000}
        )
    # 突破颈线确认
    for i in range(8):
        close = 42.5 + i * 1.0
        rows.append(
            {"open": close - 0.4, "high": close + 0.7, "low": close - 0.6, "close": close,
             "volume": 1_800_000}
        )
    # 崩跌，最低价跌破 C=39.0
    for i in range(10):
        close = 49.0 - i * 1.3
        rows.append(
            {"open": close + 0.5, "high": close + 0.6, "low": close - 1.0, "close": close,
             "volume": 2_200_000}
        )
    # 此后强力反弹：不得复活已失效结构
    for i in range(10):
        close = 37.0 + i * 1.5
        rows.append(
            {"open": close - 0.5, "high": close + 0.8, "low": close - 0.7, "close": close,
             "volume": 2_000_000}
        )
    return _frame(rows, start="2024-01-02")


def golden_delayed_upgrade() -> pd.DataFrame:
    """状态延迟升级黄金样例（对应架构第 15 节的漏信号案例）。

    结构：
      1) 前段长期下跌，使 EMA60 < EMA120（长周期冲突）；
      2) 中段出现反包 + EMA20 重新站上且向上（短期转强，但长周期仍冲突）；
      3) 后段长期上行，使 EMA60 与 EMA120 关系改善；
         此时不再出现新的 EMA20 交叉。
    预期：状态在后段仍能升级为趋势增强。
    """
    rows: list[dict[str, float]] = []
    # 1) 下跌段 160 根，EMA60 明显低于 EMA120
    for i in range(160):
        close = 200.0 - i * 0.75
        rows.append(
            {"open": close + 0.4, "high": close + 0.6, "low": close - 0.6, "close": close,
             "volume": 1_000_000}
        )
    # 2) 反包日：制造阴线后阳线反包
    rows.append({"open": 81.0, "high": 81.3, "low": 78.0, "close": 78.5, "volume": 1_300_000})
    rows.append({"open": 78.2, "high": 82.5, "low": 78.0, "close": 82.0, "volume": 2_600_000})
    # 3) 持续温和上行：颜色转绿、双均线共同向上，长周期逐步改善，
    #    且不再产生新的 EMA20 下穿再上穿。
    for i in range(120):
        close = 82.5 + i * 0.85
        rows.append(
            {"open": close - 0.35, "high": close + 0.55, "low": close - 0.5, "close": close,
             "volume": 1_500_000}
        )
    return _frame(rows, start="2022-01-03")


def golden_top_then_black() -> pd.DataFrame:
    """顶部结构 + 转黑样例，用于 Top+Black 与新高解除测试。

    先形成两个递减确认高点并跌破颈线（顶部确认），随后转黑。
    """
    rows: list[dict[str, float]] = []
    for i in range(30):
        close = 50.0 + i * 1.0
        rows.append(
            {"open": close - 0.4, "high": close + 0.6, "low": close - 0.5, "close": close,
             "volume": 1_000_000}
        )
    # 第一高点 ~82
    rows.append({"open": 80.0, "high": 82.0, "low": 79.5, "close": 81.0, "volume": 1_600_000})
    # 回落形成颈线 ~72
    for i in range(6):
        close = 79.0 - i * 1.3
        rows.append(
            {"open": close + 0.4, "high": close + 0.5, "low": close - 0.8, "close": close,
             "volume": 1_200_000}
        )
    # 第二高点 ~78（低于第一高点）
    for i in range(5):
        close = 72.0 + i * 1.2
        rows.append(
            {"open": close - 0.3, "high": close + 0.7, "low": close - 0.4, "close": close,
             "volume": 1_300_000}
        )
    # 跌破颈线确认顶部，并继续下跌至转黑
    for i in range(25):
        close = 76.0 - i * 1.4
        rows.append(
            {"open": close + 0.5, "high": close + 0.6, "low": close - 0.9, "close": close,
             "volume": 1_900_000}
        )
    return _frame(rows, start="2024-01-02")


__all__ = [
    "golden_bottom_c_invalidation",
    "golden_bullish_engulfing",
    "golden_bullish_outside_reversal",
    "golden_color_series",
    "golden_delayed_upgrade",
    "golden_top_then_black",
]
