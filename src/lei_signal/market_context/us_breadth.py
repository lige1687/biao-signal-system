"""SP500 真实市场宽度回溯 —— 与 A股 `a_share_breadth.backfill_ma_breadth_history`
同范式：拉成分股日线收盘价 → 透视 → 逐日算「站上 MA20/50/200 的个股占比」
（券商金工口径的 breadth）→ 落盘 JSON，供投影图高亮使用。

数据来源（按优先级）：
  1. 已落盘的 `sp500_klines.parquet`（成分股收盘价透视表）— 不重复下载；
  2. 用户直接提供的文件（`$SP500_KLINES_PATH` 或 cache 下 `sp500_klines_user.parquet`，
     列为 date + 各 ticker 收盘价）— 适合沙箱/离线环境；
  3. 在线拉取：yfinance（本机家宽 IP 可用；共享 IP 段会被 Yahoo 限流，失败自动跳过该票）。

绝不编造：任何来源缺失都不返回冻结/占位值，空则上层判退化、UI 明确标注「数据缺失」。
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import pandas as pd

from lei_signal.api import config

logger = logging.getLogger(__name__)

# 503 只成分股来自 wikipedia_sp500 快照（tests/fixtures 内）。
_UNIVERSE_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "market_context"
    / "universes"
    / "SP500.parquet"
)


def _klines_cache_path() -> Path:
    return Path(config.cache_root()) / "sp500_klines.parquet"


def _breadth_history_path() -> Path:
    return Path(config.cache_root()) / "sp500_ma_breadth_history.json"


def _user_klines_path() -> Path | None:
    env = os.environ.get("SP500_KLINES_PATH")
    if env and Path(env).exists():
        return Path(env)
    p = Path(config.cache_root()) / "sp500_klines_user.parquet"
    return p if p.exists() else None


def _load_universe_symbols() -> list[str]:
    """SP500 成分股 ticker（去掉宇宙表的 universe_id 列）。"""
    if not _UNIVERSE_FIXTURE.exists():
        logger.warning("未找到 SP500 宇宙表：%s", _UNIVERSE_FIXTURE)
        return []
    df = pd.read_parquet(_UNIVERSE_FIXTURE)
    col = "symbol" if "symbol" in df.columns else df.columns[1]
    return [str(s).strip() for s in df[col].tolist() if str(s).strip() and str(s) != "SP500"]


def _yf_symbol(ticker: str) -> str:
    """yfinance 用 '-' 而非 '.'（BRK.B -> BRK-B）。"""
    return ticker.replace(".", "-")


def _fetch_closes_yfinance(symbols: list[str], delay: float = 0.25) -> pd.DataFrame:
    """逐票拉日线收盘价，返回 date×symbol 透视表。单票失败跳过。"""
    import yfinance as yf  # 惰性导入：未装 yfinance 的机器不会因 import 崩溃

    frames: dict[str, pd.Series] = {}
    ok = 0
    for sym in symbols:
        yf_sym = _yf_symbol(sym)
        try:
            hist = yf.Ticker(yf_sym).history(period="5y", interval="1d", auto_adjust=False)
            close = hist.get("Close")
            if close is not None and len(close) > 0:
                frames[sym] = close.dropna()
                ok += 1
            else:
                logger.warning("yfinance %s 无收盘数据", yf_sym)
        except Exception as exc:  # noqa: BLE001 —— Yahoo 共享 IP 限流等
            logger.warning("yfinance %s 拉取失败：%s", yf_sym, exc)
        time.sleep(delay)
    logger.info("yfinance 拉取完成：%d/%d 只成功", ok, len(symbols))
    if not frames:
        return pd.DataFrame()
    piv = pd.DataFrame(frames)
    piv.index = pd.to_datetime(piv.index)
    return piv.sort_index()


def _load_closes(symbols: list[str]) -> pd.DataFrame:
    """按优先级解析成分股收盘价透视表。"""
    cache = _klines_cache_path()
    if cache.exists():
        logger.info("复用已落盘成分股收盘价：%s", cache)
        return pd.read_parquet(cache)
    user = _user_klines_path()
    if user is not None:
        logger.info("使用用户提供的成分股收盘价：%s", user)
        df = pd.read_parquet(user)
        if "date" in df.columns:
            df = df.set_index("date")
        df.index = pd.to_datetime(df.index)
        return df.sort_index()
    logger.info("在线拉取 SP500 成分股收盘价（yfinance）…")
    piv = _fetch_closes_yfinance(symbols)
    if not piv.empty:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            piv.to_parquet(cache)
            logger.info("成分股收盘价已落盘：%s", cache)
        except Exception as exc:  # noqa: BLE001
            logger.warning("成分股收盘价落盘失败：%s", exc)
    return piv


def compute_sp500_breadth(
    piv: pd.DataFrame,
    windows: tuple[int, ...] = (20, 50, 200),
    min_eligible: int = 100,
) -> list[dict]:
    """逐日算站上各 MA 的个股占比（与 A股 backfill 同算法）。

    返回 [{date, breadth_20, breadth_50, breadth_200}, ...]，占比为 0–100。
    合格样本（有均线的票）不足 min_eligible 的交易日跳过，避免早期噪声。
    """
    if piv.empty:
        return []
    ma = {w: piv.rolling(w).mean() for w in windows}
    above = {w: (piv > ma[w]) for w in windows}
    elig = {w: (piv.notna() & ma[w].notna()) for w in windows}

    pct: dict[int, pd.Series] = {}
    for w in windows:
        denom = elig[w].sum(axis=1)
        pct[w] = (above[w].sum(axis=1) / denom * 100).where(denom >= min_eligible)

    key_of = {w: f"breadth_{w}" for w in windows}
    hist: list[dict] = []
    for d in piv.index:
        if pd.isna(pct[windows[0]].get(d)):
            continue
        row: dict[str, object] = {"date": pd.Timestamp(d).strftime("%Y-%m-%d")}
        for w in windows:
            v = pct[w].get(d)
            row[key_of[w]] = None if pd.isna(v) else round(float(v), 4)
        hist.append(row)
    return hist


def backfill_sp500_breadth_history(
    max_points: int = 1260,
    min_eligible: int = 100,
) -> list[dict]:
    """重建 SP500 真实宽度历史并落盘（覆盖式写入 sp500_ma_breadth_history.json）。

    数据源见模块 docstring。无数据则返回 []（上层据此判退化，UI 标「数据缺失」）。
    """
    symbols = _load_universe_symbols()
    if not symbols:
        logger.warning("SP500 成分股列表为空，无法回溯宽度历史。")
        return []
    piv = _load_closes(symbols)
    if piv.empty:
        logger.warning("SP500 成分股收盘价为空（离线且无数据/未提供文件），无法回溯。")
        return []
    hist = compute_sp500_breadth(piv, min_eligible=min_eligible)
    if not hist:
        logger.warning("SP500 宽度历史计算为空（合格样本不足）。")
        return []
    hist.sort(key=lambda h: h["date"])
    hist = hist[-max_points:]
    try:
        _breadth_history_path().parent.mkdir(parents=True, exist_ok=True)
        _breadth_history_path().write_text(
            json.dumps(hist, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("SP500 宽度历史落盘失败：%s", exc)
    logger.info(
        "SP500 回溯完成：共 %d 个交易日（%s -> %s）",
        len(hist), hist[0]["date"], hist[-1]["date"],
    )
    return hist


def get_sp500_breadth_history(lookback_days: int = 1260) -> list[dict]:
    """返回已落盘的 SP500 宽度历史（最多 lookback_days 个交易日）。"""
    p = _breadth_history_path()
    try:
        hist = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(hist, list):
            return []
        return hist[-lookback_days:]
    except Exception:  # noqa: BLE001
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = backfill_sp500_breadth_history()
    print(f"SP500 宽度历史点数：{len(result)}")
    if result:
        print("首:", result[0])
        print("尾:", result[-1])
