#!/usr/bin/env python3
"""Synthetic-only tests for the three-report source-field reader."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reviewed_value_fields", HERE / "read_reviewed_value_fields.py")
reader = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(reader)


class ReviewedValueFieldTests(unittest.TestCase):
    def test_2013_footer_title_after_header_is_read_across_pair(self):
        pages = {
            67: "资产 附注五 期末余额 年初余额\n负债和所有者权益合计\n\n合并资产负债表\n单位：元\n币种：人民币\n2013年12月31日 2012年12月31日",
            68: "归属于母公司所有者权益合计 876,744,908.73 909,719,940.70",
        }
        found = reader.extract_parent_equity(pages, 2013)
        self.assertEqual(found["status"], "source_candidate")
        self.assertEqual(found["value"], "876,744,908.73")
        self.assertEqual(found["evidence"]["page"], 68)

    def test_2018_label_columns_and_equity_owner_wording(self):
        pages = {
            91: "资产 附注 期末余额 年初余额\n合并资产负债表\n单位：人民币元\n2018年12月31日 2017年12月31日",
            92: "归属于母公司所有者权益合计 1,365,968,206.00 1,401,000,000.00",
        }
        found = reader.extract_parent_equity(pages, 2018)
        self.assertEqual(found["value"], "1,365,968,206.00")

    def test_2023_spaced_project_header_and_shareholder_wording(self):
        pages = {
            135: "项 目 附注 2023年12月31日 2022年12月31日\n合并资产负债表\n单位：元，币种：人民币",
            136: "归属于母公司股东权益合计 6,488,818,048.97 6,100,000,000.00",
        }
        found = reader.extract_parent_equity(pages, 2023)
        self.assertEqual(found["value"], "6,488,818,048.97")

    def test_parent_only_statement_rejected(self):
        pages = {1: "母公司资产负债表\n单位：人民币元\n2023年12月31日 2022年12月31日\n项目 附注 2023年12月31日 2022年12月31日\n归属于母公司股东权益合计 5 4"}
        self.assertEqual(reader.extract_parent_equity(pages, 2023)["status"], "unknown")

    def test_wrong_or_reversed_year_columns_rejected(self):
        wrong = {1: "合并资产负债表\n单位：人民币元\n2023年12月31日 2022年12月31日\n项目 附注 2022年12月31日 2021年12月31日\n归属于母公司股东权益合计 5 4"}
        reversed_dates = {1: "项目 附注 2022年12月31日 2023年12月31日\n合并资产负债表\n单位：人民币元\n2023年12月31日 2022年12月31日\n归属于母公司股东权益合计 5 4"}
        self.assertEqual(reader.extract_parent_equity(wrong, 2023)["status"], "unknown")
        self.assertEqual(reader.extract_parent_equity(reversed_dates, 2023)["status"], "unknown")

    def test_blank_equity_and_other_equity_investment_are_not_used(self):
        pages = {1: "资产 附注 期末余额 年初余额\n合并资产负债表\n单位：人民币元\n2023年12月31日 2022年12月31日\n其他权益工具投资 9,999,999 8,888,888\n归属于母公司股东权益合计 — —"}
        found = reader.extract_parent_equity(pages, 2023)
        self.assertEqual(found["status"], "unknown")
        self.assertEqual(found["reason"], "parent_equity_row_blank_or_ambiguous")

    def test_duplicate_same_value_rows_are_ambiguous_not_merged(self):
        pages = {1: "资产 附注 期末余额 年初余额\n合并资产负债表\n单位：人民币元\n2023年12月31日 2022年12月31日\n归属于母公司股东权益合计 100 90\n归属于母公司股东权益合计 100 90"}
        self.assertEqual(reader.extract_parent_equity(pages, 2023)["status"], "unknown")

    def test_share_count_selects_post_change_integer_not_before_value_or_percent(self):
        pages = {53: "本次变动前 本次变动增减（＋，－） 本次变动后\n股份总数 422,254,134 100.00% -9,034,473 -2.14% 413,219,661 100.00%"}
        found = reader.extract_post_change_total_shares(pages, 2018, 53)
        self.assertEqual(found["value"], "413219661")
        self.assertNotEqual(found["value"], "422254134")

    def test_share_page_may_have_header_on_neighbor_but_row_must_be_bound_page(self):
        pages = {52: "本次变动前 本次变动后", 53: "股份总数 1,000 100.00%", 54: "A股 股份总数 900 100.00%"}
        self.assertEqual(reader.extract_post_change_total_shares(pages, 2018, 53)["value"], "1000")

    def test_share_percent_and_capital_are_not_a_share_count(self):
        capital_only = {53: "股本 232,864,320.00元\n普通股股东总数 232,864,320"}
        self.assertEqual(reader.extract_post_change_total_shares(capital_only, 2013, 53)["status"], "unknown")
        malformed = {53: "本次变动前 本次变动后\n股份总数 422,254,134 100.00% -9,034,473 -2.14%"}
        self.assertEqual(reader.extract_post_change_total_shares(malformed, 2018, 53)["status"], "unknown")

    def test_prepared_identity_must_match_frozen_original(self):
        target = {"code": "000032", "report_year": 2023, "announcement_id": "a",
                  "publication_date": "2024-04-18", "original_pdf": {"path": "/x.pdf", "bytes": 10, "sha256": "abc"}}
        checks = {name: True for name in ("status_qualified", "publisher_code_matches", "bytes_match", "sha256_matches", "pdf_header")}
        prepared = {"source": {"publisher_code": "000032", "announcement_id": "a", "report_year_from_title": 2023,
                               "announcement_date_asia_shanghai": "2024-04-18",
                               "source_identity": {"path": "/x.pdf", "bytes": 10, "sha256": "abc", "checks": checks}},
                    "financial_parser_result": {"tables": {"assets": {"status": "unknown"}}}}
        self.assertEqual(reader.validate_source_identity(target, prepared)["status"], "unknown")
        prepared["source"]["source_identity"]["sha256"] = "different"
        with self.assertRaises(ValueError):
            reader.validate_source_identity(target, prepared)


if __name__ == "__main__":
    unittest.main(verbosity=2)
