# 买方智库与因子研究来源集合

来源核对：2026-11-04；接入日期：2026-11-05。用途：围绕个人低频、宽基与ETF的具体问题找方法、反例和数据定义；个股横截面研究作为补充验证。

优先顺序：AQR学组合构建与成本，Robeco学低风险与其他信息的联合使用，Alpha Architect学筛选顺序与集中持仓代价；JKP、Tidy Finance、OSAP负责校准定义与查原始证据。机构公开研究有自己的产品视角，来源信誉与本地策略效果分别判断。

本集合已接入既有BIAO「策略研究 → 文献学习库」的`classic-process`路线；同一`learning-seed.json`保存方法卡，本文保存研究来源与检索用途。机器可读采用边界见[参考口径卡](../research/buy-side-method-reference.v1.json)，实际验证见[接入报告](../experiments/buy-side-method-increment-2026-11-05.md)。来源年代本身不等于过时；保留仍适用且已核的方法，淘汰已被修订的实现或不适用的历史收益结论。

## 六个核心入口

| 来源与入口 | 优先查什么 | 帮我们补什么 | 什么时候查 | 本次阅读范围与边界 |
|---|---|---|---|---|
| [AQR Research](https://www.aqr.com/Insights/Research) | portfolio construction、transaction costs、turnover、style integration、value momentum、defensive equity | 同一因子如何形成可持有组合，过滤的收益损失与成本取舍，ETF风格/资产配置研究依据 | 建议双周看新标题；遇到组合或成本问题再精读 | 官方目录和Craftsmanship原文摘要/部分正文检索内容；未完整复现论文。税务、多空、杠杆结论按本地市场另核 |
| [Robeco Insights](https://www.robeco.com/en-int/insights) | conservative investing、low volatility、net payout yield、momentum、China、enhanced indexing | 低风险与收益来源怎样联合选股，风格长期落后风险，选股与指数实现差异 | 建议双周；低波研究时定向查 | 目录及2023 Guide的保守公式段落已核。原例为股票组合，不能直接变成ETF择时规则 |
| [Alpha Architect](https://alphaarchitect.com/blog/) | quantitative value、financial strength、concentration、momentum、transaction costs | 排雷、估值、质量的先后顺序；集中持仓的耐受与执行成本 | 建议双周，优先原作者研究和方法文 | 搜索取得官方QV文章的五步构造；目录和文章直接打开均403，未读全篇。博客摘要继续追原论文 |
| [JKP / Global Factor Data](https://jkpfactors.com/) | characteristic definition、profitability、idiosyncratic volatility、release notes、replication | 把名字落实到公式/时点/缺失口径；把历史数据错误变成边界案例 | 建议每月看变更；公式实现前必查相关条目 | 当前Python仓库2026-11-01变更与部分财务测试已核；锁定5429dcb版本，未逐个复核全部因子，不当实时信号 |
| [Tidy Finance portfolios.py](https://github.com/tidy-finance/py-tidyfinance/blob/main/tidyfinance/portfolios.py) | portfolio sorts、bivariate、formation、holding period、missing returns、min_portfolio_size | 排名、形成期/持有期、缺值和小组收益的明确语义 | 修改分组或持有逻辑时按需查；建议每月看版本 | 2026-10-26提交c67253a的相关函数已读；未安装原包。默认min_portfolio_size=1，5是常用示例；小组收益置空不等于交易组合删行业 |
| [Open Source Asset Pricing](https://www.openassetpricing.com/) | signal browser、replication、原论文、post-publication、变量构建 | 机制对应哪些已有代理变量；已发表发现是否重复、是否有复制证据 | 新机制立题时查；建议每月扫更新 | 官方首页与项目定位已核；本轮未逐项读取信号浏览器、代码与发表后表现 |

## 代表阅读入口

- AQR：[Craftsmanship Alpha](https://www.aqr.com/insights/research/journal-article/craftsmanship-alpha-an-application-to-style-investing)。先问：同一信息换成不同组合构造，改变了哪些持仓、风险和成本？官方页标2017-12-31，属于经典材料。
- Robeco：[Guide to Conservative Investing](https://www.robeco.com/docm/docu-202302-guide-to-conservative-investing.pdf)，保守公式在第6页附近：低波筛选后，使用净派息/回购相关收益率与价格动量，季度再平衡。净派付收益率不等同于经营现金流或盈利能力。
- Alpha Architect：[The Quantitative Value Investing Philosophy](https://alphaarchitect.com/the-quantitative-value-investing-philosophy/)。已核官方搜索摘录列出股票池、排除异常、估值、财务质量、集中持仓；全篇访问受限。
- JKP：[当前Python数据修订记录](https://github.com/bkelly-lab/jkp-data/blob/5429dcb786155228135df840ca97f9e33920c5c0/CHANGELOG_DATA.md)。先核最新财务季度去重、连续四季度TTM及年度/季度合并变化；本地年度GP不受季度TTM修改直接影响。旧SAS记录只留历史背景，不作为当前实现。规则必须连同处理阶段和研究对象使用，不能提炼成跨所有场景的绝对禁令。
- Tidy Finance：直接核上表源码的compute_portfolio_returns、_aggregate_bivariate_returns、filter_sorting_data。关注小组收益置空的位置，以及形成后不能因后来不合格而删除历史持有收益。
- OSAP：从首页Signal Browser进入具体信号，保留论文与代码对应关系；本次未完成具体信号精读。

## 按问题使用的工程与评价来源

| 来源 | 可学习的部分 | 当前优先级与限制 |
|---|---|---|
| [AlphaAgent论文](https://arxiv.org/abs/2502.16789) | 因子表达式结构相似度、复杂度、假说与实现语义对照 | 中：适合补具体反例审查。论文摘要已核，未审全仓源码；LLM一致性评分不证明金融机制，语法不同也可能信息相同 |
| [FactorBench论文](https://arxiv.org/abs/2610.06947) | 单因子、因子集合、费用后组合三个层次统一评价 | 中高：用来完善已有增量比较。摘要与§3.3三级评价协议已核；已将费用后比较适配到现有入口，未运行原发布代码或重现完整基准 |
| [QuantaAlpha论文](https://arxiv.org/abs/2602.07085) | 修改轨迹复用、表达式和代码一致性 | 低：本地已做限定组件比较，应先读旧结果。QuantaAlpha-claw的Lead/Miner/Reviewer、完整Skill链本轮未核实 |
| [TradingAgents仓库](https://github.com/TauricResearch/TradingAgents) | 反方证据、风险角色和共享来源去重 | 低：本地已有借鉴，当前上游版本未重新核验。角色多不自动产生独立证据 |
| [Factor Engine论文](https://arxiv.org/abs/2602.14138) | 模块化因子计算与参考实现核对 | 低：仅核摘要和书目信息；OffsetColumnManager具体实现未核，不能说自动消除历史数据泄漏 |

## 可重复使用的检索方法

双周扫买方新材料、每月扫代码/数据变更是建议阅读节奏，**当前没有创建自动任务、订阅或通知**。一次只围绕一个正在影响判断的问题检索；没有新材料或新增用途时，保留旧结论即可。

可复制检索词：

- `site:aqr.com ("portfolio construction" OR "transaction costs" OR "turnover")`
- `site:robeco.com ("low volatility" OR "conservative investing") ("China" OR "momentum" OR "net payout")`
- `site:alphaarchitect.com ("quantitative value" OR "concentration" OR "transaction costs")`
- JKP / Tidy：原变量名＋缺失处理、收益口径、发布时间、形成日、持有期、修订记录。
- OSAP：先用机制词查原论文和已存在信号，避免把旧因子换名字重做。
- 近期扫描用上次检查日期到本次日期；核文章自身发表/修订日，搜索引擎抓取日期不算研究日期。经典材料只在能解当前问题时补读。

每轮产出不追求数量：最多保留3条有实际增量的候选，可以为0。每条用以下记录：

| 记录项 | 要回答的问题 |
|---|---|
| 原文与阅读范围 | 谁在什么时候研究了什么？读到摘要、方法还是代码？ |
| 机制与本地用途 | 信息为什么可能有用？改善选标的、风险、持仓还是减少无效操作？ |
| 适用市场与成本 | 股票/ETF、只做多/多空、杠杆、频率、费用和税制是否相同？ |
| 已有覆盖 | 对应哪份定义、旧报告、失败记录和负责人？有什么真正新增？ |
| 数据与可复现性 | 所需字段、当时可获得时间、修订版本、代码和许可是否明确？ |
| 支持与反例 | 同期基准、费用后效果、其他时期/市场、负结果是什么？ |
| 本轮取舍 | 只学习方法／已有覆盖／资料不足／值得单独验证；金融效果未测就明写 |
| 重开条件 | 哪一项新证据会改变旧决定？ |

进入本地检验时继续使用既有research-closure、定义登记、尝试预算与账户比较要求，不因文章上新自动开回测。ETF用途还要核基金/指数历史名单、分红与费用、母指数和可交易替代；股票论文的收益不能直接填入ETF收益栏。

## 第一批已筛出的阅读问题

| 问题 | 应读来源 | 当前取舍 |
|---|---|---|
| 为什么少于5只时返回null，和交易时留现金/重分权有何区别？ | Tidy源码＋JKP变更记录 | 优先作为边界定义案例；不把今日V2再次改成统一删行业 |
| 毛利/资产、经营盈利、经营现金流、净派付有哪些不同？ | JKP变量字典＋Robeco原文 | 优先做概念与字段映射，避免错名后反复回测 |
| 新过滤加进旧组合后，收益与风险究竟多改善了多少？ | FactorBench＋AQR；复用本地V2结果 | 已有比较，尚缺独立后续证据与完整交易资料；不重跑同一历史 |
| 语义检查能否发现“测卖压却实现普通反转”？ | AlphaAgent；本地mechanism_review | 值得保留为窄审查方法；定义反例与独立计算比增加角色更具体 |

[本轮接入与量化验证](../experiments/buy-side-method-increment-2026-11-05.md)。本集合保存网址与自行整理的阅读用途，不复制付费全文，不把开源代码许可等同于原始市场数据许可。

