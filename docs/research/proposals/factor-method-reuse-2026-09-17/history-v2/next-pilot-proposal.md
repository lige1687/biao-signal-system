# 下一步试点建议（至多一项，v2 / R2 返修版）—— **本轮裁决：暂缓执行**

**本文件是提案，不是执行许可；文档中的示例不是已实现的 schema。**

## 裁决与理由（回应主控 R1.4）

上一版直接推荐"下一轮做 Alphalens 合成核验"。按当前事实修正：**本地当前
没有已冻结的同日多 ETF 排序研究问题**（B1 是单标的描述、宽度无数字、
factor_lab 的 cross_section_ic 只在合成域验过）。旧短名单把它排第一不构成
现在的执行理由。因此本提案**降级为暂缓**：以下方案保留为"问题出现时可直接
取用的完整规格"，触发条件满足且用户/主控批准后再执行。本轮不再推荐任何
立即执行项；statsmodels/arch、外部因子数据维持暂缓不变。

## 暂缓项的完整规格（触发后使用）

### 触发条件（三者缺一不可）
1. 出现一个**已冻结协议的同日多 ETF 排序问题**（≥3 只标的、同日各有不同
   分数）；2. 用户/主控批准隔离安装；3. tag 0.4.5 复核通过（见下）。

### 候选版本与源码核验状态
alphalens-reloaded **0.4.5**（tag 0.4.5，2025-07-23；Apache-2.0，取自
performance.py 页标注，LICENSE 文件未核）。返修轮已逐项核对 **tag 0.4.5**
源码（不再是 main）：utils.py 与 performance.py 关键默认见
capability-reuse.csv B1/B2。剩余未核：与 main 的差异全集、依赖与 Python
版本兼容性——执行前仍须复查。

### 输入合同（精确）
- **factor**：pandas MultiIndex Series，层名**必须为 `date`（level 0）与
  `asset`（level 1）**——工具显式 rename 到这两个名字；本地 `symbol` 命名
  须由薄适配层改名并在协议中登记（回应 R2.4）。时区：两输入必须一致
  （None/None 可），否则 `NonMatchingTimezoneError`——时区是"一致性检查"，
  工具不会替我们猜真实发布时间。
- **prices**：date×asset 宽表，须覆盖最后因子日 + max(periods) 个交易日
  （末端 buffer）。**NaN 语义与 pandas 版本绑定**：`pct_change` 的
  `fill_method` 在 pandas 3.x 已固定为 None（NaN 向前传播，缺价日的前向收益
  为 NaN）；更早版本默认 'pad' 会**向前填充**缺价。执行前必须钉死 pandas
  版本并登记该行为，不得假设"缺报价自动剔除"（回应 R2.5）。
- **显式参数**：`quantiles=3`、`periods=(1,3)`、`filter_zscore=None`
  （逐入口确认：`get_clean_factor_and_forward_returns` 默认 20 必须显式关；
  `compute_forward_returns` 单独调用默认即 None；`get_clean_factor` 根本没有
  该参数）、`max_loss=0.0`（此时 `no_raise=False`，分组异常会**直接抛出**
  而非吞掉——见下方正负例拆分）、`binning_by_group=False`。

### 输出合同与逐入口正负例（回应 R2.5/R2.6）
- `factor_information_coefficient(factor_data, group_adjust=False,
  by_group=False)`：逐日 spearman IC。
- `mean_return_by_quantile(by_date=True, demeaned=False)`：**必须显式关
  demeaned**（默认 True = 前向收益减同日横截面均值，是多空对比口径；它
  也不等于已定义完整多空账户——账户需要 factor_weights 那套减均值+绝对值
  和归一的 dollar-neutral 权重，本试点不构造）。
- `factor_rank_autocorrelation(period=1)`：只作名次稳定性描述，不得写成
  换手/交易成本。

**正例（预期成功）**——合成价格/分数表（教学算术，可独立手算）：
6 个交易日（d1..d6）、3 标的（A/B/C）：

| date | A价格 | B价格 | C价格 | 分数(A,B,C) |
|---|---|---|---|---|
| d1 | 10.0 | 10.0 | 10.0 | 3,2,1 |
| d2 | 11.0 | 10.5 | 9.5 | 3,2,1 |
| d3 | 12.1 | 11.0 | 9.0 | 3,2,1 |
| d4 | 13.0 | 12.0 | 8.5 | 3,2,1 |

（prices 另含 d5、d6 两天以补 period=3 的末端 buffer。）
- 独立手算：d1 的 1 期前向收益 = A:+10%、B:+5%、C:−5% → 分数与收益名次
  完全同序 → 逐日 IC = **+1.0**（spearman 完全正相关）。
- 反例1：分数改为 (1,2,3) → IC = **−1.0**。
- 尺度：分数×100 → IC 仍 = **+1.0**（spearman 对单调变换不变）。
- 端点对齐（回应 R2.5）：工具的前向收益是 **t→t+h**（`pct_change(h)` 后
  `shift(-h)` 对齐因子日，h=交易日数），而本地动量对象窗口是 **t+1→t+22**
  的自身行位移。两者端点语义不同，协议中必须分别写明，不得只写 periods。

**负例（预期异常/拒绝，与正例分开登记）**：
- 常数截面（同日 A=B=C=同分）：`quantize_factor` 走 `pd.qcut`，重复边界
  触发 "Bin edges must be unique" ValueError；在 `max_loss=0.0` 下
  `no_raise=False` → **直接抛异常**（不是返回缺失 IC）。预期结果=抛该异常。
- 并列分数（部分并列）：同上机制，取决于并列位置是否造成重复边界；预期
  要么正常分组（并列不跨边界）、要么抛上述异常——**不会**把同值硬拆进
  高低两组制造假排序（上一版错误因果已撤回）。两种结果都在协议里预先
  写明可接受。
- 末端不完整前向收益：最后 max(periods) 天的前向收益为 NaN，计入损失
  报告；`max_loss=0.0` 可能因此**整体拒绝**——所以末端样本处理必须与
  常数/并列负例**分开成不同入口/不同子样例**，不能同时承诺"完整流程
  返回缺失 IC"（回应 R2.5）。
- 某日缺一标的价格：行为由 pandas 版本的 `pct_change` 填充语义决定
  （见输入合同），预期须先钉版本再写死——**当前不预设**。

以上期望值全部可独立手算复核；验证范围限于"0.4.5 在这些合成小例上的行为
与协议一致"，**不能推广为真实数据资格**（真实 ETF 输入资格是另一道闸，
principles §6），也不因合成通过就称"兼容性已验证"之外的任何东西。

### 成本/许可/停止条件
Apache-2.0 代码许可（LICENSE 文件未核——unknown）；隔离环境安装一次；
约一轮执行+主控复核。停止条件：tag 0.4.5 与文档行为不符且差异影响上述
开关；任一手算例不符且原因超出文档语义；触发条件中的研究问题始终未出现
（则本提案自然搁置，不构成欠账）。

### 可写面 / 待批准项
可写面：`docs/experiments/raw/<新实验名>-<日期>/` + `docs/experiments/`
结案报告（登记按归档规约另行完成）；不动 src/、configs/、registry。
待批准三项：①隔离安装 alphalens-reloaded 0.4.5；②新建实验目录与冻结
协议；③结案后是否列为正式横截面分析实现。

## 明确不建议本轮之后立刻做的

- arch/statsmodels 启用：等明确单序列问题再定。
- SPA/多方案检验：无完整尝试史与损失序列（红线：不得宣称过拟合已排除）。
- 外部因子数据下载与本地登记：无消费场景。
