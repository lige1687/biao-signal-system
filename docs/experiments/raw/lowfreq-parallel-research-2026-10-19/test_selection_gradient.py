import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).with_name("run_selection_gradient.py")
SPEC = importlib.util.spec_from_file_location("selection_gradient", SCRIPT)
sg = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sg)


def make_rows(scores, *, industries=None, outcomes=None, scope="gp", month="2015-01", weights=None):
    industries = industries or ["A"] * len(scores)
    outcomes = outcomes or [0.1] * len(scores)
    weights = weights or [1.0 / len(scores)] * len(scores)
    sector_sizes = {}
    for industry in industries:
        sector_sizes[industry] = sector_sizes.get(industry, 0) + 1
    rows = []
    for i, (score, industry, outcome, weight) in enumerate(zip(scores, industries, outcomes, weights)):
        rows.append({
            "scope": scope, "month": month, "code": f"x{i:03d}", "industry": industry,
            "financial_score": str(score), "future_return": "" if outcome is None else str(outcome),
            "sector_n": str(sector_sizes[industry]),
            "weight_P": str(weight), "weight_M": str(weight), "weight_F": str(weight),
            "weight_B": str(weight), "weight_D": str(weight),
        })
    return rows


class PartitionTests(unittest.TestCase):
    def test_five_names_one_per_group(self):
        parsed = sg.parse_rows(make_rows([5, 1, 4, 2, 3]))
        allocations, ties = sg._partition(parsed)
        self.assertEqual(len(allocations), 5)
        self.assertFalse(ties)
        self.assertEqual([max(allocations[f"x{i:03d}"], key=allocations[f"x{i:03d}"].get) for i in range(5)], [5, 1, 4, 2, 3])

    def test_seven_names_have_equal_fractional_group_capacity(self):
        parsed = sg.parse_rows(make_rows([7, 1, 6, 2, 5, 3, 4]))
        allocations, _ = sg._partition(parsed)
        for actual in [sum(a[g] for a in allocations.values()) for g in range(1, 6)]:
            self.assertAlmostEqual(actual, 1.4)
        self.assertEqual(allocations["x001"][1], 1.0)
        self.assertAlmostEqual(allocations["x003"][1], 0.4)
        self.assertAlmostEqual(allocations["x003"][2], 0.6)
        self.assertEqual(allocations["x000"][5], 1.0)

    def test_six_names_have_equal_fractional_group_capacity(self):
        parsed = sg.parse_rows(make_rows([6, 1, 5, 2, 4, 3]))
        allocations, _ = sg._partition(parsed)
        for actual in [sum(a[g] for a in allocations.values()) for g in range(1, 6)]:
            self.assertAlmostEqual(actual, 1.2)

    def test_partial_tie_crossing_cuts_gets_identical_group_shares(self):
        parsed = sg.parse_rows(make_rows([0, 1, 1, 1, 2, 3, 4]))
        allocations, ties = sg._partition(parsed)
        self.assertEqual([t["score"] for t in ties], [1.0])
        self.assertEqual(ties[0]["tie_count"], 3)
        self.assertEqual(ties[0]["groups"], [1, 2, 3])
        for code in ["x001", "x002", "x003"]:
            self.assertEqual(allocations[code], allocations["x001"])
        self.assertAlmostEqual(allocations["x001"][1], 0.4 / 3)
        self.assertAlmostEqual(allocations["x001"][2], 1.4 / 3)
        self.assertAlmostEqual(allocations["x001"][3], 1.2 / 3)

    def test_renaming_codes_and_row_shuffle_do_not_change_financial_result(self):
        rows_a = make_rows([0, 1, 1, 1, 2, 3, 4], outcomes=[0, .1, .1, .1, .2, .3, .4])
        rows_b = [dict(r, code=f"z{6-i:03d}") for i, r in enumerate(rows_a)]
        rows_b.reverse()
        a, _ = sg.analyze_unit(sg.parse_rows(rows_a), scope="gp", month="2015-01")
        b, _ = sg.analyze_unit(sg.parse_rows(rows_b), scope="gp", month="2015-01")
        for scenario in range(2):
            for field in [f"supported_Q{g}_return_pct" for g in range(1, 6)] + ["Q5_minus_Q1_pp"]:
                self.assertAlmostEqual(a[scenario][field], b[scenario][field])

    def test_reversing_score_order_exchanges_low_and_high_group_shares(self):
        rows = make_rows([1, 2, 3, 4, 5, 6, 7])
        forward, _ = sg._partition(sg.parse_rows(rows))
        reversed_rows = [dict(r, financial_score=str(8-int(r["financial_score"]))) for r in rows]
        reverse, _ = sg._partition(sg.parse_rows(reversed_rows))
        for row in rows:
            code = row["code"]
            self.assertAlmostEqual(forward[code][1], reverse[code][5])
            self.assertAlmostEqual(forward[code][5], reverse[code][1])
            for g in (2, 3, 4):
                self.assertAlmostEqual(forward[code][g], reverse[code][6-g])


class SupportAndOutcomeTests(unittest.TestCase):
    def test_supported_mass_and_conditional_normalization_preserve_sector_mass(self):
        rows = make_rows(
            [1, 2, 3, 4, 5, 10, 10],
            industries=["A"] * 5 + ["B"] * 2,
            outcomes=[0, 0.1, 0.2, 0.3, 0.4, 0.8, 0.9],
        )
        parsed = sg.parse_rows(rows)
        monthly, support = sg.analyze_unit(parsed, scope="gp", month="2015-01")
        self.assertAlmostEqual(monthly[0]["supported_mass"], 5 / 7)
        self.assertAlmostEqual(monthly[0]["excluded_mass"], 2 / 7)
        for group in range(1, 6):
            self.assertAlmostEqual(monthly[0][f"supported_Q{group}_weight"], 5 / 7)
        self.assertEqual(monthly[0]["supported_Q1_raw_contribution_pct"], 0.0)
        self.assertAlmostEqual(monthly[0]["supported_Q5_raw_contribution_pct"], 100 * (5 / 7) * 0.4)
        self.assertEqual(monthly[0]["supported_Q5_return_pct"], 40.0)
        q_mean = sum(monthly[0][f"supported_Q{g}_return_pct"] for g in range(1, 6)) / 5
        self.assertAlmostEqual(q_mean, monthly[0]["supported_P_return_pct"])
        q_mean_loss = sum(monthly[1][f"supported_Q{g}_return_pct"] for g in range(1, 6)) / 5
        self.assertAlmostEqual(q_mean_loss, monthly[1]["supported_P_return_pct"])
        excluded = next(r for r in support if r["row_type"] == "industry" and r["industry"] == "B")
        self.assertEqual(excluded["exclusion_reason"], "sector_n_below_5")
        month_summary = next(r for r in support if r["row_type"] == "month")
        self.assertEqual(month_summary["source_n"], 7)
        self.assertEqual(month_summary["supported_n"], 5)
        self.assertAlmostEqual(month_summary["supported_mass"], 5 / 7)
        self.assertEqual(month_summary["excluded_small_sector_n"], 2)
        self.assertEqual(sum(r["row_type"] == "month" for r in support), 1)

    def test_tiny_and_constant_score_industries_excluded(self):
        rows = make_rows([1] * 5 + [2, 3, 4, 5, 6], industries=["A"] * 5 + ["B"] * 5)
        parsed = sg.parse_rows(rows)
        _, support = sg.analyze_unit(parsed, scope="gp", month="2015-01")
        industry_support = [r for r in support if r["row_type"] == "industry"]
        self.assertEqual({r["industry"]: r["exclusion_reason"] for r in industry_support}, {"A": "constant_score", "B": ""})
        rows = make_rows([1, 2, 3, 4, 5, 6, 7], industries=["A"] * 5 + ["B"] * 2)
        parsed = sg.parse_rows(rows)
        _, support = sg.analyze_unit(parsed, scope="gp", month="2015-01")
        self.assertEqual(next(r for r in support if r["row_type"] == "industry" and r["industry"] == "B")["exclusion_reason"], "sector_n_below_5")

    def test_unknown_outcome_zero_and_minus100_are_both_retained(self):
        parsed = sg.parse_rows(make_rows([1, 2, 3, 4, 5], outcomes=[None, 0.1, 0.2, 0.3, 0.4]))
        monthly, _ = sg.analyze_unit(parsed, scope="gp", month="2015-01")
        zero, loss = monthly
        self.assertEqual(zero["supported_Q1_unknown_rows"], 1)
        self.assertEqual(loss["supported_Q1_unknown_rows"], 1)
        self.assertEqual(zero["supported_Q1_return_pct"], 0.0)
        self.assertEqual(loss["supported_Q1_return_pct"], -100.0)
        self.assertEqual(zero["supported_Q1_unknown_weight"], 1.0)
        self.assertAlmostEqual(loss["Q5_minus_Q1_pp"], 140.0)

    def test_zero_supported_mass_remains_missing(self):
        parsed = sg.parse_rows(make_rows([1, 1, 1, 1, 1]))
        monthly, _ = sg.analyze_unit(parsed, scope="gp", month="2015-01")
        for row in monthly:
            self.assertEqual(row["supported_mass"], 0.0)
            self.assertIsNone(row["supported_Q1_return_pct"])
            self.assertIsNone(row["Q5_minus_Q1_pp"])

    def test_all_missing_draws_are_counted_not_zero_filled(self):
        months = ["2015-01"]
        rows = []
        for scope in sg.SCOPES:
            row = {
                "scope": scope, "month": months[0], "scenario": "zero",
                "source_n": 0, "supported_n": 0, "supported_mass": 0.0,
                "excluded_small_sector_n": 0, "excluded_constant_score_n": 0,
                "excluded_missing_industry_n": 0, "supported_P_return_pct": None,
                "Q5_minus_Q1_pp": None,
            }
            row.update({f"supported_Q{g}_return_pct": None for g in range(1, 6)})
            rows.append(row)
            rows.append(dict(row, scenario="loss100"))
        summary = sg.summarize(rows, months, draws=8)
        for scope in sg.SCOPES:
            for scenario in ("zero", "loss100"):
                self.assertEqual(summary["scope"][scope][scenario]["Q5_minus_Q1_block_intervals_pp"]["6"]["all_missing_draws"], 8)
                self.assertIsNone(summary["scope"][scope][scenario]["Q5_minus_Q1_block_intervals_pp"]["6"]["interval_pp"])

    def test_duplicate_code_rejected(self):
        rows = make_rows([1, 2, 3, 4, 5])
        rows[1]["code"] = rows[0]["code"]
        with self.assertRaisesRegex(ValueError, "duplicate code"):
            sg.parse_rows(rows)

    def test_portfolio_weight_sum_must_be_one(self):
        rows = make_rows([1, 2, 3, 4, 5])
        rows[0]["weight_F"] = "0.1"
        with self.assertRaisesRegex(ValueError, "weight sum is not 1"):
            sg.parse_rows(rows)


class ContractBindingTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "action": "preflight", "stage": "diagnostic", "scopes": ["gp", "common_gp", "common_cfo"],
            "bindings": {
                "design": {"path": "/frozen/design.json", "sha256": "d" * 64},
                "runner": {"path": "/frozen/runner.py", "sha256": "r" * 64},
            },
            "scientific_identity": {"inputs": [{"path": "/external/stock_weights.csv", "sha256": "s" * 64}]},
        }

    def validate(self, contract):
        return sg.validate_control_binding(
            contract, design_path="/frozen/design.json", design_sha256="d" * 64,
            scopes=["gp", "common_gp", "common_cfo"], runner_path="/frozen/runner.py",
            runner_sha256="r" * 64, stock_sha256="s" * 64,
        )

    def test_exact_bound_preflight_diagnostic_contract_passes(self):
        self.assertIsNone(self.validate(self.base))

    def test_qualification_stage_rejected(self):
        contract = {**self.base, "stage": "qualification"}
        with self.assertRaisesRegex(ValueError, "preflight/diagnostic"):
            self.validate(contract)

    def test_other_valid_runner_rejected(self):
        contract = {**self.base, "bindings": {**self.base["bindings"],
                    "runner": {"path": "/frozen/other.py", "sha256": "o" * 64}}}
        with self.assertRaisesRegex(ValueError, "another runner"):
            self.validate(contract)

    def test_missing_data_identity_rejected(self):
        contract = {**self.base, "scientific_identity": {"inputs": []}}
        with self.assertRaisesRegex(ValueError, "omits stock_weights"):
            self.validate(contract)


if __name__ == "__main__":
    unittest.main()
