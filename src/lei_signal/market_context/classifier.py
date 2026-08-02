"""Market context classifier — Round 4.

Classifies breadth snapshots into heat states, direction, regime,
extreme events, divergence, and summary. Implements LEI fixed thresholds
for market breadth events (v1).

Design spec sections 7, 8, 11.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.market_context.types import (
    BreadthDirection,
    BreadthSnapshot,
    ContextDataStatus,
    ContextSourceKind,
    ContextSummary,
    HeatState,
    LongRegime,
    MarketContextEvent,
    MarketContextSnapshot,
    MarketId,
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
    is_ashare = snap.market_id in {
        MarketId.CN_ALL_A, MarketId.SSE_50, MarketId.CSI_300,
        MarketId.CSI_500, MarketId.CSI_1000, MarketId.CHINEXT,
    }
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
    snap: BreadthSnapshot,
    history: pd.DataFrame,
) -> tuple[BreadthDirection, float | None, float | None]:
    """Classify short-term breadth direction from 5-session changes.

    Returns (direction, b20_delta_5, b50_delta_5).
    """
    if len(history) < 1 or snap.breadth_20 is None or snap.breadth_50 is None:
        return BreadthDirection.UNKNOWN, None, None

    # Get 5 sessions ago (last row before current)
    prev = history.iloc[-1]
    prev_b20 = prev.get("breadth_20")
    prev_b50 = prev.get("breadth_50")

    if prev_b20 is None or pd.isna(prev_b20) or prev_b50 is None or pd.isna(prev_b50):
        return BreadthDirection.UNKNOWN, None, None

    delta_20 = snap.breadth_20 - float(prev_b20)
    delta_50 = snap.breadth_50 - float(prev_b50)

    if delta_20 > 0 and delta_50 > 0:
        direction = BreadthDirection.EXPANDING
    elif delta_20 < 0 and delta_50 < 0:
        direction = BreadthDirection.CONTRACTING
    else:
        direction = BreadthDirection.DIVERGING

    return direction, delta_20, delta_50


def _classify_summary(
    direction: BreadthDirection,
    delta_20: float | None,
    delta_50: float | None,
    snap: BreadthSnapshot,
) -> ContextSummary:
    """Classify v1 summary from Breadth20/50 5-session direction only.

    Rules (design spec section 11):
    - Coverage failure → unknown
    - Both B20 and B50 5-day deltas > 0 → tailwind
    - Both < 0 → headwind
    - All other cases → neutral
    """
    # Coverage check
    if (snap.coverage_20 < 0.90 or snap.coverage_50 < 0.90
            or snap.breadth_20 is None or snap.breadth_50 is None):
        return ContextSummary.UNKNOWN

    if direction == BreadthDirection.EXPANDING:
        return ContextSummary.TAILWIND
    elif direction == BreadthDirection.CONTRACTING:
        return ContextSummary.HEADWIND
    elif direction == BreadthDirection.DIVERGING:
        return ContextSummary.NEUTRAL
    else:
        return ContextSummary.UNKNOWN


def classify_breadth(
    current: BreadthSnapshot,
    history: pd.DataFrame,
) -> MarketContextSnapshot:
    """Classify a breadth snapshot into a full MarketContextSnapshot.

    Applies all classifier rules: extreme events, long regime, heat state,
    direction, divergence, and v1 summary.

    Args:
        current: The current breadth snapshot to classify.
        history: Historical breadth DataFrame (indexed by date) for
                 direction changes and percentiles.

    Returns:
        A complete MarketContextSnapshot with all classifications.
    """
    # Detect extreme events
    extreme_events = tuple(_detect_extreme_events(current))

    # Classify long regime
    long_regime = _classify_long_regime(current.breadth_200)

    # Classify heat state
    heat_state = _classify_heat_state(current)

    # Classify direction and compute deltas
    direction, delta_20, delta_50 = _classify_direction(current, history)

    # Compute 20-day delta for Breadth200
    delta_200 = None
    if len(history) >= 1 and current.breadth_200 is not None:
        # Use second-to-last row's breadth_200 if available
        past_b200 = history.iloc[-1].get("breadth_200")
        if past_b200 is not None and not pd.isna(past_b200):
            delta_200 = current.breadth_200 - float(past_b200)

    # Classify v1 summary
    summary = _classify_summary(direction, delta_20, delta_50, current)

    # Build reasons and conflicts
    reasons: list[str] = []
    conflicts: list[str] = []

    if summary == ContextSummary.TAILWIND:
        reasons.append("Breadth20和Breadth50最近5个交易日同步上升")
    elif summary == ContextSummary.HEADWIND:
        reasons.append("Breadth20和Breadth50最近5个交易日同步下降")

    if long_regime == LongRegime.BEAR:
        conflicts.append("Breadth200仍低于50%，长期市场底色偏熊")
    elif long_regime == LongRegime.BULL:
        reasons.append(f"Breadth200高于50%，长期市场底色为牛")

    if heat_state in (HeatState.EXTREME_COLD, HeatState.COLD):
        conflicts.append(f"市场热度处于{heat_state.value}区间")
    elif heat_state in (HeatState.EXTREME_HOT, HeatState.HOT):
        reasons.append(f"市场热度处于{heat_state.value}区间")

    for evt in extreme_events:
        if "cold" in evt.event_type:
            conflicts.append(f"触发极端事件: {evt.event_type}")
        elif "hot" in evt.event_type:
            reasons.append(f"触发极端事件: {evt.event_type}")

    # Add threshold origin note for A-share
    if current.market_id in {
        MarketId.CN_ALL_A, MarketId.SSE_50, MarketId.CSI_300,
        MarketId.CSI_500, MarketId.CSI_1000, MarketId.CHINEXT,
    }:
        reasons.append("A股LEI固定阈值为研究级，非正式验证阈值")

    return MarketContextSnapshot(
        market_id=current.market_id,
        as_of=current.as_of,
        available_at=current.available_at,
        universe_version=current.universe_version,
        breadth_20=current.breadth_20,
        breadth_50=current.breadth_50,
        breadth_200=current.breadth_200,
        coverage_20=current.coverage_20,
        coverage_50=current.coverage_50,
        coverage_200=current.coverage_200,
        constituent_count=current.constituent_count,
        percentile_20=current.percentile_20,
        percentile_50=current.percentile_50,
        percentile_200=current.percentile_200,
        breadth_direction=direction,
        breadth_20_delta_5=delta_20,
        breadth_50_delta_5=delta_50,
        breadth_200_delta_20=delta_200,
        long_regime=long_regime,
        heat_state=heat_state,
        extreme_events=extreme_events,
        summary=summary,
        reasons=tuple(reasons),
        conflicts=tuple(conflicts),
        source_kind=current.source_kind,
        provenance=current.provenance,
        data_status=current.data_status,
    )
