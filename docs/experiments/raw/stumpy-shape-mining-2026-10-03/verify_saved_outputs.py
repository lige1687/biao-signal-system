import os,subprocess,json,time,shutil
from pathlib import Path
import numpy as np
root=Path.cwd();local=root/'.biao/external-shape-mining-20261003';raw=root/'docs/experiments/raw/stumpy-shape-mining-2026-10-03';results=[]
def run(cmd,cwd=root,env=None):
 t=time.monotonic();p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True);results.append({'command':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-t,'stdout':p.stdout,'stderr':p.stderr});(raw/'final-validation.json').write_text(json.dumps(results,indent=2));assert p.returncode==0,p.stderr
run(['python3','-m','pytest','tests/unit/test_shape_mining.py','-q'])
run(['python3',str(raw/'run_probe.py'),'--root',str(root),'--local-output',str(local/'probe-real'),'--resume'])
# Independent numeric oracle on every saved complete post-discovery observation.
checked=0;max_error=0
for base in [raw/'probe/synthetic',raw/'probe/noise',local/'probe-real/real']:
 data=json.loads((base/'input.json').read_text());bank=json.loads((base/'discover/library.json').read_text());obs=json.loads((base/'apply/observations.json').read_text());x=np.log(data['close'])
 for i,row in enumerate(obs['rows']):
  for c in bank['candidates']:
   actual=row['distances'][c['candidate_id']]
   if actual is None:continue
   a=np.array(c['template']);b=x[i-19:i+1];expected=np.linalg.norm((a-a.mean())/a.std()-(b-b.mean())/b.std());err=abs(actual-expected);assert err<1e-6,(i,err);max_error=max(max_error,err);checked+=1
fresh=local/'fresh-recovery';fresh.mkdir();shutil.copy2(root/'src/lei_signal/research/shape_mining.py',fresh/'shape_mining.py');shutil.copy2(raw/'probe/synthetic/input.json',fresh/'input.json');shutil.copy2(raw/'probe/synthetic/discover/library.json',fresh/'library.json')
run(['python3','shape_mining.py','apply','--input','input.json','--library','library.json','--output','result'],cwd=fresh)
assert json.loads((fresh/'result/observations.json').read_text())==json.loads((raw/'probe/synthetic/apply/observations.json').read_text())
(raw/'independent-validation.json').write_text(json.dumps({'followup_batch':3,'checked_distances':checked,'max_absolute_error':max_error,'fresh_directory_saved_bank_application':'passed','no_discovery_refit':True,'platform':'macOS arm64 only','financial_increment':'unmeasured'},indent=2)+'\n')
print('PASS',checked,max_error)
