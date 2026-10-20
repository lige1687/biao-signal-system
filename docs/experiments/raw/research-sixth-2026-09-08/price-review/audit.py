"""Bounded frozen 16-opportunity price-version audit. No network or production writes."""
from pathlib import Path
import json,hashlib,shutil,ast,dataclasses,datetime,types
import pandas as pd,numpy as np
P=Path(__file__).resolve().parent;I=P/'inputs';S=Path('/Users/yongbiaoli/lei-signal-sync');F=P.parents[1]/'research-first-round-2026-09-08/exits/reproduction_results.json'
files={'first-reproduction.json':F,'engine.py':S/'src/lei_signal/backtest/engine.py','indicators.py':S/'src/lei_signal/features/indicators.py','rules.v2.yaml':S/'configs/rules.v2.yaml'}
refs={'A':'T2_A_ETF_cm05_shrink.json','B':'T1_Bp_a61.json','C':'T2_C_stocks_v3_b15.json'};syms=['159611.SZ','000596.SZ','000568.SZ']
for m,n in refs.items():files[n]=S/'docs/experiments/raw/lifecycle_combo'/n
for group,path in [('rebuild','exit_three_piece/pool'),('snapshot','pool-snapshot-2026-08-25')]:
 for sym in syms:
  for ext in ['parquet','meta.json']:files[f'{group}-{sym}.{ext}']=S/'docs/experiments/raw'/path/f'{sym}.bars.{ext}'
manifest=[]
for name,f in files.items():
 b=f.read_bytes();h=hashlib.sha256(b).hexdigest();dst=I/name
 if dst.exists():assert dst.read_bytes()==b,'Input drift; do not overwrite frozen input'
 else:dst.write_bytes(b)
 assert hashlib.sha256(f.read_bytes()).hexdigest()==h
 manifest.append(dict(file=name,source=str(f),sha256=h,bytes=len(b)))
(P/'input-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
# Load only deterministic legacy classes/functions from frozen text, without package imports.
ns=dict(pd=pd,np=np,dataclass=dataclasses.dataclass,field=dataclasses.field,date=datetime.date,EXIT_COSTBASIS='a6_1_costbasis',EXIT_TOP_PLUS_KEYWAVE='a6_2_top_plus_keywave',EXIT_STRUCTURE_STOP='a6_3_structure_stop',EXIT_B3_DUAL='b3_dual')
selected=[]
for file,names in [('indicators.py',{'seeded_ema'}),('engine.py',{'FeeModel','EntrySpec','Trade','is_cn_symbol','simulate_trade'})]:
 selected.extend(n for n in ast.parse((I/file).read_text()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names)
mod=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+selected,type_ignores=[]);ast.fix_missing_locations(mod);exec(compile(mod,'frozen_legacy','exec'),ns)
fee=ns['FeeModel']('standard',5.,.005)
fields=['entry_date','entry_price','exit_date','exit_price','exit_reason','holding_bars','r_net']
def eq(a,b):
 if isinstance(a,(int,float)) and isinstance(b,(int,float)):return abs(a-b)<1e-9
 return a==b
results=[];pair_stats=[];data={};first=json.loads((I/'first-reproduction.json').read_text());details=[]
for sym in syms:
 for group in ['rebuild','snapshot']:
  d=pd.read_parquet(I/f'{group}-{sym}.parquet').loc[:'2026-08-25'].copy();d.index=pd.to_datetime(d.index);d['ema20']=ns['seeded_ema'](d.close,20);d['close_lag20']=d.close.shift(20);data[group,sym]=d
 a=data['snapshot',sym];b=data['rebuild',sym];idx=a.index.intersection(b.index);diff=a.loc[idx,['open','high','low','close']]-b.loc[idx,['open','high','low','close']]
 pair_stats.append(dict(symbol=sym,snapshot_rows=len(a),rebuild_rows=len(b),snapshot_start=str(a.index.min().date()),rebuild_start=str(b.index.min().date()),overlap_rows=len(idx),columns={c:{'min_delta':float(diff[c].min()),'max_delta':float(diff[c].max()),'nonzero_rows':int((abs(diff[c])>1e-9).sum()),'rounded_unique_delta_counts':{str(k):int(v) for k,v in diff[c].round(6).value_counts().head(12).items()}} for c in diff},metadata={g:json.loads((I/f'{g}-{sym}.meta.json').read_text()) for g in ['snapshot','rebuild']}))
for m,n in refs.items():
 ref=json.loads((I/n).read_text())['trades'];sym=sorted({r['symbol'] for r in ref})[0]
 for old in [r for r in ref if r['symbol']==sym]:
  rec=dict(module=m,symbol=sym,signal_date=old['signal_date'],old={k:old.get(k) for k in fields},old_stop=old['stop_price'],scenarios={})
  for group in ['rebuild','snapshot']:
   d=data[group,sym];pos=int(d.index.get_loc(pd.Timestamp(old['signal_date'])));sp=ns['EntrySpec'](symbol=sym,signal_date=datetime.date.fromisoformat(old['signal_date']),signal_position=pos,entry_ref_price=float(d.close.iloc[pos]),stop_price=float(old['stop_price']),target_price=old['target_price'],target_source='old_frozen',reward_risk=old['reward_risk'],entry_variant=old['entry_variant'],is_first_touch=old['is_first_touch'],ma_period=old['ma_period'],clock_type=0,weekly_bull_env=False,event_id=f'{m}:{sym}:{old["signal_date"]}')
   out=ns['simulate_trade'](d,sp,exit_variant='a6_1_costbasis',fee=fee,prepared=dict(costbasis_cond=(d.close<d.ema20)&(d.close<d.close_lag20),top_dates=[]),limit_guard=True);v=json.loads(json.dumps(dataclasses.asdict(out),default=str));rec['scenarios'][group]=dict(values={k:v.get(k) for k in fields},differences={k:dict(old=old.get(k),replay=v.get(k)) for k in fields if not eq(old.get(k),v.get(k))})
   if m=='C':
    pre=d.iloc[max(0,pos-30):pos+1];rec['scenarios'][group]['prior30_min_low']=float(pre.low.min());rec['scenarios'][group]['prior30_stop_matches']=[str(t.date()) for t,x in pre.low.items() if abs(x-old['stop_price'])<1e-9]
    end=max(pd.Timestamp(old['exit_date']),pd.Timestamp(v['exit_date']));sl=d.loc[pd.Timestamp(old['entry_date']):end]
    for t,r in sl.iterrows():
     j=d.index.get_loc(t);prev=float(d.close.iloc[j-1]);details.append(dict(signal_date=old['signal_date'],pool=group,date=str(t.date()),open=float(r.open),close=float(r.close),previous_close=prev,ema20=float(r.ema20),lag20=float(r.close_lag20),stop=float(old['stop_price']),structure_breach=bool(r.close<old['stop_price']),trend_breach=bool(r.close<r.ema20 and r.close<r.close_lag20),blocked_open=bool(r.open<=prev*.905)))
  prior=next(x for x in first['trades'] if x['module']==m and x['old']['signal_date']==old['signal_date']);rec['rebuild_matches_first_round']=all(eq(rec['scenarios']['rebuild']['values'][k],prior['current'].get(k)) for k in fields);results.append(rec)
pd.DataFrame(details).to_csv(P/'c-daily-diagnostics.csv',index=False,float_format='%.17g')
output=dict(scope='Fixed original 16 opportunities; default exit only; not re-generated entries or new strategy test',fee=dataclasses.asdict(fee),cutoff='2026-08-25',summary=dict(n=len(results),snapshot_mismatches=sum(bool(x['scenarios']['snapshot']['differences']) for x in results),rebuild_mismatches=sum(bool(x['scenarios']['rebuild']['differences']) for x in results),rebuild_matches_first_round=all(x['rebuild_matches_first_round'] for x in results)),price_pairs=pair_stats,trades=results)
(P/'results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2));print(json.dumps(output['summary'],ensure_ascii=False));print(json.dumps(pair_stats,ensure_ascii=False));print(json.dumps([x for x in results if x['module']=='C'],ensure_ascii=False))
