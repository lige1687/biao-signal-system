"""Build source anchors and verify this assigned subtask without executing strategy logic."""
from pathlib import Path
import ast,hashlib,json
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,x):(P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
manifest=json.loads((P/'input-manifest.json').read_text())
lookup={x['copy']:x for x in manifest['files']}
anchors=[
('docs/trading-spec-v1.md',None,'最高策略来源：分层、B、目标、九条、时点'),
('configs/rules.v1.yaml',None,'留存旧账本，避免错误当成当前生效规则'),
('configs/rules.v2.yaml',None,'实际加载版本及各规则provenance'),
('src/lei_signal/domain/rules_config.py','_default_config_path','实际配置路径'),
('src/lei_signal/api/routes/backtest.py','RunRequest','参数默认；create_run负责交给服务'),
('src/lei_signal/backtest/service.py','BacktestParams','参数与验证；可选过滤默认关闭'),
('src/lei_signal/backtest/service.py','_execute_run_unlocked','主执行链：事件、目标、可选过滤、逐笔'),
('src/lei_signal/backtest/service.py','_cached_events','模块B实际调用dense检测器'),
('src/lei_signal/backtest/service.py','_overrides_yaml','覆盖白名单与临时账本机制'),
('src/lei_signal/backtest/runner.py','load_pool_frames','历史行情→特征→颜色，少于300根跳过'),
('src/lei_signal/features/indicators.py','compute_features','日线滚动指标与预热'),
('src/lei_signal/rules/clock_classifier.py','clock_series','SMA方向时钟'),
('src/lei_signal/rules/dense_breakout.py','_state_age_series','初始False计龄与短暂离开计龄'),
('src/lei_signal/rules/dense_breakout.py','detect_dense_breakout_events','B1/B2/B3完整事件状态'),
('src/lei_signal/backtest/engine.py','entry_specs_from_events','模块契约、目标、信号风险比'),
('src/lei_signal/backtest/engine.py','simulate_trade','next-open、结构优先、B3无条件排列分支'),
('src/lei_signal/rules/reward_risk_filter.py','_target_b','目标优先级、历史前缀'),
('src/lei_signal/rules/resistance_b1.py','find_b1','摆动高点的最早确认日期限制'),
('src/lei_signal/rules/tradability_gate.py','evaluate_tradability','九条展示评估；四项False占位'),
('src/lei_signal/api/routes/symbols.py',None,'evaluate_tradability仅用于展示DTO'),
('tests/test_dense_breakout.py',None,'既有B测试复制备查；本次未重跑该套测试'),
('tests/test_tradability_gate.py',None,'既有展示评估测试复制备查'),
('tests/test_reward_risk_filter.py',None,'既有目标测试复制备查'),
('tests/test_backtest_engine.py',None,'既有逐笔引擎测试复制备查'),
]
rows=[]
for rel,func,purpose in anchors:
 p=P/'snapshot'/rel
 line=1
 if func:
  tree=ast.parse(p.read_text());n=next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name==func);line=n.lineno
 elif rel.endswith('symbols.py'):
  line=next(i for i,s in enumerate(p.read_text().splitlines(),1) if 'tr = evaluate_tradability' in s)
 rows.append({'source':lookup['snapshot/'+rel]['source'],'snapshot':str(p),'line':line,'function':func,'sha256':sha(p),'purpose':purpose})
write('source-anchors.json',rows)
s=['# G1 冻结来源与定位','', '日期：2026-09-08。下表均为本地源码/文档证据，不引用网页结论。原仓库只读，完整243份指纹见input-manifest.json。既有测试仅作为来源备查，不冒充本次已运行。','', '| 复制件定位 | 用途 | SHA-256前12位 |','|---|---|---|']
for r in rows:s.append(f"| [{Path(r['snapshot']).name}:{r['line']}]({r['snapshot']}:{r['line']})"+(f" `{r['function']}`" if r['function'] else '')+f" | {r['purpose']} | {r['sha256'][:12]} |")
s+=['','完整原始路径、函数行号和指纹见source-anchors.json。实验只从snapshot/src导入，配置加载由复制件自身定位到snapshot/configs/rules.v2.yaml。','']
(P/'source-table.md').write_text('\n'.join(s))
r=json.loads((P/'attempt-01/results.json').read_text());diag=json.loads((P/'s02-age-diagnostic.json').read_text())
q={'date':'2026-09-08','scope':'G1 current B rules qualification only','audit_status':'completed_with_gaps','complete_B_qualified':False,'recommended_name':'B研究代理','current_ruleset_version':'2.1.0','current_dense_rule_version':'2.0.0','synthetic_cases':16,'status_counts':{k:sum(x['status']==k for x in r) for k in ['pass','finding','fixture_error']},'existing_case_diagnostics':1,'findings':[{'id':'G1-F1','source':'S09','kind':'event_engine_semantic_mismatch','description':'突破版也触发埋伏专用排列退出','production_changed':False},{'id':'G1-F2','source':'S11','kind':'signal_reference_vs_executed_price_gap','description':'信号风险比4、实际开盘1.6315789474仍入场；未满足后续方案实际成交≥3要求','production_changed':False},{'id':'G1-F3','source':'S02 intermediate-state diagnostic','kind':'initial_warmup_age','description':'首次有效横盘已有寿命15；观察日有效横盘112、状态寿命126','production_changed':False}],'nine_conditions_fully_enforced':False,'historical_candidate_runs':0,'performance_verdict':None,'historical_effect_size_measured':False,'production_modified':False,'okr_modified':False,'registry_modified':False,'subtask_only_registration':'parent consolidates','remaining':['明确原样代理或修正研究版本，冻结选择','修正版本需要自己的合成核验，不能复用此处作为通过','逐项明确九条输入与执行范围，不接占位False冒充判断','G2及数据/资金等资格由主研究另查']}
write('qualification.json',q)
required=['protocol.md','input-manifest.json','synthetic_checks.py','attempt-01/results.json','attempt-01/before.json','attempt-01/after.json','s02-diagnostic-plan.md','explain_s02.py','s02-age-diagnostic.json','rule-field-mapping.md','source-table.md','source-anchors.json','review-2026-09-08.md','qualification.json']
checks={'completed_at_utc':datetime.now(timezone.utc).isoformat(),'required_files_present':all((P/f).exists() for f in required),'protocol_unchanged':sha(P/'protocol.md')==manifest['protocol_sha256'],'frozen_source_count':len(manifest['files']),'frozen_bytes':sum(x['bytes'] for x in manifest['files']),'snapshot_mismatches':[x['copy'] for x in manifest['files'] if sha(P/x['copy'])!=x['sha256']],'source_mismatches':[x['source'] for x in manifest['files'] if not Path(x['source']).exists() or sha(Path(x['source']))!=x['sha256']],'exactly_16_distinct_cases':len(r)==16 and len({x['id'] for x in r})==16,'fixture_errors':sum(x['status']=='fixture_error' for x in r),'all_initial_findings_retained':[x['id'] for x in r if x['status']=='finding'],'s02_diagnostic_same_input':sha(P/'attempt-01/synthetic-full-features.csv')==diag['input_sha256'],'no_complete_B_claim':q['complete_B_qualified'] is False,'new_strategy_runs':0,'all_anchor_targets_exist':all(Path(x['snapshot']).exists() for x in rows)}
checks['self_check_passed']=all([checks['required_files_present'],checks['protocol_unchanged'],not checks['snapshot_mismatches'],not checks['source_mismatches'],checks['exactly_16_distinct_cases'],checks['fixture_errors']==0,checks['s02_diagnostic_same_input'],checks['no_complete_B_claim'],checks['all_anchor_targets_exist']])
write('self-check.json',checks)
files=[p for p in sorted(P.rglob('*')) if p.is_file() and p.name!='manifest.json']
write('manifest.json',{'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'seventh/rules-qualification only; manifest excludes itself','files':[{'path':str(p.relative_to(P)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]})
print(json.dumps(checks,ensure_ascii=False))
