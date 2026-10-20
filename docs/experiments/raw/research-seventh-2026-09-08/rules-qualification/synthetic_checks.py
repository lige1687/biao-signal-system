"""Bounded G1 probes; imports frozen pure functions only; no real asset signals/returns."""
import ast, dataclasses, hashlib, json, sys, traceback
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'snapshot/src'))
import pandas as pd
import yaml
from lei_signal.features.indicators import compute_features
from lei_signal.rules import dense_breakout as db
from lei_signal.rules import tradability_gate as tg
from lei_signal.domain.rules_config import get_rule, load_ruleset, _default_config_path
from lei_signal.domain.types import Pivot
from lei_signal.backtest.engine import EntrySpec, FeeModel, entry_specs_from_events, simulate_trade, EXIT_B3_DUAL, EXIT_STRUCTURE_STOP
from lei_signal.rules.reward_risk_filter import compute_reward_risk
OUT=ROOT/'attempt-01'; OUT.mkdir(exist_ok=False)
def dump(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'input-manifest.json').read_text())
dump('before.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'protocol_sha256':sha(ROOT/'protocol.md'),'snapshot_all_match':all(sha(ROOT/x['copy'])==x['sha256'] for x in manifest['files'])})
results=[]
def probe(n,label,kind,fn):
    try:
        passed,detail=fn()
        results.append({'id':n,'label':label,'input_kind':kind,'status':'pass' if passed else 'finding','detail':detail})
    except Exception:
        results.append({'id':n,'label':label,'input_kind':kind,'status':'fixture_error','traceback':traceback.format_exc()})
    dump('results.json',results)
def bars(n=306,price=100.):
    ix=pd.bdate_range('2020-01-01',periods=n)
    return pd.DataFrame({'open':price,'high':price*1.01,'low':price*.99,'close':price,'volume':1000.},index=ix)
def breakout_frame():
    b=bars(); b.loc[b.index[300]:,['open','high','low','close']]=[102.,103.,101.,102.]
    return compute_features(b)
def brief(events):
    return [{'date':str(x.available_date),'sub':x.evidence.get('sub_rule'),'variant':x.evidence.get('variant'),'reference':x.evidence.get('breakout_reference',x.evidence.get('reference_price')),'stop':x.evidence.get('stop_price')} for x in events]
def confirmed(events):return [e for e in events if e.evidence.get('sub_rule')==db.SUB_RULE_CONFIRMED and e.evidence.get('variant')=='breakout']
def ev(f,pos=300,stop=9.,price=10.):
    return db._make_event(spec=get_rule('dense_breakout'),symbol='SYNTH.SZ',day=f.index[pos].date(),lifecycle_id='synthetic-test',sub_rule=db.SUB_RULE_CONFIRMED,variant='breakout',reference=9.8,close=price,zone_low=stop,stop_price=stop)
def pivot(f,target,confirmed_pos=295):return Pivot(kind='high',index=290,pivot_date=f.index[290].date(),price=target,confirmed_index=confirmed_pos,available_date=f.index[confirmed_pos].date())
def spec(f,variant='breakout',stop=9.,ref=10.,target=14.):
    return EntrySpec(symbol='SYNTH.SZ',signal_date=f.index[300].date(),signal_position=300,entry_ref_price=10.,stop_price=stop,target_price=target,target_source='synthetic-fixed',reward_risk=4.,entry_variant=variant,is_first_touch=False,ma_period=0,clock_type=3,weekly_bull_env=False,event_id='synthetic-direct-spec',breakout_reference=ref)
def simulate(f,s,exit_variant=EXIT_B3_DUAL):
    return simulate_trade(f,s,exit_variant=exit_variant,fee=FeeModel('none',0.,0.),prepared={'costbasis_cond':pd.Series(False,index=f.index),'top_dates':[]},limit_guard=True)
def trade_detail(t):return {k:str(getattr(t,k)) if k.endswith('date') else getattr(t,k) for k in ['entry_date','entry_price','exit_date','exit_reason','reward_risk','stop_price','target_price']}
def exitframe():
    f=compute_features(bars(price=10.)); f['sma20']=10.2;f['sma60']=10.;f['close_lag20']=9.5
    return f
f=breakout_frame();f.to_csv(OUT/'synthetic-full-features.csv',index_label='date')
base_events=db.detect_dense_breakout_events(f,'SYNTH.SZ');dump('synthetic-full-events.json',brief(base_events))

def p01():
    a=yaml.safe_load((ROOT/'snapshot/configs/rules.v1.yaml').read_text());b=load_ruleset()
    rules=['dense_breakout','tradability_gate','reward_risk_filter']
    detail={'effective_config':str(_default_config_path().relative_to(ROOT)),'effective_ruleset_version':b.get('ruleset_version'),'v1_ruleset_version':a.get('ruleset_version'),'dense_runtime_params':db._params(get_rule('dense_breakout')),'rules_v1':{k:a['rules'].get(k) for k in rules},'rules_v2':{k:b['rules'].get(k) for k in rules}}
    dump('effective-config.json',detail)
    return _default_config_path()==ROOT/'snapshot/configs/rules.v2.yaml' and db._params(get_rule('dense_breakout'))==(.02,126,20),detail
probe('S01','有效配置为冻结v2；126根、2%和20根解除参数','配置原文与实际加载',p01)
def p02():
    c=confirmed(base_events); return len(c)==1 and c[0].available_date==f.index[300].date() and c[0].evidence['breakout_reference']==101. and c[0].evidence['stop_price']==99.,brief(base_events)
probe('S02','完整OHLC计算特征后产生突破，参考只到昨日','完整OHLC→特征→B事件',p02)
probe('S03','追加未来行情不改变既有B事件','完整OHLC→特征→B事件',lambda:(brief(db.detect_dense_breakout_events(f.iloc[:301],'SYNTH.SZ'))==brief([e for e in base_events if e.available_date<=f.index[300].date()]),{'prefix':brief(db.detect_dense_breakout_events(f.iloc[:301],'SYNTH.SZ'))}))
probe('S04','同一密集区持续站上上沿不重复突破','完整OHLC→特征→B事件',lambda:(len(confirmed(base_events))==1,{'breakout_count':len(confirmed(base_events)),'tail_bars_above_reference':6}))
probe('S05','缺关键字段时不发B事件','完整特征删除字段',lambda:(db.detect_dense_breakout_events(f.drop(columns='sma120'),'SYNTH.SZ')==[],{'removed':'sma120','events':brief(db.detect_dense_breakout_events(f.drop(columns='sma120'),'SYNTH.SZ'))}))
def p06():
    z=f.copy();z.loc[z.index[300],list(db._LINE_COLUMNS)]=[100.,100.1,100.2,100.,100.1,100.2]
    c=confirmed(db.detect_dense_breakout_events(z,'SYNTH.SZ'));return len(c)==1 and not db._dual_alignment(z.iloc[300]),{'alignment':db._dual_alignment(z.iloc[300]),'events':brief(c),'manual_indicators':z.iloc[300][list(db._LINE_COLUMNS)].to_dict()}
probe('S06','突破版不强制多头排列','直接控制六线的组件隔离',p06)
def p07():
    z=exitframe(); z.loc[z.index[301]:,'close']=9.8;z.loc[z.index[302]:,'close_lag20']=10.
    t=simulate(z,spec(z));return t.exit_date==z.index[303].date() and t.exit_reason=='exit_b3_dual',{'only_fallback_at':str(z.index[301].date()),'both_actions_at':str(z.index[302].date()),'actual':trade_detail(t)}
probe('S07','B3只有跌回不退出，双动作满足后下一根开盘','直接控制指标与持仓规则',p07)
def p08():
    z=exitframe();z.loc[z.index[301]:,'close']=8.8;z.loc[z.index[301]:,'close_lag20']=10.
    t=simulate(z,spec(z));return t.exit_reason=='structure_stop_C' and t.exit_date==z.index[302].date(),trade_detail(t)
probe('S08','结构失效与B3同时出现时结构失效优先','直接控制指标与持仓规则',p08)
def p09():
    z=f.copy();z.loc[z.index[301]:,'sma20']=100.;z.loc[z.index[301]:,'sma60']=100.1
    e=confirmed(db.detect_dense_breakout_events(z,'SYNTH.SZ'))[0]
    s=dataclasses.replace(spec(z,stop=99.,ref=101.,target=120.),entry_ref_price=102.)
    t=simulate(z,s);failed=[e for e in db.detect_dense_breakout_events(z,'SYNTH.SZ') if e.evidence.get('sub_rule')==db.SUB_RULE_FAILED]
    return t.exit_date is None,{'required':'突破版仅排列破坏且未跌回上沿时不触发B3退出','close':102.,'reference':101.,'sma20':100.,'sma60':100.1,'detector_failed_events':brief(failed),'actual_engine':trade_detail(t),'consequence':'事件层与逐笔退出层不一致'}
probe('S09','突破版不能套用埋伏的单独排列退出','实际B事件后直接控制两条均线',p09)
def p10():
    z=exitframe();z['sma20']=9.9;z['sma60']=10.;z['close']=10.1
    t=simulate(z,spec(z,variant='ambush'));return t.exit_reason=='exit_b3_dual' and t.exit_date==z.index[302].date(),trade_detail(t)
probe('S10','埋伏版排列破坏下一根退出','直接控制指标与持仓规则',p10)
def p11():
    z=compute_features(bars(price=10.));z.loc[z.index[301],'open']=10.9
    accepted,*_=entry_specs_from_events(z,[ev(z)],'SYNTH.SZ',module='B',entry_variant='breakout',rr_min=3.,pivots=(pivot(z,14.),))
    t=simulate(z,accepted[0],EXIT_STRUCTURE_STOP);actual=(t.target_price-t.entry_price)/(t.entry_price-t.stop_price)
    return t.exit_reason=='skipped_actual_reward_risk_below_3',{'required':'若称实际入场风险比不少于3，跳空后应取消该次入场','signal_rr':accepted[0].reward_risk,'actual_open_rr':actual,'actual':trade_detail(t)}
probe('S11','开盘跳空后的实际目标风险比仍须不少于3','实际目标筛选→直接控制下一根开盘',p11)
def p12():
    z=compute_features(bars(price=10.));out=[]
    for target in [13.,12.99]:
        a,b,c=entry_specs_from_events(z,[ev(z)],'SYNTH.SZ',module='B',entry_variant='breakout',rr_min=3.,pivots=(pivot(z,target),));out.append({'target':target,'accepted':len(a),'below_rr':b,'no_target':c})
    return out[0]['accepted']==1 and out[1]['accepted']==0 and out[1]['below_rr']==1,out
probe('S12','信号收盘风险比恰为3通过，低于3过滤','直接事件→实际目标与入场筛选',p12)
def p13():
    z=compute_features(bars(price=10.));z[['open','high','low','close']]=10.
    out=[]
    for threshold in [3.,None]:
        a,b,c=entry_specs_from_events(z,[ev(z)],'SYNTH.SZ',module='B',entry_variant='breakout',rr_min=threshold);out.append({'rr_min':threshold,'accepted':len(a),'no_target':c,'target':a[0].target_price if a else None})
    return out[0]['accepted']==0 and out[1]['accepted']==1 and out[1]['target'] is None,{'behavior_confirmed':out,'scope_limit':'rr_min=None是有意取消目标限制的对照，不能称完整纪律'}
probe('S13','无目标在默认3被拒绝，None对照允许入场','直接事件→实际目标与入场筛选',p13)
def p14():
    z=compute_features(bars(price=10.));old=pivot(z,14.);future=pivot(z,19.,304)
    r1=compute_reward_risk(z.iloc[:301],ev(z),(old,));r2=compute_reward_risk(z,ev(z),(old,future))
    z.loc[z.index[301]:,['open','high','low','close']]=1000.;r3=compute_reward_risk(z,ev(z),(old,future))
    return r1.target_b==r2.target_b==r3.target_b==14.,{'prefix_target':r1.target_b,'full_with_unconfirmed_pivot':r2.target_b,'future_extreme_prices':r3.target_b,'future_confirmation':str(future.available_date)}
probe('S14','未来才确认的高点与未来极端行情不改变旧目标','实际目标计算；提供带确认日期的摆动点',p14)
def p15():
    z=compute_features(bars(price=10.));z['signal_color']=['green' if i%2 else 'black' for i in range(len(z))]
    r=tg.evaluate_tradability(z,300);checks={x.code:x for x in r.condition_checks};placeholders=[tg.C_MODULE_UNCLEAR,tg.C_ENTRY_UNDEFINED,tg.C_RR_BELOW_3,tg.C_DEPENDS_ON_FUTURE]
    return all(not checks[x].blocked for x in placeholders) and checks[tg.C_MULTI_PERIOD_MESSY].blocked,{'checks':[dataclasses.asdict(x) for x in r.condition_checks],'placeholder_codes':placeholders,'weekly_input_supplied':False,'scope_limit':'只确认占位与单日线代理存在，不代表九条完整实现'}
probe('S15','九条展示中的四项占位、多周期实为日线颜色变化','直接控制日线颜色→实际展示评估',p15)
def p16():
    paths=['backtest/service.py','backtest/engine.py','backtest/runner.py'];calls={}
    for rel in paths:
        tree=ast.parse((ROOT/'snapshot/src/lei_signal'/rel).read_text());calls[rel]=sorted({n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))})
    present={p:'evaluate_tradability' in names for p,names in calls.items()}
    return not any(present.values()),{'main_path_evaluate_tradability_calls':present,'display_path':'api/routes/symbols.py::_tradability_dto','scope_limit':'函数缺席由静态调用核对；不等于所有单项都未做，2/3/4部分由事件与目标筛选覆盖'}
probe('S16','逐笔研究主路径没有执行九条展示评估','冻结源码AST静态调用核对',p16)
assert len(results)==16
snapshot_bad=[x['copy'] for x in manifest['files'] if sha(ROOT/x['copy'])!=x['sha256']]
source_bad=[x['source'] for x in manifest['files'] if not Path(x['source']).exists() or sha(Path(x['source']))!=x['sha256']]
dump('after.json',{'completed_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'snapshot_mismatches':snapshot_bad,'source_mismatches':source_bad,'status_counts':{s:sum(r['status']==s for r in results) for s in ['pass','finding','fixture_error']},'historical_strategy_runs':0,'production_writes':0})
print(json.dumps({'output':str(OUT),'status_counts':{s:sum(r['status']==s for r in results) for s in ['pass','finding','fixture_error']}},ensure_ascii=False))
