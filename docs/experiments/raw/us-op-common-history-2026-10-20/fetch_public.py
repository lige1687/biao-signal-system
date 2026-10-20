import os,json,urllib.request,urllib.error,hashlib,datetime,time,sys
from pathlib import Path
raw=Path(__file__).resolve().parent
plan=json.loads((raw/'storage-plan.json').read_text())
out=Path(plan['output'])/'sources'; out.mkdir(exist_ok=True)
requests=json.loads(Path(sys.argv[1]).read_text())
ledger=raw/'http-ledger.jsonl'
consecutive_failures=0
blocked={x['url'].split('/')[2] for x in map(json.loads,ledger.read_text().splitlines()) if x.get('status') in [403,429]} if ledger.exists() else set()
for item in requests:
    host=urllib.request.urlparse(item['url']).netloc if hasattr(urllib.request,'urlparse') else __import__('urllib.parse',fromlist=['urlparse']).urlparse(item['url']).netloc
    if host in blocked: continue
    if out.stat().st_dev != plan['external_device'] or Path(plan['external_mount']).stat().st_dev != plan['external_device']: raise RuntimeError('external disk changed')
    target=out/item['name']
    if target.exists(): raise RuntimeError('refuse overwrite '+str(target))
    rec={**item,'started_at':datetime.datetime.now().astimezone().isoformat(),'path':str(target)}
    try:
        req=urllib.request.Request(item['url'],headers={'User-Agent':'LeiSignalResearch/1.0 (public-source academic verification)','Accept':'application/json, text/plain, */*'})
        with urllib.request.urlopen(req,timeout=60) as r:
            rec.update(status=r.status,content_type=r.headers.get('content-type'),final_url=r.url.split('?')[0])
            with target.open('xb') as w:
                total=0
                while True:
                    b=r.read(1024*1024)
                    if not b: break
                    total+=len(b)
                    if total>item.get('max_bytes',64*1024*1024): raise RuntimeError('planned response size exceeded')
                    w.write(b)
        rec['bytes']=target.stat().st_size
        rec['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        consecutive_failures=0
        if item.get('expected_sha256') and item['expected_sha256'] != rec['sha256']: raise RuntimeError('release hash mismatch')
    except Exception as e:
        rec['error']=str(e);rec['status']=getattr(e,'code',None)
        consecutive_failures+=1
        if rec['status'] in [403,429]: blocked.add(host)
    rec['ended_at']=datetime.datetime.now().astimezone().isoformat()
    with ledger.open('a') as w: w.write(json.dumps(rec,ensure_ascii=False)+'\n')
    print(json.dumps(rec,ensure_ascii=False),flush=True)
    if consecutive_failures>=2: break
    time.sleep(1)
