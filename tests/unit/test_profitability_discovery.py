"""Semantic counterexamples for original annual-statement extraction."""

from decimal import Decimal
import importlib.util
from pathlib import Path

from lei_signal.research.profitability_discovery import HEAD, _parse_text_pages, parse_annual_pdf


def _pages(*, unit="元", asset="100.00", revenue="40.00", cost="10.00",
           cfo="-5.00", profit_header="项目 附注 本期发生额 上期发生额",
           asset_header="项目 期末余额 期初余额", profit_year=2014):
    return [f"""2014 年年度报告
合并资产负债表
2014 年 12 月 31 日
单位：{unit} 币种：人民币
{asset_header}
资产总计 {asset} 90.00
母公司资产负债表
2014 年 12 月 31 日
单位：元 币种：人民币
项目 期末余额 期初余额
资产总计 9999.00 8888.00
合并利润表
{profit_year} 年 1—12 月
单位：{unit} 币种：人民币
{profit_header}
一、营业总收入 80.00 70.00
其中：营业收入 32 {revenue} 30.00
二、营业总成本 60.00 50.00
其中：营业成本 32 {cost} 8.00
母公司利润表
2014 年 1—12 月
单位：元 币种：人民币
项目 本期发生额 上期发生额
营业收入 5000.00 4000.00
营业成本 1000.00 800.00
合并现金流量表
2014 年 1—12 月
单位：{unit} 币种：人民币
项目 本期发生额 上期发生额
经营活动产生的现金流
量净额
{cfo} 2.00
母公司现金流量表
2014 年 1—12 月
单位：元 币种：人民币
项目 本期发生额 上期发生额
经营活动产生的现金流量净额 700.00 600.00"""]


def test_consolidated_current_revenue_cost_and_split_cash_label():
    result = _parse_text_pages(_pages(), 2014)
    assert result["status"] == "qualified"
    assert {key: result["fields"][key]["value_yuan"] for key in
            ("assets", "revenue", "cost", "cfo")} == {
        "assets": "100.00", "revenue": "40.00", "cost": "10.00", "cfo": "-5.00"}
    assert Decimal(result["gross_profit_over_assets"]["value"]) == Decimal("0.3")
    assert Decimal(result["cash_flow_over_assets"]["value"]) == Decimal("-0.05")
    assert "营业总收入" not in result["fields"]["revenue"]["raw_line"]
    assert "32" in result["fields"]["revenue"]["raw_line"]


def test_unit_conversion_zero_and_negative_are_values():
    result = _parse_text_pages(_pages(unit="万元", revenue="0.00", cost="-2.00", cfo="0.00"), 2014)
    assert result["fields"]["revenue"]["value_yuan"] == "0.00"
    assert result["fields"]["cost"]["value_yuan"] == "-20000.00"
    assert result["fields"]["assets"]["value_yuan"] == "1000000.00"
    assert result["fields"]["cfo"]["value_yuan"] == "0.00"


def test_asset_next_page_and_cash_label_next_page():
    first, rest = _pages()[0].split("资产总计 100.00 90.00", 1)
    middle, last = rest.split("量净额\n-5.00 2.00", 1)
    result = _parse_text_pages(
        [first, "2014 年年度报告\n资产总计 100.00 90.00" + middle,
         "量净额\n-5.00 2.00" + last], 2014)
    assert result["fields"]["assets"]["status"] == "qualified"
    assert result["fields"]["assets"]["page"] == 2
    assert result["fields"]["cfo"]["status"] == "qualified"


def test_prior_year_or_adjusted_columns_do_not_become_current():
    prior = _parse_text_pages(_pages(profit_header="项目 附注 上期发生额 前期发生额"), 2014)
    assert prior["fields"]["revenue"]["status"] == "unknown"
    adjusted = _parse_text_pages(_pages(asset_header="项目 期末余额 调整前 调整后 期初余额"), 2014)
    assert adjusted["fields"]["assets"]["status"] == "unknown"


def test_missing_assets_and_period_mismatch_preserve_unknown():
    missing = _parse_text_pages([_pages()[0].replace("资产总计 100.00 90.00", "")], 2014)
    assert missing["gross_profit_over_assets"]["status"] == "unknown"
    mismatch = _parse_text_pages(_pages(profit_year=2013), 2014)
    assert mismatch["fields"]["revenue"]["status"] == "unknown"


def test_cash_unknown_does_not_disqualify_gross_profit():
    result = _parse_text_pages(_pages(cfo=""), 2014)
    assert result["gross_profit_over_assets"]["status"] == "qualified"
    assert result["cash_flow_over_assets"]["status"] == "unknown"


def test_unknown_unit_and_later_adjustment_table():
    page = _pages()[0].replace("单位：元", "单位：币值未列", 3)
    result = _parse_text_pages([page], 2014)
    assert result["fields"]["assets"]["status"] == "unknown"
    pages = _pages()
    pages[0] += "\n合并资产负债表\n单位：元 币种：人民币\n项目 2013 年 12 月 31 日 2014 年 1 月 1 日 调整数\n资产总计 1.00 1.00 0.00"
    result = _parse_text_pages(pages, 2014)
    assert result["fields"]["assets"]["status"] == "qualified"
    assert result["tables"]["assets"]["rejected_candidates"]


def test_parentheses_are_negative_not_positive():
    result = _parse_text_pages(_pages(cfo="(5.00)"), 2014)
    assert result["fields"]["cfo"]["value_yuan"] == "-5.00"
    assert Decimal(result["cash_flow_over_assets"]["value"]) == Decimal("-0.05")


def test_annotation_plus_one_amount_does_not_masquerade_as_two_columns():
    page = _pages()[0].replace("其中：营业收入 32 40.00 30.00", "其中：营业收入 32 100.00")
    result = _parse_text_pages([page], 2014)
    assert result["fields"]["revenue"]["status"] == "unknown"
    assert result["fields"]["revenue"]["candidates"][0]["reason"] == \
        "annotation_or_current_amount_ambiguous"


def test_currency_requires_evidence_but_accepts_spaced_rmb_and_preface():
    no_currency = _pages()[0].replace(" 币种：人民币", "")
    assert _parse_text_pages([no_currency], 2014)["fields"]["assets"]["status"] == "unknown"
    spaced = _pages()[0].replace("币种：人民币", "币种： 人民币")
    assert _parse_text_pages([spaced], 2014)["fields"]["revenue"]["status"] == "qualified"
    preface = "财务附注中报表的单位为：人民币元\n" + no_currency
    result = _parse_text_pages([preface], 2014)
    assert result["fields"]["assets"]["status"] == "qualified"
    assert result["tables"]["profit"]["currency_line"] == "财务附注中报表的单位为：人民币元"


def test_explicit_half_year_overrides_annual_page_heading():
    page = _pages()[0].replace("合并利润表\n2014 年 1—12 月",
                             "合并利润表\n2014 年 1—6 月")
    result = _parse_text_pages([page], 2014)
    assert result["fields"]["revenue"]["status"] == "unknown"
    assert result["tables"]["profit"]["reason"] == "report_period_year_or_duration_mismatch"


def test_pdfium_handles_closed_after_extraction(tmp_path, monkeypatch):
    class TextPage:
        def get_text_range(self):
            return "a page without statements"

        def close(self):
            closed.append("text")

    class Page:
        def get_textpage(self):
            return TextPage()

        def close(self):
            closed.append("page")

    class Pdf:
        def __init__(self, path):
            pass

        def __len__(self):
            return 1

        def __getitem__(self, index):
            return Page()

        def close(self):
            closed.append("pdf")

    closed = []
    monkeypatch.setattr("lei_signal.research.profitability_discovery.pypdfium2.PdfDocument", Pdf)
    path = tmp_path / "source.pdf"
    path.write_bytes(b"test")
    result = parse_annual_pdf(path, 2014, "000001", "id", "2015-01-01")
    assert result["page_count"] == 1
    assert closed == ["text", "page", "pdf"]


def test_currency_two_evidence_or_global_rmb_glossary_but_not_functional_alone():
    base = _pages()[0].replace(" 币种：人民币", "")
    functional = base + "\n本公司以人民币为记账本位币。"
    assert _parse_text_pages([functional], 2014)["fields"]["revenue"]["status"] == "unknown"
    translated = functional + "\n境外经营的外币财务报表按以下方法折算为人民币报表"
    result = _parse_text_pages([translated], 2014)
    assert result["fields"]["revenue"]["status"] == "qualified"
    assert result["tables"]["profit"]["currency_rule"] == "functional_plus_consolidated_translation"
    assert len(result["tables"]["profit"]["currency_evidence"]) == 2
    glossary = "元、万元、亿元 指 人民币元、人民币万元、人民币亿元\n" + base
    result = _parse_text_pages([glossary], 2014)
    assert result["tables"]["cash"]["currency_rule"] == "whole_report_rmb_glossary"


def test_short_glossary_requires_front_report_glossary_scope():
    base = _pages()[0].replace(" 币种：人民币", "")
    for mapping in ("元 指 人民币元", "元、万元 指 人民币元、人民币万元"):
        assert _parse_text_pages(["释义\n" + mapping, base], 2014)["fields"]["assets"]["status"] == "qualified"
        assert _parse_text_pages(["释义\n释义项 指 释义内容", mapping, base], 2014)["fields"]["assets"]["status"] == "qualified"
        assert _parse_text_pages([mapping, base], 2014)["fields"]["assets"]["status"] == "unknown"
        assert _parse_text_pages([base] + [""] * 19 + ["释义\n" + mapping], 2014)["fields"]["assets"]["status"] == "unknown"


def test_wrapped_group_presentation_and_complete_translation_policy():
    base = _pages()[0].replace(" 币种：人民币", "")
    statement = "本\n集团编制本财务报表时所采用的货币为人民币。"
    assert _parse_text_pages([base, statement], 2014)["fields"]["revenue"]["status"] == "qualified"
    functional = "本公司以人民币为记账本位币。"
    policy = ("本公司的控股子公司、合营企业、联营企业等，若采用与本公司不同的记账本位币，需对其外币财务报表折算后，再\n"
              "进行会计核算及合并财务报表的编报。")
    result = _parse_text_pages([base, functional, policy], 2014)
    assert result["tables"]["profit"]["currency_rule"] == "functional_plus_consolidated_translation"
    assert _parse_text_pages([base, policy], 2014)["fields"]["revenue"]["status"] == "unknown"
    assert _parse_text_pages([base, "子公司以人民币为记账本位币。", policy], 2014)["fields"]["revenue"]["status"] == "unknown"


def test_joined_unit_currency_and_year_opening_header_do_not_change_amounts():
    page = _pages(asset_header="项目 期末余额 年初余额")[0].replace("元 币种", "元币种")
    result = _parse_text_pages([page], 2014)
    assert result["fields"]["assets"]["value_yuan"] == "100.00"
    assert result["fields"]["revenue"]["value_yuan"] == "40.00"
    wrong = page.replace("元币种", "元美元 币种")
    assert _parse_text_pages([wrong], 2014)["fields"]["assets"]["status"] == "unknown"


def test_parenthesized_spaced_consolidated_titles_and_jan_first_comparative():
    page = _pages()[0].replace("合并资产负债表", "（一）合 并 资 产 负 债 表", 1)
    page = page.replace("合并利润表", "（三）合 并 利 润 表", 1)
    page = page.replace("合并现金流量表", "（五）合 并 现 金 流 量 表", 1)
    page = page.replace("项目 期末余额 期初余额", "项目 2014 年 12 月 31 日 2014 年 1 月 1 日", 1)
    result = _parse_text_pages([page], 2014)
    assert all(result["fields"][field]["status"] == "qualified"
               for field in ("assets", "revenue", "cost", "cfo"))


def test_reversed_columns_and_three_amounts_are_unknown():
    reversed_income = _pages(profit_header="项目 上期发生额 本期发生额")
    assert _parse_text_pages(reversed_income, 2014)["tables"]["profit"]["reason"] == "current_column_not_first"
    reversed_assets = _pages(asset_header="项目 期初余额 期末余额")
    assert _parse_text_pages(reversed_assets, 2014)["tables"]["assets"]["reason"] == "current_column_not_first"
    reversed_dates = _pages(asset_header="项目 2014 年 1 月 1 日 2014 年 12 月 31 日")
    assert _parse_text_pages(reversed_dates, 2014)["fields"]["assets"]["status"] == "unknown"
    three = _pages(profit_header="项目 本期发生额 上期发生额 调整前")
    assert _parse_text_pages(three, 2014)["fields"]["revenue"]["status"] == "unknown"
    this_amount = _pages(profit_header="项目 本期金额 上期金额")[0].replace(
        "营业收入 32", "营业收入").replace("营业成本 32", "营业成本")
    assert _parse_text_pages([this_amount], 2014)["fields"]["revenue"]["status"] == "qualified"


def test_statement_reference_without_heading_does_not_create_a_table():
    page = _pages()[0].replace("合并资产负债表\n", "参见合并资产负债表\n", 1)
    result = _parse_text_pages([page], 2014)
    assert result["fields"]["assets"]["status"] == "unknown"


def _preparer():
    script = (Path(__file__).resolve().parents[2] /
              "docs/experiments/raw/lowfreq-profitability-increment-2026-10-19/prepare_financial_documents.py")
    spec = importlib.util.spec_from_file_location("financial_preparer_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issuer_field_at_page_ten_and_code_on_next_line():
    preparer = _preparer()
    pages = ["2024 年年度报告"] + [""] * 8 + ["一、公司信息\n股票代码\n300371"]
    result = preparer.classify_pdf_header(pages, "300371", 2024, "2024年年度报告")
    assert result["identity_status"] == "match"
    assert result["identity_field_blocks"][0]["page"] == 10
    assert result["identity_field_blocks"][0]["codes"] == ["300371"]


def test_same_issuer_a_b_codes_and_other_issuer_field_conflict():
    preparer = _preparer()
    pages = ["2024 年年度报告\n股票简称 深康佳 A、深康佳 B 股票代码 000016、200016"]
    result = preparer.classify_pdf_header(pages, "000016", 2024, "2024年年度报告")
    assert result["identity_status"] == "match" and result["same_issuer_ab_codes"]
    pages.append("其他公司股票代码 300371")
    result = preparer.classify_pdf_header(pages, "000016", 2024, "2024年年度报告")
    assert result["identity_status"] == "identity_unknown"


def test_unrelated_six_digit_number_and_halfyear_notice_do_not_qualify():
    preparer = _preparer()
    pages = ["2024 年年度报告\n关联客户 300371"]
    result = preparer.classify_pdf_header(pages, "300371", 2024, "2024年年度报告")
    assert result["identity_status"] == "weak_match"
    half = preparer.classify_pdf_header(["2024年半年度报告\n股票代码 300371"],
                                         "300371", 2024, "2024年半年度报告")
    assert half["document_form"] != "suspected_full_text"
    notice = preparer.classify_pdf_header(["2024年年度报告更正公告\n股票代码 300371"],
                                           "300371", 2024, "2024年年度报告更正公告")
    assert notice["document_form"] == "notice"


def test_full_annual_candidate_keeps_gross_profit_when_cash_table_is_unreadable():
    preparer = _preparer()
    title = "2024年年度报告（更正后）"
    pages = ["股票代码 300371\n" + _pages()[0].replace("2014", "2024")]
    header = preparer.classify_pdf_header(pages, "300371", 2024, title)
    evidence = preparer.annual_candidate_evidence(["correction"], 2024, title,
                                                    header, pages, HEAD)
    assert evidence["status"] == "suspected"
    assert evidence["correction_category_not_excluded"]
    without_cash = [pages[0].replace("合并现金流量表", "参见合并现金流量表")]
    evidence = preparer.annual_candidate_evidence(["correction"], 2024, title,
                                                    header, without_cash, HEAD)
    assert evidence["status"] == "suspected"
    parsed = _parse_text_pages(without_cash, 2024)
    assert parsed["gross_profit_over_assets"]["status"] == "qualified"
    assert parsed["cash_flow_over_assets"]["status"] == "unknown"
    notice_title = "关于2024年年度报告更正的公告"
    notice_header = preparer.classify_pdf_header(pages, "300371", 2024, notice_title)
    assert preparer.annual_candidate_evidence(["correction"], 2024, notice_title,
                                               notice_header, pages, HEAD)["status"] == "unknown"


def test_notice_without_annual_year_retains_unknown_without_crash():
    preparer = _preparer()
    pages = ["更正公告\n合并资产负债表\n项目 期末余额 期初余额"]
    header = preparer.classify_pdf_header(pages, "300371", None, "更正公告")
    result = preparer.annual_candidate_evidence(
        ["correction"], None, "更正公告", header, pages, HEAD)
    assert result["status"] == "unknown"
    assert result["reason"] == "annual_year_missing"
