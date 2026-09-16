from pathlib import Path
import pandas as pd,json,hashlib
P=Path(__file__).resolve().parent;OLD=P.parents[1]/'research-first-round-2026-09-08/dca';out={}
for label in ['W5','long']:
 f=OLD/f'round18_{label}_daily_ledger.csv';d=pd.read_csv(f);q=d[d.cumulative_deposit>0].copy();q['vs_deposit']=q.equity/q.cumulative_deposit-1;i=q.vs_deposit.idxmin();out[label]={'source':str(f),'source_hash':hashlib.sha256(f.read_bytes()).hexdigest(),'minimum_relative_to_deposited_principal':float(q.loc[i,'vs_deposit']),'date':q.loc[i,'date'],'ending_cash':float(q.cash.iloc[-1]),'ending_equity':float(q.equity.iloc[-1]),'deposited_total':float(q.cumulative_deposit.iloc[-1]),'new_trades_simulated':False}
(P/'principal-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out)
