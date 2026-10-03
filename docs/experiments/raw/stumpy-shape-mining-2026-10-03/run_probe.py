"""Fixed engineering probe. Real prices and outputs remain in --local-output."""
import argparse, hashlib, json, os, subprocess, sys, time
from datetime import date, timedelta
from pathlib import Path
import numpy as np


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--local-output',type=Path,required=True);ap.add_argument('--resume',action='store_true')
    a=ap.parse_args(); root=a.root.resolve(); local=a.local_output.resolve();local.mkdir(parents=True,exist_ok=a.resume)
    raw=Path(__file__).resolve().parent
    dates=[(date(2020,1,1)+timedelta(days=i)).isoformat() for i in range(240)]
    logs=4+np.random.default_rng(420).normal(0,.01,240)
    shape=np.array([0,.1,.4,.2,-.1,-.4,-.2,.3,.5,.1,-.3,-.5,-.2,.2,.7,.4,.1,-.2,.1,.6])
    for start in [5,60,110,170,215]:logs[start:start+20]=4+.02*shape
    cases=[('synthetic',{'asset':'synthetic','dates':dates,'close':np.exp(logs).tolist()},dates[159]),('noise',{'asset':'noise','dates':dates,'close':np.exp(4+np.random.default_rng(421).normal(0,.01,240)).tolist()},dates[159])]
    source=root/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b'
    panel=json.loads(source.read_text());cal=[d for d in panel['calendar'] if '2022-01-04'<=d<='2026-06-30']
    bars=[b for b in panel['bars'] if b['asset']=='510300.SS' and '2022-01-04'<=b['date']<='2026-06-30']
    assert [b['date'] for b in bars]==cal and len(set(cal))==len(cal)
    assert all(b['action_known'] and b['status']=='quoted' for b in bars)
    cases.append(('real',{'asset':'510300.SS','dates':cal,'close':[b['close'] for b in bars]},'2024-12-31'))
    receipt={'followup_batch':3 if a.resume else 2,'financial_fits':0,'financial_increment':'unmeasured','cases':{}}
    for name,data,end in cases:
        base=local/name if name=='real' else raw/'probe'/name
        inp=base/'input.json';save(inp,data);commands=[]
        for mode in ['discover','apply']:
            cmd=[sys.executable,'-m','lei_signal.research.shape_mining',mode,'--input',str(inp),'--output',str(base/mode)]
            cmd+=['--discovery-end',end] if mode=='discover' else ['--library',str(base/'discover/library.json')]
            saved=base/mode/('library.json' if mode=='discover' else 'observations.json')
            if a.resume and saved.exists():
                commands.append({'command':cmd,'status':'reused saved output from followup2; not rerun'})
                continue
            start=time.monotonic();p=subprocess.run(cmd,cwd=root,capture_output=True,text=True)
            commands.append({'command':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-start,'stdout':p.stdout,'stderr':p.stderr})
            if p.returncode:save(local/'failure.json',commands);raise RuntimeError(p.stderr)
        bank=json.loads((base/'discover/library.json').read_text());obs=json.loads((base/'apply/observations.json').read_text())
        vals=[v for r in obs['rows'] for v in r['distances'].values() if v is not None]
        receipt['cases'][name]={'rows':len(data['dates']),'coverage':bank['coverage'],'occurrences':[len(c['occurrences']) for c in bank['candidates']],'non_null_distances':len(vals),'distance_min':min(vals) if vals else None,'distance_max':max(vals) if vals else None,'commands':commands,'artifacts':[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'delivered_in_git':name!='real'} for p in [inp,base/'discover/library.json',base/'apply/observations.json']]}
    save(raw/'probe-summary.json',receipt)
    print(json.dumps({k:{x:v[x] for x in ['rows','coverage','occurrences','non_null_distances']} for k,v in receipt['cases'].items()}))

if __name__=='__main__':main()
