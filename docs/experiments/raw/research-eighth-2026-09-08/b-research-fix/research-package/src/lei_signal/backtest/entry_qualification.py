"""Research-only actual-open qualification; frozen §10 minimum, no target reselection."""
from __future__ import annotations

from dataclasses import dataclass
import math

from lei_signal.domain.rules_config import get_rule


@dataclass(frozen=True, slots=True)
class EntryQualification:
    accepted: bool
    reason: str
    entry_price: float | None
    stop_price: float | None
    target_price: float | None
    actual_reward_risk: float | None


def _price(value: float | None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def qualify_entry_at_open(
    *, open_price: float | None, stop_price: float | None, target_price: float | None
) -> EntryQualification:
    """All three prices must use the same units at the actual execution time.

    Uses the target and stop already fixed at signal time, without selecting a new
    target after observing the open. The frozen ledger minimum remains 3.
    This pure function does not decide whether the market permits a trade.
    """
    entry, stop, target = map(_price, (open_price, stop_price, target_price))
    rr = None
    if entry is None:
        reason = "skipped_invalid_entry_price"
    elif stop is None:
        reason = "skipped_invalid_stop_price"
    elif entry <= stop:
        reason = "skipped_open_at_or_below_stop"
    elif target_price is None:
        reason = "skipped_target_unavailable_at_entry"
    elif target is None:
        reason = "skipped_invalid_target_price"
    elif target <= entry:
        reason = "skipped_target_not_above_entry"
    else:
        rr = (target - entry) / (entry - stop)
        threshold = float(get_rule("reward_risk_filter").param("rr_min_ideal", 3))
        reason = "accepted" if rr >= threshold else "skipped_actual_reward_risk_below_3"
    return EntryQualification(reason == "accepted", reason, entry, stop, target, rr)
