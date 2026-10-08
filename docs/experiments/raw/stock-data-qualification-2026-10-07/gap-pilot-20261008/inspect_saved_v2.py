"""Check corrected three-key selection against saved original files, without network."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DATES = ("2022-01-04", "2022-01-05", "2022-01-06")


def source(path: str) -> dict:
    p = ROOT / path
    return {"path": path, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main() -> None:
    scope = json.loads((OUT / "scope-v2.json").read_text())
    assert [(x["symbol"], x["date"]) for x in scope["selected_keys"]] == [("600837", d) for d in DATES]
    event_path = "docs/experiments/raw/csi300-anchor-acquisition-2026-10-07/official-20211210-csi300-event.json"
    manifest_path = "docs/experiments/raw/stock-universe-data-qualification-2026-10-05/read-only-source-manifest-v2.json"
    raw_path = "docs/experiments/raw/b02-targeted-gap-batch-2026-10-05/run-01/normalized/daily_raw/daily-1-sh-600837.json"
    factor_path = "docs/experiments/raw/b02-targeted-gap-batch-2026-10-05/run-01/normalized/factor/factor-1-sh-600837.json"
    old_factor_path = "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/normalized/factor/factor-2-sh-600837.json"
    member_path = "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/csi300_membership_daily.parquet"
    event = json.loads((ROOT / event_path).read_text())
    assert "600705" in {r["code"] for r in event["removed"]}
    assert "600837" not in {r["code"] for r in event["removed"] + event["added"]}
    manifest = json.loads((ROOT / manifest_path).read_text())
    main_file = Path(manifest["stock_close"]["source_file"]["path"])
    assert main_file.stat().st_size == manifest["stock_close"]["source_file"]["bytes"]
    assert hashlib.sha256(main_file.read_bytes()).hexdigest() == manifest["stock_close"]["source_file"]["sha256"]
    assert "600837" not in pq.read_metadata(main_file).schema.names
    rec = next(r for r in manifest["stock_close"]["per_code"] if r["symbol_code_only"] == "600837")
    assert rec["member_first"] == DATES[0] and rec["candidate_member_dates"] == 767
    raw = json.loads((ROOT / raw_path).read_text())
    by_day = {r["date"]: r for r in raw["records"]}
    rows = [by_day[d] for d in DATES + ("2022-01-07",)]
    assert all(r["code"] == "sh.600837" and r["tradestatus"] == "1" and r["adjustflag"] == "3" and int(r["volume"]) > 0 for r in rows)
    neighbor = [{"before": a["date"], "after": b["date"], "before_close": a["close"], "after_preclose": b["preclose"], "exact_match": a["close"] == b["preclose"]} for a, b in zip(rows, rows[1:])]
    assert all(x["exact_match"] for x in neighbor)
    factors = json.loads((ROOT / factor_path).read_text())["records"]
    later_factors = json.loads((ROOT / old_factor_path).read_text())["records"]
    assert not [r for r in factors + later_factors if r["dividOperateDate"] <= DATES[-1]]
    member = pq.read_table(ROOT / member_path, columns=["date", "symbol"])
    member_days = {str(r["date"])[:10] for r in member.to_pylist() if r["symbol"] == "600837" and str(r["date"])[:10] in DATES}
    assert member_days == set(DATES)
    result = {"selected_keys": [{"exchange": "XSHG", "symbol": "600837", "date": r["date"], "raw_close": r["close"], "raw_preclose": r["preclose"], "volume": r["volume"], "adjustflag": r["adjustflag"], "main_old_qfq_close": None} for r in rows[:3]],
              "neighbor_links": neighbor, "all_three_saved_links_match": True,
              "jan4_prior_neighbor_in_B02_saved_window": False,
              "saved_B02_factor_events": [r["dividOperateDate"] for r in factors],
              "saved_B01_later_factor_events": [r["dividOperateDate"] for r in later_factors],
              "saved_factor_start_state_2022_01_04": None,
              "candidate_membership_three_dates": True, "official_complete_start_anchor_verified": False,
              "600837_not_in_known_official_20211210_added_or_removed": True,
              "source_receipts": [source(x) for x in (event_path, manifest_path, raw_path, factor_path, old_factor_path, member_path)],
              "main_price_source": manifest["stock_close"]["source_file"],
              "new_requests": 0, "main_price_repair": 0}
    (OUT / "saved-observations-v2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"keys": [(r["symbol"], r["date"], r["raw_close"]) for r in result["selected_keys"]], "neighbor_links": 3, "old_main_column": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
