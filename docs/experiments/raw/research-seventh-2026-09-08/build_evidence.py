"""Package local research references; never writes production or OKR stores."""
from pathlib import Path
import ast
import json
import hashlib
from dataclasses import dataclass, field

P = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

contract = P.parent / 'research-fourth-2026-09-08/inputs/src/lei_signal/data_provenance.py'
nodes = [n for n in ast.parse(contract.read_text()).body
         if isinstance(n, ast.ClassDef) and n.name in ['EvidenceRef', 'MarketDataRef', 'RuleRef']]
ns = dict(dataclass=dataclass, field=field, COMPAT_UNKNOWN='unknown', SCHEMA_VERSION='provenance/1.2')
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'frozen_contract', 'exec'), ns)
E, M, R = ns['EvidenceRef'], ns['MarketDataRef'], ns['RuleRef']
cfg = P / 'rules-qualification/snapshot/configs/rules.v2.yaml'
rule = R('__ruleset__', '2.1.0', str(cfg), sha(cfg),
         definition_ref='策略规格§2.3/§3/§9/§10；仅研究验证，完整B资格未成立').to_dict()
items = [
    ('calendar-attribution', '改善是否集中于特定年份？',
     'A同资金净改善约98%来自三个年份；逐笔与日历汇总独立重算一致，但抽样边界权重不均，不能作未来概率。',
     ['calendar-protocol.md', 'calendar-results.json', 'calendar-monthly.csv', 'calendar-yearly.csv',
      'month-block-protocol.md', 'month-block-results.json', 'calendar-review/README.md', 'calendar-review/results.json'],
     'fixed_opportunity_calendar_diagnostic', True,
     ['旧机会选择与历史产品覆盖变化未消除', '月份抽样低估原窗首尾权重', '独立预算贡献不是有限共享资金账户']),
    ('b-rule-qualification', '当前回测能否代表完整B？',
     '不能：退出适用范围、跳空后风险比和预热计龄存在差异；16项为行为检查，不是16条完整纪律验收。',
     ['rules-qualification/protocol.md', 'rules-qualification/qualification.json',
      'rules-qualification/review-2026-09-08.md', 'rules-qualification/rule-field-mapping.md',
      'rules-qualification/attempt-01/results.json', 'rules-qualification/s02-age-diagnostic.json'],
     'synthetic_rule_qualification', False,
     ['没有运行新的策略收益', '九条纪律尚未全进入回测链', '只标B研究代理，未修改生产']),
    ('price-basis-qualification', '历史技术价能否转换成当时成交价？',
     '局部转换与日期边界最终11组检查通过；加法和比例转换改变部分条件，正式价格定义仍须明确。',
     ['price-basis-qualification/protocol.md', 'price-basis-qualification/protocol-amendment-1.md',
      'price-basis-qualification/results.json', 'price-basis-qualification/qualification-report.md',
      'price-basis-qualification/input-lock.json', 'price-basis-qualification/first-pass/review-counterexamples.json'],
     'point_in_time_price_conversion', False,
     ['部分已核公司行为不等于完整历史', '价格与量的单位定义、真实费用和完整交易日历未完成', '局部函数测试不等于策略有效'])
]
cards = []
for key, question, conclusion, paths, kind, independently_reviewed, limits in items:
    files = [P / x for x in paths]
    evidence = E(key, [str(x) for x in files], [sha(x) for x in files],
                 'research-seventh/2026-09-08', 'mixed', '冻结历史与合成例子，非当前信号', kind,
                 compatibility='unknown', limitations='；'.join(limits)).to_dict()
    cards.append({'user_question': question, 'conclusion': conclusion, 'evidence_ref': evidence,
                  'market_data_refs': [M('frozen_research_inputs', market='mixed', health='unknown',
                                         reason='依各卡范围分别使用旧行情、合成例子或四只基金名义行情').to_dict()],
                  'rule_refs': [rule], 'research': {
                      'run_id': 'research-seventh-2026-09-08', 'independently_reviewed': independently_reviewed,
                      'review_scope': '日历由另一实现全量重算；规则与价格卡仅各自研究检查及负责人阅读，不冒称另一实现全量复算',
                      'independent_market_episodes': None, 'production_adopted': False,
                      'limitations': limits}})
(P / 'evidence-cards.json').write_text(json.dumps(cards, ensure_ascii=False, indent=2) + '\n')
print('3 local evidence cards generated using provenance/1.2')
