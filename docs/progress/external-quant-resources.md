# 外部增量：量化资源适配与效果验证（持续任务）

最后更新：2026-10-03T13:41:41.637779+08:00，Asia/Shanghai（UTC+08:00）。负责人：本聊天“外部增量”；设备 MacBook-Air-126.local；仍由原负责人推进，**本次是成果与进展同步，不是交接接管或任务结束**。

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

## 正在做（当前负责，区分实际计算）

- 原负责人继续维护上述四个项目技能、归档读取/共同误差工具及两项已封存适配器；当前没有后台金融计算、安装或新因子拟合。
- 本次成果安全同步已完成；共享主线整合仍为WIP。已只读核对工具需要的准确函数与签名，清单在 `docs/progress/external-quant-shared-dependencies-2026-10-03.json`；不改由其他负责人维护的主线文件。当前缺的是本分支共同主线版本，不能说整体整合已通过。
- 同步后已实际继续catch22来源/许可/用途筛查，6次原始资料核查、0安装/0拟合，该有界来源阶段已结案。报告 `docs/experiments/external-catch22-screening-2026-10-03.md`：保留计算候选，尚不满足直接加入正式挖掘的条件。没有把其他新因子方向圈为独占。
- 上述阶段已在6d8ad5c80c055337e2bb33c536ec3cbf1f50fd5e发布并核验；本轮接入统一协作后继续原任务。共享主线改写/整合暂缓，等待实际负责人及已发布依赖版本；独立工具和来源核查可继续。

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

已封存上述tsfresh固定用途与arch限定工程验收。不能因换AI/分支/文件名重置已看历史或预算，不能压缩缺日、填未成熟尾部、调窗口求正结果。截至旧阶段累计公开来源28次、工程16批；本次catch22新增6次，总计34次、工程仍16批；tsfresh16真拟合；arch5/6请求、4/4工程批、0拟合、3565.764652/3600秒。新问题的范围与预算须另明确记录，旧账本保持原字节。

## 版本与依赖

策略体系SHA df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20；实现SHA85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903；四ETF panel SHA382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b。归档合同、收据和旧成绩不改。Python3.11.7/NumPy2.1.1/Pandas2.3.3/SciPy1.17.1/Hypothesis6.147.0；完整环境和旧冻结验证器漂移见旧包。

## 阶段记录

|时间|阶段|实际状态|相关提交|下一动作|
|---|---|---|---|---|
|2026-10-03T13:31:54.074651+08:00|持续任务恢复及安全同步启动|原负责人继续；独有代码/报告选择完毕；无新金融实验|父提交1ac596f65110e06c286f04707165251328df0962；本次未提交/推送|核最小差异和远端commit后继续下一候选资格核查|

包含本文件的准确提交由 `git log -1 --format=%H -- docs/progress/external-quant-resources.md` 查询；不为写自身SHA连续补写。下一阶段记录已存在提交与真实推送回执。

| 2026-10-03T13:41:41.637779+08:00 | 安全同步后实际继续外部候选核查 | 首次成果同步0692d3ba4aa99ae9eff988fd0b6a0842a9faef81已推送，190文件远端指纹相同；catch22来源阶段完成，0安装/0拟合；共享依赖签名清单生成 | 本阶段报告/进度发布，不把计划写运行中 | 首次同步commit0692d3ba4aa99ae9eff988fd0b6a0842a9faef81；task/external-quant-progress | 本负责人继续维护工具和有界来源/用途问题；共同主线整合仍WIP |

新增阶段的范围：仅catch22公开来源与输入/许可资格核查已完成，具体新金融用途、工程安装与效果未开始；不要求其他AI避开全部catch22研究。请复用本报告，避免重复相同版本/来源初查。


## 统一协作接入：2026-10-03T14:04:19.965435+08:00

唯一跨任务实时入口：`coordination/lei` 的 `docs/coordination/tasks/external-quant-resources.md`；本文件保留阶段历史和证据，不是排他锁。读取规则版本1.0，提交b172008890b39e912c8f1d0cfb9125d1e414a97f。catch22及依赖清单已在6d8ad5c80c055337e2bb33c536ec3cbf1f50fd5e推送核验。已读初始化任务和technical-factor-sequence：无已登记同题冲突，未登记任务状态未知。继续维护本任务四技能和归档比较工具；暂不改共享workflow/workflow_inputs/question_contract及技术语义模块，下一步只读核对实际依赖发布状态后决定是否具备整合条件。无新拟合、无后台研究、无预算重置；本轮只修改本分支AGENTS协作入口和两份自身进度。


## 2026-10-03T15:16:56.792138+08:00：统一协作复核后实际继续

读取coordination/lei@15b3e4e0edd878c3e84ef30482d108e492563dbd，沿用唯一external-quant-resources，AGENTS入口已存在未重写。最新九条任务无本任务同题写入冲突，未登记者未知。完成有界依赖兼容审查，见docs/progress/external-quant-compatibility-2026-10-03.md及同名小证据目录：17导入绑定、7一致人工场景及1能力差异反例。候选d4443168缺两tsfresh定义/计算器且不含经典风险专属分支，不整文件替换共享主线。Sol助手只读已完成，无运行中金融实验/拟合。原负责人继续，共享整合暂停；工程累计18批、来源34、真拟合16，不重跑旧题。代码和小证据待本工作分支本阶段推送，包含自身commit从Git历史定位；跨任务实时入口仍docs/coordination/tasks/external-quant-resources.md。


## 2026-10-03T15:44:20.674960+08:00：用户收敛本对话目标（brainstorming中）

用户原话：“c是对话的目前主要的目标吧， 然后b其他系统也在做》 你这一块可以收敛了哈， 我们主要是研究外部系统提供的增量，不要和远端在做的事情重复啦。”

C指建立持续研究能力：提出想法后能够找资料、准备数据、完成比较并形成可信可复现答案，减少用户逐项推动。本任务聚焦外部系统/项目/skill能给现有研究流程补什么具体能力；B（验证LEI自身经验/规则）由其他任务负责。本任务不继续扩展已有共享框架/LEI规则验证支线，已有成果、负结果、预算和维护责任保留。

当前阶段：与用户逐题澄清外部增量的用途、优先困难和验收方式；具体候选/实施方案尚未确定。先问痛点，再核已覆盖能力和远端范围；新设计确认前不安装新系统或启动实验。此次不是新的研究预算，0来源/拟合/市场实验，已有工程累计18批、公开来源34、tsfresh16拟合不变。已读协调e1a2159b7ca3a9572522c9b0b097f753354b69e6：dot三路分别做策略定义、来源资格、未来增量审阅，独立公式/绝对时间工具已交付；不重复其题目或校验器，不扩大本任务避让范围为排他锁。


## 2026-10-03T19:29:51.133663+08:00：自主程度已确认，首轮设计待审阅

用户确认三项困难都希望解决，并选择C“持续推进到可用成果”，原话“c吧， 整一下看看”。已复用RD-Agent/QuantaAlpha旧结论并读取协调ba70f640b55851eb24970dfe9f8fe35349c15b0a，准备首轮外部系统研究能力设计：docs/archive/handoffs-plans/external-research-capability-pilot-2026-10-03/DESIGN.md。目标是完整研究能力的可观察增量，先最多3候选选1，固定新人工任务与当前直接流程对照；安装数量不算成果。此为待审阅设计，尚未搜新来源、安装或启动比较。后续按brainstorming书面设计审阅节点确定执行计划；用户已确认自主方式，不逐步询问常规执行。旧任务/预算/数据权限不变，当前仅设计阶段，没有新后台研究。

## 2026-10-03T19:50:30.251593+08:00：首轮外部公式搜索试点已批准并冻结

用户“持续推进，没有卡点就不要停，达到目标为止”确认首轮设计；进入执行，原负责人不变。只研究外部能力，LEI自身规则由其他任务负责。

已完成：读取13任务最新分工，协调启动417e44430eca4ddf6995db65c9b1b491ec6515ce已逐字读回；两策略源SHA匹配。筛选gplearn/DEAP，选DEAP1.4.3（仅需当前NumPy）；来源4/6次包含wheel下载，111,429字节SHA4a9a940104b5b153e6bf010664882ba6994baf2c9c3f14f4ff515383e1fb16ad，LGPL3。只装.biao隔离目录，不改项目正式依赖或全局环境。

正在做：Sol medium实现独立raw/run.py和test_run.py，固定三个人工问题、三个搜索种子、强直接公式基准及随机搜索对照；主控核合同和证据。协议SHA8e4088da68500f765d0a95b277630c2109f1033dd8ab0a727f097f337d1f50ff，目录docs/experiments/raw/external-symbolic-search-pilot-2026-10-03/；执行计划见docs/archive/handoffs-plans/external-research-capability-pilot-2026-10-03/PLAN.md。

下一步：只执行冻结核心比较和必要独立核数/恢复，再按预定标准保留或拒绝。当前搜索尚未运行，结果/完整自动研究/节省人工/金融收益均未测量。避免同时改本试点两个实现文件及原输出；不独占公式研究整个领域。

预算：新来源4/6、核心0/1、后续0/3、市场拟合/回测/新付费0；旧34来源/18工程批/16真实拟合不变。已完成一次只读助手设计审查，仍由同一Sol进行范围明确实现。无后台市场进程。原包和大资料仍仅本地，本次人工数据可由固定种子重建，不需要受限行情。
