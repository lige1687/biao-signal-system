import csv,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]/'agent-runtime-adoption-candidate-2026-09-17/adoption-package'
rows=list(csv.DictReader((SRC/'manifest.tsv').open(),delimiter='\t'))
print('columns',list(rows[0]))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def prepare(base):
 pkg=base/'docs/experiments/raw/agent-runtime-adoption-candidate-2026-09-17/adoption-package';shutil.copytree(SRC,pkg)
 for r in rows:
  f=r['path'];p=base/f
  if r['op']=='replace':p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(pkg/'before'/f,p)
 return pkg
def snap(b):return {r['path']:sha(b/r['path']) for r in rows}
out={}
with tempfile.TemporaryDirectory() as t:
 root=Path(t)
 for case in ['normal','target_drift','payload_corrupt','dependency_drift','wrong_cwd']:
  b=root/case;pkg=prepare(b);cwd=b
  if case=='target_drift':(b/rows[-1]['path']).write_text('drift')
  if case=='payload_corrupt':(pkg/'after'/rows[-1]['path']).write_text('corrupt payload')
  if case=='dependency_drift':
   p=b/'src/lei_signal/copilot/trades.py';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# incompatible prerequisite')
  if case=='wrong_cwd':cwd=root/'intended-target';cwd.mkdir()
  before=snap(b);z=subprocess.run(['sh',str(pkg/'apply.sh')],cwd=cwd,capture_output=True,text=True)
  out[case]={'exit':z.returncode,'changed':[f for f,h in before.items() if sha(b/f)!=h],'tail':(z.stdout+z.stderr)[-250:]}
print(json.dumps(out,indent=2));Path(__file__).with_name('package-probe-results.json').write_text(json.dumps(out,indent=2)+'\n')
