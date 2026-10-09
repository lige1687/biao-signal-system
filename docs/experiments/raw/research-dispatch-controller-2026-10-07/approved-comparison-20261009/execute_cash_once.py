"""Controller-only fixed-budget driver; requires independently accepted release."""
import sys,json,hashlib,importlib.util,os,traceback
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
BASE=Path(__file__).resolve().parent
SOURCE=ROOT/'.codex/worktrees/research-direct-20261008/docs/experiments/raw/risk-comparable-cash-baseline-2026-10-09'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def open_external_result(plan):
    mount=Path(plan['external_mount']); base=Path(plan['run_directory']).parent.parent
    if not mount.is_mount() or mount.stat().st_dev!=plan['external_device']:raise RuntimeError('external mount lost')
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    fds=[]
    try:
        basefd=os.open(base,flags);fds.append(basefd)
        if os.fstat(basefd).st_dev!=plan['external_device']:raise RuntimeError('external base device changed')
        task=Path(plan['run_directory']).parent.name; run=Path(plan['run_directory']).name
        try:os.mkdir(task,dir_fd=basefd)
        except FileExistsError:pass
        taskfd=os.open(task,flags,dir_fd=basefd);fds.append(taskfd)
        if os.fstat(taskfd).st_dev!=plan['external_device']:raise RuntimeError('external task device changed')
        os.mkdir(run,dir_fd=taskfd)
        runfd=os.open(run,flags,dir_fd=taskfd);fds.append(runfd)
        if os.fstat(runfd).st_dev!=plan['external_device']:raise RuntimeError('external run device changed')
        os.mkdir('result',dir_fd=runfd)
        outfd=os.open('result',flags,dir_fd=runfd);fds.append(outfd)
        if os.fstat(outfd).st_dev!=plan['external_device']:raise RuntimeError('external result device changed')
        return fds,outfd
    except BaseException:
        for fd in reversed(fds):os.close(fd)
        raise

def main():
    release=json.loads((BASE/'cash-execution-release.json').read_text())
    if release['status']!='accepted_for_one_batch_two_paths':raise RuntimeError('no accepted release')
    for path,expected in release['fixed_files'].items():
        if sha(Path(path))!=expected:raise RuntimeError('fixed source mismatch: '+path)
    plan=json.loads((BASE/'risk-comparable-cash-baseline-20261009-output-plan.json').read_text())
    sys.path.insert(0,str(ROOT/'src'))
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(ROOT,plan,plan['task_id'],plan['estimated_bytes'],internal_bytes=plan['internal_metadata_bytes'])
    attempt={'started_at':stamp(),'status':'started','batch_attempt':1,'reserved_new_paths':2,'old_A_replays':0,'plan':plan['output'],'release_sha256':sha(BASE/'cash-execution-release.json')}
    with (BASE/'cash-real-attempt.json').open('x') as f:json.dump(attempt,f,ensure_ascii=False,indent=2)
    out=Path(plan['output']);fds=[]
    try:
        fds,outfd=open_external_result(plan)
        spec=importlib.util.spec_from_file_location('cash_comparator_frozen',SOURCE/'comparator.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        result=mod.compute_historical_in_memory(ROOT,json.loads((SOURCE/'source-manifest.json').read_text()))
        # Check device is still the planned external device before durable result writes.
        if not Path(plan['external_mount']).is_mount() or os.fstat(outfd).st_dev!=plan['external_device']:raise RuntimeError('external device lost')
        data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        fd=os.open('result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=outfd)
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        rd=os.open('result.json',os.O_RDONLY|os.O_NOFOLLOW,dir_fd=outfd)
        with os.fdopen(rd,'rb') as f:readback=f.read()
        result_hash=hashlib.sha256(readback).hexdigest()
        if result_hash!=hashlib.sha256(data).hexdigest():raise RuntimeError('result readback mismatch')
        attempt.update(status='executed_pending_independent_acceptance',completed_at=stamp(),result_sha256=result_hash,result_bytes=len(data),result_path=str(out/'result.json'))
    except BaseException as e:
        attempt.update(status='failed_no_automatic_retry',failed_at=stamp(),error=repr(e),traceback=traceback.format_exc())
        raise
    finally:
        for fd in reversed(fds):os.close(fd)
        (BASE/'cash-real-attempt.json').write_text(json.dumps(attempt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in attempt.items() if k!='traceback'},ensure_ascii=False))
if __name__=='__main__':main()
