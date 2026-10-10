"""Single synchronous bounded primary-source GET, with before-dispatch ledger."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT / 'executor-contract.json').read_text())
L = ROOT / 'request-ledger.json'
M = ROOT / 'source-manifest.json'
EX = Path(C['output_plan']['run_directory'])
ALLOWED = {'www.sse.com.cn', 'www.szse.cn', 'static.sse.com.cn', 'docs.static.szse.cn'}

def write(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')

def main():
    a = argparse.ArgumentParser()
    a.add_argument('--operation', required=True)
    a.add_argument('--url', required=True)
    a.add_argument('--name', required=True)
    v = a.parse_args()
    assert urlparse(v.url).hostname in ALLOWED and urlparse(v.url).scheme in {'http','https'}
    assert '/' not in v.name and '..' not in v.name
    l = json.loads(L.read_text())
    assert l['actual_public_actions'] < C['budgets']['total_public_actions_max']
    assert sum(x['status'].startswith('failed') for x in l['requests'] if x['operation']==v.operation) < C['budgets']['same_semantic_operation_attempts_max']
    n = l['actual_public_actions']+1
    row = {'n':n,'operation':v.operation,'kind':'http_get','url':v.url,'status':'pending','started_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'measurable_response_bytes':0}
    l['requests'].append(row); l['actual_public_actions']=n; write(L,l)
    body = EX / f'{n:02d}-{v.name}'
    hdr = EX / f'{n:02d}-{v.name}.headers.json'
    h=hashlib.sha256();size=0
    try:
        s=requests.Session();s.trust_env=False
        with s.get(v.url,timeout=(10,30),stream=True,allow_redirects=False) as resp:
            write(hdr,{'status_code':resp.status_code,'url':resp.url,'headers':dict(resp.headers)})
            with body.open('wb') as f:
                for ch in resp.iter_content(65536):
                    if not ch:continue
                    if size+len(ch)>C['budgets']['per_response_bytes_max'] or l['measurable_saved_raw_bytes']+size+len(ch)>C['budgets']['saved_raw_response_bytes_max']:
                        raise RuntimeError('raw response byte cap')
                    f.write(ch);h.update(ch);size+=len(ch)
            row.update({'status':'success_http' if resp.ok else ('redirect' if resp.is_redirect else 'failed_http'),'http_status':resp.status_code,'final_url':resp.url,'redirect_location':resp.headers.get('Location'),'body_path':str(body),'headers_path':str(hdr),'body_sha256':h.hexdigest(),'measurable_response_bytes':size})
    except Exception as e:
        row.update({'status':'failed_exception','error':f'{type(e).__name__}: {str(e)[:160]}','body_path':str(body) if body.exists() else None,'headers_path':str(hdr) if hdr.exists() else None,'body_sha256':h.hexdigest() if size else None,'measurable_response_bytes':size})
    row['finished_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    l['measurable_saved_raw_bytes']+=size;write(L,l)
    m=json.loads(M.read_text())
    if size:
        m['sources'].append({'n':n,'operation':v.operation,'url':v.url,'status':row['status'],'path':str(body),'headers_path':str(hdr),'bytes':size,'sha256':h.hexdigest(),'http_status':row.get('http_status')})
        write(M,m)
    print(json.dumps({'n':n,'status':row['status'],'http_status':row.get('http_status'),'bytes':size,'sha256':row.get('body_sha256'),'error':row.get('error'),'path':row.get('body_path')},ensure_ascii=False))
if __name__=='__main__':main()
