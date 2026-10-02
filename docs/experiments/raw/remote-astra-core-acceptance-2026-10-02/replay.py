"""Controller replay logger; executes only the explicitly supplied delivery script in its isolated checkout."""
from pathlib import Path
import sys, os, json, subprocess, hashlib, time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CHECKOUT=ROOT/'.biao/remote-astra-acceptance-20261002/checkout'
label, script, *args=sys.argv[1:]
assert '/' not in label and '..' not in label
src=(CHECKOUT/script).resolve(); assert src.is_relative_to(CHECKOUT) and src.is_file()
out=HERE/'runs'/label;out.mkdir(parents=True,exist_ok=False)
tmp=ROOT/'.biao/remote-astra-acceptance-20261002/tmp'/label;tmp.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(CHECKOUT/'src'),TMPDIR=str(tmp))
before={str(p.relative_to(CHECKOUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src.parent.rglob('*') if p.is_file() and '.git' not in p.parts}
cmd=[sys.executable,'-B',str(src),*args]
if label == 't5-counterexamples':
 # The delivered script hard-codes /tmp/t5-work and removes it. Keep its
 # scratch writes within this repository; do not edit its source or inputs.
 assert src.name == 'check_counterexamples.py' and not args
 runner="from pathlib import Path; import runpy,sys; ns=runpy.run_path(sys.argv[1],run_name='acceptance_t5'); ns['main'].__globals__['TMP']=Path(sys.argv[2]); ns['main']()"
 cmd=[sys.executable,'-B','-c',runner,str(src),str(tmp/'t5-work')]
start=time.time()
with (out/'run.log').open('w') as log:
 proc=subprocess.run(cmd,cwd=CHECKOUT,env=env,stdout=log,stderr=subprocess.STDOUT)
comparisons=[]
for p in src.parent.rglob('*'):
 if not p.is_file() or p.suffix not in ('.json','.jsonl'):continue
 rel=str(p.relative_to(CHECKOUT));now=p.read_bytes();old=subprocess.run(['git','show','HEAD:'+rel],cwd=CHECKOUT,capture_output=True)
 comparisons.append(dict(path=rel,sha256=hashlib.sha256(now).hexdigest(),matches_committed_bytes=(old.returncode==0 and old.stdout==now),before_sha256=before.get(rel)))
 if old.returncode==0 and old.stdout!=now:
  dest=out/p.name;dest.write_bytes(now)
record=dict(label=label,command=cmd,cwd=str(CHECKOUT),exit_code=proc.returncode,elapsed_seconds=round(time.time()-start,3),files=comparisons)
(out/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))
print((out/'run.log').read_text()[-4500:])
sys.exit(proc.returncode)
