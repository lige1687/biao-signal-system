# 前向对账补齐：①调度接线 + ②统一展示视图 — 2026-09-19

> 状态：S1 + S2 均已完成（候选提交在分支上，待用户验收）。

## 一句话结论（大白话）

系统里有两本"说过的判断事后自动算成绩"的账本：一本记**情绪信号**（散户冰点机会/强势散户热警报的板块判断，10 天、20 天后回头看涨跌），一本记**每日推荐**（当天推的标的，1 天、5 天、20 天后回头看涨跌）。以前的问题是：第一本的事后算成绩**只能手动想起来才跑**，两本的成绩**都没有任何页面可看**。本次两步补齐：①把情绪账本的对账挂进每天下午 4:45 的既有定时任务尾部，**从手动变自动**（重复跑不写重复数据，账本文件坏了也只是跳过并留警告，不影响主流程）；②新增一个只读的"前向成绩"网页（导航「策略研究」组里进入），把情绪四桶成绩和推荐标的到期涨跌**并排展示**——数据没到期或还没有时就明说"暂无可看成绩"和原因，不编数。注意口径：这只是把对账自动化和成绩展示补上了，**不等于"前向验证闭环完成"**——统一账本迁移（选项③）等后续仍需用户单独裁决。

## 0. 阶段与边界

- 本文档含 **S1（情绪对账调度接线）与 S2（两套成绩并排展示）** 两章。
- 红线遵守：S1 沿用账本既有 JSON 格式（零新格式），`sentiment_journal.py` 本次**零改动**；S2 只读（唯一 SQL 是 SELECT，唯一端点是 GET），不写任何账本；全程未写 `agent_observations`、未碰判定层、未接真模型、未碰他线文件；验证全程用临时副本（`LEI_CACHE_ROOT` 重定向到 `/tmp`、临时 SQLite），真实 cache 字节级未动（sha256 前后一致，见 raw 日志）。

## 1. S1：挂点选择与理由

**选择：a) `precompute_sector_trend.py` 尾部（record 调用之后）**，不选 b) `copilot_daily.py`，理由：

1. **数据新鲜度**：对账的数据源就是 `sector_trend_history.json`（板块收盘历史），16:45 的板块趋势任务刚把它重写为当日最新。挂在它尾部，当天恰好满 10/20 天的记录**当天就能对上**；若挂 copilot_daily（16:10），读到的还是昨天的历史文件，所有到期记录一律要多等一天才对账。
2. **同链同账本、零新增配置**：写账本（record）本来就在 16:45 链尾部，对账（review）操作的是同一本账本，放同处让情绪账本"写+对账"的完整生命周期在一个定时链内闭环，**不需要新增任何 launchd 配置**。
3. **不跨线**：copilot_daily 属于推荐/SQLite 域，尾部已有自己的对账步骤（`score_journal_outcomes`），再塞一个异构 JSON 对账容易混淆日志归属。

实现完全对齐 record 先例：子进程调用 + `try/except` 包裹 + 失败只打警告不抛出（失败不阻断主流程）；幂等性由 `review()` 既有逻辑保证（已对账记录带 `done` 标记自动跳过，无变化不重写文件）。另比 record 先例多判一个退出码：失败时以 `⚠` 前缀打日志，避免崩溃堆栈被误打成 `✓` 成功样式的输出。

## 2. 改动清单

| 文件 | 改动 |
|---|---|
| `scripts/precompute_sector_trend.py` | 任务尾部新增 review 子进程调用块（record 块之后、耗时统计之前），约 20 行；其余零改动 |
| `docs/ops/运维手册.md` | §9.1 任务链：16:45 尾部串联步骤由三步改四步，④=到期对账每日自动跑（写回同一账本、幂等），并注明仍可随时手动跑 |
| `docs/experiments/agent-fwd-wire-2026-09-19.md` | 本报告 |
| `docs/experiments/raw/agent-fwd-wire-2026-09-19/s1-scheduling-verification.log` | S1 全部验证输出 |

## 3. 验证证据（详见 raw 日志，全部 ALL PASS）

验证方式：把真实 `sector_trend_history.json` 复制进临时目录，手工造一条 2025-09-18 的账本记录（带一冰点一强热两个板块信号，T+10/T+20 均已到期），用环境变量 `LEI_CACHE_ROOT` 把账本读写重定向到临时目录后跑 `review`。

1. **功能正确**：四个分桶（冰点/强热 × 10 日/20 日）的收益写回值与"直接从历史文件独立手算"的预期值逐项相等（如冰点 10 日 +15.16%、强热 20 日 +6.04%），`done` 标记正确置位。
2. **幂等复跑**：第二次跑 review 后账本文件 sha256 字节级不变，记录数仍为 1，无重复写回。
3. **损坏注入不阻断**：把历史文件换成损坏 JSON——直接跑 review 确实崩溃（退出码 1，证明失败是真实的）；然后从 `precompute_sector_trend.py` **真实源码**里用语法树抽取新加的挂载块执行：异常被吞、打出 `⚠ 情绪存证对账异常（不影响主快照）` 警告，其后的主流程语句正常继续执行。
4. **降级与安全**：损坏的账本 JSON 走既有容错路径（按空账本处理，退出码 0 不崩）；测试前后真实 cache 两个文件 sha256 一致；`py_compile` 与 `--help` 通过。

## 4. 限制与未尽事项

- **S2 未做**：两套成绩的只读并排展示（API + web 页面）是下一阶段；本阶段无任何 API/前端改动。
- **失败当日的自愈方式**：若某天 16:45 主任务本身失败（如取数断网），当天 record 与 review 都不跑（与 record 先例同行为）；review 每次扫描**所有**未对账记录，次日恢复后自动补上，不会漏。
- **既有行为观察（未改）**：真实账本现存 5 条记录都是"零信号日"（picks/alarms 均空），review 的既有逻辑对这类记录不写 review 键也不标 `done`（`and group` 条件所致），因此每天会被重扫一遍——无害（无可对账内容、不写盘），属既有逻辑，S1 未动，留给后续统一账本（选项③）时一并处理。
- registry/INDEX 登记、ARCHIVE 封存段：随总交付（S2 完成）统一办理。

## 5. S2：两套成绩只读并排展示

### 5.1 形态选择与理由

- **后端**：新增 `src/lei_signal/api/fwd_ledger.py`（纯函数聚合）+ `routes/fwd_ledger.py`（仅 1 个 GET 端点 `/api/fwd-ledger/scorecard`），在 `app.py` 注册为新 router——**完全不动既有路由文件与端点**，对齐 macd_events.py 先例（api 层纯函数 + routes 注册）。
- **前端**：新增独立只读页 `/fwd`（导航「策略研究」组入口「前向成绩」），而不是塞进既有页签——两套成绩异构（情绪=四桶卡、推荐=按标的表格）、页各自职责已满；独立页对既有页面**零改动**（App.tsx 只加一行 Route，TopNav 只加一个入口）。

### 5.2 API 设计（GET /api/fwd-ledger/scorecard）

- **A 情绪线**（读 `sentiment_signal_journal.json`，路径规则与 sentiment_journal.py 一致）：`sentiment.available/reason/records/reviewedRecords/buckets[]`，四桶 key=pick10/pick20/alarm10/alarm20，每桶 n / winRatePct（收益>0 占比）/ meanPct——口径与 review 命令行输出一致；账本存分数 ×100 成百分点。
- **B 推荐线**（读 `recommendation_journal` 表 outcome，复用既有 `copilot.journal.load_recommendation` 解析标的名称）：`recommendation.available/reason/scoredDates/latestDate/bySymbol[]`，按标的给 t1/t5/t20 各自 n/均值/胜率；outcome 的 chg 本就是百分点，直接聚合不再 ×100（单测钉死该单位）。
- **降级**：账本缺席/损坏/无到期样本/库不可用 → `available=false + reason`（原因原文进响应），不编数；无该档样本的桶/单元格为 null。
- **只读**：无写路由、无写 SQL；单测断言请求前后两个数据源字节不变。

### 5.3 前端

- `web/src/pages/FwdLedgerPage.tsx`（页面）+ `fwdLedgerLogic.ts`（纯展示模型，供回归脚本断言）；复用既有 `.page/.header/.metric` 样式体系，新增少量 `fwd-*` 样式；`client.ts` 增 `fwdLedgerApi.scorecard()` 只读方法；`types.ts` 增对应接口。

### 5.4 验证（详见 raw/s2-api-frontend-verification.log）

1. **API 单测**（`tests/unit/test_fwd_ledger_api.py`，5 例全过，临时 JSON+临时 SQLite）：四桶口径与 review 输出一致、双可用形态与只读性（请求前后数据源字节不变）、缺数据降级（available=false+原因）、有存证无到期样本降级、损坏 outcome 行跳过不崩。
2. **前端构建**：`tsc --noEmit && vite build` 通过。
3. **前端回归**：既有 11 个回归脚本全部 PASS，新增 `test:fwd-ledger` PASS（断言四桶渲染、按标的渲染、名称回退、空档位为空、降态/加载态文案）；`test:structure-controls` 失败为**既有失败**（干净树上同样失败，与本阶段无关）。
4. **后端回归**：`tests/unit` 全量 2382 passed / 28 failed / 8 errors——失败集在**干净树上逐项复现**（b1_contract、factor 冻结协议、fundamentals、newsfeed_push、symbol_extraction、research preflight），全部既有、与本阶段无关；本阶段新增 5 例全过。
5. **冒烟三形态**：双可用（四桶+按标的数值与手算一致）、双降级（原因文案正确）。

### 5.5 限制

- 生产真实数据当前情绪账本无到期样本、推荐线 outcome 极少——上线初期页面很可能显示降级文案，这是**真实状态**而非缺陷。
- `test:structure-controls` 与后端 unit 里的既有失败未在本阶段处理（他线/环境问题，已在 raw 记录清单）。

## ARCHIVE

- 结案时间：2026-09-19。S1 调度接线 + S2 只读并排展示，均在候选分支待验收。
- verdict：passed（工程接线与展示按冻结目标完成；前向验证本身的"成绩好坏"要等样本自然到期累积，不在本次范围）。
