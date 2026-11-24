from pathlib import Path
import json,statistics,math
ROOT=Path(__file__).resolve().parents[4];p=Path(json.loads((ROOT/'docs/ops/breadth-reading-aid-20261101/live-refresh-v15/storage-plan.json').read_text())['output'])/'us-sigma-efficacy-v16'
snapshot=json.loads((ROOT/'docs/ops/breadth-reading-aid-20261101/us-sigma-yields-v13/overlay-snapshot.json').read_text())['series']['sp500'];dates=snapshot['dates'];values=snapshot['values'];ix={d:i for i,d in enumerate(dates)}
events=json.loads((p/'events.json').read_text());results=json.loads((p/'results.json').read_text());verified=[]
for sigma in [1.5,2]:
 for kind in ['upper','lower']:
  key=f'{sigma:g}:{kind}:63';r=results[key];base=[]
  def state(i):return ('above' if values[i]>statistics.mean(values[i-199:i+1]) else 'at_or_below')+(':'+('positive' if values[i]>values[i-63] else 'negative' if values[i]<values[i-63] else 'zero'))
  for i in range(199,len(values)-64):base.append((state(i),(values[i+64]/values[i+1]-1)*100))
  assert len(base)==r['eligible_baseline_days']
  bmeans={s:statistics.mean(v for a,v in base if a==s) for s,_ in base}
  eligible=[e for e in events if e['sigma']==sigma and e['kind']==kind and e.get('feature_eligible')]
  keep=[];last=-100000
  for e in eligible:
   i=ix[e['date']]
   if i-last<63:continue
   last=i
   if i+64<len(values):keep.append((e,i))
  returns=[(values[i+64]/values[i+1]-1)*100 for e,i in keep];worst=[min(0,min(values[i+2:i+65])/values[i+1]-1)*100 for e,i in keep]
  expected=r['cooldown'];mean=statistics.mean(returns);baseline=statistics.mean(bmeans[state(i)] for e,i in keep)
  assert len(keep)==expected['performance']['n']
  assert abs(mean-expected['performance']['mean_return_pct'])<1e-10
  assert abs(baseline-expected['conditional']['mean_return_pct'])<1e-10
  assert abs(statistics.mean(worst)-expected['performance']['mean_worst_loss_pct'])<1e-10
  verified.append({'key':key,'n':len(keep),'mean':mean,'conditional':baseline,'difference':mean-baseline,'dates':[e['date'] for e,i in keep]})
(ROOT/'docs/ops/breadth-reading-aid-20261101/us-sigma-efficacy-v16/root-arithmetic-acceptance.json').write_text(json.dumps({'status':'accepted','groups':verified,'method':'Independent direct index slicing and simple conditional state means; no model fitting, parameter change or core rerun. Event identity independently compared to production TypeScript separately.'},ensure_ascii=False,indent=2));print(verified)
