"""Controller offline retry checks: corrected missing item is older than valid item."""
import sys,json,tempfile
from pathlib import Path
from unittest.mock import patch
W=Path('/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/agents/news-agent-20260917')
sys.path.insert(0,str(W/'src'))
from lei_signal.newsfeed.pipeline import run_pipeline
from lei_signal.newsfeed.store import NewsStore
from lei_signal.newsfeed.service import NewsfeedService
from lei_signal.newsfeed.sources.fed import collect_fed_press
out=[]
def check(name,actual,expected):out.append(dict(name=name,actual=actual,expected=expected,passed=actual==expected))
def item(url='x',title='Federal Reserve issues FOMC statement',date='Wed, 16 Sep 2026 18:00:00 GMT'):
 return f'<item><title>{title}</title><link>{("https://www.federalreserve.gov/"+url+".htm") if url else ""}</link><pubDate>{date}</pubDate></item>'
def feed(*items): return '<rss><channel>'+''.join(items)+'</channel></rss>'
items,wm=collect_fed_press(since_iso=None,fetcher=lambda *_:feed())
check('valid_empty_success',(len(items),wm),(0,None))
for kind,bad in [('missing_title',item('y',title='')),('missing_link',item('',date='Wed, 16 Sep 2026 17:00:00 GMT')),('bad_date',item('y',date='invalid')),('future_date',item('y',date='Thu, 16 Sep 2099 18:00:00 GMT'))]:
 with tempfile.TemporaryDirectory(prefix='news-retry-controller-') as td:
  db=Path(td)/'test.db'; s=NewsStore(db); original='2026-09-16T16:00:00+00:00'; s.set_watermark('fed',original);s.close()
  cfg={'lookback_days':7,'fed_press':{'enabled':True},'bili_ups':[],'rss_feeds':[],'gnews_queries':[]}
  bodies=[feed(item(),bad),feed(item(),item('y',date='Wed, 16 Sep 2026 17:00:00 GMT')),feed(item(),item('y',date='Wed, 16 Sep 2026 17:00:00 GMT'))]
  with patch('lei_signal.newsfeed.pipeline.collect_eastmoney',return_value=([],None)),patch('lei_signal.newsfeed.pipeline.collect_sina',return_value=([],None)),patch('lei_signal.newsfeed.sources.fed._default_fetch',side_effect=bodies),patch('lei_signal.newsfeed.pipeline.score_items',side_effect=AssertionError('LLM forbidden')),patch('lei_signal.newsfeed.push.push_daily_brief',side_effect=AssertionError('push forbidden')):
   first=run_pipeline(db,config=cfg,no_llm=True);s=NewsStore(db)
   check(kind+'_partial',first['status'],'partial')
   check(kind+'_kept_valid',s.counts()['total'],1)
   check(kind+'_watermark_unchanged',s.get_watermark('fed'),original)
   record=dict(s.latest_run());s.close()
   check(kind+'_persisted_failure','fed' in record['errors_json'] and '不可用' in record['errors_json'],True)
   check(kind+'_health',NewsfeedService(db_path=str(db)).major_events_brief(days=7)['health']['availability'],'partial')
   second=run_pipeline(db,config=cfg,no_llm=True)
   check(kind+'_recovered',second['status'],'ok')
   check(kind+'_only_missing_inserted',second['inserted'],1)
   third=run_pipeline(db,config=cfg,no_llm=True);s=NewsStore(db)
   check(kind+'_no_duplicates',(third['inserted'],s.counts()['total']),(0,2));s.close()
print(json.dumps(dict(checks=out,passed=sum(x['passed'] for x in out),total=len(out)),ensure_ascii=False,indent=2))
assert all(x['passed'] for x in out)
