import math
from datetime import date
from typing import Any, Dict, Iterable


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _to_float(value: Any, field: str) -> float:
    if not _is_number(value):
        raise ValueError(f"Field '{field}' must be a finite number")
    float_value = float(value)
    if not math.isfinite(float_value):
        raise ValueError(f"Field '{field}' must be finite")
    return float_value


def _mean(values: Iterable[float]) -> float | None:
    values = list(values)
    if not values:
        return None
    return sum(values) / len(values)


def _median(values: Iterable[float]) -> float | None:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _parse_date(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("Date must be ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Date must be ISO date string") from exc


def _to_dict(data: Any, label: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")
    return data


def summarize(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("result must be a mapping")

    daily = result.get("daily", [])
    if not isinstance(daily, list) or not daily:
        raise ValueError("daily must be a non-empty list")

    trades = result.get("trades", [])
    if not isinstance(trades, list):
        raise ValueError("trades must be a list")

    orders = result.get("orders", [])
    if not isinstance(orders, list):
        raise ValueError("orders must be a list")

    roundtrips = result.get("roundtrips", [])
    if not isinstance(roundtrips, list):
        raise ValueError("roundtrips must be a list")

    equity_vals = []
    funding_vals = []
    rows_for_exposure = []
    max_drawdown = 0.0
    hwm = 1.0
    drawdown_start = None
    longest_drawdown_days = 0
    unrecovered_at_end = False

    for row in daily:
        row_map = _to_dict(row, "daily row")
        row_date = _parse_date(row_map.get("date"))

        equity = _to_float(row_map.get("equity"), "equity")
        assets = _to_float(row_map.get("assets"), "assets")
        cash = _to_float(row_map.get("cash"), "cash")
        receivable = _to_float(row_map.get("receivable"), "receivable")
        total_funding = _to_float(row_map.get("total_funding"), "total_funding")
        nav = _to_float(row_map.get("nav"), "nav")
        fees = _to_float(row_map.get("fees"), "fees")

        equity_vals.append(equity)
        funding_vals.append(total_funding)

        if equity > 0:
            rows_for_exposure.append((assets, equity))

        if nav <= 0.0:
            raise ValueError("nav must be positive")

        if nav < hwm:
            if drawdown_start is None:
                drawdown_start = row_date
            drawdown = (hwm - nav) / hwm
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        else:
            if drawdown_start is not None:
                recovery_days = (row_date - drawdown_start).days
                if recovery_days > longest_drawdown_days:
                    longest_drawdown_days = recovery_days
                drawdown_start = None
            hwm = max(hwm, nav)

        last_row = row_map

    if drawdown_start is not None:
        recovery_days = (date.fromisoformat(last_row["date"]) - drawdown_start).days
        if recovery_days > longest_drawdown_days:
            longest_drawdown_days = recovery_days
        unrecovered_at_end = True

    last_equity = equity_vals[-1]
    last_funding = funding_vals[-1]
    last_cash = cash
    last_assets = assets
    last_receivable = receivable
    last_fees = fees

    if not math.isfinite(last_equity):
        raise ValueError("non-finite last equity")

    exposure_values = []
    zero_exposure_days = 0
    for a, e in rows_for_exposure:
        exposure_values.append(a / e if e != 0 else 0.0)
        if a == 0.0:
            zero_exposure_days += 1
    mean_exposure = _mean(exposure_values) if exposure_values else None

    trade_count = len(trades)
    buys = 0
    sells = 0
    for t in trades:
        trade = _to_dict(t, "trade")
        side = str(trade.get("side", "")).lower()
        if side == "buy":
            buys += 1
        elif side == "sell":
            sells += 1

    order_status_counts: Dict[str, int] = {}
    rejection_reason_counts: Dict[str, int] = {}
    for o in orders:
        order = _to_dict(o, "order")
        status = str(order.get("status"))
        order_status_counts[status] = order_status_counts.get(status, 0) + 1
        if status.lower() == "rejected":
            reason = order.get("reason")
            if reason is None or reason == "":
                reason = "UNKNOWN"
            reason = str(reason)
            rejection_reason_counts[reason] = rejection_reason_counts.get(reason, 0) + 1

    completed = []
    open_positions = 0
    holding_days = []
    for r in roundtrips:
        rt = _to_dict(r, "roundtrip")
        is_closed = bool(rt.get("closed", False))
        if not is_closed:
            open_positions += 1
            continue

        net_pnl = _to_float(rt.get("net_pnl"), "net_pnl")
        net_return = _to_float(rt.get("net_return"), "net_return")
        entry_date = _parse_date(rt.get("entry_date"))
        exit_date = _parse_date(rt.get("exit_date") or rt.get("valuation_date"))

        if exit_date < entry_date:
            raise ValueError("exit_date before entry_date")
        completed.append({
            "net_pnl": net_pnl,
            "net_return": net_return,
            "holding_days": (exit_date - entry_date).days,
        })
        holding_days.append((exit_date - entry_date).days)

    completed_trades = len(completed)
    profitable_closed_count = sum(1 for c in completed if c["net_pnl"] > 0)
    closed_win_fraction = (
        profitable_closed_count / completed_trades
        if completed_trades > 0
        else None
    )

    closed_net_pnls = [c["net_pnl"] for c in completed]
    closed_net_returns = [c["net_return"] for c in completed]

    closed_mean_net_pnl = _mean(closed_net_pnls)
    closed_median_net_pnl = _median(closed_net_pnls)
    closed_mean_net_return = _mean(closed_net_returns)
    closed_median_net_return = _median(closed_net_returns)
    closed_min_pnl = min(closed_net_pnls) if closed_net_pnls else None

    if completed_trades > 0:
        worst_count = math.ceil(0.05 * completed_trades)
        worst_count = max(1, worst_count)
        worst_pnls = sorted(closed_net_pnls)[:worst_count]
        worst5_mean_net_pnl = sum(worst_pnls) / worst_count
    else:
        worst_count = 0
        worst5_mean_net_pnl = None

    mean_holding_days = _mean(holding_days)

    return {
        "last_equity": last_equity,
        "total_funding": last_funding,
        "net_gain": last_equity - last_funding,
        "cash": last_cash,
        "assets": last_assets,
        "receivable": last_receivable,
        "fees": last_fees,
        "trade_count": trade_count,
        "buys": buys,
        "sells": sells,
        "max_drawdown": max_drawdown,
        "longest_drawdown_days": longest_drawdown_days,
        "unrecovered_at_end": unrecovered_at_end,
        "worst_below_funding": min(last_equity - last_funding, 0.0),
        "mean_exposure": mean_exposure,
        "zero_exposure_days": zero_exposure_days,
        "completed_trades": completed_trades,
        "open_positions": open_positions,
        "profitable_closed_count": profitable_closed_count,
        "closed_win_fraction": closed_win_fraction,
        "closed_mean_net_pnl": closed_mean_net_pnl,
        "closed_median_net_pnl": closed_median_net_pnl,
        "closed_min_pnl": closed_min_pnl,
        "closed_mean_net_return": closed_mean_net_return,
        "closed_median_net_return": closed_median_net_return,
        "worst5_count": worst_count,
        "worst5_mean_net_pnl": worst5_mean_net_pnl,
        "mean_holding_days": mean_holding_days,
        "order_status_counts": order_status_counts,
        "rejection_reason_counts": rejection_reason_counts,
    }
