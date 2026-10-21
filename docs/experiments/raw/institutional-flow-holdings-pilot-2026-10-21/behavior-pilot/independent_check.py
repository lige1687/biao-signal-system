"""Independent reconciliation against source tables; does not import run.py."""
import collections
import csv
import hashlib
import json
import math
import pathlib
import re
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
plan = json.loads((ROOT / 'storage-plan.json').read_text())
out = pathlib.Path(plan['output'])
assert out.stat().st_dev == plan['external_device']
summary_path = out / 'behavior-pilot/summary.json'
summary = json.loads(summary_path.read_text())
rows = list(csv.DictReader((out / 'behavior-pilot/security-rows.csv').open()))
records = summary['fund_interval_rows']
accessions = {r[k] for r in records for k in ('start_accession', 'end_accession')}
lookup = {(r['series_id'], r['start_report_date']): r['start_accession'] for r in records}
lookup.update({(r['series_id'], r['end_report_date']): r['end_accession'] for r in records})
info = {}
raw = collections.defaultdict(list)
columns = ['ACCESSION_NUMBER', 'ISSUER_CUSIP', 'ISSUER_LEI', 'ISSUER_TITLE', 'BALANCE',
           'UNIT', 'CURRENCY_CODE', 'CURRENCY_VALUE', 'ASSET_CAT', 'INVESTMENT_COUNTRY',
           'PAYOFF_PROFILE', 'IS_RESTRICTED_SECURITY', 'FAIR_VALUE_LEVEL', 'DERIVATIVE_CAT']
for quarter in range(1, 5):
    base = out / 'mirror-trader298'
    for r in pq.ParquetFile(base / f'FUND_REPORTED_INFO/year=2025/quarter={quarter}/data.parquet').read().to_pylist():
        if r['ACCESSION_NUMBER'] in accessions:
            info[r['ACCESSION_NUMBER']] = r
    pf = pq.ParquetFile(base / f'FUND_REPORTED_HOLDING/year=2025/quarter={quarter}/data.parquet')
    for block in pf.iter_batches(columns=columns, batch_size=100000):
        selected = block.filter(pc.is_in(block.column(0), value_set=pa.array(sorted(accessions))))
        for r in selected.to_pylist():
            raw[r['ACCESSION_NUMBER']].append(r)

def norm(value):
    s = ' '.join(str(value).upper().split()) if value is not None else ''
    return None if s in ('', 'NA', 'N/A', 'NONE') else s

def eligible(r):
    fixed = {'ASSET_CAT':'EC', 'UNIT':'NS', 'CURRENCY_CODE':'USD', 'INVESTMENT_COUNTRY':'US',
             'PAYOFF_PROFILE':'Long', 'IS_RESTRICTED_SECURITY':'N', 'FAIR_VALUE_LEVEL':'1'}
    return (all(str(r[k]) == v for k,v in fixed.items()) and
            norm(r['DERIVATIVE_CAT']) is None and r['BALANCE'] is not None and
            math.isfinite(float(r['BALANCE'])) and float(r['BALANCE']) > 0 and
            bool(re.fullmatch('[A-Z0-9]{9}', str(r['ISSUER_CUSIP']))))

hold = {}
for acc, source_rows in raw.items():
    buckets = collections.defaultdict(list)
    for r in source_rows:
        if eligible(r): buckets[r['ISSUER_CUSIP']].append(r)
    hold[acc] = {}
    for cusip, bunch in buckets.items():
        leis = {norm(r['ISSUER_LEI']) for r in bunch} - {None}
        titles = {norm(r['ISSUER_TITLE']) for r in bunch} - {None}
        if len(leis) > 1 or len(titles) > 1: continue
        hold[acc][cusip] = dict(q=sum(float(r['BALANCE']) for r in bunch),
                               value=sum(float(r['CURRENCY_VALUE']) for r in bunch),
                               lei=next(iter(leis), None), title=next(iter(titles), None))

def near(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-10), (a,b)

computed = collections.defaultdict(list)
for row in rows:
    sid, before, after, c = (row[k] for k in ('series_id','start_report_date','end_report_date','cusip'))
    old, new = hold[lookup[(sid,before)]][c], hold[lookup[(sid,after)]][c]
    near(old['q'], row['opening_quantity']); near(new['q'], row['ending_quantity'])
    for field in ('lei','title'):
        assert old[field] is None or new[field] is None or old[field] == new[field]
    other_ids = row['peer_series_ids'].split('|')
    assert sid not in other_ids and len(set(other_ids)) == int(row['peer_count'])
    peer_changes = []
    for other in other_ids:
        a,b = hold[lookup[(other,before)]][c], hold[lookup[(other,after)]][c]
        assert re.fullmatch('[A-Z0-9]{20}', old['lei'] or '') and old['lei'] == a['lei']
        assert re.fullmatch('[A-Z0-9]{20}', new['lei'] or '') and new['lei'] == b['lei']
        for field in ('lei','title'):
            assert a[field] is None or b[field] is None or a[field] == b[field]
        peer_changes.append(math.log(b['q']/a['q']))
    own = math.log(new['q']/old['q']); peer = sum(peer_changes)/len(peer_changes)
    near(own,row['own_log_quantity_change']); near(peer,row['leave_own_out_peer_mean_log_change'])
    near(own-peer,row['relative_log_change'])
    computed[(sid,before,after)].append((own,peer,old['value']))

for record in records:
    key = tuple(record[k] for k in ('series_id','start_report_date','end_report_date'))
    local = computed[key]; assert len(local) == record['matched_securities']
    a,b = record['start_accession'],record['end_accession']
    sales = sum(float(info[b][f'SALES_FLOW_MON{i}']) for i in (1,2,3))
    redemption = sum(float(info[b][f'REDEMPTION_FLOW_MON{i}']) for i in (1,2,3))
    reinvest = sum(float(info[b][f'REINVESTMENT_FLOW_MON{i}']) for i in (1,2,3))
    nav = float(info[a]['NET_ASSETS'])
    near(100*(sales-redemption)/nav,record['net_flow_pct_prior_nav'])
    near(reinvest,record['reinvestment_3m_separate'])
    own = sum(x[0] for x in local)/len(local); peer = sum(x[1] for x in local)/len(local)
    near(math.expm1(own-peer),record['relative_multiplicative_adjustment'])
    value = sum(x['value'] for x in hold[a].values())
    near(sum(x[2] for x in local)/value,record['opening_eligible_value_share_matched_with_nonnull_values'])
    near(100*value/nav,record['opening_eligible_equity_value_pct_prior_fund_nav'])
    assert not record['opening_eligible_value_rows_missing'] and not record['matched_value_rows_missing']

result = {'status':'pass','fund_intervals':len(records),'security_rows':len(rows),
          'source':'independent source-table read; no run.py import',
          'checks':['all quantities and peer identities','self excluded','own and peer log changes',
                    'all 12 three-month net flows and reinvestments','all relative adjustments',
                    'all opening-value coverage and NAV shares'],
          'summary_sha256':hashlib.sha256(summary_path.read_bytes()).hexdigest(),
          'script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
(HERE/'independent-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
