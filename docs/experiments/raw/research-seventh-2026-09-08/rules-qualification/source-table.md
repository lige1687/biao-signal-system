# G1 冻结来源与定位

日期：2026-09-08。下表均为本地源码/文档证据，不引用网页结论。原仓库只读，完整243份指纹见input-manifest.json。既有测试仅作为来源备查，不冒充本次已运行。

| 复制件定位 | 用途 | SHA-256前12位 |
|---|---|---|
| [trading-spec-v1.md:1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/docs/trading-spec-v1.md:1) | 最高策略来源：分层、B、目标、九条、时点 | dd75d70cd22b |
| [rules.v1.yaml:1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/configs/rules.v1.yaml:1) | 留存旧账本，避免错误当成当前生效规则 | 9be26a1626fd |
| [rules.v2.yaml:1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/configs/rules.v2.yaml:1) | 实际加载版本及各规则provenance | cdab8221bba9 |
| [rules_config.py:15](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/domain/rules_config.py:15) `_default_config_path` | 实际配置路径 | 05df350a21e5 |
| [backtest.py:41](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/api/routes/backtest.py:41) `RunRequest` | 参数默认；create_run负责交给服务 | 167cad0d1e14 |
| [service.py:280](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/backtest/service.py:280) `BacktestParams` | 参数与验证；可选过滤默认关闭 | 8b69e97f9297 |
| [service.py:428](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/backtest/service.py:428) `_execute_run_unlocked` | 主执行链：事件、目标、可选过滤、逐笔 | 8b69e97f9297 |
| [service.py:653](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/backtest/service.py:653) `_cached_events` | 模块B实际调用dense检测器 | 8b69e97f9297 |
| [service.py:105](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/backtest/service.py:105) `_overrides_yaml` | 覆盖白名单与临时账本机制 | 8b69e97f9297 |
| [runner.py:101](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/backtest/runner.py:101) `load_pool_frames` | 历史行情→特征→颜色，少于300根跳过 | 3c8d9865ffa9 |
| [indicators.py:106](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/features/indicators.py:106) `compute_features` | 日线滚动指标与预热 | 098b931d3527 |
| [clock_classifier.py:97](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/rules/clock_classifier.py:97) `clock_series` | SMA方向时钟 | 3ce68b924292 |
| [dense_breakout.py:105](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/rules/dense_breakout.py:105) `_state_age_series` | 初始False计龄与短暂离开计龄 | ffb37ff38e99 |
| [dense_breakout.py:231](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/rules/dense_breakout.py:231) `detect_dense_breakout_events` | B1/B2/B3完整事件状态 | ffb37ff38e99 |
| [engine.py:192](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/backtest/engine.py:192) `entry_specs_from_events` | 模块契约、目标、信号风险比 | ca9fe8344aa5 |
| [engine.py:283](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/backtest/engine.py:283) `simulate_trade` | next-open、结构优先、B3无条件排列分支 | ca9fe8344aa5 |
| [reward_risk_filter.py:101](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/rules/reward_risk_filter.py:101) `_target_b` | 目标优先级、历史前缀 | 1161e49a6227 |
| [resistance_b1.py:46](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/rules/resistance_b1.py:46) `find_b1` | 摆动高点的最早确认日期限制 | dc221c6cc3fe |
| [tradability_gate.py:204](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/rules/tradability_gate.py:204) `evaluate_tradability` | 九条展示评估；四项False占位 | 64bd55ba3b73 |
| [symbols.py:1219](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/src/lei_signal/api/routes/symbols.py:1219) | evaluate_tradability仅用于展示DTO | c3fa4c552be3 |
| [test_dense_breakout.py:1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/tests/unit/test_dense_breakout.py:1) | 既有B测试复制备查；本次未重跑该套测试 | b434c96c6511 |
| [test_tradability_gate.py:1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/tests/unit/test_tradability_gate.py:1) | 既有展示评估测试复制备查 | 5432438cc2e8 |
| [test_reward_risk_filter.py:1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/tests/unit/test_reward_risk_filter.py:1) | 既有目标测试复制备查 | f0ee4d59b78d |
| [test_backtest_engine.py:1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-seventh-2026-09-08/rules-qualification/snapshot/tests/unit/test_backtest_engine.py:1) | 既有逐笔引擎测试复制备查 | 3f5677bcdb20 |

完整原始路径、函数行号和指纹见source-anchors.json。实验只从snapshot/src导入，配置加载由复制件自身定位到snapshot/configs/rules.v2.yaml。
