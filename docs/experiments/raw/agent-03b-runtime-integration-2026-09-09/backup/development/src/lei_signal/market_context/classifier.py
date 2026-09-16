"""Market context classifier — Round 4.

Classifies breadth snapshots into heat states, direction, regime,
extreme events, divergence, and summary. Implements LEI fixed thresholds
for market breadth events (v1).

Design spec sections 7, 8, 11.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd

from lei_signal.market_context.breadth import breadth_delta
from lei_signal.market_context.types import (
    A_SHARE_MARKETS,
    BreadthDirection,
    BreadthSnapshot,
    ContextDataStatus,
    ContextSummary,
    HeatState,
    LongRegime,
    MarketContextEvent,
    MarketContextSnapshot,
)

# ── Threshold constants ───────────────────────────────────────────────

_EVENT_VERSION = "lei_market_breadth.v1"

# Fixed LEI threshold values
_HOT_THRESHOLD = 85.0
_COLD_THRESHOLD = 15.0
_BULL_BEAR_MID = 50.0


def _detect_extreme_events(
    snap: BreadthSnapshot,
) -> list[MarketContextEvent]:
    """Detect fixed-threshold LEI breadth extreme events.

    Rules (design spec section 7):
    - Breadth20 >= 85 AND Breadth50 >= 85 → short_hot_extreme
    - Breadth20 <= 15 AND Breadth50 <= 15 → short_cold_extreme
    - Breadth50 >= 85 AND Breadth200 >= 85 → long_hot_extreme
    - Breadth50 <= 15 AND Breadth200 <= 15 → long_cold_extreme
    - Breadth200 > 50 → broad_bull_regime
    - Breadth200 < 50 → broad_bear_regime
    """
    events: list[MarketContextEvent] = []

    # Determine threshold origin
    is_ashare = snap.market_id in A_SHARE_MARKETS
    threshold_origin = "lei_threshold_research" if is_ashare else "formal"
    provenance_note = "lei_threshold_research" if is_ashare else ""

    b20 = snap.breadth_20
    b50 = snap.breadth_50
    b200 = snap.breadth_200

    # Short hot extreme
    if b20 is not None and b50 is not None and b20 >= _HOT_THRESHOLD and b50 >= _HOT_THRESHOLD:
        events.append(MarketContextEvent(
            market_id=snap.market_id,
            as_of=snap.as_of,
            available_at=snap.available_at,
            event_type="short_hot_extreme",
            event_version=_EVENT_VERSION,
            threshold_origin=threshold_origin,
            evidence={"breadth_20": b20, "breadth_50": b50},
            provenance=provenance_note,
            source_kind=snap.source_kind,
            data_status=snap.data_status,
        ))

    # Short cold extreme
    if b20 is not None and b50 is not None and b20 <= _COLD_THRESHOLD and b50 <= _COLD_THRESHOLD:
        events.append(MarketContextEvent(
            market_id=snap.market_id,
            as_of=snap.as_of,
            available_at=snap.available_at,
            event_type="short_cold_extreme",
            event_version=_EVENT_VERSION,
            threshold_origin=threshold_origin,
            evidence={"breadth_20": b20, "breadth_50": b50},
            provenance=provenance_note,
            source_kind=snap.source_kind,
            data_status=snap.data_status,
        ))

    # Long hot extreme
    if b50 is not None and b200 is not None and b50 >= _HOT_THRESHOLD and b200 >= _HOT_THRESHOLD:
        events.append(MarketContextEvent(
            market_id=snap.market_id,
            as_of=snap.as_of,
            available_at=snap.available_at,
            event_type="long_hot_extreme",
            event_version=_EVENT_VERSION,
            threshold_origin=threshold_origin,
            evidence={"breadth_50": b50, "breadth_200": b200},
            provenance=provenance_note,
            source_kind=snap.source_kind,
            data_status=snap.data_status,
        ))

    # Long cold extreme
    if b50 is not None and b200 is not None and b50 <= _COLD_THRESHOLD and b200 <= _COLD_THRESHOLD:
        events.append(MarketContextEvent(
            market_id=snap.market_id,
            as_of=snap.as_of,
            available_at=snap.available_at,
            event_type="long_cold_extreme",
            event_version=_EVENT_VERSION,
            threshold_origin=threshold_origin,
            evidence={"breadth_50": b50, "breadth_200": b200},
            provenance=provenance_note,
            source_kind=snap.source_kind,
            data_status=snap.data_status,
        ))

    return events


def _classify_long_regime(breadth_200: float | None) -> LongRegime:
    """Classify long-term regime from Breadth200."""
    if breadth_200 is None:
        return LongRegime.UNKNOWN
    if breadth_200 > _BULL_BEAR_MID:
        return LongRegime.BULL
    if breadth_200 < _BULL_BEAR_MID:
        return LongRegime.BEAR
    return LongRegime.UNKNOWN  # exactly 50


def _classify_heat_state(
    snap: BreadthSnapshot,
) -> HeatState:
    """Classify heat state from Breadth20/50 percentiles and fixed thresholds.

    Rules (design spec section 8):
    - Fixed 15% cold extreme OR median percentile <= 10% → extreme_cold
    - Not extreme_cold AND median percentile <= 25% → cold
    - Fixed 85% hot extreme OR median percentile >= 90% → extreme_hot
    - Not extreme_hot AND median percentile >= 75% → hot
    - Otherwise → neutral
    - Missing percentiles without fixed extreme → unknown
    """
    b20 = snap.breadth_20
    b50 = snap.breadth_50
    p20 = snap.percentile_20
    p50 = snap.percentile_50

    # Check fixed threshold triggers
    fixed_cold = (b20 is not None and b50 is not None
                  and b20 <= _COLD_THRESHOLD and b50 <= _COLD_THRESHOLD)
    fixed_hot = (b20 is not None and b50 is not None
                 and b20 >= _HOT_THRESHOLD and b50 >= _HOT_THRESHOLD)

    # Compute median percentile if available
    if p20 is not None and p50 is not None:
        median_pct = (p20 + p50) / 2.0

        if fixed_cold or median_pct <= 10.0:
            return HeatState.EXTREME_COLD
        if median_pct <= 25.0:
            return HeatState.COLD
        if fixed_hot or median_pct >= 90.0:
            return HeatState.EXTREME_HOT
        if median_pct >= 75.0:
            return HeatState.HOT
        return HeatState.NEUTRAL

    # No percentile data — use fixed thresholds only
    if fixed_cold:
        return HeatState.EXTREME_COLD
    if fixed_hot:
        return HeatState.EXTREME_HOT
    return HeatState.UNKNOWN


def _classify_direction(
    b20: float | None,
    b50: float | None,
    delta_20: float | None,
    delta_50: float | None,
) -> BreadthDirection:
    """Classify short-term breadth direction from exact 5-session changes."""
    if b20 is None or b50 is None or delta_20 is None or delta_50 is None:
        return BreadthDirection.UNKNOWN
    if delta_20 > 0 and delta_50 > 0:
        return BreadthDirection.EXPANDING
    if delta_20 < 0 and delta_50 < 0:
        return BreadthDirection.CONTRACTING
    return BreadthDirection.DIVERGING


def _classify_summary(
    direction: BreadthDirection,
    b20: float | None,
    b50: float | None,
) -> ContextSummary:
    """Classify v1 summary from Breadth20/50 5-session direction only.

    `b20`/`b50` arrive already coverage-gated, so a failed horizon reaches
    here as None and yields `unknown` rather than a confident reading.
    """
    if b20 is None or b50 is None:
        return ContextSummary.UNKNOWN

    if direction is BreadthDirection.EXPANDING:
        return ContextSummary.TAILWIND
    if direction is BreadthDirection.CONTRACTING:
        return ContextSummary.HEADWIND
    if direction is BreadthDirection.DIVERGING:
        return ContextSummary.NEUTRAL
    return ContextSummary.UNKNOWN


def _index_return(index_bars: pd.DataFrame | None, as_of: date, sessions_back: int) -> float | None:
    """Index close-to-close return over exactly `sessions_back` sessions."""
    if index_bars is None or index_bars.empty or "close" not in index_bars.columns:
        return None
    if not isinstance(index_bars.index, pd.DatetimeIndex):
        return None
    visible = index_bars[index_bars.index <= pd.Timestamp(as_of)].sort_index()
    if len(visible) <= sessions_back:
        return None
    closes = visible["close"]
    current = closes.iloc[-1]
    past = closes.iloc[-1 - sessions_back]
    if pd.isna(current) or pd.isna(past) or float(past) == 0.0:
        return None
    return float(current) / float(past) - 1.0


def _detect_divergence_events(
    snap: BreadthSnapshot,
    *,
    index_return: float | None,
    b20_delta_20: float | None,
    b50_delta_20: float | None,
    threshold_origin: str,
    provenance_note: str,
) -> list[MarketContextEvent]:
    """Detect 20-session divergence between index price and breadth.

    Index up while both breadth series retreat means the advance narrowed to
    fewer names; index down while breadth widens means selling narrowed.
    """
    if index_return is None or b20_delta_20 is None or b50_delta_20 is None:
        return []

    if index_return > 0 and b20_delta_20 < 0 and b50_delta_20 < 0:
        event_type = "negative_breadth_divergence"
    elif index_return < 0 and b20_delta_20 > 0 and b50_delta_20 > 0:
        event_type = "positive_breadth_divergence"
    else:
        return []

    return [MarketContextEvent(
        market_id=snap.market_id,
        as_of=snap.as_of,
        available_at=snap.available_at,
        event_type=event_type,
        event_version=_EVENT_VERSION,
        threshold_origin=threshold_origin,
        evidence={
            "index_return_20": index_return,
            "breadth_20_delta_20": b20_delta_20,
            "breadth_50_delta_20": b50_delta_20,
        },
        provenance=provenance_note,
        source_kind=snap.source_kind,
        data_status=snap.data_status,
    )]


def classify_breadth(
    current: BreadthSnapshot,
    history: pd.DataFrame,
    *,
    index_bars: pd.DataFrame | None = None,
    minimum_coverage: float = 0.90,
) -> MarketContextSnapshot:
    """Classify a breadth snapshot into a full MarketContextSnapshot.

    Coverage is gated per 20/50/200 horizon independently: a horizon below
    `minimum_coverage` contributes nothing — no reading, no conclusion, no
    extreme event — while the horizons that do have coverage still report.

    Args:
        current: The current breadth snapshot to classify.
        history: Breadth history indexed by date, used as the session axis for
                 exact 5/20-session changes. Must not extend past `current.as_of`.
        index_bars: Reference index OHLCV for divergence detection.
        minimum_coverage: Per-horizon eligible/constituent floor.
    """
    as_of = current.as_of

    ok_20 = current.coverage_20 >= minimum_coverage
    ok_50 = current.coverage_50 >= minimum_coverage
    ok_200 = current.coverage_200 >= minimum_coverage

    b20 = current.breadth_20 if ok_20 else None
    b50 = current.breadth_50 if ok_50 else None
    b200 = current.breadth_200 if ok_200 else None

    gated = replace(
        current,
        breadth_20=b20,
        breadth_50=b50,
        breadth_200=b200,
        percentile_20=current.percentile_20 if ok_20 else None,
        percentile_50=current.percentile_50 if ok_50 else None,
        percentile_200=current.percentile_200 if ok_200 else None,
    )

    extreme_events = tuple(_detect_extreme_events(gated))
    long_regime = _classify_long_regime(b200)
    heat_state = _classify_heat_state(gated)

    delta_20_5 = breadth_delta(
        history, "breadth_20", as_of=as_of, sessions_back=5, current=b20,
    ) if b20 is not None else None
    delta_50_5 = breadth_delta(
        history, "breadth_50", as_of=as_of, sessions_back=5, current=b50,
    ) if b50 is not None else None
    delta_200_20 = breadth_delta(
        history, "breadth_200", as_of=as_of, sessions_back=20, current=b200,
    ) if b200 is not None else None

    direction = _classify_direction(b20, b50, delta_20_5, delta_50_5)
    summary = _classify_summary(direction, b20, b50)

    is_ashare = current.market_id in A_SHARE_MARKETS
    threshold_origin = "lei_threshold_research" if is_ashare else "formal"
    provenance_note = "lei_threshold_research" if is_ashare else ""

    divergence_events = tuple(_detect_divergence_events(
        gated,
        index_return=_index_return(index_bars, as_of, 20),
        b20_delta_20=breadth_delta(
            history, "breadth_20", as_of=as_of, sessions_back=20, current=b20,
        ) if b20 is not None else None,
        b50_delta_20=breadth_delta(
            history, "breadth_50", as_of=as_of, sessions_back=20, current=b50,
        ) if b50 is not None else None,
        threshold_origin=threshold_origin,
        provenance_note=provenance_note,
    ))

    reasons: list[str] = []
    conflicts: list[str] = []

    for window, ok, coverage in (
        (20, ok_20, current.coverage_20),
        (50, ok_50, current.coverage_50),
        (200, ok_200, current.coverage_200),
    ):
        if not ok:
            conflicts.append(
                f"Breadth{window} 覆盖率 {coverage:.1%} 低于 {minimum_coverage:.0%}，"
                f"该周期不出结论"
            )

    if summary is ContextSummary.TAILWIND:
        reasons.append("Breadth20和Breadth50最近5个交易日同步上升")
    elif summary is ContextSummary.HEADWIND:
        reasons.append("Breadth20和Breadth50最近5个交易日同步下降")

    if long_regime is LongRegime.BEAR:
        conflicts.append("Breadth200仍低于50%，长期市场底色偏熊")
    elif long_regime is LongRegime.BULL:
        reasons.append("Breadth200高于50%，长期市场底色为牛")

    if heat_state in (HeatState.EXTREME_COLD, HeatState.COLD):
        conflicts.append(f"市场热度处于{heat_state.value}区间")
    elif heat_state in (HeatState.EXTREME_HOT, HeatState.HOT):
        reasons.append(f"市场热度处于{heat_state.value}区间")

    for evt in extreme_events:
        if "cold" in evt.event_type:
            conflicts.append(f"触发极端事件: {evt.event_type}")
        elif "hot" in evt.event_type:
            reasons.append(f"触发极端事件: {evt.event_type}")

    for evt in divergence_events:
        if evt.event_type == "negative_breadth_divergence":
            conflicts.append("指数近20个交易日上行但B20/B50同步收缩，涨幅集中在少数标的")
        else:
            reasons.append("指数近20个交易日下行但B20/B50同步扩张，跌幅集中在少数标的")

    if is_ashare:
        reasons.append("A股LEI固定阈值为研究级，非正式验证阈值")

    data_status = current.data_status
    if not (ok_20 and ok_50 and ok_200):
        data_status = ContextDataStatus.INCOMPLETE

    return MarketContextSnapshot(
        market_id=current.market_id,
        as_of=as_of,
        available_at=current.available_at,
        universe_version=current.universe_version,
        breadth_20=b20,
        breadth_50=b50,
        breadth_200=b200,
        coverage_20=current.coverage_20,
        coverage_50=current.coverage_50,
        coverage_200=current.coverage_200,
        constituent_count=current.constituent_count,
        percentile_20=gated.percentile_20,
        percentile_50=gated.percentile_50,
        percentile_200=gated.percentile_200,
        breadth_direction=direction,
        breadth_20_delta_5=delta_20_5,
        breadth_50_delta_5=delta_50_5,
        breadth_200_delta_20=delta_200_20,
        long_regime=long_regime,
        heat_state=heat_state,
        extreme_events=extreme_events,
        divergence_events=divergence_events,
        summary=summary,
        reasons=tuple(reasons),
        conflicts=tuple(conflicts),
        source_kind=current.source_kind,
        provenance=current.provenance,
        data_status=data_status,
    )
