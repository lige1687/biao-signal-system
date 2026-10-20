import math
import hashlib
import csv
import json
import os
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from run_matched_effect import (
    MONTHS, _delta_summary, compute_effect, connect_outcomes, make_choices, make_pairs,
)
from run_matched_effect import run
from run_matched_effect import _admission_map, _filing_op, _load_outcomes


def row(ticker, mom, op, admit=True, future_marker=None):
    return {"ticker": ticker, "momentum": mom, "op": op, "admit": admit,
            "future_marker": future_marker}


class MatchedEffectTests(unittest.TestCase):
    def test_pairing_adjacent_unique_and_odd_rotation_3_to_25(self):
        for n in range(3, 26):
            source = [row(f"T{i:02d}", i, i) for i in range(n)]
            for month_index in range((n + 1) // 2 if n % 2 else 1):
                pairs, omitted = make_pairs(source, month_index)
                used = [x["ticker"] for pair in pairs for x in pair]
                self.assertEqual(len(used), len(set(used)))
                self.assertEqual(len(pairs), n // 2)
                self.assertEqual(len(used) + (omitted is not None), n)
                for a, b in pairs:
                    self.assertEqual(abs(int(a["ticker"][1:]) - int(b["ticker"][1:])), 1)
            if n % 2:
                omissions = [make_pairs(source, i)[1]["ticker"] for i in range((n + 1) // 2)]
                self.assertEqual(len(set(omissions)), len(omissions))

    def test_choices_do_not_depend_on_future_values_or_target_deletion(self):
        base = [row("A", 1, 9, future_marker=1), row("B", 2, 2, future_marker=3),
                row("C", 3, 1, future_marker=5), row("D", 4, 8, future_marker=7)]
        first, _ = make_choices("2015-01", base, 0)
        changed = [dict(x, future_marker=math.nan) for x in base]
        second, _ = make_choices("2015-01", changed, 0)
        self.assertEqual(first, second)
        self.assertEqual(first, make_choices("2015-01", base, 0)[0])

    def test_feature_pool_does_not_require_future_label(self):
        formed = [dict(row("A", 1, 3), target_month="2015-01"),
                  dict(row("B", 2, 1), target_month="2015-01")]
        result = compute_effect(formed, {}, replications=5)
        self.assertEqual(len(result["monthly"]), 120)
        self.assertEqual(result["monthly"][0]["formed_count"], 2)
        self.assertEqual(result["monthly"][0]["profitability_minus_higher_momentum_unknown_delta_pairs"], 1)
        self.assertEqual(result["monthly"][0]["profitability_minus_lower_momentum_known_delta_pairs"], 1)
        self.assertEqual(result["monthly"][0]["profitability_minus_lower_momentum_known_identifiable_mean"], 0)
        self.assertEqual(result["monthly"][0]["profitability_known_return_count"], 0)

    def test_different_choice_one_unknown_keeps_delta_unknown_and_bounds(self):
        choices = [{"profitability_ticker": "A", "higher_momentum_ticker": "B",
                    "lower_momentum_ticker": "A", "target_month": "2015-01", "pair_index": 1}]
        connected = connect_outcomes(choices, {"A": -0.2})
        stats = _delta_summary(connected, "profitability", "higher_momentum")
        self.assertEqual(stats["unknown_delta_pairs"], 1)
        self.assertEqual(stats["paired_loss_probability_delta_bounds"], [0.0, 1.0])

    def test_tie_rules_and_pair_delta_decomposition(self):
        candidates = [row("B", 1, 5), row("A", 1, 5)]
        picks, _ = make_choices("2015-01", candidates, 0)
        self.assertEqual(picks[0]["higher_momentum_ticker"], "A")
        self.assertEqual(picks[0]["lower_momentum_ticker"], "A")
        self.assertEqual(picks[0]["profitability_ticker"], "A")
        self.assertIsNone(picks[0]["op_high_minus_low"])
        selected = connect_outcomes([picks[0]], {"A": -0.1, "B": 0.2})
        s = _delta_summary(selected, "profitability", "lower_momentum")
        self.assertAlmostEqual(s["known_loss_part_sum"] + s["known_upside_part_sum"],
                               selected[0]["profitability_return"] - selected[0]["lower_momentum_return"])

    def test_op_directional_pair_labels_and_both_delta_denominators(self):
        candidates = [row("A", 1, 1), row("B", 2, 9)]
        picks, _ = make_choices("2015-01", candidates, 0)
        joined = connect_outcomes(picks, {"A": -0.1, "B": 0.2})
        self.assertEqual(joined[0]["op_high_ticker"], "B")
        self.assertEqual(joined[0]["op_low_ticker"], "A")
        self.assertAlmostEqual(joined[0]["op_high_minus_low_return_delta"], 0.3)
        stats = _delta_summary(joined, "profitability", "higher_momentum")
        self.assertAlmostEqual(stats["known_loss_part_identifiable_mean"],
                               stats["known_loss_part_original_weight_contribution"])
        self.assertAlmostEqual(stats["known_upside_part_identifiable_mean"],
                               stats["known_upside_part_original_weight_contribution"])
        tied = make_choices("2015-01", [row("A", 1, 5), row("B", 2, 5)], 0)[0]
        tie_join = connect_outcomes(tied, {"A": 0.1, "B": 0.2})[0]
        self.assertIsNone(tie_join["op_high_minus_low_return_delta"])

    def test_quote_ratio_requires_valid_positive_prices_and_return_floor(self):
        choices = [{"profitability_ticker": "A", "higher_momentum_ticker": "A",
                    "lower_momentum_ticker": "A"}]
        self.assertIsNone(connect_outcomes(choices, {"A": float("nan")})[0]["profitability_return"])
        self.assertIsNone(connect_outcomes(choices, {"A": -1.01})[0]["profitability_return"])
        self.assertEqual(connect_outcomes(choices, {"A": 0.0})[0]["profitability_return"], 0.0)

    def test_op_reads_three_same_period_standard_facts_and_separate_interest_line(self):
        def fact(tag, value, qtrs, line, stmt):
            return {"tag": tag, "version": "us-gaap/2025", "ddate": "20251231",
                    "qtrs": qtrs, "uom": "USD", "segments": "", "coreg": "",
                    "value": str(value), "presentation": [{"report": "1", "line": str(line), "stmt": stmt}]}
        filing = {
            "sourcequalified": True, "automatic_scoring_eligible": True,
            "source_facts": {
                "operating_income": [fact("OperatingIncomeLoss", 12, "4", 10, "IS")],
                "interest": [fact("InterestExpense", 2, "4", 11, "IS")],
                "inclusive_equity": [fact("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", 20, "0", 20, "BS")],
            },
        }
        self.assertEqual(_filing_op(filing), 0.5)
        filing["source_facts"]["interest"][0]["presentation"][0]["line"] = "9"
        self.assertIsNone(_filing_op(filing))

    def test_pending_future_action_only_makes_label_unknown(self):
        base = {"target_month": "2015-01", "ticker": "A", "candidate_cik": "1", "adsh": "a",
                "formation_quote_detail_json": '{"adj_close":10}',
                "target_month_end_quote_detail_json": '{"qualified":true,"adj_close":12}',
                "target_month_end_quote_present_and_qualified": "True"}
        formed = [dict(base, admit=True, momentum=0.1, op=0.2)]
        choices_before, _ = make_choices("2015-01", formed, 0)
        pending, pending_reasons = _load_outcomes([(base, {"outcome_pending": True, "outcome_reasons": ["unresolved"]})], formed)
        cleared, _ = _load_outcomes([(base, {"outcome_pending": False, "outcome_reasons": []})], formed)
        self.assertEqual(dict(pending), {})
        self.assertEqual(pending_reasons[("2015-01", "A")], "unresolved")
        self.assertAlmostEqual(cleared["2015-01"]["A"], 0.2)
        self.assertEqual(make_choices("2015-01", formed, 0)[0], choices_before)

    def test_admission_mapping_rejects_missing_and_duplicate_keys(self):
        valid = {"target_month": "2015-01", "ticker": "A", "candidate_cik": "1",
                 "adsh": "x", "admit": True, "outcome_pending": True}
        self.assertEqual(len(_admission_map({"schema": "annual-op-admission/1", "rows": [valid]})), 1)
        with self.assertRaisesRegex(ValueError, "incomplete/duplicate"):
            _admission_map({"schema": "annual-op-admission/1", "rows": [dict(valid, adsh="")]})
        with self.assertRaisesRegex(ValueError, "incomplete/duplicate"):
            _admission_map({"schema": "annual-op-admission/1", "rows": [valid, dict(valid)]})

    def test_calendar_is_not_compressed_when_month_is_absent(self):
        result = compute_effect([], {}, replications=3)
        self.assertEqual(len(result["monthly"]), 120)
        self.assertEqual([m["target_month"] for m in result["monthly"]], list(MONTHS))
        self.assertEqual(result["monthly"][37]["target_month"], "2018-02")

    def test_run_guards_and_synthetic_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            design = Path(__file__).resolve().with_name("matched-effect-design.json")
            script = Path(__import__("run_matched_effect").__file__).resolve()
            sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
            out = root / "result"
            repo = Path(__file__).resolve().parents[4]
            adapter = repo / "src/lei_signal/research/annual_profitability.py"
            definition = root / "definition.json"
            admission = root / "admission.json"
            filings = root / "filings.jsonl"
            candidates = root / "candidates.csv"
            definition.write_text('{"objects":[{"id":"research.fundamental.annual_operating_profitability_after_da","version":"1.0.0"}]}', encoding="utf-8")
            candidate_fields = ["target_month", "ticker", "candidate_cik", "adsh", "sourcequalified",
                                "automatic_scoring_eligible", "mom_all_12_endpoints_qualified",
                                "mom_11_month_adjusted_price_change", "formation_quote_qualified",
                                "formation_quote_detail_json", "target_month_end_quote_present_and_qualified",
                                "target_month_end_quote_detail_json"]
            admission_rows, filing_rows, candidate_rows = [], [], []
            for mi, month in enumerate(MONTHS):
                for ix, ticker in enumerate(("A", "B", "C") if mi == 0 else ("A", "B")):
                    cik = str(1000001 + ord(ticker) - ord("A"))
                    adsh = f"{cik}-{month}"
                    candidate_rows.append({
                        "target_month": month, "ticker": ticker, "candidate_cik": cik, "adsh": adsh,
                        "sourcequalified": "True", "automatic_scoring_eligible": "True",
                        "mom_all_12_endpoints_qualified": "True",
                        "mom_11_month_adjusted_price_change": str(ord(ticker) - ord("A") + mi / 1000),
                        "formation_quote_qualified": "True",
                        "formation_quote_detail_json": '{"qualified":true,"adj_close":10}',
                        "target_month_end_quote_present_and_qualified": "True",
                        "target_month_end_quote_detail_json": '{"qualified":true,"adj_close":11}',
                    })
                    admission_rows.append({"target_month": month, "ticker": ticker, "candidate_cik": cik,
                                           "adsh": adsh, "admit": True, "reasons": [],
                                           "outcome_pending": True, "outcome_reasons": ["synthetic_pending"]})
                    def fact(tag, value, qtrs, line, stmt):
                        return {"tag": tag, "version": "us-gaap/2025", "ddate": "20251231",
                                "qtrs": qtrs, "uom": "USD", "segments": "", "coreg": "",
                                "value": str(value), "presentation": [{"report": "1", "line": str(line), "stmt": stmt}]}
                    filing_rows.append({
                        "adsh": adsh, "sourcequalified": True, "automatic_scoring_eligible": True,
                        "source_facts": {
                            "operating_income": [fact("OperatingIncomeLoss", 12 + ord(ticker) - ord("A"), "4", 10, "IS")],
                            "interest": [fact("InterestExpense", 2, "4", 11, "IS")],
                            "inclusive_equity": [fact("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", 20, "0", 20, "BS")],
                        },
                    })
            # A rejected, feature-incomplete row in the first month must not
            # enter the odd-omission ranking pool.
            candidate_rows.append({
                "target_month": MONTHS[0], "ticker": "D", "candidate_cik": "1000004",
                "adsh": "1000004-rejected", "sourcequalified": "True",
                "automatic_scoring_eligible": "True", "mom_all_12_endpoints_qualified": "False",
                "mom_11_month_adjusted_price_change": "", "formation_quote_qualified": "True",
                "formation_quote_detail_json": '{"qualified":true,"adj_close":10}',
                "target_month_end_quote_present_and_qualified": "True",
                "target_month_end_quote_detail_json": '{"qualified":true,"adj_close":11}',
            })
            with candidates.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=candidate_fields); writer.writeheader(); writer.writerows(candidate_rows)
            admission.write_text(json.dumps({"schema": "annual-op-admission/1", "rows": admission_rows}), encoding="utf-8")
            filings.write_text("".join(json.dumps(r) + "\n" for r in filing_rows), encoding="utf-8")
            contract = {
                "execution_authorized": True,
                "schema": "matched-effect-execution-contract/1",
                "definition_ref": "research.fundamental.annual_operating_profitability_after_da@1.0.0",
                "output_directory": str(out),
                "expected_counts": {"admitted_rows": 241, "unique_ciks": 3, "months": 120},
                "inputs": {
                    "runner": {"path": str(script), "sha256": sha(script)},
                    "design": {"path": str(design), "sha256": sha(design)},
                    "adapter": {"path": str(adapter), "sha256": sha(adapter)},
                    "definition_snapshot": {"path": str(definition), "sha256": sha(definition)},
                    "tests": {"path": str(Path(__file__).resolve()), "sha256": sha(__file__)},
                    "accounting_candidates": {"path": str(candidates), "sha256": sha(candidates)},
                    "filings": {"path": str(filings), "sha256": sha(filings)},
                    "admission": {"path": str(admission), "sha256": sha(admission)},
                },
                "storage": {"mount": str(root), "device": os.stat(root).st_dev,
                            "uuid": "synthetic-volume", "reserve_bytes": 0},
            }
            cpath = root / "contract.json"
            cpath.write_text(json.dumps(contract), encoding="utf-8")
            with mock.patch("run_matched_effect.subprocess.run",
                            return_value=mock.Mock(stdout=plistlib.dumps({"VolumeUUID": "synthetic-volume"}))):
                manifest = run(cpath, out)
            self.assertEqual(manifest["status"], "completed")
            expected = {"formation-with-feature.csv", "pairs.csv", "policy-choices.csv", "monthly.csv",
                        "yearly.csv", "period-summary.json", "uncertainty.json", "sign-cells.csv",
                        "coverage.json", "odd-omissions.csv", "manifest.json"}
            self.assertTrue(expected <= {p.name for p in out.iterdir()})
            with (out / "policy-choices.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 120)
            with (out / "formation-with-feature.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 241)
            self.assertEqual(len(candidate_rows), 242)
            self.assertEqual(json.loads((out / "coverage.json").read_text())["admitted_rows"], 241)
            with (out / "odd-omissions.csv").open(newline="", encoding="utf-8") as stream:
                omission = next(csv.DictReader(stream))
            self.assertEqual(omission["ticker"], "A")
            self.assertEqual(omission["original_momentum_rank"], "1")
            with self.assertRaisesRegex(ValueError, "already exists"):
                run(cpath, out)

            bad_auth = dict(contract, execution_authorized=False)
            bad_path = root / "bad-auth.json"
            bad_path.write_text(json.dumps(bad_auth), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "execution_authorized"):
                run(bad_path, root / "never")

            bad_hash = json.loads(json.dumps(contract))
            bad_hash["inputs"]["design"]["sha256"] = "0" * 64
            bad_hash_path = root / "bad-hash.json"
            bad_hash_path.write_text(json.dumps(bad_hash), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                run(bad_hash_path, root / "never2")

            bad_storage = json.loads(json.dumps(contract))
            bad_storage["output_directory"] = str(root / "bad-storage")
            bad_storage["storage"]["device"] = -1
            bad_storage_path = root / "bad-storage.json"
            bad_storage_path.write_text(json.dumps(bad_storage), encoding="utf-8")
            with mock.patch("run_matched_effect.subprocess.run",
                            return_value=mock.Mock(stdout=plistlib.dumps({"VolumeUUID": "synthetic-volume"}))):
                with self.assertRaisesRegex(ValueError, "mount/device mismatch"):
                    run(bad_storage_path, root / "bad-storage")


if __name__ == "__main__":
    unittest.main()
