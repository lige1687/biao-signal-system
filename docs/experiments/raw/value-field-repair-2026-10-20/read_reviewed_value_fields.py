#!/usr/bin/env python3
"""Read only three frozen annual-report pages for source-field candidates.

This is not a factor adapter or a point-in-time qualification. The source PDF
and prepared record must match the frozen plan's path, identity, size and SHA.
Only the bound balance-sheet page pair and bound share-table page neighbours
are sent to PDF text extraction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PLAN_SCHEMA = "reviewed-value-field-repair/1"
ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "plan.json"
PLAN_SHA256 = "3455a679f3882878bd7d38a24d177111fd04b346390b6b9384fe768745c36963"
_DATE = re.compile(r"20\d{2}年(?:12月31日|1月1日)")
_NUMBER = r"[-−－]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"
_TWO_AMOUNTS = re.compile(rf"^\s*({_NUMBER})\s+({_NUMBER})\s*$")
_SHARE_PAIR = re.compile(r"(?<![\d,.\-−－])(\d[\d,]*)\s+(100(?:\.0+)?%)")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _line_rows(pages):
    return [(page_no, line_no, line.strip())
            for page_no, text in sorted(pages.items())
            for line_no, line in enumerate(text.splitlines(), 1) if line.strip()]


def _has_period_evidence(text: str, report_year: int):
    current = f"{report_year}年12月31日"
    return {"current": current} if current in _compact(text) else None


def _balance_header(lines, report_year):
    """Check every table column header on the bound two pages, including repeats."""
    current = f"{report_year}年12月31日"
    priors = {f"{report_year - 1}年12月31日", f"{report_year}年1月1日"}
    label_pairs = (("期末余额", "年初余额"), ("期末余额", "期初余额"),
                   ("年末余额", "年初余额"), ("年末余额", "期初余额"))
    headers = []
    for page, line_no, raw in lines:
        row = _compact(raw)
        if not re.match(r"^(?:资产(?:附注|项目)|负债和(?:股东|所有者)权益(?:附注|项目)|项目(?:附注|$))", row):
            continue
        dates = _DATE.findall(row)
        if dates:
            status = ("dated" if len(dates) == 2 and dates[0] == current and dates[1] in priors
                      else "conflict")
            signature = tuple(dates) if status == "dated" else None
        else:
            present = [(left, right) for left, right in label_pairs
                       if left in row and right in row]
            status = ("labelled" if present and any(row.index(left) < row.index(right)
                      for left, right in present) else "conflict" if present else None)
            signature = present[0] if status == "labelled" else None
        if status:
            headers.append({"page": page, "line": line_no, "raw_line": raw,
                            "kind": status, "signature": signature})
    if not headers or any(h["kind"] == "conflict" for h in headers):
        return None, headers
    # The continuation may restate the identical columns; a changed pair is unsafe.
    if len({(h["kind"], h["signature"]) for h in headers}) != 1:
        return None, headers
    return headers[0]["kind"], headers


def _rmb_unit_evidence(lines):
    evidence = []
    conflicts = []
    for index, (page, line_no, raw) in enumerate(lines):
        compact = _compact(raw)
        if "单位" not in compact:
            continue
        if "万元" in compact or "百万元" in compact or any(x in compact for x in ("港元", "美元", "欧元")):
            conflicts.append({"page": page, "line": line_no, "raw_line": raw})
            continue
        if "元" not in compact:
            continue
        nearby = _compact("".join(row[2] for row in lines[max(0, index - 1):index + 3]
                                  if row[0] == page))
        if "人民币" in nearby or "币种:RMB" in nearby.upper() or "币种：RMB" in nearby.upper():
            evidence.append({"page": page, "line": line_no, "raw_line": raw})
    return evidence if evidence and not conflicts else None, conflicts


def extract_parent_equity(pages, report_year):
    """Take only a unique consolidated parent-equity row and its two cells."""
    lines = _line_rows(pages)
    text = "\n".join(line for _, _, line in lines)
    if "合并资产负债表" not in _compact(text):
        return {"status": "unknown", "reason": "consolidated_balance_heading_missing"}
    period = _has_period_evidence(text, report_year)
    if period is None:
        return {"status": "unknown", "reason": "current_report_period_unverified"}
    header_kind, headers = _balance_header(lines, report_year)
    if header_kind is None:
        return {"status": "unknown", "reason": "balance_column_header_missing_or_ambiguous",
                "header_candidates": headers[:5]}
    unit_evidence, unit_conflicts = _rmb_unit_evidence(lines)
    if unit_evidence is None:
        return {"status": "unknown", "reason": "RMB_yuan_unit_missing_or_ambiguous",
                "unit_candidates": unit_conflicts[:5]}
    label_pattern = re.compile(r"^归属于\s*母公司\s*(?:所有者权益|股东权益)\s*合计")
    candidates = []
    for index, (page, line_no, raw) in enumerate(lines):
        match = label_pattern.match(raw)
        if match is None:
            continue
        tail = raw[match.end():].strip()
        amount_match = _TWO_AMOUNTS.fullmatch(tail)
        evidence = raw
        # A separate numeric line is allowed; any labelled next row is forbidden.
        if not tail and index + 1 < len(lines) and lines[index + 1][0] == page:
            continuation = lines[index + 1][2]
            amount_match = _TWO_AMOUNTS.fullmatch(continuation)
            if amount_match:
                evidence += " | " + continuation
        values = list(amount_match.groups()) if amount_match else []
        candidates.append({"page": page, "line": line_no, "raw_text": evidence[:600],
                           "values": values, "value": values[0] if values else None})
    if len(candidates) != 1 or candidates[0]["value"] is None:
        return {"status": "unknown", "reason": "parent_equity_row_blank_or_ambiguous",
                "candidates": candidates[:5], "header_evidence": headers,
                "period_evidence": period, "unit_evidence": unit_evidence}
    chosen = candidates[0]
    return {"status": "source_candidate", "unit": "RMB_yuan", "value": chosen["value"],
            "evidence": {key: chosen[key] for key in ("page", "line", "raw_text")},
            "header_evidence": headers, "period_evidence": period,
            "unit_evidence": unit_evidence,
            "comparative_value_not_selected": chosen["values"][1]}


def extract_post_change_total_shares(pages, report_year, share_page):
    """Take the final count-percentage pair in the bound change-table row."""
    lines = _line_rows(pages)
    page_lines = [(p, n, raw) for p, n, raw in lines if p == share_page]
    context = _compact("\n".join(raw for _, _, raw in lines))
    if not ("本次变动前" in context and "本次变动后" in context):
        return {"status": "unknown", "reason": "before_after_share_table_header_missing"}
    if not any(re.search(r"单位[:：]?股", _compact(raw)) for _, _, raw in lines):
        return {"status": "unknown", "reason": "share_unit_missing"}
    label = re.compile(r"^(?:[一二三四五六七八九十]+[、.．])?(?:股份总数|总股本)(?=\s|\d|$)")
    candidates = []
    for page, line_no, raw in page_lines:
        match = label.match(raw)
        if not match:
            continue
        tail = raw[match.end():]
        pairs = list(_SHARE_PAIR.finditer(tail))
        # The last pair must close the row; do not swallow explanatory dates.
        if len(pairs) != 2 or tail[pairs[-1].end():].strip():
            candidates.append({"page": page, "line": line_no, "raw_text": raw[:500],
                               "reason": "after_change_total_or_percent_not_explicit"})
            continue
        count = int(pairs[-1].group(1).replace(",", ""))
        candidates.append({"page": page, "line": line_no, "raw_text": raw[:500],
                           "value": str(count), "basis": "reported_after_change_total_shares"})
    if len(candidates) != 1 or "value" not in candidates[0]:
        return {"status": "unknown", "reason": "after_change_total_share_row_missing_or_ambiguous",
                "candidates": candidates[:5]}
    chosen = candidates[0]
    return {"status": "source_candidate", "unit": "shares", "value": chosen["value"],
            "basis": "股份总数 row final count before 100% in 本次变动后 column",
            "report_year_context": report_year,
            "evidence": {key: chosen[key] for key in ("page", "line", "raw_text")}}


def validate_source_identity(target, prepared):
    source = prepared.get("source", {})
    identity = source.get("source_identity", {})
    original = target["original_pdf"]
    checks = identity.get("checks", {})
    required_true = ("status_qualified", "publisher_code_matches", "bytes_match", "sha256_matches", "pdf_header")
    if (source.get("publisher_code") != target["code"] or
            source.get("announcement_id") != target["announcement_id"] or
            source.get("report_year_from_title") != target["report_year"] or
            source.get("announcement_date_asia_shanghai") != target["publication_date"] or
            identity.get("path") != original["path"] or
            identity.get("bytes") != original["bytes"] or
            identity.get("sha256") != original["sha256"] or
            any(checks.get(key) is not True for key in required_true)):
        raise ValueError(f"prepared/PDF identity mismatch for {target['code']} {target['report_year']}")
    tables = (prepared.get("financial_parser_result") or {}).get("tables") or {}
    assets = tables.get("assets")
    if not isinstance(assets, dict):
        raise ValueError("prepared financial parser assets record missing")
    return assets


def _read_selected_pdf_pages(path: Path, page_numbers):
    try:
        import pypdfium2
    except ImportError as exc:
        raise RuntimeError("pypdfium2 unavailable; do not install it in this run") from exc
    pdf = pypdfium2.PdfDocument(str(path))
    selected = {}
    for page_number in sorted(set(page_numbers)):
        if page_number < 1 or page_number > len(pdf):
            raise ValueError(f"bound page {page_number} outside PDF")
        page = pdf[page_number - 1]
        selected[page_number] = page.get_textpage().get_text_range()
    return selected


def _load_bound_target(target):
    pdf_path = Path(target["original_pdf"]["path"])
    prepared_path = Path(target["prepared_text"]["path"])
    if target["original_pdf"].get("verified") is not True or target["prepared_text"].get("verified") is not True or target["prepared_text"].get("identity_status") != "match":
        raise ValueError(f"plan source verification flags are not qualified for {target['report_year']}")
    for path, item in ((pdf_path, target["original_pdf"]), (prepared_path, target["prepared_text"])):
        if not path.is_absolute() or not path.is_file() or sha256_file(path) != item["sha256"]:
            raise ValueError(f"bound input absent or changed: {path}")
    with pdf_path.open("rb") as pdf_stream:
        pdf_header = pdf_stream.read(5)
    if pdf_path.stat().st_size != target["original_pdf"]["bytes"] or pdf_header != b"%PDF-":
        raise ValueError(f"PDF size/header differs from frozen plan: {pdf_path}")
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    assets = validate_source_identity(target, prepared)
    balance_page = int(target["balance_page"])
    share_page = int(target["share_page"])
    balance_numbers = (balance_page - 1, balance_page)
    share_numbers = (max(1, share_page - 1), share_page, share_page + 1)
    balance_pages = _read_selected_pdf_pages(pdf_path, balance_numbers)
    share_pages = _read_selected_pdf_pages(pdf_path, share_numbers)
    return {
        "code": target["code"], "report_year": target["report_year"],
        "announcement_id": target["announcement_id"], "publication_date": target["publication_date"],
        "original_pdf": {"path": str(pdf_path), "sha256": target["original_pdf"]["sha256"],
                         "bytes": target["original_pdf"]["bytes"], "selected_balance_pages": list(balance_numbers),
                         "selected_share_pages": list(share_numbers)},
        "prepared_text": {"path": str(prepared_path), "sha256": target["prepared_text"]["sha256"],
                          "identity_status": "match", "prior_parser_status": assets.get("status"),
                          "prior_parser_reason": assets.get("reason")},
        "parent_attributable_equity_yuan": extract_parent_equity(balance_pages, int(target["report_year"])),
        "legal_total_shares_at_report_end": extract_post_change_total_shares(
            share_pages, int(target["report_year"]), share_page),
        "preserved_unknowns": {
            "other_equity_instruments_balance": "unknown; not presumed zero",
            "treasury_stock": "unknown; blank or dash is not interpreted as zero",
            "share_classes_and_unrestricted_float": "not reconciled across all classes",
            "revision_chain_and_as_known_at_date": "unknown; selected report only",
        },
        "factor_ready": False,
        "qualification": "source_fields_only_not_point_in_time_qualified",
    }


def extract_plan(plan_path: Path):
    plan_path = Path(plan_path).resolve()
    if plan_path != PLAN_PATH.resolve() or not plan_path.is_file() or sha256_file(plan_path) != PLAN_SHA256:
        raise ValueError("frozen reviewed-value-field plan path/SHA mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schema") != PLAN_SCHEMA:
        raise ValueError("reviewed value-field plan schema mismatch")
    targets = plan.get("targets", [])
    if [(t.get("code"), t.get("report_year")) for t in targets] != [
            ("000032", 2013), ("000032", 2018), ("000032", 2023)]:
        raise ValueError("only the three frozen 000032 report targets are accepted")
    # The exact identities and page pairs are already fixed by PLAN_SHA256.
    return {"schema": "reviewed-value-field-source-candidates/1",
            "plan": {"path": str(plan_path), "sha256": sha256_file(plan_path)},
            "status": "source_fields_only_not_point_in_time_qualified",
            "factor_ready": False,
            "field_scope": plan.get("field_scope"),
            "targets": [_load_bound_target(target) for target in targets],
            "limitations": ["其他权益工具余额、库存股、股份类别和受限流通股仍未知。",
                            "修订链及公告时点可得性未核验；本结果不能用于回测或选股。"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON file path; existing files are never overwritten")
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    if out.exists() or not out.parent.is_dir():
        raise SystemExit("output must be a new JSON file in an existing directory")
    result = extract_plan(args.plan.expanduser().resolve())
    with out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "output": str(out),
                      "targets": len(result["targets"]), "factor_ready": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
