from pathlib import Path
import json,gzip,hashlib
HERE=Path(__file__).resolve().parent
plan=json.loads((HERE.parent/'live-refresh-v15/storage-plan.json').read_text());out=Path(plan['output'])/'institutional-context-v17';assert out.stat().st_dev==plan['external_device']
audit=json.loads((out/'october-coverage.json').read_text());obs=json.loads((out/'westock-october-amounts.json').read_text());need=set(audit['missing'])|{'sh600000','sh688001','sz000001'}
base=Path('/Volumes/win+mac通用/LeiSignal-新实验结果/public-universe-deep-completion-20261026/public-universe-deep-completion-20261026-20261026T225421-69a3af262800/result/cn-all-equity')
meta=json.loads((base/'all-equity-read-index-v8-meta.json').read_text());old=Path('/Volumes/win+mac通用/LeiSignal-新实验结果/twenty-year-universe-data-20261025/twenty-year-universe-data-20261025-20261025T154847-f27d39c4e083/result/cn/stock-source-union-v4/actual-date-unions.jsonl')
refs={s:[] for s in need}
for p,fields in [(Path(meta['index_path']),['reused_raw_sources','new_price_sources']),(old,['source_refs'])]:
 for line in p.open():
  r=json.loads(line);s=r['code'].replace('.','')
  if s in need:
   for k in fields:refs[s]+=r.get(k,[])
used=[];overlap=[];filled=[]
for s,items in refs.items():
 seen=set()
 for r in items:
  p=Path(r.get('source_path') or r['path'])
  if p in seen:continue
  seen.add(p);blob=p.read_bytes();expected=r.get('compressed_sha256') or r['sha256'];assert hashlib.sha256(blob).hexdigest()==expected
  raw=gzip.decompress(blob) if p.suffix=='.gz' else blob;data=json.loads(raw);fields=data['fields'];ix={x:i for i,x in enumerate(fields)}
  for row in data['data']:
   day=row[ix['date']]
   if not day.startswith('2026-10'):continue
   if not r.get('valid_slice_start',day)<=day<=r.get('valid_slice_end',day):continue
   amount=row[ix['amount']];volume=row[ix['volume']];status=row[ix['tradestatus']]
   if status=='0' and amount in ('','0','0.0000','0.0') and volume in ('','0','0.0000','0.0'):amount=0.
   elif status=='1' and amount!='' and volume!='' and float(amount)>=0:amount=float(amount)
   else:continue
   if day in obs.get(s,{}):
    if amount>0:overlap.append({'symbol':s,'date':day,'baostock_amount':amount,'westock_amount':obs[s][day]['amount'],'ratio':obs[s][day]['amount']/amount})
   elif day in audit['missing'].get(s,[]):
    obs.setdefault(s,{})[day]={'amount':amount,'source':'saved_baostock','status':status};filled.append({'symbol':s,'date':day,'status':status,'source':str(p)})
  used.append({'path':str(p),'sha256':expected})
missing={s:[d for d in ds if d not in obs.get(s,{})] for s,ds in audit['missing'].items()};missing={s:ds for s,ds in missing.items() if ds}
result={'filled_count':len(filled),'missing':missing,'overlap':overlap,'filled':filled,'sources':used,'note':'Amount identity tested directly, not inferred from volume units; remaining absent dates require explicit status.'}
(out/'reuse-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out/'merged-october-amounts.json').write_text(json.dumps(obs));print(json.dumps({'filled':len(filled),'remaining':missing,'overlap_n':len(overlap),'ratios':{'min':min(x['ratio'] for x in overlap),'max':max(x['ratio'] for x in overlap)}}))
