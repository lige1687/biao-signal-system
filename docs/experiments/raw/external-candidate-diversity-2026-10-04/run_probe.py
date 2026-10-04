"""Fixed native-component comparison on artificial formulas; no market input."""
import argparse,hashlib,json,os,platform,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Do not overwrite evidence')
 root=Path(__file__).resolve().parent
 protocol=json.loads((root/'protocol.json').read_text()); cases=json.loads((root/'cases.json').read_text()); prov=json.loads((root/'provenance.json').read_text())
 assert hashlib.sha256((root/'cases.json').read_bytes()).hexdigest()==protocol['cases_sha256']
 for item in prov['files']:assert hashlib.sha256((a.upstream/item['path']).read_bytes()).hexdigest()==item['sha256']
 sys.path.insert(0,str(a.upstream.resolve()))
 import numpy as np
 import sympy
 from factorminer.core.parser import parse
 from factorminer.core.expression_plan import compile_tree
 from factorminer.core.canonicalizer import FormulaCanonicalizer
 from factorminer.memory import embeddings
 assert not embeddings._has_sentence_transformers and not embeddings._has_sklearn and not embeddings._has_faiss, 'Protocol requires native hash fallback, no implicit downloads'
 t=np.arange(80,dtype=float);close=10+t/10+np.sin(t);open_=close+np.cos(t)*.7
 open_[1]=0.;open_[2]=1e-12;open_[3]=np.nan;open_[4]=close[4];close[5]=np.nan
 data={'$close':close[None,:],'$open':open_[None,:],'$high':(close+2)[None,:],'$low':(close-2)[None,:]}
 # The native feature API uses names with dollar prefixes.
 start=time.monotonic();out=[];canon=FormulaCanonicalizer()
 for c in cases:
  left,right=parse(c['left']),parse(c['right']);lp,rp=compile_tree(left),compile_tree(right)
  emb=embeddings.FormulaEmbedder(use_faiss=False);emb.embed('left',c['left']);near=emb.find_nearest(c['right'],k=1)
  lv,rv=left.evaluate(data),right.evaluate(data)
  same_values=bool(np.allclose(lv,rv,rtol=0,atol=1e-12,equal_nan=True))
  if c['kind'] in ['exact','equivalent']:assert same_values,c['id']
  if c['kind'] in ['different','edge_different']:assert not same_values,c['id']
  same_ctx=c['context_left']==c['context_right']
  methods={'raw_string':c['left']==c['right'],'native_structure':lp.digest==rp.digest,'native_semantic_hash':emb.is_semantic_duplicate(c['right']) is not None,'native_algebraic':canon.is_duplicate(left,right),'context_bound_structure':lp.digest==rp.digest and same_ctx}
  different=np.where(~np.isclose(lv,rv,rtol=0,atol=1e-12,equal_nan=True))
  witnesses=[{'asset_index':int(i),'time_index':int(j),'left':None if not np.isfinite(lv[i,j]) else float(lv[i,j]),'right':None if not np.isfinite(rv[i,j]) else float(rv[i,j])} for i,j in zip(*different)][:3]
  out.append({'id':c['id'],'kind':c['kind'],'safe_same_evaluation':c['safe_same_evaluation'],'same_context':same_ctx,'same_synthetic_values':same_values,'decisions':methods,'similarity':near[0][1],'left_digest':lp.digest,'right_digest':rp.digest,'left_canonical':canon.get_canonical_form(left),'right_canonical':canon.get_canonical_form(right),'witnesses':witnesses})
 invalid=[]
 for f in protocol['invalid_controls']:
  try:parse(f)
  except Exception as e:invalid.append({'formula':f,'rejected':True,'error':type(e).__name__})
  else:invalid.append({'formula':f,'rejected':False})
 summary={}
 for method in out[0]['decisions']:
  summary[method]={'correct_duplicate':sum(x['decisions'][method] and x['safe_same_evaluation'] for x in out),'unsafe_duplicate':sum(x['decisions'][method] and not x['safe_same_evaluation'] for x in out),'missed_duplicate':sum(not x['decisions'][method] and x['safe_same_evaluation'] for x in out),'correct_keep':sum(not x['decisions'][method] and not x['safe_same_evaluation'] for x in out)}
 result={'seed':os.environ.get('PYTHONHASHSEED'),'python':platform.python_version(),'numpy':np.__version__,'sympy':sympy.__version__,'protocol_sha256':hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-start,'rows':out,'summary':summary,'invalid':invalid,'financial_increment':'not_measured'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
