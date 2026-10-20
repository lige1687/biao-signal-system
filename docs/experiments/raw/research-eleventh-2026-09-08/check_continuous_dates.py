from pathlib import Path
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
import diagnose_history as d
from lei_signal.rules.strict_structure import detect_strict_structure_events
from dataclasses import asdict
import pandas as pd
import gzip,json
from datetime import datetime,timezone

def main():
 out=P/'continuous-results';assert not out.exists();out.mkdir()
 bars,actions=d.load_inputs();epochs=d.read(P.parent/'research-tenth-2026-09-08/history-diagnostic/run-lock.json')['plan']
 plan=[]
 for s,center in [('sh513100','2015-12-31'),('sh518880','2022-12-30')]:
  dates=[r['date'] for r in bars[s] if d.START<=r['date']<=d.END];k=dates.index(center)
  for day in dates[k-10:k+11]:
   ep=next(x for x in epochs if x['symbol']==s and x['start']<=day<=x['end'])
   plan.append(dict(symbol=s,day=day,start=ep['start'],end=ep['end']))
 assert len(plan)==42
 files=dict(d.read(P/'repair-lock.json')['files']);files[str(Path(__file__).resolve())]=d.sha(Path(__file__));files[str(P/'continuous-protocol.md')]=d.sha(P/'continuous-protocol.md')
 d.save(out/'run-lock.json',dict(started_at_utc=datetime.now(timezone.utc).isoformat(),files=files,plan=plan))
 checks=[];diffs=[];cached={}
 def calc(raw,s):
  events=d.events_for(raw,s);ev=detect_strict_structure_events(raw,s)
  assert len({e.event_id for e in ev})==len(ev)
  events['strict']=[d.plain(asdict(e)) for e in ev];return events
 for p in plan:
  s,day,lo,hi=p['symbol'],p['day'],p['start'],p['end'];key=(s,hi)
  if key not in cached:
   raw=d.raw_asof(s,bars,actions,hi);cached[key]=(raw,calc(raw,s))
  raw,full=cached[key];prefix=d.raw_asof(s,bars,actions,day)
  pd.testing.assert_frame_equal(raw.loc[:day],prefix,check_exact=True)
  part=calc(prefix,s)
  for name in part:
   left=d.select(part[name],lo,day);right=d.select(full[name],lo,day)
   removed=sorted(set(left)-set(right));added=sorted(set(right)-set(left));changed=sorted(k for k in set(left)&set(right) if left[k]!=right[k])
   checks.append(dict(symbol=s,cutoff=day,module=name,matched=not(removed or added or changed),removed=len(removed),added=len(added),changed=len(changed)))
   for kind,ids in [('removed',removed),('added',added),('changed',changed)]:
    for eid in ids:diffs.append(dict(symbol=s,cutoff=day,module=name,kind=kind,event_id=eid,before=left.get(eid),after=right.get(eid)))
  d.save(out/'progress.json',dict(fund_dates_completed=len(checks)//4,checks_completed=len(checks),differences=len(diffs)))
 for f,h in files.items():assert d.sha(Path(f))==h,f
 pd.DataFrame(checks).to_csv(out/'checks.csv',index=False)
 with gzip.open(out/'differences.json.gz','wt') as f:json.dump(diffs,f,ensure_ascii=False)
 d.save(out/'summary.json',dict(fund_dates=42,checks=len(checks),passed=sum(r['matched'] for r in checks),failed=sum(not r['matched'] for r in checks),differences=len(diffs),modules=['A','C','D','strict'],input_hashes_unchanged=True,scope='two known problem dates plus/minus ten actual quotations, regression only',finished_at_utc=datetime.now(timezone.utc).isoformat()))
 print(d.read(out/'summary.json'),flush=True)
if __name__=='__main__':main()
