# 六只 ETF 均线资金比较：现有输入与账户复用

本任务只为策略规格 §2.2、§4.1—4.4、§5、§15 的“道路”层准备研究输入；11项均线参与政策是简化研究政策，不是原 A/B/C/D 入场或退出。截止本交付，真实策略收益运行 0 次、联网 0 次、未改资格或旧原始证据。

## 本地证据读法

固定2022-01-01至2026-06-30，2022首个报价为01-04。六只都有原始名义开收盘价，20/60/120日状态所需预热也已在盘。每只应从 `source-manifest.json` 所列的 `nominal_execution_ohlc` 读开盘、收盘、最高、最低、成交量；日均线信号可从既有 `factor-six-etf-economic-momentum-2026-09-23/formal/{symbol}.csv` 的 `economic_index` 读收盘经济价，并与其 `nominal_close`、行动表交叉核实。经济指数含现金分红和份额变动，是信号价格，不是可以买卖的报价，也不是账户里可支配的分红现金。付款日未知时经济信号仍可计算，账户现金到账不可填写。

特别需要避开旧 `input-bundle.json` 给510050、510500、512100引用的 `exit_three_piece/pool/*.bars.parquet`：逐日比较它们与后来已归档的名义 CSV，收盘差异分别为1210/1337/1230个共同日期。510500在2020-12-21的旧 parquet 收盘为5.788、名义 CSV为7.075；把旧 parquet 当成交价会混用价格尺度。正式经济重建 `run.py::PRICE_PATHS` 已选择三份 `normalized/*.nominal-candidate.csv`；本任务沿用该身份，不回写旧包。588000所用 parquet 的覆盖与名义身份仍依既有资格材料核对。

行动覆盖表为84/84逐期完整，包含明确的“零事件”年份；这比旧输入包中五只 `action_complete=false` 更新。它证明来源表所涵盖的现金与份额事件可供事后重建，但不自动改旧 `qualified=false`，也不证明历史公告到达时间。510300的2022至2026上半年五次现金分红已有付款日，2018/2019补充核查和2020至2025候选年报须由主控明确接受本轮适用范围。159915与588000在本轮区间没有现金或份额事件，二者不因旧账户来源资格标签自动丧失本轮受限历史比较的计算可行性。

七笔仍缺实际现金发放日：510050的2023、2025；510500的2024、2025、2026上半年；512100的2025、2026上半年。年报已给登记日、场内除息日与每份金额，不能从除息日推断到账日。最小补证是逐笔本地/官方现金分红公告的付款日和页面、文件哈希，只补这七笔；付款日未补的三只保留原集合占位。510050的2021预热分红付款日不影响2022开始的账户现金，但金额和除息日仍进入经济信号预热。

经济指数所存 `actions.json` 的 `record_date` 并未随经济价事件输出；新账户输入必须按 `event_id` 联结已存 `candidate-action-records.json` 的登记日，并对510300核旧账户行动及新的年度材料。逐笔验证代码、每份金额、除息日和付款日后再转账户格式，不能因字段为空就让现金权利变成零。

## 账户复用边界

优先复用 `docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/run_accounts.py` 中这些纯计算段：

| 入口 | 签名/作用 | 复用条件 |
|---|---|---|
| `read_bars(path: Path)` | 读名义 CSV，并把 OHLCV 转为 `Decimal` | parquet 的588000需新raw中小型只读适配；日期标准化、唯一升序、正值检查先做 |
| `floor_lot(units: Decimal, lot=Decimal('100'))` | 按100份向下取整 | 交易单位由Task1确认；不替代实际申赎单位 |
| `execute_target(cash, receivable, units, price, target, fee, apply_band=False, lot=Decimal('100'))` | 计算目标份额、可用现金、单边费用；应收不当可用现金 | B0/B50/S/E/D按同一目标规则；B50再平衡规则以Task1为准 |
| `effective_reference(reference, actions, symbol, day)`、`unavailable(symbol, day, bar, reference, settings)` | 除息/拆分参考价与未能开盘成交判断 | 旧 settings 只含四只旧产品，不可直接用于六只；事件时点及限制表须适配，不能机械复用 |
| `simulate(account_id, symbol, method, fee, bars, actions, settings, method_signals, start, end)` | 完整现金、应收、份额、费用、拒单、逐日净值、年度表 | 只把循环与记账语义作为复用基底；不直接以旧 `method` 和旧 `INPUTS` 跑新政策 |
| `period_rows(daily, trades, period, initial_equity=100000.0)` | 年/月收益、次数、费用对账 | 先核 Task1 的估值日历、期末与恢复期定义 |

`simulate` 的局部副作用为调用模块常量 `INPUTS / dated-restrictions.json` 读旧限制表；`prepare()` 会写旧 `prepared-signals.json`，`main()` 会建旧 `account-results/` 并运行旧账户。模块在导入时设置 `sys.dont_write_bytecode=True` 并绑定旧 `INPUTS/OUT` 路径。**不能运行旧 `main()`、`prepare()`，也不能将旧 `simulate` 直接用于六只。** 在本次新raw目录做一份小型账户适配：从新协议加载六只名义价、经济信号和行动；按交易日推进收盘状态与下一允许开盘订单；调用可复用的份额/费用计算；输出现金、应收、份额、当日估值及拒单。适配时要移除旧固定输入路径依赖，并按本轮起点修正 `drawdown_intervals` 内写死的2014-12-31峰值日期；旧 summary 的 `conditional_product_qualification=true` 不能继承作新资格结论。

有两个时间点必须写成账户适配测试：510500的2022-08-26份额变动在日终实施，当天开盘不能先增份额；512100的2022-09-02日终合并且当天停牌，09-05才恢复报价。旧 `simulate` 在每天一开始就按 `effective_date` 处理 split，若直接喂既有行动会提前到当日开盘。现金分红则按登记日收盘份额产生权利，除息日记应收，实际付款日才转现金。对2022-01-04初始购入、未持有时除息、买入后登记、卖出后付款、买卖费用、100份取整、开盘不可成交后订单保留/取消、期末未付应收、现金+应收+市值对账各给一个手工小例，再做六只正式运行。

现有 `src/lei_signal/research/factor_account_adapter.py::replay_account(*, registry, batch, decisions, prices, actions, fee, variant)` 并非本轮直接入口：它把股票代码限制为旧14只混合池、四种 E 变体、固定两个费率，并载入旧 `no_exit_100` 账户。这可借鉴“先验哈希后只读导入、输出重新标识”的做法；改其旧参数或旧冻结账户会改变已封存实验。

## 下轮最小执行顺序

1. Task1协议冻结并人工核对资金小例后，锁六份名义价、既有经济信号、行动/覆盖与日历哈希；对于512100的一个缺报价日，沿用已记录的合并停牌语义，不填假价格。
2. 先核七笔付款公告。资料足够的510300、159915、588000可先做受限历史完整账户对照；另三只保留缺项与未运行状态，不缩短时期或删产品。510300须由主控显式决定本轮新证据的资格适用，不能把旧标签静默翻转。
3. 新raw薄适配只改输入选择、行动/下单时序、账户输出，不改旧代码和来源。测试入口：`tests/unit/test_factor_diagnostics.py`（完整账户对账字段）、`tests/unit/test_momentum_prototype.py`（行动字段与时点）、`tests/unit/test_factor_runtime.py`（经济价份额/现金语义），另在新raw加本轮手工小例；本任务未运行测试或账户收益。

本轮是对已看历史的受限研究。数据齐全只允许诚实模拟，不代表当年真实交易者已收到所有资料，也不代表信号值得采用。实际采用仍需独立的时点、成交与资金验收。
