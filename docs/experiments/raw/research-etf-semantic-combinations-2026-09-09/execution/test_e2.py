import importlib.util,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('e2',H/'run_e2.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
P={'position_id':'p','target':20}
class Tests(unittest.TestCase):
 def test_black_before_green_does_not_exit(self):self.assertIsNone(m.e2_rule()(P,{'ema20':10,'cost20':10},9))
 def test_buy_day_green_then_later_black(self):
  r=m.e2_rule();self.assertIsNone(r(P,{'ema20':9,'cost20':9},10));self.assertEqual(r(P,{'ema20':10,'cost20':10},9),'black_after_post_entry_green')
 def test_gray_does_not_exit_or_reset(self):
  r=m.e2_rule();r(P,{'ema20':9,'cost20':9},10);self.assertIsNone(r(P,{'ema20':11,'cost20':9},10));self.assertEqual(r(P,{'ema20':11,'cost20':11},10),'black_after_post_entry_green')
 def test_target_always_protects(self):self.assertEqual(m.e2_rule()({'position_id':'x','target':10},{},10),'known_target_reached')
 def test_new_position_resets(self):
  r=m.e2_rule();r(P,{'ema20':9,'cost20':9},10);self.assertIsNone(r({'position_id':'q','target':20},{'ema20':11,'cost20':11},10))
if __name__=='__main__':unittest.main()
