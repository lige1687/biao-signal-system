"""Money reconciliation, exposure and fixed-comparison diagnostics.

Everything here rebuilds money from actual trades, corporate-action events and
nominal marks. No fitted models, no unexplained "alpha" residual:

    ending equity - initial cash
      = sum over products of
          (net sale proceeds - fee-inclusive purchases
           + dividends actually paid + ending receivable + ending market value)

Reconciliation tolerance is an absolute CNY 0.01 per path and per phase.
"""

from __future__ import annotations

import ast
import hashlib
import re

import numpy as np
import pandas as pd

from .definitions import ROOT, resolve

RECONCILE_TOLERANCE = 0.01

RISK_BINDINGS = {
    "risk.product_account_weight@1.0.0": "market_value_i/equity",
    "risk.direction_account_weight@1.0.0": "group_market_value/equity",
    "risk.product_invested_weight@1.0.0": "market_value_i/sum(market_values)",
    "risk.profit_direction_share@1.0.0": "group_net_pnl/(equity_end-initial_cash)",
}


def _event_symbol_map(actions: list[dict]) -> dict[str, str]:
    mapping = {}
    for a in actions:
        event_id = a.get("event_id")
        if not event_id:
            continue
        sym = str(a["symbol"]).split(".")[0].replace("sh", "").replace("sz", "")
        if event_id in mapping and mapping[event_id] != sym:
            raise ValueError(f"event_id maps to multiple symbols: {event_id}")
        mapping[event_id] = sym
    return mapping


def _split_map(actions: list[dict]) -> dict[tuple[str, str], float]:
    out = {}
    for a in actions:
        typ = a.get("type") or a.get("action_type")
        if typ != "split":
            continue
        sym = str(a["symbol"]).split(".")[0]
        day = a.get("effective_date") or a.get("ex_date")
        ratio = float(a.get("ratio", a.get("split_ratio", 1)))
        out[(day, sym)] = ratio
    return out


def build_marks(
    dates, symbols, prices: pd.DataFrame, actions: list[dict]
) -> pd.DataFrame:
    """Last nominal close carried to non-quote days; splits rescale old marks."""
    p = prices.copy()
    p["symbol"] = p.symbol.astype(str).str.split(".").str[0].str.zfill(6)
    quotes = {
        (r.date, r.symbol): float(r.close)
        for r in p[["date", "symbol", "close"]].itertuples(index=False)
        if pd.notna(r.close) and np.isfinite(r.close) and r.close > 0
    }
    splits = _split_map(actions)
    marks: dict[str, float] = {}
    rows = []
    for day in sorted(dates):
        for s in symbols:
            if (day, s) in splits and s in marks:
                marks[s] /= splits[(day, s)]
            if (day, s) in quotes:
                marks[s] = quotes[(day, s)]
            rows.append(dict(date=day, symbol=s, mark=marks.get(s, 0.0)))
    return pd.DataFrame(rows)


def _event_symbol(events: pd.DataFrame, mapping: dict[str, str]):
    for eid in events.event_id.unique():
        if eid not in mapping:
            raise ValueError(f"event_id has no action->symbol mapping: {eid}")
    return events.event_id.map(mapping)


def capital_contributions(
    *,
    equity: pd.DataFrame,
    trades: pd.DataFrame,
    events: pd.DataFrame,
    actions: list[dict],
    prices: pd.DataFrame,
    initial: float,
) -> pd.DataFrame:
    mapping = _event_symbol_map(actions)
    end = equity.iloc[-1]
    end_date = end["date"]
    symbols = [c.removeprefix("units_") for c in equity.columns if c.startswith("units_")]

    rows = []
    for s in sorted(set(symbols) | set(trades.symbol.unique())):
        st = trades[trades.symbol == s]
        purchases = float((st[st.side == "buy"].notional + st[st.side == "buy"].fee).sum())
        sales = float((st[st.side == "sell"].notional - st[st.side == "sell"].fee).sum())
        se = events.copy()
        if len(se):
            se = se[se.event_id.map(lambda x, sym=s: mapping.get(x) == sym)]
        paid = float(se[se.event == "cash_paid"].amount.sum()) if len(se) else 0.0
        accrued = float(se[se.event == "receivable"].amount.sum()) if len(se) else 0.0
        ending_receivable = accrued - paid
        units = float(end.get(f"units_{s}", 0.0) or 0.0)
        mark_series = build_marks([end_date], [s], prices, actions)
        mark = float(mark_series.mark.iloc[0])
        ending_mv = units * mark
        rows.append(
            dict(
                symbol=s,
                net_sales=sales,
                gross_purchases=purchases,
                cash_dividends_paid=paid,
                ending_receivable=ending_receivable,
                ending_market_value=ending_mv,
                net_contribution=sales - purchases + paid + ending_receivable + ending_mv,
            )
        )
    out = pd.DataFrame(rows)
    if len(events):
        _event_symbol(events, mapping)
    return out


def reconcile(*, contributions: pd.DataFrame, equity: pd.DataFrame, initial: float) -> dict:
    ending_equity = float(equity.iloc[-1].equity)
    total = float(contributions.net_contribution.sum())
    error = total - (ending_equity - initial)
    return {
        "passed": abs(error) <= RECONCILE_TOLERANCE,
        "max_abs_error": abs(error),
        "ending_equity": ending_equity,
        "initial_cash": initial,
        "sum_contribution": total,
        "tolerance_cny": RECONCILE_TOLERANCE,
    }


def _receivable_at(
    events: pd.DataFrame, mapping: dict[str, str], symbol: str, cutoff: str
) -> float:
    if not len(events):
        return 0.0
    se = events[events.event_id.map(lambda x: mapping.get(x) == symbol)]
    accrued = se[(se.event == "receivable") & (se.date <= cutoff)].amount.sum()
    paid = se[(se.event == "cash_paid") & (se.date <= cutoff)].amount.sum()
    return float(accrued - paid)


def phase_contributions(
    *,
    equity: pd.DataFrame,
    opening_equity: pd.DataFrame,
    trades: pd.DataFrame,
    events: pd.DataFrame,
    actions: list[dict],
    prices: pd.DataFrame,
    phase_start: str,
    phase_end: str,
) -> pd.DataFrame:
    mapping = _event_symbol_map(actions)
    start = opening_equity.iloc[-1]
    end = equity.iloc[-1]
    symbols = [
        c.removeprefix("units_")
        for c in pd.Index(equity.columns).union(pd.Index(opening_equity.columns))
        if c.startswith("units_")
    ]
    marks = build_marks([start["date"], end["date"]], sorted(set(symbols)), prices, actions)
    mark_at = {r.date: {} for r in marks.itertuples(index=False)}
    for r in marks.itertuples(index=False):
        mark_at[r.date][r.symbol] = r.mark

    rows = []
    for s in sorted(set(symbols) | set(trades.symbol.unique())):
        st = trades[trades.symbol == s]
        purchases = float((st[st.side == "buy"].notional + st[st.side == "buy"].fee).sum())
        sales = float((st[st.side == "sell"].notional - st[st.side == "sell"].fee).sum())
        se = (
            events[events.event_id.map(lambda x, sym=s: mapping.get(x) == sym)]
            if len(events)
            else events
        )
        in_window = (se.date > start["date"]) & (se.date <= end["date"])
        paid = float(se[in_window & (se.event == "cash_paid")].amount.sum()) if len(se) else 0.0
        mv0 = float(start.get(f"units_{s}", 0.0) or 0.0) * mark_at[start["date"]].get(s, 0.0)
        mv1 = float(end.get(f"units_{s}", 0.0) or 0.0) * mark_at[end["date"]].get(s, 0.0)
        rec0 = _receivable_at(events, mapping, s, start["date"])
        rec1 = _receivable_at(events, mapping, s, end["date"])
        net = sales - purchases + paid + (mv1 - mv0) + (rec1 - rec0)
        rows.append(
            dict(
                phase_start=phase_start,
                phase_end=phase_end,
                symbol=s,
                net_sales=sales,
                gross_purchases=purchases,
                cash_dividends_paid=paid,
                beginning_market_value=mv0,
                ending_market_value=mv1,
                beginning_receivable=rec0,
                ending_receivable=rec1,
                net_contribution=net,
            )
        )
    return pd.DataFrame(rows)


def load_direction_groups(registry: dict) -> dict[str, str]:
    """Extract the frozen mutually-exclusive symbol->direction literal.

    The controller script writes files at import time, so its groups dict is
    parsed from source rather than imported.
    """
    ref = "risk.direction_account_weight@1.0.0"
    resolve(registry, ref)
    source_key = "concentration_code"
    path = ROOT / registry["sources"][source_key]["path"]
    expected = registry["sources"][source_key]["sha256"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"group mapping source drifted: {path}")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "groups":
                    groups = ast.literal_eval(node.value)
                    if not isinstance(groups, dict) or not groups:
                        raise ValueError("frozen groups literal malformed")
                    return {str(k): str(v) for k, v in groups.items()}
    raise ValueError("groups literal not found in frozen controller")


def _risk_cards(registry: dict) -> dict:
    out = {}
    for ref in RISK_BINDINGS:
        card = resolve(registry, ref)
        out[ref] = {"formula": card["definition"]["formula"], "unit": card["definition"]["unit"]}
    return out


def daily_product_weights(equity: pd.DataFrame, marks: pd.DataFrame) -> pd.DataFrame:
    markp = marks.pivot(index="date", columns="symbol", values="mark").sort_index()
    rows = []
    eq = equity.set_index("date").sort_index()
    common = eq.index.intersection(markp.index)
    for day in common:
        total_mv = 0.0
        per = {}
        for s in markp.columns:
            units = float(eq.loc[day].get(f"units_{s}", 0.0) or 0.0)
            mv = units * float(markp.loc[day, s])
            per[s] = mv
            total_mv += mv
        account_equity = float(eq.loc[day, "equity"])
        for s, mv in per.items():
            rows.append(
                dict(
                    date=day,
                    symbol=s,
                    market_value=mv,
                    account_weight=mv / account_equity if account_equity else np.nan,
                    invested_weight=mv / total_mv if total_mv else np.nan,
                )
            )
    return pd.DataFrame(rows)


def daily_direction_weights(
    equity: pd.DataFrame, groups: dict[str, str], prices: pd.DataFrame, actions: list[dict]
) -> pd.DataFrame:
    """Direction account weights rebuilt from actual units and nominal marks."""
    dates = sorted(equity.date.unique())
    symbols = sorted(groups)
    marks = build_marks(dates, symbols, prices, actions)
    product = daily_product_weights(equity, marks)
    return direction_weights_from_product(product, groups)


def direction_weights_from_product(product_weights: pd.DataFrame, groups: dict[str, str]):
    rows = []
    for (day, group), g in product_weights.assign(
        direction=product_weights.symbol.map(groups)
    ).groupby(["date", "direction"]):
        rows.append(
            dict(date=day, direction=group, account_weight=g.account_weight.sum())
        )
    out = pd.DataFrame(rows).sort_values(["date", "direction"])
    return out


def _max_recovery_wait(equity: pd.Series, dates: pd.Series):
    values = equity.to_numpy(dtype=float)
    days = pd.to_datetime(dates).to_numpy()
    peak = -np.inf
    peak_day = None
    worst = 0
    worst_unrecovered = False
    underwater = False
    for v, day in zip(values, days, strict=False):
        if v > peak:
            peak = v
            peak_day = day
            underwater = False
        elif v < peak - 1e-9:
            underwater = True
        if underwater or v < peak - 1e-9:
            wait = (day - peak_day).astype("timedelta64[D]").astype(int)
            if wait > worst:
                worst = wait
                worst_unrecovered = v < peak - 1e-9
    return worst, bool(worst_unrecovered and values[-1] < peak - 1e-9)


def compare_accounts(accounts: dict[str, dict]) -> pd.DataFrame:
    path_rows = []
    parsed = {}
    for key, acc in accounts.items():
        s = acc["summary"]
        eq = acc["equity"].copy()
        mv = eq.equity - eq.cash - eq.receivable
        wait, unrecovered = _max_recovery_wait(eq.equity, eq.date)
        buys = acc["trades"][acc["trades"].side == "buy"] if len(acc["trades"]) else acc["trades"]
        mean_equity = float(eq.equity.mean())
        turnover = (
            float(buys.notional.sum()) / mean_equity
            if len(buys) and mean_equity
            else 0.0
        )
        periods = {r.period: r.return_ for r in acc["periods"].itertuples(index=False)}
        m = re.fullmatch(r"(E\d\d)-fee(0\.001|0\.002)", key)
        variant, fee = (m.group(1), m.group(2)) if m else (s.get("variant"), f"{s['fee']:.3f}")
        row = dict(
            kind="path",
            key=key,
            variant=variant,
            fee=fee,
            initial=s["initial"],
            final=s["final"],
            net_pnl=s["final"] - s["initial"],
            net_return=s["final"] / s["initial"] - 1,
            cagr=s["cagr"],
            max_drawdown=s["max_drawdown"],
            max_recovery_wait_days=wait,
            unrecovered_at_end=unrecovered,
            avg_invested=float(mv.mean()),
            max_invested=float(mv.max()),
            trades=s["trades"],
            turnover_buy_notional_over_avg_equity=turnover,
            fees=float(s["fees"]),
            ending_cash=float(eq.iloc[-1].cash),
            ending_receivable=float(eq.iloc[-1].receivable),
            phase_2020Dec_2024_return=periods.get("2020Dec-2024"),
            phase_2025_2026Jun_return=periods.get("2025-2026Jun"),
        )
        path_rows.append(row)
        parsed[key] = row

    diff_rows = []
    for fee in ("0.001", "0.002"):
        for a, b, label in (("E11", "E10", "primary"), ("E01", "E00", "secondary")):
            ka, kb = f"{a}-fee{fee}", f"{b}-fee{fee}"
            if ka in parsed and kb in parsed:
                ra, rb = parsed[ka], parsed[kb]
                diff_rows.append(
                    dict(
                        kind="difference",
                        comparison=f"{a}-{b}@fee{fee}",
                        comparison_role=label,
                        fee=fee,
                        net_pnl_difference=ra["net_pnl"] - rb["net_pnl"],
                        net_return_difference=ra["net_return"] - rb["net_return"],
                        cagr_difference=ra["cagr"] - rb["cagr"],
                        max_drawdown_difference=ra["max_drawdown"] - rb["max_drawdown"],
                        max_recovery_wait_days_difference=ra["max_recovery_wait_days"]
                        - rb["max_recovery_wait_days"],
                        fees_difference=ra["fees"] - rb["fees"],
                        trades_difference=ra["trades"] - rb["trades"],
                    )
                )
    return pd.DataFrame(path_rows + diff_rows)
