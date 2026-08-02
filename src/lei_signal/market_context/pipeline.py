"""Market context analysis pipeline — Round 4.

Orchestrates breadth, drawdown, classifier, and sentiment analysis
for all reference markets of a symbol. Produces independent
MarketContextSnapshot objects that do NOT modify any Round 3 state.

Design spec sections 3, 11, 12, 15.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lei_signal.market_context.breadth import BreadthConfig, compute_breadth_snapshot
from lei_signal.market_context.classifier import classify_breadth
from lei_signal.market_context.data_sources import BarsResult
from lei_signal.market_context.drawdown import compute_drawdown
from lei_signal.market_context.mapping import MarketMapping, map_reference_markets
from lei_signal.market_context.sentiment import SentimentObservation, latest_available_sentiment
from lei_signal.market_context.types import (
    ContextDataStatus,
    ContextSummary,
    MarketContextSnapshot,
    MarketId,
    SentimentAlignment,
    SentimentLabel,
    UniverseSnapshot,
)


@dataclass
class MarketContextRequest:
    """Input for market context analysis.

    All data providers are optional; missing providers lead to
    explicit unknown/unavailable status rather than crashes.
    """

    symbol: str
    as_of: date

    # Mapping inputs
    memberships: set[MarketId] = field(default_factory=set)

    # Data inputs (optional)
    universe_snapshot: UniverseSnapshot | None = None
    bars_by_symbol: dict[str, pd.DataFrame] = field(default_factory=dict)
    sessions: pd.DatetimeIndex | None = None
    index_bars: pd.DataFrame | None = None
    breadth_history: pd.DataFrame | None = None
    sentiment_observations: list[SentimentObservation] = field(default_factory=list)

    config: BreadthConfig = field(default_factory=BreadthConfig)


def analyze_market_context(
    request: MarketContextRequest,
) -> tuple[MarketContextSnapshot, ...]:
    """Analyze market context for all reference markets of a symbol.

    Returns one MarketContextSnapshot per reference market, in order:
    primary first, then secondaries. If mapping is incomplete or data
    is unavailable, returns an explicit unknown snapshot.

    Does NOT call run_state_machine, modify AnalysisResult, or
    write to signal_events/structure lifecycle tables.
    """
    mapping = map_reference_markets(request.symbol, memberships=request.memberships)

    snapshots: list[MarketContextSnapshot] = []

    all_markets: list[MarketId | None] = [mapping.primary_market_id]
    all_markets.extend(mapping.secondary_market_ids)

    for market_id in all_markets:
        if market_id is None:
            snapshots.append(_unknown_snapshot(
                None, request.as_of, reason="无法识别参考市场，mapping_incomplete"
            ))
            continue

        try:
            snap = _analyze_single_market(request, market_id)
            snapshots.append(snap)
        except Exception:
            snapshots.append(_unknown_snapshot(
                market_id, request.as_of,
                reason=f"分析 {market_id.value} 市场环境时出错",
                data_status=ContextDataStatus.UNAVAILABLE,
            ))

    return tuple(snapshots)


def _analyze_single_market(
    request: MarketContextRequest,
    market_id: MarketId,
) -> MarketContextSnapshot:
    """Analyze context for a single reference market."""
    # 1. Compute breadth if data available
    if request.universe_snapshot is not None and request.sessions is not None:
        breadth_snap = compute_breadth_snapshot(
            universe=request.universe_snapshot,
            bars_by_symbol=request.bars_by_symbol,
            sessions=request.sessions,
            as_of=request.as_of,
            config=request.config,
        )
        # Classify
        history = request.breadth_history if request.breadth_history is not None else pd.DataFrame()
        ctx = classify_breadth(breadth_snap, history)
    else:
        # No breadth data → unknown
        return _unknown_snapshot(
            market_id, request.as_of,
            reason="缺少成分股或行情数据，无法计算市场宽度",
            data_status=ContextDataStatus.UNAVAILABLE,
        )

    # 2. Compute drawdown if index bars available
    if request.index_bars is not None and len(request.index_bars) > 0:
        try:
            drawdown = compute_drawdown(request.index_bars, request.as_of, market_id)
            ctx = MarketContextSnapshot(
                market_id=ctx.market_id,
                as_of=ctx.as_of,
                available_at=ctx.available_at,
                universe_version=ctx.universe_version,
                breadth_20=ctx.breadth_20,
                breadth_50=ctx.breadth_50,
                breadth_200=ctx.breadth_200,
                coverage_20=ctx.coverage_20,
                coverage_50=ctx.coverage_50,
                coverage_200=ctx.coverage_200,
                constituent_count=ctx.constituent_count,
                percentile_20=ctx.percentile_20,
                percentile_50=ctx.percentile_50,
                percentile_200=ctx.percentile_200,
                breadth_direction=ctx.breadth_direction,
                breadth_20_delta_5=ctx.breadth_20_delta_5,
                breadth_50_delta_5=ctx.breadth_50_delta_5,
                drawdown_from_ath=drawdown.drawdown_from_ath,
                long_regime=ctx.long_regime,
                heat_state=ctx.heat_state,
                extreme_events=ctx.extreme_events,
                divergence_events=ctx.divergence_events,
                summary=ctx.summary,
                reasons=ctx.reasons,
                conflicts=ctx.conflicts,
                source_kind=ctx.source_kind,
                provenance=ctx.provenance,
                data_status=ctx.data_status,
            )
        except Exception:
            pass  # drawdown is optional; proceed without it

    # 3. Sentiment (only for US markets)
    if market_id in {MarketId.SP500, MarketId.NASDAQ_100, MarketId.RUSSELL_200}:
        naaim_obs = latest_available_sentiment(
            [o for o in request.sentiment_observations if o.series_id == "NAAIM"],
            pd.Timestamp(request.as_of).tz_localize("UTC"),
            max_age_days=14,
        )
        aaii_obs = latest_available_sentiment(
            [o for o in request.sentiment_observations if o.series_id == "AAII"],
            pd.Timestamp(request.as_of).tz_localize("UTC"),
            max_age_days=10,
        )

        naaim_label = naaim_obs.label if naaim_obs else SentimentLabel.UNKNOWN
        naaim_eligible = naaim_obs.current_eligible if naaim_obs else False
        aaii_label = aaii_obs.label if aaii_obs else SentimentLabel.UNKNOWN
        aaii_eligible = aaii_obs.current_eligible if aaii_obs else False

        ctx = MarketContextSnapshot(
            market_id=ctx.market_id,
            as_of=ctx.as_of,
            available_at=ctx.available_at,
            universe_version=ctx.universe_version,
            breadth_20=ctx.breadth_20,
            breadth_50=ctx.breadth_50,
            breadth_200=ctx.breadth_200,
            coverage_20=ctx.coverage_20,
            coverage_50=ctx.coverage_50,
            coverage_200=ctx.coverage_200,
            constituent_count=ctx.constituent_count,
            percentile_20=ctx.percentile_20,
            percentile_50=ctx.percentile_50,
            percentile_200=ctx.percentile_200,
            breadth_direction=ctx.breadth_direction,
            breadth_20_delta_5=ctx.breadth_20_delta_5,
            breadth_50_delta_5=ctx.breadth_50_delta_5,
            drawdown_from_ath=ctx.drawdown_from_ath,
            long_regime=ctx.long_regime,
            heat_state=ctx.heat_state,
            extreme_events=ctx.extreme_events,
            divergence_events=ctx.divergence_events,
            naaim_label=naaim_label,
            naaim_current_eligible=naaim_eligible,
            aaii_label=aaii_label,
            aaii_current_eligible=aaii_eligible,
            summary=ctx.summary,
            reasons=ctx.reasons,
            conflicts=ctx.conflicts,
            source_kind=ctx.source_kind,
            provenance=ctx.provenance,
            data_status=ctx.data_status,
        )

    return ctx


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
