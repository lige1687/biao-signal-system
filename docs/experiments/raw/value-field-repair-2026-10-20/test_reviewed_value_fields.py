#!/usr/bin/env python3
"""Synthetic, layout-faithful checks; never reads the external report PDFs."""
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
    def test_2013_footer_title_and_repeated_unit_label_header(self):
        pages = {
            67: "资产 附注五 期末余额 年初余额\n金额单位均为人民币元\n合并资产负债表\n2013年12月31日",
            68: "负债和股东权益 附注五 期末余额 年初余额\n金额单位均为人民币元\n归属于母公司所有者权益合计 876,744,908.73 909,719,940.70",
        }
        found = reader.extract_parent_equity(pages, 2013)
        self.assertEqual(found["status"], "source_candidate")
        self.assertEqual(found["value"], "876,744,908.73")
        self.assertEqual(found["evidence"]["page"], 68)
        self.assertEqual(len(found["unit_evidence"]), 2)
        self.assertEqual(len(found["header_evidence"]), 2)

    def test_2018_repeated_yuan_and_current_first(self):
        pages = {91: "资产 附注 期末余额 年初余额\n合并资产负债表\n2018年12月31日\n（金额单位均为人民币元）",
                 92: "负债和所有者权益 附注 期末余额 年初余额\n（金额单位均为人民币元）\n归属于母公司所有者权益合计 1,365,968,206.00 1,499,724,761.28"}
        found = reader.extract_parent_equity(pages, 2018)
        self.assertEqual(found["value"], "1,365,968,206.00")
        self.assertEqual(found["comparative_value_not_selected"], "1,499,724,761.28")

    def test_2023_repeated_dated_header_and_shareholder_label(self):
        pages = {135: "合并资产负债表\n2023年12月31日\n单位：人民币元\n项 目 附注 2023年12月31日 2022年12月31日",
                 136: "合并资产负债表（续）\n单位：人民币元\n项 目 附注 2023年12月31日 2022年12月31日\n归属于母公司股东权益合计 6,488,818,048.97 5,573,195,221.75"}
        found = reader.extract_parent_equity(pages, 2023)
        self.assertEqual(found["value"], "6,488,818,048.97")

    def test_parent_only_statement_rejected(self):
        pages = {1: "母公司资产负债表\n单位：人民币元\n2023年12月31日\n项目 附注 2023年12月31日 2022年12月31日\n归属于母公司股东权益合计 5 4"}
        self.assertEqual(reader.extract_parent_equity(pages, 2023)["status"], "unknown")

    def test_reversed_or_conflicting_headers_rejected_even_if_valid_duplicate_exists(self):
        base = "合并资产负债表\n2023年12月31日\n单位：人民币元\n"
        for second in ("项目 附注 2022年12月31日 2023年12月31日",
                       "项目 附注 2023年12月31日 2023年1月1日",
                       "项目 附注 期初余额 期末余额"):
            pages = {1: base + "项目 附注 2023年12月31日 2022年12月31日\n" + second +
                     "\n归属于母公司股东权益合计 5 4"}
            self.assertEqual(reader.extract_parent_equity(pages, 2023)["status"], "unknown")

    def test_conflicting_unit_on_continuation_is_rejected(self):
        pages = {135: "合并资产负债表\n2023年12月31日\n单位：人民币元\n项目 附注 2023年12月31日 2022年12月31日",
                 136: "合并资产负债表（续）\n单位：人民币万元\n项目 附注 2023年12月31日 2022年12月31日\n归属于母公司股东权益合计 5 4"}
        found = reader.extract_parent_equity(pages, 2023)
        self.assertEqual(found["status"], "unknown")
        self.assertEqual(found["reason"], "RMB_yuan_unit_missing_or_ambiguous")

    def test_blank_equity_cannot_swallow_minority_row_or_other_equity_investment(self):
        head = "合并资产负债表\n2023年12月31日\n单位：人民币元\n项目 附注 2023年12月31日 2022年12月31日\n"
        for tail in ("归属于母公司股东权益合计\n少数股东权益 100 90",
                     "其他权益工具投资 900 800\n归属于母公司股东权益合计 — —\n少数股东权益 100 90"):
            found = reader.extract_parent_equity({1: head + tail}, 2023)
            self.assertEqual(found["status"], "unknown")
            self.assertEqual(found["reason"], "parent_equity_row_blank_or_ambiguous")

    def test_numeric_continuation_only_and_negative_sign_preserved(self):
        head = "合并资产负债表\n2023年12月31日\n单位：人民币元\n项目 附注 2023年12月31日 2022年12月31日\n"
        found = reader.extract_parent_equity({1: head + "归属于母公司股东权益合计\n-12,474,956.74 −1,857,990,442.34"}, 2023)
        self.assertEqual(found["value"], "-12,474,956.74")
        self.assertEqual(found["comparative_value_not_selected"], "−1,857,990,442.34")

    def test_duplicate_equity_even_same_value_is_unknown(self):
        head = "合并资产负债表\n2023年12月31日\n单位：人民币元\n项目 附注 2023年12月31日 2022年12月31日\n"
        found = reader.extract_parent_equity({1: head + "归属于母公司股东权益合计 100 90\n归属于母公司股东权益合计 100 90"}, 2023)
        self.assertEqual(found["status"], "unknown")

    def test_share_before_after_unit_and_three_prefix(self):
        pages = {53: "单位：股\n本次变动前 本次变动增减（＋，－） 本次变动后\n三、股份总数 422,254,134 100.00% -9,034,473 -2.14% 413,219,661 100.00%"}
        found = reader.extract_post_change_total_shares(pages, 2018, 53)
        self.assertEqual(found["value"], "413219661")
        self.assertNotEqual(found["value"], "422254134")

    def test_share_2013_same_before_after_and_neighbor_header(self):
        pages = {36: "本次变动前 本次变动后\n单位：股", 37: "三、股份总数 232,864,320 100% 232,864,320 100%"}
        self.assertEqual(reader.extract_post_change_total_shares(pages, 2013, 37)["value"], "232864320")

    def test_share_row_must_be_bound_page(self):
        pages = {52: "本次变动前 本次变动后\n单位：股\n三、股份总数 99 100% 99 100%", 53: "三、股份总数 700 100% 1,000 100%"}
        self.assertEqual(reader.extract_post_change_total_shares(pages, 2018, 53)["value"], "1000")

    def test_share_duplicate_including_failed_row_is_unknown(self):
        pages = {53: "单位：股\n本次变动前 本次变动后\n三、股份总数 422,254,134 100% 413,219,661 100%\n三、股份总数 999"}
        self.assertEqual(reader.extract_post_change_total_shares(pages, 2018, 53)["status"], "unknown")

    def test_share_explanation_date_cannot_be_consumed(self):
        pages = {53: "单位：股\n本次变动前 本次变动后\n三、股份总数 422,254,134 100% 413,219,661 100%\n2018年7月解除限售"}
        self.assertEqual(reader.extract_post_change_total_shares(pages, 2018, 53)["value"], "413219661")

    def test_share_unit_or_after_pair_missing_is_unknown(self):
        without_unit = {53: "本次变动前 本次变动后\n三、股份总数 1,000 100%"}
        without_after = {53: "单位：股\n本次变动前 本次变动后\n三、股份总数 422,254,134 100% -9,034,473 -2.14%"}
        self.assertEqual(reader.extract_post_change_total_shares(without_unit, 2018, 53)["status"], "unknown")
        self.assertEqual(reader.extract_post_change_total_shares(without_after, 2018, 53)["status"], "unknown")

    def test_only_before_count_or_negative_final_count_rejected(self):
        header = "单位：股\n本次变动前 本次变动后\n三、股份总数 "
        for row in ("422,254,134 100%", "422,254,134 100% -413,219,661 100%"):
            found = reader.extract_post_change_total_shares({53: header + row}, 2018, 53)
            self.assertEqual(found["status"], "unknown")

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
