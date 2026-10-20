#!/usr/bin/env python3
"""Source-only amount inventory from frozen, already-qualified annual balance sheets.

No prices, legal share counts, version selection or factor calculation. Every
selected annual original receives one row. An integrity error aborts the batch.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import plistlib
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

SCHEMA = "saved-value-fields-source-only/1"
FIELD_PATTERNS = {
    "parent_equity": re.compile(r"^归属于\s*母公司\s*(?:所有者|股东)权益\s*合计(?=\s|\d|$)"),
    "other_equity": re.compile(r"^其他权益工具(?!投资)(?=\s|\d|$)"),
    "treasury_stock": re.compile(r"^减\s*[:：]?\s*库存股(?=\s|\d|$)"),
    "accounting_capital": re.compile(r"^(?:股本|实收资本\s*[（(]\s*或股本\s*[）)])(?=\s|\d|$)"),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bound_json(path_text: str, expected_sha: str):
    path = Path(path_text)
    if not path.is_absolute() or not path.is_file() or sha256_file(path) != expected_sha:
        raise ValueError(f"bound JSON absent or changed: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_old_parser(path_text: str, expected_sha: str):
    path = Path(path_text)
    if not path.is_absolute() or not path.is_file() or sha256_file(path) != expected_sha:
        raise ValueError("frozen old parser absent or changed")
    spec = importlib.util.spec_from_file_location("frozen_profitability_parser", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original_selection(entry, cohort_codes, years):
    """Return a reason; None means exact-title, saved, identity-matched original."""
    if entry.get("code") not in cohort_codes:
        return "outside_frozen_cohort"
    year = entry.get("year")
    if year not in years:
        return "outside_years"
    if entry.get("title") != f"{year}年年度报告":
        return "not_exact_title"
    pdf = entry.get("pdf") or {}
    if pdf.get("status") != "obtained" or not pdf.get("source_path"):
        return "annual_original_pdf_unavailable"
    prepared = entry.get("prepared_binding") or {}
    if prepared.get("identity_status") != "match" or not prepared.get("path"):
        return "annual_original_prepared_identity_unmatched"
    return None


def verify_prepared_and_pdf(entry):
    pdf = entry["pdf"]
    prepared_ref = entry["prepared_binding"]
    prepared = bound_json(prepared_ref["path"], prepared_ref["sha256"])
    path = Path(pdf["source_path"])
    if (not path.is_absolute() or not path.is_file() or
            path.stat().st_size != pdf["bytes"] or sha256_file(path) != pdf["sha256"]):
        raise ValueError(f"original PDF integrity failure: {entry.get('code')} {entry.get('id')}")
    source = prepared.get("source") or {}
    identity = source.get("source_identity") or {}
    checks = identity.get("checks") or {}
    code = entry["code"].split(".")[-1]
    if (source.get("cohort_code") != entry["code"] or
            source.get("publisher_code") != code or
            source.get("report_year_from_title") != entry["year"] or
            source.get("announcement_id") != entry["id"] or
            source.get("announcement_date_asia_shanghai") != entry["publication_date"] or
            identity.get("path") != str(path) or identity.get("sha256") != pdf["sha256"] or
            identity.get("bytes") != pdf["bytes"] or
            any(checks.get(k) is not True for k in
                ("status_qualified", "publisher_code_matches", "bytes_match", "sha256_matches", "pdf_header"))):
        raise ValueError(f"prepared/original identity failure: {entry['code']} {entry['id']}")
    return path, prepared


def selected_pages(pdf_path: Path, heading_page: int, max_pages: int):
    import pypdfium2
    pdf = pypdfium2.PdfDocument(str(pdf_path))
    if not 1 <= heading_page <= len(pdf):
        raise ValueError("qualified heading page outside PDF")
    end = min(len(pdf), heading_page + max_pages - 1)
    return [(n, pdf[n - 1].get_textpage().get_text_range())
            for n in range(heading_page, end + 1)]


def bounded_statement_rows(pages, heading_page, old):
    """Stop at the next financial table heading, especially the parent table."""
    rows = [(p, n, text.strip()) for p, body in pages
            for n, text in enumerate(body.splitlines(), 1) if text.strip()]
    starts = [i for i, (p, _, text) in enumerate(rows)
              if p == heading_page and (m := old.HEAD.fullmatch(text)) and
              re.sub(r"\s+", "", m.group(1)) == "合并" and
              re.sub(r"\s+", "", m.group(2)) == "资产负债表"]
    if len(starts) != 1:
        return None, "qualified_consolidated_heading_not_unique_on_bound_page"
    start = starts[0]
    ends = [i for i in range(start + 1, len(rows)) if old.HEAD.fullmatch(rows[i][2])]
    if not ends:
        return None, "next_financial_table_boundary_not_seen_within_page_limit"
    end = ends[0]
    next_heading = old.HEAD.fullmatch(rows[end][2])
    if re.sub(r"\s+", "", next_heading.group(1)) != "母公司" or re.sub(r"\s+", "", next_heading.group(2)) != "资产负债表":
        return None, "next_table_is_not_parent_balance_sheet"
    return rows[start:end], None


def unknown(reason, candidates=()):
    return {"status": "unknown", "value_yuan": None, "reason": reason,
            "candidates": list(candidates)[:4]}


def continuation_context_reason(rows, assets, old, unit):
    """Reject a conflicting unit or reversed/changed current-comparative header."""
    base = re.sub(r"\s+", "", assets["header"])
    dates = re.findall(r"20\d{2}年(?:12月31日|1月1日)", base)
    labels = next(((a, b) for a, b in (("期末余额", "期初余额"),
                                       ("期末余额", "年初余额"),
                                       ("年末余额", "期初余额"),
                                       ("年末余额", "年初余额")) if a in base and b in base), None)
    for _, _, raw in rows:
        compact = re.sub(r"\s+", "", raw)
        if "单位" in compact:
            found = old.UNIT.search(raw)
            if found and found.group(1) != unit:
                return "conflicting_continuation_unit"
        if not compact.startswith(("项目", "资产附注", "负债和所有者权益附注", "负债和股东权益附注")):
            continue
        current_dates = re.findall(r"20\d{2}年(?:12月31日|1月1日)", compact)
        if current_dates and (not dates or current_dates != dates):
            return "conflicting_continuation_columns"
        if labels and any(x in compact for x in ("期末余额", "年末余额", "期初余额", "年初余额")):
            if not (labels[0] in compact and labels[1] in compact and
                    compact.index(labels[0]) < compact.index(labels[1])):
                return "conflicting_continuation_columns"
    return None


def extract_amount_field(rows, pattern, unit, has_note_column, old):
    candidates = []
    for page, line, raw in rows:
        match = pattern.match(raw)
        if match is None:
            continue
        tail = raw[match.end():].strip()
        # A missing cell, dash, adjacent labelled row, or three monetary cells
        # is not repaired by reading across rows or assuming zero.
        tokens = old.MONEY_TOKEN.findall(tail)
        value, reason = (old._money(tail, has_note_column) if len(tokens) == 2
                         else (None, "exactly_two_amount_cells_required"))
        item = {"page": page, "line": line, "raw_line": raw[:300], "reason": reason}
        if reason is None:
            item["value_yuan"] = str(value * old.SCALE[unit])
        candidates.append(item)
    if len(candidates) != 1 or candidates[0]["reason"] is not None:
        return unknown("field_missing" if not candidates else "field_blank_or_ambiguous", candidates)
    item = candidates[0]
    return {"status": "source_candidate", "value_yuan": item["value_yuan"],
            "unit": "RMB_yuan", "reason": None,
            "evidence": {key: item[key] for key in ("page", "line", "raw_line")}}


def extract_qualified_fields(pages, assets, old):
    if assets.get("status") != "qualified":
        raise ValueError("extract_qualified_fields requires qualified assets metadata")
    rows, boundary_reason = bounded_statement_rows(pages, int(assets["heading_page"]), old)
    if boundary_reason:
        return {name: unknown(boundary_reason) for name in FIELD_PATTERNS}, boundary_reason
    unit_match = old.UNIT.search(assets.get("unit_line") or "")
    if unit_match is None or not assets.get("currency_rule") or not assets.get("header"):
        return {name: unknown("qualified_table_unit_or_currency_metadata_missing")
                for name in FIELD_PATTERNS}, "qualified_table_unit_or_currency_metadata_missing"
    unit = unit_match.group(1)
    conflict = continuation_context_reason(rows, assets, old, unit)
    if conflict:
        return {name: unknown(conflict) for name in FIELD_PATTERNS}, conflict
    has_note_column = "附注" in assets["header"]
    fields = {name: extract_amount_field(rows, pattern, unit, has_note_column, old)
              for name, pattern in FIELD_PATTERNS.items()}
    return fields, None


def process_entry(entry, index_position, old, max_pages):
    pdf_path, prepared = verify_prepared_and_pdf(entry)
    assets = ((prepared.get("financial_parser_result") or {}).get("tables") or {}).get("assets")
    if not isinstance(assets, dict):
        assets = {"status": "unknown", "reason": "assets_parser_record_absent"}
    result = {"entry_id": f"index:{index_position}", "code": entry["code"],
              "report_year": entry["year"], "announcement_id": entry["id"],
              "publication_date": entry["publication_date"],
              "original_pdf": {"path": str(pdf_path), "sha256": entry["pdf"]["sha256"]},
              "prepared_text": {"path": entry["prepared_binding"]["path"],
                                "sha256": entry["prepared_binding"]["sha256"]},
              "assets_table": {"status": assets.get("status"), "reason": assets.get("reason"),
                               "heading_page": assets.get("heading_page"),
                               "header": assets.get("header"), "unit_line": assets.get("unit_line"),
                               "currency_rule": assets.get("currency_rule"),
                               "period_line": assets.get("period_line")},
              "factor_ready": False,
              "as_known_at_date": "unknown_precise_release_time_and_vendor_arrival"}
    if assets.get("status") != "qualified":
        result.update(status="assets_table_unqualified",
                      fields={name: unknown("assets_table_unqualified") for name in FIELD_PATTERNS})
        return result
    pages = selected_pages(pdf_path, int(assets["heading_page"]), max_pages)
    fields, boundary_reason = extract_qualified_fields(pages, assets, old)
    result.update(status="source_fields_partial" if boundary_reason is None else "statement_boundary_unknown",
                  fields=fields, boundary_reason=boundary_reason,
                  inspected_pdf_pages=[page for page, _ in pages])
    return result


def check_output(plan, storage, out):
    mount = Path(storage["external_mount"])
    out = out.resolve()
    if (str(out) != storage["output"] or out.exists() or not out.parent.is_dir() or
            not os.path.ismount(mount) or out.parent.stat().st_dev != storage["external_device"] or
            shutil.disk_usage(mount).free < storage["external_reserve_bytes"]):
        raise ValueError("exact create-only external output/device/capacity preflight failed")
    info = plistlib.loads(subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)],
                                    capture_output=True, check=True, timeout=10).stdout)
    if info.get("VolumeUUID") != storage["external_uuid"]:
        raise ValueError("external volume UUID differs")
    return out


def run(plan_path: Path, out: Path):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or plan.get("factor_ready") is not False or plan.get("network_requests_allowed") != 0:
        raise ValueError("source-only plan scope differs")
    index = bound_json(plan["expected_index_path"], plan["expected_index_sha256"])
    cohort = bound_json(plan["cohort_path"], plan["cohort_sha256"])
    storage = bound_json(plan["storage_plan_path"], plan["storage_plan_sha256"])
    old = load_old_parser(plan["old_parser_path"], plan["old_parser_sha256"])
    out = check_output(plan, storage, out)
    codes = set(cohort["fixed_codes"])
    excluded = Counter()
    selected = []
    for i, entry in enumerate(index):
        reason = original_selection(entry, codes, set(plan["years"]))
        if reason:
            excluded[reason] += 1
        else:
            selected.append((i, entry))
    if len(selected) != plan["expected_originals"] or len({(e["code"], e["year"]) for _, e in selected}) != plan["expected_company_years"] or len({e["code"] for _, e in selected}) != plan["expected_issuers"]:
        raise ValueError("frozen annual-original selection counts differ")
    results = [process_entry(entry, i, old, plan["max_pages_per_qualified_pdf"])
               for i, entry in selected]
    if len({r["entry_id"] for r in results}) != len(results):
        raise ValueError("entry_id collision")
    qualified = sum(r["assets_table"]["status"] == "qualified" for r in results)
    if qualified != plan["expected_assets_table_qualified"]:
        raise ValueError("qualified assets-table count differs")
    counts = Counter(r["status"] for r in results)
    field_counts = {name: dict(Counter(r["fields"][name]["status"] for r in results))
                    for name in FIELD_PATTERNS}
    summary = {"schema": SCHEMA, "status": "source_only", "plan_sha256": sha256_file(plan_path),
               "index_total": len(index), "excluded_counts": dict(excluded),
               "annual_originals": len(results), "company_years": plan["expected_company_years"],
               "qualified_assets_tables": qualified, "record_status_counts": dict(counts),
               "field_status_counts": field_counts, "factor_ready": False,
               "market_effects_computed": False, "network_requests": 0}
    out.mkdir(mode=0o700)
    with (out / "rows.jsonl").open("x", encoding="utf-8") as stream:
        for result in results:
            stream.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.plan.resolve(), args.out.resolve()), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
