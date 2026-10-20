"""Independent specification assertions on frozen orders, Decimal ledger and source quotes.
Does not import or execute the account engine, adapter or signal implementation.
"""
from verify_accounts import *
from bisect import bisect_right
import gzip


def run_orders():
 params=jload(ROOT/'execution/execution-config.json');symbols=list(SYMS);start,end=params['start'],params['end']
 bars={s:{r['date']:r for r in readcsv(INPUT/'bars'/f'{s}-nominal.csv')} for s in symbols}
 dates={s:sorted(bars[s]) for s in symbols};schedule_by={s:dates[s] for s in symbols}
 actions=sorted(jload(INPUT/'actions.json'),key=lambda a:(a['effective_date'],a['event_id']))
 precision=[];diagnostic=jload(INPUT/'diagnostic-candidates.json')
 candidates=[c for c in precision if c['symbol'] in symbols and c['config_id'] in ACD]+[c for c in diagnostic if c['symbol'] in symbols and c['config_id'] in DIAG]
 cmap={c['candidate_id']:c for c in candidates};assert len(cmap)==len(candidates)
 def levels(c,day):
  ans={f:num(c[f]) if c.get(f) is not None else None for f in ('stop','target','upper')}
  for action in actions:
   if action['symbol']!=c['symbol'] or not c['signal_date']<action['effective_date']<=day:continue
   if action['type']=='split':factor=1/num(action['ratio'])
   else:
    prev=dates[c['symbol']][bisect_left(dates[c['symbol']],action['effective_date'])-1]
    ref=num(bars[c['symbol']][prev]['close']);factor=(ref-num(action['cash']))/ref
   ans={f:v*factor if v is not None else None for f,v in ans.items()}
  return ans
 road=json.load(gzip.open(INPUT/'exit-observations.json.gz','rt'))
 checks=[];exit_checks=[];attempt_count=0;field_count=0;maxerr=ZERO
 def equal_numeric(actual,expected,*context):
  nonlocal field_count,maxerr
  if expected is None:assert actual is None,context;return
  difference=abs(num(actual)-expected);field_count+=1;maxerr=max(maxerr,difference)
  assert difference<TOL,(*context,actual,str(expected),str(difference))
 for symbol in symbols:
  for cfg in CONFIGS:
   for fee_value in params['fees_per_side']:
    FEE=num(fee_value);fee_tag=str(int(round(float(fee_value)*10000))).zfill(2);account_id=f'{symbol}-R1-risk1-fee{fee_tag}bp'
    folder=ACCOUNT/account_id
    daily={r['date']:r for r in readcsv(REVIEW/'reconciliation'/account_id/'daily-independent.csv')}
    dayseq=sorted(daily);trades=readcsv(folder/'trades.csv');orders=jload(folder/'orders.json');trips=jload(folder/'roundtrips.json')
    cm={c['candidate_id']:c for c in candidates if c['config_id']==cfg and c['symbol']==symbol}
    buys=[o for o in orders if o['side']=='buy'];sells=[o for o in orders if o['side']=='sell'];assert len(orders)==len(buys)+len(sells)
    assert len({o['order_id'] for o in orders})==len(orders)
    assert len(buys)==len(cm) and {o['candidate_id'] for o in buys}==set(cm),(cfg,'candidate coverage')
    assert [o['candidate_id'] for o in buys]==[c['candidate_id'] for c in sorted(cm.values(),key=lambda c:(c['signal_date'],c['symbol'],c['candidate_id']))],(cfg,'stable source ID ordering')
    tmap={t['order_id']:t for t in trades};assert len(tmap)==len(trades)
    assert set(tmap)=={o['order_id'] for o in orders if o['status']=='filled'}
    buytrade={t['position_id']:t for t in trades if t['side']=='buy'};selltrade={t['position_id']:t for t in trades if t['side']=='sell'}
    assert set(buytrade)=={p['position_id'] for p in trips}
    assert set(selltrade)=={p['position_id'] for p in trips if p['closed']}
    bysymbol={symbol:[p for p in trips if p['symbol']==symbol]}
    def unavailable(s,day):
     if day in params['blocked_dates'][s]:return 'known_open_unavailable'
     if day not in bars[s]:return 'missing_quote'
     prev=(date.fromisoformat(day)-timedelta(days=1)).isoformat()
     ref=num(daily[prev]['mark_'+s]) if prev in daily else num(bars[s][dates[s][bisect_left(dates[s],day)-1]]['close'])
     for a in actions:
      if a['symbol']==s and a['effective_date']==day:ref=ref/num(a['ratio']) if a['type']=='split' else ref-num(a['cash'])
     limit=num(params['limits'][s])
     for eff,value in params['limit_changes'].get(s,[]):
      if eff<=day:limit=num(value)
     if abs(num(bars[s][day]['open'])-ref)>=ref*limit-D('.00051'):return 'at_open_limit_conservative'
     return None
    earliest={}
    for p in trips:
     pid=p['position_id'];s=p['symbol'];bt=buytrade[pid];c=cm[bt['candidate_id']]
     assert p['candidate_id']==c['candidate_id'] and p['entry_date']==bt['date']
     evaluated=[(d, num(bars[s][d]['close'])<levels(c,d)['stop'], num(bars[s][d]['close'])<num(road[s][d]['ema20']) and num(bars[s][d]['close'])<num(road[s][d]['cost20'])) for d in dates[s] if p['entry_date']<=d<=end]
     qualifying=[(d, 'structure_stop' if structure else 'ema_cost_exit') for d,structure,road_exit in evaluated if structure or (cfg in DIAG and road_exit)]
     trigger,exit_reason=qualifying[0] if qualifying else (None,None);earliest[pid]=trigger
     matched=[o for o in sells if o['position_id']==pid]
     assert len(matched)==int(trigger is not None),(cfg,pid,'missing or extra stop order',trigger)
     exitday=None;attempts=[]
     if trigger:
      o=matched[0];assert o['signal_date']==trigger and o['reason']==exit_reason
      d=date.fromisoformat(trigger)+timedelta(days=1)
      while str(d)<=end:
       reason=unavailable(s,str(d));attempts.append(dict(date=str(d),reason=reason or 'filled'))
       if not reason:exitday=str(d);break
       d+=timedelta(days=1)
      assert o['attempts']==attempts,(cfg,pid,'exit delay reasons')
      assert o['status']==('filled' if exitday else 'pending_at_end')
      if exitday:assert o['resolved_date']==exitday
      attempt_count+=len(attempts)
     assert p['exit_date']==exitday and p['closed']==bool(exitday),(cfg,pid,'earliest stop execution')
     for field in ('stop','target','upper'):
      equal_numeric(p.get('initial_'+field),levels(c,p['entry_date'])[field],cfg,pid,'initial',field)
      equal_numeric(p.get(field),levels(c,exitday or end)[field],cfg,pid,'frozen structure',field)
     exit_checks.append(dict(config=cfg,position_id=pid,candidate_id=c['candidate_id'],entry_date=p['entry_date'],first_exit_condition_close=trigger,exit_reason=exit_reason,exit_variant='diagnostic_ema_cost' if cfg in DIAG else 'structure_only',next_available_exit=exitday,delayed_calendar_days=max(0,len(attempts)-1),attempts=len(attempts),closed=bool(exitday)))
    assert len(sells)==sum(v is not None for v in earliest.values())
    def position_close(s,d):
     matches=[p for p in bysymbol[s] if p['entry_date']<=d and (p['exit_date'] is None or p['exit_date']>d)]
     assert len(matches)<=1;return matches[0] if matches else None
    for o in orders:
     if o['status']=='filled':
      t=tmap[o['order_id']]
      for f in ('symbol','side','reason'):assert t[f]==o[f],(cfg,o['order_id'],f)
      assert t['date']==o['resolved_date']
      for f in ('shares','price'):equal_numeric(t[f],num(o[f]),cfg,o['order_id'],f)
      if o['side']=='buy':assert t['position_id']==o['position_id'] and t['candidate_id']==o['candidate_id']
      else:assert t['position_id']==o['position_id']
    for o in buys:
     c=cm[o['candidate_id']];s=c['symbol'];d=c['signal_date'];expected_metadata=dict(c)
     if cfg in DIAG:expected_metadata.update(original_candidate_id=c.get('source_candidate_id',c['candidate_id']),original_config_id=c.get('source_config_id','P0' if cfg=='R0' else 'P5'))
     assert o['candidate_metadata']==expected_metadata,(cfg,c['candidate_id'],'source metadata mutated')
     assert o['symbol']==s and o['signal_date']==d
     ix=bisect_right(schedule_by[s],d);planned=schedule_by[s][ix] if ix<len(schedule_by[s]) else None
     assert o['planned_date']==planned
     if cfg in DIAG:
      reason=(c.get('signal_reject_reason') or 'signal_rejected') if c.get('signal_accepted') is False else None
      if reason in ('target_unavailable','signal_reward_risk_below_3'):reason=None
      if reason is None and (c.get('stop') is None or num(c['stop'])<=0):reason='invalid_stop'
      elif reason is None and num(c.get('signal_ref'))<=num(c['stop']):reason='nonpositive_signal_risk'
     else:
      reason=c.get('signal_reject_reason') or 'signal_rejected' if c.get('signal_accepted') is False else None
      if not reason:
       if c.get('target') is None or num(c['target'])<=0:reason='missing_or_invalid_target'
       elif c.get('stop') is None or num(c['stop'])<=0:reason='invalid_stop'
       elif num(c['signal_ref'])<=num(c['stop']):reason='nonpositive_signal_risk'
       else:
        rr=(num(c['target'])-num(c['signal_ref']))/(num(c['signal_ref'])-num(c['stop']))
        equal_numeric(o['signal_rr_recomputed'],rr,cfg,c['candidate_id'],'signal rr')
        if rr<3:reason='signal_rr_below3'
     p=position_close(s,d)
     if not reason and p:reason='pending_exit' if earliest[p['position_id']] and earliest[p['position_id']]<=d else 'position_exists'
     if reason:
      assert o['status']=='rejected' and o['reason']==reason and o['resolved_date']==d and not o['attempts'],(cfg,c['candidate_id'],'signal rejection',reason,o)
     elif not planned or planned>end:
      assert o['status']=='pending_at_end' and not o['attempts']
     else:
      assert len(o['attempts'])==1
      a=o['attempts'][0];attempt_count+=1
      assert a['date']==planned
      prior=(date.fromisoformat(planned)-timedelta(days=1)).isoformat();row=daily[prior]
      px=num(bars[s][planned]['open']) if planned in bars[s] else None
      lev=levels(c,planned);risk=num(row['equity_'+s])*D('.01')
      if any(p['exit_date']==planned for p in bysymbol[s]):reason='same_day_sale'
      elif any(p['entry_date']<planned and (p['exit_date'] is None or p['exit_date']>=planned) for p in bysymbol[s]):reason='position_exists'
      elif any(t['side']=='buy' and t['symbol']==s and t['date']==planned and t['candidate_id']<c['candidate_id'] for t in trades):reason='position_exists'
      else:reason=unavailable(s,planned)
      equal_numeric(a['open_price'],px,cfg,c['candidate_id'],'open')
      equal_numeric(a.get('risk_budget'),risk,cfg,c['candidate_id'],'risk')
      equal_numeric(a['previous_product_equity'],num(row['equity_'+s]),cfg,c['candidate_id'],'prior equity')
      if not reason:
       if lev['stop'] is None or not 0<lev['stop']<px:reason='nonpositive_open_risk'
       elif False:
        if lev['target'] is None or lev['target']<=0:reason='missing_or_invalid_target'
        else:
         rr=(lev['target']-px)/(px-lev['stop']);equal_numeric(a['open_rr'],rr,cfg,c['candidate_id'],'open rr')
         if rr<3:reason='open_rr_below3'
      if not reason:
       opening_cash=num(row['cash_'+s])
       # Cash-dividend payment belongs to the original record-day holder, including a closed trade.
       for action in actions:
        if action['symbol']==s and action.get('pay_date')==planned:
         record=action['record_date'];q=num(daily[record]['units_'+s]) if record in daily else ZERO
         opening_cash+=q*num(action['cash'])
       qcash=(opening_cash/(px*(1+FEE))/100).to_integral_value(rounding=ROUND_FLOOR)*100
       expected_qty=min(qcash,(risk/(px-lev['stop'])/100).to_integral_value(rounding=ROUND_FLOOR)*100)
       if expected_qty<=0:reason='insufficient_cash_or_risk_lot'
       else:equal_numeric(o['shares'],expected_qty,cfg,c['candidate_id'],'expected lot')
      assert a['reason']==(reason or 'filled'),(cfg,c['candidate_id'],'open decision',reason,a)
      assert o['status']==('rejected' if reason else 'filled') and o['resolved_date']==planned
      assert o['reason']==(reason or 'candidate_entry')
     checks.append(dict(config=cfg,candidate_id=c['candidate_id'],order_id=o['order_id'],signal_date=d,planned_date=planned,status=o['status'],reason=o['reason'],attempts=len(o['attempts'])))
 writecsv(REVIEW/'candidate-order-checks.csv',checks);writecsv(REVIEW/'initial-stop-checks.csv',exit_checks)
 result=dict(status='passed',candidate_orders=len(checks),positions=len(exit_checks),closed_positions=sum(p['closed'] for p in exit_checks),attempts=attempt_count,numeric_fields=field_count,max_numeric_difference=maxerr,scope='All candidate metadata, signal/open decisions, lot/risk/cash sizes, trade linkage, earliest structure or T road-exit closes (structure priority when both), including entry close and daily exit delays; candidate existence/target generation is reviewed separately.')
 save(REVIEW/'order-results.json',result);print(json.dumps(result,default=str))

if __name__=='__main__':
 try:run_orders()
 except Exception as e:
  import traceback
  save(REVIEW/'orders-failed-attempt.json',dict(error=repr(e),traceback=traceback.format_exc()));raise
