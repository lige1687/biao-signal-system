import importlib.util
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parents[1]/"research-twelfth-2026-09-08/precision-fix/engine.py"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

old=load("technical_old_precision_engine",ORIGINAL)
new=load("technical_initial_cash_engine",HERE/"engine.py")

def bars():
    def b(x):return dict(open=x,high=x,low=x,close=x,volume=1.)
    return {"X":{"2024-01-01":b(10.),"2024-01-02":b(10.),"2024-01-03":b(10.),"2024-01-04":b(10.)}}

def candidate(config="A20E",target=13.,stop=9.):
    return dict(candidate_id=config+"-1",config_id=config,symbol="X",signal_date="2024-01-02",
                signal_accepted=True,signal_reject_reason=None,signal_ref=10.,target=target,stop=stop,
                upper=None,variant="early")

def run(module,config="A20E",cs=None,**kw):
    return module.simulate(bars(),[],cs or {},{},start="2024-01-02",end="2024-01-04",
        fee=.001,config_id=config,limits={"X":.1},blocked_dates={},limit_changes={},
        explicit_config_set={"A20E"},exit_rule=lambda p,o,c:None,**kw)

class EngineTests(unittest.TestCase):
    def test_default_is_exactly_old_weekly_behavior(self):
        self.assertEqual(run(old,weekly_per_symbol=250),run(new,weekly_per_symbol=250))

    def test_initial_cash_is_one_time_and_visible_before_first_trade(self):
        r=run(new,weekly_per_symbol=0,initial_per_symbol=100000)
        self.assertEqual([x["deposit"] for x in r["daily"]],[0.,0.,0.])
        self.assertTrue(all(x["total_funding"]==100000 for x in r["daily"]))
        self.assertTrue(all(x["equity"]==100000 for x in r["daily"]))
        self.assertEqual(r["events"],[dict(date="2024-01-02",kind="initial_deposit",symbol="all",amount=100000.)])

    def test_one_percent_prior_equity_and_lot_rounding(self):
        r=run(new,cs=[candidate()],weekly_per_symbol=0,initial_per_symbol=100000)
        buy=r["trades"][0]
        self.assertEqual(buy["risk_budget"],1000.)
        self.assertEqual(buy["previous_product_equity"],100000.)
        self.assertEqual(buy["shares"],1000)

    def test_diagnostic_uses_available_cash_without_one_percent_scaling(self):
        r=run(new,config="R0",cs=[candidate("R0",target=None)],weekly_per_symbol=0,initial_per_symbol=100000)
        buy=r["trades"][0]
        self.assertIsNone(buy["risk_budget"])
        self.assertEqual(buy["shares"],9900)

    def test_exact_three_reward_risk_passes_below_three_rejects(self):
        good=run(new,cs=[candidate(target=13.)],weekly_per_symbol=0,initial_per_symbol=100000)
        bad=run(new,cs=[candidate(target=12.999999)],weekly_per_symbol=0,initial_per_symbol=100000)
        self.assertEqual(good["orders"][0]["status"],"filled")
        self.assertEqual(bad["orders"][0]["reason"],"signal_rr_below3")

    def test_zero_candidate_account_remains_complete_cash(self):
        r=run(new,weekly_per_symbol=0,initial_per_symbol=100000)
        self.assertEqual(r["orders"],[]);self.assertEqual(r["trades"],[])
        self.assertEqual(r["daily"][-1]["cash"],100000.)

    def test_acd_callback_ignores_road_exit_until_structure_breaks(self):
        r=run(new,cs=[candidate(stop=9.)],weekly_per_symbol=0,initial_per_symbol=100000)
        self.assertEqual([t["side"] for t in r["trades"]],["buy"])
        self.assertFalse(r["roundtrips"][0]["closed"])

if __name__=="__main__":unittest.main()
