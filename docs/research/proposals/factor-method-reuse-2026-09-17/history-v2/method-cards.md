# 方法卡（两篇）—— v2（R3 返修版）

按 `docs/literature-learning/README.md` v1.1.0 字段与 `docs/research/definition-standard.md`
v1.1.0 适用范围写。**本轮仍未下载、未通读任何原始论文全文**——两张卡的依据
是官方文档/官方源码中的引用与实现说明，阅读范围如实标注；文档转述与作者
全文结论严格分开。上一版错误（书目年份、Bartlett 权重算式、"指数段长"措辞、
"完全不能替代"表述）已按主控复核 R3 逐项纠正，原版字节存 `history-v1/`，
逐条回应见 `revision-response.md`。

---

## 卡1：HAC（Newey–West）协方差——"回归系数的误差要考虑相邻日期互相像"

- **题名/作者/年份**：A Simple, Positive Semi-Definite, Heteroskedasticity and
  Autocorrelation Consistent Covariance Matrix；Whitney K. Newey, Kenneth D.
  West；NBER 技术工作论文 t0055（1986-04），正式发表 **Econometrica 55(3),
  1987-05, 703–708**（书目据 [NBER 页](https://www.nber.org/papers/t0055)，
  2026-09-17 访问；上一版误写 1986/Econometrica 54(3)，已撤回）。自动滞后
  窗宽属 1994 后续工作。
- **原文链接**：未获取（未读原文）。
- **阅读版本与范围**：statsmodels 官方 API 文档两页 + 官方源码
  `statsmodels/stats/sandwich_covariance.py`（main 分支；发布版未固定）的
  `weights_bartlett` / `S_hac_simple` / `_HCCM2` 段。2026-09-17 访问。
- **问题**：单标的状态均值差（或宽度）对未来价格的回归里，相邻日期的误差
  相关且波动随时间变——普通最小二乘系数的"误差条"在有自相关时不再可信。
- **作者结论（据文档/源码转述，非原文核对）**：用 Bartlett 核加权的残差
  交叉积求协方差，可同时容纳异方差与有限阶自相关，且保证协方差阵半正定。
- **本库理解（本地推断）**：它估计的是"**这个回归系数的标准误/区间**"。
  自相关既可能让普通标准误被低估、也可能被高估，方向取决于残差结构——
  正相邻相关通常低估，交替（负相关）结构则可能相反，不能笼统说"必然低估"。
- **纯算术示例（自拟教学算术，未运行库）**：T=100、单一常数回归（即均值），
  自动滞后 = floor[4×(100/100)^(2/9)] = 4。Bartlett 权重为 **1−l/(nlags+1)，
  l=0..4，即 1、0.8、0.6、0.4、0.2**（上一版误写 1−l/4、l=0..3，已按源码
  `1 - np.arange(nlags+1)/(nlags+1.0)` 纠正）。S 矩阵 = w₀·x′x 加上各滞后
  l≥1 的 w_l·(s+s′)（s = x[l:]′·x[:−l]），再做三明治变换
  (X′X)⁻¹·S·(X′X)⁻¹′。手算期望须先于调用库写出。
- **既有真实结果**：本地对真实序列的 HAC 使用为 0 次（外部方法未用）。
- **关键默认值（必须显式登记）**：`cov_hac(results, nlags=None,
  weights_func=weights_bartlett, use_correction=True)`；`get_robustcov_results(
  cov_type='HAC')` 时 `maxlags` 必填。源码自注：校正因子出处不明确（"just
  guessing, need reference"）、仅 nlags=0（退化为 White）经过对照验证。
- **检查建议**：滞后/窗宽选择不得以显著性最高为准；缺失交易日先登记处理
  再喂入（等间隔假设）；调用前须先 fit。
- **适用边界**：单条时间序列回归的误差推断。它与重抽法（卡2）不是同一
  算法，但**可以作为同一统计问题的两种不同不确定性估计并存**（例如对跨日
  IC 均值既可做 HAC 回归推断、也可做分块重抽敏感性，各自前提与估计目标
  分开报告，结果不重复相加）。不构成任何因子有效性证据。

---

## 卡2：平稳自助法（Stationary Bootstrap）——"把历史切成随机小段重新拼，看结论稳不稳"

- **题名/作者/年份**：The Stationary Bootstrap；Dimitris N. Politis,
  Joseph P. Romano；1994（JASA 89(428)，据 arch 文档转述，原文未读）。
  自动块长：Politis & White 2004 + Patton/Politis/White 2009 修正。
- **原文链接**：未获取（未读原文）。
- **阅读版本与范围**：arch **8.0.0** 官方源码页（bashtage.github.io 模块页）
  的 `StationaryBootstrap.__init__` / `update_indices` 段，及 stable 文档
  `optimal_block_length` 页。2026-09-17 访问。⚠️ 版本差异留痕：stable 文档
  页（更早版本）记有 `random_state`（自 5.0 弃用）；**8.0.0 源码签名只有
  `seed`，无 `random_state`**——以固定版本源码为准，文档措辞与实现分栏。
- **问题**：只有一条真实历史，相邻日期不是独立证据，想知道"换一副历史
  抽法，这个均值差/IC 还在不在"。
- **作者结论（据文档转述）**：以随机长度的历史片段拼接重抽，在保留序列
  相关结构的同时构造统计量的经验分布；自动块长按自相关衰减估计。
- **本库理解（本地推断，与实现核对）**：8.0.0 实现是**逐步几何重启**：
  块内每前进一步以概率 1/block_size 重新抽一个均匀起点、否则继续 +1，
  因此段长是**几何分布的离散段**（平均 block_size），不是"连续指数长度"
  的字面直译（上一版措辞已纠正；文档页"expon distributed block sizes"
  指几何段的均值参数化）。重启逻辑在编译采样器
  `stationary_bootstrap_sample` 内，本轮源码页只核到其输入（候选起点、
  均匀随机数 u、p=1/block_size），采样器本体未逐行读。重抽是已有历史的
  重新组合，**不产生新证据、不增加样本量**；块长/次数按先验理由登记，
  不得按显著性挑。
- **纯算术示例（自拟，未运行）**：序列 [1,2,3,4,5,6]，block_size=2（即每步
  重启概率 1/2），seed=0。期望结构：首位置为均匀抽的起点；其后每一步由
  RNG 的均匀数决定"继续上一位置+1"还是"跳到新均匀起点"。手算例应先列出
  RNG 产出的具体数值序列，再核对展开索引——用于验证"段是连续推进+概率
  重启，不是逐点独立乱抽"。
- **既有真实结果**：**外部 Stationary 形式本地使用 0 次**；但本地已有并
  真实使用过**固定块长的成对循环分块重抽**（`factor_evidence/resampling.py`
  的 `circular_indices`/`paired_block_deltas`，PCG64 定种子、同一索引用于
  状态/主列/合法性，见 factor-evidence-reliability-v1）。上一版"既有真实
  结果：无"抹掉了这项能力，已纠正。
- **检查建议**：`seed` 显式固定；区间用 `conf_int`；块长若用
  `optimal_block_length` 估计，同时报告 b_sb/b_cb 与选择理由。与本地
  circular 口径的差异（随机几何段长 vs 固定段长绕回）须先对照登记再谈替换。
- **适用边界**：单序列统计量的历史敏感性诊断；与 HAC 是不同算法、不同
  估计目标，可对同一问题并存报告，不混称同一种检验；SPA/StepM/MCS 需
  完整候选与损失序列，当前无输入，不引用。

---

> 两卡均为"方法参照卡"，不引入任何本地对象、不启动任何真实统计；未虚构
> 阈值，未读全文处均已标注。访问时点 2026-09-17。
