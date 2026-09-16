"""Point-in-time historical evidence tables. No trading-engine imports."""
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal as D

def build_evidence(outcomes, decisions, *, group_fields, variant_field='exit_variant',
                   signal_field='signal_date', known_field='outcome_known_date',
                   return_field='net_return', holding_field='holding_days',
                   maturity_days=None, inclusive_known=True):
    """Return evidence rows using only outcomes knowable at each decision.

    With maturity_days, every variant uses the same candidate cohort whose signal
    date is at least that many calendar days before the decision. Outcomes still
    unresolved by the cutoff are counted, never scored as wins or losses.
    """
    required=set(group_fields)|{variant_field,signal_field,known_field,return_field,holding_field,'candidate_id'}
    for row in outcomes:
        missing=required-set(row)
        if missing: raise ValueError(f'missing outcome fields: {sorted(missing)}')
    result=[]
    for decision in sorted(decisions):
        cutoff=date.fromisoformat(decision)
        cohort=[]
        for row in outcomes:
            signal=date.fromisoformat(row[signal_field])
            if signal>cutoff: continue
            if maturity_days is not None and signal+timedelta(days=maturity_days)>cutoff: continue
            cohort.append(row)
        buckets=defaultdict(list)
        for row in cohort:buckets[tuple(row[k] for k in group_fields)+(row[variant_field],)].append(row)
        for key,rows in sorted(buckets.items(),key=lambda x:tuple(str(v) for v in x[0])):
            visible=[];unresolved=[]
            for row in rows:
                known=row[known_field]
                is_visible=known is not None and (known<=decision if inclusive_known else known<decision)
                (visible if is_visible else unresolved).append(row)
            returns=[D(str(r[return_field])) for r in visible]
            wins=[x for x in returns if x>0];losses=[x for x in returns if x<0]
            out={'decision_date':decision,**dict(zip(group_fields,key[:-1])),variant_field:key[-1],
                 'maturity_days':maturity_days,'cohort_count':len(rows),'visible_completed':len(visible),
                 'unresolved_count':len(unresolved),'wins':len(wins),'losses':len(losses),
                 'flat':sum(x==0 for x in returns),'win_fraction':D(len(wins))/len(returns) if returns else None,
                 'mean_net_return':sum(returns,D(0))/len(returns) if returns else None,
                 'mean_win':sum(wins,D(0))/len(wins) if wins else None,
                 'mean_loss':sum(losses,D(0))/len(losses) if losses else None,
                 'mean_holding_days':sum(D(str(r[holding_field])) for r in visible)/len(visible) if visible else None,
                 'included_candidate_ids':[r['candidate_id'] for r in visible],
                 'unresolved_candidate_ids':[r['candidate_id'] for r in unresolved]}
            result.append(out)
    return result
