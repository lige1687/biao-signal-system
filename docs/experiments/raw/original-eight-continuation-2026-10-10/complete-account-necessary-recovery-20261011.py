"""Create necessary non-overwriting copies and recover in a separate process."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[4];RAW=Path(__file__).parent
core=json.loads((RAW/'complete-account-core-output-plan-20261011.json').read_text())
eng=json.loads((RAW/'complete-account-output-plan-20261011.json').read_text())
startup=json.loads((RAW/'startup-approved-output-plan-20261011.json').read_text())
parent=Path(core['run_directory'])/'recovery-proof'
assert not parent.exists()
assert Path(core['external_mount']).stat().st_dev==core['external_device']
source_paths=[Path(core['output'])/'paired-core-account.json',
Path(core['run_directory'])/'core-stdout-attempt1.log',
Path(core['run_directory'])/'core-stderr-attempt1.log',
Path(core['run_directory'])/'core-exit-code-attempt1.txt',
Path(eng['output'])/'artificial-lifecycle.json',
Path(eng['output'])/'artificial-lifecycle-amended.json',
Path(startup['output'])/'approved-startup-replay.json',
RAW/'complete-account-core-contract-20261011.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stat(p):
    s=p.stat();return {'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'inode':s.st_ino,'device':s.st_dev}
items=[]
(parent/'backup').mkdir(parents=True)
for idx,p in enumerate(source_paths):
    b=parent/'backup'/('%02d-'%idx+p.name)
    assert not b.exists()
    s=stat(p);h=sha(p);shutil.copy2(p,b)
    assert sha(b)==h and p.stat().st_size==b.stat().st_size
    items.append({'source':str(p),'backup':str(b),'restored':str(parent/'restored'/b.name),'sha256':h,'source_stat_before':s})
manifest=parent/'copy-manifest.json'
manifest.write_text(json.dumps({'items':items},ensure_ascii=False,indent=2)+'\n')
child="from pathlib import Path;import json,os,shutil,sys;d=json.loads(Path(sys.argv[1]).read_text());r=Path(d['items'][0]['restored']).parent;r.mkdir();[(shutil.copy2(x['backup'],x['restored'])) for x in d['items']];print(os.getpid())"
child_pid=int(subprocess.check_output([sys.executable,'-c',child,str(manifest)],text=True).strip())
assert child_pid!=os.getpid()
for x in items:
    p,b,r=map(Path,[x['source'],x['backup'],x['restored']])
    assert stat(p)==x['source_stat_before'] and sha(p)==sha(b)==sha(r)==x['sha256']
    assert b.stat().st_size==r.stat().st_size==x['source_stat_before']['bytes']
    assert b.stat().st_dev==r.stat().st_dev==core['external_device']
out={'status':'necessary_new_result_same_device_copy_and_process_recovery_verified',
'items':items,'files_checked':len(items),'bytes_per_set':sum(x['source_stat_before']['bytes'] for x in items),
'controller_pid':os.getpid(),'restore_process_pid':child_pid,'restore_reads_backup_only':True,
'original_paths_and_content_and_stat_unchanged':True,'device':core['external_device'],'uuid':core['external_uuid'],
'actual_three_paths_content_equal':True,'limits':'One healthy physical external disk, two paths and independent process only. Other disk/device failure/other computer recovery not proved.',
'old_recovery_not_recopied':True,'no_deletion_or_migration':True,'additional_historical_paths':0}
q=RAW/'complete-account-necessary-recovery-readback-20261011.json'
q.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='items'},ensure_ascii=False))
