"""Append-only input readiness observations. No signal, account or trade calculation."""
from pathlib import Path
import datetime,json,hashlib,uuid
BASE=Path(__file__).resolve().parent

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def record():
 cfg=json.loads((BASE/'config.json').read_text());now=datetime.datetime.now(datetime.timezone.utc).isoformat();rows=[]
 for src in cfg['sources']:
  p=Path(src['path']); row={'id':src['id'],'path':str(p),'purpose':src['purpose'],'exists':p.is_file()}
  if p.is_file():
   try:
    before=p.stat();v=digest(p);after=p.stat();stable=(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    row.update(sha256=v,bytes=after.st_size,mtime_ns=after.st_mtime_ns,stable_during_read=stable,audited_latest_date=(src.get('audited_latest_date') if v==src.get('audited_sha256') and stable else None),date_needs_review=(v!=src.get('audited_sha256') or not stable))
   except OSError as exc:row.update(read_error=type(exc).__name__,stable_during_read=False)
  rows.append(row)
 records=BASE/'records';records.mkdir(exist_ok=True);existing=sorted(records.glob('*.json'));last=json.loads(existing[-1].read_text()) if existing else None
 changed=last is None or last['inputs']!=rows or last['config_sha256']!=digest(BASE/'config.json')
 result={'recorded_at':now,'timezone':'Asia/Shanghai','rules_frozen_at':cfg['rules_frozen_at'],'stage':'input_observation_only','signal_observation_started':False,'reason':'Matching point-in-time live inputs and initialization have not been approved by a documented readiness check. File change is not a signal.','inputs':rows,'config_sha256':digest(BASE/'config.json'),'changed_since_previous_record':changed,'source_bytes_archived':False,'historical_available_at':'unknown; file mtime is not market availability','signals':None,'trades':None,'returns':None}
 filename=records/(now.replace(':','').replace('+','_')+'-'+uuid.uuid4().hex[:8]+'.json')
 with filename.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'record':str(filename),'changed':changed,'stage':result['stage'],'sources':len(rows),'missing':[x['id'] for x in rows if not x['exists']],'unstable':[x['id'] for x in rows if x.get('stable_during_read') is False]},ensure_ascii=False))
if __name__=='__main__':record()
