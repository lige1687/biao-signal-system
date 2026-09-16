"""Recovery duration from independent daily NAV; no main or Spark metric imports."""
from pathlib import Path
from datetime import date,datetime,timezone
from decimal import Decimal as D
import json,csv,hashlib,shutil
P=Path(__file__).resolve().parent;R=P.parent
sources=['account-results/summary.json','summary-first-pass/summary.json','summary-correction.json','spark-metrics/metrics.py']
manifest=[]
for rel in sources:
 source=R/rel;dst=P/'accepted-summary'/rel;dst.parent.mkdir(parents=True,exist_ok=True);b=source.read_bytes()
 if dst.exists():assert dst.read_bytes()==b,'Previously accepted summary changed'
 else:dst.write_bytes(b)
 manifest.append(dict(source=str(source.resolve()),file=str(dst.relative_to(P)),sha256=hashlib.sha256(b).hexdigest()))
(P/'accepted-summary-inputs.json').write_text(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),files=manifest),indent=2)+'\n')
reported={r['config_id']:r for r in json.loads((P/'accepted-summary/account-results/summary.json').read_text())};results=[]
for cfg in [f'P{i}' for i in range(8)]:
 rows=list(csv.DictReader((P/'reconciliation'/cfg/'daily-independent.csv').open()))
 peak=D(rows[0]['nav']);anchor=rows[0]['date'];under=False;episode=None;longest=0;longest_start=None;longest_end=None;recovered=None
 for row in rows:
  current=D(row['nav']);today=row['date']
  if current>=peak-D('1e-25'):
   if under:
    duration=(date.fromisoformat(today)-date.fromisoformat(episode)).days
    if duration>longest:longest=duration;longest_start=episode;longest_end=today;recovered=True
   peak=max(peak,current);anchor=today;under=False;episode=None
  else:
   if not under:episode=anchor;under=True
   duration=(date.fromisoformat(today)-date.fromisoformat(episode)).days
   if duration>=longest:longest=duration;longest_start=episode;longest_end=today;recovered=False
  # 1e-25 only suppresses 40-digit Decimal roundoff, not a financial recovery tolerance.
 assert longest==reported[cfg]['longest_drawdown_days'],(cfg,longest,reported[cfg]['longest_drawdown_days'])
 assert under==reported[cfg]['unrecovered_at_end']
 results.append(dict(config=cfg,longest_days=longest,longest_interval_start=longest_start,longest_interval_end=longest_end,longest_interval_recovered=recovered,unrecovered_at_end=under,last_equal_or_higher_peak=anchor,tail_episode_start=episode))
(P/'recovery-checks.json').write_text(json.dumps(dict(status='passed',definition='Calendar-day difference from last equal-or-higher prior NAV peak to recovery or window end; every equal peak resets anchor',input='independent Decimal daily account reconstruction',results=results),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False))
