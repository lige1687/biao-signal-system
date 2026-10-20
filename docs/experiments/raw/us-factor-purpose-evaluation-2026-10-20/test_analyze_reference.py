"""Only synthetic US reference series; no source or market-effect run."""
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("analyze_reference", Path(__file__).with_name("analyze_reference.py"))
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)


def series(months, *, mom=None, gp=None, bm=None):
    mom = mom if mom is not None else [float(i) for i in range(len(months))]
    gp = gp if gp is not None else [0.0] * len(months)
    bm = bm if bm is not None else [0.0] * len(months)
    return {"signals": ["Mom12m", "GP", "BM"], "unit": "percent", "direction": "published_long_short",
            "rows": [{"date": f"{m}-28", "returns": {
                "Mom12m": {"percent": a, "decimal": a / 100},
                "GP": {"percent": g, "decimal": g / 100},
                "BM": {"percent": v, "decimal": v / 100}}}
                for m, a, g, v in zip(months, mom, gp, bm)]}


def period(start, end, count, ident="recent"):
    return {"id": ident, "start": start, "end": end, "expected_months": count}


class ReferenceTests(unittest.TestCase):
    def test_complete_support_and_percent_exactly_once(self):
        s = series(["2020-01", "2020-02"], mom=[10, -10], gp=[2, 2])
        rows = ar.expand(ar.prepare_rows(s, period("2020-01", "2020-02", 2)))
        self.assertEqual([r["M"] for r in rows], [.1, -.1])
        self.assertAlmostEqual(rows[0]["mixGP"], .06)
        self.assertAlmostEqual(rows[1]["mixGP"], -.04)
        self.assertAlmostEqual(ar.describe(rows)["series"]["halfM"]["sample_sd"],
                               ar.describe(rows)["series"]["M"]["sample_sd"] / 2)

    def test_missing_or_duplicate_month_is_rejected_not_zero_filled(self):
        p = period("2020-01", "2020-03", 3)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            ar.prepare_rows(series(["2020-01", "2020-03"]), p)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ar.prepare_rows(series(["2020-01", "2020-02", "2020-02", "2020-03"]), p)
        s = series(["2020-01", "2020-02", "2020-03"])
        s["rows"][1]["returns"]["GP"] = {"percent": None, "decimal": None}
        with self.assertRaisesRegex(ValueError, "missing"):
            ar.prepare_rows(s, p)

    def test_top_momentum_tie_break_is_date_and_condition_is_original_M(self):
        s = series(["2020-01", "2020-02", "2020-03", "2020-04", "2020-05",
                    "2020-06", "2020-07", "2020-08", "2020-09", "2020-10"],
                   mom=[1, 9, -2, 9, 0, 2, -1, 3, 4, 5],
                   gp=[0, 2, 1, 4, 0, 0, 0, 0, 0, 0])
        rows = ar.expand(ar.prepare_rows(s, period("2020-01", "2020-10", 10)))
        d = ar.describe(rows)
        self.assertEqual(d["top_M_dates"], ["2020-02-28"])
        self.assertEqual((d["M_negative_months"], d["M_positive_months"], d["M_zero_months"]), (2, 7, 1))
        self.assertAlmostEqual(d["comparisons"]["GP"]["M"]["when_M_negative_difference"],
                               ((-.005 - -.02) + (-.005 - -.01)) / 2)
        self.assertEqual(d["top_M_positive_count"], 1)

    def test_full_paired_draws_preserve_identity_and_empty_conditions(self):
        rows = ar.expand([{"month": f"2020-{i+1:02d}", "date": f"2020-{i+1:02d}-28",
                           "Mom12m": .01, "GP": .01, "BM": .01} for i in range(12)])
        u = ar.recent_intervals(rows, draws=20, block=3, seed=4)
        pair = u["pointwise"]["GP"]["M"]
        self.assertEqual(pair["mean_difference"]["bounds_95"], [0, 0])
        self.assertEqual(pair["when_M_negative_difference"]["valid_draws"], 0)
        self.assertEqual(pair["when_M_negative_difference"]["missing_draws"], 20)
        self.assertEqual(u["empty_negative_condition_draws"]["GP"], 20)

    def test_resample_changes_negative_support_with_drawn_momentum(self):
        rows = ar.expand([
            {"month": f"2020-{i+1:02d}", "date": f"2020-{i+1:02d}-28",
             "Mom12m": -.02 if i == 0 else .01, "GP": .02, "BM": .01}
            for i in range(12)])
        u = ar.recent_intervals(rows, draws=100, block=1, seed=20261020)
        item = u["pointwise"]["GP"]["M"]["when_M_negative_difference"]
        self.assertGreater(item["missing_draws"], 0)
        self.assertLess(item["missing_draws"], 100)
        self.assertAlmostEqual(item["bounds_95"][0], .02)
        self.assertAlmostEqual(item["bounds_95"][1], .02)

    def test_constant_correlation_is_unknown(self):
        self.assertIsNone(ar.corr([1, 1, 1], [1, 2, 3]))
        self.assertIsNone(ar.corr([1], [2]))

    def test_exact_two_periods_recent_only_intervals(self):
        older = ar.months_between("1963-07", "2014-12")
        recent = ar.months_between("2015-01", "2024-12")
        source = series(older + recent, mom=[-1, 1] * 369,
                        gp=[1, 0] * 369, bm=[0, 1] * 369)
        design = {"signals": list(ar.SIGNALS),
                  "combination_weights": {"momentum": .5, "candidate": .5},
                  "periods": [period("2015-01", "2024-12", 120),
                              period("1963-07", "2014-12", 618, "earlier")],
                  "uncertainty": {"block_months": 12, "draws": 5000,
                                  "seed": 20261020, "level": .95,
                                  "interval_periods": ["recent"]}}
        summaries, rows = ar.calculate(source, design, draws=3)
        self.assertEqual((len(rows), summaries["earlier"]["months"],
                          summaries["recent"]["months"]), (738, 618, 120))
        self.assertNotIn("uncertainty", summaries["earlier"])
        self.assertEqual(summaries["recent"]["uncertainty"]["draws"], 3)

    def test_existing_output_refused_before_real_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "result"
            out.mkdir()
            source = root / "source.json"
            source.write_text("{}")
            plan = root / "plan.json"
            plan.write_text(json.dumps({"output": str(out)}))
            loader = Path(__file__).resolve().parents[4] / "src/lei_signal/research/osap_reference.py"
            storage_module = ar.STORAGE_MODULE

            def bind(path):
                return {"path": str(path.resolve()), "sha256": ar.sha256(path)}

            design = root / "design.json"
            design.write_text(json.dumps({
                "schema": "purpose-specific-reference/1", "status": "design_before_effects",
                "loader": bind(loader), "source_manifest": bind(source),
                "storage_plan": bind(plan), "output": str(out)}))
            contract = root / "contract.json"
            contract.write_text(json.dumps({
                "schema": ar.SCHEMA, "approved": True, "output": str(out),
                "bindings": {"design": bind(design), "runner": bind(Path(ar.__file__)),
                             "loader": bind(loader), "source_manifest": bind(source),
                             "storage_plan": bind(plan), "storage_module": bind(storage_module)}}))
            with self.assertRaisesRegex(FileExistsError, "existing output"):
                ar.execute(design, contract)


if __name__ == "__main__":
    unittest.main()
