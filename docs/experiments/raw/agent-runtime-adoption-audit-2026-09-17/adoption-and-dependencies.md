# 最小采用清单与依赖表（S1 只读审查结论）

- 采集时点：2026-09-17 11:39:34 +0800（fingerprints.tsv 同批生成）。
- 三方基准：共同祖先 `8ba16576`、来源 `main@f8638b9f`、运行实际文件（`codex/factor-unit-research-20260915@29b150f5` + 未提交脏改，下称"运行实态"）。
- 里程碑说明：运行侧提交内容里的 agent 工作与 main 链条上的 `cb71cad6`（2026-09-15 11:31，"consolidate verified discussion UX"）逐字节一致（10 个文件核实）；main 在其之上又前进了 31 个提交（稳定性收口 → 连续讨论 → 用户事实统一 a098939a）。
- 所有哈希为 sha256，详见同目录 `fingerprints.tsv`；逐提交清单见 `main-side-commits.txt`、`runtime-side-commits.txt`。

## A. 采用动作清单（共 24 个文件）

### A1 整文件采用 main 版本（9 个 = 6 个"提交态==cb71cad6" + 3 个"运行从未改过"；运行侧在这些文件里没有任何独有内容）

| 文件 | 依据 |
|---|---|
| `src/lei_signal/api/routes/agent.py` | 运行提交态==cb71cad6，main 领先（稳定性/连续性/用户事实） |
| `src/lei_signal/copilot/chat_identity.py` | 同上 |
| `src/lei_signal/copilot/resolve.py` | 同上（import context_scope，见依赖表） |
| `src/lei_signal/plans/llm.py` | 同上 |
| `web/src/utils/agentUx.ts` | 同上 |
| `web/run-agent-ux-regression.mjs` | 同上 |
| `src/lei_signal/fundamentals/sources.py` | 运行侧自分叉未动，main 前进 |
| `src/lei_signal/market_context/market_mood.py` | 同上（每提问约 12 秒情绪材料重复计算的消除） |
| `tests/unit/test_agent_name_resolve.py` | 同上（名称/板块语义按主控裁决修正） |

（9 = 前 6 个为"提交态==cb71cad6"组，后 3 个为"运行从未改过"组。）

### A2 新增文件（10 个，运行侧不存在，直接从 main 引入）

| 文件 | 作用 |
|---|---|
| `src/lei_signal/api/ask_timing.py` | 提问分段计时/等待反馈（提问稳定性核心新模块） |
| `src/lei_signal/copilot/context_scope.py` | 第三人/假设/疑问不写入本人事实的范围判定 |
| `src/lei_signal/storage/write_tx.py` | 写事务进程内登记与锁等待诊断 |
| `tests/fixtures/agent_semantics/atr_intents.json` | ATR 意图夹具（`tests/fixtures/<类别>/` 符合治理规约，路径无需改） |
| `tests/unit/test_agent_ask_stability.py` | 提问稳定性回归 |
| `tests/unit/test_agent_context_contract.py` | 本人事实与讨论意图契约回归（引用上夹具） |
| `tests/unit/test_agent_continuity_20260916.py` | 连续讨论回归 |
| `tests/unit/test_agent_continuity_routes_20260916.py` | 连续讨论路由回归（**夹具路径需适配**，见依赖表） |
| `tests/unit/test_market_mood_perf.py` | 情绪材料计算提速回归 |
| `tests/unit/test_write_tx_tracking.py` | 写事务跟踪回归 |

### A3 采用 main + 逐字回贴运行侧未提交层（2 个）

| 文件 | main 侧新增 | 运行侧未提交层（必须保留） |
|---|---|---|
| `src/lei_signal/api/routes/copilot.py` | 连续讨论/用户事实相关演进 | 基金成交幂等：`TradeCreateRequest.request_id` 字段 + trades_create 幂等语义（同 ID 同载荷返回原成交、异载荷 409）。与 main 改动在文件内不同区域，可合并 |
| `src/lei_signal/storage/sqlite_store.py` | write_tx 登记与锁等待诊断 | 新增 `031_fund_trade_request_identity` 迁移（fund_trades 加 request_id/request_payload 两列 + 部分唯一索引 + executescript 中断重跑保护）。与 main 改动不同区域，可合并 |

注意：这两个文件的运行侧未提交层属于**正在进行的另一项工作**（基金成交重复记账修复，配套 `src/lei_signal/copilot/trades.py` 脏改与未跟踪的 `tests/unit/test_copilot_trades_dedup.py`），S1 审计期间（11:31→11:35）才出现在运行工作区。S2 构建基线时必须以届时运行实态重新核验。

### A4 双方演进、按含义合并（3 个）

| 文件 | main 侧增量（cb71cad6 → f8638b9f） | 运行侧独有（必须保留） |
|---|---|---|
| `web/src/components/AgentConsole.tsx` | 提问稳定性：`failedRetryable`（answer_state=failed 同 cid 重试）、等待心跳去重（waiting 键连续只留最新）、默认等待文案"已提交，等待系统确认…" | 外部入口问题草稿注入（`useAgentConsole` 的 storeDraft/draftSeq：草稿只进输入框、空格追加不覆盖、不自动发送）；买点 chip 渲染普通文字（不留假按钮） |
| `web/src/pages/AgentWorkspacePage.tsx` | 提问稳定性（同上）+ ChartResource 的 `subjectLabel`/`displayName`（名称与板块，运行侧同款改动收敛） | UX 第二轮：quick card 头部"看图 ↗"按钮、价位区"系统价位与条件"标签、`AnswerText` middle 插槽（结论→价位→正文→依据卡）、资料区关闭时清定位、买点编号降级为普通文字的注释与实现；**外加 21 行未提交脏改** |
| `tests/integration/test_agent_chat_e2e.py` | 数值校验器缺口改为 `xfail(strict=True)` 用例 + 断言锚点改为"AI 讲解暂时不可用" | 夹具路径治理适配：`tests/000300.SS.bars.parquet` → `tests/fixtures/kline/000300.SS.bars.parquet`（保留运行侧路径） |

## B. 明确排除项（不采用、保留运行实态）

1. **14 个运行侧领先文件**（main 自 cb71cad6 后未再动，运行侧有独有演进）：`web/src/App.tsx`、`web/src/components/AgentMarkdown.tsx`（bpLocatable 假按钮去除）、`web/src/components/ChartControls.tsx`、`web/src/components/agent/priceLinks.ts`、`web/package.json`、`web/run-agent-price-regression.mjs`、`web/src/pages/DetailPage.tsx`、`web/src/pages/WorkspacePage.tsx`、`web/src/workspace-design.css`、`web/src/styles.css`（含 31 行脏改）、`tests/unit/test_discussion_backtest_03b.py`、`tests/unit/test_discussion_contract_r2.py`、`tests/unit/test_plan_confirm_guard.py`、`configs/dca_evidence.json`（特殊，见下）。
2. **`configs/dca_evidence.json` 需主控/S2 裁决**：两侧数字完全一致（仅 JSON 排版不同），唯一分歧是注记——main 版宣称"一致性由 scripts/dca_evidence_lint.py 强制校验"，但该脚本在 main 与运行两侧都不存在；运行版注记如实记载"脚本已遗失待重建，登记时人工核对"。直接采用 main 注记会引入不实声明。建议保留运行版注记（或先重建 lint 脚本再改注记），由主控拍板。
3. **4 个仅脏改差异文件**（main==cb71cad6==运行提交态，保留运行实态即可，无采用动作）：`web/src/api/client.ts`、`web/src/components/copilot/CopilotCards.tsx`（均为基金成交幂等工作的一部分）、`web/src/components/agent/AnswerText.tsx`（17 行脏改）、`web/src/pages/agent-workspace.css`（12 行脏改）。
4. **57 个双方最终内容一致文件**：无需动作（快照已带上，含 schemas、plans store/sessions/conformance、copilot subjects/semantic_states/backtest_requests、dca、learning、upgrades、web 多页）。
5. **117 个运行侧独有产品文件**：因子证据/因子实验室等运行侧工作，与本次采用无关，一律不动。
6. **docs 层面**：main 侧 422 个新增文档（报告/raw/交接）与 2 个修改（`docs/experiments/INDEX.md`、`registry.json`）**不整体搬运**；S2 按 AGENTS 归档规约自写报告并登记。运行侧 docs 脏改（INDEX/registry/factor 报告）与全部未跟踪文件保留。
7. **策略权威文件**：`docs/trading-spec-v1.md`、`configs/rules.v1.yaml`、`.claude/skills/macd-reading/SKILL.md`、`docs/plan-sector-trend-page.md`——main 侧自共同祖先以来未触碰（已核实），采用包亦不得触碰。

## C. 依赖表（采用闭合性）

| 采用项 | 依赖 | 状态 |
|---|---|---|
| `routes/agent.py`（main 版） | `api/ask_timing.py` | A2 新增，闭合 |
| `copilot/resolve.py`（main 版） | `copilot/context_scope.py` | A2 新增，闭合 |
| `storage/sqlite_store.py`（main 版） | `storage/write_tx.py` | A2 新增，闭合 |
| `test_agent_ask_stability.py` | ask_timing、routes/agent、plans/llm、sqlite_store、write_tx | 全在采用集 |
| `test_agent_context_contract.py` | `routes/agent._user_background` + `tests/fixtures/agent_semantics/atr_intents.json` | A2 新增，闭合；夹具路径即治理规约路径 |
| `test_agent_continuity_routes_20260916.py` | plans/llm、routes/agent、AnalysisService、compose/pipeline、`tests/fixtures/kline/000300.SS.bars.parquet` | 模块闭合；**main 原文写的是治理前老路径 `tests/000300.SS.bars.parquet`，S2 引入时必须改为 `tests/fixtures/kline/` 下路径（运行侧已存在该夹具）** |
| `test_market_mood_perf.py` | `market_context/market_mood.py`、`fundamentals/sources.py` | 均在采用集 |
| `test_write_tx_tracking.py` | write_tx、sqlite_store | 闭合 |
| 共享底座（schemas、plans store/sessions/conformance、copilot subjects/semantic_states/backtest_requests、plans/llm_context） | — | 运行侧已与 main 一致或两侧均未变，闭合 |
| 前端采用集（agentUx.ts、run-agent-ux-regression.mjs） | AnswerText/priceLinks/client 等 | 均为运行实态已有（保留项），闭合 |

反向依赖关注（采用后必须回归的运行独有文件）：`tests/integration/test_plans_supervisor_e2e.py`、`tests/unit/test_intraday_check.py`、`tests/unit/test_plans_actions.py`（均 import `storage.sqlite_store.connect`——稳定入口，理论兼容，实跑确认）。运行侧独有前端文件均不 import 将被覆盖的 `agentUx/AnswerText/priceLinks`（已 grep 核实）。

## D. 对 S2 的硬性要求（S1 结论导出）

1. **基线 = 运行实态文件，不是运行 HEAD 提交**：8 个文件带未提交层（copilot.py、sqlite_store.py、trades.py、client.ts、CopilotCards.tsx、AnswerText.tsx、AgentWorkspacePage.tsx、agent-workspace.css、styles.css 中属于本清单的部分）。构建候选前重新逐文件核 sha256（对照 `fingerprints.tsv` 的 runtime_actual 列）。
2. **运行工作区是活的**：S1 审计期间（约 11:05→11:39）脏改从 15 个已跟踪文件涨到 21 个（新增基金成交幂等五件套 + trades.py）。任一目标文件在应用时与指纹不符即拒绝（对应 G3）。
3. **不改回旧目录**：夹具路径按治理后位置（`tests/fixtures/...`），唯一需适配的是 `test_agent_continuity_routes_20260916.py` 的 parquet 路径。
4. **不能为全绿扩项**：main 侧已知既有失败（数值校验器缺口，e2e 已 xfail 标注）随采用带入，按原样保留并如实报告。
