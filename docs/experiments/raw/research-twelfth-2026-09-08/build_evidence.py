from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contract=P.parent/'research-fourth-2026-09-08/inputs/src/lei_signal/data_provenance.py'
nodes=[n for n in ast.parse(contract.read_text()).body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2');exec(compile(ast.Module(body=nodes,type_ignores=[]),'existing_frozen_contract','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef'];cfg=P/'research-package/configs/rules.v2.yaml'
rule=R('__ruleset__','2.1.0',str(cfg),sha(cfg),definition_ref='策略§3.2/§9A/C/D/§10/§13/§16；有限日线入场和初始失效退出；参数未改').to_dict()
limits=['只测初始结构失效退出，盈利保护等完整退出没有测','A小周期、C/D未定义等待、九条纪律缺项未补定','同历史和重叠持仓，不是独立未来验证','行情及开盘限制继承第八有限资料','独立验证来源、资金和执行，没有独立重写信号及目标算法','本批没有新增论文全文阅读；未写生产或Zotero；第十二OKR证据待具体确认']
items=[('acd-limited-accounts','修复后的A/C/D连上资金账户后表现怎样？','12组已核对；A20增长几乎来自三笔未卖出持仓，C1已结束15笔全亏，四组无成交；不能证明完整系统有效。',['protocol.md','precision-account-results/run-lock.json','precision-account-results/summary.json','precision-account-results/product-contributions.csv','interpretation-review/review.json','independent-review/precision-addendum/results.json','independent-review/precision-addendum/summary-results.json'],'fixed_twelve_limited_accounts'),('acd-numeric-boundary','恰好达到3倍却被拒绝，修正会不会改变收益？','两条信号原被小数误差拒绝；保留原结果后按十进制纠错，两条又因次日开盘低于失效价拒绝，51财务文件完全不变。',['precision-fix/protocol.md','precision-fix/candidate-completion.json','precision-fix/comparison.json','precision-fix/root-boundary-tests.txt','independent-review/source-results.json','independent-review/precision-addendum/source-results.json','independent-review/precision-addendum/revision-difference-results.json'],'documented_after_result_numeric_correction')]
cards=[]
for key,q,c,paths,kind in items:
 fs=[P/f for f in paths];ev=E(key,[str(f) for f in fs],[sha(f) for f in fs],'research-twelfth/2026-09-08','mixed','2015-01-01—2026-06-30',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 market=M('frozen_four_fund_nominal',instrument_id='510300,159915,518880,513100',market='CN',health='unknown',reason='第八名义历史与已知公司行动；成交制度仍为有限近似',extra={'run_lock':str(P/'precision-account-results/run-lock.json'),'sha256':sha(P/'precision-account-results/run-lock.json')}).to_dict()
 cards.append(dict(user_question=q,conclusion=c,evidence_ref=ev,market_data_refs=[market],rule_refs=[rule],research=dict(run_id='research-twelfth-2026-09-08',production_adopted=False,independent_market_episodes=None,independently_reviewed=True,review_scope='完整候选来源/独立日账与订单/汇总/首轮与纠错差异；信号及目标选择未独立重写',status='limited',limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n');print('2 existing-contract evidence cards created')
