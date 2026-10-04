"""Read-only method audit. No market requests, fits, package imports or writes to input root."""
import argparse,ast,collections,csv,hashlib,io,json,math
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists(): raise SystemExit('output exists; retain previous evidence')
root=args.source_root;b=root/'docs/experiments/raw/color-gray-path-2026-10-04';sources={}
def read(rel):
 data=(root/rel).read_bytes();sources[rel]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)};return data
def obj(p):return json.loads(read(str(p.relative_to(root))))
code=read('src/lei_signal/research/color_continuous_information.py');tree=ast.parse(code)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='same_day_ranks')
ns={'defaultdict':collections.defaultdict,'math':math};exec(compile(ast.Module(body=[node],type_ignores=[]),'same_day_ranks audit body','exec'),ns);rank=ns['same_day_ranks'];checks=[]
def case(name,rows,expected):
 result=rank(rows,'x');got=[r['x_rank'] for r in result];assert got==expected,(name,got,expected);assert all('x_rank' not in r for r in rows);checks.append({'name':name,'result':got,'passed':True})
def rows(xs):return [{'asset':str(i),'date':'2025-01-02','x':x,'ready_252':True} for i,x in enumerate(xs)]
case('average ties',rows([1,2,2,4]),[0,.5,.5,1]);case('constant',rows([5]*4),[.5]*4)
case('singleton',rows([3]),[None]);case('finite numbers only',rows([False,float('nan'),2,4]),[None,None,0,1])
rr=rows([1,2,3]);rr[0]['ready_252']=False;case('unknown excluded',rr,[None,0,1])
rr=rows([1,2]);rr[1]['date']='2025-01-03';case('dates separated',rr,[None,None])
try:rank(rows([1,2]),'color20')
except ValueError:checks.append({'name':'categorical rank rejected','passed':True})
else:raise AssertionError('categorical accepted')
branches={};snapshots={};fits=0
for stage in ('core','continuous'):
 for target in ('forward_return','mae'):
  for method in ('ridge','lightgbm'):
   key=stage+'/'+method+'-'+target;p=b/key/'core-01';r=obj(p/'result.json');c=obj(p/'contract.json');receipt=obj(p/'receipt.json')
   assert receipt['contract_sha256']==sources[str((p/'contract.json').relative_to(root))]['sha256']
   for name,sha in receipt['outputs'].items():assert hashlib.sha256(read(str((p/name).relative_to(root)))).hexdigest()==sha,(key,name)
   fs=r['execution']['fits'];assert fs==len(r['execution']['fit_details']);fits+=fs
   pred=r['predictions'];assert len({x['id'] for x in pred})==len(pred)
   for x in pred:
    fold=c['split']['folds'][int(x['fold'])];assert fold['eval_start']<=x['date']<=x['label_end']<=fold['eval_end']
   branches[key]={'fits':fs,'rows':len(pred),'dates':len({x['date'] for x in pred}),'receipt_hashes_verified':True,'data_sha256':c['data']['sha256']}
   snapshots[key]=(r,c)
matrices={}
for stage in ('core','continuous'):
 for target in ('forward_return','mae'):
  r,c=snapshots[stage+'/ridge-'+target];t,d=snapshots[stage+'/lightgbm-'+target]
  for k in ('data','split','weights','feature','target','universe'):assert c[k]==d[k],(stage,target,k)
  for k in ('baseline_features','added_features','minimum_training_rows'):assert c['evaluator'][k]==d['evaluator'][k]
  for x,y in zip(r['predictions'],t['predictions']):
   for k in ('id','asset','date','label_end','y','fold'):assert x[k]==y[k],(stage,target,k)
  assert len(r['predictions'])==len(t['predictions'])
  for x,y in zip(r['execution']['fit_details'],t['execution']['fit_details']):
   for k in ('fold','model','training_rows','training_weights','features'):assert x[k]==y[k]
  pred=r['predictions'];counts=collections.Counter(x['asset'] for x in pred);diff={}
  for name,old,new in [('B-A','B1','B2'),('D-C','B1','B2'),('C-A','B1','B1'),('D-B','B2','B2')]:
   left=r if name in ('B-A','C-A','D-B') else t;right=r if name=='B-A' else t
   losses=[(x['y']-x[old])**2-(y['y']-y[new])**2 for x,y in zip(left['predictions'],right['predictions'])]
   equal_asset=sum(v/counts[x['asset']]/len(counts) for x,v in zip(pred,losses));byday=collections.defaultdict(list)
   for x,v in zip(pred,losses):byday[x['date']].append(v)
   equal_date=sum(sum(v)/len(v) for v in byday.values())/len(byday)
   diff[name]={'equal_asset_mse_improvement':equal_asset,'equal_date_mse_improvement':equal_date,'weighting_difference':equal_asset-equal_date}
  matrices[stage+'/'+target]={'same_contract_support_verified':True,'differences':diff}
for rel in ['src/lei_signal/research/color_continuous_workflow.py','src/lei_signal/research/lightgbm_information.py','src/lei_signal/research/workflow_evaluation.py','docs/experiments/raw/color-gray-path-2026-10-04/analyze_saved.py','docs/experiments/raw/color-gray-path-2026-10-04/resume-2026-10-05.json','docs/experiments/raw/color-gray-path-2026-10-04/continuous/ledger.json','configs/rules.v2.yaml']:read(rel)
ranks=list(csv.DictReader(io.StringIO(read(str((b/'same-day-ranking-rows.csv').relative_to(root))).decode())))
rank_results={}
for field in ('green_share20','switch_frequency20','distance_to_ema20','ret20','ema20_up_share20'):
 grouped=collections.defaultdict(list)
 for x in ranks:grouped[x['date']].append(x)
 n=0
 for xs in grouped.values():
  rr=[{'date':x['date'],'ready_252':True,'x':float(x[field])} for x in xs];expected=rank(rr,'x')
  for x,e in zip(xs,expected):assert math.isclose(float(x[field+'_rank']),e['x_rank'],abs_tol=1e-14)
  n+=len(xs)
 rank_results[field]={'saved_rank_rows_verified':n,'pool_scope':'saved evaluation support only; does not certify X-only pool construction'}
changed=[rel for rel,v in sources.items() if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=v['sha256']];assert not changed,changed
args.output.write_text(json.dumps({'mode':'report_only + seven tiny function boundary checks','new_market_fits':0,'observed_saved_fits':fits,'branches':branches,'rank_function_checks':checks,'saved_rank_checks':rank_results,'four_matrix_checks':matrices,'sources':sources,'source_root_role':'technical task worktree; only local at audit, published version must be supplied by owner'},indent=2,ensure_ascii=False,allow_nan=False)+'\n')
print(json.dumps({'boundary_checks':len(checks),'branches':len(branches),'matrix_pairs':len(matrices),'saved_rank_fields':len(rank_results),'observed_saved_fits':fits,'new_fits':0,'output':str(args.output)}))
