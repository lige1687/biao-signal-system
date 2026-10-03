from pathlib import Path
import copy,json,hashlib,math
from lei_signal.research.volume_direction_information import build_qualification,prepare_volume_direction_observations
R=Path(__file__).resolve().parents[4];N=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
c=json.loads((N/'draft-main.json').read_text());data=json.loads((R/c['data']['path']).read_text())
qualification=build_qualification(data,c,R);put(N/'qualification.json',qualification)
rows=prepare_volume_direction_observations(data,c,compute_labels=False)['observations'];bykey={(r['asset'],r['date']):r for r in data['bars']};index={d:i for i,d in enumerate(data['calendar'])};errs=[];signerrs=[];checked=0
for r in rows:
 if not r['eligible']:continue
 i=index[r['date']];ds=data['calendar'][i-20:i+1];pr=[bykey[(r['asset'],d)]['close'] for d in ds];vv=[bykey[(r['asset'],d)]['volume'] for d in ds[1:]]
 signs=[int(b>a)-int(b<a) for a,b in zip(pr,pr[1:])]
 direction=sum(signs)/20;expected=(sum(v for s,v in zip(signs,vv) if s>0)-sum(v for s,v in zip(signs,vv) if s<0))/sum(vv)-direction
 errs.append(abs(expected-r['features']['direction_excess20']));signerrs.append(abs(direction-r['features']['direction20']));checked+=1
assert checked>3000 and max(errs)<1e-12 and max(signerrs)<1e-12
put(N/'controller-formula-check.json',{'independent_method':'direct up-volume sum minus down-volume sum divided by total, minus direct direction count; no adapter formula reused','rows':checked,'max_error':max(errs),'max_direction_error':max(signerrs),'future_outcomes_used':False,'source_qualification_verified':True})
for mode in ['main','solo']:
 p=N/f'draft-{mode}.json';d=json.loads(p.read_text());d['research_design']['sample_fit'].update(qualification_sha256=sha(N/'qualification.json'),observations=qualification['counts']['observations'],dates=qualification['counts']['dates']);put(p,d)
print(json.dumps(qualification['scientific_support'],ensure_ascii=False,indent=2))
