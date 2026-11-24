# RD-Agent、QuantaAlpha 与 AlphaAgent 接入评估（2026-09-24）

## 一句话结论（大白话）

这次检查三套自动研究工具能否帮助 LeiSignal 把实验跑完、保留失败并交出可比较的结果。结论是：**RD-Agent 值得进入小范围接入试验，适合承担研究步骤的调度；现有 ETF 定义、资料核查和资金计算继续由本地程序负责。** 默认股票选强流程不能直接回答双均线是否有用。QuantaAlpha 可参考结果展示和实验记录，AlphaAgent 暂不优先。本轮核到了实际扩展位置和本地缺口，尚未安装、调用外部模型或跑通框架；省工、省钱和研究效果均未验证。

## 1. 问题、范围与已有工作

用户本次要求：“评估一下看看这个能介入吗”。本轮执行公开文档、固定提交源码及本地接口/环境核查，形成采用建议；不把文中建议的试点当成已经执行。服务于交易规格 §2.2、§4、§5、§15 的道路与确认机制研究，以及研究工具建设。框架本身不成为交易规则。

采用研究原则 v1.1、执行合同 v1.0.1、定义标准 v1.1.0、文献流程 v1.1.0。属于工具适配评估，不产生收益或有效性结论；未来收益目标合同不适用。已有 [Qlib 公式审阅](qlib-alpha158-controller-review-2026-09-13.md) 与 [外部复用复核](factor-reuse-refresh-2026-09-22.md)直接承接，不重复研究其已查公式。

当前另有 [均线对照计划](../archive/handoffs-plans/factor-baseline-reset-2026-09-24/plan.md) 正在准备。其首批是六只既定 ETF、20 日主问题、60/120 日辅助探索：3 周期 × SMA/EMA/双线 3 种确认，加持有与固定半仓两个共同参照，共 **11 个政策/产品**。因此不另开用户转贴中的 10 组方案，也不以框架试点重新选择参数。所有已看过的历史继续标为探索资料。

## 2. 已核实的外部事实与取舍

源码读取固定到以下提交，访问日期 2026-09-24；原始文件指纹见 [source-manifest.json](raw/rd-agent-adoption-review-2026-09-24/source-manifest.json)。未阅读三套框架论文全文，也未复现作者公布的收益或成本；这些宣传数字没有用于本地采用判断。

| 框架与固定提交 | 实际核到的能力/边界 | 本地判断 |
|---|---|---|
| RD-Agent `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` | 场景、假设生成、实验转换、代码开发、运行与反馈类可配置；有步骤记录、恢复及轮数/时长控制。MIT 许可原文存在 | 第一候选，试用独立研究执行流程；需要自定义 ETF 场景及结果转换 |
| QuantaAlpha `b7ceb27b1001261d7a95b209a963664ae1f8ab23` | 因子库、Web 展示、独立回测、方向/迭代配置；默认仍以 Qlib 股票预测和选强组合为中心 | 保留工作台与记录方式参考，本轮不并行引入第二套运行平台 |
| AlphaAgent `b42cb397025510da44355db9dcf278304321f589` | 当前 README 定位 A 股多因子研究，FactorZoo 表达式评价和可选 AgentScope 挖掘；参考资料为中证1000相关股票集合 | 与本轮 ETF 单标的均线问题距离更远，后置 |

直接依据：[RD-Agent 循环组件](https://github.com/microsoft/RD-Agent/blob/484776c211e4fbbeef03e0ec00d6bbee7362a4f4/rdagent/components/workflow/rd_loop.py)、[循环运行与恢复](https://github.com/microsoft/RD-Agent/blob/484776c211e4fbbeef03e0ec00d6bbee7362a4f4/rdagent/utils/workflow/loop.py)、[QuantaAlpha 使用指南](https://github.com/QuantaAlpha/QuantaAlpha/blob/b7ceb27b1001261d7a95b209a963664ae1f8ab23/docs/user_guide.md)、[AlphaAgent 当前说明](https://github.com/RndmVariableQ/AlphaAgent/blob/b42cb397025510da44355db9dcf278304321f589/README.md)。

有三处需要修正转贴材料给人的直觉：

1. **`fin_factor` 仍会训练预测模型。** 它避免了因子与模型结构一起自动改动，但默认评价仍通过 LightGBM 和选前50只股票的组合完成；不是纯粹拿新因子与原买卖规则比较。[固定评价模板](https://github.com/microsoft/RD-Agent/blob/484776c211e4fbbeef03e0ec00d6bbee7362a4f4/rdagent/scenarios/qlib/experiment/factor_template/conf_combined_factors.yaml)还带股票费用、1亿元模拟账户及自己的目标期限，均不能照搬到六 ETF。
2. **自动反馈不等于保留了独立的最终检验。** RD-Agent 的当前 runner 使用 `test_start/test_end` 运行评价，feedback 将当前结果与此前最佳结果交回模型，继续提新假设。因此这些被反馈的区间已经参与选择。需要另留不向生成模型暴露的最终检验，或者如本项目现状一样明确全部只是探索；不能仅靠把字段叫 test 就称为未见资料。[运行源码](https://github.com/microsoft/RD-Agent/blob/484776c211e4fbbeef03e0ec00d6bbee7362a4f4/rdagent/scenarios/qlib/developer/factor_runner.py)、[反馈源码](https://github.com/microsoft/RD-Agent/blob/484776c211e4fbbeef03e0ec00d6bbee7362a4f4/rdagent/scenarios/qlib/developer/feedback.py)。这不构成对论文全部实验的审计。
3. **有轮数配置，仍需核实际调用总量。** QuantaAlpha 固定提交默认两方向、每方向两轮、三轮进化，表达式一致性检查关闭；指南示例数值与仓库实际配置不完全相同。轮数、重试、代码纠错和模型调用要一起计数，不能直接保证总费用。以上只是配置核查，未运行证明每个开关的行为。[实际配置](https://github.com/QuantaAlpha/QuantaAlpha/blob/b7ceb27b1001261d7a95b209a963664ae1f8ab23/configs/experiment.yaml)。

许可检查：RD-Agent 读取了 MIT [LICENSE](https://github.com/microsoft/RD-Agent/blob/484776c211e4fbbeef03e0ec00d6bbee7362a4f4/LICENSE)，本轮保存其选定源码并保留许可。QuantaAlpha README 徽标及包元数据声明 MIT，但固定提交树未找到独立许可文件，GitHub 许可字段为空；AlphaAgent 说明开源但所查提交未找到具体代码许可文本。本轮对后二者仅作少量定点阅读并保存 URL/指纹，未整库复制；未来代码再利用前需确认完整许可。代码许可也不代替行情数据许可。

## 3. LeiSignal 的真实接入位置

建议的关系是：**固定研究任务 → RD-Agent 调度 → 调用本地已接受的研究程序 → 本地核对结果 → 现有报告库/因子页面**。这只是拟接入关系，当前没有建立该通路。

| 位置 | 当前代码事实 | 需要的适配 |
|---|---|---|
| 研究任务 | 已有定义登记、冻结协议和尝试记录 | 转为 RD-Agent 场景与实验对象，保存本地问题、规则和输入身份；首轮使用已固定任务清单 |
| 外层流程 | RDLoop 能按类配置加载各步骤，但仍引用 Qlib 基础因子；fin_factor 也有 Qlib 专用处理 | 自定义场景、实验转换、开发步骤、runner 与反馈；不能只改股票代码或一个 runner 配置就宣称接通 |
| 计算/资金 | `factor_lab` 有复用函数；`scripts/run_factor_lab.py` 的统一协议仍限制 `data_mode=synthetic`；真实研究另有专用程序 | 首轮调用获准的人工小例入口；真实阶段衔接均线计划交付的账户程序，不绕过旧入口限制、不另造账户引擎 |
| 结果消费 | `research/factor_access.py` 已提供只读证据/结果接入；`copilot/factor_readonly.py` 已消费，旧使用手册“未绑定”表述有时效限制 | 做 JSON/CSV 到既有结果格式的转换；候选新公式先保留草案身份，不直接改正式定义或资格 |
| 判断与反馈 | 默认反馈关注相关性、相对收益和相对净值下跌 | 按本轮完整账户指标输出：净收益、账户跌幅、恢复等待、投入比例、交易及费用；LLM 说明不能代替固定数值判据 |
| 前端 | 已有 `web/` 因子研究页面与展示目录 | 验收后的结果进入现有目录；无需先迁移 QuantaAlpha 前端或另开一套门户 |

本地依据：`src/lei_signal/research/factor_lab/contracts.py`、`runner.py`、`src/lei_signal/research/factor_access.py`、`src/lei_signal/copilot/factor_readonly.py`、`web/src/pages/factor-research/model.ts`。读取时点指纹见本轮静态核对记录。以上为静态接缝确认，不是已完成兼容性验证。

## 4. 环境、投入与尚未验证项

- 本机为 macOS arm64；当前 shell Python 3.11.7，launchd 配置指向的应用 Python 为 3.13.12。两者均未发现 rdagent/pyqlib/quantaalpha/alphaagent/litellm 分发包；当前 PATH 未找到 Docker、Podman、Conda、uv。这不能证明机器其他目录或远端都没有这些工具。
- RD-Agent [官方 README](https://github.com/microsoft/RD-Agent/blob/484776c211e4fbbeef03e0ec00d6bbee7362a4f4/README.md)声明当前支持 Linux，多数场景需 Docker，CI 充分测试的是 Python 3.10/3.11。建议独立 Linux 环境和独立 Python 3.11 环境；Mac 作为宿主的实际兼容性仍须实测，不向现有应用环境直接安装。
- 模型聊天、结构化输出及部分场景的嵌入能力需要可用服务。没有验证这些项目能直接继承当前 Codex 会话的模型接入；下一步须明确供应商和实际调用计费。没有读取凭据、调用付费模型或估造费用。
- 适配工作至少包含研究任务转换、现有程序调用、结果转换、受限反馈和运行隔离。工作量判断为中等，尚无工时实测；“改一条配置就能用”证据不足。固定均线批次本身不需要 AI 自由生成公式，框架是否比现有调度省工必须单独比较。

## 5. 一次有结束条件的试点建议

以下是可交执行者的建议范围，不是已执行或新运行许可。

**第一步，验证真实框架能调用本地程序。** 固定 RD-Agent 上述提交，在独立环境运行上游实际流程一次；只用人工价格和固定的一项均线对照，复用本地已接受计算。首轮固定一条任务、单并发、一个外层循环；自动发现新公式和模型结构搜索关闭。模型调用、代码纠错次数及金额上限在启用模型前写进运行配置。无需为了展示框架先下载股票池。

验收必须同时看：真实 RD-Agent 步骤记录存在；本地输入/规则身份一致；结果与直接调用同一程序一致；人为中断恢复不重复覆盖成果；失败留下具体原因；报告能进入既有只读消费格式。只造一个假的 RD-Agent 对象或只检查 JSON 不算接入成功。运行身份必须精确绑定，不从共享目录猜“最新结果”；上游示例 `read_exp_res.py` 按最新 recorder 取结果，不能原样用在并发共享记录库中。

**第二步，比较它是否值得保留。** 在均线主线的协议、资料和账户程序验收之后，让框架执行同一份11政策任务清单，与直接执行方式比较结果一致性、人工介入次数、重复/遗漏运行、模型调用、费用和耗时。复用同一套真实研究产物或明确核准的复现，不制造第二份独立市场证据。研究结论为负也可以完成工具验收。

采用条件：步骤记录和失败处理确实省去人工接续，结果完全可追溯，成本可接受。停止条件：必须迁移到股票预测模型才能运行、另建整套资金引擎、无法约束修改评价代码或反复反馈最终检验、或者没有减少维护负担。失败保留并继续现有研究路径，不让框架安装成为均线问题的前置。

## 6. ARCHIVE 与最小决策卡

| 问题 | 决定 |
|---|---|
| 能否接入 | 源码显示有可扩展位置；RD-Agent 作为独立研究执行流程有条件可行，尚未实跑 |
| 第一优先 | 验证一条固定任务调用本地程序和回收结果，再评价自动提案/写代码 |
| 其他两套 | QuantaAlpha 作展示与记录参考，许可确认后才考虑代码采用；AlphaAgent 后置 |
| 已有研究如何继续 | 承接2026-09-24均线11政策计划，框架评估不重开参数与数据研究 |
| 本轮实际成果 | 固定源码核查、本地环境与接口核对、接入方案、试点验收与停止条件 |
| 未完成 | 安装、上游实际循环运行、调用模型、真实数据接入、成本及节省工时验证 |

归档分类为“方法论与验证”，verdict=mixed。本轮由当前 Codex 直接完成，没有新增执行子任务。报告、来源清单及静态核对记录落在本日期目录；外部资源既有目标 `okr-4f4157e2957e` 追加此次评估依据和建议，不重复建目标、不勾选整体完成。

交付核查：16份定点源码/配置读取有URL与指纹，11份RD-Agent文件连同MIT许可已保存并复核；8项静态事实核对满足预期，Python源码仅作语法解析，未导入执行。三份固定提交树均未截断，许可文件检查范围见[记录](raw/rd-agent-adoption-review-2026-09-24/license-tree-check.json)。本地文件指纹、环境和检查范围见[static-checks.json](raw/rd-agent-adoption-review-2026-09-24/static-checks.json)。报告登记、索引、本地链接、JSON格式、仓库归置与指定文件差异格式检查通过；这些不代表框架运行通过。目标记录仅追加本次用户要求、评估证据与下一步，状态/原授权/完成勾选保持，API读回核对见[okr-update.json](raw/rd-agent-adoption-review-2026-09-24/okr-update.json)。
