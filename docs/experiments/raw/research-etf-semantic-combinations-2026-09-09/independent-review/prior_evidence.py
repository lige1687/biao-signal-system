"""Strictly prior evidence tables from independently checked fixed opportunities."""
from decimal import Decimal as D

def _stats(rows,value_field,holding_field='holding_days'):
 vals=[D(str(r[value_field])) for r in rows];wins=[x for x in vals if x>0];loss=[x for x in vals if x<0]
 return {'count':len(rows),'wins':len(wins),'losses':len(loss),'flat':sum(x==0 for x in vals),
  'win_fraction':D(len(wins))/len(vals) if vals else None,'mean_return':sum(vals,D(0))/len(vals) if vals else None,
  'mean_win':sum(wins,D(0))/len(wins) if wins else None,'mean_loss':sum(loss,D(0))/len(loss) if loss else None,
  'mean_holding_days':sum(D(str(r[holding_field])) for r in rows)/len(rows) if rows else None}
def build_prior_evidence(opportunities,decisions,*,groups,variants,fees,min_distinct=30):
 """One row per target candidate/group/variant/fee for both evidence clocks.
 Required opportunity fields: candidate_id,symbol,group,variant,fee,signal_date,
 entered,entry_date,exit_date,net_return,maturity_quote_date,return_at_60,
 holding_days,holding_days_at_60.
 maturity_quote_date is externally reconstructed as the 60th valid quote strictly
 after entry; this function never approximates it with calendar days.
 """
 out=[]
 for target in decisions:
  decision=target['signal_date'];prior=[r for r in opportunities if r['symbol']==target['symbol'] and r['signal_date']<decision and r['candidate_id']!=target['candidate_id']]
  for group in groups:
   for variant in variants:
    for fee in fees:
     scope=[r for r in prior if r['group']==group and r['variant']==variant and str(r['fee'])==str(fee)]
     entered_known=[r for r in scope if r['entered'] and r['entry_date'] is not None and r['entry_date']<=decision]
     completed=[r for r in entered_known if r['exit_date'] is not None and r['exit_date']<decision]
     unresolved=[r for r in entered_known if r['exit_date'] is None or r['exit_date']>=decision]
     # Mature opportunities require both variants to have entered; maturity is a quote date, strict before decision.
     candidate_variants={}
     for r in prior:
      if r['group']==group and str(r['fee'])==str(fee):candidate_variants.setdefault(r['candidate_id'],{})[r['variant']]=r
     common=[];immature=[]
     for cid,vr in candidate_variants.items():
      if not all(v in vr and vr[v]['entered'] and vr[v]['entry_date'] is not None and vr[v]['entry_date']<=decision for v in variants):continue
      dates={vr[v]['maturity_quote_date'] for v in variants}
      if len(dates)!=1:raise ValueError(f'maturity quote mismatch {cid}')
      md=next(iter(dates))
      if md is not None and md<decision:common.append(vr[variant])
      else:immature.append(cid)
     cs=_stats(completed,'net_return');ms=_stats(common,'return_at_60','holding_days_at_60')
     out.append({'target_candidate_id':target['candidate_id'],'decision_date':decision,'symbol':target['symbol'],'group':group,'variant':variant,'fee':str(fee),
      'completed_evidence':cs,'completed_candidate_ids':[r['candidate_id'] for r in completed],
      'unresolved_count':len(unresolved),'unresolved_candidate_ids':[r['candidate_id'] for r in unresolved],
      'maximum_completed_known_date':max((r['exit_date'] for r in completed),default=None),
      'mature_60_evidence':ms,'mature_candidate_ids':[r['candidate_id'] for r in common],
      'maximum_maturity_quote_date':max((r['maturity_quote_date'] for r in common),default=None),
      'immature_count':len(immature),'immature_candidate_ids':immature,
      'history_display_status':'descriptive' if len({r['candidate_id'] for r in completed})>=min_distinct else 'insufficient_history',
      'mature_history_display_status':'descriptive' if len({r['candidate_id'] for r in common})>=min_distinct else 'insufficient_history'})
 return out
