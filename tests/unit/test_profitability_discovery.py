"""Semantic counterexamples for original annual-statement extraction."""

from decimal import Decimal

from lei_signal.research.profitability_discovery import _parse_text_pages, parse_annual_pdf


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
