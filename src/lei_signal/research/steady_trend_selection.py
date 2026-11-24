"""Fixed, retrospective monthly ETF selection research; no trading interface.

``build_features`` never reads future observations. ``run_study`` is the only
entry point that reads later prices, and preserves immature/invalid months.
Input is the qualified workflow-input JSON shape (calendar and bars).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import calendar as calendar_module
import math

import numpy as np


METHODS = ("momentum120", "slope120", "slope_r2_120", "vol_adjusted120",
           "color_then_momentum", "equal_weight")


def _positive(x):
    return isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def _valid_ohlc(row):
    if not row or row.get("status") != "quoted" or row.get("action_known") is not True:
        return False
    if not all(_positive(row.get(k)) for k in ("open", "high", "low", "close")):
        return False
    o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
    eps = 1e-12 * max(1.0, h)
    return l <= h + eps and l - eps <= min(o, c) and max(o, c) <= h + eps


def _validate(data, design):
    calendar = data["calendar"]
    if not calendar or calendar != sorted(set(calendar)):
        raise ValueError("calendar must be sorted and unique")
    assets = tuple(a for group in design["groups"].values() for a in group)
    if len(set(assets)) != len(assets):
        raise ValueError("group assets overlap")
    bars = {}
    for row in data["bars"]:
        key = row["asset"], row["date"]
        if key in bars or key[0] not in assets or key[1] not in calendar:
            raise ValueError("duplicate or out-of-scope bar")
        bars[key] = row
    return calendar, bars


def _regression(prices):
    y = np.log(np.asarray(prices, dtype=float))
    x = np.arange(len(y), dtype=float)
    yc = y - y.mean()
    xc = x - x.mean()
    sst = float(yc @ yc)
    if sst <= 1e-24:
        return 0.0, 0.0
    slope = float((xc @ yc) / (xc @ xc))
    residual = yc - slope * xc
    r2 = min(1.0, max(0.0, 1.0 - float(residual @ residual) / sst))
    return slope * 252.0, r2


def _month_ends(calendar):
    """Only a following exchange session proves a prior calendar month ended."""
    out = [calendar[i] for i in range(len(calendar) - 1)
           if calendar[i][:7] != calendar[i + 1][:7]]
    last = date.fromisoformat(calendar[-1])
    if last.day == calendar_module.monthrange(last.year, last.month)[1]:
        out.append(calendar[-1])
    return out


def _next_month_open(calendar, signal):
    month = signal[:7]
    return next((d for d in calendar if d > signal and d[:7] != month), None)


def _next_open_after(calendar, entry):
    month = entry[:7]
    return next((d for d in calendar if d > entry and d[:7] != month), None)


def build_features(data, design):
    """Return one row per completed month and asset, including unknown reasons.

    The 120 prices are consecutive *exchange-calendar* sessions ending at the
    signal close. A bad/absent OHLC bar resets both the 120-day window and EMA.
    The function needs only the prefix through each signal and never uses labels.
    """
    calendar, bars = _validate(data, design)
    if design["lookback"] != 120:
        raise ValueError("this frozen study requires 120 closes")
    ends = set(_month_ends(calendar))
    rows = []
    for asset in sorted({a for g in design["groups"].values() for a in g}):
        history = []
        ema = None
        for d in calendar:
            row = bars.get((asset, d))
            valid = _valid_ohlc(row)
            if not valid:
                history = []
                ema = None
            else:
                c = float(row["close"])
                history.append(c)
                if len(history) == 20:
                    ema = math.fsum(history) / 20
                elif len(history) > 20:
                    ema = (2 / 21) * c + (19 / 21) * ema
            if d not in ends or not (design["signal_start"] <= d <= design["signal_end"]):
                continue
            result = {"asset": asset, "signal": d, "eligible": False,
                      "reason": "missing_or_short_contiguous_history", "scores": None, "color": None}
            if len(history) >= 120:
                window = history[-120:]
                log_returns = np.diff(np.log(np.asarray(window, dtype=float)))
                slope, r2 = _regression(window)
                denominator = float(np.sqrt(log_returns @ log_returns))
                momentum = math.log(window[-1] / window[0])
                color = ("green" if window[-1] > ema and window[-1] > history[-21]
                         else "black" if window[-1] < ema and window[-1] < history[-21]
                         else "gray")
                result.update(eligible=True, reason=None, color=color,
                              scores={"momentum120": momentum, "slope120": slope,
                                      "r_squared": r2, "slope_r2_120": slope * r2,
                                      "vol_adjusted120": float(log_returns.sum()) / denominator
                                      if denominator else 0.0})
            rows.append(result)
    return rows


def _rank(features, method, assets):
    if method == "equal_weight":
        return {a: 0.25 for a in assets}, list(assets)
    if method == "color_then_momentum":
        order = {"green": 2, "gray": 1, "black": 0}
        ranked = sorted(assets, key=lambda a: (-order[features[a]["color"]],
                                                -features[a]["scores"]["momentum120"], a))
    else:
        ranked = sorted(assets, key=lambda a: (-features[a]["scores"][method], a))
    return {a: (0.5 if a in ranked[:2] else 0.0) for a in assets}, ranked


def _rebalance(before, current, weights, fee):
    """Solve target holdings after fee using bisection, including first buy."""
    def turnover(after):
        return math.fsum(abs(weights[a] * after - current[a]) for a in weights)
    lo, hi = 0.0, before
    for _ in range(80):
        mid = (lo + hi) / 2
        if mid + fee * turnover(mid) > before:
            hi = mid
        else:
            lo = mid
    after = (lo + hi) / 2
    traded = turnover(after)
    return after, traded, fee * traded, {a: weights[a] * after for a in weights}


def _drawdown(marks):
    peak = 0.0
    worst = 0.0
    for v in marks:
        peak = max(peak, v)
        if peak:
            worst = min(worst, v / peak - 1)
    return worst


def _spearman(scores, returns):
    a = np.asarray(scores, dtype=float)
    b = np.asarray(returns, dtype=float)
    if np.all(a == a[0]) or np.all(b == b[0]):
        return None
    def rank(v):
        idx = np.argsort(v, kind="stable")
        out = np.empty(len(v), dtype=float)
        for value in np.unique(v):
            at = np.where(v == value)[0]
            out[at] = (sum(np.searchsorted(v[idx], value, side=s) for s in ("left", "right")) - 1) / 2
        return out
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def _bootstrap(values, design):
    if not values:
        return None
    cfg = design["uncertainty"]
    rng = np.random.default_rng(cfg["seed"])
    n, block = len(values), cfg["block_months"]
    draws = np.empty(cfg["replicates"], dtype=float)
    v = np.asarray(values, dtype=float)
    for i in range(len(draws)):
        starts = rng.integers(0, n, size=math.ceil(n / block))
        idx = [(int(s) + j) % n for s in starts for j in range(block)][:n]
        draws[i] = v[idx].mean()
    alpha = (1 - cfg["interval"]) / 2
    return {"lower": float(np.quantile(draws, alpha)),
            "upper": float(np.quantile(draws, 1-alpha)), "block_months": block,
            "replicates": len(draws), "seed": cfg["seed"]}


def _account(periods, weights, fee, assets, bars, calendar, initial):
    shares = {a: 0.0 for a in assets}
    cash = initial
    months, marks = [], [{"date": periods[0]["entry"], "kind": "initial_capital", "nav": initial}]
    per_asset = defaultdict(lambda: {"selected_months": 0, "gross_contribution": 0.0})
    for p in periods:
        entry, exit_ = p["entry"], p["exit"]
        op = {a: float(bars[a, entry]["open"]) for a in assets}
        xp = {a: float(bars[a, exit_]["open"]) for a in assets}
        current = {a: shares[a] * op[a] for a in assets}
        before = cash + math.fsum(current.values())
        w = weights[p["signal"]]
        after, turnover, fees, target = _rebalance(before, current, w, fee)
        shares = {a: target[a] / op[a] for a in assets}
        cash = after - math.fsum(target.values())
        marks.append({"date": entry, "kind": "before_open_rebalance", "nav": before})
        marks.append({"date": entry, "kind": "after_open_rebalance", "nav": after})
        for d in calendar:
            if entry <= d < exit_:
                marks.append({"date": d, "kind": "close",
                              "nav": cash + math.fsum(shares[a] * bars[a, d]["close"] for a in assets)})
        end = cash + math.fsum(shares[a] * xp[a] for a in assets)
        marks.append({"date": exit_, "kind": "exit_open", "nav": end})
        gross = math.fsum(w[a] * (xp[a] / op[a] - 1) for a in assets)
        for a in assets:
            if w[a]:
                per_asset[a]["selected_months"] += 1
                per_asset[a]["gross_contribution"] += w[a] * (xp[a] / op[a] - 1)
        months.append({"signal": p["signal"], "entry": entry, "exit": exit_,
                       "before_rebalance": before, "after_rebalance": after,
                       "exit_wealth": end, "net_return": end / before - 1,
                       "gross_return": gross, "turnover": turnover,
                       "turnover_fraction": turnover / before, "fee_paid": fees,
                       "weights": w})
    first, last = date.fromisoformat(periods[0]["entry"]), date.fromisoformat(periods[-1]["exit"])
    years = (last - first).days / 365.25
    wealth = months[-1]["exit_wealth"]
    return {"months": months, "daily_nav": marks,
            "performance": {"terminal_wealth": wealth, "total_return": wealth / initial - 1,
                            "cagr": (wealth / initial) ** (1 / years) - 1 if years else None,
                            "max_drawdown": _drawdown([m["nav"] for m in marks]),
                            "mean_monthly_net_return": float(np.mean([m["net_return"] for m in months])),
                            "total_turnover": sum(m["turnover"] for m in months),
                            "total_fees": sum(m["fee_paid"] for m in months),
                            "first_entry": periods[0]["entry"], "last_exit": periods[-1]["exit"],
                            "periods": len(months)},
            "per_etf": dict(per_asset)}


def _paired(candidate, opponent, periods, features, assets, design):
    cm, om = candidate["months"], opponent["months"]
    diffs = [c["net_return"] - o["net_return"] for c, o in zip(cm, om)]
    changed = []
    replaced = {"avoided_losses": 0.0, "foregone_gains": 0.0,
                "inserted_gains": 0.0, "inserted_losses": 0.0}
    best = capture = positive_winners = 0
    positive_maxima = [max(p["asset_returns"].values()) for p in periods
                       if max(p["asset_returns"].values()) > 0]
    extreme_threshold = (float(np.quantile(positive_maxima, 0.75, method="linear"))
                         if positive_maxima else None)
    extreme_count = 0
    extreme_capture = 0.0
    contributions = []
    for p, c, o, delta in zip(periods, cm, om, diffs):
        returns = p["asset_returns"]
        old = {a for a in assets if o["weights"][a] > 0}
        new = {a for a in assets if c["weights"][a] > 0}
        if old != new:
            changed.append(p["signal"])
        for a in old-new:
            v = 0.5 * returns[a]
            replaced["avoided_losses" if v < 0 else "foregone_gains"] += abs(v)
        for a in new-old:
            v = 0.5 * returns[a]
            replaced["inserted_gains" if v > 0 else "inserted_losses"] += abs(v)
        maximum = max(returns.values())
        best_assets = [a for a in assets if returns[a] == maximum]
        month_capture = sum(a in new for a in best_assets) / len(best_assets)
        best += month_capture
        if extreme_threshold is not None and maximum > 0 and maximum >= extreme_threshold:
            extreme_count += 1
            extreme_capture += month_capture
        winners = [a for a in assets if returns[a] > 0]
        positive_winners += len(winners)
        capture += sum(a in new for a in winners)
        contributions.append({"signal": p["signal"], "net_return_difference": delta,
                              "candidate_selected": sorted(new), "opponent_selected": sorted(old)})
    annual = {}
    for year in sorted({p["signal"][:4] for p in periods}):
        xs = [d for p, d in zip(periods, diffs) if p["signal"].startswith(year)]
        annual[year] = {"count": len(xs), "mean_net_difference": float(np.mean(xs)),
                        "sum_net_difference": sum(xs)}
    phases = {}
    for name, lo, hi in (("2022_2023", "2022", "2023"), ("2024_2026H1", "2024", "2026")):
        xs = [d for p, d in zip(periods, diffs) if lo <= p["signal"][:4] <= hi]
        phases[name] = {"count": len(xs), "mean_net_difference": float(np.mean(xs)) if xs else None}
    leave_one_year = {}
    for year in annual:
        xs = [d for p, d in zip(periods, diffs) if p["signal"][:4] != year]
        leave_one_year[year] = float(np.mean(xs)) if xs else None
    return {"mean_monthly_net_difference": float(np.mean(diffs)),
            "uncertainty_95": _bootstrap(diffs, design), "annual": annual,
            "phases": phases, "changed_selection_months": changed,
            "changed_selection_count": len(changed), "replaced_assets_gross_half_weight": replaced,
            "best_etf_selected_rate": best / len(periods),
            "best_etf_selected_numerator": best,
            "best_etf_selected_denominator": len(periods),
            "top_quartile_positive_winner_capture": {
                "rate": extreme_capture / extreme_count if extreme_count else None,
                "fractional_capture": extreme_capture, "extreme_months": extreme_count,
                "positive_maximum_months": len(positive_maxima),
                "positive_maximum_75th_percentile": extreme_threshold},
            "positive_etf_winners_capture": capture / positive_winners if positive_winners else None,
            "top3_absolute_difference_months": sorted(contributions,
                key=lambda x: (-abs(x["net_return_difference"]), x["signal"]))[:3],
            "leave_one_year_mean_difference": leave_one_year,
            "monthly_pairs": contributions}


def run_study(data, design):
    """Evaluate the frozen policy; return JSON-serializable, explicit unknowns.

    No filtering on realized outcomes is permitted except the declared requirement
    that all four group assets have executable/valuable bars through exit open.
    """
    calendar, bars = _validate(data, design)
    features = build_features(data, design)
    by_signal = defaultdict(dict)
    for f in features:
        by_signal[f["signal"]][f["asset"]] = f
    result = {"research_id": design["research_id"], "feature_rows": features,
              "groups": {}, "unmatured": [], "invalid": []}
    for group, assets_list in design["groups"].items():
        assets = tuple(assets_list)
        periods = []
        weights = {m: {} for m in METHODS}
        ics = []
        interrupted = False
        for signal in sorted(by_signal):
            if interrupted:
                result["invalid"].append({"group": group, "signal": signal,
                                          "reason": "after_continuity_break"})
                continue
            f = by_signal[signal]
            if not all(a in f and f[a]["eligible"] for a in assets):
                result["invalid"].append({"group": group, "signal": signal,
                                          "reason": "group_four_features_not_ready"})
                if periods:
                    interrupted = True
                continue
            entry = _next_month_open(calendar, signal)
            exit_ = _next_open_after(calendar, entry) if entry else None
            if not entry or not exit_ or exit_ > design["evaluation_end"]:
                result["unmatured"].append({"group": group, "signal": signal,
                                            "reason": "missing_next_entry_or_following_exit_open"})
                continue
            days = [d for d in calendar if entry <= d < exit_]
            needed = list(days) + [exit_]
            if any(not _valid_ohlc(bars.get((a, d))) for a in assets for d in needed):
                result["invalid"].append({"group": group, "signal": signal,
                                          "reason": "future_trade_or_valuation_unknown"})
                interrupted = True
                continue
            asset_returns = {a: bars[a, exit_]["open"] / bars[a, entry]["open"] - 1 for a in assets}
            periods.append({"signal": signal, "entry": entry, "exit": exit_,
                            "asset_returns": asset_returns})
            for method in METHODS:
                weights[method][signal], _ = _rank(f, method, assets)
            score = [f[a]["scores"]["slope_r2_120"] for a in assets]
            ic = _spearman(score, [asset_returns[a] for a in assets])
            ics.append({"signal": signal, "rank_ic": ic})
        if not periods:
            result["groups"][group] = {"periods": [], "accounts": {},
                                        "rank_ic": ics, "paired": {}, "reason": "no_complete_periods"}
            continue
        accounts = {}
        for fee in design["policy"]["fees_per_side"]:
            fee_key = f"{fee:.4f}"
            accounts[fee_key] = {method: _account(periods, weights[method], fee, assets,
                                                   bars, calendar, design["policy"]["initial_capital"])
                                 for method in METHODS}
        primary = accounts[f"{design['policy']['primary_fee']:.4f}"]
        paired = {"candidate_minus_momentum": _paired(primary["slope_r2_120"],
                    primary["momentum120"], periods, by_signal, assets, design),
                  "candidate_minus_slope": _paired(primary["slope_r2_120"],
                    primary["slope120"], periods, by_signal, assets, design)}
        valid_ic = [x["rank_ic"] for x in ics if x["rank_ic"] is not None]
        result["groups"][group] = {"periods": periods, "accounts": accounts,
                                    "rank_ic": ics,
                                    "mean_rank_ic": float(np.mean(valid_ic)) if valid_ic else None,
                                    "paired": paired}
    return result
