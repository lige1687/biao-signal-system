"""Register only owned completed reports and navigation, preserving others."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[4];RAW=Path(__file__).parent
review=json.loads((RAW/'complete-account-core-independent-review-20261011.json').read_text())
assert review['status']=='accepted_conditional_paired_core_no_additional_policy_run'
report='docs/experiments/weekly-two-etf-complete-account-2026-10-11.md'
h=hashlib.sha256((ROOT/report).read_bytes()).hexdigest()
entry={'category':'组合与仓位','verdict':'mixed',
'oneLiner':'同投入下，每周检查后调仓比只补较少持仓少2,827.83元，波动几乎一样，费用和操作略增；固定两ETF日线模拟没有看到额外收益。',
'report_sha256':h,'raw_directory':'docs/experiments/raw/weekly-two-etf-complete-account-2026-10-11',
'archive_status':'completed_bounded_conditional_negative_account_comparison',
'core_paired_batches':1,'historical_policy_path_attempts':2,'historical_successful_policy_paths':2,'mechanical_market_repair_batches':0,
'artificial_launches':3,'distinct_lifecycle_cases':10,'completed_artificial_batches':2,'artificial_case_executions':20,
'source_requests':0,'scientific_parameter_variants':0,'scheduled_weekly_deposits_per_policy':600,
'contributions_per_policy_CNY':150000,'model_quote_days':2790,
'result_sha256':'8508ce310f49ed195c3a37ba50e59e332ce22bdc195075ad19999e094be6dec3',
'core_contract_sha256':'9a19eb623bbb1dccd7cd3060322317a44dbd6931cb791c718a6210edddd360be',
'independent_review_sha256':'6f1e475acfee0cdaa754f7524a90afc9869d812553d62d54d16e02abb86149fd',
'strict_historical_qualification_ready':False,'stable_added_return_proven':False,
'production_authorized':False}
registration={'report':report,'entry':entry}
registration['insert']='    '+json.dumps(report,ensure_ascii=False)+': '+json.dumps(entry,ensure_ascii=False,indent=2)+',\n'
(RAW/'complete-account-registration-entry.json').write_text(json.dumps(registration,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'docs/experiments/weekly-portfolio-zero-sale-cash-2026-10-11.md'
body=p.read_text()
body=body.replace('这些是流程核验，完整历史收益比较尚未执行。','这些是起步流程核验；完整历史资金比较已另在[两ETF完整账户报告](weekly-two-etf-complete-account-2026-10-11.md)结案，单次固定模拟未看到调仓多赚。',1)
body=body.replace('当前进入整链适配/输入/人工验收，尚未运行市场政策账户，严格历史成交/到达未知仍未升级为真实资格。','本起步阶段之后，独立完整资金比较实际一对两路径已通过核账并另文归档；其严格历史成交/到达未知仍未升级为真实资格。',1)
p.write_text(body)
zero=json.loads((RAW/'zero-sale-registration-entry.json').read_text())
zero['entry']['report_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
zero['entry']['oneLiner']='无须卖出时按原规则买入已在三人工场景通过；确需卖却不足整百仍等下周，尾数规则如实保留；后续两ETF完整资金研究另文结案。'
zero['insert']='    '+json.dumps(zero['report'],ensure_ascii=False)+': '+json.dumps(zero['entry'],ensure_ascii=False,indent=2)+',\n'
(RAW/'zero-sale-registration-entry.json').write_text(json.dumps(zero,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'docs/experiments/registry.json';before=p.read_text();old=json.loads(before);body=before
for item in (zero,registration):
    key=item['report']
    match=re.search(r'(?m)^[ \\t]*'+re.escape(json.dumps(key))+r'[ \\t]*:[ \\t]*',body)
    if match:
        _,end=json.JSONDecoder().raw_decode(body[match.end():])
        body=body[:match.end()]+json.dumps(item['entry'],ensure_ascii=False,indent=2)+body[match.end()+end:]
    else:
        anchor=re.search(r'(?m)^ *"entries" *: *[{]\n',body);assert anchor
        body=body[:anchor.end()]+item['insert']+body[anchor.end():]
parsed=json.loads(body)
assert all(v==parsed['entries'][k] for k,v in old['entries'].items() if k not in (zero['report'],report))
assert set(parsed['entries'])==set(old['entries'])|{report}
p.write_text(body)
p=RAW/'shared-document-insertions.json';ins=json.loads(p.read_text())
previous=ins['zero_sale_index_line'];ins.setdefault('previous_own_lines',{})['zero_sale_index_line']=previous
ins['zero_sale_index_line']='- 2026-10-11：[P1首次买入及零卖出分支](weekly-portfolio-zero-sale-cash-2026-10-11.md)：批准后新3人工场景通过，旧5保留累计8；场内数量已核，完整历史资金比较另文已结案。\n'
ins['complete_account_index_line']='- 2026-10-11：[两ETF每周投入完整资金比较](weekly-two-etf-complete-account-2026-10-11.md)：各600次入金15万元，一对独核P1少2,827.83元、波动比0.997697；581/600周回简单买入，固定日线近似负结果，新增8文件同盘恢复已核。\n'
lines=ins['catalog_prefix'].splitlines(True)
for i,line in enumerate(lines):
    if line.startswith('- [首次买入及零卖出分支]'):
        lines[i]='- [首次买入及零卖出分支](weekly-portfolio-zero-sale-cash-2026-10-11.md)：用户确认无超额需卖时按原买入，新3例及旧5累计8；旧反例原文保留，整百与全部尾数一次卖规则如实说明。\n'+ins['complete_account_index_line'].replace('- 2026-10-11：','- ')
        break
else:raise AssertionError('owned catalog startup line not found')
ins['catalog_prefix']=''.join(lines)
ins['catalog_prefix']=ins['catalog_prefix'].replace('完整严格账户资格、相近风险收益和异机/坏盘恢复未证明。','新完整账户在固定日线近似下已经核账，风险相近而收益更少；稳定收益增量、严格历史成交资格和异机/坏盘恢复仍未证明。')
p.write_text(json.dumps(ins,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'docs/experiments/INDEX.md';body=p.read_text()
assert body.count(previous)==1
body=body.replace(previous,ins['zero_sale_index_line'],1)
anchor='## 1. 任务编号总账（任务书 → 执行归档）';pos=body.index('\n',body.index(anchor))+1
assert ins['complete_account_index_line'] not in body
p.write_text(body[:pos]+'\n'+ins['complete_account_index_line']+body[pos:])
p=ROOT/'docs/experiments/research-evidence-catalog-2026-10-07.md';body=p.read_text()
marker='\n---\n\n';tail=body[body.index(marker)+len(marker):]
p.write_text(ins['catalog_prefix']+tail)
print(json.dumps({'report_sha256':h,'startup_report_sha256':zero['entry']['report_sha256'],
'registry_other_entries_preserved':True,'new_owned_reports':1},ensure_ascii=False))
