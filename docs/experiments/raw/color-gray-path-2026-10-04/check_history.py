import json, math, hashlib
from pathlib import Path
from lei_signal.research.color_history_information import history_rows
root=Path(__file__).resolve().parents[4];here=Path(__file__).resolve().parent
p=root/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json'; data=json.loads(p.read_text()); actual={(r['asset'],r['date']):r for r in history_rows(data)}
checks=0; gray=0
for a in sorted({b['asset'] for b in data['bars']}):
 bars=sorted([b for b in data['bars'] if b['asset']==a],key=lambda r:r['date']); prices=[b['close'] for b in bars]; emas={}
 for n in [20,60]:
  arr=[None]*len(prices);arr[n-1]=sum(prices[:n])/n
  for i in range(n,len(prices)):arr[i]=arr[i-1]+2/(n+1)*(prices[i]-arr[i-1])
  emas[n]=arr
 last=None;prev=None;origin=None;age=0
 for i,b in enumerate(bars):
  if i<251:continue
  p=prices[i];e=emas[20][i];lag=prices[i-20]
  color='green' if p>e and p>lag else 'black' if p<e and p<lag else 'gray'
  group='bull' if min(sum(prices[i-19:i+1])/20,e)>max(sum(prices[i-59:i+1])/60,emas[60][i]) else 'bear' if max(sum(prices[i-19:i+1])/20,e)<min(sum(prices[i-59:i+1])/60,emas[60][i]) else 'overlap'
  if color=='gray':
   if prev!='gray':origin=last;age=1
   else:age+=1
  else:last=color;origin=None;age=0
  r=actual[a,b['date']]; assert r['color20']==color and r['group']==group,(a,b['date'])
  assert r['gray_origin']==origin and r['gray_age']==(age if color=='gray' else None)
  assert abs(r['distance_to_ema20']-100*(p/e-1))<1e-9
  prev=color;checks+=5;gray+=int(group=='bull' and color=='gray' and origin is not None)
result={'independent_checks':checks,'eligible_bull_gray':gray,'future_labels_used':False,'method':'direct scalar SMA-seeded EMA and strict colors; independent origin loop from first qualified row','panel_sha256':hashlib.sha256((root/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json').read_bytes()).hexdigest()}
(here/'history-independent-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
