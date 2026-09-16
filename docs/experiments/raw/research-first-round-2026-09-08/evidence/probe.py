"""Isolated audit: source snapshot imports, synthetic prices, temp SQLite; no production writes."""
from pathlib import Path
import ast,dataclasses,hashlib,importlib.util,io,json,os,sys,tempfile
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import patch
OUT=Path(__file__).resolve().parent
SNAP=OUT/'snapshot'
sys.dont_write_bytecode=True
sys.path.insert(0,str(SNAP/'src'))
import pandas as pd
import numpy as np
from lei_signal import data_provenance as dp
from lei_signal.dca.state import compute_state
from lei_signal.copilot import winrate
results={}
def load_file(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
builder=load_file('frozen_builder',SNAP/'scripts/build_module_winrate.py')
with tempfile.TemporaryDirectory(prefix='lei-research-evidence-') as tmp:
 tmp=Path(tmp)
 outputs=[]
 for order in [('runA:A','runB:B'),('runB:B','runA:A')]:
  builder.OUT=tmp/'winrate.json'
  def fake(run):return [{'symbol':'FIXTURE','entry_date':'2026-08-03','r_net':2.0 if run=='runA' else -1.0}]
  with patch.object(builder,'fetch_trades',side_effect=fake),patch.object(sys,'argv',['builder',*order]),redirect_stdout(io.StringIO()):builder.main()
  outputs.append(json.loads(builder.OUT.read_text()))
 results['module_dedup_order']={'orders':[['A','B'],['B','A']],'keys':[list(x['entries']) for x in outputs],'same_output':outputs[0]==outputs[1],'synthetic_only':True}
 with patch.object(winrate,'_load',return_value=outputs[0]): answer=winrate.winrate_for('FIXTURE','A')
 results['discussion_winrate_shape']={'value':answer,'required_match_fields_missing':[k for k in ['entry_variant','exit_variant','condition_definition','holding_horizon','rule_version','data_window','fees','source_run_ids','compatibility'] if k not in answer]}
 bars=pd.DataFrame({'close':np.linspace(100,140,260)},index=pd.bdate_range('2025-08-04',periods=260));bars.iloc[-50,0]=np.nan
 results['internal_missing_price']=compute_state('FIXTURE','合成测试',bars,None).to_dict()
 policy=dp.SourcePolicy('cn',basis='synthetic test only',verified=True)
 cal=dp.reference_calendar('cn',pd.bdate_range('2026-07-01','2026-08-03'))
 results['outdated_calendar_weekend']={d:dp.assess_freshness('2026-08-03','cn',now=datetime.fromisoformat(d),calendar=cal,policy=policy).to_dict() for d in ['2026-09-12T12:00:00','2026-09-14T08:00:00']}
 # Select existing independently authored q1/q3/q4 probes; no footer execution, no real DB.
 p=SNAP/'docs/experiments/raw/agent-closeout-controller-review-2026-09-08/reproduce.py'
 tree=ast.parse(p.read_text()); body=[]
 for n in tree.body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sources' for t in n.targets): break
  body.append(n)
 ns={'__file__':str(p),'__name__':'frozen_prior_probes'}
 exec(compile(ast.Module(body=body,type_ignores=[]),str(p),'exec'),ns)
 for name in ['q1','q3','q4']:
  c=ns['connect'](tmp/f'{name}.db')
  try:
   ok,detail=ns[name](c,tmp);results[name]={'accepted':bool(ok),'detail':detail,'qualification':'Snapshot caught ongoing engineering work; not an acceptance verdict on subsequently changed production.'}
  except Exception as exc:results[name]={'probe_error':f'{type(exc).__name__}: {exc}','qualification':'Intermediate source snapshot; no product verdict.'}
  finally:c.close()
results['assertions']={'missing_price_preserves_window':results['internal_missing_price']['deep20'] is None and results['internal_missing_price']['state_status']=='degraded','old_calendar_not_fresh':all(v['health']=='unknown' for v in results['outdated_calendar_weekend'].values()),'order_problem_reproduced':not results['module_dedup_order']['same_output']}
(OUT/'probe-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sourcepaths=[str(SNAP/'scripts/build_module_winrate.py'),str(SNAP/'src/lei_signal/copilot/winrate.py'),str(OUT/'probe-results.json')]
ev=dp.EvidenceRef(id='research-first-round:module-result-compatibility',source_path=sourcepaths,source_hash=[sha(p) for p in sourcepaths],source_version='2026-09-08-frozen-source',status='unverified',window='合成数据日期2026-08-03；非历史收益窗口',statistic_kind='implementation_probe',strategy_scope=('technical_execution',),limitations='只检查引用兼容性；未运行真实收益回测，不能用于当前机会胜率。',compatibility='unknown').to_dict()
dr=dp.MarketDataRef(source_id='probe.py:synthetic_prices',instrument_id='FIXTURE',market='synthetic',observed_at=None,available_at=None,generated_at=None,last_valid_at=None,health='unknown',reason='合成最小复例，不是市场行情；不能证明当前状态').to_dict()
rr=dp.ruleset_ref().to_dict()
card={'evidence_refs':[ev],'data_refs':[dr],'rule_refs':[rr],'research_extension':{'question':'同一标的A模块旧成绩，能否回答换退出方法后的本次胜率？','plain_conclusion':'不能。现表没有完整方法配置，且同日同标的不同模块会因输入顺序丢失。','claim_type':'fact','support_state':'evidence_insufficient','independent_review':'本轮独立合成复例；总控尚未验收，未验证收益。','source_run_ids':[],'trade_count':None,'independent_event_count':None,'unknown_reason':'合成程序例证，不是实盘或历史交易样本。','matching':{'symbol':'FIXTURE','module':'A','entry_variant':None,'exit_variant':None,'condition_definition':None,'holding_horizon':None,'rule_version':'当前规则仅证明读取版本，不能补作旧回测版本','fees':None,'data_window':None},'can_answer':['这份旧表为什么不够回答新退出问题','应补齐哪些配置与原始结果'], 'cannot_answer':['现在是否该买','新退出的胜率','与情绪基本面叠加后的胜率'], 'related_transfer_risk':{'dca_ambush':'configs/dca_evidence.json 的 ambush_template 混有统一退出成绩与分标的菜单；条目自己已注明未联合复跑。','dca_assembly':'combos.cross_asset_4_standard 引用第18轮原始结果；新代码修复不会自动更新冻结旧成绩，需重新复现并登记版本。'}}}
# Round-trip uses actual dataclass fields, retaining public aliases unchanged.
for key,cls in [('evidence_refs',dp.EvidenceRef),('data_refs',dp.MarketDataRef),('rule_refs',dp.RuleRef)]:
 fields={f.name for f in dataclasses.fields(cls)}
 for value in card[key]:
  restored=cls(**{k:v for k,v in value.items() if k in fields}).to_dict();assert restored==value,(key,restored,value)
assert json.loads(json.dumps(card,ensure_ascii=False,allow_nan=False))==card
(OUT/'evidence_card.json').write_text(json.dumps(card,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'assertions':results['assertions'],'q_probes':{k:v.get('accepted',v.get('probe_error')) for k,v in results.items() if k.startswith('q')},'public_dataclass_roundtrip':True},ensure_ascii=False,indent=2))
