"""Read only the exact A-approved files selected by B's explicit binding.

This adapter checks consumption/identity. A owns source qualification; there is
no source discovery, download, original-account replay or archived-code import.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from execution_guard import verify_file, require, PATH_IDS
from monthly_account import by_date, flag, number, dates

START, END = "2026-01-01", "2026-06-30"


def csv_rows(path):
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def load_bound_dataset(binding):
    require(binding.get("schema") == "monthly-risk-consumption-binding/1", "unknown input binding")
    require(binding.get("A_task_id") == "leisignal-risk-input-20261009", "wrong A input owner")
    require(binding.get("status") == "bound_to_A_inputs_ready", "A inputs not ready")
    require(binding.get("A_result_commit") and binding.get("A_manifest"), "A exact commit/manifest missing")
    verify_file(binding["A_manifest"])
    # Full closure supplied by A, not just convenient directly consumed files.
    for item in binding["source_closure"]:
        verify_file(item)
    files = binding["files"]
    account_keys = PATH_IDS+["B0-base", "B0-stress"]
    keys = set(account_keys+['quotes', 'calendar', 'execution_reference', 'mapped_actions']+
               [key+"-ledger" for key in account_keys])
    require(set(files) == keys, "exact consumed input roles missing or added")
    for item in files.values():
        verify_file(item)
    # Require every consumed file AND the closure to be an exact A manifest
    # artifact. C also independently checks the role mapping and old correction.
    A = json.loads(Path(binding["A_manifest"]["path"]).read_text())
    require(A.get("status") == "inputs_ready_with_retrospective_limits"
            and A.get("blocking_missing_inputs") == [], "A qualification not ready")
    expected_closure = [{"id": a["id"], "path": a["read_path"], "sha256": a["sha256"], "bytes": a["bytes"]}
                        for a in A["artifacts"]]
    require(binding["source_closure"] == expected_closure, "A entire source closure changed")
    A_by_id = {a["id"]: a for a in expected_closure}
    require(len(A_by_id) == len(expected_closure), "duplicate A artifact IDs")
    for item in files.values():
        require(item == A_by_id.get(item["id"]), "consumed source is not exact A artifact")
    accounts = {key: csv_rows(files[key]["path"]) for key in PATH_IDS+["B0-base", "B0-stress"]}
    ledgers = {key: json.loads(Path(files[key+"-ledger"]["path"]).read_text()) for key in account_keys}
    maps = {key: by_date(rows) for key, rows in accounts.items()}
    calendar = json.loads(Path(files["calendar"]["path"]).read_text())
    require(isinstance(calendar.get("days"), dict), "official calendar schema mismatch")
    trading = {day for day, value in calendar["days"].items() if flag(value["is_trading_day"])}
    natural = dates(START, END)
    require(all(day in calendar["days"] for day in natural), "official natural calendar incomplete")
    period_trading = {day for day in trading if START <= day <= END}
    require(period_trading, "no period trading calendar")
    for key in accounts:
        require(all(day in maps[key] for day in ["2025-12-31"]+natural), f"saved account coverage incomplete: {key}")
        actual = {day for day in natural if flag(maps[key][day]["is_trading_day"])}
        require(actual == period_trading, f"saved account official calendar mismatch: {key}")
        for day in natural:
            row = maps[key][day]
            wealth = number(row["cash"])+number(row["receivable"])+number(row["units"])*number(row["mark"])
            require(abs(wealth-number(row["wealth"])) <= number("0.01"), f"saved complete wealth mismatch: {key} {day}")
            # Normalize only this display field if old CSV omitted it; no signal recomputation.
            if row.get("invested_pct") in (None, ""):
                row["invested_pct"] = str(100*number(row["units"])*number(row["mark"])/number(row["wealth"]))
    initial = binding["initial_states"]
    require(set(initial) == set(PATH_IDS), "initial-state role mismatch")
    for path_id in PATH_IDS:
        saved = maps[path_id]["2025-12-31"]
        require(initial[path_id]["date"] == "2025-12-31", "wrong initial date")
        for key in ("cash", "receivable", "units", "wealth"):
            require(number(saved[key]) == number(initial[path_id][key]), f"A year-end state mismatch: {path_id} {key}")
        require(number(saved["units"]) == 0 and number(saved["receivable"]) == 0
                and number(saved["cash"]) == number(saved["wealth"]), "proposal requires actual cash-only start")
    quotes = [row for row in csv_rows(files["quotes"]["path"]) if START <= row["date"] <= END]
    reference = json.loads(Path(files["execution_reference"]["path"]).read_text())
    require(isinstance(reference, list), "execution reference schema mismatch")
    reference = [row for row in reference if START <= row["date"] <= END]
    require(set(by_date(quotes)) == set(by_date(reference)) == period_trading, "quote/reference/calendar mismatch")
    restrictions = {row["date"]: row["restriction"] for row in reference if row["restriction"] is not None}
    require(all(v in ("halt", "blocked") for v in restrictions.values()), "unhandled original restriction")
    all_actions = json.loads(Path(files["mapped_actions"]["path"]).read_text())
    actions = []
    for event in all_actions:
        if event["type"] == "dividend":
            overlaps = event["record_date"] <= END and event["pay_date"] >= START
            if overlaps:
                require(START <= event["record_date"] < event["ex_date"] <= event["pay_date"] <= END,
                        "cross-boundary dividend requires exact additional source handling")
                actions.append(event)
        elif START <= event.get("date", "") <= END:
            raise ValueError("in-period non-dividend action requires exact source adapter")
    return {"accounts": accounts, "maps": maps, "ledgers": ledgers, "initial_states": initial,
            "trading_days": trading, "period_trading": period_trading,
            "quotes": quotes, "restrictions": restrictions, "actions": actions,
            "identity_checked": True, "A_qualification_not_replaced": True}


def saved_period_fee(before, after):
    def value(row):
        bridge = row["reconciliation"]
        return number((json.loads(bridge) if isinstance(bridge, str) else bridge)["fees_cny"])
    change = value(after)-value(before)
    require(change >= 0, "negative saved fee increment")
    return change
