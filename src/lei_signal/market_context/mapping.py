"""Reference-market mapping for single symbols — Round 4.

Deterministic, versioned static mapping with no network calls.
ETFs use their tracking index as primary; A-share individual stocks
default to CN_ALL_A primary with secondary memberships from the
supplied index universe snapshot.

Design spec section 4.3.
"""

from __future__ import annotations

from typing import AbstractSet

from lei_signal.market_context.types import MarketId, MarketMapping

# ── Versioned ETF mapping ─────────────────────────────────────────────

_MAPPING_VERSION = "lei_market_mapping.v1"

# Known A-share ETF → tracking index primary
_ETF_PRIMARY: dict[str, MarketId] = {
    "510050.SH": MarketId.SSE_50,
    "510300.SH": MarketId.CSI_300,
    "510310.SH": MarketId.CSI_300,
    "510330.SH": MarketId.CSI_300,
    "159919.SZ": MarketId.CSI_300,
    "510500.SH": MarketId.CSI_500,
    "510510.SH": MarketId.CSI_500,
    "159922.SZ": MarketId.CSI_500,
    "512100.SH": MarketId.CSI_1000,
    "159845.SZ": MarketId.CSI_1000,
    "159915.SZ": MarketId.CHINEXT,
    "159949.SZ": MarketId.CHINEXT,
    "510710.SH": MarketId.SSE_50,
    "588000.SH": MarketId.SSE_50,  # 科创50 ETF → SSE_50 as best proxy
    "588080.SH": MarketId.SSE_50,
}

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
    # Normalize symbol case
    sym = symbol.strip().upper()

    # Check A-share ETFs
    if symbol in _ETF_PRIMARY:
        primary = _ETF_PRIMARY[symbol]
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


def _is_a_share(symbol: str) -> bool:
    """Heuristic: A-share symbols end with .SH or .SZ suffix."""
    return symbol.endswith(".SH") or symbol.endswith(".SZ")


def _is_us_equity(symbol: str) -> bool:
    """Heuristic: US symbols are plain tickers without .SH/.SZ/.HK suffixes."""
    return not _is_a_share(symbol) and "." not in symbol


def map_reference_markets(
    symbol: str,
    memberships: AbstractSet[MarketId] = frozenset(),
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

    # 2. A-share individual stock
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
            reason_cn=f"A股个股，主参考市场全A，已识别指数归属: {', '.join(m.value for m in sorted_secondary)}"
            if sorted_secondary
            else "A股个股，主参考市场全A",
        )

    # 3. US individual stock with membership info
    if _is_us_equity(symbol):
        us_memberships = {m for m in memberships if m in {
            MarketId.SP500, MarketId.NASDAQ_100, MarketId.RUSSELL_2000,
        }}

        if us_memberships:
            # Priority: SP500 > NASDAQ_100 > RUSSELL_2000
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

            # mypy: primary is guaranteed to be MarketId at this point
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
