from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contract=P.parent/'research-fourth-2026-09-08/inputs/src/lei_signal/data_provenance.py'
nodes=[n for n in ast.parse(contract.read_text()).body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2')
exec(compile(ast.Module(body=nodes,type_ignores=[]),'existing_frozen_contract','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef']
cfg=P/'b-research-fix/research-package/configs/rules.v2.yaml'
rule=R('__ruleset__','2.1.0',str(cfg),sha(cfg),definition_ref='策略§2.3/§3/§9B/§10/§13；副本三项修复见b-research-fix/research.patch；非完整B').to_dict()
items=[
 ('technical-candidates','为什么几乎没有交易？','B原始6机会仅2符合原结构下的信号纪律；普通突破1082条全被目标/风险纪律拒绝，不能推广成所有突破无效。',['candidate-study/run-lock.json','candidate-study/summary.json','candidate-study/candidates.csv','candidate-review/review-2026-09-08.md','candidate-review/summary.json'],'candidate_coverage_and_qualification'),
 ('technical-accounts','完整现金一起算，B比简单办法改善了吗？','模拟共入金60万元；B两笔后亏850元，平均持仓约0.0473%；未证明普遍改善。',['protocol.md','protocol-addendum-01.md','account-results/run-lock.json','account-results/summary.json','account-results/comparisons.json','account-review/README.md','execution-checks.json'],'limited_known_event_cash_comparison'),
 ('technical-risk-sizing','按计划风险金额买入是否减少了损失？','本批两次买入都先受现金限制，P7与P4数量和结果完全相同；不能据此宣称风险预算无用。',['account-results/P4/trades.csv','account-results/P7/trades.csv','account-review/README.md','account-review/order-boundary-checks.json'],'realized_position_sizing_comparison')]
cards=[]
for key,q,c,paths,kind in items:
 files=[P/x for x in paths]
 limits=['有限四产品历史且已反复查看，不是未来验证','完整B纪律、全部公司行动和真实成交制度未齐','资金与费用为研究假设，非用户实际条件','重复配置交易不是独立市场经历','未改变生产有效性或代用户验收']
 evidence=E(key,[str(f) for f in files],[sha(f) for f in files],'research-eighth/2026-09-08','mixed','2015-01-01—2026-06-30',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 market=M('frozen_four_fund_nominal',instrument_id='510300,159915,518880,513100',market='CN',health='unknown',reason='原名义历史及已核行动；完整事件/日历仍未全覆盖',extra={'input_manifest':str(P/'product-qualification/manifest.json'),'sha256':sha(P/'product-qualification/manifest.json')}).to_dict()
 cards.append({'user_question':q,'conclusion':c,'evidence_ref':evidence,'market_data_refs':[market],'rule_refs':[rule],'research':{'run_id':'research-eighth-2026-09-08','production_adopted':False,'independent_market_episodes':None,'independently_reviewed':True,'review_scope':'候选39条及全部数量；账户全部33592日及1925成交；按各卡报告范围，不冒称全部目标重新实现','limitations':limits}})
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n')
print('3 existing-contract evidence cards saved locally')
