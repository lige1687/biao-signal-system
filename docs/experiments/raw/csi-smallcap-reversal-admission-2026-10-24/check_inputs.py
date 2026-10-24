"""Read-only qualification of two existing source bundles; never computes factor effects."""
import csv, datetime, hashlib, json
from pathlib import Path
import pandas as pd
MAIN = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
OUT = Path(__file__).resolve().parent
CAT = MAIN / 'docs/experiments/raw/common-universe-acquisition-2026-10-24/coverage-manifest.json'
HIST = CAT.parent / 'cn/history-coverage.json'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
catalog = json.loads(CAT.read_text()); history = json.loads(HIST.read_text())
checks=[]; pools=[]; code_sets=[]
for u in catalog['universes']:
    if u['index_id'] not in ['000852','932000']: continue
    m=u['current_members']; bindings=[(m['source_file'],m['source_sha256']),(m['parsed_file'],m['parsed_sha256'])]
    for kind in ['parent_price','parent_full_return']:
        z=u[kind]; bindings += [(z['source_file'],z['source_sha256']),(z['parsed_file'],z['parsed_sha256'])]
    bindings += [(u['parent_price']['own_series_publication_evidence_file'],u['parent_price']['own_series_publication_evidence_sha256'])]
    for path,expected in bindings:
        actual=sha(path); assert actual==expected, path
        checks.append({'path':path,'sha256':actual,'bytes':Path(path).stat().st_size,'match':True})
    original=pd.read_excel(m['source_file'],dtype=str)
    code_col=next(c for c in original if 'Constituent Code' in c)
    code_set=set(original[code_col].str.zfill(6)); rows=list(csv.DictReader(open(m['parsed_file'])))
    assert code_set=={r['constituent_code'] for r in rows}
    assert len(code_set)==len(rows)==m['members']
    assert {r['snapshot_date'] for r in rows}=={'2026-10-23'}
    assert set(original['日期Date'])=={'20261023'}
    code_sets.append(code_set)
    dates={}
    for kind in ['parent_price','parent_full_return']:
        z=u[kind]; data=list(csv.DictReader(open(z['parsed_file'])))
        ds=[r['trade_date'] for r in data]
        assert ds==sorted(set(ds)) and len(ds)==z['rows']
        dates[kind]={'rows':len(ds),'first':ds[0],'last':ds[-1], 'pre_parent_launch_rows':sum(d<z['launch_date'] for d in ds), 'series_code':z['source_index_code'],'own_series_publication_verified':z['own_series_publication_date_verified']}
    events=[n for n in history['notice_sources'] if u['index_id'] in n['indices']]
    for n in events:
        assert sha(n['path'])==n['sha256']
        checks.append({'path':n['path'],'sha256':n['sha256'],'bytes':Path(n['path']).stat().st_size,'match':True})
    pools.append({'index_id':u['index_id'],'name':u['name'],'snapshot_date':'2026-10-23','snapshot_rows':len(rows),'unique_codes':len(code_set),'exchanges':original['交易所Exchange'].value_counts().to_dict(),'parent_launch':u['parent_price']['launch_date'],'benchmarks':dates,'bound_history_notice_count':len(events),'notices':[{'date':n['announcement_date'],'effective_date':n['effective_date'],'scope':n['scope'],'path':n['path']} for n in events],'verified_continuous_historical_formation_months':0,'monthly_reversal_effects_computed':0,'can_run_requested_constituent_backtest':False,'reason':'Only one current complete snapshot. Historical start/member transitions and exact effective dates do not form a qualified continuous chain in this delivered bundle. No mature forward period follows the current snapshot at cutoff.','planned_holding_window_if_membership_qualified': ['2015-01','2025-12'] if u['index_id']=='000852' else ['2023-09','2025-12']})
assert len(pools)==2
report={'schema':'smallcap-reversal-input-admission/1','checked_at':datetime.datetime.now().astimezone().isoformat(),'source_cutoff':'2026-10-23','catalog':{'path':str(CAT),'sha256':sha(CAT)},'history_receipt':{'path':str(HIST),'sha256':sha(HIST)},'pools':pools,'current_pool_overlap':len(code_sets[0]&code_sets[1]),'source_checks':checks,'checks_passed':len(checks),'factor_study_execution_status':'blocked','evidence_status':'not_evaluated','blocking_reason':'historical_point_in_time_membership_missing','source_requests':2,'new_market_downloads':0,'core_effect_attempts':0,'scope':'Readback of specified delivered bundle, not a proof that no public historical source exists. No index timing experiment substituted for stock selection.'}
(OUT/'admission.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pools':[{k:p[k] for k in ['index_id','snapshot_rows','exchanges','bound_history_notice_count','verified_continuous_historical_formation_months']} for p in pools],'source_checks':len(checks),'overlap':report['current_pool_overlap'],'status':report['factor_study_execution_status']},ensure_ascii=False))
