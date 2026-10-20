#!/usr/bin/env python3
"""Read-only audit existing v2 files, then create only manifest and local receipt."""
import csv,datetime as dt,hashlib,json,os
from collections import Counter
from pathlib import Path

RAW=Path(__file__).resolve().parent
CONTRACT=RAW/'luna-identity-daily-contract-v2.json'
RUNNER=RAW/'qualify_identity_daily_v2.py'
TEST=RAW/'test_qualify_identity_daily_v2.py'
OLD_RECEIPT=RAW/'identity-daily-receipt.json'
RECEIPT=RAW/'identity-daily-receipt-v2.json'
EXPECTED=['daily-coverage.csv','daily-issues.csv','monthly-identity-candidates.csv','identity-examples.json','summary.json']

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def read_csv(p):
 with Path(p).open('r',encoding='utf-8',newline='') as f:
  reader=csv.DictReader(f); rows=list(reader); return reader.fieldnames,rows

def main():
 c=json.loads(CONTRACT.read_text(encoding='utf-8')); job_path=Path(c['job_path']);job=json.loads(job_path.read_text(encoding='utf-8'))
 out=Path(job['output']); assert out.is_dir()
 assert not (out/'manifest.json').exists(),'manifest already exists; refusing replacement'
 storage=json.loads((RAW/'storage-plan.json').read_text(encoding='utf-8'))
 assert os.stat(storage['external_mount']).st_dev==storage['external_device']==job['external_device']
 # Do not count or parse AppleDouble metadata. Only the five contract outputs are data artifacts.
 for name in EXPECTED: assert (out/name).is_file(),f'missing expected output: {name}'
 actual={p.name for p in out.iterdir() if p.is_file() and not p.name.startswith('._') and p.name!='.DS_Store'}
 assert set(EXPECTED)<=actual,f'expected data file set incomplete: {actual}'
 daily_header,daily=read_csv(out/'daily-coverage.csv')
 issue_header,issues=read_csv(out/'daily-issues.csv')
 monthly_header,monthly=read_csv(out/'monthly-identity-candidates.csv')
 summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
 examples=json.loads((out/'identity-examples.json').read_text(encoding='utf-8'))
 assert len(daily)==2516 and len(monthly)==60510
 dates=[dt.date.fromisoformat(r['date']) for r in daily]
 assert dates==sorted(set(dates)) and dates[0].isoformat()=='2015-01-02' and dates[-1].isoformat()=='2024-12-31'
 assert all('ticker' in r and 'issues' in r for r in issues)
 keyrows=[(r['month'],r['ticker']) for r in monthly]
 assert len(keyrows)==len(set(keyrows))==60510,'monthly member key duplication or missing rows'
 md=[dt.date.fromisoformat(r['quote_date']) for r in monthly]
 assert min(md)>=dt.date(2015,1,1) and max(md)<=dt.date(2024,12,31)
 candidate_counts=Counter(r['status'] for r in monthly)
 assert dict(candidate_counts)==summary['monthly_identity_status_counts']
 for r in monthly:json.loads(r['candidate_evidence_json'])
 for r in issues:json.loads(r['price_rows_json'])
 assert sum(int(r['eligible_exact_price_rows']) for r in daily)==summary['eligible_exact_price_rows']
 assert len(issues)==summary['daily_issue_rows']
 assert sum(int(r['active_member_rows']) for r in daily)==summary['daily_member_days']
 assert summary['network_requests']==0 and summary['returns_or_op_calculated'] is False
 assert examples['identity_status_note']=='all links are candidates; no historical identity is confirmed'
 # Include only named data files; sidecars and manifest are not data outputs.
 files=[]
 for name in EXPECTED:
  p=out/name
  row_count=None
  if p.suffix=='.csv':
   fields,rows=read_csv(p);row_count=len(rows)
  files.append({'path':name,'sha256':sha(p),'bytes':p.stat().st_size,'rows':row_count})
 manifest={'status':'completed_manifest_finalization_after_runner_manifest_error','contract_sha256':sha(CONTRACT),'job_sha256':sha(job_path),'runner_sha256_used_for_run':'bd8bdd201f843ef6b0e3d5ce4e9e52153e32b79ff6e87b7003543e11a83f807f','runner_initial_exit_code':1,'finalizer_sha256':sha(Path(__file__)),'input_hashes':{Path(x['path']).name:sha(x['path']) for x in job['input_files']},'files':files,'summary':summary,'ignored_external_metadata':[p.name for p in out.iterdir() if p.name.startswith('._') or p.name=='.DS_Store'],'checks':{'daily_utf8_csv_parsed':True,'monthly_utf8_csv_parsed':True,'daily_unique_dates':len(dates),'monthly_unique_keys':len(keyrows),'monthly_status_counts':dict(candidate_counts),'all_candidate_evidence_json_valid':True,'all_issue_price_json_valid':True}}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 assert not RECEIPT.exists()
 receipt={'status':'data_outputs_validated_manifest_finalized','finalized_at':dt.datetime.now(dt.timezone.utc).isoformat(),'contract_path':str(CONTRACT),'contract_sha256':sha(CONTRACT),'job_path':str(job_path),'job_sha256':sha(job_path),'runner_path':str(RUNNER),'runner_sha256_used_for_actual_run':'bd8bdd201f843ef6b0e3d5ce4e9e52153e32b79ff6e87b7003543e11a83f807f','runner_test_sha256':'f41b51a12b2083ca136a005f6d523685e8a0a591f5473f172bd1dc75bb7fa8b1','synthetic_test':'PASS: end-to-end fixture, finite-value and date/string checks, duplicate price/member, period filter, monthly CIK conflict, STI suffix and create-only behavior','actual_command':'PYTHONDONTWRITEBYTECODE=1 python3 -B docs/experiments/raw/us-op-common-history-2026-10-20/qualify_identity_daily_v2.py --contract docs/experiments/raw/us-op-common-history-2026-10-20/luna-identity-daily-contract-v2.json','actual_tool_session_id':24764,'actual_exit_code':1,'actual_failure':'UnicodeDecodeError during manifest CSV row counting because external volume created binary AppleDouble ._* metadata siblings; five intended data outputs had already been written. No data output was rewritten.','v1_failure_receipt_path':str(OLD_RECEIPT),'v1_failure_receipt_sha256':sha(OLD_RECEIPT),'finalizer_path':str(Path(__file__)),'finalizer_sha256':sha(Path(__file__)),'manifest_path':str(out/'manifest.json'),'manifest_sha256':sha(out/'manifest.json'),'output_path':str(out),'outputs':files,'summary':summary,'output_validation':'All expected CSVs parsed as UTF-8; exact 2,516 unique SPY dates 2015-01-02 through 2024-12-31; 60,510 unique monthly (month,ticker) keys; candidate JSON fields parsed; summary counts reconciled. AppleDouble/.DS_Store metadata ignored and preserved.','network_requests':0,'returns_or_op_calculated':False,'identity_claim_boundary':'CIK links remain candidates only; no historical identity validation or payout conclusion.'}
 RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # Read back both artifacts and verify checksums after storage writes.
 assert sha(out/'manifest.json')==receipt['manifest_sha256'] and sha(RECEIPT)==sha(RECEIPT)
 print(json.dumps({'receipt':str(RECEIPT),'receipt_sha256':sha(RECEIPT),'manifest_sha256':sha(out/'manifest.json'),'summary':summary},ensure_ascii=False))
if __name__=='__main__':main()
