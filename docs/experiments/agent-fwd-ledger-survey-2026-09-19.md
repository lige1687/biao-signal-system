# 前向验证账本现状核查（GPT ITERATION:8 计划 a 前置调查）— 2026-09-19

## 一句话结论（大白话）

查实了两套"说过的判断事后自动算成绩"的账本确实各干各的：情绪线存的是"冰点机会/过热警报"这些板块判断，账本是一个 JSON 文件，到期对账（10天/20天后涨了多少）**没有排定时任务、只能手动跑**；超级入口的"今日推荐"存进 SQLite 数据库，每天收盘后自动补 1/5/20 天的成绩，但对账结果目前**没有任何页面展示**。另外还发现一个重要事实：代码库里其实已经铺好了一套"统一观察账本"的数据库表（就是把两套合并的设计，2026-09-17 从 Agent 采用包合入），**但至今没有任何代码往里写数据，是空转的**。所以任务书说"同一机制两套实现"是部分属实，且前提已过时——统一的地基已经打好，缺的是接线。建议最小做法：先把情绪线的对账挂上每日定时任务、再给两套成绩并排一个展示页；要不要全面迁到统一账本，留给用户裁决。

## 0. 调查性质与红线遵守

只读调查，零产品代码改动。所有结论基于本仓（`lei-agent-runtime-adoption-20260917`，分支 `codex/agent-runtime-adoption-20260917`）源码与 launchd 配置；未写任何真实库，未动他线文件。

## 1. 两套账本事实卡

### 账本 A：情绪线前向存证（`sentiment_signal_journal.json`）

| 维度 | 事实 | 源码指针 |
|---|---|---|
| 存储位置 | JSON 文件 `~/.lei_signal_lab/cache/sentiment_signal_journal.json`（`{"records":[…]}`，每条含 date/picks/alarms/review） | `scripts/sentiment_journal.py:28-29` |
| 写入方 | `record()`：读板块趋势快照的 `sig_icepoint_pick` / `sig_heat_alarm` 字段落账，按 date 幂等；触发时 macOS+飞书推送 | `scripts/sentiment_journal.py:50-108` |
| 写入触发链 | launchd `com.lei.sector.trend`（16:45）→ `precompute_sector_trend.py` 任务尾部以子进程调 `sentiment_journal.py record`（失败不阻断主快照） | `scripts/precompute_sector_trend.py:106-118`；`scripts/launchd/com.lei.sector.trend.plist`；运维口径见 `docs/ops/运维手册.md:146` |
| 读取方/对账 | `review()`：对账所有到期记录，四个分桶 `pick10/pick20/alarm10/alarm20`（冰点/警报 × 10日/20日），结果**写回 JSON 并打印 stdout 战绩**；数据源是 `sector_trend_history.json` 收盘价 | `scripts/sentiment_journal.py:111-172` |
| 对账调度 | **无定时任务**。`review` 是手动子命令（运维手册原文：「`review` 子命令可随时看 T+10/T+20 前向战绩」）；launchd 目录无任何条目调它 | `scripts/launchd/` 全目录核查；`docs/ops/运维手册.md:146` |
| 展示端 | **无**。没有任何 API 或 web 页面读这个 JSON（`web/src` 全文检索零命中） | `web/src` grep `sentiment_signal_journal` 零结果 |
| observation/live 分层 | **无**。推送文案带「research_proxy·非买卖点·前向存证中」声明，但账本记录本身无分层字段 | `scripts/sentiment_journal.py:89` |

### 账本 B：超级入口 D9 推荐质量账本（`recommendation_journal` 表）

| 维度 | 事实 | 源码指针 |
|---|---|---|
| 存储位置 | SQLite 表 `recommendation_journal`（`journal_id=rj_{run_date}` 主键、`run_date` 唯一、payload=完整推荐卡 JSON、outcome=对账结果 JSON）；另有 `recommendation_journal_history` 版本历史表 | `src/lei_signal/storage/sqlite_store.py:828-838, 942-953` |
| 写入方 ① | `save_recommendation()`：按 run_date 幂等落库（当日重跑整体覆盖） | `src/lei_signal/copilot/journal.py:20-37` |
| 写入方 ② | launchd `com.lei.copilot.daily`（16:10）→ `copilot_daily.py` 组装推荐卡后存证 | `scripts/copilot_daily.py:125-131`；`scripts/launchd/com.lei.copilot.daily.plist` |
| 写入方 ③ | Web API：`GET /copilot/recommend`（save=true 默认）与 chat dispatch recommend 分支也存证 | `src/lei_signal/api/routes/copilot.py:127-141, 230-237` |
| 对账机制 | `score_journal_outcomes()`：给 outcome 为空的日期补 T+1/5/20 收盘涨跌（百分点），幂等只补一次，行情不足跳过；由 `copilot_daily.py` **每天自动**调用 | `src/lei_signal/copilot/journal.py:133-174`；`scripts/copilot_daily.py:136` |
| 读取方 | `ops_today`（每日操作清单）只读**当日**推荐原文（`load_recommendation`）；**对账结果 outcome 无任何 API/web 消费方**（`load_outcome` 全仓仅 journal.py 自身定义，routes/web 零调用） | `src/lei_signal/api/routes/copilot.py:608-610`；全仓 grep `load_outcome` |
| observation/live 分层 | **无**。表结构与写入路径均无分层字段 | `sqlite_store.py:828-838`；`journal.py:20-37` |

### 意外发现：账本 C —— 统一观察账本 schema 已部署但零接线

SQLite 迁移 023/024/025/026 已建 `agent_observations` + `agent_observation_outcomes` + `agent_observation_batch_members` 三张表，注释明写这是「总任务书 §3.6 前向验证闭环**统一机制**」，设计上兼容吸收两套旧账本（「旧 recommendation_journal / sentiment_signal_journal.json 原样保留（兼容读），历史通过 observation.backfill_* 幂等迁入」），且具备 layer（observation/live 分层）、sample_key、按 horizon 一行一档、引用冻结等字段——**正是任务书 §3.6 五维度的目标形态**。

但全仓核查（src/、scripts/、tests/、web/）：**除 `sqlite_store.py` 的建表 DDL 外，没有任何写入方、读取方或 backfill 代码**。该 schema 随 2026-09-17 Agent 采用包合入（commit `96a6bf55`「采用已验收Agent改动（S1清单24项）」），运行主线从未接线。

指针：`src/lei_signal/storage/sqlite_store.py:850-1029`（迁移 023/024/025/026）；grep `agent_observations` 于 src/scripts/tests/web 除 sqlite_store 外零命中。

## 2. 五维度对照与结论

| 维度 | 账本 A（情绪线 JSON） | 账本 B（推荐 SQLite） | 结论 |
|---|---|---|---|
| 自动落账 | ✅ 每日 16:45 经 sector.trend 尾部自动 | ✅ 每日 16:10 跑批 + API 访问时 | 两者都有 |
| 到期检查 | ⚠️ 有逻辑（T+10/20 全到期才写）但**无调度，纯手动** | ✅ 每日自动补 T+1/5/20，幂等 | 实质差异最大的一项 |
| 滚动公开 | ❌ 仅 stdout 打印战绩，无页面 | ⚠️ 当日推荐进 /ops；**历史成绩无任何展示** | 两者都缺滚动公开 |
| 按类型分桶 | ✅ pick/alarm × 10/20 四桶 | ⚠️ 仅按标的×horizon 存涨跌，无类型分桶语义 | A 强于 B |
| observation/live 分层 | ❌ 无 | ❌ 无（统一账本 C 的 layer 字段才有） | 两者都没有 |

**结论：部分属实。** 两套账本目的同构（前向存证+到期对账），但机制差异实质存在（存储介质、到期档位、分桶口径、对账调度均不同），不是"同一机制抄了两遍"。同时任务书前提已部分过时：统一机制的**数据库地基（账本 C）已在 2026-09-17 随 Agent 采用包部署**，缺的是写入接线与历史迁移，而非从零设计。

## 3. 统一路径建议（仅建议级，不设计实现）

| 选项 | 内容 | 改动面估计 | 适用 |
|---|---|---|---|
| ① 补齐对账调度（最小） | 把 `sentiment_journal.py review` 挂到 `copilot_daily.py` 或 `copilot_weekly.py` 尾部（或独立 launchd），让 A 的 T+10/20 到期自动对账 | 1 个脚本尾部几行 + 运维手册一段 | 想先堵"手动对账可能长期不跑"的洞 |
| ② 统一展示视图 | 新增只读 API + web 一页，把 A（pick/alarm×10/20）与 B（标的×1/5/20）到期成绩并排展示 | api 层一个路由 + web 一个页面，零写入逻辑改动 | 想让"滚动公开"落地且不动存储 |
| ③ 激活统一账本 C（迁移） | 按 023-026 已有 schema 接线：A/B 写入方改写/双写 agent_observations，历史 backfill，outcome 统一进 agent_observation_outcomes | 大：journal.py、sentiment_journal.py、copilot_daily、API、tests 均需改，历史迁移需单独验收 | 用户确认要把 §3.6 五维度当长期口径时 |
| ④ 维持现状 | 不动 | 0 | 若统一账本另有部署节奏（采用包未部署到生产） |

注意：账本 C 来自 Agent 采用包且相关采用报告注明「未部署」（见 `docs/experiments/agent-runtime-adoption-final-review-2026-09-17.md`），选项③之前应先与该线确认部署计划，避免两线重复接线。

## 4. 证据与复现

完整证据指针（文件:行、launchd 配置、schema 摘录、检索命令）见
`docs/experiments/raw/agent-fwd-ledger-survey-2026-09-19/evidence.md`。

## ARCHIVE

- 结案时间：2026-09-19。性质：只读调查，零产品代码改动。
- verdict：mixed（事实核查类——任务书前提"部分属实且已部分过时"）。
- 后续决策权在用户：是否立项统一（上述①-④）。
