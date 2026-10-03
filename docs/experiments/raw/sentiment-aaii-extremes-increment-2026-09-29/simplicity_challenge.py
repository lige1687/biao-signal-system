"""Recorded after original inline execution: reproduce saved-error challenge.

This creates no new fit, label or draw. Refuses overwriting the existing output;
for a reproduction use a different empty --output path in this raw directory.
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'executor/run-01'

def quant(v,q):
    v=sorted(v);z=(len(v)-1)*q;k=math.floor(z)
    return v[k]+(v[min(k+1,len(v)-1)]-v[k])*(z-k)

def calculate():
    results=json.loads((RUN/'results.json').read_text())
    manifest=json.loads((RUN/'manifest.json').read_text())
    for name,rec in manifest['outputs'].items():
        assert hashlib.sha256((RUN/name).read_bytes()).hexdigest()==rec['sha256']
    out={}
    for h,res in results['horizons'].items():
        draws=list(csv.DictReader((RUN/f'draws-h{h}.csv').open()));pairs={}
        for a,b in [('X','I'),('BX','I'),('BXE','I'),('XE','X')]:
            values=[100*(1-float(d['mse_'+a])/float(d['mse_'+b])) for d in draws]
            mse=res['overall']['mse']
            pairs[a+'_vs_'+b]={'improvement_pct':100*(1-mse[a]/mse[b]),
                             'range':[quant(values,.025),quant(values,.975)]}
        annual=[v['improvement_pct']['BXE_vs_B'] for v in res['annual'].values() if v['n']]
        leave=[v['improvement_pct']['BXE_vs_B'] for v in res['remove_year_no_refit'].values() if v['n']]
        pred=list(csv.DictReader((RUN/f'predictions-h{h}.csv').open()));yeargroups={}
        for row in pred:
            year=row['t'][:4];g=row['group']
            d=yeargroups.setdefault(year,{}).setdefault(g,{'n':0,'sum_y':0,
                'squared_error_reduction_BXE_vs_B':0,'squared_error_reduction_BX_vs_B':0})
            d['n']+=1;d['sum_y']+=float(row['y'])
            for a in ['BX','BXE']:
                d['squared_error_reduction_'+a+'_vs_B']+=(float(row['y'])-float(row['pred_B']))**2-(float(row['y'])-float(row['pred_'+a]))**2
        for gs in yeargroups.values():
            for d in gs.values():d['mean_y']=d.pop('sum_y')/d['n']
        out[h]={'challenger_pairs':pairs,
                'positive_eval_years_BXE_vs_B':sum(v>0 for v in annual),
                'evaluated_years':len(annual),
                'leave_any_year_improvement_range':[min(leave),max(leave)],
                'year_groups':yeargroups}
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='simplicity-challenge.json')
    args=parser.parse_args();out=(ROOT/args.output).resolve()
    assert out.parent==ROOT and not out.exists(),'Refuse existing output or out-of-scope write.'
    result={'protocol':'followup-protocol.json',
        'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'new_fits':0,'new_labels':0,
        'range_kind':'original shared 52-row paired losses, exploratory additional comparisons',
        'results':calculate()}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
