import importlib.util
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reinvest_runner", HERE / "run_accounts_attempt03.py")
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)


def bar(day, price="10"):
    p = D(price)
    return {"date": day, "open": p, "high": p, "low": p, "close": p, "volume": D("1")}


def dividend(event_id, record, effective, pay, cash="1"):
    return {"event_id": event_id, "symbol": "test", "type": "cash_dividend",
            "record_date": record, "effective_date": effective, "pay_date": pay,
            "cash": cash, "currency": "CNY"}


def run(bars, actions, end=None, blocked=None, cash="100000"):
    settings = {"blocked_dates": {"test": blocked or []}, "limits": {"test": .1}, "limit_changes": {}}
    result = m.simulate("x", "test", "hold_dividend_reinvest", D("0"), bars, actions,
                        settings, [], bars[0]["date"], end or bars[-1]["date"])
    return result


class ReinvestmentTests(unittest.TestCase):
    def test_csv_fields_cover_initial_and_reinvestment_rows(self):
        self.assertEqual(m.csv_fieldnames([{"a": 1}, {"a": 2, "payment_sources": []}]),
                         ["a", "payment_sources"])

    def test_effective_date_receivable_cannot_buy_before_payment(self):
        bars = [bar("2015-01-01"), bar("2015-01-02"), bar("2015-01-05")]
        got = run(bars, [dividend("d1", "2015-01-01", "2015-01-02", "2015-01-05")])
        self.assertEqual([t["date"] for t in got["trades"]], ["2015-01-01", "2015-01-05"])
        self.assertGreater(got["daily"][1]["receivable"], 0)

    def test_payment_day_executes_and_blocked_payment_delays(self):
        bars = [bar("2015-01-01"), bar("2015-01-02"), bar("2015-01-05"), bar("2015-01-06")]
        action = dividend("d1", "2015-01-01", "2015-01-02", "2015-01-05")
        direct = run(bars, [action])
        delayed = run(bars, [action], blocked=["2015-01-05"])
        self.assertEqual(direct["trades"][1]["date"], "2015-01-05")
        self.assertEqual(delayed["trades"][1]["date"], "2015-01-06")
        self.assertEqual(delayed["trades"][1]["payment_sources"][0]["event_id"], "d1")

    def test_below_one_lot_waits_for_next_positive_payment(self):
        bars = [bar("2015-01-01", "1000"), bar("2015-01-02", "1000"), bar("2015-01-05", "1000"),
                bar("2015-01-06", "1000"), bar("2015-01-07", "1000"), bar("2015-01-08", "1000")]
        actions = [dividend("d1", "2015-01-01", "2015-01-02", "2015-01-05", "1"),
                   dividend("d2", "2015-01-06", "2015-01-07", "2015-01-08", "1000")]
        got = run(bars, actions)
        self.assertTrue(any(r["reason"] == "reinvestment_below_one_lot" and r["date"] == "2015-01-05" for r in got["rejected"]))
        self.assertEqual(got["trades"][-1]["date"], "2015-01-08")

    def test_multiple_payments_merge_while_blocked(self):
        bars = [bar("2015-01-01"), bar("2015-01-02"), bar("2015-01-05"), bar("2015-01-06")]
        actions = [dividend("d1", "2015-01-01", "2015-01-02", "2015-01-05"),
                   dividend("d2", "2015-01-01", "2015-01-02", "2015-01-06")]
        got = run(bars, actions, blocked=["2015-01-05"])
        self.assertEqual([x["event_id"] for x in got["trades"][-1]["payment_sources"]], ["d1", "d2"])

    def test_no_dividend_matches_hold(self):
        bars = [bar("2015-01-01"), bar("2015-01-02")]
        settings = {"blocked_dates": {}, "limits": {"test": .1}, "limit_changes": {}}
        a = m.simulate("x", "test", "hold_dividend_reinvest", D(".001"), bars, [], settings, [], "2015-01-01", "2015-01-02")
        b = m.simulate("x", "test", "hold", D(".001"), bars, [], settings, [], "2015-01-01", "2015-01-02")
        self.assertEqual(a["daily"], b["daily"])
        self.assertEqual(a["trades"], b["trades"])
        aa, bb = dict(a["summary"]), dict(b["summary"])
        aa.pop("method"); bb.pop("method")
        self.assertEqual(aa, bb)

    def test_new_units_receive_next_record_dividend(self):
        bars = [bar("2015-01-01"), bar("2015-01-02"), bar("2015-01-05"), bar("2015-01-06"),
                bar("2015-01-07"), bar("2015-01-08")]
        actions = [dividend("d1", "2015-01-01", "2015-01-02", "2015-01-05"),
                   dividend("d2", "2015-01-06", "2015-01-07", "2015-01-08")]
        got = run(bars, actions)
        self.assertGreater(got["trades"][2]["shares"], got["trades"][1]["shares"])

    def test_zero_entitlement_does_not_trigger_and_terminal_pending_is_preserved(self):
        bars = [bar("2015-01-02"), bar("2015-01-05"), bar("2015-01-06")]
        no_right = dividend("d0", "2015-01-01", "2015-01-02", "2015-01-05")
        self.assertEqual(len(run(bars, [no_right])["trades"]), 1)
        entitled = dividend("d1", "2015-01-02", "2015-01-05", "2015-01-06")
        got = run(bars, [entitled], blocked=["2015-01-06"])
        self.assertTrue(any(r["reason"] == "pending_at_period_end" for r in got["rejected"]))


if __name__ == "__main__":
    unittest.main()
