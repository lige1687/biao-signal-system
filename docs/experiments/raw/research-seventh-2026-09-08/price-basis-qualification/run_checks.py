"""Fixed G3 positive and intentionally broken-price counterexamples; stdlib only."""
import csv, json, hashlib
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal as D
from price_basis import PriceBasis, QualificationError, MODES, FIELDS
BASE = Path(__file__).resolve().parent

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, data): (BASE/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str)+'\n')
def equal(a,b): assert abs(D(a)-D(b)) <= D('1e-30'), (a,b)

lock = json.loads((BASE/'input-lock.json').read_text())
assert digest(BASE/'protocol.md') == lock['protocol_sha256']
for item in lock['files']: assert digest(BASE/item['file']) == item['sha256'], item
code_lock = json.loads((BASE/'code-lock.json').read_text())
for name, h in code_lock['sha256'].items(): assert digest(BASE/name) == h
bars = {p.name.split('-')[0]: list(csv.DictReader(p.open())) for p in (BASE/'inputs/prices').glob('*.csv')}
actions = json.loads((BASE/'inputs/actions.json').read_text())
engine = PriceBasis(bars, actions)
checks=[]; failures=[]
def check(name, fn):
    try:
        detail=fn(); checks.append({'name':name,'status':'passed','detail':detail})
    except Exception as e:
        failures.append({'name':name,'error':repr(e)})

def rejected(fn):
    try: fn()
    except QualificationError as e: return str(e)
    raise AssertionError('invalid case was accepted')

def quote(symbol, day): return next(b for b in bars[symbol] if b['date']==day)
def fixture(symbol='X', day='2020-01-01', close='10'):
    return dict(date=day,open=close,high=close,low=close,close=close,volume='100')
def event(kind, eff, amount, known='2020-01-01', symbol='X', suffix=''):
    return dict(symbol=symbol,type=kind,event_id=kind+eff+suffix,effective_date=eff,announcement_date=known,currency='CNY',**({'cash':amount} if kind=='cash_dividend' else {'ratio':amount}))

def all_rows():
    result={}; max_error=D(0)
    for s, rows in sorted(bars.items()):
        counts={}
        for mode in MODES:
            for row in rows:
                transformed=engine.bar(s,row,rows[-1]['date'],mode)
                t=engine.mapping(s,row['date'],rows[-1]['date'],mode)
                for field in FIELDS:
                    error=abs(t.inverse_to_original_date(transformed[field])-D(row[field]))
                    max_error=max(max_error,error); assert error<=D('1e-30')
                if row['date']==rows[-1]['date']:
                    for f in FIELDS: equal(transformed[f],D(row[f]))
            counts[mode]=len(rows)
        result[s]={'date_min':rows[0]['date'],'date_max':rows[-1]['date'],'rows_checked_each_mode':counts}
    return dict(instruments=result,max_roundtrip_absolute_error=max_error)
check('all_frozen_rows_finite_positive_ordered_and_roundtrip',all_rows)

def dividend_case():
    symbol='sh510300'; prev=quote(symbol,'2014-01-20'); ex=quote(symbol,'2014-01-21'); d=D('.048'); results={}
    for mode in MODES:
        pre=engine.bar(symbol,prev,'2014-01-20',mode)
        post=engine.bar(symbol,prev,'2014-01-21',mode)
        equal(pre['close'],D(prev['close'])); equal(post['close'],D(prev['close'])-d)
        equal(post['volume'],D(prev['volume']))
        level=dict(symbol=symbol,value=D(prev['close']),basis_as_of='2014-01-20',source_date='2014-01-20',confirmed_at='2014-01-20')
        moved=engine.rebase_level(level,'2014-01-21',mode,'open')
        equal(moved['value'],post['close']); assert level['basis_as_of']=='2014-01-20'
        results[mode]={'previous_bar_converted':post,'line_at_ex_open':moved['value']}
    nominal_return=D(ex['close'])/D(prev['close'])-1
    wealth_return=(D(ex['close'])+d)/D(prev['close'])-1
    tech_return=D(ex['close'])/(D(prev['close'])-d)-1
    assert abs(wealth_return-tech_return)>D('1e-9')
    assert abs((tech_return+d/D(prev['close']))-wealth_return)>D('1e-9')
    return dict(previous_nominal=prev,ex_nominal=ex,dividend_per_share=d,methods=results,
        one_share_cash_receivable_wealth_change=wealth_return,technical_close_change=tech_return,
        nominal_price_only_change=nominal_return,incorrect_technical_plus_dividend_change=tech_return+d/D(prev['close']),
        meaning='Single event arithmetic only; receivable is not spendable until pay date; no strategy return. Converter emits no money or account credit.')
check('real_2014_dividend_and_no_double_count_arithmetic',dividend_case)

def split_case():
    s='sh513100'; prev=quote(s,'2022-01-12'); resumed=quote(s,'2022-01-14')
    assert not any(b['date']=='2022-01-13' for b in bars[s])
    output={}
    for mode in MODES:
        t=engine.mapping(s,prev['date'],'2022-01-13',mode,'open')
        equal(t.a,D('.2')); assert len(t.event_ids)==1
        adjusted=engine.bar(s,prev,'2022-01-13',mode,'open')
        for f in FIELDS: equal(adjusted[f],D(prev[f])/5)
        equal(adjusted['volume'],D(prev['volume'])*5)
        line=dict(symbol=s,value=D('5.4'),basis_as_of='2022-01-12',confirmed_at='2022-01-12',source_date='2022-01-10')
        moved=engine.rebase_level(line,'2022-01-13',mode,'open'); equal(moved['value'],D('1.08'))
        equal(D(prev['close'])*100,adjusted['close']*500)
        output[mode]=dict(adjusted_previous_bar=adjusted,line_nominal_basis=moved['value'],event_ids=t.event_ids)
    return dict(previous_quote=prev,event_day='2022-01-13',event_day_quote_present=False,
        synthetic_tradeable_OHLC_inserted=False,first_resumed_quote=resumed,methods=output,
        zero_new_cash='100 old units become 500 units; stale last quote divides by 5; total marked value unchanged')
check('real_2022_split_effective_without_event_day_quote',split_case)

def prefix():
    comparisons=0; rows_compared=0
    for s, rows in bars.items():
        boundaries={rows[0]['date'], rows[-1]['date']}
        for a in actions:
            if a['symbol']==s:
                for field in ('announcement_date','effective_date'):
                    when=date.fromisoformat(a[field]); boundaries.update(str(when+timedelta(days=i)) for i in (-1,0,1))
        for asof in sorted(boundaries):
            prefix_bars={s:[b for b in rows if b['date']<=asof]}
            for phase in ('open','close'):
                prefix_actions=[a for a in actions if a['effective_date']<=asof and (a['announcement_date']<asof if phase=='open' else a['announcement_date']<=asof)]
                cut=PriceBasis(prefix_bars,prefix_actions)
                for mode in MODES:
                    for row in prefix_bars[s]:
                        if phase == 'open' and row['date'] == asof:
                            continue
                        assert engine.bar(s,row,asof,mode,phase)==cut.bar(s,row,asof,mode,phase)
                        rows_compared+=1
                    comparisons+=1
    return dict(asof_symbol_phase_mode_cases=comparisons,bar_comparisons=rows_compared)
check('full_input_equals_each_date_prefix_at_action_boundaries',prefix)

def future():
    prev=quote('sh510300','2014-01-20'); asof=prev['date']
    poisoned=actions+[
        event('cash_dividend','2099-01-01','9999',known='2014-01-01',symbol='sh510300'),
        event('cash_dividend','2014-01-19','9999',known='2099-01-01',symbol='sh510300',suffix='late')]
    alternate={s:[dict(b,close='9999',open='9999',low='9999',high='9999') if b['date']>asof else b for b in rows] for s,rows in bars.items()}
    poisoned_engine=PriceBasis(alternate,poisoned)
    for mode in MODES:
        for row in bars['sh510300']:
            if row['date']<=asof: assert engine.bar('sh510300',row,asof,mode)==poisoned_engine.bar('sh510300',row,asof,mode)
    return 'Future prices, announced-but-not-effective actions, and not-yet-announced actions do not change the saved as-of output.'
check('future_prices_and_future_events_do_not_leak',future)

def timing():
    e=PriceBasis({'X':[fixture()]},[event('cash_dividend','2020-01-02','1',known='2020-01-02')])
    equal(e.mapping('X','2020-01-01','2020-01-02',MODES[0],'open').forward(10),D(10))
    equal(e.mapping('X','2020-01-01','2020-01-02',MODES[0],'close').forward(10),D(9))
    line=dict(symbol='X',value=10,basis_as_of='2020-01-02',source_date='2020-01-01',confirmed_at='2020-01-02')
    messages=[rejected(lambda:e.rebase_level(line,'2020-01-01',MODES[0])),rejected(lambda:e.rebase_level(line,'2020-01-02',MODES[0],'open'))]
    equal(e.rebase_level(line,'2020-01-02',MODES[0],'close')['value'],D(10))
    return dict(rejections=messages,meaning='Date-only announcements/structure confirmation on the same date are available after close, not at open.')
check('announcement_phase_and_structure_confirmation_boundaries',timing)

def composition():
    bs={'X':[fixture(),fixture(day='2020-01-03',close='1.8')]}
    es=[event('cash_dividend','2020-01-02','1'),event('split','2020-01-03','5'),event('cash_dividend','2020-01-04','.1')]
    e=PriceBasis(bs,es); answer={}
    for mode in MODES:
        t=e.mapping('X','2020-01-01','2020-01-04',mode)
        equal(t.forward(10),D('1.7')); equal(t.volume_multiplier,5)
        earlier=e.mapping('X','2020-01-01','2020-01-02',mode)
        later=e.mapping('X','2020-01-02','2020-01-04',mode)
        for x in ('9','10','11'): equal(t.forward(x),later.forward(earlier.forward(x)))
        answer[mode]=dict(a=t.a,b=t.b,price10=t.forward(10))
    return answer
check('cash_then_split_then_cash_and_level_composition',composition)

def deliberate_errors():
    prev=quote('sh510300','2014-01-20'); bad={}
    for mode in MODES:
        at_signal=engine.bar('sh510300',prev,'2014-01-20',mode)['close']
        at_terminal=engine.bar('sh510300',prev,'2026-09-07',mode)['close']
        assert at_signal!=at_terminal
        t=engine.mapping('sh510300','2014-01-20','2014-01-21',mode)
        current=t.forward(prev['close']); old=t.inverse_to_original_date(current)
        equal(old-current,D('.048'))
        bad[mode]=dict(saved_signal_price=at_signal,wrong_terminal_adjusted_signal=at_terminal,
            proper_ex_day_level=current,wrong_old_nominal_execution_level=old)
    return bad
check('negative_controls_detect_terminal_leak_and_wrong_inverse_execution',deliberate_errors)

def rejected_data():
    bs={'X':[fixture()]}; e1=event('cash_dividend','2020-01-02','1')
    cases={
      'duplicate_economic_event_different_id':lambda:PriceBasis(bs,[e1,dict(e1,event_id='another')]).mapping('X','2020-01-01','2020-01-03',MODES[0]),
      'conflicting_same_economic_event_amount':lambda:PriceBasis(bs,[e1,dict(e1,event_id='another',cash='2')]).mapping('X','2020-01-01','2020-01-03',MODES[0]),
      'missing_proportional_reference':lambda:PriceBasis({},[e1]).mapping('X','2020-01-01','2020-01-03',MODES[1]),
      'reference_not_above_dividend':lambda:PriceBasis(bs,[dict(e1,cash='10')]).mapping('X','2020-01-01','2020-01-03',MODES[1]),
      'nonpositive_additive_price':lambda:PriceBasis(bs,[dict(e1,cash='11')]).bar('X',fixture(),'2020-01-03',MODES[0]),
      'same_day_cash_and_split_unknown_order':lambda:PriceBasis(bs,[e1,event('split','2020-01-02','5')]).mapping('X','2020-01-01','2020-01-03',MODES[0]),
      'future_price_observation':lambda:engine.mapping('sh510300','2014-01-21','2014-01-20',MODES[0])}
    return {k:rejected(v) for k,v in cases.items()}
check('invalid_inputs_stop_instead_of_guessing',rejected_data)

def additional_time_and_reference_guards():
    bs={'X':[fixture()]}
    events=[event('split','2020-01-02','5'),event('cash_dividend','2020-01-03','1')]
    e=PriceBasis(bs,events)
    stale=rejected(lambda:e.mapping('X','2020-01-01','2020-01-03',MODES[1]))
    opening=rejected(lambda:e.bar('X',fixture(),'2020-01-01',MODES[0],'open'))
    after_close=e.bar('X',fixture(),'2020-01-01',MODES[0],'close')
    equal(after_close['close'],D(10))
    return dict(stale_reference_rejection=stale,same_day_full_bar_open_rejection=opening,
       note='Two omissions independently reproduced in first-pass/review-counterexamples.json; first-pass code, lock and result preserved. No change to dividend formulas.')
check('review_counterexamples_stale_reference_and_open_bar_are_rejected',additional_time_and_reference_guards)


def semantic_differences():
    s='sh510300'; rows=[b for b in bars[s] if b['date']<='2014-01-21'][-20:]; out={}
    for mode in MODES:
        adjusted=[engine.bar(s,b,'2014-01-21',mode) for b in rows]
        sma=sum(x['close'] for x in adjusted)/len(adjusted)
        previous=engine.bar(s,quote(s,'2014-01-20'),'2014-01-21',mode)
        out[mode]={'sma20_on_ex_date':sma,'close_to_sma20_fraction':D(rows[-1]['close'])/sma-1,
           'previous_day_high_low_width_over_low':(previous['high']-previous['low'])/previous['low'],
           'historical_reference_2_50_at_2014_01_17':engine.mapping(s,'2014-01-17','2014-01-21',mode).forward('2.50')}
    assert out[MODES[0]]['sma20_on_ex_date']!=out[MODES[1]]['sma20_on_ex_date']
    a_width=(D('10.2')-1-(D('10')-1))/(D('10')-1)
    p_width=(D('10.2')*D('.9')-D('10')*D('.9'))/(D('10')*D('.9'))
    assert a_width>D('.02') and p_width<=D('.02')
    return dict(real_2014_fixed_indicator_example=out,
       synthetic_percent_threshold_example=dict(original_low=10,original_high='10.2',dividend=1,
           additive_width=a_width,proportional_width=p_width,fixed_threshold='.02',additive_pass=False,proportional_pass=True),
       interpretation='This is a fixed arithmetic threshold illustration, not a B-module signal count or rule amendment. Under positive affine transforms, order and same-basis reward/risk ratios stay unchanged; percentages and percentage stops can change.')
check('additive_vs_proportional_have_material_percentage_semantics',semantic_differences)

save('results.json',dict(created_at_utc=datetime.now(timezone.utc).isoformat(),input_lock_sha256=digest(BASE/'input-lock.json'),code_lock_sha256=digest(BASE/'code-lock.json'),
    scope='price conversion only; no candidate signals, trades, strategy returns or account simulation',checks=checks,failures=failures,
    passed_groups=len(checks),failed_groups=len(failures),formal_G3_status='mathematics-qualified-for-tested-proxies; strategy dividend convention and complete action coverage remain unresolved'))
print(json.dumps({'passed_groups':len(checks),'failed_groups':len(failures),'failures':failures},ensure_ascii=False))
if failures: raise SystemExit(1)
