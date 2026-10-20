from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent

def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
t=ast.parse((P/'inputs/src/lei_signal/data_provenance.py').read_text())
selected=[n for n in t.body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2')
exec(compile(ast.Module(body=selected,type_ignores=[]),'frozen_contract_only','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef']
cfg=P/'inputs/configs/rules.v1.yaml'
rule=R('__ruleset__','1.5.0',str(cfg),sha(cfg),definition_ref='trading-spec-v1 §3.2–3.3；任务书06/R2资金研究，非技术触发规则').to_dict()
summary=json.loads((P/'study/summary.json').read_text())
base={x['arm']:x for x in summary if x['scenario']=='base'}
items=[('06-actual-cash','相同投入，季度调整比不调整实际多得到什么？','2023—2025同投入157000元，季度调整比只定期投入多4101.49元，但最大跌幅多0.30个百分点、多30笔买卖。',['study/protocol.md','study/protocol-lock.json','study/protocol-clarifications.md','study/execution-assumptions.md','study/summary.json','study/engine-review.md','study/reviewer-real-ledgers.json','study/reconciliation.json'],'historical_cash_account_comparison',True),('06-event-coverage','已有2013年以来价格，就能当完整长期账户吗？','不能；13次沪深300分红有原公告，其他三只共同明确分红覆盖目前限2023—2025，更早事件与特殊停牌仍有缺口。',['prices/fetch-manifest.json','events/510300/events.json','events/other/events-and-coverage.json'],'data_coverage',False)]
cards=[]
for key,q,conclusion,paths,kind,reviewed in items:
 refs=[P/p for p in paths]
 limits=['固定四只今天仍存续产品，不能代表当时全部可投选择','2023—2025属于修正计量后重算，不是未见行情的正式验证','开盘成交、分红发放日开盘可用、无最低手续费均为研究假设','更早完整事件与停牌未覆盖；不代表当前触发或实际预算','12固定场景中仅base三个账户由另一个审查者完整重算，其余为主研究独立收支程序核对']
 evidence=E(key,[str(f) for f in refs],[sha(f) for f in refs],'research-fourth/2026-09-08','mixed','2023-01-01—2025-12-31',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 market=[M('frozen_tencent_nominal_and_primary_fund_announcements',instrument_id=s,market='CN',available_at=None,health='unknown',reason='仅历史资料，首次可得时间和完整交易事件未全部核实。',extra={'price_sha256':sha(P/'prices'/f'{s}-nominal.csv'),'cash_event_sources':str(P/'events'),'quote_window':['2023-01-03','2025-12-31']}).to_dict() for s in ['sh510300','sz159915','sh518880','sh513100']]
 cards.append(dict(user_question=q,conclusion=conclusion,evidence_ref=evidence,market_data_refs=market,rule_refs=[rule],research=dict(run_id='research-fourth-2026-09-08',classification=kind,base_accounts=base if reviewed else None,planned_comparisons=12,independent_market_episodes=1,independent_event_count_reason='一个连续三年市场经历；三方案和四情景共享行情，不能算12次独立证据。',independently_reviewed=reviewed,independent_review_scope='基础3账户逐日重建与6组合成检查' if reviewed else '事件来源分别核对，非全历史独立验收',production_adopted=False,limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2))
print('2 provenance/1.2 evidence cards')
