from pathlib import Path
import json,hashlib,sys
import pandas as pd
R=Path(__file__).resolve().parents[5]; B=Path(__file__).resolve().parent; S=B.parent.parent/'research-mixed-defense-2026-09-09'/'execution'; D=B.parent.parent/'research-rotation-clean-2026-09-09'/'full-pool-preparation'
if len(sys.argv)>1:
 S=Path(sys.argv[1]).resolve(); outdir=B/'representative-groups'; outdir.mkdir(exist_ok=True); B=outdir
groups={'510300':'沪深300','515130':'沪深300','512400':'有色金属','159652':'有色金属','515050':'通信','515880':'通信','515300':'300红利低波','512890':'红利低波100','518850':'黄金','588000':'科创50','515170':'食品饮料','516220':'化工','513870':'纳斯达克100','562590':'半导体材料设备'}
e=pd.read_csv(S/'equity.csv',dtype={'date':str}); t=pd.read_csv(S/'trades.csv',dtype={'date':str,'symbol':str}); a=pd.read_csv(S/'actions.csv',dtype={'date':str}); a['symbol']=a.event_id.str[:6]
p=pd.read_csv(D/'prices.csv',dtype={'date':str,'symbol':str});p['symbol']=p.symbol.str[:6]
# Daily marking uses actual quotes and explicit split rescaling on any intervening nonquote dates.
raw=json.loads((D/'action-sources/normalized-actions.json').read_text())['events'];splits={}
for x in raw:
 if (x.get('type') or x.get('action_type'))=='split': splits[(x.get('effective_date') or x.get('ex_date'),str(x['symbol'])[:6])]=float(x.get('ratio',x.get('split_ratio',1)))
dates=sorted(e.date.unique()); quotes={(x.date,x.symbol):x.close for x in p.itertuples()};marks={};rows=[]
for day in dates:
 for s in groups:
  if (day,s) in splits and s in marks:marks[s]/=splits[(day,s)]
  if (day,s) in quotes: marks[s]=quotes[(day,s)]
 rows.append({'date':day,**{s:marks.get(s,0.) for s in groups}})
mark=pd.DataFrame(rows).set_index('date'); out=[]; expo=[];checks=[]
for aid,g in e.groupby('account_id',sort=False):
 g=g.set_index('date');tt=t[t.account_id==aid]; aa=a[a.account_id==aid]; cum={}
 for end in ['2024-12-31','2026-06-30']:
  es=g.loc[end]; totals={}
  for s,grp in groups.items():
   ts=tt[(tt.symbol==s)&(tt.date<=end)]; av=aa[(aa.symbol==s)&(aa.date<=end)]
   bought=(ts[ts.side=='buy'].notional+ts[ts.side=='buy'].fee).sum();sold=(ts[ts.side=='sell'].notional-ts[ts.side=='sell'].fee).sum()
   earned=av[av.event=='receivable'].amount.sum();paid=av[av.event=='cash_paid'].amount.sum();mv=es['units_'+s]*mark.loc[end,s];pnl=sold-bought+earned+mv
   out.append({'account_id':aid,'through_date':end,'symbol':s,'group':grp,'net_pnl':pnl,'buy_cash':bought,'sell_cash':sold,'dividend_earned':earned,'dividend_paid':paid,'receivable':earned-paid,'end_market_value':mv})
   totals[s]=pnl
  delta=sum(totals.values())-(es.equity-1000000);assert abs(delta)<1e-6,(aid,end,delta)
  checks.append({'account_id':aid,'through_date':end,'pnl_identity_error':delta})
 for grp in set(groups.values()):
  ss=[s for s in groups if groups[s]==grp]; mv=sum(g['units_'+s]*mark[s] for s in ss);ex=mv/g.equity
  both=sum((g['units_'+s]>0).astype(int) for s in ss)>=2
  expo.append({'account_id':aid,'group':grp,'average_account_share':ex.mean(),'max_account_share':ex.max(),'calendar_days_two_group_products_held':int(both.sum()),'calendar_days':len(g)})
pd.DataFrame(out).to_csv(B/'symbol-profit-phases.csv',index=False)
v=pd.DataFrame(out); gv=v.groupby(['account_id','through_date','group'],as_index=False).net_pnl.sum();gv.to_csv(B/'group-profit-phases.csv',index=False)
pd.DataFrame(expo).to_csv(B/'group-exposure.csv',index=False)
(B/'group-accounting-checks.json').write_text(json.dumps({'passed':True,'checks':checks,'scope':'Cash flows from trades plus earned dividend rights and actual ending units*nominal marks reconcile at both cutoffs; different index designs grouped descriptively, not assumed identical holdings.'},ensure_ascii=False,indent=2)+'\n')
print(gv[(gv.account_id=='fast_reentry_exit-fee0.001')&(gv.through_date=='2026-06-30')].sort_values('net_pnl',ascending=False).to_string(index=False))
