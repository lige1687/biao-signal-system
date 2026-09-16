import json,hashlib,difflib
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
m=json.loads((P/'source-manifest.json').read_text());changed=[];sourcebad=[];diff=[]
for x in m['files']:
 source=Path(x['source']);copy=P/x['copy']
 if sha(source)!=x['sha256']:sourcebad.append(str(source))
 if sha(copy)!=x['sha256']:
  changed.append(x['copy']);diff.extend(difflib.unified_diff(source.read_text().splitlines(True),copy.read_text().splitlines(True),fromfile='original/'+x['copy'],tofile='research/'+x['copy']))
new=['research-package/src/lei_signal/backtest/entry_qualification.py']
for rel in new:diff.extend(difflib.unified_diff([], (P/rel).read_text().splitlines(True),fromfile='/dev/null',tofile='research/'+rel))
(P/'research.patch').write_text(''.join(diff))
counts={}
for folder in ['before-replay16','before-boundaries','after-replay16','after-boundaries']:
 r=json.loads((P/folder/'results.json').read_text());counts[folder]={k:sum(v['status']==k for v in r) for k in sorted({v['status'] for v in r})}
old=P.parents[1]/'research-seventh-2026-09-08/rules-qualification';oldmanifest=json.loads((old/'manifest.json').read_text());oldbad=[x['path'] for x in oldmanifest['files'] if sha(old/x['path'])!=x['sha256']]
pre=json.loads((P/'pre-edit-tests-manifest.json').read_text());testsbad=[x['path'] for x in pre['files'] if sha(P/x['path'])!=x['sha256']]
expected={'research-package/src/lei_signal/backtest/engine.py','research-package/src/lei_signal/rules/dense_breakout.py'}
newruntime={str(p.relative_to(P)) for p in (P/'research-package').rglob('*') if p.is_file()}-{x['copy'] for x in m['files']}
checks={'time_utc':datetime.now(timezone.utc).isoformat(),'source_changes':sourcebad,'prior_sealed_changes':oldbad,'pre_edit_tests_or_protocol_changes':testsbad,'modified_copied_files':changed,'modified_files_exact_authorized_set':set(changed)==expected,'new_runtime_files':sorted(newruntime),'new_runtime_exact_authorized_set':newruntime==set(new),'configuration_unchanged':all(sha(P/x['copy'])==x['sha256'] for x in m['files'] if x['copy'].startswith('research-package/configs/')),'test_counts':counts,'integration_passed':json.loads((P/'integration-check.json').read_text())['passed'],'historical_strategy_runs':0,'production_edits':0,'okr_edits':0}
checks['passed']=not(sourcebad or oldbad or testsbad) and set(changed)==expected and newruntime==set(new) and checks['configuration_unchanged'] and counts['after-replay16']=={'pass':16} and counts['after-boundaries']=={'pass':16} and checks['integration_passed']
write('self-check.json',checks)
write('qualification.json',{'research_implementation_id':'b-research-fix-2026-09-08-v1','name':'修正后的B研究代理','three_specific_fixes_verified':checks['passed'],'complete_B_qualified':False,'nine_conditions_fully_enforced':False,'test_counts':counts,'historical_strategy_runs':0,'performance_verdict':None,'production_changed':False,'config_changed':False,'b3_semantics':'close<breakout_reference AND close<SMA20 AND close<close_lag20; ambush extra SMA20<=SMA60; no EMA slope condition','remaining':['九条完整规则与历史输入未核验','价格同单位转换和真实交易可用性由主研究负责','未修埋伏false→true等其他未授权差异','本次无四基金历史收益结果']})
files=[p for p in sorted(P.rglob('*')) if p.is_file() and p != P/'manifest.json']
write('manifest.json',{'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'research_implementation_id':'b-research-fix-2026-09-08-v1','files':[{'path':str(p.relative_to(P)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]})
print(json.dumps(checks,ensure_ascii=False))
