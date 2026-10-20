from adapter import M,F
import pandas as pd,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def compare_rows(a,b,drop_account=True):
 a=pd.DataFrame(a).reset_index(drop=True);b=pd.DataFrame(b).reset_index(drop=True)
 if drop_account:
  a=a.drop(columns=['account_id'],errors='ignore');b=b.drop(columns=['account_id'],errors='ignore')
 if list(a.columns)!=list(b.columns) or len(a)!=len(b):return False
 for c in a:
  if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
   if (a[c]-b[c]).abs().fillna(0).max()>1e-8:return False
  elif not a[c].fillna('').astype(str).equals(b[c].fillna('').astype(str)):return False
 return True
p,a=M.load();idx=M.economic_indices(p,a);decs=M.decisions(idx);rows=[]
old_summary=json.loads((M.HERE/'summary.json').read_text())['accounts']; oldeq=pd.read_csv(M.HERE/'equity.csv');oldt=pd.read_csv(M.HERE/'trades.csv')
for method in ['no_exit_100','no_exit_75','fast_reentry_exit']:
 s,*parts=M.simulate(method,.001,p,a,idx,decs); aid=s['account_id']; ref=next(x for x in old_summary if x['account_id']==aid)
 daily_ok=compare_rows(parts[0],oldeq[oldeq.account_id==aid]); trades_ok=compare_rows(parts[1],oldt[oldt.account_id==aid])
 rows.append({'method':method,'fee':.001,'daily_rows':len(parts[0]),'trade_rows':len(parts[1]),'daily_exact':daily_ok,'trades_exact':trades_ok,'summary_final_diff':s['final']-ref['final'],'passed':daily_ok and trades_ok and abs(s['final']-ref['final'])<1e-8})
p2,a2=F.load();i2=F.economic_indices(p2,a2);d2=F.decisions(i2);s,*parts=F.simulate('full14','equal',.001,p2,a2,i2,d2);aid=s['account_id'];fs=json.loads((F.HERE/'summary.json').read_text())['accounts'];ref=next(x for x in fs if x['account_id']==aid);feq=pd.read_csv(F.HERE/'equity.csv');ft=pd.read_csv(F.HERE/'trades.csv')
daily_ok=compare_rows(parts[0],feq[feq.account_id==aid]);trades_ok=compare_rows(parts[1],ft[ft.account_id==aid]);rows.append({'method':'equal','fee':.001,'daily_rows':len(parts[0]),'trade_rows':len(parts[1]),'daily_exact':daily_ok,'trades_exact':trades_ok,'summary_final_diff':s['final']-ref['final'],'passed':daily_ok and trades_ok and abs(s['final']-ref['final'])<1e-8})
(HERE/'baseline-verification.json').write_text(json.dumps({'passed':all(x['passed'] for x in rows),'checks':rows},indent=2)+'\n');print(rows)
