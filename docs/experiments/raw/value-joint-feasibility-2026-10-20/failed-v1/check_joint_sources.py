#!/usr/bin/env python3
"""Bounded read-only join of the fixed cohort, extracted annual source rows, and bound price responses."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def bound_json(binding: dict[str, Any], label: str) -> tuple[Path, Any]:
    if not isinstance(binding, dict) or not isinstance(binding.get("path"), str):
        raise ValueError(f"{label}: invalid path binding")
    path = Path(binding["path"])
    expected = binding.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"{label}: invalid SHA-256 binding")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label}: SHA-256 mismatch for {path}: expected {expected}, got {actual}")
    return path, read_json(path)


def source_binding(binding: dict[str, Any], label: str) -> dict[str, str]:
    path = Path(binding["path"])
    actual = sha256(path)
    if actual != binding.get("sha256"):
        raise ValueError(f"{label}: SHA-256 mismatch for {path}: expected {binding.get('sha256')}, got {actual}")
    return {"path": str(path), "sha256": actual}


def normalized_flag(value: Any) -> str:
    return str(value).strip()


def load_response(binding: dict[str, Any], expected_code: str, expected_adjustflag: str, label: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    path, payload = bound_json(binding, label)
    if not isinstance(payload, dict):
        raise ValueError(f"{label}: response must be an object")
    try:
        error_code = int(payload.get("error_code"))
    except (TypeError, ValueError):
        raise ValueError(f"{label}: missing/non-numeric error_code")
    if error_code != 0:
        raise ValueError(f"{label}: vendor error_code={payload.get('error_code')}: {payload.get('error_msg')}")
    fields = payload.get("fields")
    if not isinstance(fields, list) or not all(isinstance(x, str) for x in fields):
        raise ValueError(f"{label}: fields must be a string list")
    records = payload.get("data")
    if records is None:
        records = payload.get("rows")
    if not isinstance(records, list):
        raise ValueError(f"{label}: expected data or rows list")
    required = {"date", "code", "close", "adjustflag", "tradestatus"}
    missing = sorted(required - set(fields))
    if missing:
        raise ValueError(f"{label}: response lacks required columns {missing}")
    index = {name: fields.index(name) for name in required}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for n, row in enumerate(records):
        if not isinstance(row, list) or len(row) != len(fields):
            raise ValueError(f"{label}: row {n} does not match fields width")
        item = {name: row[i] for name, i in index.items()}
        dt = item["date"]
        if not isinstance(dt, str):
            raise ValueError(f"{label}: row {n} has invalid date")
        date.fromisoformat(dt)
        if dt in seen:
            raise ValueError(f"{label}: duplicate date {dt}")
        seen.add(dt)
        if item["code"] != expected_code:
            raise ValueError(f"{label}: unexpected code {item['code']} at {dt}")
        if normalized_flag(item["adjustflag"]) != expected_adjustflag:
            raise ValueError(f"{label}: unexpected adjustflag {item['adjustflag']} at {dt}")
        out.append(item)
    out.sort(key=lambda x: x["date"])
    return {"path": str(path), "sha256": binding["sha256"]}, out


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    result = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"field_rows line {n}: invalid JSON: {e}") from e
            if not isinstance(row, dict):
                raise ValueError(f"field_rows line {n}: expected object")
            result.append(row)
    return result


def status_of(row: dict[str, Any], name: str) -> str:
    obj = row.get("fields", {}).get(name, {})
    if not isinstance(obj, dict):
        return "unknown"
    return str(obj.get("status", "unknown"))


def run(plan_path: Path, out_path: Path) -> dict[str, Any]:
    plan_sha = sha256(plan_path)
    plan = read_json(plan_path)
    if plan.get("schema") != "annual-value-joint-source-check/1":
        raise ValueError(f"unsupported plan schema: {plan.get('schema')}")
    if plan.get("mode") != "source_qualification":
        raise ValueError("plan mode is not source_qualification")

    definition_path, _ = bound_json(plan["definition_binding"], "definition_binding")
    cohort_path, cohort = bound_json(plan["cohort"], "cohort")
    field_path = Path(plan["field_rows"]["path"])
    field_hash = sha256(field_path)
    if field_hash != plan["field_rows"].get("sha256"):
        raise ValueError(f"field_rows SHA-256 mismatch: {field_path}")
    calendar_path, calendar = bound_json(plan["calendar"], "calendar")

    codes = cohort.get("fixed_codes") if isinstance(cohort, dict) else None
    if not isinstance(codes, list) or len(codes) != 600 or len(set(codes)) != 600:
        raise ValueError("financial-cohort.fixed_codes must contain exactly 600 unique codes")
    cohort_codes = set(codes)

    cal_fields = calendar.get("fields")
    cal_rows = calendar.get("data")
    if not isinstance(cal_fields, list) or not isinstance(cal_rows, list):
        raise ValueError("calendar must contain fields/data arrays")
    if "calendar_date" not in cal_fields or "is_trading_day" not in cal_fields:
        raise ValueError("calendar lacks calendar_date/is_trading_day")
    ci_date, ci_trade = cal_fields.index("calendar_date"), cal_fields.index("is_trading_day")
    last_trade: dict[int, str] = {}
    dates_seen = set()
    for n, row in enumerate(cal_rows):
        if not isinstance(row, list) or len(row) != len(cal_fields):
            raise ValueError(f"calendar row {n} width mismatch")
        dt = row[ci_date]
        date.fromisoformat(dt)
        if dt in dates_seen:
            raise ValueError(f"calendar duplicate date {dt}")
        dates_seen.add(dt)
        if normalized_flag(row[ci_trade]) == "1":
            year = int(dt[:4])
            last_trade[year] = max(last_trade.get(year, ""), dt)
    years = [int(y) for y in plan.get("years", [])]
    if not years or any(y not in last_trade for y in years):
        raise ValueError("calendar does not cover all requested years")

    all_fields = read_jsonl(field_path)
    if len(all_fields) != 5503:
        raise ValueError(f"expected 5503 field_rows records, got {len(all_fields)}")
    source_rows = [r for r in all_fields if r.get("code") in cohort_codes and r.get("report_year") in years]
    source_by_key: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for r in source_rows:
        if not isinstance(r.get("original_pdf"), dict):
            raise ValueError(f"row {r.get('entry_id')} missing original_pdf binding")
        source_by_key[(r["code"], int(r["report_year"]))].append(r)

    price_sources: dict[str, dict[str, Any]] = {}
    prices_by_code_year: dict[tuple[str, int], dict[str, Any]] = {}
    for binding in plan.get("price_sources", []):
        code = binding.get("code")
        expected_flag = str(binding.get("requested_adjustflag"))
        if not code or expected_flag != "3":
            raise ValueError(f"invalid price source plan entry: {binding}")
        receipt_binding = binding.get("receipt")
        receipt_path, receipt_obj = bound_json(receipt_binding, f"receipt:{code}")
        data_binding, records = load_response(binding["data"], code, expected_flag, f"price:{code}")
        price_sources[code] = {
            "data": data_binding,
            "receipt": {"path": str(receipt_path), "sha256": receipt_binding["sha256"]},
            "requested_adjustflag": expected_flag,
            "response_rows": len(records),
            "response_schema": "data" if isinstance(read_json(binding["data"]["path"]), dict) and "data" in read_json(binding["data"]["path"]) else "rows",
        }
        for rec in records:
            if rec["date"][:4].isdigit():
                key = (code, int(rec["date"][:4]))
                if rec["date"] == last_trade.get(key[1]):
                    prices_by_code_year[key] = rec

    yearly = {}
    intersections = []
    for year in years:
        year_rows = [r for r in source_rows if int(r["report_year"]) == year]
        codes_with_docs = {r["code"] for r in year_rows}
        price_codes = {code for code in cohort_codes if (code, year) in prices_by_code_year}
        joint_codes = codes_with_docs & price_codes
        parent_candidates = sum(status_of(r, "parent_equity") == "source_candidate" for r in year_rows)
        other_candidates = sum(status_of(r, "other_equity") == "source_candidate" for r in year_rows)
        yearly[str(year)] = {
            "last_market_date": last_trade[year],
            "original_document_rows": len(year_rows),
            "issuers_with_originals": len(codes_with_docs),
            "parent_equity_candidate_rows": parent_candidates,
            "other_equity_candidate_rows": other_candidates,
            "cohort_issuers_with_last_market_day_price": len(price_codes),
            "issuers_with_original_and_last_market_day_price": len(joint_codes),
        }
        for code in sorted(joint_codes):
            price = prices_by_code_year[(code, year)]
            for source in sorted(source_by_key[(code, year)], key=lambda x: (x.get("publication_date", ""), x.get("announcement_id", ""))):
                intersections.append({
                    "code": code,
                    "report_year": year,
                    "market_last_trading_date": last_trade[year],
                    "announcement_id": source.get("announcement_id"),
                    "announcement_date": source.get("publication_date"),
                    "original_pdf": source["original_pdf"],
                    "field_status": {name: status_of(source, name) for name in ("parent_equity", "other_equity", "treasury_stock", "accounting_capital")},
                    "price": {"close": price["close"], "adjustflag": price["adjustflag"], "tradestatus": price["tradestatus"], "code": price["code"], "date": price["date"]},
                })

    result = {
        "schema": "annual-value-joint-source-check-result/1",
        "plan": {"path": str(plan_path), "sha256": plan_sha},
        "inputs": {
            "definition_binding": {"path": str(definition_path), "sha256": plan["definition_binding"]["sha256"]},
            "cohort": {"path": str(cohort_path), "sha256": plan["cohort"]["sha256"], "fixed_code_count": len(codes)},
            "field_rows": {"path": str(field_path), "sha256": field_hash, "record_count": len(all_fields)},
            "calendar": {"path": str(calendar_path), "sha256": plan["calendar"]["sha256"]},
            "price_sources": price_sources,
        },
        "scope": {"years": years, "fixed_cohort_only": True, "only_bound_two_price_responses": True, "market_data_requests": 0, "market_effects_computed": False, "factor_eligibility_asserted": False},
        "totals": {
            "cohort_original_document_rows": len(source_rows),
            "cohort_company_years_with_originals": len(source_by_key),
            "parent_equity_candidate_rows": sum(status_of(r, "parent_equity") == "source_candidate" for r in source_rows),
            "other_equity_candidate_rows": sum(status_of(r, "other_equity") == "source_candidate" for r in source_rows),
            "company_years_with_bound_price_on_last_market_day": sum(1 for key in source_by_key if key in prices_by_code_year),
            "joint_original_price_records": len(intersections),
        },
        "by_year": yearly,
        "original_price_intersections": intersections,
        "limitations": ["This checks only the original 600-code cohort and the two price responses bound in the plan.", "Candidate financial fields and matching source dates do not establish financial-factor eligibility or point-in-time qualification.", "No missing values are imputed and no returns/effects are calculated."],
    }
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {out_path}")
    if not out_path.parent.is_dir():
        raise FileNotFoundError(f"output parent directory does not exist: {out_path.parent}")
    with out_path.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path, help="path to frozen plan.json")
    parser.add_argument("--out", required=True, type=Path, help="new output JSON path; existing files are refused")
    args = parser.parse_args()
    result = run(args.plan, args.out)
    print(json.dumps({"status": "complete", "output": str(args.out), "year_count": len(result["by_year"]), "totals": result["totals"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
