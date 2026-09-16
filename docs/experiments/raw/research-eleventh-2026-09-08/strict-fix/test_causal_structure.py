from pathlib import Path
import sys, importlib.util
from dataclasses import asdict
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1]; OLD=P.parent/'research-tenth-2026-09-08'
sys.path.insert(0,str(P/'research-package/src'))
from lei_signal.rules.strict_structure import detect_strict_structures,detect_strict_structure_events

def frame(rows):
 f=pd.DataFrame(rows,columns=['open','high','low','close'],index=pd.bdate_range('2024-01-01',periods=len(rows)));f['volume']=1000.;return f

def serialized(f):return [asdict(e) for e in detect_strict_structure_events(f,'SYNTHETIC')]

def test_contained_tail_keeps_first_confirmation_and_later_invalidation():
 f=frame([(9.2,9.8,9.,9.4),(9.9,10.3,9.3,10.2),(10.2,10.8,9.7,10.6),(10.1,10.7,9.8,10.4),(9.8,11.,8.8,10.5)])
 full=serialized(f)
 for n in range(1,len(f)+1):
  assert serialized(f.iloc[:n])==[e for e in full if e['available_date']<=f.index[n-1].date()]
 b=[s for s in detect_strict_structures(f) if s.side=='bottom' and s.reference_price==9.]
 assert len(b)==1
 assert b[0].confirmed_date==f.index[2].date()
 assert b[0].final_price==10.8
 assert b[0].invalidated_date==f.index[4].date()

def legacy_with_candidate_dates():
 # Independent reference retains old whole-history algorithm; added field is tracing only.
 src=(OLD/'research-package/src/lei_signal/rules/strict_structure.py').read_text()
 src=src.replace('    structure_id: str = ""','    trigger_date: date | None = None\n    structure_id: str = ""')
 for side in ('top','bottom'):
  old=f'contained_bars_merged=pending_{side}.merged_count,'
  src=src.replace(old,old+f'\n                        trigger_date=pending_{side}.trigger_date,')
 import types
 mod=types.ModuleType('legacy_strict_reference');sys.modules[mod.__name__]=mod
 exec(compile(src,'frozen_tenth_strict_plus_trace','exec'),mod.__dict__)
 return mod

def slow_daily_reference(f):
 legacy=legacy_with_candidate_dates();accepted={}
 for n in range(1,len(f)+1):
  day=f.index[n-1].date()
  for s in legacy.detect_strict_structures(f.iloc[:n]):
   if s.confirmed_date!=day:continue
   key=(s.side,s.reference_date,s.trigger_date,s.reference_price,s.trigger_price)
   if key not in accepted:
    row=asdict(s);row.pop('trigger_date');row['invalidated_date']=None;row['invalidated_reason']=None;accepted[key]=row
 # Separate reference recomputes the first subsequent raw extreme breach.
 for row in accepted.values():
  later=f.loc[f.index.date>row['confirmed_date']]
  hit=later.high>row['reference_price'] if row['side']=='top' else later.low<row['reference_price']
  if hit.any():
   row['invalidated_date']=later.index[hit][0].date()
   row['invalidated_reason']='higher_high_breaks_top' if row['side']=='top' else 'new_low_breaks_bottom'
 return sorted(accepted.values(),key=lambda r:(r['confirmed_date'],r['side']))

def test_stream_matches_slow_daily_original_reference():
 for seed in range(8):
  rng=np.random.default_rng(seed);c=100+np.cumsum(rng.normal(0,1.4,60));width=rng.uniform(.2,3.,60)
  f=frame(list(zip(c,c+width,c-width,c)))
  expected=slow_daily_reference(f)
  actual=sorted([asdict(s) for s in detect_strict_structures(f)],key=lambda r:(r['confirmed_date'],r['side']))
  assert actual==expected,seed
  full=serialized(f)
  assert len({e['event_id'] for e in full})==len(full)
  for n in range(1,len(f)+1):
   assert serialized(f.iloc[:n])==[e for e in full if e['available_date']<=f.index[n-1].date()],(seed,n)
