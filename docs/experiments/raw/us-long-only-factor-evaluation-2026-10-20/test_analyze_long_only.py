"""Synthetic French section and arithmetic checks; no real performance read."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("analyze_long_only", Path(__file__).with_name("analyze_long_only.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

HEADERS = ["SMALL LoBM", "ME1 BM2", "SMALL HiBM", "BIG LoBM", "ME2 BM2", "BIG HiBM"]


def fixture_text(rows=None, counts=None, *, duplicate=False):
    rows = rows or ["202001,1,2,3,4,5,6", "202002,-2,0,2,-4,0,4"]
    counts = counts or ["202001,10,11,12,20,21,22", "202002,10,11,12,20,21,22"]
    header = "," + ",".join(HEADERS)
    return "\n".join([
        "Fama French synthetic file", "Average Value Weighted Returns -- Monthly", header,
        *rows, *(rows[:1] if duplicate else []), "",
        "Average Equal Weighted Returns -- Monthly", header, "202001,80,80,80,80,80,80", "",
        "Annual summary ignored", "2020,999,999,999,999,999,999", "",
        "Number of Firms in Portfolios", header, *counts, "",
        "Post-count annual summary", "2020,900,900,900,900,900,900", "",
    ])


def source(path):
    return {"id": "BM", "path": str(path), "headers": HEADERS,
            "small_indices": [0, 1, 2], "big_indices": [3, 4, 5]}


def row(month, l, n, h):
    return {"month": month, "source": "BM", "size": "big", "L": l, "N": n, "H": h,
            "B": (l+n+h)/3, "Nfirm_L": 10, "Nfirm_N": 11, "Nfirm_H": 12}


class FrenchTests(unittest.TestCase):
    def test_section_isolation_units_and_paired_identities(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "french.csv"
            p.write_text(fixture_text())
            data = a.prepare_source(source(p), [{"id": "primary", "start": "2020-01",
                                                   "end": "2020-02", "expected_months": 2}],
                                    returns_section="Average Value Weighted Returns -- Monthly",
                                    count_section="Number of Firms in Portfolios",
                                    missing_codes=[-99.99, -999.0])
            rows = data["primary"]["big"]
            self.assertEqual((rows[0]["L"], rows[0]["N"], rows[0]["H"]), (.04, .05, .06))
            self.assertAlmostEqual(rows[0]["B"], .05)
            self.assertEqual((rows[0]["Nfirm_L"], rows[0]["Nfirm_H"]), (20, 22))
            self.assertAlmostEqual(rows[0]["H"]-rows[0]["B"], (2*rows[0]["H"]-rows[0]["L"]-rows[0]["N"])/3)
            d = a.describe(rows)
            self.assertAlmostEqual(d["contrasts"]["H-B"]["mean_paired_difference"],
                                   a.mean([r["H"]-r["B"] for r in rows]))
            self.assertAlmostEqual(d["contrasts"]["H-L"]["mean_paired_difference"],
                                   d["contrasts"]["H-B"]["mean_paired_difference"] +
                                   d["contrasts"]["B-L"]["mean_paired_difference"])

    def test_missing_sentinel_duplicate_month_and_count_gap_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "french.csv"
            p.write_text(fixture_text(rows=["202001,1,2,3,4,5,-99.99", "202002,1,2,3,4,5,6"]))
            kwargs = dict(returns_section="Average Value Weighted Returns -- Monthly",
                          count_section="Number of Firms in Portfolios",
                          missing_codes=[-99.99, -999.0])
            period = [{"id": "primary", "start": "2020-01", "end": "2020-02", "expected_months": 2}]
            with self.assertRaisesRegex(ValueError, "missing/invalid"):
                a.prepare_source(source(p), period, **kwargs)
            p.write_text(fixture_text(duplicate=True))
            with self.assertRaisesRegex(ValueError, "duplicate monthly"):
                a.prepare_source(source(p), period, **kwargs)
            p.write_text(fixture_text(counts=["202001,10,11,12,20,21,22"]))
            with self.assertRaisesRegex(ValueError, "missing return/count"):
                a.prepare_source(source(p), period, **kwargs)

    def test_month_end_drawdown_includes_initial_wealth(self):
        growth, draw = a.wealth_stats([-.10, .20])
        self.assertAlmostEqual(growth, .08)
        self.assertAlmostEqual(draw, -.10)
        self.assertEqual(a.wealth_stats([.10, .10])[1], 0)
        with self.assertRaisesRegex(ValueError, "below -100"):
            a.wealth_stats([-1.01])

    def test_B_condition_zero_and_top_tie_month(self):
        rows = [row(f"2020-{i+1:02d}", 0, 0, 0) for i in range(10)]
        rows[0] = row("2020-01", -.03, -.03, -.03)
        rows[1] = row("2020-02", .03, .03, .03)
        rows[2] = row("2020-03", .03, .03, .03)
        result = a.describe(rows)
        self.assertEqual((result["B_negative_months"], result["B_positive_months"],
                          result["B_zero_months"]), (1, 2, 7))
        self.assertEqual(result["top_B_months"], ["2020-02"])
        self.assertEqual(result["top_B_positive_months"], 1)

    def test_joint_draws_keep_source_pairing_and_missing_condition(self):
        rows = [row(f"2020-{i+1:02d}", .01, .01, .01) for i in range(12)]
        joint = {s: [dict(r, source=s) for r in rows] for s in a.SOURCES}
        out = a.intervals(joint, draws=20, block=3, seed=5)
        hashes = [out["index_sha256_u16be"] for _ in a.SOURCES]
        self.assertEqual(len(set(hashes)), 1)
        for s in a.SOURCES:
            self.assertEqual(out["pointwise"][s]["mean_H_minus_B"]["bounds_95"], [0, 0])
            empty = out["pointwise"][s]["B_negative_mean_H_minus_B"]
            self.assertIsNone(empty["bounds_95"])
            self.assertEqual((empty["valid_draws"], empty["missing_draws"]), (0, 20))

    def test_primary_halves_and_leave_one_year_out_keep_fixed_dates(self):
        months = a.calendar("2020-01", "2021-12")
        rows = [row(month, 0, 0, .12 if month[:4] == "2020" else -.06)
                for month in months]
        result = a.stability(rows, halves=[["2020-01", "2020-12"],
                                           ["2021-01", "2021-12"]])
        self.assertEqual([part["statistics"]["months"] for part in result["primary_halves"]],
                         [12, 12])
        contrast = result["contrasts"]["H-L"]
        self.assertAlmostEqual(contrast["leave_one_year_out_mean_min"], -.06)
        self.assertAlmostEqual(contrast["leave_one_year_out_mean_max"], .12)
        self.assertEqual(contrast["largest_absolute_annual_mean_contribution"]["year"], "2020")

    def test_source_hash_drift_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "source.csv"
            p.write_text("fixed")
            binding = {"path": str(p), "sha256": a.sha256(p)}
            p.write_text("changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                a.bound(binding)


if __name__ == "__main__":
    unittest.main()
