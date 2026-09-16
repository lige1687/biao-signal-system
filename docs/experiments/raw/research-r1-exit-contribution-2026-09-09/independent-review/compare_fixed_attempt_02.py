#!/usr/bin/env python3
"""Compare all 660 executor fixed paths against clean-room attempt 02."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "fixed-entries/attempt-02/path-comparison.csv"
INDEPENDENT = HERE / "attempt-02-independent/fixed-entries-independent.json"
TOL = 1e-7


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


lock = json.loads((HERE / "fixed-attempt-02-lock.json").read_text())
lock_mismatches = []
for name, expected in lock["files"].items():
    actual = sha(Path(name))
    if actual != expected:
        lock_mismatches.append({"path": name, "expected": expected, "actual": actual})

ind = json.loads(INDEPENDENT.read_text())
index = {(x["symbol"], str(x["fee"]), x["candidate_id"], x["rule"]): x for x in ind}
with TARGET.open(newline="", encoding="utf-8") as f:
    target = list(csv.DictReader(f))

mismatches = []
max_abs = {k: 0.0 for k in ("exit_price", "sell_fee", "dividend_accrued", "terminal_market_value", "net_pnl", "net_return")}
method_map = {"road_or_structure": "original", "structure_only": "structure_only"}
for row in target:
    key = (row["symbol"], str(float(row["fee_per_side"])), row["candidate_id"], method_map[row["method"]])
    own = index.get(key)
    if own is None:
        mismatches.append({"path_id": row["path_id"], "reason": "missing independent path"})
        continue
    expected_terminal_market = float(own.get("terminal_mark", 0.0)) * float(own["shares"]) if own.get("exit_date") is None else 0.0
    expected_net_return = float(own["net_pnl"]) / (float(row["entry_notional"]) + float(row["buy_fee"]))
    checks = {
        "entry_date": own["entry_date"] == row["entry_date"],
        "entry_price": abs(float(own["entry_price"]) - float(row["entry_price"])) <= TOL,
        "initial_shares": abs((float(row["entry_notional"]) / float(row["entry_price"])) - float(row["initial_shares"])) <= TOL,
        "initial_stop": abs(float(own["initial_stop"]) - float(row["initial_stop"])) <= TOL,
        "exit_signal_date": (own.get("exit_signal_date") or "") == row["exit_signal_date"],
        "exit_reason": (own.get("exit_reason") or "") == row["exit_reason"],
        "exit_date": (own.get("exit_date") or "") == row["exit_date"],
    }
    numeric = {
        "exit_price": (float(own["exit_price"]) if own.get("exit_price") is not None else 0.0, float(row["exit_price"] or 0.0)),
        "sell_fee": (float(own["sell_fee"]), float(row["sell_fee"] or 0.0)),
        "dividend_accrued": (float(own["dividends"]), float(row["dividend_accrued"])),
        "terminal_market_value": (expected_terminal_market, float(row["terminal_market_value"])),
        "net_pnl": (float(own["net_pnl"]), float(row["net_pnl"])),
        "net_return": (expected_net_return, float(row["net_return"])),
    }
    for name, (a, b) in numeric.items():
        diff = abs(a - b)
        max_abs[name] = max(max_abs[name], diff)
        checks[name] = diff <= TOL
    if not all(checks.values()):
        mismatches.append({"path_id": row["path_id"], "checks": checks, "numeric": numeric})

result = {
    "status": "passed" if len(target) == 660 and not lock_mismatches and not mismatches else "failed",
    "target_rows": len(target),
    "independent_rows": len(ind),
    "locked_files": len(lock["files"]),
    "lock_mismatches": lock_mismatches,
    "path_mismatch_count": len(mismatches),
    "mismatches": mismatches[:20],
    "max_abs_differences": max_abs,
    "covered_fields": ["entry_date", "entry_price", "initial_shares", "initial_stop", "exit_signal_date", "exit_reason", "exit_date", "exit_price", "sell_fee", "dividend_accrued", "terminal_market_value", "net_pnl", "net_return"],
    "not_independently_rebuilt_here": ["path-daily holding drawdown", "dividend payment-date split between cash and receivable; complete-account daily checks cover that ordering", "summary aggregation fields"]
}
(HERE / "fixed-attempt-02-comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(result["status"])
