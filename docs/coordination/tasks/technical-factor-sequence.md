# LEI 技术因子顺序与组合研究

- task-id：technical-factor-sequence；负责人：本技术因子研究会话 /root，设备 MacBook-Air-126.local。持续负责，不是接管或结束。
- 状态：active（语义与资料资格准备）；C01/Q01 completed；新效果实验未启动。
- 更新时间：2026-10-03T14:02:21.051775+08:00，Asia/Shanghai。
- 目标：把 LEI 技术原文的经验判断转为明确可计算信号，检验它在已有信息之后是否仍提供可重复的收益或风险信息。国内宽基/ETF优先。交易和线上业务增量未测量，预测误差改善不能当成交易收益。
- 验收：原文来源、定义、时点、简单基准、增量比较、收益/风险/机会与后期证据可核；负结果也结案。遵循当前研究规范索引，不改旧冻结合同。
- 规范：远端 COORDINATION.md 1.0，实际读取提交0b758e7e10f720c44cbd898d511ff392f2857535；工作分支AGENTS.md、docs/research/current-standards.json（本地索引research-standards/1.0，workflow/1.1）；新研究采用最新索引，封存研究保留原绑定。情绪、宽度、宏观、Module E、账户政策和生产交易不归本任务；改变原文、研究范围或技术规则须用户确认。

## 版本与唯一入口映射

仓库 https://github.com/lige1687/biao-signal-system 。工作分支 task/technical-factor-sequence-progress；已推送成果完整commit d444316817e9330c2d72a4a90c655467b45dd5bb；发布基础d7da6cb0f9c127606b6faa572fabc9ee93f104f7。

成果入口：https://github.com/lige1687/biao-signal-system/blob/d444316817e9330c2d72a4a90c655467b45dd5bb/docs/progress/technical-factor-sequence.md 。精确上传范围和测试见同commit的technical-factor-sequence-files.json、technical-factor-sequence-validation.json。原共享工作区HEAD18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，分支codex/factor-unit-research-20260915，有大量其他任务修改；不代表成果分支，不整批提交。

跨任务当前状态只有本文件；阶段历史仍为docs/ops/work-progress/technical-factor-sequence.md，旧阶段不当作实时锁或接管许可。本文件自身commit从Git历史定位，不无限补写自指SHA。

## 已完成、证据和封存结论

- C01：昨日简单顶部仍有效×当日双跌破的未来20日下探比较；4ETF、874条后期预测。原有信息误差3.701662→加入组合3.703634个百分点，略差。本实验范围未发现实际增量，不代表整套退出规则无效。代码src/lei_signal/research/prior_top_dual_break_information.py；报告docs/experiments/prior-top-dual-break-information-2026-10-02.md。
- Q01：EMA20方向向上而SMA20未向上时，当日已知连续等待日龄；4ETF、89条后期未来20日收益预测。原有信息误差8.261842→加入日龄8.287496个百分点，略差；未发现实际增量。代码src/lei_signal/research/ema_only_wait_age_information.py；报告docs/experiments/ema-only-wait-age-information-2026-10-02.md。
- 封存状态、controller/final-review.md、numeric-audit/receipt.json：docs/experiments/raw/technical-combination-semantics-2026-10-02/及ema-sma-sequence-information-2026-10-02/。小回执已推，完整输入/路径没有随Git交付。
- 下一问题原文与旧定义去重已完成：docs/research/proposals/technical-sequence-next-2026-10-03/README.md。SMA方向与抵扣价的公式关系不是未来收益证据；候选只剩已知抵扣路径形状，不重复盒顶距离、当前日龄或60日斜率变化。

## 正在做、下一步及文件范围

正在接入统一协作，核对该单一候选的输入字段、当时可知范围、缺价与资料资格；无新标签/模型/适配器。限定修改本任务进度、上述候选目录及本分支AGENTS.md的协作说明；共享区AGENTS.md不整文件提交。

下一步：只读无标签输入检查；有明确新用途、足够输入并解决潜在重叠后，才按当前规范冻结一个问题和预算。若仅为旧数学关系重复则关闭候选，不换参数寻正结果。用途、模型、目标和效果合同尚未确定，不把全部技术方向圈为本任务。

## 重叠核对与其他AI避让

实际读远端任务目录：当时仅lei-coordination-bootstrap，completed/初始化；它不认领本研究。未发现已登记同题冲突，但未登记任务状态未知，不宣称全局无冲突。

本地非实时线索：technical-factor-mainline维护137起点等待路径及2B定义；classic-factor-research维护经典波动风险；sentiment-factor-research维护情绪与宽度。保留原负责人，未替他们登记。共享workflow.py/workflow_inputs.py/question_contract.py由多任务依赖，需要明确实现者和验证者再改，本轮不改。

其他AI避免重做C01/Q01的同用途实验，避免同时改对应两适配器/测试/报告和本候选目录；记录不是排他锁。抵扣路径形状若被别人认领，暂停重叠部分并在记录协调，独立资料检查可继续。未登记邻居实时状态未确认；新效果/共享工具修改暂不执行。

## 检查、运行中实验与累计预算

- 前一同步阶段：隔离封存源码最小合成测试10项通过、exit0，差异检查通过；没有市场实验重跑。证据为工作分支validation.json；不当成新因子有效。
- 本轮：remote目标一致，规则及现有任务读回；两分支树无.github/workflows，未配置core.hooksPath。外部仓库级自动化未确认；本轮只普通Git文档推送，不执行上线/发布/付费计算。
- 进程只读核对：本机未发现匹配C01/Q01或run_factor_lab的进程；不杀其他任务，不推断远端没有任务。无本任务可接续checkpoint进程、无新输出锁需迁移。
- 累计C01：4次真实拟合，1核心+2后续批次，0市场网络请求；Q01：4次真实拟合，1核心批次，0市场网络请求。新候选目前0次效果/拟合/标签、0市场请求。不重置旧账。
- 未运行：大回测、Linux/云端真实workflow、生产、真实交易；文档同步不需要重跑已封存测试。首次推送核验完成后才称已同步。

## 输入、仅本地材料与阻塞

权威原文只读：Desktop/lei signal doc/LEI 技术交易体系.md SHA256 df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20；LEI 技术实现.md SHA256 85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903。

共同panel：docs/experiments/raw/volume-information-2026-09-30/execution/panel.json，1,582,974字节，SHA256 382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b；来源manifest SHA256 a0c3b15bc56ac34c4538ac9b11e505a83c0f8bed97175459d7eccb74c2b11c94。

完整数据证据包：docs/ops/recovery/technical-factor-sequence-20261003/data-evidence.tar.gz，31,526,692字节，233文件，SHA256 d7ac78098b11ca484fc9f6072f0e3a2f593e08aef0c58d772d14d4987ec06936；仅本地，远端不可复现。完整handoff原件/私人附件/来源PDF/数据库/大日志不进此公开仓库；不上传凭证。权重不适用。

阻塞：新效果前要定用途与非重复输入并核实时负责人；供应商历史到达/行动资料完整性、数据再分发许可未独立证实。远端运行原效果缺输入，不能把缺资料写成已恢复。无本次同步权限阻塞，旧定义/数据缺口没有因此解除。

## 不要重复与最小恢复

A01/A02/A03、D01抵扣盒、双均线静态排列、60日斜率变化、简单顶部失效、回调层级及C01/Q01沿用封存用途和预算，详见docs/research/technical-semantic-evidence-map-2026-10-02.md。无新证据/定义纠错/明确新用途，不改名或调参重跑。邻居137起点事后等待长度与Q01当前可知日龄不同，禁止重复其已结案价格描述。

下轮先fetch coordination/lei并读本文件和相关新增任务，核对工作分支准确commit与输入SHA，然后只做剩余资格步骤。权限不从旧交接包自动继承。本版新增：接入统一规则、旧入口映射、真实研究预算、窄范围避让和未知任务边界；推后核验回执在本地运维目录，不替其他任务改状态。

## 本阶段更新：协作接入后继续原任务

更新时间：2026-10-03T14:06:34.521708+08:00，Asia/Shanghai。最新读取协调commit 067b29d17c0488d04edeba8d056dbed424433cd0；COORDINATION.md规则SHA256 6871aa85da956453ca8e4d077e9bd9d9bf229df42c8447ffb94f97ba7f2461e0。实际追加读取market-observation：只处理CPI说明和观察卡叙事，不涉及本候选、两适配器或workflow；与本任务没有已登记的模块/实验冲突。其他未登记任务实时状态仍未知。其他任务文件均完整保留。

已核对工作分支远端最新完整SHA d444316817e9330c2d72a4a90c655467b45dd5bb；AGENTS只追加协作入口，原有工作分支字节前缀保留，进展文件增加唯一入口映射。没有将共享区脏AGENTS或其他代码带入。AGENTS变更提交f3bd94915c9bed45bf56f2d70b273c686ef8cae8；后续只增加输入核查文档，不改代码。

原任务独立部分已继续：输入指纹未变，4ETF各1337行、2020-12-21至2026-06-30，无重复日期或异常close，历史窗口1318/对象。具体聚合回执在工作成果commit的docs/research/proposals/technical-sequence-next-2026-10-03/input-qualification.md；这不是机会数或效果验证。0新标签/拟合/市场请求；行动/到达时间等资格限制保留。

当前已完成协作登记和基础输入完整性核查；下一步待办是固定候选的独立用途与表达，先读最新协调记录、核相关实时分工后再冻结；没有新效果进程正在运行，不把待办写成后台执行。新效果/共享工具修改在资格与分工明确前不启动。未遇已登记冲突，不借记录当锁。

本轮实测：文档diff检查通过；本机共享工作区现有版本check_repo_hygiene.py退出0（只证明该工作区检查，不代表独立发布树或云端已测试）。本轮无交易代码变更，不重跑封存10项或大实验。独立索引和单文件协调提交不动原工作区、原暂存区和其他进程。输入完整性阶段已更新工作分支，同一任务状态继续active，原效果成果C01/Q01仍completed，旧预算不变。初次任务登记已推并fetch逐字读回；本次阶段状态同步提交须再核远端包含及内容。
