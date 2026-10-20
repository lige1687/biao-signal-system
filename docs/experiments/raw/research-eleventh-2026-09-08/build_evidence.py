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
items=[('acd-repair-history','修复后，后来行情还会改写当年判断吗？','原定366次真实历史检查及168次连续日期补充均一致；修复前后差异完整保留，没有收益结论。',['protocol.md','history-diagnostic/run-lock.json','history-diagnostic/summary.json','continuous-results/summary.json','runtime-audit-lock.json','old-new-event-comparison.json'],'isolated_repair_fixed_history_validation'),('acd-repair-independent','怎样确认修复没有把正确行为一起删掉？','64项合并检查通过；独立手工预期及1024种短行情覆盖历史保留、后来失效、后续新结构。旧失败、一项输入异常接口变更及证据局限均保留。',['complete-regression-tests.txt','history-review/strict-independent-results.json','history-review/driver-independent-review-2026-09-08.md','a-fix/integration-eleventh-fixed.json','cd-fix/history-diff-explanation.json','input-contract-change.md'],'regression_counterexamples_and_independent_finite_checks')]
for key,q,c,paths,kind in items:
 fs=[P/p for p in paths]; limits=['固定及连续日期存在重叠，不是独立未来行情','受控指标反例不证明真实市场发生频率','未运行收益或完整账户；待定义的策略流程未补造','连续日期原数据指纹在运行中补记且核对旧封存值，不冒称全部启动前登记','一项缺输入接口契约有明确变更，生产调用方尚未适配','本批未新增论文全文阅读，生产未采用；OKR按单独确认记录']
 ev=E(key,[str(f) for f in fs],[sha(f) for f in fs],'research-eleventh/2026-09-08','mixed','2015-01-01—2026-06-30',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 m=M('frozen_four_fund_nominal',instrument_id='510300,159915,518880,513100',market='CN',health='unknown',reason='第八批名义历史与已知行动；真实交易日历等完整制度未齐',extra={'input_manifest':str(P/'history-diagnostic/run-lock.json'),'sha256':sha(P/'history-diagnostic/run-lock.json')}).to_dict()
 cards.append(dict(user_question=q,conclusion=c,evidence_ref=ev,market_data_refs=[m],rule_refs=[rule],research=dict(run_id='research-eleventh-2026-09-08',production_adopted=False,independent_market_episodes=None,independently_reviewed=True,review_scope='核心结构独立手工预期/固定1024短序列；驱动静态及重复编号检查；C/D删记录固定3条原因抽检；非独立账户验证',status='limited',limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n')
print('two evidence cards use existing provenance contract')
