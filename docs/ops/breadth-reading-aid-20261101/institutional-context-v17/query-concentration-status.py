from pathlib import Path
import json,gzip,hashlib,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'src'))
from lei_signal.market_context.cn_breadth_refresh import _baostock_status,StatusQueryError
p=Path(json.loads((ROOT/'docs/ops/breadth-reading-aid-20261101/live-refresh-v15/storage-plan.json').read_text())['output'])/'institutional-context-v17'
a=json.loads((p/'reuse-audit.json').read_text());assert len(a['missing'])<=12
records=[]
for symbol,days in a['missing'].items():
 name=f'baostock-{symbol}-october.txt.gz'
 try:
  result,raw=_baostock_status(symbol,min(days),max(days));record={'symbol':symbol,'requested_dates':days,'result':result}
 except StatusQueryError as e:
  raw=e.raw;record={'symbol':symbol,'requested_dates':days,'error':str(e)}
 blob=gzip.compress(raw);(p/name).write_bytes(blob);record.update(raw=name,sha256=hashlib.sha256(blob).hexdigest());records.append(record)
 (p/'targeted-status.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
 print(symbol,'rows',len(record.get('result',{}).get('rows',[])),record.get('error',''),flush=True)
