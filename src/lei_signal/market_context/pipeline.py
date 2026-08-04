"""Market context analysis pipeline — Round 4 + Round 5.

Orchestrates breadth, drawdown, classifier, and sentiment analysis
for all reference markets of a symbol. Per-market data isolation is
load-bearing: each reference market gets its own universe membership,
its own component bars, its own index bars, and its own breadth
history. A single ``bars_by_symbol`` dict is **never** reused across
markets — that was the Round 4 defect that let one market silently
inherit another market's components.

Market-context outputs are independent of Round 3 signal state:
no call to run_state_machine, no write to signal_events, structure
lifecycle, or daily_assessments.

Design spec sections 3, 11, 12, 15.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import Protocol

import pandas as pd

from lei_signal.market_context.breadth import BreadthConfig, compute_breadth_snapshot
from lei_signal.market_context.classifier import classify_breadth
from lei_signal.market_context.drawdown import compute_drawdown
from lei_signal.market_context.mapping import map_reference_markets
from lei_signal.market_context.sentiment import (
    SentimentObservation,
    latest_available_sentiment_at,
)
from lei_signal.market_context.types import (
    ContextDataStatus,
    ContextSummary,
    MarketContextSnapshot,
    MarketId,
    SentimentLabel,
    UniverseSnapshot,
)


class MarketDataProvider(Protocol):
    """Per-market data source. Implementations are responsible for fetching the
    universe, component bars, index bars, and breadth history that belong to
    *this* market_id — never to another market.
    """

    def universe(self, market_id: MarketId, as_of: date) -> UniverseSnapshot | None: ...

    def sessions(self, market_id: MarketId) -> pd.DatetimeIndex | None: ...

    def index_bars(self, market_id: MarketId, as_of: date) -> pd.DataFrame | None: ...

    def breadth_history(
        self, market_id: MarketId, *, up_to: date,
    ) -> pd.DataFrame | None: ...

    def component_bars(
        self, market_id: MarketId, symbols: tuple[str, ...], as_of: date,
    ) -> dict[str, pd.DataFrame]: ...


@dataclass
class MarketContextRequest:
    """Input for market context analysis.

    `provider` is the only way to feed breadth components into the pipeline;
    legacy ``universe_snapshot``/``bars_by_symbol``/``index_bars``/``breadth_history``
    are still accepted for callers that hold a per-call snapshot in memory,
    but when both are supplied the per-market provider takes precedence and
    the legacy fields are used only as a fallback for the **primary** market.
    """

    symbol: str
    as_of: date

    memberships: set[MarketId] = field(default_factory=set)
    provider: MarketDataProvider | None = None
    sentiment_observations: list[SentimentObservation] = field(default_factory=list)
    config: BreadthConfig = field(default_factory=BreadthConfig)

    # Legacy single-snapshot fields, kept for back-compat with test fixtures.
    universe_snapshot: UniverseSnapshot | None = None
    bars_by_symbol: dict[str, pd.DataFrame] = field(default_factory=dict)
    sessions: pd.DatetimeIndex | None = None
    index_bars: pd.DataFrame | None = None
    breadth_history: pd.DataFrame | None = None


def analyze_market_context(
    request: MarketContextRequest,
) -> tuple[MarketContextSnapshot, ...]:
    """Analyze market context for every reference market of a symbol.

    Returns one snapshot per reference market, primary first. Each market
    resolves its own data through the request's `provider`; if the provider
    cannot answer for a market, that market contributes an explicit unknown
    snapshot rather than borrowing another market's data.
    """
    mapping = map_reference_markets(request.symbol, memberships=request.memberships)

    ordered: list[MarketId | None] = [mapping.primary_market_id]
    ordered.extend(mapping.secondary_market_ids)

    snapshots: list[MarketContextSnapshot] = []
    for market_id in ordered:
        if market_id is None:
            snapshots.append(_unknown_snapshot(
                None, request.as_of, reason="无法识别参考市场，mapping_incomplete",
            ))
            continue
        try:
            snapshots.append(_analyze_single_market(request, market_id))
        except _InsufficientData:
            snapshots.append(_unknown_snapshot(
                market_id, request.as_of,
                reason="缺少成分股或行情数据，无法计算市场宽度",
                data_status=ContextDataStatus.UNAVAILABLE,
            ))

    return tuple(snapshots)


class _InsufficientData(Exception):
    """Raised internally to signal that a market had no usable data; the
    pipeline converts this to a structured unknown snapshot."""


def _analyze_single_market(
    request: MarketContextRequest,
    market_id: MarketId,
) -> MarketContextSnapshot:
    """Analyze context for a single reference market, using only its own data."""
    universe, bars_by_symbol, sessions, index_bars, history = _load_market_data(
        request, market_id
    )
    if universe is None or sessions is None or sessions.empty:
        raise _InsufficientData(market_id.value)

    breadth_snap = compute_breadth_snapshot(
        universe=universe,
        bars_by_symbol=bars_by_symbol,
        sessions=sessions,
        as_of=request.as_of,
        config=request.config,
    )

    ctx = classify_breadth(
        breadth_snap, history if history is not None else pd.DataFrame(),
        index_bars=index_bars,
        minimum_coverage=request.config.minimum_coverage,
    )

    # 2. Drawdown — optional. Failure does not invalidate breadth reading.
    if index_bars is not None and not index_bars.empty:
        try:
            drawdown = compute_drawdown(index_bars, request.as_of, market_id)
            ctx = replace(ctx, drawdown_from_ath=drawdown.drawdown_from_ath)
        except Exception:
            pass

    # 3. Sentiment — only for US markets. Decision_at keyed, not load-time.
    if market_id in {MarketId.SP500, MarketId.NASDAQ_100, MarketId.RUSSELL_2000}:
        ctx = _attach_sentiment(ctx, request, market_id)

    return ctx


def _load_market_data(
    request: MarketContextRequest,
    market_id: MarketId,
) -> tuple[
    UniverseSnapshot | None,
    dict[str, pd.DataFrame],
    pd.DatetimeIndex | None,
    pd.DataFrame | None,
    pd.DataFrame | None,
]:
    """Resolve the (universe, bars, sessions, index, history) tuple for one
    market. When a provider is supplied, it is the sole source of truth; the
    legacy single-snapshot fields are reserved as a fallback for the primary
    market only, so a one-off test fixture can still drive the pipeline."""
    if request.provider is not None:
        universe = request.provider.universe(market_id, request.as_of)
        if universe is None:
            return None, {}, request.provider.sessions(market_id), None, None
        sessions = request.provider.sessions(market_id)
        bars = request.provider.component_bars(
            market_id, universe.symbols, request.as_of,
        )
        index_bars = request.provider.index_bars(market_id, request.as_of)
        history = request.provider.breadth_history(market_id, up_to=request.as_of)
        return universe, bars, sessions, index_bars, history

    # Legacy fallback: only the primary market gets a snapshot.
    is_primary = market_id is not None and market_id == (
        map_reference_markets(request.symbol, memberships=request.memberships).primary_market_id
    )
    if not is_primary:
        return None, {}, None, None, None

    return (
        request.universe_snapshot,
        dict(request.bars_by_symbol),
        request.sessions,
        request.index_bars,
        request.breadth_history,
    )


def _attach_sentiment(
    ctx: MarketContextSnapshot,
    request: MarketContextRequest,
    market_id: MarketId,
) -> MarketContextSnapshot:
    """Resolve sentiment eligibility and labels **at decision_at**, not at load
    time. `latest_available_sentiment_at` re-evaluates the age rule on each
    call so an observation that was current last week is no longer current now.
    """
    decision_at = pd.Timestamp(request.as_of).tz_localize("UTC")
    naaim_obs = latest_available_sentiment_at(
        [o for o in request.sentiment_observations if o.series_id == "NAAIM"],
        decision_at, max_age_days=14,
    )
    aaii_obs = latest_available_sentiment_at(
        [o for o in request.sentiment_observations if o.series_id == "AAII"],
        decision_at, max_age_days=10,
    )
    return replace(
        ctx,
        naaim_label=naaim_obs.label if naaim_obs else SentimentLabel.UNKNOWN,
        naaim_current_eligible=bool(naaim_obs.current_eligible) if naaim_obs else False,
        aaii_label=aaii_obs.label if aaii_obs else SentimentLabel.UNKNOWN,
        aaii_current_eligible=bool(aaii_obs.current_eligible) if aaii_obs else False,
    )


def _unknown_snapshot(
    market_id: MarketId | None,
    as_of: date,
    *,
    reason: str = "",
    data_status: ContextDataStatus = ContextDataStatus.UNAVAILABLE,
) -> MarketContextSnapshot:
    """Create an explicit unknown snapshot."""
    return MarketContextSnapshot(
        market_id=market_id or MarketId.CN_ALL_A,
        as_of=as_of,
        available_at=as_of,
        universe_version="",
        breadth_20=None,
        breadth_50=None,
        breadth_200=None,
        coverage_20=0.0,
        coverage_50=0.0,
        coverage_200=0.0,
        constituent_count=0,
        summary=ContextSummary.UNKNOWN,
        reasons=(reason,) if reason else (),
        data_status=data_status,
    )
