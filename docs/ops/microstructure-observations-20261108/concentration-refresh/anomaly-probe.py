"""Independent, bounded Eastmoney witness for eight BaoStock status/amount conflicts."""
import datetime as dt
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/concentration-derived-20261108-run1/audit.json')
RAW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/concentration-refresh-20261108/anomaly-probes')
RESULT = HERE / 'anomaly-probe-result.json'
DEADLINE = dt.datetime.fromisoformat('2026-11-08T13:00:46.537129+00:00')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    if RESULT.exists() or RAW.exists():
        raise FileExistsError('anomaly probe output already exists')
    rows = [r for r in json.loads(AUDIT.read_text())['newInvalidRows'] if r['code'] != 'sh.600656']
    if len(rows) != 8:
        raise RuntimeError('expected exactly eight anomalous rows')
    RAW.mkdir()
    out = []
    response_bytes = 0
    for ref in rows:
        if dt.datetime.now(dt.timezone.utc) >= DEADLINE or len(out) >= 16 or response_bytes >= 2*1024*1024:
            break
        code, day = ref['code'], ref['date']
        market = '1' if code.startswith('sh.') else '0'
        start = (dt.date.fromisoformat(day)-dt.timedelta(days=7)).strftime('%Y%m%d')
        end = (dt.date.fromisoformat(day)+dt.timedelta(days=7)).strftime('%Y%m%d')
        params = {'secid':market+'.'+code[3:], 'fields1':'f1,f2,f3,f4,f5,f6',
                  'fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                  'klt':'101','fqt':'0','beg':start,'end':end}
        url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get?' + urllib.parse.urlencode(params)
        status = 'error'; error = None
        try:
            request = urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
            with urllib.request.urlopen(request,timeout=12) as response:
                body = response.read(2*1024*1024+1)
                status = response.status
        except Exception as exc:
            error = repr(exc)
            body = json.dumps({'error':error}).encode()
        response_bytes += len(body)
        if response_bytes > 2*1024*1024:
            raise RuntimeError('response byte cap reached')
        path = RAW / (code.replace('.','')+'-'+day+'.json')
        path.write_bytes(body)
        source = json.loads(Path(ref['path']).read_text())
        sfields = source['fields']
        bao_rows = [dict(zip(sfields,r)) for r in source['data'] if r[0] == day]
        em_body = json.loads(body)
        klines = ((em_body.get('data') or {}).get('klines') or []) if isinstance(em_body,dict) else []
        matching = [k for k in klines if k.split(',')[0] == day]
        east = None
        if matching:
            f = matching[0].split(',')
            east = {'date':f[0], 'open':f[1], 'close':f[2], 'high':f[3], 'low':f[4],
                    'volumeLots100Shares':f[5], 'amountYuan':f[6],
                    'impliedAmountPerShareYuan':float(f[6])/(float(f[5])*100) if float(f[5]) else None}
        rec={'code':code,'date':day,'url':url,'httpStatus':status,'error':error,
             'responseBytes':len(body),'sha256':sha(body),'path':str(path),
             'eastmoneyResponseCode':em_body.get('rc') if isinstance(em_body,dict) else None,
             'eastmoneyWindowRows':len(klines),'eastmoneyTargetRows':len(matching),
             'eastmoneyTarget':east,'baoTargetRows':bao_rows,
             'baoPath':ref['path'],'baoSha256':sha(Path(ref['path']).read_bytes())}
        out.append(rec)
        RESULT.write_text(json.dumps({'schemaVersion':1,'requestsAlreadyWithRootSearches':5350,
                                      'newRequests':len(out),'newResponseBytes':response_bytes,
                                      'totalKnownRequests':5350+len(out),
                                      'rows':out},ensure_ascii=False,indent=2)+'\n')
    print('requests',len(out),'bytes',response_bytes,'targetRows',sum(bool(x['eastmoneyTarget']) for x in out))


if __name__=='__main__':
    main()
