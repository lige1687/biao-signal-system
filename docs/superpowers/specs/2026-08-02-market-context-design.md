# Round 4：LEI 市场环境层设计

> 状态：已确认设计，待实施计划与开发
>
> 日期：2026-08-02
>
> 目标分支：`recovery/lei-round2`
>
> Round 3 当前状态：代码语义门禁完成；真实 `159915` 快照回放仍待验收

## 1. 背景与目标

LEI 技术信号研究系统目前以单一股票或 ETF 为分析对象，识别颜色、双均线、
顶底结构、量能、长周期趋势和关键性波动。Round 3 已将底部观察链统一为按
`structure_id + lifecycle_id` 推进的事件生命周期：

```text
candidate
→ early_watch
→ structure_confirmed
→ joint_confirmed
→ long_trend_improved
```

Round 4 增加独立的“市场环境层”，补充以下信息：

- A 股与美股市场宽度；
- 指数自历史最高收盘价以来的回撤；
- 美国主动投资经理仓位情绪（NAAIM）；
- 美国个人投资者情绪（AAII）；
- 指数上涨但市场参与度下降等宽度背离。

市场环境层回答的是“当前市场是否为该技术机会提供顺风”，不是“这个标的的
技术信号是否成立”。首期采用纯提示模式：只输出 `顺风 / 中性 / 逆风 / 未知`、
原始维度与解释，不修改、不屏蔽、不降级任何单标的技术信号。

## 2. 非目标

Round 4 首期明确不做：

- 不修改 `DayState.opportunity_stage`；
- 不修改 `structure_id`、`lifecycle_id` 或底部状态机；
- 不把市场逆风解释成结构失效；
- 不直接输出买入、卖出或仓位建议；
- 不因历史收益调整 15% / 50% / 85% 等阈值；
- 不把 NAAIM、AAII 强行映射为 A 股情绪；
- 不接入融资余额、北向资金或未经定义的 A 股情绪代理；
- 不用当前指数成分股名单冒充正式历史宽度；
- 不抓取受限网页数据充当正式生产数据源。

## 3. 总体架构

新增独立包：

```text
src/lei_signal/market_context/
  types.py          市场环境领域类型
  universe.py       历史指数成分股及有效日期
  breadth.py        MA20/50/200 市场宽度
  drawdown.py       指数历史高点回撤
  sentiment.py      NAAIM、AAII 与发布时间对齐
  classifier.py     市场环境摘要与解释
  mapping.py        标的到参考市场的映射
  pipeline.py       市场环境分析入口
```

数据流：

```text
历史成分股 ─┐
             ├→ 市场宽度 ─────┐
成分股行情 ─┘                  │
                               ├→ MarketContextSnapshot
指数行情 ─────→ 指数回撤 ─────┤        │
                               │        ├→ UI 市场环境面板
NAAIM/AAII ──→ 情绪状态 ──────┘        ├→ 市场环境事件
                                        └→ 历史有效性研究

单标的 LEI 状态机 ─→ 技术信号 ─┐
                                ├→ 组合解释（并列展示，不互相覆盖）
市场环境快照 ───────→ 环境说明 ─┘
```

市场环境事件必须使用独立类型和独立存储，不混入原子技术信号的事件胜率统计。

## 4. 首期市场范围

### 4.1 A 股

首期正式覆盖：

| 市场 ID | 含义 |
|---|---|
| `CN_ALL_A` | 全部符合数据质量要求的 A 股 |
| `SSE_50` | 上证 50 |
| `CSI_300` | 沪深 300 |
| `CSI_500` | 中证 500 |
| `CSI_1000` | 中证 1000 |
| `CHINEXT` | 创业板 |

### 4.2 美国

首期覆盖：

- S&P 500；
- Nasdaq 100；
- Russell 2000；
- NAAIM Exposure Index；
- AAII Investor Sentiment Survey。

### 4.3 标的映射

- A 股个股：`CN_ALL_A` 为主参考市场；当日属于其他已覆盖指数时，将这些指数作为
  次级参考市场全部展示，不把多个市场压成一个分数；
- 上证 50 ETF：`SSE_50 + CN_ALL_A`；
- 沪深 300 ETF：`CSI_300 + CN_ALL_A`；
- 中证 500 ETF：`CSI_500 + CN_ALL_A`；
- 中证 1000 ETF：`CSI_1000 + CN_ALL_A`；
- 创业板 ETF：`CHINEXT + CN_ALL_A`；
- 美股标的：按当日指数归属映射到 S&P 500、Nasdaq 100 或 Russell 2000；存在
  多个归属时全部展示，并由版本化映射配置显式指定一个主参考市场；
- 无法识别：只使用国家级环境，并标记 `mapping_incomplete`。

映射结果是有顺序的 `primary_market_id + secondary_market_ids[]`。ETF 的主参考市场
是其跟踪指数；A 股个股默认以 `CN_ALL_A` 为主参考市场。多个参考市场分别保留各自
快照和摘要，不投票、不平均、不拼成综合分数。标的映射只决定展示哪些市场环境，
不参与单标的状态机推进。

## 5. 历史成分股口径

正式市场宽度必须使用 point-in-time 历史成分股：某交易日只能看到当日已经生效的
指数成分股名单。指数调仓从正式生效日开始应用。

支持三类来源，但语义严格区分：

1. **正式口径**：历史成分股版本 + 成分股行情自行计算；
2. **外部核对**：第三方预计算宽度，仅用于交叉核对；
3. **研究代理**：当前成分股回算历史，必须标记 `research_proxy`，不得进入正式
   结论或用来证明策略有效。

每份成分股快照至少包含：

```text
universe_id
symbol
effective_from
effective_until
source
source_version
retrieved_at
provenance
```

同一市场、同一日期存在重叠且互相矛盾的成分股版本时，输出
`DATA_CONFLICT`，不得自行挑选一个继续运行。

## 6. 市场宽度计算

对周期 `N ∈ {20, 50, 200}`：

```text
BreadthN = 当日收盘价高于 MA(N) 的合格成分股数量
           ÷ 当日具备完整 MA(N) 数据的合格成分股数量 × 100%
```

每个周期单独计算分母。新股不足 N 根时，只从该周期分母中排除，不影响更短周期。

每个日期必须同时保存：

```text
constituent_count
eligible_count_20/50/200
missing_count_20/50/200
coverage_20/50/200
breadth_20/50/200
universe_version
price_as_of
calculated_at
provenance
```

### 6.1 数据质量

- 覆盖率低于 90%：对应周期输出 `DATA_INCOMPLETE`；
- 缺失数据不能被解释成市场冷清，也不能自动归入“中性”；
- 正常短期停牌最多沿用最近 5 个市场交易日的可知状态，同时标记 `stale`；
- 长期停牌或行情异常需从合格分母中排除并降低覆盖率；
- 当日收盘后才能使用当日数据；
- 追加未来数据不得改变过去 `as_of` 时点的宽度结果。

5 个市场交易日是版本化的数据配置默认值，不写死在分类器中；允许未来按市场修改，
但修改必须升级配置版本并重新运行历史研究。移动平均只按该证券实际产生的交易收盘
计算，不为停牌日复制虚构 K 线。

## 7. LEI 宽度事件

保留作者给出的可复核固定阈值：

| 条件 | 事件 |
|---|---|
| `Breadth20 >= 85` 且 `Breadth50 >= 85` | `short_hot_extreme` |
| `Breadth20 <= 15` 且 `Breadth50 <= 15` | `short_cold_extreme` |
| `Breadth50 >= 85` 且 `Breadth200 >= 85` | `long_hot_extreme` |
| `Breadth50 <= 15` 且 `Breadth200 <= 15` | `long_cold_extreme` |
| `Breadth200 > 50` | `broad_bull_regime` |
| `Breadth200 < 50` | `broad_bear_regime` |

这些阈值来自 LEI 对美股市场宽度的观察。应用到 A 股时必须标记
`lei_threshold_research`，在样本外证据形成前不得称为 A 股有效阈值。

A 股与美股同时计算各自滚动历史分位数，用于比较固定阈值与本市场自身的极端值。
固定阈值和历史分位数是两个独立维度，不互相覆盖。

历史分位数默认使用截至 `as_of` 的最近 1,260 个市场交易日（约五年），至少需要
252 个有效观测；不足时输出 `unknown`。窗口长度与最小样本数均写入规则版本，
不得使用 `as_of` 之后的数据。

## 8. 宽度方向与背离

除绝对水平外，保存：

- 5 日变化；
- 20 日变化；
- Breadth20、Breadth50 是否扩张；
- Breadth200 是否改善；
- 指数价格方向与宽度方向是否背离。

变化量定义为当前值减去 5 或 20 个市场交易日前的值。Breadth20 与 Breadth50
的 5 日变化都大于 0 时为 `expanding`，都小于 0 时为 `contracting`；其余情况
（包括任一变化等于 0）为 `diverging`。若任一所需观测不可用，则为 `unknown`。

市场宽度拆为四个可解释维度：

```text
长期底色：牛 / 熊 / 未知
当前热度：极冷 / 偏冷 / 中性 / 偏热 / 极热 / 未知
扩散方向：扩张 / 收缩 / 分化 / 未知
极端事件：短期底部关注 / 长期底部关注 / 顶部风险关注 / 无
```

`heat_state` 使用 Breadth20 与 Breadth50 历史分位数的中位数，规则固定为：

| 条件 | 热度 |
|---|---|
| 触发任一固定 15% 冷极端，或中位分位 `<= 10%` | `extreme_cold` |
| 未极冷且中位分位 `<= 25%` | `cold` |
| 触发任一固定 85% 热极端，或中位分位 `>= 90%` | `extreme_hot` |
| 未极热且中位分位 `>= 75%` | `hot` |
| 其余有效观测 | `neutral` |
| 任一必要分位不可用且未触发固定极端 | `unknown` |

`long_regime` 在 Breadth200 `> 50%` 时为 `bull`，`< 50%` 时为 `bear`，
恰好等于 50% 或对应覆盖不足时为 `unknown`。

宽度背离使用 20 个市场交易日的固定定义：指数收盘收益 `> 0`，同时 Breadth20
与 Breadth50 的 20 日变化都 `< 0`，产生 `negative_breadth_divergence`；指数收益
`< 0` 且两条宽度变化都 `> 0`，产生 `positive_breadth_divergence`。等于 0、方向
分化或数据不足均不产生背离事件。

典型背离：指数创新高或继续上涨，而 Breadth20、Breadth50 持续下降。该状态输出
“指数上涨但参与度收缩”，只作为风险关注，不直接构成卖出信号。

## 9. 指数回撤

使用截至当日的历史最高**收盘价**：

```text
drawdown_from_ath = index_close / historical_max_close - 1
```

计算只使用 `as_of` 当日及以前数据。回撤与宽度极冷同时出现时，输出更强的
“人性极端观察”说明，但仍不等于趋势已经反转。

回撤阈值在首期不做收益驱动优化；分类器保留原始连续值和历史分位数。

## 10. NAAIM 与 AAII

### 10.1 NAAIM

保存：

```text
survey_week
available_at
exposure_index
ma20_weeks
historical_percentile
publication_delay
source
license_status
```

NAAIM 表示美国主动投资经理报告的美股风险敞口，不是未来方向预测。公开免费数据
存在约三个月延迟；没有及时授权数据时，只能用于历史研究，不得进入当前市场环境摘要。

### 10.2 AAII

保存：

```text
bullish
neutral
bearish
bull_bear = bullish - bearish
bull_bear_ma20_weeks
historical_percentile
survey_week
available_at
```

AAII 调查从周四开始、周三结束，结果在之后实际发布时才可用。回测按
`available_at` 对齐，不能倒填到调查周内。

### 10.3 情绪输出

```text
机构仓位：极低 / 偏低 / 中性 / 偏高 / 极高 / 未知
散户情绪：极度悲观 / 悲观 / 中性 / 乐观 / 极度乐观 / 未知
机构与散户：一致 / 分歧 / 不可判断
```

情绪指标不直接生成买卖信号。延迟或缺失数据必须输出 `stale` 或 `unknown`，不能沿用
旧值假装当前数据。

## 11. 领域模型

核心快照：

```text
MarketContextSnapshot
├── market_id
├── as_of
├── available_at
├── universe_version
├── breadth_20/50/200
├── coverage_20/50/200
├── breadth_percentiles
├── breadth_direction
├── drawdown_from_ath
├── long_regime
├── heat_state
├── extreme_events[]
├── divergence_events[]
├── naaim_state
├── aaii_state
├── summary
├── reasons[]
├── conflicts[]
├── provenance
└── data_status
```

`summary` 只允许：

```text
tailwind
neutral
headwind
unknown
```

摘要必须能够由 `reasons` 和原始维度完整复算。不能只存一个不可解释的综合分数。
首期不使用机器学习或收益优化生成摘要。

首期摘要只反映市场参与度的短期方向，使用固定且保守的规则：

| 前提 | `summary` |
|---|---|
| Breadth20 或 Breadth50 覆盖不足，或无法计算 5 日变化 | `unknown` |
| Breadth20、Breadth50 的 5 日变化都大于 0 | `tailwind` |
| Breadth20、Breadth50 的 5 日变化都小于 0 | `headwind` |
| 其他组合 | `neutral` |

Breadth200 牛熊底色、冷热极端、指数回撤、背离和 NAAIM/AAII 只进入
`reasons` / `conflicts` 与独立维度，首期不改变摘要。这避免在完成增量研究前，
用未经验证的权重拼出一个不可审计的综合评分。例如“熊市底色但短期宽度扩张”可以
同时显示 `tailwind` 摘要与“长期仍偏熊”的冲突说明。

## 12. UI 设计

单标的技术状态和市场环境并列展示：

```text
标的技术状态：双均线共同确认
市场环境摘要：中性

支持：
- 创业板 Breadth20、Breadth50 正在扩张
- 指数已从较大回撤中修复

冲突：
- Breadth200 仍低于 50%
- 长期市场底色偏熊

解释：
标的技术信号成立；市场短期改善，但长期环境尚未完全转强。
市场环境不改变该技术信号阶段。
```

UI 必须展示：

- 参考市场及映射原因；
- 顺风 / 中性 / 逆风 / 未知摘要；
- 长期底色、热度、扩散方向、极端事件；
- Breadth20/50/200 及覆盖率；
- 指数回撤；
- NAAIM、AAII 的发布时间、陈旧度和授权状态；
- 固定 LEI 阈值与市场历史分位数；
- 支持理由、冲突理由和数据限制。

`DATA_INCOMPLETE`、`stale`、`mapping_incomplete` 必须在主面板可见，不能藏在日志中。

## 13. 存储与审计

市场环境使用独立表，至少包括：

```text
universe_membership_versions
market_breadth_snapshots
market_context_events
sentiment_observations
market_context_assessments
```

每条记录保留 `as_of`、`available_at`、`source_version` 和 `provenance`。
同一原始数据修订不得覆盖历史快照，应保留版本或修订记录，以支持 point-in-time 审计。

## 14. 历史研究

研究问题不是“加入环境过滤后收益是否更漂亮”，而是：

```text
同一种 LEI 技术事件，在不同市场环境下，后续收益、MFE、MAE、失败率和信号延伸
是否存在稳定差异？
```

分组至少包括：

1. 原始 LEI 技术事件；
2. 技术事件 + 市场宽度状态；
3. 技术事件 + 指数回撤状态；
4. 技术事件 + NAAIM 状态；
5. 技术事件 + AAII 状态；
6. 技术事件 + 完整市场环境摘要。

研究要求：

- 按真实 `available_at` 对齐；
- 使用历史成分股；
- 固定阈值后做样本外窗口；
- 每次只增加一个环境维度，检查增量价值；
- 缺失数据进入 `unknown`，不能混入中性组；
- 不因研究结果自动修改单标的技术信号；
- 不把相关性描述为因果关系；
- 不把 A 股代理口径与正式口径合并统计。

## 15. 错误处理

- 成分股版本冲突：`DATA_CONFLICT`；
- 行情覆盖不足：对应周期 `DATA_INCOMPLETE`；
- NAAIM/AAII 未到发布时间：不可见；
- 情绪数据超出允许陈旧期：`stale`，不参与当前摘要；
- 标的映射失败：`mapping_incomplete`，退回国家级市场；
- 外部服务失败：允许读取满足陈旧策略的缓存，否则显式不可用；
- 任一维度不可用时，保留其他维度，但摘要必须披露缺失项。

## 16. 测试与验收

### 16.1 Point-in-time

- 某日宽度只使用当日有效成分股；
- 调仓生效日前不得提前使用新成分股；
- 追加未来行情不改变过去宽度；
- AAII/NAAIM 在实际发布前不可见；
- 指数历史高点只使用当日及以前收盘价。

### 16.2 宽度公式

- 20/50/200 分母独立；
- 新股只影响历史不足的周期；
- 覆盖率不足不产生冷清事件；
- 15% / 50% / 85% 边界有精确测试；
- A 股固定阈值事件带 `lei_threshold_research`。

### 16.3 隔离性

- 同一单标的行情在顺风、逆风和缺失市场环境下，`opportunity_stage` 完全一致；
- 市场环境不得创建或结束单标的 `lifecycle_id`；
- 市场事件不得进入原子技术事件胜率表；
- UI 必须明确写出“市场环境不改变技术信号阶段”。

### 16.4 数据质量

- 当前成分股回算只能得到 `research_proxy`；
- 正式与代理数据不得混合；
- 陈旧情绪数据不得伪装为当前数据；
- 数据冲突和映射不完整必须在 UI 可见。

### 16.5 真实验收

- 为 A 股六个市场各选至少一个包含调仓、停牌、新股和缺失行情的真实窗口；
- 与独立来源抽样核对多个日期的宽度；
- 美股宽度与外部图表做抽样交叉核对；
- 真实 NAAIM/AAII 数据核对发布时间，而不只核对数值日期；
- 真实数据不足时明确跳过，不得用合成数据冒充。

## 17. 实施阶段

### Round 4.1：基础设施

- 领域类型；
- point-in-time 历史成分股接口；
- 市场环境存储表；
- 数据质量与来源元数据；
- 单标的到参考市场映射。

### Round 4.2：A 股市场宽度

- 六类 A 股市场；
- Breadth20/50/200；
- 覆盖率与历史分位；
- 指数回撤；
- 固定 LEI 阈值事件；
- 宽度扩张、收缩与背离。

### Round 4.3：美国市场与情绪

- S&P 500、Nasdaq 100、Russell 2000 宽度；
- NAAIM；
- AAII；
- 发布时间、延迟和授权状态。

### Round 4.4：UI 与研究

- 市场环境面板；
- 支持与冲突解释；
- 独立历史有效性研究；
- 单标的技术层隔离门禁。

### Round 4.5：真实数据验收与影子运行

- 真实历史成分股回放；
- 外部宽度抽样核对；
- 数据陈旧与故障演练；
- 只提示、不交易的影子运行。

## 18. 完成标准

Round 4 只有同时满足以下条件才可称为代码完成：

- A 股六类市场宽度可 point-in-time 重算；
- 正式、外部核对、研究代理三种来源不会混淆；
- 美股情绪严格按发布时间可见；
- 市场环境与单标的状态机完全隔离；
- 缺失、陈旧、授权和映射状态可见；
- UI 能解释顺风、中性、逆风或未知的原因；
- 自动化门禁和真实数据抽样核对通过；
- 未调整 Round 3 的技术参数和结构生命周期。

即使完成以上内容，也只能表述为“市场环境研究与提示模块可用”，不能据此宣称
策略具有正期望或可以直接实盘。

## 19. 参考资料

- LEI，《最容易賺到錢的投資時機》：
  <https://www.youtube.com/watch?v=9_0RKCJjDSo>
- LEI，《市場寬度 Market Breadth》：
  <https://www.patreon.com/posts/90474496>
- NAAIM Exposure Index 官方说明：
  <https://www.naaim.org/programs/naaim-exposure-index/>
- AAII Investor Sentiment Survey 官方说明：
  <https://www.aaii.com/sentimentsurvey>
- LEI 制作的 NAAIM 与 AAII 参考图：
  <https://en.macromicro.me/charts/80902/NAAIM-Exposure-Index>、
  <https://en.macromicro.me/charts/80901/AAII-Investor-Sentiment-Survey>
