import subprocess,json,hashlib,pathlib
R=pathlib.Path('/Users/yongbiaoli/Desktop/lei-signal-lab'); D=pathlib.Path('/Users/yongbiaoli/lei-agent-ux-20260913'); O=R/'docs/experiments/raw/agent-runtime-integration-2026-09-15'
def git(*args): return subprocess.check_output(['git','-C',str(D),*args])
def sha(b):return hashlib.sha256(b).hexdigest() if b is not None else None
paths=set(git('diff','a61fc671','--name-only','--','src','tests','web').decode().splitlines())|set(git('ls-files','--others','--exclude-standard','--','src','tests','web').decode().splitlines())
rows=[]
for f in sorted(paths):
 bproc=subprocess.run(['git','-C',str(D),'show','a61fc671:'+f],capture_output=True);base=bproc.stdout if bproc.returncode==0 else None
 ours=(R/f).read_bytes() if (R/f).exists() else None;theirs=(D/f).read_bytes() if (D/f).exists() else None
 for kind,value in [('base',base),('before',ours),('developer',theirs)]:
  if value is not None:
   p=O/kind/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
 if ours==theirs: state='already_same'; merged=ours
 elif ours==base:state='take_developer';merged=theirs
 elif theirs==base:state='keep_runtime';merged=ours
 elif base is not None and ours is not None and theirs is not None:
  p=subprocess.run(['git','merge-file','-p',str(O/'before'/f),str(O/'base'/f),str(O/'developer'/f)],capture_output=True)
  state='merge_clean' if p.returncode==0 else 'conflict';merged=p.stdout
 else:state='conflict_add_delete';merged=None
 if merged is not None:
  p=O/'candidate'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(merged)
 rows.append({'path':f,'status':state,'base_sha':sha(base),'runtime_sha':sha(ours),'developer_sha':sha(theirs),'candidate_sha':sha(merged)})
(O/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(json.dumps(rows,ensure_ascii=False,indent=2))
