import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("adapter",HERE/"account_adapter.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
pspec=importlib.util.spec_from_file_location("prep",HERE/"prepare_signals.py")
p=importlib.util.module_from_spec(pspec);sys.modules[pspec.name]=p;pspec.loader.exec_module(p)


class PreparationTests(unittest.TestCase):
    def test_terminal_partial_week_is_candidate_only(self):
        rows=[{"signal_date":"2026-06-26","eligible_date":"2026-06-29"},
              {"signal_date":"2026-06-30","eligible_date":"2026-07-06"}]
        got=m.qualify_weekly_records(rows,"2026-06-30")
        self.assertEqual(got[0]["status"],"confirmed_completed_week")
        self.assertEqual(got[1]["status"],"unconfirmed_partial_week")
        self.assertTrue(got[1]["candidate_only"]);self.assertFalse(got[1]["executable_in_window"])

    def test_official_suspension_is_not_merged_with_other_blocks(self):
        rows=m.load_json(m.FIRST12/"inputs/dated-restrictions.json")
        labels={r["date"]:m.classify_restriction(r) for r in rows if r["symbol"]=="sz159915"}
        self.assertEqual(labels["2021-02-08"],"official_suspension")
        self.assertEqual(labels["2021-02-09"],"delayed_open_no_open_fill")

    def test_unconfirmed_signal_is_rejected_before_account(self):
        gate=m.load_json(HERE/"protocol-gate.json")
        bundle={"candidates":[{"candidate_id":"C1","provenance":"research_proxy","claims_paper_original":False,
                 "execution_policy":"exact_target_transition","signals":[{"symbol":"sh510300","signal_date":"2026-06-30",
                 "eligible_date":"2026-07-06","target":"1","reason":"x","candidate_only":True}]}]}
        with self.assertRaises(ValueError):m.validate_candidate_bundle(bundle,gate)

    def test_two_candidate_cap_means_eight_accounts(self):
        gate=m.load_json(HERE/"protocol-gate.json")
        self.assertEqual(gate["candidate_count_max"]*len(gate["symbols"])*len(gate["fees_per_side"]),8)

    def test_h1_exact_boundaries_and_hold_zone(self):
        weekly=[{"signal_date":"2015-01-02","eligible_date":"2015-01-05","breadth":"43.33333333333333"},
                {"signal_date":"2015-01-09","eligible_date":"2015-01-12","breadth":"45.33333333333333"},
                {"signal_date":"2015-01-16","eligible_date":"2015-01-19","breadth":"45.33333333333334"},
                {"signal_date":"2015-01-23","eligible_date":"2015-01-26","breadth":"43.33333333333334"}]
        got=p.build_h1(weekly,["sh510300"],"2015-01-31")
        self.assertEqual([x["target"] for x in got],["1","1","0","0"])

    def test_h2_uses_state_known_by_week_end_and_caps_at_one(self):
        weekly=[{"signal_date":"2015-01-08","eligible_date":"2015-01-12","breadth":60}]
        changes=[{"signal_date":"2015-01-09","target":"1"},{"signal_date":"2015-01-12","target":"0"}]
        bars=[{"date":"2015-01-08"},{"date":"2015-01-09"}]
        got=p.build_h2(weekly,{"sh510300":changes},{"sh510300":bars},["sh510300"],"2015-01-31")[0]
        self.assertEqual(got["breadth_target"],"0");self.assertEqual(got["trend_target"],"1")
        self.assertEqual(got["combined_target"],"1");self.assertEqual(got["recent_trend_switch_date"],"2015-01-09")
        self.assertEqual(got["breadth_source_date"],"2015-01-08");self.assertEqual(got["decision_date"],"2015-01-11")
        self.assertEqual(got["etf_observation_date"],"2015-01-09")

    def test_filter_uses_eligible_date_and_does_not_preseed_old_week(self):
        weekly=[{"signal_date":"2014-12-19","eligible_date":"2014-12-22","breadth":1},
                {"signal_date":"2014-12-31","eligible_date":"2015-01-05","breadth":1},
                {"signal_date":"2015-01-02","eligible_date":"2015-01-05","breadth":50}]
        h1=p.build_h1(weekly,["sh510300"],"2015-01-31")
        self.assertEqual(len(h1),2);self.assertEqual(h1[0]["signal_date"],"2014-12-31");self.assertEqual(h1[0]["target"],"1")
        h2=p.build_h2(weekly,{"sh510300":[]},{"sh510300":[{"date":"2015-01-02"}]},["sh510300"],"2015-01-31")
        self.assertEqual(len(h2),2);self.assertEqual(h2[0]["breadth_source_date"],"2014-12-31")


if __name__=="__main__":unittest.main()
