"""实时 bar 叠加模块测试。"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from lei_signal.api.realtime import (
    IntradayOverlayProvider,
    RealtimeBar,
    SinaRealtimeBarSource,
    TencentRealtimeBarSource,
    apply_forming_bar,
)
from lei_signal.data.providers import PriceData
from lei_signal.data.validation import DataUnavailableError, ValidationReport


def _bars(n: int = 30) -> pd.DataFrame:
    rows = []
    for i in range(n):
        c = 100.0 + i * 0.5
        rows.append(
            {"open": c - 0.2, "high": c + 0.4, "low": c - 0.5,
             "close": c, "volume": 1_000_000.0}
        )
    idx = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=idx)


def _bar(d: str, **kw) -> RealtimeBar:
    return RealtimeBar(
        bar_date=date.fromisoformat(d),
        open=kw.get("open", 110.0),
        high=kw.get("high", 111.0),
        low=kw.get("low", 109.0),
        close=kw.get("close", 110.5),
        volume=kw.get("volume", 1000.0),
        source=kw.get("source", "tencent_rt"),
    )


def test_apply_forming_bar_appends_new_date() -> None:
    bars = _bars()
    last = bars.index[-1].date()
    next_day = (last + pd.Timedelta(days=1)).isoformat()
    bar = _bar(d=next_day, close=130.0, high=131.0, low=128.0, open=129.0)
    merged = apply_forming_bar(bars, bar)
    assert len(merged) == len(bars) + 1
    assert merged.index[-1] == pd.Timestamp(next_day)
    assert merged["close"].iloc[-1] == 130.0


def test_apply_forming_bar_overrides_same_day() -> None:
    bars = _bars()
    last = bars.index[-1]
    bar = _bar(d=last.date().isoformat(), close=130.0, high=131.0, low=128.0, open=129.0)
    merged = apply_forming_bar(bars, bar)
    assert len(merged) == len(bars)
    assert merged.loc[last, "close"] == 130.0
    assert merged["close"].iloc[-1] == 130.0


def test_apply_forming_bar_rejects_older_date() -> None:
    """报价源比日线源还旧时不得污染历史。"""
    bars = _bars()
    older = bars.index[0].date().isoformat()
    bar = _bar(d=older, close=999.0)
    merged = apply_forming_bar(bars, bar)
    assert merged is bars or merged.equals(bars)


def test_apply_forming_bar_writes_nan_when_volume_absent() -> None:
    """新浪 KOSPI 没成交量：写 NaN，不得拿昨日量冒充。"""
    bars = _bars()
    last = bars.index[-1].date().isoformat()
    bar = RealtimeBar(
        bar_date=date.fromisoformat(last), open=110, high=111, low=109, close=110.5,
        volume=None, source="sina_rt",
    )
    merged = apply_forming_bar(bars, bar)
    assert np.isnan(merged["volume"].iloc[-1])


def test_apply_forming_bar_clamps_ohlc_outliers() -> None:
    """盘中四价刷新时点偶发不一致：按定义收敛而非让校验直接判失败。

    场景：high=109（小于 open=110），low=110（等于 open）。
    按定义收敛：high = max(high, open, close) = 110；low = min(low, open, close) = 110。
    """
    bars = _bars()
    last = bars.index[-1].date()
    next_day = (last + pd.Timedelta(days=1)).isoformat()
    bar = RealtimeBar(
        bar_date=date.fromisoformat(next_day), open=110, high=109, low=110, close=110,
        volume=100.0, source="tencent_rt",
    )
    merged = apply_forming_bar(bars, bar)
    row = merged.iloc[-1]
    assert row["high"] == 110  # 由 109 收敛到 110（=open=close）
    assert row["low"] == 110


def test_tencent_source_parses_us_index_payload() -> None:
    """腾讯美股字段下标 1/3/5/6/30/33/34 须正确解析。

    实测响应有 78 个字段（``~`` 分隔）。下标 1=name、3=price、4=prev_close、
    5=open、6=volume、30=quote_time、33=high、34=low。
    """
    parts = ["0"] * 78  # type: ignore[var-annotated]
    parts[0] = "200"
    parts[1] = "标普500"
    parts[3] = "7600.50"
    parts[4] = "7489.72"
    parts[5] = "7504.78"
    parts[6] = "3188486610"
    parts[30] = "2026-08-03 17:05:56"
    parts[33] = "7610.04"
    parts[34] = "7504.78"
    raw = 'v_usINX="' + "~".join(parts) + '"'
    src = TencentRealtimeBarSource(opener=lambda _u: raw)
    bar = src.fetch("^GSPC")
    assert bar is not None
    assert bar.bar_date == date(2026, 8, 3)
    assert bar.close == 7600.50
    assert bar.open == 7504.78
    assert bar.high == 7610.04
    assert bar.low == 7504.78
    assert bar.volume == 3188486610.0


def test_tencent_source_handles_hk_slash_date() -> None:
    """港股返回 ``2026/08/04 09:37:02``，不是 ``-``。否则会静默取不到。"""
    parts = ["0"] * 78  # type: ignore[var-annotated]
    parts[0] = "100"
    parts[1] = "恒生科技指数"
    parts[3] = "4890.61"
    parts[4] = "4829.220"
    parts[5] = "4861.920"
    parts[6] = "802568"
    parts[30] = "2026/08/04 09:37:02"
    parts[33] = "4918.52"
    parts[34] = "4880.39"
    raw = 'v_hkHSTECH="' + "~".join(parts) + '"'
    src = TencentRealtimeBarSource(opener=lambda _u: raw)
    bar = src.fetch("^HSTECH")
    assert bar is not None
    assert bar.bar_date == date(2026, 8, 4)


def test_tencent_source_returns_none_on_unsupported_symbol() -> None:
    src = TencentRealtimeBarSource(opener=lambda _u: "ignored")
    assert src.supports("^KS11") is False
    assert src.fetch("^KS11") is None


def test_tencent_source_returns_none_on_network_error() -> None:
    def boom(_u: str) -> str:
        raise OSError("connection reset")

    src = TencentRealtimeBarSource(opener=boom)
    assert src.fetch("^GSPC") is None


def test_sina_source_parses_kospi_payload_without_volume() -> None:
    raw = 'var hq_str_znb_KOSPI="首尔综合指数,6293.6300,-24.00,-0.38,2:27 AM,1759127220,2026-08-04,09:45:50,6351.3800,6257.4500,6389.4000,6080.2500,0";'  # noqa: E501
    src = SinaRealtimeBarSource(opener=lambda _u: raw)
    bar = src.fetch("^KS11")
    assert bar is not None
    assert bar.bar_date == date(2026, 8, 4)
    assert bar.close == 6293.63
    assert bar.open == 6351.38
    assert bar.high == 6389.40
    assert bar.low == 6080.25
    assert bar.volume is None  # 新浪不给成交量；与 A 股/港股口径不同


def test_overlay_provider_merges_realtime_bar_with_history() -> None:
    """inner 正常返回历史时，overlay 必须把实时 bar 追加/覆盖到末尾。"""
    bars = _bars()

    def inner(symbol, *, min_rows=21):
        info_stub = object()
        return PriceData(
            symbol=symbol, display_name=symbol, bars=bars.copy(),
            report=ValidationReport(
                rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
                adjusted=True, provider="tencent", duplicates_removed=0, warnings=(),
            ),
            info=info_stub,
        )

    parts = ["0"] * 78  # type: ignore[var-annotated]
    parts[0] = "200"
    parts[3] = "7600.50"
    parts[4] = "7489.72"
    parts[5] = "7504.78"
    parts[6] = "3188486610"
    parts[30] = "2026-08-03 17:05:56"
    parts[33] = "7610.04"
    parts[34] = "7504.78"
    rt = TencentRealtimeBarSource(
        opener=lambda _u: 'v_usINX="' + "~".join(parts) + '"'
    )

    p = IntradayOverlayProvider(inner, sources=[rt])  # type: ignore[arg-type]
    data = p.fetch("^GSPC", min_rows=21)
    last = data.bars.iloc[-1]
    assert data.report.provider == "tencent+tencent_rt"
    assert last["close"] == 7600.50


def test_overlay_provider_does_not_silently_swallow_inner_failure() -> None:
    """inner 失败且无实时 bar 时，必须原样抛异常，不允许「假装从缓存读」。

    缓存兜底是「拿到实时 bar 才启用」的增强，不是 inner 失败的兜底——
    inner 失败意味着「连历史都拿不到」，这时「假装有数据」比抛错更危险。
    """
    def inner(_s, *, min_rows=21):
        raise DataUnavailableError("所有行情源均不可用：断网")

    # 不提供任何实时源 → _realtime_bar 返回 None → 不走 cache → 抛原异常
    p = IntradayOverlayProvider(inner, sources=[])
    with pytest.raises(DataUnavailableError):
        p.fetch("^GSPC", min_rows=21)


def test_overlay_provider_uses_cache_when_inner_fails_and_realtime_ok() -> None:
    """inner 失败 + 实时 bar 拿到时，必须用缓存历史 + 实时 bar 兜底。"""
    import os
    import tempfile

    from lei_signal.data.cache import ParquetCache

    bars = _bars()
    with tempfile.TemporaryDirectory() as tmp:
        cache = ParquetCache(tmp)
        cache.write("^GSPC", bars, provider="tencent")

        def inner(_s, *, min_rows=21):
            raise DataUnavailableError("Yahoo 429 / 腾讯限流")

        parts = ["0"] * 78  # type: ignore[var-annotated]
        parts[0] = "200"
        parts[3] = "7600.50"
        parts[4] = "7489.72"
        parts[5] = "7504.78"
        parts[6] = "3188486610"
        parts[30] = "2026-08-03 17:00:00"
        parts[33] = "7610.04"
        parts[34] = "7504.78"
        rt = TencentRealtimeBarSource(
            opener=lambda _u: 'v_usINX="' + "~".join(parts) + '"'
        )
        p = IntradayOverlayProvider(
            inner, cache_root=tmp, sources=[rt],  # type: ignore[arg-type]
        )
        data = p.fetch("^GSPC", min_rows=21)
        # 缓存 30 根 + 实时 1 根
        assert len(data.bars) == len(bars) + 1
        assert data.bars["close"].iloc[-1] == 7600.50
        assert data.report.provider == "parquet_cache+tencent_rt"
    # 临时目录已被回收，确认 cleanup 正常
    assert not os.path.exists(tmp)


def test_cache_first_provider_serves_fresh_cache_without_calling_inner() -> None:
    """ParquetCache 命中且 < TTL → 直接返回，不调用 inner。

    Yahoo v8 / yfinance 现在都触发 IP 限流，海外指数必须靠缓存兜底——
    如果连缓存都打过去，等于一边一边耗限流额度。
    """
    import os
    import tempfile

    from lei_signal.api.realtime import CacheFirstProvider
    from lei_signal.data.cache import ParquetCache

    bars = _bars()
    call_count = {"n": 0}

    def inner(_s, *, min_rows=21):
        call_count["n"] += 1
        raise AssertionError("inner 不应被调用——缓存新鲜")

    with tempfile.TemporaryDirectory() as tmp:
        cache = ParquetCache(tmp)
        cache.write("^IXIC", bars, provider="yahoo_v8")
        # 缓存是刚刚写入的，肯定新鲜
        assert cache.age_seconds("^IXIC") < 5

        p = CacheFirstProvider(
            inner, cache_root=tmp, cache_max_age_seconds=1800,  # type: ignore[arg-type]
        )
        data = p.fetch("^IXIC", min_rows=21)
        assert call_count["n"] == 0
        assert data.report.provider == "parquet_cache"
        assert len(data.bars) == len(bars)
    assert not os.path.exists(tmp)


def test_cache_first_provider_falls_through_to_inner_when_stale() -> None:
    """缓存不存在 / 过期 → 调用 inner 取新数据。"""
    import os
    import tempfile

    from lei_signal.api.realtime import CacheFirstProvider

    bars = _bars()

    def inner(symbol, *, min_rows=21):
        info_stub = object()
        return PriceData(
            symbol=symbol, display_name=symbol, bars=bars.copy(),
            report=ValidationReport(
                rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
                adjusted=True, provider="tencent", duplicates_removed=0, warnings=(),
            ),
            info=info_stub,
        )

    with tempfile.TemporaryDirectory() as tmp:
        # 不预热缓存：第一次 fetch 必须落 inner
        p = CacheFirstProvider(
            inner, cache_root=tmp, cache_max_age_seconds=1800,  # type: ignore[arg-type]
        )
        data = p.fetch("^IXIC", min_rows=21)
        assert data.report.provider == "tencent"
    assert not os.path.exists(tmp)
