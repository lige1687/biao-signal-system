#!/usr/bin/env python3
"""Read-only bounded default-exit replay; protocol.md fixes scope before execution."""
from pathlib import Path
import sys, json, hashlib, socket
from dataclasses import asdict
from datetime import date

ROOT = Path('/Users/yongbiaoli/lei-signal-sync')
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'src'))
def no_network(*args, **kwargs):
    raise RuntimeError('Network prohibited in bounded reproduction')
socket.create_connection = no_network
socket.socket.connect = no_network

import pandas as pd
from lei_signal.domain import rules_config
from lei_signal.features.indicators import compute_features
from lei_signal.backtest.engine import EntrySpec, FeeModel, prepare_frame, simulate_trade, EXIT_COSTBASIS

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
inputs = {}
def record(path):
    inputs[str(path)] = {'sha256': digest(path), 'bytes': path.stat().st_size}

def independent(frame, spec, fee):
    """Reimplement documented close-confirmation / next-open mechanics, not engine calls."""
    ent = spec.signal_position + 1
    if ent >= len(frame): return {'exit_reason':'signal_at_end_not_entered'}
    ep = float(frame.open.iloc[ent]); previous = float(frame.close.iloc[ent-1])
    if ep >= previous * 1.095: return {'exit_reason':'skipped_limit_up_at_entry'}
    risk = ep-spec.stop_price
    if risk<=0: return {'exit_reason':'invalid_nonpositive_risk'}
    for day in range(ent,len(frame)):
        close=float(frame.close.iloc[day])
        reason='structure_stop_C' if close<spec.stop_price else ('exit_a6_1_costbasis' if close<float(frame.ema20.iloc[day]) and close<float(frame.close_lag20.iloc[day]) else None)
        if reason is None: continue
        ex=day+1
        while ex<len(frame) and float(frame.open.iloc[ex])<=float(frame.close.iloc[ex-1])*.905: ex+=1
        if ex==len(frame): return {'exit_reason':reason+'(数据末尾未执行)'}
        xp=float(frame.open.iloc[ex]); fee_fraction=2*max(fee.per_side_bps/10000,fee.per_share_usd/ep)
        return {'entry_date':frame.index[ent].date().isoformat(),'entry_price':ep,'exit_date':frame.index[ex].date().isoformat(),'exit_price':xp,'exit_reason':reason,'holding_bars':ex-ent,'r_net':((xp-ep)-fee_fraction*ep)/risk}
    return {'exit_reason':'open_at_end'}

sources = {'A':'T2_A_ETF_cm05_shrink.json','B':'T1_Bp_a61.json','C':'T2_C_stocks_v3_b15.json'}
for path in [ROOT/'configs/rules.v1.yaml',ROOT/'configs/rules.v2.yaml',ROOT/'src/lei_signal/domain/rules_config.py',ROOT/'src/lei_signal/backtest/engine.py',ROOT/'src/lei_signal/features/indicators.py',OUT/'protocol.md',Path(__file__)]: record(path)
fee=FeeModel.from_ledger('standard')
result={'scope':'default exits on frozen historical opportunities, not regeneration of entries or portfolio backtest','source_root':str(ROOT),'ledger_path':str(rules_config._default_config_path()),'ledger_version':rules_config.ruleset_version(),'fee_model':asdict(fee),'selection':'lexicographically first symbol in each reference, all its opportunities','cutoff':'2026-08-25','data_checks':{},'trades':[]}
for module, filename in sources.items():
    rp=ROOT/'docs/experiments/raw/lifecycle_combo'/filename; record(rp)
    rows=json.loads(rp.read_text())['trades']; symbol=sorted({r['symbol'] for r in rows})[0]
    rows=[r for r in rows if r['symbol']==symbol]
    pp=ROOT/'docs/experiments/raw/exit_three_piece/pool'/f'{symbol}.bars.parquet'; record(pp)
    meta=pp.with_suffix('').with_suffix('.meta.json')
    actual_meta=pp.with_name(pp.name.replace('.parquet','.meta.json'))
    if actual_meta.exists(): record(actual_meta)
    bars=pd.read_parquet(pp); bars=bars.loc[:'2026-08-25']
    check={'rows':len(bars),'start':str(bars.index.min()),'end':str(bars.index.max()),'monotonic':bars.index.is_monotonic_increasing,'duplicate_dates':int(bars.index.duplicated().sum()),'missing_ohlcv':int(bars[['open','high','low','close','volume']].isna().sum().sum()),'nonpositive_ohlc':int((bars[['open','high','low','close']]<=0).sum().sum()),'high_below_low':int((bars.high<bars.low).sum()),'reference_opportunities':len(rows)}
    result['data_checks'][symbol]=check
    frame=compute_features(bars); prepared=prepare_frame(frame)
    for old in rows:
        key=f"{module}:{symbol}:{old['signal_date']}"
        timestamp=pd.Timestamp(old['signal_date'])
        if timestamp not in frame.index:
            result['trades'].append({'key':key,'error':'signal date missing','old':old});continue
        position=int(frame.index.get_loc(timestamp))
        spec=EntrySpec(symbol=symbol,signal_date=date.fromisoformat(old['signal_date']),signal_position=position,entry_ref_price=float(frame.close.iloc[position]),stop_price=float(old['stop_price']),target_price=old['target_price'],target_source='historical_reference',reward_risk=old['reward_risk'],entry_variant=old['entry_variant'],is_first_touch=old['is_first_touch'],ma_period=old['ma_period'],clock_type=0,weekly_bull_env=False,event_id=key)
        trade=simulate_trade(frame,spec,exit_variant=EXIT_COSTBASIS,fee=fee,prepared=prepared,limit_guard=True)
        current=json.loads(json.dumps(asdict(trade),default=str)); manual=independent(frame,spec,fee)
        manual_diffs={}
        for field,value in manual.items():
            observed=current.get(field)
            equal=abs(value-observed)<=1e-9 if isinstance(value,(int,float)) and observed is not None else value==observed
            if not equal: manual_diffs[field]={'engine':observed,'independent':value}
        historical_diffs={}
        for field in ('entry_date','entry_price','exit_date','exit_price','exit_reason','holding_bars','r_net'):
            a,b=old.get(field),current.get(field)
            equal=abs(a-b)<=1e-9 if isinstance(a,(int,float)) and isinstance(b,(int,float)) else a==b
            if not equal: historical_diffs[field]={'old':a,'current':b}
        result['trades'].append({'key':key,'module':module,'old':old,'current':current,'independent':manual,'independent_differences':manual_diffs,'historical_differences':historical_diffs,'entry_price_change_fraction':current['entry_price']/old['entry_price']-1,'effective_one_side_cost_bps':fee.round_trip_fraction(current['entry_price'])*5000})
valid=[x for x in result['trades'] if 'error' not in x]
result['summary']={'opportunities':len(result['trades']),'mapped':len(valid),'independent_mismatch_trades':sum(bool(x['independent_differences']) for x in valid),'historical_mismatch_trades':sum(bool(x['historical_differences']) for x in valid),'by_module':{m:{'n':sum(x['module']==m for x in valid),'historical_mismatches':sum(x['module']==m and bool(x['historical_differences']) for x in valid),'old_closed_mean_r':pd.Series([x['old']['r_net'] for x in valid if x['module']==m],dtype=float).mean(),'current_closed_mean_r':pd.Series([x['current']['r_net'] for x in valid if x['module']==m],dtype=float).mean()} for m in sources}}
result['summary']['all_input_hashes_unchanged']=all(digest(Path(p))==v['sha256'] for p,v in inputs.items())
result['inputs']=inputs
(OUT/'reproduction_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps(result['summary'],ensure_ascii=False,indent=2,default=str))
