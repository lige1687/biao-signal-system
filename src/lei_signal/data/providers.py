"""行情 Provider：Yahoo、东方财富（A 股增强）、腾讯（A 股前复权主源）。

Provider 接口可替换。任何数据问题都通过 DataUnavailableError 显式暴露，
不得静默返回空结果。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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


class YahooV8PriceProvider:
    """Yahoo Finance 公开 v8 图表 API（不走 yfinance 库）。

    为什么单独写一个
    ----------------
    之前的 ``YahoPriceProvider`` 用 ``yfinance.Ticker.history`` 走的是
    query2 端点 + 复杂的 cookie/crumb 机制，在共享 IP 段上会触发
    限流（Too Many Requests）。但 Yahoo 的公开 v8 图表 API
    （``query1.finance.yahoo.com/v8/finance/chart/...``）走的是另一条
    端点，限流阈值更宽松，实测连续 5 次稳定。

    覆盖范围
    --------
    几乎所有 Yahoo Finance 支持的代码：A 股、港股、美股、ETF、加密货币，
    以及**海外指数** ``^KS11 ^GSPC ^IXIC ^HSI ^DJI ^NDX ^N225``——
    这些在 yfinance 端点限流时仍可访问。

    限制
    ----
    只取日线（interval=1d），最多 2 年历史。如需更久，把 ``range`` 改成
    ``max`` 即可。
    """

    name = "yahoo_v8"

    def __init__(
        self,
        opener: Callable[[str], str] | None = None,
        *,
        timeout: float = 10.0,
        range_param: str = "2y",
    ) -> None:
        self._opener = opener or self._default_opener
        self._timeout = timeout
        self._range = range_param

    def _default_opener(self, url: str) -> str:
        request = urllib.request.Request(  # noqa: S310
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            return response.read().decode("utf-8", errors="replace")

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{urllib.parse.quote(info.symbol)}?interval=1d&range={self._range}"
        )
        try:
            text = self._opener(url)
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise DataUnavailableError(f"Yahoo v8 请求失败：{reason}") from exc

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DataUnavailableError(f"Yahoo v8 返回非 JSON：{text[:80]}") from exc

        chart = payload.get("chart") or {}
        if chart.get("error"):
            raise DataUnavailableError(
                f"Yahoo v8 错误：{chart['error'].get('description', 'unknown')}"
            )
        results = chart.get("result") or []
        if not results:
            raise DataUnavailableError(f"Yahoo v8 无数据：{info.symbol}")

        result = results[0]
        meta = result.get("meta") or {}
        ts = result.get("timestamp") or []
        quote = (result.get("indicators") or {}).get("quote") or [{}]
        q = quote[0]
        opens = q.get("open") or []
        highs = q.get("high") or []
        lows = q.get("low") or []
        closes = q.get("close") or []
        volumes = q.get("volume") or []

        # Yahoo v8 返回的 timestamp 是 UTC 秒，index 用交易日本地日期。
        records: list[dict[str, Any]] = []
        for i, t in enumerate(ts):
            try:
                if None in (opens[i], highs[i], lows[i], closes[i]):
                    continue
                date = datetime.fromtimestamp(t, tz=UTC).date()
                records.append(
                    {
                        "date": date,
                        "open": float(opens[i]),
                        "high": float(highs[i]),
                        "low": float(lows[i]),
                        "close": float(closes[i]),
                        "volume": float(volumes[i]) if volumes[i] is not None else 0.0,
                    }
                )
            except (TypeError, ValueError):
                continue

        if len(records) < min_rows:
            raise DataUnavailableError(
                f"Yahoo v8 只返回 {len(records)} 根日K线，至少需要 {min_rows} 根"
            )

        frame = pd.DataFrame(records).set_index("date")
        bars, report = validate_bars(
            frame,
            symbol=info.symbol,
            provider=self.name,
            adjusted=True,  # Yahoo 已是复权价
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=meta.get("longName") or meta.get("shortName") or info.symbol,
            bars=bars,
            report=report,
            info=info,
        )


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
                return response.read().decode("utf-8-sig")
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


class TencentPriceProvider:
    """腾讯财经日线源（A 股前复权主源）。

    为什么新增
    ----------
    腾讯 ``web.ifzq.gtimg.cn`` 接口对 A 股前复权日线稳定可用，且不需要 token、
    不触发东方财富偶发的 ``Empty reply from server`` 也不触发 Yahoo 的 429 限流。
    已在 A 股路径中放在东方财富之前，避免任何 A 股用户看到「新浪不复权」标签。

    复权口径（重要）
    ---------------
    优先使用 ``qfq``（前复权），与东方财富 ``fqt=1`` 口径一致；因此
    ``adjusted=True`` 会如实写进 ValidationReport——可与东方财富互为对照。

    ETF 回退
    --------
    部分 ETF 在腾讯接口下不返回 ``qfqday``（ETF 分红拆股极少，前复权无意义），
    但会返回 ``day``（不复权）。此时**回退到 ``day`` 并如实标记 ``adjusted=False``**，
    不冒充前复权。界面会据此提示「未复权」，LEI 信号在除权日附近可能有形态偏差。
    """

    name = "tencent"
    _HOST = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

    def __init__(
        self,
        opener: Callable[[str], str] | None = None,
        *,
        timeout: float = 10.0,
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
                "Referer": "https://gu.qq.com/",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                if response.status != 200:
                    raise DataUnavailableError(f"腾讯返回 HTTP {response.status}")
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise DataUnavailableError(f"腾讯网络请求失败：{exc.reason}") from exc
        except OSError as exc:
            raise DataUnavailableError(f"腾讯连接中断：{exc}") from exc

    def _fetch_text(self, url: str) -> str:
        last: DataUnavailableError | None = None
        for attempt in range(self._attempts):
            try:
                return self._opener(url)
            except DataUnavailableError as exc:
                last = exc
            except Exception as exc:  # noqa: BLE001 - 统一转为可显示错误
                last = DataUnavailableError(f"腾讯请求失败：{exc}")
            if attempt < self._attempts - 1:
                self._sleep(self._backoff * (attempt + 1))
        assert last is not None
        raise last

    @staticmethod
    def _tencent_symbol(info: SymbolInfo) -> str:
        """A 股代码到腾讯口径：沪市 sh600000，深市 sz159915。"""
        if not is_a_share(info):
            raise ValueError(f"{info.symbol} 不是 A 股标的，无法映射腾讯代码")
        prefix = "sh" if info.market is Market.CN_SH else "sz"
        return f"{prefix}{info.bare_code}"

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        if not is_a_share(info):
            raise DataUnavailableError(f"{info.symbol} 不是 A 股标的，腾讯源不适用")

        params = {
            "param": f"{self._tencent_symbol(info)},day,,,{self._max_bars},qfq",
        }
        url = f"{self._HOST}?{urllib.parse.urlencode(params)}"
        bars_raw, adjusted = self._parse_payload(self._fetch_text(url), info.symbol)
        # 不复权回退必须如实标记，避免下游误用。
        warnings: tuple[str, ...] = ()
        if not adjusted:
            warnings = (
                "tencent_etf_unadjusted",
                f"{info.symbol} 腾讯未返回前复权数据，已回退到不复权（adjusted=False）。"
                "除权除息日附近形态可能有偏差。",
            )
        bars, report = validate_bars(
            bars_raw,
            symbol=info.symbol,
            provider=self.name,
            adjusted=adjusted,
            min_rows=min_rows,
        )
        # 把 ETF 回退警告并入 ValidationReport.warnings，让 UI 看到。
        if warnings:
            report = ValidationReport(
                rows=report.rows,
                first_date=report.first_date,
                last_date=report.last_date,
                adjusted=report.adjusted,
                provider=report.provider,
                duplicates_removed=report.duplicates_removed,
                warnings=report.warnings + warnings,
            )
        return PriceData(
            symbol=info.symbol,
            display_name=info.symbol,
            bars=bars,
            report=report,
            info=info,
        )

    @staticmethod
    def _parse_payload(text: str, symbol: str) -> tuple[pd.DataFrame, bool]:
        """解析 kline 数组：每行 [日期, 开, 收, 高, 低, 成交量, ...]。

        优先使用 ``qfqday``（前复权）。若该键缺失/为空但 ``day``（不复权）
        存在，则**回退到 ``day``**，返回 ``adjusted=False``——这种情况常见于
        ETF（分红拆股稀少，qfq 无意义）。

        返回 ``(DataFrame, adjusted)``：
        - ``adjusted=True`` 表示前复权（qfqday）
        - ``adjusted=False`` 表示不复权回退（day）

        两者皆无则报错。
        """
        payload_text = text.strip()
        if not payload_text:
            raise DataUnavailableError(f"{symbol} 腾讯返回空内容")
        try:
            payload: dict[str, Any] = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise DataUnavailableError(f"{symbol} 腾讯返回非 JSON 内容") from exc

        # 腾讯在错误时也会返回 200 + code != 0，例如 code=1 + msg="param invalid"
        if int(payload.get("code", 0)) != 0:
            raise DataUnavailableError(
                f"{symbol} 腾讯返回错误：code={payload.get('code')} msg={payload.get('msg')!r}"
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            raise DataUnavailableError(f"{symbol} 腾讯返回缺少 data 字段")
        # 取任意一个子市场（key 是 sh600000 / sz159915 形式）
        market_data = next(
            (value for value in data.values() if isinstance(value, dict)),
            None,
        )
        if market_data is None:
            raise DataUnavailableError(f"{symbol} 腾讯返回缺少行情子对象")

        # 优先 qfqday（前复权）；若缺失则回退 day（不复权），常见于 ETF。
        qfq_rows = market_data.get("qfqday")
        if isinstance(qfq_rows, list) and qfq_rows:
            rows = qfq_rows
            adjusted = True
            key_label = "qfqday"
        else:
            day_rows = market_data.get("day")
            if not isinstance(day_rows, list) or not day_rows:
                raise DataUnavailableError(
                    f"{symbol} 腾讯未返回 qfqday/day（请确认股票代码或稍后重试）"
                )
            rows = day_rows
            adjusted = False
            key_label = "day"

        records: list[dict[str, Any]] = []
        for item in rows:
            if not isinstance(item, list) or len(item) < 6:
                raise DataUnavailableError(
                    f"{symbol} 腾讯 {key_label} 元素字段不足: {item!r}"
                )
            try:
                records.append(
                    {
                        "date": item[0],
                        "open": float(item[1]),
                        "close": float(item[2]),
                        "high": float(item[3]),
                        "low": float(item[4]),
                        "volume": float(item[5]),
                    }
                )
            except (TypeError, ValueError) as exc:
                raise DataUnavailableError(
                    f"{symbol} 腾讯 {key_label} 数值无法解析: {item!r}"
                ) from exc

        frame = pd.DataFrame(records)
        frame["date"] = pd.to_datetime(frame["date"])
        return frame.set_index("date"), adjusted


class TencentGlobalIndexProvider(TencentPriceProvider):
    """腾讯财经海外指数日线源（纳指 / 标普500 / 恒生科技）。

    为什么新增
    ----------
    Yahoo 对免费调用做 IP 级 429 限流（实测 curl 直连同样 429），导致海外
    大盘指数长期不可用。腾讯 ``web.ifzq.gtimg.cn`` 同一接口也覆盖海外指数，
    且返回中文名，不需要 token。

    覆盖范围与实测稳定性（2026-08 实测）
    ------------------------------------
    - ``^HSTECH`` → ``hkHSTECH``：稳定，可取 500+ 根。
    - ``^IXIC`` / ``^GSPC`` → ``usIXIC`` / ``usINX``：**间歇可用**。同一 URL
      有时返回 320 根、有时返回 0/1 根（腾讯侧限流）。因此保留父类的重试与
      backoff，并依赖 Parquet 缓存兜底：抓到一次后，限流期间界面显示缓存数据
      并标注「缓存兜底」，而不是空白。
    - ``^KS11``（韩国 KOSPI）腾讯**没有**对应标的（``usKS11``/``krKS11`` 均无
      日线），故不在映射表中——由链路继续下探 Yahoo/东财。

    条数上限
    --------
    美股指数请求 800/1500 根只会返回 1 根（隐性上限），实测 320 根可用，
    因此海外指数固定用 ``_GLOBAL_MAX_BARS``。320 根日线覆盖约 15 个月，
    足够 EMA120 与 LEI 三色计算。

    复权口径
    --------
    指数不存在除权除息，腾讯只返回 ``day``（不复权）。父类会如实标记
    ``adjusted=False``；对指数而言这是正确口径，不是数据缺陷。
    """

    name = "tencent_global"

    #: 实测上限：>320 时腾讯美股接口只回 1 根。
    _GLOBAL_MAX_BARS = 320

    #: Yahoo 口径符号 → 腾讯口径符号 + 中文名。
    #: 只登记实测有日线返回的标的；KOSPI 无数据故不登记。
    _GLOBAL_SYMBOLS: dict[str, tuple[str, str]] = {
        "^IXIC": ("usIXIC", "纳斯达克"),
        "^GSPC": ("usINX", "标普500"),
        "^HSTECH": ("hkHSTECH", "恒生科技指数"),
        "^DJI": ("usDJI", "道琼斯"),
        "^NDX": ("usNDX", "纳斯达克100"),
        "^HSI": ("hkHSI", "恒生指数"),
    }

    @classmethod
    def supports(cls, symbol: str) -> bool:
        return symbol.strip().upper() in cls._GLOBAL_SYMBOLS

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        mapping = self._GLOBAL_SYMBOLS.get(info.symbol)
        if mapping is None:
            raise DataUnavailableError(
                f"{info.symbol} 不在腾讯海外指数映射表中，腾讯海外源不适用"
            )
        tencent_code, display_name = mapping

        params = {"param": f"{tencent_code},day,,,{self._GLOBAL_MAX_BARS},qfq"}
        url = f"{self._HOST}?{urllib.parse.urlencode(params)}"
        bars_raw, adjusted = self._parse_payload(self._fetch_text(url), info.symbol)
        bars, report = validate_bars(
            bars_raw,
            symbol=info.symbol,
            provider=self.name,
            adjusted=adjusted,
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=display_name,
            bars=bars,
            report=report,
            info=info,
        )


def _classify_error(exc: DataUnavailableError) -> str:
    """把底层 Provider 错误分类成用户能理解的中文。

    分类规则：
    - 包含「限流」「429」「Too Many Requests」→ 限流
    - 包含「连接中断」「网络请求失败」「Remote end」→ 网络不通
    - 包含「未返回」「没有返回」「没有找到」「不是」→ 无数据
    - 其余保持原样
    """
    msg = str(exc)
    if any(kw in msg for kw in ("限流", "429", "Too Many Requests", "Rate limited")):
        return f"限流：{msg}"
    if any(kw in msg for kw in ("连接中断", "网络请求失败", "Remote end", "Empty reply")):
        return f"网络不通：{msg}"
    if any(kw in msg for kw in ("未返回", "没有返回", "没有找到", "不是 A 股", "空内容")):
        return f"无数据：{msg}"
    return msg


class ChainedPriceProvider:
    """按顺序尝试多个 Provider，全部失败则报告全部原因。

    A 股优先腾讯（前复权、稳定）+ 东方财富（前复权、A 股增强），新浪已从
    默认链路中移除：新浪接口返回不复权价格，会污染 LEI 信号。

    海外指数（^IXIC / ^GSPC / ^HSTECH 等）优先腾讯海外源：Yahoo 对免费调用
    做 IP 级 429 限流，长期不可用；腾讯海外源虽对美股间歇限流，但配合
    Parquet 缓存兜底仍显著优于「完全拿不到」。
    """

    name = "chained"

    #: A 股尝试顺序。腾讯与东方财富都是前复权口径，腾讯在前是因为接口更稳；
    #: 新浪已退出默认链路（不复权，会污染信号）。Yahoo 仍然作为最终兜底。
    _A_SHARE_ORDER = ("tencent", "eastmoney")

    #: 海外指数尝试顺序：Yahoo v8（公开图表 API 稳定）→ 腾讯海外源 →
    #: yfinance Yahoo provider（query2 端点，常被 IP 限流）。
    _GLOBAL_INDEX_ORDER = ("yahoo_v8", "tencent_global", "yahoo")

    def __init__(self, providers: list[PriceProvider]) -> None:
        if not providers:
            raise ValueError("至少需要一个 Provider")
        self._providers = providers

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        info = resolve_symbol(symbol)
        is_global_index = TencentGlobalIndexProvider.supports(info.symbol)

        def rank(provider: PriceProvider) -> int:
            if is_global_index:
                try:
                    return self._GLOBAL_INDEX_ORDER.index(provider.name)
                except ValueError:
                    return len(self._GLOBAL_INDEX_ORDER)
            if not is_a_share(info):
                # 非 A 股、非已登记的海外指数：腾讯海外源不适用，排到最后
                # 避免浪费一次注定失败的请求。
                return 1 if provider.name == "tencent_global" else 0
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
                errors.append(f"[{provider.name}] {_classify_error(exc)}")
        raise DataUnavailableError(
            f"{info.symbol} 所有行情源均不可用：\n" + "\n".join(errors)
        )


class EastmoneySectorProvider:
    """东财板块日线（行业 + 概念）。

    为什么新增
    ----------
    自选和板块 ETF 走势常常 1-2% 的差异，对短线判断板块强度有干扰。
    直接看板块指数本身（成份股加权）更准。东财 ``43.push2his.eastmoney.com``
    的 ``/api/qt/stock/kline/get`` 端点对 ``secid=90.BKxxxx`` 返回完整日线，
    700+ 根，含当日形成中 bar + 成交量——足够跑 LEI 全量分析（EMA120）。

    覆盖范围
    --------
    - 行业板块（t:2，496 个）：电网设备、白色家电、半导体……
    - 概念板块（t:3，503 个）：智能电网、绿色电力、华为概念……
    两类都用同一个东财 secid=90.BKxxxx 拉取。

    主机选择
    --------
    ``push2his.eastmoney.com`` 与 ``push2.eastmoney.com`` 在本机段常被掐。
    用 ``43.push2his.eastmoney.com`` 实测稳定——其它号段也常轮询，失败时
    逐个重试。

    符号约定
    --------
    用户输入 ``BK0457`` → ``resolve_symbol`` 识别为 ``Market.SECTOR``。
    这里再剥出 4 位数字构造 ``secid="90.BK0457"``。
    """

    name = "eastmoney_sector"
    _HOSTS: tuple[str, ...] = (
        "https://43.push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://1.push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://push2hisdelay.eastmoney.com/api/qt/stock/kline/get",
    )
    _SECTOR_SECID_PREFIX = "90."
    _BARE_CODE_RE = __import__("re").compile(r"BK(\d{4})", __import__("re").IGNORECASE)

    def __init__(
        self,
        opener: Callable[[str], str] | None = None,
        *,
        timeout: float = 10.0,
        max_bars: int = 1000,
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

    @classmethod
    def supports(cls, symbol: str) -> bool:
        return bool(cls._BARE_CODE_RE.search(symbol))

    @staticmethod
    def _default_opener(url: str) -> str:
        # push2his 在部分网络环境 TLS 握手被掐（含本机）；走标准 urllib，
        # 失败由上层 _fetch_with_failover 轮询其它号段主机兜底。
        request = urllib.request.Request(  # noqa: S310 - 固定 https 主机
            url,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                if response.status != 200:
                    raise DataUnavailableError(f"东财板块返回 HTTP {response.status}")
                return response.read().decode("utf-8-sig")
        except urllib.error.URLError as exc:
            raise DataUnavailableError(f"东财板块请求失败：{exc.reason}") from exc
        except OSError as exc:
            raise DataUnavailableError(f"东财板块连接中断：{exc}") from exc

    def _fetch_with_failover(self, params: dict[str, str]) -> str:
        """东财各号段轮询；其它异常不向调用方穿透。"""
        last: DataUnavailableError | None = None
        for host in self._HOSTS:
            url = f"{host}?{urllib.parse.urlencode(params)}"
            for attempt in range(self._attempts):
                try:
                    return self._opener(url)
                except DataUnavailableError as exc:
                    last = exc
                except Exception as exc:  # noqa: BLE001
                    last = DataUnavailableError(f"东财板块请求失败：{exc}")
                if attempt < self._attempts - 1:
                    self._sleep(self._backoff * (attempt + 1))
        assert last is not None
        raise last

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        m = self._BARE_CODE_RE.search(symbol)
        if m is None:
            raise DataUnavailableError(
                f"{symbol} 不是东财板块代码（需 BK+4 位数字）"
            )
        bare = f"BK{m.group(1)}"
        info = resolve_symbol(bare)
        secid = f"{self._SECTOR_SECID_PREFIX}{m.group(1)}"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "101",
            "fqt": "1",
            "beg": "0",
            "end": "20500101",
            "lmt": str(self._max_bars),
        }
        text = self._fetch_with_failover(params)
        bars_raw, name = EastmoneyPriceProvider._parse_payload(text, bare)
        bars, report = validate_bars(
            bars_raw,
            symbol=info.symbol,
            provider=self.name,
            adjusted=False,
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=name or bare,
            bars=bars,
            report=report,
            info=info,
        )


class SohuSectorProvider:
    """搜狐申万行业/地域板块日线。

    为什么新增
    ----------
    东财 ``push2his`` 在部分网络环境（含开发者本机）TLS 握手被掐，板块日线
    拿不到。搜狐 ``q.stock.sohu.com/hisHq`` 对 ``zs_00003xxx``（申万一级行业
    + 地域板块，共 54 个）返回 755 根日线，足够跑 LEI 全量分析。

    覆盖范围（实测 2026-08）
    ------------------------
    - 申万一级行业（28 个）：传媒 SW3098、公用事业 SW3111、电子 SW3123、
      通信 SW3125、银行 SW3124、医药生物 SW3116……
    - 地域板块（26 个）：安徽 SW3126、北京 SW3127、广东 SW3130……
    - **概念板块（电网设备/智能电网等细分）搜狐无历史**，需东财（BK 前缀）。

    局限
    ----
    - 盘中无当日形成中 bar：搜狐收盘后才出当日 K。板块强度看收盘形态即可，
      不像个股盘中要操作，可接受。
    - 字段顺序「最低在前、最高在后」（与惯例相反），解析时注意对调。

    符号约定
    --------
    用户输 ``SW3098`` -> resolve_symbol 识别为 Market.SECTOR -> 这里拼
    ``zs_00003098`` 请求。
    """

    name = "sohu_sector"
    _HOST = "https://q.stock.sohu.com/hisHq"
    _CODE_RE = __import__("re").compile(r"SW(\d{4})", __import__("re").IGNORECASE)

    def __init__(
        self,
        opener: Callable[[str], str] | None = None,
        *,
        timeout: float = 12.0,
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

    @classmethod
    def supports(cls, symbol: str) -> bool:
        return bool(cls._CODE_RE.search(symbol))

    @staticmethod
    def _default_opener(url: str) -> str:
        request = urllib.request.Request(  # noqa: S310 - 固定 https 主机
            url,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://q.stock.sohu.com/"},
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:  # noqa: S310
                if response.status != 200:
                    raise DataUnavailableError(f"搜狐板块返回 HTTP {response.status}")
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise DataUnavailableError(f"搜狐板块请求失败：{exc.reason}") from exc
        except OSError as exc:
            raise DataUnavailableError(f"搜狐板块连接中断：{exc}") from exc

    def _fetch_text(self, url: str) -> str:
        last: DataUnavailableError | None = None
        for attempt in range(self._attempts):
            try:
                return self._opener(url)
            except DataUnavailableError as exc:
                last = exc
            except Exception as exc:  # noqa: BLE001
                last = DataUnavailableError(f"搜狐板块请求失败：{exc}")
            if attempt < self._attempts - 1:
                self._sleep(self._backoff * (attempt + 1))
        assert last is not None
        raise last

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        m = self._CODE_RE.search(symbol)
        if m is None:
            raise DataUnavailableError(
                f"{symbol} 不是搜狐板块代码（需 SW+4 位数字）"
            )
        digits = m.group(1)
        bare = f"SW{digits}"
        info = resolve_symbol(bare)
        # 搜狐 code: zs_ + 8 位补零（3xxx 段补成 00003xxx）
        sohu_code = f"zs_{digits.zfill(8)}"
        params = {
            "code": sohu_code,
            "start": "20100101",
            "end": "20500101",
            "stat": "1",
            "order": "A",   # 升序，旧->新
            "period": "d",
        }
        url = f"{self._HOST}?{urllib.parse.urlencode(params)}"
        text = self._fetch_text(url)
        bars_raw = self._parse_payload(text, bare)
        bars, report = validate_bars(
            bars_raw,
            symbol=info.symbol,
            provider=self.name,
            adjusted=False,  # 板块指数无复权
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=bare,  # 搜狐历史接口不返回板块名
            bars=bars,
            report=report,
            info=info,
        )

    @staticmethod
    def _parse_payload(text: str, symbol: str) -> pd.DataFrame:
        """解析搜狐 hisHq。

        字段顺序：[日期, 开盘, 收盘, 涨跌额, 涨跌幅, 最低, 最高, 成交量, 成交额, 换手率]
        注意**最低在前最高在后**，与 OHLC 惯例相反。
        """
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DataUnavailableError(f"{symbol} 搜狐返回非 JSON 内容") from exc
        if not isinstance(payload, list) or not payload:
            raise DataUnavailableError(f"{symbol} 搜狐无板块数据")
        item = payload[0]
        hq = item.get("hq")
        if not isinstance(hq, list) or not hq:
            msg = item.get("msg") if isinstance(item, dict) else "无数据"
            raise DataUnavailableError(f"{symbol} 搜狐板块无历史K线：{msg}")

        records: list[dict[str, Any]] = []
        for row in hq:
            # row: [日期, 开, 收, 涨跌额, 涨跌幅, 低, 高, 量, 额, 换手率]
            if len(row) < 7:
                continue
            try:
                records.append({
                    "open": float(row[1]),
                    "close": float(row[2]),
                    "low": float(row[5]),   # 低在前
                    "high": float(row[6]),  # 高在后
                    "volume": float(row[7]) if len(row) > 7 and row[7] not in ("-", "") else 0.0,
                })
            except (ValueError, TypeError):
                continue
        if not records:
            raise DataUnavailableError(f"{symbol} 搜狐板块日线解析为空")
        df = pd.DataFrame(records)
        df.index = pd.to_datetime([r[0] for r in hq[:len(records)]], errors="coerce")
        df = df[df.index.notna()]
        return df[["open", "high", "low", "close", "volume"]]


class THSBoardProvider:
    """同花顺行业板块日线（主用源）。

    为什么是板块的主路径
    --------------------
    东财 ``push2his`` 在部分网络环境 TLS 被掐；搜狐 ``hisHq`` 有 code 截断 bug。
    同花顺 ``d.10jqka.com.cn/v4/line/bk_{code}/01/{year}.js`` 实测稳定、不限流、
    按年分片返回完整 OHLCV。行业板块 881xxx（90 个）覆盖电网设备、电力、半导体、
    通信等主流行业。

    数据口径
    --------
    - 板块指数（成份股加权），不复权（指数无复权概念）。
    - 按年分片：每 年 一个 js 文件，拼接得到全历史（2018 至今 2000+ 根）。
    - 盘中无当日 bar：同花顺收盘后才出当日 K（板块看收盘形态即可）。
    - 字段顺序：日期,开,收,高,低,量,额,,,,标志位（注意收在高前）。

    cookie 机制
    -----------
    接口需要 ``Cookie: v=<token>``，token 由同花顺的 ``ths.js``（混淆 JS）算出。
    ``ths.js`` 已内嵌为 ``data/assets/ths.js``，用 ``py_mini_racer`` 执行--
    不依赖 akshare 运行时。token 缓存 1 小时（实测有效期远长于此）。

    符号约定
    --------
    用户输 ``TH881278`` -> resolve_symbol 识别为 Market.SECTOR -> 这里取 881278
    请求。display_name 由调用方通过板块列表反查（本 provider 只保证代码可用）。
    """

    name = "ths_board"
    _LINE_URL = "https://d.10jqka.com.cn/v4/line/bk_{code}/01/{year}.js"
    _CODE_RE = __import__("re").compile(r"TH(\d{6})", __import__("re").IGNORECASE)
    _THS_JS_PATH = (
        Path(__file__).resolve().parent / "assets" / "ths.js"
    )
    _COOKIE_TTL = 3600.0  # 1 小时

    def __init__(
        self,
        opener: Callable[[str, dict[str, str]], str] | None = None,
        *,
        timeout: float = 12.0,
        start_year: int = 2018,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._opener = opener or self._default_opener
        self._timeout = timeout
        self._start_year = start_year
        self._sleep = sleep if sleep is not None else time.sleep
        self._cookie: str | None = None
        self._cookie_at: float = 0.0

    @classmethod
    def supports(cls, symbol: str) -> bool:
        return bool(cls._CODE_RE.search(symbol))

    def _compute_cookie(self) -> str:
        """用 ths.js 算 v cookie（py_mini_racer 执行混淆 JS）。"""
        import time as _time
        if self._cookie and (_time.time() - self._cookie_at) < self._COOKIE_TTL:
            return self._cookie
        try:
            import py_mini_racer
        except ImportError as exc:
            raise DataUnavailableError(
                "同花顺板块需要 py_mini_racer（pip install py_mini_racer）"
            ) from exc
        js_text = self._THS_JS_PATH.read_text(encoding="utf-8")
        racer = py_mini_racer.MiniRacer()
        racer.eval(js_text)
        token = racer.call("v")
        if not isinstance(token, str) or not token:
            raise DataUnavailableError("同花顺 ths.js 算出的 v cookie 为空")
        self._cookie = token
        self._cookie_at = _time.time()
        return token

    @staticmethod
    def _default_opener(url: str, headers: dict[str, str]) -> str:
        request = urllib.request.Request(  # noqa: S310 - 固定 https 主机
            url, headers={**headers, "User-Agent": headers.get("User-Agent", "Mozilla/5.0")}
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:  # noqa: S310
                if response.status != 200:
                    raise DataUnavailableError(f"同花顺板块返回 HTTP {response.status}")
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise DataUnavailableError(f"同花顺板块请求失败：{exc.reason}") from exc
        except OSError as exc:
            raise DataUnavailableError(f"同花顺板块连接中断：{exc}") from exc

    def _fetch_year(self, code: str, year: int) -> list[list[str]]:
        url = self._LINE_URL.format(code=code, year=year)
        headers = {
            "Referer": "http://q.10jqka.com.cn",
            "Host": "d.10jqka.com.cn",
            "Cookie": f"v={self._compute_cookie()}",
        }
        text = self._opener(url, headers)
        # 响应：quotebridge_v4_line_bk_881278_01_2026({"data":"...;..."})
        start = text.find("{")
        if start < 0:
            raise DataUnavailableError(f"同花顺板块 {code} {year} 年返回非 JSONP")
        try:
            payload = json.loads(text[start : text.rfind(")")])
        except json.JSONDecodeError as exc:
            raise DataUnavailableError(f"同花顺板块 {code} {year} 年 JSON 解析失败") from exc
        data = payload.get("data")
        if not isinstance(data, str) or not data.strip():
            return []
        return [b.split(",") for b in data.split(";") if b.strip()]

    def fetch(self, symbol: str, *, min_rows: int = 21) -> PriceData:
        m = self._CODE_RE.search(symbol)
        if m is None:
            raise DataUnavailableError(
                f"{symbol} 不是同花顺板块代码（需 TH+6 位数字）"
            )
        code = m.group(1)
        bare = f"TH{code}"
        info = resolve_symbol(bare)

        # 按年拉全历史，拼接
        import datetime as _dt
        end_year = _dt.datetime.now().year
        all_rows: list[list[str]] = []
        last_err: DataUnavailableError | None = None
        for year in range(self._start_year, end_year + 1):
            try:
                rows = self._fetch_year(code, year)
                all_rows.extend(rows)
            except DataUnavailableError as exc:
                # 单年失败不致命（可能该年无数据/限流）；至少拿到一年就继续
                last_err = exc
                # cookie 可能过期，重置后重试一次
                self._cookie = None
        if not all_rows:
            raise last_err or DataUnavailableError(
                f"同花顺板块 {bare} 无任何年份数据"
            )

        bars_raw = self._parse_rows(all_rows, bare)
        bars, report = validate_bars(
            bars_raw,
            symbol=info.symbol,
            provider=self.name,
            adjusted=False,
            min_rows=min_rows,
        )
        return PriceData(
            symbol=info.symbol,
            display_name=bare,
            bars=bars,
            report=report,
            info=info,
        )

    @staticmethod
    def _parse_rows(rows: list[list[str]], symbol: str) -> pd.DataFrame:
        """解析同花顺 line 数据。

        字段：日期,开,收,高,低,量,额,,,,标志位（收在高前，与 OHLC 惯例不同）。
        """
        records: list[dict[str, Any]] = []
        dates: list[str] = []
        for row in rows:
            if len(row) < 7:
                continue
            try:
                records.append({
                    "open": float(row[1]),
                    "close": float(row[2]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "volume": float(row[5]) if row[5] else 0.0,
                })
                dates.append(row[0])
            except (ValueError, TypeError):
                continue
        if not records:
            raise DataUnavailableError(f"{symbol} 同花顺板块日线解析为空")
        df = pd.DataFrame(records)
        df.index = pd.to_datetime(dates, format="%Y%m%d", errors="coerce")
        df = df[df.index.notna()]
        return df[["open", "high", "low", "close", "volume"]]


def default_provider() -> ChainedPriceProvider:
    """默认行情源组合。

    A 股实际尝试顺序由 ``ChainedPriceProvider._A_SHARE_ORDER`` 决定：
    腾讯（前复权）→ 东方财富（前复权）→ Yahoo。
    海外指数由 ``_GLOBAL_INDEX_ORDER`` 决定：Yahoo v8（公开 API）→ 腾讯海外源
    → yfinance Yahoo 兜底。Yahoo v8 在大多数场景下足够稳定，实测连续 5 次无
    限流；只有 v8 都失败时才会降到腾讯海外源/yfinance 兜底。
    新浪已退出默认链路（不复权）。
    """
    return ChainedPriceProvider(
        [
            TencentPriceProvider(),
            TencentGlobalIndexProvider(),
            EastmoneyPriceProvider(),
            THSBoardProvider(),
            EastmoneySectorProvider(),
            SohuSectorProvider(),
            YahooV8PriceProvider(),
            YahooPriceProvider(),
        ]
    )


__all__ = [
    "ChainedPriceProvider",
    "EastmoneyPriceProvider",
    "EastmoneySectorProvider",
    "PriceData",
    "PriceProvider",
    "SinaPriceProvider",
    "SohuSectorProvider",
    "THSBoardProvider",
    "TencentGlobalIndexProvider",
    "TencentPriceProvider",
    "YahooPriceProvider",
    "YahooV8PriceProvider",
    "default_provider",
]
