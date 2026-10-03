# 原策略语义与黑绿验证流程样板 Implementation Plan

> For agentic workers: 按项目既有 research-closure 和研究入口逐项执行；本轮为证据核查与执行说明，不启动新的市场实验。

**Goal:** 将用户已认可的“原策略拆解—金融语义—规范定义—多种验证—实际增量”落实到已有流程，用黑绿证据检验可复用边界。

**Architecture:** 权威文档、定义登记、冻结合同、实验账本、研究报告继续分别承担原职责。只在现有使用说明增加人工执行要求，不创造新的评分器、登记库或全局有效标志。

**Tech Stack:** Markdown、JSON、Python标准库，读取既有保存预测，不使用新数据或模型拟合。

## Global Constraints

- 用户2026-10-03认可上一轮流程设计，并明确黑绿研究不能遗漏；最终寻求真实增量，允许无增量结果。
- 原文最高来源为桌面两文档，指纹沿configs/strategy-documents.v1.json；不得修改原文、交易规则或生产。
- 统一规范沿docs/research/current-standards.json；旧合同与已封存成绩保持。
- 协调task-id technical-factor-sequence；工作分支task/technical-factor-sequence-progress；基础0e9607c2d37444ed6d4330dd4f78e14ee9021fba。
- 本轮市场拟合/新标签/行情请求/付费预算均0；复算保存结果不是新独立市场证据。
- 既有黑绿8真实及24合成拟合不重跑；旧20八轮复用。
- remote-core的black-reset/账户、dot未来SMA20、情绪宽度和外部自动搜索保持原负责人。

## Task 1：原文条件与既有证据对齐

- [x] 阅读体系§2.2、§2.7与既有黑绿报告，保留20主60辅、排列、灰态、变色、周期、失效环境。
- [x] 读取已有方法规范与文献学习目录，核新说明不与权威规范相互矛盾。
- [x] 读取最新协调记录，登记本轮范围并核远端36907af045c1654c43d856a462392737dde5beb6及任务文件blob。

## Task 2：核对数字，不重跑封存研究

Files: docs/experiments/raw/technical-factor-method-pilot-2026-10-03/verify_saved.py、verification.json。

输入：既有green-black-state-information-2026-10-03的两目标core-01/contract.json、result.json与audit-02.json。输出：准确输入SHA/字节、配对数量、误差、简单基准挑战结果。

执行：`python3 docs/experiments/raw/technical-factor-method-pilot-2026-10-03/verify_saved.py --out docs/experiments/raw/technical-factor-method-pilot-2026-10-03/verification.json --strategy-root '/Users/yongbiaoli/Desktop/lei signal doc'`。

异机移植：省略可选--strategy-root，仅复核保存预测；原文读取和行情许可分别检查，不借算术通过宣称都已具备。

验收：两目标各948行/237日期、完全配对；四种误差与旧保存成绩差<1e-10；原件指纹匹配；不写旧目录、不拟合、不新造目标。实际退出码和状态见verification.json及报告，不凭复选框认定。

## Task 3：可复用说明和完整覆盖表

Files: docs/research/research-workflow-usage.md追加“2026-10-03原策略语义与多方法验证”；docs/experiments/technical-factor-method-pilot-2026-10-03.md；原raw/coverage.json。

产出：原义映射、有限候选、方法适配、简单参照、原始/条件/模型增量区分、反假改善、封存与重开条件；黑绿完整条件逐项写已测或未测，不能把计划写成已验证。

验收：报告直接列性能和增量；保留原文中被旧代理省略的条件；新流程只声称已验证的部分。没有正向例证时不声称流程一定能发现有效因子。

## Task 4：归档与协作同步

Files: 原registry/INDEX只新增本报告；两份technical-factor-sequence进度；本raw/manifest.json。

核准确发布路径、敏感项、文件大小、旧材料未改；当前可用归置检查器只读核隔离树；独立目录只复制复算所需小文件，运行verify_saved.py并对比结果。只提交本任务精确路径；普通push工作分支；核远端完整commit，再更新自身协调记录。状态以最终报告/manifest/远端记录为准，不通过修改计划重复实验。

## 后续研究的优先选择（尚未执行，不是全部独占）

优先核原文排列背景下20黑绿状态/变化的证据缺口，复用20旧8轮逐题去重；与black-reset趋势身份和完整账户分开。若原义/共同可比样本不支持，留具体缺口，不靠换定义过关。EMA20稳定比例仍仅待去重的候选，不因提过就自动开实验。新效应合同必须在看新结果前绑定定义、已有信息、有限方法及预算；当前计划不替代其冻结。
