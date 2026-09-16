# 审阅范围与职责确认（scope）

任务：双均线首轮结果解释·并行审阅任务书 v1.0.0（2026-09-15）。
性质：有界文档审阅。本目录全部文件是**待主控采用的独立审阅意见**，不是第二份权威合同，不是首轮报告，不产生任何真实因子有效性结论。

## 1. 审阅对象

- 对象：`candidate:lei.dual_ma.bull_state@draft-1`
  （候选卡：`docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`）。
- 它是一个**逐日布尔状态**（state_signal，0/1/缺失），不是完整策略：没有入场、退出、仓位、费用、成交规则。交易规格 `docs/trading-spec-v1.md` 中它对应"道路"定位（§2.2 均线方向是道路；§4.5 均线排列；§5 EMA 预警 + SMA 确认），候选条件为：收盘同时站上 EMA20/SMA20、两均线较前一观察上升、颜色为 green。
- 本轮用途：**历史描述**——在真实历史资料（510300 供应商调整价）上，描述该状态为真/为假之后，固定 22 格点目标的分布差别。用途不是市场风险收益回归（无模型卡、无 β/α 估计），也不是单只 ETF 横截面 IC（同一日只有一个标的，没有横截面；定义标准 v1.1.0 §7.1 同日排序 IC 口径本轮不适用）。

## 2. 实际使用的模型（如实记录，不冒称）

- 状态计算：`src/lei_signal/research/factor_unit/close_state.py::compute_close_state`，公式完全复用生产函数
  `src/lei_signal/rules/dual_ma.py::dual_ma_bull_state`、
  `src/lei_signal/rules/lei_color.py::classify_colors`、
  `src/lei_signal/features/indicators.py::seeded_ema`（只读核对，未运行）。
- 描述统计：`src/lei_signal/research/factor_unit/state_description.py::describe_states`。它是**确定性分组计数器**：共同合法集合上的 n/均值/中位数/严格大于 0 比例、辅助下行、逐年分组、连续状态段、固定锚点稀疏视角。
- **没有使用任何统计推断模型**：无回归、无显著性检验、无相关性诊断、无抽样方法。代码输出本身声明 `no_claims: [strategy_return, annualization, IC, significance, risk_adjusted_alpha]`，并标注重叠窗口不等于独立成功。审阅结论同样不得超出这个范围。
- 当前实现 `describe_states` 只接受 `data_mode='synthetic'`；真实模式未实现。首轮真实运行尚待主控另行裁决（见四修复主控复核 §4）。

## 3. 本轮边界（任务书 Global Constraints 复述为自我约束）

- 零联网、零安装、零密钥访问、零真实因子/目标计算、零真实价格读取、零账户/策略运行、零 OKR 写入。
- 唯一可写目录：`docs/research/proposals/factor-unit-interpretation-review-2026-09-15/`（本目录）。所有其他文件只读，包括 registry、INDEX、对象登记表、主线合同、原始资料、代码及其他 agent 输出（如 `docs/research/proposals/510300-acquisition-review-2026-09-15/`）。
- 不依赖主线正在写的文件（B1 合同草案、输入包）。本审阅只基于已存在文件；其 SHA-256 与读取时间记录在 `sources-and-checks.md`。发现后续漂移只列明，不自动重审、不改写他人产物。
- 不新增研究参数、标的、目标期限、牛熊分类、情绪/宽度因子、统计推断能力或外部工具适配。审阅中发现的必要新增项单列于 `interpretation-review.md` 末节"待主控决定"，不执行。
- 身份核对：工作目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`，与任务书一致（git status 存在主线未提交改动，与任务书预期相符，本审阅不触碰）。

## 4. 治理文档版本（已核对，非猜测）

| 文档 | 版本 | 路径 |
|---|---|---|
| 研究原则 | v1.1 | `docs/research/experiment-backtest-principles.md` |
| 定义标准 | 1.1.0 | `docs/research/definition-standard.md` |
| AI 执行合同 | 1.0.1 | `docs/research/ai-execution-contract.md` |
| 报告模板 | 1.1.0 | `docs/research/experiment-report-template.md` |
| 交易规格 | v1（2016-08-04 快照） | `docs/trading-spec-v1.md` |

本任务为文档审阅，不触发完整实验归档；按任务书约定不写 registry/INDEX，由主控复核时统一归档。
