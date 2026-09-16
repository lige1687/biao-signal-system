# 小型研究因子库 v0 建设交付（2026-09-09）

## 一句话结论（大白话）

这期把之前只登记了名字的研究指标，真正接进了统一计算程序，并用老的14只ETF混合池跑了一次受控对照。
要回答的问题是：**"按涨幅选最强三只"的老选强办法，再加一道"波动太高就不买"的过滤，到底值不值？**
答案是**有条件、不能直接说好**：在2020年底到2026年中整段历史里，加过滤后赚得更多（费用低的口径下多赚约59.3万元，费用高的口径下多赚约51.2万元），
但过程中最大回撤反而更深约5个百分点、从坑里爬出来等得更久，手续费也花得更多；而且**分段看方向是反的**——2020-12至2024年过滤是少赚的，多赚全部来自2025年1月到2026年6月这一段。
在"不选强、所有合格产品平均分"的用法下，同一道过滤两头费用下都少赚且回撤更深。
所以这是一个"看条件的交换"，不是一道普遍有效的改进，**最多算值得继续验证，不构成可上线采用的结论**。
工程交付本身（统一计算、身份绑定、完整资金对账、可复现运行）已达到任务书验收要求。

## 0. 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 决策与资金用途 | 不新增交易模块；检验"波动过滤加在选强上值不值"，同时验证因子库能否被真实研究调用 |
| 基准与增量 | 四格E00/E01/E10/E11，固定名单/区间/资金/费用；主比较E11−E10只变"加不加过滤" |
| 收益解释 | 多赚集中在2025-2026且伴随更深回撤；过滤在等权用法下少赚；没有把任何未解释差额叫"α" |
| 代价与执行 | 最大回撤加深约5个百分点；回本等待多97/137天；费用增加约2.8万/5.4万元；成交规则未改 |
| 证据与结论 | 两费用方向一致但两固定时期方向相反→**依赖条件（mixed）**；单池单段历史，至多值得继续验证 |
| 下一步与边界 | 是否接受"多赚但更难受"由用户决定；继续验证需另立冻结观察，本轮无生产授权、无OKR写入 |

## 1. 任务与规范版本

- 任务书：`docs/superpowers/plans/2026-09-09-factor-library-v0.md` 计划版本1.0.0；执行者按 Task 1–6 实施，本报告是交回主控独立验收的交付件，不自宣布验收。
- 规范：`docs/research/experiment-backtest-principles.md` v1.0、`docs/research/definition-standard.md` v1.0.0；根 AGENTS.md 约束全程生效。
- 实验性质：新的历史受控研究，不是"没见过的新数据验证"；不搜参数、不扩池、不接新数据。

## 2. 实际绑定的对象与代码（任务书 §8.1 要求）

以下对象不是"登记了"，而是本期被代码实际调用并核验：

| 对象 ID@1.0.0 | 实际绑定位置 |
|---|---|
| mixed.price.economic | `factor_runtime.reconstructed_economic_index`（显式历史重建分支） |
| mixed.asset.total_return | 经济指数相邻有效报价区间收益（带前后观察日期） |
| mixed.momentum.raw / mixed.rv20 / mixed.rv_percentile | `definitions.quote_features/realized_volatility/historical_percentile`，经 `build_mixed_batch` 调用，无第二份指标公式 |
| mixed.volatility_allowed / mixed.eligible / mixed.momentum.rank / mixed.top3 / mixed.target.equal | `factor_runtime.monthly_decisions`（0.8整档剔除、NaN放行、同分代码升序、无候选全现金） |
| trend.sma200 / trend.distance200 / trend.above200 | 批量输出；仅写入 `holdings-description.csv` 描述持仓，不参与新买卖 |
| risk.product_account_weight / direction_account_weight / product_invested_weight | `factor_diagnostics.daily_product_weights/direction_weights_from_product` |
| risk.profit_direction_share | 各路径 `direction-profit-*.csv`（方向盈亏÷整账户净损益） |
| cash.zero | 账户现金利息固定0，引擎层与诊断层一致 |
| mixed.no_exit_100 | 仅 E11 引用为兼容参照（冻结函数原样重放） |

新增 policy 卡（**追加新ID，旧78卡零改动**，登记表容器 1.1.0→1.2.0）：
`policy.mixed.eligible_equal@1.0.0`（E00）、`policy.mixed.eligible_equal_rv_filtered@1.0.0`（E01）、
`policy.mixed.top3_equal@1.0.0`（E10）。三卡的证据指向 run-01 产物，状态均 not_authorized。

## 3. 输入身份与"旧东西没被改"的证据

- 冻结输入全部来自登记表 sources：混合池 prices.csv / normalized-actions.json / candidate-pool.json、
  冻结防守实验 protocol.json 与 execution/run.py、其8账户结果、互斥方向分组脚本；prepare 阶段 31→34 个来源哈希全部匹配，无漂移。
- 登记表冻结快照：`prepare-02/frozen-definitions.v1.0.0.json`（78对象/1.1.0），run 的每张 manifest 都用显式 `registry_path` 指到这份快照；
  比对脚本确认 run 之后新登记表里**原78张卡逐字段无变化**，只多出3张卡和3个新来源。
- 冻结引擎只读使用：`factor_account_adapter.load_frozen_defense` 先核哈希再 import，不调其 `main()`，不改其全局常量；
  每次 replay 后复核 defense_code/protocol/prices/actions 四源哈希一致（测试 `test_replay_keeps_frozen_sources_unchanged`）。
- 历史到达时间：21个公司行动事件全部没有 available_at 时间戳，严格口径函数会拒绝；本期统一走显式标记
  `historical_reconstruction_only` 的重建分支，manifest 与 quality 报告都写明"数值可复算、历史时点合法性未证实、容量未验收"。
- prepare-01 因协议文本两处换行瑕疵被 prepare-02 取代（未跑任何账户），记录在 run-01/attempts.json，旧目录保留未删。

## 4. 兼容闸门（先闭合才允许解释新三格）

E11（两档费用）与冻结 `no_exit_100` 旧结果逐行比较（`run-01/compatibility.json`）：

| 路径 | 权益最大绝对误差 | 成交逐行 | 信号逐行 |
|---|---|---|---|
| E11-fee0.001 | 4.66e-10 元 | 完全一致 | 完全一致 |
| E11-fee0.002 | 4.66e-10 元 | 完全一致 | 完全一致 |

另有单元测试把新链路与"现场重调旧函数"再比一次（final/fees/交易数一致）。闸门通过后才跑 E00/E01/E10。

## 5. 主要结果（完整表见 run-01/decision-comparisons.csv）

整段 2020-12-01～2026-06-30，初始100万元：

| 路径 | 净损益(元) | 总收益率 | 年化 | 最大回撤 | 最长回本等待(天) | 交易笔数 | 费用(元) |
|---|---|---|---|---|---|---|---|
| E00 所有合格等权 | 908,394 / 898,748 | 90.8% / 89.9% | 12.3% / 12.2% | -24.6% / -24.7% | 1112 / 1120 | 727 | 5,417 / 10,797 |
| E01 等权+过滤 | 813,149 / 750,837 | 81.3% / 75.1% | 11.3% / 10.6% | -34.8% / -35.4% | 1044 / 1051 | 655/653 | 37,607 / 73,759 |
| E10 选前三不过滤 | 1,503,634 / 1,424,646 | 150.4% / 142.5% | 17.9% / 17.2% | -28.0% / -28.6% | 1036 / 1108 | 244/245 | 41,351 / 81,226 |
| E11 选前三+过滤 | **2,096,475 / 1,936,350** | 209.6% / 193.6% | 22.5% / 21.3% | **-33.0% / -33.7%** | 1133 / 1245 | 265/264 | 69,819 / 135,416 |

（每格两数分别为每边0.001 / 0.002费用。）

固定差额（差额只用完整净损益算钱；年化差、回撤差单独列，不相加成"利润贡献"）：

- **主比较 E11−E10**：+592,842 / +511,704 元；年化 +4.6/+4.1个百分点；最大回撤**加深**5.0/5.2个百分点；
  回本等待多97/137天；费用多28,468/54,191元；交易多21/19笔。
- 辅助 E01−E00：−95,245 / −147,911 元；回撤加深10.2/10.7个百分点——同一道过滤，在等权用法下是亏的。
- E10−E00 同时改变了"选不选强"和"持有几只"，只能称**选强政策差异**，不叫动量因子溢价。

分段（同一条连续账户切开，不在2025年初重新入金）：

| 路径 | 2020-12～2024净损益(费0.001) | 2025-01～2026-06净损益 |
|---|---|---|
| E10 | 434,778 | 1,068,855 |
| E11 | 248,930（**过滤在此段少赚约18.6万**） | 1,847,545（**此段多赚约77.9万**） |
| E00 | 79,244 | 829,150 |
| E01 | 68,823 | 744,326 |

过滤在67个执行月里43个月剔除过产品（被剔次数最多的是515880通信21次、515050通信20次、512400有色18次、518850黄金18次）。
按任务书 §2.3 的判定规则：两费用方向一致但**两固定时期方向相反**，记"依赖条件"；增收与更差的回撤并存，是交换而非免费改进；
不替用户决定这个代价值不值。未解释差额没有称为 α 或运气。

## 6. 资金核账（0.01元容差）

- 8条路径全窗口与两个分期，"净卖出−含费买入+已付分红+期末应收+期末持仓"之和分别等于期末权益−初始资金；
  最大误差：全窗口 1.16e-9 元、分期 1.46e-9 元（远小于0.01元），见 `quality-report.json`。
- 期末所有路径应收≈0（分红均已到账），期末现金/市值列于各路径 capital-contributions.csv；手续费在现金流内、不重复扣。
- 方向权重按冻结 group_accounting.py 的14个互斥方向字面量重建（脚本顶层会写文件，故只解析不导入）；方向是同一笔钱的另一种归并，不与产品贡献相加。

## 7. 文件清单与复现入口

新增代码/测试：

- `src/lei_signal/research/factor_runtime.py`、`factor_account_adapter.py`、`factor_diagnostics.py`
- `scripts/run_factor_library_v0.py`（prepare/run 单一入口；输出目录禁止覆盖、自动换编号）
- `tests/unit/test_factor_runtime.py`（14项）、`test_factor_account_adapter.py`（8项）、`test_factor_diagnostics.py`（7项）
- `tests/integration/test_factor_library_v0.py`（3项，含完整研究跑两遍验证不覆盖、篡改协议被拒）
- `src/lei_signal/research/definitions.py` 仅一处兼容性扩展：`make_manifest(registry_path=...)`，默认行为不变；旧测试新增2项（30项）
- 报告模板新增 §8.1"实际调用定义绑定与运行证据"

产物目录（全部带 manifest/哈希）：

- 冻结准备：`docs/experiments/raw/research-factor-library-v0-2026-09-09/prepare-02/`（protocol、来源清单、登记表快照、基线测试、工作区状态）
- 正式运行：`.../run-01/`（8个 paths/<路径>/ 各14张表+manifest；根目录 summary/compatibility/quality/attempts/artifact-manifest/test-results，共158个文件）
- 宽度跨线回归：`.../breadth-regression-01/`（只重跑既有小例，78定义/31来源通过，未启动W0–W3新账户）

复现命令（目录存在时自动换编号）：

```sh
python3 -m pytest tests/unit/test_research_definitions.py tests/unit/test_factor_runtime.py \
  tests/unit/test_factor_account_adapter.py tests/unit/test_factor_diagnostics.py \
  tests/integration/test_factor_library_v0.py tests/unit/test_experiment_reports.py -q
# 66 passed
python3 scripts/run_factor_library_v0.py prepare \
  --output docs/experiments/raw/research-factor-library-v0-2026-09-09/prepare-01
python3 scripts/run_factor_library_v0.py run \
  --protocol docs/experiments/raw/research-factor-library-v0-2026-09-09/prepare-02/protocol.json \
  --output docs/experiments/raw/research-factor-library-v0-2026-09-09/run-01
```

## 8. 失败尝试与阻断项（不覆盖保留）

- prepare-01 协议文本两处换行瑕疵 → prepare-02 取代（attempts.json 已记录）。
- 开发中实际遇到并修正：严格链对缺 available_at 的旧事件给 KeyError（据此明确历史重建分支与严格分支分离）；
  合成测试一度用同价开高低收被引擎判为"一字板"全部延期成交（修正测试数据，引擎未动）；
  冻结CSV文本往返带来1e-10级金额显示差（比较用数值容差，成交身份字段仍逐行精确）。
- 仍存在的资料限制：历史数据到达时间无法证实；14只现存ETF存活池选择偏差与重复经济方向；实际成交容量未验收。
- 阻断项：无。所有停止条件（来源漂移/E11不兼容/核账超0.01元）均未触发。

## 9. 未接入的消费者与没做的后续阶段

- 生产规则、Web/API、Streamlit、既有冻结实验脚本：全部未改、未迁移，仍标 legacy/mapped。
- 没有做：合格的基础收益参照（市场模型）、收益解释回归/归因模型、参数搜索、扩池、新数据、W0–W3宽度账户、自动下单。
- 因子库目前唯一消费者是本研究入口；`calculate()` 未扩绑本期对象，旧消费者行为不变。

## 10. 主控独立验收建议（对照任务书 §5）

建议重点抽查：E11兼容证据（compatibility.json）、独立累加任一8路径资金账、
prepare-02快照与run manifest的显式绑定、错误版本/价格身份拒绝测试、宽度小例回归。

## 11. 边界确认

- 生产采用：**未授权**。OKR台账：已阅读 `docs/okr/README.md` 并只读核对（`~/.lei_signal_lab/system_upgrades.db`）。
  与因子库相关的唯一条目是 `okr-4f4157e2957e`「因子库后续：外部资源适配与分批接入」，状态 planned，描述的是 v0 之后的消费者接入待办，
  本期建设不完成它；v0 建设本身无独立台账条目。未获明确写入授权，本轮**未改任何完成度**，
  是否把 v0 交付挂为新证据/新目标由用户授权后处理。
- 模型分工：全部工作由当前执行模型完成（未实际派发 Sol/Spark 子任务），无额度回退事项需记录。

## 12. ARCHIVE

- 结案日期：2026-09-09（交付待主控独立验收）
- 最终结论：mixed（依赖条件；过滤增收但回撤更深、分段方向相反；至多值得继续验证）
- 生产采用：未授权
- 原始数据与复现入口：见 §7
- registry.json：已登记；INDEX.md：已补导航
