"""Synthetic annual pages only; no original PDF or market outcome is read."""

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("extract_annual_value_anchors.py")
spec = importlib.util.spec_from_file_location("annual_value_anchors", MODULE)
anchor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(anchor)


def pages(*, unit="万元", parent="300.00 250.00", other="10.00 5.00", shares="1000000", share_capital="100.00 90.00", extra=""):
    return [f"2024 年年度报告\n合并资产负债表\n2024 年 12 月 31 日\n单位：{unit} 币种：人民币\n项目 期末余额 年初余额\n资产总计 400 350\n所有者权益\n股本 {share_capital}\n其他权益工具 {other}\n其中：优先股 10 5\n减：库存股 2 1\n归属于母公司所有者权益合计 {parent}\n",
            f"普通股股本变动情况\n报告期内公司股份总数变为 {shares} 股。\n{extra}"]


class AnnualValueAnchorTests(unittest.TestCase):
    def test_unit_scale_and_current_column_not_prior(self):
        result = anchor.extract_pages(pages(), 2024)
        fields = result["fields"]
        self.assertEqual(fields["parent_attributable_equity"]["value"], "3000000.00")
        self.assertEqual(fields["other_equity_instruments"]["value"], "100000.00")
        self.assertEqual(fields["share_capital_yuan"]["value"], "1000000.00")
        self.assertEqual(result["ordinary_equity_yuan"], "2900000.00")

    def test_share_capital_rmb_is_not_implicitly_number_of_shares(self):
        result = anchor.extract_pages(pages(shares="100"), 2024)
        self.assertEqual(result["fields"]["share_capital_yuan"]["value"], "1000000.00")
        self.assertEqual(result["fields"]["ordinary_shares_report_end"]["status"], "unknown")
        self.assertEqual(result["fields"]["ordinary_shares_report_end"]["candidates"][0]["value_shares"], 100)

    def test_explicit_share_count_kept_as_candidate_needing_context_review(self):
        result = anchor.extract_pages(pages(), 2024)
        count = result["fields"]["ordinary_shares_report_end"]
        self.assertEqual(count["status"], "candidate_explicit_shares")
        self.assertEqual(count["unit"], "shares_not_RMB")
        self.assertFalse(result["annual_bp_ready"])

    def test_blank_other_equity_cannot_borrow_preferred_line_or_become_zero(self):
        result = anchor.extract_pages(pages(other=""), 2024)
        other = result["fields"]["other_equity_instruments"]
        self.assertEqual(other["status"], "unknown")
        self.assertIsNone(result["ordinary_equity_yuan"])
        self.assertIn("other_equity_balance_unknown", result["blocking_reasons"])

    def test_split_parent_line_and_preferred_balance_subtracted(self):
        sample = pages()
        sample[0] = sample[0].replace("归属于母公司所有者权益合计 300.00 250.00",
                                      "归属于母公司所有者权益\n合计\n300.00 250.00")
        result = anchor.extract_pages(sample, 2024)
        self.assertEqual(result["fields"]["parent_attributable_equity"]["value"], "3000000.00")
        self.assertEqual(result["ordinary_equity_yuan"], "2900000.00")

    def test_h_shares_block_single_price_assumption(self):
        result = anchor.extract_pages(pages(extra="A股 上海证券交易所\nH股 香港联合交易所"), 2024)
        self.assertEqual(result["share_classes"]["status"], "multi_price_classes")
        self.assertIn("multi_price_class_requires_all_class_quotes", result["blocking_reasons"])

    def test_wrong_fiscal_year_and_missing_currency_remain_unknown(self):
        self.assertEqual(anchor.extract_pages(pages(), 2023)["reason"], "current_fiscal_year_or_unit_not_verified")
        no_currency = [text.replace("币种：人民币", "") for text in pages()]
        self.assertEqual(anchor.extract_pages(no_currency, 2024)["reason"], "RMB_consolidated_table_currency_unverified")


if __name__ == "__main__":
    unittest.main()
