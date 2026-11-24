# 其他策略组合与外部方法接入：三类组合、两种股票规模

2026-10-23。问题负责人：strategy-account-bridge-20261020。方法接入及固定比较已完成。先前存储失败保留；容量恢复后沿原合同完成新增5格、复用1格及两个预定时期对照。

## 一句话结论（大白话）

**已扩大检验价值＋动量、价值＋盈利能力，以及小规模盈利能力＋动量。主要十年里，较低的相关性没有转化为比单项更好的收益和亏损取舍，小规模结果更弱；暂不增加可采用的策略。最值得继续补资料的是在同一批便宜股票中检验经营支撑，而不是继续调这几条公开收益曲线的权重。专业方法已接入现有研究技能，全部固定比较、负结果及曲线已留档。**

个人实际费用扣除后的收益，以及相对对应母指数的优势，当前均**未评价**。本次可用的 French 资料是公开股票分组的毛收益，缺逐股持仓、换手和个人费用；三组平均参照也不是标普500、罗素2000或其他母指数。

## 2026-10-23 接续：先按金融含义区分中美市场与股票范围

**要区分。先说明一条赚钱或减亏的理由为什么可能在某类股票中成立，再固定股票范围和比较规则；不能回测后挑表现最好的股票池。当前还不能得出“A股用反转、美股用动量”的固定分工。** 下面复用已有结果，没有新跑策略，也没有把未完成的数据补齐写成新策略有效。

这里的 Universe 指“每次作出选择时实际允许买入的股票集合”。至少分清：交易市场与证券类型、财务指标能否相互比较、成交活跃程度与市值规模。指数成员是一个可追踪的研究范围，**指数名字本身不是收益机制**。市场环境则是另一个随时间变化的问题，不能与股票范围混在一起。

### 金融理由、争议与合适的比较

| 研究方向 | 从什么金融理由出发 | 应怎样限定股票范围 | 最需要排除的竞争解释；简单对手 |
| --- | --- | --- | --- |
| A股月度反转，另保留美股同定义对照 | 暂时卖压消退后价格可能修复；买入者承接压力可能得到补偿 | 当时有完整交易记录的股票；按形成日前的成交活跃程度比较；行业内相对反转另需历史行业归属 | 跌价可能反映真实坏消息、报价失真或风险变高。比较同一活跃档、同数量的低波动选择与普通反转，含费用及错过的大涨；成交额不是散户比例，也不是买卖价差 |
| 美股价值＋盈利能力联合选股，A股单独核定义 | 相对便宜还要有经营支撑，避免只买账面便宜但经营持续恶化的企业 | 第一项可检验提案是会计口径可比的非金融普通股；金融企业另核合适的盈利和资产定义。大规模且较易交易的股票可作操作上的起点，不能由上一轮赢家来证明机制 | 收益可能来自行业偏好、风险投入或单独盈利指标。对照单独价值、单独盈利、简单平均分，以及行业内比较；必须同一批有合格资料的股票。只取“财务资料齐”的公司也可能产生选择偏差 |
| 中美中期动量分别研究，再考虑与价值搭配 | 公开信息可能逐步反映在价格中；便宜与持续上涨有可能在不同阶段起作用 | 两国分别用历史成员、统一观察和持有期；规模与成交条件逐项对照，不先认定某国或某指数有效 | 也可能只是行业行情、共同市场风险或更大波动；急速反弹时旧输家走强可能伤害追涨。比较同池动量单项、价值单项、简单降低股票投入，以及共同下跌和少赚 |
| 小规模股票作为单独适用范围 | 信息覆盖、资金承接和交易容量可能不同，值得检验可迁移性 | 使用各市场当时的规模与交易资格，不能把 French 的“小规模”改叫罗素2000，也不能等同中证1000 | 高回报可能是承担难成交、退出或制度风险的补偿。保留较易成交对手、历史退出和真实费用；规模不直接证明信息少或散户多 |

这些是待检验的金融假说及研究顺序，不是已经证实的原因，也不是新生产规则。盈利数据仍属于独立策略研究，未改变原LEI技术判定中基本面只作解释的边界。

### 为什么中美不能直接照搬，又不能贴国家标签

1. **行为解释要与期限对应。** Jones等2021年稿研究2016年1月至2019年6月的上交所账户，发现不同资金规模的个人投资者行为并不相同，每日和每周的交易方向也会变化。这支持区分投资者和期限，不支持把所有散户看成一种人，更不能从每日或每周行为推出月度反转必胜。本轮实际读摘要、引言和资料章节至印刷页12，未复现其账户检验。[作者原稿](https://www.cfrn.com.cn/uploads/fileupload/45ca232b9e4f499b95fedc010e669a7b/paper/7f83b4e75e4b493a84dc501983ba7486.pdf)
2. **股票资格与价值定义可能包含制度背景。** 复用前次核读的Liu、Stambaugh、Yuan稿：其A股2000—2016研究排除最小30%等股票；不能把论文筛选阈值当成今天通用的投资规则。论文关于小公司的上市资格价值，是需要结合当年制度解释的线索，不能当作当前所有小盘股的收益原因。原反转规则看过去20个交易日、每天分批持有5天，与我们的月度方案不同。[原作者稿](https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2019/04/01-18-Stambaugh.Published.BlumePrize.pdf)、[此前方法与适用范围审查](/library?report=docs%2Fexperiments%2Fa-share-reversal-applicability-review-2026-10-20.md)
3. **同一个因子名字也可能测不同东西。** Novy-Marx稿用毛利润相对总资产，并排除金融企业；本轮French资料用经营盈利相对账面权益。美国公开分组的互补线索不能证明这一公式适合所有中国行业。先核会计含义、首次公告和修订，再比较效果。[原稿及本次此前阅读范围：摘要至§2.1](https://mysimon.rochester.edu/novy-marx/research/OSoV.pdf)
4. **交易限制改变可实现的收益。** 持有期限、当时适用的卖出限制、停牌、价格限制、费用、退出权利，都应按市场和历史日期记录；这里没有用一套今天的制度倒填全部年份。美元与人民币结果先各自比较；跨市场分配资金另算汇率、共同日期和费用，不能直接拼接两条本币收益曲线。

### 现有数字支持到哪里

下面全部是旧证据复用。A股是报价和费用近似比较，美股是公开毛收益组合；**两种计量不能用于直接评选哪个国家更好**。美股跌幅按月末计算，不包括月内最深下跌。

| 已有范围与时期 | 结果 | 相对简单对手的增量 | 能改变什么判断 |
| --- | --- | --- | --- |
| A股2014年底固定抽取300只；2014-12—2025-10共131形成月 | 买近期最差一成股票的月度反转存在排序线索；买入收益对低波动的完整共同月份为沪113、深92 | 费用可算的共同月份另为沪98、深75；每边0.25%费用近似后，月均差沪−0.479、深−0.523个百分点，误差范围均跨0 | 保留反转研究；不能采用“跌多就买”，也不能据此认定没有任何反转用途 |
| 美股French大规模，2015—2024，120月：价值＋盈利 | 年化13.45%；月末最大跌幅25.84% | 单独盈利15.56%／24.85%；组合年化少2.11个百分点、跌幅深0.99个百分点 | 固定各半搭配未改善这段历史的取舍；同一只股票的联合选股仍未评价 |
| 同期美股French较小规模：价值＋盈利 | 年化9.10%；月末最大跌幅46.33% | 两个普通组组合10.25%／33.27%；年化少1.15个百分点、跌幅深13.06个百分点 | 此版较小规模组合降低优先级；不否定所有小盘策略，更不能转述为A股小盘结论 |
| 同期美股French大规模：价值＋动量 | 年化11.94%；月末最大跌幅26.58% | 单独动量12.88%／24.14%；年化少0.94个百分点、跌幅深2.44个百分点 | 相关性较低仍不足以采用；保留原六格、早期和近期反例，不挑一段重命名 |

A股数字及完整/未知月份来自[月度反转原报告](/library?report=docs%2Fexperiments%2Freversal-method-replication-2026-10-21.md)；该固定300只不是沪深300。美股完整性能、增量、不确定性和四张曲线在下方原第2节，原数据与图均未改变。两个市场的个人实际净收益、同定义跨市场差异和真实母指数优势仍未评价。

### 接入现有研究流程的位置与本次取舍

**已接入组合研究技能的选题与合同检查环节**：每个候选先写机制、竞争解释、历史股票资格、当时可用字段、期限、强对手和成本，再看效果。不新增一个研究平台；这一说明不是程序自动拦截。

具体比较时，先分别报告“策略在本池相对简单方法的改善”；再保持规则、权重和成本一致，检查这种改善能否跨池保留。不同股票池本身的行业、市值和风险构成也要展示。若改成行业内排名、换了阈值形式或持有规则，就登记为另一个研究对象；行业内比较是在检查行业构成能否解释结果，不能单独证明经营机制。把一个池的收益减去另一个池的收益，不能证明选股信息更有效。共同股票资料只是控制比较，另须保留每池覆盖及被排除对象，不能删除缺失公司后声称全池有效。

母指数回答“主动选择值不值得”，同池简单方法回答“新增信息有没有帮助”，两者都保留。分红口径、币种、日期与可交易性对齐；ETF的实际可交易回报与指数总回报分开。资料不足时明确未知，不用当前名单回填，也不用三组平均参照冒充母指数。

| 下一项确实能改变取舍的证据 | 当前分工与状态（2026-10-23协调记录） | 本任务如何接用 |
| --- | --- | --- |
| A股反转按形成日前成交活跃程度比较，含同档低波动和费用 | `personal-lowfreq-system-audit-20261018`已登记开展；用36,019行完整原始机会，不能只用过滤后的结果 | 等原负责人实际交付后复核是否存在可用范围；本轮不重复跑。行业内反转仍需历史行业资料，尚未完成 |
| 沪深300、中证500、标普500、纳指100历史成员及报价、退出 | `research-utility-review-20261012`正在续采及跨来源核对；旧报告数量只是阶段快照 | 逐池核准入，下载成功不解锁策略；当前没有据其新增任何指数策略收益 |
| 中证1000/2000、Russell1000/2000/3000资格及下跌敏感度 | `downside-sensitivity-universe-20261023`新登记；ETF风险用途也是该负责人范围 | 只接用已核结果，不重新收集，也不把这些名称对应到旧French大小分组 |
| 同池便宜股票是否因经营支撑而更值得持有 | 本组合任务保留的下一研究问题；历史财务版本、行业与共同股票覆盖仍未合格 | 先补准确输入资格，再比较单项、简单组合与联合选择；现有聚合月表无法完成这项检验 |

本次完成的是**股票范围如何由金融理由决定、哪些争议应检验及怎样接续**。不重跑已封存组合，不扫描“市场×股票池×参数”挑赢家，不新增前向版本。尚无证据支持已经找到能穿越牛熊的新完整策略；这一限制与已有负结果一起保留。


## 1. 其他策略究竟研究什么

“价值”在这批资料中指相对股票市值，账面权益较高；“盈利能力”指经营盈利相对账面权益较高；“动量”指过去第12至第2个月上涨较多。它们都沿原来源定义，不能泛称任何便宜、质量或趋势指标。

| 固定候选 | 值得检验的金融理由 | 可能推翻它的情况 | 这轮实际状态 |
| --- | --- | --- | --- |
| 价值＋动量 | 相对便宜与价格延续来自不同判断，可能在不同阶段互补 | 便宜来自经营困境；动量在反弹期受损；共同股票风险仍高 | 大、小规模各1组已完成，未支持采用 |
| 价值＋盈利能力 | 购买便宜资产与经营支撑可能互补 | 两组股票仍一起跌；盈利带来的好处不足以补价值组拖累 | 大、小规模各1组已完成，未支持采用 |
| 盈利能力＋动量 | 企业经营与过去价格延续可能提供不同帮助 | 大盘旧比较相关仍高、近期增量反向；小盘交易成本可能更高 | 大规模复用；小规模已完成，未见改善取舍 |

两种规模沿 French 的纽约证券交易所市值中位数划分，覆盖其合格 NYSE、AMEX、NASDAQ 股票。它们**不能改称标普500或罗素2000**，也不等于A股沪深300和中证1000。组内按市值分配资金；各指标需要的财务、价格资料不同，因此合格股票并非严格相同。保留小规模是检验适用性，不预设小盘效果更好。

除这三对组合，原来商定的方向仍保留，但按负责人和具体缺口推进：

| 更完整的策略方向 | 本轮复用或等待的具体证据 | 为什么没有再做一份 |
| --- | --- | --- |
| 同一只股票上结合价值、盈利和动量 | 当时合格股票、财报公开日期与修订、行业、价格、完整退出与费用 | 分组收益不足以联合选股；历史指数成员与逐股数据正由 `research-utility-review-20261012` 补齐，资料完成还须核财务资格 |
| A股行业内相对反转 | 连续历史行业归属、流动性可比对手、交易限制和被错过的上涨 | 旧固定300股结果不能直接推广到中证1000；既有反转研究和行业资料保留，不重复回测 |
| 季度公告后的信息消化 | 首次公告及真实公开时点、可比盈利数据、公告前后价格与成本 | 单家公司披露样例不等于全市场完整策略，复用原三方向接续资料 |
| 市场趋势下的参与比例调整 | 固定、当时可判断的月度规则及下一次实际成交 | `personal-lowfreq-system-audit-20261018` 正负责SPY固定月度规则与费用情景，本轮不重做 |
| 机构申赎或持仓变化 | 公告时点、申赎与主动选择区分、完整同期资料 | `mechanism-rebalancing-review-20261020` 正负责机构资料与收益检验，本轮只读其状态 |

这些是研究候选及分工，不是已经上线的5套交易策略。A股与美股分别结论，不以美股论文替代A股效果。

## 2. 实测结果：五组新增、一组旧结果复用

主要十年为2015—2024，共120个月；每段独立从100开始，两边初始各50，以后不转钱。下面均为公开毛收益，月末最大跌幅不包含月中风险。**六组相对各自来源参照的月均收益差，描述范围全部跨过零；尚未找到稳定、可直接采用的低相关组合。**

### 性能表与简单对手

| 固定组合 | 年化毛收益 | 月末最大跌幅 | 各自来源参照年化 | 已结束最长／期末未恢复的低于前高月数 |
| --- | ---: | ---: | ---: | ---: |
| 大规模 盈利能力＋动量 | 14.29% | 23.28% | 12.46% | 18／1 |
| 较小规模 盈利能力＋动量 | 10.73% | 38.96% | 9.09% | 26／1 |
| 大规模 价值＋动量 | 11.94% | 26.58% | 12.39% | 25／1 |
| 较小规模 价值＋动量 | 10.38% | 39.51% | 9.09% | 26／1 |
| 大规模 价值＋盈利能力 | 13.45% | 25.84% | 12.08% | 17／1 |
| 较小规模 价值＋盈利能力 | 9.10% | 46.33% | 9.25% | 27／1 |

月数是月末观察低于过去高点的次数，不含恢复到前高的那个观察月，不能当完整自然月跨度。大规模盈利＋动量的旧结果逐项一致；其新对手和诊断补入本轮。

单项必须一起看，避免只挑容易战胜的对手。以下不重复列同一来源：

| 股票规模与单项 | 全部投入年化 | 全部投入月末最大跌幅 | 半份单项、半份零息现金年化 | 半份单项、半份现金月末跌幅 |
| --- | ---: | ---: | ---: | ---: |
| 大规模 盈利能力 | 15.56% | 24.85% | 10.12% | 18.78% |
| 大规模 动量 | 12.88% | 24.14% | 8.10% | 17.42% |
| 大规模 价值 | 10.92% | 38.08% | 6.69% | 22.82% |
| 较小规模 盈利能力 | 9.49% | 45.88% | 5.68% | 27.21% |
| 较小规模 动量 | 11.86% | 32.70% | 7.36% | 20.18% |
| 较小规模 价值 | 8.69% | 46.76% | 5.14% | 28.15% |

### 相对已有信息的增量表

下面单位均为**年化差额，百分点**。每对名称中第一个叫第一项、第二个叫第二项；“普通第一项＋强第二项”等保持初始各半的相同资金结构。来源参照由每个来源的低、中、高三组月收益平均构成，再以初始各半合用；它不是普通中间组，也不是母指数。

| 组合 | 对第一项单独 | 对第二项单独 | 对普通第一项＋强第二项 | 对强第一项＋普通第二项 | 对两普通组 | 对各自来源参照 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 大规模 盈利能力＋动量 | -1.27 | +1.41 | +1.71 | -0.18 | +1.51 | +1.83 |
| 较小规模 盈利能力＋动量 | +1.25 | -1.13 | -0.91 | +1.10 | +0.11 | +1.65 |
| 大规模 价值＋动量 | +1.02 | -0.94 | +1.14 | -0.21 | +0.90 | -0.45 |
| 较小规模 价值＋动量 | +1.69 | -1.48 | -0.11 | +1.14 | +1.01 | +1.29 |
| 大规模 价值＋盈利能力 | +2.53 | -2.10 | +1.00 | +1.84 | +3.01 | +1.37 |
| 较小规模 价值＋盈利能力 | +0.40 | -0.39 | -0.12 | -1.04 | -1.15 | -0.15 |

**三个值得改变下一步取舍的事实：**

- 大规模价值＋动量的涨跌同步程度确实更低，但11.94%的年化和26.58%的月末跌幅，均不如单独动量的12.88%与24.14%。当前固定搭配不值得因为“低相关”就采用。

- 大规模价值＋盈利能力的相对表现最有互补线索，但13.45%的年化和25.84%的月末跌幅，也不如单独盈利的15.56%与24.85%。可优先核同一批便宜股票中的经营支撑，不能把现有资金搭配当联合选股已经有效。

- 扩到较小规模没有改善主要十年的取舍。盈利＋动量月末跌幅38.96%，价值＋盈利46.33%；后者还不如普通两组的10.25%年化、33.27%跌幅。小规模方向先降低优先级。

### 相关性、共同亏损与不确定性

原收益相关接近1表示大多一起涨跌；“相对差额相关”先扣各自来源参照，只描述相对表现，**没有完整消除市场或行业风险，不是可独立交易的收益**。低相关本身不决定采用。

| 组合 | 原收益相关 | 相对差额相关 | 两强组共同亏损／120月 | 两普通组共同亏损／120月 | 共同亏损月组合平均收益 | 对来源参照月均差描述范围（百分点） |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 大规模 盈利能力＋动量 | 0.924 | 0.247 | 35 | 36 | -4.06% | [-0.120, +0.326] |
| 较小规模 盈利能力＋动量 | 0.922 | -0.327 | 39 | 46 | -5.77% | [-0.032, +0.265] |
| 大规模 价值＋动量 | 0.725 | -0.432 | 32 | 36 | -4.81% | [-0.222, +0.169] |
| 较小规模 价值＋动量 | 0.915 | -0.182 | 39 | 45 | -5.70% | [-0.096, +0.304] |
| 大规模 价值＋盈利能力 | 0.744 | -0.639 | 28 | 38 | -5.31% | [-0.013, +0.254] |
| 较小规模 价值＋盈利能力 | 0.947 | 0.261 | 46 | 44 | -5.41% | [-0.233, +0.307] |

描述范围来自同一套连续12个月分块重抽，每次保留相邻月份的部分依赖，共2000次、固定种子。它描述已见历史月均差的不确定性，不是年化、最大跌幅或未来胜率范围；本轮方法审阅通过，主控未重复整套随机重抽。

### 四种情况：不能只报平均

六组共同使用大规模动量来源参照的涨跌分月：上涨77个月、不涨43个月；这只是事后描述，不是牛熊或实时调配。表格每格为“月份数／组合相对自身来源参照的平均差额（百分点）”；各组相等月份均为0。

| 组合 | 共同参照上涨、组合更多赚 | 共同参照上涨、组合更少赚 | 共同参照不涨、组合相对更好 | 共同参照不涨、组合相对更差 |
| --- | --- | --- | --- | --- |
| 大规模 盈利能力＋动量 | 37／+1.06 | 40／-1.23 | 25／+1.41 | 18／-0.61 |
| 较小规模 盈利能力＋动量 | 39／+0.71 | 38／-0.74 | 30／+0.88 | 13／-0.82 |
| 大规模 价值＋动量 | 33／+0.92 | 44／-1.08 | 25／+1.01 | 18／-0.67 |
| 较小规模 价值＋动量 | 31／+0.66 | 46／-0.80 | 35／+0.98 | 8／-0.84 |
| 大规模 价值＋盈利能力 | 44／+0.68 | 33／-0.45 | 14／+0.68 | 29／-0.39 |
| 较小规模 价值＋盈利能力 | 39／+0.91 | 38／-0.84 | 21／+1.17 | 22／-1.15 |

大规模价值＋盈利虽将两组共同亏损从38个月减为28个月，但在共同参照不涨的43个月中有29个月落后自己的来源组合。**共同亏损次数减少仍不等于整体更抗跌**，次数也受单项自身亏损频率影响。

| 组合 | 同一8个大涨月平均收益 | 自身来源参照平均收益 | 少赚月份数／8 | 第一项期末资金占比 |
| --- | ---: | ---: | ---: | ---: |
| 大规模 盈利能力＋动量 | 8.66% | 10.21% | 6 | 55.83% |
| 较小规模 盈利能力＋动量 | 12.47% | 12.54% | 3 | 44.65% |
| 大规模 价值＋动量 | 9.57% | 10.23% | 6 | 45.64% |
| 较小规模 价值＋动量 | 11.58% | 12.41% | 6 | 42.87% |
| 大规模 价值＋盈利能力 | 9.78% | 9.71% | 4 | 39.91% |
| 较小规模 价值＋盈利能力 | 12.72% | 12.20% | 4 | 48.19% |

大涨月份按固定共同参照正收益月份中最大的10%向上取整选择，全部6组用同样8个月，只报均值与次数，不拼成一条账户。长期资金占比漂移同样不能忽略：早期大规模盈利＋动量的盈利份额从50%降至27.75%。

### 更早历史和近期反例

| 时期与组合 | 年化毛收益 | 月末最大跌幅 | 对自身来源参照年化差（百分点） | 对第一项／第二项单独年化差（百分点） |
| --- | ---: | ---: | ---: | --- |
| 1963-07—2014-12 大规模 盈利能力＋动量 | 12.55% | 46.12% | +2.60 | +1.28／-0.81 |
| 1963-07—2014-12 较小规模 盈利能力＋动量 | 17.06% | 53.56% | +4.27 | +2.24／-1.12 |
| 1963-07—2014-12 大规模 价值＋动量 | 13.11% | 53.86% | +2.36 | +0.28／-0.25 |
| 1963-07—2014-12 较小规模 价值＋动量 | 17.37% | 55.55% | +4.54 | +1.24／-0.80 |
| 1963-07—2014-12 大规模 价值＋盈利能力 | 12.19% | 55.84% | +1.52 | -0.65／+0.92 |
| 1963-07—2014-12 较小规模 价值＋盈利能力 | 15.57% | 58.58% | +2.48 | -0.56／+0.75 |
| 2025-01—2026-08 大规模 盈利能力＋动量 | 16.81% | 10.44% | -3.73 | +0.44／-0.44 |
| 2025-01—2026-08 较小规模 盈利能力＋动量 | 17.15% | 15.24% | -2.05 | +4.87／-4.74 |
| 2025-01—2026-08 大规模 价值＋动量 | 27.32% | 7.72% | +4.67 | -9.57／+10.07 |
| 2025-01—2026-08 较小规模 价值＋动量 | 21.00% | 13.51% | +0.93 | +0.89／-0.89 |
| 2025-01—2026-08 大规模 价值＋盈利能力 | 26.91% | 6.24% | +3.41 | -9.98／+10.53 |
| 2025-01—2026-08 较小规模 价值＋盈利能力 | 16.23% | 15.33% | -3.92 | -3.87／+3.96 |

近期大规模价值＋动量27.32%、价值＋盈利26.91%的年化看上去很高，但只覆盖20个月，价值单项同期更高；不能据此宣称找到新的稳定高收益策略。大规模价值＋动量早期也不如动量单项的收益与跌幅取舍；早期六组月末跌幅仍达46%—59%，没有“穿越牛熊还能少跌”的证明。

### 收益曲线与相对差额

先看相对各自来源参照的累计收益差；下方绝对资金路径同时保留两单项，避免只看一条好看的组合线。两方先从同一100起点独立复利，再求累计收益差，未连乘每月差额。个人净费用和真正母指数优势仍未评价。


大规模股票：三组相对差额

<svg xmlns:xlink="http://www.w3.org/1999/xlink" width="100%" style="max-width:100%;height:auto;display:block" viewBox="0 0 691.2 734.4" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-10-23T18:11:08.132126</dc:date>
    <dc:format>image/svg+xml</dc:format>
    <dc:creator>
     <cc:Agent>
      <dc:title>Matplotlib v3.11.2, https://matplotlib.org/</dc:title>
     </cc:Agent>
    </dc:creator>
   </cc:Work>
  </rdf:RDF>
 </metadata>
 <defs>
  <style type="text/css">*{stroke-linejoin: round; stroke-linecap: butt}</style>
 </defs>
 <g id="figure_1">
  <g id="patch_1">
   <path d="M 0 734.4 
L 691.2 734.4 
L 691.2 0 
L 0 0 
z
" style="fill: #f8fafc"/>
  </g>
  <g id="axes_1">
   <g id="patch_2">
    <path d="M 82.944 258.672 
L 635.904 258.672 
L 635.904 95.472 
L 82.944 95.472 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_1">
    <g id="xtick_1">
     <g id="line2d_1">
      <defs>
       <path id="m80ae50af5d" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_2">
     <g id="line2d_2">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_3">
     <g id="line2d_3">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_4">
     <g id="line2d_4">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_5">
     <g id="line2d_5">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_2">
    <g id="ytick_1">
     <g id="line2d_6">
      <path d="M 82.944 250.379585 
L 635.904 250.379585 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_7">
      <defs>
       <path id="m7712ef1b3c" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="250.379585" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_1">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="254.178413" transform="rotate(-0 75.944 254.178413)">0</text>
     </g>
    </g>
    <g id="ytick_2">
     <g id="line2d_8">
      <path d="M 82.944 224.333445 
L 635.904 224.333445 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_9">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="224.333445" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_2">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="228.132273" transform="rotate(-0 75.944 228.132273)">10</text>
     </g>
    </g>
    <g id="ytick_3">
     <g id="line2d_10">
      <path d="M 82.944 198.287305 
L 635.904 198.287305 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_11">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="198.287305" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_3">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="202.086133" transform="rotate(-0 75.944 202.086133)">20</text>
     </g>
    </g>
    <g id="ytick_4">
     <g id="line2d_12">
      <path d="M 82.944 172.241165 
L 635.904 172.241165 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_13">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="172.241165" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_4">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="176.039993" transform="rotate(-0 75.944 176.039993)">30</text>
     </g>
    </g>
    <g id="ytick_5">
     <g id="line2d_14">
      <path d="M 82.944 146.195025 
L 635.904 146.195025 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_15">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="146.195025" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_5">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="149.993853" transform="rotate(-0 75.944 149.993853)">40</text>
     </g>
    </g>
    <g id="ytick_6">
     <g id="line2d_16">
      <path d="M 82.944 120.148885 
L 635.904 120.148885 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_17">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="120.148885" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_6">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="123.947713" transform="rotate(-0 75.944 123.947713)">50</text>
     </g>
    </g>
    <g id="text_7">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="57.819" y="177.072" transform="rotate(-90 57.819 177.072)">累计差额（百分点）</text>
    </g>
   </g>
   <g id="line2d_18">
    <path d="M 108.078545 250.379585 
L 112.344469 246.11822 
L 116.197561 247.655654 
L 120.463484 246.82734 
L 124.591797 251.253818 
L 128.857721 248.256909 
L 132.986034 247.027069 
L 137.251957 241.713862 
L 141.51788 242.787297 
L 145.646193 240.233747 
L 149.912117 240.497133 
L 154.04043 239.697903 
L 158.306353 236.200133 
L 162.572277 235.053421 
L 166.562979 236.108549 
L 170.828903 236.885874 
L 174.957216 243.872865 
L 179.223139 243.282266 
L 183.351452 237.296583 
L 187.617375 237.59548 
L 191.883299 242.188621 
L 196.011612 241.266086 
L 200.277535 244.293428 
L 204.405848 250.397217 
L 208.671771 250.957349 
L 212.937695 250.370226 
L 216.790787 250.700624 
L 221.05671 250.029982 
L 225.185023 249.08783 
L 229.450947 245.051691 
L 233.57926 247.555204 
L 237.845183 245.909136 
L 242.111106 242.308871 
L 246.239419 245.886982 
L 250.505343 241.169999 
L 254.633656 238.840026 
L 258.899579 240.576991 
L 263.165503 234.12833 
L 267.018595 228.402111 
L 271.284518 231.160448 
L 275.412831 230.494 
L 279.678754 225.971786 
L 283.807067 227.505975 
L 288.072991 228.70511 
L 292.338914 215.979138 
L 296.467227 213.676758 
L 300.733151 221.418379 
L 304.861464 224.653915 
L 309.127387 225.005795 
L 313.39331 230.816252 
L 317.246403 227.208461 
L 321.512326 220.864423 
L 325.640639 224.709849 
L 329.906562 218.632699 
L 334.034875 219.2615 
L 338.300799 218.976711 
L 342.566722 206.121164 
L 346.695035 212.527938 
L 350.960958 213.929829 
L 355.089271 217.8434 
L 359.355195 215.595182 
L 363.621118 207.220743 
L 367.611821 210.716339 
L 371.877744 197.397896 
L 376.006057 192.420054 
L 380.27198 188.347548 
L 384.400293 179.23714 
L 388.666217 164.650248 
L 392.93214 144.894742 
L 397.060453 149.878843 
L 401.326377 160.709265 
L 405.45469 172.087221 
L 409.720613 173.688323 
L 413.986536 176.452096 
L 417.839628 195.569066 
L 422.105552 201.642495 
L 426.233865 200.281294 
L 430.499788 205.184291 
L 434.628101 197.094865 
L 438.894025 194.966748 
L 443.159948 189.926514 
L 447.288261 196.955618 
L 451.554184 190.246303 
L 455.682497 183.678148 
L 459.948421 183.46583 
L 464.214344 196.292562 
L 468.067436 201.821295 
L 472.33336 190.51937 
L 476.461673 188.118339 
L 480.727596 192.470494 
L 484.855909 184.876019 
L 489.121832 186.039705 
L 493.387756 188.760913 
L 497.516069 190.350932 
L 501.781992 178.349278 
L 505.910305 173.65674 
L 510.176229 168.215716 
L 514.442152 189.034885 
L 518.295244 192.860907 
L 522.561167 184.800014 
L 526.68948 175.384592 
L 530.955404 167.8222 
L 535.083717 163.817245 
L 539.34964 170.765781 
L 543.615564 161.80145 
L 547.743877 170.891365 
L 552.0098 167.559233 
L 556.138113 157.194464 
L 560.404036 168.307939 
L 564.66996 155.878821 
L 568.660662 140.418805 
L 572.926586 142.546201 
L 577.054899 149.647377 
L 581.320822 125.082772 
L 585.449135 102.890182 
L 589.715058 122.506817 
L 593.980982 109.988573 
L 598.109295 107.372381 
L 602.375218 108.975018 
L 606.503531 113.513255 
L 610.769455 103.092423 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_19">
    <path d="M 82.944 250.379585 
L 635.904 250.379585 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #64748b; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_3">
    <path d="M 82.944 258.672 
L 82.944 95.472 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_4">
    <path d="M 82.944 258.672 
L 635.904 258.672 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_8">
    <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start; fill: #1d4ed8" x="615.769455" y="103.092423" transform="rotate(-0 615.769455 103.092423)">+56.5</text>
   </g>
   <g id="text_9">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="89.472" transform="rotate(-0 82.944 89.472)">盈利能力＋动量</text>
   </g>
  </g>
  <g id="axes_2">
   <g id="patch_5">
    <path d="M 82.944 470.832 
L 635.904 470.832 
L 635.904 307.632 
L 82.944 307.632 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_3">
    <g id="xtick_6">
     <g id="line2d_20">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_7">
     <g id="line2d_21">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_8">
     <g id="line2d_22">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_9">
     <g id="line2d_23">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_10">
     <g id="line2d_24">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_4">
    <g id="ytick_7">
     <g id="line2d_25">
      <path d="M 82.944 470.513204 
L 635.904 470.513204 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_26">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="470.513204" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_10">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="474.312033" transform="rotate(-0 75.944 474.312033)">−25</text>
     </g>
    </g>
    <g id="ytick_8">
     <g id="line2d_27">
      <path d="M 82.944 442.917636 
L 635.904 442.917636 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_28">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="442.917636" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_11">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="446.716465" transform="rotate(-0 75.944 446.716465)">−20</text>
     </g>
    </g>
    <g id="ytick_9">
     <g id="line2d_29">
      <path d="M 82.944 415.322068 
L 635.904 415.322068 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_30">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="415.322068" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_12">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="419.120897" transform="rotate(-0 75.944 419.120897)">−15</text>
     </g>
    </g>
    <g id="ytick_10">
     <g id="line2d_31">
      <path d="M 82.944 387.7265 
L 635.904 387.7265 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_32">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="387.7265" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_13">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="391.525329" transform="rotate(-0 75.944 391.525329)">−10</text>
     </g>
    </g>
    <g id="ytick_11">
     <g id="line2d_33">
      <path d="M 82.944 360.130932 
L 635.904 360.130932 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_34">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="360.130932" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_14">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="363.929761" transform="rotate(-0 75.944 363.929761)">−5</text>
     </g>
    </g>
    <g id="ytick_12">
     <g id="line2d_35">
      <path d="M 82.944 332.535364 
L 635.904 332.535364 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_36">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="332.535364" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_15">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="336.334193" transform="rotate(-0 75.944 336.334193)">0</text>
     </g>
    </g>
    <g id="text_16">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="49.439312" y="389.232" transform="rotate(-90 49.439312 389.232)">累计差额（百分点）</text>
    </g>
   </g>
   <g id="line2d_37">
    <path d="M 108.078545 332.535364 
L 112.344469 334.817886 
L 116.197561 338.805969 
L 120.463484 335.231816 
L 124.591797 344.06489 
L 128.857721 337.391914 
L 132.986034 332.64343 
L 137.251957 324.946978 
L 141.51788 328.922258 
L 145.646193 329.091128 
L 149.912117 335.00386 
L 154.04043 329.58202 
L 158.306353 326.051513 
L 162.572277 330.716116 
L 166.562979 340.96652 
L 170.828903 343.415149 
L 174.957216 345.124815 
L 179.223139 346.031095 
L 183.351452 341.598179 
L 187.617375 346.765221 
L 191.883299 346.196542 
L 196.011612 346.046338 
L 200.277535 342.710138 
L 204.405848 337.387034 
L 208.671771 334.47421 
L 212.937695 338.851799 
L 216.790787 340.472271 
L 221.05671 348.426391 
L 225.185023 353.573704 
L 229.450947 356.111077 
L 233.57926 349.205725 
L 237.845183 344.268996 
L 242.111106 343.12746 
L 246.239419 340.835978 
L 250.505343 330.620861 
L 254.633656 331.810021 
L 258.899579 335.264684 
L 263.165503 324.58252 
L 267.018595 315.050182 
L 271.284518 321.862864 
L 275.412831 318.62693 
L 279.678754 318.386586 
L 283.807067 328.904588 
L 288.072991 333.6305 
L 292.338914 322.405832 
L 296.467227 327.099471 
L 300.733151 334.502171 
L 304.861464 340.806822 
L 309.127387 343.925993 
L 313.39331 353.611587 
L 317.246403 357.48601 
L 321.512326 360.348724 
L 325.640639 362.846787 
L 329.906562 350.024688 
L 334.034875 357.88984 
L 338.300799 357.052828 
L 342.566722 347.655591 
L 346.695035 353.20809 
L 350.960958 361.381833 
L 355.089271 373.520956 
L 359.355195 372.080388 
L 363.621118 369.065239 
L 367.611821 373.861093 
L 371.877744 376.519223 
L 376.006057 386.495393 
L 380.27198 388.17907 
L 384.400293 383.060606 
L 388.666217 367.15787 
L 392.93214 356.076018 
L 397.060453 358.294633 
L 401.326377 360.256 
L 405.45469 385.53281 
L 409.720613 390.502009 
L 413.986536 379.364654 
L 417.839628 394.287495 
L 422.105552 415.460661 
L 426.233865 418.193864 
L 430.499788 411.879341 
L 434.628101 428.375027 
L 438.894025 454.408502 
L 443.159948 446.317416 
L 447.288261 420.266699 
L 451.554184 415.621692 
L 455.682497 433.34452 
L 459.948421 459.877824 
L 464.214344 432.817605 
L 468.067436 417.612511 
L 472.33336 409.630858 
L 476.461673 392.339819 
L 480.727596 374.085269 
L 484.855909 377.50494 
L 489.121832 393.139932 
L 493.387756 373.715943 
L 497.516069 354.923714 
L 501.781992 325.186019 
L 505.910305 342.666672 
L 510.176229 321.06485 
L 514.442152 371.481279 
L 518.295244 383.296856 
L 522.561167 432.463748 
L 526.68948 424.141452 
L 530.955404 445.305914 
L 535.083717 458.342766 
L 539.34964 462.466857 
L 543.615564 463.413818 
L 547.743877 458.614318 
L 552.0098 454.030997 
L 556.138113 439.351388 
L 560.404036 440.748507 
L 564.66996 437.928957 
L 568.660662 430.63661 
L 572.926586 423.387726 
L 577.054899 435.980795 
L 581.320822 423.320828 
L 585.449135 422.011044 
L 589.715058 440.919325 
L 593.980982 430.018647 
L 598.109295 444.575834 
L 602.375218 414.088184 
L 606.503531 395.303025 
L 610.769455 402.260235 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_38">
    <path d="M 82.944 332.535364 
L 635.904 332.535364 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #64748b; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_6">
    <path d="M 82.944 470.832 
L 82.944 307.632 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_7">
    <path d="M 82.944 470.832 
L 635.904 470.832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_17">
    <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start; fill: #1d4ed8" x="615.769455" y="402.260235" transform="rotate(-0 615.769455 402.260235)">-12.6</text>
   </g>
   <g id="text_18">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="301.632" transform="rotate(-0 82.944 301.632)">价值＋动量</text>
   </g>
  </g>
  <g id="axes_3">
   <g id="patch_8">
    <path d="M 82.944 682.992 
L 635.904 682.992 
L 635.904 519.792 
L 82.944 519.792 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_5">
    <g id="xtick_11">
     <g id="line2d_39">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_19">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="158.443964" y="697.589656" transform="rotate(-0 158.443964 697.589656)">2016</text>
     </g>
    </g>
    <g id="xtick_12">
     <g id="line2d_40">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_20">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="259.03719" y="697.589656" transform="rotate(-0 259.03719 697.589656)">2018</text>
     </g>
    </g>
    <g id="xtick_13">
     <g id="line2d_41">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_21">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="359.492805" y="697.589656" transform="rotate(-0 359.492805 697.589656)">2020</text>
     </g>
    </g>
    <g id="xtick_14">
     <g id="line2d_42">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_22">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="460.086031" y="697.589656" transform="rotate(-0 460.086031 697.589656)">2022</text>
     </g>
    </g>
    <g id="xtick_15">
     <g id="line2d_43">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_23">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="560.541647" y="697.589656" transform="rotate(-0 560.541647 697.589656)">2024</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_6">
    <g id="ytick_13">
     <g id="line2d_44">
      <path d="M 82.944 666.580076 
L 635.904 666.580076 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_45">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="666.580076" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_24">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="670.378904" transform="rotate(-0 75.944 670.378904)">0</text>
     </g>
    </g>
    <g id="ytick_14">
     <g id="line2d_46">
      <path d="M 82.944 633.420106 
L 635.904 633.420106 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_47">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="633.420106" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_25">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="637.218935" transform="rotate(-0 75.944 637.218935)">10</text>
     </g>
    </g>
    <g id="ytick_15">
     <g id="line2d_48">
      <path d="M 82.944 600.260137 
L 635.904 600.260137 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_49">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="600.260137" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_26">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="604.058965" transform="rotate(-0 75.944 604.058965)">20</text>
     </g>
    </g>
    <g id="ytick_16">
     <g id="line2d_50">
      <path d="M 82.944 567.100167 
L 635.904 567.100167 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_51">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="567.100167" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_27">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="570.898995" transform="rotate(-0 75.944 570.898995)">30</text>
     </g>
    </g>
    <g id="ytick_17">
     <g id="line2d_52">
      <path d="M 82.944 533.940197 
L 635.904 533.940197 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_53">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="533.940197" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_28">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="537.739025" transform="rotate(-0 75.944 537.739025)">40</text>
     </g>
    </g>
    <g id="text_29">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="57.819" y="601.392" transform="rotate(-90 57.819 601.392)">累计差额（百分点）</text>
    </g>
   </g>
   <g id="line2d_54">
    <path d="M 108.078545 666.580076 
L 112.344469 668.108143 
L 116.197561 669.653593 
L 120.463484 670.255592 
L 124.591797 669.126266 
L 128.857721 670.541126 
L 132.986034 670.436427 
L 137.251957 672.800931 
L 141.51788 672.512471 
L 145.646193 672.193361 
L 149.912117 673.803207 
L 154.04043 672.99216 
L 158.306353 673.894198 
L 162.572277 674.352789 
L 166.562979 674.152197 
L 170.828903 673.177756 
L 174.957216 672.895892 
L 179.223139 674.634561 
L 183.351452 675.573818 
L 187.617375 673.859724 
L 191.883299 672.139831 
L 196.011612 672.45935 
L 200.277535 671.046027 
L 204.405848 663.312504 
L 208.671771 661.011038 
L 212.937695 661.898664 
L 216.790787 659.867434 
L 221.05671 662.339184 
L 225.185023 664.001797 
L 229.450947 665.884884 
L 233.57926 663.208312 
L 237.845183 664.089704 
L 242.111106 664.977522 
L 246.239419 664.083332 
L 250.505343 662.93734 
L 254.633656 659.694399 
L 258.899579 657.297153 
L 263.165503 658.257118 
L 267.018595 657.606211 
L 271.284518 659.945206 
L 275.412831 660.733474 
L 279.678754 664.68981 
L 283.807067 666.607922 
L 288.072991 662.568529 
L 292.338914 662.094172 
L 296.467227 663.513701 
L 300.733151 661.461394 
L 304.861464 661.650654 
L 309.127387 664.635592 
L 313.39331 667.232046 
L 317.246403 668.912537 
L 321.512326 669.40178 
L 325.640639 665.508832 
L 329.906562 667.256168 
L 334.034875 666.529317 
L 338.300799 663.750796 
L 342.566722 664.769721 
L 346.695035 661.155918 
L 350.960958 658.146423 
L 355.089271 660.25362 
L 359.355195 655.592025 
L 363.621118 659.860542 
L 367.611821 662.119448 
L 371.877744 670.394601 
L 376.006057 667.892763 
L 380.27198 669.853339 
L 384.400293 662.850173 
L 388.666217 663.414891 
L 392.93214 654.863139 
L 397.060453 657.383328 
L 401.326377 663.543943 
L 405.45469 666.549845 
L 409.720613 668.211577 
L 413.986536 673.771434 
L 417.839628 673.32653 
L 422.105552 661.325613 
L 426.233865 660.426236 
L 430.499788 653.019597 
L 434.628101 656.964943 
L 438.894025 655.172762 
L 443.159948 655.396528 
L 447.288261 656.644905 
L 451.554184 654.404966 
L 455.682497 643.624811 
L 459.948421 631.902647 
L 464.214344 614.451253 
L 468.067436 619.813129 
L 472.33336 617.101081 
L 476.461673 606.836508 
L 480.727596 601.376334 
L 484.855909 606.975452 
L 489.121832 604.788965 
L 493.387756 610.576461 
L 497.516069 617.636113 
L 501.781992 598.09762 
L 505.910305 584.60878 
L 510.176229 586.385715 
L 514.442152 589.013349 
L 518.295244 591.940348 
L 522.561167 590.636011 
L 526.68948 579.155671 
L 530.955404 582.195274 
L 535.083717 576.358011 
L 539.34964 573.067906 
L 543.615564 575.809076 
L 547.743877 582.153396 
L 552.0098 584.668682 
L 556.138113 574.653576 
L 560.404036 565.514466 
L 564.66996 571.666901 
L 568.660662 576.720729 
L 572.926586 565.708712 
L 577.054899 572.96948 
L 581.320822 553.82663 
L 585.449135 543.0702 
L 589.715058 538.403514 
L 593.980982 527.210182 
L 598.109295 532.430537 
L 602.375218 536.499378 
L 606.503531 536.638447 
L 610.769455 532.565106 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_55">
    <path d="M 82.944 666.580076 
L 635.904 666.580076 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #64748b; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_9">
    <path d="M 82.944 682.992 
L 82.944 519.792 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_10">
    <path d="M 82.944 682.992 
L 635.904 682.992 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_30">
    <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start; fill: #1d4ed8" x="615.769455" y="532.565106" transform="rotate(-0 615.769455 532.565106)">+40.4</text>
   </g>
   <g id="text_31">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="513.792" transform="rotate(-0 82.944 513.792)">价值＋盈利能力</text>
   </g>
  </g>
  <g id="text_32">
   <text style="font-size: 17px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="76.032" y="24.2352" transform="rotate(-0 76.032 24.2352)">大规模美国股票：相对来源参照的累计收益差</text>
  </g>
  <g id="text_33">
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 36.7016)">2015—2024 · 起始各半，以后不调配 · 毛收益，个人净费用未评价</text>
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 47.0016)">参照是两种来源三组平均的组合，并非母指数；月末观察，全部已见历史</text>
  </g>
 </g>
 <defs>
  <clipPath id="p7311188120">
   <rect x="82.944" y="95.472" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pf527fceebe">
   <rect x="82.944" y="307.632" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pd228cd0829">
   <rect x="82.944" y="519.792" width="552.96" height="163.2"/>
  </clipPath>
 </defs>
</svg>




较小规模股票：三组相对差额

<svg xmlns:xlink="http://www.w3.org/1999/xlink" width="100%" style="max-width:100%;height:auto;display:block" viewBox="0 0 691.2 734.4" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-10-23T18:11:08.442550</dc:date>
    <dc:format>image/svg+xml</dc:format>
    <dc:creator>
     <cc:Agent>
      <dc:title>Matplotlib v3.11.2, https://matplotlib.org/</dc:title>
     </cc:Agent>
    </dc:creator>
   </cc:Work>
  </rdf:RDF>
 </metadata>
 <defs>
  <style type="text/css">*{stroke-linejoin: round; stroke-linecap: butt}</style>
 </defs>
 <g id="figure_1">
  <g id="patch_1">
   <path d="M 0 734.4 
L 691.2 734.4 
L 691.2 0 
L 0 0 
z
" style="fill: #f8fafc"/>
  </g>
  <g id="axes_1">
   <g id="patch_2">
    <path d="M 82.944 258.672 
L 635.904 258.672 
L 635.904 95.472 
L 82.944 95.472 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_1">
    <g id="xtick_1">
     <g id="line2d_1">
      <defs>
       <path id="m80ae50af5d" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_2">
     <g id="line2d_2">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_3">
     <g id="line2d_3">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_4">
     <g id="line2d_4">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_5">
     <g id="line2d_5">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_2">
    <g id="ytick_1">
     <g id="line2d_6">
      <path d="M 82.944 238.636959 
L 635.904 238.636959 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_7">
      <defs>
       <path id="m7712ef1b3c" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="238.636959" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_1">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="242.435787" transform="rotate(-0 75.944 242.435787)">0</text>
     </g>
    </g>
    <g id="ytick_2">
     <g id="line2d_8">
      <path d="M 82.944 208.859904 
L 635.904 208.859904 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_9">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="208.859904" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_2">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="212.658732" transform="rotate(-0 75.944 212.658732)">10</text>
     </g>
    </g>
    <g id="ytick_3">
     <g id="line2d_10">
      <path d="M 82.944 179.082849 
L 635.904 179.082849 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_11">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="179.082849" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_3">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="182.881677" transform="rotate(-0 75.944 182.881677)">20</text>
     </g>
    </g>
    <g id="ytick_4">
     <g id="line2d_12">
      <path d="M 82.944 149.305794 
L 635.904 149.305794 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_13">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="149.305794" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_4">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="153.104622" transform="rotate(-0 75.944 153.104622)">30</text>
     </g>
    </g>
    <g id="ytick_5">
     <g id="line2d_14">
      <path d="M 82.944 119.528739 
L 635.904 119.528739 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_15">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="119.528739" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_5">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="123.327567" transform="rotate(-0 75.944 123.327567)">40</text>
     </g>
    </g>
    <g id="text_6">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="57.819" y="177.072" transform="rotate(-90 57.819 177.072)">累计差额（百分点）</text>
    </g>
   </g>
   <g id="line2d_16">
    <path d="M 108.078545 238.636959 
L 112.344469 233.389448 
L 116.197561 235.487399 
L 120.463484 233.382061 
L 124.591797 238.427004 
L 128.857721 235.328551 
L 132.986034 232.94946 
L 137.251957 227.242896 
L 141.51788 230.650933 
L 145.646193 228.458979 
L 149.912117 229.99259 
L 154.04043 231.405177 
L 158.306353 231.558907 
L 162.572277 231.648981 
L 166.562979 233.666279 
L 170.828903 236.48467 
L 174.957216 239.757828 
L 179.223139 240.064471 
L 183.351452 238.110163 
L 187.617375 239.030607 
L 191.883299 241.804996 
L 196.011612 244.571737 
L 200.277535 242.712218 
L 204.405848 244.732522 
L 208.671771 246.38618 
L 212.937695 247.824261 
L 216.790787 249.952469 
L 221.05671 251.00227 
L 225.185023 249.485437 
L 229.450947 249.24633 
L 233.57926 251.253818 
L 237.845183 250.613066 
L 242.111106 248.658444 
L 246.239419 250.823519 
L 250.505343 247.173561 
L 254.633656 244.552611 
L 258.899579 240.219609 
L 263.165503 238.416566 
L 267.018595 237.011844 
L 271.284518 238.056473 
L 275.412831 241.122952 
L 279.678754 240.984047 
L 283.807067 239.062722 
L 288.072991 239.25587 
L 292.338914 237.162612 
L 296.467227 236.487196 
L 300.733151 239.185985 
L 304.861464 243.748723 
L 309.127387 241.840005 
L 313.39331 245.839453 
L 317.246403 247.63155 
L 321.512326 245.059788 
L 325.640639 245.739267 
L 329.906562 240.116207 
L 334.034875 239.992551 
L 338.300799 236.608462 
L 342.566722 233.61335 
L 346.695035 241.683593 
L 350.960958 239.421258 
L 355.089271 240.594683 
L 359.355195 243.978957 
L 363.621118 238.338942 
L 367.611821 237.768334 
L 371.877744 247.50045 
L 376.006057 243.868276 
L 380.27198 239.030811 
L 384.400293 237.823231 
L 388.666217 231.424181 
L 392.93214 229.4487 
L 397.060453 224.219427 
L 401.326377 227.650984 
L 405.45469 227.651869 
L 409.720613 228.83212 
L 413.986536 214.442738 
L 417.839628 215.501872 
L 422.105552 219.791666 
L 426.233865 210.620289 
L 430.499788 202.146895 
L 434.628101 199.013446 
L 438.894025 201.000902 
L 443.159948 198.08713 
L 447.288261 197.280201 
L 451.554184 190.674519 
L 455.682497 184.731727 
L 459.948421 183.068648 
L 464.214344 193.652898 
L 468.067436 187.666761 
L 472.33336 190.715062 
L 476.461673 182.83807 
L 480.727596 174.369641 
L 484.855909 189.230807 
L 489.121832 183.491997 
L 493.387756 186.593419 
L 497.516069 192.176625 
L 501.781992 175.785874 
L 505.910305 166.575551 
L 510.176229 169.673519 
L 514.442152 180.140007 
L 518.295244 177.1102 
L 522.561167 175.832341 
L 526.68948 171.160355 
L 530.955404 173.292631 
L 535.083717 167.651109 
L 539.34964 170.159137 
L 543.615564 163.621789 
L 547.743877 162.025902 
L 552.0098 165.672749 
L 556.138113 158.705559 
L 560.404036 158.855888 
L 564.66996 152.262675 
L 568.660662 139.058151 
L 572.926586 130.657249 
L 577.054899 138.516721 
L 581.320822 133.853172 
L 585.449135 147.247151 
L 589.715058 133.593722 
L 593.980982 125.358096 
L 598.109295 122.597332 
L 602.375218 119.493179 
L 606.503531 102.890182 
L 610.769455 123.816106 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_17">
    <path d="M 82.944 238.636959 
L 635.904 238.636959 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #64748b; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_3">
    <path d="M 82.944 258.672 
L 82.944 95.472 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_4">
    <path d="M 82.944 258.672 
L 635.904 258.672 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_7">
    <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start; fill: #1d4ed8" x="615.769455" y="123.816106" transform="rotate(-0 615.769455 123.816106)">+38.6</text>
   </g>
   <g id="text_8">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="89.472" transform="rotate(-0 82.944 89.472)">盈利能力＋动量</text>
   </g>
  </g>
  <g id="axes_2">
   <g id="patch_5">
    <path d="M 82.944 470.832 
L 635.904 470.832 
L 635.904 307.632 
L 82.944 307.632 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_3">
    <g id="xtick_6">
     <g id="line2d_18">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_7">
     <g id="line2d_19">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_8">
     <g id="line2d_20">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_9">
     <g id="line2d_21">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_10">
     <g id="line2d_22">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_4">
    <g id="ytick_6">
     <g id="line2d_23">
      <path d="M 82.944 462.318049 
L 635.904 462.318049 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_24">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="462.318049" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_9">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="466.116877" transform="rotate(-0 75.944 466.116877)">−10</text>
     </g>
    </g>
    <g id="ytick_7">
     <g id="line2d_25">
      <path d="M 82.944 429.38868 
L 635.904 429.38868 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_26">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="429.38868" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_10">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="433.187509" transform="rotate(-0 75.944 433.187509)">0</text>
     </g>
    </g>
    <g id="ytick_8">
     <g id="line2d_27">
      <path d="M 82.944 396.459312 
L 635.904 396.459312 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_28">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="396.459312" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_11">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="400.25814" transform="rotate(-0 75.944 400.25814)">10</text>
     </g>
    </g>
    <g id="ytick_9">
     <g id="line2d_29">
      <path d="M 82.944 363.529943 
L 635.904 363.529943 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_30">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="363.529943" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_12">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="367.328772" transform="rotate(-0 75.944 367.328772)">20</text>
     </g>
    </g>
    <g id="ytick_10">
     <g id="line2d_31">
      <path d="M 82.944 330.600575 
L 635.904 330.600575 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_32">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="330.600575" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_13">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="334.399403" transform="rotate(-0 75.944 334.399403)">30</text>
     </g>
    </g>
    <g id="text_14">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="49.439312" y="389.232" transform="rotate(-90 49.439312 389.232)">累计差额（百分点）</text>
    </g>
   </g>
   <g id="line2d_33">
    <path d="M 108.078545 429.38868 
L 112.344469 426.294417 
L 116.197561 430.466298 
L 120.463484 429.076466 
L 124.591797 432.362393 
L 128.857721 429.483055 
L 132.986034 428.023248 
L 137.251957 426.543985 
L 141.51788 425.406979 
L 145.646193 420.360222 
L 149.912117 423.076079 
L 154.04043 422.075801 
L 158.306353 424.372774 
L 162.572277 420.192178 
L 166.562979 423.937123 
L 170.828903 427.264513 
L 174.957216 427.757847 
L 179.223139 428.15695 
L 183.351452 425.861777 
L 187.617375 428.204105 
L 191.883299 429.460692 
L 196.011612 430.240134 
L 200.277535 425.2011 
L 204.405848 422.35348 
L 208.671771 420.130421 
L 212.937695 422.422436 
L 216.790787 425.869278 
L 221.05671 430.192856 
L 225.185023 431.632591 
L 229.450947 435.022323 
L 233.57926 435.195073 
L 237.845183 433.923006 
L 242.111106 432.814604 
L 246.239419 432.039587 
L 250.505343 428.260276 
L 254.633656 429.076328 
L 258.899579 427.758741 
L 263.165503 426.663115 
L 267.018595 425.952743 
L 271.284518 425.870904 
L 275.412831 424.484569 
L 279.678754 421.45836 
L 283.807067 423.313365 
L 288.072991 424.936443 
L 292.338914 422.354445 
L 296.467227 423.572733 
L 300.733151 421.65338 
L 304.861464 424.146744 
L 309.127387 423.077348 
L 313.39331 429.749991 
L 317.246403 433.000404 
L 321.512326 433.608952 
L 325.640639 437.051554 
L 329.906562 431.994177 
L 334.034875 434.606673 
L 338.300799 429.474554 
L 342.566722 427.473042 
L 346.695035 431.740701 
L 350.960958 432.870986 
L 355.089271 436.076576 
L 359.355195 437.155661 
L 363.621118 437.208553 
L 367.611821 436.858628 
L 371.877744 443.006282 
L 376.006057 445.531533 
L 380.27198 450.013847 
L 384.400293 449.774546 
L 388.666217 444.361436 
L 392.93214 449.014269 
L 397.060453 446.32648 
L 401.326377 445.508773 
L 405.45469 456.616404 
L 409.720613 463.413818 
L 413.986536 436.339524 
L 417.839628 444.534259 
L 422.105552 443.430157 
L 426.233865 444.083674 
L 430.499788 428.422114 
L 434.628101 428.326244 
L 438.894025 434.871322 
L 443.159948 429.729633 
L 447.288261 418.006908 
L 451.554184 411.566527 
L 455.682497 408.879363 
L 459.948421 407.196685 
L 464.214344 394.001685 
L 468.067436 385.150288 
L 472.33336 384.209985 
L 476.461673 366.091367 
L 480.727596 347.652668 
L 484.855909 374.825351 
L 489.121832 380.20743 
L 493.387756 379.455718 
L 497.516069 380.180225 
L 501.781992 356.71878 
L 505.910305 352.464204 
L 510.176229 352.334881 
L 514.442152 376.003884 
L 518.295244 373.59535 
L 522.561167 384.883177 
L 526.68948 383.680297 
L 530.955404 389.479705 
L 535.083717 389.440642 
L 539.34964 388.291884 
L 543.615564 381.774883 
L 547.743877 385.8564 
L 552.0098 388.211901 
L 556.138113 376.641321 
L 560.404036 368.386331 
L 564.66996 364.047539 
L 568.660662 356.727481 
L 572.926586 346.979165 
L 577.054899 348.956316 
L 581.320822 349.463928 
L 585.449135 355.18765 
L 589.715058 335.5532 
L 593.980982 328.788413 
L 598.109295 332.575051 
L 602.375218 326.359821 
L 606.503531 315.050182 
L 610.769455 331.304878 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_34">
    <path d="M 82.944 429.38868 
L 635.904 429.38868 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #64748b; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_6">
    <path d="M 82.944 470.832 
L 82.944 307.632 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_7">
    <path d="M 82.944 470.832 
L 635.904 470.832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_15">
    <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start; fill: #1d4ed8" x="615.769455" y="331.304878" transform="rotate(-0 615.769455 331.304878)">+29.8</text>
   </g>
   <g id="text_16">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="301.632" transform="rotate(-0 82.944 301.632)">价值＋动量</text>
   </g>
  </g>
  <g id="axes_3">
   <g id="patch_8">
    <path d="M 82.944 682.992 
L 635.904 682.992 
L 635.904 519.792 
L 82.944 519.792 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_5">
    <g id="xtick_11">
     <g id="line2d_35">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_17">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="158.443964" y="697.589656" transform="rotate(-0 158.443964 697.589656)">2016</text>
     </g>
    </g>
    <g id="xtick_12">
     <g id="line2d_36">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_18">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="259.03719" y="697.589656" transform="rotate(-0 259.03719 697.589656)">2018</text>
     </g>
    </g>
    <g id="xtick_13">
     <g id="line2d_37">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_19">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="359.492805" y="697.589656" transform="rotate(-0 359.492805 697.589656)">2020</text>
     </g>
    </g>
    <g id="xtick_14">
     <g id="line2d_38">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_20">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="460.086031" y="697.589656" transform="rotate(-0 460.086031 697.589656)">2022</text>
     </g>
    </g>
    <g id="xtick_15">
     <g id="line2d_39">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_21">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="560.541647" y="697.589656" transform="rotate(-0 560.541647 697.589656)">2024</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_6">
    <g id="ytick_11">
     <g id="line2d_40">
      <path d="M 82.944 675.995132 
L 635.904 675.995132 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_41">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="675.995132" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_22">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="679.79396" transform="rotate(-0 75.944 679.79396)">−30</text>
     </g>
    </g>
    <g id="ytick_12">
     <g id="line2d_42">
      <path d="M 82.944 653.720903 
L 635.904 653.720903 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_43">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="653.720903" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_23">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="657.519731" transform="rotate(-0 75.944 657.519731)">−25</text>
     </g>
    </g>
    <g id="ytick_13">
     <g id="line2d_44">
      <path d="M 82.944 631.446674 
L 635.904 631.446674 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_45">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="631.446674" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_24">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="635.245502" transform="rotate(-0 75.944 635.245502)">−20</text>
     </g>
    </g>
    <g id="ytick_14">
     <g id="line2d_46">
      <path d="M 82.944 609.172445 
L 635.904 609.172445 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_47">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="609.172445" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_25">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="612.971273" transform="rotate(-0 75.944 612.971273)">−15</text>
     </g>
    </g>
    <g id="ytick_15">
     <g id="line2d_48">
      <path d="M 82.944 586.898215 
L 635.904 586.898215 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_49">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="586.898215" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_26">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="590.697044" transform="rotate(-0 75.944 590.697044)">−10</text>
     </g>
    </g>
    <g id="ytick_16">
     <g id="line2d_50">
      <path d="M 82.944 564.623986 
L 635.904 564.623986 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_51">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="564.623986" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_27">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="568.422814" transform="rotate(-0 75.944 568.422814)">−5</text>
     </g>
    </g>
    <g id="ytick_17">
     <g id="line2d_52">
      <path d="M 82.944 542.349757 
L 635.904 542.349757 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_53">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="542.349757" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_28">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="546.148585" transform="rotate(-0 75.944 546.148585)">0</text>
     </g>
    </g>
    <g id="ytick_18">
     <g id="line2d_54">
      <path d="M 82.944 520.075528 
L 635.904 520.075528 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_55">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="520.075528" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_29">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="523.874356" transform="rotate(-0 75.944 523.874356)">5</text>
     </g>
    </g>
    <g id="text_30">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="49.439312" y="601.392" transform="rotate(-90 49.439312 601.392)">累计差额（百分点）</text>
    </g>
   </g>
   <g id="line2d_56">
    <path d="M 108.078545 542.349757 
L 112.344469 542.563887 
L 116.197561 546.320353 
L 120.463484 547.429809 
L 124.591797 544.464267 
L 128.857721 549.304877 
L 132.986034 550.497372 
L 137.251957 556.717335 
L 141.51788 551.251865 
L 145.646193 549.693842 
L 149.912117 548.900644 
L 154.04043 555.288975 
L 158.306353 558.622682 
L 162.572277 551.995141 
L 166.562979 549.340347 
L 170.828903 547.890787 
L 174.957216 547.113464 
L 179.223139 550.539018 
L 183.351452 550.618176 
L 187.617375 550.731317 
L 191.883299 549.55775 
L 196.011612 554.489145 
L 200.277535 546.789928 
L 204.405848 539.906412 
L 208.671771 533.628947 
L 212.937695 538.397725 
L 216.790787 543.10286 
L 221.05671 545.52571 
L 225.185023 544.657225 
L 229.450947 549.289907 
L 233.57926 554.050957 
L 237.845183 554.914647 
L 242.111106 557.403474 
L 246.239419 556.793727 
L 250.505343 554.187891 
L 254.633656 549.446703 
L 258.899579 544.994888 
L 263.165503 549.001173 
L 267.018595 549.25847 
L 271.284518 548.147793 
L 275.412831 549.802707 
L 279.678754 561.549988 
L 283.807067 560.349778 
L 288.072991 561.760079 
L 292.338914 572.111254 
L 296.467227 571.381922 
L 300.733151 561.704707 
L 304.861464 567.635446 
L 309.127387 567.712563 
L 313.39331 567.834635 
L 317.246403 575.131126 
L 321.512326 580.148077 
L 325.640639 577.411319 
L 329.906562 581.929507 
L 334.034875 587.100361 
L 338.300799 590.777264 
L 342.566722 597.642643 
L 346.695035 588.336822 
L 350.960958 594.828127 
L 355.089271 599.086783 
L 359.355195 600.354091 
L 363.621118 609.626293 
L 367.611821 612.061681 
L 371.877744 626.091252 
L 376.006057 630.923033 
L 380.27198 635.612515 
L 384.400293 639.824328 
L 388.666217 640.019937 
L 392.93214 639.834481 
L 397.060453 641.432727 
L 401.326377 638.080806 
L 405.45469 652.585406 
L 409.720613 669.249524 
L 413.986536 675.573818 
L 417.839628 672.503878 
L 422.105552 649.860347 
L 426.233865 642.573551 
L 430.499788 620.931538 
L 434.628101 643.803985 
L 438.894025 631.640997 
L 443.159948 633.803858 
L 447.288261 620.149257 
L 451.554184 621.933034 
L 455.682497 608.287632 
L 459.948421 597.826137 
L 464.214344 562.501255 
L 468.067436 556.868514 
L 472.33336 568.948547 
L 476.461673 545.75631 
L 480.727596 527.210182 
L 484.855909 548.521079 
L 489.121832 550.985598 
L 493.387756 564.515334 
L 497.516069 569.757621 
L 501.781992 554.148254 
L 505.910305 537.50596 
L 510.176229 537.257566 
L 514.442152 544.478228 
L 518.295244 541.886149 
L 522.561167 558.988302 
L 526.68948 557.308486 
L 530.955404 580.627316 
L 535.083717 576.452428 
L 539.34964 569.205358 
L 543.615564 556.710581 
L 547.743877 543.623602 
L 552.0098 534.40442 
L 556.138113 538.879645 
L 560.404036 538.953812 
L 564.66996 539.395938 
L 568.660662 551.68185 
L 572.926586 543.645496 
L 577.054899 541.991185 
L 581.320822 541.8669 
L 585.449135 553.752781 
L 589.715058 541.762941 
L 593.980982 546.300043 
L 598.109295 547.01678 
L 602.375218 551.815193 
L 606.503531 557.305645 
L 610.769455 557.065081 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_57">
    <path d="M 82.944 542.349757 
L 635.904 542.349757 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #64748b; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_9">
    <path d="M 82.944 682.992 
L 82.944 519.792 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_10">
    <path d="M 82.944 682.992 
L 635.904 682.992 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_31">
    <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start; fill: #1d4ed8" x="615.769455" y="557.065081" transform="rotate(-0 615.769455 557.065081)">-3.3</text>
   </g>
   <g id="text_32">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="513.792" transform="rotate(-0 82.944 513.792)">价值＋盈利能力</text>
   </g>
  </g>
  <g id="text_33">
   <text style="font-size: 17px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="76.032" y="24.2352" transform="rotate(-0 76.032 24.2352)">较小规模美国股票：相对来源参照的累计收益差</text>
  </g>
  <g id="text_34">
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 36.7016)">2015—2024 · 起始各半，以后不调配 · 毛收益，个人净费用未评价</text>
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 47.0016)">参照是两种来源三组平均的组合，并非母指数；月末观察，全部已见历史</text>
  </g>
 </g>
 <defs>
  <clipPath id="p7311188120">
   <rect x="82.944" y="95.472" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pf527fceebe">
   <rect x="82.944" y="307.632" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pd228cd0829">
   <rect x="82.944" y="519.792" width="552.96" height="163.2"/>
  </clipPath>
 </defs>
</svg>




大规模股票：组合、来源参照和单项资金路径

<svg xmlns:xlink="http://www.w3.org/1999/xlink" width="100%" style="max-width:100%;height:auto;display:block" viewBox="0 0 691.2 734.4" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-10-23T18:11:08.291667</dc:date>
    <dc:format>image/svg+xml</dc:format>
    <dc:creator>
     <cc:Agent>
      <dc:title>Matplotlib v3.11.2, https://matplotlib.org/</dc:title>
     </cc:Agent>
    </dc:creator>
   </cc:Work>
  </rdf:RDF>
 </metadata>
 <defs>
  <style type="text/css">*{stroke-linejoin: round; stroke-linecap: butt}</style>
 </defs>
 <g id="figure_1">
  <g id="patch_1">
   <path d="M 0 734.4 
L 691.2 734.4 
L 691.2 0 
L 0 0 
z
" style="fill: #f8fafc"/>
  </g>
  <g id="axes_1">
   <g id="patch_2">
    <path d="M 82.944 258.672 
L 635.904 258.672 
L 635.904 95.472 
L 82.944 95.472 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_1">
    <g id="xtick_1">
     <g id="line2d_1">
      <defs>
       <path id="m80ae50af5d" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_2">
     <g id="line2d_2">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_3">
     <g id="line2d_3">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_4">
     <g id="line2d_4">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_5">
     <g id="line2d_5">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_2">
    <g id="ytick_1">
     <g id="line2d_6">
      <path d="M 82.944 247.860737 
L 635.904 247.860737 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_7">
      <defs>
       <path id="m7712ef1b3c" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="247.860737" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_1">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="251.659565" transform="rotate(-0 75.944 251.659565)">100</text>
     </g>
    </g>
    <g id="ytick_2">
     <g id="line2d_8">
      <path d="M 82.944 225.856328 
L 635.904 225.856328 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_9">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="225.856328" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_2">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="229.655156" transform="rotate(-0 75.944 229.655156)">150</text>
     </g>
    </g>
    <g id="ytick_3">
     <g id="line2d_10">
      <path d="M 82.944 203.851919 
L 635.904 203.851919 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_11">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="203.851919" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_3">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="207.650747" transform="rotate(-0 75.944 207.650747)">200</text>
     </g>
    </g>
    <g id="ytick_4">
     <g id="line2d_12">
      <path d="M 82.944 181.84751 
L 635.904 181.84751 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_13">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="181.84751" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_4">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="185.646338" transform="rotate(-0 75.944 185.646338)">250</text>
     </g>
    </g>
    <g id="ytick_5">
     <g id="line2d_14">
      <path d="M 82.944 159.843101 
L 635.904 159.843101 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_15">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="159.843101" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_5">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="163.641929" transform="rotate(-0 75.944 163.641929)">300</text>
     </g>
    </g>
    <g id="ytick_6">
     <g id="line2d_16">
      <path d="M 82.944 137.838691 
L 635.904 137.838691 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_17">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="137.838691" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_6">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="141.637519" transform="rotate(-0 75.944 141.637519)">350</text>
     </g>
    </g>
    <g id="ytick_7">
     <g id="line2d_18">
      <path d="M 82.944 115.834282 
L 635.904 115.834282 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_19">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="115.834282" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_7">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="119.63311" transform="rotate(-0 75.944 119.63311)">400</text>
     </g>
    </g>
    <g id="text_8">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="51.4565" y="177.072" transform="rotate(-90 51.4565 177.072)">初始资金100</text>
    </g>
   </g>
   <g id="line2d_20">
    <path d="M 108.078545 247.860737 
L 112.344469 248.562766 
L 116.197561 246.064322 
L 120.463484 246.625571 
L 124.591797 246.684133 
L 128.857721 245.752566 
L 132.986034 246.452617 
L 137.251957 245.236837 
L 141.51788 248.083067 
L 145.646193 249.074785 
L 149.912117 245.913498 
L 154.04043 245.708137 
L 158.306353 246.280896 
L 162.572277 248.621908 
L 166.562979 248.842515 
L 170.828903 246.042907 
L 174.957216 246.357711 
L 179.223139 245.468971 
L 183.351452 244.782458 
L 187.617375 242.964556 
L 191.883299 243.341493 
L 196.011612 243.145901 
L 200.277535 244.459404 
L 204.405848 243.175116 
L 208.671771 242.464183 
L 212.937695 241.383144 
L 216.790787 239.699483 
L 221.05671 239.603448 
L 225.185023 238.953685 
L 229.450947 237.668284 
L 233.57926 237.663661 
L 237.845183 236.22596 
L 242.111106 235.612619 
L 246.239419 234.761448 
L 250.505343 232.798948 
L 254.633656 230.503025 
L 258.899579 229.889231 
L 263.165503 225.459767 
L 267.018595 227.102298 
L 271.284518 228.856605 
L 275.412831 228.523611 
L 279.678754 226.459918 
L 283.807067 226.222968 
L 288.072991 224.336972 
L 292.338914 220.054713 
L 296.467227 219.472824 
L 300.733151 225.532187 
L 304.861464 225.031831 
L 309.127387 230.836245 
L 313.39331 226.352156 
L 317.246403 223.706432 
L 321.512326 221.920064 
L 325.640639 219.613967 
L 329.906562 223.857723 
L 334.034875 219.102899 
L 338.300799 218.145159 
L 342.566722 218.309149 
L 346.695035 217.916872 
L 350.960958 216.559674 
L 355.089271 214.165088 
L 359.355195 211.661682 
L 363.621118 210.438404 
L 367.611821 216.801673 
L 371.877744 224.855852 
L 376.006057 215.863163 
L 380.27198 211.736177 
L 384.400293 208.613445 
L 388.666217 203.035714 
L 392.93214 194.82022 
L 397.060453 198.751301 
L 401.326377 201.71591 
L 405.45469 192.517893 
L 409.720613 188.545501 
L 413.986536 189.156322 
L 417.839628 188.679095 
L 422.105552 186.676202 
L 426.233865 181.423078 
L 430.499788 182.168806 
L 434.628101 178.264005 
L 438.894025 176.839325 
L 443.159948 172.662494 
L 447.288261 178.233512 
L 451.554184 170.161316 
L 455.682497 171.859205 
L 459.948421 168.766912 
L 464.214344 176.907599 
L 468.067436 179.838645 
L 472.33336 175.07458 
L 476.461673 185.174508 
L 480.727596 186.222879 
L 484.855909 193.655326 
L 489.121832 184.974455 
L 493.387756 188.4976 
L 497.516069 197.42319 
L 501.781992 188.797976 
L 505.910305 183.612651 
L 510.176229 188.799341 
L 514.442152 185.248329 
L 518.295244 188.040196 
L 522.561167 183.912974 
L 526.68948 181.675438 
L 530.955404 178.932739 
L 535.083717 171.016907 
L 539.34964 168.012959 
L 543.615564 169.136505 
L 547.743877 175.645618 
L 552.0098 177.935645 
L 556.138113 166.677902 
L 560.404036 162.021948 
L 564.66996 159.041078 
L 568.660662 150.491149 
L 572.926586 146.498958 
L 577.054899 152.76977 
L 581.320822 143.578011 
L 585.449135 135.938975 
L 589.715058 137.035909 
L 593.980982 132.979464 
L 598.109295 129.262535 
L 602.375218 130.238753 
L 606.503531 121.022792 
L 610.769455 124.522235 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_21">
    <path d="M 108.078545 247.860737 
L 112.344469 249.282787 
L 116.197561 246.524571 
L 120.463484 247.225775 
L 124.591797 246.536418 
L 128.857721 246.111224 
L 132.986034 247.019075 
L 137.251957 246.70104 
L 141.51788 249.365897 
L 145.646193 250.789075 
L 149.912117 247.583285 
L 154.04043 247.512966 
L 158.306353 248.676725 
L 162.572277 251.211491 
L 166.562979 251.253818 
L 170.828903 248.32287 
L 174.957216 247.457118 
L 179.223139 246.668168 
L 183.351452 246.993025 
L 187.617375 245.124621 
L 191.883299 244.725478 
L 196.011612 244.685762 
L 200.277535 245.487751 
L 204.405848 243.172137 
L 208.671771 242.366562 
L 212.937695 241.384726 
L 216.790787 239.645238 
L 221.05671 239.662519 
L 225.185023 239.171947 
L 229.450947 238.568511 
L 233.57926 238.140882 
L 237.845183 236.981308 
L 242.111106 236.976286 
L 246.239419 235.52054 
L 250.505343 234.355045 
L 254.633656 232.452805 
L 258.899579 231.545525 
L 263.165503 228.205658 
L 267.018595 230.815719 
L 271.284518 232.103964 
L 275.412831 231.883576 
L 279.678754 230.583978 
L 283.807067 230.087804 
L 288.072991 227.999197 
L 292.338914 225.867179 
L 296.467227 225.674311 
L 300.733151 230.425613 
L 304.861464 229.378565 
L 309.127387 235.123523 
L 313.39331 229.657671 
L 317.246403 227.621537 
L 321.512326 226.907089 
L 325.640639 223.95125 
L 329.906562 229.22183 
L 334.034875 224.360761 
L 338.300799 223.451141 
L 342.566722 225.787266 
L 346.695035 224.31247 
L 350.960958 222.718401 
L 355.089271 219.66256 
L 359.355195 217.539023 
L 363.621118 217.730731 
L 367.611821 223.503367 
L 371.877744 233.807895 
L 376.006057 225.656286 
L 380.27198 222.21741 
L 384.400293 220.634017 
L 388.666217 217.520957 
L 392.93214 212.643449 
L 397.060453 215.732392 
L 401.326377 216.867042 
L 405.45469 205.74655 
L 409.720613 201.503628 
L 413.986536 201.647468 
L 417.839628 197.940146 
L 422.105552 194.911057 
L 426.233865 189.887928 
L 430.499788 189.805222 
L 434.628101 187.267249 
L 438.894025 186.202146 
L 443.159948 182.876937 
L 447.288261 187.260284 
L 451.554184 180.321726 
L 455.682497 183.129403 
L 459.948421 180.072984 
L 464.214344 186.046404 
L 468.067436 188.043289 
L 472.33336 185.188852 
L 476.461673 195.694469 
L 480.727596 196.00748 
L 484.855909 204.723125 
L 489.121832 195.845632 
L 493.387756 198.908988 
L 497.516069 207.565922 
L 501.781992 200.968565 
L 505.910305 196.576114 
L 510.176229 202.682146 
L 514.442152 195.613426 
L 518.295244 197.75883 
L 522.561167 194.993616 
L 526.68948 194.346955 
L 530.955404 192.882034 
L 535.083717 185.642898 
L 539.34964 181.464893 
L 543.615564 184.103096 
L 547.743877 189.076333 
L 552.0098 191.929372 
L 556.138113 182.422911 
L 560.404036 175.88917 
L 564.66996 175.008385 
L 568.660662 169.070654 
L 572.926586 164.719008 
L 577.054899 169.789971 
L 581.320822 164.748766 
L 585.449135 160.859498 
L 589.715058 158.64191 
L 593.980982 156.700608 
L 598.109295 153.425724 
L 602.375218 154.131152 
L 606.503531 144.148389 
L 610.769455 149.408587 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_22">
    <path d="M 108.078545 247.860737 
L 112.344469 248.639869 
L 116.197561 246.042111 
L 120.463484 246.880753 
L 124.591797 246.374539 
L 128.857721 245.947432 
L 132.986034 246.907572 
L 137.251957 246.090703 
L 141.51788 248.734523 
L 145.646193 249.62923 
L 149.912117 246.198048 
L 154.04043 246.143379 
L 158.306353 247.032616 
L 162.572277 249.216893 
L 166.562979 248.768101 
L 170.828903 245.746043 
L 174.957216 246.12979 
L 179.223139 245.33497 
L 183.351452 245.09085 
L 187.617375 242.905349 
L 191.883299 243.121918 
L 196.011612 242.909475 
L 200.277535 244.246722 
L 204.405848 242.376669 
L 208.671771 241.553503 
L 212.937695 240.283727 
L 216.790787 238.249853 
L 221.05671 237.870118 
L 225.185023 237.0456 
L 229.450947 235.897916 
L 233.57926 236.030233 
L 237.845183 235.026409 
L 242.111106 234.561944 
L 246.239419 233.726342 
L 250.505343 232.23491 
L 254.633656 229.567929 
L 258.899579 228.503506 
L 263.165503 224.807238 
L 267.018595 226.967851 
L 271.284518 228.595651 
L 275.412831 228.412853 
L 279.678754 226.738992 
L 283.807067 226.028613 
L 288.072991 223.382399 
L 292.338914 219.924414 
L 296.467227 219.276764 
L 300.733151 224.688049 
L 304.861464 223.615294 
L 309.127387 229.630611 
L 313.39331 225.167456 
L 317.246403 222.455749 
L 321.512326 220.589281 
L 325.640639 217.706279 
L 329.906562 222.66936 
L 334.034875 217.476508 
L 338.300799 216.151493 
L 342.566722 216.630107 
L 346.695035 215.730544 
L 350.960958 213.561572 
L 355.089271 210.6742 
L 359.355195 207.86411 
L 363.621118 206.938118 
L 367.611821 213.492532 
L 371.877744 221.506504 
L 376.006057 211.631965 
L 380.27198 207.354338 
L 384.400293 203.805629 
L 388.666217 198.416116 
L 392.93214 189.699153 
L 397.060453 193.617593 
L 401.326377 197.241616 
L 405.45469 187.499197 
L 409.720613 183.374898 
L 413.986536 185.352321 
L 417.839628 184.081358 
L 422.105552 179.602327 
L 426.233865 173.864686 
L 430.499788 173.895131 
L 434.628101 169.402193 
L 438.894025 165.903423 
L 443.159948 162.629563 
L 447.288261 170.201605 
L 451.554184 162.421061 
L 455.682497 161.759579 
L 459.948421 155.564003 
L 464.214344 163.602895 
L 468.067436 168.051953 
L 472.33336 163.185178 
L 476.461673 173.14625 
L 480.727596 174.873792 
L 484.855909 182.751234 
L 489.121832 172.976742 
L 493.387756 178.457225 
L 497.516069 189.429868 
L 501.781992 180.755583 
L 505.910305 173.131275 
L 510.176229 180.20962 
L 514.442152 173.400486 
L 518.295244 175.534469 
L 522.561167 167.937556 
L 526.68948 165.440078 
L 530.955404 162.266066 
L 535.083717 153.491002 
L 539.34964 149.942284 
L 543.615564 150.930524 
L 547.743877 158.252025 
L 552.0098 160.944418 
L 556.138113 149.402843 
L 560.404036 144.170184 
L 564.66996 141.377927 
L 568.660662 133.399162 
L 572.926586 129.0688 
L 577.054899 135.494871 
L 581.320822 125.163978 
L 585.449135 116.96423 
L 589.715058 116.39159 
L 593.980982 111.445568 
L 598.109295 107.418144 
L 602.375218 111.158265 
L 606.503531 102.890182 
L 610.769455 105.002215 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_23">
    <path d="M 108.078545 247.860737 
L 112.344469 248.485662 
L 116.197561 246.086533 
L 120.463484 246.370388 
L 124.591797 246.993727 
L 128.857721 245.5577 
L 132.986034 245.997663 
L 137.251957 244.382972 
L 141.51788 247.431611 
L 145.646193 248.52034 
L 149.912117 245.628948 
L 154.04043 245.272895 
L 158.306353 245.529177 
L 162.572277 248.026923 
L 166.562979 248.916928 
L 170.828903 246.339771 
L 174.957216 246.585632 
L 179.223139 245.602971 
L 183.351452 244.474066 
L 187.617375 243.023764 
L 191.883299 243.561068 
L 196.011612 243.382326 
L 200.277535 244.672086 
L 204.405848 243.973564 
L 208.671771 243.374864 
L 212.937695 242.482562 
L 216.790787 241.149113 
L 221.05671 241.336779 
L 225.185023 240.86177 
L 229.450947 239.438653 
L 233.57926 239.29709 
L 237.845183 237.42551 
L 242.111106 236.663293 
L 246.239419 235.796555 
L 250.505343 233.362987 
L 254.633656 231.438121 
L 258.899579 231.274956 
L 263.165503 226.112296 
L 267.018595 227.236745 
L 271.284518 229.11756 
L 275.412831 228.634369 
L 279.678754 226.180844 
L 283.807067 226.417324 
L 288.072991 225.291545 
L 292.338914 220.185012 
L 296.467227 219.668883 
L 300.733151 226.376326 
L 304.861464 226.448368 
L 309.127387 232.04188 
L 313.39331 227.536856 
L 317.246403 224.957114 
L 321.512326 223.250847 
L 325.640639 221.521656 
L 329.906562 225.046085 
L 334.034875 220.729289 
L 338.300799 220.138825 
L 342.566722 219.988191 
L 346.695035 220.103201 
L 350.960958 219.557776 
L 355.089271 217.655977 
L 359.355195 215.459255 
L 363.621118 213.93869 
L 367.611821 220.110814 
L 371.877744 228.2052 
L 376.006057 220.094361 
L 380.27198 216.118016 
L 384.400293 213.421261 
L 388.666217 207.655311 
L 392.93214 199.941286 
L 397.060453 203.885009 
L 401.326377 206.190204 
L 405.45469 197.53659 
L 409.720613 193.716105 
L 413.986536 192.960323 
L 417.839628 193.276833 
L 422.105552 193.750078 
L 426.233865 188.981471 
L 430.499788 190.442482 
L 434.628101 187.125817 
L 438.894025 187.775228 
L 443.159948 182.695425 
L 447.288261 186.265419 
L 451.554184 177.901571 
L 455.682497 181.958831 
L 459.948421 181.969822 
L 464.214344 190.212302 
L 468.067436 191.625338 
L 472.33336 186.963982 
L 476.461673 197.202766 
L 480.727596 197.571967 
L 484.855909 204.559418 
L 489.121832 196.972167 
L 493.387756 198.537974 
L 497.516069 205.416511 
L 501.781992 196.840369 
L 505.910305 194.094026 
L 510.176229 197.389061 
L 514.442152 197.096172 
L 518.295244 200.545923 
L 522.561167 199.888393 
L 526.68948 197.910798 
L 530.955404 195.599412 
L 535.083717 188.542811 
L 539.34964 186.083634 
L 543.615564 187.342487 
L 547.743877 193.039212 
L 552.0098 194.926872 
L 556.138113 183.95296 
L 560.404036 179.873712 
L 564.66996 176.70423 
L 568.660662 167.583136 
L 572.926586 163.929116 
L 577.054899 170.044669 
L 581.320822 161.992044 
L 585.449135 154.913719 
L 589.715058 157.680227 
L 593.980982 154.513359 
L 598.109295 151.106925 
L 602.375218 149.31924 
L 606.503531 139.155402 
L 610.769455 144.042255 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="patch_3">
    <path d="M 82.944 258.672 
L 82.944 95.472 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_4">
    <path d="M 82.944 258.672 
L 635.904 258.672 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_9">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="89.472" transform="rotate(-0 82.944 89.472)">盈利能力＋动量</text>
   </g>
   <g id="legend_1">
    <g id="line2d_24">
     <path d="M 91.944 109.572 
L 101.944 109.572 
L 111.944 109.572 
" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="text_10">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="113.072" transform="rotate(-0 119.944 113.072)">两组各半</text>
    </g>
    <g id="line2d_25">
     <path d="M 91.944 124.572 
L 101.944 124.572 
L 111.944 124.572 
" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_11">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="128.072" transform="rotate(-0 119.944 128.072)">来源参照</text>
    </g>
    <g id="line2d_26">
     <path d="M 179.944 109.572 
L 189.944 109.572 
L 199.944 109.572 
" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_12">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="113.072" transform="rotate(-0 207.944 113.072)">盈利能力单独</text>
    </g>
    <g id="line2d_27">
     <path d="M 179.944 124.572 
L 189.944 124.572 
L 199.944 124.572 
" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_13">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="128.072" transform="rotate(-0 207.944 128.072)">动量单独</text>
    </g>
   </g>
  </g>
  <g id="axes_2">
   <g id="patch_5">
    <path d="M 82.944 470.832 
L 635.904 470.832 
L 635.904 307.632 
L 82.944 307.632 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_3">
    <g id="xtick_6">
     <g id="line2d_28">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_7">
     <g id="line2d_29">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_8">
     <g id="line2d_30">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_9">
     <g id="line2d_31">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_10">
     <g id="line2d_32">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_4">
    <g id="ytick_8">
     <g id="line2d_33">
      <path d="M 82.944 453.74181 
L 635.904 453.74181 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_34">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="453.74181" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_14">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="457.540638" transform="rotate(-0 75.944 457.540638)">100</text>
     </g>
    </g>
    <g id="ytick_9">
     <g id="line2d_35">
      <path d="M 82.944 425.667499 
L 635.904 425.667499 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_36">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="425.667499" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_15">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="429.466328" transform="rotate(-0 75.944 429.466328)">150</text>
     </g>
    </g>
    <g id="ytick_10">
     <g id="line2d_37">
      <path d="M 82.944 397.593189 
L 635.904 397.593189 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_38">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="397.593189" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_16">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="401.392017" transform="rotate(-0 75.944 401.392017)">200</text>
     </g>
    </g>
    <g id="ytick_11">
     <g id="line2d_39">
      <path d="M 82.944 369.518878 
L 635.904 369.518878 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_40">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="369.518878" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_17">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="373.317706" transform="rotate(-0 75.944 373.317706)">250</text>
     </g>
    </g>
    <g id="ytick_12">
     <g id="line2d_41">
      <path d="M 82.944 341.444568 
L 635.904 341.444568 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_42">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="341.444568" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_18">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="345.243396" transform="rotate(-0 75.944 345.243396)">300</text>
     </g>
    </g>
    <g id="ytick_13">
     <g id="line2d_43">
      <path d="M 82.944 313.370257 
L 635.904 313.370257 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_44">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="313.370257" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_19">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="317.169085" transform="rotate(-0 75.944 317.169085)">350</text>
     </g>
    </g>
    <g id="text_20">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="51.4565" y="389.232" transform="rotate(-90 51.4565 389.232)">初始资金100</text>
    </g>
   </g>
   <g id="line2d_45">
    <path d="M 108.078545 453.74181 
L 112.344469 455.882813 
L 116.197561 452.910464 
L 120.463484 453.440465 
L 124.591797 453.43348 
L 128.857721 452.274479 
L 132.986034 452.937686 
L 137.251957 451.885898 
L 141.51788 455.658479 
L 145.646193 457.445281 
L 149.912117 454.014573 
L 154.04043 453.347456 
L 158.306353 454.462038 
L 162.572277 458.156152 
L 166.562979 459.251585 
L 170.828903 455.706194 
L 174.957216 454.672068 
L 179.223139 453.869158 
L 183.351452 453.839792 
L 187.617375 451.965281 
L 191.883299 451.275305 
L 196.011612 451.28387 
L 200.277535 451.803097 
L 204.405848 447.847146 
L 208.671771 446.370938 
L 212.937695 445.669167 
L 216.790787 443.508804 
L 221.05671 444.510129 
L 225.185023 444.504546 
L 229.450947 444.178092 
L 233.57926 442.710473 
L 237.845183 440.800259 
L 242.111106 440.721554 
L 246.239419 438.56912 
L 250.505343 436.002276 
L 254.633656 433.595745 
L 258.899579 432.758217 
L 263.165503 427.453152 
L 267.018595 429.806954 
L 271.284518 432.293688 
L 275.412831 431.793713 
L 279.678754 430.344389 
L 283.807067 430.982402 
L 288.072991 428.54217 
L 292.338914 424.972485 
L 296.467227 425.31912 
L 300.733151 431.718474 
L 304.861464 430.947026 
L 309.127387 438.825515 
L 313.39331 432.951063 
L 317.246403 430.870023 
L 321.512326 430.470834 
L 325.640639 426.751429 
L 329.906562 432.179656 
L 334.034875 426.807488 
L 338.300799 425.452141 
L 342.566722 427.918292 
L 346.695035 425.911199 
L 350.960958 424.605948 
L 355.089271 422.218954 
L 359.355195 419.139328 
L 363.621118 420.038385 
L 367.611821 428.34785 
L 371.877744 443.264751 
L 376.006057 434.445135 
L 380.27198 430.927435 
L 384.400293 428.879759 
L 388.666217 424.074024 
L 392.93214 417.451206 
L 397.060453 421.40938 
L 401.326377 422.870732 
L 405.45469 411.468841 
L 409.720613 406.885811 
L 413.986536 406.072198 
L 417.839628 401.759589 
L 422.105552 398.794487 
L 426.233865 393.107018 
L 430.499788 391.237319 
L 434.628101 391.257158 
L 438.894025 392.925763 
L 443.159948 388.198151 
L 447.288261 390.504737 
L 451.554184 381.868885 
L 455.682497 386.928634 
L 459.948421 384.471335 
L 464.214344 386.716552 
L 468.067436 387.380058 
L 472.33336 383.224036 
L 476.461673 393.422968 
L 480.727596 390.386891 
L 484.855909 402.217792 
L 489.121832 393.272892 
L 493.387756 395.179417 
L 497.516069 404.328737 
L 501.781992 391.396548 
L 505.910305 386.836155 
L 510.176229 391.925155 
L 514.442152 388.68152 
L 518.295244 393.154761 
L 522.561167 395.9747 
L 526.68948 393.531864 
L 530.955404 395.646642 
L 535.083717 387.871937 
L 539.34964 382.381455 
L 543.615564 386.500258 
L 547.743877 391.881001 
L 552.0098 395.462945 
L 556.138113 382.025021 
L 560.404036 372.930502 
L 564.66996 372.217143 
L 568.660662 364.5927 
L 572.926586 356.925866 
L 577.054899 365.021546 
L 581.320822 356.976617 
L 585.449135 352.839303 
L 589.715058 350.132598 
L 593.980982 346.265022 
L 598.109295 344.729331 
L 602.375218 342.162561 
L 606.503531 327.727268 
L 610.769455 336.413432 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_46">
    <path d="M 108.078545 453.74181 
L 112.344469 455.650601 
L 116.197561 452.272525 
L 120.463484 453.166141 
L 124.591797 452.260526 
L 128.857721 451.780399 
L 132.986034 452.926692 
L 137.251957 452.657902 
L 141.51788 456.026058 
L 145.646193 457.79568 
L 149.912117 453.763441 
L 154.04043 453.647914 
L 158.306353 455.121672 
L 162.572277 458.341233 
L 166.562979 458.393842 
L 170.828903 454.599341 
L 174.957216 453.391282 
L 179.223139 452.496172 
L 183.351452 452.917788 
L 187.617375 450.517609 
L 191.883299 449.885487 
L 196.011612 449.909333 
L 200.277535 450.767967 
L 204.405848 447.353563 
L 208.671771 446.17369 
L 212.937695 445.026565 
L 216.790787 442.701344 
L 221.05671 442.893458 
L 225.185023 442.364213 
L 229.450947 441.77962 
L 233.57926 441.014516 
L 237.845183 439.60654 
L 242.111106 439.643969 
L 246.239419 437.724659 
L 250.505343 436.197048 
L 254.633656 433.669538 
L 258.899579 432.48055 
L 263.165503 428.262234 
L 267.018595 431.585807 
L 271.284518 433.379453 
L 275.412831 433.208686 
L 279.678754 431.783813 
L 283.807067 431.351779 
L 288.072991 428.430756 
L 292.338914 426.003012 
L 296.467227 425.87214 
L 300.733151 431.518381 
L 304.861464 430.10553 
L 309.127387 437.666691 
L 313.39331 430.806876 
L 317.246403 428.331673 
L 321.512326 427.641246 
L 325.640639 423.6677 
L 329.906562 430.400382 
L 334.034875 424.228054 
L 338.300799 422.95786 
L 342.566722 426.380038 
L 346.695035 423.808062 
L 350.960958 421.671257 
L 355.089271 418.049291 
L 359.355195 415.116221 
L 363.621118 416.322024 
L 367.611821 424.143584 
L 371.877744 438.79006 
L 376.006057 428.955519 
L 380.27198 425.26653 
L 384.400293 423.739581 
L 388.666217 420.551709 
L 392.93214 415.056301 
L 397.060453 418.788764 
L 401.326377 420.050577 
L 405.45469 406.077153 
L 409.720613 400.988583 
L 413.986536 401.308027 
L 417.839628 395.477245 
L 422.105552 390.358094 
L 426.233865 384.392563 
L 430.499788 383.165271 
L 434.628101 381.506924 
L 438.894025 380.527017 
L 443.159948 376.622551 
L 447.288261 381.579402 
L 451.554184 373.416109 
L 455.682497 376.672829 
L 459.948421 371.516169 
L 464.214344 376.514353 
L 468.067436 378.724747 
L 472.33336 375.380737 
L 476.461673 387.338771 
L 480.727596 386.159818 
L 484.855909 397.642819 
L 489.121832 387.107296 
L 493.387756 390.989916 
L 497.516069 402.051061 
L 501.781992 392.144233 
L 505.910305 385.805448 
L 510.176229 393.092106 
L 514.442152 384.719364 
L 518.295244 387.990549 
L 522.561167 385.8085 
L 526.68948 384.212332 
L 530.955404 384.173947 
L 535.083717 375.072939 
L 539.34964 369.162893 
L 543.615564 373.185358 
L 547.743877 379.054377 
L 552.0098 383.102604 
L 556.138113 371.158109 
L 560.404036 361.921454 
L 564.66996 361.494941 
L 568.660662 354.612385 
L 572.926586 347.683014 
L 577.054899 354.49754 
L 581.320822 347.740572 
L 585.449135 343.736508 
L 589.715058 339.106172 
L 593.980982 336.347574 
L 598.109295 333.33091 
L 602.375218 333.865797 
L 606.503531 321.34161 
L 610.769455 329.319982 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_47">
    <path d="M 108.078545 453.74181 
L 112.344469 457.226506 
L 116.197561 454.342735 
L 120.463484 455.04058 
L 124.591797 454.231326 
L 128.857721 453.745477 
L 132.986034 454.510565 
L 137.251957 454.467091 
L 141.51788 458.122649 
L 145.646193 460.307197 
L 149.912117 457.134763 
L 154.04043 456.254798 
L 158.306353 458.156986 
L 162.572277 462.358466 
L 166.562979 463.413818 
L 170.828903 459.611102 
L 174.957216 457.229169 
L 179.223139 456.877076 
L 183.351452 458.258657 
L 187.617375 456.360001 
L 191.883299 454.29453 
L 196.011612 454.539708 
L 200.277535 453.932621 
L 204.405848 446.91193 
L 208.671771 444.723364 
L 212.937695 444.458265 
L 216.790787 441.838819 
L 221.05671 443.602036 
L 225.185023 444.196908 
L 229.450947 445.359683 
L 233.57926 442.605059 
L 237.845183 441.172487 
L 242.111106 441.98755 
L 246.239419 438.78851 
L 250.505343 436.759687 
L 254.633656 434.402464 
L 258.899579 432.935582 
L 263.165503 428.912228 
L 267.018595 432.185205 
L 271.284518 434.759036 
L 275.412831 434.375565 
L 279.678754 434.607245 
L 283.807067 435.58156 
L 288.072991 432.137418 
L 292.338914 431.513217 
L 296.467227 432.864988 
L 300.733151 437.106009 
L 304.861464 435.471198 
L 309.127387 444.091699 
L 313.39331 438.090526 
L 317.246403 437.219808 
L 321.512326 438.59837 
L 325.640639 433.365746 
L 329.906562 439.72556 
L 334.034875 434.488805 
L 338.300799 432.531454 
L 342.566722 437.655945 
L 346.695035 433.495022 
L 350.960958 431.5804 
L 355.089271 429.232822 
L 359.355195 425.876255 
L 363.621118 429.614382 
L 367.611821 438.358611 
L 371.877744 457.865196 
L 376.006057 450.574171 
L 380.27198 448.611989 
L 384.400293 447.95729 
L 388.666217 445.702304 
L 392.93214 442.298601 
L 397.060453 445.183352 
L 401.326377 445.164976 
L 405.45469 433.401901 
L 409.720613 429.110206 
L 413.986536 428.447242 
L 417.839628 419.418206 
L 422.105552 412.884212 
L 426.233865 407.593298 
L 430.499788 401.989871 
L 434.628101 406.261114 
L 438.894025 408.769773 
L 443.159948 405.795612 
L 447.288261 405.854009 
L 451.554184 399.253314 
L 455.682497 404.196359 
L 459.948421 399.267739 
L 464.214344 393.242011 
L 468.067436 392.766202 
L 472.33336 390.401346 
L 476.461673 397.736064 
L 480.727596 391.192866 
L 484.855909 405.939733 
L 489.121832 397.730123 
L 493.387756 399.545437 
L 497.516069 409.0681 
L 501.781992 394.145588 
L 505.910305 388.528723 
L 510.176229 394.502753 
L 514.442152 388.389167 
L 518.295244 392.934287 
L 522.561167 399.413072 
L 526.68948 397.050514 
L 530.955404 404.229051 
L 535.083717 397.6828 
L 539.34964 389.839375 
L 543.615564 396.470875 
L 547.743877 399.964197 
L 552.0098 404.719716 
L 556.138113 391.844927 
L 560.404036 378.860394 
L 564.66996 381.477457 
L 568.660662 377.865714 
L 572.926586 367.194024 
L 577.054899 375.58286 
L 581.320822 369.76694 
L 585.449135 370.523186 
L 589.715058 361.580129 
L 593.980982 357.885423 
L 598.109295 359.160137 
L 602.375218 356.307416 
L 606.503531 340.404355 
L 610.769455 351.541794 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_48">
    <path d="M 108.078545 453.74181 
L 112.344469 454.53912 
L 116.197561 451.478193 
L 120.463484 451.840349 
L 124.591797 452.635635 
L 128.857721 450.803482 
L 132.986034 451.364808 
L 137.251957 449.304706 
L 141.51788 453.194309 
L 145.646193 454.583364 
L 149.912117 450.894383 
L 154.04043 450.440113 
L 158.306353 450.76709 
L 162.572277 453.953838 
L 166.562979 455.089351 
L 170.828903 451.801286 
L 174.957216 452.114967 
L 179.223139 450.86124 
L 183.351452 449.420928 
L 187.617375 447.570561 
L 191.883299 448.256079 
L 196.011612 448.028032 
L 200.277535 449.673572 
L 204.405848 448.782363 
L 208.671771 448.018512 
L 212.937695 446.880068 
L 216.790787 445.178789 
L 221.05671 445.418222 
L 225.185023 444.812183 
L 229.450947 442.9965 
L 233.57926 442.815886 
L 237.845183 440.428032 
L 242.111106 439.455559 
L 246.239419 438.349731 
L 250.505343 435.244865 
L 254.633656 432.789026 
L 258.899579 432.580852 
L 263.165503 425.994076 
L 267.018595 427.428704 
L 271.284518 429.82834 
L 275.412831 429.211862 
L 279.678754 426.081533 
L 283.807067 426.383245 
L 288.072991 424.946922 
L 292.338914 418.431754 
L 296.467227 417.773252 
L 300.733151 426.330938 
L 304.861464 426.422853 
L 309.127387 433.559331 
L 313.39331 427.811599 
L 317.246403 424.520238 
L 321.512326 422.343298 
L 325.640639 420.137111 
L 329.906562 424.633752 
L 334.034875 419.126171 
L 338.300799 418.372827 
L 342.566722 418.18064 
L 346.695035 418.327376 
L 350.960958 417.631497 
L 355.089271 415.205087 
L 359.355195 412.4024 
L 363.621118 410.462389 
L 367.611821 418.33709 
L 371.877744 428.664307 
L 376.006057 418.316098 
L 380.27198 413.24288 
L 384.400293 409.802227 
L 388.666217 402.445744 
L 392.93214 392.603811 
L 397.060453 397.635407 
L 401.326377 400.576489 
L 405.45469 389.535781 
L 409.720613 384.661417 
L 413.986536 383.697154 
L 417.839628 384.100972 
L 422.105552 384.704762 
L 426.233865 378.620738 
L 430.499788 380.484768 
L 434.628101 376.253203 
L 438.894025 377.081753 
L 443.159948 370.60069 
L 447.288261 375.155464 
L 451.554184 364.484455 
L 455.682497 369.660908 
L 459.948421 369.674931 
L 464.214344 380.191093 
L 468.067436 381.993914 
L 472.33336 376.046726 
L 476.461673 389.109872 
L 480.727596 389.580916 
L 484.855909 398.495851 
L 489.121832 388.815662 
L 493.387756 390.813396 
L 497.516069 399.589373 
L 501.781992 388.647508 
L 505.910305 385.143588 
L 510.176229 389.347556 
L 514.442152 388.973873 
L 518.295244 393.375236 
L 522.561167 392.536327 
L 526.68948 390.013213 
L 530.955404 387.064234 
L 535.083717 378.061074 
L 539.34964 374.923535 
L 543.615564 376.529641 
L 547.743877 383.797804 
L 552.0098 386.206173 
L 556.138113 372.205115 
L 560.404036 367.00061 
L 564.66996 362.956828 
L 568.660662 351.319687 
L 572.926586 346.657707 
L 577.054899 354.460231 
L 581.320822 344.186295 
L 585.449135 335.15542 
L 589.715058 338.685067 
L 593.980982 334.64462 
L 598.109295 330.298524 
L 602.375218 328.017707 
L 606.503531 315.050182 
L 610.769455 321.28507 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="patch_6">
    <path d="M 82.944 470.832 
L 82.944 307.632 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_7">
    <path d="M 82.944 470.832 
L 635.904 470.832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_21">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="301.632" transform="rotate(-0 82.944 301.632)">价值＋动量</text>
   </g>
   <g id="legend_2">
    <g id="line2d_49">
     <path d="M 91.944 321.732 
L 101.944 321.732 
L 111.944 321.732 
" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="text_22">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="325.232" transform="rotate(-0 119.944 325.232)">两组各半</text>
    </g>
    <g id="line2d_50">
     <path d="M 91.944 336.732 
L 101.944 336.732 
L 111.944 336.732 
" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_23">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="340.232" transform="rotate(-0 119.944 340.232)">来源参照</text>
    </g>
    <g id="line2d_51">
     <path d="M 179.944 321.732 
L 189.944 321.732 
L 199.944 321.732 
" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_24">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="325.232" transform="rotate(-0 207.944 325.232)">价值单独</text>
    </g>
    <g id="line2d_52">
     <path d="M 179.944 336.732 
L 189.944 336.732 
L 199.944 336.732 
" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_25">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="340.232" transform="rotate(-0 207.944 340.232)">动量单独</text>
    </g>
   </g>
  </g>
  <g id="axes_3">
   <g id="patch_8">
    <path d="M 82.944 682.992 
L 635.904 682.992 
L 635.904 519.792 
L 82.944 519.792 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_5">
    <g id="xtick_11">
     <g id="line2d_53">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_26">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="158.443964" y="697.589656" transform="rotate(-0 158.443964 697.589656)">2016</text>
     </g>
    </g>
    <g id="xtick_12">
     <g id="line2d_54">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_27">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="259.03719" y="697.589656" transform="rotate(-0 259.03719 697.589656)">2018</text>
     </g>
    </g>
    <g id="xtick_13">
     <g id="line2d_55">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_28">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="359.492805" y="697.589656" transform="rotate(-0 359.492805 697.589656)">2020</text>
     </g>
    </g>
    <g id="xtick_14">
     <g id="line2d_56">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_29">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="460.086031" y="697.589656" transform="rotate(-0 460.086031 697.589656)">2022</text>
     </g>
    </g>
    <g id="xtick_15">
     <g id="line2d_57">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_30">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="560.541647" y="697.589656" transform="rotate(-0 560.541647 697.589656)">2024</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_6">
    <g id="ytick_14">
     <g id="line2d_58">
      <path d="M 82.944 668.201084 
L 635.904 668.201084 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_59">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="668.201084" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_31">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="671.999913" transform="rotate(-0 75.944 671.999913)">100</text>
     </g>
    </g>
    <g id="ytick_15">
     <g id="line2d_60">
      <path d="M 82.944 646.800728 
L 635.904 646.800728 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_61">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="646.800728" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_32">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="650.599556" transform="rotate(-0 75.944 650.599556)">150</text>
     </g>
    </g>
    <g id="ytick_16">
     <g id="line2d_62">
      <path d="M 82.944 625.400372 
L 635.904 625.400372 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_63">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="625.400372" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_33">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="629.1992" transform="rotate(-0 75.944 629.1992)">200</text>
     </g>
    </g>
    <g id="ytick_17">
     <g id="line2d_64">
      <path d="M 82.944 604.000016 
L 635.904 604.000016 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_65">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="604.000016" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_34">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="607.798844" transform="rotate(-0 75.944 607.798844)">250</text>
     </g>
    </g>
    <g id="ytick_18">
     <g id="line2d_66">
      <path d="M 82.944 582.59966 
L 635.904 582.59966 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_67">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="582.59966" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_35">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="586.398488" transform="rotate(-0 75.944 586.398488)">300</text>
     </g>
    </g>
    <g id="ytick_19">
     <g id="line2d_68">
      <path d="M 82.944 561.199304 
L 635.904 561.199304 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_69">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="561.199304" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_36">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="564.998132" transform="rotate(-0 75.944 564.998132)">350</text>
     </g>
    </g>
    <g id="ytick_20">
     <g id="line2d_70">
      <path d="M 82.944 539.798948 
L 635.904 539.798948 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_71">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="539.798948" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_37">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="543.597776" transform="rotate(-0 75.944 543.597776)">400</text>
     </g>
    </g>
    <g id="text_38">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="51.4565" y="601.392" transform="rotate(-90 51.4565 601.392)">初始资金100</text>
    </g>
   </g>
   <g id="line2d_72">
    <path d="M 108.078545 668.201084 
L 112.344469 669.908105 
L 116.197561 667.545768 
L 120.463484 668.219554 
L 124.591797 667.664957 
L 128.857721 667.272091 
L 132.986034 668.030586 
L 137.251957 667.616794 
L 141.51788 670.295687 
L 145.646193 671.563373 
L 149.912117 668.685744 
L 154.04043 668.323772 
L 158.306353 669.48118 
L 162.572277 672.14468 
L 166.562979 672.328679 
L 170.828903 669.409771 
L 174.957216 668.688533 
L 179.223139 668.167837 
L 183.351452 668.5757 
L 187.617375 666.789298 
L 191.883299 666.107381 
L 196.011612 666.097522 
L 200.277535 666.516407 
L 204.405848 662.931198 
L 208.671771 661.696769 
L 212.937695 660.97827 
L 216.790787 658.99088 
L 221.05671 659.478253 
L 225.185023 659.30404 
L 229.450947 659.189128 
L 233.57926 658.203579 
L 237.845183 657.169438 
L 242.111106 657.254232 
L 246.239419 655.628625 
L 250.505343 654.130119 
L 254.633656 651.934809 
L 258.899579 650.858123 
L 263.165503 647.527271 
L 267.018595 649.825377 
L 271.284518 651.597918 
L 275.412831 651.362872 
L 279.678754 650.637219 
L 283.807067 650.663128 
L 288.072991 648.06365 
L 292.338914 646.144214 
L 296.467227 646.34449 
L 300.733151 650.592271 
L 304.861464 649.44753 
L 309.127387 655.658222 
L 313.39331 651.200631 
L 317.246403 649.550134 
L 321.512326 649.167941 
L 325.640639 645.771661 
L 329.906562 650.609044 
L 334.034875 646.087969 
L 338.300799 644.697629 
L 342.566722 646.883503 
L 346.695035 644.860184 
L 350.960958 643.075734 
L 355.089271 640.776929 
L 359.355195 638.13114 
L 363.621118 639.105595 
L 367.611821 645.625593 
L 371.877744 656.957277 
L 376.006057 649.376658 
L 380.27198 646.548697 
L 384.400293 644.57352 
L 388.666217 641.093279 
L 392.93214 635.557164 
L 397.060453 638.562088 
L 401.326377 640.317353 
L 405.45469 631.096514 
L 409.720613 627.455247 
L 413.986536 628.164137 
L 417.839628 624.104794 
L 422.105552 619.436405 
L 426.233865 614.629771 
L 430.499788 612.508898 
L 434.628101 611.95203 
L 438.894025 611.206812 
L 443.159948 608.481254 
L 447.288261 612.1856 
L 451.554184 605.886348 
L 455.682497 607.448668 
L 459.948421 602.557435 
L 464.214344 604.169909 
L 468.067436 606.152023 
L 472.33336 602.8841 
L 476.461673 610.52345 
L 480.727596 608.869651 
L 484.855909 618.320835 
L 489.121832 610.438759 
L 493.387756 613.795662 
L 497.516069 622.760821 
L 501.781992 612.855208 
L 505.910305 607.006904 
L 510.176229 612.725849 
L 514.442152 607.084624 
L 518.295244 609.854642 
L 522.561167 608.629767 
L 526.68948 606.514848 
L 530.955404 607.707419 
L 535.083717 600.945308 
L 539.34964 596.230233 
L 543.615564 599.238303 
L 547.743877 604.129998 
L 552.0098 607.251747 
L 556.138113 596.732309 
L 560.404036 589.238906 
L 564.66996 588.878564 
L 568.660662 583.622125 
L 572.926586 577.448998 
L 577.054899 583.771133 
L 581.320822 576.530818 
L 585.449135 572.831726 
L 589.715058 569.14473 
L 593.980982 565.331415 
L 598.109295 563.858824 
L 602.375218 564.590269 
L 606.503531 554.508457 
L 610.769455 559.780382 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_73">
    <path d="M 108.078545 668.201084 
L 112.344469 669.710872 
L 116.197561 667.149059 
L 120.463484 667.745142 
L 124.591797 667.336312 
L 128.857721 666.760825 
L 132.986034 667.532833 
L 137.251957 666.813847 
L 141.51788 669.529972 
L 145.646193 670.838847 
L 149.912117 667.753429 
L 154.04043 667.496142 
L 158.306353 668.537122 
L 162.572277 671.141429 
L 166.562979 671.351319 
L 170.828903 668.558186 
L 174.957216 667.873329 
L 179.223139 667.128217 
L 183.351452 667.414847 
L 187.617375 665.849689 
L 191.883299 665.389764 
L 196.011612 665.338664 
L 200.277535 665.939971 
L 204.405848 663.352955 
L 208.671771 662.415584 
L 212.937695 661.582516 
L 216.790787 659.857304 
L 221.05671 660.02564 
L 225.185023 659.636827 
L 229.450947 659.278858 
L 233.57926 658.638784 
L 237.845183 657.490879 
L 242.111106 657.461079 
L 246.239419 655.950888 
L 250.505343 654.6003 
L 254.633656 652.823567 
L 258.899579 652.056302 
L 263.165503 648.601544 
L 267.018595 650.983665 
L 271.284518 652.454303 
L 275.412831 652.117514 
L 279.678754 650.881202 
L 283.807067 650.659534 
L 288.072991 648.581434 
L 292.338914 646.723225 
L 296.467227 646.740278 
L 300.733151 651.252957 
L 304.861464 650.083788 
L 309.127387 655.909203 
L 313.39331 651.116479 
L 317.246403 649.249076 
L 321.512326 648.803734 
L 325.640639 645.90993 
L 329.906562 650.521779 
L 334.034875 646.094521 
L 338.300799 645.062813 
L 342.566722 647.117171 
L 346.695035 645.560299 
L 350.960958 644.164295 
L 355.089271 641.593506 
L 359.355195 639.549406 
L 363.621118 639.972909 
L 367.611821 646.201342 
L 371.877744 656.464923 
L 376.006057 649.207225 
L 380.27198 646.126205 
L 384.400293 645.054951 
L 388.666217 641.50182 
L 392.93214 637.069509 
L 397.060453 639.749144 
L 401.326377 640.709237 
L 405.45469 631.100416 
L 409.720613 627.244663 
L 413.986536 627.235924 
L 417.839628 623.234006 
L 422.105552 620.114616 
L 426.233865 615.424068 
L 430.499788 614.259196 
L 434.628101 613.193088 
L 438.894025 612.679194 
L 443.159948 609.924753 
L 447.288261 613.467967 
L 451.554184 607.457832 
L 455.682497 610.411583 
L 459.948421 607.03337 
L 464.214344 610.898356 
L 468.067436 612.188393 
L 472.33336 609.270524 
L 476.461673 618.234758 
L 480.727596 617.285722 
L 484.855909 626.014208 
L 489.121832 618.41435 
L 493.387756 621.024241 
L 497.516069 629.078187 
L 501.781992 621.694474 
L 505.910305 617.587221 
L 510.176229 623.076811 
L 514.442152 617.096428 
L 518.295244 619.488648 
L 522.561167 618.432129 
L 526.68948 617.799017 
L 530.955404 618.599255 
L 535.083717 612.59058 
L 539.34964 608.30017 
L 543.615564 610.954428 
L 547.743877 615.027239 
L 552.0098 617.824332 
L 556.138113 608.597578 
L 560.404036 602.283791 
L 564.66996 601.129334 
L 568.660662 595.220579 
L 572.926586 590.468811 
L 577.054899 595.853774 
L 581.320822 591.084293 
L 585.449135 588.77357 
L 589.715058 585.688919 
L 593.980982 583.320366 
L 598.109295 581.173966 
L 602.375218 581.380231 
L 606.503531 571.280469 
L 610.769455 577.078154 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_74">
    <path d="M 108.078545 668.201084 
L 112.344469 670.857382 
L 116.197561 668.659154 
L 120.463484 669.191105 
L 124.591797 668.57423 
L 128.857721 668.20388 
L 132.986034 668.787087 
L 137.251957 668.753948 
L 141.51788 671.54049 
L 145.646193 673.205717 
L 149.912117 670.787449 
L 154.04043 670.116673 
L 158.306353 671.566664 
L 162.572277 674.769349 
L 166.562979 675.573818 
L 170.828903 672.675101 
L 174.957216 670.859412 
L 179.223139 670.59102 
L 183.351452 671.644165 
L 187.617375 670.196867 
L 191.883299 668.622409 
L 196.011612 668.809302 
L 200.277535 668.346535 
L 204.405848 662.994835 
L 208.671771 661.326545 
L 212.937695 661.124466 
L 216.790787 659.127727 
L 221.05671 660.471784 
L 225.185023 660.925241 
L 229.450947 661.811596 
L 233.57926 659.711813 
L 237.845183 658.619798 
L 242.111106 659.241101 
L 246.239419 656.802551 
L 250.505343 655.25603 
L 254.633656 653.459177 
L 258.899579 652.341009 
L 263.165503 649.274105 
L 267.018595 651.769015 
L 271.284518 653.730983 
L 275.412831 653.438672 
L 279.678754 653.615276 
L 283.807067 654.357972 
L 288.072991 651.732588 
L 292.338914 651.256775 
L 296.467227 652.287197 
L 300.733151 655.520023 
L 304.861464 654.273847 
L 309.127387 660.845042 
L 313.39331 656.270495 
L 317.246403 655.606769 
L 321.512326 656.657613 
L 325.640639 652.668913 
L 329.906562 657.516842 
L 334.034875 653.524992 
L 338.300799 652.032952 
L 342.566722 655.939225 
L 346.695035 652.767456 
L 350.960958 651.307987 
L 355.089271 649.518486 
L 359.355195 646.959858 
L 363.621118 649.80934 
L 367.611821 656.474851 
L 371.877744 671.34424 
L 376.006057 665.786471 
L 380.27198 664.290748 
L 384.400293 663.791687 
L 388.666217 662.072767 
L 392.93214 659.478207 
L 397.060453 661.677183 
L 401.326377 661.663175 
L 405.45469 652.696472 
L 409.720613 649.425019 
L 413.986536 648.919658 
L 417.839628 642.037046 
L 422.105552 637.056343 
L 426.233865 633.02321 
L 430.499788 628.751854 
L 434.628101 632.007718 
L 438.894025 633.920007 
L 443.159948 631.652877 
L 447.288261 631.697392 
L 451.554184 626.665845 
L 455.682497 630.433807 
L 459.948421 626.676841 
L 464.214344 622.083576 
L 468.067436 621.720879 
L 472.33336 619.918208 
L 476.461673 625.509283 
L 480.727596 620.521564 
L 484.855909 631.762738 
L 489.121832 625.504754 
L 493.387756 626.888523 
L 497.516069 634.147415 
L 501.781992 622.772351 
L 505.910305 618.490753 
L 510.176229 623.044609 
L 514.442152 618.384373 
L 518.295244 621.849006 
L 522.561167 626.787625 
L 526.68948 624.986705 
L 530.955404 630.458727 
L 535.083717 625.468681 
L 539.34964 619.48983 
L 543.615564 624.54486 
L 547.743877 627.207734 
L 552.0098 630.832749 
L 556.138113 621.018614 
L 560.404036 611.120824 
L 564.66996 613.115746 
L 568.660662 610.362603 
L 572.926586 602.227837 
L 577.054899 608.62244 
L 581.320822 604.189107 
L 585.449135 604.765575 
L 589.715058 597.948503 
L 593.980982 595.132119 
L 598.109295 596.103803 
L 602.375218 593.929243 
L 606.503531 581.806731 
L 610.769455 590.296527 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_75">
    <path d="M 108.078545 668.201084 
L 112.344469 668.958828 
L 116.197561 666.432382 
L 120.463484 667.248002 
L 124.591797 666.755685 
L 128.857721 666.340302 
L 132.986034 667.274085 
L 137.251957 666.47964 
L 141.51788 669.050883 
L 145.646193 669.921029 
L 149.912117 666.584038 
L 154.04043 666.53087 
L 158.306353 667.395696 
L 162.572277 669.520011 
L 166.562979 669.08354 
L 170.828903 666.144441 
L 174.957216 666.517655 
L 179.223139 665.744654 
L 183.351452 665.507235 
L 187.617375 663.381729 
L 191.883299 663.592352 
L 196.011612 663.385742 
L 200.277535 664.686279 
L 204.405848 662.867561 
L 208.671771 662.066993 
L 212.937695 660.832074 
L 216.790787 658.854032 
L 221.05671 658.484722 
L 225.185023 657.682839 
L 229.450947 656.56666 
L 233.57926 656.695344 
L 237.845183 655.719077 
L 242.111106 655.267362 
L 246.239419 654.454698 
L 250.505343 653.004209 
L 254.633656 650.410441 
L 258.899579 649.375237 
L 263.165503 645.780437 
L 267.018595 647.881739 
L 271.284518 649.464853 
L 275.412831 649.287073 
L 279.678754 647.659162 
L 283.807067 646.968284 
L 288.072991 644.394713 
L 292.338914 641.031654 
L 296.467227 640.401783 
L 300.733151 645.66452 
L 304.861464 644.621214 
L 309.127387 650.471401 
L 313.39331 646.130767 
L 317.246403 643.4935 
L 321.512326 641.678269 
L 325.640639 638.87441 
L 329.906562 643.701247 
L 334.034875 638.650946 
L 338.300799 637.362305 
L 342.566722 637.82778 
L 346.695035 636.952912 
L 350.960958 634.843481 
L 355.089271 632.035372 
L 359.355195 629.302423 
L 363.621118 628.401851 
L 367.611821 634.776336 
L 371.877744 642.570313 
L 376.006057 632.966844 
L 380.27198 628.806645 
L 384.400293 625.355353 
L 388.666217 620.11379 
L 392.93214 611.636121 
L 397.060453 615.446993 
L 401.326377 618.971532 
L 405.45469 609.496556 
L 409.720613 605.485475 
L 413.986536 607.408616 
L 417.839628 606.172542 
L 422.105552 601.816467 
L 426.233865 596.236332 
L 430.499788 596.265942 
L 434.628101 591.896341 
L 438.894025 588.493618 
L 443.159948 585.30963 
L 447.288261 592.673808 
L 451.554184 585.106852 
L 455.682497 584.463529 
L 459.948421 578.43803 
L 464.214344 586.256243 
L 468.067436 590.583167 
L 472.33336 585.849992 
L 476.461673 595.537618 
L 480.727596 597.217737 
L 484.855909 604.878932 
L 489.121832 595.372764 
L 493.387756 600.7028 
L 497.516069 611.374228 
L 501.781992 602.938064 
L 505.910305 595.523055 
L 510.176229 602.407089 
L 514.442152 595.784875 
L 518.295244 597.860278 
L 522.561167 590.47191 
L 526.68948 588.042992 
L 530.955404 584.956111 
L 535.083717 576.421936 
L 539.34964 572.970636 
L 543.615564 573.931747 
L 547.743877 581.052262 
L 552.0098 583.670745 
L 556.138113 572.446003 
L 560.404036 567.356987 
L 564.66996 564.641382 
L 568.660662 556.881646 
L 572.926586 552.670159 
L 577.054899 558.919825 
L 581.320822 548.87253 
L 585.449135 540.897877 
L 589.715058 540.340957 
L 593.980982 535.530711 
L 598.109295 531.613845 
L 602.375218 535.251295 
L 606.503531 527.210182 
L 610.769455 529.264237 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="patch_9">
    <path d="M 82.944 682.992 
L 82.944 519.792 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_10">
    <path d="M 82.944 682.992 
L 635.904 682.992 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_39">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="513.792" transform="rotate(-0 82.944 513.792)">价值＋盈利能力</text>
   </g>
   <g id="legend_3">
    <g id="line2d_76">
     <path d="M 91.944 533.892 
L 101.944 533.892 
L 111.944 533.892 
" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="text_40">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="537.392" transform="rotate(-0 119.944 537.392)">两组各半</text>
    </g>
    <g id="line2d_77">
     <path d="M 91.944 548.892 
L 101.944 548.892 
L 111.944 548.892 
" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_41">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="552.392" transform="rotate(-0 119.944 552.392)">来源参照</text>
    </g>
    <g id="line2d_78">
     <path d="M 179.944 533.892 
L 189.944 533.892 
L 199.944 533.892 
" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_42">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="537.392" transform="rotate(-0 207.944 537.392)">价值单独</text>
    </g>
    <g id="line2d_79">
     <path d="M 179.944 548.892 
L 189.944 548.892 
L 199.944 548.892 
" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_43">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="552.392" transform="rotate(-0 207.944 552.392)">盈利能力单独</text>
    </g>
   </g>
  </g>
  <g id="text_44">
   <text style="font-size: 17px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="76.032" y="24.2352" transform="rotate(-0 76.032 24.2352)">大规模美国股票：从100开始的公开资金路径</text>
  </g>
  <g id="text_45">
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 36.7016)">2015—2024 · 起始各半，以后不调配 · 毛收益，个人净费用未评价</text>
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 47.0016)">参照是两种来源三组平均的组合，并非母指数；月末观察，全部已见历史</text>
  </g>
 </g>
 <defs>
  <clipPath id="p7311188120">
   <rect x="82.944" y="95.472" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pf527fceebe">
   <rect x="82.944" y="307.632" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pd228cd0829">
   <rect x="82.944" y="519.792" width="552.96" height="163.2"/>
  </clipPath>
 </defs>
</svg>




较小规模股票：组合、来源参照和单项资金路径

<svg xmlns:xlink="http://www.w3.org/1999/xlink" width="100%" style="max-width:100%;height:auto;display:block" viewBox="0 0 691.2 734.4" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-10-23T18:11:08.598617</dc:date>
    <dc:format>image/svg+xml</dc:format>
    <dc:creator>
     <cc:Agent>
      <dc:title>Matplotlib v3.11.2, https://matplotlib.org/</dc:title>
     </cc:Agent>
    </dc:creator>
   </cc:Work>
  </rdf:RDF>
 </metadata>
 <defs>
  <style type="text/css">*{stroke-linejoin: round; stroke-linecap: butt}</style>
 </defs>
 <g id="figure_1">
  <g id="patch_1">
   <path d="M 0 734.4 
L 691.2 734.4 
L 691.2 0 
L 0 0 
z
" style="fill: #f8fafc"/>
  </g>
  <g id="axes_1">
   <g id="patch_2">
    <path d="M 82.944 258.672 
L 635.904 258.672 
L 635.904 95.472 
L 82.944 95.472 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_1">
    <g id="xtick_1">
     <g id="line2d_1">
      <defs>
       <path id="m80ae50af5d" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_2">
     <g id="line2d_2">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_3">
     <g id="line2d_3">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_4">
     <g id="line2d_4">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_5">
     <g id="line2d_5">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="258.672" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_2">
    <g id="ytick_1">
     <g id="line2d_6">
      <path d="M 82.944 239.125806 
L 635.904 239.125806 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_7">
      <defs>
       <path id="m7712ef1b3c" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="239.125806" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_1">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="242.924634" transform="rotate(-0 75.944 242.924634)">100</text>
     </g>
    </g>
    <g id="ytick_2">
     <g id="line2d_8">
      <path d="M 82.944 210.410747 
L 635.904 210.410747 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_9">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="210.410747" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_2">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="214.209575" transform="rotate(-0 75.944 214.209575)">150</text>
     </g>
    </g>
    <g id="ytick_3">
     <g id="line2d_10">
      <path d="M 82.944 181.695688 
L 635.904 181.695688 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_11">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="181.695688" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_3">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="185.494516" transform="rotate(-0 75.944 185.494516)">200</text>
     </g>
    </g>
    <g id="ytick_4">
     <g id="line2d_12">
      <path d="M 82.944 152.980629 
L 635.904 152.980629 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_13">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="152.980629" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_4">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="156.779457" transform="rotate(-0 75.944 156.779457)">250</text>
     </g>
    </g>
    <g id="ytick_5">
     <g id="line2d_14">
      <path d="M 82.944 124.26557 
L 635.904 124.26557 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_15">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="124.26557" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_5">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="128.064398" transform="rotate(-0 75.944 128.064398)">300</text>
     </g>
    </g>
    <g id="ytick_6">
     <g id="line2d_16">
      <path d="M 82.944 95.55051 
L 635.904 95.55051 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_17">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="95.55051" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_6">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="99.349339" transform="rotate(-0 75.944 99.349339)">350</text>
     </g>
    </g>
    <g id="text_7">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="51.4565" y="177.072" transform="rotate(-90 51.4565 177.072)">初始资金100</text>
    </g>
   </g>
   <g id="line2d_18">
    <path d="M 108.078545 239.125806 
L 112.344469 240.645981 
L 116.197561 237.287775 
L 120.463484 236.021018 
L 124.591797 237.968217 
L 128.857721 236.337668 
L 132.986034 235.2118 
L 137.251957 235.870179 
L 141.51788 239.798294 
L 145.646193 242.874239 
L 149.912117 240.017567 
L 154.04043 238.302194 
L 158.306353 241.342984 
L 162.572277 246.691151 
L 166.562979 246.714414 
L 170.828903 243.040389 
L 174.957216 242.138245 
L 179.223139 241.591224 
L 183.351452 241.455341 
L 187.617375 238.236866 
L 191.883299 237.380334 
L 196.011612 236.8436 
L 200.277535 239.745597 
L 204.405848 233.284622 
L 208.671771 232.069811 
L 212.937695 232.074709 
L 216.790787 231.482816 
L 221.05671 231.216567 
L 225.185023 230.027263 
L 229.450947 231.53803 
L 233.57926 229.415883 
L 237.845183 228.94861 
L 242.111106 229.800066 
L 246.239419 225.101044 
L 250.505343 224.202506 
L 254.633656 221.386926 
L 258.899579 220.275893 
L 263.165503 217.962575 
L 267.018595 220.629743 
L 271.284518 220.045437 
L 275.412831 219.727797 
L 279.678754 214.685779 
L 283.807067 213.235378 
L 288.072991 211.937414 
L 292.338914 208.427402 
L 296.467227 210.415705 
L 300.733151 220.466881 
L 304.861464 220.404115 
L 309.127387 229.58177 
L 313.39331 222.323317 
L 317.246403 218.739371 
L 321.512326 220.399315 
L 325.640639 217.952388 
L 329.906562 223.901169 
L 334.034875 218.329379 
L 338.300799 217.88302 
L 342.566722 222.136089 
L 346.695035 221.802378 
L 350.960958 219.596922 
L 355.089271 216.554237 
L 359.355195 213.956301 
L 363.621118 216.690807 
L 367.611821 223.524505 
L 371.877744 242.75887 
L 376.006057 232.185177 
L 380.27198 226.464331 
L 384.400293 223.299417 
L 388.666217 220.234653 
L 392.93214 215.203584 
L 397.060453 217.397109 
L 401.326377 215.495723 
L 405.45469 199.325614 
L 409.720613 190.70771 
L 413.986536 180.900365 
L 417.839628 170.6052 
L 422.105552 167.558662 
L 426.233865 163.328271 
L 430.499788 159.284798 
L 434.628101 156.782975 
L 438.894025 161.753131 
L 443.159948 158.572537 
L 447.288261 161.95457 
L 451.554184 156.476971 
L 455.682497 160.239049 
L 459.948421 156.282002 
L 464.214344 169.328122 
L 468.067436 166.900768 
L 472.33336 166.568814 
L 476.461673 176.443262 
L 480.727596 174.447534 
L 484.855909 185.996135 
L 489.121832 173.976926 
L 493.387756 176.468826 
L 497.516069 188.617717 
L 501.781992 174.787183 
L 505.910305 170.739758 
L 510.176229 178.116782 
L 514.442152 167.862316 
L 518.295244 169.670341 
L 522.561167 175.529383 
L 526.68948 176.960436 
L 530.955404 178.191852 
L 535.083717 168.607106 
L 539.34964 161.163891 
L 543.615564 166.806093 
L 547.743877 173.495331 
L 552.0098 181.419975 
L 556.138113 170.661369 
L 560.404036 156.247137 
L 564.66996 160.445533 
L 568.660662 152.559736 
L 572.926586 147.374097 
L 577.054899 157.950632 
L 581.320822 151.114231 
L 585.449135 156.53969 
L 589.715058 141.142435 
L 593.980982 141.748302 
L 598.109295 140.099669 
L 602.375218 140.791501 
L 606.503531 122.164733 
L 610.769455 137.381615 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_19">
    <path d="M 108.078545 239.125806 
L 112.344469 241.658053 
L 116.197561 237.895221 
L 120.463484 237.034514 
L 124.591797 238.008711 
L 128.857721 236.975751 
L 132.986034 236.308732 
L 137.251957 238.067718 
L 141.51788 241.338535 
L 145.646193 244.837236 
L 149.912117 241.684781 
L 154.04043 239.696966 
L 158.306353 242.708107 
L 162.572277 248.038901 
L 166.562979 247.673094 
L 170.828903 243.455495 
L 174.957216 241.922066 
L 179.223139 241.315904 
L 183.351452 241.556942 
L 187.617375 238.160944 
L 191.883299 236.769324 
L 196.011612 235.698977 
L 200.277535 238.959614 
L 204.405848 232.108989 
L 208.671771 230.575242 
L 212.937695 230.302782 
L 216.790787 229.300428 
L 221.05671 228.831707 
L 225.185023 227.934949 
L 229.450947 229.491832 
L 233.57926 226.982507 
L 237.845183 226.638814 
L 242.111106 227.867252 
L 246.239419 222.750659 
L 250.505343 222.556077 
L 254.633656 220.245992 
L 258.899579 219.970652 
L 263.165503 218.005081 
L 267.018595 220.943174 
L 271.284518 220.157394 
L 275.412831 219.248331 
L 279.678754 214.233103 
L 283.807067 213.153263 
L 288.072991 211.818047 
L 292.338914 208.711755 
L 296.467227 210.830324 
L 300.733151 220.360992 
L 304.861464 219.418224 
L 309.127387 228.964008 
L 313.39331 220.934193 
L 317.246403 217.004611 
L 321.512326 219.160563 
L 325.640639 216.582587 
L 329.906562 223.615871 
L 334.034875 218.06793 
L 338.300799 218.27425 
L 342.566722 223.104978 
L 346.695035 221.214782 
L 350.960958 219.445657 
L 355.089271 216.176657 
L 359.355195 212.926006 
L 363.621118 216.748285 
L 367.611821 223.692034 
L 371.877744 241.049396 
L 376.006057 231.176229 
L 380.27198 226.38837 
L 384.400293 223.456358 
L 388.666217 221.62576 
L 392.93214 216.975696 
L 397.060453 220.177775 
L 401.326377 217.614555 
L 405.45469 201.444275 
L 409.720613 192.59874 
L 413.986536 185.566632 
L 417.839628 175.067195 
L 422.105552 171.193298 
L 426.233865 168.731763 
L 430.499788 166.322528 
L 434.628101 164.425044 
L 438.894025 169.011885 
L 443.159948 166.393261 
L 447.288261 169.930925 
L 451.554184 165.727344 
L 455.682497 170.635591 
L 459.948421 166.999297 
L 464.214344 178.004064 
L 468.067436 176.731238 
L 472.33336 175.811367 
L 476.461673 187.205028 
L 480.727596 186.84258 
L 484.855909 195.524952 
L 489.121832 184.61257 
L 493.387756 186.506308 
L 497.516069 197.578383 
L 501.781992 186.909085 
L 505.910305 184.638027 
L 510.176229 191.417555 
L 514.442152 179.144448 
L 518.295244 181.536824 
L 522.561167 187.642322 
L 526.68948 189.974447 
L 530.955404 190.794618 
L 535.083717 182.297935 
L 539.34964 174.371004 
L 543.615564 181.274045 
L 547.743877 188.271077 
L 552.0098 195.492365 
L 556.138113 186.0775 
L 560.404036 171.634274 
L 564.66996 177.104284 
L 568.660662 171.765204 
L 572.926586 168.199822 
L 577.054899 177.260524 
L 581.320822 171.323568 
L 585.449135 174.16577 
L 589.715058 161.40181 
L 593.980982 163.596058 
L 598.109295 162.479886 
L 602.375218 163.770407 
L 606.503531 148.34581 
L 610.769455 159.526771 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_20">
    <path d="M 108.078545 239.125806 
L 112.344469 241.115185 
L 116.197561 237.612384 
L 120.463484 236.550811 
L 124.591797 237.788896 
L 128.857721 237.150334 
L 132.986034 236.345031 
L 137.251957 237.84922 
L 141.51788 241.46931 
L 145.646193 244.851683 
L 149.912117 241.509418 
L 154.04043 240.846713 
L 158.306353 243.88838 
L 162.572277 248.820432 
L 166.562979 247.920666 
L 170.828903 243.691636 
L 174.957216 242.921932 
L 179.223139 242.733194 
L 183.351452 242.837341 
L 187.617375 239.207576 
L 191.883299 237.897682 
L 196.011612 237.95241 
L 200.277535 240.751842 
L 204.405848 233.68671 
L 208.671771 232.002067 
L 212.937695 232.372606 
L 216.790787 231.927302 
L 221.05671 231.244113 
L 225.185023 229.58454 
L 229.450947 230.960534 
L 233.57926 229.628947 
L 237.845183 229.516108 
L 242.111106 230.919051 
L 246.239419 226.299396 
L 250.505343 225.504935 
L 254.633656 221.921408 
L 258.899579 220.410954 
L 263.165503 218.840921 
L 267.018595 221.52885 
L 271.284518 220.667539 
L 275.412831 220.819012 
L 279.678754 217.80226 
L 283.807067 215.810816 
L 288.072991 214.340125 
L 292.338914 212.854649 
L 296.467227 214.535873 
L 300.733151 223.879187 
L 304.861464 224.349915 
L 309.127387 233.702253 
L 313.39331 225.477222 
L 317.246403 222.472725 
L 321.512326 224.659069 
L 325.640639 221.011669 
L 329.906562 228.197288 
L 334.034875 222.817326 
L 338.300799 223.81877 
L 342.566722 229.465137 
L 346.695035 227.179086 
L 350.960958 225.50863 
L 355.089271 222.489476 
L 359.355195 220.017804 
L 363.621118 224.094837 
L 367.611821 231.2345 
L 371.877744 251.253818 
L 376.006057 241.586847 
L 380.27198 235.515787 
L 384.400293 233.356798 
L 388.666217 231.259661 
L 392.93214 225.294064 
L 397.060453 227.952844 
L 401.326377 226.069964 
L 405.45469 210.187292 
L 409.720613 202.485197 
L 413.986536 199.196954 
L 417.839628 187.701976 
L 422.105552 181.809167 
L 426.233865 175.969819 
L 430.499788 171.106582 
L 434.628101 172.364839 
L 438.894025 174.242235 
L 443.159948 172.255616 
L 447.288261 176.077354 
L 451.554184 171.770124 
L 455.682497 173.56105 
L 459.948421 168.490094 
L 464.214344 178.983424 
L 468.067436 177.263339 
L 472.33336 178.713698 
L 476.461673 188.115386 
L 480.727596 186.443342 
L 484.855909 195.915556 
L 489.121832 182.792556 
L 493.387756 187.631822 
L 497.516069 200.576471 
L 501.781992 188.861699 
L 505.910305 183.144105 
L 510.176229 190.904195 
L 514.442152 177.586478 
L 518.295244 179.098579 
L 522.561167 185.105113 
L 526.68948 186.230209 
L 530.955404 189.633757 
L 535.083717 179.161266 
L 539.34964 170.922978 
L 543.615564 175.965885 
L 547.743877 179.717923 
L 552.0098 185.948543 
L 556.138113 177.749992 
L 560.404036 165.078983 
L 564.66996 170.07537 
L 568.660662 165.059404 
L 572.926586 160.337627 
L 577.054899 170.335097 
L 581.320822 163.381339 
L 585.449135 169.422138 
L 589.715058 155.431192 
L 593.980982 157.847812 
L 598.109295 155.370901 
L 602.375218 158.128386 
L 606.503531 141.439285 
L 610.769455 154.404399 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_21">
    <path d="M 108.078545 239.125806 
L 112.344469 240.176777 
L 116.197561 236.963166 
L 120.463484 235.491224 
L 124.591797 238.147539 
L 128.857721 235.525002 
L 132.986034 234.07857 
L 137.251957 233.891137 
L 141.51788 238.127277 
L 145.646193 240.896795 
L 149.912117 238.525716 
L 154.04043 235.757675 
L 158.306353 238.797588 
L 162.572277 244.561869 
L 166.562979 245.508161 
L 170.828903 242.389143 
L 174.957216 241.354557 
L 179.223139 240.449255 
L 183.351452 240.07334 
L 187.617375 237.266156 
L 191.883299 236.862986 
L 196.011612 235.734789 
L 200.277535 238.739353 
L 204.405848 232.882534 
L 208.671771 232.137556 
L 212.937695 231.776813 
L 216.790787 231.038331 
L 221.05671 231.189022 
L 225.185023 230.469986 
L 229.450947 232.115525 
L 233.57926 229.202819 
L 237.845183 228.381112 
L 242.111106 228.681081 
L 246.239419 223.902692 
L 250.505343 222.900077 
L 254.633656 220.852445 
L 258.899579 220.140832 
L 263.165503 217.084228 
L 267.018595 219.730636 
L 271.284518 219.423335 
L 275.412831 218.636582 
L 279.678754 211.569298 
L 283.807067 210.659941 
L 288.072991 209.534704 
L 292.338914 204.000154 
L 296.467227 206.295537 
L 300.733151 217.054575 
L 304.861464 216.458315 
L 309.127387 225.461286 
L 313.39331 219.169411 
L 317.246403 215.006016 
L 321.512326 216.13956 
L 325.640639 214.893107 
L 329.906562 219.605051 
L 334.034875 213.841431 
L 338.300799 211.947269 
L 342.566722 214.807041 
L 346.695035 216.425669 
L 350.960958 213.685215 
L 355.089271 210.618998 
L 359.355195 207.894798 
L 363.621118 209.286777 
L 367.611821 215.81451 
L 371.877744 234.263923 
L 376.006057 222.783507 
L 380.27198 217.412875 
L 384.400293 213.242036 
L 388.666217 209.209644 
L 392.93214 205.113104 
L 397.060453 206.841373 
L 401.326377 204.921482 
L 405.45469 188.463936 
L 409.720613 178.930222 
L 413.986536 162.603775 
L 417.839628 153.508424 
L 422.105552 153.308158 
L 426.233865 150.686724 
L 430.499788 147.463014 
L 434.628101 141.201112 
L 438.894025 149.264027 
L 443.159948 144.889457 
L 447.288261 147.831787 
L 451.554184 141.183818 
L 455.682497 146.917049 
L 459.948421 144.07391 
L 464.214344 159.67282 
L 468.067436 156.538197 
L 472.33336 154.423929 
L 476.461673 164.771138 
L 480.727596 162.451726 
L 484.855909 176.076713 
L 489.121832 165.161296 
L 493.387756 165.30583 
L 497.516069 176.658963 
L 501.781992 160.712668 
L 505.910305 158.335411 
L 510.176229 165.329369 
L 514.442152 158.138153 
L 518.295244 160.242103 
L 522.561167 165.953653 
L 526.68948 167.690663 
L 530.955404 166.749946 
L 535.083717 158.052946 
L 539.34964 151.404803 
L 543.615564 157.646301 
L 547.743877 167.272738 
L 552.0098 176.891407 
L 556.138113 163.572746 
L 560.404036 147.41529 
L 564.66996 150.815697 
L 568.660662 140.060068 
L 572.926586 134.410567 
L 577.054899 145.566168 
L 581.320822 138.847124 
L 585.449135 143.657242 
L 589.715058 126.853677 
L 593.980982 125.648791 
L 598.109295 124.828437 
L 602.375218 123.454617 
L 606.503531 102.890182 
L 610.769455 120.358832 
" clip-path="url(#p7311188120)" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="patch_3">
    <path d="M 82.944 258.672 
L 82.944 95.472 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_4">
    <path d="M 82.944 258.672 
L 635.904 258.672 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_8">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="89.472" transform="rotate(-0 82.944 89.472)">盈利能力＋动量</text>
   </g>
   <g id="legend_1">
    <g id="line2d_22">
     <path d="M 91.944 109.572 
L 101.944 109.572 
L 111.944 109.572 
" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="text_9">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="113.072" transform="rotate(-0 119.944 113.072)">两组各半</text>
    </g>
    <g id="line2d_23">
     <path d="M 91.944 124.572 
L 101.944 124.572 
L 111.944 124.572 
" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_10">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="128.072" transform="rotate(-0 119.944 128.072)">来源参照</text>
    </g>
    <g id="line2d_24">
     <path d="M 179.944 109.572 
L 189.944 109.572 
L 199.944 109.572 
" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_11">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="113.072" transform="rotate(-0 207.944 113.072)">盈利能力单独</text>
    </g>
    <g id="line2d_25">
     <path d="M 179.944 124.572 
L 189.944 124.572 
L 199.944 124.572 
" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_12">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="128.072" transform="rotate(-0 207.944 128.072)">动量单独</text>
    </g>
   </g>
  </g>
  <g id="axes_2">
   <g id="patch_5">
    <path d="M 82.944 470.832 
L 635.904 470.832 
L 635.904 307.632 
L 82.944 307.632 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_3">
    <g id="xtick_6">
     <g id="line2d_26">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_7">
     <g id="line2d_27">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_8">
     <g id="line2d_28">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_9">
     <g id="line2d_29">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="xtick_10">
     <g id="line2d_30">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="470.832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_4">
    <g id="ytick_7">
     <g id="line2d_31">
      <path d="M 82.944 452.168186 
L 635.904 452.168186 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_32">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="452.168186" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_13">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="455.967015" transform="rotate(-0 75.944 455.967015)">100</text>
     </g>
    </g>
    <g id="ytick_8">
     <g id="line2d_33">
      <path d="M 82.944 423.267144 
L 635.904 423.267144 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_34">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="423.267144" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_14">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="427.065972" transform="rotate(-0 75.944 427.065972)">150</text>
     </g>
    </g>
    <g id="ytick_9">
     <g id="line2d_35">
      <path d="M 82.944 394.366101 
L 635.904 394.366101 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_36">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="394.366101" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_15">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="398.164929" transform="rotate(-0 75.944 398.164929)">200</text>
     </g>
    </g>
    <g id="ytick_10">
     <g id="line2d_37">
      <path d="M 82.944 365.465058 
L 635.904 365.465058 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_38">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="365.465058" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_16">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="369.263886" transform="rotate(-0 75.944 369.263886)">250</text>
     </g>
    </g>
    <g id="ytick_11">
     <g id="line2d_39">
      <path d="M 82.944 336.564015 
L 635.904 336.564015 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_40">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="336.564015" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_17">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="340.362843" transform="rotate(-0 75.944 340.362843)">300</text>
     </g>
    </g>
    <g id="ytick_12">
     <g id="line2d_41">
      <path d="M 82.944 307.662972 
L 635.904 307.662972 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_42">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="307.662972" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_18">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="311.4618" transform="rotate(-0 75.944 311.4618)">350</text>
     </g>
    </g>
    <g id="text_19">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="51.4565" y="389.232" transform="rotate(-90 51.4565 389.232)">初始资金100</text>
    </g>
   </g>
   <g id="line2d_43">
    <path d="M 108.078545 452.168186 
L 112.344469 454.192473 
L 116.197561 451.156306 
L 120.463484 450.070884 
L 124.591797 451.607978 
L 128.857721 450.012751 
L 132.986034 449.099207 
L 137.251957 450.668801 
L 141.51788 453.720176 
L 145.646193 456.376578 
L 149.912117 453.72142 
L 154.04043 451.345157 
L 158.306353 454.777658 
L 162.572277 459.491246 
L 166.562979 459.878177 
L 170.828903 456.257357 
L 174.957216 454.720188 
L 179.223139 454.118104 
L 183.351452 453.942572 
L 187.617375 450.950776 
L 191.883299 449.796999 
L 196.011612 448.718153 
L 200.277535 451.156092 
L 204.405848 443.77065 
L 208.671771 441.870513 
L 212.937695 441.934073 
L 216.790787 441.459957 
L 221.05671 441.780194 
L 225.185023 441.191084 
L 229.450947 443.36892 
L 233.57926 440.744517 
L 237.845183 440.116048 
L 242.111106 441.118296 
L 246.239419 435.822826 
L 250.505343 434.958803 
L 254.633656 432.93837 
L 258.899579 432.583608 
L 263.165503 430.371228 
L 267.018595 433.195785 
L 271.284518 432.313447 
L 275.412831 431.012689 
L 279.678754 425.182038 
L 283.807067 424.477381 
L 288.072991 423.455102 
L 292.338914 419.667671 
L 296.467227 422.054485 
L 300.733151 431.362167 
L 304.861464 430.699691 
L 309.127387 440.155333 
L 313.39331 433.262028 
L 317.246403 429.804876 
L 321.512326 432.064599 
L 325.640639 430.2091 
L 329.906562 436.392769 
L 334.034875 431.28311 
L 338.300799 430.540111 
L 342.566722 434.964847 
L 346.695035 433.888853 
L 350.960958 432.275151 
L 355.089271 429.49005 
L 359.355195 426.331586 
L 363.621118 430.214403 
L 367.611821 437.069693 
L 371.877744 455.344316 
L 376.006057 445.934455 
L 380.27198 442.144958 
L 384.400293 439.055061 
L 388.666217 436.29492 
L 392.93214 432.63478 
L 397.060453 435.323364 
L 401.326377 432.528669 
L 405.45469 418.094574 
L 409.720613 410.144242 
L 413.986536 397.65477 
L 417.839628 388.880041 
L 422.105552 385.244269 
L 426.233865 383.285719 
L 430.499788 378.438054 
L 434.628101 376.054077 
L 438.894025 382.142821 
L 443.159948 378.431629 
L 447.288261 379.705986 
L 451.554184 374.269953 
L 455.682497 379.266253 
L 459.948421 375.361202 
L 464.214344 383.784302 
L 468.067436 380.978818 
L 472.33336 379.594508 
L 476.461673 388.088541 
L 480.727596 384.654427 
L 484.855909 397.98829 
L 489.121832 387.984198 
L 493.387756 389.363518 
L 497.516069 400.43677 
L 501.781992 385.620962 
L 505.910305 382.975167 
L 510.176229 389.676416 
L 514.442152 381.614637 
L 518.295244 383.707517 
L 522.561167 392.001896 
L 526.68948 394.256634 
L 530.955404 395.998139 
L 535.083717 387.624199 
L 539.34964 379.452534 
L 543.615564 385.70814 
L 547.743877 393.852031 
L 552.0098 401.842128 
L 556.138113 390.155185 
L 560.404036 373.946496 
L 564.66996 378.768425 
L 568.660662 371.978833 
L 572.926586 366.958245 
L 577.054899 376.449561 
L 581.320822 370.612837 
L 585.449135 374.06954 
L 589.715058 357.93317 
L 593.980982 358.816349 
L 598.109295 358.477261 
L 602.375218 358.463769 
L 606.503531 340.890643 
L 610.769455 354.773262 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_44">
    <path d="M 108.078545 452.168186 
L 112.344469 454.73562 
L 116.197561 450.967148 
L 120.463484 450.125688 
L 124.591797 451.085992 
L 128.857721 449.996185 
L 132.986034 449.338886 
L 137.251957 451.16814 
L 141.51788 454.419098 
L 145.646193 457.961375 
L 149.912117 454.829493 
L 154.04043 452.628813 
L 158.306353 455.658117 
L 162.572277 461.105541 
L 166.562979 460.835108 
L 170.828903 456.63022 
L 174.957216 455.006454 
L 179.223139 454.334314 
L 183.351452 454.561662 
L 187.617375 451.158709 
L 191.883299 449.784359 
L 196.011612 448.568695 
L 200.277535 451.891153 
L 204.405848 445.005563 
L 208.671771 443.495648 
L 212.937695 443.156883 
L 216.790787 442.07773 
L 221.05671 441.639035 
L 225.185023 440.797202 
L 229.450947 442.380027 
L 233.57926 439.7253 
L 237.845183 439.320121 
L 242.111106 440.516931 
L 246.239419 435.357503 
L 250.505343 435.156876 
L 254.633656 432.993199 
L 258.899579 432.869717 
L 263.165503 430.849656 
L 267.018595 433.798908 
L 271.284518 432.930935 
L 275.412831 431.873525 
L 279.678754 426.574075 
L 283.807067 425.543802 
L 288.072991 424.236619 
L 292.338914 420.902415 
L 296.467227 423.075379 
L 300.733151 432.719971 
L 304.861464 431.619826 
L 309.127387 441.263184 
L 313.39331 433.198606 
L 317.246403 429.170897 
L 321.512326 431.3238 
L 325.640639 428.864009 
L 329.906562 435.935417 
L 334.034875 430.367178 
L 338.300799 430.525037 
L 342.566722 435.301106 
L 346.695035 433.475995 
L 350.960958 431.663889 
L 355.089271 428.3161 
L 359.355195 424.968221 
L 363.621118 428.841753 
L 367.611821 435.758467 
L 371.877744 452.95397 
L 376.006057 443.100843 
L 380.27198 438.52455 
L 384.400293 435.476658 
L 388.666217 433.666699 
L 392.93214 429.18983 
L 397.060453 432.350212 
L 401.326377 429.699053 
L 405.45469 413.315195 
L 409.720613 404.171689 
L 413.986536 396.434664 
L 417.839628 386.221484 
L 422.105552 382.779519 
L 426.233865 380.706254 
L 430.499788 378.607719 
L 434.628101 376.24057 
L 438.894025 381.180434 
L 443.159948 378.37178 
L 447.288261 381.703869 
L 451.554184 377.398339 
L 455.682497 382.866326 
L 459.948421 379.256641 
L 464.214344 389.995906 
L 468.067436 388.74414 
L 472.33336 387.524884 
L 476.461673 399.199342 
L 480.727596 399.001838 
L 484.855909 407.565984 
L 489.121832 396.617157 
L 493.387756 398.128428 
L 497.516069 409.074505 
L 501.781992 398.376966 
L 505.910305 396.477993 
L 510.176229 403.201942 
L 514.442152 390.985459 
L 518.295244 393.501118 
L 522.561167 399.814104 
L 526.68948 402.279988 
L 530.955404 403.003503 
L 535.083717 394.636419 
L 539.34964 386.6664 
L 543.615564 394.065958 
L 547.743877 401.493407 
L 552.0098 409.070034 
L 556.138113 399.414116 
L 560.404036 384.654454 
L 564.66996 390.237987 
L 568.660662 384.73331 
L 572.926586 381.423879 
L 577.054899 390.568139 
L 581.320822 384.642311 
L 585.449135 387.09431 
L 589.715058 374.404444 
L 593.980982 376.47507 
L 598.109295 375.4713 
L 602.375218 376.54879 
L 606.503531 360.960884 
L 610.769455 371.990258 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_45">
    <path d="M 108.078545 452.168186 
L 112.344469 455.158982 
L 116.197561 452.321073 
L 120.463484 451.631703 
L 124.591797 452.032373 
L 128.857721 451.481441 
L 132.986034 451.110154 
L 137.251957 454.437988 
L 141.51788 456.277161 
L 145.646193 458.802509 
L 149.912117 455.87863 
L 154.04043 453.912074 
L 158.306353 457.717473 
L 162.572277 461.343033 
L 166.562979 461.164474 
L 170.828903 457.062054 
L 174.957216 455.029003 
L 179.223139 454.736001 
L 183.351452 454.763287 
L 187.617375 451.605061 
L 191.883299 449.703289 
L 196.011612 448.6811 
L 200.277535 450.532953 
L 204.405848 441.656821 
L 208.671771 438.606352 
L 212.937695 439.096551 
L 216.790787 438.891584 
L 221.05671 439.380392 
L 225.185023 438.925864 
L 229.450947 441.625338 
L 233.57926 439.308103 
L 237.845183 438.878195 
L 242.111106 440.580779 
L 246.239419 434.799177 
L 250.505343 434.080241 
L 254.633656 432.10027 
L 258.899579 432.106967 
L 263.165503 430.758608 
L 267.018595 433.744175 
L 271.284518 432.28879 
L 275.412831 430.479122 
L 279.678754 425.930877 
L 283.807067 425.436809 
L 288.072991 424.524778 
L 292.338914 422.520312 
L 296.467227 424.98369 
L 300.733151 432.77033 
L 304.861464 432.0455 
L 309.127387 441.895503 
L 313.39331 434.44152 
L 317.246403 431.717576 
L 321.512326 435.096136 
L 325.640639 432.639665 
L 329.906562 440.26454 
L 334.034875 435.846173 
L 338.300799 436.266605 
L 342.566722 442.237781 
L 346.695035 438.456682 
L 350.960958 437.987482 
L 355.089271 435.503356 
L 359.355195 431.928273 
L 363.621118 438.292911 
L 367.611821 445.433481 
L 371.877744 463.413818 
L 376.006057 456.14887 
L 380.27198 453.975292 
L 384.400293 451.99335 
L 388.666217 450.531578 
L 392.93214 447.334371 
L 397.060453 450.972076 
L 401.326377 447.315014 
L 405.45469 435.010962 
L 409.720613 428.70576 
L 413.986536 420.159008 
L 417.839628 411.763811 
L 422.105552 404.693829 
L 426.233865 403.415142 
L 430.499788 396.964401 
L 434.628101 398.498907 
L 438.894025 402.561258 
L 443.159948 399.541776 
L 447.288261 399.129105 
L 451.554184 394.948065 
L 455.682497 399.1703 
L 459.948421 394.221752 
L 464.214344 395.36801 
L 468.067436 392.911968 
L 472.33336 392.271308 
L 476.461673 398.845149 
L 480.727596 394.311355 
L 484.855909 407.265847 
L 489.121832 398.243777 
L 493.387756 400.856948 
L 497.516069 411.576787 
L 501.781992 397.994747 
L 505.910305 395.095812 
L 510.176229 401.459053 
L 514.442152 392.573287 
L 518.295244 394.641469 
L 522.561167 405.481685 
L 526.68948 408.2429 
L 530.955404 412.67272 
L 535.083717 404.67817 
L 539.34964 395.026043 
L 543.615564 401.25533 
L 547.743877 407.854327 
L 552.0098 414.153554 
L 556.138113 404.184591 
L 560.404036 388.029319 
L 564.66996 394.250746 
L 568.660662 391.496853 
L 572.926586 387.14177 
L 577.054899 394.896547 
L 581.320822 389.985661 
L 585.449135 392.057795 
L 589.715058 376.697455 
L 593.980982 379.676502 
L 598.109295 379.823995 
L 602.375218 381.179728 
L 606.503531 366.731104 
L 610.769455 376.914549 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_46">
    <path d="M 108.078545 452.168186 
L 112.344469 453.225965 
L 116.197561 449.991539 
L 120.463484 448.510064 
L 124.591797 451.183583 
L 128.857721 448.544061 
L 132.986034 447.08826 
L 137.251957 446.899614 
L 141.51788 451.16319 
L 145.646193 453.950646 
L 149.912117 451.56421 
L 154.04043 448.778241 
L 158.306353 451.837842 
L 162.572277 457.639459 
L 166.562979 458.59188 
L 170.828903 455.45266 
L 174.957216 454.411373 
L 179.223139 453.500208 
L 183.351452 453.121858 
L 187.617375 450.296492 
L 191.883299 449.89071 
L 196.011612 448.755207 
L 200.277535 451.779231 
L 204.405848 445.884478 
L 208.671771 445.134674 
L 212.937695 444.771595 
L 216.790787 444.02833 
L 221.05671 444.179997 
L 225.185023 443.456304 
L 229.450947 445.112501 
L 233.57926 442.18093 
L 237.845183 441.3539 
L 242.111106 441.655812 
L 246.239419 436.846474 
L 250.505343 435.837366 
L 254.633656 433.776471 
L 258.899579 433.060249 
L 263.165503 429.983848 
L 267.018595 432.647396 
L 271.284518 432.338105 
L 275.412831 431.546257 
L 279.678754 424.433199 
L 283.807067 423.517952 
L 288.072991 422.385427 
L 292.338914 416.81503 
L 296.467227 419.12528 
L 300.733151 429.954003 
L 304.861464 429.353881 
L 309.127387 438.415164 
L 313.39331 432.082537 
L 317.246403 427.892176 
L 321.512326 429.033062 
L 325.640639 427.778535 
L 329.906562 432.520998 
L 334.034875 426.720048 
L 338.300799 424.813618 
L 342.566722 427.691913 
L 346.695035 429.321024 
L 350.960958 426.56282 
L 355.089271 423.476744 
L 359.355195 420.734899 
L 363.621118 422.135895 
L 367.611821 428.705906 
L 371.877744 447.274814 
L 376.006057 435.720041 
L 380.27198 430.314624 
L 384.400293 426.116771 
L 388.666217 422.058262 
L 392.93214 417.935188 
L 397.060453 419.674652 
L 401.326377 417.742325 
L 405.45469 401.178186 
L 409.720613 391.582724 
L 413.986536 375.150532 
L 417.839628 365.996272 
L 422.105552 365.794708 
L 426.233865 363.156296 
L 430.499788 359.911707 
L 434.628101 353.609247 
L 438.894025 361.724384 
L 443.159948 357.321481 
L 447.288261 360.282868 
L 451.554184 353.591841 
L 455.682497 359.362205 
L 459.948421 356.500652 
L 464.214344 372.200594 
L 468.067436 369.045668 
L 472.33336 366.917707 
L 476.461673 377.331933 
L 480.727596 374.997499 
L 484.855909 388.710732 
L 489.121832 377.724618 
L 493.387756 377.870088 
L 497.516069 389.296754 
L 501.781992 373.247176 
L 505.910305 370.854522 
L 510.176229 377.893779 
L 514.442152 370.655987 
L 518.295244 372.773565 
L 522.561167 378.522107 
L 526.68948 380.270367 
L 530.955404 379.323558 
L 535.083717 370.570228 
L 539.34964 363.879026 
L 543.615564 370.160949 
L 547.743877 379.849736 
L 552.0098 389.530703 
L 556.138113 376.125779 
L 560.404036 359.863674 
L 564.66996 363.286104 
L 568.660662 352.460812 
L 572.926586 346.774721 
L 577.054899 358.002575 
L 581.320822 351.240012 
L 585.449135 356.081285 
L 589.715058 339.168886 
L 593.980982 337.956196 
L 598.109295 337.130528 
L 602.375218 335.74781 
L 606.503531 315.050182 
L 610.769455 332.631974 
" clip-path="url(#pf527fceebe)" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="patch_6">
    <path d="M 82.944 470.832 
L 82.944 307.632 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_7">
    <path d="M 82.944 470.832 
L 635.904 470.832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_20">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="301.632" transform="rotate(-0 82.944 301.632)">价值＋动量</text>
   </g>
   <g id="legend_2">
    <g id="line2d_47">
     <path d="M 91.944 321.732 
L 101.944 321.732 
L 111.944 321.732 
" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="text_21">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="325.232" transform="rotate(-0 119.944 325.232)">两组各半</text>
    </g>
    <g id="line2d_48">
     <path d="M 91.944 336.732 
L 101.944 336.732 
L 111.944 336.732 
" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_22">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="340.232" transform="rotate(-0 119.944 340.232)">来源参照</text>
    </g>
    <g id="line2d_49">
     <path d="M 179.944 321.732 
L 189.944 321.732 
L 199.944 321.732 
" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_23">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="325.232" transform="rotate(-0 207.944 325.232)">价值单独</text>
    </g>
    <g id="line2d_50">
     <path d="M 179.944 336.732 
L 189.944 336.732 
L 199.944 336.732 
" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_24">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="340.232" transform="rotate(-0 207.944 340.232)">动量单独</text>
    </g>
   </g>
  </g>
  <g id="axes_3">
   <g id="patch_8">
    <path d="M 82.944 682.992 
L 635.904 682.992 
L 635.904 519.792 
L 82.944 519.792 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_5">
    <g id="xtick_11">
     <g id="line2d_51">
      <g>
       <use xlink:href="#m80ae50af5d" x="158.443964" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_25">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="158.443964" y="697.589656" transform="rotate(-0 158.443964 697.589656)">2016</text>
     </g>
    </g>
    <g id="xtick_12">
     <g id="line2d_52">
      <g>
       <use xlink:href="#m80ae50af5d" x="259.03719" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_26">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="259.03719" y="697.589656" transform="rotate(-0 259.03719 697.589656)">2018</text>
     </g>
    </g>
    <g id="xtick_13">
     <g id="line2d_53">
      <g>
       <use xlink:href="#m80ae50af5d" x="359.492805" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_27">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="359.492805" y="697.589656" transform="rotate(-0 359.492805 697.589656)">2020</text>
     </g>
    </g>
    <g id="xtick_14">
     <g id="line2d_54">
      <g>
       <use xlink:href="#m80ae50af5d" x="460.086031" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_28">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="460.086031" y="697.589656" transform="rotate(-0 460.086031 697.589656)">2022</text>
     </g>
    </g>
    <g id="xtick_15">
     <g id="line2d_55">
      <g>
       <use xlink:href="#m80ae50af5d" x="560.541647" y="682.992" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_29">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="560.541647" y="697.589656" transform="rotate(-0 560.541647 697.589656)">2024</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_6">
    <g id="ytick_13">
     <g id="line2d_56">
      <path d="M 82.944 659.188409 
L 635.904 659.188409 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_57">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="659.188409" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_30">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="662.987237" transform="rotate(-0 75.944 662.987237)">100</text>
     </g>
    </g>
    <g id="ytick_14">
     <g id="line2d_58">
      <path d="M 82.944 620.393266 
L 635.904 620.393266 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_59">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="620.393266" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_31">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="624.192094" transform="rotate(-0 75.944 624.192094)">150</text>
     </g>
    </g>
    <g id="ytick_15">
     <g id="line2d_60">
      <path d="M 82.944 581.598122 
L 635.904 581.598122 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_61">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="581.598122" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_32">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="585.39695" transform="rotate(-0 75.944 585.39695)">200</text>
     </g>
    </g>
    <g id="ytick_16">
     <g id="line2d_62">
      <path d="M 82.944 542.802979 
L 635.904 542.802979 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_63">
      <g>
       <use xlink:href="#m7712ef1b3c" x="82.944" y="542.802979" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_33">
      <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: end" x="75.944" y="546.601807" transform="rotate(-0 75.944 546.601807)">250</text>
     </g>
    </g>
    <g id="text_34">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: middle" x="51.4565" y="601.392" transform="rotate(-90 51.4565 601.392)">初始资金100</text>
    </g>
   </g>
   <g id="line2d_64">
    <path d="M 108.078545 659.188409 
L 112.344469 662.539611 
L 116.197561 658.268677 
L 120.463484 657.088878 
L 124.591797 658.194147 
L 128.857721 657.393016 
L 132.986034 656.599821 
L 137.251957 659.849478 
L 141.51788 663.52932 
L 145.646193 667.509121 
L 149.912117 663.288931 
L 154.04043 661.521364 
L 158.306353 666.130145 
L 162.572277 671.895216 
L 166.562979 671.167562 
L 170.828903 665.557342 
L 174.957216 663.672865 
L 179.223139 663.348714 
L 183.351452 663.437381 
L 187.617375 658.865692 
L 191.883299 656.704418 
L 196.011612 656.055324 
L 200.277535 659.189305 
L 204.405848 648.459262 
L 208.671771 645.273863 
L 212.937695 645.853177 
L 216.790787 645.414798 
L 221.05671 645.281365 
L 225.185023 643.855225 
L 229.450947 646.596547 
L 233.57926 644.141772 
L 237.845183 643.777004 
L 242.111106 645.867445 
L 246.239419 638.866331 
L 250.505343 637.847127 
L 254.633656 634.097485 
L 258.899579 633.081639 
L 263.165503 631.116071 
L 267.018595 634.935648 
L 271.284518 633.377002 
L 275.412831 632.264727 
L 279.678754 627.174198 
L 283.807067 625.497335 
L 288.072991 623.891724 
L 292.338914 621.542916 
L 296.467227 624.331965 
L 300.733151 635.869728 
L 304.861464 635.701228 
L 309.127387 648.629958 
L 313.39331 638.070887 
L 317.246403 634.213057 
L 321.512326 637.957569 
L 325.640639 633.844966 
L 329.906562 643.816592 
L 334.034875 637.21684 
L 338.300799 638.175517 
L 342.566722 645.997433 
L 346.695035 641.915393 
L 350.960958 640.472054 
L 355.089271 636.765282 
L 359.355195 632.696125 
L 363.621118 639.722005 
L 367.611821 649.337535 
L 371.877744 674.928867 
L 376.006057 663.522613 
L 380.27198 657.962652 
L 384.400293 655.173989 
L 388.666217 652.776232 
L 392.93214 646.600481 
L 397.060453 650.838064 
L 401.326377 647.111625 
L 405.45469 628.12444 
L 409.720613 618.689652 
L 413.986536 610.732041 
L 417.839628 597.332341 
L 422.105552 588.606462 
L 426.233865 583.803652 
L 430.499788 576.188885 
L 434.628101 578.068779 
L 438.894025 582.063533 
L 443.159948 578.694942 
L 447.288261 580.999625 
L 451.554184 575.283813 
L 455.682497 579.327463 
L 459.948421 572.580609 
L 464.214344 580.43839 
L 468.067436 577.628013 
L 472.33336 578.177765 
L 476.461673 588.940963 
L 480.727596 584.768509 
L 484.855909 599.861865 
L 489.121832 584.941666 
L 493.387756 589.96457 
L 497.516069 605.903784 
L 501.781992 588.874346 
L 505.910305 583.066318 
L 510.176229 592.579237 
L 514.442152 577.618986 
L 518.295244 580.028546 
L 522.561167 591.361724 
L 526.68948 593.974998 
L 530.955404 599.247331 
L 535.083717 586.807244 
L 539.34964 574.763885 
L 543.615564 582.351389 
L 547.743877 589.315025 
L 552.0098 597.751792 
L 556.138113 585.522625 
L 560.404036 566.12015 
L 564.66996 573.670952 
L 568.660662 568.434235 
L 572.926586 562.321575 
L 577.054899 574.279847 
L 581.320822 566.286401 
L 585.449135 571.757835 
L 589.715058 551.997252 
L 593.980982 555.629178 
L 598.109295 554.05497 
L 602.375218 556.827635 
L 606.503531 535.856315 
L 610.769455 551.449341 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="line2d_65">
    <path d="M 108.078545 659.188409 
L 112.344469 662.502316 
L 116.197561 657.577116 
L 120.463484 656.204083 
L 124.591797 657.825862 
L 128.857721 656.181639 
L 132.986034 655.180747 
L 137.251957 657.347069 
L 141.51788 661.978835 
L 145.646193 666.229998 
L 149.912117 662.147959 
L 154.04043 659.267733 
L 158.306353 663.295881 
L 162.572277 670.215274 
L 166.562979 669.950008 
L 170.828903 664.592258 
L 174.957216 662.843168 
L 179.223139 661.922386 
L 183.351452 661.997266 
L 187.617375 657.405872 
L 191.883299 655.448998 
L 196.011612 653.941 
L 200.277535 658.415958 
L 204.405848 648.88482 
L 208.671771 646.792771 
L 212.937695 646.541505 
L 216.790787 645.28363 
L 221.05671 644.728208 
L 225.185023 643.453332 
L 229.450947 645.387778 
L 233.57926 642.103767 
L 237.845183 641.588571 
L 242.111106 643.245531 
L 246.239419 636.350617 
L 250.505343 635.785273 
L 254.633656 632.861406 
L 258.899579 632.620936 
L 263.165503 629.957591 
L 267.018595 633.732353 
L 271.284518 632.367155 
L 275.412831 630.966642 
L 279.678754 623.830083 
L 283.807067 622.362261 
L 288.072991 620.511018 
L 292.338914 616.35934 
L 296.467227 619.275418 
L 300.733151 632.498666 
L 304.861464 631.297206 
L 309.127387 644.212505 
L 313.39331 633.632172 
L 317.246403 628.503508 
L 321.512326 631.374215 
L 325.640639 627.738275 
L 329.906562 636.922966 
L 334.034875 629.422604 
L 338.300799 629.740872 
L 342.566722 636.367041 
L 346.695035 633.905802 
L 350.960958 631.331869 
L 355.089271 626.883364 
L 359.355195 622.593479 
L 363.621118 628.004415 
L 367.611821 637.195773 
L 371.877744 660.343567 
L 376.006057 648.095759 
L 380.27198 641.719028 
L 384.400293 638.196791 
L 388.666217 635.764965 
L 392.93214 629.621515 
L 397.060453 633.58073 
L 401.326377 630.438097 
L 405.45469 608.924639 
L 409.720613 596.587452 
L 413.986536 587.528335 
L 417.839628 574.663328 
L 422.105552 569.881286 
L 426.233865 566.34762 
L 430.499788 562.502254 
L 434.628101 560.398442 
L 438.894025 566.51163 
L 443.159948 562.766333 
L 447.288261 567.449245 
L 451.554184 561.422751 
L 455.682497 567.843029 
L 459.948421 562.918258 
L 464.214344 576.928593 
L 468.067436 575.099273 
L 472.33336 573.54504 
L 476.461673 588.347642 
L 480.727596 587.405377 
L 484.855909 598.787002 
L 489.121832 583.437557 
L 493.387756 586.103979 
L 497.516069 601.130142 
L 501.781992 586.819395 
L 505.910305 583.909964 
L 510.176229 593.466146 
L 514.442152 577.248269 
L 518.295244 580.109292 
L 522.561167 588.463779 
L 526.68948 591.369628 
L 530.955404 592.580508 
L 535.083717 580.867564 
L 539.34964 570.086431 
L 543.615564 579.850157 
L 547.743877 589.093159 
L 552.0098 599.135636 
L 556.138113 586.127017 
L 560.404036 566.711623 
L 564.66996 574.185421 
L 568.660662 566.80886 
L 572.926586 562.095895 
L 577.054899 574.342299 
L 581.320822 566.3705 
L 585.449135 569.771764 
L 589.715058 552.099458 
L 593.980982 554.941155 
L 598.109295 553.242112 
L 602.375218 555.179035 
L 606.503531 533.25144 
L 610.769455 548.886365 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_66">
    <path d="M 108.078545 659.188409 
L 112.344469 663.203086 
L 116.197561 659.393635 
L 120.463484 658.468265 
L 124.591797 659.006101 
L 128.857721 658.266561 
L 132.986034 657.768166 
L 137.251957 662.235263 
L 141.51788 664.704067 
L 145.646193 668.093953 
L 149.912117 664.169101 
L 154.04043 661.529307 
L 158.306353 666.637461 
L 162.572277 671.504211 
L 166.562979 671.264523 
L 170.828903 665.757663 
L 174.957216 663.028609 
L 179.223139 662.6353 
L 183.351452 662.671927 
L 187.617375 658.432501 
L 191.883299 655.879668 
L 196.011612 654.50754 
L 200.277535 656.993363 
L 204.405848 645.07854 
L 208.671771 640.983762 
L 212.937695 641.641777 
L 216.790787 641.366641 
L 221.05671 642.02279 
L 225.185023 641.412656 
L 229.450947 645.03628 
L 233.57926 641.925753 
L 237.845183 641.348668 
L 242.111106 643.634122 
L 246.239419 635.873223 
L 250.505343 634.908163 
L 254.633656 632.25036 
L 258.899579 632.25935 
L 263.165503 630.449388 
L 267.018595 634.457046 
L 271.284518 632.503419 
L 275.412831 630.074222 
L 279.678754 623.968912 
L 283.807067 623.305703 
L 288.072991 622.081443 
L 292.338914 619.39076 
L 296.467227 622.697461 
L 300.733151 633.149812 
L 304.861464 632.176841 
L 309.127387 645.398934 
L 313.39331 635.393124 
L 317.246403 631.736653 
L 321.512326 636.271843 
L 325.640639 632.974414 
L 329.906562 643.20962 
L 334.034875 637.278651 
L 338.300799 637.843015 
L 342.566722 645.858388 
L 346.695035 640.782853 
L 350.960958 640.153024 
L 355.089271 636.818472 
L 359.355195 632.019482 
L 363.621118 640.563015 
L 367.611821 650.148117 
L 371.877744 674.283916 
L 376.006057 664.531856 
L 380.27198 661.614167 
L 384.400293 658.953719 
L 388.666217 656.991518 
L 392.93214 652.699765 
L 397.060453 657.582817 
L 401.326377 652.673782 
L 405.45469 636.157511 
L 409.720613 627.69376 
L 413.986536 616.221079 
L 417.839628 604.951835 
L 422.105552 595.461487 
L 426.233865 593.745049 
L 430.499788 585.085935 
L 434.628101 587.145771 
L 438.894025 592.598843 
L 443.159948 588.545659 
L 447.288261 587.991712 
L 451.554184 582.379319 
L 455.682497 588.047011 
L 459.948421 581.404356 
L 464.214344 582.943029 
L 468.067436 579.646176 
L 472.33336 578.78619 
L 476.461673 587.610546 
L 480.727596 581.524634 
L 484.855909 598.914021 
L 489.121832 586.803298 
L 493.387756 590.311073 
L 497.516069 604.700784 
L 501.781992 586.469014 
L 505.910305 582.577646 
L 510.176229 591.119305 
L 514.442152 579.191549 
L 518.295244 581.967762 
L 522.561167 596.519061 
L 526.68948 600.225562 
L 530.955404 606.171905 
L 535.083717 595.440467 
L 539.34964 582.483991 
L 543.615564 590.845839 
L 547.743877 599.703963 
L 552.0098 608.159692 
L 556.138113 594.777914 
L 560.404036 573.09198 
L 564.66996 581.443276 
L 568.660662 577.746604 
L 572.926586 571.900584 
L 577.054899 582.310164 
L 581.320822 575.718065 
L 585.449135 578.499582 
L 589.715058 557.88072 
L 593.980982 561.879627 
L 598.109295 562.077612 
L 602.375218 563.897474 
L 606.503531 544.502448 
L 610.769455 558.172135 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="line2d_67">
    <path d="M 108.078545 659.188409 
L 112.344469 661.876137 
L 116.197561 657.143718 
L 120.463484 655.709492 
L 124.591797 657.382193 
L 128.857721 656.519471 
L 132.986034 655.431477 
L 137.251957 657.463693 
L 141.51788 662.354573 
L 145.646193 666.924289 
L 149.912117 662.40876 
L 154.04043 661.513421 
L 158.306353 665.622829 
L 162.572277 672.286221 
L 166.562979 671.070602 
L 170.828903 665.35702 
L 174.957216 664.317121 
L 179.223139 664.062128 
L 183.351452 664.202835 
L 187.617375 659.298884 
L 191.883299 657.529168 
L 196.011612 657.603107 
L 200.277535 661.385246 
L 204.405848 651.839983 
L 208.671771 649.563965 
L 212.937695 650.064578 
L 216.790787 649.462955 
L 221.05671 648.539941 
L 225.185023 646.297794 
L 229.450947 648.156814 
L 233.57926 646.35779 
L 237.845183 646.205341 
L 242.111106 648.100769 
L 246.239419 641.859439 
L 250.505343 640.786092 
L 254.633656 635.944609 
L 258.899579 633.903929 
L 263.165503 631.782754 
L 267.018595 635.414249 
L 271.284518 634.250585 
L 275.412831 634.455231 
L 279.678754 630.379483 
L 283.807067 627.688966 
L 288.072991 625.702006 
L 292.338914 623.695072 
L 296.467227 625.96647 
L 300.733151 638.589644 
L 304.861464 639.225615 
L 309.127387 651.860983 
L 313.39331 640.748651 
L 317.246403 636.689461 
L 321.512326 639.643294 
L 325.640639 634.715518 
L 329.906562 644.423563 
L 334.034875 637.15503 
L 338.300799 638.508019 
L 342.566722 646.136477 
L 346.695035 643.047934 
L 350.960958 640.791084 
L 355.089271 636.712091 
L 359.355195 633.372768 
L 363.621118 638.880995 
L 367.611821 648.526954 
L 371.877744 675.573818 
L 376.006057 662.51337 
L 380.27198 654.311136 
L 384.400293 651.394259 
L 388.666217 648.560947 
L 392.93214 640.501197 
L 397.060453 644.093311 
L 401.326377 641.549468 
L 405.45469 620.09137 
L 409.720613 609.685544 
L 413.986536 605.243003 
L 417.839628 589.712847 
L 422.105552 581.751437 
L 426.233865 573.862255 
L 430.499788 567.291835 
L 434.628101 568.991788 
L 438.894025 571.528223 
L 443.159948 568.844225 
L 447.288261 574.007538 
L 451.554184 568.188306 
L 455.682497 570.607916 
L 459.948421 563.756861 
L 464.214344 577.933751 
L 468.067436 575.609849 
L 472.33336 577.56934 
L 476.461673 590.271381 
L 480.727596 588.012385 
L 484.855909 600.809709 
L 489.121832 583.080033 
L 493.387756 589.618067 
L 497.516069 607.106783 
L 501.781992 591.279678 
L 505.910305 583.554989 
L 510.176229 594.039168 
L 514.442152 576.046422 
L 518.295244 578.08933 
L 522.561167 586.204386 
L 526.68948 587.724434 
L 530.955404 592.322758 
L 535.083717 578.174021 
L 539.34964 567.04378 
L 543.615564 573.856939 
L 547.743877 578.926087 
L 552.0098 587.343893 
L 556.138113 576.267337 
L 560.404036 559.148319 
L 564.66996 565.898628 
L 568.660662 559.121867 
L 572.926586 552.742565 
L 577.054899 566.249529 
L 581.320822 556.854736 
L 585.449135 565.016087 
L 589.715058 546.113784 
L 593.980982 549.37873 
L 598.109295 546.032328 
L 602.375218 549.757796 
L 606.503531 527.210182 
L 610.769455 544.726547 
" clip-path="url(#pd228cd0829)" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="patch_9">
    <path d="M 82.944 682.992 
L 82.944 519.792 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_10">
    <path d="M 82.944 682.992 
L 635.904 682.992 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_35">
    <text style="font-size: 13px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="82.944" y="513.792" transform="rotate(-0 82.944 513.792)">价值＋盈利能力</text>
   </g>
   <g id="legend_3">
    <g id="line2d_68">
     <path d="M 91.944 533.892 
L 101.944 533.892 
L 111.944 533.892 
" style="fill: none; stroke: #2563eb; stroke-opacity: 0.95; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="text_36">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="537.392" transform="rotate(-0 119.944 537.392)">两组各半</text>
    </g>
    <g id="line2d_69">
     <path d="M 91.944 548.892 
L 101.944 548.892 
L 111.944 548.892 
" style="fill: none; stroke: #64748b; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_37">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="119.944" y="552.392" transform="rotate(-0 119.944 552.392)">来源参照</text>
    </g>
    <g id="line2d_70">
     <path d="M 179.944 533.892 
L 189.944 533.892 
L 199.944 533.892 
" style="fill: none; stroke: #c2410c; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_38">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="537.392" transform="rotate(-0 207.944 537.392)">价值单独</text>
    </g>
    <g id="line2d_71">
     <path d="M 179.944 548.892 
L 189.944 548.892 
L 199.944 548.892 
" style="fill: none; stroke: #15803d; stroke-opacity: 0.95; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="text_39">
     <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="207.944" y="552.392" transform="rotate(-0 207.944 552.392)">盈利能力单独</text>
    </g>
   </g>
  </g>
  <g id="text_40">
   <text style="font-size: 17px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; text-anchor: start" x="76.032" y="24.2352" transform="rotate(-0 76.032 24.2352)">较小规模美国股票：从100开始的公开资金路径</text>
  </g>
  <g id="text_41">
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 36.7016)">2015—2024 · 起始各半，以后不调配 · 毛收益，个人净费用未评价</text>
   <text style="font-size: 10px; font-family: 'DejaVu Sans', 'Bitstream Vera Sans', 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica', 'Avant Garde', sans-serif; fill: #475569" transform="translate(76.032 47.0016)">参照是两种来源三组平均的组合，并非母指数；月末观察，全部已见历史</text>
  </g>
 </g>
 <defs>
  <clipPath id="p7311188120">
   <rect x="82.944" y="95.472" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pf527fceebe">
   <rect x="82.944" y="307.632" width="552.96" height="163.2"/>
  </clipPath>
  <clipPath id="pd228cd0829">
   <rect x="82.944" y="519.792" width="552.96" height="163.2"/>
  </clipPath>
 </defs>
</svg>




## 3. 专业经验具体接到了哪里

**已经修改本项目 `lei-lowfreq-research` 技能，增加按需入口与组合方法说明。** 它继续使用原合同、登记表和负责人，没有新增研究平台。它是工作要求，不是所有程序入口的强制检查器。

| 外部实践 | 本轮吸收的具体动作 | 采用状态与边界 |
| --- | --- | --- |
| AQR区分先建独立策略再分配资金、先合并信息再选股 | 合同先写是哪一种问题；本轮已完成固定资金组合比较 | 复用[已有方法卡的学习入口](/learning?path=classic-process)，未声称完成联合选股 |
| 价值与动量的互补研究 | 候选先有金融理由，再测本地相关与共同亏损 | 已固定价值＋动量；论文中的相关性不作为本地结果。[官方摘要](https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere) |
| 盈利与价值的研究 | 先核盈利公式与适用股票，防止同名换口径 | 已明确原文毛利润÷资产与本次经营盈利÷权益不同，原文排除金融企业；只借鉴理由。[作者工作稿](https://mysimon.rochester.edu/novy-marx/research/OSoV.pdf) |
| 股票共同风险与风格分散 | 同时看原始涨跌相关、相对各自参照的差额相关和共同亏损 | 已真实计算并独立核数；相对差额不称独立收益。外部部分分散例子涉及做空与扩大投入，不能照搬。[AQR说明](https://www.aqr.com/Insights/Research/Journal-Article/Understanding-Expected-Returns) |
| Microsoft RD-Agent的假设—实施—反馈循环 | 将假设、依赖的旧结果、代码、结果或失败及下一证据串进当前合同；记录实施错误和金融反例的区别 | 借鉴流程、未安装运行该软件；不采用无限生成候选追好成绩的循环。[源码入口](https://github.com/microsoft/RD-Agent/blob/main/rdagent/app/qlib_rd_loop/quant.py) |

技能具体位置：`.agents/skills/lei-lowfreq-research/SKILL.md` → `references/strategy-combinations.md`。现有QuantConnect完整策略分工、现实成交模型和CFA表现评价资料继续复用原方法卡。没有安装外部Skill、Qlib、LEAN、Alphalens或付费数据服务；本次未发现必须安装才能回答当前有限问题的理由。

本轮新增外部请求6次：2次检索、4个原始页面/源码/PDF读取，均取得内容；无行情下载。实际阅读范围：AQR两页为官方摘要；Novy-Marx为2012年6月工作稿摘要、引言与§2/2.1至印刷页6；RD-Agent读取当前main的主要流程，未固定提交、未审完整依赖，不声称读完论文或完成软件审计。已有AQR2017整合方法复用2026-10-20读过的范围。

## 4. 新比较已固定的资金、时期与反例

所有6格都保留，其中大规模盈利＋动量为旧结果复用，新增5格；不会按效果只挑最好一格。主期固定2015—2024，另用1963-07—2014-12和2025-01—2026-08检查时期依赖，主期120个月、早期618个月、近期20个月。这些都是已经公开、已经看过的历史，不能称真正未来验证。

每个时期独立从100开始，两组各50，以后不互相转钱，资金占比可漂移。高分组＋高分组同时对比高分＋普通、普通＋高分、普通＋普通、各自单独高分、各自半份高分＋半份零息现金，以及各来源三组平均的组合。所有对手预先保留，不把事后表现最好的单项变成可以提前知道的交易规则。

三组平均先按每月低、中、高收益求平均，再形成各自连续路径；组合的两边仍只在开始分配资金。该参照仅用于比较相对表现。真正母指数尚未绑定，不能把它叫指数超额。

新程序还固定：

- 6格统一用**大规模动量来源三组平均**的当月涨跌划分描述月份，组合相对表现则对比自己的来源组合。单月涨跌不代表牛熊，也不参与调配。
- 展示上涨时多赚／少赚、参照不涨时多赚／少赚四种情况，相等单列；再看共同大涨月份错过多少。不会把事后挑出的月份拼成可实现账户。
- 报共同亏损次数、平均亏损、两种相关性、已结束和期末尚未结束的回本等待，以及资金占比漂移。
- 用相同的连续月份抽取次序描述各比较月均差的不确定性。近期仅20个月，判断很薄；6格共享大量月份，不是6次独立证明。
- 检查四条资产路径相加减的恒等关系。在初始各半、不再转资的规则下，这个差恒为零；它能核账，不能证明两条信息联合选股有额外效果。

仅有上述历史组合仍不足以直接上前向台。完整逐股选择、入场、退出、数量、费用、缺价和实际可成交时点需要独立合格版本；改原LEI技术规则或真实资金运用均不在本轮。

## 5. 实际执行、失败与核验

17:55的新外盘计划通过；18:00执行前重新核查时，内盘空闲5,132,701,696字节，低于本机5GiB加小记录的5,370,806,272字节要求，18:02又降至4,047,101,952字节。当时没有计算收益或创建外盘新运行目录。18:07:56内盘恢复到6,328,127,488字节，主控及执行者分别复核原计划通过，随后沿同一合同一次完成固定批次。未删除数据、放宽预留或调整金融参数。

实现纠正均在效果前保留：合成小数严格相等改为容差；预审删除离散强涨月份连乘财富字段；等待区间加入相等容差。画图核验阶段曾误用“只准创建新目录”的预检检查已完成结果，被拒绝后改为核原路径、UUID、设备与同样内外盘预留，再只追加新图；未绕过容量要求。

主控从原始月表用独立计算路径核完整资金与月收益、统计、等待、相关、共同亏损和四格，83,268项数值核对通过；最大的净值绝对舍入差约1.05×10⁻⁹。18个组合时期的资金恒等关系成立。大规模盈利＋动量三个时期四项原方案末值、总收益、年化和月末跌幅与已存结果差为0，不重启旧股票回测。全部源和输出SHA一致。数值核对只确认计算，不证明策略未来有效。

本轮是1个预先固定的组合批次、两个固定时期对照；新增5格、1格旧复用；0参数搜索、0行情下载、0新前向版本。结果原件和4组SVG/PNG图均在已核固定外盘，本机只留代码、合同、报告与小回执。没有后台自动恢复、通知、生产或真实交易动作。

## 6. 证据与最小决策卡

- 合同：同名raw下 `contract.json`，SHA `fe1dd2c7dff6813216d03732136cd782d3e81226030407cb5a9ac186b086bc6d`；状态保持效果前冻结。
- 输入、18组资格、来源、方法审阅及失败：`manifest.json`、`qualification.json`、`sources.json`、`controller-review.json`、`execution-log.json`、`storage-observations.json`。执行脚本仅新增本题路径。
- 三个准确参照对象：`reference.french.longonly.bm@1.0.0`、`reference.french.longonly.op@1.0.0`、`reference.french.longonly.mom@1.0.0`；从登记表解析，不伪造本地逐股实现。技术因子原生工作流不支持这一资金组合问题，本次未宣称已通过该入口。
- 两份权威原文实际SHA：技术交易体系 `df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`；技术实现 `85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。服务独立研究和组合层，不改变原技术规则。

| 决策项 | 本次结论 |
| --- | --- |
| 改善了什么 | 确认“相对表现互补”不自动改善资金组合；五个新增范围已完成，专业方法进入现有技能 |
| 策略收益改善是否成立 | 未找到同时支持稳定收益与亏损改善的新组合；小规模没有改善主要十年取舍；费用后效果未评价 |
| 付出什么代价 | 公开分组仍承担大幅股票风险，部分搭配少赚、跌幅更深；真实换手和个人成本未知 |
| 保留什么 | 价值与经营支撑联合选股这一金融假设；有边界地补大规模同池财报、行业和持仓资格，保留普通盈利强对手 |
| 暂停什么 | 用同样公开月收益继续调权重追求好曲线；降低小规模固定搭配优先级，不否定整类因子 |
| 下一项能改变决定的证据 | 共同股票池、当时已公布且版本可核的财务数据、行业、退出和成交成本，允许真正比较联合选股 |
| 采用和交易 | 本轮没有增加生产策略、前向版本或真实资金运用 |

## ARCHIVE：本轮有界比较与方法接入完成

固定范围的计算、反例、全部尝试、方法接入和独立核数已完成。全部结果为已看历史的公开毛收益，不是实际费用后、对应母指数的优势证明；本轮没有完成全市场策略发现或联合选股的验证。后续按上述新证据条件推进，不能把改名或换权重当新的独立检验。


## 2026-10-24 接续：盈利与资产增长的联合组合

新增检验已见[盈利与资产增长的策略组合](profitability-investment-combinations-2026-10-24.md)：慢增长＋强盈利在主要十年有收益线索，但其他时期、费用和母指数仍限制；快增长联合条件未见稳定帮助。原六组结果与本文既有结论保持。
