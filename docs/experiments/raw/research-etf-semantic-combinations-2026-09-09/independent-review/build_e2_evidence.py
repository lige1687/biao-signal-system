from pathlib import Path
from datetime import date
from decimal import Decimal as D
import csv,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;EX=ROOT/'execution';IN=EX/'inputs';sys.path.insert(0,str(HERE));from prior_evidence import build_prior_evidence
def jl(p):return json.loads(p.read_text())
def rc(p):return list(csv.DictReader(p.open()))
def dec(x):return D(str(x))
def records(base,summary,bars):
 out=[];checks=[]
 for f in jl(summary):
  folder=base/'fixed-opportunities'/f['path_id'];trips=jl(folder/'roundtrips.json');daily={r['date']:r for r in rc(folder/'daily.csv')};events=jl(folder/'events.json');rt=trips[0] if trips else None;entry=rt['entry_date'] if rt else None;maturity=None;ret60=None;hold60=None
  if rt:
   after=[d for d in bars[f['symbol']] if d>entry]
   if len(after)>=60:
    maturity=after[59];cut=min(x for x in (rt['exit_date'],maturity) if x is not None);hold60=(date.fromisoformat(cut)-date.fromisoformat(entry)).days
    if rt['exit_date'] and rt['exit_date']<=maturity:ret60=dec(rt['net_return'])
    else:
     accrued=sum((dec(e['amount']) for e in events if e['kind']=='dividend_receivable' and e.get('position_id')==rt['position_id'] and e['date']<=maturity),D(0));r=daily[maturity];ret60=(dec(r['units_'+f['symbol']])*dec(r['mark_'+f['symbol']])+accrued)/(dec(rt['entry_notional'])+dec(rt['buy_fee']))-1
    checks.append({'path_id':f['path_id'],'maturity_quote_date':maturity,'return_at_60':ret60,'holding_days_at_60':hold60})
  holding=(date.fromisoformat(rt['exit_date'] or '2026-06-30')-date.fromisoformat(entry)).days+(0 if rt and rt['exit_date'] else 1) if rt else 0
  for g in f['groups']:out.append({'candidate_id':f['candidate_id'],'symbol':f['symbol'],'group':g,'variant':f['exit_variant'],'fee':str(f['fee']),'signal_date':f['signal_date'],'entered':bool(rt),'entry_date':entry,'exit_date':rt['exit_date'] if rt else None,'net_return':rt['net_return'] if rt else None,'maturity_quote_date':maturity,'return_at_60':ret60,'holding_days':holding,'holding_days_at_60':hold60})
 return out,checks
def main():
 bars={s:[r['date'] for r in rc(IN/'bars'/f'{s}-nominal.csv')] for s in ('sh510300','sz159915')};a,c1=records(EX/'attempt-01',EX/'attempt-01/fixed-summary.json',bars);b,c2=records(EX/'attempt-e2',EX/'attempt-e2/fixed-summary.json',bars);cond=jl(EX/'conditions.json')['rows'];decisions=[{'candidate_id':x['candidate_id'],'symbol':x['symbol'],'signal_date':x['signal_date']} for x in cond];x=build_prior_evidence(a+b,decisions,groups=['G0','GP','GQ','GPQ'],variants=['E0','E1','E2'],fees=['0.001','0.002']);assert len(x)==2016
 for r in x:
  assert r['maximum_completed_known_date'] is None or r['maximum_completed_known_date']<r['decision_date'];assert r['maximum_maturity_quote_date'] is None or r['maximum_maturity_quote_date']<r['decision_date']
 (HERE/'prior-evidence-e0-e1-e2-2016.json').write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n');(HERE/'maturity-60-e2-independent.json').write_text(json.dumps(c2,ensure_ascii=False,indent=2,default=str)+'\n');print(json.dumps({'status':'passed','rows':len(x),'e2_maturity_paths':len(c2)}))
if __name__=='__main__':main()
