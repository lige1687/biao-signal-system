"""Frozen ETF policy comparison runner. Preflight never calculates effects."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import statistics
import time

from lei_signal.research.lowfreq_confirmation_execution import evaluate_asset


RAW = Path(__file__).resolve().parent
DESIGN = RAW / "design.json"
DESIGN_SHA = "5aba781fb5ede8cdb1e32975df9318d2f328ae7726e280dc7d6ee8c72d839c12"
CODE = Path(__file__).resolve().parents[4] / "src/lei_signal/research/lowfreq_confirmation_execution.py"
PLAN = RAW / "storage-plan.json"
POLICIES = ("direct", "hourly_eod", "fixed5")


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def inputs(design: dict, *, load_data: bool) -> tuple[list[dict], dict]:
    rows = []
    data = {}
    for asset in design["assets"]:
        path = Path(asset["path"])
        if digest(path) != asset["sha256"]:
            raise ValueError(f"input hash changed: {asset['code']}")
        obj = read_json(path)
        if obj["asset"]["code"] != asset["code"] or obj["asset"].get("group") != "etf":
            raise ValueError(f"asset identity changed: {asset['code']}")
        dates = [row["date"] for row in obj["daily"]]
        if dates != sorted(set(dates)):
            raise ValueError(f"daily dates not strictly unique: {asset['code']}")
        hour_keys = [(row["date"], row["time"]) for row in obj["hours"]]
        if len(hour_keys) != len(set(hour_keys)):
            raise ValueError(f"duplicate hourly timestamp: {asset['code']}")
        identities = [row["identity_key"] for row in obj["events"]]
        if len(identities) != len(set(identities)):
            raise ValueError(f"duplicate event identity: {asset['code']}")
        for row in obj["daily"]:
            if row.get("qualified") is True and any(isinstance(row.get(field), bool) or not isinstance(row.get(field), (int, float))
                                                     or not math.isfinite(row[field]) or row[field] <= 0
                                                     for field in ("adjusted_open", "adjusted_low", "adjusted_close")):
                raise ValueError(f"qualified daily price missing: {asset['code']}")
        known15 = sum(row["time"] == "15:00" and row.get("hour_qualified") is True and isinstance(row.get("bull"), bool)
                      for row in obj["hours"])
        rows.append({"asset": asset["code"], "daily": len(dates), "events": len(identities),
                     "known_qualified_15_states": known15, "first_daily": dates[0], "last_daily": dates[-1],
                     "input_sha256": asset["sha256"]})
        if load_data:
            data[asset["code"]] = obj
    if sum(row["events"] for row in rows) != 1589:
        raise ValueError("original 1589 events changed")
    old = design["old_events"]
    if digest(Path(old["path"])) != old["sha256"]:
        raise ValueError("old events hash changed")
    return rows, data


def verify_binding(path: Path, design: dict) -> dict:
    binding = read_json(path)
    files = binding.get("files", binding)
    if not isinstance(files, dict):
        raise ValueError("binding must map paths to SHA-256")
    required = [DESIGN, CODE, Path(__file__), *[Path(a["path"]) for a in design["assets"]],
                Path(design["old_events"]["path"])]
    for file in required:
        expected = files.get(str(file)) or files.get(str(file.relative_to(Path.cwd()))) if file.is_relative_to(Path.cwd()) else files.get(str(file))
        if not expected or digest(file) != expected:
            raise ValueError(f"missing or mismatched frozen binding: {file}")
    return binding


def _mean(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def _asset_metric(rows):
    paired = [row for row in rows if row.get("paired")]
    out = {"events": len(rows), "paired": len(paired),
           "common_reasons": dict(Counter(row.get("common_reason") or "eligible" for row in rows)),
           "unpaired_reasons": dict(Counter(row.get("common_reason") or "policy_unknown"
                                            for row in rows if not row.get("paired")))}
    for policy in POLICIES:
        out[policy] = {"score_pct": _mean(row["policies"][policy]["score_pct"] for row in paired),
                       "decline_pct": _mean(row["policies"][policy]["decline_pct"] for row in paired),
                       "participation_fraction": _mean(1.0 if row["policies"][policy]["status"] == "participated" else 0.0 for row in paired),
                       "scheduled": sum(bool(row["policies"][policy].get("scheduled_open_date")) for row in paired),
                       "opening_gap_cancellations": sum(row["policies"][policy].get("reason") == "opening_gap_below_anchor" for row in paired),
                       "next_open_minus_decision_close_pct": _mean(row["policies"][policy].get("next_open_minus_decision_close_pct") for row in paired),
                       "wait_trading_days_if_participated": _mean(row["policies"][policy].get("wait_trading_days") for row in paired if row["policies"][policy]["status"] == "participated")}
    out["hourly_minus_direct_pp"] = _mean(row.get("delta_pp") for row in paired)
    out["hourly_minus_fixed5_pp"] = _mean(row["policies"]["hourly_eod"]["score_pct"] - row["policies"]["fixed5"]["score_pct"] for row in paired)
    out["decomposition_pp"] = {key: _mean(row["decomposition_pp"][key] for row in paired)
                               for key in ("timing_both", "avoided_down_direct_only", "missed_up_direct_only",
                                           "hourly_only_positive", "hourly_only_negative")}
    return out


def _equal_asset(rows, assets):
    groups = {asset: _asset_metric([row for row in rows if row["asset"] == asset]) for asset in assets}
    missing = [asset for asset in assets if not groups[asset]["paired"]]
    valid = [groups[asset] for asset in assets if groups[asset]["paired"]]
    complete = not missing
    fields = ("score_pct", "decline_pct", "participation_fraction",
              "next_open_minus_decision_close_pct", "wait_trading_days_if_participated")
    metric_missing = {
        name: {field: [asset for asset in assets if groups[asset][name][field] is None]
               for field in fields}
        for name in POLICIES
    }
    return {"per_asset": groups, "assets_with_pairs": len(valid), "required_assets": list(assets),
            "missing_products": missing, "metric_missing_products": metric_missing, "equal_asset": {
        "hourly_minus_direct_pp": _mean(group["hourly_minus_direct_pp"] for group in valid) if complete else None,
        "hourly_minus_fixed5_pp": _mean(group["hourly_minus_fixed5_pp"] for group in valid) if complete else None,
        "decomposition_pp": {key: _mean(group["decomposition_pp"][key] for group in valid) if complete else None
                             for key in ("timing_both", "avoided_down_direct_only", "missed_up_direct_only",
                                         "hourly_only_positive", "hourly_only_negative")},
        "policies": {name: {field: _mean(group[name][field] for group in valid)
                            if complete and not metric_missing[name][field] else None
                            for field in fields}
                     for name in POLICIES}}}


def _all_groups(rows, design):
    main, sector = design["main_assets"], design["auxiliary_assets"]
    return {"main4broad": _equal_asset(rows, main), "aux4sector": _equal_asset(rows, sector),
            "all8": _equal_asset(rows, main + sector)}

def _maintenance(rows, assets):
    paired = [r for r in rows if r.get("paired") and r["asset"] in assets]
    per_asset = {}
    for asset in assets:
        sub = [r for r in paired if r["asset"] == asset]
        price_rows = [r for r in sub if r.get("old_paired") and r.get("old_first_hour_to_new_open_pct") is not None]
        per_asset[asset] = {
            "paired": len(sub),
            "intraday_lost_events": sum(bool(r.get("intraday_bull_lost_at_close_dates")) for r in sub),
            "intraday_lost_unique_dates": len({d for r in sub for d in r.get("intraday_bull_lost_at_close_dates", [])}),
            "old_new_price_pairs": len(price_rows),
            "old_first_hour_to_new_open_pct": _mean(r["old_first_hour_to_new_open_pct"] for r in price_rows),
        }
    missing = [a for a in assets if not per_asset[a]["old_new_price_pairs"]]
    return {"scope": "new paired events; price differences additionally old paired and both observation prices",
            "per_asset": per_asset, "price_difference_missing_products": missing,
            "equal_asset_old_first_hour_to_new_open_pct": None if missing else
                _mean(per_asset[a]["old_first_hour_to_new_open_pct"] for a in assets)}


def summarize(rows, design):
    main, sector = design["main_assets"], design["auxiliary_assets"]
    horizons = [design["horizons"]["primary"], design["horizons"]["secondary"]]
    result = {"schema": "lowfreq-confirmation-execution-summary/1", "event_count": len(rows),
              "event_identities": len(set((r["asset"], r["identity_key"]) for r in rows)),
              "horizons": {}, "already_seen_history": True,
              "future_daily_qualification_is_retrospective": True,
              "prices_are_observations_not_fills": True}
    for h in horizons:
        sub = [r for r in rows if r["horizon"] == h]
        result["horizons"][str(h)] = {**_all_groups(sub, design),
                                       "periods": {period[0]: _all_groups([r for r in sub if r["period"] == period[0]], design)
                                                   for period in design["periods"]},
                                       "initial15bull": {str(value): _all_groups([r for r in sub if r.get("initial15bull") is value], design)
                                                         for value in (True, False)},
                                       "true_wait": _all_groups([r for r in sub if r.get("paired") and r["policies"]["hourly_eod"].get("wait_trading_days", 0) > 0], design),
                                       "old_paired_intersection": _all_groups([r for r in sub if r.get("old_paired")], design),
                                       "old_rising_background": _all_groups([r for r in sub if r.get("old_rising_background") is True], design),
                                       "old_new_coverage": {"old_paired": sum(bool(r.get("old_paired")) for r in sub),
                                                            "new_paired": sum(bool(r.get("paired")) for r in sub),
                                                            "intersection": sum(bool(r.get("old_paired") and r.get("paired")) for r in sub)},
                                       "maintenance_effect": {
                                           "main4broad": _maintenance(sub, main),
                                           "aux4sector": _maintenance(sub, sector),
                                           "all8": _maintenance(sub, main + sector)}}
    return result


def bootstrap_60day(rows, design, data):
    """Descriptive shared calendar-block resampling; never a success probability."""
    main = design["main_assets"]
    primary = design["horizons"]["primary"]
    usable = [r for r in rows if r["horizon"] == primary and r.get("paired") and r["asset"] in main]
    dates = [row["date"] for row in data[main[0]]["daily"]]
    if usable:
        first, last = min(r["first_seen"] for r in usable), max(r["first_seen"] for r in usable)
        dates = [day for day in dates if first <= day <= last]
    blocks = [set(dates[i:i + 60]) for i in range(0, len(dates), 60)]
    if not blocks:
        return {"draws": 0, "complete_draws": 0, "omitted_incomplete_product_draws": 0, "range_pct_points": None}
    rng = random.Random(20261020)
    values_direct = []
    values_fixed5 = []
    omitted = 0
    for _ in range(2000):
        picked = [rng.randrange(len(blocks)) for _ in blocks]
        multiplicity = Counter(day for block_id in picked for day in blocks[block_id])
        per_asset_direct = []
        per_asset_fixed5 = []
        for asset in main:
            weighted = [(r, multiplicity[r["first_seen"]]) for r in usable if r["asset"] == asset and multiplicity[r["first_seen"]]]
            if not weighted:
                break
            denominator = sum(n for _, n in weighted)
            per_asset_direct.append(sum(row["delta_pp"] * n for row, n in weighted) / denominator)
            per_asset_fixed5.append(sum((row["policies"]["hourly_eod"]["score_pct"] - row["policies"]["fixed5"]["score_pct"]) * n for row, n in weighted) / denominator)
        if len(per_asset_direct) != len(main):
            omitted += 1
        else:
            values_direct.append(statistics.mean(per_asset_direct))
            values_fixed5.append(statistics.mean(per_asset_fixed5))
    values_direct.sort()
    values_fixed5.sort()
    bounds = lambda values: [values[int((len(values) - 1) * q)] for q in (0.025, 0.975)] if values else None
    return {"method": "shared_60_trading_date_blocks", "seed": 20261020,
            "trading_dates": len(dates), "blocks": len(blocks), "draws": 2000,
            "complete_draws": len(values_direct), "omitted_incomplete_product_draws": omitted,
            "hourly_minus_direct_range_pp": bounds(values_direct),
            "hourly_minus_fixed5_range_pp": bounds(values_fixed5)}


def intraday_lost_before_decision(row, asset_data):
    """Count earlier qualified bullish hours absent at the 15:00 check."""
    daily = asset_data["daily"]
    start = row["first_seen"]
    candidate = row["policies"]["hourly_eod"]
    last = candidate.get("decision_date")
    if last is None and row.get("horizon_date"):
        endpoint_index = next((i for i, day in enumerate(daily) if day["date"] == row["horizon_date"]), None)
        if endpoint_index is not None and endpoint_index > 0:
            last = daily[endpoint_index - 1]["date"]
    if not last:
        return []
    hour_by_day = defaultdict(list)
    for hour in asset_data["hours"]:
        if start <= hour["date"] <= last:
            hour_by_day[hour["date"]].append(hour)
    lost = []
    for day in daily:
        stamp = day["date"]
        if not start <= stamp <= last:
            continue
        hours = hour_by_day.get(stamp, [])
        closing = next((h for h in hours if h["time"] == "15:00"), None)
        if closing and closing.get("hour_qualified") is True and closing.get("bull") is False:
            if any(h["time"] < "15:00" and h.get("hour_qualified") is True and h.get("bull") is True for h in hours):
                lost.append(stamp)
    return lost


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--binding", type=Path)
    parser.add_argument("--budget-state", type=Path)
    args = parser.parse_args()
    if digest(DESIGN) != DESIGN_SHA:
        raise ValueError("frozen design SHA changed")
    design = read_json(DESIGN)
    plan = read_json(PLAN)
    if args.out is not None and args.out != Path(plan["output"]):
        raise ValueError("--out differs from frozen storage plan")
    started = time.monotonic()
    qualification, data = inputs(design, load_data=args.run)
    if args.preflight:
        print(json.dumps({"status": "preflight_only", "events": sum(r["events"] for r in qualification),
                          "qualification": qualification, "effects_computed": False}, ensure_ascii=False))
        return
    if not args.out or not args.binding or not args.budget_state:
        parser.error("--run requires --out, --binding, and --budget-state")
    if not args.out.is_dir() or any(args.out.iterdir()):
        raise ValueError("planned result directory must exist and be empty (create-only)")
    binding = verify_binding(args.binding, design)
    budget = read_json(args.budget_state)
    consumed = budget.get("cumulative_seconds", budget.get("market_seconds_cumulative"))
    if not isinstance(consumed, (int, float)) or consumed < design["budget"]["inherited_market_seconds"]:
        raise ValueError("missing or stale cumulative budget")
    if consumed >= design["budget"]["cap_seconds"]:
        raise ValueError("market budget exhausted")
    if budget.get("core_runs", 0) >= design["budget"]["new_core_max"]:
        raise ValueError("one new core run already consumed")
    old = read_json(Path(design["old_events"]["path"]))
    old_lookup = {(r["asset"], r["identity_key"], r["horizon"]): r for r in old if r.get("group") == "etf"}
    rows = []
    for asset in design["assets"]:
        rows.extend(evaluate_asset(data[asset["code"]], [design["horizons"]["primary"], design["horizons"]["secondary"]], design["periods"]))
    for row in rows:
        old_row = old_lookup.get((row["asset"], row["identity_key"], row["horizon"]))
        row["old_paired"] = bool(old_row and old_row.get("qualification") == "paired")
        row["old_rising_background"] = old_row.get("rising_background") if old_row else None
        row["old_hourly_observation"] = ({key: old_row.get(key) for key in
                                           ("candidate_status", "candidate_entry_date", "candidate_entry_time",
                                            "candidate_entry_close", "candidate_return_pct", "confirmation_wait_hours")}
                                          if old_row else None)
        new_open = row["policies"]["hourly_eod"].get("entry_open")
        old_price = old_row.get("candidate_entry_close") if old_row else None
        row["old_first_hour_to_new_open_pct"] = (100 * (new_open / old_price - 1)
                                                   if isinstance(new_open, (int, float)) and isinstance(old_price, (int, float))
                                                   and math.isfinite(new_open) and math.isfinite(old_price) and old_price > 0 else None)
        row["intraday_bull_lost_at_close_dates"] = intraday_lost_before_decision(row, data[row["asset"]])
        if row.get("paired"):
            if abs(sum(row["decomposition_pp"].values()) - row["delta_pp"]) > 1e-9:
                raise AssertionError("decomposition does not reconcile")
    expected = sum(row["events"] for row in qualification) * 2
    if len(rows) != expected:
        raise AssertionError("original events not retained at both horizons")
    summary = summarize(rows, design)
    summary["descriptive_resampling"] = bootstrap_60day(rows, design, data)
    elapsed = time.monotonic() - started
    if consumed + elapsed > design["budget"]["cap_seconds"]:
        raise ValueError("market budget cap reached before writing results")
    receipt = {"schema": "lowfreq-confirmation-run-receipt/1", "design_sha256": DESIGN_SHA,
               "code_sha256": digest(CODE), "runner_sha256": digest(Path(__file__)),
               "input_binding": str(args.binding), "input_binding_sha256": digest(args.binding),
               "prior_cumulative_seconds": consumed, "elapsed_seconds": elapsed,
               "new_cumulative_seconds": consumed + elapsed, "core_runs_used": 1,
               "events": len(rows), "effects_computed": True}
    for name, obj in (("event-rows.json", rows), ("summary.json", summary), ("run-receipt.json", receipt)):
        with (args.out / name).open("x", encoding="utf-8") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({"status": "completed", "output": str(args.out), "events": len(rows),
                      "cumulative_seconds": consumed + elapsed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
