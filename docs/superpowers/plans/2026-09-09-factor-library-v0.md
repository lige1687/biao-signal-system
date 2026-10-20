# 小型研究因子库 v0 建设与验收计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans 按任务执行；用户允许并行且确有独立任务时可使用 superpowers:subagent-driven-development。Steps use checkbox (`- [ ]`) syntax for tracking。此文件是待执行任务书，不是已执行报告。不要重新询问是否需要写计划；用户将本计划交给执行 agent 后，按此范围交付，再交回原主控独立验收。

**Goal:** 在现有定义登记之上，建成一个能被真实研究调用的小型计算与证据库，用混合池的一次受控实验验证“定义 → 合法输入 → 计算 → 完整账户 → 解释与取舍”的流程。

**Architecture:** 复用 `definitions.py`、唯一JSON登记表和冻结混合池账户函数；新增研究专用的批量计算、只读旧账户适配、结果解释模块与单一运行入口。定义、输入、输出及研究结论分别版本化，不改旧消费者，不另建大平台。

**Tech Stack:** 当前项目已有 Python、pandas、NumPy、pytest、ruff；JSON/CSV/Parquet/Markdown；本地资料；不新增服务、数据库、付费依赖或前端。

## Global Constraints

- 用户当前原话：“这一块你可以给我一个建设计划，我让执行 agent 去做，做完你收。”当前主控只交计划；执行者获得此任务书后开展首期 v0，完成后提交原主控验收，不能自称最终验收通过。
- 用户已认可原方向；本次1.0.1仅补正式运行前的policy/快照、4只以上实际等权成交测试、事件来源映射和含分红价格缩放测试，不增加新因子、新数据或账户路径，不重新规划。
- 沿用 `docs/research/experiment-backtest-principles.md` v1.0、`docs/research/definition-standard.md` v1.0.0，以及根 AGENTS；不建立平行总纲。
- 目标不是寻找新因子、提高历史年化。定义正确不等于有效；用于归因不等于允许参与交易；测试通过不等于获得生产授权。
- 不得改变生产规则、正在运行的冻结实验、旧封存结果、正式交易权限或 OKR 完成度。不得顺手调参数、扩 ETF 池、接大量新数据、重建整个回测框架。
- 只使用本仓库与被其冻结清单明确引用的本地资料；不下载学术因子、不找新论文、不补全全市场历史成员。资料缺失只阻断受影响项。
- 每个新输出目录必须不存在；禁止 `--overwrite`、禁止运行旧文件的 `main()`、禁止向旧raw目录写入。保存本轮所有失败尝试，不用最终成功覆盖中间失败。
- 现有工作区有大量未提交修改。先保存 `git status --short`；只处理本任务文件。提交版本控制时仅显式列本任务文件，不能 `git add .`，不能覆盖或撤销其他工作。
- 本计划是组合配置与研究可信度层的建设，不是新增 A/B/C/D 交易触发。策略规格、规则账本、MACD及基本面叙事边界保持。

## 0. 大白话目标与建设路线

这一期不是“再登记更多名字”，而是让执行程序真的用同一套动量、波动与趋势定义算数，再问：
**波动过滤有没有让选强方案更值得用？它少买了什么、少亏或少赚了什么、付出了什么代价？**

路线选择：

| 路线 | 取舍 | 本次决定 |
|---|---|---|
| 只继续补登记卡 | 工作量小，但不能证明真正进入研究调用 | 不作为本期终点 |
| 小型计算库＋一次真实研究＋独立核账 | 直接检验复用价值，可控制范围 | 本期执行 |
| 全市场因子平台＋自动搜索＋回归模型 | 需要更多合格数据和方法选择，容易扩大到“找漂亮结果” | 不在本期 |

本期完成后，后续路线依次是：有需要的消费者逐条接入 → 针对具体问题补合格的基础收益参照 → 独立冻结适配的收益解释模型 → 另行讨论交易采用。
后续阶段只是路线说明，不自动授权执行。尤其不要求 v0 必须产出一个“已发现的有效因子”。

## 1. 已有事实：不能重复建设的起点

先读以下文件，依次核对实际存在的版本，不凭聊天摘要猜代码：

1. `AGENTS.md`、`docs/trading-spec-v1.md`、`configs/rules.v1.yaml`、`.claude/skills/macd-reading/SKILL.md`、`docs/plan-sector-trend-page.md`。
2. 上述两份研究规范、`docs/research/experiment-report-template.md`。
3. `docs/experiments/definition-normalization-ARCHIVE-2026-09-09.md`。
4. `docs/research/definition-evidence-mixed-2026-09-09.md`、`definition-evidence-breadth-2026-09-09.md`、`definition-review-2026-09-09.md`。
5. `src/lei_signal/research/definitions.py`、`tests/unit/test_research_definitions.py`、`scripts/verify_research_definitions.py`。
6. `docs/experiments/raw/research-mixed-defense-2026-09-09/protocol.json`、`execution/run.py`及其结果清单。

截至本计划：76个登记对象，28项定义测试和4项报告库测试通过；两条小例完成，旧消费者仍未迁移。
`calculate()` 只绑定少数计算，不能把其他纯函数的存在说成所有对象已接入。登记表目前 `models=[]`。
本期开始先实际跑回归，不能把这些历史通过数当成本轮测试结果。

特别保留五个事实：

- 混合池经济指数和宽度ETF连续价格连接公式不同，不能合并成一个价格适配器。
- 本期混合池动量为 `I[t-21]/I[t-252]-1`；273条及当前报价是月选资格，不是每个公式共同预热条件。
- 波动是20个简单收益的样本标准差年化；分位756/最少252、包含当前、并列平均；恰好0.8剔除，旧NaN放行。
- 完整账户输出中的单产品归因表可能未包含期末应收；独立核账必须补上应收，不能为对齐而漏记，也不能暗改旧引擎。
- 历史数据到达时间未知是资料资格限制。可以重建历史数值，不能因此声称历史时点合法性全部通过。

## 2. 首期范围与冻结实验

### 2.1 计算库仅接入已有对象

精确引用以下 `@1.0.0` 对象，不新增窗口或阈值：

- `mixed.price.economic`、`mixed.asset.total_return`、`cash.zero`。
- `mixed.momentum.raw`、`mixed.rv20`、`mixed.rv_percentile`、`mixed.volatility_allowed`。
- `mixed.eligible`、`mixed.momentum.rank`、`mixed.top3`、`mixed.target.equal`。
- `trend.sma200`、`trend.distance200`、`trend.above200`：用于描述持仓，不参与本次新买卖。
- `risk.product_account_weight`、`risk.direction_account_weight`、`risk.product_invested_weight`、`risk.profit_direction_share`。
- `breadth.csi300.b50.common`、`breadth.csi300.b200.common`：仅保留跨研究线接口回归，不启动新宽度账户。

基础资产收益先保留每只ETF自己的序列与公司行动口径，不把其中一只当作能解释整个混合池的“市场因子”。
有效报价间的收益须同时保存区间起止；隔了多日的收益不能伪装成统一日频收益来回归。模拟现金零息不是无风险利率。

### 2.2 四个实验版本，主问题只检验波动过滤

固定原 full14 名单、`2020-12-01—2026-06-30`、原预热输入、100万元初始资金、无外部入金、现金零息、100份单位、原成交限制。
费用固定为每边0.001与0.002。所有版本均不使用SMA退出、不使用快速回补；每月调仓，月间不自动再平衡。

| 实验标识 | 选择强者 | 波动过滤 | 当月如何分配 |
|---|---|---|---|
| E00 | 不按涨幅选前三 | 不过滤 | 所有动态合格产品平均分配 |
| E01 | 不按涨幅选前三 | 剔除分位≥0.8 | 过滤后所有合格产品平均分配 |
| E10 | 涨幅排名取前三 | 不过滤 | 前三平均；不足三只全选 |
| E11 | 涨幅排名取前三 | 剔除分位≥0.8 | 过滤后取前三并平均，等同原满额选强无退出 |

共同资格：当日真实有效报价、累计≥273、动量可算；原 full14 正常输入下应与旧eligible集合一致；若发现不一致，先报告，不额外缩池。
负动量允许；并列按代码升序；NaN波动分位按旧协议放行但输出计数；无候选全现金；不去除同经济方向产品。

主要比较：**E11−E10，回答在现有选强政策中增加波动过滤改变了什么。**
辅助比较：E01−E00；以及二者差额描述过滤与选强是否互相影响。
E10−E00同时改变选强和集中持有，必须称“选强政策差异”，不能声称纯动量因子溢价。
本期不把上述四格强行分解成互不重叠的市场β、动量α或运气金额。

最多 **8条正式账户路径**（4版本×2费用），另外最多2条原E11旧函数对照重放，仅用于兼容性校验，不算新独立证据。
分期固定沿旧 `2020-12-01—2024-12-31` 与 `2025-01-01—2026-06-30`；只切同一完整路径统计，不在分期起点重新入金或重置持仓。
不得扩为排名窗口、过滤分位或持有数量搜索。历史区间已被研究过，不改称从未见过的数据验证。

### 2.3 评价与停止条件

建设验收看可复现和可解释，不看新收益高低。研究结论使用规则：

- 若E11在两费用下净损益均不高于E10，且最大跌幅、恢复等待也无改善，记“该固定比较未见过滤价值”。
- 若增收但更难承受下跌，或少跌但少赚，量化交换，不由执行者替用户确定可接受代价。
- 两费用或两个固定时期方向不一致，记“依赖条件”；资料/核账不合格则“证据不足”。
- 即使方向一致，也最多“值得继续验证”，不能宣称普遍有效或获准采用。
- 过滤结论仅适用于本轮固定full14池、无SMA退出/无快速回补、月度政策、区间和双费用；不得自动改动快速回补候选、其过滤条件或生产规则，也不能据本轮负结果淘汰其他政策中的过滤。
- 来源指纹漂移、运行前policy/快照未锁定、E11兼容不一致、4只以上实际等权执行不通过、账户对账超容差：立即暂停受影响路径及收益解释，交差异文件；仍完成不受影响的纯函数和接口测试。

## 3. 文件职责与接口合同

新增文件（若执行时已存在同职责模块，合并到它，不另造同名体系；在交接中解释路径差异）：

| 文件 | 单一职责 |
|---|---|
| `src/lei_signal/research/factor_runtime.py` | 按精确定义批量计算、输入身份检查、构造四种实验名单；不运行账户 |
| `src/lei_signal/research/factor_account_adapter.py` | 只读导入冻结函数，明确传入指数/决策，运行隔离账户，不复制生产引擎 |
| `src/lei_signal/research/factor_diagnostics.py` | 从日账、交易、行动重建贡献、实际权重和固定比较；不拟合模型 |
| `scripts/run_factor_library_v0.py` | 单一命令编排和新输出目录管理；准备与运行分两种模式 |
| `tests/unit/test_factor_runtime.py` | 定义绑定、批量计算、缺失/时点/单位/版本边界 |
| `tests/unit/test_factor_account_adapter.py` | 四格名单、旧函数隔离、接口与成交兼容 |
| `tests/unit/test_factor_diagnostics.py` | 手算资金贡献、应收、现金、权重、路径比较 |
| `tests/integration/test_factor_library_v0.py` | 新命令在合成小输入上可执行，目录防覆盖，输出身份完整 |

允许小改 `definitions.py` 的登记加载/manifest兼容能力及唯一登记表，必须保留旧行为和旧卡快照；无必要不改。
本期不能把该文件变成包揽所有研究的巨型引擎。

公共接口固定如下；可以增加私有函数，不得让下游猜字段：

```python
# factor_runtime.py
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class FactorBatch:
    values: pd.DataFrame       # date, symbol, economic_index, momentum, rv20, rv_rank,
                              # valid_count, sma200, distance200, above200
    missing: pd.DataFrame      # date, symbol, field, reason（仅异常行）
    metadata: dict             # refs, input identity, calculation binding, units, quality

def build_mixed_batch(prices: pd.DataFrame, actions: list[dict], *,
                      registry: dict, input_identity: dict) -> FactorBatch: ...

def monthly_decisions(batch: FactorBatch, *, variant: str,
                      completed_months: list[str], symbols: list[str]) -> pd.DataFrame: ...
# output: decision_date, selected, ranked, scores, weights, exclusion_reasons

# factor_account_adapter.py
def replay_account(*, registry: dict, batch: FactorBatch, decisions: pd.DataFrame,
                   prices: pd.DataFrame, actions: list[dict], fee: float,
                   variant: str) -> dict: ...
# output: summary, equity, trades, orders, signals, events, annual,
# per_symbol_legacy, reentry_events, periods, reentry_diagnostics
# tables全部DataFrame；summary为dict；旧归因表只用于对照。
# events来自旧simulate返回值中的events，旧导出曾命名actions.csv；
# 本接口统一命名events，绝不与输入actions（原始公司行动列表）混用。

# factor_diagnostics.py
def capital_contributions(*, equity: pd.DataFrame, trades: pd.DataFrame,
                          events: pd.DataFrame, actions: list[dict],
                          prices: pd.DataFrame, initial: float) -> pd.DataFrame: ...
# output: symbol, net_sales, gross_purchases, cash_dividends,
# ending_receivable, ending_market_value, net_contribution

def compare_accounts(accounts: dict[str, dict]) -> pd.DataFrame: ...
# key为E00/E01/E10/E11各自费用唯一标识；输出每路径与固定差额，不筛赢家。
```

此处签名是接口合同，不是让执行者提交 `...` 空实现。下列任务给出必须实现的行为及判定例。

## 4. 按顺序执行的任务

### Task 1：锁住资料、版本和本轮协议

**Files:** 新输出根 `docs/experiments/raw/research-factor-library-v0-2026-09-09/`；其下每次独立 `prepare-01/`、`run-01/`，已存在就使用下一个编号，不覆盖。

**Consumes:** 唯一登记表的来源指纹、现有冻结协议与原账户结果。**Produces:** `protocol.json`、`source-inventory.json`、`frozen-definitions.v1.0.0.json`、`run-registry.snapshot.json`、`resolved-policy-cards.json`、`baseline-tests.txt`、`workspace-status.txt`。

- [ ] 记录工作区状态、Git HEAD和实际代码文件哈希；实际跑现有32项回归并保存stdout/stderr/退出码。
- [ ] `load_registry()` + `verify_sources()`；哈希不符时定位哪个对象受影响，不能自动把新哈希当老证据。
- [ ] 从登记表读取 `mixed_prices/mixed_actions/mixed_pool/defense_code/defense_protocol`，不要重新猜绝对路径。原账户对照读 `docs/experiments/raw/research-mixed-defense-2026-09-09/execution/` 的 `equity.csv/trades.csv/accounts.csv`。
- [ ] 将当前原始登记表逐字节保存为生成快照并核同哈希；它是历史证据，不是第二份手写权威。冻结本计划§2的四格、资金、日期、双费用、来源、预热、评价、停止条件。
- [ ] **在任何正式历史账户运行（含E11兼容重放）之前确定policy卡，不得等Task 5或看完收益再补。** E00=`policy.factor_v0.e00@1.0.0`、E01=`policy.factor_v0.e01@1.0.0`、E10=`policy.factor_v0.e10@1.0.0`；E11=`mixed.no_exit_100@1.0.0`，另记本期执行绑定。前三张只描述本计划已有三种组合，不是新增因子/路径。完整填写选择、1/N权重、现金、费用、月末和成交时点、无退出/无快速回补、资格、依赖及限制；未运行状态保持proposal，不能预填有效性通过。
- [ ] 将前三张卡追加进唯一登记表，容器版本升1.1.0；旧76卡展开语义、共用profile和原sources不变。E00/E01不得引用含“取前三”的对象冒充自己的选择或分母；各卡只依赖实际使用的对象。冲突ID或不同语义已占用时拒绝本轮准备，不能悄悄覆盖或自动选最新。
- [ ] 在`prepare`成功前，将包含四个精确policy引用的完整登记表逐字节保存为`run-registry.snapshot.json`，展开四卡及依赖为`resolved-policy-cards.json`；`protocol.json`锁定这两个文件的SHA-256及E00—E11绑定。旧1.0.0快照用于兼容，运行快照用于本批计算，两者不能混用。卡片与运行快照冻结之后，本次结果和验收状态另写证据，不修改已锁卡。
- [ ] 用输入日期并集及完整月份声明构造可用月末：从2020-11开始到2026-06；最后月不能只凭“文件最大日期”自动认为完整。完整月份声明来自冻结协议的截至时间；对历史真实交易日历资格的限制单列。
- [ ] 记录资料分层：数值可复算、历史到达时间未证实、实际成交容量未验收。禁止把到达时间补成收盘时刻；本次运行时刻只能表示本次历史重建。

准备模式不得运行收益账户：

```sh
python3 scripts/run_factor_library_v0.py prepare --output docs/experiments/raw/research-factor-library-v0-2026-09-09/prepare-01
```

应输出 `preparation_complete` 或具名 `blocked_items`，不能提前宣称收益结果。若开发时还没准备好卡片或计算绑定，只保存明确标记的准备草稿，不输出可用于正式运行的成功协议。Task 1的资料合格分支继续，无需为纯准备反复请求用户批准。
Task 2/3可先开发和运行合成单元测试；正式历史账户开始前，必须完成上述卡片/运行快照与执行代码绑定检查，不得以任务排序为由延后。

### Task 2：把已有定义变成身份绑定的批量计算

**Files:** `factor_runtime.py`、`test_factor_runtime.py`；必要的登记绑定最小增补。

**Consumes:** Task 1合法名义价格、行动与身份快照。**Produces:** `FactorBatch`及实际可用对象/未实现对象清单。

- [ ] 先写以下手算测试，运行至预期失败，再实现：

```python
def test_reference_momentum_is_252_to_21():
    import numpy as np
    import pandas as pd
    from lei_signal.research.definitions import quote_features
    q = pd.Series(np.arange(1., 281.))
    out = quote_features(q)
    assert out.momentum.iloc[252] == 231.0
    assert out.valid_count.iloc[272] == 273

def test_mixed_price_chain_oracle():
    # 成交间隔内先分红1再一拆二；原价100，后价49.5，经济指数应不变。
    import pandas as pd
    from lei_signal.research.definitions import economic_index
    q = pd.Series([100., 49.5], index=pd.to_datetime(['2020-01-01', '2020-01-04']))
    events = [
        dict(event_id='d', type='cash_dividend', cash=1., effective_date='2020-01-02',
             available_at='2020-01-01T12:00:00+08:00'),
        dict(event_id='s', type='split', ratio=2., effective_date='2020-01-03',
             available_at='2020-01-02T12:00:00+08:00'),
    ]
    assert economic_index(q, events).iloc[-1] == 1.
```

  以上是必须保留的旧公式判定值；另写直接调用 `build_mixed_batch` 的新接口测试，缺新函数时必须失败。
- [ ] 按每产品有效报价计算，复用 `quote_features/realized_volatility/historical_percentile`，不要另一份硬编码指标公式。输出每产品单期收益时标明前后观察日期。
- [ ] 经济指数数值独立按登记公式重建，并逐值对冻结 `economic_indices`；不是用旧输出抄回去。事件先按生效日/event_id排序，在相邻合法报价区间逆序合并拆分与现金。
- [ ] 旧事件没有真实available_at时，不能伪造后喂给严格 `economic_index`。历史重建分支必须显式标 `historical_reconstruction_only`，记录未知项；与严格时点接口分开，不削弱严格接口检查。该分支只能用于本轮历史数值复算。
- [ ] 为每个已绑定 `id@version` 固定可执行契约摘要：公式/参数/端点/单位/价格输入/日历/资格/时间/依赖均进入摘要。相同参数但修改公式、价格口径或版本时也须拒绝；不能只匹配ID前缀和窗口。
- [ ] 旧版与新实现逐值比较普通日、分红/拆分日、第一条可算动量、273资格边界；同时验未来追加不变、历史修订会改变且指纹改变。
- [ ] **价格单位缩放必须同步缩放每份现金分红。** 原始名义OHLC均乘10，所有对应`cash_dividend`的每份现金字段（归一后`cash`，原始别名也须一致）乘10；拆分比例、份额数量、日期、event_id不变，`entitlement`份额不能乘10。联合输入再重建首值为1的经济指数，其指数及衍生无量纲信号应不变。若只对现成P_signal乘10，则SMA绝对值也应乘10，距离/状态/动量等不变。这是信号单位测试，不要求固定100万元、100份整手的账户资金路径缩放后不变。

```python
def test_price_and_dividend_scale_together():
    from copy import deepcopy
    import pandas as pd
    from lei_signal.research.definitions import economic_index
    q = pd.Series([100., 99.], index=pd.to_datetime(['2020-01-01', '2020-01-02']))
    actions = [dict(event_id='d', type='cash_dividend', cash=1.,
                    effective_date='2020-01-02', available_at='2020-01-01T12:00:00+08:00')]
    scaled = deepcopy(actions)
    scaled[0]['cash'] *= 10
    expected = economic_index(q, actions)
    pd.testing.assert_series_equal(economic_index(q * 10, scaled), expected)
    # 反例：只缩价格不缩每份分红，经济含义已变，不能拿它要求缩放不变。
    assert economic_index(q * 10, actions).iloc[-1] != expected.iloc[-1]
```

  批量接口也须覆盖同一联合缩放，并保留分红与拆分共存例；不得只测无分红样本。
- [ ] 缺报价、缺名单、预热不足、非正价、无穷值、单位错误分别返回原因或拒绝。ETF连续价对象禁止传给混合池绑定；B200水平禁止当收益序列。

数值标准：`atol=1e-10, rtol=1e-10`；计数、名单、布尔状态精确一致。输入全缺失不得输出零收益或零宽度。

### Task 3：统一定义进入真实账户，而不迁移旧实验

**Files:** `factor_account_adapter.py`、`test_factor_account_adapter.py`；Task 2中的 `monthly_decisions`。

**Consumes:** FactorBatch、冻结月份、四格配置、原名义价/行动。**Produces:** 8条新路径及最多2条原函数兼容重放。

- [ ] 名单逻辑按§2.2实现。排名只在有当前报价且满足资格的集合内；筛掉高波动后不足3只不补入被筛者；无候选返回空名单和全零权重。
- [ ] 用手工4产品例覆盖四格（下面分位0.8必须剔除；同涨幅按代码）：

```python
# 合格且当日报价的产品：
momentum = {'000001': .4, '000002': .3, '000003': .2, '000004': .1}
rv_rank = {'000001': .8, '000002': .2, '000003': .3, '000004': .4}
expected = {
    'E00': ['000001', '000002', '000003', '000004'],
    'E01': ['000002', '000003', '000004'],
    'E10': ['000001', '000002', '000003'],
    'E11': ['000002', '000003', '000004'],
}
# 测试须把以上数据构造为FactorBatch，通过monthly_decisions断言名单和1/N权重。
```

- [ ] 只读导入登记 `defense_code` 对应模块，哈希先核；`simulate(method,fee,p,acts,idx,decs)`是本期复用边界，不调用`main()`，不修改其SYMS/START/END/INITIAL等全局值。
- [ ] 原函数的 `idx` 由新FactorBatch提供；`decs`由新月选产生并转换为冻结函数所需字段。账户调用method固定 `no_exit_100`，不同实验通过传入名单/权重表达。外部产物必须另有E00—E11身份，不沿用旧账户名假称四者都是原策略。
- [ ] 不向旧引擎注入新过滤、止损、回补或现金规则；仅在当前研究路径使用新计算输入。检查导入前后和运行前后所有旧来源文件哈希一致。
- [ ] **增加4只和5只实际等权成交的合成接口测试，不能以E11最多3只的兼容证明代替。** 从原FULL14取前4/5只，其他产品权重0；不扩真实池、不改旧全局值。合成首个执行日为2020-12-01，前一月末2020-11-30发目标，所有产品开收盘10、high=11、low=9、volume>0、无公司行动；100万元、费用0.001、100份整手。通过`monthly_decisions → replay_account → 旧simulate`实际调用，而不是只测权重字典；E00和过滤后仍留4只以上的E01都要覆盖。

  合成测试以手算断言：4只每只目标250000、成交24900份、各手续费249，总持仓996000、现金3004、权益999004；5只每只目标200000、成交19900份、各手续费199，总持仓995000、现金4005、权益999005。检查所有入选产品均实际成交，未偷偷截成前三；总费用、现金、份额与权益同时核对。实际权重因费用和整手偏离名义目标是正常残差，不能强行每日恢复目标。
  下一同月报价日只让第一只价格变化且无新目标，必须无新增成交、份额不变、实际权重自然漂移。缺价和资金限制另按原边界测试；合成样例仅作接口验收，不增加正式历史路径或新市场证据。
- [ ] 先做E11两费用兼容比较：新指标/名单与原函数指标/名单逐值一致，权益/成交/未成交及信号时点逐行一致；原冻结结果也比对。兼容未闭合前不解释E00/E01/E10收益。
- [ ] E11兼容与4/5只实际等权执行测试均通过后完成固定8路径；名单变化要在signals.csv中可追到具体原始值、排除原因和对应定义，不只贴manifest标签。E00/E01实际大于3只的月份还须从本批已有路径抽查目标、每只成交和期末份额，不另跑新账户。
- [ ] 加交易边界测试：无候选现金保留、少于一手不买、同日先卖后买、缺开盘不成交、现金不足不超用、行动日份额/应收与月底目标冲突。测试可以调用旧simulate的合成输入，但不得改旧全局值来制造另一套规则。

独立重建动作的期望结果应来自合成输入的手算，不直接复制被测返回作为expected。失败保存最早不同的日期、字段、原值、新值及归属版本。

### Task 4：把资金贡献与风险解释接起来

**Files:** `factor_diagnostics.py`、`test_factor_diagnostics.py`。

**Consumes:** Task 3完整日账、交易、行动、名义价及冻结的经济方向映射。**Produces:** `capital-contributions.csv`、`risk-exposures.csv`、`decision-comparisons.csv`、`quality-report.json`。

- [ ] 先从手算账户写测试：初始100，含费买入60，净卖出20，现金分红2，期末应收3，期末持仓50；期末权益115，产品贡献应为15，现金期末62但不能再当“额外赚62”。

```python
def test_capital_contribution_oracle():
    net_sales, purchases, paid, receivable, market_value = 20., 60., 2., 3., 50.
    contribution = net_sales - purchases + paid + receivable + market_value
    cash_end = 100. - purchases + net_sales + paid
    assert contribution == 15.
    assert cash_end + receivable + market_value - 100. == contribution
```

  另用同样数字构造DataFrame直接调用 `capital_contributions`，不能只提交这段算术测试。
- [ ] 本期无外部入金且初始空仓，按每产品计算：净卖出−含费买入＋已付分红＋期末应收＋期末市值；合计应等于期末权益−初始现金。现金利息固定0；手续费已含买卖现金流，另显示费用但不重复扣。
- [ ] **明确两种资料的来源，不把同名文件混用：** `actions`参数来自登记来源`mixed_actions`对应`normalized-actions.json`的`events`列表，经冻结`action_fields`口径归一，正是传入本路径旧simulate的同一份公司行动输入。保存原文件指纹及归一输入快照`corporate-actions-input.json`，含event_id、symbol、type、record_date、effective_date、pay_date、每份cash、ratio；不从执行日志倒推这一输入。
- [ ] `events`参数来自**当前这一条账户**旧`simulate`返回的账户事件列表（返回顺序中signals之后、annual之前），含account_id、date、event_id、event、amount。旧`main()`把它导出为`actions.csv`，但那不是原始公司行动；新适配器统一返回`events`并导出`account-events.csv`。若读旧结果的`actions.csv`仅作兼容核对，manifest必须明确其角色为account_events。完整归因显式调用 `capital_contributions(events=account['events'], actions=normalized_actions, ...)`。
- [ ] 按输入中**唯一**`event_id → (symbol,type,关键日期,每份cash/ratio)`映射账户事件；多账户可共享同一个公司行动ID，但账户日志必须先按路径隔离。symbol统一6位字符串，ID保留原文，不按前缀猜。输入ID重复/冲突、账户事件找不到ID、交易产品不在声明池、日志混入别的账户，都阻断对应归因；日志金额不能当每份分红再乘持仓一次。

  账户事件单位逐类核：`entitlement.amount`是锁定的份额数，`receivable.amount`是本账户新增应收人民币金额，`cash_paid.amount`是实际从应收转现金的人民币金额，`split.amount`是拆分比例。只把cash_paid计已付分红；期末应收为已建立应收减实际支付；entitlement本身不记收入，split不记现金收入，receivable和cash_paid不能重复算两份利润。
  用原行动日期与成交后的持仓独立核登记日权益、除息应收、支付日转换、拆分份额；若旧引擎在无登记权益时使用持仓回退，应记录且核金额，不能伪造一条entitlement日志。重复日志键`(account_id,event_id,event,date)`、种类与行动type不符、累计支付超过应收、日期或金额不符均须报错并保留证据；零金额合法但不增加收益。
- [ ] 补直接调用归因函数的反例：event_id不含产品代码仍能正确映射；同ID两账户不同金额分别核对；缺ID、重复ID、账户混入、重复支付必须拒绝；期末未支付应收和零分红均不漏记。输入每份分红只接受冻结合同已声明的cash/cash_per_share/cash_per_unit映射；不把未声明的amount字段自动当每份分红。缺必要字段须阻断并留原因，不能默认零或凭名字猜单位。
- [ ] 分期贡献必须减期初持仓市值与期初应收、加区间现金流；不能把全期公式直接套在中间年份。未恢复下跌标明截至期末仍未恢复。
- [ ] 独立从成交、行动和名义价格重建份额/标价，核实际产品权重。缺价旧标记仅允许估值；不得用它产生新信号。经济方向按冻结 `concentration_code` 里的互斥映射，静态读取或提取字面常量，禁止导入会顶层写文件的脚本。
- [ ] 同时列完整账户分母和在场资产分母，空仓的后者缺失。方向贡献是同一笔资金的另一种归并视角，不再加到产品贡献总和；趋势状态、动量排名作为持仓描述，不当成额外一份收益。
- [ ] `compare_accounts` 固定输出净损益、净收益、年化、最大跌幅、最长恢复等待、平均/最大投入、交易次数、换手（明确分母）、费用、期末现金/应收、两固定时期表现。E11−E10是主比较；全结果输出，不按好坏删版本。
- [ ] 差额仅用完整净损益做金额比较；年化差和最大跌幅差分别列，不能当作可加利润贡献。资金归因余额不写alpha或运气。

资金验收：全路径、分期及期末各项均须解释到人民币0.01元以内；浮点误差必须单列实际最大值，不用相对容差放过大额差错。超限不准出“完整对账通过”。

### Task 5：版本、证据输出与跨线回归

**Files:** `scripts/run_factor_library_v0.py`、`test_factor_library_v0.py`；必要时增补原登记表/模板，新增本期报告。

**Consumes:** Task 1冻结协议、Task 2—4输出。**Produces:** 可复现运行目录及接入说明。

- [ ] 实现 `prepare` 和 `run --protocol <准备目录/protocol.json> --output <全新目录>`；`run`必须重新核源哈希、协议哈希、Task 1运行快照/展开卡哈希、精确policy引用和8路径上限，未知variant/费用拒绝。运行只从该快照解析定义，不从当下权威表重新取最新版；快照缺失、policy未注册或内容漂移一律在首个历史账户调用前失败。
- [ ] 首个历史账户调用前保存`run-lock.json`：本计划1.0.1、protocol哈希、运行registry快照及四卡绑定哈希、输入快照/池、所有实际执行代码及旧引擎哈希、双费用、8条路径清单和锁定时间。运行后逐项复核；运行中任何卡/参数/代码变更都需新尝试目录和新锁，不覆盖原输出。新增测试覆盖“缺卡/错版本/快照改一字节/执行代码漂移”均不触发账户函数，不能等账户跑完才发现。
- [ ] 每个路径写 `equity.csv/trades.csv/orders.csv/signals.csv/account-events.csv`、上述诊断表、`manifest.json`；总目录另存`corporate-actions-input.json`、`summary.json`、`attempts.json`、`artifact-manifest.json`、实际测试日志。manifest分别标识corporate_actions_input和account_events的路径、SHA-256、字段单位及对应账户；不再用一个actions文件兼任输入和结果。
- [ ] manifest记录规范、定义ID/版本及所有依赖、registry原文件哈希、代码哈希、输入/池版本、数据截止、历史可得时间质量、当前重建时间、执行协议、费用、variant、缺失编码与生产未授权。每个文件旁置元数据，行内保留日期/产品/账户身份。
- [ ] 复核Task 1在正式运行前已登记、锁定的四个policy引用及完整运行快照；此时只关联本次执行证据，不补造“事前卡”或修改快照。E11新执行绑定与旧冻结消费者分开；E00/E01/E10精确ID按Task 1，不是E11的别名。
- [ ] 核唯一登记表1.1.0新增卡与旧76卡语义差异；Task 1保存的旧原文快照仍是旧版本可解析来源，旧实验不回填新manifest。以后修改有效性/实现状态也另留版本或外部证据，不改本次run-lock已锁内容；不得并列维护两份等价手写全库。
- [ ] 需要支持从旧快照产生manifest时，对 `make_manifest` 做兼容扩展：可显式传 registry_path，必须核该路径JSON与传入registry一致；原默认路径行为不变。自动选择最新版本、忽略文件哈希均禁止。为默认路径、旧快照、内容不一致写测试。
- [ ] 只把实际调用并核验的消费者列为已接入，旧生产和冻结脚本仍legacy；状态或后续证据变化留版本记录，不能批量把所有对象状态改为通过。
- [ ] 对宽度只重跑现有小型例与前缀/共同分母/单位回归，另开新输出目录。创业板缺口不修；不得启动W0—W3新账户。
- [ ] 在报告模板补“本轮实际使用的对象、计算绑定、运行证据与限制”引用，避免继续只贴登记表名字。正文解释仍用原三层归因，不另做第四套报告流程。

执行命令（输出目录已存在时换新编号，不删旧目录）：

```sh
python3 -m pytest tests/unit/test_research_definitions.py tests/unit/test_factor_runtime.py tests/unit/test_factor_account_adapter.py tests/unit/test_factor_diagnostics.py tests/integration/test_factor_library_v0.py tests/unit/test_experiment_reports.py -q
python3 -m ruff check src/lei_signal/research/factor_runtime.py src/lei_signal/research/factor_account_adapter.py src/lei_signal/research/factor_diagnostics.py scripts/run_factor_library_v0.py tests/unit/test_factor_runtime.py tests/unit/test_factor_account_adapter.py tests/unit/test_factor_diagnostics.py tests/integration/test_factor_library_v0.py
python3 scripts/run_factor_library_v0.py run --protocol docs/experiments/raw/research-factor-library-v0-2026-09-09/prepare-01/protocol.json --output docs/experiments/raw/research-factor-library-v0-2026-09-09/run-01
```

以上是预定命令，不是已经执行或通过的证据。执行者须回传真实命令、stdout/stderr、退出码和版本；修改了其他测试覆盖的文件，还须加跑相应回归。

### Task 6：交回主控，不能自行宣布最终验收

**Files:** `docs/experiments/factor-library-v0-delivery-YYYY-MM-DD.md`（日期取实际交付日）；`docs/experiments/registry.json`、`INDEX.md`。

- [ ] 报告含“## 一句话结论（大白话）”、最小决策卡、规范版本、文件清单、输入/旧结果未变证据、失败史、未接入消费者、阻断项和下一步。
- [ ] 登记报告分类“方法论与验证”。不能仅因测试通过给“策略成立”；研究结论按§2.3证据写，工程交付与策略价值分开。
- [ ] 阅读 `docs/okr/README.md`，只核对同一目标是否已存在并提供对应ID/证据；不得改完成度或把本计划自动当成生产授权。本次若没有明确的台账写入授权，把建议作为交接项，不改种子伪造进展。
- [ ] 回传下面固定清单，随后停止新增实验，等主控验收：

```text
1. 报告路径、主运行目录、协议路径、Git/逐文件版本。
2. 正式运行前的policy ID、运行快照、run-lock及锁定时间；旧版快照和兼容证明。
3. 实际测试命令、通过/失败数量、静态检查和未通过项。
4. E11兼容及4/5只实际等权执行：最早差异或零差异证据；实际运行路径数量。
5. 每账户及分期核账差额；公司行动输入/账户事件来源映射；含分红缩放及成交/资金限制测试。
6. E11−E10主要结果：多赚/少赚、少跌/多跌、费用与操作变化。
7. 未接入消费者、资料质量限制、没有执行的后续阶段。
8. 模型分工与回退记录；生产/冻结实验/OKR是否发生写入（应无）。
```

## 5. 原主控的独立验收方式

主控收到交付后不只读执行者的“通过”，按以下次序收：

1. **范围与身份**：核diff/新文件，核旧源与旧结果未变；确认没有隐藏调参、扩池、新数据或第9条正式路径；检查旧76卡语义是否被profile继承悄悄改变；确认四张policy与运行快照/run-lock均在首个历史账户调用前已锁定。
2. **独立算关键数字**：另算252/21、SMA等号、分位并列及0.8边界；核普通月末与候选不足月的名单；联合缩放价格与每份分红，核公司行动连接和未知到达时刻没有被伪造。
3. **真正接入而非贴标签**：抽查研究入口的实际调用链；故意换错误定义版本/公式/价格身份或破坏快照应在账户运行前拒绝；独立复核旧引擎4/5只实际成交、份额、现金、费用及月间漂移，不能只看E11或权重字典；用合法输入在新目录复算，不读取执行者已算好的答案作为计算输入。
4. **资金独立重建**：抽一组E11/E10主费用完整账，核events来自该路径账户日志、actions来自锁定的公司行动输入及唯一ID映射，独立累加成交、分红、期末应收与持仓；对全部8路径核贡献总和；查期初未投入现金、期末未成交、跨期持仓没有被漏掉。
5. **结论与价值**：确认主对照没换、负结果没删、选强集中度没被说成纯动量因子；资金贡献与风险描述没有重复相加；收益未解释部分没有自动叫α。过滤结论不得超出本轮固定政策，更不得据此自动改快速回补候选或生产规则。
6. **回归与交接**：重跑相关测试、旧版本读取与宽度小例；检查每个交付是否有输入/代码/协议可追溯身份。

验收结论分开给：

- **工程交付可接受**：计算/接入/核账/证据满足要求，策略可能仍无增量。
- **局部交付可接受、受影响项待补证**：明确哪些对象/路径不能用；不因一处历史资料缺口否定已核验纯函数。
- **退回修正**：算法/时间/身份/资金或授权边界错误。指出最小修复范围，不授权扩展试验找回漂亮结果。

这三种结论都不是生产审批。最终资金取舍或扩大建设范围仍由用户决定。

## 6. 资源与工作安排

本期按六个可独立检查的交付块推进，不承诺在未知数据异常下固定几小时完成。
优先Sol执行已定方案；边界清楚的小测试/格式工具可用Spark，工具不提供或额度不足时如实回退。
策略歧义、时点风险和本计划之外的模型选择交回主控，不让执行者自行调规则补洞。
只有Task 2接口固定后，Task 3适配与Task 4合成核账可按独立文件并行；真实结果分析等待账户兼容通过。

暂停条件只暂停对应分支。不能以“必须先把所有历史缺口补完”为由不交计算库，
也不能以“先做工程”为由漏交至少一次真实研究调用及清楚标记的阻断证据。

## 7. 计划自检与状态

- [x] 以现有登记、代码与源协议制定，不重做76卡盘点。
- [x] 写明首期范围、四格、主比较、8路径上限、费用和停止条件。
- [x] 分清统一计算、完整资金对照、风险描述与未授权后续模型。
- [x] 保留旧版本/旧结果，给出精确接口、手算判定值、命令与独立验收清单。
- [x] 1.0.1按用户评审补齐运行前policy/快照、4/5只实际等权执行、events/actions映射、每份分红同步缩放及过滤结论边界；范围与正式路径数不变。
- [ ] 执行者已完成首期交付。
- [ ] 原主控已完成独立验收。

计划版本：1.0.1，2026-09-09。1.0.0为初始计划；1.0.1仅为用户指定的接口和验收补充，不重定实验方案。计划已写不等于实验已跑；没有新收益、生产或OKR完成声明。
