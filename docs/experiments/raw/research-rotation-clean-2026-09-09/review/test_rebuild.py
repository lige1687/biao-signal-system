import importlib.util
from pathlib import Path
P=Path(__file__).with_name('rebuild.py')
s=importlib.util.spec_from_file_location('review_rebuild',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)

def test_temporal_decisions_and_first_signal():
 bars,acts=m.load(); econ=m.economic_indices(bars,acts); ds=m.decisions(bars,econ)
 july=[x for x in ds if x['decision_date']=='2021-07-30']
 assert len(july)==4
 for x in ds:
  for z in x['details'].values():
   assert z['latest_quote']<=x['decision_date']
   if z['momentum_skip_date']: assert z['momentum_long_date']<z['momentum_skip_date']<x['decision_date']

def test_split_connects_without_false_crash():
 bars,acts=m.load(); e=m.economic_indices(bars,acts)['512170.SH']
 # 1:3 split is effective on the no-quote halt day, between these quotes.
 nominal=bars['512170.SH'].close
 assert '2021-02-24' not in nominal.index.strftime('%Y-%m-%d')
 assert abs(float(e.loc['2021-02-25']/e.loc['2021-02-23']-1)) < .10
 assert float(nominal.loc['2021-02-25']/nominal.loc['2021-02-23']-1) < -.60

def test_no_future_action_in_pre_event_index():
 bars,acts=m.load(); allidx=m.economic_indices(bars,acts)['510300.SH']
 nofuture=m.economic_indices(bars,[a for a in acts if not (a['symbol']=='510300.SH' and (a.get('effective_date') or '')>'2024-01-01')])['510300.SH']
 assert allidx.loc[:'2023-12-31'].equals(nofuture.loc[:'2023-12-31'])
