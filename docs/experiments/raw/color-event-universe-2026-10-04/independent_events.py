"""Independent standard-library event calculation, without future outcomes."""
import collections
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent

def color(c,e,lag):
    return 'green' if c>e and c>lag else 'black' if c<e and c<lag else 'gray'

def main():
    path=ROOT/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json'
    p=json.loads(path.read_text()); cal=p['calendar']; dates={d:i for i,d in enumerate(cal)}
    bars={(r['asset'],r['date']):r for r in p['bars']}
    assets=sorted({r['asset'] for r in p['bars']}); results=[]
    for a in assets:
        history=[]; daily={}; ema={20:None,60:None}
        for d in cal:
            r=bars.get((a,d),{})
            if r.get('status')!='quoted' or r.get('action_known') is not True:
                history=[]; ema={20:None,60:None};continue
            c=float(r['close']);history.append(c);n=len(history)
            for k in ema:
                if n==k:ema[k]=sum(history)/k
                elif n>k:ema[k]=2/(k+1)*c+(1-2/(k+1))*ema[k]
            if n>=252:
                daily[d]={'color':color(c,ema[20],history[-21]),
                          'bull_group': min(sum(history[-20:])/20,ema[20])>max(sum(history[-60:])/60,ema[60])}
        weeks=[]
        for d in cal:
            week=datetime.date.fromisoformat(d).isocalendar()[:2]
            if not weeks or weeks[-1][0]!=week:weeks.append((week,[]))
            weeks[-1][1].append(d)
        wh=[];we=None;available={}
        for j,(week,ds) in enumerate(weeks[:-1]):
            valid=all(bars.get((a,d),{}).get('status')=='quoted' and bars.get((a,d),{}).get('action_known') is True for d in ds)
            if j==0 and datetime.date.fromisoformat(ds[0]).weekday()!=0:valid=False
            if not valid:wh=[];we=None;state=None
            else:
                wh.append(float(bars[(a,ds[-1])]['close']))
                if len(wh)==20:we=sum(wh)/20
                elif len(wh)>20:we=2/21*wh[-1]+19/21*we
                state=color(wh[-1],we,wh[-21]) if len(wh)>=120 else None
            available[weeks[j+1][0]]=(state,ds[-1])
        for d in cal:
            if d<'2022-01-04' or d>'2026-06-30':continue
            i=dates[d]
            if not i or d not in daily or cal[i-1] not in daily:continue
            w=available.get(datetime.date.fromisoformat(d).isocalendar()[:2])
            # Previous DAILY colour must be known; previous weekly readiness is irrelevant.
            if not w or not w[0]:continue
            state=daily[d]['color'];prev=daily[cal[i-1]]['color']
            if state in ('green','black') and prev!=state:
                results.append({'id':a+'|'+d,'asset':a,'date':d,'event_color':state,
                                'prior_color':prev,'week20_state':w[0],
                                'bull_group':daily[d]['bull_group'],'last_completed_week_date':w[1]})
    counts=collections.Counter((r['event_color'],r['date'][:4],r['week20_state']) for r in results)
    out={'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'new_fits':0,'future_outcomes_read':False,
         'rows':results,'counts':[{'event':e,'year':y,'week_state':w,'count':n} for (e,y,w),n in sorted(counts.items())]}
    (OUT/'independent-events.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out['counts']))

if __name__=='__main__':main()
