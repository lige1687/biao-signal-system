# 外部增量：量化资源适配与效果验证（持续任务）

最后更新：2026-10-03T13:31:54.074651+08:00，Asia/Shanghai（UTC+08:00）。负责人：本聊天“外部增量”；设备 MacBook-Air-126.local；仍由原负责人推进，**本次是成果与进展同步，不是交接接管或任务结束**。

## 原始目标及当前范围

从 FactorHub/Codex skill 评估，扩展到适合 LEI 宽基和 ETF 的开源方法、研究工具与有界因子效果比较。服务研究工具和证据层；工具正确、预测增量和真实交易收益分别记录。不改策略原文/生产交易/Streamlit，不接券商，不采购服务；基本面与消息不进入技术判断。

最新用户要求：把已有安全成果和实际进展同步现有 GitHub，便于另一 AI 查看和避重；原负责人继续推进。历史交接包的“冻结研究/接管”描述只代表当时用户要求，本次明确撤回接管安排，**以本文件的当前负责人及范围为准**。旧包/原锁/成绩保持原字节，仍可复现旧阶段。

## 基础版本与上传方式

- 现有 origin：git@github.com:lige1687/biao-signal-system.git；项目 https://github.com/lige1687/biao-signal-system。
- 原共享工作区分支 codex/factor-unit-research-20260915；完整 HEAD 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；无切换/清理/回滚。
- 本轮独立持续分支：`task/external-quant-progress`，此前没有该远端分支；使用用户此次明确指定的 task/ 命名。
- 本轮父提交 `1ac596f65110e06c286f04707165251328df0962`，已有远端交接证据包；代码初次包提交725478cb15750c4b4f16e409a591b8b55489cad1。
- 本分支根路径补入本任务独有代码/测试/报告/小证据。共享规范/研究代码只保留旧包中的必要依赖快照，不整文件提交当前其他负责人的修改；registry只追加本任务14个原记录，pyproject只加本任务2个可选依赖。
- **WIP：分支根路径与共同研究主线的整体整合尚未完成。** 基线还没有其他负责人开发的workflow/workflow_inputs等模块，因此不能宣称直接从该分支根目录运行全部研究/部署通过。可运行的完整最低任务目录依既有交接包 restore.py 重建；必要依赖位于该包payload中，已核版本和指纹。另一AI应查看源码/报告和下面文件归属，不把本分支当生产部署候选。

## 已完成（每项都有关联证据）

|成果|文件/证据|实际验证与业务边界|
|---|---|---|
|FactorHub五项GET只读适配|.agents/skills/factorhub-readonly；docs/experiments/factorhub-codex-2026-10-02.md|25项工程检查；真实接口缺用户安全配置，未验证当前访问|
|资料可得时间、预测边界技能|.agents/skills/lei-data-availability；lei-causal-validation；open-finance-skills报告|24项限定例子；不替换项目研究合同|
|有限统计、日历及归档读取|.agents/skills/lei-quant-tools；quant-resources-adoption/integration/workflow-fit报告|组件27项、桥接29项；缺日/跨多拟合时期拒绝；不补行情、不重训|
|Hypothesis生成反例|tests/unit/test_research_property_checks.py；external-increment报告|128个生成例与故意错误例；没有发现项目新bug或金融收益增量|
|tsfresh公式和正式适配器|tsfresh_calculators.py、tsfresh_candidates.py、src/lei_signal/research/tsfresh_price_information.py；tests/unit/test_tsfresh*.py|26+5项合成检查；源函数0.21.2、许可保留|
|tsfresh当前预测用途结案|docs/experiments/tsfresh-factor-validation-2026-10-02.md及四份forecast-artifact报告|4 ETF/4固定比较/16真拟合；共同1268行317日。既有背景误差8.221932，加两表达8.725659；两单项也变差，历史均值6.804367更好。账户收益未测量|
|arch共同误差工具与退化保护|.agents/skills/lei-quant-tools/scripts/multiple_comparison.py及lei_arch_bootstrap；tests/unit/test_multiple_comparison.py；external-multiple-comparison报告|固定arch8.0.0；22回归、3×1000合成独立算式；888行222日旧预测只读核查、0真拟合；不能替代完整尝试史|
|读取规模评估|docs/experiments/parquet-reading-assessment-2026-10-02.md|既有约9.84MB资料未显示迁移理由；DuckDB未安装/实测|
|最低独立恢复和资料指纹|docs/archive/handoffs-plans/external-quant-handoff-2026-10-03/|新环境安装与56项唯一测试有通过证据；初版漏V2导致3失败，补齐后受影响5项全通过；3份保存预测原件不变。Linux/Windows未验证|

本次仅同步已核源码；上述代码对旧验收快照指纹无变化，**不重跑已完成大实验**。最新安全范围与最小检查记录见 docs/progress/external-quant-progress-sync-2026-10-03.json。

## 正在做（有边界，非泛称优化）

1. 当前执行：本任务成果同步与上传清单/差异检查；维护本文件和docs/ops/work-progress/external-quant-resources.md。
2. 同步后恢复：下一批外部计算候选的来源、许可、用途与已有信息重复核查。先查本库评估/其他任务当前范围，再选择一个明确问题；候选/新合同尚未冻结，0新拟合，不能把计划写运行中。
3. 继续维护：上述四项目skills、共同误差与归档读取工具的研究边界；只在具体风险或输入变化时做必要检查。

## 下一步（计划，尚未启动）

- 用少量公开原始资料比较尚未被tsfresh/Qlib已有研究覆盖的外部计算候选，先核许可和可解释用途。只有能改变判断的明确问题才登记新合同/来源/预算；不为公式数量添加无意义计算。
- 共同研究主线同步完成后，只整合本任务适配器和准确两定义，不接手其他技术含义实现。若对方已经修复旧接口/错误，复用其结果再决定是否需局部调整。
- FactorHub实际查询和远端真实资料复现，分别依赖安全凭据和材料使用/存储授权；缺它们不阻止纯源码选型，不能伪装真实访问成功。

## 其他AI请暂时避开的准确范围

- 写入 `.agents/skills/{factorhub-readonly,lei-data-availability,lei-causal-validation,lei-quant-tools}/`；特别是 multiple_comparison.py、workflow_bridge.py、tsfresh_calculators.py、tsfresh_candidates.py 与本轮同名测试。
- 两表达定义 research.external.mean_abs_log_change20@1.0.0、research.external.return_autocorrelation20_lag1@1.0.0 的当前固定20间隔预测用途；封存，不重新拟合/改参数。
- raw/external-multiple-comparison-2026-10-02 与 raw/tsfresh-factor-validation-2026-10-02 的原账本/原结果；本进度文件及本任务独立分支，由本负责人单写。
- 下一批只占当前来源/重复核查；**不独占所有新因子、所有ETF研究或所有外部库**。其他AI可推进别的明确问题，在新题实施前互核范围即可。

本负责人不认领：EMA/SMA等待、顶部/回调/2B语义、经典Qlib、情绪/宽度/宏观、账户政策、远端T2-T10/完整A及小时资料。最新本机技术顺序任务进度2026-10-03T13:12:45+08:00；远端及未提交任务实时状态仍需对方自己的分支/进度确认，不能凭旧快照宣称全部去重完成。

## 未完成、暂停与阻塞

- WIP共享研究主线整体整合，根路径全项目测试/部署未验；本次不修改其他负责人模块以制造完整状态。
- 暂停：FactorHub真实认证调用（缺FACTORHUB_API_KEY及平台权限）；完整科学skills整包下载未成功不记安装。
- 阻塞远端真实资料复现：`docs/ops/recovery/external-quant-handoff-20261003/research-materials.tar.gz`，8,326,487字节，SHA256 `a6fff0b74610b91474d3f7d217b3122dd1b4412d4ca15bc64a5acbe5c74f3818`，仍仅本地；没有授权远端位置或数据再分发资格。本次不直接塞入Git。
- 原供应商资格文件约70,348,971字节未交，逐文件大小/原SHA见旧包evidence/source-qualification-inputs.json；只读旧预测不需这些来源原件，重新核资料资格才需要。
- 系统待升级目标okr-4f4157e2957e仅本地成果追加稿，外部数据库未写；没有用户验收完成/真实收益提升记录。
- Linux/Windows、整套库、自动skill选择、云端真实数据运行均未测量/未验证。
- 原工作区其他任务未提交文件不属于本轮，原样保留；共享定义/协议等只保留小型归属记录，不整包提交。

## 封存与预算

已封存上述tsfresh固定用途与arch限定工程验收。不能因换AI/分支/文件名重置已看历史或预算，不能压缩缺日、填未成熟尾部、调窗口求正结果。累计公开来源28次、工程16批；tsfresh16真拟合；arch5/6请求、4/4工程批、0拟合、3565.764652/3600秒。新问题的范围与预算须另明确记录，旧账本保持原字节。

## 版本与依赖

策略体系SHA df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20；实现SHA85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903；四ETF panel SHA382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b。归档合同、收据和旧成绩不改。Python3.11.7/NumPy2.1.1/Pandas2.3.3/SciPy1.17.1/Hypothesis6.147.0；完整环境和旧冻结验证器漂移见旧包。

## 阶段记录

|时间|阶段|实际状态|相关提交|下一动作|
|---|---|---|---|---|
|2026-10-03T13:31:54.074651+08:00|持续任务恢复及安全同步启动|原负责人继续；独有代码/报告选择完毕；无新金融实验|父提交1ac596f65110e06c286f04707165251328df0962；本次未提交/推送|核最小差异和远端commit后继续下一候选资格核查|

包含本文件的准确提交由 `git log -1 --format=%H -- docs/progress/external-quant-resources.md` 查询；不为写自身SHA连续补写。下一阶段记录已存在提交与真实推送回执。
