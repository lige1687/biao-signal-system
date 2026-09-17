# 方法卡（两篇）

按 `docs/literature-learning/README.md` v1.1.0 字段（题名/作者/年份/原文链接/
阅读版本与范围/问题/作者摘要/本库理解/例子/适用边界）与
`docs/research/definition-standard.md` v1.1.0 适用范围写。
**本轮未下载、未通读任何原始论文全文**——两张卡的依据是官方文档/官方源码中
的引用与实现说明，阅读范围如实标注；作者结论与本库推断严格分开。

---

## 卡1：HAC（Newey–West）协方差——"回归系数的误差要考虑相邻日期互相像"

- **题名/作者/年份**：A Simple, Positive Semi-Definite, Heteroskedasticity and
  Autocorrelation Consistent Covariance Matrix；Whitney K. Newey, Kenneth D.
  West；1986（Econometrica 54(3)）。自动滞后窗宽属 1994 后续（Automatic Lag
  Length Selection in Covariance Matrix Estimation）。
- **原文链接**：未获取（JSTOR 等付费源，本轮未访问）。
- **阅读版本与范围**：**未读原文**。间接证据：statsmodels 官方 API 文档
  `cov_hac` / `get_robustcov_results` 页（2026-09-17 访问），其中给出
  nlags=None 时的自动滞后公式 floor[4(T/100)^(2/9)] 并标注 Bartlett 核默认。
- **问题**：单标的状态均值差（或宽度）对未来价格的回归里，昨天和今天的误差
  高度相似、波动大小也随时间变——普通最小二乘的系数"误差条"会被低估。
- **作者结论（据文档转述，非原文核对）**：用 Bartlett 权重加权的残差交叉积
  求协方差，可同时容纳波动变化（异方差）与有限阶的误差相关（自相关），
  且保证协方差阵半正定。
- **本库理解（本地推断）**：它回答"**这个回归系数的区间有多宽**"，不回答
  "换个历史抽法结论会不会翻"。它是对一个已拟合模型的误差描述，重抽法
  （卡2）是对整个统计过程的扰动实验，两者不可互相替代或重复相加报告。
- **纯算术示例（自拟，未运行）**：设 T=100、单一常数回归（即均值），残差全为
  +1/−1 交替且放大自相关；自动滞后 = floor[4×(100/100)^(2/9)] = 4；用
  Bartlett 权重 1−l/4（l=0..3）加权残差滞后交叉积。手算期望应先于调用库。
- **既有真实结果**：无（本地尚未对任何真实序列使用 HAC）。
- **关键默认值（必须显式登记的）**：`cov_hac(results, nlags=None,
  weights_func=weights_bartlett, use_correction=True)`；`get_robustcov_results(
  cov_type='HAC')` 时 `maxlags` 必填、`use_t` 默认对稳健型为 False。statsmodels
  文档自注：小样本校正因子出处"just guessing"、仅 nlags=0 情形经过对照验证。
- **检查建议**：选滞后不能以哪个显著性最高为准（这是任务红线）；缺失交易日
  必须先登记处理方式再喂入（文档要求等间隔单序列）；调用前须先 fit。
- **适用边界**：单条时间序列回归的误差推断；不适用于横截面排序问题（那是
  IC/分组的地盘）；不构成任何因子有效性证据。

---

## 卡2：平稳自助法（Stationary Bootstrap）——"把历史切成随机小段重新拼，看结论稳不稳"

- **题名/作者/年份**：The Stationary Bootstrap；Dimitris N. Politis,
  Joseph P. Romano；1994（JASA 89(428)）。自动块长：Automatic Block-Length
  Selection for Dependent Bootstrap；Politis & White 2004，Patton/Politis/
  White 2009 修正。
- **原文链接**：未获取（本轮未访问）。
- **阅读版本与范围**：**未读原文**。间接证据：arch 官方文档
  `StationaryBootstrap`（页自述"Politis and Romano (1994) bootstrap with
  expon distributed block sizes"，签名含 `block_size, *args, random_state=None,
  seed=None`，`random_state` 自 arch 5.0 弃用）与 `optimal_block_length`
  （实现 Politis & White 2004 + Patton/Politis/White 2009；返回 b_sb/b_cb 两列；
  文档明示部分调参来自 Patton 的 MATLAB 程序且与 MATLAB 数值不完全一致）。
  2026-09-17 访问；arch 总览页首次抓取超时未读。
- **问题**：只有一条真实历史（比如 510300 一次过去），相邻日期不是独立证据，
  想知道"如果历史换一副抽法，这个均值差/IC 还在不在"。
- **作者结论（据文档转述）**：以随机（指数分布）长度的历史片段拼接重抽，
  可在保留序列相关结构的同时构造统计量的经验分布；自动块长按自相关衰减估。
- **本库理解（本地推断）**：重抽的是"已有历史的重新组合"，**不产生新证据、
  不增加样本量**；它量化的是"结论对重抽扰动稳不稳"，不是"结论在未来成立
  的概率"。块长/重抽次数的选择必须按先验理由登记；用多个块长试出最显著
  结果再报告，等于又一次挑答案。
- **纯算术示例（自拟，未运行）**：序列 [1,2,3,4,5,6]，block_size=2，seed=0；
  期望结构是"从随机起点取随机长度≥1的连续段、段间可回绕拼接、总长6"。
  手算例应先列出 RNG 抽到的起点与段长序列再对答案；该例用于验证"段是连续
  的、不是逐点乱抽"。
- **既有真实结果**：无。
- **检查建议**：`seed` 显式固定；区间用 `conf_int`（无 get_interval 方法）；
  块长若用 `optimal_block_length` 估计，须同时报告它给出的 b_sb 与选择理由，
  不得反复试块长挑显著。
- **适用边界**：单序列统计量的不确定性描述；与 HAC 分开报告、不混称"同一种
  检验"；SPA/StepM/MCS 需要完整候选与损失序列，当前无此输入，一律不引用。

---

> 两卡均为"方法参照卡"，不引入任何本地对象、不启动任何真实统计；未虚构阈值，
> 未读全文处均已标注。访问时点 2026-09-17。
