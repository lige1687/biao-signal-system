"""Frozen, descriptive weekly CSI300 ERP crossing study. Standard library only."""
from __future__ import annotations

import bisect
import collections
import datetime as dt
import hashlib
import json
import math
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
BASE = pathlib.Path(__file__).resolve().parent
K = float(sys.argv[1])
assert K in (1,1.5,2)
HERE = BASE / ("sigma-" + str(K))
HERE.mkdir(exist_ok=False)
HORIZONS = (21, 63, 126)
SEED = 20261101


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def three_year_cutoff(day):
    try:
        return day.replace(year=day.year - 3)
    except ValueError:
        return day.replace(year=day.year - 3, day=28)


def quantile(values, q):
    if not values:
        return None
    a = sorted(values)
    position = (len(a) - 1) * q
    lo = int(position)
    hi = min(lo + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (position - lo)


def price_bin(change):
    if change <= -10:
        return "<=-10"
    if change <= 0:
        return "(-10,0]"
    if change <= 10:
        return "(0,10]"
    return ">10"


def block_of(date):
    year = dt.date.fromisoformat(date).year
    first = 2008 + 2 * ((year - 2008) // 2)
    return f"{first}-{first + 1}"


def outcome(prices, index, horizon):
    entry = index + 1
    exit_index = entry + horizon
    if exit_index >= len(prices):
        return None
    base = prices[entry]
    path = [100 * (p / base - 1) for p in prices[entry : exit_index + 1]]
    low = min(range(len(path)), key=path.__getitem__)
    high = max(range(len(path)), key=path.__getitem__)
    return {"entryOffset": 1, "exitOffset": 1 + horizon,
            "returnPct": path[-1], "minMovePct": path[low],
            "minDayFromEntry": low, "maxMovePct": path[high],
            "maxDayFromEntry": high}


def weighted_mean(items):
    total = sum(weight for _, weight in items)
    return sum(value * weight for value, weight in items) / total if total else None


def main():
    contract = json.loads((BASE / "method.json").read_text())
    inputs = {}
    for name, spec in contract["inputs"].items():
        path = ROOT / spec["path"]
        actual = digest(path)
        if actual != spec["sha256"]:
            raise ValueError(f"input fingerprint changed: {name} {actual}")
        inputs[name] = json.loads(path.read_text())
    reference = inputs["weeklyErp"]["points"]
    spine = inputs["sourceWeeklySpine"]["points"]
    price_source = inputs["dailyPrice"]["series"]["hs300"]
    dates = price_source["dates"]
    prices = price_source["values"]
    assert len(dates) == len(prices) and len(set(dates)) == len(dates)
    assert dates == sorted(dates) and all(isinstance(x, (int, float)) and x > 0 and math.isfinite(x) for x in prices)
    price_index = {date: index for index, date in enumerate(dates)}
    reference_by_date = {row["date"]: row for row in reference}
    assert len(reference_by_date) == len(reference)
    assert all(day in price_index for day in reference_by_date)
    first_valid_date = dt.date.fromisoformat(reference[0]["date"])
    warmup_date = first_valid_date.replace(year=first_valid_date.year + 3)

    # Recompute the frozen band from independently loaded reference ERP values.
    valid_history = []
    rows = []
    for source in spine:
        day = source["date"]
        price_i = price_index.get(day)
        ref = reference_by_date.get(day)
        row = {"date": day, "sourceDate": source["sourceDate"], "priceIndex": price_i,
               "peTtm": source["peTtm"], "erp": None, "middle": None,
               "sigma": None, "upper": None, "lower": None, "nWindow": 0,
               "side": None, "firstEntry": None, "B": None, "outcomes": {}}
        if ref is not None:
            assert abs(ref["peTtm"] - source["peTtm"]) < 1e-9
            assert price_i is not None
            assert abs(ref["close"] - prices[price_i]) < 0.011
            value = 100 / source["peTtm"] - ref["cn10y"]
            assert abs(value - ref["value"]) < 0.00000051
            row["erp"] = value
            day_obj = dt.date.fromisoformat(day)
            valid_history.append((day_obj, value))
            cutoff = three_year_cutoff(day_obj)
            window = [v for d, v in valid_history if cutoff < d <= day_obj]
            row["nWindow"] = len(window)
            if day_obj >= warmup_date:
                mu = statistics.fmean(window)
                sd = math.sqrt(statistics.fmean((v - mu) ** 2 for v in window))
                row.update(middle=mu, sigma=sd, upper=mu + K * sd, lower=mu - K * sd)
                row["side"] = "upper" if value > row["upper"] else "lower" if value < row["lower"] else "inside"
        if price_i is not None and price_i >= 199 and price_i >= 63:
            momentum = 100 * (prices[price_i] / prices[price_i - 63] - 1)
            sma = statistics.fmean(prices[price_i - 199 : price_i + 1])
            row["B"] = "|".join((price_bin(momentum), "above200" if prices[price_i] > sma else "notAbove200", "pre2017" if day <= "2016-12-31" else "post2016"))
            row["past63Pct"] = momentum
            row["sma200"] = sma
            for h in HORIZONS:
                row["outcomes"][str(h)] = outcome(prices, price_i, h)
        rows.append(row)

    old = inputs["oldBandsCheckOnly"]
    old_by_date = {x["date"]: x for x in old}
    checks = []
    for row in rows:
        prior = old_by_date.get(row["date"])
        if prior is None or row["erp"] is None:
            continue
        for key in (("middle", "sigma", "upper", "lower") if K == 2 else ("middle", "sigma")):
            a, b = row[key], prior[key]
            if a is None or b is None:
                assert a is None and b is None
            else:
                checks.append(abs(a - b))
    assert len(old_by_date) == len(reference)
    assert max(checks) < 2e-6

    events = []
    for index, row in enumerate(rows):
        if index == 0 or row["side"] not in ("upper", "lower"):
            continue
        prior = rows[index - 1]
        gap = (dt.date.fromisoformat(row["date"]) - dt.date.fromisoformat(prior["date"])).days
        if gap > 10 or prior["side"] is None or prior["side"] == row["side"]:
            continue
        row["firstEntry"] = row["side"]
        row["block"] = block_of(row["date"])
        events.append(row)

    # Controls use only price state and current first-entry status known at this close.
    for row in rows:
        row["controlEligible"] = bool(row["side"] is not None and row["B"] is not None and row["firstEntry"] is None)
        if row["side"] is not None:
            row["block"] = block_of(row["date"])

    def candidates(h):
        return [r for r in events if r["B"] is not None and r["outcomes"].get(str(h)) is not None]

    def eligible(h):
        return [r for r in rows if r["side"] is not None and r["B"] is not None and r["outcomes"].get(str(h)) is not None]

    def controls(h):
        return [r for r in rows if r["controlEligible"] and r["outcomes"].get(str(h)) is not None]

    def sign(r):
        return 1 if r["firstEntry"] == "upper" else -1

    def raw_metric(event_rows, all_rows, h):
        if not event_rows:
            return None
        counts = collections.Counter(r["firstEntry"] for r in event_rows)
        event_return = statistics.fmean(sign(r) * r["outcomes"][str(h)]["returnPct"] for r in event_rows)
        by_side = {side: [r["outcomes"][str(h)]["returnPct"] * (1 if side == "upper" else -1) for r in all_rows] for side in counts}
        baseline = sum(counts[side] * statistics.fmean(by_side[side]) for side in counts) / len(event_rows)
        direction = sum(sign(r) * r["outcomes"][str(h)]["returnPct"] > 0 for r in event_rows) / len(event_rows)
        return {"eventN": len(event_rows), "eventDirectionalMeanPct": event_return,
                "directionRate": direction, "allWeekN": len(all_rows),
                "allWeekDirectionalMeanPct": baseline, "rawDifferencePct": event_return - baseline,
                "eventSideN": dict(counts)}

    def matched_metric(event_rows, control_rows, h, min_controls=5):
        by_cell = collections.defaultdict(list)
        for r in control_rows:
            by_cell[r["B"]].append(r["outcomes"][str(h)]["returnPct"])
        qualifying = {cell: statistics.fmean(values) for cell, values in by_cell.items() if len(values) >= min_controls}
        common = [r for r in event_rows if r["B"] in qualifying]
        if not common:
            return {"commonEventN": 0, "excludedEventN": len(event_rows), "controlN": sum(len(v) for v in by_cell.values()), "eventDirectionalMeanPct": None, "standardizedControlDirectionalMeanPct": None, "incrementPct": None, "commonDirectionRate": None, "cellCounts": {k: len(v) for k,v in by_cell.items()}}
        event_mean = statistics.fmean(sign(r) * r["outcomes"][str(h)]["returnPct"] for r in common)
        control_mean = statistics.fmean(sign(r) * qualifying[r["B"]] for r in common)
        return {"commonEventN": len(common), "excludedEventN": len(event_rows) - len(common), "controlN": sum(len(v) for v in by_cell.values()),
                "eventDirectionalMeanPct": event_mean, "standardizedControlDirectionalMeanPct": control_mean,
                "incrementPct": event_mean - control_mean,
                "commonDirectionRate": sum(sign(r) * r["outcomes"][str(h)]["returnPct"] > 0 for r in common) / len(common),
                "cellCounts": {k: len(v) for k,v in by_cell.items()}, "commonEventDates": [r["date"] for r in common]}

    def bootstrap(h, event_rows, all_rows, control_rows, common_dates):
        blocks = sorted({r["block"] for r in all_rows})
        rng = random.Random(SEED)
        event_by_block = {b: [r for r in event_rows if r["block"] == b] for b in blocks}
        all_by_block = {b: [r for r in all_rows if r["block"] == b] for b in blocks}
        control_by_block = {b: [r for r in control_rows if r["block"] == b] for b in blocks}
        common = set(common_dates)
        values = {"event": [], "rawDifference": [], "matchedDifference": []}
        for _ in range(2000):
            drawn = [rng.choice(blocks) for _ in blocks]
            es = [r for b in drawn for r in event_by_block[b]]
            aa = [r for b in drawn for r in all_by_block[b]]
            cc = [r for b in drawn for r in control_by_block[b]]
            if es:
                raw = raw_metric(es, aa, h)
                values["event"].append(raw["eventDirectionalMeanPct"])
                values["rawDifference"].append(raw["rawDifferencePct"])
            ec = [r for r in es if r["date"] in common]
            match = matched_metric(ec, cc, h, min_controls=1)
            if match["incrementPct"] is not None and match["commonEventN"] == len(ec) and ec:
                values["matchedDifference"].append(match["incrementPct"])
        return {key: {"lo": quantile(v, .025), "hi": quantile(v, .975), "validReplicates": len(v), "emptyReplicates": 2000 - len(v)} for key, v in values.items()} | {"blocks": blocks, "resamples": 2000, "seed": SEED}

    results = {}
    for h in HORIZONS:
        es, aa, cc = candidates(h), eligible(h), controls(h)
        raw = raw_metric(es, aa, h)
        match = matched_metric(es, cc, h)
        uncertainty = bootstrap(h, es, aa, cc, match.get("commonEventDates", []))
        side_results = {}
        for side in ("upper", "lower"):
            side_events = [r for r in es if r["firstEntry"] == side]
            side_raw = raw_metric(side_events, aa, h)
            side_match = matched_metric(side_events, cc, h)
            signed_returns = [r["outcomes"][str(h)]["returnPct"] for r in side_events]
            side_results[side] = {"raw": side_raw, "matched": side_match,
                "actualReturnMeanPct": statistics.fmean(signed_returns) if signed_returns else None,
                "actualReturnMedianPct": statistics.median(signed_returns) if signed_returns else None,
                "riseN": sum(v > 0 for v in signed_returns), "fallN": sum(v < 0 for v in signed_returns),
                "zeroN": sum(v == 0 for v in signed_returns),
                "uncertainty": bootstrap(h, side_events, aa, cc, side_match.get("commonEventDates", []))}
        results[str(h)] = {"raw": raw, "matched": match, "uncertainty": uncertainty, "bySide": side_results}

    h = 63
    es, aa, cc = candidates(h), eligible(h), controls(h)
    periods = {}
    for label, predicate in (("through2016", lambda r: r["date"] <= "2016-12-31"), ("from2017", lambda r: r["date"] >= "2017-01-01")):
        e1, a1, c1 = [r for r in es if predicate(r)], [r for r in aa if predicate(r)], [r for r in cc if predicate(r)]
        periods[label] = {"raw": raw_metric(e1, a1, h), "matched": matched_metric(e1, c1, h)}
    cooldown = []
    last_by_side = {}
    for event in es:
        side = event["firstEntry"]
        if side not in last_by_side or event["priceIndex"] - last_by_side[side] > 63:
            cooldown.append(event)
            last_by_side[side] = event["priceIndex"]
    cooldown_result = {"raw": raw_metric(cooldown, aa, h), "matched": matched_metric(cooldown, cc, h), "dates": [r["date"] for r in cooldown]}
    lobo = {}
    for block in sorted({r["block"] for r in aa}):
        e1, c1 = [r for r in es if r["block"] != block], [r for r in cc if r["block"] != block]
        lobo[block] = matched_metric(e1, c1, h)
    event_details = []
    for r in events:
        detail = {k: r[k] for k in ("date", "sourceDate", "erp", "middle", "upper", "lower", "side", "B", "past63Pct", "sma200", "priceIndex", "outcomes", "block") if k in r}
        detail["outcomes"] = {}
        for horizon, result in r["outcomes"].items():
            if result is None:
                detail["outcomes"][horizon] = None
                continue
            entry_i = r["priceIndex"] + 1
            detail["outcomes"][horizon] = dict(result, entryDate=dates[entry_i],
                exitDate=dates[entry_i + int(horizon)],
                minDate=dates[entry_i + result["minDayFromEntry"]],
                maxDate=dates[entry_i + result["maxDayFromEntry"]])
        event_details.append(detail)
    examples = []
    for r in es:
        o = r["outcomes"]["63"]
        examples.append({"date": r["date"], "side": r["firstEntry"], "returnPct": o["returnPct"], "directionalReturnPct": sign(r) * o["returnPct"], "minMovePct": o["minMovePct"], "minDayFromEntry": o["minDayFromEntry"], "maxMovePct": o["maxMovePct"], "maxDayFromEntry": o["maxDayFromEntry"]})
    examples.sort(key=lambda r: r["directionalReturnPct"])
    worst = examples[:5]
    missed_rises = sorted((x for x in examples if x["side"] == "lower"), key=lambda x: x["maxMovePct"], reverse=True)[:5]
    continued_falls = sorted((x for x in examples if x["side"] == "upper"), key=lambda x: x["minMovePct"])[:5]
    serializable_rows = [{k: v for k, v in r.items() if k not in ("priceIndex",)} for r in rows if r["side"] is not None]
    write("eligible-weeks.json", serializable_rows)
    write("entry-events.json", event_details)
    write("results.json", {"horizons": results, "periods63": periods, "sameSideCooldown63": cooldown_result, "leaveOneBlockOut63": lobo, "counterexamples63": {"worstDirectional": worst, "largestMissedRisesAfterLower": missed_rises, "largestContinuedFallsAfterUpper": continued_falls}, "audit": {"sourceWeeklyN": len(spine), "erpValidN": len(reference), "bandEligibleN": len(serializable_rows), "entryN": len(events), "bandCrossCheckMaxAbs": max(checks), "bandCrossCheckComparisons": len(checks), "warmupDate": warmup_date.isoformat()}})
    print(json.dumps({"sigma":K,"eventN":len(events),"main":{s:results["63"]["bySide"][s]["actualReturnMeanPct"] for s in ("upper","lower")}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
