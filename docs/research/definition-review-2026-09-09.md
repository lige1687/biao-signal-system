# 研究定义登记与纯函数独立复核

日期：2026-09-09
规范：`docs/research/experiment-backtest-principles.md` v1.0
范围：只读检查 `docs/research/definitions.v1.json`、`src/lei_signal/research/definitions.py`、`tests/unit/test_research_definitions.py`；不重跑旧收益，不修改实现、登记表、生产或 OKR。

## 一句话结论（大白话）

新登记表已经把混合池最容易混淆的规则写对了，包括 252/21 动量端点、波动最高 20% 的剔除边界、月末不先过 SMA200、退出与快速回补的等号边界、75% 目标和两种集中度。但是当前纯函数还不能作为可靠的独立复算入口：它会在没有“决策日当前报价”的情况下误选产品，带时区的价格日期遇到分红或拆分会直接报错，而且登记表指向的定义标准文件不存在。现有 15 个测试全部通过，但没有覆盖这三处。

## 1. 复核对象与指纹

| 文件 | SHA-256 |
|---|---|
| `docs/research/definitions.v1.json` | `1735bd38737e6823a38e6e5cb9514a3ee404182c9cfe2f6c4c85b0c5232afd98` |
| `src/lei_signal/research/definitions.py` | `208d5584ed973b5ff378f43549db3ab9cbf8a24b317220ec77c9c9adfce5bf76` |
| `tests/unit/test_research_definitions.py` | `641a71ffba0bbe29f1e69be5e80627a2088e861358d39e364bbd8754068cc3f5` |

登记表列出的全部 `sources` 路径均存在，盘点时实际 SHA-256 与登记值一致。唯一失踪的入口是登记表第 4 行声明的 `docs/research/definition-standard.md`。

## 2. 必须修正后才能称“可独立复算”

### P1：混合池选择函数没有执行“决策日当前有报价”

- 证据定义：`definitions.v1.json:413-459` 把资格写成 `current_valid_quote AND count_valid_quotes_through_t>=273`，排名也明确“缺当日报价无资格”。这与冻结旧实现 `full-execution/run.py:63-68` 一致：只有决策日在透视表里存在该产品值，才加入资格名单。
- 实现：`definitions.py:183-187` 的 `select_mixed(momentum, rv_rank, valid_count)` 没有当前报价或资格布尔量，只检查 `valid_count>=273` 和动量有限。
- 独立手算：`select_mixed({'a': 1.0}, {'a': .2}, {'a': 273})` 返回 `['a']`。该接口无法表达“a 在决策日缺报价”，因此调用者把上一有效日的动量和累计数传入时会误选。
- 风险：这会改变候选池、排名、Top 3 和后续资金路径，不是只有显示差异。
- 必要处理：函数必须接收并强制检查显式 `current_valid_quote`／`eligible`；或者删除它“复现冻结月选”的承诺，改为只排序已经由上游严格筛好的集合。测试需构造累计 273 但决策日缺报价的产品。

### P1：显式时区契约与公司行动函数不兼容

- 登记与接口意图：混合池 profile 将时区写为 `Asia/Shanghai`；`economic_index` 注释要求带事件可知时间；`make_manifest` 也拒绝无时区时间。
- 实现：`definitions.py:216` 无条件执行 `pd.Timestamp(day).normalize().tz_localize('Asia/Shanghai')`。当价格序列本身已经是带 `Asia/Shanghai` 时区的 `DatetimeIndex`，只要区间内出现公司行动就报错。
- 独立复现：两条带 `Asia/Shanghai` 日期的价格 `[100,100]`，第二天生效现金分红 1，事件 `available_at` 带 `+08:00`，得到 `TypeError: Cannot localize tz-aware Timestamp`。
- 风险：最守规矩、显式带时区的输入反而不能计算；这会诱导调用者退回无时区日期。
- 必要处理：对无时区观察日期做本地化，对已有时区先转换到 `Asia/Shanghai`；同时测试无时区、上海时区和非上海时区的观察索引，并明确 `effective_date` 是交易日期还是精确时刻。

### P1：登记表声明的权威标准文件不存在

- `definitions.v1.json:4` 声明 `standard = docs/research/definition-standard.md`，实际路径不存在。
- `load_registry()` 只解析 JSON；`validate_registry()` 不检查 `standard` 路径或标准版本。
- 风险：无法从登记表追溯“为什么必须有这些字段、允许哪些类型和用途”。代码中的 6 个类型和 6 个用途变成实现者自行写死的集合，无法证明覆盖用户确认的分类。
- 必要处理：补齐并冻结标准文件，或把登记表改指向实际存在的权威文件；验证器至少检查标准版本/路径，交付清单应核文件指纹。

## 3. 登记内容与混合池证据的一致性

| 检查项 | 结论 | 说明 |
|---|---|---|
| 经济指数 | 一致，但新接口加了更严格条件 | 公式、事件区间和反向合并顺序与冻结实现一致；新函数要求 `available_at`，这是合理加严，但不能称已逐值兼容缺少该字段的旧事件文件。 |
| 动量 | 一致 | `I(t-21)/I(t-252)-1`；自身有效报价；第 253 条首次可算；不含最近 21 条。测试的手算值正确。 |
| RV20 | 一致 | 简单收益最近 20 个值、`ddof=1`、乘 `sqrt(252)`，包含当前收益。 |
| 波动历史分位 | 一致 | 最多 756、至少 252、当前值包含、相同值平均名次、除非空数；`>=0.8` 剔除，NaN 放行。现有测试覆盖相同值和 0.8 端点。 |
| 排名与 Top 3 | 部分一致 | 分数降序、完全同分代码升序、过滤后前三正确；但当前报价资格没有落进函数边界。 |
| SMA200 | 登记一致 | 最近 200 个自身有效报价，含当前；月末无 SMA 入场过滤。退出 `<`，相等不卖；恢复 `>=`，相等可触发。 |
| 月度与快速回补 | 登记文字一致，未实现为纯函数 | policy 卡准确写出月度目标优先、实际止损净卖款预算、等待跌回撤单留预算、无每日重排。现有单元测试并没有复核这些状态转换。 |
| 75% 参照 | 一致 | 月度总目标 75%，不是每日固定 75%，也不是相同风险；实际持仓允许漂移。 |
| 普通平均配置 | 一致 | 当月全部动态合格产品平均，不用动量/RV，不做 SMA 月末入场过滤。 |
| 集中度 | 一致但函数范围较窄 | 登记分清完整账户权重、在场资产权重和方向利润占比；`concentration()` 只算当时持仓权重和 HHI，不算冻结报告的“前三方向利润/账户净利润”。 |

## 4. 字段、类型和用途验证的遗漏

`validate_registry()` 确实检查了每张卡具有 15 个顶层字段、5 个分节的必填键，且 benchmark／policy 另有 9 个执行字段；也检查精确版本依赖、循环依赖、来源键存在、研究用途不与 `not_for` 相冲突，以及生产状态必须是未授权。这是有效的基础防线。

但以下内容仍未被机器校验：

1. **类型来源与覆盖数**：`TYPES` 只在 Python 中写死为 6 类：`feature`、`state_signal`、`factor_return`、`risk_metric`、`benchmark`、`policy/strategy`。由于标准文件缺失，无法证明这就是用户要求的全部类型；验证器也没有从权威标准加载或核对类型版本。
2. **用途来源与组合约束**：`USES` 同样写死为 6 项。只检查“属于集合”，没有检查例如用于 `ranking` 的对象应输出可排序标量/有序名单、用于 `attribution` 的对象必须声明资金分母和币种、`research_signal` 必须有执行时点。
3. **字段的数据类型**：没有检查 `name/scope` 是非空字符串、`uses/not_for/dependencies/sources` 是非空字符串列表、`input.fields` 是无重复字段名列表、`tolerance` 三项是有限非负数、`tests` 是路径列表、`timezone` 可解析。
4. **语义单位**：多张布尔状态或名单对象沿用 `unit='fraction'`。例如 `mixed.top3` 实际输出有序代码名单，`mixed.eligible` 和 `mixed.volatility_allowed` 是布尔状态；当前验证器不检查“类型—单位—公式”的匹配。
5. **来源内容**：只检查对象引用的来源键存在，不验证每个来源具有合法相对路径和 64 位哈希，也不在加载登记表时核实际文件哈希。此次人工检查恰好全部匹配，不代表以后能自动阻止漂移。
6. **顶层结构**：不检查 `standard`、`created`、`profiles`、`sources`、`models` 的完整结构；未知顶层键和未知卡片键也会静默接受，拼错字段只要同时继承到一个同名正确字段就可能不被发现。
7. **policy 内容有效性**：只检查 9 个键存在，不检查值非空、费用与 `definition.parameters` 一致、依赖是否真的包含 selection/均线/现金所引用对象。
8. **用户边界的强制性**：`resolve(..., purpose='production_trade')` 会拒绝，因为生产不在 `uses`，但直接调用纯函数没有 registry reference、用途或 manifest 约束。模块注释写“无订单执行”是说明，不是运行时边界。

## 5. 其他函数与时间语义风险

### P2：manifest 的登记表哈希不是文件哈希

`make_manifest()` 第 336 行将内存 JSON 排序后重新编码再求哈希。它不是 `definitions.v1.json` 的原文件 SHA-256，也没有保存登记表文件路径。相同语义但不同字节的文件会得到同一哈希，审计者也无法用常规 `sha256sum` 对上。若字段名仍叫 `registry_sha256`，应明确是“规范化内容哈希”；若要锁文件，应同时保存 `fingerprint(REGISTRY)`。

### P2：公司行动日期与可知时间的比较规则没有完全定型

代码用 `effective_date` 决定事件属于哪个相邻报价区间，再只检查它到当前报价收盘是否已经可知。没有检查 `available_at <= effective_date`，也未定义事件在当日 15:00 后公布、但 `effective_date` 仍写当天时是否应该推迟连接。冻结旧资料本来就缺逐条到达时间，因此新增严格函数应把“市场生效日”和“研究可知时刻”的冲突处理写成明确规则，不应由 pandas 时间比较偶然决定。

### P2：公开辅助函数允许绕过其登记语义

- `trend_state()` 直接接收含缺失行的序列时，交叉只看紧邻上一行，而不是上一条有效报价；`quote_features()` 因先删缺失而没有这个问题。应明确它只接受已经压缩的有效报价序列，或在函数内执行同一规则。
- `select_mixed()` 用字典键集合代表横截面，没有验证三个映射键是否相同、代码是否规范化为 6 位字符串、分位是否在 `[0,1]`。错误映射目前可能静默放行 NaN 或抛不稳定的 `KeyError`。
- `historical_percentile()` 没有拒绝无穷值；冻结 RV 输入不会产生无穷，但作为公开适配函数，输入契约应明确。

### P2：月末是否“已完成”只有文字限制，没有纯函数或校验

policy 的 limitation 正确提醒“部分月不能装作完成月”，但模块没有月末并集函数，也没有数据截止时间相对月末的检查。`make_manifest()` 只验证 `data_cutoff <= available_at <= decision_at`，不会判断该月是否已经结束。后续调用者若直接取当前数据最大日期作为月末，仍可能制造月中调仓。

## 6. 测试证据与缺口

执行：

```text
pytest -q tests/unit/test_research_definitions.py
...............
15 passed in 0.75s
```

现有测试有效覆盖：动量精确端点与价格尺度不变性、缺失报价压缩后的 SMA、SMA 相等边界、交叉事件、波动分位相同值与 0.8 剔除、RV 样本标准差、宽度共同分母、三档边界、简单公司行动、前缀不受未来数据影响、集中度分母、依赖与研究用途、manifest 时间顺序、非正和无穷价格拒绝。

最小必补测试：

- 累计 273 但决策日无当前报价，必须不合格；
- 带 `Asia/Shanghai` 时区的价格索引加现金分红／拆分，结果与无时区交易日输入一致且不报错；
- `standard` 路径缺失、来源哈希漂移、非法字段类型和空 policy 值应失败；
- 快速回补状态边界：实际全清才建预算、`>=SMA`、排队后跌回取消但保留预算、月度优先清队列；
- 月度最后日期必须证明月份已完成，不能把数据截止日自动当月末；
- `mixed.top3`、资格状态等对象的单位和输出类型与登记一致。

## 7. 验收建议

在三个 P1 问题修正并补测试前，建议状态保持“定义草案／研究适配器”，不要描述成已经形成完整、可独立复算的定义基础设施。修正只属于研究规范化，不授权迁移旧消费者、改生产判定、更新 OKR 或得出任何新收益结论。

## 8. 修订期间的失败记录与定向复核

以下记录保留修订过程，不用后来的通过覆盖先前失败：

- 初次审阅时原 15 个测试全部通过，但没有覆盖本文三项 P1。
- 主控加入新检查、实现尚未全部落盘的第一次中间态：28 项中 20 项通过、8 项失败。失败包括字段校验尚未生效、`verify_sources` 尚不存在、`trend_state` 尚未使用上一有效报价。
- 第二次中间态：28 项中 16 项通过、12 项失败。此时验证器已经要求定义标准 v1.0.0，但 `docs/research/definition-standard.md` 尚未写入，所有需要加载登记表的测试都被该前置条件阻断。这是修订中的有意义失败，不是旧收益实验失败。

### P1：ETF 基准不能继承成分股宽度 profile 的输入与资格

当时版本中，以下五张卡使用 `profile="breadth"`，却没有覆盖 `input`、`universe`、`time` 和 `scope`：

- `baseline.etf_hold_reinvest`
- `baseline.etf_price200`
- `baseline.etf_monthly50`
- `baseline.hold_paid_cash`
- `baseline.hold_payment_open`

展开后会错误声称这些固定 ETF 账户需要 `membership_by_date`、成分股连续价、当日成分资格、至少 200 个成分股报价以及 90% 宽度覆盖。实际账户输入是 510300／159915 自身的名义开收盘、公司行动、交易限制、份额、现金和应收；持有基准也不需要宽度成员资格。

具体建议：建立独立的“ETF 账户执行”profile，或由五张卡逐项覆盖上述四节。`baseline.etf_price200` 可要求 ETF 自身 200 个连续价格观察，但这与“成分股共同分母至少 200 个有效报价”不是一回事。

### P1：宽度策略卡同时有信号池和成交标的，不能只继承单一宽度输入

12 张 `policy.breadth.{all_a,csi300,chinext}.w0-w3` 的宽度信号资格继承正确，但账户执行还需要固定 510300／159915 的名义 OHLCV、行动、限制和账户状态。建议每张策略卡的 `input` 明列 `signal_input` 与 `traded_etf_input`，`universe` 分开 `signal_universe` 与 `execution_instrument`，并在 `scope` 说明每个宽度来源绑定哪个 ETF。否则“信号能算”会被误读成“账户成交输入也合格”。

### P1：长期投入基准不应继承 mixed 的 273 报价月选资格

`baseline.dca_quarterly`、`baseline.dca_hold`、`baseline.dca_single` 虽已覆盖输入、时间和范围，但当时仍继承 mixed profile 的 `universe`：当前存续 14 只、决策日有报价且累计 273、月度选择。实际长期投入是固定 4 只 ETF（单产品版固定 510300），按各自上市和可成交状态管理，没有混合池动量月选的 273 报价门槛。三张卡必须覆盖 `universe`，避免把两项研究资格混在一起。

### P1：ETF 连续价格与 mixed 经济指数不是同一公式

独立读取 `research-etf-breadth-confirmation-2026-09-09/run_backtest.py:50-69` 后确认：ETF `continuous_close` 首值等于首个名义收盘，不是 1；现金分红日使用 `ref=previous_close-cash`，拆分日再 `ref/=ratio`，随后 `level *= current_close/ref`。mixed 经济指数则是首值 1，并用 `(current_close*split_multiplier+cash)/previous_close` 连接。现金分红下两式通常不相等，不能只靠缩放解释。

因此，B1 自身 SMA200、W3 自身 SMA50 应依赖独立的 `etf.price.continuous` 以及对应 `etf.trend.sma50/200`、`etf.trend.above50/200`；不能依赖限定为 mixed 经济指数的 `trend.*`。测试至少要用一次现金分红手算出两个指数确实不同，并锁住 ETF 版本的首值和除息分母。

### P1：B0 实现允许支付日当天开盘再投，协议文字却写下一开盘

`run_backtest.py:214-236` 的顺序是：自然日开始先把支付金额从应收转入现金；若 `method=="B0"`，立即创建 `signal_date=day` 的再投指令；随后执行条件对 B0 特别放行，不要求 `signal_date<day`。若支付日当天有可交易开盘且不受限，实际就在同日开盘买入。

这与 `protocol.md:21` 和旧卡片“分红支付后下一可成交开盘”的自然理解不同。历史结果应登记实际代码口径为“假设支付款在支付日开盘前可用，支付日有可成交开盘则同日买；否则延后”；同时把协议文字差异留在 `limitations`。不能将它改写为所有研究通用的分红可用时点。

## 9. 最终补丁独立复验

最终读取版本：

| 文件 | 最终复验 SHA-256 |
|---|---|
| `docs/research/definition-standard.md` | `b12fe66d7b13e41a4e11b17b77c9e2251e98d2655ee00a7b8d53881a3f0c5ade` |
| `docs/research/definitions.v1.json` | `1626c0b4f414de09fbb2f523daffa73c8db0018048cf860cc5f40c3b1414de7a` |
| `src/lei_signal/research/definitions.py` | `1e465d3c24dea5999522376663e1976054b50f9f0e545e689caa27e9aee60599` |
| `tests/unit/test_research_definitions.py` | `ca1119620caa38ed064def8ec9d04615b6f8d1571c3537592ab5217f2f593276` |

最终测试：

```text
pytest -q tests/unit/test_research_definitions.py
............................
28 passed in 0.78s
```

最终额外只读检查：登记的 30 个来源文件指纹全部吻合；累计 273 但 `current_quotes` 为空时选择结果为空；带 `Asia/Shanghai` 时区的价格索引遇到现金分红可正常计算；定义标准文件及 `standard_version=1.0.0` 均可加载；manifest 同时保存登记表与标准原文件指纹。

本文最初三项 P1 均已关闭：

1. `select_mixed` 强制要求显式 `current_quotes`；
2. `economic_index` 正确处理无时区和带时区观察日期；
3. 定义标准 v1.0.0 已落地，字段、来源、时区、policy 和模型卡的结构检查已有失败用例。

定向复核发现的继承问题也已关闭：五张 ETF 账户基准覆盖了自身名义行情、行动、限制与可交易资格；三张长期投入基准不再继承混合池 273 报价月选门槛；12 张宽度策略同时声明宽度信号输入和 ETF 成交输入，并按全 A、沪深300、创业板分别写清实际或拟执行对象。创业板成员链失败、冻结旧账户未运行的状态得到保留，没有冒充已运行结果。

ETF 连续价已登记为独立对象，并有自身 SMA50／SMA200 与严格站上状态；没有再把它伪装成 mixed 经济指数的缩放版本。B0 卡也已把“支付日开盘前记入现金、同日有合法开盘即可买，否则延期”的实际代码口径写入，同时保留冻结协议文字差异。

结论：在本次允许的定义规范化范围内，先前发现的阻断问题已经修复，最终版本可作为研究对象身份、计算口径和证据来源的登记入口。这里的“通过”只指登记与小型计算接口一致；旧消费者尚未迁移，历史收益没有重跑，研究有效性、生产采用和 OKR 状态均未改变。
