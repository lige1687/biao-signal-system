"""Market context historical research — Round 4.

Non-filtering join of market context onto forward outcome data.
Adds context columns without dropping or selecting signals.
Groups by context dimensions for descriptive statistics.

Design spec section 14.
"""

from __future__ import annotations

import pandas as pd


def attach_market_context(
    outcomes: pd.DataFrame,
    contexts: pd.DataFrame,
    market_clock: str = "Asia/Shanghai",
) -> pd.DataFrame:
    """Attach market context to forward outcome rows using as-of joins.

    Each outcome row gets the latest context available before its
    signal_date. Missing context yields 'unknown', not 'neutral'.

    Args:
        outcomes: DataFrame from build_forward_outcomes() with signal_date column.
        contexts: DataFrame of market context assessments indexed by date.
        market_clock: Timezone for market close decision timestamps.

    Returns:
        outcomes DataFrame with additional market context columns.
        Row count is preserved. Signal keys, returns, MFE, MAE unchanged.
    """
    if outcomes.empty:
        return outcomes.assign(context_summary="unknown")

    result = outcomes.copy()

    # Ensure signal_date is datetime
    if "signal_date" in result.columns:
        result["_decision_ts"] = pd.to_datetime(result["signal_date"])

    # Default context columns
    result["context_summary"] = "unknown"
    result["context_long_regime"] = "unknown"
    result["context_heat_state"] = "unknown"
    result["context_breadth_direction"] = "unknown"

    if contexts.empty:
        return result.drop(columns=["_decision_ts"], errors="ignore")

    # For each outcome row, find the latest context before decision date
    for idx, row in result.iterrows():
        decision_date = row.get("_decision_ts")
        if decision_date is None or pd.isna(decision_date):
            continue

        # Find contexts available before this date
        prior = contexts[contexts.index <= decision_date]
        if prior.empty:
            continue

        # Use the most recent
        latest = prior.iloc[-1]
        result.at[idx, "context_summary"] = latest.get("summary", "unknown")
        result.at[idx, "context_long_regime"] = latest.get("long_regime", "unknown")
        result.at[idx, "context_heat_state"] = latest.get("heat_state", "unknown")
        result.at[idx, "context_breadth_direction"] = latest.get("breadth_direction", "unknown")

    result.drop(columns=["_decision_ts"], errors="ignore", inplace=True)
    return result


def summarize_outcomes_by_context(
    enriched: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize outcome statistics grouped by context dimension.

    Groups by context_summary and computes sample count, mean return,
    median return, MFE, MAE, and missing rate for each group.

    Does NOT output an optimized filter or recommended threshold.
    """
    if enriched.empty or "context_summary" not in enriched.columns:
        return pd.DataFrame()

    groups = []
    for summary_val in sorted(enriched["context_summary"].dropna().unique()):
        subset = enriched[enriched["context_summary"] == summary_val]
        group_stats = {
            "context_summary": summary_val,
            "sample_count": len(subset),
        }

        for col in ["forward_return_20", "mfe_20", "mae_20"]:
            if col in subset.columns:
                vals = subset[col].dropna()
                group_stats[f"{col}_mean"] = vals.mean() if len(vals) > 0 else None
                group_stats[f"{col}_median"] = vals.median() if len(vals) > 0 else None

        groups.append(group_stats)

    return pd.DataFrame(groups)
