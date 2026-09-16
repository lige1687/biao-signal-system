"""Synthetic contract audit. Frozen dependencies + untouched tenth supplements only."""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import sys
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'research-package/src'))
import json
import hashlib
import pandas as pd
from lei_signal.rules import two_b_reversal as c, module_d_false_breakout as d
from lei_signal.domain.rules_config import get_rule, load_ruleset
from lei_signal.features.pivots import confirmed_pivots, swing_lows
from lei_signal.rules.dual_ma import ema20_reclaim_state, dual_ma_bull_state

def frame(n):
    f = pd.DataFrame(index=pd.bdate_range('2024-01-02', periods=n))
    for name in ('open', 'close'): f[name] = 104.
    f['high'] = 105.; f['low'] = 103.; f['volume'] = 1000000.
    for name in ('ema20','ema60','ema120','sma20','sma60','sma120','close_lag20'): f[name] = 100.
    f['signal_color'] = 'green'
    return f

def bar(f,i,close,low):
    for name,value in [('open',close),('close',close),('low',low),('high',max(close,low)+1)]:
        f.iloc[i,f.columns.get_loc(name)] = value

def serial(events):
    return [dict(event_id=e.event_id,day=str(e.available_date),lifecycle_id=e.lifecycle_id,evidence=e.evidence) for e in events]

def save_frame(f,name):
    f.to_csv(HERE/(name+'.csv'),index_label='date')

results = {'input_kind':'synthetic precomputed feature frames; deliberately isolated rule inputs, not raw OHLC-derived market histories', 'parameter_changes':False}

# A later confirmed valley supersedes the old one according to C1, but the code scans both.
f = frame(27)
bar(f,3,101,100); bar(f,11,102,101); bar(f,18,99.5,99); bar(f,19,104,103)
for i in range(len(f)):
    f.iloc[i,f.columns.get_loc('ema20')] = 100+i*.01
    f.iloc[i,f.columns.get_loc('sma20')] = 100+i*.01
save_frame(f,'c-recent-valley')
events=c.detect_two_b_reversal_events(f,'SYNTH')
results['c_recent_valley']={'pivots':[dict(index=p.index,price=p.price,available_date=str(p.available_date)) for p in swing_lows(confirmed_pivots(f))], 'events':serial(events),'confirmed_l1_prices':sorted(set(e.evidence['l1_price'] for e in events if e.evidence['sub_rule']==c.SUB_RULE_V1))}
assert results['c_recent_valley']['confirmed_l1_prices']==[100.,101.]
prefix_errors=[]
for cut in range(1,len(f)+1):
    pref=serial(c.detect_two_b_reversal_events(f.iloc[:cut],'SYNTH'))
    known=[e for e in serial(events) if e['day']<=str(f.index[cut-1].date())]
    if pref!=known: prefix_errors.append(cut)
results['c_all_prefixes']={'cuts':len(f),'differences':prefix_errors}
assert not prefix_errors

# D backdates a zone's end to the first absent day only after the 21st absent day.
g=frame(219)
for name in ('open','close'): g[name]=100.
g['high']=100.5; g['low']=99.8
g.loc[g.index[191]:,'ema120']=110.
bar(g,191,99.8,99.)
bar(g,195,98.,97.5)
bar(g,196,100.5,99.8)
save_frame(g,'d-future-zone-end')
params=d._params(get_rule(d.RULE_ID))
pref=d.detect_module_d_events(g.iloc[:197],'SYNTH')
full=d.detect_module_d_events(g,'SYNTH')
results['d_future_zone_end']={'prefix_length':197,'full_length':len(g),'prefix_intervals':d._zone_intervals(g.iloc[:197],params[1],params[2],params[3]),'full_intervals':d._zone_intervals(g,params[1],params[2],params[3]),'prefix_events':serial(pref),'full_events':serial(full),'disappeared_event_ids':sorted(set(e.event_id for e in pref)-set(e.event_id for e in full))}
assert any(e.evidence['sub_rule']==d.SUB_RULE_CONFIRMED for e in pref)
assert results['d_future_zone_end']['disappeared_event_ids']

# D recent-valley requirement: both confirmed valleys in a single active zone are scanned.
h=frame(224)
h['open']=100.; h['close']=100.; h['high']=100.5; h['low']=99.8
bar(h,189,99.8,99.); bar(h,201,99.8,99.2)
bar(h,210,98.8,98.5); bar(h,211,100.5,99.8)
save_frame(h,'d-recent-valley')
hevents=d.detect_module_d_events(h,'SYNTH')
results['d_recent_valley']={'events':serial(hevents),'confirmed_valleys':sorted(set(e.evidence['valley_price'] for e in hevents if e.evidence['sub_rule']==d.SUB_RULE_CONFIRMED))}
assert results['d_recent_valley']['confirmed_valleys']==[99.,99.2]

# C v2/v3 use current same-day and previous-day MA data, with no new rule parameters.
j=frame(24)
bar(j,3,101,100); bar(j,10,99.5,99); bar(j,11,100.5,100.)
j['ema20']=102.; j['sma20']=102.
j.loc[j.index[12]:,'ema20']=[103.5+i*.01 for i in range(len(j)-12)]
j.loc[j.index[13]:,'sma20']=[103.5+i*.01 for i in range(len(j)-13)]
save_frame(j,'c-version-timing')
jevents=c.detect_two_b_reversal_events(j,'SYNTH')
results['c_version_timing']={'events':serial(jevents),'states':[dict(day=str(ts.date()),close=float(j.loc[ts,'close']),ema20=float(j.loc[ts,'ema20']),sma20=float(j.loc[ts,'sma20']),v2=bool(ema20_reclaim_state(j).loc[ts]),v3=bool(dual_ma_bull_state(j).loc[ts])) for ts in j.index]}
assert {e.evidence['version'] for e in jevents if 'version' in e.evidence}=={'v1','v2','v3'}
assert all(Path(m.__file__).resolve().is_relative_to(HERE/'research-package') for m in [c,d])
results['imports']={name:module.__file__ for name,module in sys.modules.copy().items() if name.startswith('lei_signal') and getattr(module,'__file__',None)}
assert all(Path(p).resolve().is_relative_to(HERE/'research-package') for p in results['imports'].values())
results['effective_parameters']={key:load_ruleset()['rules'][key] for key in ['two_b_reversal','module_d_false_breakout','swing_pivots','tradability_gate','clock_classifier']}
(HERE/'synthetic-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps({key:value for key,value in results.items() if key in ['c_all_prefixes','d_recent_valley']},ensure_ascii=False))
print('Synthetic audit assertions passed; known defects reproduced, no implementation fixes applied.')
