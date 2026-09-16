# LeiSignal 自有因子与信号研究体系：首轮通用能力执行规格

> 执行者：用户指定 ZCode/GLM；主控与独立复核：当前 Codex 任务。按任务顺序执行，技能可用时使用 executing-plans 与 test-driven-development；不自动派生其他 agent。版本 1.0.0，2026-09-14。

## 1. 用户目标与这轮交付

用户要求的是自己的因子研究体系：可追溯地积累双均线、宽度等技术特征与状态，研究其预测作用、过拟合风险、策略贡献与适用标的，最终为真实交易提供可核查依据。

固定池属于每次实验的协议，而不是平台的边界。不能先看结果挑适用标的，再用同一段数据证明有效。先声明假设的适用范围，实验中固定名单/成员规则，检验后将支持与不支持的范围分别记录。

本轮交付一个**离线、可调用、带测试和报告的研究工具**，不是只写规划，也不是批量寻找赚钱参数。真实材料不足只阻断对应真实结论；不阻断合成小例、通用接口与现有函数复用。

本轮不承诺发现有效因子，不承诺排除过拟合，不取得生产权限。归因分资金贡献、决策增量、风险/收益模型解释三层，不能相加重复记账。IC 表示当前分数与之后结果的相关程度，不等于可获利、完整策略价值或收益解释能力。

## 2. 权威入口、现有事实和复用顺序

开工先读根 AGENTS、CLAUDE、交易规格、规则账本及其指定策略文档，再读：

- `docs/research/experiment-backtest-principles.md` v1.1；`definition-standard.md` v1.1.0；`ai-execution-contract.md` v1.0.1；`experiment-report-template.md` v1.1.0。
- 唯一对象登记表 `docs/research/definitions.v1.json` v1.2.0。本轮只读，先保存其 SHA 和展开卡；不让新消费者改变旧卡或冻结协议。
- `docs/research/factor-research-roadmap-2026-09-10.md` 顶部最新方向纠正；`docs/experiments/factor-research-workbench-mandate-2026-09-14.md`（目标、OKR、派发状态）。
- 上轮主控 `docs/experiments/momentum-prototype-controller-review-2026-09-13.md` §13：S1–S3 收口，无本轮返修。不重查全部旧日志。
- 本地 Qlib 审阅 `docs/experiments/qlib-alpha158-definition-review-2026-09-12.md`，以及 `docs/experiments/raw/research-data-provenance-2026-09-10/reuse-decision.md` 若实际存在。只为复用定位，不开启新外部研究。

已核到的复用面：

| 能力 | 实际代码 | 本轮做法 |
|---|---|---|
| 定义解析、均线/涨幅/宽度计算 | `src/lei_signal/research/definitions.py` 的 resolve、quote_features、breadth、calculate | 薄适配，不复制第二套公式 |
| 混合池计算与已有账户 | `factor_runtime.py`、`factor_account_adapter.py` | 不改其固定池/政策；不调用旧真实账户入口 |
| 未来目标、并列平均名次 IC | `momentum_prototype.py` 的 build_targets、rank_diagnostic | 复用固定目标与数学核，外层增加通用列/时点合同，不能把全部指标都改名 momentum |
| 资金贡献/净损益核对/账户比较 | `factor_diagnostics.py` 的 capital_contributions、reconcile、compare_accounts | 复用；额外校验事件映射，采用合成完整台账示例 |
| 双均线共同确认状态 | `rules/dual_ma.py::dual_ma_bull_state` | 只读调用，不是新设交叉买点 |
| EMA 计算 | `features/indicators.py::seeded_ema` | 复用种子/预热规则，不改生产函数 |
| 数据资格 | `data_snapshot.py`、`data_quality.py`、`input_preflight.py` | 保留旧拒绝原因，不放宽检查，不补未知 available_at |

`definitions.calculate` 当前只支持部分对象，不能把已登记等于已接入。已有 rank_diagnostic 说明“全仓没有IC工具”的旧路线图文字已过时；先盘点再做增量。

## 3. 范围、预算与文件权限

工作区：`/Users/yongbiaoli/Desktop/lei-signal-lab`。当前有大量他人未提交代码，不能只 checkout HEAD 构建空白副本、reset 或覆盖现有修改。仅新增隔离研究包和自己的输出；不启动 API/web 预览服务。

允许新建：

```text
src/lei_signal/research/factor_lab/__init__.py
src/lei_signal/research/factor_lab/contracts.py
src/lei_signal/research/factor_lab/adapters.py
src/lei_signal/research/factor_lab/diagnostics.py
src/lei_signal/research/factor_lab/validation.py
src/lei_signal/research/factor_lab/attribution.py
src/lei_signal/research/factor_lab/runner.py
scripts/run_factor_lab.py
tests/unit/test_factor_lab_contracts.py
tests/unit/test_factor_lab_adapters.py
tests/unit/test_factor_lab_diagnostics.py
tests/unit/test_factor_lab_validation.py
tests/unit/test_factor_lab_attribution.py
tests/integration/test_factor_lab_cli.py
docs/research/factor-lab-usage.md
docs/experiments/factor-research-workbench-v1-2026-09-14.md
docs/experiments/raw/factor-research-workbench-v1-2026-09-14/
```

允许修改：实验 registry/INDEX 的本轮条目；路线图只追加本轮实际交付入口。不得改现有研究模块、定义卡、生产规则、UI/API、旧测试、旧 raw、价格/成员缓存和账户数据库。必要研究夹具生成脚本放自己的 raw 并纳入代码身份，不无限增加模块。

预算：外部网络0（ZCode模型服务与完工回调除外）；新增依赖0；真实收益/账户/动量/因子检验运行0；真实数据只读字段/身份/资格检查最多1批，限已有 full14 快照，不重算指标或补资料。该批不是完成前置条件，资料不合格保留原因。正式合成端到端示例最多3类，每类初跑1次+纠错1次；失败占次数。局部单测按需，完整相关回归最多2次，记录实际计数，不全仓运行。额度用尽停止受影响分支，交可验证产物。

不安装 Alphalens/Qlib/vectorbt/Backtrader/LEAN；保留后续适配接口和已审阅决策，不新造框架替代它们。无扫参、批量造新因子、训练预测模型、自动选池、交易和资金扩大权限。

OKR由主控写入。执行者只读任务合同中的方向/子任务ID，在报告给实际里程碑证据和下一步；不得直接写真实OKR或勾完成。提交git、部署和生产合入均不授权。

## 4. 数据与研究接口合同（以下均为待实现）

### 4.1 一份定义、多种用途

```python
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class ResearchBatch:
    values: pd.DataFrame
    metadata: dict
    findings: list[dict]

def calculate_batch(reference: str, inputs: dict, *, protocol: dict) -> ResearchBatch: ...
def evaluate_predictive(batch: ResearchBatch, targets: pd.DataFrame,
                        *, protocol: dict) -> dict: ...
def audit_validation(pairs: pd.DataFrame, trials: list[dict],
                     *, protocol: dict) -> dict: ...
def explain_strategy(accounts: dict, *, model_card: dict | None,
                     protocol: dict) -> dict: ...
def run_protocol(protocol_path, output_dir) -> int: ...
```

`values` 行键：`observation_date, entity_id, value, missing_reason`，不因缺值删掉观察。metadata 保存 `reference`、完整卡或候选绑定、type、unit、用途、数据/名单/代码/协议身份、币种日历、时间证据、synthetic、definition_status、data_status、implementation_status、effectiveness_status、production_authorization。每行不重复大段卡片。

输入必须显式提供价格尺度、交易日历、股票/产品成员版本、生效与可得时点；禁止由当前名单冒充历史名单。实体轴 `instrument` 和 `universe` 区分单产品指标与市场共同状态；宽度一条观测不能复制成14份独立证据。

协议显式区分 `calculation_only / predictive_diagnostic / state_diagnostic / strategy_explanation`；资料模式 `synthetic / historical_reconstruction / qualified`。本轮正式输出仅 synthetic；真实只读资格结果不能输出新IC。qualified接口可由严格合成小例测试逻辑，但必须保持synthetic，不输出真实资格成功。

身份/格式失败退出3；合法资料不足返回2并完整写原因；合成检查完成退出0并常驻synthetic。不提供跳过核验、强制通过或覆盖开关。

### 4.2 首批支持的已有对象与一个源代码绑定案例

- 已登记：`mixed.momentum.raw@1.0.0`、`mixed.rv20@1.0.0`、`trend.distance50@1.0.0`、`trend.distance200@1.0.0`。
- 宽度：`breadth.csi300.b50.common@1.0.0`、`breadth.csi300.b200.common@1.0.0`，同E200合格分母、coverage>=0.9，缺成员/不足/零分母返回缺失。用合成“指数成分”示例，不能叫真实沪深300证据。
- 双均线示例：`candidate:lei.dual_ma.bull_state@draft-1`，只表示本轮源代码绑定候选，不冒充已登记因子。冻结源码和以下语义：Close>EMA20 且 Close>SMA20，两均线相比前观察上升，signal_color=green；不是只看EMA/SMA交叉，也不是要求同日上穿。

双均线候选附完整定义卡草案，放本轮 raw，不建立第二份机器登记库。调用只读原函数；原函数预热/缺失输出False需在候选卡写清并另外记录 readiness，不把未就绪混成有效看空样本。需要推导绿色时严格绑定既有颜色函数/定义，不能调用者任意填green；合成单位测试可直接给frame，正式合成案例必须走已核指标与颜色计算。

此候选仅覆盖已有状态的登记准备和合成接入，不创造成熟收益因子，不改生产。若查出实际代码/配置与上述含义冲突，候选暂停而其余对象继续。

库本身不写死14产品；适用范围由每张卡约束。使用同一API跑3实体与5实体两套合成输入，改名称不影响无量纲计算。不能据合成跨实体测试宣称混合池卡已适用股票或所有市场。

## Task 0 — 建立现状清单与冻结运行合同

- [ ] 检查工作区和上述复用面，交 `capability-map.md`：能力、实际API、已实现范围、缺口、本轮复用/薄适配/延后，不重查全部历史。
- [ ] 保存允许修改文件前件、相关原模块/卡/规则/旧raw的哈希，git HEAD加脏工作区指纹；禁止裸宣称保护了896项却无逐文件清单。
- [ ] 写任务合同与候选卡草案；运行manifest须保存规范版本、对象精确版本、展开卡、代码哈希必需键、数据/成员哈希、目标/分组/时间切分协议、attempt history。开发中不覆盖正式协议，先草稿，正式运行前排他冻结版本。
- [ ] 建三份预先固定的合成演示协议：①多产品数值与排名研究，②双均线/宽度状态研究，③策略三层归因入口。每份合成输入/期望单独写明，不能使用被测结果生成期望。

## Task 1 — 通用计算与元数据适配

Files：contracts.py、adapters.py及对应2份单测。

- [ ] 先测未知对象/错版本/用途不符/输入列缺失/单位错/重复键拒绝；再测合法3产品、5产品输入都能出完整行键、相同接口与元数据。
- [ ] 薄封装definitions.quote_features及breadth，检查精确参数绑定，不复制公式；双均线只读调用实际函数，候选身份单列。
- [ ] 测动量首个合法位置253、252/21端点；SMA含当日、严格大于/等于边界；RV ddof=1、年化；宽度共同分母、成员生效变化、空集合与覆盖门槛。
- [ ] 价格缩放不改变无量纲值。若测试包含分红，价格与每份现金分红必须同步缩放；拆分比例不缩放。只调用已有行动适配，禁止把账户events当公司actions。
- [ ] 追加未来输入不改变已有合法日期计算；更正历史源文件是输入新版本，不伪装成单纯追加。未知available_at不回填。

示例验收代码合同：

```python
batch = calculate_batch("trend.distance50@1.0.0", inputs, protocol=protocol)
assert batch.metadata["reference"] == "trend.distance50@1.0.0"
assert batch.metadata["synthetic"] is True
assert not batch.values.duplicated(["observation_date", "entity_id"]).any()
```

## Task 2 — 可复用预测/状态检验

Files：diagnostics.py、test_factor_lab_diagnostics.py。

- [ ] 将通用 value/target 成对数据薄映射到已有 rank_diagnostic数学核；每观察日横向比较产品，ties=average，少于3对/常数返回缺失及原因，禁止把选股按代码打破并列的名次用于IC。
- [ ] 独立例：分数[1,2,3]，目标[3,2,1] => IC=-1；同序=>1；常数=>null；NaN剔除后n不足=>null；空日期仍保留n=0。每期输出n、剔除原因、窗口与日期，不只给均值。
- [ ] 未来目标第一版复用固定t后第1交易日到其后21交易日（t+22）经济价格变化，缺端点不顺延；协议明确它是测量目标，不是可成交开盘或完整账户收益。不扫多期限。
- [ ] 输入label_start/label_end/label_available_at；目标没成熟或截至评价时不可知，不能进入统计；特征必须早于其决策截止可得。同日时间需时区。只解释同期收益时才能使用同期收益序列，不混入预测输入。
- [ ] 连续共同状态（宽度）走每个明确目标实体的跨日期诊断；不把同日复制到所有产品后算横向IC，若误请求则返回not_applicable。时间上的相关系数不当独立样本的显著性证据。
- [ ] 二元双均线状态走“状态真/假时后续结果”的样本数、均值、中位数与差额；缺失/未就绪单列。不强制所有二元状态有排名IC，不把同一连续状态期间的每日观测当独立成功次数。
- [ ] 可选固定分组仅支持显式q=2、并列不拆散；有效不同分数不足返回不足，组规模/边界/目标覆盖均输出，不为分满组按产品代码拆分。均值等权只是诊断，不称可投资因子收益。

统计不确定性第一版输出每期/各固定时期分布、计数、依赖风险；未实现相关性稳健置信区间则明确not_implemented。不得伪造通用p值、IC及格线或“高IC就有效”。

## Task 3 — 过拟合风险与试验史检查

Files：validation.py、test_factor_lab_validation.py。

要建设的是“识别证据薄弱、偷看未来和反复挑优的风险”，不是一个可证明不存在过拟合的开关。

- [ ] 协议先固定按时间顺序的开发段/验证段/保留段，保存各段起止和已看过标记；本轮无训练器、不拟合模型，只生成合法配对和分段诊断。
- [ ] 根据实际标签[start,end]剔除开发样本跨入验证/保留期的情况（边界接触也视为重叠）；按label_available_at在切分截止前是否已知检查。不能只按观察日期切，也不能随机打散日期。
- [ ] 前处理第一版明确none，不做全历史标准化/填补/截尾。保留段若已用于选因子或参数，标已使用，不能靠重命名或换AI恢复为未知。
- [ ] trials记录每次对象/参数/池/目标/切分/输入/运行版本、成功/失败/放弃、选择依据；未知尝试史返回unknown，不当1次。保存所有版本，不只存赢家。
- [ ] 检查标签重叠、共享状态/重复产品、各段有效n、方向变化和对少数时期的依赖；输出逐项证据及“风险尚未排除”，无自动not_overfit=true。
- [ ] 测试：按观察日不重叠但标签越界、端点接触、仅追加未来、重复尝试、已看过保留段、未知历史、非法乱序切分、合法无重叠正向。切分函数测试不替代真实研究效果证据。

输出函数 `audit_validation` 必须包含 `split_findings, overlap_findings, trial_history_status, sample_counts, limitations`，没有材料的字段为unknown/未检验，不给默认绿色。

## Task 4 — 策略三层归因入口

Files：attribution.py、test_factor_lab_attribution.py。

- [ ] 第一层资金贡献：复用capital_contributions/reconcile，输入账户equity/trades/events和公司actions；events必须来自该账户运行的实际现金/应收账，actions来自独立公司行动资料，通过event_id映射产品。未知ID/一对多冲突/账户字段混入actions拒绝，不用同名字段猜。
- [ ] 独立合成期末核算：初始100，买入1份花50、手续费1，剩余现金49，期间已付分红2、期末价格55 =>期末总资产106、净损益6、产品净贡献6；缺最后持仓或手续费会破坏核对。再测应收未付、无交易全现金、映射冲突。这里生成输入表不是跑新账户引擎。
- [ ] 第二层决策增量：只消费两份已存在的完整账户结果及受控协议，核对初始资金、外部入金、池/时段/费用/基准/冻结规则，只允许声明的一个动作变化；不满足时只报“不可归给该动作”。复用compare_accounts，不把年化差、回撤差相加成资金贡献。
- [ ] 第三层风险/因子解释：本轮实现模型卡与输入资格检查，不强行回归。模型卡必须区分因变量、factor_return的ID/版本、币种频率/对齐、窗口、rf、估计方法和不确定性；宽度水平/双均线布尔不能无说明当收益因子。缺适配收益序列或模型未实现返回not_run及原因，不给alpha数字。
- [ ] model_card=None 是合法“本轮未做风险模型”；不能阻断第一二层。明确剩余收益不自动叫独特alpha或运气。零现金利息不等于无风险序列为0。

合成三层示例必须真实调用前两层，第三层展示明确拒绝或not_run，不用一份全空JSON假称完成归因能力。禁止对真实旧账户重新运行或直接借旧收益宣称本轮策略改善。

## Task 5 — 三类离线端到端示例与统一报告

Files：runner.py、CLI、integration测试、raw合成输入与输出。

- [ ] 统一入口 `python scripts/run_factor_lab.py --protocol <不可变协议文件> --out <新目录>`；协议包含实际实现代码必需键和hash，删键不能免核，current指针拒绝、输出已有拒绝。
- [ ] 三类示例：①3/5实体通用数值接口+手算IC+时间切分；②双均线候选/共同分母宽度+状态诊断，常数宽度的横向IC明确不适用；③资金6元对账+受控差额比较+风险模型未运行说明。
- [ ] 各例产物：manifest、values（如适用）、targets（仅合成）、diagnostics、validation、attribution（如适用）、quality、完整原始日志和中文summary。所有标题常驻“合成算法验证，非真实收益/有效性证据”。
- [ ] 测试直接从正式CLI调用真实函数；不得mock资格判断硬放行。禁止外部socket、加载真实API服务预热或读私人交易数据库。
- [ ] 如进行唯一一批真实资料只读检查：仅输入字段/身份/资格，不调用calculate/evaluate；输出不能含新真实IC或收益。该分支缺资料不影响三类合成示例继续交付。

## Task 6 — 回归、用户手册和交接

- [ ] 新6文件单测/集成均运行，ruff仅新文件；完整相关回归最多2次，由已有研究定义/动量/归因/资格相关测试组成，运行前记录实际文件名单，不凑数量。不得改旧测试期望来消绿。
- [ ] 主控复核需要的独立期望表与失败日志入raw。退出码和日志不丢失；正式示例失败算次数，超出重试上限暂停该例而继续其余交付。
- [ ] `factor-lab-usage.md` 给一次注册/引用定义→提供合法输入→选择研究问题→执行→读证据与限制的例子；已有卡/候选卡、支持/未支持分列。后续新因子的准入：假设、定义、适用实体、合法时点、简单对手、冻结尝试、失败证据、采用边界，不自动注册/挖掘。
- [ ] 明确未实现：正式双均线对象登记与真实有效性研究、稳健统计推断/多重试验调整、适配风险模型回归、外部库安装、前端研究台、生产接入。这些不伪称通过，也不阻止本轮确定交付。
- [ ] 执行报告落 `docs/experiments/factor-research-workbench-v1-2026-09-14.md`，category“方法论与验证”、verdict mixed；registry/INDEX本条、路线图当前入口更新。保留决策卡、保护清单对比、失败史、实际模型、命令/版本、六类状态、下一步。
- [ ] 给主控逐里程碑证据建议，执行者不写OKR；主控收到回调后独立检查，再更新进展/待验收，绝不由执行者自行标完成。

## 7. 完成条件与停止条件

完成以可调用功能为准：同一API适配不同合成实体集合；已有数值/双均线状态/宽度三类完整输出；IC及状态检验方法分流；尝试史/时间切分/重叠风险可见；资金与受控决策归因可核；不适配风险模型诚实不运行。资料不足的分支不能靠空壳冒称已实现，逐项说明。

停止受影响分支：政策/时点歧义、需要新资料/依赖/生产修改、原保护文件意外变化、已消耗预算、新增实际因子定义需要判断。其余可完成项继续。主控最多3轮（初交+2次限范围返修），达到后不无限循环修复。

本任务不执行 `2026-09-14-etf-research-data-admissibility.md` 的40请求/20材料计划；该计划已经后置，旧授权提案不继承。本轮没有官方补证额度。
