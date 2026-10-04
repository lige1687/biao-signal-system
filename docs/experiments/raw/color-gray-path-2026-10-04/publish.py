import json,subprocess,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];records=[]
env={**os.environ,'PYTHONPATH':'src','DYLD_LIBRARY_PATH':'/opt/homebrew/lib/python3.11/site-packages/torch/lib'};py=str(HERE/'.venv.local/bin/python')
for group in ['core','continuous']:
 for branch in ['ridge-forward_return','ridge-mae','lightgbm-forward_return','lightgbm-mae']:
  d=HERE/group/branch;c=json.loads((d/'draft.json').read_text());c['publication']['conclusion']='not_supported' if group=='core' and branch=='lightgbm-forward_return' else 'insufficient'
  c['question']['baseline']='B0=各ETF等总权重的成熟训练整体均值；B1=冻结字段；辅助ETF_mean=每只ETF自身成熟均值，辅助结果独立表列出'
  c['controller_review']['conclusion_scope']['reason']='历史同条件预测比较；报告证据不足或本范围未发现增量。小改善不等于赢过更强简单基线；完整账户/真正未见证据未覆盖'
  draft=d/'accepted-draft.json';draft.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
  commands=[([py,'scripts/run_factor_lab.py','--workflow-draft',str(draft),'--out',str(d/'accepted-freeze')],d/'accepted-freeze.log'),([py,'scripts/run_factor_lab.py','--workflow-contract',str(d/'accepted-freeze/contract.json'),'--out',str(d/'accepted-01'),'--reuse-predictions',str(d/'core-01'),'--register-report'],d/'accepted-01.log')]
  for cmd,log in commands:
   with log.open('x') as f:p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
   records.append({'branch':group+'/'+branch,'command':cmd,'exit_code':p.returncode});(HERE/'publication-ledger.json').write_text(json.dumps(records,indent=2)+'\n')
   if p.returncode:print(log.read_text()[-5000:]);raise SystemExit(p.returncode)
  r=json.loads((d/'accepted-01/result.json').read_text());assert r['execution']['fits']==0;print(group,branch,'registered zero fits',flush=True)
