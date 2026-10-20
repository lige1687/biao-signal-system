"""Independently reconcile saved records and preselected original-page reviews.

Does not import the extractor, read prices, or rerun PDF extraction.
"""
import collections
import hashlib
import json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    storage = json.loads((HERE / "storage-plan.json").read_text())
    output = Path(storage["output"])
    rows_path = output / "rows.jsonl"
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    summary = json.loads((output / "summary.json").read_text())
    original = json.loads((HERE / "independent-original-review.json").read_text())
    index = json.loads(Path(plan["expected_index_path"]).read_text())
    codes = set(json.loads(Path(plan["cohort_path"]).read_text())["fixed_codes"])
    expected_ids = {
        f"index:{i}"
        for i, item in enumerate(index)
        if item["code"] in codes
        and isinstance(item["year"], int)
        and not isinstance(item["year"], bool)
        and 2013 <= item["year"] <= 2024
        and item["title"] == f'{item["year"]}年年度报告'
        and (item.get("pdf") or {}).get("status") == "obtained"
        and (item.get("prepared_binding") or {}).get("identity_status") == "match"
    }
    assert len(rows) == len(expected_ids) == 5503
    assert {row["entry_id"] for row in rows} == expected_ids
    assert all(row["factor_ready"] is False for row in rows)
    assert summary["market_effects_computed"] is False
    assert summary["plan_sha256"] == digest(HERE / "plan.json")
    lookup = {(r["code"], r["report_year"], r["announcement_id"]): r for r in rows}
    fields = ("parent_equity", "other_equity", "treasury_stock", "accounting_capital")
    field_stats = {}
    by_year = {}
    for name in fields:
        status = dict(collections.Counter(r["fields"][name]["status"] for r in rows))
        assert status == summary["field_status_counts"][name]
        accepted = [r for r in rows if r["fields"][name]["status"] == "source_candidate"]
        field_stats[name] = {
            "status_counts": status,
            "unique_company_years": len({(r["code"], r["report_year"]) for r in accepted}),
            "issuers": len({r["code"] for r in accepted}),
            "negative_current_amounts": sum(
                Decimal(r["fields"][name]["value_yuan"]) < 0 for r in accepted
            ),
            "unknown_reasons": dict(collections.Counter(
                r["fields"][name]["reason"] for r in rows
                if r["fields"][name]["status"] != "source_candidate"
            )),
        }
    for year in range(2013, 2025):
        group = [r for r in rows if r["report_year"] == year]
        by_year[str(year)] = {
            "originals": len(group),
            "company_years": len({r["code"] for r in group}),
            "qualified_assets_contexts": sum(r["assets_table"]["status"] == "qualified" for r in group),
            **{f"{name}_candidates": sum(
                r["fields"][name]["status"] == "source_candidate" for r in group
            ) for name in fields},
        }
    mapping = {
        "parent_equity": "parent_equity_total",
        "other_equity": "other_equity_instruments",
        "treasury_stock": "treasury_shares",
        "accounting_capital": "share_capital",
    }
    comparisons = []
    for case in original["cases"]:
        row = lookup[(case["code"], case["year"], case["announcement_id"])]
        for field, manual_name in mapping.items():
            observed = row["fields"][field]
            manual = case["fields"][manual_name]
            result = {
                "code": case["code"], "year": case["year"],
                "field": field, "automated_status": observed["status"],
                "manual_current": manual["current_yuan"],
                "manual_comparative": manual["comparative_yuan"],
            }
            if observed["status"] == "source_candidate":
                try:
                    expected = Decimal(manual["current_yuan"])
                    comparison = Decimal(manual["comparative_yuan"])
                except Exception as exc:
                    raise AssertionError(f"Automatic amount lacks independent numeric support: {result}") from exc
                assert Decimal(observed["value_yuan"]) == expected, result
                assert Decimal(observed["comparative_value_yuan_not_selected"]) == comparison, result
                result["verdict"] = "both_amounts_match"
            else:
                assert observed["value_yuan"] is None
                result["verdict"] = (
                    "manual_amount_exists_auto_rejected"
                    if manual["current_yuan"] is not None else "missing_not_filled"
                )
                result["automated_reason"] = observed["reason"]
            comparisons.append(result)
    protected = json.loads((HERE / "protected-before.json").read_text())
    for item in protected:
        assert digest(Path(item["path"])) == item["sha256"]
    record = {
        "status": "source_only_reconciled",
        "rows_path": str(rows_path), "rows_sha256": digest(rows_path),
        "rows_bytes": rows_path.stat().st_size, "records": len(rows),
        "unique_company_years": len({(r["code"], r["report_year"]) for r in rows}),
        "issuers": len({r["code"] for r in rows}),
        "field_statistics": field_stats, "by_year": by_year,
        "comparison_counts": dict(collections.Counter(c["verdict"] for c in comparisons)),
        "comparison_counts_by_field": {
            name: dict(collections.Counter(c["verdict"] for c in comparisons if c["field"] == name))
            for name in fields
        },
        "original_page_comparisons": comparisons,
        "old_protected_files_unchanged": True,
        "all_factor_ready_false": True,
        "market_effects_computed": False,
        "limitations": [
            "Independent review is 12 preselected originals, not complete financial certification.",
            "No original with numeric other-equity-instrument balances in independent review; automatic numeric candidates remain unvalidated for that field.",
            "Current and comparison amounts belong to this version; comparison dates are raw headers, never backfilled.",
            "Independent reviewer read extra nearby pages and recorded the scope deviation; only consolidated-table amounts were used.",
        ],
    }
    with (HERE / "controller-output-review.json").open("x") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: record[k] for k in (
        "status", "records", "unique_company_years", "issuers",
        "field_statistics", "comparison_counts", "comparison_counts_by_field"
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()
