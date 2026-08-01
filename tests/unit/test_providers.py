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
    provider = YahooPriceProvider(ticker_factory=lambda _: ticker)
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

    provider = YahooPriceProvider(ticker_factory=lambda _: EmptyTicker())
    with pytest.raises(DataUnavailableError, match="没有找到"):
        provider.fetch("NOPE")


def test_yahoo_provider_wraps_network_errors_in_chinese() -> None:
    def boom(_: str) -> object:
        raise RuntimeError("connection reset")

    with pytest.raises(DataUnavailableError, match="无法获取"):
        YahooPriceProvider(ticker_factory=boom).fetch("QQQ")


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

    provider = EastmoneyPriceProvider(opener=opener)
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
    provider = EastmoneyPriceProvider(opener=lambda _: "{}")
    with pytest.raises(DataUnavailableError, match="不是 A 股"):
        provider.fetch("QQQ")


def test_eastmoney_provider_surfaces_malformed_payloads() -> None:
    with pytest.raises(DataUnavailableError, match="非 JSON"):
        EastmoneyPriceProvider(opener=lambda _: "<html>error</html>").fetch("159915")
    with pytest.raises(DataUnavailableError, match="缺少 data"):
        EastmoneyPriceProvider(opener=lambda _: '{"rc":1}').fetch("159915")
    with pytest.raises(DataUnavailableError, match="没有返回日线"):
        EastmoneyPriceProvider(
            opener=lambda _: '{"data":{"code":"159915","market":0,"klines":[]}}'
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
            return EastmoneyPriceProvider(opener=lambda _: _eastmoney_payload()).fetch(symbol)

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
    entry = cache.write("QQQ", frame)
    assert entry.rows == 25

    loaded = cache.read("QQQ", required_columns=("open", "close"))
    assert loaded is not None and len(loaded) == 25

    # 缺列视为未命中
    assert cache.read("QQQ", required_columns=("nonexistent",)) is None
    # 损坏文件视为未命中，不得抛出
    entry.path.write_bytes(b"not parquet")
    assert cache.read("QQQ") is None
    assert cache.read("NEVER_FETCHED") is None
