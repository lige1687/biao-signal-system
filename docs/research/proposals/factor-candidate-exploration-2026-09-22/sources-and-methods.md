# 候选探索的来源与阅读边界

日期：2026-09-22。仅方法调研，未复制全文、安装软件、取行情或运行外部代码。以下 P 编号只用于这份提案，不是文献数据库的新增 `paper_id`。既有编号 `cederburg2020`、`L05` 沿用，未修改学习库种子。

## 一句话结论（大白话）

高点位置与上涨路径有直接相关的原始研究；按风险改变仓位也有支持和反对证据。它们足以帮助选择下一步问题，但不能证明我们手里的 ETF 已经适用。

| 来源 | 本轮实际阅读范围 | 对本轮的作用及限制 |
|---|---|---|
| P1 George & Hwang (2004), *The 52-Week High and Momentum Investing*, Journal of Finance 59(5), DOI 10.1111/j.1540-6261.2004.00695.x。[作者 PDF](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf) | 摘要、导论、§I 数据与方法开头，PDF 第1–4页；非通读 | 支持研究高点位置与普通动量的区别。原文为美国股票，不是 ETF；本地 252 有效行、经济指数和排除当日均须显式说明。 |
| P2 Da, Gurun & Warachka (2014), *Frog in the Pan: Continuous Information and Momentum*, RFS，DOI 10.1093/rfs/hhu003。[作者所存期刊先行版](https://academicweb.nd.edu/~zda/Frog.pdf) | 摘要、导论、§1 式(1)及零收益处理、局限，PDF 第1–9页相关段落；未逐表复核实证 | 用上涨/下跌频率描述形成路径，必须结合原有涨跌幅，不能单独按 ID 最小买。只看符号的代理存在反例。 |
| P3 `cederburg2020`: Cederburg et al. (2020), *On the performance of volatility-managed portfolios*, JFE，DOI 10.1016/j.jfineco.2020.04.015。[作者 PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf) | 摘要与导论，PDF 第1–2页；未重新通读 | 103 项股票策略的研究不支持一概通过波动调仓得到更好结果；提醒检查实时可用性、参数稳定与费用。不能据此宣布所有风控无效。 |
| P4 DeMiguel, Martín-Utrera & Uppal (2024), *A Multifactor Perspective on Volatility-Managed Portfolios*, JF 79(6), DOI 10.1111/jofi.13395。[出版社摘要](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13395) | 官方检索返回的摘要、作者和出版信息；直开正文失败，未读方法/附录 | 在不同的多因子条件组合设计下，作者报告扣费及未参与拟合的数据中仍有优势。仅作为 P3 的范围限定，不借摘要移植权重公式。 |
| P5 Patrick Schwarz (2025), *On the performance of volatility-managed equity factors – International and further evidence*, Empirical Finance 80, 101560，DOI 10.1016/j.jempfin.2024.101560。[作者机构记录](https://orbi.uliege.be/handle/2268/324663) | 元数据、摘要；正文须申请副本，未阅读 | 45 个国际股票市场的研究提示效果依因子而异，下行风险尺度值得继续查。未据此采用任何日窗或宣称中国 ETF 适用。年份为正式发表 2025，不按 DOI 中的 2024 写年份。 |
| P6 `L05`: Sepp & Lucic (2026), *The Science and Practice of Trend-Following Systems*。[arXiv v1](https://arxiv.org/abs/2607.19497v1) | 本轮只读摘要；2026-07-21 预印本，不称同行评审结论 | 提醒趋势信号之间可能高度相似，应研究真实新增价值，不能把多个均线变体计为多份独立证据。本轮不移植其策略。 |

## 为什么优先这三个，而不是堆很多名称

这是主控的取舍，不是论文替我们选定了策略：高点位置直接对照现有动量；路径连续性问的是同样涨幅是否走法不同；下跌波动问的是风险而不是收益排名。三者可以共享部分价格输入，但必须保留不同用途与评价标准。

经典论文仅保留与这三个问题直接相关者，并用 2024–2026 年来源检查风险与趋势研究的边界。没有用“新论文更多”代替本地适用性；未做系统综述、全文复现或完整发表偏差检验。

## 外部方法与软件复用

- 文献是方法线索，不是行情数据许可、软件许可或执行命令。下载入口可公开读不代表可重新分发全文；本轮仅留链接、阅读位置和简短概括。
- `factor-momentum-rank-reuse-2026-09-22.md` 已核提现有动量流程，不再重写排序/账户骨架。未来复用前仍须核输入身份与具体定义，不能把任意新分数挂到旧动量精确版本下。
- `factor-reuse-refresh-2026-09-22.md` 对 FactorHub 的结论保持：公开材料未证明满足本地 ETF 的价格、行动与历史可知性要求。本轮无新增 FactorHub 接入证据，不用换工具回避数据问题。
- 不直接移植股票的做多做空组合，不把黄金/海外 ETF 混作国内宽基，不引入基本面/消息面的硬过滤。

## 与既有结论的关系

旧外部候选设计仍作为尝试史保留。本轮纠正其“数据全部就绪”“高点含当日即退化”“相同基准超额动量提供新排序”等推论。没有改写旧数值，没有把旧股票研究结果当成新 ETF 效果，也未计算新的后续涨跌。
