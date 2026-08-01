"""行情 Provider：Yahoo（默认）与东方财富（A 股增强源）。

Provider 接口可替换。任何数据问题都通过 DataUnavailableError 显式暴露，
不得静默返回空结果。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from lei_signal.data.symbols import SymbolInfo, eastmoney_secid, is_a_share, resolve_symbol
from lei_signal.data.validation import (
    DataUnavailableError,
    ValidationReport,
    validate_bars,
)


@dataclass(frozen=True, slots=True)
class PriceData:
    """统一行情结果。"""

    symbol: str
    display_name: str
    bars: pd.DataFrame
    report: ValidationReport
    info: SymbolInfo


class PriceProvider(Protocol):
    name: str

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData: ...


class YahooPriceProvider:
    """Yahoo Finance 复权日线。"""

    name = "yahoo"

    def __init__(self, ticker_factory: Callable[[str], Any] | None = None) -> None:
        if ticker_factory is None:
            import yfinance as yf

            ticker_factory = yf.Ticker
        self._ticker_factory = ticker_factory

    def fetch(self, symbol: str, *, min_rows: int = 21, period: str = "max") -> PriceData:
        info = resolve_symbol(symbol)
        try:
            ticker = self._ticker_factory(info.symbol)
            raw = ticker.history(
                period=period,
                interval="1d",
                auto_adjust=True,   # 复权：避免分红拆股造成虚假颜色切换
                actions=False,
            )
        except Exception as exc:  # noqa: BLE001 - 网络与解析异常统一转为可显示错误
            raise DataUnavailableError(f"无法获取 {info.symbol} 的行情：{exc}") from exc

        if raw is None or len(raw) == 0:
            raise DataUnavailableError(
                f"没有找到 {info.symbol} 的日线行情，请检查代码和市场后缀"
            )

        renamed = raw.rename(columns=str.lower)
        bars, report = validate_bars(
            renamed,
            symbol=info.symbol,
            provider=self.name,
            adjusted=True,
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=self._display_name(ticker, info.symbol),
            bars=bars,
            report=report,
            info=info,
        )

    @staticmethod
    def _display_name(ticker: Any, fallback: str) -> str:
        try:
            meta = getattr(ticker, "info", None) or {}
            name = meta.get("shortName") or meta.get("longName")
        except Exception:  # noqa: BLE001 - info 是可选元数据，失败不应阻断行情
            name = None
        return str(name or fallback)


class EastmoneyPriceProvider:
    """东方财富 A 股增强源。

    移植来源
    --------
    旧路径 : /Users/yongbiaoli/Desktop/licai-wt-pg-integration
             src/plan_guardian/adapters/market/{transport,history_parser}.py
    旧commit: 2ee7fdc6f3f83fa6a787286e1f7f901b309cc666
    改造原因:
      1. 旧历史接口固定 `fqt=0`（不复权）。LEI 信号必须使用复权日线，
         因此改为 `fqt=1`（前复权），并在 ValidationReport 标注 adjusted=True。
      2. 旧 DTO 围绕 RequirementKey / SignalAssetId / FundId；新项目改为通用 Symbol。
      3. 只移植「有界请求 + klines 解析」，不移植 redaction、SourceError 分类体系
         与账户域依赖。
    """

    name = "eastmoney"
    _HOST = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    def __init__(
        self,
        opener: Callable[[str], str] | None = None,
        *,
        timeout: float = 10.0,
        max_bars: int = 6000,
    ) -> None:
        self._opener = opener or self._default_opener
        self._timeout = timeout
        self._max_bars = max_bars

    def _default_opener(self, url: str) -> str:
        request = urllib.request.Request(  # noqa: S310 - 固定 https 主机
            url,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                if response.status != 200:
                    raise DataUnavailableError(f"东方财富返回 HTTP {response.status}")
                return response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise DataUnavailableError(f"东方财富网络请求失败：{exc.reason}") from exc

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        if not is_a_share(info):
            raise DataUnavailableError(f"{info.symbol} 不是 A 股标的，东方财富源不适用")

        params = {
            "secid": eastmoney_secid(info),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
            "klt": "101",   # 日线
            "fqt": "1",     # 前复权（旧实现为 0=不复权，此处改动）
            "beg": "0",
            "end": "20500101",
            "lmt": str(self._max_bars),
        }
        url = f"{self._HOST}?{urllib.parse.urlencode(params)}"
        payload = self._parse_payload(self._opener(url), info.symbol)
        bars_raw, name = payload
        bars, report = validate_bars(
            bars_raw,
            symbol=info.symbol,
            provider=self.name,
            adjusted=True,
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=name,
            bars=bars,
            report=report,
            info=info,
        )

    @staticmethod
    def _parse_payload(text: str, symbol: str) -> tuple[pd.DataFrame, str]:
        """解析 klines。字段顺序由 fields2 固定：日期,开,收,高,低,量,额,振幅。"""
        try:
            payload: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DataUnavailableError(f"{symbol} 东方财富返回非 JSON 内容") from exc

        data = payload.get("data")
        if not isinstance(data, dict):
            raise DataUnavailableError(f"{symbol} 东方财富返回缺少 data 字段")
        klines = data.get("klines")
        if not isinstance(klines, list) or not klines:
            raise DataUnavailableError(f"{symbol} 东方财富没有返回日线数据")

        records: list[dict[str, Any]] = []
        for line in klines:
            parts = str(line).split(",")
            if len(parts) < 6:
                raise DataUnavailableError(f"{symbol} 东方财富 kline 字段不足: {line!r}")
            records.append(
                {
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": float(parts[5]),
                }
            )
        frame = pd.DataFrame(records)
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date")
        name = str(data.get("name") or symbol)
        return frame, name


class ChainedPriceProvider:
    """按顺序尝试多个 Provider，全部失败则报告全部原因。

    A 股优先东方财富（复权 + 交易日更贴近本地口径），其余走 Yahoo。
    """

    name = "chained"

    def __init__(self, providers: list[PriceProvider]) -> None:
        if not providers:
            raise ValueError("至少需要一个 Provider")
        self._providers = providers

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        ordered = sorted(
            self._providers,
            key=lambda p: 0 if (is_a_share(info) and p.name == "eastmoney") else 1,
        )
        errors: list[str] = []
        for provider in ordered:
            try:
                return provider.fetch(symbol, min_rows=min_rows)
            except DataUnavailableError as exc:
                errors.append(f"[{provider.name}] {exc}")
        raise DataUnavailableError(
            f"{info.symbol} 所有行情源均不可用：" + "；".join(errors)
        )


def default_provider() -> ChainedPriceProvider:
    """默认行情源组合。"""
    return ChainedPriceProvider([YahooPriceProvider(), EastmoneyPriceProvider()])


__all__ = [
    "ChainedPriceProvider",
    "EastmoneyPriceProvider",
    "PriceData",
    "PriceProvider",
    "YahooPriceProvider",
    "default_provider",
]
