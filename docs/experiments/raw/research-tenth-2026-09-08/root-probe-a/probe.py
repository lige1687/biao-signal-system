"""Read-only frozen A-contract probes. No real instrument candidates or returns."""
from pathlib import Path
import sys, json, hashlib
from dataclasses import asdict
from unittest.mock import patch
import pandas as pd
import numpy as np
ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PKG = ROOT / 'docs/experiments/raw/research-eighth-2026-09-08/b-research-fix/research-package'
sys.path.insert(0, str(PKG / 'src'))
from lei_signal.rules import first_ma_pullback as a
from lei_signal.rules.strict_structure import detect_strict_structure_events, StrictStructure
from lei_signal.features.weekly_context import weekly_env_series
from lei_signal.data.point_in_time import aggregate_weekly
from lei_signal.domain.rules_config import get_rule

def encode(obj):
    if hasattr(obj, 'isoformat'): return obj.isoformat()
    if hasattr(obj, 'value'): return obj.value
    if isinstance(obj, np.generic): return obj.item()
    raise TypeError(type(obj).__name__)
def event(e): return asdict(e)
def bars(rows):
    f = pd.DataFrame(rows, columns=['open','high','low','close'], index=pd.bdate_range('2024-01-01',periods=len(rows)))
    f['volume']=1000.
    return f

def derived(rows):
    f=bars(rows)
    f['signal_color']='green'
    for n, sm, em in [(20,9.2,8.9),(60,8.0,8.0),(120,7.0,7.0)]:
        f[f'sma{n}']=sm
        f[f'ema{n}']=em + np.arange(len(f))*.001
        f[f'close_lag{n}']=8.5
    return f

def controlled(frame, weekly=None, structures=None, clock=None):
    with patch.object(a,'weekly_env_series', lambda f: pd.Series(True if weekly is None else weekly[:len(f)],index=f.index)), patch.object(a,'clock_series',lambda f:pd.Series(2 if clock is None else clock[:len(f)],index=f.index)):
        if structures is None: return a.detect_first_ma_pullback_events(frame,'SYNTHETIC')
        with patch.object(a,'detect_strict_structures',lambda f: structures):
            return a.detect_first_ma_pullback_events(frame,'SYNTHETIC')

def confirmed(es):return [e for e in es if e.evidence['sub_rule']==a.SUB_RULE_CONFIRMED]
report={'scope':'Frozen package, synthetic only; isolated derived-column probes patch clock/week and explicitly named structures; no full-market proof.', 'package':str(PKG.relative_to(ROOT)), 'tests':{}}
# 1. Exact four-bar counterexample in actual frozen strict detector.
f=bars([(9.2,9.8,9.,9.4),(9.9,10.3,9.3,10.2),(10.2,10.8,9.7,10.6),(10.1,10.7,9.8,10.4)])
p=detect_strict_structure_events(f.iloc[:3],'SYNTHETIC'); full=detect_strict_structure_events(f,'SYNTHETIC')
report['tests']['strict_future_contained_bar']={'input':f.reset_index(names='date').to_dict('records'),'prefix':[event(e) for e in p], 'full':[event(e) for e in full], 'past_changed':set(e.event_id for e in p)!=set(e.event_id for e in full if e.available_date<=f.index[2].date())}
assert report['tests']['strict_future_contained_bar']['past_changed']
# 2. Propagation through actual A cycle, only environmental dependencies fixed.
f=derived([(9.,10.,8.,9.)]*20+[(9.2,9.8,9.,9.4),(9.9,10.3,9.3,10.2),(10.2,10.8,9.7,10.6),(10.1,10.7,9.8,10.4)])
p=controlled(f.iloc[:23]); full=controlled(f)
past=[e for e in full if e.available_date<=f.index[22].date()]
report['tests']['a_future_contained_bar']={'input':f.reset_index(names='date').to_dict('records'),'prefix':[event(e) for e in confirmed(p)], 'full':[event(e) for e in confirmed(full)],'past_confirmed_changed':[event(e) for e in confirmed(p)] != [event(e) for e in confirmed(past)]}
assert report['tests']['a_future_contained_bar']['past_confirmed_changed']
# 3. Weekly environment blocks confirmation but does not block a fresh touch after episode already starts.
w=[True]*len(f); w[20:]=[False]*(len(f)-20)
es=controlled(f,weekly=w,structures=[])
bad=[e for e in es if e.evidence['sub_rule']==a.SUB_RULE_TOUCHED and e.available_date>=f.index[20].date()]
report['tests']['weekly_false_new_touch']={'touches':[event(e) for e in bad], 'confirmed_count':len(confirmed(es))}
assert bad and any(e.evidence['weekly_bull_env'] is False for e in bad)
# 4. Bottom structure invalidates after touch, but cached A3 reference still accepted.
g=f.iloc[:23].copy(); g.loc[g.index[20],'low']=9.3; g.loc[g.index[21],['low','close']]=[8.8,9.4]; g.loc[g.index[22],['low','close']]=[8.9,10.6]
s=StrictStructure(side='bottom',confirmed_date=g.index[20].date(),reference_price=9.0,trigger_price=9.5,final_price=10.,reference_date=g.index[18].date(),contained_bars_merged=2,structure_id='synthetic_bottom',invalidated_date=g.index[21].date())
# keep close > EMA20 on previous day so no reclaim alternative.
ck=[2]*len(g); ck[21]=3
es=controlled(g,structures=[s],clock=ck); stale=[e for e in confirmed(es) if e.evidence.get('a3_structure_id')=='synthetic_bottom' and e.available_date>=s.invalidated_date]
report['tests']['cached_invalidated_structure']={'structure':asdict(s),'confirmed':[event(e) for e in stale]}
assert stale
# 5. Actual weekly aggregation across warmup and all ten last daily cuts.
idx=pd.bdate_range('2018-01-01',periods=650); c=100*(1.0012**np.arange(650))
h=pd.DataFrame({'open':c,'high':c*1.01,'low':c*.99,'close':c,'volume':1000.},index=idx)
whole=weekly_env_series(h); checks=[]
for cut in range(590,611):
    part=weekly_env_series(h.iloc[:cut]); checks.append(bool(part.equals(whole.iloc[:cut])))
assert all(checks)
report['tests']['actual_weekly_prefix']={'cuts':list(range(590,611)), 'all_equal':all(checks),'first_true_date':str(whole[whole].index[0].date()),'first_true_completed_week_count':len(aggregate_weekly(h.loc[:whole[whole].index[0]]))}
# 6. No volume: explicit declared required columns insufficient for actual function input.
try: a.detect_first_ma_pullback_events(f.drop(columns='volume'),'SYNTHETIC')
except Exception as exc: report['tests']['volume_implicit_required']={'error_type':type(exc).__name__,'message':str(exc)}
else: report['tests']['volume_implicit_required']={'error_type':None}
# Exact source hashes and current-vs-frozen equivalence.
relpaths=['rules/first_ma_pullback.py','features/weekly_context.py','rules/strict_structure.py','data/point_in_time.py','data/calendar.py','backtest/engine.py','features/indicators.py','rules/clock_classifier.py','domain/rules_config.py']
report['sources']=[]
for rel in relpaths:
    curr=ROOT/'src/lei_signal'/rel; frozen=PKG/'src/lei_signal'/rel
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report['sources'].append({'current':str(curr.relative_to(ROOT)),'frozen':str(frozen.relative_to(ROOT)),'current_sha256':sha(curr),'frozen_sha256':sha(frozen),'identical':sha(curr)==sha(frozen)})
for path in ['AGENTS.md','docs/trading-spec-v1.md','configs/rules.v1.yaml','configs/rules.v2.yaml','.claude/skills/macd-reading/SKILL.md','docs/plan-sector-trend-page.md']:
    p=ROOT/path; report['sources'].append({'path':path,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
report['versions']={'A':get_rule('first_ma_pullback').version,'strict_structure':get_rule('strict_structure').version,'python':sys.version,'pandas':pd.__version__}
(OUT/'probe-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=encode)+'\n')
print(json.dumps({k:({x:y for x,y in v.items() if x not in ['input','prefix','full','structure','confirmed','touches']} or {'recorded':True}) for k,v in report['tests'].items()},ensure_ascii=False,indent=2))
