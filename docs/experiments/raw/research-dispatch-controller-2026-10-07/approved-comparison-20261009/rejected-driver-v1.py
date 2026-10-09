"""Controller-only fixed-budget driver; requires independently accepted release."""
import sys,json,hashlib,importlib.util,os,traceback
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
BASE=Path(__file__).resolve().parent
SOURCE=ROOT/'.codex/worktrees/research-direct-20261008/docs/experiments/raw/risk-comparable-cash-baseline-2026-10-09'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
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
    out=Path(plan['output']);out.mkdir(parents=True,exist_ok=False)
    try:
        spec=importlib.util.spec_from_file_location('cash_comparator_frozen',SOURCE/'comparator.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        result=mod.compute_historical_in_memory(ROOT,json.loads((SOURCE/'source-manifest.json').read_text()))
        # Check device is still the planned external device before durable result writes.
        if not Path(plan['external_mount']).is_mount() or out.stat().st_dev!=plan['external_device']:raise RuntimeError('external device lost')
        data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with (out/'result.json').open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        if sha(out/'result.json')!=hashlib.sha256(data).hexdigest():raise RuntimeError('result readback mismatch')
        attempt.update(status='executed_pending_independent_acceptance',completed_at=stamp(),result_sha256=sha(out/'result.json'),result_bytes=len(data),result_path=str(out/'result.json'))
    except BaseException as e:
        attempt.update(status='failed_no_automatic_retry',failed_at=stamp(),error=repr(e),traceback=traceback.format_exc())
        raise
    finally:
        (BASE/'cash-real-attempt.json').write_text(json.dumps(attempt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in attempt.items() if k!='traceback'},ensure_ascii=False))
if __name__=='__main__':main()
