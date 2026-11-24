"""Offline coverage diagnostic, does not install or redefine the old monthly series."""
from pathlib import Path
import gzip,json,hashlib
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[4]
PLAN=json.loads((ROOT/'docs/ops/breadth-reading-aid-20261101/live-refresh-v15/storage-plan.json').read_text())
BASE=Path(PLAN['output']);RAW=BASE/'cn-breadth/raw';OUT=BASE/'institutional-context-v17'
assert BASE.stat().st_dev==PLAN['external_device']
listings=json.loads(gzip.decompress((RAW/'official-listings.json.gz').read_bytes()))
obs=defaultdict(dict)
for f in sorted(RAW.glob('batch-*.md.gz')):
 for line in gzip.decompress(f.read_bytes()).decode().splitlines():
  c=[v.strip() for v in line.strip().strip('|').split('|')]
  if len(c)!=9 or not c[0].startswith(('sh','sz')) or not c[1].startswith('2026-10'):continue
  obs[c[0]][c[1]]={'amount':float(c[7]),'volume':float(c[6]),'close':float(c[3])}
cal=sorted({c[0].strip() for line in gzip.decompress((RAW/'index.md.gz').read_bytes()).decode().splitlines() if (c:=line.strip().strip('|').split('|')) and c[0].strip().startswith('2026-10')})
oldbase=Path('/Volumes/win+mac通用/LeiSignal-新实验结果/public-universe-deep-completion-20261026/public-universe-deep-completion-20261026-20261026T225421-69a3af262800/result/cn-all-equity')
meta=json.loads((oldbase/'all-equity-read-index-v8-meta.json').read_text());expected={s:(d,None) for s,d in listings.items() if s.startswith(('sh','sz')) and d<='2026-10-30'}
for line in Path(meta['index_path']).open():
 r=json.loads(line);c=r['code'].replace('.','');ipo,out=r.get('supplier_ipo'),r.get('supplier_out')
 if c.startswith(('sh60','sh68','sz00','sz30')) and ipo and ipo<='2026-10-30' and (not out or out>='2026-10-01'):
  expected.setdefault(c,(ipo,out))
missing={}
for s,(ipo,out) in expected.items():
 absent=[d for d in cal if ipo<=d and (not out or d<=out) and d not in obs[s]]
 if absent:missing[s]=absent
result={'calendar':cal,'current_listed_count':sum(s.startswith(('sh','sz')) for s in listings),'expected_month_lifecycle_count':len(expected),'missing':missing,'status':'needs_qualification','note':'Do not infer amount units from volume units. Compare same-day amount with raw BaoStock before any splice; absent row remains unknown.'}
(OUT/'october-coverage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'calendar':len(cal),'pool':len(expected),'missing_count':len(missing),'missing':missing},ensure_ascii=False))
(OUT/'westock-october-amounts.json').write_text(json.dumps(obs))
