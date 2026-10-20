from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent;ROOT=P.parents[3];OLD=P.parent/'research-eighth-2026-09-08'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contract=P.parent/'research-fourth-2026-09-08/inputs/src/lei_signal/data_provenance.py'
nodes=[n for n in ast.parse(contract.read_text()).body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2')
exec(compile(ast.Module(body=nodes,type_ignores=[]),'existing_frozen_contract','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef'];cfg=OLD/'b-research-fix/research-package/configs/rules.v2.yaml'
rule=R('__ruleset__','2.1.0',str(cfg),sha(cfg),definition_ref='策略§4.6/§9B/§10/§13；R0/R1仅诊断参照，不符合完整现行纪律；B区间语义未变').to_dict()
items=[
 ('entry-discipline-diagnostic','此前普通突破为什么完全不能买入？','固定其它条件，取消历史目标空间检查后，原普通突破买入由0次变132次，期末92.79万元；简单方向2次变340次、108.07万元。均入金60万元，也承受18.61%/16.27%最大投资净值跌幅；未证明应取消纪律。',['protocol.md','account-results/run-lock.json','account-results/summary.json','account-results/paired-comparisons.json','reference-account-review/results.json','execution-checks.json'],'limited_entry_filter_diagnostic'),
 ('b-zone-semantics','横盘很久为何失效区间可能只有一天？','横盘资格与本次观察价格区间独立计时；6个旧B事件中3个仅用1根价格形成区间。原文缺明确起点算法，需澄清结构含义，不能直接称完整B验证或擅改止损。',['b-zone-semantics/protocol.md','b-zone-semantics/README.md','b-zone-semantics/six-events.csv','b-zone-semantics/source-table.md','b-zone-semantics/manifest.json'],'existing_six_event_structure_definition_diagnostic')]
cards=[]
for key,q,c,paths,kind in items:
 files=[P/x for x in paths];limits=['已看过的有限四基金历史，不是未来检验','日线成交近似，真实费用/完整行动和交易日历未齐','R0/R1仅诊断，不自动取消现行纪律','B替代仅旧6日期机械比较，未生成新信号或收益','不同配置和同一市场交易不代表独立经历数']
 evidence=E(key,[str(f) for f in files],[sha(f) for f in files],'research-ninth/2026-09-08','mixed','2015-01-01—2026-06-30',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
 market=M('frozen_four_fund_nominal',instrument_id='510300,159915,518880,513100',market='CN',health='unknown',reason='第八批已核名义日线与已知公司行动；完整交易制度未齐',extra={'input_manifest':str(OLD/'product-qualification/manifest.json'),'sha256':sha(OLD/'product-qualification/manifest.json')}).to_dict()
 cards.append(dict(user_question=q,conclusion=c,evidence_ref=evidence,market_data_refs=[market],rule_refs=[rule],research=dict(run_id='research-ninth-2026-09-08',production_adopted=False,independent_market_episodes=None,independently_reviewed=key=='entry-discipline-diagnostic',review_scope='账户8398日/941成交/全部1742原候选/472次持仓；B仅源文与6旧日期机械复核，不称独立收益验证',status='limited',limitations=limits)))
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n')
body='''文献索引：`sullivan1999`。本条是对论文比较思想的本地应用，不是作者讨论本系统B规则，也不是作者提供的采用门槛。

作者的方法要求把尝试过的方法及其相对参照表现共同考虑。本次已读范围仍为1998年工作论文相关方法章节，详见[版本与章节记录](../experiments/raw/research-seventh-2026-09-08/paper-methods/METHODS.md)。没有复现作者完整候选集合及统计检验。

本地检查：普通突破加上本系统选目标、衡量计划亏损的纪律后，没有一次买入。我们先固定只有两组诊断，保留所有原始候选和其余执行条件，再取消这一个组合检查。普通突破从0次买入变132次，简单方向从2次变340次。更多参与带来更多期末财富，也承受明显跌幅和费用；这只能定位原来为何不能参与，不能替我们决定取消纪律。

检查建议：先问参照是否被改成另一个问题，再看成绩。至少一起保留原始触发数、各拒绝原因、真正成交数、资金参与和完整账户结果。定义差异不能在看到赢家后重新命名。出现负结果也保留，不临时添加第三组或更换周期。

另一个本地反例是B：横盘资格累计很久，但一次新观察的价格上下沿可能只有一天。若改用长期箱体，上沿与失效下沿必须一起讨论，不能保留原小区间买点后只加宽止损。这个判断来自本系统原文与代码核对，不能归功为论文已经证明哪种箱体最好。

[本地诊断报告](../experiments/entry-discipline-and-b-zone-diagnosis-2026-09-08.md)保留全部两组结果、失败版本和来源。这些历史数据已被看过，没有新的未来有效性证据。
'''
entry=dict(id='sullivan1999-reference-diagnostic-20260908',paper_id='sullivan1999',title='先查比较的是不是同一个问题',category='实验方法',body_markdown=body,method_acceptance=dict(origin='本库从论文比较思想引出的本地检查建议',paper_numeric_threshold=None,automatic_adoption=False),evidence_paths=['docs/experiments/entry-discipline-and-b-zone-diagnosis-2026-09-08.md'])
L=ROOT/'docs/literature-learning'
(L/'reference-definition-lessons-2026-09-08.json').write_text(json.dumps(dict(schema_version='learning-followup/1',date='2026-09-08',merge_policy='按文献和条目ID增量合并；不覆盖旧阅读状态；本批未写入页面或Zotero',reading_updates=[],entries=[entry]),ensure_ascii=False,indent=2)+'\n')
(L/'reference-definition-lessons-2026-09-08.md').write_text('# 先查比较的是不是同一个问题\n\n日期：2026-09-08。学习增补，待工程合并。\n\n'+body)
print('2 existing-contract evidence cards and 1 learning entry written')
