import copy
import unittest

from metrics import summarize


class SummarizeMetricsTest(unittest.TestCase):
    def test_deposit_only_nav_unchanged(self):
        result = {
            "daily": [
                {
                    "date": "2026-09-01",
                    "equity": 1000.0,
                    "assets": 0.0,
                    "cash": 1000.0,
                    "receivable": 0.0,
                    "total_funding": 1000.0,
                    "nav": 1.0,
                    "fees": 3.0,
                },
                {
                    "date": "2026-09-02",
                    "equity": 1100.0,
                    "assets": 0.0,
                    "cash": 1100.0,
                    "receivable": 0.0,
                    "total_funding": 1100.0,
                    "nav": 1.0,
                    "fees": 4.0,
                },
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertEqual(metrics["max_drawdown"], 0.0)
        self.assertEqual(metrics["longest_drawdown_days"], 0)
        self.assertFalse(metrics["unrecovered_at_end"])
        self.assertEqual(metrics["net_gain"], 0.0)
        self.assertEqual(metrics["mean_exposure"], 0.0)
        self.assertEqual(metrics["trade_count"], 0)

    def test_open_positions_excluded_from_closed(self):
        result = {
            "daily": [
                {
                    "date": "2026-09-01",
                    "equity": 1000.0,
                    "assets": 100.0,
                    "cash": 900.0,
                    "receivable": 0.0,
                    "total_funding": 1000.0,
                    "nav": 1.0,
                    "fees": 0.0,
                }
            ],
            "trades": [
                {"side": "buy", "fee": 0.1},
                {"side": "sell", "fee": 0.1},
            ],
            "roundtrips": [
                {
                    "closed": True,
                    "net_pnl": 15.0,
                    "net_return": 0.012,
                    "entry_date": "2026-09-01",
                    "exit_date": "2026-09-03",
                    "valuation_date": "2026-09-03",
                },
                {
                    "closed": False,
                    "net_pnl": 0.0,
                    "net_return": 0.0,
                    "entry_date": "2026-09-02",
                    "exit_date": "2026-09-10",
                    "valuation_date": "2026-09-10",
                },
            ],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertEqual(metrics["completed_trades"], 1)
        self.assertEqual(metrics["open_positions"], 1)
        self.assertEqual(metrics["profitable_closed_count"], 1)
        self.assertAlmostEqual(metrics["closed_mean_net_pnl"], 15.0)
        self.assertEqual(metrics["mean_holding_days"], 2.0)

    def test_drawdown_recovery_then_new_peak_and_unresolved_tail(self):
        result = {
            "daily": [
                {"date": "2026-09-01", "equity": 1000.0, "assets": 0.0, "cash": 1000.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 1.0, "fees": 0.0},
                {"date": "2026-09-02", "equity": 900.0, "assets": 0.0, "cash": 900.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 0.9, "fees": 0.0},
                {"date": "2026-09-03", "equity": 850.0, "assets": 0.0, "cash": 850.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 0.85, "fees": 0.0},
                {"date": "2026-09-04", "equity": 950.0, "assets": 0.0, "cash": 950.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 0.95, "fees": 0.0},
                {"date": "2026-09-05", "equity": 1200.0, "assets": 0.0, "cash": 1200.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 1.2, "fees": 0.0},
                {"date": "2026-09-06", "equity": 800.0, "assets": 300.0, "cash": 500.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 0.9, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertAlmostEqual(metrics["max_drawdown"], 0.25)
        self.assertEqual(metrics["longest_drawdown_days"], 4)
        self.assertTrue(metrics["unrecovered_at_end"])
        self.assertEqual(metrics["order_status_counts"], {})

    def test_longest_drawdown_days_uses_prior_peak_anchor_for_recovered_case(self):
        result = {
            "daily": [
                {"date": "2020-01-01", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
                {"date": "2020-01-02", "equity": 50.0, "assets": 0.0, "cash": 50.0, "receivable": 0.0, "total_funding": 100.0, "nav": 0.5, "fees": 0.0},
                {"date": "2020-01-04", "equity": 120.0, "assets": 0.0, "cash": 120.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.2, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertFalse(metrics["unrecovered_at_end"])
        self.assertEqual(metrics["longest_drawdown_days"], 3)

    def test_longest_drawdown_days_uses_prior_peak_anchor_for_unresolved_tail(self):
        result = {
            "daily": [
                {"date": "2020-01-01", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
                {"date": "2020-01-02", "equity": 50.0, "assets": 0.0, "cash": 50.0, "receivable": 0.0, "total_funding": 100.0, "nav": 0.5, "fees": 0.0},
                {"date": "2020-01-03", "equity": 60.0, "assets": 0.0, "cash": 60.0, "receivable": 0.0, "total_funding": 100.0, "nav": 0.6, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertTrue(metrics["unrecovered_at_end"])
        self.assertEqual(metrics["longest_drawdown_days"], 2)

    def test_longest_drawdown_days_is_zero_for_flat_nav(self):
        result = {
            "daily": [
                {"date": "2020-01-01", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
                {"date": "2020-01-02", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
                {"date": "2020-01-03", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertEqual(metrics["longest_drawdown_days"], 0)
        self.assertFalse(metrics["unrecovered_at_end"])

    def test_worst_below_funding_uses_historical_minimum(self):
        result = {
            "daily": [
                {"date": "2020-01-01", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
                {"date": "2020-01-02", "equity": 50.0, "assets": 0.0, "cash": 50.0, "receivable": 0.0, "total_funding": 100.0, "nav": 0.5, "fees": 0.0},
                {"date": "2020-01-04", "equity": 120.0, "assets": 0.0, "cash": 120.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.2, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertEqual(metrics["worst_below_funding"], -50.0)

    def test_rejects_unsorted_or_repeated_daily_dates(self):
        result = {
            "daily": [
                {"date": "2020-01-02", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
                {"date": "2020-01-01", "equity": 110.0, "assets": 0.0, "cash": 110.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.1, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        with self.assertRaises(ValueError):
            summarize(result)

        repeated = {
            "daily": [
                {"date": "2020-01-01", "equity": 100.0, "assets": 0.0, "cash": 100.0, "receivable": 0.0, "total_funding": 100.0, "nav": 1.0, "fees": 0.0},
                {"date": "2020-01-01", "equity": 95.0, "assets": 0.0, "cash": 95.0, "receivable": 0.0, "total_funding": 100.0, "nav": 0.95, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        with self.assertRaises(ValueError):
            summarize(repeated)

    def test_worst5_ceil_with_few_closed_trades(self):
        result = {
            "daily": [
                {"date": "2026-09-01", "equity": 1000.0, "assets": 0.0, "cash": 1000.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 1.0, "fees": 0.0},
                {"date": "2026-09-02", "equity": 1000.0, "assets": 0.0, "cash": 1000.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 1.0, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [
                {"closed": True, "net_pnl": -10.0, "net_return": -0.1, "entry_date": "2026-09-01", "exit_date": "2026-09-02", "valuation_date": "2026-09-02"},
                {"closed": True, "net_pnl": -2.0, "net_return": -0.02, "entry_date": "2026-09-01", "exit_date": "2026-09-03", "valuation_date": "2026-09-03"},
                {"closed": True, "net_pnl": 8.0, "net_return": 0.08, "entry_date": "2026-09-01", "exit_date": "2026-09-04", "valuation_date": "2026-09-04"},
            ],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertEqual(metrics["completed_trades"], 3)
        self.assertEqual(metrics["worst5_count"], 1)
        self.assertEqual(metrics["worst5_mean_net_pnl"], -10.0)
        self.assertEqual(metrics["profitable_closed_count"], 1)
        self.assertAlmostEqual(metrics["closed_win_fraction"], 1 / 3)

    def test_zero_initial_equity_ignored_in_exposure(self):
        result = {
            "daily": [
                {"date": "2026-09-01", "equity": 0.0, "assets": 0.0, "cash": 0.0, "receivable": 0.0, "total_funding": 0.0, "nav": 1.0, "fees": 0.0},
                {"date": "2026-09-02", "equity": 1000.0, "assets": 0.0, "cash": 500.0, "receivable": 500.0, "total_funding": 0.0, "nav": 1.0, "fees": 0.0},
                {"date": "2026-09-03", "equity": 2000.0, "assets": 500.0, "cash": 1500.0, "receivable": 500.0, "total_funding": 0.0, "nav": 1.0, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertEqual(metrics["zero_exposure_days"], 1)
        self.assertAlmostEqual(metrics["mean_exposure"], 0.125)

    def test_rejects_non_finite_input(self):
        result = {
            "daily": [
                {"date": "2026-09-01", "equity": float("nan"), "assets": 0.0, "cash": 0.0, "receivable": 0.0, "total_funding": 0.0, "nav": 1.0, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        with self.assertRaises(ValueError):
            summarize(result)

    def test_empty_merchant_arrays_return_none_metrics_not_nan(self):
        result = {
            "daily": [
                {"date": "2026-09-01", "equity": 1000.0, "assets": 0.0, "cash": 1000.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 1.0, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [],
        }
        metrics = summarize(result)
        self.assertIsNone(metrics["closed_mean_net_pnl"])
        self.assertIsNone(metrics["closed_median_net_return"])
        self.assertIsNone(metrics["closed_win_fraction"])
        self.assertEqual(metrics["mean_exposure"], 0.0)
        self.assertIsNone(metrics["worst5_mean_net_pnl"])

    def test_no_mutation_of_input(self):
        result = {
            "daily": [
                {"date": "2026-09-01", "equity": 1000.0, "assets": 0.0, "cash": 1000.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 1.0, "fees": 0.0},
            ],
            "trades": [
                {"side": "buy", "fee": 1.0},
            ],
            "roundtrips": [
                {"closed": True, "net_pnl": 5.0, "net_return": 0.01, "entry_date": "2026-09-01", "exit_date": "2026-09-02", "valuation_date": "2026-09-02"},
            ],
            "orders": [
                {"status": "rejected", "reason": "资金不足"},
                {"status": "rejected", "reason": "风控"},
                {"status": "filled"},
            ],
        }
        snapshot = copy.deepcopy(result)
        summarize(result)
        self.assertEqual(result, snapshot)

    def test_rejection_reason_counts(self):
        result = {
            "daily": [
                {"date": "2026-09-01", "equity": 1000.0, "assets": 0.0, "cash": 1000.0, "receivable": 0.0, "total_funding": 1000.0, "nav": 1.0, "fees": 0.0},
            ],
            "trades": [],
            "roundtrips": [],
            "orders": [
                {"status": "rejected", "reason": "资金不足"},
                {"status": "rejected", "reason": "资金不足"},
                {"status": "filled"},
            ],
        }
        metrics = summarize(result)
        self.assertEqual(metrics["order_status_counts"], {"rejected": 2, "filled": 1})
        self.assertEqual(metrics["rejection_reason_counts"], {"资金不足": 2})


if __name__ == "__main__":
    unittest.main()
