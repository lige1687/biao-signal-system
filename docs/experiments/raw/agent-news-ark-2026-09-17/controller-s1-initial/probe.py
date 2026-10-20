"""Independent offline probes. No product LLM/network/push; only temporary DBs."""
import json, sys, tempfile
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch
W = Path('/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/agents/news-agent-20260917')
sys.path.insert(0, str(W / 'src'))
from lei_signal.newsfeed.health import build_news_health
from lei_signal.newsfeed.event_context import build_event_reference
from lei_signal.newsfeed.sources.fed import parse_fed_pubdate, collect_fed_press
from lei_signal.newsfeed.store import NewsStore
from lei_signal.newsfeed.service import NewsfeedService
from lei_signal.newsfeed.pipeline import run_pipeline
results = []
def check(case, actual, expected):
    results.append(dict(case=case,actual=actual,expected=expected,passed=actual==expected))
now = '2026-09-17T12:00:00+08:00'
run = dict(status='ok',finished_at='2026-09-17T11:00:00+08:00',stats={'stages': {'collect': {'status':'ok'}}})
def health(r=run, **kw):
    args=dict(latest_run=r, latest_success_at=None, latest_item_at=None,unscored_count=0, now=now,max_age_hours=26)
    args.update(kw)
    return build_news_health(**args)
check('healthy_empty',health()['availability'],'fresh')
check('legacy_no_stage',health(dict(status='ok',finished_at=run['finished_at']))['availability'],'unknown')
check('failed_stage_not_overridden_by_ok',health({**run,'stats':{'stages':{'collect':{'status':'failed'}}}})['availability'],'failed')
check('future_latest_item',health(latest_item_at='2026-09-18T11:00:00+08:00')['availability'],'unknown')
check('invalid_success_timezone',health(latest_success_at='2026-09-17T11:00:00')['availability'],'unknown')
check('26h_1m_is_stale',health({**run,'finished_at':'2026-09-16T09:59:00+08:00'})['availability'],'stale')
check('4m_future_run',health({**run,'finished_at':'2026-09-17T12:04:00+08:00'})['availability'],'unknown')
base = dict(source='fed',source_name='美联储官网',url='https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm',category='macro',title='Federal Reserve issues FOMC statement',summary='',content=None,published_at=now,dedupe_key='probe')
check('statement',build_event_reference(base)['event_stage'],'official_result')
for title in ['Speech by Powell on the FOMC statement','Minutes of the FOMC statement discussion']:
    check(title,build_event_reference({**base,'title':title})['event_stage'],'commentary')
check('EST_explicit_offset',parse_fed_pubdate('Wed, 16 Sep 2026 14:00:00 EST').astimezone(UTC).isoformat(),'2026-09-16T19:00:00+00:00')
check('EDT_explicit_offset',parse_fed_pubdate('Wed, 16 Sep 2026 14:00:00 EDT').astimezone(UTC).isoformat(),'2026-09-16T18:00:00+00:00')
xml='<rss><channel><item><title>Federal Reserve issues FOMC statement</title><link>https://www.federalreserve.gov/x.htm</link><pubDate>Wed, 16 Sep 2026 18:00:00 GMT</pubDate></item></channel></rss>'
items,_=collect_fed_press(since_iso='2026-09-16T19:00:00+00:00',fetcher=lambda *a:xml)
check('watermark_compares_instants',len(items),0)
with tempfile.TemporaryDirectory(prefix='controller-news-') as td:
    db=Path(td)/'visibility.db'
    s=NewsStore(db); s.insert_items([{**base,'published_at':datetime.now().astimezone().isoformat()}]); s.close()
    svc=NewsfeedService(db_path=str(db))
    check('official_unscored_visible',len(svc.major_events_brief()['items']),1)
    s=NewsStore(db); i=s.fetch_unscored()[0]['id']; s.apply_scores([dict(id=i,category='macro',importance=6,direction='neutral',symbols=[],note='mock')]); s.close()
    check('official_scored6_still_visible',len(svc.major_events_brief()['items']),1)
    db=Path(td)/'exception.db'
    with patch('lei_signal.newsfeed.pipeline._collect_all',return_value=({'fed':0},[],{'fed':{'ok':True}})), patch('lei_signal.newsfeed.pipeline._score_all',side_effect=RuntimeError('injected score failure')), patch('lei_signal.newsfeed.push.push_daily_brief') as push:
        try: run_pipeline(db,config={'lookback_days':3})
        except RuntimeError: pass
        check('no_external_push',push.call_count,0)
    s=NewsStore(db); row=dict(s.latest_run()); s.close()
    check('exception_run_finalized',row['status']!='running',True)
    stats=json.loads(row.get('stats_json') or '{}')
    check('exception_score_failure_persisted',stats.get('stages',{}).get('score',{}).get('status'),'failed')
print(json.dumps({'probes':results,'passed':sum(r['passed'] for r in results),'total':len(results)},ensure_ascii=False,indent=2))
