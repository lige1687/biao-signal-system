#!/usr/bin/env python3
"""One-pass, create-only acquisition of the explicitly listed public issuer pages."""
import hashlib,json,os,time,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlparse

RAW=Path(__file__).resolve().parents[1]
PLAN=RAW/'storage-plan.json'
REQ=Path(__file__).with_name('source-request-plan.json')
plan=json.loads(PLAN.read_text())
mount=plan['external_mount']
if os.stat(mount).st_dev!=int(plan['external_device']):raise SystemExit('external device mismatch; stopped')
base=Path(plan['output'])/'exit-primary-cases'
if base.exists():raise SystemExit('create-only output already exists; stopped')
base.mkdir(parents=True,exist_ok=False)
(base/'originals').mkdir()
requests=json.loads(REQ.read_text())['requests']
blocked=set(); records=[]
class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old=urlparse(req.full_url).hostname; new=urlparse(newurl).hostname
        if old!=new: raise RuntimeError(f'cross-host redirect refused: {old} -> {new}')
        return super().redirect_request(req,fp,code,msg,headers,newurl)
opener=urllib.request.build_opener(SameHostRedirect())
for item in requests:
    host=urlparse(item['url']).hostname
    rec={k:item[k] for k in ('event','name','url','source_date','issuer','purpose')}
    if host in blocked:
        rec.update(status='not_requested_host_blocked',reason='earlier 403/429 on this host');records.append(rec);continue
    rec['started_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
    path=base/'originals'/item['name']
    try:
        req=urllib.request.Request(item['url'],headers={'User-Agent':'LeiSignalResearch/1.0 (public-source event qualification)','Accept':'text/html,application/pdf,*/*'})
        with opener.open(req,timeout=45) as response:
            rec.update(status=response.status,content_type=response.headers.get('Content-Type'),final_url=response.geturl())
            body=response.read(int(item['max_bytes'])+1)
            if len(body)>int(item['max_bytes']): raise RuntimeError('response exceeds per-document cap')
            with path.open('xb') as f:f.write(body)
            rec.update(path=str(path),bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
    except urllib.error.HTTPError as e:
        rec.update(status=e.code,error=str(e))
        if e.code in (403,429):blocked.add(host)
    except Exception as e:
        rec.update(status='error',error=f'{type(e).__name__}: {e}')
    rec['ended_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z');records.append(rec)
    time.sleep(1)
manifest={'schema':'exit-primary-sources/1','network_requests_attempted':sum(x.get('status')!='not_requested_host_blocked' for x in records),'blocked_hosts_after_403_429':sorted(blocked),'max_documents_per_event':2,'records':records}
(base/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
