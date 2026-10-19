"""Meaningful synthetic source and time boundaries; no saved market inputs."""

import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from lei_signal.research.asset_growth_discovery import (
    _full_annual_title, _latest, _notice_event, _tokens, annual_assets,
    check_bound, notice_decision, qualify, run, sha,
)


def record(year=2023, day="2024-04-01", code="sz.000001", ident="one", status="obtained"):
    return {"code": code, "id": ident, "year": year, "publication_date": day,
            "categories": ["annual"], "excluded_doc_kind": None, "title": f"{year}年年度报告",
            "pdf": {"status": status, "sha256": "a" * 64}}


def document(expected=None, current="120", comparative="100", header="项目 2023年12月31日 2022年12月31日"):
    expected = expected or record()
    return {"source": {"cohort_code": expected["code"], "announcement_id": expected["id"],
                       "report_year_from_title": expected["year"],
                       "announcement_date_asia_shanghai": expected["publication_date"]},
            "header_evidence": {"document_form": "suspected_full_text", "identity_status": "match"},
            "annual_candidate_evidence": {"status": "suspected"},
            "financial_parser_result": {
                "report_year": expected["year"], "publication_date": expected["publication_date"],
                "tables": {"assets": {"status": "qualified", "header": header,
                                      "currency_rule": "table_currency", "period_line": "2023 年 12 月 31 日"}},
                "fields": {"assets": {"status": "qualified", "raw_label": "资产总计",
                                      "raw_line": f"资产总计 {current} {comparative}",
                                      "value_yuan": current, "unit": "元", "page": 8},
                           "revenue": {"status": "qualified", "value_yuan": "60"},
                           "cost": {"status": "qualified", "value_yuan": "30"}}}}


def audit():
    return {"month": "2024-07", "decision_date": "2024-06-28", "code": "sz.000001",
            "gp": {"status": "qualified", "report_year": 2023,
                   "publication_date": "2024-04-01", "announcement_ids": ["one"],
                   "amounts_yuan": {"assets": "120", "revenue": "60", "cost": "30"},
                   "value": "0.25"}}


def checked_pair(current, comparative):
    return {"current": current, "comparative": comparative,
            "gp_readback": {"revenue": "60", "cost": "30",
                            "ratio": str(Decimal(30) / Decimal(current))}}


class AssetGrowthQualificationTest(unittest.TestCase):
    def test_exact_two_year_pair_preserves_negative_growth(self):
        current = record()
        prior = record(2022, "2023-04-01", ident="prior")
        def loader(records, _day):
            chosen = records[0]
            value = (checked_pair("80", "100") if chosen["year"] == 2023
                     else checked_pair("100", "90"))
            # In the real source, the old GP audit must match current assets.
            return value, None, [{"id": chosen["id"], **value}]
        a = audit(); a["gp"]["amounts_yuan"]["assets"] = "80"
        a["gp"]["value"] = str(Decimal(30) / Decimal(80))
        row, evidence = qualify(a, [current, prior], {}, load_pair=loader)
        self.assertEqual(row["status"], "qualified")
        self.assertEqual(row["growth"], "-0.2")
        self.assertTrue(evidence["crossreport_equal"])

    def test_latest_failed_version_never_falls_back(self):
        latest, error = _latest([record(), record(day="2024-05-01", ident="failed", status="failed")],
                                "sz.000001", 2023, "2024-06-28")
        self.assertIsNone(error)
        self.assertEqual([r["id"] for r in latest], ["failed"])
        row, _ = qualify(audit(), [record(), record(day="2024-05-01", ident="failed", status="failed")], {})
        self.assertEqual(row["reason"], "current_latest_ids_differ_from_gp_audit")

    def test_source_index_distinguishes_summaries_notices_and_full_revisions(self):
        summary = record(year=None, ident="summary")
        summary.update(title="2023年年度报告摘要更正公告", excluded_doc_kind="摘要",
                       categories=["annual", "correction"])
        english = record(year=None, ident="english")
        english.update(title="2023年年度报告英文版", excluded_doc_kind="英文")
        notice = record(ident="notice")
        notice.update(title="关于更正2023年年度报告的公告", categories=["annual", "correction"],
                      prepared_binding={"document_form": "notice"})
        revised = record(ident="revised")
        revised.update(title="2023年年度报告（更正版）", categories=["annual", "correction"],
                       prepared_binding={"document_form": "suspected_full_text"})
        ambiguous = record(year=None, ident="ambiguous")
        ambiguous["title"] = "年报全文"
        self.assertFalse(_notice_event(summary))
        self.assertFalse(_notice_event(english))
        self.assertTrue(_notice_event(notice))
        self.assertFalse(_notice_event(revised))
        self.assertTrue(_notice_event(ambiguous))
        self.assertTrue(_full_annual_title(revised))
        self.assertFalse(_full_annual_title(notice))
        self.assertEqual(annual_assets(document(revised), revised, "2024-06-28")["status"], "qualified")
        latest, _ = _latest([record(), revised, notice], "sz.000001", 2023, "2024-06-28")
        self.assertEqual({r["id"] for r in latest}, {"one", "revised"})

    def test_python_parser_binding_is_hash_only_and_run_contract_is_source_only(self):
        with TemporaryDirectory() as temp:
            parser = Path(temp) / "parser.py"
            parser.write_text("MONEY_TOKEN = 1\n", encoding="utf-8")
            check_bound({"path": str(parser), "sha256": sha(parser)})
            with self.assertRaises(ValueError):
                check_bound({"path": str(parser), "sha256": "0" * 64})
            contract = Path(temp) / "run.json"
            contract.write_text('{"schema":"asset-growth-source-run/1","market_effects_allowed":true}',
                                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source-only"):
                run(contract)

    def test_same_day_versions_must_agree(self):
        records = [record(), record(ident="other")]
        latest, _ = _latest(records, "sz.000001", 2023, "2024-06-28")
        self.assertEqual(len(latest), 2)
        a = audit()
        a["gp"]["announcement_ids"] = ["one", "other"]
        def loader(items, _):
            return None, "same_day_asset_pair_conflict", [{"id": r["id"]} for r in items]
        row, detail = qualify(a, records, {}, load_pair=loader)
        self.assertEqual(row["reason"], "current_same_day_asset_pair_conflict")
        self.assertEqual(len(detail["current"]), 2)

    def test_future_or_same_day_publication_excluded(self):
        self.assertEqual(_latest([record(day="2024-06-28")], "sz.000001", 2023, "2024-06-28"),
                         ([], "no_public_full_annual"))
        d = document()
        self.assertEqual(annual_assets(d, record(), "2024-04-01")["reason"], "document_identity_or_time_unknown")

    def test_prior_missing_or_crossreport_mismatch(self):
        def loader(items, _):
            if items[0]["year"] == 2023:
                return checked_pair("120", "101"), None, [{}]
            return checked_pair("100", "90"), None, [{}]
        row, _ = qualify(audit(), [record()], {}, load_pair=loader)
        self.assertEqual(row["reason"], "prior_no_public_full_annual")
        row, _ = qualify(audit(), [record(), record(2022, "2023-04-01", ident="prior")], {},
                         load_pair=loader)
        self.assertEqual(row["reason"], "unknown_crossreport_mismatch")

    def test_amount_unit_note_and_adjusted_columns(self):
        self.assertEqual(_tokens("资产总计 1,200.00 1,000.00", "资产总计", False)[0], [1200, 1000])
        self.assertEqual(_tokens("资产总计 3 1,200.00 1,000.00", "资产总计", True)[0], [1200, 1000])
        self.assertIsNotNone(_tokens("资产总计 3 1200 1000", "资产总计", False)[1])
        d = document()
        self.assertEqual(annual_assets(d, record(), "2024-06-28")["status"], "qualified")
        self.assertEqual(annual_assets(d, record(), "2024-06-28")["gp_readback"]["ratio"], "0.25")
        d["financial_parser_result"]["fields"]["assets"]["unit"] = "万元"
        self.assertEqual(annual_assets(d, record(), "2024-06-28")["reason"],
                         "current_assets_do_not_match_frozen_field")
        d = document(header="项目 2023年12月31日 调整前 2022年12月31日")
        self.assertEqual(annual_assets(d, record(), "2024-06-28")["reason"],
                         "adjusted_or_multiple_columns")
        d = document(header="项目 2022年12月31日 2023年12月31日")
        self.assertEqual(annual_assets(d, record(), "2024-06-28")["reason"],
                         "annual_column_order_unknown")

    def test_year_start_only_accepted_after_crossreport_match(self):
        d = document(header="项目 2023年12月31日 2023年1月1日")
        self.assertEqual(annual_assets(d, record(), "2024-06-28")["comparative_kind"], "year_start")
        def loader(items, _):
            if items[0]["year"] == 2023:
                return checked_pair("120", "100"), None, [{}]
            return checked_pair("99", "90"), None, [{}]
        row, _ = qualify(audit(), [record(), record(2022, "2023-04-01", ident="prior")], {},
                         load_pair=loader)
        self.assertEqual(row["reason"], "unknown_crossreport_mismatch")

    def test_dual_period_unknown_notice_recovery_boundary(self):
        event = {"code": "sz.000001", "id": "notice", "publication_date": "2022-06-01",
                 "pdf": {"sha256": "x"}}
        args = (2023, "2024-04-01", "2023-04-01", ["one"], ["prior"], True)
        self.assertEqual(notice_decision(event, None, *args)[0], "uncertain_recovery")
        event["publication_date"] = "2023-02-01"  # after prior fiscal end
        self.assertEqual(notice_decision(event, None, *args)[0], "block")
        event["publication_date"] = "2022-06-01"
        self.assertEqual(notice_decision(event, None, *args[:-1], False)[0], "block")
        review = {"cohort_code": "sz.000001", "announcement_id": "notice",
                  "publication_date": "2022-06-01", "source_sha256": "x",
                  "controller_accepted": True, "affected_years": [2022],
                  "affected_fields": ["assets"], "continuing_scope": "cleared"}
        self.assertEqual(notice_decision(event, review, *args)[0], "block")
        review["resolved_by_announcement_ids"] = ["prior"]
        self.assertEqual(notice_decision(event, review, *args)[0], "ignore")
        review["source_sha256"] = "wrong"
        self.assertEqual(notice_decision(event, review, *args)[0], "block")


if __name__ == "__main__":
    unittest.main()
