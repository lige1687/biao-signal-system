"""缓存防污染 + 新浪日线源。

为什么需要这组测试
------------------
真实事故：合成测试行情落进 ``~/.lei_signal_lab/cache/159915.SZ.bars.parquet``，
起点恰好 100.0、``open == close``，而真实创业板 ETF 在 3 元附近。
离线兜底读到它之后分析结论**看起来完全正常**，实际毫无意义——
这类污染不会报错，只会静默产出错误结论，因此必须由测试锁死。

断言写法说明：不用「读到的不是 None」这类存在性断言，
而是逐一枚举来源标记的可信/不可信取值，并验证拒绝行为。
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from lei_signal.data.cache import UNTRUSTED_PROVIDERS, ParquetCache
from lei_signal.data.providers import (
    ChainedPriceProvider,
    DataUnavailableError,
    SinaPriceProvider,
)


def _bars(rows: int = 30, start: float = 3.0) -> pd.DataFrame:
    close = [start + i * 0.01 for i in range(rows)]
    return pd.DataFrame(
        {
            "open": close,
            "high": [c + 0.02 for c in close],
            "low": [c - 0.02 for c in close],
            "close": close,
            "volume": [1_000_000.0] * rows,
        },
        index=pd.bdate_range("2024-01-01", periods=rows),
    )


# ==========================================================================
# 缓存来源标记
# ==========================================================================


def test_trusted_provider_cache_is_readable(tmp_path) -> None:  # noqa: ANN001
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars(), provider="sina")
    frame = cache.read("159915.SZ")
    assert frame is not None
    assert len(frame) == 30


@pytest.mark.parametrize("provider", sorted(UNTRUSTED_PROVIDERS - {""}))
def test_untrusted_provider_cache_is_rejected(tmp_path, provider: str) -> None:  # noqa: ANN001
    """合成/夹具/上传/缓存自身来源，一律不得冒充真实行情。"""
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars(start=100.0), provider=provider)
    assert cache.read("159915.SZ") is None, (
        f"来源 {provider!r} 的缓存被当成真实行情读出——这正是 159915 污染事故的成因"
    )


def test_cache_without_provider_argument_is_rejected(tmp_path) -> None:  # noqa: ANN001
    """不显式声明来源即写入，读取时必须视为未命中。

    默认值 ``unknown`` 属不可信，用来迫使调用方声明来源。
    """
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars())
    assert cache.read("159915.SZ") is None


def test_cache_without_meta_sidecar_is_rejected(tmp_path) -> None:  # noqa: ANN001
    """没有 meta 旁文件的老缓存/手工塞入文件不可信。"""
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars(), provider="sina")
    (tmp_path / "159915.SZ.bars.meta.json").unlink()
    assert cache.read("159915.SZ") is None


def test_corrupt_meta_is_rejected(tmp_path) -> None:  # noqa: ANN001
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars(), provider="sina")
    (tmp_path / "159915.SZ.bars.meta.json").write_text("{not json", encoding="utf-8")
    assert cache.read("159915.SZ") is None


def test_meta_records_provider_and_range(tmp_path) -> None:  # noqa: ANN001
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars(), provider="eastmoney")
    meta = json.loads((tmp_path / "159915.SZ.bars.meta.json").read_text(encoding="utf-8"))
    assert meta["provider"] == "eastmoney"
    assert meta["symbol"] == "159915.SZ"
    assert meta["rows"] == 30


def test_clear_removes_meta_sidecar(tmp_path) -> None:  # noqa: ANN001
    """清缓存必须连来源标记一起删，否则残留 meta 会配错 parquet。"""
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars(), provider="sina")
    cache.clear()
    assert list(tmp_path.glob("*.parquet")) == []
    assert list(tmp_path.glob("*.meta.json")) == []


def test_read_can_opt_out_of_provider_check(tmp_path) -> None:  # noqa: ANN001
    """诊断/迁移场景可显式绕过来源校验，但必须是显式的。"""
    cache = ParquetCache(tmp_path)
    cache.write("159915.SZ", _bars(), provider="fixture")
    assert cache.read("159915.SZ") is None
    assert cache.read("159915.SZ", require_trusted_provider=False) is not None


# ==========================================================================
# 新浪日线源
# ==========================================================================

_SINA_JSON = (
    '[{"day":"2024-01-02","open":"3.100","high":"3.200","low":"3.050",'
    '"close":"3.180","volume":"120000"},'
    '{"day":"2024-01-03","open":"3.180","high":"3.260","low":"3.150",'
    '"close":"3.240","volume":"130000"}]'
)


def test_sina_parses_daily_bars() -> None:
    provider = SinaPriceProvider(opener=lambda url: _SINA_JSON, max_bars=10)
    data = provider.fetch("159915.SZ", min_rows=2)
    assert list(data.bars.columns) == ["open", "high", "low", "close", "volume"]
    assert len(data.bars) == 2
    assert float(data.bars["close"].iloc[-1]) == pytest.approx(3.24)
    assert data.bars.index[0] == pd.Timestamp("2024-01-02")


def test_sina_reports_unadjusted_honestly() -> None:
    """新浪该接口是不复权价格；必须如实标记，不得冒充复权。"""
    provider = SinaPriceProvider(opener=lambda url: _SINA_JSON, max_bars=10)
    data = provider.fetch("159915.SZ", min_rows=2)
    assert data.report.adjusted is False
    assert data.report.provider == "sina"


def test_sina_maps_exchange_prefix() -> None:
    seen: list[str] = []

    def opener(url: str) -> str:
        seen.append(url)
        return _SINA_JSON

    provider = SinaPriceProvider(opener=opener, max_bars=10)
    provider.fetch("159915.SZ", min_rows=2)
    provider.fetch("600000.SS", min_rows=2)
    assert "symbol=sz159915" in seen[0]
    assert "symbol=sh600000" in seen[1]


def test_sina_rejects_non_a_share() -> None:
    provider = SinaPriceProvider(opener=lambda url: _SINA_JSON)
    with pytest.raises(DataUnavailableError, match="不是 A 股标的"):
        provider.fetch("0700.HK", min_rows=2)


@pytest.mark.parametrize(
    "payload",
    ["", "   ", "not json at all", "[]", "{}"],
)
def test_sina_bad_payload_becomes_data_unavailable(payload: str) -> None:
    """任何异常载荷都必须转成 DATA_UNAVAILABLE，不得穿透原始异常。"""
    provider = SinaPriceProvider(opener=lambda url: payload, attempts=1)
    with pytest.raises(DataUnavailableError):
        provider.fetch("159915.SZ", min_rows=2)


def test_sina_missing_field_is_reported() -> None:
    bad = '[{"day":"2024-01-02","open":"3.1","high":"3.2","low":"3.0"}]'
    provider = SinaPriceProvider(opener=lambda url: bad, attempts=1)
    with pytest.raises(DataUnavailableError, match="缺少字段"):
        provider.fetch("159915.SZ", min_rows=1)


def test_sina_network_error_is_wrapped() -> None:
    def boom(url: str) -> str:
        raise OSError("Remote end closed connection without response")

    provider = SinaPriceProvider(opener=boom, attempts=1)
    with pytest.raises(DataUnavailableError):
        provider.fetch("159915.SZ", min_rows=2)


# ==========================================================================
# 链式顺序
# ==========================================================================


class _StubProvider:
    def __init__(self, name: str, *, fail: bool = False) -> None:
        self.name = name
        self._fail = fail
        self.calls = 0

    def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN201
        self.calls += 1
        if self._fail:
            raise DataUnavailableError(f"{self.name} 不可用")
        raise DataUnavailableError(f"{self.name} 到此为止")


def test_a_share_order_is_eastmoney_then_sina_then_yahoo() -> None:
    """A 股顺序必须是 东财(前复权) → 新浪(不复权兜底) → Yahoo。

    新浪排在 Yahoo 之前：Yahoo 对 A 股常年 429 限流。
    """
    order: list[str] = []

    class Recorder(_StubProvider):
        def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN201
            order.append(self.name)
            raise DataUnavailableError(f"{self.name} 不可用")

    chained = ChainedPriceProvider(
        [Recorder("yahoo"), Recorder("sina"), Recorder("eastmoney")]
    )
    with pytest.raises(DataUnavailableError):
        chained.fetch("159915.SZ")
    assert order == ["eastmoney", "sina", "yahoo"]


def test_all_source_failures_are_aggregated() -> None:
    chained = ChainedPriceProvider(
        [_StubProvider("eastmoney", fail=True), _StubProvider("sina", fail=True)]
    )
    with pytest.raises(DataUnavailableError, match="所有行情源均不可用") as excinfo:
        chained.fetch("159915.SZ")
    message = str(excinfo.value)
    assert "[eastmoney]" in message
    assert "[sina]" in message
