import csv,hashlib,json,shutil,subprocess,tempfile,os,re
from pathlib import Path
A=Path(__file__).resolve().parents[4];SRC=A/'docs/experiments/raw/agent-runtime-adoption-candidate-2026-09-17/adoption-package'
rows=list(csv.DictReader((SRC/'manifest.tsv').open(),delimiter='\t'));deps=list(csv.DictReader((SRC/'dependencies.tsv').open(),delimiter='\t'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def snap(b):return {r['path']:sha(b/r['path']) for r in rows}
def prepare(root):
 b=root/'target';pkg=root/'external-package';shutil.copytree(SRC,pkg);(b/'docs/experiments').mkdir(parents=True)
 for r in rows:
  p=b/r['path'];p.parent.mkdir(parents=True,exist_ok=True)
  if r['op']=='replace':shutil.copy2(pkg/'before'/r['path'],p)
 for d in deps:
  p=b/d['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(A/d['path'],p);assert sha(p)==d['required_sha256']
 return b,pkg
def run(b,pkg,what='apply',args=True,env=None):return subprocess.run(['sh',str(pkg/(what+'.sh'))]+(['--target',str(b)] if args else []),cwd='/',capture_output=True,text=True,env=env)
out={}
with tempfile.TemporaryDirectory() as t:
 for case in ['normal_roundtrip','no_target','after_corrupt','before_corrupt','dep_drift','target_drift','revert_modified','recovery_modified']:
  root=Path(t)/case;b,pkg=prepare(root);initial=snap(b);mode='apply';env=os.environ.copy();tmp=root/'tmp';tmp.mkdir();env['TMPDIR']=str(tmp)
  if case=='after_corrupt':(pkg/'after'/rows[-1]['path']).write_text('bad')
  if case in ['before_corrupt','revert_modified']:
   assert run(b,pkg,env=env).returncode==0;mode='revert'
  if case=='before_corrupt':(pkg/'before'/rows[-1]['path']).write_text('bad')
  if case=='dep_drift':(b/deps[0]['path']).write_text('bad')
  if case=='target_drift':(b/rows[-1]['path']).write_text('changed')
  if case=='revert_modified':(b/rows[-1]['path']).write_text('new user work')
  if case=='recovery_modified':(b/'web/src/pages').chmod(0o500)
  before=snap(b);z=run(b,pkg,mode,case!='no_target',env);after=snap(b)
  result={'rc':z.returncode,'changed_n':sum(after[k]!=v for k,v in before.items())}
  if case=='normal_roundtrip':result['after_matches']=all(sha(b/r['path'])==r['after_sha256'] for r in rows);zz=run(b,pkg,'revert',env=env);result.update(revert_rc=zz.returncode,restored=snap(b)==initial)
  if case=='recovery_modified':
   (b/'web/src/pages').chmod(0o700);rs=list(tmp.glob('adoption-keep-*/restore-partial.sh'));assert len(rs)==1
   victim=b/'src/lei_signal/api/routes/agent.py';victim.write_text('NEW USER EDIT AFTER INTERRUPTED APPLY');saved=sha(victim);zz=subprocess.run(['sh',str(rs[0])],capture_output=True,text=True);result.update(restore_rc=zz.returncode,later_edit_preserved=sha(victim)==saved)
  out[case]=result
print(json.dumps(out,indent=2));Path(__file__).with_name('package-probe-r1-results.json').write_text(json.dumps(out,indent=2)+'\n')
