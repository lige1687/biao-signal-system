#!/usr/bin/env python3
"""Synthetic source-only checks; no PDF batch, network or result directory."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("saved_value_fields", HERE / "extract_saved_value_fields.py")
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)
# The plan binds the exact pre-existing parser implementation.
plan = json.loads((HERE / "plan.json").read_text())
old = extract.load_old_parser(plan["old_parser_path"], plan["old_parser_sha256"])


class SourceOnlyTests(unittest.TestCase):
    def asset(self, unit="元"):
        return {"status": "qualified", "heading_page": 10, "header": "项目 附注 2023年12月31日 2022年12月31日",
                "unit_line": f"单位：人民币{unit}", "currency_rule": "table_rmb_unit"}

    def pages(self, body):
        return [(10, "合并资产负债表\n项目 附注 2023年12月31日 2022年12月31日\n" + body),
                (11, "母公司资产负债表\n项目 附注 2023年12月31日 2022年12月31日\n归属于母公司所有者权益合计 999.00 888.00")]

    def test_four_fields_keep_signed_yuan_and_accounting_capital_distinct(self):
        pages = self.pages("股本 356,180,613.00 356,180,613.00\n其他权益工具 10.00 9.00\n减：库存股 3.00 2.00\n归属于母公司所有者权益合计 -12,474,956.74 -1,857,990,442.34")
        fields, reason = extract.extract_qualified_fields(pages, self.asset(), old)
        self.assertIsNone(reason)
        self.assertEqual(fields["parent_equity"]["value_yuan"], "-12474956.74")
        self.assertEqual(fields["other_equity"]["value_yuan"], "10.00")
        self.assertEqual(fields["treasury_stock"]["value_yuan"], "3.00")
        self.assertEqual(fields["accounting_capital"]["value_yuan"], "356180613.00")
        self.assertNotIn("share_count", str(fields))

    def test_blank_one_side_and_investment_do_not_become_zero(self):
        pages = self.pages("其他权益工具投资 99.00 88.00\n其他权益工具 10.00\n减：库存股 — —\n归属于母公司股东权益合计 100.00 90.00")
        fields, _ = extract.extract_qualified_fields(pages, self.asset(), old)
        self.assertEqual(fields["other_equity"]["status"], "unknown")
        self.assertEqual(fields["treasury_stock"]["status"], "unknown")
        self.assertEqual(fields["parent_equity"]["value_yuan"], "100.00")

    def test_parent_table_is_hard_boundary(self):
        pages = [(10, "合并资产负债表\n项目 期末余额 期初余额\n归属于母公司所有者权益合计 100.00 90.00\n母公司资产负债表\n归属于母公司所有者权益合计 999.00 888.00")]
        fields, reason = extract.extract_qualified_fields(pages, self.asset(), old)
        self.assertIsNone(reason)
        self.assertEqual(fields["parent_equity"]["value_yuan"], "100.00")

    def test_no_boundary_fails_closed(self):
        fields, reason = extract.extract_qualified_fields([(10, "合并资产负债表\n股本 1.00 1.00")], self.asset(), old)
        self.assertEqual(reason, "next_financial_table_boundary_not_seen_within_page_limit")
        self.assertTrue(all(f["status"] == "unknown" for f in fields.values()))

    def test_three_numbers_even_annotation_are_ambiguous(self):
        pages = self.pages("归属于母公司所有者权益合计 25 100.00 90.00")
        fields, _ = extract.extract_qualified_fields(pages, self.asset(), old)
        self.assertEqual(fields["parent_equity"]["status"], "unknown")

    def test_one_integer_plus_one_amount_in_note_column_is_ambiguous(self):
        pages = self.pages("股本 25 100.00")
        fields, _ = extract.extract_qualified_fields(pages, self.asset(), old)
        self.assertEqual(fields["accounting_capital"]["status"], "unknown")

    def test_unit_scaling_only_after_two_amounts(self):
        pages = self.pages("归属于母公司所有者权益合计 1.25 0.75")
        fields, _ = extract.extract_qualified_fields(pages, self.asset("万元"), old)
        self.assertEqual(fields["parent_equity"]["value_yuan"], "12500.00")

    def test_duplicate_label_is_unknown(self):
        pages = self.pages("股本 1.00 1.00\n股本 1.00 1.00")
        fields, _ = extract.extract_qualified_fields(pages, self.asset(), old)
        self.assertEqual(fields["accounting_capital"]["status"], "unknown")

    def test_non_parent_next_table_rejected(self):
        pages = [(10, "合并资产负债表\n股本 1.00 1.00\n合并利润表")]
        fields, reason = extract.extract_qualified_fields(pages, self.asset(), old)
        self.assertEqual(reason, "next_table_is_not_parent_balance_sheet")
        self.assertEqual(fields["accounting_capital"]["status"], "unknown")

    def test_continuation_reverse_columns_or_unit_conflict_is_unknown(self):
        for continuation in ("项目 附注 2022年12月31日 2023年12月31日",
                             "单位：人民币万元"):
            pages = [(10, "合并资产负债表\n项目 附注 2023年12月31日 2022年12月31日\n股本 1.00 1.00"),
                     (11, continuation + "\n母公司资产负债表")]
            fields, reason = extract.extract_qualified_fields(pages, self.asset(), old)
            self.assertIsNotNone(reason)
            self.assertEqual(fields["accounting_capital"]["status"], "unknown")

    def test_original_selection_counts_one_precise_annual_original(self):
        entry = {"code": "sz.000032", "year": 2018, "title": "2018年年度报告",
                 "pdf": {"status": "obtained", "source_path": "/x"},
                 "prepared_binding": {"identity_status": "match", "path": "/y"}}
        self.assertIsNone(extract.original_selection(entry, {"sz.000032"}, {2018}))
        self.assertEqual(extract.original_selection({**entry, "title": "2018年年度报告摘要"}, {"sz.000032"}, {2018}), "not_exact_title")

    def test_prepared_or_pdf_sha_and_identity_mismatch_are_hard_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            pdf = d / "source.pdf"; pdf.write_bytes(b"%PDF-synthetic")
            source = {"cohort_code": "sz.000032", "publisher_code": "000032", "report_year_from_title": 2018,
                      "announcement_id": "id1", "announcement_date_asia_shanghai": "2019-04-25",
                      "source_identity": {"path": str(pdf), "bytes": pdf.stat().st_size,
                                          "sha256": extract.sha256_file(pdf),
                                          "checks": {k: True for k in ("status_qualified", "publisher_code_matches", "bytes_match", "sha256_matches", "pdf_header")}}}
            prepared = d / "prepared.json"; prepared.write_text(json.dumps({"source": source}))
            entry = {"code": "sz.000032", "year": 2018, "id": "id1", "publication_date": "2019-04-25",
                     "pdf": {"source_path": str(pdf), "bytes": pdf.stat().st_size,
                             "sha256": extract.sha256_file(pdf)},
                     "prepared_binding": {"path": str(prepared), "sha256": extract.sha256_file(prepared)}}
            extract.verify_prepared_and_pdf(entry)
            bad = {**entry, "pdf": {**entry["pdf"], "sha256": "0" * 64}}
            with self.assertRaises(ValueError):
                extract.verify_prepared_and_pdf(bad)
            source["announcement_id"] = "other"
            prepared.write_text(json.dumps({"source": source}))
            entry["prepared_binding"]["sha256"] = extract.sha256_file(prepared)
            with self.assertRaises(ValueError):
                extract.verify_prepared_and_pdf(entry)

    def test_missing_assets_parser_record_is_unqualified_not_integrity_error(self):
        # process_entry's metadata path accepts null financial_parser_result;
        # no source PDF is parsed in this case.
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp); pdf = d / "source.pdf"; pdf.write_bytes(b"%PDF-synthetic")
            source = {"cohort_code": "sz.000032", "publisher_code": "000032", "report_year_from_title": 2018,
                      "announcement_id": "id1", "announcement_date_asia_shanghai": "2019-04-25",
                      "source_identity": {"path": str(pdf), "bytes": pdf.stat().st_size,
                                          "sha256": extract.sha256_file(pdf),
                                          "checks": {k: True for k in ("status_qualified", "publisher_code_matches", "bytes_match", "sha256_matches", "pdf_header")}}}
            prepared = d / "prepared.json"; prepared.write_text(json.dumps({"source": source, "financial_parser_result": None}))
            entry = {"code": "sz.000032", "year": 2018, "id": "id1", "publication_date": "2019-04-25",
                     "pdf": {"source_path": str(pdf), "bytes": pdf.stat().st_size,
                             "sha256": extract.sha256_file(pdf)},
                     "prepared_binding": {"path": str(prepared), "sha256": extract.sha256_file(prepared)}}
            row = extract.process_entry(entry, 42, old, 6)
            self.assertEqual(row["entry_id"], "index:42")
            self.assertEqual(row["status"], "assets_table_unqualified")
            self.assertTrue(all(f["status"] == "unknown" for f in row["fields"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
