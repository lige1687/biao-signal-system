# 外部增量任务统一协作记录

- task-id：external-quant-resources；任务名：量化资源适配与效果验证。负责人：本聊天“外部增量”，会话01a0cd21-07e5-7163-8f4e-72a4d5ebc32e，设备MacBook-Air-126.local；继续负责，不是接管或结束。
- 状态：active（工具维护/有界来源资格核查）；固定tsfresh、arch和catch22来源阶段completed；共享研究主线整合paused；FactorHub真实调用blocked。
- 更新时间：2026-10-03T14:08:27.808600+08:00，Asia/Shanghai（UTC+08:00）。
- 验收：公开原始来源与许可可定位、限定工具有测试证据；金融用途同对象/日期/条件核简单基准、原有信息增量及反例。负结果可结案，不换参数求正结果。线上收益和效率节省未测量。
- 规范：COORDINATION.md 1.0，实际读取b172008890b39e912c8f1d0cfb9125d1e414a97f，最新基线3fab17d5bd7225eb447bb2358aa9ca1ec1f97e13规则字节未变；工作分支AGENTS.md、docs/research/current-standards.json、准确定义登记；旧冻结合同不迁移。
- 工作分支：task/external-quant-progress（用户明确task/命名）；初始基础1ac596f65110e06c286f04707165251328df0962，本轮基础6d8ad5c80c055337e2bb33c536ec3cbf1f50fd5e；最近已推成果完整commit：59826afc936835e7ef38d3f1d832812b03abdc68，已核远端SHA并fetch逐文件读回AGENTS及两份自身进度。
- 成果入口：https://github.com/lige1687/biao-signal-system/blob/59826afc936835e7ef38d3f1d832812b03abdc68/docs/progress/external-quant-resources.md 。阶段历史仍为docs/ops/work-progress/external-quant-resources.md并已链接本入口；唯一跨任务当前摘要为本记录，旧交接文本不代表当前移交。

## 本轮实际范围、冲突、运行与验证

已读取最新远端lei-coordination-bootstrap、technical-factor-sequence和market-observation。前者已完成初始化；后两者负责抵扣路径资料资格和CPI/观察卡说明，本任务不碰这些问题/文件。没有已登记同题冲突；未登记的技术主线/经典Qlib等实时状态未知，不当作空闲。共享workflow.py、workflow_inputs.py、workflow_evaluation.py、question_contract.py、top_structure_information.py、trend_slope_change_information.py的实现者/独立验证者尚未在本记录明确，本任务是使用者，整合写入暂停；独立工具/公开来源核查可继续。记录不是排他锁，新重叠先暂停冲突块并在记录协调，不替别人改状态。

正在做：统一接入及既有工具维护。同步后继续原任务的只读依赖发布状态核对：docs/progress/external-quant-shared-dependencies-2026-10-03.json列出的17个导入绑定能否对应准确远端版本；核对后才决定最小整合是否具备条件。不新增模型/标签、不认领共同主线，亦不圈所有外部方法。

本轮通过：remote一致、规则和三条任务读取、独立索引准确3路径、差异检查、工作分支推后完整SHA匹配与三文件读回、原共享HEAD和索引不变；两基线无.github/workflows、未配置core.hooksPath、本地无pre-push。外部仓库级集成未独立确认；仅普通文档推送，不执行上线或付费动作。协调记录远端核验待本提交推后执行，不能预写通过。

本轮曾因共享FETCH_HEAD被其他fetch改写，版本断言停止，未生成提交、首次推送无ref失败；已改为专属远端跟踪引用和固定已读commit，保留对方新增记录，不盲重试、不强推。

运行：agent清单仅root，无本任务子agent或由本负责人启动的研究计算；旧实验已到完整结案点，没有待迁checkpoint。进程清单存在其他Python/UI程序，归属未确认，不终止、不宣告结束；远端未登记任务运行状态未知。最后检查时间同更新时间。本轮0拟合/0市场资料请求/0付费任务。没有重跑旧研究，Linux/Windows/云端/生产/真实收益未验证。

较上一版：首次唯一ID映射，引用准确成果，写明未登记未知和共享写入暂停，保留负结果/预算/仅本地资料。代码继续工作分支；协调只写本文件，不改规则/他人记录。文件自身提交由git log -- 本路径定位。

## 最小接续

下轮先fetch origin coordination/lei并读取规则、本记录及相关新增任务；核对工作分支59826afc936835e7ef38d3f1d832812b03abdc68与输入SHA，核新版是否已修旧问题，做最低复现后仅推进许可具备的未完成项。共享依赖写入等负责人明确；FactorHub等用户安全配置；材料使用/存储资格未确认时不上传。权限不因旧包或complete自动继承。

## 目标、成果、精确证据、材料与封存预算

以下摘自本任务已核工作分支进度，保留报告准确路径/指纹；当前协调范围以上文为准，不把旧“阶段记录”当实时锁。

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


补充依赖指纹：panel来源manifest SHA256 a0c3b15bc56ac34c4538ac9b11e505a83c0f8bed97175459d7eccb74c2b11c94；固定输入panel为1,582,974字节。无单独神经权重/tokenizer/数据库交付需求；旧模型系数随补充结果包，仅本地、远端不可复现。原供应商材料70,348,971字节指纹见旧包evidence/source-qualification-inputs.json。磁盘约446MiB，完整worktree曾空间不足，本轮采用单独目录和独立索引，不删除资料。


推前并发更新：普通推送被拒，随后读取9c994de31b2c325ee49080df50009e3369a52f55新增investor-observation-map和lei-technical-reader-research。前者只维护观察地图，后者等待描述/阅读页且下一研究blocked；均未认领本任务技能/比较工具，不存在已登记同题冲突。技术阅读页明确共享四个工作流偏离冻结值且含他人改动，整文件未上传；因此本任务继续暂停共享整合，不能把旧快照当最新发布。保留所有新增记录；本任务只重建自己的单文件增量。

追加核对9780820345511d37acfad09fd367b39305d3532c新增classic-factor-research和remote-core-review：经典专属风险分支及转黑单问题资格，与本任务四技能/固定tsfresh/共同比较不同；均不执行共享工作流改写。保留它们的记录，共享整合继续暂停。第二次普通推送并发拒绝已保留，本次只整合自身记录。


同步后实际继续（2026-10-03，Asia/Shanghai）：首次协调成果2ebefda220f9a34d218c0a725e5e65e09d1d2465已在远端210cc70b96e0db6ca119158971027a6119cd1b55内，任务文件SHA256读回一致，原共享HEAD/index不变。已读technical-factor-sequence新分工澄清，2B不由其执行。随后只读其工作分支d444316817e9330c2d72a4a90c655467b45dd5bb的5个所需模块：top_structure_information.py、trend_slope_change_information.py与既有依赖清单指纹一致；workflow.py、workflow_evaluation.py、workflow_inputs.py已存在但指纹分别为1f2554509c3719d0274d425d6e8179c357a45054dcfb4775d57ac5f1b8564bdb、65188447542c8c84b7a749c6e033c558034ecf3133fc45fca1757c0ceab27cab、0ff1fe0a3de19680cc9c8800fb62267993cc9f55dab36fbe28a2dd7153ca4691，与冻结依赖不同。模块缺失已部分解除，不能直接认为接口等价或具备整体运行条件；下一步只读差异/接口资格核对，整合写入继续暂停，0新拟合/市场请求。完整此次只读JSON回执仅本地.biao/external-quant-coordination-20261003/dependency-recheck.json，必要指纹已在本记录交付。
