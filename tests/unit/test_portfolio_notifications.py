import unittest

from lei_signal.portfolio.notifications import compare, extract_facts


def packet():
    return {
        "generated_at": "2026-10-08T09:10:00+08:00",
        "source_status": {"workspace": {"ok": True}, "plans": {"ok": True}, "trades": {"ok": True}},
        "coverage": {"total": 1},
        "holdings": [{"holding_id": "h1", "name": "示例基金", "facts": {"gaps": ["缺少计划"]}}],
        "news_coverage": {"last_run": {"errors": [{"source": "bili", "error": "HTTP 412"}]}},
        "trade_ledger": {"available": True, "records": []},
        "plan_review": [],
    }


class NotificationTests(unittest.TestCase):
    def test_known_initial_gaps_do_not_create_a_flood(self):
        report, state = compare(packet())
        self.assertTrue(report["initial_baseline"])
        self.assertFalse(report["should_notify"])
        again, _ = compare(packet(), state)
        self.assertEqual(again["events"], [])

    def test_new_failure_repeats_quietly_then_recovery_is_visible(self):
        p = packet()
        _, old = compare(p)
        p["source_status"]["workspace"] = {"ok": False, "error": "offline"}
        p.update(coverage={}, holdings=[])
        report, failed = compare(p, old)
        self.assertEqual([e["fact_key"] for e in report["events"]], ["source:workspace"])
        self.assertFalse(compare(p, failed)[0]["should_notify"])
        recovered, _ = compare(packet(), failed)
        self.assertEqual([e["fact_key"] for e in recovered["events"]], ["source:workspace"])

    def test_dates_and_error_wording_do_not_repeatedly_alert(self):
        p = packet()
        _, old = compare(p)
        p["generated_at"] = "2026-10-09T17:10:00+08:00"
        p["source_status"]["workspace"]["retrieved_at"] = p["generated_at"]
        p["news_coverage"]["last_run"]["errors"][0]["error"] = "HTTP 412: request 999"
        self.assertFalse(compare(p, old)[0]["should_notify"])

    def test_trade_pending_and_pricing_change_are_separate(self):
        p = packet()
        _, old = compare(p)
        p["trade_ledger"]["records"] = [
            {"trade_id": "t1", "fund_name": "示例基金", "price_status": "pending"}
        ]
        report, pending = compare(p, old)
        self.assertEqual(report["events"][0]["after"]["category"], "trade_record")
        p["trade_ledger"]["records"][0]["price_status"] = "priced"
        report, _ = compare(p, pending)
        self.assertEqual(report["events"][0]["before"]["value"]["price_status"], "pending")

    def test_intraday_or_missing_plan_does_not_invent_recovery(self):
        p = packet()
        p["plan_review"] = [
            {
                "name": "示例基金",
                "plan": {"plan_id": "p1", "state": "entered"},
                "state": "按系统原计划逐项复核",
                "gaps": [],
                "system_alerts": [
                    {"code": "STOP_PRICE_BREACHED", "severity": "block", "data_as_of": "2026-10-07"}
                ],
            }
        ]
        _, old = compare(p)
        p["plan_review"][0].update(
            state="原计划或可用行情不足，不能判定安全或失效", system_alerts=[]
        )
        report, current = compare(p, old)
        self.assertEqual(report["events"], [])
        self.assertEqual(
            current["facts"]["plan:p1"]["fingerprint"], old["facts"]["plan:p1"]["fingerprint"]
        )

    def test_new_confirmed_alert_and_material_change_only(self):
        p = packet()
        p["plan_review"] = [
            {
                "name": "示例基金",
                "plan": {"plan_id": "p1", "state": "entered", "stop_price": 1.0},
                "state": "按系统原计划逐项复核",
                "gaps": [],
                "system_alerts": [],
            }
        ]
        _, old = compare(p)
        p["plan_review"][0]["system_alerts"] = [
            {
                "code": "STOP_PRICE_BREACHED",
                "severity": "block",
                "data_as_of": "2026-10-07",
                "actionable_from": "2026-10-08",
            }
        ]
        report, changed = compare(p, old)
        self.assertEqual(len(report["events"]), 1)
        self.assertEqual(
            report["events"][0]["after"]["evidence"]["alerts"][0]["actionable_from"], "2026-10-08"
        )
        p["plan_review"][0]["system_alerts"][0]["data_as_of"] = "2026-10-08"
        self.assertFalse(compare(p, changed)[0]["should_notify"])

    def test_offline_trades_do_not_look_like_sellout(self):
        p = packet()
        p["trade_ledger"]["records"] = [{"trade_id": "t1", "price_status": "priced"}]
        _, old = compare(p)
        p["trade_ledger"] = {"available": False, "records": []}
        report, state = compare(p, old)
        self.assertEqual(report["events"], [])
        self.assertIn("trade:t1", state["facts"])

    def test_stale_packet_or_unknown_state_cannot_replace_baseline(self):
        p = packet()
        _, old = compare(p)
        p["generated_at"] = "2026-10-07T09:10:00+08:00"
        with self.assertRaises(ValueError):
            compare(p, old)
        with self.assertRaises(ValueError):
            compare(packet(), {"schema_version": 99})

    def test_quality_changes_not_price_moves_are_notifications(self):
        p = packet()
        p["market_background"] = {
            "cn": {
                "ok": True,
                "data": {
                    "items": [
                        {"metric_id": "example", "quality_status": "time_unverified", "value": 1}
                    ]
                },
            }
        }
        _, old = compare(p)
        p["market_background"]["cn"]["data"]["items"][0]["value"] = 2
        self.assertFalse(compare(p, old)[0]["should_notify"])
        p["market_background"]["cn"]["data"]["items"][0]["quality_status"] = "missing"
        self.assertTrue(compare(p, old)[0]["should_notify"])

    def test_notification_titles_use_display_names_and_unknown_is_explicit(self):
        p = packet()
        p["holdings"][0]["display_name"] = "代码对应基金"
        p["trade_ledger"]["records"] = [
            {
                "trade_id": "t1",
                "fund_code": "123456",
                "display_name": "代码对应基金",
                "price_status": "pending",
            }
        ]
        facts = extract_facts(p)
        self.assertEqual(facts["gaps:h1"]["title"], "代码对应基金资料缺口变化")
        self.assertEqual(facts["trade:t1"]["title"], "代码对应基金成交台账变化")

        p["trade_ledger"]["records"][0].pop("display_name")
        facts = extract_facts(p)
        self.assertEqual(facts["trade:t1"]["title"], "名称未知成交台账变化")


if __name__ == "__main__":
    unittest.main()
