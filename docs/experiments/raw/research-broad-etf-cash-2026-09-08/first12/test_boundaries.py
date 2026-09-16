import importlib.util
import json
import sys
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("first12_runner", HERE / "run_accounts.py")
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)


class BoundaryTests(unittest.TestCase):
    def test_weekly_latest_and_2015_partial_first_week(self):
        rows = [
            {"date": "2014-12-31", "ma200_pct": 40},
            {"date": "2015-01-01", "ma200_pct": 50},
            {"date": "2015-01-02", "ma200_pct": None},
            {"date": "2015-01-09", "ma200_pct": 60},
        ]
        got = m.build_weekly_breadth(rows, "2015-01-01", "2015-01-31")
        self.assertEqual([(x["signal_date"], x["eligible_date"], x["target"]) for x in got],
                         [("2015-01-01", "2015-01-05", "0.5"), ("2015-01-09", "2015-01-12", "0")])

    def test_fee_affordability_and_band_only_when_requested(self):
        cash, units, trade, reason, *_ = m.execute_target(D("100000"), D("0"), D("0"), D("3.5"), D("1"), D(".001"))
        self.assertGreaterEqual(cash, 0); self.assertEqual(units % 100, 0); self.assertEqual(trade[0], "buy")
        # A full-exit signal must sell the small remainder; the 5pp band belongs only to breadth.
        result = m.execute_target(D("95000"), D("0"), D("100"), D("5"), D("0"), D(".001"), apply_band=False)
        self.assertEqual(result[2][0], "sell"); self.assertEqual(result[1], 0)
        held = m.execute_target(D("95000"), D("0"), D("100"), D("5"), D("0"), D(".001"), apply_band=True)
        self.assertEqual(held[3], "inside_5pp_band")

    def test_receivable_counts_as_equity_but_cannot_be_spent(self):
        cash, units, trade, _, equity, _ = m.execute_target(D("1000"), D("9000"), D("0"), D("10"), D("1"), D("0"))
        self.assertEqual(equity, D("10000")); self.assertEqual(units, D("100")); self.assertEqual(cash, D("0"))
        self.assertEqual(trade[1], D("100"))

    def test_periods_reconcile_from_true_initial_capital(self):
        daily = [
            {"date":"2015-01-02","equity":99900.,"dividends_received":10.,"units":100.},
            {"date":"2015-01-30","equity":101000.,"dividends_received":10.,"units":100.},
            {"date":"2015-02-02","equity":102000.,"dividends_received":15.,"units":100.},
        ]
        rows = m.period_rows(daily, [], "month")
        self.assertEqual(rows[0]["start_equity"], 100000.)
        self.assertAlmostEqual(sum(x["change"] for x in rows), 2000.)
        self.assertEqual([x["dividends_received"] for x in rows], [10., 5.])

    def test_drawdown_includes_initial_buy_fee(self):
        intervals = m.drawdown_intervals([{"date":"2015-01-05","equity":99900.}, {"date":"2015-01-06","equity":100100.}])
        self.assertAlmostEqual(intervals[0]["max_drawdown"], -.001)
        self.assertEqual(intervals[0]["recovery_date"], "2015-01-06")

    def test_frozen_breadth_hash(self):
        self.assertEqual(m.sha256(HERE / "inputs/a_share_breadth_33y_snapshot.json"),
                         "8fabf1882d1d04fa2912bfa7545d4c1216a23e964d0981b1addc7042f43b33ca")

    def test_weekend_signal_survives_and_dividend_receivable_survives_sale(self):
        symbol = "test"
        bars = [
            {"date":"2015-01-01","open":D("10"),"high":D("10"),"low":D("10"),"close":D("10"),"volume":D("1")},
            {"date":"2015-01-02","open":D("10"),"high":D("10"),"low":D("10"),"close":D("10"),"volume":D("1")},
            {"date":"2015-01-05","open":D("9"),"high":D("9"),"low":D("9"),"close":D("9"),"volume":D("1")},
            {"date":"2015-01-06","open":D("9"),"high":D("9"),"low":D("9"),"close":D("9"),"volume":D("1")},
        ]
        actions = [{"event_id":"d","symbol":symbol,"type":"cash_dividend","announcement_date":"2014-12-20",
                    "record_date":"2015-01-02","effective_date":"2015-01-05","pay_date":"2015-01-06",
                    "cash":"1","currency":"CNY"}]
        settings = {"blocked_dates":{},"limits":{symbol:.1},"limit_changes":{}}
        signals = [
            {"symbol":symbol,"signal_date":"2014-12-31","eligible_date":"2015-01-01","target":"1","reason":"buy"},
            {"symbol":symbol,"signal_date":"2015-01-02","eligible_date":"2015-01-03","target":"0","reason":"sell"},
        ]
        result = m.simulate("x", symbol, "simple_60_close_breakout", D("0"), bars, actions, settings, signals,
                            "2015-01-01", "2015-01-06")
        self.assertEqual([t["date"] for t in result["trades"]], ["2015-01-01", "2015-01-05"])
        self.assertEqual(result["summary"]["final_units"], 0)
        self.assertEqual(result["summary"]["dividends_received"], 10000)
        self.assertEqual(result["summary"]["final_equity"], 100000)
        self.assertTrue(any(r["date"] == "2015-01-03" and r["reason"] == "missing_quote" for r in result["rejected"]))

    def test_hold_ignores_technical_signal_and_starts_with_cash_calendar_rows(self):
        bars = [{"date":"2014-12-31","open":D("10"),"high":D("10"),"low":D("10"),"close":D("10"),"volume":D("1")},
                {"date":"2015-01-05","open":D("10"),"high":D("10"),"low":D("10"),"close":D("10"),"volume":D("1")}]
        settings={"blocked_dates":{},"limits":{"test":.1},"limit_changes":{}}
        rogue=[{"symbol":"test","signal_date":"2015-01-05","eligible_date":"2015-01-06","target":"0","reason":"rogue"}]
        result=m.simulate("h","test","hold",D("0"),bars,[],settings,rogue,"2015-01-01","2015-01-06")
        self.assertEqual(result["daily"][0]["date"], "2015-01-01")
        self.assertEqual(result["daily"][0]["cash"], 100000)
        self.assertEqual(len(result["trades"]), 1); self.assertEqual(result["trades"][0]["side"], "buy")

    def test_missing_breadth_week_cancels_blocked_old_order(self):
        bars=[]
        d=date.fromisoformat("2015-01-05")
        for _ in range(12):
            if d.weekday()<5:
                bars.append({"date":d.isoformat(),"open":D("10"),"high":D("10"),"low":D("10"),"close":D("10"),"volume":D("1")})
            d += m.timedelta(days=1)
        blocked=[b["date"] for b in bars if b["date"] <= "2015-01-09"]
        settings={"blocked_dates":{"test":blocked},"limits":{"test":.1},"limit_changes":{}}
        sig=[{"signal_date":"2015-01-02","eligible_date":"2015-01-05","target":"1","reason":"weekly_breadth_target"}]
        result=m.simulate("b","test","breadth_three_tier",D("0"),bars,[],settings,sig,"2015-01-05","2015-01-16")
        self.assertFalse(result["trades"])
        self.assertTrue(any(r["date"]=="2015-01-12" and r["reason"]=="stale_weekly_order_cancelled" for r in result["rejected"]))

    def test_suspension_close_is_absent_from_prepared_signal_dates(self):
        prepared=json.loads((HERE/"prepared-signals.json").read_text())
        self.assertNotIn("2021-02-08", {s["signal_date"] for s in prepared["breakout"]["sz159915"]})


if __name__ == "__main__":
    unittest.main()
