from pathlib import Path
import datetime,json,hashlib
from lei_signal.research.definitions import load_registry,resolve,verify_sources,make_manifest
R=Path(__file__).resolve().parents[5];W=Path(__file__).resolve().parents[1];C=W/'controller';r=load_registry();n=verify_sources(r)
refs=['benchmark.etf.price_sma50_binary_account@1.0.0','policy.breadth.all_a.w3@1.0.0','policy.breadth.csi300.w0@1.0.0','baseline.etf_price200@1.0.0','baseline.etf_hold_reinvest@1.0.0','baseline.etf_monthly50@1.0.0']
now=datetime.datetime.now(datetime.timezone.utc).isoformat();old=R/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09';first=R/'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs'
inputs=[first/'bars/sh510300-nominal.csv',first/'bars/sz159915-nominal.csv',first/'actions.json',first/'dated-restrictions.json',first/'price-limit-regimes.json',old/'results/summary.csv',old/'prepared/breadth_all_a.parquet',old/'prepared/breadth_csi300.parquet',C/'source-lock.json']
meta=make_manifest(registry=r,references=refs,code_files=[W/'execution/run_price50.py',W/'execution/research_engine.py',C/'relative_and_attribution.py',C/'complete_metrics.py'],input_files=inputs,data_cutoff='2026-06-30T15:00:00+08:00',available_at=now,decision_at=now,protocol=W/'protocol.md',pool_version='fixed ETF510300/159915; first12 frozen inputs; legacy breadth proxies separately identified',quality={'historical_available_at':'unknown','metadata_decision_time':'actual manifest assembly after calculations, not historical trading time; execution pre-run lock separately preserved','definitions':'new50 matched isolated adapter; legacy comparisons external mappings, not migrated','data':'limited frozen ETF and breadth sources','implementation':'new4 signals/account replay and independent metrics passed','effectiveness':'historical comparison only','production':'not_authorized','verified_registry_sources':n})
(C/'experiment-manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');(C/'registry-snapshot.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');(C/'resolved-definition-cards.json').write_text(json.dumps({k:resolve(r,k) for k in refs},ensure_ascii=False,indent=2)+'\n')
digest=hashlib.sha256((R/'docs/research/definitions.v1.json').read_bytes()).hexdigest()
(C/'definition-metadata.md').write_text(f'''定义登记表：`definitions.v1.json` v{r['version']}，SHA-256 `{digest}`。本轮新增`etf.trend.price50.state@1.0.0`与`benchmark.etf.price_sma50_binary_account@1.0.0`；原对象版本保持。准确对手引用、完整依赖、输入/代码指纹与时点见本批`controller/experiment-manifest.json`和`resolved-definition-cards.json`。

定义清晰程度／数据资格／实现核验／有效性证据／生产授权：固定规则明确／历史资料有限／新4条账户及信号核验通过／已知历史比较、不保证稳定收益／未授权。原宽度与基准账户为旧实现（legacy），只做外部定义映射，未宣称消费者已迁移。新50日使用隔离适配器，尚非全仓库统一执行引擎。历史资料到达时间未知；manifest时间只是本次资料读取与整理时间，不冒充历史决策时间。模型列表为空。
''')
print('manifest complete',n,'sources verified')
