"""Decode saved 600837 public responses locally; never execute response JavaScript."""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import akshare
from akshare.stock.stock_zh_a_sina import hk_js_decode, py_mini_racer

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
DATES = ("2022-01-04", "2022-01-05", "2022-01-06")
NEIGHBORS = DATES + ("2022-01-07",)


def digest(path: Path) -> dict:
    return {"path": str(path), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main() -> None:
    ledger = json.loads((OUT / "request-ledger.json").read_text())
    last = ledger["attempts"][-2:]
    assert [(x["kind"], x["result"], x["http_status"]) for x in last] == [
        ("qfq-600837", "response_saved", 200),
        ("history-600837", "response_saved", 200)]
    qfq_path = OUT / "sina-qfq-sh600837-response.bin"
    history_path = OUT / "sina-history-sh600837-response.bin"
    qfq_bytes, history_bytes = qfq_path.read_bytes(), history_path.read_bytes()
    assert [hashlib.sha256(x).hexdigest() for x in (qfq_bytes, history_bytes)] == [x["sha256"] for x in last]
    match = re.fullmatch(rb'var sh600837qfq=(\{"total":\d+,"data":\[.*?\]\})\s*/\*.*?\*/\s*', qfq_bytes, re.DOTALL)
    assert match, "unexpected adjustment wrapper"
    factor_obj = json.loads(match.group(1))
    factors = factor_obj["data"]
    assert len(factors) == factor_obj["total"] and all(set(x) == {"d", "f"} for x in factors)
    match = re.match(rb'^var KLC_K2_sh600837="([A-Za-z0-9+/=]+)";', history_bytes)
    assert match, "unexpected encoded history wrapper"
    decoder = py_mini_racer.MiniRacer()
    decoder.eval(hk_js_decode)  # installed decoder only, never the remote code
    decoded = decoder.call("d", match.group(1).decode("ascii"))
    assert isinstance(decoded, list)
    by_day = {r["date"][:10]: r for r in decoded}
    assert len(by_day) == len(decoded)
    saved_path = ROOT / "docs/experiments/raw/b02-targeted-gap-batch-2026-10-05/run-01/normalized/daily_raw/daily-1-sh-600837.json"
    saved = {r["date"]: r for r in json.loads(saved_path.read_text())["records"]}
    compared = []
    for day in NEIGHBORS:
        raw = Decimal(str(by_day[day]["close"]))
        prior = Decimal(saved[day]["close"])
        assert raw == prior, f"Sina and BaoStock raw close differ at {day}"
        eligible_factors = [f for f in factors if f["d"] <= day]
        factor = max(eligible_factors, key=lambda f: f["d"]) if eligible_factors else None
        qfq = f"{round(float(raw) / float(factor['f']), 2):.2f}" if factor else None
        compared.append({"date": day, "sina_current_raw_close": str(raw),
                         "baostock_saved_raw_close": saved[day]["close"],
                         "raw_sources_match": True,
                         "sina_current_factor_date": factor["d"] if factor else None,
                         "sina_current_qfq_factor": factor["f"] if factor else None,
                         "illustrative_current_sina_qfq_close": qfq,
                         "old_main_original_qfq_close": None})
    links = []
    for before, after in zip(NEIGHBORS, NEIGHBORS[1:]):
        links.append({"before": before, "after": after,
                      "exact_match": saved[after]["preclose"] == saved[before]["close"]})
    assert all(x["exact_match"] for x in links)
    earlier = max((f["d"] for f in factors if f["d"] <= DATES[0]), default=None)
    later = min((f["d"] for f in factors if f["d"] > DATES[-1]), default=None)
    result = {
        "schema": "stock-gap-pilot-current-provider-comparison/2.0",
        "selected_dates": list(DATES), "current_sina_decoded_history_rows": len(decoded),
        "current_sina_factor_rows": len(factors), "compared_dates": compared,
        "all_four_raw_closes_cross_source_equal": True,
        "saved_preclose_neighbor_links": links,
        "current_factor_event_bracketing_window": {"last_at_or_before": earlier, "next_after": later},
        "adjustment_method": "installed AKShare 1.18.49 forward-fills Sina qfq factor by date, computes raw close/factor and rounds to 2 decimals",
        "installed_akshare_version": akshare.__version__,
        "response_hashes": [digest(qfq_path), digest(history_path)],
        "saved_baostock_source": digest(saved_path),
        "old_original_600837_qfq_column_present": False,
        "old_original_sina_factor_snapshot_and_anchor_verified": False,
        "historically_available_at_2022": None,
        "official_corporate_action_or_adjustment_basis_verified": False,
        "actual_price_repair_performed": False,
        "cumulative_new_requests": ledger["cumulative_requests_attempted"],
        "cumulative_new_received_bytes": ledger["cumulative_response_bytes"],
    }
    (OUT / "comparison-v2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"selected": compared[:3], "factor_bracket": result["current_factor_event_bracketing_window"],
                      "new_requests": result["cumulative_new_requests"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
