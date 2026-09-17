# Agent 运行采用准备 S1：只读差异与依赖审查

## 一句话结论（大白话）

把"已验收的 agent 改进"（来源：本地 main 仓库）和"正在运行的实际系统"逐个文件比对后确认：运行系统里其实已经带着这些改进的**中期版本**（9 月 15 日晚的状态），之后验收链又修了两天的稳定性和"别人/假设的话不该记成你的事"这些缺陷——这部分就是要采用的差异。真正需要搬的只有 **24 个文件**：9 个整文件替换、10 个新文件、2 个"搬新文件但要保住运行系统里当天正在写的一半成品"、3 个需要按两边各自的改动手工缝合。另有 14 个文件运行系统反而**更新**（界面样式、去除假按钮等），这些绝不能被旧版本覆盖。还有一个坑：运行目录当天正被人同时改代码（审计的半小时里脏文件从 15 个涨到 21 个），所以后续制作采用包时每个文件都要当场核对指纹，对不上就拒绝应用。本阶段只读不写：真实数据库、服务、来源仓库都没动过，也没有调用任何真实大模型。

## 0. 背景与授权

用户授权"可以啊，你可以 delegate 给 zcode 做"，承接已验收代码定向采用准备。本阶段为 S1（只读差异与依赖审查），服务目标 G1：准确区分已存在、待采用与并行冲突，并查清最小依赖。对应委派 job `1b20120c-4d07-4e3f-b726-d5b8d3a4bdb8`（stage=S1，attempt=initial）。

术语约定（首次出现先解释）：
- **三方对比**：对每个文件同时看三个版本——两边共同的起点（分叉点）、来源侧的最终版、运行侧的实际文件——以此判断"不一样"到底是"运行落后"还是"两边各走了各的路"。
- **脏改/脏文件**：已经写在运行目录里、但还没用 git 提交固定的改动。
- **采用**：把来源侧已验收的文件内容带进运行系统，同时保住运行系统自己的新东西。本阶段只做甄别，不动手。

## 1. 仓库拓扑与指纹（G1 第一条验收）

所有 `lei-agent*` 目录其实是**同一个 git 仓库的不同工作树**（主仓在 `/Users/yongbiaoli/Desktop/lei-signal-lab`）：

| 角色 | 位置 | 分支 @ 提交 | 状态 |
|---|---|---|---|
| 来源（已验收） | `~/lei-agent-main-consolidation-20260915` | `main @ f8638b9f`（完整哈希 `f8638b9fc73d…578b3`） | 干净 |
| 运行 | `~/Desktop/lei-signal-lab` | `codex/factor-unit-research-20260915 @ 29b150f5` + **21 个脏改 + 22 个未跟踪路径**（11:40 快照，仍在增长） | 活跃编辑中 |
| 本阶段工作区 | `~/lei-agent-runtime-adoption-20260917` | `codex/agent-runtime-adoption-20260917 @ d803ff71` | 干净；产品代码与运行 HEAD 提交完全一致（仅多 1 个文档提交） |

关键里程碑（均记入 raw/topology.txt）：
- 分叉点：`8ba16576`（"docs: plan local cross-agent delegation"）。
- 运行分支第一个提交是 2026-09-16 19:50 的"治理前现场快照"（`1d431137`，把当时所有在制工作一次提交），所以运行分支**自带一份 agent 工作的中间状态**。
- 该快照里的 agent 文件与 main 链条上的 `cb71cad6`（2026-09-15 11:31，"consolidate verified discussion UX"）**逐字节一致**（10 个文件核实）。main 从这个点又前进了 31 个提交——这就是全部"待采用"量的来源，**两边文件不同≠运行落后**。
- 运行侧自己独有 11 个提交：7 个目录治理 + 因子/脚本找回 + 2 个采用规划文档。main 侧独有 32 个提交（完整列表在 raw/main-side-commits.txt）。

## 2. 逐文件三方对比结果（G1 核心工作量）

对来源侧自分叉以来改动的全部 99 个产品文件（src/web/scripts/configs/tests）逐个算 sha256 并与运行实态比对，另对运行侧独有的 117 个产品文件登记指纹（全表：raw/fingerprints.tsv，采集时点 2026-09-17 11:39:34）：

| 分类 | 数量 | 含义 |
|---|---|---|
| 双方最终内容一致 | 57 | 快照已带上（含 schemas、定投、学习库、升级台账等），零动作 |
| 运行侧从未动过、main 前进 | 3 | 直接采用 main（fundamentals/sources.py、market_context/market_mood.py、test_agent_name_resolve.py） |
| 运行提交态==cb71cad6、main 领先 | 6 | 直接采用 main（agent.py、copilot 链 3 个、plans/llm.py、agentUx.ts、agent-ux 回归脚本） |
| 运行侧不存在的新文件 | 10 | 新增（ask_timing.py、context_scope.py、write_tx.py、1 个夹具、6 个测试） |
| 采用 main + 回贴运行脏改 | 2 | copilot.py、sqlite_store.py（运行脏改=基金成交幂等，与 main 改动不同区域） |
| 双方都演进、按含义缝合 | 3 | AgentConsole.tsx、AgentWorkspacePage.tsx、test_agent_chat_e2e.py |
| 运行侧领先、不采用 | 14 | 运行独有 UX/样式/测试工作（含 bpLocatable 假按钮去除、样式第二轮） |
| 仅脏改差异、保留实态 | 4 | client.ts、CopilotCards.tsx、AnswerText.tsx、agent-workspace.css |
| 运行侧独有（不属采用范围） | 117 | 因子证据/实验室等，一律不动 |

**最小采用清单 = 24 个文件**（9 整文件替换 + 10 新增 + 2 回贴脏改 + 3 缝合），逐文件理由、两边各自改了什么、依赖闭合表、排除项，全部在 raw/adoption-and-dependencies.md。

## 3. 覆盖"此前未部署的稳定性与连续讨论依赖"（G1 第二条验收）

- **提问稳定性**（断开后可同题重试不重复建问题、等待心跳去重、数据库提交失败回滚、写锁计时纠偏）：落点为 ask_timing.py（新）、write_tx.py（新）、sqlite_store.py、routes/agent.py、agentUx.ts、两个入口组件，全部在采用清单内；对应已验收结论 `docs/experiments/controller-ask-stability-closeout-2026-09-16.md`（来源侧，verdict=passed），其"下一步如采用运行版，应单独核对当前运行目录差异再定向更新"正是本阶段做的事。
- **连续讨论与用户事实**（第三人/假设不写入本人事实、概念解释不再被"回测"字样误拦）：早期 ZCode 三轮裁决（controller-zcode-continuity-final-2026-09-17，mixed）点名的缺陷已由后续修复链（e461d838 → 29f66fd8 → 925891b7 → **a098939a 统一用户事实**）解决并经验收合入 main——即**旧失败裁决对最新源码已不成立**，核心载体 context_scope.py 就在新增清单里。
- **名称与板块**：subjects.py、semantic_states.py 运行侧已与 main 一致；增量 test_agent_name_resolve.py 在采用清单。
- **前端 agentUx 与两个入口**：agentUx.ts 采用 main；工作台（AgentWorkspacePage）与控制台（AgentConsole）两个入口都属"双方演进"缝合项，main 的稳定性增量与运行侧的外部入口草稿注入、UX 第二轮增量互不覆盖。
- **提速**（消除每提问约 12 秒的情绪材料重复计算）：market_mood.py + sources.py + test_market_mood_perf.py 采用。
- 主控裁决过的遗留（连续讨论所有权缺陷在 d6abedc4 保留记录）不在代码采用范围，属后续方向，S1 不扩项。

## 4. 冲突与保留要求（对 S2 的约束）

1. **基线是运行实态文件，不是运行 HEAD 提交**。8 个文件带未提交层；其中 copilot.py 与 sqlite_store.py 的脏改（基金成交幂等：request_id 字段、031 号数据库迁移、部分唯一索引）与 main 的改动在文件内不同区域，S2 逐字保留后可合入 main 版本。
2. **运行工作区是活的**：审计开始（约 11:05）时脏改 15 个已跟踪文件；11:31–11:39 之间新增基金成交幂等五件套（copilot.py、trades.py、sqlite_store.py、client.ts、CopilotCards.tsx）与宽度描述工作（breadth 文档、两个未跟踪测试）。S2/G3 的"目标文件变化即拒绝应用"必须以指纹门禁落实（对照 raw/fingerprints.tsv 的 runtime_actual 列）。
3. **测试夹具按治理后路径**：唯一需适配的是 test_agent_continuity_routes_20260916.py 里 main 原文的 `tests/000300.SS.bars.parquet` → 运行侧实际的 `tests/fixtures/kline/000300.SS.bars.parquet`；新增夹具 `tests/fixtures/agent_semantics/` 本身符合规约。
4. **不能覆盖运行侧领先工作**：14 个运行领先文件 + 4 个仅脏改文件 + 117 个运行独有文件全部保留（含样式第二轮、bpLocatable、因子证据 runner/stability 脏改）。
5. **configs/dca_evidence.json 需主控裁决**：两侧数字一致，但 main 版注记宣称的校验脚本（scripts/dca_evidence_lint.py）在两侧都不存在，运行版注记如实记载"脚本遗失待重建"。建议保留运行版注记。
6. **策略权威文件零触碰**：trading-spec、rules.v1.yaml、MACD skill、板块方案——main 侧未改，采用包也不得改。
7. **main 侧 422 个新增文档与 2 个登记文件改动不整体搬运**；S2 按归档规约自写报告/登记。

## 5. 用户得到什么、哪些仍未投入使用

**采用完成后（S2/S3）用户将得到**（本阶段尚未发生，只是确认了可行性与清单）：问答更可靠——提交后有真实阶段反馈、失败可同题重试且不会重复记录问题、数据库被占用时不静默出错；"朋友操作了/如果以后有钱"这类话不会被错记成用户自己的持仓或资金；问"对应的 ETF"这类系统没有资料的问题会老实说清楚；名称与板块语义按主控裁决修正；每个提问省去约 12 秒的重复计算。**全部仍是解释与交互层的改善**：技术判定、买卖触发、资金纪律、模型配置均不变。

**仍然没有投入使用/未验证的**：
- 本阶段没有任何代码被采用或部署——运行系统今天的行为与审计前完全一致；
- 全程**未调用真实大模型**（来源报告中的相关验证也以无模型说明与临时库为准），真实模型回答质量不在本次证据内；
- 修复中带有一个已知既有缺口（数值校验器的"百分比派生"放行规则，来源侧已用 xfail(strict) 钉住），随采用原样带入，不为全绿扩项。

## 6. 检查命令与结果

只读命令清单（均不改任何仓库文件；`git merge-file` 试合并仅在 /tmp 生成结果用于冲突定位）：
- `git -C <worktree> log/status/worktree list/merge-base/rev-list`——拓扑与漂移监测；
- `git show <rev>:<file> | shasum -a 256` ×三方 + `shasum -a 256 <运行实际文件>`——216 个文件的指纹表（raw/fingerprints.tsv）；
- `git merge-file -p <main> <祖先> <运行实态>`——5 个缝合项的机械试合并（raw/merge-trial-parallel.txt；文本冲突是算法噪音，缝合以逐文件 delta 描述为准）；
- `git grep`/`diff`——引用闭合、夹具存在性、反向依赖、策略文件零触碰核查。

结果：分类表见 §2；全部 raw 文件（fingerprints.tsv、adoption-and-dependencies.md、topology.txt、runtime-dirty.txt、merge-trial-parallel.txt、main-side-commits.txt、runtime-side-commits.txt）在 `docs/experiments/raw/agent-runtime-adoption-audit-2026-09-17/`。

## 7. 限制

- 运行实态是移动靶：指纹表只代表 11:39:34 那一刻，S2 构建时必须重验；
- 归置检查（check_repo_hygiene）在本阶段工作区执行并在结案说明中报告，但运行工作区的治理状态不由本阶段负责；
- 未跑任何测试、未 build 前端——S1 为纯静态审查，运行行为验证属 S2；
- 审计期间运行目录正被并行写入（基金成交幂等 + 宽度描述），两项在制工作均未纳入或评价其完成度，仅作为"必须保留的并行改动"登记。

## ARCHIVE

分类：数据与质量。本报告是 S1 只读审查的阶段交付：完成来源 main@f8638b9f 与运行实态（29b150f5+脏改）的逐文件三方核对，产出 24 个文件的最小采用清单、依赖闭合表与明确排除项；真实库/服务/来源仓库零改动，未测真实模型。完成不等于整体采用任务验收；S2（隔离副本整合）与 S3（采用包）待主控推进。
