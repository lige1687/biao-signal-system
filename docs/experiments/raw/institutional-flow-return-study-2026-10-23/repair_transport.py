"""One serial transport repair per failed download, preserve original failures and partials."""
import datetime as dt
import hashlib,json,os,urllib.request
from pathlib import Path
from acquire_nport import guard, MANIFEST, OUT
rows=json.loads(MANIFEST.read_text())
failed=[r for r in rows if r['state']=='failed']
for original in failed:
    rel=original['relative_path']
    if any(r.get('repair_of')==rel for r in rows):
        raise RuntimeError('repair already attempted; inspect evidence')
    guard()
    target=OUT/'transport-attempt2'/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_suffix('.partial')
    if target.exists() or partial.exists():raise RuntimeError('preserve existing attempt')
    r=dict(relative_path=rel,path=str(target),url=original['url'],repair_of=rel,attempt=2,
           retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),diagnosis='Intermittent TLS EOF or truncated transport amid successful samehost files; change from3parallel to1serial, preserve original partial')
    n=0; h=hashlib.sha256()
    try:
        req=urllib.request.Request(r['url'],headers={'User-Agent':'LeiSignal-public-research/1.0','Connection':'close'})
        with urllib.request.urlopen(req,timeout=120) as response,partial.open('wb') as f:
            length=response.headers.get('Content-Length');r['status']=response.status
            while chunk:=response.read(1024*1024):
                guard();f.write(chunk);h.update(chunk);n+=len(chunk)
        if length and n!=int(length):raise RuntimeError('truncated response')
        with partial.open('rb') as f:
            if f.read(4)!=b'PAR1':raise RuntimeError('not parquet')
            f.seek(-4,2)
            if f.read()!=b'PAR1':raise RuntimeError('invalid parquet trailer')
        os.replace(partial,target)
        r.update(state='completed',bytes=n,sha256=h.hexdigest())
    except Exception as e:r.update(state='failed',bytes=n,error=str(e),partial_path=str(partial))
    rows.append(r);MANIFEST.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:r.get(k) for k in ['relative_path','state','bytes','error']}),flush=True)
