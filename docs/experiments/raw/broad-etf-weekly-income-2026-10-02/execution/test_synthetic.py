"""One bounded synthetic suite; no archived market bars are loaded."""
from __future__ import annotations

import unittest
from decimal import Decimal as D
from weekly_accounts import calendar, income_days, simulate, xirr, drawdown, period_rows
from legacy_primitives import execute_target

SYM = "sh510300"


def bar(day, price, close=None, high=None, low=None):
    p = D(str(price))
    return {"date": day, "open": p, "close": D(str(close)) if close is not None else p,
            "high": D(str(high)) if high is not None else p,
            "low": D(str(low)) if low is not None else p, "volume": D("1000")}


def signal(day, eligible, target, source_week=None):
    row = {"signal_date": day, "eligible_date": eligible, "target": str(target), "reason": "synthetic_frozen_signal"}
    if source_week: row["source_week"] = list(source_week)
    return row


def settings(blocked=(), no_mark=()):
    return {"blocked_dates": {SYM: list(blocked)}, "limits": {SYM: 10}, "limit_changes": {},
            "dated_restrictions": [{"symbol": SYM, "date": d, "close_mark_allowed": False} for d in no_mark]}


def run(method="hold", bars=(), signals=(), actions=(), start="2024-01-01", end="2024-01-10",
        income="250", fee="0"):
    return simulate(SYM, method, fee, list(bars), list(actions), settings(), list(signals), start, end, D(income))


class SyntheticAcceptance(unittest.TestCase):
    def test_01_calendar_and_unfunded(self):
        days = income_days()
        self.assertEqual((len(days), days[0], days[-1]), (600, "2015-01-05", "2026-06-29"))
        r = run(start="2015-01-01", end="2015-01-06", bars=[bar("2015-01-05", 2)])
        self.assertEqual([x["equity"] for x in r["daily"][:4]], [0.0]*4)
        self.assertTrue(all(x["nav"] is None for x in r["daily"][:4]))
        self.assertEqual(r["summary"]["unfunded_days"], 4)

    def test_02_first_fee_lot_and_no_daily_retry(self):
        r = run(start="2024-01-01", end="2024-01-02", fee="0.001", bars=[bar("2024-01-01", 2)])
        self.assertEqual((r["daily"][0]["units"], r["daily"][0]["cash"]), (100.0, 49.8))
        self.assertAlmostEqual(r["daily"][0]["nav"], 0.9992)
        r = run(start="2024-01-01", end="2024-01-09", bars=[bar("2024-01-01", 3), bar("2024-01-02", 2), bar("2024-01-08", 2)])
        self.assertEqual([t["date"] for t in r["trades"]], ["2024-01-08"])

    def test_03_unit_nav_and_xirr(self):
        self.assertAlmostEqual(xirr([("2023-01-01", D("100"))], "2024-01-01", D("110"))["rate"], 0.1, places=11)
        r = run(start="2024-01-01", end="2024-01-08", bars=[bar("2024-01-01", 1), bar("2024-01-07", 1), bar("2024-01-08", 1)], income="100")
        self.assertAlmostEqual(r["summary"]["unit_cumulative_return"], 0)
        self.assertAlmostEqual(r["summary"]["xirr"]["rate"], 0, places=10)
        # The second deposit uses the preceding booked unit value, not today's price.
        values = r["daily"]
        self.assertEqual(values[-1]["account_units"], 200.0)
        self.assertEqual(values[-1]["nav"], 1.0)

    def test_04_active60_and_exit_priority(self):
        s = [signal("2023-12-31", "2024-01-01", 1)]
        r = run(method="simple_60_close_breakout", start="2024-01-01", end="2024-01-08",
                bars=[bar("2024-01-01", 3), bar("2024-01-08", 2)], signals=s)
        self.assertTrue(r["daily"][0]["active60"])
        self.assertEqual([t["date"] for t in r["trades"]], ["2024-01-08"])
        s += [signal("2024-01-01", "2024-01-02", 0)]
        r = run(method="simple_60_close_breakout", start="2024-01-01", end="2024-01-08",
                bars=[bar("2024-01-02", 2), bar("2024-01-08", 2)], signals=s)
        self.assertEqual(len([t for t in r["trades"] if t["side"] == "buy"]), 0)
        self.assertFalse(r["daily"][-1]["active60"])
        self.assertTrue(any(x["reason"] == "replaced_by_new_target" for x in r["rejected"]))
        # A blocked exit leaves shares, but active60 remains false and new money stays cash.
        r = simulate(SYM, "simple_60_close_breakout", "0",
                     [bar("2024-01-01", 2), bar("2024-01-02", 2), bar("2024-01-08", 2)], [],
                     settings(blocked=["2024-01-02", "2024-01-08"]), s,
                     "2024-01-01", "2024-01-08")
        self.assertEqual(r["daily"][-1]["units"], 100.0)
        self.assertFalse(r["daily"][-1]["active60"])
        self.assertEqual(len([t for t in r["trades"] if t["side"] == "buy"]), 1)

    def test_05_dividend_right_receivable_payment(self):
        action = {"symbol": SYM, "event_id": "d1", "type": "cash_dividend", "record_date": "2024-01-01",
                  "effective_date": "2024-01-02", "pay_date": "2024-01-03", "cash": "1"}
        r = run(bars=[bar("2024-01-01", 10), bar("2024-01-02", 9), bar("2024-01-03", 9)],
                actions=[action], income="1000", end="2024-01-03")
        d = {row["date"]: row for row in r["daily"]}
        self.assertEqual((d["2024-01-02"]["units"], d["2024-01-02"]["receivable"]), (100.0, 100.0))
        self.assertEqual(d["2024-01-02"]["equity"], 1000.0)
        self.assertEqual((d["2024-01-03"]["receivable"], d["2024-01-03"]["cash"]), (0.0, 100.0))
        self.assertEqual(d["2024-01-03"]["equity"], 1000.0)
        self.assertEqual(len(r["trades"]), 1)
        same_day = dict(action, pay_date="2024-01-02")
        r2 = run(bars=[bar("2024-01-01", 10), bar("2024-01-02", 9)],
                 actions=[same_day], income="1000", end="2024-01-02")
        self.assertEqual((r2["daily"][-1]["cash"], r2["daily"][-1]["receivable"]), (100.0, 0.0))

    def test_06_breadth_band_missing_week_and_retry(self):
        s = [signal("2023-12-31", "2024-01-01", 1, (2023, 52))]
        r = run(method="breadth_three_tier", bars=[bar("2024-01-01", 3), bar("2024-01-02", 2), bar("2024-01-08", 2)], signals=s, end="2024-01-08")
        self.assertEqual(len(r["trades"]), 0)
        self.assertTrue(any(x["reason"] == "stale_weekly_order_cancelled" for x in r["rejected"]) is False)
        self.assertTrue(any(x["reason"] == "buy_rounds_to_zero_or_cash_short" for x in r["rejected"]))
        # Missing next completed week cancels a still-blocked target, even with new cash.
        r_missing = simulate(SYM, "breadth_three_tier", "0", [bar("2024-01-08", 2)], [],
                             settings(), s, "2024-01-01", "2024-01-08")
        self.assertTrue(any(x["reason"] == "stale_weekly_order_cancelled" for x in r_missing["rejected"]))
        s2 = [signal("2024-01-07", "2024-01-08", 1, (2024, 1))]
        r2 = run(method="breadth_three_tier", bars=[bar("2024-01-08", 2)], signals=s2, start="2024-01-08", end="2024-01-08")
        self.assertEqual(len(r2["trades"]), 1)
        self.assertEqual(len(r2["orders"]), 1)
        # Exactly five percentage points is evaluated; less than five is consumed.
        inside = execute_target(D("4.9"), D("0"), D("95.1"), D("1"), D("1"), D("0"), True, D("0.1"))
        edge = execute_target(D("5"), D("0"), D("95"), D("1"), D("1"), D("0"), True, D("0.1"))
        self.assertEqual(inside[3], "inside_5pp_band")
        self.assertNotEqual(edge[3], "inside_5pp_band")

    def test_07_future_data_and_limits(self):
        bars1 = [bar("2024-01-01", 2, close=2, high=2, low=2)]
        bars2 = [bar("2024-01-01", 2, close=9, high=20, low=0.1)]
        a = run(bars=bars1, end="2024-01-01")["trades"]
        b = run(bars=bars2, end="2024-01-01")["trades"]
        self.assertEqual([(x["side"], x["shares"], x["price"]) for x in a], [(x["side"], x["shares"], x["price"]) for x in b])
        with self.assertRaisesRegex(RuntimeError, "market signal must precede"):
            run(method="simple_60_close_breakout", signals=[signal("2024-01-01", "2024-01-01", 1)],
                bars=bars1, end="2024-01-01")
        r = simulate(SYM, "hold", "0", [bar("2024-01-01", 2), bar("2024-01-02", 2)], [],
                     settings(blocked=["2024-01-01"], no_mark=["2024-01-01"]), [], "2024-01-01", "2024-01-02")
        self.assertEqual([t["date"] for t in r["trades"]], ["2024-01-02"])
        self.assertTrue(any(x["reason"] == "known_open_unavailable" for x in r["rejected"]))

    def test_08_full_ledger(self):
        r = run(bars=[bar("2024-01-01", 2), bar("2024-01-08", 2)], end="2024-01-10", fee="0.001")
        d = r["daily"]
        self.assertEqual(sum(x["external_income"] for x in d), r["summary"]["total_external_income"])
        for row in d:
            self.assertAlmostEqual(row["equity"], row["cash"] + row["receivable"] + row["market_value"])
        self.assertAlmostEqual(sum(x["net_gain"] for x in r["monthly"]), r["summary"]["net_gain"])
        self.assertEqual(len({t["order_id"] for t in r["trades"]}), len(r["trades"]))
        self.assertTrue(all(t["trigger_type"] in ("funding_00", "market_signal") for t in r["trades"]))

    def test_09_nonpar_issuance_and_new_money_earnings(self):
        r = run(bars=[bar("2024-01-01", 1), bar("2024-01-08", 1, close=1.1)],
                end="2024-01-08", income="100")
        self.assertEqual(r["daily"][-1]["equity"], 220)
        self.assertEqual(r["daily"][-1]["account_units"], 200)
        self.assertAlmostEqual(r["daily"][-1]["nav"], 1.1)
        r = run(bars=[bar("2024-01-01", 1, close=1.2), bar("2024-01-08", 1.2)],
                end="2024-01-08", income="100")
        self.assertAlmostEqual(r["daily"][-1]["account_units"], 100+100/1.2)
        self.assertAlmostEqual(r["daily"][-1]["nav"], 1.2)

    def test_10_period_denominator_and_initial_fee(self):
        rows = [{"date":"2023-12-01", "equity":99.92, "external_income":100, "nav":.9992},
                {"date":"2023-12-31", "equity":110, "external_income":0, "nav":1.1},
                {"date":"2024-01-01", "equity":121, "external_income":0, "nav":1.21},
                {"date":"2024-01-31", "equity":110, "external_income":0, "nav":1.1}]
        years = period_rows(rows, "year")
        self.assertAlmostEqual(years[0]["unit_return"], .1)
        self.assertAlmostEqual(years[1]["unit_return"], 0)
        first = run(bars=[bar("2024-01-01", 2)], fee=".001", end="2024-01-01")
        self.assertAlmostEqual(first["yearly"][0]["unit_return"], -.0008)

    def test_11_initial_fee_distinct_valleys_and_equal_high(self):
        rows = [{"date":f"2024-01-{i:02}", "nav":v} for i,v in
                enumerate([.9992, 1, 1, .8, 1, 1, .9, 1], 1)]
        deepest, intervals = drawdown(rows)
        self.assertAlmostEqual(deepest, -.2)
        self.assertEqual([r["valley_date"] for r in intervals], ["2024-01-01","2024-01-04","2024-01-07"])
        self.assertEqual([r["start_date"] for r in intervals], ["2024-01-01","2024-01-03","2024-01-06"])
        self.assertEqual([r["recovery_days"] for r in intervals], [1,2,2])

    def test_12_payment_without_quote_and_unsafe_effective_mark(self):
        a = {"symbol":SYM,"event_id":"d","type":"cash_dividend","record_date":"2024-01-01",
             "effective_date":"2024-01-02","pay_date":"2024-01-03","cash":"1"}
        r = run(bars=[bar("2024-01-01",10),bar("2024-01-02",9)], actions=[a],income="1000",end="2024-01-03")
        self.assertEqual(r["daily"][-1]["equity"], 1000)
        self.assertEqual(r["daily"][-1]["cash"], 100)
        for bars, config in [([bar("2024-01-01",10)], settings()),
                             ([bar("2024-01-01",10),bar("2024-01-02",9)], settings(no_mark=["2024-01-02"]))]:
            with self.assertRaisesRegex(RuntimeError,"qualified ex-date mark"):
                simulate(SYM,"hold","0",bars,[a],config,[],"2024-01-01","2024-01-03",D("1000"))

    def test_13_sold_rights_and_split(self):
        a = {"symbol":SYM,"event_id":"d","type":"cash_dividend","record_date":"2024-01-01",
             "effective_date":"2024-01-02","pay_date":"2024-01-03","cash":"1"}
        sig = [signal("2023-12-31","2024-01-01",1),signal("2024-01-01","2024-01-02",0)]
        r = run(method="simple_60_close_breakout",bars=[bar("2024-01-01",10),bar("2024-01-02",9)],
                actions=[a], signals=sig, income="1000",end="2024-01-03")
        self.assertEqual(r["daily"][1]["receivable"],100)
        self.assertEqual(r["daily"][-1]["units"],0)
        self.assertEqual(r["daily"][-1]["cash"],1000)
        split = {"symbol":SYM,"event_id":"s","type":"split","effective_date":"2024-01-02","ratio":"2"}
        r = run(bars=[bar("2024-01-01",10),bar("2024-01-02",5)],actions=[split],income="1000",end="2024-01-02")
        self.assertEqual(r["daily"][-1]["units"],200)
        self.assertEqual(r["daily"][-1]["equity"],1000)

    def test_14_unfinished_week_candidate_identity(self):
        sig = signal("2026-06-30","2026-07-06",1,(2026,27))
        r = run(method="breadth_three_tier",signals=[sig],start="2026-06-29",end="2026-06-30")
        rejected = [x for x in r["rejected"] if x["reason"]=="signal_after_period_end"]
        self.assertEqual(rejected[0]["source_signal"],sig)
        self.assertTrue(rejected[0]["unfinished_source_week_candidate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
