# 行业 ETF 技术研究：执行接口准备

日期：2026-09-09。状态：只读准备；协议尚未固定，未生成候选、未运行收益。

## 服务的策略层

本批只研究规格中的道路、模块 A 的均线支撑回调和模块 B 的均线密集区突破。相对沪深 300 的强弱只做独立分组，不能硬挡全部信号，也不改变原触发、失效位或盈亏比不少于 3 的纪律。MACD 不参与转折或买卖判定。

## 建议的最小执行接口

建议入口拆成三个纯步骤，所有输出先锁代码、配置、原始价格、分红事件和协议，再运行账户：

1. `build_point_in_time_frames(symbol, as_of)`：读取真实未复权日线和截至 `as_of` 已公告的现金分红，用 `PriceBasis(...).bar(..., "cash_proportional_v1")` 生成当时可见的同单位价格。禁止把前复权价格当作名义成交价格。
2. `build_candidates(symbol)`：在每个除息信息时期内运行冻结的 `first_ma_pullback` 3.0.0；只取 `ma_period=20` 且 `entry_variant=early/confirmed` 的确认事件，命名 A20E/A20J。每个信号日重新截断价格和已知分红，复算特征、已确认枢轴、目标和不少于 3 的盈亏比。目标不存在或当日尚未确认就明确拒绝，不准后来补入。
3. `run_accounts(candidates, group_filter, exit_variant, fee)`：把冻结候选送入旧现金账户引擎；持有和简单趋势退出的精确定义、费用、资金期和重叠机会处理须由根协议固定。相对强弱只产生独立布尔字段和分组 ID，不改候选本体。

时期缓存只能作为提速手段：每个抽查信号日必须断尾重算，并与缓存框架截至该日的前缀逐值相等。新 ETF 历史较短时，周线环境和 SMA120 预热会自然减少甚至消除 A20 候选，不能放宽规则补样本。

## 相对沪深 300 强弱字段

建议字段为 `rs_ratio = etf_close / benchmark_close`、`rs_ma20 = rs_ratio.rolling(20).mean()`、`rs_above_ma20 = rs_ratio > rs_ma20`，仅在双方同一有效报价日对齐后计算，并在信号收盘后才可用。必须保存 `benchmark_symbol`、`benchmark_source`、`basis_as_of`、20 个组成日期和缺失原因。

协议还需固定基准口径。若用沪深 300 价格指数，而 ETF 用含现金分红转换的价格，两者在 ETF 除息附近会有机械跳变；这只能称为“相对价格强弱”。优先使用来源可靠、历史充分的沪深 300 全收益指数；若数据审计无法提供，就使用明确指定的沪深 300 价格指数并把上述局限写进结果，不能悄悄改用 510300。20 日窗口不足、基准停牌或日期无法对齐时写 `unknown`，不能默认为不通过。

## 模块 B 可复用范围

`b-research-fix` 已提供可执行的因果链：冻结的 `dense_breakout` 产生突破事件和密集区下沿失效位，`generate_candidates.py` 在每个信号日用截至当日的已确认枢轴或历史区间计算目标，并记录 `target_confirmed_at`、`target_source_date`；无目标会被拒绝，实际下一开盘还会重新检查盈亏比不少于 3。它也有断尾重算检查。因此现成修复输入可以在新 ETF 原始数据和分红事件合格后运行，不需要未来目标。

但该包自己明确说明仍是“修正后的 B 研究代理”：密集定义、埋伏切换以及九条无交易条件并未全部证明。建议协议只纳入 `variant=breakout`，单列为 `B-breakout-repaired-proxy`；不把它写成完整 B，也不把旧 API 的 `+R` 收益直接搬来。若根协议没有固定这层语义，本批先不运行 B 收益。

## 冻结依赖

- A 规则与配置：`research-twelfth-2026-09-08/research-package/src/lei_signal/` 和其中 `configs/rules.v2.yaml`；规则账本标明 `first_ma_pullback` 版本 3.0.0。
- A 因果适配参考：`research-twelfth-2026-09-08/adapter/build_candidates.py`。
- B 修复包：`research-eighth-2026-09-08/b-research-fix/research-package/`；候选参考为 `research-eighth-2026-09-08/generate_candidates.py`。
- 价格转换：`research-eighth-2026-09-08/product-qualification/price-helper/price_basis.py`。
- 现金账户：`research-broad-etf-technical-2026-09-08/execution/engine.py` 与 `metrics.py`。
- 投入资金口径：`research-invested-capital-metrics-2026-09-08/analysis/calculate.py`。

运行目录应复制上述必要代码和配置后锁定，使用独立 Python 进程并禁止写字节码，且核验所有导入都来自本批复制件，避免误加载生产代码或其他研究包。

## 协议固定前仍需解决

- 数据审计给出最终行业 ETF 清单、真实未复权日线、分红公告日/生效日，以及沪深 300 基准的精确代码和价格口径。
- 固定 A20E/A20J 是否分别与相对强弱开关形成四组；不同组是同一机会的对照，结果不能相加。
- 固定简单趋势退出的准确状态与次日开盘执行规则，并保留结构失效优先。
- 固定 B 是否进入正式收益路径；若进入，明确只用突破版修复代理及其版本标签。
- 固定账户期、费用、初始资金、每笔风险、同日/重叠候选优先级、持有基准及完整投入资金报表。

