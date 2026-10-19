#!/usr/bin/env python3
"""Bounded original-PDF annual book-value source check; no price or outcome data.

Contract ``annual-value-anchor-run/1`` binds plan, storage_plan and this runner
as {path,sha256}; output binds the plan's exact new child, external_device and
external_uuid. The eight targets are fixed by the plan. This is not a B/P factor
adapter: blank equity items, share classes, treasury conventions and prices
remain explicit unknowns until independently qualified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pypdfium2
from lei_signal.research.profitability_discovery import _money, SCALE

SCHEMA = "annual-value-anchor-run/1"
MONEY_LABELS = {
    "parent_attributable_equity": re.compile(r"^归属于\s*母公司\s*所有者权益\s*合计"),
    "other_equity_instruments": re.compile(r"^其他权益工具(?!投资)"),
    "share_capital_yuan": re.compile(r"^(?:实收资本\s*[（(]或股本[）)]|股本)(?=\s|\d|$)"),
    "treasury_stock_yuan": re.compile(r"^减\s*[:：]?\s*库存股"),
}
COUNT = re.compile(r"([\d,]+)(?:\.00)?\s*股")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bound(item, *, decode=True):
    path = Path(item["path"])
    if not path.is_absolute() or not path.is_file() or sha(path) != item["sha256"]:
        raise ValueError(f"bound source absent or changed: {path}")
    return path, json.loads(path.read_text(encoding="utf-8")) if decode else None


def _unknown(reason, candidates=()):
    return {"status": "unknown", "reason": reason, "value": None,
            "evidence": None, "candidates": list(candidates)[:8]}


def _pages(pdf_path):
    pdf = pypdfium2.PdfDocument(str(pdf_path))
    return [page.get_textpage().get_text_range() for page in pdf]


def _rows(pages):
    return [(page, line_no, line.strip()) for page, text in enumerate(pages, 1)
            for line_no, line in enumerate(text.splitlines(), 1) if line.strip()]


def _balance_context(pages, year, preferred_page=None):
    heading = []
    for page, text in enumerate(pages, 1):
        for line in text.splitlines():
            if re.fullmatch(r"(?:[一二三四五六七八九十\d]+[、．.]\s*)?合\s*并\s*资\s*产\s*负\s*债\s*表", line.strip()):
                heading.append(page)
    if preferred_page is not None:
        heading = [p for p in heading if p == preferred_page]
    if len(set(heading)) != 1:
        return None, "consolidated_balance_heading_missing_or_ambiguous"
    page = heading[0]
    window = "\n".join(pages[page - 1: min(page + 1, len(pages))])
    year_text = re.search(rf"{year}\s*年\s*12\s*月\s*31\s*日", window)
    unit_match = re.search(r"单位\s*[:：]\s*(?:人民币\s*)?(百万元|万元|元)", window)
    if year_text is None or unit_match is None:
        return None, "current_fiscal_year_or_unit_not_verified"
    unit = unit_match.group(1)
    # A report-specific RMB unit or a qualified prepared parser's evidence is
    # checked by the caller. An isolated subsidiary table is never accepted.
    return {"heading_page": page, "year_evidence": year_text.group(),
            "unit": unit, "unit_evidence": unit_match.group(),
            "currency_in_table": bool(re.search(r"单位\s*[:：].{0,18}币种\s*[:：]\s*人民币", window))}, None


def _table_field(rows, heading_page, name, unit):
    pattern = MONEY_LABELS[name]
    start = next((i for i, (page, _, text) in enumerate(rows)
                  if page == heading_page and "合并资产负债表" in re.sub(r"\s+", "", text)), None)
    if start is None:
        return _unknown("heading_not_located_in_rows")
    candidates = []
    for i in range(start + 1, len(rows)):
        page, line_no, text = rows[i]
        if page > heading_page + 3 or re.fullmatch(r"母\s*公\s*司\s*资\s*产\s*负\s*债\s*表|合\s*并\s*利\s*润\s*表", text):
            break
        if name == "parent_attributable_equity" and text.startswith("归属于母公司所有者权益"):
            pass  # 合计 and amounts may occupy the next two extracted lines.
        elif not pattern.match(text):
            continue
        joined = text
        # Some PDF text puts 合计 and the two amount columns on following lines.
        for j in range(i + 1, min(i + (3 if name == "parent_attributable_equity" else 1), len(rows))):
            current_match = pattern.match(joined)
            if current_match and len(re.findall(r"[-−－]?\d[\d,]*(?:\.\d+)?", joined[current_match.end():])) >= 2:
                break
            if rows[j][0] > page + 1:
                break
            joined += " " + rows[j][2]
        match = pattern.match(joined)
        if not match:
            candidates.append({"page": page, "line": line_no, "raw_line": joined[:300],
                               "reason": "split_label_not_verified"})
            continue
        current, reason = _money(joined[match.end():], has_note_column=True)
        candidates.append({"page": page, "line": line_no, "raw_line": joined[:300], "reason": reason})
        if reason is None:
            candidates[-1]["value"] = str(current * SCALE[unit])
    valid = [item for item in candidates if "value" in item]
    if len(candidates) != 1 or len(valid) != 1:
        return _unknown("blank_or_ambiguous_statement_field", candidates)
    item = valid[0]
    return {"status": "qualified", "reason": None, "value": item["value"],
            "unit": "RMB_yuan", "evidence": {k: item[k] for k in ("page", "line", "raw_line")},
            "candidates": candidates}


def _share_evidence(rows, capital):
    candidates = []
    for i, (page, line_no, text) in enumerate(rows):
        joined = " ".join(r[2] for r in rows[i:min(i + 3, len(rows))] if r[0] <= page + 1)
        compact = re.sub(r"\s+", "", joined)
        if not any(word in compact for word in ("股份总数", "总股本")) or "普通股股东总数" in compact:
            continue
        for match in COUNT.finditer(joined):
            value = int(match.group(1).replace(",", ""))
            candidates.append({"value_shares": value, "page": page, "line": line_no,
                               "raw_line": joined[:260], "proposal": "拟" in joined or "建议" in joined})
    if capital["status"] != "qualified":
        return _unknown("share_capital_amount_unqualified", candidates)
    # This equality selects an independently *stated count in 股*. It never
    # converts share-capital RMB into a share count.
    amount = Decimal(capital["value"])
    matches = [item for item in candidates if not item["proposal"] and Decimal(item["value_shares"]) == amount]
    if not matches:
        return _unknown("no_explicit_year_end_share_count_reconciled", candidates)
    chosen = matches[0]
    return {"status": "candidate_explicit_shares", "reason": "ordinary_and_year_end_context_requires_review",
            "value": str(chosen["value_shares"]), "unit": "shares_not_RMB",
            "evidence": {k: chosen[k] for k in ("page", "line", "raw_line")}, "candidates": candidates[:8]}


def _share_classes(rows):
    lines = [(p, n, text) for p, n, text in rows if p <= 120 and
             (re.search(r"(?:A|Ａ)\s*股", text) or re.search(r"(?:H|Ｈ|B|Ｂ)\s*股", text))]
    a = [r for r in lines if re.search(r"(?:A|Ａ)\s*股", r[2])]
    other = [r for r in lines if re.search(r"(?:H|Ｈ|B|Ｂ)\s*股", r[2])]
    status = "multi_price_classes" if a and other else "single_price_not_proven"
    return {"status": status, "evidence": [{"page": p, "line": n, "raw_line": s[:220]}
                                            for p, n, s in (a[:2] + other[:2])]}


def extract_pages(pages, year, *, prepared_table=None):
    preferred = prepared_table.get("heading_page") if prepared_table else None
    context, reason = _balance_context(pages, year, preferred)
    if reason:
        return {"status": "unknown", "reason": reason, "table": None, "fields": {}}
    if not context["currency_in_table"] and not (prepared_table and prepared_table.get("status") == "qualified"):
        return {"status": "unknown", "reason": "RMB_consolidated_table_currency_unverified", "table": context, "fields": {}}
    rows = _rows(pages)
    fields = {name: _table_field(rows, context["heading_page"], name, context["unit"])
              for name in MONEY_LABELS}
    fields["ordinary_shares_report_end"] = _share_evidence(rows, fields["share_capital_yuan"])
    classes = _share_classes(rows)
    equity = fields["parent_attributable_equity"]
    other = fields["other_equity_instruments"]
    ordinary = (str(Decimal(equity["value"]) - Decimal(other["value"]))
                if equity["status"] == other["status"] == "qualified" else None)
    return {"status": "source_fields_partial", "reason": None, "table": context,
            "fields": fields, "share_classes": classes,
            "ordinary_equity_yuan": ordinary,
            "annual_bp_ready": False,
            "blocking_reasons": [reason for reason, condition in (
                ("other_equity_balance_unknown", other["status"] != "qualified"),
                ("ordinary_share_count_not_final", fields["ordinary_shares_report_end"]["status"] != "qualified"),
                ("multi_price_class_requires_all_class_quotes", classes["status"] == "multi_price_classes"),
                ("share_class_or_treasury_convention_unresolved", True),
                ("same_fiscal_year_end_unadjusted_prices_not_in_this_stage", True)) if condition]}


def _guard_output(spec, plan, storage, out):
    mount = Path(storage["external_mount"])
    parent = Path(storage["output"])
    out = out.resolve()
    if (str(out) != plan["output_directory"] or str(out) != spec["output"]["path"] or
            out.parent != parent or out.exists() or not parent.is_dir() or
            not os.path.ismount(mount) or parent.stat().st_dev != storage["external_device"] or
            spec["output"]["external_device"] != storage["external_device"] or
            spec["output"]["external_uuid"] != storage["external_uuid"] or
            shutil.disk_usage(mount).free < storage["external_reserve_bytes"]):
        raise ValueError("external create-only path/device/capacity preflight failed")
    info = plistlib.loads(subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)],
                                    capture_output=True, check=True, timeout=10).stdout)
    if info.get("VolumeUUID") != storage["external_uuid"]:
        raise ValueError("external volume UUID differs")
    return out


def run(contract_path, out_path):
    contract_path = Path(contract_path).resolve()
    spec = json.loads(contract_path.read_text(encoding="utf-8"))
    if spec.get("schema") != SCHEMA or set(spec.get("inputs", {})) != {"plan", "storage_plan", "runner"}:
        raise ValueError("contract schema/input set differs")
    plan_path, plan = bound(spec["inputs"]["plan"])
    _, storage = bound(spec["inputs"]["storage_plan"])
    runner_path, _ = bound(spec["inputs"]["runner"], decode=False)
    if runner_path.resolve() != Path(__file__).resolve() or plan.get("schema") != "annual-value-source-qualification/1":
        raise ValueError("runner or plan identity differs")
    targets = plan["targets"]
    if len(targets) != 8 or len({(t["code"], t["report_year"]) for t in targets}) != 8:
        raise ValueError("eight frozen target identities required")
    out = _guard_output(spec, plan, storage, Path(out_path))
    results = []
    for target in targets:
        identity = {"code": target["code"], "report_year": target["report_year"],
                    "publication_date": target.get("publication_date"), "plan_status": target["status"]}
        if target["status"] == "no_qualified_consolidated_balance":
            results.append({**identity, "status": "unknown", "reason": target["status"], "fields": {}})
            continue
        pdf_path, _ = bound(target["original"], decode=False)
        prepared = None
        if "prepared_record" in target:
            _, prepared = bound(target["prepared_record"])
            source = prepared.get("source", {})
            if (source.get("publisher_code") != target["code"] or
                    source.get("report_year_from_title") != target["report_year"] or
                    source.get("source_identity", {}).get("sha256") != target["original"]["sha256"]):
                raise ValueError("prepared source identity differs from frozen target")
            prepared = (prepared.get("financial_parser_result") or {}).get("tables", {}).get("assets")
        result = extract_pages(_pages(pdf_path), target["report_year"], prepared_table=prepared)
        results.append({**identity, "original": {"path": str(pdf_path), "sha256": target["original"]["sha256"]},
                        "prepared_record_sha256": target.get("prepared_record", {}).get("sha256"), **result})
    out.mkdir(mode=0o700)
    payload = json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with (out / "anchors.json").open("x", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush(); os.fsync(stream.fileno())
    manifest = {"schema": "annual-value-anchor-result/1", "status": "source_only_partial",
                "contract": {"path": str(contract_path), "sha256": sha(contract_path)},
                "inputs": spec["inputs"], "targets": len(results),
                "outputs": {"anchors.json": {"sha256": sha(out / "anchors.json"), "bytes": (out / "anchors.json").stat().st_size}},
                "no_price_or_future_return_read": True, "annual_bp_effects_run": False}
    with (out / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2); stream.write("\n")
        stream.flush(); os.fsync(stream.fileno())
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.contract, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
