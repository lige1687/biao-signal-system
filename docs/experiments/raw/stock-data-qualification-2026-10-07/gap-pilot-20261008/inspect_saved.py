"""Read existing price-source observations for the three fixed dates; no network."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DATES = ("2022-01-04", "2022-01-05", "2022-01-06")


def rel_file(path: str) -> dict:
    p = ROOT / path
    return {"path": path, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main() -> None:
    scope = json.loads((OUT / "scope.json").read_text())
    assert [r["date"] for r in scope["selected_keys"]] == list(DATES)
    manifest_path = "docs/experiments/raw/stock-universe-data-qualification-2026-10-05/read-only-source-manifest-v2.json"
    raw_path = "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/normalized/daily_raw/daily-1-sh-600705.json"
    factor_path = "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/normalized/factor/factor-1-sh-600705.json"
    wire_path = "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/raw/daily-1-sh-600705-wire.bin"
    factor_wire_path = "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/raw/factor-1-sh-600705-wire.bin"
    membership_path = "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/csi300_membership_daily.parquet"
    main_price_path = Path("/Users/yongbiaoli/.lei_signal_lab/cache/a_share_klines_full.parquet")
    manifest = json.loads((ROOT / manifest_path).read_text())
    expected_main = manifest["stock_close"]["source_file"]
    assert main_price_path.stat().st_size == expected_main["bytes"]
    assert hashlib.sha256(main_price_path.read_bytes()).hexdigest() == expected_main["sha256"]
    assert "600705" not in pq.read_metadata(main_price_path).schema.names
    old = [r for r in manifest["stock_close"]["per_code"] if r["symbol_code_only"] == "600705"]
    assert len(old) == 1 and old[0]["candidate_member_dates"] == 9
    assert old[0]["close_column_present"] is False and old[0]["member_first"] == DATES[0]
    factor = json.loads((ROOT / factor_path).read_text())
    assert factor["records"] == []
    raw = json.loads((ROOT / raw_path).read_text())
    by_day = {r["date"]: r for r in raw["records"]}
    preceding, following = by_day["2021-12-31"], by_day["2022-01-07"]
    selected = [by_day[d] for d in DATES]
    assert all(r["code"] == "sh.600705" and r["tradestatus"] == "1" and int(r["volume"]) > 0 and float(r["close"]) > 0 for r in selected)
    member = pq.read_table(ROOT / membership_path, columns=["date", "symbol"])
    member_dates = {str(r["date"])[:10] for r in member.to_pylist() if r["symbol"] == "600705" and str(r["date"])[:10] in DATES}
    assert member_dates == set(DATES)
    context = [preceding] + selected + [following]
    adjacent = []
    for left, right in zip(context, context[1:]):
        adjacent.append({"previous_date": left["date"], "date": right["date"], "previous_close": left["close"], "reported_preclose": right["preclose"], "exact_string_match": left["close"] == right["preclose"]})
    result = {
        "scope": "saved observations only; no new request or adjusted price",
        "selection_rule": scope["selection_rule"],
        "selected_keys": [{"exchange": "XSHG", "symbol": "600705", "date": r["date"], "raw_close": r["close"], "raw_preclose": r["preclose"], "raw_adjustflag": r["adjustflag"], "trade_status": r["tradestatus"], "volume": r["volume"], "amount": r["amount"], "main_old_qfq_column_present": False} for r in selected],
        "same_source_adjacency": adjacent,
        "all_four_neighbor_links_match": all(r["exact_string_match"] for r in adjacent),
        "saved_factor_query_rows": 0,
        "saved_factor_window": ["2021-12-01", "2022-02-15"],
        "old_candidate_membership_not_official_anchor": True,
        "old_main_qfq_column_present": False,
        "old_main_qfq_adjustment_anchor_known": False,
        "source_receipts": [rel_file(x) for x in [manifest_path, raw_path, factor_path, wire_path, factor_wire_path, membership_path]],
        "main_price_source": {"path": str(main_price_path), "bytes": expected_main["bytes"], "sha256": expected_main["sha256"]},
        "new_requests": 0,
    }
    target = OUT / "saved-observations.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"selected": [(r["symbol"], r["date"], r["raw_close"]) for r in result["selected_keys"]], "neighbor_links_match": result["all_four_neighbor_links_match"], "factor_rows": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
