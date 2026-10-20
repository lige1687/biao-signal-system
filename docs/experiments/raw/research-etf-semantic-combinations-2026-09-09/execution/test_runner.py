import importlib.util,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('runner',H/'run.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_nested_groups(self):
  c={'condition_P':True,'condition_Q':True}
  self.assertTrue(all(m.selected(c,g) for g in ('G0','GP','GQ','GPQ')))
 def test_unknown_not_false_group_member(self):
  c={'condition_P':None,'condition_Q':True};self.assertTrue(m.selected(c,'G0'));self.assertTrue(m.selected(c,'GQ'));self.assertFalse(m.selected(c,'GP'))
 def test_target_exit(self):self.assertEqual(m.exit_rule('E0')({'target':10},{},10),'known_target_reached')
 def test_target_is_strictly_close_based(self):self.assertIsNone(m.exit_rule('E0')({'target':10},{},9.99))
 def test_e1_black_only(self):self.assertEqual(m.exit_rule('E1')({'target':12},{'ema20':10,'cost20':11},9),'black_after_entry')
 def test_gray_does_not_exit(self):self.assertIsNone(m.exit_rule('E1')({'target':12},{'ema20':10,'cost20':8},9))
 def test_structure_priority_is_engine_owned(self):self.assertIsNone(m.exit_rule('E0')({'target':12},{},9))
if __name__=='__main__':unittest.main()
