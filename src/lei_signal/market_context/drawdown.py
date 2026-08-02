"""Index drawdown from all-time-high closing price — Round 4.

Design spec section 9.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.market_context.types import DrawdownState, MarketId


def compute_drawdown(
    index_bars: pd.DataFrame,
    as_of: date,
    market_id: MarketId | None = None,
) -> DrawdownState:
    """Compute drawdown from historical max CLOSING price.

    Uses only data on or before as_of. Closing highs only, not intraday.
    Returns a DrawdownState with drawdown as a negative percentage
    (e.g. -0.15 for 15% below ATH, 0.0 at ATH).

    Args:
        index_bars: DataFrame with DatetimeIndex and 'close' column.
        as_of: The decision date.
        market_id: Optional market identifier for the result.

    Returns:
        DrawdownState with drawdown, ath_close, ath_date, current_close.
    """
    if market_id is None:
        market_id = MarketId.CN_ALL_A

    as_of_ts = pd.Timestamp(as_of)

    # Crop to as_of
    if isinstance(index_bars.index, pd.DatetimeIndex):
        frame = index_bars[index_bars.index <= as_of_ts].copy()
    else:
        frame = index_bars.copy()

    if len(frame) == 0 or "close" not in frame.columns:
        return DrawdownState(
            market_id=market_id,
            as_of=as_of.date() if hasattr(as_of, 'date') else as_of,
            drawdown_from_ath=0.0,
            ath_close=0.0,
            ath_date=as_of.date() if hasattr(as_of, 'date') else as_of,
            current_close=0.0,
        )

    closes = frame["close"]

    # Find ATH (max closing price)
    ath_idx = closes.idxmax()
    ath_close = float(closes.max())
    current_close = float(closes.iloc[-1])

    if ath_close > 0:
        drawdown = current_close / ath_close - 1.0
    else:
        drawdown = 0.0

    ath_date = ath_idx.date() if hasattr(ath_idx, 'date') else as_of
    if hasattr(as_of, 'date'):
        as_of_date = as_of.date()
    else:
        as_of_date = as_of

    return DrawdownState(
        market_id=market_id,
        as_of=as_of_date,
        drawdown_from_ath=drawdown,
        ath_close=ath_close,
        ath_date=ath_date,
        current_close=current_close,
    )
