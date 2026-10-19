"""Run the new gate against bound real inputs; forbid any return computation."""
from pathlib import Path
import datetime as dt
import hashlib,json,sys,time,types
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'src'))
from lei_signal.research.lowfreq_input_guard import guarded_run_study
contract=HERE.parent/'lowfreq-expanded-discovery-2026-10-19/evaluation-input-contract-v2.json'
old=ROOT/'src/lei_signal/research/lowfreq_discovery.py'
old_before=hashlib.sha256(old.read_bytes()).hexdigest()
calls=[]
def forbidden(*args,**kwargs):
 calls.append('called')
 raise AssertionError('statistics executor must not run for bad real input')
sys.modules['lei_signal.research.lowfreq_discovery']=types.SimpleNamespace(run_study=forbidden)
plan=json.loads((HERE/'storage-plan.json').read_text())
never_out=Path(plan['output'])/'must-not-create-performance'
assert not never_out.exists()
started=time.monotonic()
report=guarded_run_study(contract,never_out)
assert report['status']=='blocked'
assert report['blockers']['returned_adjustflag']['by_code']['sz.001914']==1560
assert not calls and not never_out.exists()
assert hashlib.sha256(old.read_bytes()).hexdigest()==old_before
report.update({'at':dt.datetime.now().astimezone().isoformat(),'seconds':time.monotonic()-started,'old_evaluator_sha256':old_before,'contract_sha256':hashlib.sha256(contract.read_bytes()).hexdigest(),'executor_call_count':len(calls),'performance_output_created':never_out.exists(),'new_guard_sha256':hashlib.sha256((ROOT/'src/lei_signal/research/lowfreq_input_guard.py').read_bytes()).hexdigest()})
with (HERE/'actual-600-preflight.json').open('x') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=False))
