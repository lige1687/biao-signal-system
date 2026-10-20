"""Fixed three-policy comparison. Only offline research data and frozen E01 accounting."""
from pathlib import Path
import importlib.util,sys,ast,json,hashlib,datetime,gzip
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent;E=P.parent/'e01'
spec=importlib.util.spec_from_file_location('e01_frozen',E/'run_e01.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):(P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=str)+'\n')
def csv(name,rows):
 b=pd.DataFrame(rows).to_csv(index=False,float_format='%.17g').encode();f=P/name;f.parent.mkdir(exist_ok=True,parents=True);f.write_bytes(gzip.compress(b,mtime=0) if name.endswith('.gz') else b)
def factory(target):
 tree=ast.parse((E/'run_e01.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='account')
 class Change(ast.NodeTransformer):
  count=0
  def visit_Compare(self,n):
   n=self.generic_visit(n)
   if len(n.comparators)==1 and isinstance(n.ops[0],ast.GtE) and isinstance(n.comparators[0],ast.Constant) and n.comparators[0].value==.30:n.comparators[0]=ast.Name(id='TARGET',ctx=ast.Load());self.count+=1
   return n
 c=Change();fn=c.visit(fn);assert c.count==1;ns={'np':np,'pd':pd,'risk_stats':m.risk_stats,'TARGET':target if target is not None else float('inf')};exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'frozen_account_one_threshold_change','exec'),ns);return ns['account']

def main():
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();inputs={str(f):h(f) for f in (E/'inputs').rglob('*') if f.is_file()};inputs[str(E/'run_e01.py')]=h(E/'run_e01.py');inputs[str(E/'frozen-events.json')]=h(E/'frozen-events.json');inputs[str(P/'protocol-v1.md')]=h(P/'protocol-v1.md')
 funcs={.30:factory(.30),.50:factory(.50),None:factory(None)};growth=['399006','512100','588000'];frames={s:m.full_frame(s) for s in m.SYMS};old=json.loads((E/'inputs/legacy_results.json').read_text());expected={x['case']:x for x in json.loads((E/'account-summary.json').read_text())};evs={(x['symbol'],x['kind']):[{'e':z['e'],'decision_at':pd.Timestamp(z['decision_at'])} for z in x['events']] for x in json.loads((E/'frozen-events.json').read_text())}
 singles=[];accounts=[];actions=[];plans=[];eventrows=[];baseline_errors=[];identity_errors=[]
 for s,(d,start) in frames.items():
  for k in m.KINDS:
   for fee in [10.,20.]:
    results={}
    for arm,target in [('A',.30),('B',.50 if s in growth else .30),('C',None)]:
     case=f'{s}|{k}|fee{int(fee)}|{arm}';f=funcs[target];r,days,tr,er,ac=f(d,start,evs[s,k],fee,case);r.update(symbol=s,kind=k,arm=arm,target=target);accounts.append(r);plans+=tr;eventrows+=er;actions+=ac;results[arm]=(r,days)
     csv('daily/continuous_'+case.replace('|','_')+'.csv.gz',days)
     if arm=='A':
      oldr=expected[f'{s}|{k}|fee{int(fee)}']
      for field in oldr:
       if field!='case' and oldr[field]!=r[field]:baseline_errors.append({'case':case,'field':field,'old':oldr[field],'new':r[field]})
     for n,t in enumerate(old['trades'][k+'|Xtarget'].get(s,[])):
      e=int(d.index.get_loc(pd.Timestamp(t['entry_date'])));end=min(e+756,len(d)-1);one=d.iloc[:end+1];ev=[{'e':e,'decision_at':d.index[e]+pd.Timedelta(hours=16)}];ck=f'{case}|single{n:03d}';q,ds,ts,es,acs=f(one,e,ev,fee,ck);q.update(symbol=s,kind=k,arm=arm,target=target,opportunity=f'{s}|{k}|{t["entry_date"]}',entry_date=t['entry_date']);singles.append(q);actions+=acs;plans+=ts;eventrows+=es;csv('daily/single_'+ck.replace('|','_')+'.csv.gz',ds)
    if s not in growth:
     if results['A'][1]!=results['B'][1]:identity_errors.append({'symbol':s,'kind':k,'fee':fee})
 assert not baseline_errors and not identity_errors
 assert len(accounts)==192 and len(singles)==876
 save('continuous-summary.json',accounts);save('single-summary.json',singles);csv('all-actions.csv.gz',actions);csv('all-plans.csv',plans);csv('all-events.csv',eventrows)
 # Connected historical coverage is descriptive dependence grouping, not an independence certificate.
 intervals=sorted({(q['entry_date'],q['end'],q['opportunity']) for q in singles});groups=[];mapping={}
 for st,en,key in intervals:
  if not groups or st>groups[-1]['end']:groups.append({'id':len(groups)+1,'start':st,'end':en,'opportunities':[]})
  else:groups[-1]['end']=max(groups[-1]['end'],en)
  groups[-1]['opportunities'].append(key);mapping[key]=groups[-1]['id']
 save('historical-overlap-groups.json',{'groups':groups,'note':'重叠或相连覆盖归组，不能据此称统计独立；没有新历史验证'})
 pair=[]
 for fee in [10.,20.]:
  for k in m.KINDS:
   for sym in growth:
    rows=[q for q in singles if q['fee_bps']==fee and q['kind']==k and q['symbol']==sym];keys=sorted({q['opportunity'] for q in rows})
    for key in keys:
     arms={q['arm']:q for q in rows if q['opportunity']==key}
     for arm in ['B','C']:
      a,b=arms['A'],arms[arm];pair.append(dict(symbol=sym,kind=k,fee_bps=fee,opportunity=key,coverage_group=mapping[key],comparison=arm+'-A',wealth_delta=b['final_wealth']-a['final_wealth'],drawdown_delta=b['max_drawdown']-a['max_drawdown'],a_wealth=a['final_wealth'],b_wealth=b['final_wealth'],a_mdd=a['max_drawdown'],b_mdd=b['max_drawdown']))
 csv('single-paired-differences.csv',pair);groupstats=[]
 for fee in [10.,20.]:
  for k in m.KINDS:
   for cmp in ['B-A','C-A']:
    rows=[x for x in pair if x['fee_bps']==fee and x['kind']==k and x['comparison']==cmp];v=np.array([x['wealth_delta'] for x in rows]);ids=sorted({x['coverage_group'] for x in rows});leave=[]
    for cid in ids:
     rem=[x['wealth_delta'] for x in rows if x['coverage_group']!=cid];leave.append({'excluded':cid,'remaining':len(rem),'median':float(np.median(rem)) if rem else None})
    groupstats.append(dict(fee_bps=fee,kind=k,comparison=cmp,n=len(v),mean_delta=float(v.mean()),median_delta=float(np.median(v)),minimum=float(v.min()),p10=float(np.quantile(v,.1)),maximum=float(v.max()),positive=int((v>1e-12).sum()),negative=int((v< -1e-12).sum()),zero=int((abs(v)<=1e-12).sum()),coverage_groups=ids,leave_one_group_out=leave))
 save('comparison-summary.json',groupstats)
 assert all(h(Path(f))==v for f,v in inputs.items())
 save('run-manifest.json',{'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':inputs,'script_sha256':h(Path(__file__)),'unchanged_inputs':True,'single_paths':876,'continuous_paths':192,'baseline_mismatches':baseline_errors,'unchanged_symbol_mismatches':identity_errors,'coverage_groups':len(groups),'trials':['A 30%','B fixed growth50%, other30%','C deadline only'],'verdict_scope':'exploratory historical comparison; no product acceptance'})
 print(json.dumps({'counts':[len(singles),len(accounts)],'groups':len(groups),'main':[r for r in groupstats if r['fee_bps']==10 and r['comparison']=='B-A']},ensure_ascii=False))
if __name__=='__main__':main()
