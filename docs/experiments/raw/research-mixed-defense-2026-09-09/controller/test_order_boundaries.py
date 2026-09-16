from pathlib import Path
import importlib.util,pandas as pd,json,numpy as np
B=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('mixed_test',B/'execution/run.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def dec(day,selected=True):
 return dict(config='momentum_top3_sma200',decision_date=day,selected='X' if selected else '',ranked='X',lookback_start='test',lookback_end='test',scores='{}',weights=json.dumps({'X':1. if selected else 0.}),trend_states='test')
def run(days,opens,closes,decs,invalid=None):
 m.SYMS=['X'];m.START='2020-12-01';m.END='2026-06-30'
 p=pd.DataFrame([dict(date=d,symbol='X',open=(float('nan') if d==invalid else o),high=max(o,c)+1,low=min(o,c)-1,close=c,volume=100000) for d,o,c in zip(days,opens,closes)])
 z=pd.DataFrame([dict(date=d,symbol='X',economic_index=c,sma200=100.,momentum=.1) for d,c in zip(days,closes)])
 return m.simulate('fast_reentry_exit',.001,p,[],z,decs)
# A missing opening observation followed by an observed lower close must cancel;
# later recovery may use only the already received stop-sale budget.
days=['2021-01-04','2021-01-05','2021-01-06','2021-01-07','2021-01-08','2021-01-11','2021-01-12']
r=run(days,[100,98,100,99,100,102,103],[99,101,98,99,101,103,104],[dec('2020-12-31')],invalid='2021-01-06');tr=r[2];fast=[x for x in tr if x['reason']=='fast_reentry'];stop=[x for x in tr if x['reason']=='stop'];ev=r[8]
assert len(fast)==1 and fast[0]['date']=='2021-01-11'
assert any(x['event']=='reentry_queue_cancelled' and x['date']=='2021-01-06' for x in ev)
assert fast[0]['notional']+fast[0]['fee']<=stop[0]['notional']-stop[0]['fee']+1e-8
# Month-end recovery must not buy the old fund when the next executed monthly list excludes it.
days=['2021-01-04','2021-01-05','2021-01-29','2021-02-01','2021-02-02']
r2=run(days,[100,98,100,103,104],[99,99,101,104,105],[dec('2020-12-31'),dec('2021-01-29',False)])
assert not any(x['reason']=='fast_reentry' for x in r2[2])
assert any(x['event']=='monthly_cancel' for x in r2[8])
assert r2[1][-1]['units_X']==0
out={'passed':True,'cases':['blocked open then lower observed close cancels queued reentry; later recovery waits for next open','reentry gross cost stays within actual stop sale net proceeds','new monthly list clears old recovery queue and budget before open'], 'case1_trade_dates':[(x['date'],x['side'],x['reason']) for x in tr], 'case2_trade_dates':[(x['date'],x['side'],x['reason']) for x in r2[2]],'scope':'synthetic execution boundary checks, not additional strategy or return search'}
(B/'controller/order-boundary-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
