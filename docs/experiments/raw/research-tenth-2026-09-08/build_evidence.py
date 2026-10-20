from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent; ROOT=P.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
contract=P.parent/'research-fourth-2026-09-08/inputs/src/lei_signal/data_provenance.py'
nodes=[n for n in ast.parse(contract.read_text()).body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2')
exec(compile(ast.Module(body=nodes,type_ignores=[]),'existing_frozen_contract','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef']
cfg=P/'research-package/configs/rules.v2.yaml'
rule=R('__ruleset__','2.1.0',str(cfg),sha(cfg),definition_ref='策略§3.2/§9A/C/D/§10/§13；A3.0.0、C3.0.0、D2.0.0，未修改参数').to_dict()
cards=[]
items=[('acd-history-stability','后来行情会不会改写当年入场判断？','四只基金122个固定日期组合、三个模块共366次检查；A在两个日期删除四条确认并新增两条失败。C/D固定日期一致，但受控反例仍未通过。',['protocol.md','history-diagnostic/run-lock.json','history-diagnostic/summary.json','history-diagnostic/differences.json.gz','history-review/independent-driver-review.md'],'fixed_historical_event_prefix_diagnostic'),('acd-repair-contract','完整账户比较前要修复哪些具体问题？','保留已发布历史，重检失效底部，遵循最近已确认低点；区分可确定错误与等待期限等缺失定义。',['a-contract/contract.json','a-review/review-results.json','cd-contract/contract.json','cd-contract/synthetic-results.json','repair-acceptance-handoff.md'],'controlled_rule_counterexamples_and_definition_review')]
for key,q,c,paths,kind in items:
 fs=[P/p for p in paths]; limits=['固定历史检查不是所有日期保证，也不是未来行情检验','受控指标反例证明函数路径，不证明真实发生频率','未运行收益或完整资金账户，原始确认不等于合格交易','真实驱动独立审阅为静态核对；主任务反例重跑不是第二套独立算法','本批未新增论文全文阅读，未更新生产或OKR']
 ev=E(key,[str(f) for f in fs],[sha(f) for f in fs],'research-tenth/2026-09-08','mixed','2015-01-01—2026-06-30',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 m=M('frozen_four_fund_nominal',instrument_id='510300,159915,518880,513100',market='CN',health='unknown',reason='第八批名义历史与已知行动；真实交易日历等完整制度未齐',extra={'input_manifest':str(P/'history-diagnostic/run-lock.json'),'sha256':sha(P/'history-diagnostic/run-lock.json')}).to_dict()
 cards.append(dict(user_question=q,conclusion=c,evidence_ref=ev,market_data_refs=[m],rule_refs=[rule],research=dict(run_id='research-tenth-2026-09-08',production_adopted=False,independent_market_episodes=None,independently_reviewed=False,review_scope='A与C/D分工核查，历史驱动独立静态审阅，主任务原反例重跑；不冒称独立账户验证',status='limited',limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n')
print('two evidence cards use existing provenance contract')
