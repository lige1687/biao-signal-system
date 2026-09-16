from pathlib import Path
import json,hashlib,shutil,datetime,sys
P=Path(__file__).resolve().parent;ROOT=P.parents[3];SRC=Path('/Users/yongbiaoli/lei-signal-sync');CACHE=Path('/Users/yongbiaoli/.lei_signal_lab/cache');POOL=CACHE.parent/'backtest_pool'
def h(f):return hashlib.sha256(f.read_bytes()).hexdigest()
files=[]
def cp(src,name):
 dst=P/'inputs'/name;dst.parent.mkdir(parents=True,exist_ok=True);before=h(src);shutil.copyfile(src,dst);assert before==h(src)==h(dst);files.append({'source':str(src),'snapshot':str(dst),'sha256':before})
for name in ['AGENTS.md','docs/trading-spec-v1.md','configs/rules.v1.yaml','configs/rules.v2.yaml','.claude/skills/macd-reading/SKILL.md','docs/plan-sector-trend-page.md','src/lei_signal/data/providers.py','src/lei_signal/data/cache.py','src/lei_signal/market_context/market_mood.py','src/lei_signal/market_context/sentiment_signals.py','src/lei_signal/market_context/sources.py','scripts/backfill_timing_data.py','scripts/dca_sector_sentiment_study.py','docs/experiments/dca-sector-sentiment-2026-09-08.md','docs/experiments/cross-market-pairing-ARCHIVE-2026-09-04.md','docs/experiments/cross-market-unify-ARCHIVE-2026-09-04.md','configs/sentiment_evidence.json']:
 if (SRC/name).exists():cp(SRC/name,'source/'+name)
for name in ['tx_sector_flow_pilot.json','sector_flow_history.json','sentiment_signal_journal.json','sector_trend_history.json','sector_members.json','us_sector_breadth.json','sector_trend_snapshot.json','cn_fund_flow_history.json','a_share_fund_flow_history.json']:
 if (CACHE/name).exists():cp(CACHE/name,'cache/'+name)
for name in ['510300','159915','518880','513100','SOXX','512480']:
 for ext in ['.parquet','.parquet.quarantined']:
  f=CACHE/'timing'/(name+ext)
  if f.exists():cp(f,'timing/'+f.name)
 for suffix in ['.SS','.SZ','']:
  for ext in ['.bars.parquet','.bars.meta.json']:
   f=POOL/(name+suffix+ext)
   if f.exists():cp(f,'pool/'+f.name)
cp(CACHE/'timing/SH000001.parquet','timing/SH000001.parquet')
cp(CACHE/'timing/breadth_cn_all.parquet','timing/breadth_cn_all.parquet')
prior=ROOT/'docs/experiments/raw/research-unified-2026-09-08'
cp(prior/'e01/run_e01.py','prior/e01.py');cp(prior/'e02/run_e02.py','prior/e02.py')
(P/'input-manifest.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'isolated_quarantine_read_only':True},ensure_ascii=False,indent=2))
(P/'scope.md').write_text('''# 本轮05—08推进范围

日期2026-09-08。用户明确说“5到8你继续做吧，按你的节奏来，不确定的来问我”。

05：在新研究副本补明确的未执行/取消安排记录，以合成反例检查，保留旧E01/E02封存结果；只做固定定义的边界检查，不挑新退出参数。
06：核元数据、隔离价格跳变与官方拆分公告，最多四个ETF的公开行情读取只存研究目录。先证明数据含义，再决定能否冻结实际产品的三对照；不把修正代理算新策略收益。
07：核完整四条件输入覆盖、120日计算要求、旧19轮和跨市场负面证据；最多固定一对产业关系的数据可行性，不开参数网格或新的收益假设。
08：完善解释/退出两份未来验证协议；用户偏好问题已发出，等待答复。未授权收费模型或自动观察，当前不调用。

服务层：资金用途与持有退出的研究核查、市场环境的独立说明；不改道路/路牌/技术判定、生产规则、真实账本、调度或文献学习页面。不将普通研究再次放回待授权。''')
sys.path.insert(0,str(ROOT/'src'));from lei_signal.api import upgrades_store as s
DB='/Users/yongbiaoli/.lei_signal_lab/system_upgrades.db';d=s.list_goals(DB);(P/'okr-before.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
for k in ['okr-e9ae686dca95','okr-02a9b781fd88','okr-12a112a12d19']:
 x=next(i for i in s.list_goals(DB)['items'] if i['id']==k)
 if x['status']=='approved':s.act_on_goal(DB,k,{'version':x['version'],'action':'start','note':'用户再次明确继续05—08；按本轮范围核数据与完善协议，不调用收费模型或改生产。','scope':''})
print('frozen files',len(files))
