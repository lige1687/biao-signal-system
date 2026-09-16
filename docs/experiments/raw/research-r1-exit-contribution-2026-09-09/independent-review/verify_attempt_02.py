#!/usr/bin/env python3
"""Compare clean-room attempt 02 with locked old and executor accounts."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TECH = ROOT.parent / "research-broad-etf-technical-2026-09-08" / "execution/account-results"
EXEC = ROOT / "execution/attempt-01"
IND = HERE / "attempt-02-independent"
TOL = 1e-7


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def js(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def csv_rows(p: Path):
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


lock_checks = []
revision = js(HERE / "attempt-02-code-lock.json")
checker_path = str((HERE / "independent_check.py").resolve())
for lock_name in ("review-lock.json", "executor-attempt-01-lock.json"):
    lock = js(HERE / lock_name)
    for name, expected in lock["files"].items():
        p = Path(name)
        actual = sha(p)
        revised_match = lock_name == "review-lock.json" and name == checker_path and actual == revision["independent_check_sha256"]
        lock_checks.append({"lock": lock_name, "path": name, "match": actual == expected or revised_match, "original_match": actual == expected, "revision_match": revised_match})

complete = js(IND / "complete-independent.json")
complete_checks = []
for own in complete:
    symbol, fee, rule = own["symbol"], own["fee"], own["rule"]
    tag = f"{int(round(fee * 10000)):02d}"
    target = TECH / f"{symbol}-R1-fee{tag}bp" if rule == "original" else EXEC / f"{symbol}-R1-structure-only-fee{tag}bp"
    target_daily, target_trades, target_rt = csv_rows(target / "daily.csv"), csv_rows(target / "trades.csv"), js(target / "roundtrips.json")
    daily_max = {k: max(abs(float(a[k]) - float(b[f'units_{symbol}' if k == 'shares' else k])) for a, b in zip(own["daily"], target_daily)) for k in ("equity", "cash", "shares", "receivable", "fees")}
    own_seq = [(x["date"], x["side"], float(x["shares"]), float(x["price"]), x["reason"]) for x in own["trades"]]
    target_seq = [(x["date"], x["side"], float(x["shares"]), float(x["price"]), x["reason"]) for x in target_trades]
    own_dates = [(x["entry_date"], x.get("exit_date")) for x in own["roundtrips"]]
    target_dates = [(x["entry_date"], x.get("exit_date")) for x in target_rt]
    complete_checks.append({"symbol": symbol, "fee": fee, "rule": rule, "daily_rows": len(own["daily"]), "target_daily_rows": len(target_daily), "daily_max_abs_diff": daily_max, "trade_sequence_exact": own_seq == target_seq, "roundtrip_dates_exact": own_dates == target_dates, "independent_trade_count": len(own_seq), "target_trade_count": len(target_seq)})

fixed = js(IND / "fixed-entries-independent.json")
fixed_index = {(x["symbol"], x["fee"], x["candidate_id"], x["rule"]): x for x in fixed}
fixed_mismatches = []
fixed_groups = []
for symbol in ("sh510300", "sz159915"):
    for fee in (0.001, 0.002):
        tag = f"{int(round(fee * 10000)):02d}"
        folder = TECH / f"{symbol}-R1-fee{tag}bp"
        old = js(folder / "roundtrips.json")
        sells = {x["position_id"]: x for x in csv_rows(folder / "trades.csv") if x["side"] == "sell"}
        changed = open_new = 0
        for row in old:
            original = fixed_index[(symbol, fee, row["candidate_id"], "original")]
            new = fixed_index[(symbol, fee, row["candidate_id"], "structure_only")]
            expected_reason = sells[row["position_id"]]["reason"] if row.get("closed") else None
            checks = {
                "exit_date": original.get("exit_date") == row.get("exit_date"),
                "exit_price": original.get("exit_price") == row.get("exit_price"),
                "exit_reason": original.get("exit_reason") == expected_reason,
                "net_pnl": abs(float(original["net_pnl"]) - float(row["net_pnl"])) <= TOL,
                "dividends": abs(float(original["dividends"]) - float(row["dividend_accrued"])) <= TOL,
            }
            if not all(checks.values()):
                fixed_mismatches.append({"symbol": symbol, "fee": fee, "candidate_id": row["candidate_id"], "checks": checks})
            if (original.get("exit_date"), original["net_pnl"]) != (new.get("exit_date"), new["net_pnl"]):
                changed += 1
            if new.get("exit_date") is None:
                open_new += 1
        fixed_groups.append({"symbol": symbol, "fee": fee, "frozen_entries": len(old), "changed_under_structure_only": changed, "open_at_end_under_structure_only": open_new})

result = {
    "status": "passed_for_available_targets" if all(x["match"] for x in lock_checks) and all(x["trade_sequence_exact"] and x["roundtrip_dates_exact"] and x["daily_rows"] == x["target_daily_rows"] and max(x["daily_max_abs_diff"].values()) <= TOL for x in complete_checks) and not fixed_mismatches else "failed",
    "scope": {
        "rule_review": "synthetic strict-inequality/priority tests plus independent event-order implementation",
        "numeric_coverage": "8 complete paths (4 old regression + 4 new executor), 330 frozen entries x 2 exit rules",
        "executor_fixed_entry_target_available": False
    },
    "locked_file_checks": {"count": len(lock_checks), "all_match": all(x["match"] for x in lock_checks), "mismatches": [x for x in lock_checks if not x["match"]]},
    "complete_account_checks": complete_checks,
    "fixed_original_checks": {"entries": 330, "comparisons": 330, "mismatch_count": len(fixed_mismatches), "mismatches": fixed_mismatches[:20]},
    "fixed_structure_only_inventory": fixed_groups,
    "limitations": ["Executor fixed-entry phase13 target has not arrived, so structure-only fixed paths are independently generated but not yet cross-compared.", "Performance interpretation and invested-capital metrics are outside this checkpoint."]
}
(HERE / "attempt-02-review-results-v2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(result["status"])
