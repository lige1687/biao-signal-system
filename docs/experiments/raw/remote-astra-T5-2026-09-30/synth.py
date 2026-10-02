"""T5 人工合成报价与公共工具（人工合成，不是任何真实品种的行情）。

所有序列都由本文件确定性生成；同一参数每次生成完全相同的数据。
不联网、不读本机数据库/接口。SQLite 只写调用方给出的 /tmp 临时路径。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars

SYNTH_LABEL = "人工合成（T5 反例，非真实行情）"
START = "2024-01-02"


def to_bars(rows: list[dict], start: str = START) -> pd.DataFrame:
    index = pd.bdate_range(start=start, periods=len(rows))
    frame = pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]
    frame.index.name = "date"
    return frame


def base_rows(
    *,
    confirm_close: float = 74.4,
    confirm_low: float = 72.1,
    confirm_vol: float = 3_500_000.0,
    inval_low: float = 68.6,
    climb: float = 0.15,
    right_side: tuple[float, float, float] = (70.9, 71.6, 72.2),
) -> list[dict]:
    """“两次探底 + 放量突破颈线 + 后来跌回 C + 回升”的固定序列（91 根）。

    关键位置（下标 / 2024 日期）：
      50 = 第一低点 L1（最低 68.8，即两种底部的 C）；58 = 第二低点 L2（69.4）；
      61 = L2 三左三右确认日（结构候选日）；62 = 突破日（收盘>颈线 73.5，放量 3.5 倍）；
      80 = 最低价回到 C 以下（inval_low），随后 81-90 回升。
    """
    rows: list[dict] = []
    for i in range(50):
        c = 100 - 0.6 * i
        rows.append(dict(open=c + 0.2, high=c + 0.5, low=c - 0.5, close=c, volume=1e6))
    rows.append(dict(open=70.4, high=70.6, low=68.8, close=69.6, volume=1e6))  # 50
    for c in (70.5, 71.3, 72.0, 72.6, 73.0):  # 51-55
        rows.append(dict(open=c - 0.4, high=c + 0.5, low=c - 0.6, close=c, volume=1e6))
    for c in (72.0, 71.0):  # 56-57
        rows.append(dict(open=c + 0.4, high=c + 0.5, low=c - 0.6, close=c, volume=1e6))
    rows.append(dict(open=70.8, high=71.0, low=69.4, close=70.2, volume=1e6))  # 58
    for c in right_side:  # 59-61
        rows.append(dict(open=c - 0.3, high=c + 0.5, low=c - 0.6, close=c, volume=1e6))
    rows.append(dict(open=72.4, high=74.6, low=confirm_low, close=confirm_close,
                     volume=confirm_vol))  # 62
    c = confirm_close
    for _ in range(12):  # 63-74
        c = round(c + climb, 4)
        rows.append(dict(open=c - 0.1, high=c + 0.4, low=c - 0.4, close=c, volume=1e6))
    for _ in range(5):  # 75-79
        c = round(c - 1.0, 4)
        rows.append(dict(open=c + 0.6, high=c + 0.8, low=c - 0.3, close=c, volume=1e6))
    c80 = round(c - 1.0, 4)
    close80 = max(c80, inval_low)
    high80 = max(c80 + 0.8, close80 + 0.2)
    rows.append(dict(open=min(max(c80 + 0.6, inval_low), high80), high=high80,
                     low=inval_low, close=close80, volume=1e6))  # 80
    c = rows[-1]["close"]
    for _ in range(10):  # 81-90
        c = round(c + 0.5, 4)
        rows.append(dict(open=c - 0.3, high=c + 0.4, low=c - 0.5, close=c, volume=1e6))
    return rows


def random_series(seed: int, drift: np.ndarray, vol: np.ndarray,
                  start: str = "2020-01-06") -> pd.DataFrame:
    """人工合成随机行情：对数收益正态，振幅与波动同量级，6% 的日子量能放大 3 倍。"""
    rng = np.random.default_rng(seed)
    n = len(drift)
    close = 100 * np.exp(np.cumsum(rng.normal(drift / 100, vol)))
    high = close * (1 + rng.uniform(0.1, 1.0, n) * vol)
    low = close * (1 - rng.uniform(0.1, 1.0, n) * vol)
    op = np.clip(close * (1 + rng.normal(0, 0.3, n) * vol), low, high)
    volume = rng.uniform(1e6, 2e6, n)
    volume[rng.random(n) < 0.06] *= 3.0
    frame = pd.DataFrame(dict(open=op, high=high, low=low, close=close, volume=volume),
                         index=pd.bdate_range(start, periods=n))
    frame.index.name = "date"
    return frame


@dataclass
class MemoryProvider:
    """内存行情源（隔离替身）：只把给定 DataFrame 经真实 validate_bars 包成 PriceData。"""

    bars: pd.DataFrame
    name: str = "synthetic_t5"

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        clean, report = validate_bars(self.bars, symbol=info.symbol, provider=self.name,
                                      adjusted=True, min_rows=min_rows)
        return PriceData(symbol=info.symbol, display_name=info.symbol, bars=clean,
                         report=report, info=info)


def ev(e) -> dict:
    """事件摘要（输出用）。"""
    return {
        "event_id": e.event_id[:16], "rule_id": e.rule_id,
        "sub_rule": e.evidence.get("sub_rule"), "event_date": str(e.event_date),
        "available_date": str(e.available_date),
        "structure_id": (e.structure_id or "")[:16] or None,
    }


def st(s) -> dict:
    return {
        "structure_id": s.structure_id[:16], "type": s.structure_type, "side": s.side,
        "detected": str(s.detected_date), "confirmed": str(s.confirmed_date),
        "invalidated": str(s.invalidated_date), "status": s.status.value,
        "c_price": s.c_price, "neckline": s.neckline,
    }


def day_of(frame: pd.DataFrame, position: int) -> date:
    return frame.index[position].date()


def dump(obj, path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")
