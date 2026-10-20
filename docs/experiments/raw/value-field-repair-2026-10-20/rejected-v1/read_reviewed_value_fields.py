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
_DATE = re.compile(r"20\d{2}年12月31日")
_AMOUNT = re.compile(r"(?<![\d.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
_SHARE_TOKEN = re.compile(r"(?<![\w.])[-−+]?\d[\d,]*(?:\.\d+)?%?")


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
    compact = _compact(text)
    current = f"{report_year}年12月31日"
    previous_options = (f"{report_year - 1}年12月31日", f"{report_year}年1月1日")
    current_pos = compact.find(current)
    if current_pos < 0:
        return None
    prior_positions = [compact.find(item) for item in previous_options if compact.find(item) >= 0]
    prior_pos = min(prior_positions) if prior_positions else -1
    if prior_pos <= current_pos:
        return None
    return {"current": current, "comparative": compact[prior_pos:prior_pos + 12]}


def _balance_header(lines, report_year):
    headers = []
    current = f"{report_year}年12月31日"
    previous = f"{report_year - 1}年12月31日"
    prior_open = f"{report_year}年1月1日"
    for page, line_no, raw in lines:
        row = _compact(raw)
        if not (row.startswith("资产") or row.startswith("项目")):
            continue
        dates = _DATE.findall(row)
        if len(dates) >= 2 and dates[0] == current and dates[1] == previous:
            headers.append({"page": page, "line": line_no, "raw_line": raw,
                            "period_order": "current_then_comparative"})
            continue
        pairs = (("期末余额", "年初余额"), ("期末余额", "期初余额"),
                 ("年末余额", "年初余额"), ("年末余额", "期初余额"))
        if any(a in row and b in row and row.index(a) < row.index(b) for a, b in pairs):
            headers.append({"page": page, "line": line_no, "raw_line": raw,
                            "period_order": "current_then_comparative_labels"})
    return headers


def extract_parent_equity(pages, report_year):
    """Return only a uniquely labelled consolidated RMB-yuan equity row."""
    lines = _line_rows(pages)
    text = "\n".join(line for _, _, line in lines)
    compact = _compact(text)
    if "合并资产负债表" not in compact:
        return {"status": "unknown", "reason": "consolidated_balance_heading_missing"}
    if "母公司资产负债表" in compact and "合并资产负债表" not in compact:
        return {"status": "unknown", "reason": "parent_company_statement_only"}
    period = _has_period_evidence(text, report_year)
    if period is None:
        return {"status": "unknown", "reason": "current_and_comparative_report_period_unverified"}
    headers = _balance_header(lines, report_year)
    if len(headers) != 1:
        return {"status": "unknown", "reason": "balance_column_header_missing_or_ambiguous",
                "header_candidates": headers[:5]}
    if headers[0]["period_order"] == "current_then_comparative_labels" and not (
            f"{report_year}年12月31日" in _compact(text) and
            (f"{report_year-1}年12月31日" in _compact(text) or f"{report_year}年1月1日" in _compact(text))):
        return {"status": "unknown", "reason": "label_columns_not_tied_to_fiscal_year"}
    # Require yuan plus RMB evidence on/next to the unit line.
    unit_evidence = []
    for index, (_, _, line) in enumerate(lines):
        if "单位" not in line or "元" not in line or "万元" in line or "百万元" in line:
            continue
        nearby = " ".join(item[2] for item in lines[max(0, index - 1):index + 3])
        if "人民币" in nearby or re.search(r"币种\s*[:：]\s*RMB", nearby, re.I):
            unit_evidence.append({"page": lines[index][0], "line": lines[index][1],
                                  "raw_line": line, "currency_context": nearby[:240]})
    if len(unit_evidence) != 1:
        return {"status": "unknown", "reason": "RMB_yuan_unit_missing_or_ambiguous",
                "unit_candidates": unit_evidence[:5]}
    row_hits = []
    label_pattern = re.compile(r"^归属于母公司(?:所有者权益|股东权益)合计")
    raw_label_pattern = re.compile(r"^归属于\s*母公司\s*(?:所有者权益|股东权益)\s*合计")
    for index, (page, line_no, raw) in enumerate(lines):
        normalized = _compact(raw)
        match = label_pattern.match(normalized)
        if not match:
            continue
        joined = raw
        # PDF text sometimes moves the two amount cells to following text lines.
        for next_row in lines[index + 1:index + 4]:
            if label_pattern.match(_compact(next_row[2])) or re.match(r"^(?:所有者权益|负债和所有者权益)", _compact(next_row[2])):
                break
            if next_row[0] > page + 1:
                break
            joined += " " + next_row[2]
        label = raw_label_pattern.match(joined)
        if label is None:
            continue
        tail = joined[label.end():]
        values = _AMOUNT.findall(tail)
        row_hits.append({"page": page, "line": line_no, "raw_text": joined[:600],
                         "values": values[:4], "value": values[0] if len(values) >= 2 else None})
    valid = [row for row in row_hits if row["value"] is not None]
    if len(row_hits) != 1 or len(valid) != 1:
        return {"status": "unknown", "reason": "parent_equity_row_blank_or_ambiguous",
                "candidates": row_hits[:5], "period_evidence": period,
                "header_evidence": headers[0], "unit_evidence": unit_evidence[0]}
    chosen = valid[0]
    return {"status": "source_candidate", "unit": "RMB_yuan", "value": chosen["value"],
            "evidence": {key: chosen[key] for key in ("page", "line", "raw_text")},
            "header_evidence": headers[0], "period_evidence": period,
            "unit_evidence": unit_evidence[0], "comparative_value_not_selected": chosen["values"][1]}


def extract_post_change_total_shares(pages, report_year, share_page):
    """Read the explicitly reported after-change total-share row, never capital."""
    lines = _line_rows(pages)
    page_lines = [(p, n, text) for p, n, text in lines if p == share_page]
    all_compact = _compact("\n".join(text for _, _, text in lines))
    has_before_after = "本次变动前" in all_compact and "本次变动后" in all_compact
    has_report_end = "期末股份总数" in all_compact or "报告期末股份总数" in all_compact
    if not (has_before_after or has_report_end):
        return {"status": "unknown", "reason": "after_change_or_report_end_share_table_header_missing"}
    candidates = []
    label_pattern = re.compile(r"^(?:股份总数|总股本)(?=$|[\d,\s:：])")
    for index, (page, line_no, raw) in enumerate(page_lines):
        if "普通股股东总数" in _compact(raw) or not label_pattern.match(_compact(raw)):
            continue
        joined = raw
        for _, _, next_line in page_lines[index + 1:index + 4]:
            nxt = _compact(next_line)
            if label_pattern.match(nxt) or nxt.startswith(("其中", "国家股", "国有法人股", "境内上市")):
                break
            joined += " " + next_line
        tokens = _SHARE_TOKEN.findall(joined)
        if not tokens or not tokens[-1].endswith("%") or len(tokens) < 2:
            candidates.append({"page": page, "line": line_no, "raw_text": joined[:500],
                               "reason": "after_change_total_or_percent_not_explicit"})
            continue
        raw_count = tokens[-2].replace(",", "").replace("−", "-").replace("+", "")
        try:
            number = float(raw_count)
        except ValueError:
            number = -1
        if number < 0 or not number.is_integer():
            candidates.append({"page": page, "line": line_no, "raw_text": joined[:500],
                               "reason": "after_change_share_count_not_integer"})
            continue
        candidates.append({"page": page, "line": line_no, "raw_text": joined[:500],
                           "value": str(int(number)), "basis": "reported_after_change_total_shares"})
    valid = [item for item in candidates if "value" in item]
    if len(valid) != 1:
        return {"status": "unknown", "reason": "after_change_total_share_row_missing_or_ambiguous",
                "candidates": candidates[:5]}
    return {"status": "source_candidate", "unit": "shares", "value": valid[0]["value"],
            "basis": "股份总数 row, final post-change quantity before its percentage; not reconciled to accounting capital",
            "report_year_context": report_year,
            "evidence": {key: valid[0][key] for key in ("page", "line", "raw_text")}}


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
    expected = {
        2013: ("63941824", "2014-04-29", "3208731ff190185af0f52dab45e096d1f296793c475fe4516320fe35d936351d", "059f395fa6ca5e2591a7454cfe20f0fe97632fe4b1af054c1a407e980f9ad904", 68, 37),
        2018: ("1206089248", "2019-04-25", "42f230f9e67d8842957796d2e855fff0f7ba1968a7884ec34af833f81e697803", "5b4598e8fe4ec9d0941c2bf8cf64a111bd334665eee9fab1befb7a5224d2a83e", 92, 53),
        2023: ("1219652709", "2024-04-18", "854095919c8f93f9f255efcd1bdd960737291712245744459b3abfa294f9b89a", "f57e0e875866b48e73c75c129d03d452816e96538e74bcb95d54aa02860a56ee", 136, 118),
    }
    for target in targets:
        ann_id, pub_date, pdf_sha, prepared_sha, balance_page, share_page = expected[target["report_year"]]
        if (target.get("announcement_id") != ann_id or target.get("publication_date") != pub_date or
                target.get("original_pdf", {}).get("sha256") != pdf_sha or
                target.get("prepared_text", {}).get("sha256") != prepared_sha or
                target.get("balance_page") != balance_page or target.get("share_page") != share_page):
            raise ValueError(f"frozen source identity/pages differ for report year {target['report_year']}")
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
