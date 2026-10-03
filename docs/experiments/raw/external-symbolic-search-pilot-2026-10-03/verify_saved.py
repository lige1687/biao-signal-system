"""Independent saved-result arithmetic. Does not import run.py or DEAP or fit."""
import ast
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent

def scalar_expression(text, row):
    def visit(n):
        if isinstance(n, ast.Name) and n.id in ('x0','x1','x2','x3'):
            return float(row[int(n.id[1])])
        if isinstance(n, ast.Constant) and type(n.value) is float and n.value == 1.0:
            return 1.0
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name) or len(n.args)!=2 or n.keywords:
            raise ValueError('unaccepted expression')
        a,b=map(visit,n.args)
        if n.func.id=='add': return a+b
        if n.func.id=='sub': return a-b
        if n.func.id=='mul': return a*b
        if n.func.id=='protected_divide': return a/b if abs(b)>1e-6 else 1.0
        raise ValueError('unaccepted function')
    return visit(ast.parse(text,mode='eval').body)

def main():
    p=json.loads((HERE/'protocol.json').read_text())
    results=json.loads((HERE/'core/results.json').read_text())
    saved=json.loads((HERE/'core/predictions.json').read_text())
    hashes=json.loads((HERE/'core/input-fingerprints.json').read_text())
    by_key={(r['task'],r['seed'],r['arm']):r for r in saved['runs']}
    datasets={}
    for split,seed in p['data']['seeds'].items():
        rng=np.random.default_rng(seed);n=p['data']['rows'][split]
        if split=='outside_range':
            rows=[]
            while len(rows)<n:
                block=rng.uniform(-4,4,size=(n,4))
                rows.extend(row for row in block if max(abs(v) for v in row)>2)
            x=np.array(rows[:n])
        else:
            x=rng.uniform(-2,2,size=(n,4))
        for index,task in enumerate(('additive','rational','noise')):
            gen=np.random.default_rng(seed+991+index*10000)
            if task=='additive': y=x[:,0]+2*x[:,1]-x[:,2]+gen.normal(0,0.05,n)
            elif task=='rational': y=x[:,0]/(1+x[:,1]*x[:,1])+x[:,2]+gen.normal(0,0.05,n)
            else: y=gen.normal(0,1,n)
            for name,arr in [('x',x),('y',y)]:
                assert hashlib.sha256(np.array(arr,dtype='<f8').tobytes()).hexdigest()==hashes[split][task][name+'_sha256']
            datasets[(split,task)]=(x,y)
    max_pred=max_metric=0.0;checked=0
    for r in results['runs']:
        a=by_key[(r['task'],r['seed'],r['arm'])]
        for split in p['data']['seeds']:
            x,y=datasets[(split,r['task'])];prediction=[]
            for row in x:
                if r['arm']=='direct_baseline':
                    m=r['model'];terms=[1.0]
                    for s in m['specs']:
                        if s['kind']=='monomial': terms.append(math.prod(float(v)**k for v,k in zip(row,s['powers'])))
                        else: terms.append(float(row[s['i']])/(1+float(row[s['j']])**2))
                    value=math.fsum(t*c for t,c in zip(terms,m['coefficients']))
                else: value=scalar_expression(r['expression'],row)
                prediction.append(value)
            delta=max(abs(v-w) for v,w in zip(prediction,a['outputs'][split]));max_pred=max(max_pred,delta)
            assert delta<1e-10
            metric=math.fsum((float(v)-w)**2 for v,w in zip(y,prediction))/len(y)
            max_metric=max(max_metric,abs(metric-r['mse'][split]));assert math.isclose(metric,r['mse'][split],rel_tol=1e-10,abs_tol=1e-10);checked+=1
    direct={r['task']:r for r in results['runs'] if r['arm']=='direct_baseline' and r['seed']==17}
    passes={};additive_safe=0
    for task in ('additive','rational'):
        records=[r for r in results['runs'] if r['arm']=='external' and r['task']==task]
        passes[task]=sum(all(r['mse'][s]<=0.9*direct[task]['mse'][s] for s in ['test','outside_range']) for r in records)
        if task=='additive': additive_safe=sum(all(r['mse'][s]<=1.1*direct[task]['mse'][s] for s in ['test','outside_range']) for r in records)
    table=[]
    for task in ('additive','rational','noise'):
        for arm in ('direct_baseline','random_control','external'):
            rows=[r for r in results['runs'] if r['task']==task and r['arm']==arm]
            table.append({'task':task,'arm':arm,'test_mse_mean':math.fsum(r['mse']['test'] for r in rows)/len(rows),'outside_mse_mean':math.fsum(r['mse']['outside_range'] for r in rows)/len(rows),'wall_seconds_total':math.fsum(r['wall_seconds'] for r in rows)})
    assert sum(r['evaluation_count'] for r in results['runs'])==57600
    assert sum(r.get('fit_count',0) for r in results['runs'])==18
    answer={'status':'verified','independent_score_checks':checked,'independent_input_hashes':24,'max_prediction_difference':max_pred,'max_metric_difference':max_metric,'accuracy_pass_seeds_of_3':passes,'additive_no_material_degradation_seeds':additive_safe,'accuracy_adoption_pass':any(v>=2 for v in passes.values()) and additive_safe>=2,'noise_promoted':False,'table':table,'additional_searches':0,'additional_fits':0}
    print(json.dumps(answer,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
