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
HEAD = re.compile(
    r"^(?:(?:[一二三四五六七八九十\d]+[、．.]|[（(][一二三四五六七八九十\d]+[）)])\s*)?"
    r"(合\s*并|母\s*公\s*司)\s*(资\s*产\s*负\s*债\s*表|利\s*润\s*表|现\s*金\s*流\s*量\s*表)\s*$")
NUM = re.compile(r"(?<![\d.])[-−－]?\d[\d,]*(?:\.\d{1,2})?(?![\d.])")
MONEY_TOKEN = re.compile(
    r"(?<![\d.])(?:[（(]\s*[-−－]?\d[\d,]*(?:\.\d{1,2})?\s*[）)]|"
    r"[-−－]?\d[\d,]*(?:\.\d{1,2})?)(?![\d.])")
YEAR = re.compile(r"(20\d{2})\s*年")
UNIT = re.compile(r"单位\s*[:：]\s*(?:人民币\s*)?(百万元|万元|元)(?=币种|[^\w]|$)")
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
    headings = [(i, re.sub(r"\s+", "", match.group(1)),
                 re.sub(r"\s+", "", match.group(2)))
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


def _currency_evidence(pages):
    """Only whole-report presentation evidence; never subsidiary currency alone."""
    matches = {"statement": [], "glossary": [], "functional": [], "translation": []}
    for page_no, page in enumerate(pages, 1):
        glossary_scope = next((n + 1 for n in range(max(0, page_no - 3), page_no)
                               if re.search(r"(?m)^\s*释\s*义\s*$|释义项\s*指\s*释义内容", pages[n])), None)
        for line in page.splitlines():
            compact = re.sub(r"\s+", "", line)
            if re.search(r"财务附注中报表的单位为[:：]?人民币元|本财务报表以人民币列示|"
                         r"财务报表的列报货币为[:：]?人民币", compact):
                matches["statement"].append({"page": page_no, "text": line.strip()[:240]})
            if re.search(r"元、万元、亿元指人民币元[、，](?:人民币)?万元[、，](?:人民币)?亿元", compact):
                matches["glossary"].append({"page": page_no, "text": line.strip()[:240]})
            # An explicit front-matter glossary maps the report's unit, even
            # when only 元 or 元/万元 is defined. A subsidiary currency note
            # or an isolated later table cannot supply this report-wide scope.
            if page_no <= 20 and glossary_scope is not None and re.fullmatch(
                    r"元(?:[、，]万元)?(?:[、，]亿元)?指人民币元"
                    r"(?:[、，](?:人民币)?万元)?(?:[、，](?:人民币)?亿元)?", compact):
                matches["glossary"].append({"page": page_no, "text": line.strip()[:240],
                                            "scope_page": glossary_scope})
            if re.search(r"本公司(?:以|采用)人民币为记账本位币", compact):
                matches["functional"].append({"page": page_no, "text": line.strip()[:240]})
            if re.search(r"境外经营的外币财务报表.*折算为人民币报表|"
                         r"在编制合并财务报表时将境外经营的财务报表折算为人民币", compact):
                matches["translation"].append({"page": page_no, "text": line.strip()[:240]})
        # Some issuer presentation sentences end on the next extracted line.
        lines = page.splitlines()
        for first, second in zip(lines, lines[1:]):
            compact = re.sub(r"\s+", "", first + second)
            if "本财务报表以人民币列示" in compact and not any(
                    item["page"] == page_no for item in matches["statement"]):
                matches["statement"].append({"page": page_no,
                                             "text": (first.strip() + " | " + second.strip())[:240]})
        # Presentation policies are often wrapped over several PDF lines.
        # Require the whole-report subject and full affirmative statement.
        compact_page = re.sub(r"\s+", "", page)
        scoped_presentation = ("编制本财务报表时所采用的货币为人民币" in compact_page or
                               "本公司的控股子公司、合营企业、联营企业等" in compact_page)
        for start in range(len(lines) if scoped_presentation else 0):
            window = lines[start:start + 6]
            compact = re.sub(r"\s+", "", "".join(window))
            if re.search(r"本(?:公司|集团)编制本财务报表时所采用的货币为人民币", compact):
                if not any(item["page"] == page_no for item in matches["statement"]):
                    matches["statement"].append({"page": page_no, "text": " | ".join(window)})
            if re.search(r"本公司的控股子公司、合营企业、联营企业等[，,]"
                         r"若采用与本公司不同的记账本位币[，,]需对其外币财务报表折算后[，,]"
                         r"再进行会计核算及合并财务报表的编报", compact):
                if not any(item["page"] == page_no for item in matches["translation"]):
                    matches["translation"].append({"page": page_no, "text": " | ".join(window)})
    all_evidence = (matches["statement"][:2] + matches["glossary"][:2] +
                    matches["functional"][:1] + matches["translation"][:1])
    if matches["statement"]:
        return "statement_presentation", all_evidence
    if matches["functional"] and matches["translation"]:
        return "functional_plus_consolidated_translation", all_evidence
    if matches["glossary"]:
        return "whole_report_rmb_glossary", all_evidence
    return None, all_evidence


def _qualification(rows, start, end, pages, kind, report_year):
    nearby, page_header = _context(rows, start, end, pages)
    header = next((line for line in nearby[1:] if line.startswith("项目") and
                   any(word in line for word in ("期末", "期初", "年末", "年初", "本期", "上期", "年度", "年12", "年 12"))), None)
    evidence = {"heading_page": rows[start][0], "heading": rows[start][2],
                "header": header, "unit_line": None, "currency_line": None,
                "currency_page": None, "currency_rule": None,
                "currency_evidence": [], "period_line": None}
    if header is None:
        return "current_column_header_missing", evidence, None
    compact = re.sub(r"\s+", "", header)
    if "调整" in compact or "重述" in compact or "前" in compact and "后" in compact:
        return "adjusted_or_multiple_columns", evidence, None
    dates = re.findall(r"20\d{2}(?:年(?:\d{1,2}月\d{1,2}日|度))?", compact)
    if len(dates) > 2:
        return "adjusted_or_multiple_columns", evidence, None
    if kind == "assets":
        variants = (("期末余额", "期初余额"), ("年末余额", "年初余额"),
                    ("期末余额", "年初余额"), ("年末余额", "期初余额"))
        current = any(a in compact and b in compact and compact.index(a) < compact.index(b)
                      for a, b in variants)
        reversed_columns = any(a in compact and b in compact and compact.index(a) > compact.index(b)
                               for a, b in variants)
        if len(dates) == 2:
            current_date = f"{report_year}年12月31日"
            prior_dates = {f"{report_year-1}年12月31日", f"{report_year}年1月1日"}
            current = dates[0] == current_date and dates[1] in prior_dates
            reversed_columns = dates[1] == current_date and dates[0] in prior_dates
    else:
        variants = (("本期发生额", "上期发生额"), ("本期发生额", "上期金额发生额"),
                    ("本期金额", "上期金额"))
        current = any(a in compact and b in compact and compact.index(a) < compact.index(b)
                      for a, b in variants)
        reversed_columns = any(a in compact and b in compact and compact.index(a) > compact.index(b)
                               for a, b in variants)
        if len(dates) == 2:
            current = dates[0] == f"{report_year}年度" and dates[1] == f"{report_year-1}年度"
            reversed_columns = dates[1] == f"{report_year}年度" and dates[0] == f"{report_year-1}年度"
    if reversed_columns:
        return "current_column_not_first", evidence, None
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
        evidence["currency_rule"] = "table_currency"
        evidence["currency_evidence"] = [{"page": rows[start][0], "text": currency_marks[0][0]}]
    elif re.search(r"单位\s*[:：]\s*人民币\s*(?:元|万元|百万元)", units[0][0]):
        evidence["currency_line"] = units[0][0]
        evidence["currency_page"] = rows[start][0]
        evidence["currency_rule"] = "table_rmb_unit"
        evidence["currency_evidence"] = [{"page": rows[start][0], "text": units[0][0]}]
    else:
        rule, source = _currency_evidence(pages)
        evidence["currency_rule"] = rule
        evidence["currency_evidence"] = source
        if rule is None:
            return "currency_not_verified_as_rmb", evidence, None
        primary = (next(item for item in source if "记账本位币" in item["text"])
                   if rule == "functional_plus_consolidated_translation" else source[0])
        evidence["currency_page"], evidence["currency_line"] = primary["page"], primary["text"]
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
