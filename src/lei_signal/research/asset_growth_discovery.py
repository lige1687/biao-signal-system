"""Offline, source-only qualification of reported annual asset growth.

The output contains no price, future return, or portfolio outcome. Unknown
source states remain rows and never become zero growth.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import plistlib
import re
import subprocess
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from lei_signal.research import profitability_discovery as source_parser

MONEY_TOKEN = source_parser.MONEY_TOKEN
SCALE = source_parser.SCALE

SCHEMA = "asset-growth-source-run/1"
COLUMNS = ("formation_year", "decision_date", "code", "industry", "status",
           "growth", "reason", "current_year", "prior_year", "current_ids",
           "prior_ids", "current_publication_date", "prior_publication_date",
           "notice_status")


def sha(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            digest.update(part)
    return digest.hexdigest()


def bound_json(binding: dict) -> object:
    path = Path(binding["path"])
    if sha(path) != binding["sha256"]:
        raise ValueError(f"bound sha256 mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_bound(binding: dict) -> None:
    if sha(binding["path"]) != binding["sha256"]:
        raise ValueError(f"bound sha256 mismatch: {binding['path']}")


def _decimal(value: object) -> Decimal | None:
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _tokens(raw_line: str, raw_label: str, note_column: bool) -> tuple[list[Decimal] | None, str | None]:
    if not raw_line.startswith(raw_label):
        return None, "asset_line_label_mismatch"
    tail = raw_line[len(raw_label):]
    tokens = [match.group().strip() for match in MONEY_TOKEN.finditer(tail)]
    if len(tokens) == 3 and note_column and not re.search(r"[,.()（）]", tokens[0]):
        tokens = tokens[1:]
    if len(tokens) != 2:
        return None, "two_asset_amounts_not_verified"
    values = []
    for token in tokens:
        parenthesized = token.startswith(("(", "（")) and token.endswith((")", "）"))
        amount = _decimal(token.strip("()（） ").replace(",", "").replace("−", "-").replace("－", "-"))
        if amount is None:
            return None, "invalid_asset_amount"
        values.append(-abs(amount) if parenthesized else amount)
    return values, None


def annual_assets(document: dict, expected: dict, decision: str) -> dict:
    """Return a qualified current/comparative pair from one exact full annual."""
    source = document.get("source") or {}
    parsed = document.get("financial_parser_result") or {}
    year = expected["year"]
    if (source.get("cohort_code") != expected["code"] or
            str(source.get("announcement_id")) != str(expected["id"]) or
            source.get("report_year_from_title") != year or
            source.get("announcement_date_asia_shanghai") != expected["publication_date"] or
            parsed.get("report_year") != year or
            parsed.get("publication_date") != expected["publication_date"] or
            not expected["publication_date"] < decision):
        return {"status": "unknown", "reason": "document_identity_or_time_unknown"}
    if (document.get("header_evidence", {}).get("document_form") != "suspected_full_text" or
            document.get("header_evidence", {}).get("identity_status") != "match" or
            document.get("annual_candidate_evidence", {}).get("status") != "suspected"):
        return {"status": "unknown", "reason": "full_annual_identity_unknown"}
    table = parsed.get("tables", {}).get("assets", {})
    field = parsed.get("fields", {}).get("assets", {})
    if table.get("status") != "qualified" or field.get("status") != "qualified":
        return {"status": "unknown", "reason": "assets_table_or_field_unknown"}
    unit = field.get("unit")
    if unit not in SCALE or not table.get("currency_rule") or not table.get("period_line"):
        return {"status": "unknown", "reason": "currency_period_or_unit_unknown"}
    header = re.sub(r"\s+", "", str(table.get("header") or ""))
    if any(word in header for word in ("调整", "重述")):
        return {"status": "unknown", "reason": "adjusted_or_multiple_columns"}
    dates = re.findall(r"20\d{2}年\d{1,2}月\d{1,2}日", header)
    explicit = len(dates) == 2
    if len(dates) > 2 or (dates and not explicit):
        return {"status": "unknown", "reason": "annual_column_dates_unknown"}
    if explicit:
        if dates[0] != f"{year}年12月31日" or dates[1] not in (f"{year-1}年12月31日", f"{year}年1月1日"):
            return {"status": "unknown", "reason": "annual_column_order_unknown"}
        comparative_kind = "prior_year_end" if dates[1] == f"{year-1}年12月31日" else "year_start"
    else:
        variants = (("期末余额", "期初余额"), ("年末余额", "年初余额"),
                    ("期末余额", "年初余额"), ("年末余额", "期初余额"))
        matched = [(a, b) for a, b in variants if a in header and b in header and header.index(a) < header.index(b)]
        if not matched:
            return {"status": "unknown", "reason": "annual_column_order_unknown"}
        comparative_kind = "year_start" if "初" in matched[0][1] else "prior_year_end"
    raw_label = str(field.get("raw_label") or "")
    if raw_label != "资产总计" or field.get("page") is None:
        return {"status": "unknown", "reason": "assets_line_unknown"}
    values, reason = _tokens(str(field.get("raw_line") or ""), raw_label,
                             bool(re.search(r"附注|注释", header)))
    if reason:
        return {"status": "unknown", "reason": reason}
    current, comparative = (amount * SCALE[unit] for amount in values)
    frozen = _decimal(field.get("value_yuan"))
    if frozen != current:
        return {"status": "unknown", "reason": "current_assets_do_not_match_frozen_field"}
    if current <= 0 or comparative <= 0:
        return {"status": "unknown", "reason": "nonpositive_asset_pair"}
    gp_fields = parsed.get("fields", {})
    revenue = gp_fields.get("revenue", {})
    cost = gp_fields.get("cost", {})
    gp_readback = None
    if revenue.get("status") == "qualified" and cost.get("status") == "qualified":
        rev, expense = _decimal(revenue.get("value_yuan")), _decimal(cost.get("value_yuan"))
        if rev is not None and expense is not None:
            gp_readback = {"revenue": str(rev), "cost": str(expense),
                           "ratio": str((rev - expense) / current)}
    return {"status": "qualified", "current": str(current), "comparative": str(comparative),
            "comparative_kind": comparative_kind, "unit": unit, "table": table,
            "field": {k: field.get(k) for k in ("raw_line", "raw_label", "page", "unit", "value_yuan")},
            "gp_readback": gp_readback}


def _full_annual(record: dict, code: str, year: int, decision: str) -> bool:
    return (record.get("code") == code and record.get("year") == year and
            record.get("publication_date") is not None and record["publication_date"] < decision and
            _full_annual_title(record))


def _full_annual_title(record: dict) -> bool:
    """Include a failed latest full report, but exclude notices mentioning a report."""
    title = str(record.get("title") or "")
    if (record.get("year") is None or record.get("excluded_doc_kind") is not None or
            "annual" not in record.get("categories", []) or
            not re.search(r"年度报告|年报", title) or
            re.search(r"摘要|英文|审计|意见|问询|半年度|季度|季报|中期|公告|通知|说明", title)):
        return False
    form = (record.get("prepared_binding") or {}).get("document_form")
    return form != "notice"


def _notice_event(record: dict) -> bool:
    categories = record.get("categories", [])
    if record.get("excluded_doc_kind") is not None:
        return False
    if _full_annual_title(record):
        return False  # Revised full reports are versions, not separate notices.
    if "correction" in categories:
        return True
    title = str(record.get("title") or "")
    return ("annual" in categories and record.get("year") is None and
            record.get("excluded_doc_kind") is None and
            bool(re.search(r"年度报告|年报", title)) and
            not bool(re.search(r"摘要|英文|审计|意见|问询|半年度|季度|季报|中期", title)))


def _latest(index: list[dict], code: str, year: int, decision: str) -> tuple[list[dict], str | None]:
    candidates = [r for r in index if _full_annual(r, code, year, decision)]
    if not candidates:
        return [], "no_public_full_annual"
    day = max(r["publication_date"] for r in candidates)
    return [r for r in candidates if r["publication_date"] == day], None


def _load_pair(records: list[dict], decision: str) -> tuple[dict | None, str | None, list[dict]]:
    checked = []
    values = []
    for record in records:
        binding = record.get("prepared_binding") or {}
        pdf = record.get("pdf") or {}
        if (pdf.get("status") != "obtained" or not binding.get("sha256") or not pdf.get("sha256") or
                not pdf.get("source_path") or not binding.get("path") or
                sha(pdf["source_path"]) != pdf["sha256"]):
            checked.append({"id": record["id"], "status": "unknown", "reason": "original_pdf_binding_unknown"})
            return None, "original_pdf_binding_unknown", checked
        doc = bound_json(binding)
        source_identity = (doc.get("source") or {}).get("source_identity") or {}
        if (source_identity.get("sha256") != pdf["sha256"] or
                source_identity.get("path") != pdf["source_path"] or
                binding.get("announcement_id") != record["id"]):
            checked.append({"id": record["id"], "status": "unknown", "reason": "prepared_pdf_binding_mismatch"})
            return None, "prepared_pdf_binding_mismatch", checked
        pair = annual_assets(doc, record, decision)
        checked.append({"id": record["id"], "prepared_path": binding["path"],
                        "prepared_sha256": binding["sha256"], "pdf_sha256": pdf["sha256"], **pair})
        if pair["status"] != "qualified":
            return None, pair["reason"], checked
        values.append((pair["current"], pair["comparative"]))
    if len(set(values)) != 1:
        return None, "same_day_asset_pair_conflict", checked
    return checked[0], None, checked


def notice_decision(event: dict, review: dict | None, current_year: int,
                    current_pub: str, prior_pub: str, current_ids: list[str],
                    prior_ids: list[str], crossreport_equal: bool) -> tuple[str, str]:
    """Return (action, reason). Unknown scope recovery never certifies accounts."""
    day = event.get("publication_date")
    if not day:
        return "block", "notice_publication_unknown"
    if review:
        if (review.get("cohort_code") != event.get("code") or
                str(review.get("announcement_id")) != str(event.get("id")) or
                review.get("publication_date") != day or
                review.get("source_sha256") != event.get("pdf", {}).get("sha256") or
                review.get("controller_accepted") is not True):
            return "block", "notice_review_binding_mismatch"
        if (review.get("disposition") == "unrelated_business" or
                review.get("disposition") == "cleared" and review.get("whole_notice_cleared") is True):
            return "ignore", "whole_notice_cleared"
        fields = review.get("affected_fields")
        if fields is not None and "assets" not in fields:
            return "ignore", "known_fields_exclude_assets"
        years = review.get("affected_years")
        if years is not None and set(years) & {current_year, current_year - 1}:
            if set(map(str, review.get("resolved_by_announcement_ids", []))) & set(current_ids + prior_ids):
                return "ignore", "exact_full_version_resolution"
            return "block", "affected_annual_assets_unresolved"
        if years is not None and max(years) < current_year - 1 and review.get("continuing_scope") == "cleared":
            return "ignore", "known_older_scope_cleared"
        if years is not None and min(years) > current_year:
            return "ignore", "known_future_scope_irrelevant"
        if review.get("continuing_scope") in ("unknown", "extends"):
            return "block", "continuing_scope_unknown_or_extends"
        return "block", "reviewed_notice_scope_unresolved"
    if (crossreport_equal and day < f"{current_year-1}-12-31" and
            day < f"{current_year}-12-31" and day < prior_pub and day < current_pub):
        return "uncertain_recovery", "both_full_reports_after_unreviewed_notice"
    return "block", "unreviewed_notice_within_pair"


def qualify(audit: dict, index: list[dict], review_map: dict, *,
            industry: str = "", load_pair=_load_pair) -> tuple[dict, dict]:
    gp = audit.get("gp") or {}
    year = int(audit["month"][:4])
    result = {"formation_year": year, "decision_date": audit["decision_date"],
              "code": audit["code"], "industry": industry,
              "status": "unknown", "growth": "", "reason": "", "current_year": year - 1,
              "prior_year": year - 2, "current_ids": "", "prior_ids": "",
              "current_publication_date": "", "prior_publication_date": "", "notice_status": ""}
    evidence = {"formation_year": year, "decision_date": audit["decision_date"], "code": audit["code"],
                "gp_audit": gp, "current": [], "prior": [], "notices": []}
    def unknown(reason):
        result["reason"] = reason
        evidence["status"] = "unknown"
        evidence["reason"] = reason
        return result, evidence
    if audit["month"][-2:] != "07" or year not in range(2015, 2026) or not audit["decision_date"].startswith(f"{year}-06"):
        return unknown("formation_date_invalid")
    if gp.get("status") != "qualified" or gp.get("report_year") != year - 1 or gp.get("publication_date", "9999") >= audit["decision_date"]:
        return unknown("inherited_gp_not_qualified")
    current_records, error = _latest(index, audit["code"], year - 1, audit["decision_date"])
    if error:
        return unknown("current_" + error)
    current_ids = sorted(str(r["id"]) for r in current_records)
    result["current_ids"] = "|".join(current_ids)
    result["current_publication_date"] = current_records[0]["publication_date"]
    if current_ids != sorted(map(str, gp.get("announcement_ids", []))) or result["current_publication_date"] != gp["publication_date"]:
        return unknown("current_latest_ids_differ_from_gp_audit")
    current, error, evidence["current"] = load_pair(current_records, audit["decision_date"])
    if error:
        return unknown("current_" + error)
    if _decimal(current["current"]) != _decimal(gp.get("amounts_yuan", {}).get("assets")):
        return unknown("current_assets_differ_from_gp_audit")
    gp_readback = current.get("gp_readback")
    if (not gp_readback or
            any(_decimal(gp_readback[key]) != _decimal(gp.get("amounts_yuan", {}).get(key))
                for key in ("revenue", "cost")) or
            _decimal(gp_readback["ratio"]) != _decimal(gp.get("value"))):
        return unknown("current_gp_readback_differs_from_audit")
    prior_records, error = _latest(index, audit["code"], year - 2, audit["decision_date"])
    if error:
        return unknown("prior_" + error)
    prior_ids = sorted(str(r["id"]) for r in prior_records)
    result["prior_ids"] = "|".join(prior_ids)
    result["prior_publication_date"] = prior_records[0]["publication_date"]
    prior, error, evidence["prior"] = load_pair(prior_records, audit["decision_date"])
    if error:
        return unknown("prior_" + error)
    if _decimal(current["comparative"]) != _decimal(prior["current"]):
        return unknown("unknown_crossreport_mismatch")
    notices = [r for r in index if r.get("code") == audit["code"] and _notice_event(r) and
               (not r.get("publication_date") or r["publication_date"] < audit["decision_date"])]
    recovered = False
    for event in notices:
        key = (event["code"], str(event["id"]))
        action, reason = notice_decision(event, review_map.get(key), year - 1,
                                         result["current_publication_date"], result["prior_publication_date"],
                                         current_ids, prior_ids, True)
        evidence["notices"].append({"id": event["id"], "publication_date": event.get("publication_date"),
                                    "action": action, "reason": reason})
        if action == "block":
            return unknown(reason)
        if action == "uncertain_recovery":
            recovered = True
    result.update(status="qualified", growth=str(_decimal(current["current"]) / _decimal(prior["current"]) - 1),
                  reason="", notice_status="unreviewed_scope_unknown" if recovered else "no_unresolved_notice")
    evidence.update(status="qualified", growth=result["growth"], current_value_yuan=current["current"],
                    prior_value_yuan=prior["current"], crossreport_equal=True,
                    financial_authenticity_certified=False)
    return result, evidence


def run(contract: Path) -> dict:
    spec = json.loads(contract.read_text(encoding="utf-8"))
    if spec.get("schema") != SCHEMA or spec.get("market_effects_allowed") is not False:
        raise ValueError("source-only contract required")
    design = bound_json(spec["design"])
    if design.get("schema") != "asset-growth-source-design/1" or design.get("status") != "frozen_source_qualification_only":
        raise ValueError("source design not frozen")
    bindings = design["source_bindings"]
    audit = bound_json(bindings["audit"])
    index = bound_json(bindings["source_index"])
    panel_path = Path(bindings["panel"]["path"])
    if sha(panel_path) != bindings["panel"]["sha256"]:
        raise ValueError("bound panel sha256 mismatch")
    check_bound(bindings["old_parser"])
    if sha(source_parser.__file__) != bindings["old_parser"]["sha256"]:
        raise ValueError("active money parser differs from frozen parser")
    bound_json(bindings["old_rules"])
    reviews = bound_json(bindings["reviewed_notices"])
    bound_json(bindings["business_review"])
    if not isinstance(audit, list) or not isinstance(index, list) or len(audit) != 79200:
        raise ValueError("frozen source shape changed")
    review_map = {(d["cohort_code"], str(d["announcement_id"])): d
                  for d in reviews.get("decisions", [])}
    industries = {}
    with panel_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["month"].endswith("-07"):
                industries[(row["month"], row["code"])] = row["industry"]
    by_code = defaultdict(list)
    for record in index:
        by_code[record.get("code")].append(record)
    selected = [r for r in audit if r.get("month", "").endswith("-07")]
    axis = Counter(r["month"] for r in selected)
    if (len(selected) != 6600 or len({r["code"] for r in selected}) != 600 or
            len({(r["month"], r["code"]) for r in selected}) != 6600 or
            axis != Counter({f"{year}-07": 600 for year in range(2015, 2026)})):
        raise ValueError("600 by 11 source row axis changed")
    output = spec["output"]
    directory = Path(output["path"])
    mount = Path(output["mount"])
    if (not output.get("external_uuid") or directory.exists() or not directory.parent.is_dir() or
            mount not in directory.parents or directory.parent.stat().st_dev != output["external_device"]):
        raise ValueError("new external output directory required")
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if str(volume.get("VolumeUUID", "")).upper() != output["external_uuid"].upper():
        raise ValueError("external volume identity changed")
    rows, evidence = [], []
    for item in selected:
        key = (item["month"], item["code"])
        if key not in industries:
            raise ValueError("old panel row missing")
        row, detail = qualify(item, by_code[item["code"]], review_map,
                              industry=industries[key])
        rows.append(row)
        evidence.append(detail)
    directory.mkdir(mode=0o700)
    if directory.stat().st_dev != output["external_device"]:
        raise ValueError("external device changed")
    with (directory / "panel.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader(); writer.writerows(rows)
    coverage = {"schema": "asset-growth-source-coverage/1", "rows": len(rows),
                "qualified": sum(r["status"] == "qualified" for r in rows),
                "reason_counts": dict(Counter(r["reason"] for r in rows if r["reason"])),
                "by_year": {str(y): dict(Counter(r["status"] for r in rows if r["formation_year"] == y))
                            for y in range(2015, 2026)},
                "by_industry": {k: dict(Counter(r["status"] for r in rows if r["industry"] == k))
                                for k in sorted({r["industry"] for r in rows})},
                "market_effects_run": False}
    for name, data in (("source-pairs.json", evidence), ("coverage.json", coverage)):
        with (directory / name).open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    manifest = {"schema": "asset-growth-source-result/1", "contract_path": str(contract),
                "contract_sha256": sha(contract), "design_sha256": spec["design"]["sha256"],
                "inputs": bindings, "rows": len(rows), "market_effects_run": False,
                "outputs": {name: sha(directory / name) for name in ("panel.csv", "source-pairs.json", "coverage.json")}}
    with (directory / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2); stream.write("\n")
    return manifest


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--contract", required=True, type=Path)
    args = cli.parse_args()
    print(json.dumps(run(args.contract), ensure_ascii=False))


if __name__ == "__main__":
    main()
