# 保存预测组合：审查证据补充

2026-10-04 Asia/Shanghai。成果基线955611c1e7633a00752a14148f9102e0ad3b8538；本附件版本1。只补证据导航，不改旧合同、定义、输入或成绩，不重跑研究。归档报告仍为 docs/experiments/external-prediction-combination-2026-10-04.md，不另登记一个实验。

## 一句话结论（大白话）

这次组合的是模型已经算出的预测值。两组固定平均都没有超过较好单项；算术已复核，但历史资料实际何时收到、行动记录是否完整，仍有原研究明确保留的缺口。不能由组合算术通过推定原始市场资料全部合格，更不能推出交易收益。

## 原文、定义和省略条件

以下原文是原冻结合同 research_design.claim_mapping 的准确摘录，供审查定位；不是重新创造策略授权。五合同的实际SHA、精确代码绑定、输入和定义绑定完整摘录在 bindings.json，各字段保留原值。原始大文件仅本地，附件不交付市场预测行。

| 原文/准确出处 | 对象ID@版本 | 研究代理与边界 |
|---|---|---|
| tsfresh原合同：“外部时序计算表达可能补充已有价格背景，需用未来涨跌误差检查”；原报告§3引用tsfresh0.21.2固定函数 | research.external.mean_abs_log_change20@1.0.0；research.external.return_autocorrelation20_lag1@1.0.0 | 20个每日对数变化的绝对值平均、固定相邻联系；保留t及以前完整经济收盘和252日共同资格；省略LEI完整执行、真实到达、未见历史。不是桌面原作者买卖定义。 |
| volume原合同：“同涨跌天数下成交偏向可能补充后续风险”；原报告§原文映射与结果前固定的设计，定位技术体系§2.5研究扩展 | research.volume.direction_excess20@1.0.0 | 成交量加权涨跌方向减不加权方向平均；保留20完整量价对、同尺度行动处理、收盘观察；省略完整LEI条件/退出/账户、成交额/资金流、全部单位变化与真实到达。不能把研究扩展说成§2.5唯一公式。 |
| session原合同：“相同近期总变化的隔夜与日内构成差异可能包含额外后续风险信息”；原报告§问题、定义与策略位置 | research.price.overnight_minus_intraday20@1.0.0 | 固定20间隔隔夜减日内对数变化；保留完整报价和经济价尺度；省略LEI触发/退出、可成交开盘、历史到达与独立新资料。属于用户批准的价格风险观察扩展。 |

本轮没有重新独立逐段审阅桌面策略原文；上表复用原合同和报告的语义判断，不能标成本轮新增的原文语义独立认证。两权威原件指纹沿组合protocol.json，本次未修改/外传原件。

## 输入与时间

- 输入类型：五个保存运行 result.json 的 predictions 中B2（已训练模型的预测）；价格组另读共同B0/B1，风险组分别读双方B0/B1和原逐ETF简单参照。原始因子量纲没有直接相加。
- 价格目标：forward_return，经济收盘t+1至t+21，百分点；风险目标：mae，t+1经济收盘作为起点、至t+21收盘路径的下探，百分点。mae在此是风险目标标识，不是平均绝对预测误差。两用途分别计算，不混合。
- 观察为t完整收盘后；供应商历史实际到达未知。label_end是结果成熟日期，不能替代供应商到达时间。原合同训练未成熟标签剔除，评价标签止于原期；本次未重新拟合或选择时间窗。
- 价格四ETF1268条，风险三ETF951条，各317日期；完整保存身份、日期、fold、label_end、y对齐。风险510300仅原市场参照，不作为预测对象。两期旧历史已见，有同日和未来20间隔重叠，不是独立新证据。
- 合同路径与SHA、target/split/weights、原data路径SHA、bindings.files源码SHA及freeze摘要见bindings.json。代码当前状态可能已演进，不能以当前文件代替冻结代码；本附件记录原绑定，没有声称重验全部当前源码与旧绑定相同。

## 方法、对照及实际代码

固定平均适合回答“这些已有预测在这批同一目标记录上平均后，误差怎样变化”。它不回答原因子整体有效性、最优组合或资金配置。

本轮代码位于 docs/experiments/raw/external-prediction-combination-2026-10-04/：
- run_probe.py::align及main：三价格运行严格相同身份、目标、B0/B1；不取交集或补值。equal3三分之一平均，half_simple再与B0各一半。
- risk_followup.py::main：核原target/split/weights相同，逐条身份/成熟/目标/资格一致；分别保留volume和session B0/B1/B2，固定两个B2各一半。不要求双方训练资料或背景完全相同，也不声称相同；只能归因于完整预测组合，不能把差额归给某个孤立因子。
- 每日期完整四/三资产使逐行等比与当前完整面板的资产等比一致；原训练weights separately保留。删ETF汇总不重训，也不作为选资产方案。
- arithmetic-details.json及report_details.py保留更强逐ETF简单参照、逐条改善/恶化；风险双方B0/B1不同的初始发现保存在other-factor-compatibility.json，不覆盖成共同基准。

## 已有复核及未验证

| 层次 | 证据位置 | 本次处理 |
|---|---|---|
| tsfresh原定义/公式/数值 | raw/tsfresh-factor-validation-2026-10-02/controller-pre-freeze-review.json、independent-numeric-audit.*、controller-terminal-review.md、selected-definition-closure.json、verification-root-manifest.json | 复用原报告§8导航；旧源码漂移与失败记录保留。不重新执行。 |
| 两风险原公式/模型/目标 | raw/{volume-direction-information,session-composition-information}-2026-10-04/controller-formula-check.json、controller-verification.json、diagnostics.json | 复用原负责人已有逐行公式、目标及模型方程证据；不将其自报complete替代独立审查者核验。 |
| 本组合算术 | raw/external-prediction-combination-2026-10-04/verification-processes.json、core/summary.json、risk-summary.json、arithmetic-details.json | 已有239价格核数、63风险核数及临时恢复162核数，复用不重跑。 |
| 原始市场完整资格 | 原qualification及source-manifest；原合同省略条件 | 历史到达/行动完整性未验证；远端缺大原件。组合检查没有补齐。 |
| 收益/执行/未见确认 | 无 | 未测量；不推生产。 |

路径表中raw均相对docs/experiments/。bindings.json另给当前实际存在文件的大小与SHA，用于审查定位，指纹一致只证明版本而非科学有效性。

## 报告、登记、聊天一致性及停止条件

组合报告已登记在成果基线的docs/experiments/registry.json，原结论为固定旧历史未找到组合新增帮助；聊天沿用这一有限结论。不能扩写为“所有组合无效”“原因子真实有效”或“线上收益改善”。本附件仅澄清边界，不更改原登记/旧分数，不倒填规范。

本次0新拟合、0新算术实验、0付费/模型调用；只读取元数据和制作证据索引。无后台实验。证据附件提交后供独立审查，未解决事项是原始资料资格边界及独立审查意见；发现具体错误再按影响做最小修正，不重启封存研究。原外部候选生成方向继续保留，规模与调用预算尚未冻结。
