"""Thin pool adapter over frozen mixed-defense simulator. No run until protocol is frozen."""
from pathlib import Path
import importlib.util,json,hashlib,pandas as pd,numpy as np
from collections import defaultdict
HERE=Path(__file__).resolve().parent
REPO=Path(__file__).resolve().parents[5]
MIXED=REPO/'docs/experiments/raw/research-mixed-defense-2026-09-09/execution/run.py'
FULLRUN=REPO/'docs/experiments/raw/research-rotation-clean-2026-09-09/full-execution/run.py'
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=module(MIXED,'frozen_mixed'); F=module(FULLRUN,'frozen_full')
def restricted_decisions(idx,allowed):
 """Same frozen indicators; only eligibility/ranking universe changes."""
 allowed=set(allowed); piv=idx.pivot(index='date',columns='symbol');months={}
 for d in sorted(idx.date.unique()):
  if '2020-11-01'<=d<=M.END:months[d[:7]]=d
 rows=[]
 for d in months.values():
  mom={s:piv.loc[d,('momentum',s)] if d in piv.index and ('momentum',s) in piv else np.nan for s in M.SYMS}
  elig=[s for s in M.SYMS if s in allowed and d in piv.index and ('valid_count',s) in piv and pd.notna(piv.loc[d,('valid_count',s)]) and piv.loc[d,('valid_count',s)]>=273]
  ranked_all=sorted([s for s in elig if pd.notna(mom[s])],key=lambda s:(-mom[s],s));ranked=[s for s in ranked_all if pd.isna(piv.loc[d,('rv_rank',s)]) or piv.loc[d,('rv_rank',s)]<.8];top=ranked[:3]
  for cfg,selected in [('equal',elig),('momentum_top3',top),('momentum_top3_sma200',top)]:
   w={s:0. for s in M.SYMS}
   for s in selected:w[s]=1/len(selected)
   rows.append(dict(config=cfg,decision_date=d,selected='|'.join(selected),ranked='|'.join(ranked),lookback_start='shift252',lookback_end='shift21',scores=json.dumps({s:(None if pd.isna(v) else float(v)) for s,v in mom.items()}),weights=json.dumps(w),trend_states=json.dumps({s:'included_monthly_without_entry_sma_filter' for s in selected})))
 return rows
def run_frozen_protocol():
 proto=HERE.parent/'dedup-protocol.json'
 if not proto.exists():raise SystemExit('dedup-protocol.json not frozen; preparation only, no returns run')
 q=json.loads(proto.read_text());allowed=q['symbols'];p,a=M.load();idx=M.economic_indices(p,a);decs=restricted_decisions(idx,allowed)
 outputs=[]
 for fee in q['fees']:
  # ordinary equal through no-exit engine with its decision config remapped
  eq=[dict(x,config='momentum_top3') for x in decs if x['config']=='equal']
  outputs.append(('equal',fee,M.simulate('no_exit_100',fee,p,a,idx,eq)))
  for method in ['no_exit_100','no_exit_75','fast_reentry_exit']:
   outputs.append((method,fee,M.simulate(method,fee,p,a,idx,decs)))
 return outputs
def main():
 q=json.loads((HERE.parent/'dedup-protocol.json').read_text()); locked=[HERE.parent/'dedup-protocol.json',HERE.parent/'dedup-protocol.sha256',MIXED]
 before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in locked}; tables=defaultdict(list); sums=[]
 for label,fee,result in run_frozen_protocol():
  summary,*parts=result; oldaid=summary['account_id']; newaid=f'{label}-fee{fee:.3f}'
  summary=dict(summary,account_id=newaid,method=label);sums.append(summary)
  for name,rows in zip(['equity','trades','orders','signals','actions','annual','per_symbol','reentry_events','periods','reentry_diagnostics'],parts):
   for r in rows:r['account_id']=newaid
   tables[name]+=rows
 for name,rows in tables.items():pd.DataFrame(rows).to_csv(HERE/f'{name}.csv',index=False)
 pd.DataFrame(sums).to_csv(HERE/'accounts.csv',index=False);(HERE/'summary.json').write_text(json.dumps({'protocol':q['id'],'accounts':sums},ensure_ascii=False,indent=2)+'\n')
 assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in locked}
 (HERE/'run-lock.json').write_text(json.dumps({'inputs':before},indent=2)+'\n')
if __name__=='__main__':main()
