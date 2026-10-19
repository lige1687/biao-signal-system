# 研究工具、基准与数据：复用审查与一个实际入口修补

2026-10-20｜个人低频研究准备层；检索、代码及公开文档核查。没有新行情回测、安装、付费数据开通或生产策略变更。

## 一句话结论（大白话）

**这批工具值得分工使用，我们已经具备其中不少能力。目前最影响研究可信度的是历史资料能否还原当时所知，以及买卖能否按记录发生。** 本轮补了一个实际断点：JKP、French、AQR已有登记，研究准备工具却查不到它们；现在真实命令能分别取回1、8、2张参照卡，同时保留用途和未验证状态。旧诊断工具和已完成回测直接复用。RQData列为具体数据候选，账户访问、实际返回质量和完整覆盖尚未验证。

本轮没有证明任何新因子更赚钱，也没有重跑其他对话的价值、现金经营盈利、应计或资产增长研究。检索改善解决的是后续AI漏查、重复建设和用错资料的问题；尚未测量它节省了多少时间或费用。

## 各项怎样采用，哪些已经做过

| 资源/工具 | 当前实际状态 | 本轮取舍与用途边界 |
|---|---|---|
| JKP Global Factor Data | 已有`reference.jkp.catalog@1.0.0`，本轮补通检索；没有本地逐股复现适配 | 用于分类、找定义、比较跨市场与分组证据。官网区分公开组合收益与需机构WRDS订阅的逐股数据，不能把前者当成本地选股原始表。[官网](https://jkpfactors.com/)、[下载说明](https://jkpfactors.com/data) |
| Kenneth French Data Library | 月度FF5与动量解析、百分数转小数、快照指纹及市场/币种/频率检查已有 | 保留作收益来源解释和经典定义参照。已接通的`classic_attribution`实验限定中国CH3、六ETF和固定期间；不能由共用读取函数推定US FF5已自动适用于A股。官网有源格式/分红再投入口径变化，冻结快照须保留。[官方库](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) |
| AQR Data Sets | BAB、QMJ已有来源卡；本地作用未验证 | 用于低贝塔、质量、价值/动量的原方法与公开结果对照；原论文版、更新版和本地版本区分。公开多空组合不能直接代表个人做多组合。[官方数据](https://www.aqr.com/Insights/Datasets) |
| Alphalens Reloaded | 已有固定来源组件；排名持续性/组内成员变化有真实保存分数调用报告 | 直接复用。原技术分支还有排名关联及分组收益组件，避免仅搜当前目录漏判“没有”。成员变化不等于成交金额换手，缺失不能悄悄删除；不整包换平台。[已有真实使用报告](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/alphalens-ranking-use-2026-10-08.md) |
| statsmodels | 已借用有限的相关误差估计函数，独立CLI可用；当前Python未安装完整包 | 普通/滚动回归可按具体问题再选用。滚动窗口默认处理缺值、估计结果可用时点须显式核定；同月回顾解释不能当月初预测。[官方滚动回归](https://www.statsmodels.org/stable/examples/notebooks/generated/rolling_ls.html) |
| arch | 已借用有限组件，用于相同日期、目标、单位下的多候选误差比较 | 直接复用既有连续日期重组和共同比较工具；当前实现没有覆盖全部arch方法。统计检查数字不代表因子有效概率，也不能补回未留账的试验。[官方说明](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison_examples.html) |
| QuantStats | 限定代码及当前Python中未找到安装/调用 | 可作最终收益序列的图表层，优先级低于数据与成交资格。应输入扣费用、含现金和未成交影响的账户收益；重叠持有期收益、IC或前后组收益差不能冒充账户净值。[官方仓库](https://github.com/ranaroussi/quantstats) |
| RQData | 公开文档提供按历史查询日取财报、公告日/版本标识、历史股本等接口；当前未接入实取 | 作为补历史财务/股本的候选，先核返回字段与原财报，之后才决定是否值得购数。公共文档不能证明本账号可用、供应商当时到达时间或所有年份覆盖。[财务/股本说明](https://www.ricequant.com/doc/rqdata/python/stock-mod) |
| vectorbt / 自建引擎 | 项目已有交易与资金相关模拟器；限定目录和当前Python未发现vectorbt | 保留现有引擎。vectorbt可作将来速度/独立算账对照，不能自动补中国市场制度和资料。官网也说明共享现金、订单顺序与成交价格的假设；不因能批量运算就升级回测可信度。[官方组合接口](https://vectorbt.dev/api/portfolio/base/) |

当前环境核对仅覆盖`/opt/homebrew/opt/python@3.11/bin/python3.11`及本次限定项目路径，未穷举所有环境。完整包未安装不等于缺少功能；组件已实现也不等于所有入口自动调用。

## 实际修补与相对原有能力的增量

原`preparation.build_context`读取唯一登记表，却只把因子对象与方法案例纳入检索；`research_references`只被格式校验。真实查询证实三个名称均不返回参照卡。本轮在原模块增加关键词检索和准确版本参数，原定义与案例输出保持一致。

| 同一条真实查询 | 修补前直接返回的参照卡 | 修补后 | 独立检查 |
|---|---:|---:|---|
| JKP | 0 | 1 | 原卡逐字段相同，仍为资料来源记录 |
| French | 0 | 8 | 含5个因子、动量、模型说明与官方案例；8张卡不是8个独立因子 |
| AQR | 0 | 2 | BAB/QMJ用途、状态和来源原样保留 |
| 准确查询`reference.jkp.catalog@1.0.0` | 原CLI无此参数 | 精确1张 | `@latest`拒绝；不静默换版本 |

默认每类结果最多6条，French测试显式使用`--limit 50`；超过上限时返回截断数量和未显示ID，不能把默认显示数当全部命中。输出单列参照卡，与可计算因子对象分开；明确“仅已有登记，本次未重新取源”，执行授权仍为false。没有新增资料库、定义表、实验账本或自动下载器。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lei_signal.research.preparation \
  --term JKP --term French --term AQR --limit 50

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lei_signal.research.preparation \
  --reference-ref reference.aqr.bab@1.0.0
```

该入口已按原文件指纹核对后补到主工作区，两文件与成果树相同；旧14项准备检查加新增4项均通过。另一条独立核查对真实登记卡逐字段比较，并确认旧动量定义/案例输出不变。它仍需现有登记表与依赖；不能由两份源码交付声称全部设备资料已恢复。

Luna第一版测试把机构写在顶层，真实数据却放在`source`里面，导致French仍会漏查。主控发现后先按真实结构重现，再修复并跑真实CLI；保留失败说明。这次实证说明，合成用例通过不能代替真实入口验证。

## 最大缺口与优先次序

**第一，补齐可追溯的历史输入。** 复用已有600源检查，混合复权标记的来源已经定位；旧财务比较受影响的记录仍待原范围纠错，不能用换工具绕开。后续数据资格应同时绑定报告期、公告日、修订版本、我们取得资料的时间，以及历史股本、名义价格与分红拆股。当前名单不能代表过去名单，低股价也不能替代小市值。

RQData文档使这项候选更具体：财务查询显式指定历史`date`，审查时保留`statements='all'`的版本及`info_date/if_adjusted`；历史股本另查`get_shares`。价格接口要明确复权方式和停牌保留方式；历史合约列表有日期参数。以上仅是公开接口依据，没有取回供应商样本。[行情/合约说明](https://www.ricequant.com/doc/rqdata/python/generic-api)

接入前需完成的具体验收是：用同一报告期公告前后、后来修订前后对照原报；纯拆股不能算净发行；停牌不删掉时间轴；已退出股票保留退出前历史；字段单位、同一证券身份和价格调整相互一致。真实付费试用/账号权限未确认，本轮没有凭空编造结果。旧数据请求预算不重置。

**第二，把基准与成交落到同一研究问题。** 因子排序、随后报价、实际买卖账户分别回答不同问题。市场、币种、频率、是否扣无风险收益以及做多/多空不一致时，不凑一张排行榜。我们的`engine.simulate_trade`里仍有默认关闭、按9.5%近似的涨跌停处理；这只是该入口的简化假设，不能代表整个系统或各历史板块制度已合格。原600股诊断已发现次日停牌等暴露，复用原证据，不重测。

补成交研究时，应检查T日决定、T+1尝试、未成交留现金/等候、卖出受限、最低交易单位、费用和共同资金占用；没有相应规则与资料时，报告只能叫报价结果。用vectorbt或自建引擎都要遵守同一合同；新引擎的优先条件是解决已证实的性能或对账问题，目前未有这种证据。

**第三，让AI真正取到既有研究与失败。** 本轮检索补丁已落地；下一AI可以在原准备入口找到参照、版本和用途，随后复用现有合同、家族运行记录及报告登记。所有试验继续写现有`research-workflow-ledgers-2026-09-29/<family-hash>/`与原报告/registry；旧冻结入口的覆盖限制继续披露，不另建“统一账本”。

## 保留、暂缓与未评价

- 保留：JKP/French/AQR/OSAP参照；现有Alphalens诊断、有限统计组件、自建引擎与研究账本。
- 本轮实际采用：现有准备入口的参照卡检索与准确版本取回；用途是减少漏查并保留证据边界。
- 暂缓：批量安装分析平台、迁移vectorbt、仅为漂亮报告接QuantStats。需要一个现有能力无法解决的具体问题才重开。
- 待资料：RQData实际访问/数据样本、完整历史规模/财务版本及成交资格；价值和现金经营盈利原题归“因子实现”，不重复。
- 未评价：新策略收益、风险保护效果、所有工具自动接通、真实token/时间成本节省。本轮没有伪造因子性能表。

## 证据与复现

- [实际查询前](raw/research-stack-gap-audit-2026-10-20/actual-cli-before.json)、[实际查询后](raw/research-stack-gap-audit-2026-10-20/actual-cli-after.json)、[独立验收](raw/research-stack-gap-audit-2026-10-20/verification.json)。
- [来源与阅读范围](raw/research-stack-gap-audit-2026-10-20/sources.json)、[本地原件指纹](raw/research-stack-gap-audit-2026-10-20/local-source-bindings.json)、[主控裁决](raw/research-stack-gap-audit-2026-10-20/controller-review.md)。
- 改动：`src/lei_signal/research/preparation.py`、`tests/unit/test_research_preparation_references.py`；原准备模块前版保存在本raw，便于核增量，未改冻结源定义。
- 复用：[数据输入防护](lowfreq-data-integrity-enforcement-2026-10-20.md)、[12–1与资格体检](momentum-universe-execution-audit-2026-10-20.md)、[三候选与OSAP](trend-factor-reuse-2026-10-20.md)。
- 两份策略SHA仍为`df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`及`85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`；本轮只服务研究准备层。

## ARCHIVE

有界工具复用审查与检索补缺完成；数据质量和有效策略目标未完成。10个公开文档页面、22个读取/定位操作，0新行情、0市场试验、0付费/安装/交易/通知。Luna低思考盘点和小实现，root审查实际结构、工具覆盖与真实CLI，模型实际费用未知。旧研究预算、原规范及另一对话范围保持；发布/归置回执与当前协调记录另存同名raw及原进度。
