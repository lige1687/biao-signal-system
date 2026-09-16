import gzip,importlib.util,json,sys
from pathlib import Path
import pandas as pd
H=Path(__file__).parent;OLD=H.parents[1]/'research-broad-etf-technical-2026-09-08/execution'
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
old=load('oldreal',OLD/'engine.py');new=load('newreal',H/'engine.py')
rows=pd.read_csv(H/'inputs/bars/sh510300-nominal.csv').to_dict('records');prices={'sh510300':{r['date']:{k:r[k] for k in ('open','high','low','close','volume')} for r in rows}}
actions=[]
for a in json.load(open(H/'inputs/actions.json')):
 if a['symbol']!='sh510300':continue
 x=dict(a,ex_date=a['effective_date']);x['cash_per_share' if a['type']=='cash_dividend' else 'ratio']=float(a['cash' if a['type']=='cash_dividend' else 'ratio']);actions.append(x)
with gzip.open(H/'inputs/exit-observations.json.gz','rt') as f:obs=json.load(f)
cs=[c for c in json.load(open(H/'inputs/diagnostic-candidates.json')) if c['symbol']=='sh510300' and c['config_id']=='R1']
kw=dict(start='2015-01-01',end='2026-06-30',initial_per_symbol=100000,weekly_per_symbol=0,fee=.001,config_id='R1',limits={'sh510300':.1},limit_changes={'sh510300':[]},blocked_dates={'sh510300':[]})
a=old.simulate(prices,actions,cs,{'sh510300':obs['sh510300']},**kw);b=new.simulate(prices,actions,cs,{'sh510300':obs['sh510300']},**kw)
checks={k:a[k]==b[k] for k in ('daily','trades','orders','events','roundtrips')};assert all(checks.values())
print(json.dumps({'account':'sh510300-R1-fee10bp','all_five_tables_exact':True,'tables':checks},indent=2))
