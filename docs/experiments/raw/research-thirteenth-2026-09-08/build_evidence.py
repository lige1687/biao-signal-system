from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent;T=P.parent/'research-twelfth-2026-09-08'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contract=P.parent/'research-fourth-2026-09-08/inputs/src/lei_signal/data_provenance.py'
nodes=[n for n in ast.parse(contract.read_text()).body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2');exec(compile(ast.Module(body=nodes,type_ignores=[]),'existing_frozen_contract','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef'];cfg=T/'research-package/configs/rules.v2.yaml'
rule=R('__ruleset__','2.1.0',str(cfg),sha(cfg),definition_ref='策略§9 A5/A6①③、§3.2、§14/§16/§20；EMA20+20根前收盘退出，原结构保护保留').to_dict()
limits=['固定原17含重复配置，不是17次独立行情','原历史已看过；不构成未来验证','只比A6①+结构与纯结构；未补A6②、多周期、C/D/B缺项','资料与成交约束继续为第八有限研究近似','独立核账户、EMA与退出；未重新实现A形态和目标选择','独立接收224副本后1旧日志改名、2缓存源清理；接受副本完整、经济/源码221项不变','本批未写生产/真实账户/OKR/Zotero']
items=[('a-road-exit-account','增加道路退出会怎样改变完整账户？','六对账户已核：A20最大投资跌幅约10.9%降到5.7%，但每组期末少18.46万元；其余四组无差异，不能直接认定升级。',['protocol.md','execution/run-lock.json','execution/account-results/summary.json','independent-review/summary.json','independent-review/source-integrity-final.json'],'six_paired_limited_exit_accounts'),('a-road-exit-fixed-entry','是否只是提前卖出错过了上涨？','原17买入固定数量的比较有8条退出改变（两组重复同四段行情）；一段提前卖出避免后续损失，三段减少长期上涨参与。完整账户还各新增7次A20买入，仍未补回差额。',['execution/fixed-17-comparison.csv','independent-review/fixed-path-results.json','independent-review/comparison-table-results.json','supplemental-tests/root-tests.txt','paper-methods/METHODS.md'],'fixed_original_entries_and_subsequent_reentry_comparison')]
cards=[]
for key,q,c,paths,kind in items:
 fs=[P/f for f in paths];ev=E(key,[str(f) for f in fs],[sha(f) for f in fs],'research-thirteenth/2026-09-08','mixed','2015-01-01—2026-06-30',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 market=M('frozen_four_fund_nominal',instrument_id='510300,159915,518880,513100',market='CN',health='unknown',reason='第八名义历史与14已知行动，仍有限成交近似',extra={'run_lock':str(P/'execution/run-lock.json'),'sha256':sha(P/'execution/run-lock.json')}).to_dict()
 cards.append(dict(user_question=q,conclusion=c,evidence_ref=ev,market_data_refs=[market],rule_refs=[rule],research=dict(run_id='research-thirteenth-2026-09-08',status='limited',production_adopted=False,independently_reviewed=True,independent_market_episodes=None,review_scope='全EMA/抵扣价与现金订单退出、固定数量路径；原信号算法复用',limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n');print('two existing-contract evidence cards created')
