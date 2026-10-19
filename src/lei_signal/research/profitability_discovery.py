"""Conservative extraction of original consolidated annual-statement amounts.

This module extracts evidence and eligibility only. It never chooses a filing
version, fetches data, scores stocks, or treats OCR/ambiguous columns as facts.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pypdfium2

TABLES = {"assets": "资产负债表", "profit": "利润表", "cash": "现金流量表"}
HEAD = re.compile(r"^(?:[一二三四五六七八九十\d]+[、．.])?\s*(合并|母公司)(资产负债表|利润表|现金流量表)\s*$")
NUM = re.compile(r"(?<![\d.])[-−－]?\d[\d,]*(?:\.\d{1,2})?(?![\d.])")
MONEY_TOKEN = re.compile(
    r"(?<![\d.])(?:[（(]\s*[-−－]?\d[\d,]*(?:\.\d{1,2})?\s*[）)]|"
    r"[-−－]?\d[\d,]*(?:\.\d{1,2})?)(?![\d.])")
YEAR = re.compile(r"(20\d{2})\s*年")
UNIT = re.compile(r"单位\s*[:：]\s*(百万元|万元|元)(?![\w])")
LABELS = {
    "revenue": re.compile(r"^(?:[一二三四五六七八九十]+[、．.]\s*|其中\s*[:：]\s*)?营业收入(?=\s|\d|$)"),
    "cost": re.compile(r"^(?:减\s*[:：]\s*|其中\s*[:：]\s*)?营业成本(?=\s|\d|$)"),
    "assets": re.compile(r"^资产总计(?=\s|\d|$)"),
    "cfo": re.compile(r"^经营活动产生的现金\s*流\s*量\s*净额(?=\s|[-−－\d]|$)"),
}
FIELD_TABLE = {"revenue": "profit", "cost": "profit", "assets": "assets", "cfo": "cash"}
SCALE = {"元": Decimal(1), "万元": Decimal(10000), "百万元": Decimal(1000000)}


def _unknown(reason, candidates=()):
    return {"status": "unknown", "value_yuan": None, "raw_value": None,
            "raw_label": None, "raw_line": None, "page": None, "unit": None,
            "reason": reason, "candidates": list(candidates)}


def _rows(pages):
    return [(page_no, line_no, line.strip())
            for page_no, page in enumerate(pages, 1)
            for line_no, line in enumerate(page.splitlines(), 1) if line.strip()]


def _sections(rows):
    headings = [(i, match.group(1), match.group(2))
                for i, (_, _, line) in enumerate(rows)
                if (match := HEAD.fullmatch(line))]
    result = {name: [] for name in TABLES}
    for n, (start, owner, table) in enumerate(headings):
        if owner == "合并":
            kind = next(key for key, title in TABLES.items() if title == table)
            end = headings[n + 1][0] if n + 1 < len(headings) else len(rows)
            result[kind].append((start, end))
    return result


def _context(rows, start, end, pages):
    page_no = rows[start][0]
    # The title may occur after the preceding table on the same physical page.
    nearby = [line for p, _, line in rows[start:min(end, start + 16)] if p <= page_no + 1]
    page_header = pages[page_no - 1].splitlines()[:2]
    return nearby, page_header


def _qualification(rows, start, end, pages, kind, report_year):
    nearby, page_header = _context(rows, start, end, pages)
    header = next((line for line in nearby[1:] if line.startswith("项目") and
                   ("期末余额" in line or "本期" in line or "年度" in line or "年12" in line
                    or "年 12" in line)), None)
    evidence = {"heading_page": rows[start][0], "heading": rows[start][2],
                "header": header, "unit_line": None, "currency_line": None,
                "currency_page": None, "period_line": None}
    if header is None:
        return "current_column_header_missing", evidence, None
    compact = re.sub(r"\s+", "", header)
    if "调整" in compact or "重述" in compact or "前" in compact and "后" in compact:
        return "adjusted_or_multiple_columns", evidence, None
    dates = re.findall(r"20\d{2}(?:年(?:\d{1,2}月\d{1,2}日|度))?", compact)
    if len(dates) > 2:
        return "adjusted_or_multiple_columns", evidence, None
    if kind == "assets":
        current = "期末余额" in compact and "期初余额" in compact or (
            len(dates) == 2 and dates[0].startswith(str(report_year)) and
            dates[1].startswith(str(report_year - 1)))
    else:
        current = "本期发生额" in compact and ("上期发生额" in compact or "上期金额发生额" in compact)
        current = current or (len(dates) == 2 and dates[0].startswith(str(report_year))
                              and dates[1].startswith(str(report_year - 1)))
    if not current:
        return "current_and_comparative_columns_not_verified", evidence, None
    unit_lines = [line for line in nearby[:12] if "单位" in line and
                  ("币种" in line or "元" in line)]
    units = [(line, UNIT.search(line)) for line in unit_lines]
    units = [(line, found.group(1)) for line, found in units if found]
    if len({unit for _, unit in units}) != 1:
        return "unit_missing_or_conflicting", evidence, None
    evidence["unit_line"] = units[0][0]
    if any(re.search(r"(?:美元|港元|欧元|USD|HKD|EUR)", line, re.I) for line in unit_lines):
        return "multiple_or_non_rmb_currencies", evidence, None
    currency_marks = [(line, re.search(r"币种\s*[:：]\s*([^\s，,;；。]+)", line))
                      for line in unit_lines if "币种" in line]
    if currency_marks:
        if any(mark is None or mark.group(1) not in ("人民币", "RMB")
               for _, mark in currency_marks):
            return "currency_not_verified_as_rmb", evidence, None
        evidence["currency_line"] = currency_marks[0][0]
        evidence["currency_page"] = rows[start][0]
    else:
        # A statement preface, rather than domicile, can establish its currency.
        preface = [(page_no, line) for page_no, page in enumerate(pages[:rows[start][0]], 1)
                   for line in page.splitlines()
                   if re.search(r"(?:财务附注中报表的单位为|财务报表的列报货币为)\s*[:：]?\s*人民币元?", line)]
        if not preface:
            return "currency_not_verified_as_rmb", evidence, None
        evidence["currency_page"], evidence["currency_line"] = preface[-1]
    period_lines = [line for line in nearby[1:12] if YEAR.search(line) and
                    ("月" in line or "年度" in line or "—" in line or "-" in line)]
    explicit = [(line, match) for line in period_lines if
                (match := re.search(r"(20\d{2})\s*年\s*(\d{1,2}\s*月\s*\d{1,2}\s*日|"
                                    r"\d{1,2}\s*[—–-]\s*\d{1,2}\s*月)", line))]
    if explicit:
        evidence["period_line"] = explicit[0][0]
        full_year = (r"12\s*月\s*31\s*日" if kind == "assets" else
                     r"1\s*[—–-]\s*12\s*月")
        if any(int(match.group(1)) != report_year or
               not re.fullmatch(full_year, match.group(2)) for _, match in explicit):
            return "report_period_year_or_duration_mismatch", evidence, None
    elif any(re.search(r"年度报告", line) and re.search(rf"{report_year}\s*年", line)
             for line in page_header):
        evidence["period_line"] = next(line for line in page_header if "年度报告" in line)
    else:
        return "annual_report_period_not_verified", evidence, None
    return None, evidence, units[0][1]


def _money(tail, has_note_column):
    tokens = [match.group().strip() for match in MONEY_TOKEN.finditer(tail)]
    if len(tokens) == 3 and has_note_column and not re.search(r"[,.()（）]", tokens[0]):
        tokens = tokens[1:]  # Statement annotation index, not money.
    if len(tokens) == 2 and has_note_column and not re.search(r"[,.()（）]", tokens[0]):
        return None, "annotation_or_current_amount_ambiguous"
    if len(tokens) != 2:
        return None, "two_amount_columns_not_verified"
    try:
        values = []
        for token in tokens:
            parenthesized = token.startswith(("(", "（")) and token.endswith((")", "）"))
            normalized = token.strip("()（） ").replace(",", "").replace("−", "-").replace("－", "-")
            value = Decimal(normalized)
            values.append(-abs(value) if parenthesized else value)
    except InvalidOperation:
        return None, "invalid_amount"
    return values[0], None


def _field(rows, start, end, key, unit, has_note_column):
    candidates, values = [], []
    for i in range(start + 1, end):
        page, line_no, line = rows[i]
        text = line
        if key == "cfo" and line.startswith("经营活动产生的现金") and not LABELS[key].match(line):
            for next_i in range(i + 1, min(end, i + 4)):
                if rows[next_i][0] > page + 1:
                    break
                text += " " + rows[next_i][2]
                if LABELS[key].match(text):
                    break
        match = LABELS[key].match(text)
        if not match:
            continue
        tail = text[match.end():]
        if len(NUM.findall(tail)) < 2:
            for next_i in range(i + 1, min(end, i + 4)):
                continuation = rows[next_i][2]
                if (re.match(r"^[一二三四五六七八九十]+[、．.]", continuation)
                        or any(label.match(continuation) for label in LABELS.values())):
                    break
                if continuation in text:
                    continue
                if not re.fullmatch(r"[\s\d,.\-−－()（）]+", continuation):
                    break
                text += " " + continuation
                tail += " " + continuation
                if len(NUM.findall(tail)) >= 2:
                    break
        current, reason = _money(tail, has_note_column)
        candidate = {"page": page, "line": line_no, "raw_line": text[:300],
                     "reason": reason}
        candidates.append(candidate)
        if reason is None:
            values.append((current, candidate, match.group()))
    if len(candidates) != 1 or len(values) != 1:
        reason = "field_missing" if not candidates else "field_ambiguous_or_amount_unreadable"
        return _unknown(reason, candidates)
    value, evidence, label = values[0]
    return {"status": "qualified", "value_yuan": str(value * SCALE[unit]),
            "raw_value": str(value), "raw_label": label, "raw_line": evidence["raw_line"],
            "page": evidence["page"], "unit": unit, "reason": None,
            "candidates": candidates}


def _parse_text_pages(pages, report_year):
    rows = _rows(pages)
    sections = _sections(rows)
    fields, tables = {}, {}
    for kind in TABLES:
        group = sections[kind]
        qualified = []
        rejected = []
        for start, end in group:
            reason, evidence, unit = _qualification(rows, start, end, pages, kind, report_year)
            (rejected if reason else qualified).append((start, end, reason, evidence, unit))
        if len(qualified) != 1:
            reason = ("consolidated_table_missing" if not group else
                      "multiple_consolidated_tables" if len(qualified) > 1 else
                      rejected[0][2])
            tables[kind] = {"status": "unknown", "reason": reason,
                            "candidate_pages": [rows[start][0] for start, _ in group],
                            "rejected": [evidence for _, _, _, evidence, _ in rejected]}
            for key, table in FIELD_TABLE.items():
                if table == kind:
                    fields[key] = _unknown(reason, tables[kind]["candidate_pages"])
            continue
        start, end, reason, evidence, unit = qualified[0]
        tables[kind] = {"status": "qualified" if reason is None else "unknown",
                        "reason": reason, **evidence,
                        "rejected_candidates": [e for _, _, _, e, _ in rejected]}
        for key, table in FIELD_TABLE.items():
            if table == kind:
                fields[key] = (_unknown(reason, [evidence]) if reason else
                               _field(rows, start, end, key, unit, "附注" in (evidence["header"] or "")))
    valid_gp = all(fields[key]["status"] == "qualified" for key in ("revenue", "cost", "assets"))
    valid_cfo = all(fields[key]["status"] == "qualified" for key in ("cfo", "assets"))
    if fields["assets"]["status"] == "qualified" and Decimal(fields["assets"]["value_yuan"]) <= 0:
        fields["assets"] = _unknown("nonpositive_assets", fields["assets"]["candidates"])
        valid_gp = valid_cfo = False
    asset = Decimal(fields["assets"]["value_yuan"]) if fields["assets"]["status"] == "qualified" else None
    gp = (Decimal(fields["revenue"]["value_yuan"]) - Decimal(fields["cost"]["value_yuan"])) / asset if valid_gp else None
    cfo = Decimal(fields["cfo"]["value_yuan"]) / asset if valid_cfo else None
    return {"status": "qualified" if valid_gp else "unknown", "tables": tables,
            "fields": fields,
            "gross_profit_over_assets": {"status": "qualified" if valid_gp else "unknown",
                                         "value": str(gp) if gp is not None else None,
                                         "reason": None if valid_gp else "revenue_cost_or_assets_unknown"},
            "cash_flow_over_assets": {"status": "qualified" if valid_cfo else "unknown",
                                      "value": str(cfo) if cfo is not None else None,
                                      "reason": None if valid_cfo else "cash_flow_or_assets_unknown"}}


def parse_annual_pdf(path, report_year, code, announcement_id, publication_date):
    """Return serializable evidence; caller must qualify publication/version timing."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {"code": str(code), "report_year": int(report_year),
              "announcement_id": str(announcement_id), "publication_date": str(publication_date),
              "source_path": str(path), "source_sha256": digest, "page_count": None,
              "text_extractable_pages": 0}
    try:
        pdf = pypdfium2.PdfDocument(path)
        try:
            pages = []
            for i in range(len(pdf)):
                page = pdf[i]
                try:
                    text_page = page.get_textpage()
                    try:
                        pages.append(text_page.get_text_range())
                    finally:
                        text_page.close()
                finally:
                    page.close()
        finally:
            pdf.close()
        result["page_count"] = len(pages)
        result["text_extractable_pages"] = sum(bool(page.strip()) for page in pages)
        result.update(_parse_text_pages(pages, int(report_year)))
    except Exception as exc:
        result.update({"status": "unknown", "reason": "pdf_extraction_error",
                       "error": f"{type(exc).__name__}: {exc}"})
    return result
