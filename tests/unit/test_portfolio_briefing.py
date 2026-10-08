from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lei_signal.portfolio.briefing import build_packet, collect_news_safely

NOW = datetime.fromisoformat("2026-10-08T14:40:00+08:00")


class PortfolioBriefingTests(unittest.TestCase):
    def source(self):
        return {"workspace": {"ok": True, "data": {"as_of": "2026-09-04", "coverage": {"total": 1}, "items": [{
            "holding_id": "h1", "name": "示例基金", "nav": {"value": 1.2, "date": "2026-09-30"},
            "plan": {"plan_id": "p1", "state": "entered"}, "technical": {"meta": {"last_bar_date": "2026-09-30"}},
            "status": "action_required",
            "gaps": ["行情时点尚未核实"], "alerts": [{"code": "STOP_PRICE_BREACHED"}],
        }]}}}

    def test_noon_never_emits_operation_review(self):
        out = build_packet(self.source(), slot="1135", now=NOW)
        self.assertEqual(out["plan_review"], [])
        self.assertEqual(out["mode"], "information_only")

    def test_incomplete_input_cannot_become_sell_or_safe(self):
        out = build_packet(self.source(), slot="1440", now=NOW)
        self.assertEqual(out["plan_review"][0]["system_alerts"], [])
        self.assertIn("不能判定", out["plan_review"][0]["state"])

    def test_refresh_only_does_not_count_as_change(self):
        src = self.source()
        old = build_packet(src, slot="1135", now=NOW)
        src["workspace"]["data"]["items"][0]["nav"]["updated_at"] = NOW.isoformat()
        out = build_packet(src, slot="1440", now=NOW, previous=old)
        self.assertEqual(out["changes"], [])
        src["workspace"]["data"]["items"][0]["nav"]["value"] = 1.3
        out = build_packet(src, slot="1440", now=NOW, previous=old)
        self.assertEqual(out["changes"][0]["fields"], ["nav_value"])

    def test_first_observation_is_not_daily_change(self):
        out = build_packet(self.source(), slot="1440", now=NOW)
        self.assertTrue(out["first_observation"])
        self.assertEqual(out["changes"], [])

    def test_news_dates_and_content_basis(self):
        src = self.source()
        src["news"] = {"ok": True, "data": {"items": [
            {"id": 1, "source": "bilibili", "published_at": "2026-10-07T10:00:00+08:00", "title": "仅标题"},
            {"id": 2, "published_at": "2026-10-08T16:00:00+08:00"},
            {"id": 3, "published_at": "2026-10-08T13:00:00"},
            {"id": 4, "published_at": "2026-10-01T10:00:00+08:00"},
        ]}}
        out = build_packet(src, slot="1135", now=NOW)
        self.assertEqual(len(out["blogger_yesterday"]), 1)
        self.assertIn("不能概括", out["blogger_yesterday"][0]["content_basis"])
        self.assertEqual(len(out["unqualified_news"]), 2)
        self.assertEqual(out["news"], [])

    def test_api_failure_is_not_all_holdings_removed(self):
        old = build_packet(self.source(), slot="1135", now=NOW)
        out = build_packet({"workspace": {"ok": False, "error": "offline"}}, slot="1440", now=NOW, previous=old)
        self.assertEqual(out["removed_since_previous"], [])
        self.assertFalse(out["source_status"]["workspace"]["ok"])
        self.assertIsNone(out["quantitative_evidence"]["win_rate"])

    def test_actions_preserve_server_dates(self):
        src = deepcopy(self.source())
        item = src["workspace"]["data"]["items"][0]
        item["gaps"] = []
        item["alerts"][0].update(data_as_of="2026-10-07", actionable_from="2026-10-08")
        out = build_packet(src, slot="1440", now=NOW)
        self.assertEqual(out["plan_review"][0]["system_alerts"], item["alerts"])

    def test_draft_and_intraday_cannot_pass_as_confirmed(self):
        for changed in ("draft", "intraday"):
            src = self.source()
            item = src["workspace"]["data"]["items"][0]
            item["gaps"] = []
            if changed == "draft":
                item["plan"]["state"] = "draft"
            else:
                item["technical"]["meta"]["is_intraday_forming"] = True
            out = build_packet(src, slot="1440", now=NOW)
            self.assertEqual(out["plan_review"][0]["system_alerts"], [])

    def test_trade_changes_do_not_invent_current_position(self):
        src = self.source()
        src["trades"] = {"ok": True, "data": {"trades": []}}
        old = build_packet(src, slot="1135", now=NOW)
        src["trades"]["data"]["trades"] = [{"trade_id": "t1", "fund_code": "123456", "side": "sell", "amount": 100, "price_status": "pending"}]
        out = build_packet(src, slot="1440", now=NOW, previous=old)
        self.assertEqual(out["trade_ledger"]["changes"][0]["kind"], "new")
        self.assertEqual(out["trade_ledger"]["pending_pricing"], ["t1"])
        self.assertEqual(out["holdings"], old["holdings"])
        self.assertNotIn("positions", out["trade_ledger"])
        src["trades"]["data"]["trades"][0]["price_status"] = "priced"
        revised = build_packet(src, slot="1440", now=NOW, previous=out)
        self.assertEqual(revised["trade_ledger"]["changes"][0]["kind"], "updated")

    def test_first_trade_read_and_failure_do_not_invent_changes(self):
        src = self.source()
        src["trades"] = {"ok": True, "data": {"trades": [{"trade_id": "t1"}]}}
        old = build_packet(src, slot="1135", now=NOW)
        self.assertEqual(old["trade_ledger"]["changes"], [])
        src["trades"] = {"ok": False, "error": "offline"}
        out = build_packet(src, slot="1440", now=NOW, previous=old)
        self.assertEqual(out["trade_ledger"]["changes"], [])
        self.assertFalse(out["trade_ledger"]["available"])

    def test_total_news_failure_is_saved_and_other_sources_remain(self):
        with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as folder:
            with patch("lei_signal.portfolio.briefing.refresh_news", side_effect=ImportError("collector unavailable")):
                fresh = collect_news_safely(Path(folder), NOW)
            saved = json.loads(Path(fresh["receipt_path"]).read_text())
            self.assertEqual(saved["status"], "failed")
            src = self.source()
            src["news"] = {"ok": False, "data": fresh}
            out = build_packet(src, slot="1440", now=NOW)
            self.assertEqual(len(out["holdings"]), 1)
            self.assertFalse(out["source_status"]["news"]["ok"])

    def test_news_truncation_cannot_look_complete(self):
        src = self.source()
        src["news"] = {"ok": True, "data": {"items": [], "total": 201}}
        out = build_packet(src, slot="1135", now=NOW)
        self.assertTrue(out["news_coverage"]["truncated"])

    def test_user_rationale_does_not_become_a_confirmed_plan(self):
        src = self.source()
        item = src["workspace"]["data"]["items"][0]
        item.update(code="123456", plan=None, gaps=[])
        context = {"fund_code": "123456", "stated_reason": "觉得低估，分批定投", "stop_condition": None}
        src["user_context"] = {"ok": True, "data": {"entries": [context]}}
        out = build_packet(src, slot="1440", now=NOW)
        self.assertEqual(out["plan_review"][0]["user_stated_context"], [context])
        self.assertIsNone(out["plan_review"][0]["plan"])
        self.assertEqual(out["plan_review"][0]["system_alerts"], [])
        self.assertIsNone(out["user_stated_context"][0]["stop_condition"])


if __name__ == "__main__":
    unittest.main()
