"""行情 Provider：Yahoo（默认）与东方财富（A 股增强源）。

Provider 接口可替换。任何数据问题都通过 DataUnavailableError 显式暴露，
不得静默返回空结果。
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from lei_signal.data.symbols import (
    Market,
    SymbolInfo,
    eastmoney_secid,
    is_a_share,
    resolve_symbol,
)
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

    def __init__(
        self,
        ticker_factory: Callable[[str], Any] | None = None,
        *,
        attempts: int = 3,
        backoff: float = 2.0,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        if ticker_factory is None:
            import yfinance as yf

            ticker_factory = yf.Ticker
        self._ticker_factory = ticker_factory
        self._attempts = max(1, attempts)
        self._backoff = backoff
        self._sleep = sleep if sleep is not None else time.sleep

    def fetch(self, symbol: str, *, min_rows: int = 21, period: str = "max") -> PriceData:
        info = resolve_symbol(symbol)
        last_error: Exception | None = None
        raw = None
        ticker: Any = None

        # Yahoo 常见 429 限流是瞬时的，有界重试后再判定不可用。
        for attempt in range(self._attempts):
            try:
                ticker = self._ticker_factory(info.symbol)
                raw = ticker.history(
                    period=period,
                    interval="1d",
                    auto_adjust=True,   # 复权：避免分红拆股造成虚假颜色切换
                    actions=False,
                )
                if raw is not None and len(raw) > 0:
                    break
                last_error = None
            except Exception as exc:  # noqa: BLE001 - 网络与解析异常统一转为可显示错误
                last_error = exc
                raw = None
            if attempt < self._attempts - 1:
                self._sleep(self._backoff * (attempt + 1))

        if last_error is not None and (raw is None or len(raw) == 0):
            raise DataUnavailableError(
                f"无法获取 {info.symbol} 的行情：{last_error}"
            ) from last_error

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
        attempts: int = 3,
        backoff: float = 1.5,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._opener = opener or self._default_opener
        self._timeout = timeout
        self._max_bars = max_bars
        self._attempts = max(1, attempts)
        self._backoff = backoff
        self._sleep = sleep if sleep is not None else time.sleep

    def _fetch_text(self, url: str) -> str:
        """有界重试：瞬时网络中断不应等同于永久不可用。

        任何非 DataUnavailableError 的异常（例如 RemoteDisconnected、
        socket.timeout）都在此统一转换，保证界面永远只看到 DATA_UNAVAILABLE，
        而不是原始堆栈。
        """
        last: DataUnavailableError | None = None
        for attempt in range(self._attempts):
            try:
                return self._opener(url)
            except DataUnavailableError as exc:
                last = exc
            except Exception as exc:  # noqa: BLE001 - 统一转为可显示错误
                last = DataUnavailableError(f"东方财富请求失败：{exc}")
            if attempt < self._attempts - 1:
                self._sleep(self._backoff * (attempt + 1))
        assert last is not None
        raise last

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
        except OSError as exc:
            # RemoteDisconnected / ConnectionReset / socket.timeout 等都是 OSError 子类。
            # 必须转成可显示的 DATA_UNAVAILABLE，不能让原始异常穿透到界面。
            raise DataUnavailableError(f"东方财富连接中断：{exc}") from exc

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
        payload = self._parse_payload(self._fetch_text(url), info.symbol)
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


class SinaPriceProvider:
    """新浪财经日线源（A 股兜底）。

    为什么需要第三条路
    ------------------
    东方财富的 ``push2his`` 主机在部分网络环境下对**任何**请求都返回
    ``Empty reply from server``（连无参数裸路径也一样），Yahoo 则经常
    ``Too Many Requests``。两条路同时断掉时系统完全取不到数据。
    新浪的 ``getKLineData`` 在同样网络下可用，因此作为 A 股第三兜底。

    复权口径（重要）
    ----------------
    该接口返回的是**不复权**价格，与东方财富的 ``fqt=1``（前复权）口径不同。
    因此 ``adjusted=False`` 会如实写进 ValidationReport——**不冒充复权数据**。
    除权除息日附近的形态可能因此与复权口径有差异，界面需据此提示使用者。
    这也是本 Provider 排在东方财富之后的原因。
    """

    name = "sina"
    _HOST = (
        "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "CN_MarketData.getKLineData"
    )

    def __init__(
        self,
        opener: Callable[[str], str] | None = None,
        *,
        timeout: float = 15.0,
        max_bars: int = 1500,
        attempts: int = 3,
        backoff: float = 1.5,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._opener = opener or self._default_opener
        self._timeout = timeout
        self._max_bars = max_bars
        self._attempts = max(1, attempts)
        self._backoff = backoff
        self._sleep = sleep if sleep is not None else time.sleep

    def _default_opener(self, url: str) -> str:
        request = urllib.request.Request(  # noqa: S310 - 固定 https 主机
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn/",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                if response.status != 200:
                    raise DataUnavailableError(f"新浪返回 HTTP {response.status}")
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise DataUnavailableError(f"新浪网络请求失败：{exc.reason}") from exc
        except OSError as exc:
            raise DataUnavailableError(f"新浪连接中断：{exc}") from exc

    def _fetch_text(self, url: str) -> str:
        last: DataUnavailableError | None = None
        for attempt in range(self._attempts):
            try:
                return self._opener(url)
            except DataUnavailableError as exc:
                last = exc
            except Exception as exc:  # noqa: BLE001 - 统一转为可显示错误
                last = DataUnavailableError(f"新浪请求失败：{exc}")
            if attempt < self._attempts - 1:
                self._sleep(self._backoff * (attempt + 1))
        assert last is not None
        raise last

    @staticmethod
    def _sina_symbol(info: SymbolInfo) -> str:
        """A 股代码到新浪口径：沪市 sh600000，深市 sz159915。"""
        if not is_a_share(info):
            raise ValueError(f"{info.symbol} 不是 A 股标的，无法映射新浪代码")
        prefix = "sh" if info.market is Market.CN_SH else "sz"
        return f"{prefix}{info.bare_code}"

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        if not is_a_share(info):
            raise DataUnavailableError(f"{info.symbol} 不是 A 股标的，新浪源不适用")

        params = {
            "symbol": self._sina_symbol(info),
            "scale": "240",   # 240 分钟 = 日线
            "ma": "no",
            "datalen": str(self._max_bars),
        }
        url = f"{self._HOST}?{urllib.parse.urlencode(params)}"
        bars_raw = self._parse_payload(self._fetch_text(url), info.symbol)
        bars, report = validate_bars(
            bars_raw,
            symbol=info.symbol,
            provider=self.name,
            # 如实标记：新浪该接口是不复权价格，不得冒充复权。
            adjusted=False,
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=info.symbol,
            bars=bars,
            report=report,
            info=info,
        )

    @staticmethod
    def _parse_payload(text: str, symbol: str) -> pd.DataFrame:
        """解析 ``[{day,open,high,low,close,volume}, ...]``。

        新浪偶尔返回单引号或裸键的类 JSON，这里先做一次容错修正再解析；
        修正失败即报 DATA_UNAVAILABLE，不猜测内容。
        """
        payload_text = text.strip()
        if not payload_text:
            raise DataUnavailableError(f"{symbol} 新浪返回空内容")
        try:
            payload: Any = json.loads(payload_text)
        except json.JSONDecodeError:
            # 裸键 {day:"..."} → {"day":"..."}
            repaired = re.sub(r"([{,])\s*([A-Za-z_]\w*)\s*:", r'\1"\2":', payload_text)
            try:
                payload = json.loads(repaired)
            except json.JSONDecodeError as exc:
                raise DataUnavailableError(f"{symbol} 新浪返回非 JSON 内容") from exc

        if not isinstance(payload, list) or not payload:
            raise DataUnavailableError(f"{symbol} 新浪没有返回日线数据")

        records: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise DataUnavailableError(f"{symbol} 新浪 kline 元素格式异常: {item!r}")
            missing = {"day", "open", "high", "low", "close", "volume"} - item.keys()
            if missing:
                raise DataUnavailableError(
                    f"{symbol} 新浪 kline 缺少字段 {sorted(missing)}: {item!r}"
                )
            try:
                records.append(
                    {
                        "date": item["day"],
                        "open": float(item["open"]),
                        "high": float(item["high"]),
                        "low": float(item["low"]),
                        "close": float(item["close"]),
                        "volume": float(item["volume"]),
                    }
                )
            except (TypeError, ValueError) as exc:
                raise DataUnavailableError(
                    f"{symbol} 新浪 kline 数值无法解析: {item!r}"
                ) from exc

        frame = pd.DataFrame(records)
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.set_index("date")


class ChainedPriceProvider:
    """按顺序尝试多个 Provider，全部失败则报告全部原因。

    A 股优先东方财富（复权 + 交易日更贴近本地口径），其余走 Yahoo。
    """

    name = "chained"

    #: A 股尝试顺序。东方财富为前复权口径，优先；新浪为不复权兜底，
    #: 排在 Yahoo 之前是因为 Yahoo 对 A 股限流严重且常年 429。
    _A_SHARE_ORDER = ("eastmoney", "sina")

    def __init__(self, providers: list[PriceProvider]) -> None:
        if not providers:
            raise ValueError("至少需要一个 Provider")
        self._providers = providers

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)

        def rank(provider: PriceProvider) -> int:
            if not is_a_share(info):
                return 0
            try:
                return self._A_SHARE_ORDER.index(provider.name)
            except ValueError:
                return len(self._A_SHARE_ORDER)

        ordered = sorted(self._providers, key=rank)
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
    """默认行情源组合。

    A 股实际尝试顺序由 ``ChainedPriceProvider._A_SHARE_ORDER`` 决定：
    东方财富（前复权）→ 新浪（不复权兜底）→ Yahoo。
    """
    return ChainedPriceProvider(
        [YahooPriceProvider(), EastmoneyPriceProvider(), SinaPriceProvider()]
    )


__all__ = [
    "ChainedPriceProvider",
    "EastmoneyPriceProvider",
    "PriceData",
    "PriceProvider",
    "SinaPriceProvider",
    "YahooPriceProvider",
    "default_provider",
]
