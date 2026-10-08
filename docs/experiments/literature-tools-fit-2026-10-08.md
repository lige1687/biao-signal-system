# 三本书与三个开源项目：对 LeiSignal 研发的具体用途

## 一句话结论（大白话）

最值得借用的是三件事：从 CrossSection 学习怎样保存一个观点的出处、准确含义和失败证据；从 Alphalens 借用排名稳定性与分组变化的诊断；从 Carver 与 pysystemtrade 学习怎样把“看到了什么”与“如何使用”分开。Aronson 帮助审查判断是否站得住，APM 帮助理解为什么多个好判断仍可能集中承担同一种风险。此次是理论与代码适配审阅，没有证明这些方法能提高 LeiSignal 收益。

范围：沿用 research-closure 的 report_only。三本书使用官方目录、作者说明及相关教学资料，未通读全书。三个项目固定到提交版本，静态检查 12 份文件，未安装或执行第三方项目。与 10 月 7 日观点综合相比，本轮新增具体函数、字段和采用障碍；不重做旧实验。

## 1. 风险、机会质量与仓位之间的关系

用户理解的方向成立，但需要保留三个不同问题：

|问题|需要研究的对象|不能从中直接推出|
|资产容易跟什么一起涨跌？|风险暴露，例如市场下跌时是否通常跌得更多|下一次下跌什么时候发生|
|某状态是否提前提示损失？|未来损失概率、严重程度、预警覆盖与误报|收到提示就退出一定划算|
|收到提示后如何使用？|保持、减仓或退出后的完整结果，包含错过上涨与重新参与的代价|某个特征本身具有更强预测力|

因此“避开多少下跌、错过多少上涨”是风险信息的使用价值，需要先知道信息是否可靠，再比较动作。机会质量可以作为特征；实际仓位还依赖现有持仓、资金与限制。同一个机会在不同账户里应有不同金额，不能把最终仓位全部归因于一个固定的机会分数。这是本轮方法综合，不是新策略规定。

## 2. CrossSection：最值得借的是证据组织，同时要核实现

核查版本：`OpenSourceAP/CrossSection@8db892442c2c3a3779b0f1eac4370d3655be15a1`。

`SignalDoc.csv` 将作者、年份、原文表格、定义、数据类型、原文证据强弱、复现质量、分组方式和研究时间连接起来。对我们最有用的不是增加一个目录，而是在既有定义与文献记录中补齐缺失出处和原文适用条件。它既包含价格动量，也包含风险特征；不能把它理解成只有基本面的股票因子库。[固定版本资料表](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/SignalDoc.csv)。

两个有用例子：

- `Mom12m`：代码按月份处理滞后收益，并把缺失收益补成零；这提醒我们复用公式时必须同时核时间约定与缺失含义。资料表写 t-12 到 t-1，所读 Python 明确乘 t-11 到 t-1 的 11 项。此处存在需要原文和日期约定进一步解释的表述差异，本轮不宣布哪一方错误，不直接复制成我们的正式定义。
- `DownsideBeta`：衡量市场较弱时跟随市场变化的程度。资料表保留其事前预测证据不足的分类与说明；这不等于所有风险用途都无效。尤其是“用后来发生的风险解释后来收益”与“用此前知道的风险预测未来”不同，适合作为研究讨论中的反例。

还发现不能忽略的实现差异：资料表写 252 个交易日窗口、至少 50 次观察；所读 Python 先筛选市场较弱的日期，再用 252 行窗口和至少 10 行做估计。代码所表达的观察单位与门槛和资料表不一致。未运行其依赖、未对照原 Stata 和论文，故判断为**需要核实的差异**，不是已确认上游错误。直接搬代码会把这些选择一起带进来。[实际实现](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/Signals/pyCode/Placebos/ZZ2_DownsideBeta.py)。

采用判断：立即借用出处和反例组织方式；动量、市场敏感度等可作未来有出处的候选参照。美国股票数据、原作者结果和具体实现均不直接迁移为 ETF 结论，也不因此扩大基本面参与技术判定的范围。

## 3. Alphalens：补充诊断，不替换现有验证入口

核查版本：`stefan-jansen/alphalens-reloaded@f0a07c22d554e4b4036983cc80320b432714fe7e`。

|实际函数或能力|对我们的用途|相对已有系统的判断|
|`factor_information_coefficient`|比较同一天的分数排序与以后收益排序是否一致|factor_lab 已有同类计算，重新安装不能算增量|
|`quantile_turnover`|观察某个高分组中有多少成员换了|可能补充“机会名单是否忽冷忽热”的解释；不是实际交易金额换手|
|`factor_rank_autocorrelation`|观察前后两次排序是否稳定|可帮助判断分数变化频率与研究时间尺度；稳定不代表预测正确|
|分组收益与报告组织|让读者同时看到效果、变化和覆盖|复用报告思路；已有分组与时点检查继续保留|

本地核对入口为 `factor_lab/diagnostics.py`、`rank_ic_evaluation.py` 与 `factor_diagnostics.py`。后者的账户金额换手不能与上面的成员变化比例混称一个指标。排名稳定性函数未在本轮检查的入口中找到，不据此声称全仓库均无实现。[上游诊断代码](https://github.com/stefan-jansen/alphalens-reloaded/blob/f0a07c22d554e4b4036983cc80320b432714fe7e/src/alphalens/performance.py)。

具体采用障碍：`get_clean_factor_and_forward_returns` 默认 `filter_zscore=20`，源码明确提醒，用未来收益分布剔除异常值会引入未来信息；底层 `compute_forward_returns` 的默认值则为 `None`，不能把二者混说。入口还默认容许一定比例资料在清洗中丢失（`max_loss=0.35`）。若将来适配，应明确关闭前者，逐项报告后者的丢失原因并服从已有合同，不能直接接受默认清洗后的漂亮报告。[清洗入口](https://github.com/stefan-jansen/alphalens-reloaded/blob/f0a07c22d554e4b4036983cc80320b432714fe7e/src/alphalens/utils.py)。

采用判断：有条件借用排名稳定性和报告组织；少量高度相关 ETF 的排名解释力有限，单 ETF 风险预警更不能强套股票排序报告。未经适配测试，不声称函数已接入。

## 4. pysystemtrade：把系统各环节的含义讲清楚

核查版本：`pst-group/pysystemtrade@326b5d402c2825cc8561cabb899d1454e593bda9`。

|所读模块|能够借用的思路|对 LeiSignal 的限定|
|`forecast_scale_cap.py`|先统一信号尺度，再限制极端值|分数尺度统一不等于上涨概率已校准；不改写原技术含义|
|`forecast_combine.py`|考虑不同信号的相关程度、权重及组合规模|多个指标名称不等于多份独立证据；复杂权重仍要和简单组合比较|
|`positionsizing.py`|将预测分数与单位风险对应的持有规模分开|源码是波动尺度与预测分数相乘；历史波动不是止损距离，也不是损失上限|
|`risk_overlay.py`|按整体风险、压力情形和杠杆限制缩减持仓|是使用约束，不是新的预测因子；本轮不采用其阈值|
|`buffering.py`|给目标持仓设置容许小幅变化的范围|可作为减少微小调整的研究思路；此文件构造范围，不等于完整交易执行已验证|

对因子系统的直接帮助是保留不同含义：原始特征、预测判断、风险估计和动作规则分开记录。这样研究失败时能定位是信息无用，还是使用方式不合适。这一分层作为学习依据，不要求再建一套执行框架。[仓位模块](https://github.com/pst-group/pysystemtrade/blob/326b5d402c2825cc8561cabb899d1454e593bda9/systems/positionsizing.py)、[整体风险模块](https://github.com/pst-group/pysystemtrade/blob/326b5d402c2825cc8561cabb899d1454e593bda9/systems/risk_overlay.py)。

采用判断：现在借系统边界与设计思路；未来明确开展融合或动作研究时参考具体方法。期货引擎、接单接口、杠杆与参数不迁移，本轮也不复制代码进正式实现。

## 5. 三本书收敛成三个研发问题

|资料|核心问题|值得带回现有研发流程的内容|边界|
|Aronson|什么证据能使我们改变原来的看法？|研究前说清预期、对照与反例；评价时保留搜索次数和负结果|统计检查不能替代合理问题和资料资格|
|Carver|一种信息该在系统哪一步发挥作用？|区分预测、组合、风险尺度和执行；复杂方法与简单方法比较|不能从书中的组织方式推断本地参数有效|
|APM 及相关理论|多份判断经过共同风险与实际约束后，还剩多少可用价值？|关注新增的独立判断、重复暴露、预测与实施之间的损失|不是一切择时问题的统一考试，也不必立即做组合优化|

Aronson依据为[出版商目录和章节介绍](https://onlinelibrary.wiley.com/doi/book/10.1002/9781118268315)；Carver依据为[作者说明与目录](https://www.systematicmoney.org/systematic-trading-information)。APM 的本轮理论归纳参照 [CFA 主动管理教学说明](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/analysis-active-portfolio-management)，不是声称核验了书中某页原话。

三者合起来支持的方向是：**先寻找有意义且可反驳的问题，再辨明信息的作用位置，最后检查重复风险与约束是否削弱用途。** 这为现有研究卡提供理由，不另加一套强制表单。

## 6. 本轮决策与接续

本轮理论适配问题已回答；效益量级未测，不虚构提高多少收益或节省多少时间。最值得优先复用的是 CrossSection 的来源追踪，其次是 Alphalens 尚未覆盖的诊断，再是 Carver/pysystemtrade 的信息与动作边界。APM 用于后续融合方向的理论约束。

低频执行日期差异保留为后续策略实施问题：此前固定入金星期的观察不等于未来月度调仓规则验证。没有创建自动执行日程，没有选出“最佳日期”。人工判断研究沿用现有负责人，不重启。风险与仓位主题只给方法依据，不与当前 D—MAE、原生流程、数据资格和调度任务重复计算。

归档状态：报告与源码快照已保存在本机；共享登记等待明确本任务写入范围后串行合入，未写 `registry.json`、`INDEX.md` 或别人的协调文件，不宣称完整归档或远端同步。登记候选在本报告 raw 目录。

## 7. 核查与复现位置

- 原始来源、提交和文件 SHA：`docs/experiments/raw/literature-tools-fit-2026-10-08/source-files.json`；各项目 tree JSON；`sources/` 下 12 份静态原文。版本指向检查时实际提交，不暗示未来保持不变。
- 本地参照：`src/lei_signal/research/factor_lab/diagnostics.py`、`rank_ic_evaluation.py`、`attribution.py`；`src/lei_signal/research/factor_diagnostics.py`；既有 `literature-rd-core-ideas-2026-10-07.md`。
- 已在线获取协调分支并读取规则、`external-quant-resources`、`research-dispatch-controller`；基线 `875f197c52f6e74a584e146dfa43513b826748aa`。本轮仅准备自己隔离的新文件；未取得共享修改的登记准入。
- 验证回执另存 `verification.json`。不运行市场实验，不作因子性能表；本报告采用定性判断、代码证据、反例与适用范围。
