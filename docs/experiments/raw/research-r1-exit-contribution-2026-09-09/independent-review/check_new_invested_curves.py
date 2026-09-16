#!/usr/bin/env python3
"""Independently derive the four new invested-capital curves."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent / "execution"
SOURCE = HERE / "attempt-02-independent/complete-independent.json"
TARGET = EXEC / "invested-results.json"
TOL = 1e-12


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


source = json.loads(SOURCE.read_text())
targets = {x["account_id"]: x for x in json.loads(TARGET.read_text()) if x["method"] == "R1-structure-only"}
actions = json.loads((EXEC / "inputs/actions.json").read_text())
lock = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "locked_before_independent_invested_curve_check",
    "files": {
        str(TARGET.resolve()): sha(TARGET),
        str((EXEC / "inputs/actions.json").resolve()): sha(EXEC / "inputs/actions.json"),
        str(SOURCE.resolve()): sha(SOURCE),
    },
}
(HERE / "new-invested-curve-lock.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n")

checks = []
for account in source:
    if account["rule"] != "structure_only":
        continue
    symbol, fee = account["symbol"], account["fee"]
    aid = f"{symbol}-R1-structure-only-fee{int(round(fee * 10000)):02d}bp"
    positions = sorted(account["roundtrips"], key=lambda x: x["entry_date"])
    entries = {p["entry_date"]: p for p in positions}
    dividend_by_position = {p["candidate_id"]: {} for p in positions}
    for p in positions:
        for action in actions:
            if action["symbol"] != symbol or action["type"] != "cash_dividend":
                continue
            held_at_record_close = p["entry_date"] <= action["record_date"] and (p.get("exit_date") is None or action["record_date"] < p["exit_date"])
            if held_at_record_close:
                dividend_by_position[p["candidate_id"]][action["effective_date"]] = float(p["shares"]) * float(action["cash"])
    base = nav = peak = 1.0
    max_decline = 0.0
    active = None
    accrued = 0.0
    curve = []
    for row in account["daily"]:
        d = row["date"]
        if d in entries:
            active = entries[d]
            accrued = 0.0
        if active is not None:
            accrued += dividend_by_position[active["candidate_id"]].get(d, 0.0)
            capital = float(active["entry_notional"]) + float(active["buy_fee"])
            if active.get("exit_date") == d:
                value = float(active["shares"]) * float(active["exit_price"]) - float(active["sell_fee"]) + accrued
            else:
                value = float(row["shares"]) * float(row["mark"]) + accrued
            nav = base * value / capital
            if active.get("exit_date") == d:
                base = nav
                active = None
                accrued = 0.0
        else:
            nav = base
        peak = max(peak, nav)
        max_decline = max(max_decline, 1.0 - nav / peak)
        curve.append({"date": d, "unit": nav})
    span = (date.fromisoformat(account["daily"][-1]["date"]) - date.fromisoformat(account["daily"][0]["date"])).days
    annualized = nav ** (365.25 / span) - 1.0
    target = targets[aid]
    diffs = {
        "unit_final": abs(nav - float(target["unit_final"])),
        "calendar_annualized_unit_return": abs(annualized - float(target["calendar_annualized_unit_return"])),
        "maximum_unit_curve_decline": abs(max_decline - float(target["maximum_unit_curve_decline"])),
    }
    checks.append({"account_id": aid, "daily_points": len(curve), "span_days": span, "independent": {"unit_final": nav, "calendar_annualized_unit_return": annualized, "maximum_unit_curve_decline": max_decline}, "target": {k: target[k] for k in diffs}, "absolute_differences": diffs, "all_match": max(diffs.values()) <= TOL})

result = {
    "status": "passed" if len(checks) == 4 and all(x["all_match"] for x in checks) else "failed",
    "accounts": checks,
    "coverage": "independent daily normalized invested-capital curve, terminal unit, 4198-day calendar annualization, and maximum decline for four new accounts",
    "not_covered": ["old four invested curves, previously independently checked in the sealed technical batch", "executor invested-trades and invested-annual aggregation fields"]
}
(HERE / "new-invested-curve-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(result["status"])
