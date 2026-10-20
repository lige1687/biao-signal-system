"""Descriptive paired reporting only; no new parameters or selection."""
from pathlib import Path
import json, hashlib
import pandas as pd

P=Path(__file__).resolve().parent
d=pd.read_csv(P/'atr-opportunity-ledger.csv')
one=d[(d.fee=='amount_5bp')&(d.sizing=='same_budget')]
paired=[]
for mod,g in one.groupby('module'):
    base=g[g.arm=='base'].set_index('key'); buf=g[g.arm=='buffer'].set_index('key').loc[base.index]
    a=g[g.arm=='base_rr3'].set_index('key').loc[base.index]; b=g[g.arm=='buffer_rr3'].set_index('key').loc[base.index]
    assert not (b.entered&~a.entered).any()
    used=base.entered&buf.entered
    changed=used&(base.exit_date.fillna('')!=buf.exit_date.fillna(''))
    skipped=a.entered&~b.entered
    paired.append({'module':mod,'opportunities':len(base),'entered':int(used.sum()),'changed_exit_date':int(changed.sum()),'changed_exit_reason':int((used&(base.exit_reason.fillna('')!=buf.exit_reason.fillna(''))).sum()),'mean_additional_holding_bars':float((buf.holding_bars-base.holding_bars).mean()),'mean_budget_return_change':float((buf.budget_return-base.budget_return).mean()),'base_rr3_entered':int(a.entered.sum()),'buffer_rr3_entered':int(b.entered.sum()),'additional_skips':int(skipped.sum()),'skipped_baseline_profitable':int((skipped&(a.budget_return>0)).sum()),'skipped_baseline_loss':int((skipped&(a.budget_return<0)).sum()),'forgone_return_mean_all_opportunities':float(a.loc[skipped,'budget_return'].sum()/len(a))})
groups=[]
for key,g in d.groupby(['module','structure_distance_atr_group','arm','fee','sizing']):
    groups.append(dict(zip(['module','distance_atr_group','arm','fee','sizing'],key),n=len(g),entered=int(g.entered.sum()),mean_budget_return=float(g.budget_return.mean()),mean_minimum_budget_return=float(g.minimum_budget_return.mean())))
fees=d[(d.arm=='base')&(d.sizing=='same_budget')&(d.entered)]
wide=fees.pivot(index='key',columns='fee',values='budget_return')
base=fees[fees.fee=='legacy'].set_index('key')
base['effective_legacy_one_side_bps']=(50/base.entry_price).clip(lower=5)
base['amount5_minus_legacy_return']=wide['amount_5bp']-wide['legacy']
base[['module','symbol','entry_date','entry_price','effective_legacy_one_side_bps','amount5_minus_legacy_return']].to_csv(P/'fee-opportunity-comparison.csv')
cost={m:{'entered':len(g),'legacy_above_label_5bps':int((g.effective_legacy_one_side_bps>5+1e-10).sum()),'median_effective_one_side_bps':float(g.effective_legacy_one_side_bps.median()),'maximum_effective_one_side_bps':float(g.effective_legacy_one_side_bps.max()),'mean_amount5_minus_legacy_return':float(g.amount5_minus_legacy_return.mean())} for m,g in base.groupby('module')}
out={'paired_amount5_same_budget':paired,'cost_diagnostics':cost,'distance_groups':groups,'note':'all figures are independent adjusted-price opportunity budgets; not account returns or authentic product fee estimates','source_ledger_sha256':hashlib.sha256((P/'atr-opportunity-ledger.csv').read_bytes()).hexdigest()}
(P/'atr-paired-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='distance_groups'},ensure_ascii=False,indent=2))
