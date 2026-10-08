"""Decode the two saved Sina responses locally; no network or market experiment."""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import akshare
from akshare.stock.stock_zh_a_sina import hk_js_decode, py_mini_racer

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]
DATES = ("2022-01-04", "2022-01-05", "2022-01-06")


def digest(p: Path) -> dict:
    return {"path": str(p), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main() -> None:
    ledger = json.loads((OUT / "request-ledger.json").read_text())
    assert [(a["kind"], a["result"], a["http_status"]) for a in ledger["attempts"]] == [
        ("qfq", "response_saved", 200), ("history", "response_saved", 200)]
    qfq_path = OUT / "sina-qfq-sh600705-response.bin"
    history_path = OUT / "sina-history-sh600705-response.bin"
    qfq_bytes, history_bytes = qfq_path.read_bytes(), history_path.read_bytes()
    assert len(qfq_bytes) == 1587 and len(history_bytes) == 66202
    assert hashlib.sha256(qfq_bytes).hexdigest() == ledger["attempts"][0]["sha256"]
    assert hashlib.sha256(history_bytes).hexdigest() == ledger["attempts"][1]["sha256"]
    qfq_match = re.fullmatch(rb'var sh600705qfq=(\{"total":\d+,"data":\[.*?\]\})\s*/\*.*?\*/\s*', qfq_bytes, flags=re.DOTALL)
    assert qfq_match, "unexpected JS wrapper; do not execute public JS"
    factor_obj = json.loads(qfq_match.group(1))
    factors = factor_obj["data"]
    assert len(factors) == factor_obj["total"] == 28
    assert all(set(x) == {"d", "f"} for x in factors)
    hist_match = re.match(rb'^var KLC_K2_sh600705="([A-Za-z0-9+/=]+)";', history_bytes)
    assert hist_match, "unexpected encoded-price wrapper"
    decoder = py_mini_racer.MiniRacer()
    decoder.eval(hk_js_decode)  # installed library decoder, not public response code
    decoded = decoder.call("d", hist_match.group(1).decode("ascii"))
    assert isinstance(decoded, list) and len(decoded) == 5564
    by_day = {r["date"][:10]: r for r in decoded}
    assert len(by_day) == len(decoded)
    saved_path = ROOT / "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/normalized/daily_raw/daily-1-sh-600705.json"
    saved = {r["date"]: r for r in json.loads(saved_path.read_text())["records"]}
    use_days = ("2021-12-31",) + DATES + ("2022-01-07",)
    compared = []
    for day in use_days:
        original = by_day[day]
        factor = max((f for f in factors if f["d"] <= day), key=lambda f: f["d"])
        raw = Decimal(str(original["close"]))
        prior = Decimal(saved[day]["close"])
        assert raw == prior, f"Sina/BaoStock raw close disagrees on {day}"
        computed = round(float(raw) / float(factor["f"]), 2)  # installed AKShare 1.18.49 policy
        compared.append({"date": day, "sina_raw_close": str(raw), "baostock_raw_close": saved[day]["close"],
                         "raw_sources_match": True, "sina_current_factor_date": factor["d"],
                         "sina_current_qfq_factor": factor["f"],
                         "illustrative_current_sina_qfq_close": f"{computed:.2f}",
                         "old_main_original_qfq_close": None})
    for before, after in zip(compared, compared[1:]):
        assert before["sina_current_factor_date"] == after["sina_current_factor_date"]
        assert saved[after["date"]]["preclose"] == saved[before["date"]]["close"]
    installed_source = Path("/opt/homebrew/lib/python3.11/site-packages/akshare/stock/stock_zh_a_sina.py")
    result = {
        "schema": "stock-gap-pilot-current-provider-comparison/1.0",
        "selected_dates": list(DATES), "same_source_compared_dates": compared,
        "all_five_sina_vs_saved_baostock_raw_closes_match": True,
        "all_four_saved_preclose_neighbor_links_match": True,
        "current_sina_factor_constant_across_window": True,
        "factor_event_bracketing_window": {"last_at_or_before": "2021-08-05", "next_after": "2022-07-07"},
        "current_sina_total_factor_rows": len(factors),
        "adjustment_method": "installed AKShare 1.18.49 joins dated Sina qfq factors, forward-fills, computes raw close / factor and rounds to 2 decimals",
        "installed_akshare_version": akshare.__version__,
        "installed_source": digest(installed_source),
        "response_hashes": [digest(qfq_path), digest(history_path)],
        "saved_baostock_source": digest(saved_path),
        "old_original_600705_qfq_column_present": False,
        "old_original_sina_factor_snapshot_and_anchor_verified": False,
        "historically_available_at_2022": None,
        "official_corporate_action_or_adjustment_basis_verified": False,
        "actual_price_repair_performed": False,
        "new_requests": 2,
        "new_received_bytes": ledger["cumulative_response_bytes"],
    }
    target = OUT / "comparison.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"selected_current_sina_qfq_examples": [(r["date"], r["illustrative_current_sina_qfq_close"]) for r in compared if r["date"] in DATES],
                      "raw_closes_match": True, "old_main_price_repaired": False, "requests": 2}, ensure_ascii=False))


if __name__ == "__main__":
    main()
