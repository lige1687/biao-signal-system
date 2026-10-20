# 因子、信号与基准定义规范化：首批登记与复算

日期：2026-09-09。研究与验收原则 v1.0；定义规范 v1.0.0；登记表 v1.0.0。
本轮只处理研究定义、文档、机器登记与隔离校验，没有改变生产、冻结实验、正式交易权限或 OKR 完成度。

## 一句话结论（大白话）

首批 76 个研究对象已经有可追溯的定义卡，两条小例能从同一输入算回原结果：混合池 38 次月末名单完全相同，沪深300宽度四个日期与封存数字一致。现在后续 AI 能分清“算的是什么”和“还没证明什么”。这不是证明策略赚钱：创业板历史成分仍有缺口，历史数据何时到达仍未完全确认，旧策略和生产程序没有迁移。

## 1. 当前交付与范围

权威入口是 [定义管理细则](../research/definition-standard.md)，它从属既有
[研究与验收原则](../research/experiment-backtest-principles.md)，没有建立另一套总纲。
唯一手写登记表及定义卡正文是 [definitions.v1.json](../research/definitions.v1.json)。
完整展开卡片的只读快照见 [本次生成卡片](raw/definition-normalization-2026-09-09/run-02/resolved-definition-cards.json)。

已核对根 AGENTS、交易规格、规则账本、MACD 口径、板块方案、研究总规范、相关冻结协议、实际代码与结果清单。
本轮属于组合配置与研究可信度层，不把独立 ETF 研究冒充既有 A/B/C/D 触发规则。
检索仅到当前仓库及冻结清单明确引用的本地缓存，没有扩池、下载新行情、调参数、找新因子或重新运行所有账户。

## 2. 证据映射与最终处理

逐项公式、端点、行号与指纹见 [混合池完整映射](../research/definition-evidence-mixed-2026-09-09.md) 和
[宽度完整映射](../research/definition-evidence-breadth-2026-09-09.md)。下表补上最终处理状态与长期投入；
`sources` 名称对应登记表内完整路径与 SHA-256，不是无版本的泛称。

| 对象 | 绑定协议/代码/输入 | 程序实际定义 | 文档或设计定义 | 差异与本轮处理 |
|---|---|---|---|---|
| 混合池动量与资格 | mixed_protocol / mixed_code / mixed_prices / mixed_actions / mixed_pool | 自身有效报价 `I[t-21]/I[t-252]-1`；月选当日报价且累计≥273 | 252/21、动态资格 | 一致；原始值、排名、波动、前三、权重拆开登记；逐值与名单复算 |
| 波动值与分位 | mixed_code / mixed_protocol | 20个简单收益的样本标准差×√252；756窗至少252，当前值参与，相同值平均名次；≥0.8剔除，NaN放行 | “20日波动幅度”措辞本身不够精确 | 不猜成ATR或最高最低振幅；精确定义已登记，旧NaN放行保留 |
| SMA与月选/退出 | mixed_code / mixed_protocol；小池差异见混合映射 | full14月选不先过SMA；持仓收盘严格低于SMA200才排队退出 | 旧小池有月末均线准入 | 明确保留两种语义，不能把小池文字套到full14；新适配不改消费者 |
| 75%、月度与快速回补 | defense_protocol / defense_code / defense_results | 75%仅月目标；快速回补需实际全清、同产品净卖款、收盘≥SMA；月调仓优先清旧队列 | 冻结防守协议对应上述规则 | 定义映射完成；本轮不重跑账户或新增回补状态引擎，旧实现仍legacy |
| ETF连续信号价格 | breadth_runner::continuous_close / etf_actions / etf_510300 / etf_159915 | 首值为首价；除息参考价先减现金、再除拆分比例，连乘当前价/参考价 | 也称“连续价格” | 与混合池 `(close×拆分+现金)/prev` 不同；新增独立 `etf.price.continuous` 与 `etf.trend.*`，未冒称资产总回报 |
| 共同分母宽度 | breadth_code / breadth_protocol / breadth_inputs / csi_members | 当前成员、当前报价、SMA200可算为同一E；B50/B200严格>；覆盖≥90%；原值0—100 | 本轮要求共同分母 | 冻结研究已共同分母；隔离比例版0—1单列ID，与旧百分数值逐值比对 |
| 日常及生产宽度 | breadth_legacy / all_a_legacy | 各N独立分母；生产允许最多5交易日旧状态、低覆盖保留值；日常全A另有最低100只等要求 | 不能套用本轮共同分母/缺失返回规则 | 分别登记legacy，不改生产、不重写旧宽度结果 |
| 全A、沪深300、创业板指数 | breadth_prepare / breadth_quality / breadth_inputs | 全A用缓存列首末报价推集合；沪深300每20交易日探测成员；创业板链曾出现101成员而中断 | 理想是完整历史生效成员 | 分别B级有限、B级有限、C级阻断；创业板指数不等于全创业板；只暂停该数据分支 |
| 宽度转强确认 | breadth_runner / breadth_results | W1/W2是ETF日历上当前宽度减20行前宽度>0；W3是自身价格>SMA50，只约束加仓 | 早先提案未必已运行 | 实際仓库全A/沪深300相关分支已运行，不能标成全未运行；创业板四条仍未运行。既有结果不因登记重新算作成功 |
| 三档与简单基准 | breadth_runner / breadth_protocol / ETF输入指纹 | 周末有效宽度，<43.3满额、[43.3,56.7)半额、其余0；5个百分点免调差额严格小于才免调；B1价格200、B2月50% | 简单对照须有完整执行规则 | 股票信号集合与固定交易ETF分开；基准不继承“成分股200条+90%覆盖”资格 |
| 含分红持有B0 | breadth_runner:218–236 / breadth_protocol | 支付日开盘前现金到账，有可交易开盘可同日再买 | 协议写“支付后下一开盘” | 冲突保留。卡写实际同日规则及限制，不能当成已符合文字协议；不改旧账 |
| 留现金/支付日再投旧参照 | hold_protocol / hold_code | 初始10万元；后者支付日开盘前到账、当日可买，另有延期/整手规则 | 与B0初始100万元不是同一账户版本 | 各自独立卡，不因都称“持有”就合并 |
| 长期投入及季度再平衡 | dca_protocol / dca_code / dca_lock | 2013-07-30至2026-06-30；周一00:00入1000，四ETF各25%；季度首日排队并等全部可交易；用现金+旧参考市值形成预算，应收不可花 | 持续投入与完整账户 | 单列季度、无再平衡、单510300；固定产品不继承273条选强资格；策略净值与投资者资金回报分开。仅映射，本轮不复算旧资金路径 |
| 权重、方向与利润份额 | concentration_code / dedup_protocol | 权重=市值/账户权益或在场市值；方向互斥归并；方向利润/账户净利润另算 | “集中度”可能混指多种比例 | 明确分母、自然日统计与资金贡献边界；纯函数只复算权重，不把利润占比当暴露，未新造集中度收益因子 |
| 现金与无风险收益 | cash.zero，相关账户协议 | 模拟现金利息为0 | 风险调整模型需要适配无风险序列 | 未找到合格统一序列；models为空，不构造严格超额收益、β或α |

## 3. 实际实现、测试与失败记录

研究专用 [definitions.py](../../src/lei_signal/research/definitions.py) 提供登记解析、精确版本/依赖/用途校验、
实际来源指纹校验、动量/均线/分位/宽度/权重等纯计算、身份绑定的小型调用及实验 manifest。
没有生产消费者导入它，不包含券商接口或新账户回测引擎。

采用先写反例、看它失败、再实现的测试过程，保留结论而不是只报最终绿灯：

| 阶段 | 实际结果 | 含义 |
|---|---|---|
| 初始合约测试 | 15失败：模块尚未实现 | 验证测试确实依赖新实现 |
| 纯函数后、登记表前 | 13通过、2失败：缺登记表 | 不跳过登记解析 |
| 首次登记与run-01 | 15通过；第一轮局部真实复算通过 | 这是中间草稿，不是最终验收；随后审阅发现接口缺口 |
| 当前报价/时区/身份绑定反例 | 4失败、14通过 → 修正后18通过 | 不能只从“原本15通过”推断边界安全 |
| 字段/来源/跨缺失上穿反例 | 8失败、20通过 → 修正后28通过 | 补空名称、负容差、错误时区、空执行规则、来源漂移与上一有效报价 |
| 最终单元及报告库回归 | **32通过，1.71秒** | 28项新研究测试 + 4项既有报告库测试；补检重复事件及上海/UTC/无时区日期 |
| 最终静态检查 | **All checks passed** | 仅检查本轮3个Python文件，没有对全仓库作通过承诺 |

实际命令：

```sh
python3 -m pytest tests/unit/test_research_definitions.py tests/unit/test_experiment_reports.py -q --tb=short
python3 -m ruff check src/lei_signal/research/definitions.py scripts/verify_research_definitions.py tests/unit/test_research_definitions.py --output-format concise
python3 scripts/verify_research_definitions.py --output docs/experiments/raw/definition-normalization-2026-09-09/run-02
```

复算结果：[verification.json](raw/definition-normalization-2026-09-09/run-02/verification.json)。
76卡、30个登记来源计算前后指纹一致，宽度例确实用了冻结清单引用的真实本地缓存，不是合成行情。
174项比较、497,749个数值位置（包含重叠前缀，不是这么多独立市场证据），最大绝对误差
`1.4210854715202004e-14`，低于声明的 `1e-10` 容差；计数与名单要求精确一致。
混合池38次月末前三名单全部一致；沪深300四天B50/B200相对封存值误差都是0。

手算/边界包括：252/21端点、SMA含当日与相等、上穿事件、波动样本标准差与并列分位、0.8剔除、
273资格与当日缺价、全缺失/预热/新股/成员变化、缺报价停牌、分红拆分与重复事件、
单位缩放、追加未来行不改变前缀、历史输入修订会改变结果、完整账户/在场资产分母、版本/依赖/用途/来源漂移。
公司行动的合成例仅核算法，不当成真实资料到达时间的证明。

独立复核由 Sol 完成，报告为 [定义独立审阅](../research/definition-review-2026-09-09.md)。
主控另读关键公式、补反例、核ETF价格连接/B0时点与真实输入输出。未使用Spark（当前子agent工具模型列表不提供该选项），
没有为调用模型另建用户任务或消费额度重置。独立审阅不等于全策略状态机已重算。

## 4. 两个最小接入示例

入口统一为 [verify_research_definitions.py](../../scripts/verify_research_definitions.py)，只允许新输出目录，
不会调用旧main或任何会覆盖旧结果的账户入口。目录 `run-02` 约2.1MB；`run-01` 原样保留为草稿尝试史。

### 混合池

保存冻结名义价/行动及由旧函数构造的经济指数输入，独立复算动量、SMA200、波动分位、资格与月选名单。
真实资料中的公司行动连接并未被宣称独立核验；第三个AI可直接使用保存的合法经济指数输入复算这些信号。

```python
import pandas as pd
from lei_signal.research.definitions import calculate

data = pd.read_csv('docs/experiments/raw/definition-normalization-2026-09-09/run-02/mixed-signal-input.csv', dtype={'symbol': str})
q = data[data.symbol == '510300'].set_index('date').economic_index
result = calculate('mixed.momentum.raw@1.0.0', q)
# result包含准确reference、fraction单位、逐日值和缺失约定，不包含交易授权。
```

[混合输出](raw/definition-normalization-2026-09-09/run-02/mixed-output.csv) 与
[混合manifest](raw/definition-normalization-2026-09-09/run-02/mixed-manifest.json) 分别存值和一次性的对象/输入/代码身份。
历史观察截止2023-12-29；本轮真实复算可得/决策时刻是2026-09-09，不虚构历史数据已在收盘瞬间到达。

### 宽度

[收盘小片段](raw/definition-normalization-2026-09-09/run-02/breadth-input.csv) 与
[四天历史名单](raw/definition-normalization-2026-09-09/run-02/breadth-members.csv) 已复制到独立目录；每股保留200条预热及目标日。
引用 `breadth.csi300.b50.common@1.0.0`、`breadth.csi300.b200.common@1.0.0`；
输出 [breadth-output.csv](raw/definition-normalization-2026-09-09/run-02/breadth-output.csv)，元数据见
[breadth-manifest.json](raw/definition-normalization-2026-09-09/run-02/breadth-manifest.json)。

2025-06-13有300成员、299合格，B50为0.5484949833；6月16日成员变动后合格数298，B50为0.5671140940。
两日宽度变化不能全称价格转强。输出同时有成员总数、实际报价数、共同合格数、覆盖率与缺失原因。

## 5. 接入范围、限制与下一步

已接入：新复算脚本、单元测试、根 AGENTS、研究报告模板和文档导航。
登记中的旧混合池、快速回补、宽度账户、日常全A/生产宽度、分红持有与定投入金引擎均只做版本映射，
没有把它们迁到新登记消费者，也未向旧冻结 manifest 填新版本号。

尚未核验或受阻项：

- 创业板指数历史成员链不完整；该研究账户仍未运行，不能因算法合成测试通过而升级数据资格。
- 全A生存范围与沪深300每20交易日探测成员仍有历史覆盖限制；共同分母只解决分母一致，不消除此偏差。
- 历史供应商报价/行动真正到达时刻缺失；人民币海外ETF报价也不等于境外市场同一时刻可成交。
- ETF旧连续价对缺报价期间行动及同日多事件的处理只映射，未在本轮修正；不能称严格总回报因子。
- 月末完整性、快速回补排队/净卖款预算及所有完整账户路径只核源代码定义，未新增独立状态引擎测试。
- 无适配收益模型与无风险序列；不报告α、预测能力或新的年化。本轮不能替代公平增量对照与实盘执行验收。

最能改变下一步可用性的工作是补齐已知历史成员/到达时间证据，并单独冻结后续消费者接入协议。
这只是未完成事项，不是本轮自动启动的数据扩充、生产迁移或新实验授权。

## 6. 文件修改清单与交接

新增：`docs/research/definition-standard.md`、`definitions.v1.json`、两份证据映射、独立审阅；
`src/lei_signal/research/definitions.py`、`tests/unit/test_research_definitions.py`、
`scripts/verify_research_definitions.py`；本报告与独立输出目录。

增补已有入口：根 `AGENTS.md`、`docs/README.md`、`docs/research/experiment-report-template.md`、
`docs/experiments/registry.json` 与 `INDEX.md`。既有脏工作区的其他修改未处理、未撤销。
代码基点HEAD为 `91c720ed46ad95237dcbc56575ac122ab606edd8`，但工作区有未提交修改，
因此复现以 [产物清单](raw/definition-normalization-2026-09-09/run-02/artifact-manifest.json) 的逐文件哈希为准，不能只看Git提交号。

## 7. 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 改变什么决策 | 让研究先绑定定义和合法输入；不改变买卖决策 |
| 比谁好、增量是什么 | 比对冻结实现和手算值；没有比较新增策略收益 |
| 钱从哪里来 | 本轮无新资金账户结果；资金贡献—决策增量—风险解释三层流程仍沿用总规范 |
| 代价与可执行性 | 小规模本地复算；数据缺口与执行假设独立保留，未验收真实成交容量 |
| 现在怎么办 | 采用研究登记与核验入口；旧消费者保留legacy；受阻资料不升级 |
| 授权边界 | 研究定义交付完成不等于策略有效、发现α或获准生产；不改OKR完成度 |

## ARCHIVE

2026-09-09封存本轮规范化交付，报告库分类“方法论与验证”，结论 `mixed` 表示局部核验完成而资料与全仓库迁移仍有边界。
不存在新交易授权。旧报告、旧封存数据、冻结实验与生产规则均未被覆盖。
