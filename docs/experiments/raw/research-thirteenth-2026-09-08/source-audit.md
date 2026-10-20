# A退出规则来源核对

2026-09-08。Sol只读核查，负责人对照相关原文确认；未运行收益后选择规则。

| 固定口径 | 依据 |
|---|---|
| 结构失效保留，另加同时低于EMA20与20根前收盘 | docs/trading-spec-v1.md §9 A5/A6①③、§20；不是取消结构保护的纯道路退出。 |
| 同时满足、严格小于，相等不触发 | configs/rules.v1.yaml 519–535；既有formula/condition。 |
| 20根是报价K线序列，不是20自然日 | src/lei_signal/features/indicators.py compute_features：close.shift(20)。 |
| A20/60/120退出均用EMA20 | A2定义入场回调位置，A6①明确退出EMA20；不自行换成入场均线周期。 |
| EMA首20个有效收盘均值种子，alpha=2/21 | src/lei_signal/features/indicators.py seeded_ema；冻结研究副本同口径。 |
| 入场当天收盘可形成卖出请求，但不能当天卖出 | §3.2、既有生产backtest/engine.py 403–408及第十二现金引擎顺序。 |
| 同一日结构与道路均触发时记录结构优先 | 既有引擎结构先检查；只影响原因归类，不改变开盘执行时间。 |
| EMA、抵扣价、当日收盘保持同一当时价格单位 | 第八PriceBasis cash_proportional_v1及第十二adapter；禁止期末复权价与名义收盘混用。 |

旧止损矩阵在“结构+A6①”的默认退出上增加ATR/时间等；本次比较“纯结构”与“结构+A6①”，并承接修正的A来源和完整现金。属于不同问题，不将旧ATR叠加失败直接套为本批结论。A6②顶部出现后等待关键波动，以及C/D新增盈利退出不在本次范围；继续保留未定义处。
