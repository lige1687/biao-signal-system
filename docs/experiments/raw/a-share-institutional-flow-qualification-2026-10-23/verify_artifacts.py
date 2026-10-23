"""Read back sources, frozen evidence and report API; no statistical rerun."""
import json,hashlib,datetime,urllib.request,urllib.parse,sys
from pathlib import Path
R=Path(__file__).resolve().parent; ROOT=R.parents[3];sys.path.insert(0,str(ROOT/'src'))
from lei_signal.research.output_storage import plan_output
report=ROOT/'docs/experiments/a-share-institutional-flow-qualification-2026-10-23.md'
key=str(report.relative_to(ROOT));v={'at':datetime.datetime.now().astimezone().isoformat(),'report':key,'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'freeze_bindings':{},'diagnostics':[{'attempt':'first API detail URL used basename, 404 at 8000/5173/5188','resolution':'read list-provided exact full name and use it for detail; no service mutation'}]}
for f in ['freeze.json','history-effect-freeze.json']:
 d=json.loads((R/f).read_text())
 for p,h in d['bindings'].items():
  if isinstance(h,dict):h=h['sha256']
  target=Path(p);target=target if target.is_absolute() else ROOT/target
  ok=hashlib.sha256(target.read_bytes()).hexdigest()==h;assert ok,p;v['freeze_bindings'][p]=ok
v['strategy_sources']={}
for p,h in json.loads((R/'start.json').read_text())['strategy'].items():
 ok=hashlib.sha256(Path(p).read_bytes()).hexdigest()==h;assert ok,p;v['strategy_sources'][p]=ok
files=[]
for f in ['jiashi-history/source-manifest.json','huaxia-history/manifest.json']:
 for a in json.loads((R/f).read_text())['reports']:
  p=Path(a['pdf_path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==a['pdf_sha256'],p;files.append(str(p))
assert len(files)==len(set(files))==28;v['official_pdfs_all_hash_verified']=28
s=json.loads((R/'history-effect-summary.json').read_text());a=json.loads((R/'history-effect-independent.json').read_text());assert a['status'] in ['pass','passed'];assert not a['differences_from_frozen_summary'];v['independent_numeric_audit']=a['status'];v['frozen_effect_runs']=s['effect_runs'];v['metadata_correction_records']=len(json.loads((R/'corrections.json').read_text())['history_effect']['mapping'])
assert (Path(s['out'])/'summary.json').read_bytes()==(R/'history-effect-summary.json').read_bytes();v['external_summary_exact']=True
plan=json.loads((R/'storage-plan.json').read_text());live=plan_output(ROOT,plan['task_id'],plan['estimated_bytes'],internal_bytes=plan['internal_metadata_bytes']);assert live['external_uuid']==plan['external_uuid'] and live['external_device']==plan['external_device'];assert Path(plan['output']).stat().st_dev==live['external_device'];v['storage_uuid']=live['external_uuid'];v['storage_device']=live['external_device'];v['actual_external_bytes']=sum(p.stat().st_size for p in Path(plan['output']).rglob('*') if p.is_file());v['local_raw_bytes_at_check']=sum(p.stat().st_size for p in R.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
v['api']={}
for port in [8000,5173,5188]:
 try:
  root=f'http://localhost:{port}/api/experiments';listing=json.load(urllib.request.urlopen(root,timeout=10));matches=[x for x in listing['items'] if x['name']==key];assert len(matches)==1;item=matches[0];assert item['category']=='方法论与验证' and item['verdict']=='mixed'
  detail=json.load(urllib.request.urlopen(root+'/'+urllib.parse.quote(item['name']),timeout=10));body=[(k,z) for k,z in detail.items() if isinstance(z,str) and z==report.read_text()];assert len(body)==1,list(detail)
  v['api'][str(port)]={'status':'passed','unique':True,'category':item['category'],'verdict':item['verdict'],'body_field':body[0][0],'body_sha256':hashlib.sha256(body[0][1].encode()).hexdigest()}
 except Exception as e:v['api'][str(port)]={'status':'failed','error':str(e)}
assert any(x['status']=='passed' for x in v['api'].values()),v['api']
v['repo_hygiene']='passed 2026-10-23; check_repo_hygiene.py exit 0';v['production_or_trading_changes']=False;v['external_other_device_restoration']='not verified'
(R/'verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:x for k,x in v.items() if k not in ['freeze_bindings','strategy_sources']},ensure_ascii=False,indent=2))
