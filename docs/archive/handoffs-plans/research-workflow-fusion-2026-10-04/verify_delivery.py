"""Read-only independent checks of fixed deliveries; no research runs or fitting."""
import argparse,csv,hashlib,io,json,math,subprocess
from pathlib import Path
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
root=Path.cwd(); sources=[]
def blob(ref,path):
 b=subprocess.check_output(['git','show',ref+':'+path]);sources.append({'commit':ref,'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
def obj(ref,path):return json.loads(blob(ref,path))
def close(a,b):assert abs(a-b)<1e-10,(a,b)
tech='2ab565017a7a4959af744430339e32a09ce12667';risk='c47aaa78b6972689743c57fdcb739c675c7c05af';ext='af8934d60511ae24f9e182bdf2d4a441a723cc12'
report=blob(tech,'docs/experiments/technical-persistence-and-color-transition-2026-10-04.md').decode()
assert all(x in report for x in ['D1实际用途','D2负结论','D5真正未来观察','最早合法新观察日期','未确定','paused'])
a=obj(tech,'docs/experiments/raw/technical-multimethod-2026-10-03/analysis.json')
tech_scores={}
for purpose in ['return','risk']:
 v=a['core'][purpose]['subsets']['all'];close(v['B1_minus_B2'],v['rmse']['B1']-v['rmse']['B2']);tech_scores[purpose]=v
prefix='docs/experiments/raw/risk-shape-error-decomposition-2026-10-04/'
s=obj(risk,prefix+'summary.json');v=obj(risk,prefix+'verification.json')
original_path=v['original_run']+'/result.json';raw=blob(risk,original_path);assert hashlib.sha256(raw).hexdigest()==v['original_hashes_sha256']['result.json']
original=json.loads(raw)['predictions'];rows=list(csv.DictReader(io.StringIO(blob(risk,prefix+'full-differences.csv').decode())))
old={r['id']:r for r in original};assert len(old)==len(original)==len(rows)==951;assert set(old)=={r['id'] for r in rows}
assets=Counter(r['asset'] for r in rows);dates=Counter(r['date'] for r in rows);assert len(assets)==3 and set(assets.values())=={317} and set(dates.values())=={3}
contrib={'better':[],'same':[],'worse':[]};m1=[];m2=[]
for r in rows:
 o=old[r['id']]
 for key in ['asset','date','label_end','fold']:assert str(o[key])==r[key]
 for key in ['y','B0','B1','B2','train_mean']:close(float(r[key]),float(o[key]))
 w=1/len(assets)/assets[r['asset']];e1=(float(o['y'])-float(o['B1']))**2;e2=(float(o['y'])-float(o['B2']))**2;delta=e1-e2
 close(w,float(r['weight_equal_asset']));close(delta,float(r['difference_old_minus_new']));close(w*delta,float(r['weighted_difference']))
 sign='better' if delta>0 else 'worse' if delta<0 else 'same';assert sign==r['direction'];contrib[sign].append(w*delta);m1.append(w*e1);m2.append(w*e2)
for name,values in contrib.items():assert len(values)==s['signs'][name]['rows'];close(math.fsum(values),s['signs'][name]['signed_contribution'])
close(math.fsum(m1),s['B1_mse']);close(math.fsum(m2),s['B2_mse']);net=math.fsum(m1)-math.fsum(m2);close(net,s['net_weighted_improvement'])
c=obj(ext,'docs/experiments/raw/external-mining-reuse-2026-10-03/core-result.json');x=c['inputs']['x'][0];z=c['inputs']['z'][0];y=c['inputs']['target'][0]
def corr(a,b):
 ma=math.fsum(a)/len(a);mb=math.fsum(b)/len(b);return math.fsum((u-ma)*(v-mb) for u,v in zip(a,b))/math.sqrt(math.fsum((u-ma)**2 for u in a)*math.fsum((v-mb)**2 for v in b))
close(corr(x,z),0);close(corr(x,y),1/math.sqrt(2))
trans=c['pool_transitions'];assert [p['size'] for p in trans]==[1,2,2,3]
w=trans[1]['json']['weights'];combo=[w[0]*u+w[1]*v for u,v in zip(x,z)];close(corr(combo,y),1)
w=trans[3]['json']['weights'];signed=[w[0]*u+w[1]*v-w[2]*u for u,v in zip(x,z)];close(corr(signed,y),1)
p=args.source_root/'docs/ops/materials-readiness-classic-baseline-2026-10-04.json';b=p.read_bytes();d=json.loads(b);sources.append({'path':str(p.relative_to(args.source_root)),'delivery':'local_only','bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
checks={}
for group,hashfield,base in [('lifecycle_basis','sha256_main',args.source_root),('definition_sources','sha256',args.source_root),('legacy_inputs','sha256_main',args.source_root),('local_only_saved_artifacts','sha256',root)]:
 results=[]
 for item in d[group]:
  path=base/item['path'];actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
  results.append({'path':item['path'],'expected':item.get(hashfield),'actual':actual,'matches':actual==item.get(hashfield) and actual is not None})
 checks[group]={'count':len(results),'matched':sum(r['matches'] for r in results),'mismatches':[r for r in results if not r['matches']]}
checks['classic_missing_legacy_inputs']=[r['path'] for r in d['legacy_inputs'] if not (root/r['path']).is_file()]
out={'checked_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'mode':'report_only','coordination_read':'2a1cafee62d0a58d0f4ebd7f929d9242def61ffc','D1_D2_D5':{'required_sections_present':True,'reported_aggregate_arithmetic_matches':True,'scores':tech_scores,'future_collection':'blocked; readiness review only'},'D3':{'rows':len(rows),'dates':len(dates),'assets':len(assets),'original_saved_predictions_sha_matches':True,'original_identity_values_weights_match':True,'sign_counts':{k:len(v) for k,v in contrib.items()},'signed_contributions':{k:math.fsum(v) for k,v in contrib.items()},'net':net,'B1_mse':math.fsum(m1),'B2_mse':math.fsum(m2),'relative_percent':100*net/math.fsum(m1)},'D4':{'synthetic_input_correlation':corr(x,z),'single_target_correlation':corr(x,y),'combined_target_correlation':corr(combo,y),'negative_duplicate_combination_correlation':corr(signed,y),'saved_pool_sizes':[p['size'] for p in trans],'financial_increment':'not_evaluated','scope':'saved algebra only; native pool not rerun'},'D6':checks,'sources':sources,'budget':{'new_market_fits':0,'market_requests':0,'paid_operations':0,'saved_result_review_batches':1},'limitations':['D1/D2 review verifies scope and saved aggregate, not a new full financial replication.','D6 local source presence does not establish transfer permission or cross-machine restoration.']}
args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['D3','D4','D6']},ensure_ascii=False))
