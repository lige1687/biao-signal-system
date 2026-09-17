"""Offline independent source and pipeline checks; temporary DB, no external calls."""
from pathlib import Path
import sys,json,tempfile
from unittest.mock import patch
from datetime import UTC,datetime
W=Path('/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/agents/news-agent-20260917')
sys.path.insert(0,str(W/'src'))
from lei_signal.newsfeed.sources.fed import collect_fed_press
from lei_signal.newsfeed.sources import NewsSourceError
from lei_signal.newsfeed.pipeline import run_pipeline
from lei_signal.newsfeed.service import NewsfeedService
from lei_signal.newsfeed.store import NewsStore
raw=W/'docs/experiments/raw/agent-news-ark-2026-09-17'
xml=(raw/'fed-press-monetary-live-2026-09-17.xml').read_text()
checks=[]
def check(name,actual,expected): checks.append(dict(name=name,actual=actual,expected=expected,passed=actual==expected))
items,wm=collect_fed_press(since_iso='2026-09-14T00:00:00+00:00',fetcher=lambda *_:xml)
check('real_feed_item_count',len(items),2)
stmt=next(x for x in items if 'FOMC statement' in x.title)
check('real_statement_utc',datetime.fromisoformat(stmt.published_at).astimezone(UTC).isoformat(),'2026-09-16T18:00:00+00:00')
check('real_feed_replay_no_new',len(collect_fed_press(since_iso=wm,fetcher=lambda *_:xml)[0]),0)
valid_item='<item><title>Federal Reserve issues FOMC statement</title><link>https://www.federalreserve.gov/x.htm</link><pubDate>Wed, 16 Sep 2026 18:00:00 GMT</pubDate></item>'
invalid_item='<item><title>Federal Reserve issues FOMC statement</title><link>https://www.federalreserve.gov/y.htm</link><pubDate>not-a-time</pubDate></item>'
for name,body in [('html_200','<html><body>Service unavailable</body></html>'),('missing_fields','<rss><channel><item><title>missing date and url</title></item></channel></rss>'),('invalid_times','<rss><channel>'+invalid_item+'</channel></rss>')]:
 try:
  actual=collect_fed_press(since_iso=None,fetcher=lambda *_, b=body:b)
  result='accepted_empty' if not actual[0] else 'accepted_items'
 except NewsSourceError: result='source_error'
 check(name,result,'source_error')
with tempfile.TemporaryDirectory(prefix='news-controller-repair1-') as td:
 cfg={'lookback_days':7,'fed_press':{'enabled':True},'bili_ups':[],'rss_feeds':[],'gnews_queries':[]}
 body='<rss><channel>'+valid_item+invalid_item+'</channel></rss>'
 db=Path(td)/'partial.db'
 with patch('lei_signal.newsfeed.pipeline.collect_eastmoney',return_value=([],None)),patch('lei_signal.newsfeed.pipeline.collect_sina',return_value=([],None)),patch('lei_signal.newsfeed.sources.fed._default_fetch',return_value=body):
  run=run_pipeline(db,config=cfg,no_llm=True)
 svc=NewsfeedService(db_path=str(db)); brief=svc.major_events_brief(days=7)
 check('partial_feed_health_not_fresh',brief['health']['availability']!='fresh',True)
 s=NewsStore(db); row=dict(s.latest_run()); count=s.counts(); s.close()
 checks.append({'name':'partial_feed_run_detail','observed':{'health':brief['health'],'run':row,'counts':count}})
print(json.dumps({'checks':checks,'passed':sum(x.get('passed',False) for x in checks),'total':sum('passed' in x for x in checks)},ensure_ascii=False,indent=2))
