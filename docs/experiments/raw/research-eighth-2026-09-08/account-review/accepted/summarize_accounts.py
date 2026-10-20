from pathlib import Path
import sys
sys.dont_write_bytecode = True
import json
import hashlib
import importlib.util
from collections import Counter
import pandas as pd
import numpy as np

P = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('research_metrics',P/'spark-metrics/metrics.py')
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)

def records(path):
    try: return pd.read_csv(path).replace({np.nan:None}).to_dict('records')
    except pd.errors.EmptyDataError: return []

def read(path): return json.loads(path.read_text())

def main():
    root=P/'account-results'; summaries=[]; annual=[]; mappings=[]
    for i in range(8):
        cfg=f'P{i}'; q=root/cfg
        data={k:records(q/(k+'.csv')) for k in ['daily','trades']}
        data.update({k:read(q/(k+'.json')) for k in ['orders','events','roundtrips']})
        m=metrics.summarize(data); m['config_id']=cfg
        m['raw_candidates']=sum(o['side']=='buy' and 'candidate_id' in o for o in data['orders'])
        m['signal_accepted_candidates']=sum(o['side']=='buy' and o.get('signal_accepted') is True for o in data['orders'])
        summaries.append(m)
        df=pd.DataFrame(data['daily'])
        pnl=df.equity.diff().fillna(df.equity.iloc[0])-df.deposit
        assert abs(pnl.sum()-m['net_gain'])<1e-6
        assert abs(-min(df.drawdown)-m['max_drawdown'])<1e-12
        df['investment_pnl']=pnl;df['year']=df.date.str[:4]
        for year,g in df.groupby('year'):
            annual.append({'config_id':cfg,'year':year,'investment_pnl':float(g.investment_pnl.sum()),
                           'deposits':float(g.deposit.sum()),'ending_equity':float(g.equity.iloc[-1]),
                           'mean_exposure':float((g.assets/g.equity.replace(0,np.nan)).mean()),
                           'trade_count':sum(t['date'].startswith(year) for t in data['trades'])})
        for o in data['orders']:
            if o['side']=='buy' and 'candidate_id' in o:
                mappings.append({'candidate_id':o['candidate_id'],'config_id':cfg,'symbol':o['symbol'],
                  'signal_date':o['signal_date'],'opportunity_key':o['opportunity_key'],
                  'signal_accepted':o['signal_accepted'],'signal_rr':o.get('signal_rr'),
                  'status':o['status'],'reason':o['reason'],'planned_date':o.get('planned_date'),
                  'resolved_date':o.get('resolved_date'),'open_rr':o.get('open_rr'),
                  'shares':o.get('shares'),'position_id':o.get('position_id')})
    summaries_by={m['config_id']:m for m in summaries}
    comparisons=[]
    for a,b in [('P1','P0'),('P3','P2'),('P4','P3'),('P7','P4'),('P4','P0'),('P4','P5'),('P4','P6')]:
        comparisons.append({'candidate':a,'reference':b,**{k:summaries_by[a][k]-summaries_by[b][k]
           for k in ['last_equity','net_gain','max_drawdown','trade_count','fees','mean_exposure']}})
    (root/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    pd.DataFrame(summaries).to_csv(root/'summary.csv',index=False)
    pd.DataFrame(annual).to_csv(root/'annual-contributions.csv',index=False)
    pd.DataFrame(mappings).to_csv(root/'candidate-outcomes.csv',index=False)
    (root/'comparisons.json').write_text(json.dumps(comparisons,indent=2,allow_nan=False)+'\n')
    (root/'summary-code-lock.json').write_text(json.dumps({'files':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()
           for f in [Path(__file__),P/'spark-metrics/metrics.py']},'meaning':'descriptive summaries; no significance or adoption threshold'},indent=2)+'\n')
    print(pd.DataFrame(summaries)[['config_id','last_equity','net_gain','max_drawdown','trade_count','mean_exposure','completed_trades']].to_string(index=False))

if __name__=='__main__':main()
