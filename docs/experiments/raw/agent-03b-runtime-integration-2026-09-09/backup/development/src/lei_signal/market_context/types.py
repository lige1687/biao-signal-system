"""Market context domain types — Round 4.

All types are immutable (frozen dataclasses) and carry explicit
provenance, data-status, and version metadata. None of these types
reference Round 3 signal fields (structure_id, lifecycle_id, Stage,
RiskState, opportunity_stage).

Design specification: docs/superpowers/specs/2026-08-02-market-context-design.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

# ── Market identifiers ────────────────────────────────────────────────


class MarketId(StrEnum):
    """Supported market identifiers."""

    # A-share
    CN_ALL_A = "CN_ALL_A"
    SSE_50 = "SSE_50"
    CSI_300 = "CSI_300"
    CSI_500 = "CSI_500"
    CSI_1000 = "CSI_1000"
    CHINEXT = "CHINEXT"
    STAR_50 = "STAR_50"

    # US
    SP500 = "SP500"
    NASDAQ_100 = "NASDAQ_100"
    RUSSELL_2000 = "RUSSELL_2000"


#: Every A-share reference market. A-share LEI fixed thresholds are
#: research-grade, so this set also drives the `lei_threshold_research`
#: provenance marker on emitted events.
A_SHARE_MARKETS: frozenset[MarketId] = frozenset({
    MarketId.CN_ALL_A,
    MarketId.SSE_50,
    MarketId.CSI_300,
    MarketId.CSI_500,
    MarketId.CSI_1000,
    MarketId.CHINEXT,
    MarketId.STAR_50,
})


# ── Summary and classification enums ──────────────────────────────────


class ContextSummary(StrEnum):
    """Top-level market environment hint — v1 uses only Breadth20/50 direction."""

    TAILWIND = "tailwind"
    NEUTRAL = "neutral"
    HEADWIND = "headwind"
    UNKNOWN = "unknown"


class LongRegime(StrEnum):
    """Long-term breadth regime based on Breadth200."""

    BULL = "bull"
    BEAR = "bear"
    UNKNOWN = "unknown"


class HeatState(StrEnum):
    """Current market heat based on Breadth20/50 percentiles and fixed thresholds."""

    EXTREME_COLD = "extreme_cold"
    COLD = "cold"
    NEUTRAL = "neutral"
    HOT = "hot"
    EXTREME_HOT = "extreme_hot"
    UNKNOWN = "unknown"


class BreadthDirection(StrEnum):
    """Short-term direction of market participation."""

    EXPANDING = "expanding"
    CONTRACTING = "contracting"
    DIVERGING = "diverging"
    UNKNOWN = "unknown"


class VolRegime(StrEnum):
    """Market volatility regime (research_proxy, 2026-08-27 实证阈值).

    等权成分日收益的 20 日已实现波动率 3 年滚动分位：≥0.8 high / ≤0.2 low。
    LEI 信号对账：市场高波期信号 60 日均值 0.73% vs 低波期 4.98%（3755 条）。
    """

    HIGH = "high"
    MID = "mid"
    LOW = "low"
    UNKNOWN = "unknown"


class ContextSourceKind(StrEnum):
    """Data provenance classification — formal, external check, or research proxy."""

    FORMAL = "formal"
    EXTERNAL_CHECK = "external_check"
    RESEARCH_PROXY = "research_proxy"


class ContextDataStatus(StrEnum):
    """Data quality status for a dimension or snapshot."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    CONFLICT = "conflict"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class SentimentLabel(StrEnum):
    """Sentiment classification labels."""

    EXTREME_LOW = "extreme_low"
    LOW = "low"
    NEUTRAL = "neutral"
    HIGH = "high"
    EXTREME_HIGH = "extreme_high"
    UNKNOWN = "unknown"


class SentimentAlignment(StrEnum):
    """Institutional vs retail sentiment alignment."""

    ALIGNED = "aligned"
    DIVERGENT = "divergent"
    INDETERMINATE = "indeterminate"


# ── Immutable domain dataclasses ──────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MarketMapping:
    """Resolved reference-market assignment for a single symbol.

    Primary market is the symbol's main reference index (tracking index
    for ETFs, CN_ALL_A for individual A-shares). Secondaries are additional
    indices the symbol belongs to.
    """

    symbol: str
    primary_market_id: MarketId | None
    secondary_market_ids: tuple[MarketId, ...]
    mapping_incomplete: bool
    reason_cn: str


@dataclass(frozen=True, slots=True)
class UniverseSnapshot:
    """Point-in-time index universe membership snapshot."""

    market_id: MarketId
    as_of: date
    symbols: tuple[str, ...]
    source: str
    source_version: str
    source_kind: ContextSourceKind
    retrieved_at: datetime
    universe_version: str  # deterministic hash of active rows


@dataclass(frozen=True, slots=True)
class BreadthSnapshot:
    """Market breadth snapshot for a single as_of date.

    Each of the three moving-average windows (20, 50, 200) has an independent
    denominator and coverage ratio. Eligibility counts and coverage ratios are
    preserved separately for auditability.
    """

    market_id: MarketId
    as_of: date
    available_at: date
    universe_version: str

    # Constituent counts
    constituent_count: int
    eligible_20: int
    eligible_50: int
    eligible_200: int
    missing_20: int
    missing_50: int
    missing_200: int

    # Coverage ratios (eligible / constituent)
    coverage_20: float
    coverage_50: float
    coverage_200: float

    # Breadth values (percentage of constituents above MA)
    breadth_20: float | None
    breadth_50: float | None
    breadth_200: float | None

    # Percentiles (optional — only when history is available)
    percentile_20: float | None = None
    percentile_50: float | None = None
    percentile_200: float | None = None

    source_kind: ContextSourceKind = ContextSourceKind.FORMAL
    provenance: str = ""
    data_status: ContextDataStatus = ContextDataStatus.COMPLETE


@dataclass(frozen=True, slots=True)
class DrawdownState:
    """Index drawdown from all-time-high closing price."""

    market_id: MarketId
    as_of: date
    drawdown_from_ath: float  # negative percentage, e.g. -0.15 for -15%
    ath_close: float
    ath_date: date
    current_close: float


@dataclass(frozen=True, slots=True)
class MarketContextEvent:
    """A discrete market-context event (breadth extreme, divergence, etc.)."""

    market_id: MarketId
    as_of: date
    available_at: date
    event_type: str  # e.g. "short_hot_extreme", "negative_breadth_divergence"
    event_version: str  # e.g. "lei_market_breadth.v1"
    threshold_origin: str  # "lei_threshold_research" or "formal"
    evidence: dict[str, float | str | None] = field(default_factory=dict)
    provenance: str = ""
    source_kind: ContextSourceKind = ContextSourceKind.FORMAL
    data_status: ContextDataStatus = ContextDataStatus.COMPLETE


@dataclass(frozen=True, slots=True)
class SentimentObservation:
    """A single survey observation (NAAIM or AAII) aligned to available_at."""

    series_id: str  # "NAAIM" or "AAII"
    survey_week: date
    available_at: datetime
    source: str
    license_status: str  # "licensed", "public_delayed", etc.
    publication_delay_days: int | None = None
    current_eligible: bool = False

    # NAAIM-specific
    exposure_index: float | None = None

    # AAII-specific
    bullish: float | None = None
    neutral: float | None = None
    bearish: float | None = None
    bull_bear: float | None = None

    # Computed
    percentile: float | None = None
    label: SentimentLabel = SentimentLabel.UNKNOWN


@dataclass(frozen=True, slots=True)
class MarketContextSnapshot:
    """Complete market context for one reference market on one date.

    This is the primary output consumed by UI and research. It contains
    all raw dimensions plus classified summaries, reasons, and conflicts.

    It MUST NOT contain structure_id, lifecycle_id, Stage, RiskState,
    or opportunity_stage.
    """

    market_id: MarketId
    as_of: date
    available_at: date
    universe_version: str

    # Breadth raw
    breadth_20: float | None
    breadth_50: float | None
    breadth_200: float | None
    coverage_20: float
    coverage_50: float
    coverage_200: float
    constituent_count: int

    # Percentiles
    percentile_20: float | None = None
    percentile_50: float | None = None
    percentile_200: float | None = None

    # Direction
    breadth_direction: BreadthDirection = BreadthDirection.UNKNOWN
    breadth_20_delta_5: float | None = None
    breadth_50_delta_5: float | None = None
    breadth_200_delta_20: float | None = None

    # Classification
    long_regime: LongRegime = LongRegime.UNKNOWN
    heat_state: HeatState = HeatState.UNKNOWN

    # Drawdown
    drawdown_from_ath: float | None = None

    # Market volatility regime (research_proxy, 2026-08-27)
    market_rv20_ann: float | None = None
    market_rv_pct: float | None = None
    vol_regime: VolRegime = VolRegime.UNKNOWN

    # Events
    extreme_events: tuple[MarketContextEvent, ...] = ()
    divergence_events: tuple[MarketContextEvent, ...] = ()

    # Sentiment
    naaim_label: SentimentLabel = SentimentLabel.UNKNOWN
    naaim_current_eligible: bool = False
    aaii_label: SentimentLabel = SentimentLabel.UNKNOWN
    aaii_current_eligible: bool = False
    sentiment_alignment: SentimentAlignment = SentimentAlignment.INDETERMINATE

    # Summary
    summary: ContextSummary = ContextSummary.UNKNOWN
    reasons: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    source_kind: ContextSourceKind = ContextSourceKind.FORMAL
    provenance: str = ""
    data_status: ContextDataStatus = ContextDataStatus.COMPLETE
