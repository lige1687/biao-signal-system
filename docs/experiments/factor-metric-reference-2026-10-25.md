# 研究总览指标口径、焦点模型身份与外部情绪信息

## 一句话结论（大白话）

**当前焦点股动量是有金融含义的自建观察指标，尚不能称为经过验证的权威预测因子，也没有复刻原视频模型。研究总览的“20日动量”则是另一项个股排序研究：固定300只A股样本、每月观察、评价后续一个持有月。Rank IC、ICIR 可以解释方向与稳定程度，但不能套用统一及格线。**

本轮是既有证据与原始资料核验、展示修正，没有新增收益检验、改参数或引入交易规则。结论限于现有版本；没有证明所有动量或情绪模型都无效。

## 1. 两个“20日”并非同一个模型

| 对象 | 输入与股票范围 | 评价对象与目前证据 |
|---|---|---|
| 总览的20日动量 | 每只股票的收盘价÷20交易日前收盘价−1；2014年底固定300只来源A股内，逐月按本批10项信息共同资格筛选 | 将当月各股得分排序与随后一个持有月报价涨跌排序比较；不是市场顶底模型 |
| 焦点股动量独立版 | 同类固定历史样本内，每天按过去20日平均成交额取前5%，对入选股过去20日复权价格涨跌等权平均 | 描述交易活跃股的历史强弱；20日未来收益及20/60日阶段顶底检验未建立稳定预测增量 |
| 抖音原模型 | 原视频可确认交易活跃小批股票与近期平均涨跌的思路；股数/比例、窗口、权重和完整数据处理未公开 | 无法严格复制，原视频的负值频率或事后低点表现不能移植给独立版 |

这里“固定300只”不等于沪深300历史成分，也不代表全A、创业板自身、科创自身或美股研究已完成。原视频见[量化舵](https://www.douyin.com/video/7699879945107016969)，来源核查见[既有报告](/library?report=docs%2Fexperiments%2Ffocus-stock-momentum-source-review-2026-10-24.md)。

## 2. 研究总览实际数值与范围

研究批次 `fixed2014_300_extension`，定义 `research.curves.momentum20@1.0.0`。形成月份2016-01—2025-11；未来结果为次月首交易日开盘至再下月首交易日开盘的调整后报价涨跌。20日是因子回看窗口，不是此处未来结果窗口。

| 候选池 | 平均Rank IC | ICIR（不年化） | 有效月份 | Rank IC均值95%历史区间 |
|---|---:|---:|---:|---:|
| 全部共同合格候选 | −0.0624 | −0.4202 | 119 | −0.0909 至 −0.0339 |
| 其中双均线绿色候选 | −0.0935 | −0.5477 | 108 | −0.1216 至 −0.0654 |

这些是已看历史中的反向排序关系。两池数量和资格不同，不能由绿色池负值更大就认定过滤带来增量；也不能事后将分数反号直接宣称可交易。未来收益未知仍保留在覆盖分母；绿色池有11个月形成时不足30只，未构成合格相关观察。报价、退市退出及实际成交限制沿原研究保留。

## 3. 数值参照为什么不能成为统一学术门槛

| 指标 | 数值可以说明什么 | 不能据此推出什么 |
|---|---|---|
| 平均Rank IC | 每期股票分数与未来结果的Spearman排名相关，再跨期平均；0无平均排序方向，±0.05是弱同/反向相关的数值示例 | 不是5%收益或胜率，也不是有效/无效的固定分界 |
| ICIR | 本页逐月Rank IC均值÷样本标准差，不年化；0.5或1只表示均值是其波动的0.5或1倍 | 不是平均Rank IC的不确定区间；不等于账户IR，不能按此自动评级 |
| 报价账户IR | G5相对同池同费用基准的逐月收益差均值÷样本标准差×√12 | 不是个股预测相关；年化近似也未自动处理时间依赖 |

[Alphalens原实现](https://github.com/quantopian/alphalens/blob/master/alphalens/performance.py)定义了上述排名相关；其[统计展示实现](https://github.com/quantopian/alphalens/blob/master/alphalens/plotting.py)使用均值除以标准差。它们没有赋予本页统一通过线。0.02/0.05、0.5/1之类数值需要结合范围、频率、用途、有效观察和简单对照解释，不能写成学术界普遍认可的及格标准。

应核同池同期限的简单对手、跨年份稳定性、均值区间、未用于选规则的新资料与费用。均值区间未跨零也不独立证明能赚钱或适合交易。[Harvey、Liu和Zhu](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824)讨论大量反复检验的证据要求，其特定语境的t值要求不能换成IC或ICIR阈值。[Hodrick](https://business.columbia.edu/sites/default/files-efs/pubfiles/1103/Hodrick_RFS1992.pdf)讨论重叠长窗口结果的推断问题；其他逐日未来20日研究不能把相邻日期当独立样本。本页实际是按月形成的持有月标签，未冒称逐日20日标签。

## 4. 外部信息：优先复用已做的工作

权威来源、经济含义和对本系统有预测增量，是三项不同的判断。

| 外部观察 | 金融含义 | 当前系统与证据状态 | 本轮决定 |
|---|---|---|---|
| VIX水平 | 美国标普500期权定价的预期波动 | 基本面与情绪页已有读取和展示 | 保留简单对照，不能包装成全新模型 |
| 美国高收益债OAS | 信用、流动性等风险的市场定价 | 基本面已有FRED/ICE来源及展示入口；本轮未检查实时最新值 | 保留现有信用背景，扩大利差不是确定底部 |
| OFR金融压力指数FSI | 33项变量、五类来源汇总的全球金融压力 | 今日已有官方历史及与VIX的247个月描述性对照；水平相关0.802，月差相关0.777；未证明预测/交易增量 | 优先考虑风险环境解释，使用滞后与历史修订要显式记录 |
| Cboe VVIX | 期权市场对VIX自身波动的不确定性 | 今日已有官方历史；同247个月与VIX水平相关0.405、月差相关0.712；未证明预测/交易增量 | 次要观察候选，相关较低不能作为有效证据 |
| VIX期限结构、股票期权Put/Call | 不同期限风险定价、期权交易构成 | 已有旧研究及负向/定义冲突结果；公开PCR旧覆盖和近年口径需分别核 | 先保留旧反例，不能直接当反向买点或重做旧实验 |
| A股ETF实际份额变化 | 一级市场确认的创造/注销份额 | 目前仅局部定期报告或字段线索，连续历史和发布时间未合格 | 与ETF用途贴近，但先补准确输入；成交额与申赎清单都不是实际净申赎 |

FSI与VVIX的数字直接复用[今日已有用途核验](/library?report=docs%2Fexperiments%2Ffinancial-stress-operating-feasibility-2026-10-25.md)，不重新下载或冒称新增预测检验。官方来源：[OFR](https://www.financialresearch.gov/financial-stress-index/)、[Cboe历史数据](https://www.cboe.com/tradable-products/vix/vix-historical-data/)、[FRED高收益债OAS](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)。

[Cboe期限结构](https://www.cboe.com/tradable-products/vix/term-structure)可解释不同期限的期权波动价格；[Cboe对PCR的说明](https://www.cboe.com/insights/posts/how-early-exercise-order-flow-impacts-equity-option-put-call-ratios)指出提前行权等非方向性交易可扭曲汇总比值。[Pan与Poteshman](https://www.mit.edu/people/junpan/volume.pdf)的个股买方发起新开仓期权量证据不能当成公开汇总PCR预测大盘的证明。[上交所ETF说明](https://www.sse.com.cn/assortment/fund/etf/question/)中的开市前申赎清单是可申赎对价，不是当日已发生净申赎。

## 5. 交付与复现

总览与单因子诊断新增所选样本、候选池、公式、未来结果期、观察覆盖和均值区间；表内因子行显示当前市场与候选池。增加Rank IC/ICIR数值参考及原始出处，未产生新评级。原始静态数据和冻结结论不修改。

输入：`web/public/research/factor-curve-library-20261022/catalog.json`、`web/public/research/factor-workbench-20261024/metrics.json`及原来源指纹清单；展示：`web/src/pages/factor-workbench/MetricReference.tsx`与原工作台容器。验证与来源账放在 `docs/archive/handoffs-plans/focus-momentum-display-20261025/metric-reference/`。

原焦点证据：[独立版本效果](/library?report=docs%2Fexperiments%2Ffocus-stock-momentum-evaluation-2026-10-25.md)、[阶段顶底](/library?report=docs%2Fexperiments%2Ffocus-momentum-turning-points-2026-10-25.md)。外部旧证据：`vix-sentiment-ARCHIVE-2026-09-01.md`、`sentiment-putcall-increment-2026-09-29.md`。本轮不改变这些研究状态。

ARCHIVE：有界口径及来源核验完成；焦点原版效果仍无法评价，自建版稳定预测增量未获支持；外部新信息用途仅为观察候选。本轮0金融实验、0大数据下载、0生产交易变更。
