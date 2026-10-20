"""Read-only, source-bound review of two strategy portfolio accounts.

This module does not run a strategy or infer actual holdings from target lists.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from statistics import mean


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _date(value):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _rows(account, part):
    rows = (account.get(part) or {}).get("series") or []
    result, duplicates = {}, set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not (day := _date(row.get("date"))):
            continue
        if day in result:
            duplicates.add(day)
        else:
            result[day] = row
    for day in duplicates:
        del result[day]
    return result, len(duplicates)


def _curve(rows):
    return [
        {"date": day, "nav": _number(row.get("nav")),
         "equity": _number(row.get("equity")),
         "drawdown": _number(row.get("drawdown"))}
        for day, row in sorted(rows.items())
    ]


def _summary(account):
    source = (account.get("history") or {}).get("summary") or {}
    keys = ("cumulative_return", "max_drawdown", "cost", "average_exposure",
            "trade_count", "longest_recovery_days")
    return {key: _number(source.get(key)) for key in keys}


def _correlation(pairs):
    if len(pairs) < 2:
        return None
    left, right = [p[0] for p in pairs], [p[1] for p in pairs]
    lx, ly = mean(left), mean(right)
    cross = sum((x - lx) * (y - ly) for x, y in pairs)
    xx = sum((x - lx) ** 2 for x in left)
    yy = sum((y - ly) ** 2 for y in right)
    return cross / math.sqrt(xx * yy) if xx > 0 and yy > 0 else None


def _weighted_overlap(left, right, field):
    """Only complete, valid nonlevered weights can support a weight overlap."""
    maps = []
    for rows in (left, right):
        weights = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("symbol"), str):
                return None
            symbol, weight = row["symbol"], _number(row.get(field))
            if not symbol or symbol in weights or weight is None or not 0 <= weight <= 1:
                return None
            weights[symbol] = weight
        if sum(weights.values()) > 1.000001:
            return None
        maps.append(weights)
    return sum(min(maps[0][symbol], maps[1][symbol]) for symbol in maps[0].keys() & maps[1].keys())


def _overlap(left, right, *, weight_field):
    if not isinstance(left, list) or not isinstance(right, list):
        return {"status": "missing", "left_count": None, "right_count": None,
                "common_count": None, "union_count": None, "count_overlap": None,
                "weight_overlap": None, "common_symbols": []}
    l = {row.get("symbol") for row in left if isinstance(row, dict) and isinstance(row.get("symbol"), str)}
    r = {row.get("symbol") for row in right if isinstance(row, dict) and isinstance(row.get("symbol"), str)}
    common, union = l & r, l | r
    complete = len(l) == len(left) and len(r) == len(right)
    return {"status": "available" if l and r and complete else ("empty" if not l and not r else "incomplete"),
            "left_count": len(l), "right_count": len(r), "common_count": len(common),
            "union_count": len(union), "count_overlap": len(common) / len(union) if union and complete else None,
            "weight_overlap": _weighted_overlap(left, right, weight_field) if l and r and complete else None,
            "common_symbols": sorted(common)}


def summarize_portfolio(payload: dict, market: str) -> dict:
    """Summarize the existing 8028 DTO without reading files or changing it."""
    market_id = market.upper()
    markets = payload.get("markets", []) if isinstance(payload, dict) else []
    selected = next((row for row in markets if isinstance(row, dict) and row.get("id") == market_id), None)
    if selected is None:
        return {"market": market_id, "available": False, "reason": "该市场没有策略组合资料。"}
    accounts = {row.get("scheme"): row for row in selected.get("accounts", []) if isinstance(row, dict)}
    if not all(scheme in accounts for scheme in ("mv", "rv")):
        return {"market": market_id, "available": False, "reason": "两套主方案资料不齐。"}
    a, b = accounts["mv"], accounts["rv"]
    ar, adup = _rows(a, "history")
    br, bdup = _rows(b, "history")
    common_dates = sorted(ar.keys() & br.keys())
    comparison = selected.get("comparison") or {}
    # The first record may be the uninvested 100000/100000 initialization.
    # Exclude only this identifiable synthetic observation from daily statistics.
    initial_excluded = []
    if common_dates:
        first = common_dates[0]
        if all(_number(row.get("equity")) == 100000 and _number(row.get("return")) == 0
               for row in (ar[first], br[first])):
            initial_excluded = [first]
    valid = []
    for day in common_dates:
        if day in initial_excluded:
            continue
        x, y = _number(ar[day].get("return")), _number(br[day].get("return"))
        if x is not None and y is not None:
            valid.append((day, x, y))
    both_down = sum(x < 0 and y < 0 for _, x, y in valid)
    either_down = sum(x < 0 or y < 0 for _, x, y in valid)
    correlation = _correlation([(x, y) for _, x, y in valid])
    reported = _number(comparison.get("return_correlation"))
    months = defaultdict(list)
    for day in common_dates:
        months[day[:7]].append(day)
    monthly = []
    for month, days in sorted(months.items()):
        start, end = days[0], days[-1]
        start_returns = [_number(ar[start].get("return")), _number(br[start].get("return"))]
        end_equities = [_number(ar[end].get("equity")), _number(br[end].get("equity"))]
        start_equities = [_number(ar[start].get("equity")), _number(br[start].get("equity"))]
        # Divide out the first day's return so every month includes that day,
        # including the first month of the historical account.
        if any(v is None for v in start_returns + end_equities + start_equities):
            continue
        if any(1 + v <= 0 for v in start_returns) or any(v <= 0 for v in start_equities):
            continue
        bases = [start_equities[i] / (1 + start_returns[i]) for i in (0, 1)]
        returns = [end_equities[i] / bases[i] - 1 for i in (0, 1)]
        monthly.append({"month": month, "start": start, "end": end,
                        "mv_return": returns[0], "rv_return": returns[1],
                        "both_down": all(value < 0 for value in returns)})
    combo = comparison.get("combined_history") or {}
    combo_rows, combo_duplicates = _rows({"history": combo}, "history")
    combo_summary = combo.get("summary") or {}
    history_target = _number(comparison.get("holding_overlap"))
    fa, fb = a.get("forward") or {}, b.get("forward") or {}
    targets = _overlap(fa.get("targets"), fb.get("targets"), weight_field="target_weight")
    holdings = _overlap(fa.get("holdings"), fb.get("holdings"), weight_field="weight")
    far, _ = _rows({"forward": fa}, "forward")
    fbr, _ = _rows({"forward": fb}, "forward")
    forward_days = sorted(far.keys() & fbr.keys())
    forward_valid = []
    for day in forward_days:
        x, y = _number(far[day].get("return")), _number(fbr[day].get("return"))
        x_equity, y_equity = _number(far[day].get("equity")), _number(fbr[day].get("equity"))
        if None not in (x, y, x_equity, y_equity):
            forward_valid.append((day, x, y, x_equity, y_equity))
    forward_both_down = [row for row in forward_valid if row[1] < 0 and row[2] < 0]
    # Each independent account starts with 100000; the combined account assigns
    # half the initial capital to each and makes no daily transfers.
    forward_joint_loss = sum(
        (-row[1] * row[3] / (1 + row[1]) - row[2] * row[4] / (1 + row[2])) / 2
        for row in forward_both_down
    ) if forward_valid and all(row[1] > -1 and row[2] > -1 for row in forward_both_down) else None
    return {
        "market": market_id, "available": True, "source": "/api/strategy-portfolios",
        "generated_at": payload.get("generated_at"), "source_date": selected.get("source_date"),
        "history": {
            "status": "historical_quote_account_proxy" if valid else "no_common_valid_returns",
            "period_start": common_dates[0] if common_dates else None,
            "period_end": common_dates[-1] if common_dates else None,
            "common_curve_days": len(common_dates), "common_valid_return_days": len(valid),
            "initialization_dates_excluded": initial_excluded,
            "duplicate_dates_excluded": {"mv": adup, "rv": bdup, "combined": combo_duplicates},
            "both_down_days": both_down, "either_down_days": either_down,
            "both_down_share_all_valid_days": both_down / len(valid) if valid else None,
            "both_down_share_either_down_days": both_down / either_down if either_down else None,
            "return_correlation_recomputed": correlation, "return_correlation_reported": reported,
            "return_correlation_difference": correlation - reported if correlation is not None and reported is not None else None,
            "monthly": {"common_months": len(monthly), "both_down_months": sum(row["both_down"] for row in monthly),
                        "series": monthly},
            "targets": {"status": "last_historical_month_targets_only", "count_overlap": history_target,
                        "common_count": None, "weight_overlap": None, "date": None},
            "accounts": {"mv": {"name": a.get("name"), "summary": _summary(a), "curve": _curve(ar)},
                         "rv": {"name": b.get("name"), "summary": _summary(b), "curve": _curve(br)}},
            "combined": {"summary_source": "upstream_combined_history",
                         "summary": {key: _number(combo_summary.get(key)) for key in
                                     ("cumulative_return", "max_drawdown", "cost", "average_exposure")},
                         "curve": _curve(combo_rows)},
        },
        "forward": {"started_at": payload.get("started_at"), "common_recorded_days": len(forward_days),
                    "common_valid_return_days": len(forward_valid),
                    "first_recorded_date": forward_days[0] if forward_days else None,
                    "last_recorded_date": forward_days[-1] if forward_days else None,
                    "both_down_days": len(forward_both_down) if forward_valid else None,
                    "both_down_loss_50_50_initial_capital": forward_joint_loss,
                    "targets": targets, "holdings": holdings},
        "conclusion": (f"历史{len(valid)}个共同有效收益日中，{both_down}日同跌；尚不能确认是否由同一种风格驱动。"
                       if valid else "缺少共同有效收益资料，暂不能评价共同亏损。"),
        "limitations": ["历史是已看过的个股报价模拟，不是ETF或真实账户成绩。",
                        "两方案都使用低波动信息；相关和共同亏损不能单独证明同一风格。",
                        "历史目标名单只有重合比例，没有逐日实际持仓权重或目标名单日期。",
                        "前向目标名单不是成交持仓；空持仓不能按零风险重合解释。",
                        "同跌日损失金额为每日亏损相加，不等于整段净亏损或最大跌幅。",
                        "共同收益中的零值可能包含沿用旧价格，不能当作独立风险来源。"],
    }
