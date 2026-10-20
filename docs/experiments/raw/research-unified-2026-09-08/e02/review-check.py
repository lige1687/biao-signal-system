"""Bounded independent E02 checks; does not execute the E01/E02 engines."""
from pathlib import Path
import json,hashlib
import pandas as pd
P=Path(__file__).resolve().parent;E=P.parent/'e01';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();errors=[]
script_before=h(P/'run_e02.py');summ=json.loads((P/'continuous-summary.json').read_text());baseline=[];negative=[]
for q in summ:
 sym,k,fee,arm=q['case'].split('|');stem='_'.join([sym,k,fee]);target=P/'daily'/f'continuous_{stem}_{arm}.csv.gz'
 if arm=='A':
  source=E/'daily'/f'{stem}.csv.gz';baseline.append({'case':q['case'],'e01_sha256':h(source),'e02_sha256':h(target),'identical':source.read_bytes()==target.read_bytes()})
 if arm=='B' and sym not in ['399006','512100','588000']:
  source=P/'daily'/f'continuous_{stem}_A.csv.gz';negative.append({'case':q['case'],'a_sha256':h(source),'b_sha256':h(target),'identical':source.read_bytes()==target.read_bytes()})
assert len(baseline)==64 and len(negative)==40
numeric=json.loads((P/'numeric-before-label-fix.json').read_text());hashes=[{'path':k,'before':v,'after':h(P/k),'identical':v==h(P/k)} for k,v in numeric.items()];assert len(hashes)==4
labels=[]
for old,new in [('v1-all-actions.csv.gz','all-actions.csv.gz'),('v1-all-plans.csv','all-plans.csv')]:
 a=pd.read_csv(P/old);b=pd.read_csv(P/new);assert list(a.columns)==list(b.columns) and a.shape==b.shape
 changing=(a.reason!=b.reason);same_numeric=a.drop(columns=['reason']).equals(b.drop(columns=['reason']));rows=b.loc[changing,['case','reason']]
 valid=bool(((rows.reason=='target50') & rows.case.str.match(r'^(399006|512100|588000)\|[^|]+\|fee(10|20)\|B($|\|)')).all() and (a.loc[changing,'reason']=='target30').all())
 labels.append({'file':new,'changed_labels':int(changing.sum()),'everything_except_reason_equal':same_numeric,'only_growth_B_30_to_50':valid})
actions=pd.read_csv(P/'all-actions.csv.gz');case='399006|deep20|fee10|B';x=actions[(actions.case==case)&(actions.plan==1)];buy=x[x.action=='buy'];sell=x[x.action=='sell'].iloc[0];d=pd.read_parquet(E/'inputs/cache/399006.parquet');i=d.index.get_loc(sell.date);qty=float(((buy.amount-buy.fee)/buy.price).sum());spent=float(buy.amount.sum());pre=float(d.close.iloc[i-1]);prior=float(d.close.iloc[i-2]);op=float(d.open.iloc[i]);net=qty*op*.999
q={'case':case,'plan':1,'buy_count':len(buy),'actual_spend':spent,'units':qty,'previous_quote':str(d.index[i-1].date()),'previous_close':pre,'signal_return':qty*pre/spent-1,'prior_quote_return':qty*prior/spent-1,'execution_date':sell.date,'execution_open':op,'reported_available_at':sell.available_at,'reported_reason':sell.reason,'reconstructed_net_proceeds':net,'reported_net_proceeds':float(sell.amount-sell.fee),'price_matches':abs(op-sell.price)<1e-12,'quantity_matches':abs(qty-sell.units)<1e-12,'net_matches':abs(net-(sell.amount-sell.fee))<1e-12,'trigger_before_execution':pd.Timestamp(sell.available_at)<pd.Timestamp(sell.date)+pd.Timedelta(hours=9,minutes=30),'target50_met':qty*pre/spent-1>=.5}
q={k:(v.item() if hasattr(v,'item') else v) for k,v in q.items()}
# Independent interval merging, using all policies/fees only once per fixed opportunity.
singles=json.loads((P/'single-summary.json').read_text());intervals=sorted(set((x['entry_date'],x['end'],x['opportunity']) for x in singles));groups=[]
for start,end,key in intervals:
 if not groups or start>groups[-1]['end']:groups.append({'start':start,'end':end,'n':1})
 else:groups[-1]['end']=max(groups[-1]['end'],end);groups[-1]['n']+=1
out={'scope':'Only requested E02 baseline/negative-control/one-exit/label checks, not production acceptance or all-path independent accounting.','baseline_A_vs_E01':{'n':len(baseline),'all_identical':all(x['identical'] for x in baseline),'files':baseline},'non_growth_B_vs_A':{'n':len(negative),'all_identical':all(x['identical'] for x in negative),'files':negative},'numeric_before_after_labels':hashes,'action_plan_label_changes':labels,'growth_exit_arithmetic':q,'coverage_groups_rebuilt':groups,'fixed_opportunities':len(intervals),'E02_source_sha256':script_before,'E02_source_unchanged':script_before==h(P/'run_e02.py'),'E01_source_hash_matches_run_manifest':h(E/'run_e01.py')==json.loads((P/'run-manifest.json').read_text())['inputs'][str(E/'run_e01.py')]}
(P/'review-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['baseline_A_vs_E01','non_growth_B_vs_A']},ensure_ascii=False,indent=2));print('A64',out['baseline_A_vs_E01']['all_identical'],'B40',out['non_growth_B_vs_A']['all_identical'])
