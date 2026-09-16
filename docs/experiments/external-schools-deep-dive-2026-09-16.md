# 外部技术流派融合深度调研（第二轮）

日期：2026-09-16。性质：**调研深挖**，零回测、零定义登记、零生产改动。承接第一轮候选盘点（`external-schools-fusion-candidates-2026-09-16.md`）。

## 一句话结论（大白话）

第二轮挖下来，最重要的发现其实是个"反向结论"：**最顺畅的融合不是从外面搬新流派，而是用成熟工具把我们自己规格里"写了但一直没实现"的两块补上**——筹码分布（规格 §11：成交密集的价格区域在哪里，用来找支撑、压力和盈利目标）和横盘密集/箱体识别（规格 §4.6 与 B 模块：怎么客观判定"盘完了、要动了"）。这两块本来就是自家规格，不存在边界问题。同时第一轮三个因子候选的精确算法和 A 股证据都补齐了；新扫描的流派（缠论、Wyckoff/SMC 等）结论是：与我们现有模块高度同构、独立证据弱，只吸收概念不引入全套。

## 0. 授权与边界

- 用户原话（2026-09-16）："再去深度探索, 做进一步的调研好吧"。授权范围＝第二轮深度调研；仍未授权任何回测、定义登记或生产改动。
- 治理不变：超规格候选走体系扩展提案；基本面/消息面只做叙事；外部结论不自动背书本地规则。
- 本轮方法：对第一轮一线候选取**原始口径**（定义、参数、窗口、触发条件）；对未覆盖流派查**形式化可行性**（有没有可执行的客观定义、独立回测证据）；对每个"规格内待实现章节"查**外部工具适配**。

## 1. 新发现的最高优先候选：规格内未实现章节 × 外部工具（P0）

### D1. 筹码分布 / 成交量剖面（Volume Profile）落地规格 §11

**规格溯源（这是它排最高优先的原因）：**
- §10 盈亏比过滤：合法目标 B 来源明确列出"已经形成的筹码密集区或成交量峰"；
- §11 整节就是它：回看窗口、价格分箱数量、POC（最大成交量价格）、HVN/LVN（高/低成交量区）定义、"接近筹码峰"的距离、固定还是滚动区间——一张完整的待配置清单；
- §15 回测顺序：第四轮过滤器里"筹码分布"排在最后，前置条件"先完成不含筹码的基础回测"——**第十二/十四批等基础账户已完成，前置条件已满足**；
- 内部现状：`filters-round4-log-2026-08-25.md` 中筹码过滤器**默认关闭落地，等独立实验开关验证**——系统里已经给它留了位置，只是一直没做。

**外部工具与日线可行性：**
- 成交量剖面是成熟体系：POC＝成交量最大的价格档；VAH/VAL＝围绕 POC 扩展覆盖 70% 成交量的价值区上/下沿（[TradingView 官方定义](https://cn.tradingview.com/support/solutions/43000502040/)）。
- 日线近似是社区标准做法：每天的总成交量按当日最高-最低区间展开（均匀或三角加权）分配到价格分箱，滚动窗口累积成分布（[Python 实现示例](https://juejin.cn/post/7553865490731319350)、[邢不行日线近似筹码分布](https://www.bilibili.com/read/cv25916232/)）。规格 §11 自己写明"最好使用更细粒度的成交数据"——近似版是合法第一版，须标注失真局限。

**它直接服务的既有模块（四个挂点）：**
1. A2 回调位置："回调到筹码峰附近"替代/补充"回调到均线附近"的支撑判定；
2. B 目标选择：密集区上沿作为盈亏比目标 B 的客观来源（§10 合法）；
3. D 假突破：低成交量区（LVN）价格稀薄、易被刺穿后收回——给假跌破/假突破一个结构性解释；
4. 量能异常：POC 附近的放量行为比全日放量更能定位"谁在出手"。

**风险与注意：** 日线分配假设敏感（单边长阳日的成交量其实集中在某一段）；ETF 分箱粒度与回看窗是规格 §17 式待确认参数；必须按规格原文"作为独立过滤器加入、比较增量效果"，不做参数搜索。

### D2. 波动收缩 / 箱体识别（服务 §4.6 均线密集 + B 模块环境条件）

**规格溯源：**
- §4.6 均线密集：六线压缩（参考约 2% 以内）、整理约不少于 6 个月，两个数值都标了"应做敏感性测试"——至今没有客观代理；
- B 模块 B1 环境条件："横盘阶段不频繁交易，只等待标志性动作"——**"横盘"本身没有客观定义**；
- §17 待确认参数表直接点名：`cluster_threshold`（密集最大宽度）、`minimum_consolidation_bars`（横盘最短时间）；
- 主战场计划阶段三 open item："B 的长期箱体与局部观察区间**先把定义补清**"，由总控按策略定稿。

**外部工具（三个可执行的客观定义选项）：**
1. **布林带宽分位（Bollinger BandWidth Squeeze）**：带宽跌入历史低分位＝波动收缩状态（[Bollinger 本人的 Squeeze 定义](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/bollinger-band-squeeze)、[量化回测](https://www.quantifiedstrategies.com/bollinger-band-squeeze-strategy/)）；
2. **Darvas 箱体规则**：创新高后停顿、箱底三日不破则箱体成立；**收盘价**破箱顶＋**放量**才触发（[规则要点](https://tradethatswing.com/the-technical-foundations-of-nicolas-darvass-trading-strategy/)、[Investopedia](https://www.investopedia.com/terms/d/darvasboxtheory.asp)）。注意"真 Darvas 箱＝强势品种创新高后的停顿"，与 B 模块"均线刚形成多头排列时提前观察"语义对齐；
3. **ATR 收缩 / VCP 思想**：回撤逐级收窄后突破。反证要记：VCP 宣传的高胜率依赖强市＋强板块，弱板块中≈抛硬币（[对照分析](https://www.finermarketpoints.com/post/mark-minervini-vcp-patterns-why-sector-and-thematic-filters-matter-more-than-pattern-selection)）；证据多为实践者回测与卖方材料。

**它直接服务的点：** 给 B 模块一个客观"环境成立"判定；给待定稿的 B 箱体定义提供三个具体构造选项供主控选择（不替代定稿权）；"收盘确认＋放量确认"正好对应 §17 里悬而未决的 `break_basis` 与 `volume_threshold`。

**风险：** squeeze/VCP 类证据质量参差（实践者回测为主，样本多为美股个股）；宽基 ETF 创新高频率高、箱体窄，"新高后停顿"结构比个股少见，需按 ETF 重新数样本。

## 2. 第一轮一线候选的精确口径（P1 补强）

### C1. 52 周新高距离
- **原文学术口径**（George & Hwang 2004）：`接近度 = 当前价 / 过去 52 周最高价`；按接近度十分组，最接近新高组后续收益显著更高，且经典动量利润的相当部分可被接近度解释；机制＝锚定效应（投资者锚定旧高点，不愿在接近新高处追买，导致价格对信息反应不足）。
- **本地定义草案（feature）**：`close / rolling_max(close, 252)`。与既有 `mixed.momentum.raw`（12-1 动量）的差异：锚是**历史最高点**（变量锚）而非固定窗口，且不剔除近月——两者是不同对象，登记时须写差异表。
- **A 股证据**：上证 A 股复制研究存在（[SSRN 2025](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6403338)），本轮未能取得全文细节；立项前按文献工作流补方法卡，不以其摘要直接背书。国际市场后续验证见 [Liu 2011](https://www.sciencedirect.com/science/article/abs/pii/S0261560610001099)。
- **已知风险**：动量崩溃/深回撤有专门研究（[Jeon 2023](https://epublications.marquette.edu/cgi/viewcontent.cgi?article=1168&context=fin_fac)）；ETF 池小，先描述统计。

### C2. 剩余动量（残差动量）
- **A 股实证口径**（[BigQuant 2015-2025 全 A 检验](https://bigquant.com/wiki/doc/vmpoW4sE1e)，5487 只含退市股、119 个月度截面）：
  - 普通价格动量：3/6 月回看 IC 全负（最优组合 IC 均值 -0.032，T=-2.66 显著反向）；高动量组年化仅 2.04%、回撤最深 -68%；多空净年化 -6.8%——再次确认 A 股裸动量不可用；
  - 残差动量构造：逐股滚动 12 个月 OLS 回归（对市场等权＋行业等权收益），**残差累积看 6 个月、跳过最近 1 个月**，上下 1% 缩尾＋截面标准化；
  - 结果：IC +0.0086、ICIR +0.15（T=+1.47，方向从 -0.24 翻正但未达 5% 显著）；
  - **机制发现（对我们最有价值）**：A 股表观反转主要来自系统性部分（板块轮动均值回归），剥掉后特质动量为正——解释了"选强为什么总选到高贝塔"。
  - 附加发现：震荡市动量 ICIR +0.45、牛市反转 -0.36——与"道路"分层（横盘/趋势）结合的天然接口。
- **与经典原版的差异要登记**：Blitz 2011 原版是 36 个月回归＋12 个月残差动量；BigQuant 是 12 个月回归＋6 个月残差。正式立项必须冻结一个口径并写明出处。
- **小池适配草案**：10-14 只 ETF 逐只回归自由度不足，建议简化为"相对沪深 300 超额收益的 12-1 动量"（贝塔调整简版）或对指数基准的滚动回归残差；口径选择留给协议冻结。

### C3. 市场宽度推力（Zweig Breadth Thrust）
- **原始口径**（Zweig《Winning on Wall Street》）：指标＝**上涨家数 /（上涨＋下跌家数）的 10 日均线**；触发＝10 个交易日内从 **<0.40 冲上 >0.615**（[定义](https://www.tradingsim.com/blog/breadth-thrust-indicator)、[Zweig 原文引述](https://www.tradingview.com/script/RvGzTmhX-Breadth-Thrust-PRO-by-Martin-E-Zweig/)）。
- **证据面**：1945 年以来美股仅约 14-25 次（[Investopedia](https://www.investopedia.com/terms/b/breadth-thrust-indicator.asp)、[逐次统计](https://quantifiableedges.com/a-look-at-zweig-thrust-signals/)）；历史前瞻收益平均约 6 个月 +15%、12 个月 +20-23%；2025-04-24 有最新案例。**以实践者统计为主、学术检验少**——定位只能是市场级路牌（描述先行），不能当信号。
- **A 股适配**：涨跌家数比可由既有宽度面板直接推出；0.40/0.615 是美股口径，A 股阈值必须重新标定并列敏感性；**2024-09-30 前后极可能是一次典型事件**——我们轮动研究正是在这次踏空吃亏，若清点证实，它是"路牌层缺市场级预警"的直接注脚。第一步永远是事件清点（预期个位数到十几次），样本太少就止步于描述。

## 3. 新扫描流派速评（第一轮未覆盖）

| 流派 | 核心思想 | 与我们体系的关系 | 判定 |
|---|---|---|---|
| **缠论** | 分型→笔→线段→中枢→背驰，三类买卖点 | 中枢≈均线密集区；背驰≈顶底构造＋力度衰减；三类买卖点≈A 回调/B 突破/C 反转——**高度同构**。开源生态成熟（[chan.py](https://github.com/Vespa314/chan.py) 笔段算法可配置、[czsc](https://github.com/waditu/czsc) Rust 化"去笔段化"因子路线），但笔/线段定义本身流派分歧大，无实现能对齐原文，线段划分是公认难点 | **全套不引入**；只吸收一个概念——"背驰＝离开段力度弱于进入段"作为路牌候选（与关键性波动互补）。注意：chan 的背驰量化用 MACD 面积比例，属于**强度比较**用法，与我们 MACD 唯一口径（强度非转折）兼容，但若登记必须标研究代理 |
| **Wyckoff / SMC（聪明钱/流动性扫荡）** | spring（假跌破）/upthrust（假突破）、吸筹-派发结构、量价背离 | spring≈我们 C 的 2B/假跌破，upthrust≈D 的假突破；effort vs result＝量能异常的理论化。量化证据稀薄：独立回测少，一个期货品种 spring 回测胜率 43%、盈亏因子 0.74（亏损）（[来源](https://pinescriptforge.com/6E/wyckoff-spring/backtest)、[综述](https://www.quantifiedstrategies.com/wyckoff-trading-strategy/)） | **不做新信号**：我们的 C/D 模块本来就是这套思想的规则化版本，D 机会少的事实与"该类形态独立证据弱"互相印证；命名与叙事可借鉴 |
| **Darvas 箱体** | 新高后停顿成箱、收盘＋放量破顶 | 并入 D2，作为 B 箱体定义的候选构造规则 | 并入 P0-D2 |
| **VCP（波动收缩形态）** | 回撤逐级收窄后突破 | 并入 D2；强市/强板块依赖是重要反证 | 并入 P0-D2 |
| **Coppock 曲线** | 月频长周期底部确认（两个 ROC 之和的 WMA 上穿零轴），为指数设计 | 服务投资线（长期资金进场时点参照），不入技术判定 | P3 低优先；本轮未单独核证 A 股证据，如关注再补 |
| **Ichimoku 一目均衡表** | 云图＋转换/基准线＝均线族扩展 | 与双均线体系信息冗余 | 不引入 |
| **Elder 三重滤网** | 大周期定向、中周期择时、小周期触发 | 多周期纪律＝规格 §6 周期扩散已有；中周期震荡器腿被 C4（RSI-2）覆盖 | 不引入（概念已有） |
| **海龟金字塔加仓** | 每 0.5N 逐笔加仓 | 我们 §14 单笔状态机不含加仓语义，属体系扩展 | P3 扩展提案候选（低优先） |
| **Elliott 波浪 / Harmonic / 斐波那契** | 主观数浪/比例 | 无可证伪的客观定义（违反 lo2000"先写清图形是什么"原则） | 不引入 |
| **CANSLIM / Minervini SEPA** | 基本面成长＋个股形态 | 个股线已降级，主战场宽基/ETF | 不引入（VCP 思想已并入 D2） |

## 4. 两轮合并后的总优先级

| 级别 | 候选 | 一句话理由 |
|---|---|---|
| **P0 规格内实现** | D1 筹码/成交量剖面；D2 波动收缩＋箱体 | 自家规格 §10/§11/§4.6/§17 的占位空格，外部工具成熟，零边界成本 |
| **P1 因子线首批** | C1 52 周高距离；C2 剩余动量；C3 宽度推力 | 与因子线直接结合；口径已补齐；C3 零新增数据 |
| **P2 模块对照** | C4 RSI-2（A 模块简单对手）；C5 绝对动量腿（轮动退出对照）；C6 ATR 通道（距离参数统一） | 便宜的比较与参数化，不产生新信号 |
| **P3 低优先/特定用途** | Coppock；海龟加仓；Weinstein 阶段（展示语言）；日历效应（执行优化）；网格（闲钱线） | 各有专门用途或证据不足 |
| 概念吸收、不做信号 | 缠论"背驰＝力度衰减"路牌；Wyckoff 命名体系 | 与既有路牌/量能异常互补 |
| 不引入 | Ichimoku、三重滤网、Elliott/Harmonic/斐氏、SMC 全套、CANSLIM、宏观/资金流 | 冗余或不可证伪或越界 |

## 5. 下一步可执行草案（全部待授权，未启动）

- **若先走 P0**：D1/D2 都是"独立过滤器/环境定义"路径。协议冻结要点：输入＝既有日线 OHLCV；D1 需定分配假设（均匀 vs 三角）、分箱数、回看窗（§17 式参数表）；D2 需在三个箱体构造选项中由主控定稿一个；比较对象＝既有 48 技术账户与 R0/R1 直接引用，输出按规格 §16。
- **若先走 P1**：C1/C2/C3 各写方法卡＋定义草案进登记表（feature/state_signal），走 factor_unit B1 同款"描述→可靠性→对照"路径；C3 第一步是事件清点（含 2024-09-30 案例）。
- **可并行建议**：C3（零新增数据、工作量小）可与 D1 或 D2 并行；D2 直接服务 B 子批待定稿项，做了就有下游消费者。

## 6. 最小决策卡

| 项 | 内容 |
|---|---|
| 本轮做了什么 | 一线候选精确口径＋A 股证据深挖；未覆盖流派扫描与判定；规格内待实现章节×外部工具映射 |
| 本轮没做什么 | 仍未验证任何候选有效性；未登记任何定义；未启动协议 |
| 新增关键结论 | P0＝规格内实现（D1/D2）；缠论/Wyckoff 只吸收概念；Ichimoku 等明确不引入 |
| 需要用户决定 | ① 首批走 P0（规格内）还是 P1（因子线），或 C3＋D2 并行；② D2 箱体构造选项是否交主控定稿流程；③ C2 小池口径选"超额动量简版"还是"对基准回归残差" |
| 下一步（若授权） | 写 D1/D2 或 C1/C2/C3 的方法卡＋单项冻结协议 |

## 7. 本轮新增证据来源

- A 股动量与残差动量：[BigQuant 实证（2015-2025）](https://bigquant.com/wiki/doc/vmpoW4sE1e)
- 宽度推力：[TradingSim 定义](https://www.tradingsim.com/blog/breadth-thrust-indicator)、[Investopedia](https://www.investopedia.com/terms/b/breadth-thrust-indicator.asp)、[Quantifiable Edges 逐次统计](https://quantifiableedges.com/a-look-at-zweig-thrust-signals/)、[Zweig 原文引述](https://www.tradingview.com/script/RvGzTmhX-Breadth-Thrust-PRO-by-Martin-E-Zweig/)
- 缠论形式化：[chan.py](https://github.com/Vespa314/chan.py)、[czsc](https://github.com/waditu/czsc)
- Wyckoff/SMC：[QuantifiedStrategies](https://www.quantifiedstrategies.com/wyckoff-trading-strategy/)、[6E spring 回测（PF 0.74）](https://pinescriptforge.com/6E/wyckoff-spring/backtest)
- 成交量剖面：[TradingView 官方](https://cn.tradingview.com/support/solutions/43000502040/)、[Python 日线实现](https://juejin.cn/post/7553865490731319350)、[日线近似筹码分布](https://www.bilibili.com/read/cv25916232/)
- 波动收缩/箱体：[Bollinger Squeeze（StockCharts）](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/bollinger-band-squeeze)、[QuantifiedStrategies 回测](https://www.quantifiedstrategies.com/bollinger-band-squeeze-strategy/)、[Darvas 规则](https://tradethatswing.com/the-technical-foundations-of-nicolas-darvass-trading-strategy/)、[VCP 板块依赖反证](https://www.finermarketpoints.com/post/mark-minervini-vcp-patterns-why-sector-and-thematic-filters-matter-more-than-pattern-selection)

外部结论均有市场与口径适用条件，不构成对 A 股 ETF 的直接证明；正式立项时按文献工作流 v1.1.0 补方法卡与原文定位。
