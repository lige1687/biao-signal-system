"""宽度择时回测数据层：行情/宽度加载、对齐、全A宽度重算（纯函数）。

宽度口径：个股收盘价 > MA(N) 的占比（0-100），各窗口独立分母；
个股须有 >= N 根 K 线才计入该窗口分母（与 market_context/breadth.py 口径一致）。

数据诚实声明（页面展示用）：
- 全A宽度由当前存续个股（新浪不复权价）回算，早年存在幸存者偏差；
- 宽度序列截至最近一次回填日，重跑 scripts/backfill_timing_data.py 可刷新。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TIMING_CACHE_DIR = Path(
    os.environ.get("LEI_TIMING_CACHE_DIR", str(Path.home() / ".lei_signal_lab/cache/timing"))
)

BREADTH_FILES = {"cn_all": "breadth_cn_all.parquet", "sp500": "breadth_sp500.parquet"}

SURVIVORSHIP_NOTE = "全A宽度：当前存续成分回算，早年有幸存者偏差；底表为新浪不复权价"


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    name: str
    market: str  # cn | us
    breadth: str  # cn_all | sp500
    data_file: str
    source: str  # ak_index | ak_etf | yf
    fetch_symbol: str
    fee_default_bps: float
    note: str = ""


def _spec(symbol: str, name: str, market: str, breadth: str, source: str,
          fetch: str, fee: float, note: str) -> InstrumentSpec:
    return InstrumentSpec(
        symbol, name, market, breadth, f"{symbol}.parquet", source, fetch, fee, note
    )


_US_NOTE = "SP500 成分宽度（当前成分回算，早年有幸存者偏差）"
_A = SURVIVORSHIP_NOTE
_A_ETF = "含分红复权（源不可用时退新浪不复权），历史较短，" + SURVIVORSHIP_NOTE

INSTRUMENTS: dict[str, InstrumentSpec] = {
    "000300": _spec("000300", "沪深300", "cn", "cn_all", "ak_index", "sh000300", 5.0, _A),
    "399006": _spec("399006", "创业板指", "cn", "cn_all", "ak_index", "sz399006", 5.0, _A),
    "^GSPC": _spec("^GSPC", "标普500", "us", "sp500", "yf", "^GSPC", 1.0, _US_NOTE),
    "^IXIC": _spec("^IXIC", "纳斯达克", "us", "sp500", "yf", "^IXIC", 1.0, _US_NOTE),
    "SPY": _spec("SPY", "SPY(ETF)", "us", "sp500", "yf", "SPY", 1.0, "含分红复权，" + _US_NOTE),
    "QQQ": _spec("QQQ", "QQQ(ETF)", "us", "sp500", "yf", "QQQ", 1.0, "含分红复权，" + _US_NOTE),
    "510300": _spec("510300", "沪深300ETF", "cn", "cn_all", "ak_etf", "510300", 5.0, _A_ETF),
    "159915": _spec("159915", "创业板ETF", "cn", "cn_all", "ak_etf", "159915", 5.0, _A_ETF),
}


def compute_breadth_from_close_matrix(
    close_wide: pd.DataFrame,
    windows: tuple[int, ...] = (20, 50, 200),
    min_eligible: int = 30,
) -> pd.DataFrame:
    """逐日计算「收盘 > MA(w)」个股占比（0-100），各窗口独立分母。

    eligible < min_eligible 的日子输出 NaN（早期市场个股太少，宽度无意义）。
    """
    close_wide = close_wide.sort_index()
    out = pd.DataFrame(index=close_wide.index)
    for w in windows:
        ma = close_wide.rolling(w, min_periods=w).mean()
        above = ((close_wide > ma) & ma.notna()).sum(axis=1)
        eligible = (close_wide.rolling(w, min_periods=w).count() >= w).sum(axis=1)
        pct = above / eligible.where(eligible > 0) * 100
        out[f"b{w}"] = pct.astype(float).where(eligible >= min_eligible)
        out[f"n{w}"] = eligible
    return out


def load_breadth(market: str, cache_dir: Path | None = None) -> pd.DataFrame:
    path = (cache_dir or TIMING_CACHE_DIR) / BREADTH_FILES[market]
    df = pd.read_parquet(path)[["b20", "b50", "b200"]]
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.columns = ["b20", "b50", "b200"]
    return df


def load_index_bars(symbol: str, cache_dir: Path | None = None) -> pd.DataFrame:
    spec = INSTRUMENTS.get(symbol)
    file = spec.data_file if spec is not None else f"{symbol}.parquet"
    df = pd.read_parquet((cache_dir or TIMING_CACHE_DIR) / file)
    # 兼容只有 open/close 的旧缓存：高低价由开收盘合成（足够画 K 线示意）
    for col in ("open", "close"):
        if col not in df.columns:
            raise ValueError(f"{file} 缺少 {col} 列")
    if "high" not in df.columns:
        df["high"] = df[["open", "close"]].max(axis=1)
    if "low" not in df.columns:
        df["low"] = df[["open", "close"]].min(axis=1)
    df = df[["open", "high", "low", "close"]]
    return df[~df.index.duplicated(keep="last")].sort_index()


def align_index_breadth(index_df: pd.DataFrame, breadth_df: pd.DataFrame) -> pd.DataFrame:
    """按日期交集对齐行情与宽度（列序固定：open, high, low, close, b20, b50, b200）。"""
    merged = index_df.join(breadth_df, how="inner").sort_index()
    return merged[["open", "high", "low", "close", "b20", "b50", "b200"]]


def data_unavailable_detail(symbol: str) -> str:
    spec = INSTRUMENTS.get(symbol)
    if spec is None:
        return f"未知标的 {symbol}（可用：{', '.join(INSTRUMENTS)}）"
    return (
        f"DATA_UNAVAILABLE: {spec.name}({symbol}) 本地无行情数据，"
        f"请先运行 scripts/backfill_timing_data.py 回填后再试"
    )
