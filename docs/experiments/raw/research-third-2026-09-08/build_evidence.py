"""Reuse frozen provenance dataclasses; research-only extensions remain outside refs."""
from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
t=ast.parse((P/'inputs/src/lei_signal/data_provenance.py').read_text());selected=[n for n in t.body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']];ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2');exec(compile(ast.Module(body=selected,type_ignores=[]),'frozen_contract_only','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef'];cfg=P/'inputs/configs/rules.v1.yaml'
rule=R('__ruleset__','1.5.0',str(cfg),sha(cfg),definition_ref='trading-spec-v1 §3.1–3.3；本轮不修改策略规则').to_dict()
review=P/'07/independent-results-review.md'
items=[
('06-history','实际基金是否已有长历史价格？','四基金已取回2013年以来价格，尚非完整可交易账户数据。',['06/fetch-manifest.json','06/long-coverage.json'],'2013-07-29—2026-09-07','data_coverage','mixed',False,['只能说明取得数据和分段一致','不能承诺历史真实交易可复制或已经完成三对照'],3187),
('06-dividend','前复权价格变化等于现金持有财富变化吗？','本例不相等；现金持有变化2.4673%，前复权比值变化2.6057%。',['06/measurement-protocol.json','06/dividend-results.json','06/dividend-daily-ledger.csv','06/510300-official-dividend.pdf'],'2025-06-10—2025-06-30','valuation_diagnostic','mixed',True,['单一已知分红事件的持有计量','非新策略、无交易或长历史有效性结论'],1),
('07-legacy','旧四区间数字能否证明完整冰点？','252条旧价格观察可复现，但实际仅两条件，不能证明完整四条件。',['07/replay-protocol.json','07/replay-summary.json','07/legacy-observations.csv','inputs/scripts/icepoint_multi_event_validation.py'],'四个固定区间：2022及2026','legacy_price_observation','mixed',True,['当前成员、非完整交易、同事件重复观察','252不是独立事件数','兼容完整四条件未知'],252),
('08-material','解释价值可以怎样开始检验？','已准备8份事实题与来源，未运行模型或评价用户理解。',['08/explanation-cases.json'],'尚未开始观察','study_material','watch',False,['材料准备数不是通过数','无模型表现或退出效果结论'],8)]
cards=[]
for key,q,conclusion,paths,window,kind,status,checked,limits,n in items:
 refs=[P/f for f in paths];e=E(key,[str(f) for f in refs],[sha(f) for f in refs],'research-third/2026-09-08',status,window,kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 data=M('frozen_research_material',instrument_id='510300' if key=='06-dividend' else '',market='CN',available_at=None,health='unknown',reason='历史首次可得时间未完整核实；研究材料不作为当前行情。',extra={'research_input_manifest':str(P/'input-manifest.json')}).to_dict()
 cards.append(dict(user_question=q,conclusion=conclusion,evidence_ref=e,market_data_refs=[data],rule_refs=[rule],research=dict(run_id='research-third-2026-09-08',classification=kind,reported_units=n,independent_event_count=None,independent_event_count_reason='资料行/重叠观察/固定计量例子或练习数，不作为独立投资事件数。',independently_reviewed=checked,independent_review_path=str(review) if checked else None,production_adopted=False,limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2));print('4 evidence cards using frozen provenance/1.2 fields')
