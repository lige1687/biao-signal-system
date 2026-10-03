"""Standard-library readback and independent arithmetic. Never refits/mines."""
import hashlib,json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def main():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for item in manifest['files']:
        p=ROOT/item['path'];assert len(p.read_bytes())==item['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],item['path']
    inputs=json.loads((ROOT/'core/inputs.json').read_text());results=json.loads((ROOT/'core/results.json').read_text());pack=json.loads((ROOT/'core/skill-pack.json').read_text())
    payload={k:v for k,v in pack.items() if k!='pack_id'};assert hashlib.sha256(canonical(payload)).hexdigest()==pack['pack_id']
    cfg=inputs['action']['config'];checked=0;max_error=0
    for name,failed in [('no_history',0),('failed_history',100),('foreign_context',0)]:
        row=results[name]['estimates'][0];p=cfg['prior_success']/(cfg['prior_success']+cfg['prior_failure']+failed);net=p*cfg['prior_gain']-cfg['evaluation_cost']-cfg['generation_cost'];max_error=max(max_error,abs(row['net_value']-net));assert abs(row['net_value']-net)<1e-14;assert results[name]['chosen']['kind']==('stop' if net<=0 else 'generate');checked+=1
    # Four panels have equal artificial effects, so their estimated radius is zero.
    score_maps={'without_memory':[0,0,0,0],'with_scoped_memory':[.15,-.1,0,0],'different_target':[0,0,0,0],'unknown_dynamics':[0,0,0,0],'100_rows_one_dataset':[0,0,0,0],'local_contradiction':[-.125,-.1,0,0]}
    for name,scores in score_maps.items():
        exponent=[math.exp((v-max(scores))/.02) for v in scores];total=sum(exponent);probs=[.9*v/total+.1/4 for v in exponent]
        for row,expected in zip(results[name]['variants'],probs):
            error=abs(row['probability']-expected);max_error=max(max_error,error);assert error<1e-12;(checked:=checked+1)
    print(json.dumps({'status':'passed','files':len(manifest['files']),'independent_values':checked,'max_absolute_error':max_error,'model_calls':0,'new_fits':0}))

if __name__=='__main__':main()
