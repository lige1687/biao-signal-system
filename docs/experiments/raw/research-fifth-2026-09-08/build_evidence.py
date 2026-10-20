from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent;OLD=P.parent/'research-fourth-2026-09-08'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
t=ast.parse((OLD/'inputs/src/lei_signal/data_provenance.py').read_text());nodes=[n for n in t.body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2');exec(compile(ast.Module(body=nodes,type_ignores=[]),'existing_frozen_contract','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef'];cfg=OLD/'inputs/configs/rules.v1.yaml'
rule=R('__ruleset__','1.5.0',str(cfg),sha(cfg),definition_ref='交易规格§3.2/3.3与用户任务06/R2；资金安排研究不冒充A/B/C/D触发').to_dict()
rows=json.loads((P/'study/summary.json').read_text());base=[x for x in rows if x['window']=='full' and x['scenario']=='base']
limits=['固定今天仍存在的四产品，不能视为2013事前选品','现金分红证据连续覆盖至2026-06-30；全部历史份额事件与盘中停牌未逐年排尽','日线开盘近似成交、发放日开盘可花、无最低收费是假设','方案与历史不是未见数据；不计算未来获胜概率','仅最长3基础账户由另一研究者独立重建实际成交后的账户及交易资格，不是重新生成目标买量','无真实预算/用户风险取舍/未来观察，不准自动生产接入']
items=[('06-long-cash','季度调整在较长历史中是否有额外价值？','同投入674000元，季度方案期末1822644.63元、不调整1772556.04元；多50088.59元，最大跌幅少5.04个百分点，但多213笔交易。',['study/protocol.md','study/protocol-lock.json','study/qualification.json','study/run-lock.json','study/summary.json','study/reconciliation.json','study/independent-long-ledgers.json','study/independent-long-ledgers-review.md'],'historical_cash_account_comparison',True),('06-window-dependence','长期好看是否意味着任一开始时期都顺利？','不意味着：2020—2022三方案均低于累计投入，且只看到2025年的风险对照与延至2026上半年不同。',['study/protocol.md','study/summary.json','study/reconciliation.json'],'historical_period_comparison',False)]
cards=[]
for key,q,conclusion,paths,kind,reviewed in items:
 fs=[P/f for f in paths];ref=E(key,[str(f) for f in fs],[sha(f) for f in fs],'research-fifth/2026-09-08','mixed','2013-07-30—2026-06-30',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 markets=[M('frozen_nominal_prices_and_formal_fund_reports',instrument_id=s,market='CN',available_at=None,health='unknown',reason='历史材料与有限执行近似；不是当前行情或完整市场事件数据库',extra={'price_sha256':sha(OLD/'prices'/f'{s}-nominal.csv'),'qualification_path':str(P/'study/qualification.json'),'cash_events_verified_through':'2026-06-30'}).to_dict() for s in ['sh510300','sz159915','sh518880','sh513100']]
 cards.append(dict(user_question=q,conclusion=conclusion,evidence_ref=ref,market_data_refs=markets,rule_refs=[rule],research=dict(run_id='research-fifth-2026-09-08',status='limited_support',planned_runs=21,base_summary=base if reviewed else None,independent_market_episodes=None,independent_event_count_reason='完整历史与三个分段共享行情；不将21账户当21独立市场事件。',independently_reviewed=reviewed,independent_review_scope='最长3基础账户从原价/公告/成交重建，未独立生成全部目标买量' if reviewed else '分段9账户主研究重建，非第二研究者全量复验',production_adopted=False,limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2))
print('2 existing-contract evidence cards written')
