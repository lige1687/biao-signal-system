"""海外指数「当日形成中 bar」实时叠加。

为什么需要
----------
海外指数的**日线**源在盘中拿不到当日 bar，导致美股开盘后卡片纹丝不动：

- ``yahoo_v8`` / ``yfinance``：Yahoo 对免费调用做 **IP 级** 429 限流，
  一旦触发会持续几十分钟——盘中恰好正是用不上的时候。
- ``tencent_global``（``web.ifzq.gtimg.cn``）：美股盘中**只返回 1 根**当日
  形成中 bar（实测请求 60/120/200/250/320 根均如此），不足 ``min_rows``
  → 链路判定该源失败。收盘后才恢复返回 320 根。

两者一起失败 → ``analyze()`` 回落 Parquet 缓存 → 现价停在上一交易日收盘。
用户可见症状就是「美股都开盘了，纳指标普还不更新」。

解决办法：把「历史」与「当日」拆开取
------------------------------------
- **历史**：日线源（一天只变一次，天然适合缓存/限流兜底）；
- **当日**：实时报价接口——轻量、不限流、盘中随时可取：

  =========== ==================================== ==================
  标的        实时源                                成交量
  =========== ==================================== ==================
  ^IXIC/^GSPC 腾讯 ``qt.gtimg.cn``（usIXIC/usINX）  有
  ^HSTECH     腾讯 ``qt.gtimg.cn``（hkHSTECH）      有
  ^KS11       新浪 ``hq.sinajs.cn``（znb_KOSPI）    **无** → NaN
  =========== ==================================== ==================

这与 A 股口径是**一致**的：腾讯 A 股日线接口本来就含当日形成中 bar。所以
这里是把海外补齐到与 A 股相同的语义，不是引入新语义。

诚实原则
--------
- 新浪 KOSPI 不给成交量 → 写 ``NaN``，界面显示「—」，绝不拿昨日量顶替。
- 实时源任何失败 → 原样返回历史，不阻断分析（叠加是增强，不是前置条件）。
- 报价日期若不晚于历史最后一根，只在**同日**时刷新该根；更早则丢弃
  （说明报价源比日线源还旧，不能让它把已收盘的 bar 改回去）。
"""
from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import numpy as np
import pandas as pd

from lei_signal.data.cache import ParquetCache
from lei_signal.data.providers import PriceData, PriceProvider
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import DataUnavailableError, ValidationReport

Opener = Callable[[str], str]

#: 腾讯实时报价字段下标（``~`` 分隔）。与 quotes.py 共用同一套布局，
#: 但这里要的是 OHLCV 而不是盘口，故单列一份下标常量。
_T_NAME = 1
_T_PRICE = 3
_T_PREV_CLOSE = 4
_T_OPEN = 5
_T_VOLUME = 6
_T_TIME = 30
_T_HIGH = 33
_T_LOW = 34
_T_MIN_FIELDS = 35

#: 新浪全球指数字段下标（``,`` 分隔）。
_S_NAME = 0
_S_PRICE = 1
_S_DATE = 6
_S_OPEN = 8
_S_PREV_CLOSE = 9
_S_HIGH = 10
_S_LOW = 11
_S_MIN_FIELDS = 12

#: Yahoo 口径符号 → 腾讯实时代码。只登记实测有实时报价返回的标的。
_TENCENT_RT: dict[str, str] = {
    "^IXIC": "usIXIC",
    "^GSPC": "usINX",
    "^HSTECH": "hkHSTECH",
    "^DJI": "usDJI",
    "^NDX": "usNDX",
    "^HSI": "hkHSI",
}

#: Yahoo 口径符号 → 新浪全球指数代码（腾讯不覆盖的标的）。
_SINA_RT: dict[str, str] = {
    "^KS11": "znb_KOSPI",
}


@dataclass(frozen=True, slots=True)
class RealtimeBar:
    """一根当日形成中的日 K 线。``volume`` 为 None 表示源不提供（不得编造）。"""

    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    source: str
    quote_time: str | None = None


class RealtimeBarSource(Protocol):
    """实时 bar 源：``supports`` 判定覆盖范围，``fetch`` 失败一律返回 None。"""

    name: str

    def supports(self, symbol: str) -> bool: ...

    def fetch(self, symbol: str) -> RealtimeBar | None: ...


def _to_float(raw: str) -> float | None:
    text = raw.strip()
    if not text or text in ("-", "-1"):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value


def _parse_date(text: str) -> date | None:
    """认 ``2026-08-03`` 与 ``2026/08/03`` 两种写法（腾讯美股/港股不一致）。"""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _default_opener(url: str, *, referer: str, encoding: str, timeout: float) -> str:
    request = urllib.request.Request(  # noqa: S310 - 固定 https 主机
        url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read().decode(encoding, errors="replace")


def _payload(text: str, sep: str) -> list[str] | None:
    """从 ``var x="a~b~c";`` 形式的响应里取出字段列表。"""
    if '="' not in text:
        return None
    body = text.split('="', 1)[1]
    body = body.rsplit('"', 1)[0]
    if not body.strip():
        return None
    return body.split(sep)


class TencentRealtimeBarSource:
    """腾讯实时报价 → 当日形成中 bar（美股/港股指数，含成交量）。"""

    name = "tencent_rt"
    _HOST = "https://qt.gtimg.cn/q="

    def __init__(self, opener: Opener | None = None, *, timeout: float = 8.0) -> None:
        self._opener = opener or (
            lambda url: _default_opener(
                url, referer="https://gu.qq.com/", encoding="gbk", timeout=timeout
            )
        )

    def supports(self, symbol: str) -> bool:
        return symbol.strip().upper() in _TENCENT_RT

    def fetch(self, symbol: str) -> RealtimeBar | None:
        code = _TENCENT_RT.get(symbol.strip().upper())
        if code is None:
            return None
        try:
            text = self._opener(f"{self._HOST}{code}")
        except (urllib.error.URLError, OSError, UnicodeError):
            return None

        parts = _payload(text, "~")
        if parts is None or len(parts) < _T_MIN_FIELDS:
            return None

        close = _to_float(parts[_T_PRICE])
        open_ = _to_float(parts[_T_OPEN])
        high = _to_float(parts[_T_HIGH])
        low = _to_float(parts[_T_LOW])
        raw_time = parts[_T_TIME].strip()
        if close is None or open_ is None or high is None or low is None or not raw_time:
            return None

        # 腾讯返回交易所当地时间。美股用 "2026-08-03 10:03:20"，港股用
        # "2026/08/03 16:08:32"（斜杠）——两种都得认，否则港股静默取不到。
        bar_date = _parse_date(raw_time[:10])
        if bar_date is None:
            return None

        return RealtimeBar(
            bar_date=bar_date,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=_to_float(parts[_T_VOLUME]),
            source=self.name,
            quote_time=raw_time,
        )


class SinaRealtimeBarSource:
    """新浪全球指数 → 当日形成中 bar（KOSPI；**不提供成交量**）。

    必须带 ``Referer``：不带会被新浪直接 403，这也是早前误判「新浪不可用」
    的原因。
    """

    name = "sina_rt"
    _HOST = "https://hq.sinajs.cn/list="

    def __init__(self, opener: Opener | None = None, *, timeout: float = 8.0) -> None:
        self._opener = opener or (
            lambda url: _default_opener(
                url,
                referer="https://finance.sina.com.cn",
                encoding="gbk",
                timeout=timeout,
            )
        )

    def supports(self, symbol: str) -> bool:
        return symbol.strip().upper() in _SINA_RT

    def fetch(self, symbol: str) -> RealtimeBar | None:
        code = _SINA_RT.get(symbol.strip().upper())
        if code is None:
            return None
        try:
            text = self._opener(f"{self._HOST}{code}")
        except (urllib.error.URLError, OSError, UnicodeError):
            return None

        parts = _payload(text, ",")
        if parts is None or len(parts) < _S_MIN_FIELDS:
            return None

        close = _to_float(parts[_S_PRICE])
        open_ = _to_float(parts[_S_OPEN])
        high = _to_float(parts[_S_HIGH])
        low = _to_float(parts[_S_LOW])
        raw_date = parts[_S_DATE].strip()
        if close is None or open_ is None or high is None or low is None:
            return None
        bar_date = _parse_date(raw_date)
        if bar_date is None:
            return None

        return RealtimeBar(
            bar_date=bar_date,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=None,  # 新浪该接口不给成交量；写 NaN 而不是拿昨日量冒充
            source=self.name,
            quote_time=raw_date,
        )


def _clamp(bar: RealtimeBar) -> RealtimeBar:
    """修正源偶发的 OHLC 越界，避免下游校验直接判定「非法 OHLC」丢弃整条。

    盘中报价的 high/low 与 price 来自不同刷新时点，极偶尔会出现
    ``price > high``。这里按定义收敛（high 至少是四价最大值），
    属于口径修正而非编数据。
    """
    high = max(bar.high, bar.open, bar.close)
    low = min(bar.low, bar.open, bar.close)
    if high == bar.high and low == bar.low:
        return bar
    return RealtimeBar(
        bar_date=bar.bar_date,
        open=bar.open,
        high=high,
        low=low,
        close=bar.close,
        volume=bar.volume,
        source=bar.source,
        quote_time=bar.quote_time,
    )


def apply_forming_bar(bars: pd.DataFrame, bar: RealtimeBar) -> pd.DataFrame:
    """把实时 bar 叠加到日线历史上，返回新 DataFrame（不原地改）。

    - 报价日 > 历史最后一日 → 追加一根形成中 bar；
    - 报价日 == 历史最后一日 → 用更新的四价覆盖（盘中会持续变化）；
    - 报价日 < 历史最后一日 → 原样返回（报价源比日线源还旧，不采信）。
    """
    if bars.empty:
        return bars
    bar = _clamp(bar)
    stamp = pd.Timestamp(bar.bar_date)
    last = bars.index[-1]
    if stamp < last:
        return bars

    updated = bars.copy()
    values: dict[str, float] = {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": float("nan") if bar.volume is None else bar.volume,
    }
    if stamp == last:
        for column, value in values.items():
            if column in updated.columns:
                updated.loc[stamp, column] = value
        return updated

    row = {column: values.get(column, np.nan) for column in updated.columns}
    return pd.concat([updated, pd.DataFrame([row], index=[stamp])])


class IntradayOverlayProvider:
    """在日线 provider 之上叠加「当日形成中 bar」。

    与 ``analyze()`` 内置的缓存兜底的关系
    --------------------------------------
    ``analyze()`` 自己也有 Parquet 兜底，但它兜到的是**纯历史**——正是当前
    症状的来源（链路全挂 → 拿缓存 → 停在上一交易日）。所以这里必须自己先
    兜一次缓存、再叠加实时 bar，让 ``analyze()`` 根本走不到那条降级分支。

    对 A 股是 no-op：A 股日线源本来就带当日形成中 bar，``_sources`` 里没有
    对应条目，直接返回内层结果。
    """

    name = "intraday_overlay"

    def __init__(
        self,
        inner: PriceProvider | Callable[[str, int], PriceData],
        *,
        cache_root: str | None = None,
        sources: list[RealtimeBarSource] | None = None,
        cache_max_age_seconds: float = 86400.0 * 7,
    ) -> None:
        self._inner = inner
        self._cache = ParquetCache(cache_root) if cache_root else None
        self._sources: list[RealtimeBarSource] = (
            sources
            if sources is not None
            else [TencentRealtimeBarSource(), SinaRealtimeBarSource()]
        )
        self._cache_max_age = cache_max_age_seconds

    def _realtime_bar(self, symbol: str) -> RealtimeBar | None:
        for source in self._sources:
            if source.supports(symbol):
                bar = source.fetch(symbol)
                if bar is not None:
                    return bar
        return None

    def _call_inner(self, symbol: str, min_rows: int) -> PriceData:
        inner = self._inner
        if callable(inner) and not hasattr(inner, "fetch"):
            try:
                return inner(symbol, min_rows)
            except TypeError:
                # 兼容测试里常见的 ``def inner(symbol, *, min_rows=21)`` 写法
                return inner(symbol, min_rows=min_rows)  # type: ignore[call-arg]
        return inner.fetch(symbol, min_rows=min_rows)  # type: ignore[union-attr]

    def _from_cache(self, symbol: str, min_rows: int) -> PriceData | None:
        """日线源全挂时，用缓存历史顶上（随后再叠加实时 bar）。"""
        if self._cache is None:
            return None
        cached = self._cache.read(
            symbol, kind="bars", required_columns=("open", "close")
        )
        if cached is None or len(cached) < min_rows:
            return None
        age = self._cache.age_seconds(symbol)
        if age is None or age > self._cache_max_age:
            return None
        info = resolve_symbol(symbol)
        report = ValidationReport(
            rows=len(cached),
            first_date=cached.index[0],
            last_date=cached.index[-1],
            adjusted=True,
            provider="parquet_cache",
            duplicates_removed=0,
            warnings=("cache_stale", f"cache age {age:.0f}s"),
        )
        return PriceData(
            symbol=info.symbol,
            display_name=info.symbol,
            bars=cached,
            report=report,
            info=info,
        )

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        bar = self._realtime_bar(symbol)

        try:
            data = self._call_inner(symbol, min_rows)
        except DataUnavailableError:
            # 只有拿到实时 bar 才值得走缓存兜底：否则维持原异常语义，
            # 让 analyze() 自己的兜底/报错逻辑照常工作。
            fallback = self._from_cache(symbol, min_rows) if bar is not None else None
            if fallback is None:
                raise
            data = fallback

        if bar is None:
            return data

        merged = apply_forming_bar(data.bars, bar)
        if merged is data.bars:
            return data

        report = data.report
        provider = (
            report.provider
            if report.provider.endswith(f"+{bar.source}")
            else f"{report.provider}+{bar.source}"
        )
        return PriceData(
            symbol=data.symbol,
            display_name=data.display_name,
            bars=merged,
            report=ValidationReport(
                rows=len(merged),
                first_date=merged.index[0],
                last_date=merged.index[-1],
                adjusted=report.adjusted,
                provider=provider,
                duplicates_removed=report.duplicates_removed,
                warnings=report.warnings,
            ),
            info=data.info,
        )


__all__ = [
    "CacheFirstProvider",
    "IntradayOverlayProvider",
    "RealtimeBar",
    "SinaRealtimeBarSource",
    "TencentRealtimeBarSource",
    "apply_forming_bar",
]


class CacheFirstProvider:
    """缓存优先 provider：ParquetCache 命中且年龄 < TTL 直接返回，不打网络。

    为什么需要
    ----------
    Yahoo v8 / yfinance 的 query2 端点对外网 IP 做 429 限流，海外指数一旦
    触发就持续几十分钟——而用户一天也就看 2-3 次。**日线历史一天只多一根**，
    盘中的「更新」由外层 ``IntradayOverlayProvider`` 用实时报价（腾讯
    qt.gtimg.cn / 新浪 hq.sinajs.cn）叠加，缓存新鲜时连日线源都不用打。

    行为
    ----
    - 缓存不存在 / 过期 → 调用 ``inner.fetch()``（让真正的 provider 跑）
    - 缓存存在且年龄 < ``cache_max_age_seconds`` → 直接返回缓存

    注意
    ----
    只在海外指数路径启用；A 股不包这层（A 股日线本就是当前 bar）。
    """

    name = "cache_first"

    def __init__(
        self,
        inner: PriceProvider | Callable[[str, int], PriceData],
        *,
        cache_root: str,
        cache_max_age_seconds: float = 1800.0,  # 30 min
    ) -> None:
        self._inner = inner
        self._cache = ParquetCache(cache_root)
        self._cache_max_age = cache_max_age_seconds

    def _from_cache(self, symbol: str, min_rows: int) -> PriceData | None:
        cached = self._cache.read(
            symbol, kind="bars", required_columns=("open", "close")
        )
        if cached is None or len(cached) < min_rows:
            return None
        age = self._cache.age_seconds(symbol)
        if age is None or age > self._cache_max_age:
            return None
        info = resolve_symbol(symbol)
        report = ValidationReport(
            rows=len(cached),
            first_date=cached.index[0],
            last_date=cached.index[-1],
            adjusted=True,
            provider="parquet_cache",
            duplicates_removed=0,
            warnings=("cache_fresh", f"cache age {age:.0f}s"),
        )
        return PriceData(
            symbol=info.symbol,
            display_name=info.symbol,
            bars=cached,
            report=report,
            info=info,
        )

    def _call_inner(self, symbol: str, min_rows: int) -> PriceData:
        inner = self._inner
        if callable(inner) and not hasattr(inner, "fetch"):
            try:
                return inner(symbol, min_rows)  # type: ignore[call-arg]
            except TypeError:
                return inner(symbol, min_rows=min_rows)  # type: ignore[call-arg]
        return inner.fetch(symbol, min_rows=min_rows)  # type: ignore[union-attr]

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        # 缓存优先：避免海外指数在 Yahoo 限流期间被反复打
        cached = self._from_cache(symbol, min_rows)
        if cached is not None:
            return cached
        return self._call_inner(symbol, min_rows)
