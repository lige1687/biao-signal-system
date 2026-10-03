"""Read-only inventory of the existing sentiment family. No market downloads."""
from pathlib import Path
import csv
import hashlib
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
CACHE = Path('/Users/yongbiaoli/.lei_signal_lab/cache')
RESEARCH = CACHE / 'sentiment_research_2026-09'
manifest = []

def bind(path):
    path = Path(path)
    b = path.read_bytes()
    manifest.append({'path': str(path), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
    return path

inventory = []
for path, datecol in [
    (ROOT/'data/sentiment/naaim.csv', 'survey_week'),
    (ROOT/'data/sentiment/aaii.csv', 'survey_week'),
    (RESEARCH/'naaim_clean.csv','date'), (RESEARCH/'aaii_clean.csv','reported'),
    (RESEARCH/'margin_history.csv','date'), (RESEARCH/'px_SPY.csv','Date'),
    (RESEARCH/'px_QQQ.csv','Date'), (RESEARCH/'apx_510300_SS.csv','date'),
    (RESEARCH/'apx_510500_SS.csv','date'), (RESEARCH/'apx_159915_SZ.csv','date'),
    (RESEARCH/'breadth_sp500_200dma.csv','date'),
    (RESEARCH/'breadth_a_share_200dma.csv','date'),
]:
    if not path.exists():
        inventory.append({'path':str(path),'status':'missing'}); continue
    d = pd.read_csv(bind(path))
    r = {'path':str(path),'rows':len(d),'columns':list(d),'start':str(d[datecol].min()),
         'end':str(d[datecol].max()),'duplicate_dates':int(d[datecol].duplicated().sum()),
         'missing':{k:int(v) for k,v in d.isna().sum().items() if v}}
    if 'available_at' in d:
        r['explicit_timezone_rows'] = int(d.available_at.str.contains(r'(?:Z|[+-]\d\d:\d\d)$',regex=True).sum())
        r['source_counts'] = d.source.value_counts().to_dict()
        r['license_counts'] = d.license_status.value_counts().to_dict()
    if 'bullish' in d:
        r['composition_sum_min_max'] = [float(d[['bullish','neutral','bearish']].sum(axis=1).min()),float(d[['bullish','neutral','bearish']].sum(axis=1).max())]
    col = 'naaim' if 'naaim' in d else 'exposure_index' if 'exposure_index' in d else None
    if col:
        r['value_min_max'] = [float(d[col].min()),float(d[col].max())]
        r['values_above_100'] = int((d[col]>100).sum())
    inventory.append(r)

hist = json.loads(bind(CACHE/'sector_trend_history.json').read_text())
dates = sorted({r['date'] for r in hist})
all_codes = sorted({c for r in hist for c in r['boards']})
board_rows = []
for r in hist:
    for c,v in r['boards'].items():
        board_rows.append({'date':r['date'],'code':c, **{k:v.get(k) for k in ['close','b20','b50','b200','stage','rs_pctile']}})
bh = pd.DataFrame(board_rows)
sector = {'history_dates':len(dates),'start':dates[0],'end':dates[-1],'boards':len(all_codes),
          'fields_non_null':bh.notna().sum().to_dict(),
          'historical_membership': 'not recorded in this file',
          'row_available_at': 'not recorded in this file'}
flow_metrics = []
flows = {}
for fname in ['tx_sector_flow_pilot.json','sector_flow_history.json']:
    raw = json.loads(bind(CACHE/fname).read_text())
    boards = raw.get('boards',raw)
    pts = [{'code':c, **p} for c,rows in boards.items() for p in rows]
    df = pd.DataFrame(pts)
    flows[fname] = df
    n = df.groupby('date').code.nunique()
    medium = df['mid_yi'] if 'mid_yi' in df else df['medium_yi']
    residual = df.main_yi + medium + df.small_yi
    known = residual.dropna()
    flow_metrics.append({'file':fname,'rows':len(df),'boards':df.code.nunique(),
        'dates':df.date.nunique(),'start':df.date.min(),'end':df.date.max(),
        'board_count_daily_min_max':[int(n.min()),int(n.max())],
        'residual_main_plus_medium_plus_small_max_abs_yi':float(known.abs().max()),
        'residual_within_0_02_yi_fraction':float((known.abs()<=0.020000001).mean()),
        'duplicate_date_board':int(df.duplicated(['date','code']).sum()),
        'available_at_present':'available_at' in df})
a,b=flows.values()
overlap=a[['date','code','small_yi']].merge(b[['date','code','small_yi']],on=['date','code'],suffixes=('_tx','_em'))
delta=(overlap.small_yi_tx-overlap.small_yi_em).dropna()
sector['flow_sources']=flow_metrics
sector['flow_overlap']={'rows':len(overlap),'small_value_disagree_rows':int((delta.abs()>0.01000001).sum()),'small_max_abs_difference_yi':float(delta.abs().max())}
bh[['date','code','close','b50']].to_csv(OUT/'board_coverage.csv',index=False)
coverage=[]
for code in ['BK1036','BK0478']:
    merged=pd.concat([a[a.code==code],b[b.code==code]]).drop_duplicates(['date','code'],keep='first').set_index('date')
    axis=pd.Index(dates)
    vals=merged.small_yi.reindex(axis)
    full=vals.notna().rolling(140,min_periods=140).sum().eq(140)
    bp=bh[bh.code==code].set_index('date').reindex(axis)
    coverage.append({'code':code,'total_flow_rows':len(merged),'flow_on_board_axis':int(vals.notna().sum()),'continuous_140_rows_on_board_axis':int(full.sum()),'full_windows_with_price_b50':int((full & bp.close.notna() & bp.b50.notna()).sum())})
sector['fixed_prior_pair_coverage']=coverage
j=json.loads(bind(CACHE/'sentiment_signal_journal.json').read_text()).get('records',[])
sector['signal_journal']={'rows':len(j),'dates':[r['date'] for r in j]}

definitions=json.loads(bind(ROOT/'docs/research/definitions.v1.json').read_text())
sector['definition_registry_version']=definitions.get('version')
for p in ['docs/trading-spec-v1.md','configs/rules.v1.yaml','configs/rules.v2.yaml',
          '.claude/skills/macd-reading/SKILL.md','docs/plan-sector-trend-page.md',
          'src/lei_signal/market_context/sentiment.py','src/lei_signal/market_context/market_mood.py',
          'src/lei_signal/market_context/sentiment_signals.py','scripts/fetch_sentiment_weekly.py',
          'configs/sentiment_evidence.json','docs/research/experiment-backtest-principles.md',
          'docs/research/ai-execution-contract.md','docs/research/definition-standard.md',
          'docs/research/experiment-report-template.md','docs/research/factor-increment-evidence-standard.md',
          'docs/research/research-question-method-standard.md']:
    bind(ROOT/p)
result={'inventory':inventory,'sector':sector,'notes':['Counts do not prove source history, licence, original publication time or investability.','Board-history date axis is a quoted-data axis, not an independently verified exchange calendar.','Cache reads only; production loaders and network-capable fetch functions not invoked.']}
(OUT/'input-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
(OUT/'source-manifest.json').write_text(json.dumps({'files':manifest},ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
