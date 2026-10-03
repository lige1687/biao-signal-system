"""Read-only SP500 source qualification. No future returns or production imports."""
from pathlib import Path
import csv, datetime, hashlib, json, sqlite3

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
DB=Path('/Users/yongbiaoli/.lei_signal_lab/lab.db')
QUERY="SELECT * FROM market_breadth_snapshots WHERE market_id='SP500' ORDER BY as_of, universe_version"
con=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
con.execute('PRAGMA query_only=ON');con.execute('BEGIN');con.row_factory=sqlite3.Row
rows=[dict(r) for r in con.execute(QUERY)]
con.rollback();con.close()
assert rows
snapshot=OUT/'us-sp500-source-snapshot.csv'
assert not snapshot.exists(), 'Source snapshots must not overwrite.'
with snapshot.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

good=[r for r in rows if r['universe_version']=='backfill_v1']
summary={'source_database':str(DB),'query':QUERY,'snapshot_file':snapshot.name,
 'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'transaction':'consistent SQLite read transaction, query_only; no DB writes',
 'read_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':len(rows),'source_dates':len({r['as_of'] for r in rows}),
 'start':min(r['as_of'] for r in rows),'end':max(r['as_of'] for r in rows),'backfill_rows':len(good),'backfill_end':max(r['as_of'] for r in good),
 'source_counts':{},'historical_available_at_proven':False,'historical_membership_proven':False,'new_return_experiments':0,'fields':{}}
for r in rows:
    key=r['source_kind']+'|'+r['data_status']+'|'+r['universe_version'];summary['source_counts'][key]=summary['source_counts'].get(key,0)+1
for window in [20,50,200]:
    key=f'breadth_{window}';vals=[r[key] for r in rows if r[key] is not None]
    bins=[0]*10
    for v in vals:
        assert 0<=v<=100
        bins[min(9,int(v//10))]+=1
    pairs=[(r[f'eligible_{window}'],r['constituent_count'],r[f'coverage_{window}']) for r in good]
    residual=max(abs(e/c-coverage) for e,c,coverage in pairs if c)
    assert residual<1e-12
    summary['fields'][key]={'non_null_rows':len(vals),'null_rows':len(rows)-len(vals),'min_percent':min(vals),'max_percent':max(vals),'count_fixed_10pp_intervals':bins,
      'coverage_min':min(r[f'coverage_{window}'] for r in good),'coverage_max':max(r[f'coverage_{window}'] for r in good),
      'below_90pct_coverage_rows':sum(r[f'coverage_{window}']<.9 for r in good),'coverage_count_fraction_max_difference':residual}
summary['source_available_at_equals_as_of_rows']=sum(r['available_at']==r['as_of'] for r in rows)
summary['timestamp_timezone_rows']=sum('T' in r['available_at'] and ('+' in r['available_at'] or r['available_at'].endswith('Z')) for r in rows)
summary['distinct_constituent_counts_backfill']=sorted({r['constituent_count'] for r in good})
summary['earliest_row']={k:good[0][k] for k in ['as_of','available_at','constituent_count','eligible_20','eligible_50','eligible_200','coverage_20','coverage_50','coverage_200','provenance','run_id']}
summary['original_LEI_threshold_only']={'low_20_and_50_count':sum(r['breadth_20'] is not None and r['breadth_50'] is not None and r['breadth_20']<=15 and r['breadth_50']<=15 for r in good),
 'high_20_and_50_count':sum(r['breadth_20'] is not None and r['breadth_50'] is not None and r['breadth_20']>=85 and r['breadth_50']>=85 for r in good),
 'not_interpretation':'Counts only for the present-member backfill; not genuine historical SP500 triggers or independent evidence.'}
source_paths=['scripts/backfill_sp500_breadth.py','scripts/backfill_breadth_full.py','scripts/archive/ingest_sp500_breadth_to_sqlite.py','scripts/breadth_data.py','tests/fixtures/market_context/universes/SP500.parquet']
manifest=[]
for rel in source_paths:
    p=ROOT/rel
    if p.exists():
        b=p.read_bytes();manifest.append({'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
summary['qualification_verdict']='blocked_for_historical_SP500_prediction: current members backfilled; per-window denominators; synthetic date-only arrival; nonvalidated price actions'
summary['meaningful_available_use']='Audit and descriptive map of the frozen current-member group; not the historical SP500 market.'
(OUT/'us-source-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(OUT/'us-source-manifest.json').write_text(json.dumps({'files':manifest,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'snapshot_sha256':summary['snapshot_sha256']},ensure_ascii=False,indent=2))
print(json.dumps({k:summary[k] for k in ['rows','source_dates','start','end','backfill_rows','backfill_end','fields','earliest_row','source_available_at_equals_as_of_rows','qualification_verdict']},ensure_ascii=False,indent=2))
