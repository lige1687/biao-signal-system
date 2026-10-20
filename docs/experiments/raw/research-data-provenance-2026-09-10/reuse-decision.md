# 复用决策表：成熟工具 vs 自建（2026-09-10）

> **⚠️ 本文已被复核修正，请连同修正一起读。**
> 修正见 [`docs/experiments/factor-library-external-backlog-2026-09-09.md`](../../factor-library-external-backlog-2026-09-09.md)
> §「成熟工具复用：2026-09-10 复核与后置待办」（待办规格 v1.1.0）。
>
> 本文按「保留原始记录、不改写结论历史」的要求**原样保留**，
> 下列判断已被复核推翻或收窄，**不得再作为依据**：
> ①「Alphalens 只能当第二个算盘」——它可以承担合格后的正式分析；
> ②「自写 SciPy 包装与它比对＝独立核验」——两者都调 `scipy.stats.spearmanr`，
>   不构成独立数值核心，独立期望值必须来自**手算小例**；
> ③「`max_loss` 静默丢弃」——源码有损失摘要，不能一律称静默；
> ④「`demeaned=False` 即无多空」——原始负分仍可产生负权重，且 IC 函数无此参数；
> ⑤「14 只必然报错 / 禁止一切分组」——并列未必造成重复边界，可先不分组；
> ⑥「Qlib 唯一价值是日历」——它有 PIT 机制（主要覆盖季度/年度财务），
>   且数据导入与 provider 可自定义，预置整包下载不是唯一用法；
> ⑦ 维护活跃度推断——旧 issue、第三方活跃标签、未发版时长不单独证明当前版本不可用。
>
> 本文**漏掉**的一项风险，以复核为准：`filter_zscore` 涉及未来分布，初次验证须显式关闭。
>
> 执行者说明：上述修正我**未能独立复验**——`github.com` 与
> `raw.githubusercontent.com` 在本环境被网络策略阻断，源码取不到。
> 因此以上按复核方断言记录，安装前仍须在隔离环境固定版本实测。

---

本轮：`research-data-provenance-2026-09-10`
性质：**评估，不安装、不引入依赖。** 需要新增依赖时另行确认后再装。

---

## 一句话结论（大白话）

同意你的分法，并且有一处要说清楚：

- **数据基础**：复用仓库现有接口。两个外部工具**都不解决**我们真正缺的东西
  （获取时间、真实交易日历、公司行动到达时间）——它们默认这些已经就绪。
- **因子分析**：Alphalens 值得试，但**最大价值不是拿它出结论，而是拿它当"第二个算盘"
  校验我自己写的 IC**。它的分组和默认多空构造在我们 14 只的池子上不能直接用。
- **Qlib**：不做底座。它唯一对得上我们缺口的组件（中国市场交易日历）是**跟它整套数据包
  绑在一起**的，而下载整套数据本轮明令禁止，且那份数据自身的资格也要另外核。

---

## 0. 环境现状（实测）

| 项 | 值 |
|---|---|
| Python | 3.11.7 |
| 已装 | numpy 2.1.1、pandas 2.3.3、scipy 1.17.1 |
| **alphalens-reloaded** | **未安装** |
| **pyqlib** | **未安装** |
| 项目依赖声明 | `pyproject.toml:10-12` → `numpy>=2.0,<3`、`pandas>=2.2,<3` |

---

## 1. 候选工具的外部事实（本轮联网核实）

| | alphalens-reloaded | Microsoft Qlib（pyqlib） |
|---|---|---|
| 最新版 | **0.4.6**，2025-06-02 | **0.9.7**，2025-08-15 |
| 许可 | **Apache-2.0**（原作者 Quantopian） | **MIT**（贡献需签 Microsoft CLA） |
| 开发状态标签 | Production/Stable | **3 - Alpha**（无 1.0） |
| 维护活跃度 | 距今 >15 个月无新版，**低活跃** | 距今 ~13 个月无官方发版；Snyk 标 **INACTIVE**；社区 PR 仍有（2026-09 仍有提交），积压 ~299 issues / ~167 PRs |
| 主要依赖 | matplotlib、seaborn、statsmodels、scipy | 重量级：LightGBM、pydantic-settings、MLflow 等 |
| 与我们环境的兼容 | **未知**——需在隔离环境实测 numpy 2.1 / pandas 2.3 下能否装能否跑 | 已知依赖债（issue #2233：LightGBM 4.0+ 与 pandas 2.x 不兼容） |

来源见文末。

---

## 2. 决策表

### 2.1 数据基础（本轮主战场）

| 当前需求 | 仓库已有能力 | 成熟工具对应组件 | 定义差异 | 依赖/许可成本 | 采用与否 |
|---|---|---|---|---|---|
| 行情抓取（有界、超时、有限重试、失败不伪装空成功） | `data/providers.py`（8 provider、链式回退、失败一律 raise） | Qlib `data/collector` | Qlib 面向"批量灌库"，无单次有界请求预算概念 | 重依赖 | **不采用**，用现有 |
| K 线基础校验 | `data/validation.py::validate_bars`（12 项） | Qlib `DataHandler` 的 processor | Qlib processor 偏"特征清洗"（去极值/标准化），不是资料合法性校验 | — | **不采用**，用现有 |
| **获取时间 / 发布时间 / 生效时间分别记录** | `data_provenance.py::MarketDataRef`（已有完整字段，`SOURCE_POLICIES` 故意留空以诚实降级） | **两者都没有** | Alphalens 完全不管来源；Qlib 有 calendar 但无 `available_at` 语义 | — | **本轮自建薄适配**（已完成） |
| **真实交易所日历** | ❌ 无（`WeekdayCalendar` 节假日表为空） | Qlib 的 CN calendar | **这是唯一真正对得上的组件**，但它随 `qlib data cn` 整包下载而来 | 本轮禁止批量下载；且该数据自身资格未核 | **不采用（本轮）**，列为独立缺口 |
| 公司行动到达时间 | ❌ 21/21 缺 `available_at` | 两者都不提供 | — | — | **保持未知**，不补造 |

**小结**：数据基础层，两个工具都帮不上忙。它们的设计前提是"数据已经干净且时点无争议"，
而我们的问题恰恰在这一层。

### 2.2 因子分析（本轮不交付，先评估）

| 当前需求 | 仓库已有能力 | Alphalens 组件 | 定义差异（**必须核**） | 采用建议 |
|---|---|---|---|---|
| Rank IC | ❌ 无 | `factor_information_coefficient`（Spearman） | 并列处理、最小样本、缺失、汇总权重的具体口径需实测 | **借它当校验对手**，不当结论来源 |
| 分组收益 | ❌ 无 | `mean_return_by_quantile` | 用 `pd.qcut` 切分；**14 只切 5 组每组不到 3 只**，且并列会导致 bin 边界重复报错 | **不采用**——不为用工具而强切五组 |
| 因子收益序列 | ❌ 无 | `factor_returns(demeaned=True)` | **默认 demean = 隐含构造多空组合** | **不采用**——不为填 `factor_return` 类型新造多空 |
| 换手 | ❌ 无 | `quantile_turnover` / `factor_rank_autocorrelation` | 依赖分组，分组不可用则换手也要另算 | 条件性，待分组问题解决 |
| 前向收益 | ❌ 无 | `get_clean_factor_and_forward_returns` | 见下方红旗 | **谨慎**，需逐项核 |

---

## 3. Alphalens 的四面红旗（采用前必须实测确认）

以下是我依据对该库的既有认识列出的**待验证疑点**，不是已核实结论——
本轮未安装、未运行，标为"待实测"：

1. **`max_loss` 默认 0.35 —— 静默丢弃最多 35% 的样本**，超过才报错。
   我们的池非矩形（562590 只有 654 行、513870 只有 643 行），
   很可能触发大量丢弃却不报错。**必须显式设为 0 或极小值。**
2. **默认 `demeaned=True`** —— 多处函数默认把收益去均值，等价于隐含一个
   美元中性多空组合。这与"不新造多空策略"直接冲突，也会让"factor return"
   这个名字被误读成我们能真实取得的账户利润。
3. **日历由价格面板的索引推断**（会调 `infer_freq`）。我们没有权威交易日历，
   面板索引是 14 只报价日期的并集——工具会把它当成真日历，**静默继承我们的近似**。
4. **`pd.qcut` 分组在小样本 + 并列时行为不确定**（重复 bin 边界会抛错或产生
   不等大的组）。14 只标的必然踩到。

**这四条正好对应你给的复用验收 1/2/3 项。**

---

## 4. 名称映射（防止工具词汇污染我们的结论）

| 工具输出名 | **不得**解释成 | 在本项目应称为 |
|---|---|---|
| `alpha` / `alpha factor` | 独特收益、我们的能力 | **待检验的排序打分**（`feature` 类对象） |
| `factor return` | 可实际取得的账户利润 | **该构造下的名义收益差**，且须注明是否含隐含多空与是否扣费 |
| `IC` | 预测能力已成立 | **同日排序与后续排序的吻合程度**（诊断值，无通用及格线） |
| `quantile` / 分组收益 | 分组单调即因子有效 | 小池下**不构成证据**，须报有效样本量 |
| `turnover` | 真实换手成本 | 名义换手率，未含成交容量与冲击 |

映射依据：`definition-standard.md` 1.1.0 §2 类型边界与
`experiment-backtest-principles.md` v1.1 §2.3（残差不得直接叫 `alpha`）。

---

## 5. 建议（按你的分法，补两点具体化）

**同意**：数据基础复用现有接口；因子分析优先试 Alphalens；Qlib 按具体缺口选组件。
在此之上补两条：

### 5.1 Alphalens 的正确用法是"第二个算盘"，不是结论来源

最高价值的用法是：**我自己按登记定义实现 Rank IC，然后用 Alphalens 在同一份
合法输入上独立算一遍，两者比对。** 理由：

- 满足复用验收第 4 项（手算小例与现有合法输入的一致性）；
- 满足 `ai-execution-contract.md` §1「复核者用独立计算的期望值，不复制被测输出」——
  Alphalens 是天然的独立实现；
- 避开它的分组、多空和日历假设——那些我们不采用。

**引入条件**（缺一不可）：在隔离虚拟环境安装（不动生产环境）、
确认 numpy 2.1 / pandas 2.3 下可运行、显式设 `max_loss=0`、`demeaned=False`、
不使用 quantile 相关函数。

### 5.2 Qlib 唯一值得单独立项的是"交易日历"，且现在不做

我们最硬的数据缺口之一是**没有真实交易所日历**。Qlib 有中国市场日历，
但它**随整套数据包下载而来**，而本轮明令禁止批量历史回填；
更关键的是，那份日历本身的资格（谁发布、覆盖到哪、是否含临时休市调整）
**同样需要核**，不能因为来自 Microsoft 就当权威。

建议：作为独立小课题另行授权——目标只是**取得一份可核验的 A 股交易日历**，
候选来源不限于 Qlib（交易所官方公告、akshare、baostock 都可比较）。
**不为了用 Qlib 而下载整套数据、搬入全部因子或重建账户。**

---

## 6. 本轮实际结论

| 工具 | 本轮 | 理由 |
|---|---|---|
| 现有 pandas / NumPy / SciPy | **继续用** | 已装、已在依赖声明内；SciPy 1.17.1 的 `spearmanr` 足以实现 Rank IC |
| `data_provenance.py` 等仓库既有件 | **薄适配复用**（本轮已完成） | 字段与哲学完全对口 |
| alphalens-reloaded | **本轮不引入**，列为下一批的校验对手 | 本轮是数据基础，Alphalens 诊断不自动加入交付 |
| Qlib | **本轮不引入，也不作为底座** | 唯一对口组件与整套数据绑定，且本身资格待核 |

**需要另行授权的事项**：
1. 在隔离环境安装 alphalens-reloaded 0.4.6（Apache-2.0）作为 IC 校验对手；
2. 单独立项取得一份可核验的 A 股交易日历（来源不预设）。

---

## 来源

- [alphalens-reloaded 0.4.6 — PyPI](https://pypi.org/project/alphalens-reloaded/)
- [stefan-jansen/alphalens-reloaded — GitHub](https://github.com/stefan-jansen/alphalens-reloaded)
- [microsoft/qlib — GitHub](https://github.com/microsoft/qlib)
- [microsoft/qlib Releases](https://github.com/microsoft/qlib/releases)
- [pyqlib 0.9.7 — PyPI](https://pypi.org/project/pyqlib/)
- [pyqlib — Snyk package health](https://security.snyk.io/package/pip/pyqlib)
- [microsoft/qlib issue #2233（LightGBM/pandas 兼容）](https://github.com/microsoft/qlib/issues/2233)
