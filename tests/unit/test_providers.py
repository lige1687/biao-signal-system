"""Provider 测试：不依赖网络，使用假客户端。"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from lei_signal.data.cache import ParquetCache
from lei_signal.data.providers import (
    ChainedPriceProvider,
    EastmoneyPriceProvider,
    TencentPriceProvider,
    YahooPriceProvider,
)
from lei_signal.data.validation import DataUnavailableError


def _yahoo_frame(rows: int = 30) -> pd.DataFrame:
    close = np.linspace(10.0, 20.0, rows)
    return pd.DataFrame(
        {
            "Open": close - 0.1,
            "High": close + 0.2,
            "Low": close - 0.2,
            "Close": close,
            "Volume": [1_000_000] * rows,
        },
        index=pd.to_datetime(pd.bdate_range("2024-01-02", periods=rows), utc=True),
    )


class FakeTicker:
    info = {"shortName": "Invesco QQQ Trust"}

    def __init__(self, rows: int = 30) -> None:
        self._rows = rows
        self.last_kwargs: dict[str, object] = {}

    def history(self, **kwargs: object) -> pd.DataFrame:
        self.last_kwargs = kwargs
        return _yahoo_frame(self._rows)


def test_yahoo_provider_normalizes_columns_and_requests_adjusted_data() -> None:
    ticker = FakeTicker()
    provider = YahooPriceProvider(ticker_factory=lambda _: ticker, sleep=lambda _: None)
    data = provider.fetch("qqq")

    assert data.symbol == "QQQ"
    assert data.display_name == "Invesco QQQ Trust"
    assert data.bars.columns.tolist() == ["open", "high", "low", "close", "volume"]
    assert data.bars.index.tz is None
    # 必须请求复权数据
    assert ticker.last_kwargs["auto_adjust"] is True
    assert ticker.last_kwargs["interval"] == "1d"
    assert data.report.adjusted is True
    assert data.report.provider == "yahoo"


def test_yahoo_provider_reports_data_unavailable_on_empty_result() -> None:
    class EmptyTicker:
        info: dict[str, str] = {}

        def history(self, **_: object) -> pd.DataFrame:
            return pd.DataFrame()

    provider = YahooPriceProvider(
        ticker_factory=lambda _: EmptyTicker(), sleep=lambda _: None
    )
    with pytest.raises(DataUnavailableError, match="没有找到"):
        provider.fetch("NOPE")


def test_yahoo_provider_wraps_network_errors_in_chinese() -> None:
    def boom(_: str) -> object:
        raise RuntimeError("connection reset")

    with pytest.raises(DataUnavailableError, match="无法获取"):
        YahooPriceProvider(ticker_factory=boom, sleep=lambda _: None).fetch("QQQ")


def _eastmoney_payload(rows: int = 30) -> str:
    klines = []
    for i in range(rows):
        day = pd.Timestamp("2024-01-02") + pd.Timedelta(days=i)
        close = 10.0 + i * 0.1
        klines.append(
            f"{day.date()},{close - 0.05},{close},{close + 0.08},{close - 0.09},"
            f"{1_000_000 + i},{12345678},1.2"
        )
    return json.dumps({"data": {"code": "159915", "market": 0, "name": "创业板ETF",
                                "klines": klines}})


def test_eastmoney_provider_parses_klines_and_requests_adjusted() -> None:
    captured: dict[str, str] = {}

    def opener(url: str) -> str:
        captured["url"] = url
        return _eastmoney_payload()

    provider = EastmoneyPriceProvider(opener=opener, sleep=lambda _: None)
    data = provider.fetch("159915")

    assert data.symbol == "159915.SZ"
    assert data.display_name == "创业板ETF"
    assert len(data.bars) == 30
    assert data.bars.columns.tolist() == ["open", "high", "low", "close", "volume"]
    # 改造点：必须使用前复权 fqt=1，而不是旧实现的 fqt=0
    assert "fqt=1" in captured["url"]
    assert "secid=0.159915" in captured["url"]
    assert data.report.adjusted is True


def test_eastmoney_provider_rejects_non_a_share() -> None:
    provider = EastmoneyPriceProvider(opener=lambda _: "{}", sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="不是 A 股"):
        provider.fetch("QQQ")


def test_eastmoney_provider_surfaces_malformed_payloads() -> None:
    with pytest.raises(DataUnavailableError, match="非 JSON"):
        EastmoneyPriceProvider(
            opener=lambda _: "<html>error</html>", sleep=lambda _: None
        ).fetch("159915")
    with pytest.raises(DataUnavailableError, match="缺少 data"):
        EastmoneyPriceProvider(opener=lambda _: '{"rc":1}', sleep=lambda _: None).fetch("159915")
    with pytest.raises(DataUnavailableError, match="没有返回日线"):
        EastmoneyPriceProvider(
            opener=lambda _: '{"data":{"code":"159915","market":0,"klines":[]}}',
            sleep=lambda _: None,
        ).fetch("159915")


def test_chained_provider_prefers_eastmoney_for_a_shares() -> None:
    order: list[str] = []

    class Recorder:
        def __init__(self, name: str, succeed: bool) -> None:
            self.name = name
            self._succeed = succeed

        def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN202
            order.append(self.name)
            if not self._succeed:
                raise DataUnavailableError(f"{self.name} 不可用")
            return EastmoneyPriceProvider(
                opener=lambda _: _eastmoney_payload(), sleep=lambda _: None
            ).fetch(symbol)

    chained = ChainedPriceProvider([Recorder("yahoo", False), Recorder("eastmoney", True)])
    chained.fetch("159915")
    assert order[0] == "eastmoney"


def test_chained_provider_reports_all_failures() -> None:
    class Failing:
        def __init__(self, name: str) -> None:
            self.name = name

        def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN202
            raise DataUnavailableError(f"{self.name} 挂了")

    chained = ChainedPriceProvider([Failing("yahoo"), Failing("eastmoney")])
    with pytest.raises(DataUnavailableError, match="所有行情源均不可用") as exc:
        chained.fetch("QQQ")
    assert "yahoo" in str(exc.value)
    assert "eastmoney" in str(exc.value)


def test_parquet_cache_roundtrip_and_corruption_is_a_miss(tmp_path) -> None:  # noqa: ANN001
    cache = ParquetCache(tmp_path)
    frame = _yahoo_frame(25).rename(columns=str.lower)
    frame.index = frame.index.tz_localize(None)
    # provider 必须显式声明为可信来源，否则命中会被来源校验拦掉，
    # 下面的「损坏文件视为未命中」就会因为错误的原因通过。
    entry = cache.write("QQQ", frame, provider="yahoo")
    assert entry.rows == 25

    loaded = cache.read("QQQ", required_columns=("open", "close"))
    assert loaded is not None and len(loaded) == 25

    # 缺列视为未命中
    assert cache.read("QQQ", required_columns=("nonexistent",)) is None
    # 损坏文件视为未命中，不得抛出
    entry.path.write_bytes(b"not parquet")
    assert cache.read("QQQ") is None
    assert cache.read("NEVER_FETCHED") is None


def test_eastmoney_retries_transient_failures_before_giving_up() -> None:
    """瞬时中断应重试；成功后不得报告不可用。"""
    calls: list[int] = []

    def flaky(_: str) -> str:
        calls.append(1)
        if len(calls) < 3:
            raise DataUnavailableError("东方财富连接中断：RemoteDisconnected")
        return _eastmoney_payload()

    provider = EastmoneyPriceProvider(opener=flaky, attempts=3, sleep=lambda _: None)
    data = provider.fetch("159915")
    assert len(calls) == 3
    assert len(data.bars) == 30


def test_eastmoney_reports_last_error_after_exhausting_retries() -> None:
    attempts: list[int] = []

    def always_fail(_: str) -> str:
        attempts.append(1)
        raise DataUnavailableError("东方财富连接中断：RemoteDisconnected")

    provider = EastmoneyPriceProvider(opener=always_fail, attempts=3, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="连接中断"):
        provider.fetch("159915")
    assert len(attempts) == 3


def test_yahoo_retries_rate_limit_then_succeeds() -> None:
    state: list[int] = []

    class Flaky:
        info = {"shortName": "Invesco QQQ Trust"}

        def history(self, **_: object) -> pd.DataFrame:
            state.append(1)
            if len(state) < 2:
                raise RuntimeError("Too Many Requests. Rate limited.")
            return _yahoo_frame(30)

    provider = YahooPriceProvider(
        ticker_factory=lambda _: Flaky(), attempts=3, sleep=lambda _: None
    )
    data = provider.fetch("QQQ")
    assert len(state) == 2
    assert len(data.bars) == 30


def test_network_errors_are_always_data_unavailable_not_raw_exceptions() -> None:
    """OSError 子类(RemoteDisconnected 等)不得穿透到界面。"""
    from http.client import RemoteDisconnected

    def disconnect(_: str) -> str:
        raise RemoteDisconnected("Remote end closed connection without response")

    provider = EastmoneyPriceProvider(opener=disconnect, attempts=1, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError):
        provider.fetch("159915")


# ---------- 腾讯 provider ----------

def _tencent_payload(rows: int = 30, market_key: str = "sz159915") -> str:
    qfqday = []
    for i in range(rows):
        day = pd.Timestamp("2024-01-02") + pd.Timedelta(days=i)
        close = 10.0 + i * 0.1
        qfqday.append([
            day.strftime("%Y-%m-%d"),
            f"{close - 0.05:.4f}",   # open
            f"{close:.4f}",          # close
            f"{close + 0.08:.4f}",   # high
            f"{close - 0.09:.4f}",   # low
            f"{1_000_000 + i}",      # volume
        ])
    return json.dumps({
        "code": 0,
        "msg": "",
        "data": {market_key: {"qfqday": qfqday, "qfqfactor": 1.0}},
    })


def test_tencent_provider_parses_qfqday_and_is_marked_adjusted() -> None:
    captured: dict[str, str] = {}

    def opener(url: str) -> str:
        captured["url"] = url
        return _tencent_payload()

    provider = TencentPriceProvider(opener=opener, sleep=lambda _: None)
    data = provider.fetch("159915")

    assert data.symbol == "159915.SZ"
    assert len(data.bars) == 30
    assert data.bars.columns.tolist() == ["open", "high", "low", "close", "volume"]
    # 必须显式请求 qfq 前复权
    assert "qfq" in captured["url"]
    assert "param=sz159915" in captured["url"]
    assert data.report.adjusted is True
    assert data.report.provider == "tencent"


def test_tencent_provider_uses_sh_prefix_for_shanghai() -> None:
    captured: dict[str, str] = {}

    def opener(url: str) -> str:
        captured["url"] = url
        return _tencent_payload(market_key="sh600000")

    provider = TencentPriceProvider(opener=opener, sleep=lambda _: None)
    provider.fetch("600000")
    assert "param=sh600000" in captured["url"]


def test_tencent_provider_rejects_non_a_share() -> None:
    provider = TencentPriceProvider(opener=lambda _: "{}", sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="不是 A 股"):
        provider.fetch("QQQ")


def test_tencent_provider_surfaces_qfqday_missing() -> None:
    """qfqday 和 day 都缺失时必须显式报错。"""
    payload = json.dumps({"code": 0, "data": {"sz159915": {}}})
    provider = TencentPriceProvider(opener=lambda _: payload, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="未返回 qfqday/day"):
        provider.fetch("159915")


def test_tencent_provider_etf_falls_back_to_unadjusted_day() -> None:
    """ETF 场景：qfqday 缺失但 day 有数据时，回退到不复权并如实标记。"""
    day_rows = []
    for i in range(30):
        day = pd.Timestamp("2024-01-02") + pd.Timedelta(days=i)
        close = 10.0 + i * 0.1
        day_rows.append([
            day.strftime("%Y-%m-%d"),
            f"{close - 0.05:.4f}",
            f"{close:.4f}",
            f"{close + 0.08:.4f}",
            f"{close - 0.09:.4f}",
            f"{1_000_000 + i}",
        ])
    # 只有 day，没有 qfqday —— ETF 常见情况
    payload = json.dumps({"code": 0, "data": {"sh515130": {"day": day_rows}}})
    provider = TencentPriceProvider(opener=lambda _: payload, sleep=lambda _: None)
    data = provider.fetch("515130")

    assert data.symbol == "515130.SS"
    assert len(data.bars) == 30
    # 必须如实标记不复权
    assert data.report.adjusted is False
    # 必须有警告说明回退原因
    assert any("未返回前复权" in str(w) for w in data.report.warnings)


def test_tencent_provider_surfaces_error_code() -> None:
    payload = json.dumps({"code": 1, "msg": "param invalid"})
    provider = TencentPriceProvider(opener=lambda _: payload, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="腾讯返回错误"):
        provider.fetch("159915")


def test_tencent_provider_surfaces_malformed_payloads() -> None:
    with pytest.raises(DataUnavailableError, match="非 JSON"):
        TencentPriceProvider(
            opener=lambda _: "<html>error</html>", sleep=lambda _: None
        ).fetch("159915")
    with pytest.raises(DataUnavailableError, match="缺少 data"):
        TencentPriceProvider(
            opener=lambda _: '{"code":0,"rc":1}', sleep=lambda _: None
        ).fetch("159915")
    with pytest.raises(DataUnavailableError, match="qfqday 元素字段不足"):
        TencentPriceProvider(
            opener=lambda _: json.dumps({"code": 0, "data": {"sz159915": {"qfqday": [[]]}}}),
            sleep=lambda _: None,
        ).fetch("159915")


def test_tencent_provider_retries_transient_failures_then_succeeds() -> None:
    calls: list[int] = []

    def flaky(_: str) -> str:
        calls.append(1)
        if len(calls) < 3:
            raise DataUnavailableError("腾讯连接中断：RemoteDisconnected")
        return _tencent_payload()

    provider = TencentPriceProvider(opener=flaky, attempts=3, sleep=lambda _: None)
    data = provider.fetch("159915")
    assert len(calls) == 3
    assert len(data.bars) == 30


def test_chained_provider_prefers_tencent_for_a_shares() -> None:
    """腾讯是 A 股新主源，必须排在东方财富之前。"""
    order: list[str] = []

    class Recorder:
        def __init__(self, name: str, succeed: bool) -> None:
            self.name = name
            self._succeed = succeed

        def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN202
            order.append(self.name)
            if not self._succeed:
                raise DataUnavailableError(f"{self.name} 不可用")
            return TencentPriceProvider(
                opener=lambda _: _tencent_payload(), sleep=lambda _: None
            ).fetch(symbol)

    chained = ChainedPriceProvider(
        [Recorder("yahoo", False), Recorder("eastmoney", False), Recorder("tencent", True)]
    )
    chained.fetch("159915")
    assert order[0] == "tencent"


def test_chained_provider_skips_sina_when_tencent_present() -> None:
    """Sina 已退出默认链路——默认 Provider 链中不应出现它。"""
    from lei_signal.data.providers import default_provider

    chain = default_provider()._providers  # noqa: SLF001 - 测试可见私有
    names = [provider.name for provider in chain]
    assert "sina" not in names
    assert names[0] == "tencent"
