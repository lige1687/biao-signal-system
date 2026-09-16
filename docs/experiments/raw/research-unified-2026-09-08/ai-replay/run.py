from pathlib import Path
import json,ast,hashlib,datetime,shutil
import pandas as pd,numpy as np
P=Path(__file__).resolve().parent;O=P.parent/'other-lines';SYMS=['512690.SS','513180.SS','512010.SS','512480.SS','510300.SS']
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str,allow_nan=False)+'\n')
# Never import the network-capable original module or execute its main.
def funcs(file,names,ns):
 t=ast.parse(file.read_text());t.body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in names];exec(compile(t,str(file),'exec'),ns);return ns

def run():
 cache=json.loads((P/'inputs/cache.json').read_text());lookup={(x['symbol'],x['date']):x['action'] for x in cache};ns=funcs(P/'inputs/mechanical.py',{'regime_series','simulate'},{'pd':pd,'POOL':P/'inputs','START':'2021-01-04','END':'2026-08-24','FEE':.001,'TARGET_TP':.4});out=[];allactions=[]
 for sym in SYMS:
  d=pd.read_parquet(P/'inputs'/f'{sym}.bars.parquet').loc['2021-01-04':'2026-08-24'];reg=ns['regime_series'](d.close)
  for mode in ['none','cached_close','cached_next_open']:
   units=cash=deposits=issued=fees=0.;lastweek=None;pending=None;rows=[];applied=0
   for i,(date,row) in enumerate(d.iterrows()):
    if pending and np.isfinite(row.open) and row.open>0:
     part=units*(.5 if pending=='sell_half' else 1);cash+=part*row.open*.999;units-=part;fees+=part*row.open*.001;allactions.append(dict(symbol=sym,mode=mode,date=str(date.date()),action=pending,timing='next_open',amount=part*row.open));pending=None;applied+=1
    before=units*row.close+cash;week=(date.isocalendar().year,date.isocalendar().week);deposit=0.
    if week!=lastweek:
     lastweek=week
     if reg.loc[date]=='downtrend':
      deposit=1.;nav=before/issued if issued else 1.;issued+=deposit/nav;deposits+=1.;units+=.999/row.close;fees+=.001;allactions.append(dict(symbol=sym,mode=mode,date=str(date.date()),action='buy',timing='same_close_legacy',amount=1.))
    act=lookup.get((sym,str(date.date())))
    if mode!='none' and act in ['sell_half','clear'] and units>0:
     if mode=='cached_next_open':pending=act
     else:
      part=units*(.5 if act=='sell_half' else 1.);cash+=part*row.close*.999;units-=part;fees+=part*row.close*.001;applied+=1;allactions.append(dict(symbol=sym,mode=mode,date=str(date.date()),action=act,timing='same_close_legacy',amount=part*row.close))
    eq=units*row.close+cash;nav=eq/issued if issued else 1.;assert abs(eq-cash-units*row.close)<1e-10
    rows.append(dict(date=str(date.date()),external_deposit=deposit,total_deposits=deposits,shares=units,cash=cash,equity=eq,unit_value=nav,total_fees=fees))
   q=pd.DataFrame(rows);positive=q[q.equity>0];out.append(dict(symbol=sym,mode=mode,deposits=deposits,final=q.equity.iloc[-1],multiple=q.equity.iloc[-1]/deposits,raw_balance_mdd=float((positive.equity/positive.equity.cummax()-1).min()),deposit_adjusted_mdd=float((q.unit_value/q.unit_value.cummax()-1).min()),sell_actions_applied=applied,pending_action=pending,ending_cash=cash,total_fees=fees));q.to_csv(P/(sym+'_'+mode+'.csv'),index=False,float_format='%.17g')
  out.append(dict(symbol=sym,mode='legacy_mechanical_trend',**ns['simulate'](sym,'trend'),note='原机械路径清仓后停投，可能和AI版不同本金；非公平资金效果对比'))
 save('results.json',out);pd.DataFrame(allactions).to_csv(P/'actions.csv',index=False);save('run-manifest.json',{'script_hash':h(Path(__file__)),'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':{str(f):h(f) for f in (P/'inputs').glob('*') if f.is_file()},'model_calls':0,'scope':'cached action replay, not historical model reproduction or corrected strategy'})
 print(json.dumps(out,ensure_ascii=False,default=str))
if __name__=='__main__':run()
