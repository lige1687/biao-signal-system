"""Reference-market mapping for single symbols — Round 4.

Deterministic, versioned static mapping with no network calls.
ETFs use their tracking index as primary; A-share individual stocks
default to CN_ALL_A primary with secondary memberships from the
supplied index universe snapshot.

Design spec section 4.3.
"""

from __future__ import annotations

from collections.abc import Set

from lei_signal.market_context.types import A_SHARE_MARKETS, MarketId, MarketMapping

# ── Versioned ETF mapping ─────────────────────────────────────────────

#: v2 splits 科创50 ETF out of SSE_50 into its own STAR_50 market.
MAPPING_VERSION = "lei_market_mapping.v2"

# Known dashboard / reference index symbols. These resolve to their tracking
# index as primary (not the generic All-A basket). Individual A-share stocks
# always fall through to the CN_ALL_A primary rule below. Keep this in sync
# with the dashboard index registry (api/config.py DashboardIndex).
_KNOWN_INDEX_SYMBOLS: frozenset[str] = frozenset(
    {
        "000001.SS",  # 上证指数
        "000300.SS",  # 沪深300
        "000688.SS",  # 科创50
        "000905.SS",  # 中证500
    }
)

__all__ = ["A_SHARE_MARKETS", "MAPPING_VERSION", "map_reference_markets", "to_repo_symbol"]


# Known A-share ETF → tracking index primary.
# Keys use the repository-canonical Shanghai suffix `.SS` (see
# lei_signal.data.symbols.resolve_symbol); the `.SH` alias is accepted on lookup.
_ETF_PRIMARY: dict[str, MarketId] = {
    "510050.SS": MarketId.SSE_50,
    "510710.SS": MarketId.SSE_50,
    "510300.SS": MarketId.CSI_300,
    "510310.SS": MarketId.CSI_300,
    "510330.SS": MarketId.CSI_300,
    "515130.SS": MarketId.CSI_300,
    "159919.SZ": MarketId.CSI_300,
    "510500.SS": MarketId.CSI_500,
    "510510.SS": MarketId.CSI_500,
    "159922.SZ": MarketId.CSI_500,
    "512100.SS": MarketId.CSI_1000,
    "159845.SZ": MarketId.CSI_1000,
    "159915.SZ": MarketId.CHINEXT,
    "159949.SZ": MarketId.CHINEXT,
    # 科创50 ETF tracks 上证科创板50 (000688) — a different index from 上证50.
    # Proxying it with SSE_50 produced confidently wrong conclusions.
    "588000.SS": MarketId.STAR_50,
    "588080.SS": MarketId.STAR_50,
}


def to_repo_symbol(symbol: str) -> str:
    """Canonicalize a symbol to the repository's own form.

    Shanghai listings are `.SS` throughout this repo — `lei_signal.data`
    rejects `.SH` as a non-A-share, so every symbol crossing into price
    fetching or universe lookup must pass through here.
    """
    sym = symbol.strip().upper()
    if sym.endswith(".SH"):
        return sym[:-3] + ".SS"
    return sym


# Known US ETFs
_US_ETF_PRIMARY: dict[str, MarketId] = {
    "SPY": MarketId.SP500,
    "IVV": MarketId.SP500,
    "VOO": MarketId.SP500,
    "QQQ": MarketId.NASDAQ_100,
    "IWM": MarketId.RUSSELL_2000,
}


def _standard_etf_mapping(symbol: str) -> MarketMapping | None:
    """Return a standard mapping for known ETFs, or None."""
    sym = symbol.strip().upper()
    canonical = to_repo_symbol(sym)

    # Check A-share ETFs
    if canonical in _ETF_PRIMARY:
        primary = _ETF_PRIMARY[canonical]
        return MarketMapping(
            symbol=symbol,
            primary_market_id=primary,
            secondary_market_ids=(MarketId.CN_ALL_A,),
            mapping_incomplete=False,
            reason_cn=f"ETF跟踪指数 {primary.value}，叠加全A市场",
        )

    # Check US ETFs
    if sym in _US_ETF_PRIMARY:
        primary = _US_ETF_PRIMARY[sym]
        return MarketMapping(
            symbol=symbol,
            primary_market_id=primary,
            secondary_market_ids=(),
            mapping_incomplete=False,
            reason_cn=f"ETF tracks {primary.value}",
        )

    return None


def _us_mapping_with_memberships(
    symbol: str, us_memberships: set[MarketId],
) -> MarketMapping:
    """Pick a US primary by SP500 > NASDAQ_100 > RUSSELL_2000 priority."""
    priority = [MarketId.SP500, MarketId.NASDAQ_100, MarketId.RUSSELL_2000]
    primary: MarketId | None = None
    for p in priority:
        if p in us_memberships:
            primary = p
            break

    if primary is None:
        # All members are non-priority; pick the first by enum order
        sorted_mems = sorted(us_memberships, key=lambda m: list(MarketId).index(m))
        primary = sorted_mems[0]

    assert primary is not None

    secondary = tuple(
        sorted(
            [m for m in us_memberships if m != primary],
            key=lambda m: list(MarketId).index(m),
        )
    )
    return MarketMapping(
        symbol=symbol,
        primary_market_id=primary,
        secondary_market_ids=secondary,
        mapping_incomplete=False,
        reason_cn=f"美股，主参考 {primary.value}"
        + (f"，次参考: {', '.join(m.value for m in secondary)}" if secondary else ""),
    )


def _is_a_share(symbol: str) -> bool:
    """Heuristic: A-share symbols end with .SH or .SZ (or .SS alias) suffix."""
    return (
        symbol.endswith(".SH")
        or symbol.endswith(".SZ")
        or symbol.endswith(".SS")
    )


def _is_us_equity(symbol: str) -> bool:
    """Heuristic: US symbols are plain tickers without .SH/.SZ/.HK suffixes."""
    return not _is_a_share(symbol) and "." not in symbol


def map_reference_markets(
    symbol: str,
    memberships: Set[MarketId] = frozenset(),
) -> MarketMapping:
    """Map a symbol to its reference market(s).

    Rules (in priority order):
    1. Known A-share ETF → tracking index primary + CN_ALL_A secondary.
    2. Known US ETF → tracking index primary.
    3. A-share individual stock (.SH/.SZ) → CN_ALL_A primary,
       secondary = supplied memberships sorted by enum order.
    4. US individual stock → supplied memberships dictating primary/secondary;
       without membership data → mapping_incomplete.
    5. Unknown symbol → mapping_incomplete.

    The mapping is deterministic and makes no network calls.
    """
    # 1. Check known ETF mappings
    etf = _standard_etf_mapping(symbol)
    if etf is not None:
        return etf

    # 2. Known dashboard index (000001.SS / 000300.SS / 000688.SS / …).
    #    These look like A-share symbols (`.SS` suffix), but the caller
    #    has already declared which reference market they belong to via
    #    `memberships`. Use the first non-`CN_ALL_A` membership as the
    #    primary so the bread reader is CSI_300, not the generic All-A
    #    basket.
    if _is_a_share(symbol) and memberships and to_repo_symbol(symbol) in _KNOWN_INDEX_SYMBOLS:
        non_generic = tuple(
            m for m in memberships if m is not MarketId.CN_ALL_A
        )
        if non_generic:
            sorted_memberships = sorted(
                non_generic, key=lambda m: list(MarketId).index(m),
            )
            primary = sorted_memberships[0]
            secondary = tuple(
                sorted(
                    [m for m in memberships if m is not primary],
                    key=lambda m: list(MarketId).index(m),
                )
            )
            return MarketMapping(
                symbol=symbol,
                primary_market_id=primary,
                secondary_market_ids=secondary,
                mapping_incomplete=False,
                reason_cn=(
                    f"参考指数 {primary.value}"
                    + (f"，叠加: {', '.join(m.value for m in secondary)}" if secondary else "")
                ),
            )

    # 3. A-share individual stock
    if _is_a_share(symbol):
        # Sort secondary memberships by MarketId enum definition order
        sorted_secondary = tuple(
            sorted(
                [m for m in memberships if m != MarketId.CN_ALL_A],
                key=lambda m: list(MarketId).index(m),
            )
        )
        return MarketMapping(
            symbol=symbol,
            primary_market_id=MarketId.CN_ALL_A,
            secondary_market_ids=sorted_secondary,
            mapping_incomplete=False,
            reason_cn=(
                "A股个股，主参考市场全A，已识别指数归属: "
                + ", ".join(m.value for m in sorted_secondary)
            )
            if sorted_secondary
            else "A股个股，主参考市场全A",
        )

    # 3. US individual stock with membership info
    if _is_us_equity(symbol):
        us_memberships = {m for m in memberships if m in {
            MarketId.SP500, MarketId.NASDAQ_100, MarketId.RUSSELL_2000,
        }}

        if us_memberships:
            return _us_mapping_with_memberships(symbol, set(us_memberships))

        # No membership info from point-in-time data → mapping_incomplete
        return MarketMapping(
            symbol=symbol,
            primary_market_id=None,
            secondary_market_ids=(),
            mapping_incomplete=True,
            reason_cn=f"无法识别美股 {symbol} 的参考市场，缺少成分股信息，mapping_incomplete",
        )

    # 4. Unknown symbol type
    return MarketMapping(
        symbol=symbol,
        primary_market_id=None,
        secondary_market_ids=(),
        mapping_incomplete=True,
        reason_cn=f"无法识别 {symbol} 的市场归属，mapping_incomplete",
    )
