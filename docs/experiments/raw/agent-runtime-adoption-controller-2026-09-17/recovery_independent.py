"""Independent temp-only probes; chmod simulates write failure, no production DB/network."""
import csv, hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path
A=Path(__file__).resolve().parents[4]
P=A/'docs/experiments/raw/agent-runtime-adoption-candidate-2026-09-17/adoption-package'
rows=list(csv.DictReader((P/'manifest.tsv').open(),delimiter='\t'))
deps=list(csv.DictReader((P/'dependencies.tsv').open(),delimiter='\t'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def snap(b):return {r['path']:sha(b/r['path']) for r in rows}
def init(root):
 b=root/'target';pkg=root/'package';tmp=root/'tmp';tmp.mkdir(parents=True);shutil.copytree(P,pkg);(b/'docs/experiments').mkdir(parents=True)
 for r in rows:
  f=b/r['path'];f.parent.mkdir(parents=True,exist_ok=True)
  if r['op']=='replace':shutil.copy2(pkg/'before'/r['path'],f)
 for r in deps:
  f=b/r['path'];f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(A/r['path'],f);assert sha(f)==r['required_sha256']
 return b,pkg,tmp,dict(os.environ,TMPDIR=str(tmp))
def call(cmd,env):return subprocess.run(cmd,cwd='/',env=env,text=True,capture_output=True)
results={}
with tempfile.TemporaryDirectory() as top:
 for scenario in ['apply_clean','apply_later_edit','apply_backup_corrupt','apply_restore_write_fail','revert_clean','revert_later_edit']:
  b,pkg,tmp,env=init(Path(top)/scenario);initial=snap(b);mode='revert' if scenario.startswith('revert') else 'apply'
  if mode=='revert':
   z=call(['sh',str(pkg/'apply.sh'),'--target',str(b)],env);assert z.returncode==0,z.stdout+z.stderr
  expected_restored=snap(b);blocked=b/'web/src/pages';blocked.chmod(0o500)
  try:z=call(['sh',str(pkg/(mode+'.sh')),'--target',str(b)],env)
  finally:blocked.chmod(0o700)
  recoveries=list(tmp.glob('**/restore-partial.sh'));assert z.returncode!=0 and len(recoveries)==1,(scenario,z.stdout,z.stderr,recoveries)
  restore=recoveries[0];victim=b/'src/lei_signal/api/routes/agent.py'
  if scenario.endswith('later_edit'):victim.write_text('new user edit after interrupted operation\n')
  if scenario.endswith('backup_corrupt'):
   backups=list(restore.parent.glob('**/agent.py'));assert backups;backups[0].write_text('damaged backup\n')
  perm=None
  if scenario.endswith('restore_write_fail'):perm=b/'src/lei_signal/api/routes';perm.chmod(0o500)
  before=snap(b)
  try:zz=call(['sh',str(restore)],env)
  finally:
   if perm:perm.chmod(0o700)
  after=snap(b)
  good=(zz.returncode==0 and after==expected_restored) if scenario.endswith('clean') else (zz.returncode!=0 and (after==before if not scenario.endswith('write_fail') else True))
  results[scenario]={'pass':good,'operation_exit':z.returncode,'recovery_exit':zz.returncode,'modified_by_recovery':sum(before[k]!=after[k] for k in before),'recovery_output':(zz.stdout+zz.stderr)[-1200:]}
print(json.dumps(results,ensure_ascii=False,indent=2));Path(__file__).with_name('recovery-independent-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
raise SystemExit(0 if all(r['pass'] for r in results.values()) else 1)
