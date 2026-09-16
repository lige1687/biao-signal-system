"""市场波动体制（vol_regime）单测：纯函数 + pipeline 挂接 + 序列化。"""
from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd

from lei_signal.market_context.pipeline import (
    MarketContextRequest,
    analyze_market_context,
)
from lei_signal.market_context.types import MarketId, UniverseSnapshot
from lei_signal.market_context.vol_regime import (
    compute_market_vol_regime,
    vol_event_type,
)


def _sessions(n: int, start: str = "2023-01-02") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def _bars(n: int, seed: int, base: float = 100.0, vol_daily: float = 0.01) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, vol_daily, n)
    close = base * np.cumprod(1 + rets)
    idx = _sessions(n)
    return pd.DataFrame({"close": close}, index=idx)


def test_compute_none_when_no_data():
    assert compute_market_vol_regime({}, _sessions(10), date(2023, 1, 1)) is None


def test_compute_none_when_history_short():
    bars = {"A": _bars(100, 1)}
    assert compute_market_vol_regime(bars, _sessions(100), date(2024, 5, 31)) is None


def test_compute_mid_regime_typical_case():
    n = 400
    bars = {"A": _bars(n, 1), "B": _bars(n, 2), "C": _bars(n, 3)}
    sessions = _sessions(n)
    as_of = sessions[-1].date()
    v = compute_market_vol_regime(bars, sessions, as_of)
    assert v is not None
    assert 0.0 <= v.rv_pct <= 1.0
    assert v.rv20_ann > 0
    assert v.regime in ("high", "mid", "low")
    assert "research_proxy" in v.provenance


def test_compute_high_regime_when_vol_spike_at_end():
    n = 500
    bars = {"A": _bars(n, 1, vol_daily=0.005), "B": _bars(n, 2, vol_daily=0.005)}
    # 末段注入高波动
    for df in bars.values():
        tail = df["close"].iloc[-30:].pct_change().fillna(0) * 4 + 1
        df.loc[df.index[-30:], "close"] = df["close"].iloc[-30] * np.cumprod(tail.values)
    sessions = _sessions(n)
    v = compute_market_vol_regime(bars, sessions, sessions[-1].date())
    assert v is not None
    assert v.regime == "high"
    assert v.rv_pct > 0.8


def test_compute_uses_last_session_on_or_before_as_of():
    n = 400
    bars = {"A": _bars(n, 1)}
    sessions = _sessions(n)
    # as_of = 最后一日之后几天（周末）：回落到最后交易日
    as_of = (sessions[-1] + pd.Timedelta(days=3)).date()
    v = compute_market_vol_regime(bars, sessions, as_of)
    assert v is not None


def test_vol_event_type_mapping():
    assert vol_event_type("high") == "high_vol_regime"
    assert vol_event_type("low") == "low_vol_regime"
    assert vol_event_type("mid") is None


def _universe(market_id: MarketId, symbols: tuple[str, ...], day: date) -> UniverseSnapshot:
    from lei_signal.market_context.types import ContextSourceKind
    return UniverseSnapshot(
        market_id=market_id,
        as_of=day,
        symbols=symbols,
        source="test",
        source_version="test-1",
        source_kind=ContextSourceKind.FORMAL,
        retrieved_at=datetime(2026, 8, 27, tzinfo=UTC),
        universe_version="test-v1",
    )


def test_pipeline_attaches_vol_regime_and_event():
    """provider 供数 → 快照带 vol 字段；高波场景发 high_vol_regime 事件。"""
    n = 500
    day = _sessions(n)[-1].date()
    bars = {"A": _bars(n, 1, vol_daily=0.005), "B": _bars(n, 2, vol_daily=0.005)}
    for df in bars.values():
        tail = df["close"].iloc[-30:].pct_change().fillna(0) * 4 + 1
        df.loc[df.index[-30:], "close"] = df["close"].iloc[-30] * np.cumprod(tail.values)
    idx_bars = pd.DataFrame({"close": bars["A"]["close"].values}, index=bars["A"].index)

    class _Provider:
        def universe(self, market_id, as_of):
            return _universe(market_id, ("A", "B"), as_of)

        def sessions(self, market_id):
            return _sessions(n)

        def index_bars(self, market_id, as_of):
            return idx_bars

        def breadth_history(self, market_id, *, up_to):
            return pd.DataFrame()

        def component_bars(self, market_id, symbols, as_of):
            return bars

    request = MarketContextRequest(
        symbol="510300.SS",
        as_of=day,
        provider=_Provider(),  # type: ignore[arg-type]
    )
    snapshots = analyze_market_context(request)
    ctx = snapshots[0]
    assert ctx.market_rv_pct is not None and ctx.market_rv_pct > 0.8
    assert ctx.vol_regime.value == "high"
    types = [e.event_type for e in ctx.extreme_events]
    assert "high_vol_regime" in types
    ev = next(e for e in ctx.extreme_events if e.event_type == "high_vol_regime")
    assert ev.event_version == "research_market_vol.v1"
    assert ev.threshold_origin.startswith("empirical_research")
    assert "rv_pct" in ev.evidence


def test_pipeline_vol_absent_leaves_breadth_intact():
    """成分行情缺失（宽度走 missing 计数）时波动体制为 UNKNOWN，快照不失败。"""
    n = 320
    day = _sessions(n)[-1].date()

    class _NoBarsProvider:
        def universe(self, market_id, as_of):
            return _universe(market_id, ("A",), as_of)

        def sessions(self, market_id):
            return _sessions(n)

        def index_bars(self, market_id, as_of):
            return pd.DataFrame()

        def breadth_history(self, market_id, *, up_to):
            return pd.DataFrame()

        def component_bars(self, market_id, symbols, as_of):
            return {}

    request = MarketContextRequest(
        symbol="510300.SS", as_of=day, provider=_NoBarsProvider(),  # type: ignore[arg-type]
    )
    snapshots = analyze_market_context(request)
    ctx = snapshots[0]
    assert ctx.market_rv_pct is None
    assert ctx.vol_regime.value == "unknown"
    # 宽度快照本身仍然产出（数据状态可以是 degraded，但不能崩）
    assert ctx.as_of == day


def test_snapshot_to_dict_includes_vol_fields():
    from lei_signal.api.market_context_service import _snapshot_to_dict
    from lei_signal.market_context.pipeline import MarketContextRequest

    # 用最简路径构造一个 snapshot（unknown 兜底也行，字段必须在）
    request = MarketContextRequest(symbol="510300.SS", as_of=date(2026, 8, 27))
    snapshots = analyze_market_context(request)
    d = _snapshot_to_dict(snapshots[0])
    assert "market_rv20_ann" in d and "market_rv_pct" in d and "vol_regime" in d
    assert d["vol_regime"] in ("high", "mid", "low", "unknown")
