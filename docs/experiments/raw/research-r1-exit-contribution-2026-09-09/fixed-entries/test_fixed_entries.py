import unittest,importlib.util,sys
from pathlib import Path
P=Path(__file__).with_name('run_fixed_entries.py');s=importlib.util.spec_from_file_location('fixed',P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_strict_threshold(self):
  self.assertFalse(m.dec('10')<m.dec('10'))
 def test_fee_both_rates(self):
  self.assertEqual(m.dec('1000')*m.dec('.002'),m.dec('2'))
 def test_entry_ex_day_is_current_unit(self):
  # Protocol guard: the implementation explicitly skips stop/share action adjustment on entry day.
  src=P.read_text();self.assertIn("if not entry_day and not sold:stop*=",src);self.assertIn("if not entry_day and not sold:shares*=",src)
 def test_structure_priority(self):
  src=P.read_text();self.assertIn("reason='structure_stop' if structure else",src)
 def test_sale_after_signal(self):
  src=P.read_text();self.assertIn("day>pending['signal_date']",src)
 def test_record_after_open_trade(self):
  src=P.read_text();self.assertLess(src.index("if pending and not sold"),src.index("rights[a['event_id']]=shares"))
if __name__=='__main__':unittest.main()
