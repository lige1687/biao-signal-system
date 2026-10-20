"""Independent saved-input arithmetic and decision-time review; no engine imports."""
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def review(output):
    started = time.monotonic()
    here = Path(__file__).resolve().parent
    design = json.loads((here / "design.json").read_text())
    inputs = {}
    for item in design["assets"]:
        assert checksum(item["path"]) == item["sha256"]
        inputs[item["code"]] = json.loads(Path(item["path"]).read_text())
    rows = json.loads((Path(output) / "event-rows.json").read_text())
    if isinstance(rows, dict):
        rows = rows["event_rows"]
    assert len(rows) == 2 * sum(len(d["events"]) for d in inputs.values())
    assert len({(r["asset"], r["identity_key"], r["horizon"]) for r in rows}) == len(rows)
    differences = []
    evaluated = Counter()
    coverage = Counter()
    means = {}
    for row in rows:
        data = inputs[row["asset"]]
        events = {e["identity_key"]: e for e in data["events"]}
        event = events[row["identity_key"]]
        assert row["first_seen"] == event["first_seen"]
        daily = data["daily"]
        positions = {d["date"]: i for i, d in enumerate(daily)}
        hourly = {(h["date"], h["time"]): h for h in data["hours"]}
        start = positions.get(event["first_seen"])
        end = start + row["horizon"] if start is not None else None
        anchor = event["anchor_adjusted_low"]
        expected_eligible = start is not None and end < len(daily)
        if expected_eligible:
            expected_eligible = any(first <= daily[start]["date"] <= daily[end]["date"] <= last
                                    for _, first, last in design["periods"])
        if expected_eligible:
            expected_eligible = all(d["qualified"] and all(
                isinstance(d.get(k), (int, float)) and not isinstance(d.get(k), bool)
                and math.isfinite(d[k]) and d[k] > 0
                for k in ("adjusted_open", "adjusted_low", "adjusted_close"))
                for d in daily[start:end + 1])
        if expected_eligible:
            initial = hourly.get((daily[start]["date"], "15:00"), {})
            expected_eligible = initial.get("hour_qualified") is True and type(initial.get("bull")) is bool
        if expected_eligible:
            for j in range(start, end):
                if j > start and daily[j]["adjusted_low"] < anchor:
                    break
                h = hourly.get((daily[j]["date"], "15:00"), {})
                if h.get("hour_qualified") is not True or type(h.get("bull")) is not bool:
                    expected_eligible = False
                    break
                if h["bull"]:
                    break
        assert row["paired"] == expected_eligible, (row["identity_key"], row["horizon"], "coverage")
        coverage[f'{row["horizon"]}/{"paired" if expected_eligible else "unknown"}'] += 1
        if not row["paired"]:
            for policy in row["policies"].values():
                if policy["status"] == "unknown":
                    assert policy["score_pct"] is None
            continue
        assert daily[end]["date"] == row["horizon_date"]
        assert all(d["qualified"] for d in daily[start:end + 1])
        assert hourly[(daily[start]["date"], "15:00")]["hour_qualified"]
        assert type(hourly[(daily[start]["date"], "15:00")]["bull"]) is bool
        same_period = [name for name, first, last in design["periods"]
                       if first <= daily[start]["date"] <= daily[end]["date"] <= last]
        assert same_period == [row["period"]]
        choices = {"direct": start, "fixed5": start + 5, "hourly_eod": None}
        if min(d["adjusted_low"] for d in daily[start + 1:start + 6]) < anchor:
            choices["fixed5"] = None
        for j in range(start, end):
            if j > start and daily[j]["adjusted_low"] < anchor:
                break
            h = hourly[(daily[j]["date"], "15:00")]
            assert h["hour_qualified"] and type(h["bull"]) is bool
            if h["bull"]:
                choices["hourly_eod"] = j
                break
        scores = {}
        for policy_name, decision in choices.items():
            actual = row["policies"][policy_name]
            entry = None if decision is None else decision + 1
            if entry is not None and daily[entry]["adjusted_open"] < anchor:
                entry = None
            if entry is None:
                assert actual["status"] == "nonparticipation", (row, policy_name)
                score = decline = 0.0
            else:
                assert actual["status"] == "participated", (row, policy_name)
                assert actual["entry_date"] == daily[entry]["date"]
                assert actual["decision_date"] == daily[decision]["date"]
                assert actual["entry_date"] > actual["decision_date"]
                assert entry <= end
                price = daily[entry]["adjusted_open"]
                assert math.isclose(price, actual["entry_open"], abs_tol=1e-12)
                score = 100 * (daily[end]["adjusted_close"] / price - 1)
                minimum = min([price] + [d["adjusted_close"] for d in daily[entry:end + 1]])
                decline = max(0.0, 100 * (1 - minimum / price))
            assert math.isclose(score, actual["score_pct"], abs_tol=1e-10)
            assert math.isclose(decline, actual["decline_pct"], abs_tol=1e-10)
            differences.extend([abs(score - actual["score_pct"]),
                                abs(decline - actual["decline_pct"])])
            scores[policy_name] = score
            evaluated[policy_name] += 1
        delta = scores["hourly_eod"] - scores["direct"]
        assert math.isclose(delta, row["delta_pp"], abs_tol=1e-10)
        assert math.isclose(delta, sum(row["decomposition_pp"].values()), abs_tol=1e-10)
        key = f'{row["asset"]}/{row["horizon"]}'
        means.setdefault(key, []).append(scores)
    asset_means = {}
    for key, items in means.items():
        asset_means[key] = {
            "events": len(items),
            **{p: sum(x[p] for x in items) / len(items)
               for p in ("direct", "hourly_eod", "fixed5")},
        }
    groups = {}
    for horizon in (20, 30):
        for name, codes in (("main4", design["main_assets"]),
                            ("sector4", design["auxiliary_assets"]),
                            ("all8", design["main_assets"] + design["auxiliary_assets"])):
            subset = [asset_means.get(f"{c}/{horizon}") for c in codes]
            groups[f"{name}/{horizon}"] = None if any(x is None for x in subset) else {
                p: sum(x[p] for x in subset) / len(subset)
                for p in ("direct", "hourly_eod", "fixed5")
            }
    return {
        "accepted": True,
        "method": "independent raw input decision scan and arithmetic; no candidate module import",
        "all_event_horizon_rows": len(rows),
        "independently_checked_coverage": dict(coverage),
        "paired_policies_checked": dict(evaluated),
        "maximum_absolute_numeric_difference": max(differences, default=0),
        "independent_asset_means": asset_means,
        "independent_group_means": groups,
        "seconds": time.monotonic() - started,
        "limitations": "Does not requalify vendor source or validate real fills/full original strategy.",
    }


if __name__ == "__main__":
    result = review(sys.argv[1])
    destination = Path(__file__).with_name("independent-result.json")
    with destination.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(result, ensure_ascii=False))
