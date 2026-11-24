import json
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lei_signal.portfolio.briefing import (
    _news_since,
    _select_blogger_videos,
    blogger_window,
    build_packet,
    collect_news_safely,
    refresh_news,
)

NOW = datetime.fromisoformat("2026-10-08T14:40:00+08:00")


class PortfolioBriefingTests(unittest.TestCase):
    def source(self):
        return {
            "workspace": {
                "ok": True,
                "data": {
                    "as_of": "2026-09-04",
                    "coverage": {"total": 1},
                    "items": [
                        {
                            "holding_id": "h1",
                            "name": "示例基金",
                            "nav": {"value": 1.2, "date": "2026-09-30"},
                            "plan": {"plan_id": "p1", "state": "entered"},
                            "technical": {"meta": {"last_bar_date": "2026-09-30"}},
                            "status": "action_required",
                            "gaps": ["行情时点尚未核实"],
                            "alerts": [{"code": "STOP_PRICE_BREACHED"}],
                        }
                    ],
                },
            }
        }

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
        src["news"] = {
            "ok": True,
            "data": {
                "items": [
                    {
                        "id": 1,
                        "source": "bilibili",
                        "published_at": "2026-09-30T10:00:00+08:00",
                        "title": "仅标题",
                    },
                    {"id": 2, "published_at": "2026-10-08T16:00:00+08:00"},
                    {"id": 3, "published_at": "2026-10-08T13:00:00"},
                    {"id": 4, "published_at": "2026-10-01T10:00:00+08:00"},
                ]
            },
        }
        out = build_packet(src, slot="1135", now=NOW)
        self.assertEqual(len(out["blogger_yesterday"]), 1)
        self.assertIn("不能概括", out["blogger_yesterday"][0]["content_basis"])
        self.assertEqual(len(out["unqualified_news"]), 2)
        self.assertEqual(out["news"], [])

    def test_api_failure_is_not_all_holdings_removed(self):
        old = build_packet(self.source(), slot="1135", now=NOW)
        out = build_packet(
            {"workspace": {"ok": False, "error": "offline"}}, slot="1440", now=NOW, previous=old
        )
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
        src["trades"]["data"]["trades"] = [
            {
                "trade_id": "t1",
                "fund_code": "123456",
                "side": "sell",
                "amount": 100,
                "price_status": "pending",
            }
        ]
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
            with patch(
                "lei_signal.portfolio.briefing.refresh_news",
                side_effect=ImportError("collector unavailable"),
            ):
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
        context = {
            "fund_code": "123456",
            "stated_reason": "觉得低估，分批定投",
            "stop_condition": None,
        }
        src["user_context"] = {"ok": True, "data": {"entries": [context]}}
        out = build_packet(src, slot="1440", now=NOW)
        self.assertEqual(out["plan_review"][0]["user_stated_context"], [context])
        self.assertIsNone(out["plan_review"][0]["plan"])
        self.assertEqual(out["plan_review"][0]["system_alerts"], [])
        self.assertIsNone(out["user_stated_context"][0]["stop_condition"])

    def test_product_names_are_resolved_only_from_same_code_records(self):
        src = self.source()
        item = src["workspace"]["data"]["items"][0]
        item.update(code="123456", name=None, plan=None, gaps=[])
        item["nav"]["fund_name"] = "同代码基金"
        src["trades"] = {
            "ok": True,
            "data": {
                "trades": [
                    {
                        "trade_id": "t1",
                        "fund_code": "123456",
                        "fund_name": "另一显示名",
                        "price_status": "pending",
                    },
                    {
                        "trade_id": "t2",
                        "fund_code": "654321",
                        "fund_name": "654321",
                        "price_status": "pending",
                    },
                ]
            },
        }
        out = build_packet(src, slot="1440", now=NOW)
        self.assertEqual(out["holdings"][0]["display_name"], "同代码基金")
        self.assertEqual(out["trade_ledger"]["records"][0]["display_name"], "同代码基金")
        self.assertEqual(out["trade_ledger"]["records"][1]["display_name"], "名称未知")
        self.assertEqual(out["plan_review"][0]["display_name"], "同代码基金")

    def test_changes_and_removed_rows_include_product_name(self):
        src = self.source()
        src["workspace"]["data"]["items"][0]["code"] = "123456"
        old = build_packet(src, slot="1135", now=NOW)
        prev = deepcopy(old)
        prev["holdings"][0]["holding_id"] = "removed"
        src["workspace"]["data"]["items"][0]["nav"]["value"] = 1.3
        out = build_packet(src, slot="1440", now=NOW, previous=prev)
        self.assertEqual(out["changes"][0]["display_name"], "示例基金")
        self.assertEqual(out["removed_since_previous"][0]["display_name"], "示例基金")


if __name__ == "__main__":
    unittest.main()


class BloggerTradingDayTests(unittest.TestCase):
    def test_calendar_handles_monday_long_holiday_and_makeup_weekend(self):
        cases = {
            "2026-10-08T11:35:00+08:00": "2026-09-30",
            "2026-10-12T11:35:00+08:00": "2026-10-09",
            "2026-10-10T11:35:00+08:00": "2026-10-09",
            "2026-10-09T11:35:00+08:00": "2026-10-08",
            "2026-10-11T16:10:00+00:00": "2026-10-09",
            "2026-09-28T11:35:00+08:00": "2026-09-24",
        }
        for stamp, expected in cases.items():
            window = blogger_window(datetime.fromisoformat(stamp))
            self.assertEqual(window["status"], "verified")
            self.assertEqual(window["date"], expected)
            self.assertTrue(window["calendar_source"].startswith("https://www.sse.com.cn/"))

    def test_missing_or_uncovered_calendar_never_guesses_yesterday(self):
        self.assertEqual(
            blogger_window(datetime.fromisoformat("2027-01-04T11:35:00+08:00"))["status"],
            "unavailable",
        )
        self.assertEqual(
            blogger_window(datetime.fromisoformat("2026-01-01T11:35:00+08:00"))["date"], None
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "calendar.json"
            self.assertEqual(blogger_window(NOW, path)["status"], "unavailable")
            path.write_text('{"schema_version": 1, "market": "wrong"}')
            self.assertIsNone(blogger_window(NOW, path)["date"])

    def test_target_video_day_is_separate_from_current_news(self):
        src = {
            "news": {
                "ok": True,
                "data": {
                    "items": [
                        {
                            "id": 1,
                            "source": "bilibili",
                            "published_at": "2026-09-30T23:59:59+08:00",
                        },
                        {
                            "id": 2,
                            "source": "bilibili",
                            "published_at": "2026-10-07T10:00:00+08:00",
                        },
                        {
                            "id": 3,
                            "source": "eastmoney",
                            "published_at": "2026-10-07T10:00:00+08:00",
                        },
                        {"id": 4, "source": "bilibili", "published_at": "2026-09-30T16:00:00Z"},
                    ]
                },
            }
        }
        out = build_packet(src, slot="1135", now=NOW)
        self.assertEqual([x["id"] for x in out["blogger_previous_trading_day"]], [1])
        self.assertEqual([x["id"] for x in out["news"]], [3])
        self.assertEqual(out["blogger_window"]["date"], "2026-09-30")
        self.assertEqual(_news_since(NOW), "2026-09-30")
        self.assertEqual(out["blogger_yesterday"], out["blogger_previous_trading_day"])

    def test_latest_list_boundary_is_not_claimed_complete(self):
        window = blogger_window(NOW)
        stamp = int(datetime.fromisoformat("2026-10-07T10:00:00+08:00").timestamp())
        selected, coverage = _select_blogger_videos([{"created": stamp}] * 10, window)
        self.assertEqual(selected, [])
        self.assertTrue(coverage["target_may_be_truncated"])

    def test_refresh_replays_target_date_without_old_watermark_filter(self):
        videos = [
            {
                "bvid": "target",
                "title": "target",
                "description": "",
                "duration": 100,
                "created": int(datetime.fromisoformat("2026-09-30T20:00:00+08:00").timestamp()),
            },
            {
                "bvid": "holiday",
                "title": "holiday",
                "description": "",
                "duration": 100,
                "created": int(datetime.fromisoformat("2026-10-07T20:00:00+08:00").timestamp()),
            },
        ]
        with (
            TemporaryDirectory() as tmp,
            patch(
                "lei_signal.newsfeed.config_loader.load_config",
                return_value={"bili_ups": [{"mid": 1, "name": "author"}]},
            ),
            patch("lei_signal.newsfeed.pipeline._collect_all", return_value=({}, [])) as ordinary,
            patch(
                "lei_signal.newsfeed.sources.bilibili.BilibiliClient.__init__", return_value=None
            ),
            patch(
                "lei_signal.newsfeed.sources.bilibili.BilibiliClient.fetch_up_videos",
                return_value=videos,
            ) as listing,
            patch(
                "lei_signal.newsfeed.sources.bilibili.BilibiliClient.fetch_video_detail",
                return_value={},
            ) as detail,
        ):
            out = refresh_news(Path(tmp), NOW)
            self.assertEqual(out["receipt"]["blogger_window"]["date"], "2026-09-30")
            self.assertEqual([x["title"] for x in out["items"]], ["target"])
            listing.assert_called_once_with(1, limit=10)
            detail.assert_called_once_with("target")
            self.assertEqual(ordinary.call_args.args[1]["bili_ups"], [])
            self.assertFalse(out["receipt"]["production_news_database_updated"])
